import { test, expect } from "@playwright/test";

import { loginE2EAdmin, seedFullProject } from "../fixtures/seed";

// M02 项目管理 dogfooding spec — P2 spike pilot (2026-05-12)
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M02-project.md
// 范式：两轨方案 B — DOM 主路径 + API 旁路 backend-only P0
//
// 覆盖 testpoint:
//   - [P0] T1.1 创建项目 happy path（DOM）— 命中 §1 L25 G1
//   - [P0-CRITICAL] 🔴 trigger_bug 复现：创建项目后是否跳 login（DOM）— 00-plan.md dogfooding sprint 起点 bug
//   - [P0] T1.2 GET /projects 列表渲染（DOM）— 命中 §1 L26 G2
//   - [P1-API 旁路] tenant 隔离：userB 非成员调 GET /projects/{projectA_id} 返 403 — 命中 §5 L88 T1
//   - [P1-API 旁路] backend project 状态机 archived → active 禁转 409 — 命中 §2 L44
//
// punt 清单（不进本 spike）:
//   - 大量 §6 并发乐观锁（C1-C6）— backend pytest
//   - §11 AES 加密 helper — backend unit test
//   - §7 数据完整性 CHECK 约束 — backend integration
//   - §12 baseline-patch / §14 ErrorCode parity — backend lint/CI 守护
//   - viewer/editor 权限三层 — 需多种子户口 / spike 时间不允许 / P2 模块本批补
//
// 范式说明：M02 是 dogfooding trigger_bug 主舞台（"创建项目后跳 login"）/ DOM 路径必走。

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M02 项目管理 dogfooding", () => {
  test("[P0] create-project happy path — DOM 主路径 page.goto /projects/new + form 填写 + 跳详情页", async ({
    page,
  }) => {
    // testpoint §1 L25 G1: POST /api/projects owner 创建 201 + 多表事务
    // DOM 视角化简：点新建 → 填 name/template → submit → 跳 /projects/{id}
    await page.goto("/projects/new");
    await expect(page.getByRole("heading", { name: "新建项目" })).toBeVisible();

    const projectName = `DOM Spike ${Date.now()}`;

    // page.tsx L120-127 实证：Label htmlFor="name" + Input id="name"
    await page.getByLabel("项目名称").fill(projectName);
    await page.getByLabel("项目描述").fill("DOM spike pilot 创建 / P2 范式验证");

    // 默认 selectedTemplate="product_analysis"（page.tsx L67）/ 不点其他模板
    // 监听 createProject server action 触发的 POST /api/projects（rewrites 转到 backend）
    // server action 由 Next.js 提交 / 注意走 server-side fetch / 浏览器看到的是 server action 调用而非直接 POST

    await page.getByRole("button", { name: /创建项目|创建中/ }).click();

    // 关键：page.tsx L91 `router.push(/projects/{id})` → 跳到详情页（UUID 路径）
    // 若 trigger_bug 真存在 → 不会跳 /projects/{uuid} 而是 /login
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}/, { timeout: 15_000 });

    // 详情页 DOM 验（projects/[projectId]/page.tsx 渲染 ProjectWorkspace / 验工作区存在）
    // 不直接验项目 name 文案（workspace.tsx 复杂 / 验 URL + 不是 /login 已等效）
    expect(page.url()).not.toContain("/login");
  });

  test("[P0-CRITICAL] 🔴 trigger_bug 复现：创建项目后是否跳 login（dogfooding sprint 起点 bug）", async ({
    page,
  }) => {
    // 00-plan.md 字面: "创建项目后跳 login" 是浏览器路径 bug（cookie/redirect/SSR/hydration）
    // p1-p2-gate-finding.md L13 列为 DOM 测试核心价值
    //
    // 复现路径（CY 拍板第一条 dogfooding bug）：
    //   1. storageState 已登录态（playwright.config 默认 / 含 refresh cookie）
    //   2. page.goto /projects/new
    //   3. 填 form → submit
    //   4. 看 URL：跳 /projects/{uuid} = 已修 / 跳 /login = bug 真复现
    //
    // 这条 test 不能 try/catch 兜底（feedback_subagent_sprint §2 T1）/ 不能 monkeypatch
    // 真路径打 / 报到 spike-report.md

    await page.goto("/projects/new");
    await expect(page.getByRole("heading", { name: "新建项目" })).toBeVisible({ timeout: 10_000 });

    const projectName = `TriggerBug Repro ${Date.now()}`;
    await page.getByLabel("项目名称").fill(projectName);
    await page.getByLabel("项目描述").fill("trigger_bug 复现 spike pilot");

    // 同时监听重定向 / 验证浏览器实际跳到哪
    await page.getByRole("button", { name: /创建项目|创建中/ }).click();

    // 等待跳转完成（要么 /projects/{id} 要么 /login）
    // 用 waitForURL 任一匹配 → 拿到最终 URL 判断是否 trigger_bug
    await page.waitForURL(
      (url) => /\/projects\/[0-9a-f-]{36}/.test(url.pathname) || url.pathname === "/login",
      { timeout: 15_000 },
    );

    const finalUrl = page.url();
    const wentToLogin = finalUrl.includes("/login");

    // 这是 trigger_bug assertion 核心
    // 如果 bug 已修 → 期望跳 /projects/{uuid} / 这条 PASS
    // 如果 bug 真复现 → 跳 /login / 这条 FAIL（spike subagent 报到 spike-report 进入 03-bug-queue.md）
    expect(
      wentToLogin,
      `trigger_bug 复现: 创建项目后跳到了 /login 而非 /projects/{uuid} (final url: ${finalUrl})`,
    ).toBe(false);

    // 如果跳了 /projects/{uuid} → 验项目详情页 DOM
    expect(finalUrl).toMatch(/\/projects\/[0-9a-f-]{36}/);
  });

  test("[P0] list projects DOM — page.goto /projects + 已 seed 项目卡片渲染", async ({
    page,
    request,
  }) => {
    // testpoint §1 L26 G2: GET /api/projects 列表
    // 先 seed 一个项目（API 路径 / 不走 DOM seed 避免抖）
    const seeded = await seedFullProject(request);

    await page.goto("/projects");
    await expect(page).toHaveURL(/\/projects(?!\/login|\/new)/);

    // 我的项目 tab（默认 activeTab="personal" / page.tsx L45）
    await expect(page.getByText("我的项目")).toBeVisible();

    // 验种子项目卡片出现（page.tsx L172 `<h3>{project.title}</h3>`）
    // 等卡片渲染（useEffect 异步拉 → setApiProjects → grid 渲染）
    await expect(page.getByRole("heading", { name: seeded.project.name })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("[P1-API 旁路] backend tenant 隔离：非成员访问别人项目返 403", async ({ request }) => {
    // testpoint §5 L88 T1: userB 非成员调 GET /projects/{projectA_id} 返 PERMISSION_DENIED 403
    // 无 DOM 入口（前端 ProjectsPage 只列自己有成员的项目 / 无法尝试访问陌生 project_id）
    // → API 旁路 / 范式 B 验证

    // 用 e2e admin 创建 projectA
    const { accessToken: adminToken } = await loginE2EAdmin(request);
    const createRes = await request.post(`${API_BASE}/api/projects`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        name: `Tenant Iso A ${Date.now()}`,
        description: "tenant 隔离 A 项目",
        template_type: "custom",
      },
    });
    expect(createRes.status()).toBe(201);
    const projectA = await createRes.json();

    // 注：完整两用户场景需要 admin 创建 userB / 现 e2e fixture 只 1 admin
    // → spike 范围内验"无 token 访问别人项目"也命中 401/403 路径
    // （完整 userB seed 需 phase2 prompt 加 fixture / 留 punt）

    // 子场景 1: 无 Authorization 头 → 401（require_user Depends 拦）
    const noAuthRes = await request.get(`${API_BASE}/api/projects/${projectA.id}`);
    expect([401, 403]).toContain(noAuthRes.status());

    // 子场景 2: 用错误格式 token → 401
    const badAuthRes = await request.get(`${API_BASE}/api/projects/${projectA.id}`, {
      headers: { Authorization: "Bearer not-a-real-jwt" },
    });
    expect(badAuthRes.status()).toBe(401);

    // 子场景 3 (本 spike 落不下 / 留 punt 到 phase2 完整 case)：
    //   - 需要 admin POST /auth/users 创建 userB
    //   - 用 userB token 调 GET /projects/{projectA.id} → 期望 403 PERMISSION_DENIED
    //   - spike-report 记 phase2 需补 userB fixture
  });

  test("[P1-API 旁路] backend 状态机：archived → archived 拒转 409 PROJECT_ALREADY_ARCHIVED", async ({
    request,
  }) => {
    // testpoint §2 L44: archived → archived 重复归档拒转返 PROJECT_ALREADY_ARCHIVED 409
    // 当前 page.tsx 列表无归档按钮 UI（仅 PRD 提及 / design §6 dialog 未实装入口）
    // → API 旁路 / 范式 B 验证

    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 1. 创建项目（active）
    const createRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: {
        name: `Archive Test ${Date.now()}`,
        description: "状态机禁转 spike",
        template_type: "custom",
      },
    });
    expect(createRes.status()).toBe(201);
    const project = await createRes.json();
    expect(project.status).toBe("active");

    // 2. 首次归档 → 200 / status=archived
    const archive1Res = await request.post(`${API_BASE}/api/projects/${project.id}/archive`, {
      headers: auth,
    });
    // 部分实现可能返 200 或 204 / 实证后端约定
    expect([200, 204]).toContain(archive1Res.status());

    // 3. 二次归档 → 409 PROJECT_ALREADY_ARCHIVED（testpoint §2 L44）
    const archive2Res = await request.post(`${API_BASE}/api/projects/${project.id}/archive`, {
      headers: auth,
    });
    // 若 backend 已实装该禁转 → 409；若未实装 / 幂等返 200 → spike-report 记 design vs impl 漂移
    if (archive2Res.status() === 409) {
      const body = await archive2Res.json();
      expect(body.code || body.error_code || JSON.stringify(body)).toMatch(/ARCHIVED|already/i);
    } else {
      // 不让 test 静默通过（feedback_subagent_sprint §2 T1：禁 try/catch 吞错）
      // 记录真实状态码到 fail message / spike-report 决定下步
      expect(
        archive2Res.status(),
        `archived → archived 期望 409 实际 ${archive2Res.status()}`,
      ).toBe(409);
    }
  });
});
