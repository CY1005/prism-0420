import { test, expect } from "@playwright/test";

// Phase 2.3 子 sprint B — e2e #9 / SKELETON
// 范围：M18 语义搜索 / search query → embedding match → 结果列表
// 关键断言：query 200 + results.length > 0 + DOM 渲染 cards
// 当前状态：SKELETON / 需 embedding seed + mock provider

test.describe.skip("semantic search / SKELETON", () => {
  test("search query returns embedding-matched results", async ({ page }) => {
    await page.goto("/search");
    // TODO
    expect(true).toBe(true);
  });
});
