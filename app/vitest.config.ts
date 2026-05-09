import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    // Phase 2.3 子 sprint B — 排除 Playwright e2e 目录（它们用 @playwright/test 不是 vitest）
    exclude: ["**/node_modules/**", "**/dist/**", "**/.next/**", "**/e2e/**"],
  },
  resolve: {
    alias: {
      "@": new URL("./src", import.meta.url).pathname,
    },
  },
});
