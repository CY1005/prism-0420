import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #9 M18 search smoke（embedding seed + mock provider 真跑推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M18 search — smoke API 路径", () => {
  test("query 200 + search_mode 字段存在（无 embedding 走 keyword_only / PRD AC4）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const searchRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/search`, {
      headers: auth,
      data: { query: "Root Module" },
    });
    expect(searchRes.ok()).toBeTruthy();
    const body = await searchRes.json();
    expect(body).toHaveProperty("results");
    expect(Array.isArray(body.results)).toBe(true);
    expect(body).toHaveProperty("search_mode");
  });

  test("query > 200 char → 400 INVALID_QUERY_LENGTH（design §7 line 663）", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const longQuery = "x".repeat(201);
    const searchRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/search`, {
      headers: auth,
      data: { query: longQuery },
    });
    expect(searchRes.status()).toBe(400);
  });

  test("empty query → 422 Pydantic min_length=1", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const searchRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/search`, {
      headers: auth,
      data: { query: "" },
    });
    expect(searchRes.status()).toBe(422);
  });
});

// M18 happy path 推下次（pgvector 真接通 + 真业务 path 启用 + embedding worker 真跑 + mock
// embedding provider 全栈 + cosine similarity 排序）：cross-sprint pool §"性能黑洞" 触发条件
