import { test, expect } from "@playwright/test";

// M01 用户账号 dogfooding spec — P2 spike pilot (2026-05-12)
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M01-user-account.md
// 范式：两轨方案 B — DOM 主路径 + API 旁路 backend-only P0
//
// 覆盖 testpoint（DOM 路径 / 5 tests / 2 API 旁路 / 1 unauth opt-out）:
//   - [P0] T1.1 /auth/login 邮箱密码正确（DOM）— 命中 testpoints §1 L25 (G1)
//   - [P0] T3.1 错密码登录 INVALID_CREDENTIALS 401（DOM 报错文案）— 命中 §3 L60 (L2)
//   - [P0] T1.6 /register UI（DOM）— 当前实现为"暂未开放自助注册"提示，非真注册 → 测真实 UI 而非 testpoint 漂走
//   - [P0] AuthProvider mount auto /auth/refresh（DOM trigger_bug 范式）— 命中 R-X1 cookie sync / ADR-004 #5
//   - [P1] storageState opt-out 后 /login 不被自动跳走（unauth 范式验证）— P2 范式红线（test.use opt-out 缺漏 = 进 page 被 auth 重定向）
//
// punt 清单（不进本 spike）:
//   - [P0] M01 大量 P0 在 §10 ADR-004 P2 凭据路径（HMAC 签名）— backend-only API/integration（INTERNAL_TOKEN 不进浏览器）/ phase2-case Forbidden 红线明确这类走 backend integration test 不进 playwright
//   - [P0] /auth/refresh 直接走 API 测刷 token 路径 — backend 已有 pytest 覆盖
//   - [P0] §6 并发乐观锁 / §10 token_invalidated_at 撤销链 — backend pytest
//   - [P0] 注册 happy path — 当前实现是 admin-invite-only / 非自助注册（page.tsx 字面"暂未开放自助注册"）/ spike 报到 spike-report 作 design vs UI 漂移 finding
//
// 范式注释：M01 testpoint L25/L60/L77 这些 backend testpoint 在 DOM 视角下化简为
// "登录页交互 → 后端 200/401/423 → 前端 toast 文案" 的端到端，DOM 测的是契约的浏览器侧效果。

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

// Unauth specs（M01 登录/注册）：必加 opt-out / 防 storageState 自动跳到 /projects
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("M01 用户账号 dogfooding", () => {
  test("[P0] login happy path — DOM 路径填表单 + 跳转 + cookie 已设", async ({ page, context }) => {
    // 1. 进登录页（未登录态 / storageState 已清）
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Prism/i })).toBeVisible();

    // 2. DOM 填表单（用 page.tsx 实证的 label "邮箱" / "密码"）
    await page.getByLabel("邮箱").fill("e2e@example.com");
    await page.getByLabel("密码").fill("Password123!");

    // 3. 监听 /auth/login 请求（验真 POST 走出去 / 不是前端 zod 拦死）
    const loginRequestPromise = page.waitForRequest(
      (req) => req.url().includes("/auth/login") && req.method() === "POST",
    );

    await page.getByRole("button", { name: "登录" }).click();

    const loginReq = await loginRequestPromise;
    expect(loginReq.method()).toBe("POST");

    // 4. 跳转 /projects（design §1 + login/page.tsx L34 router.push("/projects")）
    await expect(page).toHaveURL(/\/projects(?!\/login)/, { timeout: 8_000 });

    // 5. 旁路验 refresh cookie 已设（httpOnly / Path=/auth / Strict / global-setup 注释证）
    const cookies = await context.cookies();
    const refreshCookie = cookies.find((c) => c.name.toLowerCase().includes("refresh"));
    expect(refreshCookie, "refresh_token cookie should be set after login").toBeTruthy();
    expect(refreshCookie?.httpOnly).toBe(true);
  });

  test("[P0] login invalid password — DOM 报错 toast 邮箱或密码错误", async ({ page }) => {
    // testpoint §3 L60: 错密码登录返 INVALID_CREDENTIALS 401（design §13 + tests.md L2）
    // DOM 侧：login/page.tsx L37 `if (e.status === 401) setError("邮箱或密码错误")` → div role="alert"
    await page.goto("/login");

    await page.getByLabel("邮箱").fill("e2e@example.com");
    await page.getByLabel("密码").fill("wrong-password-1234");

    // 验请求真发出 + 后端真返 401（不允许 monkeypatch / 走真路径）
    const responsePromise = page.waitForResponse(
      (res) => res.url().includes("/auth/login") && res.request().method() === "POST",
    );
    await page.getByRole("button", { name: "登录" }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(401);

    // DOM 报错文案（login/page.tsx L37 字面）
    // 🔴 Next.js 自定义版坑：__next-route-announcer__ 也是 role=alert / getByRole 严格模式 fail
    // → 用文本定位定到业务侧 alert 而非 Next 内部 announcer
    await expect(page.getByText("邮箱或密码错误")).toBeVisible({ timeout: 5_000 });
    // 验证业务 alert（bg-red-50 类）真渲染了 / 不是 Next announcer 自带 role 误判
    await expect(page.locator('div[role="alert"].bg-red-50')).toBeVisible();

    // 不应该跳走
    await expect(page).toHaveURL(/\/login$/);
  });

  test("[P0] register page — 实现是 admin-invite-only 而非自助注册（DOM 文案验证 + design 漂移登记）", async ({
    page,
  }) => {
    // 范式 finding：M01 testpoint L25 含"register happy path"语义但 register/page.tsx 实测无 form
    // 仅"暂未开放自助注册"提示（M01 design §4 Q1=B/C/D 待扩展）。
    // 处置：DOM 测真实 UI（不能编造 form 字段）/ design vs UI 漂移记到 spike-report
    await page.goto("/register");

    await expect(page.getByRole("heading", { name: /Prism/i })).toBeVisible();
    await expect(page.getByText("暂未开放自助注册")).toBeVisible();
    await expect(page.getByText(/请联系管理员开通账号/)).toBeVisible();
    await expect(page.getByRole("link", { name: "登录" })).toBeVisible();

    // 链接真能点到 /login（DOM 跳转端到端）
    await page.getByRole("link", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("[P0] AuthProvider mount 自动触发 /auth/refresh（cookie sync trigger_bug 范式 / R-X1）", async ({
    page,
    context,
  }) => {
    // 先用 API context 拿 refresh cookie（loginE2EAdmin 行为 / 不内联 helper / 用真 fetch）
    const apiCtx = await page.request;
    const loginRes = await apiCtx.post(`${API_BASE}/auth/login`, {
      data: { email: "e2e@example.com", password: "Password123!" },
    });
    expect(loginRes.ok()).toBeTruthy();

    // 现在 context 有 refresh cookie 了 / 模拟用户已登录但 access_token 内存丢失的"刷新页面"路径
    // 这是 ADR-004 #5 + auth-context.tsx L55-66 AuthProvider mount /auth/refresh 续杯路径
    // trigger_bug 类：浏览器 cookie 真带过去 + 前端 mount 真发请求 + 后端真接收

    const refreshRequestPromise = page.waitForRequest(
      (req) => req.url().includes("/auth/refresh") && req.method() === "POST",
      { timeout: 10_000 },
    );

    await page.goto("/projects");

    const refreshReq = await refreshRequestPromise;
    expect(refreshReq.method()).toBe("POST");

    // 应留在 /projects（refresh 成功 → access_token 填回 → user state 设 → 不 redirect /login）
    await expect(page).toHaveURL(/\/projects(?!\/login)/, { timeout: 8_000 });

    // 验 cookie 仍在（refresh 后 backend rotate refresh_token / 但 cookie 应仍存在）
    const cookies = await context.cookies();
    const refreshCookie = cookies.find((c) => c.name.toLowerCase().includes("refresh"));
    expect(refreshCookie).toBeTruthy();
  });

  test("[P1] storageState opt-out 后 page.goto /login 不被自动跳到 /projects", async ({ page }) => {
    // playwright.config.ts L25 storageState 默认带登录态 → 顶部 test.use({cookies:[]}) 已清
    // 验证 opt-out 真生效（不然 unauth 测试根本测不到 / 范式红线）
    await page.goto("/login");
    // 应停在 /login（如果 cookie 没清，AuthProvider mount → refresh → 跳 /projects）
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByLabel("邮箱")).toBeVisible();
    await expect(page.getByLabel("密码")).toBeVisible();
  });
});
