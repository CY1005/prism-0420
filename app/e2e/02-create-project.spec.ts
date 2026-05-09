import { test, expect } from "@playwright/test";

// Phase 2.3 子 sprint B — e2e #2 / SKELETON
// 范围：登录后创建项目 → 跳详情页 → 验证 capability-matrix activity_log 追加 project_created
// 当前状态：SKELETON 待 DB seed fixture 落地（admin 用户 + login session 复用）
// 触发激活条件：
//   1) backend e2e 引入 conftest 级 admin user fixture（参考 tests/conftest.py make_admin_user）
//   2) e2e 加 storageState fixture：单次 login → 复用 cookie
// 预期完整断言（待激活时填）：
//   - POST /projects 200 + body.id !== null
//   - 跳转 /projects/{id} URL 匹配
//   - DOM 含项目名称 + 描述
//   - GET /activity-stream/{project_id}/events 含 action_type="project_created"

test.describe.skip("create project / SKELETON", () => {
  test("logged-in user creates project + redirects to detail", async ({ page }) => {
    // TODO: storageState login fixture
    await page.goto("/projects/new");
    await page.getByLabel(/项目名|name/i).fill(`E2E Test Project ${Date.now()}`);
    await page.getByLabel(/描述|description/i).fill("Phase 2.3 e2e #2");
    await page.getByRole("button", { name: /创建|create/i }).click();
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]{36}/);
  });
});
