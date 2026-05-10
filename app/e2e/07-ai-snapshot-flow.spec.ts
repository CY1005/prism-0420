import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #7 M16 AI snapshot smoke（mock provider 全栈推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M16 AI snapshot — smoke API 路径", () => {
  test("trigger generate — 422 业务码（ai_provider 未配置 / version 不足）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // seedFullProject 没配 ai_provider 也没 version；任一不满足都返 422 + 业务 code
    const triggerRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/snapshot/generate`,
      { headers: auth },
    );
    expect(triggerRes.status()).toBe(422);
    const body = await triggerRes.json();
    expect(body).toHaveProperty("code");
    expect(["snapshot_provider_not_configured", "snapshot_insufficient_versions"]).toContain(
      body.code,
    );
  });

  test("trigger generate after ai_provider configured — version_count < 3 → 422", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 配 ai_provider（不真调 LLM；M16 service 内部 schema 校验先于 provider 调用）
    const aiRes = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      headers: auth,
      data: { ai_provider: "claude", ai_api_key: "sk-mock-test-key" },
    });
    expect(aiRes.ok()).toBeTruthy();

    const triggerRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/snapshot/generate`,
      { headers: auth },
    );
    expect(triggerRes.status()).toBe(422);
    const body = await triggerRes.json();
    expect(body.code).toBe("snapshot_insufficient_versions");
  });
});

// M16 happy path 推下次（mock AI provider 全栈 + 3+ versions seed + 后台 runner 真跑 +
// poll status 变迁）：cleanup-plan §433 Task 2.3 完整断言子片
