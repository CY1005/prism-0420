import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #6 M07 issue + D 类 #3 join 字段实证（API 路径）
// Phase 2.2 子片 5 关闸时 IssueResponse 加 join 字段（node_name / created_by_name / assigned_to_name）；
// 本 spec 验证响应 payload 含字段（DOM 渲染推下次）+ L1-α detach 验证
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M07 issue — join 字段 + L1-α detach 实证", () => {
  test("create issue + GET 含 join 字段（D 类 #3）", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // seedFullProject 已创了一个 issue（node_id + created_by 都已 set / assigned_to=null）
    const getRes = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/issues/${seeded.issue.id}`,
      { headers: auth },
    );
    expect(getRes.ok()).toBeTruthy();
    const issue = await getRes.json();

    // D 类 #3 join 字段实证（Phase 2.2 子片 5 关闸成果）
    expect(issue.node_id).toBe(seeded.node.id);
    expect(issue.node_name).toBe(seeded.node.name); // join from nodes
    expect(issue.created_by).toBe(seeded.user.id);
    expect(issue.created_by_name).toBe("E2E Test Admin"); // user.name (scripts/seed_e2e_admin.py)
    expect(issue.assigned_to).toBeNull();
    expect(issue.assigned_to_name).toBeNull();
  });

  test("L1-α 4C.3 detach: assigned_to 显式 null 清空（保持 status open）", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 先 assign（PUT update with assigned_to=user）
    const assignRes = await request.put(
      `${API_BASE}/api/projects/${seeded.project.id}/issues/${seeded.issue.id}`,
      {
        headers: auth,
        data: { assigned_to: seeded.user.id },
      },
    );
    expect(assignRes.ok()).toBeTruthy();
    expect((await assignRes.json()).assigned_to).toBe(seeded.user.id);

    // 再 detach（PUT update with assigned_to=null）—— L1-α 显式 None = detach
    const detachRes = await request.put(
      `${API_BASE}/api/projects/${seeded.project.id}/issues/${seeded.issue.id}`,
      {
        headers: auth,
        data: { assigned_to: null },
      },
    );
    expect(detachRes.ok()).toBeTruthy();
    const detached = await detachRes.json();
    expect(detached.assigned_to).toBeNull();
    expect(detached.assigned_to_name).toBeNull();
    expect(detached.status).toBe("open"); // 状态不变（不走 transition）
  });

  test("L1-α 4C.3 detach: node_id 显式 null 游离 issue", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const detachRes = await request.put(
      `${API_BASE}/api/projects/${seeded.project.id}/issues/${seeded.issue.id}`,
      {
        headers: auth,
        data: { node_id: null },
      },
    );
    expect(detachRes.ok()).toBeTruthy();
    const floating = await detachRes.json();
    expect(floating.node_id).toBeNull();
    expect(floating.node_name).toBeNull();
  });
});
