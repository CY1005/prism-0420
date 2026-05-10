import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #8 M19 export API（M17 import + WS 推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M19 export — markdown 多 node + 单 node API 路径", () => {
  test("export multi-node returns markdown body", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const exportRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/exports`, {
      headers: auth,
      data: {
        node_ids: [seeded.node.id],
        include: { dimensions: true, issues: true, competitors: true, versions: true },
      },
    });
    expect(exportRes.ok()).toBeTruthy();
    expect(exportRes.headers()["content-type"]).toContain("text/markdown");
    const body = await exportRes.text();
    expect(body.length).toBeGreaterThan(0);
    // markdown 含项目名 / node 名（design §7 章节 head）
    expect(body).toContain(seeded.project.name);
  });

  test("export single-node 入口 B 等价 A", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const exportRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/export`,
      {
        headers: auth,
        data: { include: { dimensions: true, issues: true } },
      },
    );
    expect(exportRes.ok()).toBeTruthy();
    expect(exportRes.headers()["content-type"]).toContain("text/markdown");
    const body = await exportRes.text();
    expect(body.length).toBeGreaterThan(0);
  });

  test("export include all-false 422 业务码（R1-C P1-2 立修）", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const exportRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/exports`, {
      headers: auth,
      data: {
        node_ids: [seeded.node.id],
        include: {
          dimensions: false,
          issues: false,
          competitors: false,
          versions: false,
        },
      },
    });
    expect(exportRes.status()).toBe(422);
  });
});

// M17 import zip + WS 进度推下次：
// - multipart/form-data 上传 zip fixture 文件
// - WebSocket 客户端连 /ws/import-progress/{task_id}（playwright.WebSocket 有限支持）
// - 期待 task: pending → running → succeeded / progress 0 → 100
// 复杂度：multipart fixture 文件 + WS 客户端端到端 + import 异步路径需要 worker 真跑
