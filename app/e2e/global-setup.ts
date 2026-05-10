import { request, type FullConfig } from "@playwright/test";
import * as fs from "node:fs";
import * as path from "node:path";

import { loginE2EAdmin } from "./fixtures/seed";

// Sprint 2 Task 2.2 — storageState login share（cleanup-plan §401）
// 一次 login → 存储 access_token + refresh cookie → 所有 e2e 自动带登录态
// 对 prism-0420 auth 范式（Phase 2.2 子片 2）：
//   - access_token 在内存 React context（前端 mount 时 /auth/refresh 拿）
//   - refresh_token 在 httpOnly cookie / Path=/auth / Strict
//   - storageState 主要是 refresh cookie（access 是内存的，每次刷新页面会重 refresh）

const STORAGE_DIR = path.join(__dirname, ".auth");
const STORAGE_PATH = path.join(STORAGE_DIR, "storage.json");

async function globalSetup(_config: FullConfig) {
  fs.mkdirSync(STORAGE_DIR, { recursive: true });

  // 第一步：API context login → set httpOnly refresh cookie
  const apiCtx = await request.newContext();
  await loginE2EAdmin(apiCtx);
  const apiState = await apiCtx.storageState();
  await apiCtx.dispose();

  // 第二步：写到 storage.json（含 refresh cookie）
  // 注：access_token 是 in-memory React context / 每次页面 mount 重 /auth/refresh 拿
  // 所以 e2e 用 storageState 启动 → 页面 mount → AuthProvider auto refresh → 走业务页面
  fs.writeFileSync(STORAGE_PATH, JSON.stringify(apiState, null, 2));
  console.log(`[global-setup] storageState saved to ${STORAGE_PATH}`);
}

export default globalSetup;
