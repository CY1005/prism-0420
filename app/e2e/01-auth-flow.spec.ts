import { test, expect } from "@playwright/test";

// Phase 2.3 子 sprint B — pilot e2e #1
// 范围：登录页加载 + 错误密码反馈 + 注册页"暂未开放"提示
// scope 限制：本 pilot 不依赖 DB 中的 admin 用户（避免 e2e 级 DB seeding 复杂度）；
//   完整 happy path（登录 + 跳转 + 业务 endpoint）推 02+ skeleton 在 backend e2e seed fixture 落地后启用

test.describe("auth flow / 登录页基础", () => {
  test("login page renders + invalid credentials show error", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /Prism/i })).toBeVisible();
    await expect(page.getByLabel(/邮箱|email/i).first()).toBeVisible();
    await expect(page.getByLabel(/密码|password/i).first()).toBeVisible();

    // 填错误凭据 → 期望显示错误消息（不依赖 DB seed / 401 路径全栈打通）
    await page
      .getByLabel(/邮箱|email/i)
      .first()
      .fill("nonexistent@example.com");
    await page
      .getByLabel(/密码|password/i)
      .first()
      .fill("wrong-password-1234");
    await page.getByRole("button", { name: /登录|sign in/i }).click();

    // 后端 401 → 前端展示"邮箱或密码错误"
    await expect(page.getByText(/邮箱或密码错误|invalid|错误/i)).toBeVisible({ timeout: 8_000 });
  });

  test("register page shows admin-invite-only notice", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByText(/暂未开放自助注册|admin/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /登录|sign in/i })).toBeVisible();
  });
});
