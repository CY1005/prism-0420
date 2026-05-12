import type { APIRequestContext } from "@playwright/test";

// Sprint 2 Task 2.1 — DB seed fixture（API 路径，cleanup-plan §370 选项 A）
// 与生产路径一致 / 一次创建一个完整种子项目供 e2e #2-#10 复用
//
// dogfooding P2-close 2026-05-12 改造（opt-in / 默认行为不变）：
//   原默认 (opts={}): project + folder(Root Module) + issue（保持向后兼容）
//   新 opt-in:
//     opts.withEnabledDim=true → 启用 description 维度（M04/M19 file-view happy path）
//     opts.withFileNode=true   → 新增 root-level file 节点 "Root File"（M05/M19 file 视图）
//
// 改造动因（pre-existing FAIL spec / workspace fix 后 seed 状态偏差）:
//   - M04 workspace smoke: seed 无 enabled dimensions → workspace 渲染 "0/0 维度已填写" 不显示
//     dimension card → "点击添加，或上传文档自动分析" 不出现 → spec 断言失配
//   - M05/M19 file-view 路径: seed 仅 folder node / 这些 spec 内联建 file node 重复模板
//
// 向后兼容承诺:
//   - 默认 seedFullProject(request) 行为 100% 跟改造前一致（不启 dim / 不建 file 节点）
//   - SeededProject 接口加 file/dimensionTypeId 可选字段（默认 null）
//   - batch 1-5 已写 22 spec 不受影响
//   - M04 §2 边界 test (enabled_count=0) / M03 M07 M10 等依赖 "seed 无 enabled dims" 边界
//     的 spec 保持原 seed 状态 / 不破边界 assumption
//
// 已知未由本 fixture 修复的 FAIL spec（需 spec-level 修复 / 见上报）:
//   - M04 workspace smoke L138: spec 期望 "点击添加，或上传文档自动分析" 文本可见，
//     但 dimension card defaultExpanded=hasContent / hasContent=false 时折叠 → 文本 hidden
//   - M19 export node happy path L57: spec click folder 节点期待 "导出 Markdown" 按钮，
//     但 workspace L970 仅 file 视图渲染此按钮（design 真实行为）
//   - M19 export button DOM L117: folder 视图 folderChildren 异步加载 / 2s timeout 不够
//   - M11 welcome card L37: workspace sidebar 顶部 "导入文档" link + welcome card "导入文档"
//     2 elements strict-mode 冲突 / 自建 empty project 不走 seed / 跟本 fixture 完全无关

const E2E_EMAIL = "e2e@example.com";
const E2E_PASSWORD = "Password123!";

// description 维度（scripts/seed_dimension_types.py 保证 key=description 存在）
// dimension_types 表 id 不可硬编码（重 seed 会重新分配 id）/ runtime 查 key=description
const SEED_DIMENSION_KEY = "description";

export interface SeededProject {
  accessToken: string;
  user: { id: string; email: string };
  project: { id: string; name: string };
  node: { id: string; name: string };
  /** opt-in：仅在 seedFullProject(opts.withFileNode=true) 时存在 */
  file: { id: string; name: string } | null;
  issue: { id: string; title: string };
  /** opt-in：仅在 seedFullProject(opts.withEnabledDim=true) 时存在 */
  dimensionTypeId: number | null;
}

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

export async function loginE2EAdmin(api: APIRequestContext): Promise<{
  accessToken: string;
  user: { id: string; email: string };
}> {
  const res = await api.post(`${API_BASE}/auth/login`, {
    data: { email: E2E_EMAIL, password: E2E_PASSWORD },
  });
  if (!res.ok()) {
    throw new Error(
      `e2e admin login failed: ${res.status()} ${await res.text()} (run \`uv run python scripts/seed_e2e_admin.py\` first)`,
    );
  }
  const body = await res.json();
  return { accessToken: body.access_token, user: body.user };
}

// 查找 dimension_types 表中 key=description 的 type_id
// 不能 hardcode id（seed_dimension_types.py 重跑会重分配 id / id=2 非永久契约）
// dogfooding P2-close 2026-05-12：通过 GET /dimension-configs 拉取 enabled_dimension_types
// 或 GET /api/dimension-types（admin endpoint TBD）兜底
async function resolveDescriptionDimensionTypeId(
  api: APIRequestContext,
  projectId: string,
  auth: { Authorization: string },
): Promise<number> {
  // 优先：通过 PUT 自动创建/启用 description type（design §3.Y R3-6-C runtime admin）
  // 实际范式（M04 spec setupDimensionForProject helper / 已实战验证）:
  //   1. GET /api/projects/{pid}/dimension-configs 拉当前 configs
  //   2. 若已有 enabled / 直接返其 type_id
  //   3. 否则用已知 type_id（按 key=description 反查）/ PUT enable
  // 这里采用 scripts/seed_dimension_types.py 实际查询路径：直接 GET /api/dimension-types
  // 若该端点不存在 → fallback 用 KNOWN_DIM_TYPE_ID=2（seed_dimension_types.py 当前 seed 顺序）
  const KNOWN_FALLBACK_ID = 2;

  // 尝试 GET /api/dimension-types（global / 不带 projectId）
  // 若端点不存在或返回非 ok / 走 fallback
  const typesRes = await api.get(`${API_BASE}/api/dimension-types`, { headers: auth });
  if (typesRes.ok()) {
    const body = await typesRes.json();
    const items = (body.items ?? body) as { id: number; key: string }[];
    if (Array.isArray(items)) {
      const found = items.find((t) => t.key === SEED_DIMENSION_KEY);
      if (found) return found.id;
    }
  }

  // Fallback: 通过 GET /api/projects/{pid}/dimension-configs 看 enabled_dimension_types
  const cfgRes = await api.get(`${API_BASE}/api/projects/${projectId}/dimension-configs`, {
    headers: auth,
  });
  if (cfgRes.ok()) {
    const body = await cfgRes.json();
    // 该端点返 { items: [{dimension_type_id, enabled, ...}], enabled_dimension_types: [{id, key, ...}] }
    const types = (body.enabled_dimension_types ?? body.dimension_types ?? []) as {
      id: number;
      key: string;
    }[];
    if (Array.isArray(types)) {
      const found = types.find((t) => t.key === SEED_DIMENSION_KEY);
      if (found) return found.id;
    }
  }

  return KNOWN_FALLBACK_ID;
}

export interface SeedOptions {
  suffix?: string;
  /** opt-in：启用 description 维度（M04/M19 file-view happy path 用）/ 默认 false */
  withEnabledDim?: boolean;
  /** opt-in：新增 root-level file 节点 "Root File"（M05/M19 file 视图用）/ 默认 false */
  withFileNode?: boolean;
}

export async function seedFullProject(
  api: APIRequestContext,
  opts: SeedOptions = {},
): Promise<SeededProject> {
  const { accessToken, user } = await loginE2EAdmin(api);
  const auth = { Authorization: `Bearer ${accessToken}` };
  const suffix = opts.suffix ?? `${Date.now()}`;
  const withEnabledDim = opts.withEnabledDim ?? false;
  const withFileNode = opts.withFileNode ?? false;

  const projectRes = await api.post(`${API_BASE}/api/projects`, {
    headers: auth,
    data: {
      name: `E2E Project ${suffix}`,
      description: "Sprint 2 Task 2.1 seed fixture",
      template_type: "custom",
    },
  });
  if (!projectRes.ok()) {
    throw new Error(`project create failed: ${projectRes.status()} ${await projectRes.text()}`);
  }
  const project = await projectRes.json();

  // opt-in 启用 description 维度（默认不启用 / 保 batch 1-5 边界 spec 兼容）
  let dimensionTypeId: number | null = null;
  if (withEnabledDim) {
    dimensionTypeId = await resolveDescriptionDimensionTypeId(api, project.id, auth);
    const enableRes = await api.put(`${API_BASE}/api/projects/${project.id}/dimension-configs`, {
      headers: { ...auth, "Content-Type": "application/json" },
      data: {
        configs: [{ dimension_type_id: dimensionTypeId, enabled: true, sort_order: 1 }],
      },
    });
    if (!enableRes.ok()) {
      throw new Error(
        `dimension-configs enable failed: ${enableRes.status()} ${await enableRes.text()} ` +
          "(prerequisite: run scripts/seed_dimension_types.py)",
      );
    }
  }

  // folder 根节点（保 batch 1-5 兼容 / name="Root Module" 不变 / M18 spec query 仍有效）
  const nodeRes = await api.post(`${API_BASE}/api/projects/${project.id}/nodes`, {
    headers: auth,
    data: { name: "Root Module", type: "folder", description: "seed root node" },
  });
  if (!nodeRes.ok()) {
    throw new Error(`node create failed: ${nodeRes.status()} ${await nodeRes.text()}`);
  }
  const node = await nodeRes.json();

  // opt-in file 节点（M05/M19 file-view 路径复用 / page.tsx findFirstLeaf 优先返 file）
  // 注意：默认进入 workspace 时会自动选中此 file（page.tsx L17 type==="file" 优先）
  // 兼容性决策：parent_id=null（root level / 不挂在 Root Module 下）
  //   - 若挂在 Root Module 下 → breadcrumb 显示 "Root Module / Root File" → sidebar 也含 Root Module
  //     → batch 1-5 spec 中 `getByText("Root Module")` 命中 2 处 strict mode violation
  //   - 平级放置 → breadcrumb 只含 Root File / Root Module 仅在 sidebar 出现 1 次 / 向后兼容
  let file: { id: string; name: string } | null = null;
  if (withFileNode) {
    const fileRes = await api.post(`${API_BASE}/api/projects/${project.id}/nodes`, {
      headers: auth,
      data: {
        name: "Root File",
        type: "file",
        parent_id: null,
        description: "seed file node (P2-close fixture-fix / root-level)",
      },
    });
    if (!fileRes.ok()) {
      throw new Error(`file node create failed: ${fileRes.status()} ${await fileRes.text()}`);
    }
    const fileBody = await fileRes.json();
    file = { id: fileBody.id, name: fileBody.name };
  }

  const issueRes = await api.post(`${API_BASE}/api/projects/${project.id}/issues`, {
    headers: auth,
    data: {
      node_id: node.id,
      category: "bug",
      title: "Seed issue",
      description: "Auto-created by e2e seed fixture",
    },
  });
  if (!issueRes.ok()) {
    throw new Error(`issue create failed: ${issueRes.status()} ${await issueRes.text()}`);
  }
  const issue = await issueRes.json();

  return {
    accessToken,
    user: { id: user.id, email: user.email },
    project: { id: project.id, name: project.name },
    node: { id: node.id, name: node.name },
    file,
    issue: { id: issue.id, title: issue.title },
    dimensionTypeId,
  };
}
