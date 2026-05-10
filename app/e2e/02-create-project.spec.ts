import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.1+2.2 pilot 激活：DB seed fixture + storageState login share 真打通
// （cleanup-plan §433 Task 2.3 e2e #2-#10 完整 DOM 断言推下次新会话 / 本 pilot 只验基础设施工作）
//
// 完整断言推下次（Task 2.3 范围）：
//   - 跳转 /projects/{id} URL 匹配 + DOM 项目名
//   - GET /activity-stream/{project_id}/events 含 action_type="project_created"

test.describe("M02 projects — Sprint 2 基础设施 pilot", () => {
  test("seedFullProject 创建完整种子项目（API 路径）", async ({ request }) => {
    // 验证 Task 2.1：seedFullProject API 调用全栈打通
    const seeded = await seedFullProject(request);
    expect(seeded.project.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(seeded.project.name).toContain("E2E Project");
    expect(seeded.node.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(seeded.issue.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(seeded.accessToken.length).toBeGreaterThan(20);
  });

  test("storageState 让 page 直接进 /projects 不被 redirect 到 /login", async ({ page }) => {
    // 验证 Task 2.2：global-setup login → 所有 e2e 自动带 refresh cookie
    await page.goto("/projects");
    // AuthProvider mount → /auth/refresh → access_token → 留在 /projects（非 redirect /login）
    await expect(page).toHaveURL(/\/projects(?!\/login)/, { timeout: 8_000 });
  });
});
