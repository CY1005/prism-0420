import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #5 M06 competitor + ref（API 验证 / DOM 推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M06 competitor + ref — API 路径", () => {
  test("create competitor + link ref to node + list refs", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const compRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/competitors`,
      {
        headers: auth,
        data: { display_name: "RivalCo", website_url: "https://rival.example.com" },
      },
    );
    expect(compRes.status()).toBe(201);
    const competitor = await compRes.json();
    expect(competitor.id).toMatch(/^[0-9a-f-]{36}$/);

    // M06 ref：在 node 上引用 competitor
    const refRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/competitor-refs`,
      {
        headers: auth,
        data: {
          competitor_id: competitor.id,
          competitor_version: "v1.0",
          feature_coverage: "覆盖核心功能",
          tech_approach: "REST + Postgres",
        },
      },
    );
    expect(refRes.status()).toBe(201);
    const ref = await refRes.json();
    expect(ref.competitor_id).toBe(competitor.id);
    expect(ref.node_id).toBe(seeded.node.id);

    // L1-α 4C.3 验证：detach pros_and_cons（PUT 显式 None 清空）
    const detachRes = await request.put(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/competitor-refs/${ref.id}`,
      {
        headers: auth,
        data: { feature_coverage: null }, // 显式 null = detach
      },
    );
    expect(detachRes.ok()).toBeTruthy();
    const detached = await detachRes.json();
    expect(detached.feature_coverage).toBeNull();
  });
});
