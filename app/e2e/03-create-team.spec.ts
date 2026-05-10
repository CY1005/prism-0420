import { test, expect } from "@playwright/test";

import { loginE2EAdmin } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #3 M20 team CRUD（API 验证 / DOM 完整断言推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M20 teams — API 路径验证", () => {
  test("create team + list shows it + transfer-eligible default", async ({ request }) => {
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `E2E Team ${Date.now()}`, description: "Sprint 2 #3 e2e" },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();
    expect(team.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(team.creator_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(team.version).toBe(1); // 乐观锁初值

    const listRes = await request.get(`${API_BASE}/api/teams`, { headers: auth });
    expect(listRes.ok()).toBeTruthy();
    const list = (await listRes.json()) as Array<{ id: string }>;
    expect(list.some((t) => t.id === team.id)).toBe(true);

    const detailRes = await request.get(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
    expect(detailRes.ok()).toBeTruthy();
    const detail = await detailRes.json();
    expect(detail.name).toBe(team.name);
  });
});
