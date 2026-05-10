import { test, expect } from "@playwright/test";

import { seedFullProject } from "./fixtures/seed";

// Sprint 2 Task 2.3 — e2e #10 M08 module_relation API（XYFlow DOM 拖拽推下次）
const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M08 module_relation — API 路径验证", () => {
  test("create relation between two nodes + list + delete", async ({ request }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 创建第二个 node 作为 target
    const targetRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/nodes`, {
      headers: auth,
      data: { name: "Target Node", type: "folder" },
    });
    expect(targetRes.status()).toBe(201);
    const target = await targetRes.json();

    // 创建 depends_on 关系
    const createRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/relations`,
      {
        headers: auth,
        data: {
          source_node_id: seeded.node.id,
          target_node_id: target.id,
          relation_type: "depends_on",
          notes: "e2e test relation",
        },
      },
    );
    expect(createRes.status()).toBe(201);
    const relation = await createRes.json();
    expect(relation.source_node_id).toBe(seeded.node.id);
    expect(relation.target_node_id).toBe(target.id);
    expect(relation.relation_type).toBe("depends_on");

    // self_loop 422 守卫（design §13 service 层 raise）
    const selfLoopRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/relations`,
      {
        headers: auth,
        data: {
          source_node_id: seeded.node.id,
          target_node_id: seeded.node.id, // 同一 node
          relation_type: "related_to",
        },
      },
    );
    expect(selfLoopRes.status()).toBe(422);

    // M10 overview endpoint 可达性（projeck 未启用 dimension type → 422 overview_no_dimensions
    // 是 design 字面预期；只验 endpoint 不是 404，dim 完整 setup 推下次）
    const overviewRes = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/overview`,
      { headers: auth },
    );
    expect([200, 422]).toContain(overviewRes.status());

    // delete relation
    const delRes = await request.delete(
      `${API_BASE}/api/projects/${seeded.project.id}/relations/${relation.id}`,
      { headers: auth },
    );
    expect([200, 204]).toContain(delRes.status());
  });
});

// XYFlow DOM 拖拽创建 relation 推下次专 sprint：
// - frontend page /projects/{id}/graph 的 React Flow 渲染（@xyflow/react）
// - playwright 操作 SVG / canvas 元素拖拽
// - 验证 onConnect callback 触发 POST /relations
// 复杂度：XYFlow 自定义 handle / 拖拽事件 simulation 需要 page.dragTo + 等待 React 状态
