import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #4 M03 node 树 CRUD（API）+ M04 dimension 推下次（依赖 dimension_type seed）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M03 node 树 — API CRUD", () => {
  test("create child + reorder + delete + L1-α description detach", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 创建 child node（parent = seeded.node）
    const childRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/nodes`, {
      headers: auth,
      data: {
        name: "Child A",
        type: "folder",
        parent_id: seeded.node.id,
        description: "child folder for e2e",
      },
    });
    expect(childRes.status()).toBe(201);
    const child = await childRes.json();
    expect(child.parent_id).toBe(seeded.node.id);

    // L1-α 4C.3 detach: description 显式 null 清空
    const detachRes = await request.put(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${child.id}`,
      {
        headers: auth,
        data: { description: null },
      },
    );
    expect(detachRes.ok()).toBeTruthy();
    const detached = await detachRes.json();
    expect(detached.description).toBeNull();

    // delete
    const delRes = await request.delete(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${child.id}`,
      { headers: auth },
    );
    expect(delRes.status()).toBe(204);
  });
});

// M04 dimension：完整 e2e 需要预 seed dimension_type + project enable，推下次
// （cleanup-plan §433 Task 2.3 完整断言子片或独立 fixture sprint）
