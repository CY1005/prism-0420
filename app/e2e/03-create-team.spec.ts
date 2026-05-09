import { test, expect } from "@playwright/test";

// Phase 2.3 子 sprint B — e2e #3 / SKELETON
// 范围：M20 / 创建团队 + 邀请第二用户加入 + 验证 team_member 列表
// 当前状态：SKELETON / 同 #2 待 DB seed
// 预期断言：POST /teams + POST /teams/{id}/members → 200 + DOM 列表渲染

test.describe.skip("create team / SKELETON", () => {
  test("create team and invite member", async ({ page }) => {
    await page.goto("/teams/new");
    // TODO
    expect(true).toBe(true);
  });
});
