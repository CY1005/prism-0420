import { defineConfig, devices } from "@playwright/test";

// Phase 2.3 子 sprint B — Playwright e2e config
// 决策：browser=chromium 单浏览器（其他 browser 上线后加 / shadow 项目最简起步）
// webServer：复用 CY 已起的 pnpm dev（不强行 spawn / 防 port 冲突）
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./e2e",
  // Sprint 2 Task 2.2 — global setup login → storageState 共享 refresh cookie
  globalSetup: require.resolve("./e2e/global-setup"),
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false, // 业务流串行（DB 状态依赖）
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // 注：unauth specs（如 01-auth-flow）需在 spec 顶部 `test.use({ storageState: { cookies: [], origins: [] } });` 显式 opt-out
    storageState: "./e2e/.auth/storage.json",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        extraHTTPHeaders: {
          "x-e2e-api-url": API_URL,
        },
      },
    },
  ],
  // 不配 webServer：CY 启动 pnpm dev / uvicorn / docker compose 后才跑 e2e
  // CI 阶段单独 job 起服务（见 .github/workflows/ci.yml e2e job 推上线 sprint）
});
