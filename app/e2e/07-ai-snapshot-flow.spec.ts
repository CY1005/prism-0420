import { test, expect } from "@playwright/test";

// Phase 2.3 子 sprint B — e2e #7 / SKELETON
// 范围：M16 AI 快照（§12B 后台 fire-and-forget）/ 触发 + 轮询状态 + 验 SSE/状态切换
// 关键断言：POST trigger → 200 + status 变迁 pending → running → succeeded
// 当前状态：SKELETON / 需 mock AI provider 或 dev key

test.describe.skip("AI snapshot flow / SKELETON", () => {
  test("trigger AI snapshot + poll until succeeded", async ({ page }) => {
    // TODO
    expect(true).toBe(true);
  });
});
