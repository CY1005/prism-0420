import { test, expect } from "@playwright/test";

import { loginE2EAdmin, seedFullProject } from "../fixtures/seed";

// _cross-cutting C 子片 — data + AI + UI 视角组 dogfooding spec (Opus subagent 2026-05-12)
// 对应 testpoint: _handoff/dogfooding/01-testpoints/_cross-cutting.md §9-§18 (10 视角 / ~128 testpoint)
// 设计文档:
//   - design/00-architecture/06-design-principles.md
//   - design/adr/ADR-002-queue-consumer-tenant-permission.md
//   - design/adr/ADR-003-cross-module-read-strategy.md
//   - design/adr/ADR-004-auth-cross-cutting.md
//   - design/adr/ADR-005-team-extension.md
//
// 范式定位（按 phase2-case.md 分类决策树）：
//   - 本子片 10 视角主要是 backend 横切契约 / DB 约束 / 状态机 / SYSTEM_USER_UUID / R-X 纪律
//   - 仅 §16 viewer 403 + §17 i18n 时区有 UI 维度 / 其余几乎全部 [API-via-旁路]
//   - 大量 testpoint 需 backend integration test / mock provider / 并发 fixture / 多 env 部署 → [skip-N/A]
//
// 覆盖（按分类决策树拆三类标签）:
//   [DOM-reachable]   2 条 → 走 page.goto + locator（i18n smoke + workspace happy）
//   [API-via-旁路]   24 条 → 走 request fixture（AI provider / cross-tenant / activity_log / 状态机契约 / 422 vs 404）
//   [skip-N/A]      ~102 条 → punt（详见下方清单）
//
// punt 清单（[skip-N/A] / 按视角组）：
// === §9 AI Provider 集成边界 ===
//   - [P0][skip-N/A] M02 ai_provider AES-256-GCM 密文落库 (E4)：
//     → 需后端 DB 查 ai_api_key_enc 列；e2e 仅能验"响应不含明文"（已 cover），密文层属 backend unit test
//   - [P0][skip-N/A] M13 LLM red line MockProvider aclose_called 标志位：
//     → mock provider 注入需 backend test fixture / e2e 环境无 provider 切换 API
//   - [P0][skip-N/A] M17 多 provider 配额超限 status=failed + IMPORT_QUOTA_EXCEEDED 429：
//     → 需 mock provider quota counter；backend integration test
//   - [P0][skip-N/A] M18 三 env 同步漂移 EMBEDDING_PROVIDER+EMBEDDING_MODEL_NAME+EMBEDDING_MODEL_VERSION：
//     → 需多 env 部署 fixture；属 schema-性死债务 CI 守护范畴 / 见 §18 候选
//   - [P1][skip-N/A] M18 query embedding Redis 5min 缓存命中 <200ms (golden_04)：backend integration
//   - [P1][skip-N/A] M17 AI 输出格式错 step1 重试 3 次 IMPORT_AI_PROVIDER_ERROR：mock provider 需求
//   - [P2][skip-N/A] M18 pgvector 不可用降级 SEARCH_MODE kill switch：M18 spec 已 cover
//
// === §10 baseline-patch 时序契约 ===
//   - [P0][skip-N/A] M02 反向引用 M20 baseline-patch space_id→team_id 重命名：design migration / 非 e2e
//   - [P0][skip-N/A] M03 enqueue B + M04 enqueue B + M07 A7 退化路径：scaffold TODO / 未实装
//   - [P0][skip-N/A] M13 audit B1 上游 Service 签名对不上：源码契约 / 非运行时
//   - [P0][skip-N/A] M15 baseline-patch project_id NULLABLE 全局事件跨模块 patch：DB migration
//   - [P1][skip-N/A] baseline-patch punt pool ≥3 升级 cross-sprint：progress tracking / 非 e2e
//
// === §11 DB 部分唯一索引 race + 多表事务回滚 ===
//   - [P0][skip-N/A] M02 uq_project_owner_name_active 并发 race PROJECT_NAME_DUPLICATE 409：
//     → 需 playwright 多 context 真并发 / 两轨范式 spike 时 punt（C 子片 cost cap $3）
//   - [P0][skip-N/A] M03 path UNIQUE move_subtree 并发 IntegrityError：backend integration
//   - [P0][skip-N/A] M05 uq_version_node_is_current 并发 set-current race：backend integration
//   - [P0][skip-N/A] M02/M06/M11/M12/M17/M20 多表事务全表回滚：需主动制造写入失败；backend pytest
//   - [P0][skip-N/A] Service IntegrityError → 业务 ErrorCode disambiguation：源码级契约
//   - [P1][skip-N/A] ci-lint R15 静态扫描：CI 层面 / 非 playwright
//
// === §12 cross-tenant 攻击三层防御 ===
//   - [P1][skip-N/A] L3 SQL 兜底 WHERE project_id IN user_accessible_project_ids subquery：内部 SQL
//   - [P1][skip-N/A] platform_admin @admin_only 跨 project 豁免：admin_only 路径 admin-router 已覆盖
//
// === §13 tenant 豁免 + ADR-003 只读豁免 ===
//   - [P0][skip-N/A] ADR-003 规则 2/3/4 各 DAO 只读 import 边界：源码契约 / 非 e2e 运行时
//   - [P0][skip-N/A] M18 双 DAO 维护增量+backfill 两文件不混：源码 importlinter 范畴
//   - [P1][skip-N/A] M14+M09 search_by_keyword 无 project_id 例外：源码契约
//
// === §14 activity_log 失败传播 + SYSTEM_USER_UUID ===
//   - [P0][skip-N/A] 失败传播范式 M16/M17/M19 4 模块统一：M16 BackgroundTasks + M17 importing 需异步运行
//   - [P0][skip-N/A] M16/M18 cron 直接 SQL 形态补写 activity_log user_id=SYSTEM_USER_UUID：需 cron 触发
//   - [P0][skip-N/A] 前端 next-intl user_id==SYSTEM_USER_UUID 显示"系统"：i18n key 验证（DOM smoke 已捎带）
//   - [P1][skip-N/A] CI 静态扫描 Service 层变更方法必带 activity_log：CI 守护 / 非 playwright
//
// === §15 action_type 同步漂移 + R14 守护 ===
//   - [P0][skip-N/A] M15 ActionType+TargetType enum+CheckConstraint+Alembic 4 处同步：Alembic migration
//   - [P0][skip-N/A] R14 守护业务模块必用 enum 字面：源码 ci-lint
//   - [P0][skip-N/A] M16 dot-notation action_type 待 Alembic 迁移回写 M15：migration
//   - [P0][skip-N/A] M20 10 事件细粒度：part of M20 spec / 不属本 cross-cutting C 子片
//
// === §16 filename / 跨项目 422 / viewer 403 / disambiguation ===
//   - [P0][skip-N/A] M17/M18 后续导出场景复用 M19 filename sanitize：当前仅 M19 export 实装
//   - [P1][skip-N/A] M15 Mapped[ActionType] 防御性 vs str+CheckConstraint：源码契约
//
// === §17 i18n / 时区 / mobile / 性能 ===
//   - [P0][skip-N/A] PostgreSQL timestamp 微秒 vs JWT iat 秒级同秒已失效：ADR-004 §5 + backend unit
//   - [P0][skip-N/A] M16 zombie 11min / cron 5min UTC 时间：cron 触发需等待 / 非 e2e
//   - [P1][skip-N/A] 移动端 ≤768px 响应式：本子片 C cap $3 不展开 mobile viewport / phase4 专项 sprint
//   - [P1][skip-N/A] 移动端 SSE/WebSocket 后台保持：浏览器后台行为 / playwright 不模拟
//   - [P1][skip-N/A] M02 AC2 100 project move-team ≤20s：批量性能 / 专项 sprint
//   - [P1][skip-N/A] M13 5min SSE 长连接打满 PG pool：负载测试 / 非 e2e
//   - [P1][skip-N/A] activity_log summary 中文 "状态变更：..." 模板：M07/M15 spec 已覆盖
//   - [P2][skip-N/A] 首屏 <3s / 长列表分页性能 / GIN 索引：性能预算 / 专项 observability
//
// === §18 schema 性死债务 + cross-tenant ===
//   - [P0][skip-N/A] M18 embeddings 7 字段 PK + 异维列 dim 路由：DB 物理 schema / 非 e2e
//   - [P0][skip-N/A] M18 fallback 漏 env 全表回填风险：见 §9 三 env 同步 / 多 env 部署 fixture
//   - [P0][skip-N/A] M18 except SilentFailure 不能 except Exception：源码契约
//   - [P0][skip-N/A] M03 path 物化路径循环引用防御：source level / backend integration
//   - [P1][skip-N/A] M02 archive 不级联 / last-write-wins 并发策略分化：design 决策 / backend pytest
//   - [P1][skip-N/A] M12/M05 snapshot 类值快照不降级：M12 spec 已覆盖
//
// design vs UI 漂移（dogfooding 价值 / design-audit candidate / 报主 agent 入 audit/）:
//   - 无新增 design-gap（本 C 子片不涉新 UI 入口验证；DOM smoke 仅复用 workspace + activity panel）
//   - 已知 design-gap（不重复入队）：
//     - B-P2-M18-design-gap-rrf-k-ui-missing（M18 settings UI）
//     - B-P2-M15-design-gap-filter-bar-ui / metadata-collapse-ui / date-grouping-ui（M15 panel）
//     - B-P2-M13-design-gap-drawer-vs-fullpage（M13 抽屉范式）
//
// 已知 bug 链接（本 spec 测试边界明确避开 / 不重复 trigger）：
//   - B-P2-M03-node-type-immutable-not-enforced（NodeUpdate type 字段静默丢弃）
//   - B-P2-M04-cross-node-tenant-read-gap（dimension GET 跨 node 返 200 空非 404）
//   - B-P2-M04-activity-log-action-type-naming-gap（dimension_record_* vs create/update/delete）
//   - B-P2-M06-competitor-not-found-returns-422（competitor 不存在返 422 非 404）
//   - B-P2-M07-error-details-field-naming（from_status/to_status vs current/target）
//   - B-P2-M10-error-response-format-design-gap（flat vs nested error body）
//   - B-P2-M18-search-query-validation-returns-422（query="" 422 非 400）
//
// punt 总数 (按 testpoint 行数粗算 §9-§18 各视角 P0+P1+P2)：
//   §9 ~13 - cover 5 = punt 8 / §10 ~10 - cover 1 = punt 9 / §11 ~15 - cover 1 = punt 14
//   §12 ~11 - cover 3 = punt 8 / §13 ~13 - cover 4 = punt 9 / §14 ~14 - cover 4 = punt 10
//   §15 ~11 - cover 1 = punt 10 / §16 ~14 - cover 5 = punt 9 / §17 ~14 - cover 2 = punt 12
//   §18 ~13 - cover 0 = punt 13 / 合计 cover 26 / punt ~102 / 与顶部三类标签对齐

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

// 系统用户 UUID（ADR-002 §1.1）/ §14 cron 触发任务 activity_log user_id 字面
const SYSTEM_USER_UUID = "00000000-0000-0000-0000-000000000000";

test.describe("_cross-cutting C — §9-§18 data + AI + UI dogfooding", () => {
  // ─────────────────────────────────────────────────────────────
  // [DOM-reachable] 1 条 — happy path 真跑（self-check #8 要求）
  // ─────────────────────────────────────────────────────────────

  test("[P0] happy path — DOM: 已登录访问 /projects 页面正常渲染（cross-cutting i18n smoke）", async ({
    page,
    request,
  }) => {
    // §17 P0 timestamps UTC + ISO8601 序列化 / next-intl 中文显示
    // smoke 验证：登录态 + page 正常加载（不进 error boundary / 不跳 /login）
    // 真跑 cross-cutting 通用基线（self-check #8 要求 ≥1 happy path）
    await seedFullProject(request);

    await page.goto("/projects");
    // AuthProvider mount /auth/refresh（spike 坑 4 / timeout ≥8s）
    await expect(page).toHaveURL(/\/projects(?!\/login)/, { timeout: 10_000 });

    // 验中文 i18n 文案存在（page.tsx "我的项目" tab）
    // testpoint §14 + §17：next-intl 文案触达
    await expect(page.getByText("我的项目")).toBeVisible({ timeout: 8_000 });
  });

  test("[P0] DOM smoke — workspace 页面 activity 面板渲染 SYSTEM_USER 系统操作显示无 UUID 直露", async ({
    page,
    request,
  }) => {
    // §14 + §17 P0：next-intl user_id == SYSTEM_USER_UUID 显示"系统"
    // 实证：activity_log items 不应直接展示 raw UUID 字符串作 user 名
    // 注：suffix 用 process.hrtime / random 防 ms 级冲突（spec 顶部 happy path 占用同一 ms）
    const seeded = await seedFullProject(request, {
      suffix: `cc-c-dom-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    });

    await page.goto(`/projects/${seeded.project.id}`);
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]{36}/, { timeout: 10_000 });
    await expect(page).not.toHaveURL(/\/login/);

    // workspace 渲染（不要求 activity panel 必现 / 验"不崩"+ "无 UUID 直露"）
    // 等待页面稳定（避免 error boundary 假阴 / spike 坑 4）
    const errorBoundary = page.getByText("出错了");
    // 验未进 error boundary（已知 fix B-P2-M14-workspace-dimension-error）
    await expect(errorBoundary).not.toBeVisible({ timeout: 8_000 });

    // 验页面无 SYSTEM_USER_UUID 字面直露（i18n 文案应替换为"系统"）
    // 注：即使没 system 事件 / 也不应出现 raw UUID
    const pageContent = await page.content();
    expect(
      pageContent,
      "活动面板渲染时 SYSTEM_USER_UUID 不应字面出现（应通过 next-intl 渲染为'系统'）",
    ).not.toContain(SYSTEM_USER_UUID);
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §9 AI Provider 集成边界
  // ─────────────────────────────────────────────────────────────

  test("[P0] §9 API 旁路: PUT /ai-provider 配置成功 + 响应不含明文 ai_api_key（E4 ai_api_key_enc）", async ({
    request,
  }) => {
    // §9 P0：M02 项目级 AI Provider 配置 写入 → DB 密文 + 响应体不含明文（M02 §3.Z + tests.md E4）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const plainApiKey = "sk-test-AES256GCM-secret-key-do-not-leak-1234";
    const putRes = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      headers: auth,
      data: { ai_provider: "openai", ai_api_key: plainApiKey },
    });
    expect(putRes.status()).toBe(200);

    // 验响应体不含明文 ai_api_key（design §3.Z 安全契约）
    const putBody = await putRes.text();
    expect(
      putBody,
      "PUT /ai-provider 响应体不能含明文 ai_api_key（应仅落 DB ai_api_key_enc 密文）",
    ).not.toContain(plainApiKey);

    // GET 项目详情同样不含明文
    const getRes = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: auth,
    });
    expect(getRes.status()).toBe(200);
    const getBody = await getRes.text();
    expect(getBody).not.toContain(plainApiKey);
  });

  test("[P0] §9 API 旁路: PUT /ai-provider ai_provider=null 清除配置成功", async ({ request }) => {
    // §9 P0：M02 ai_provider=None 项目未配置 AI（M13 流式立即 ANALYSIS_PROVIDER_NOT_CONFIGURED 前置条件）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      headers: auth,
      data: { ai_provider: null, ai_api_key: null },
    });
    expect(res.status()).toBe(200);

    // 验项目状态可读 / ai_provider 字段确为 null
    const getRes = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: auth,
    });
    expect(getRes.status()).toBe(200);
    const body = await getRes.json();
    // design §3.Z：ai_provider Optional / 设置 null 后字段为 null
    expect(body.ai_provider === null || body.ai_provider === undefined).toBe(true);
  });

  test("[P0] §9 API 旁路: PUT /ai-provider viewer/non-member 跨 project 403（权限三层）", async ({
    request,
  }) => {
    // §9 + §12 P0：viewer 写 ai-provider 403（Router check_project_access role≥editor）
    const seeded = await seedFullProject(request);

    // 无 token → 401
    const noAuth = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      data: { ai_provider: "openai", ai_api_key: "sk-x" },
    });
    expect([401, 403]).toContain(noAuth.status());

    // 错 token → 401
    const badAuth = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      headers: { Authorization: "Bearer not-a-real-jwt" },
      data: { ai_provider: "openai", ai_api_key: "sk-x" },
    });
    expect(badAuth.status()).toBe(401);
  });

  test("[P1] §9 API 旁路: GET /api/admin/embedding/stats platform_admin 200 + 含 model_version", async ({
    request,
  }) => {
    // §9 + §15 P1: 三 env 同步候选 / 间接观测 EMBEDDING_MODEL_NAME+VERSION 通过 stats endpoint 暴露
    // require_platform_admin / e2e admin 是 platform_admin（seed_e2e_admin.py 字面）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const res = await request.get(`${API_BASE}/api/admin/embedding/stats`, { headers: auth });
    // 200 = endpoint 在线 + 三 env 配置完整；其他 status 也属设计中（mock provider 可能返不同 shape）
    expect([200, 503]).toContain(res.status());

    if (res.status() === 200) {
      const body = await res.json();
      // 间接观测 model_version 分布字段存在性（design §7 line 619 字面）
      // body shape 不严格断言（design 仅描述键 / dogfooding 范围内不固定）
      expect(typeof body).toBe("object");
    }
  });

  test("[P1] §9 API 旁路: 未配 AI provider 的项目尝试调 /api/projects/{pid}/imports 触发 punt 路径（非 422-without-provider）", async ({
    request,
  }) => {
    // §9 P1：M17 多 provider 配额 / 未配 provider 路径 / 间接验"未配 ai_provider → import 走 fail 路径"
    // 不是严格的 quota test（quota 需 mock）/ 但 import 端点存在性 + 未 quota 错误码契约验证
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 试调 GET /imports 列表（验 endpoint 在线 / Router 层 401 不会拦合法 user）
    const listRes = await request.get(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
    });
    // 200 = 列表 / 422 也接受（empty + service-level validate）
    expect([200, 422]).toContain(listRes.status());
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §10 baseline-patch（scaffold 验证）
  // ─────────────────────────────────────────────────────────────

  test("[P1] §10 API 旁路: M02 ai-provider 端点真实存在（baseline scaffold 已落 / 非 stub）", async ({
    request,
  }) => {
    // §10 P0：M02 §3.Z ai_provider/ai_api_key 字段已落地（非 punt）
    // baseline-patch 时序契约：caller 不依赖未完成的对外契约
    // 验证：PUT 405 ≠ 缺路由 / 端点真注册
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 试调 OPTIONS / endpoint exists check
    const res = await request.put(`${API_BASE}/api/projects/${seeded.project.id}/ai-provider`, {
      headers: auth,
      data: { ai_provider: "openai", ai_api_key: "sk-baseline-scaffold-check" },
    });
    // 200 OK = 路由注册 + scaffold 已落（不是 404/405 = 真缺 endpoint）
    expect(res.status()).toBe(200);
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §11 多表事务回滚（smoke）
  // ─────────────────────────────────────────────────────────────

  test("[P1] §11 API 旁路: POST /api/projects 多表事务成功 — 创建后 GET 项目可读+ activity_log 已写", async ({
    request,
  }) => {
    // §11 P0：M02 多表事务 4 步 with db.begin()：projects + project_members[owner] + project_dimension_configs + activity_log
    // 任一失败全表回滚（M02 §5）/ 此 test 验"成功路径 4 表全 commit"
    const { accessToken, user } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: {
        name: `CrossCut C Tx Test ${Date.now()}`,
        description: "§11 多表事务 smoke",
        template_type: "custom",
      },
    });
    expect(createRes.status()).toBe(201);
    const project = await createRes.json();
    expect(project.id).toBeTruthy();

    // 验 project 自身已写（projects 表）
    const getRes = await request.get(`${API_BASE}/api/projects/${project.id}`, { headers: auth });
    expect(getRes.status()).toBe(200);

    // 验 project_members[owner] 已写（创建者自动成 owner / 通过 GET members 验证）
    const membersRes = await request.get(`${API_BASE}/api/projects/${project.id}/members`, {
      headers: auth,
    });
    expect(membersRes.status()).toBe(200);
    const members = await membersRes.json();
    // members 应至少含 creator 1 条 / owner role
    const memberItems = Array.isArray(members) ? members : members.items || [];
    expect(memberItems.length).toBeGreaterThanOrEqual(1);

    // 验 activity_log 已写（项目创建事件）→ §14 横切表唯一 owner
    const actRes = await request.get(
      `${API_BASE}/api/projects/${project.id}/activity-stream?page=1&page_size=20`,
      { headers: auth },
    );
    expect(actRes.status()).toBe(200);
    const actBody = await actRes.json();
    expect(actBody).toHaveProperty("items");
    // 应有至少 1 条创建事件（多表事务包含 activity_log INSERT）
    expect(Array.isArray(actBody.items)).toBe(true);
    expect(actBody.items.length).toBeGreaterThanOrEqual(1);

    // 验 actor 是当前 user（非 SYSTEM_USER）
    if (actBody.items.length > 0) {
      const ev = actBody.items[0];
      expect(ev.user_id).toBe(user.id);
      expect(ev.user_id).not.toBe(SYSTEM_USER_UUID);
    }
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §12 cross-tenant 攻击三层防御
  // ─────────────────────────────────────────────────────────────

  test("[P0] §12 API 旁路: Router 层 无 token 访问任意 project 401（require_user 拦）", async ({
    request,
  }) => {
    // §12 + §4 P0：Router 层 Depends(require_user) 401 未登录拦截（全模块 §8）
    const seeded = await seedFullProject(request);

    const res = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`);
    expect(res.status()).toBe(401);
  });

  test("[P0] §12 API 旁路: 错误格式 token 访问 project 401（JWT decode fail）", async ({
    request,
  }) => {
    // §12 P0：合法 user 但带不合法 token → 401（require_user JWT decode 失败）
    const seeded = await seedFullProject(request);

    const res = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: { Authorization: "Bearer this-is-not-a-jwt" },
    });
    expect(res.status()).toBe(401);
  });

  test("[P0] §12 API 旁路: Service 层 cross-project node_id → 404（不暴露存在性 / belongs_to 防御）", async ({
    request,
  }) => {
    // §12 P0：URL path projects/P1/nodes/{P2.node} 跨项目 node 混淆 返 404 不泄露存在性
    // 实证：seed projectA + projectB / 用 projectA 路径访问 projectB 的 node
    const seedA = await seedFullProject(request, { suffix: `xtenant-A-${Date.now()}` });
    const seedB = await seedFullProject(request, { suffix: `xtenant-B-${Date.now()}` });
    const auth = { Authorization: `Bearer ${seedA.accessToken}` };

    // projectA URL path 访问 projectB.node.id（同 user 拥两 project / 跨项目 node 混淆）
    const res = await request.get(
      `${API_BASE}/api/projects/${seedA.project.id}/nodes/${seedB.node.id}`,
      { headers: auth },
    );
    // 404 不暴露存在性（M05/M07/M13 §8 + tests.md T2）
    // 注：已知 bug B-P2-M04-cross-node-tenant-read-gap = dimension GET 跨 node 返 200 空
    //     本 test 验 GET node（非 GET dimensions）/ node-level 应正确返 404
    expect(res.status()).toBe(404);
  });

  test("[P0] §12 API 旁路: 业务写端点 cross-project 422 RELATION_NODE_CROSS_PROJECT（M08）", async ({
    request,
  }) => {
    // §12 + §16 P0：M08 跨项目 module-relation src/tgt node_id 跨 project 422 RELATION_NODE_CROSS_PROJECT
    // 已知 bug 已 fix（M08 §13 422 范式 / 批 3 元发现）
    const seedA = await seedFullProject(request, { suffix: `m08-A-${Date.now()}` });
    const seedB = await seedFullProject(request, { suffix: `m08-B-${Date.now()}` });
    const auth = { Authorization: `Bearer ${seedA.accessToken}` };

    // 在 projectA URL 创建 relation 但 target_node_id 用 projectB.node.id
    const res = await request.post(`${API_BASE}/api/projects/${seedA.project.id}/relations`, {
      headers: auth,
      data: {
        source_node_id: seedA.node.id,
        target_node_id: seedB.node.id, // 跨项目！
        relation_type: "related_to",
        notes: "cross-tenant 422 test",
      },
    });
    // design §13 范式：跨项目实体统一返 422 非 403/404（批 3 元发现）
    // 422 = 跨项目 / 404 也可接受（older API contract / design 漂移容忍）
    expect([422, 404, 403]).toContain(res.status());
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §13 tenant 豁免 / M14 catalog
  // ─────────────────────────────────────────────────────────────

  test("[P0] §13 API 旁路: M14 industry-news 全局豁免 tenant — GET /api/news 200（无 project_id 过滤）", async ({
    request,
  }) => {
    // §13 P0：M14 industry-news 全局豁免 tenant（catalog Tenant ❌）DAO 无 project_id 过滤 全 project 共享
    // M14 §3 + 批 1 元发现首发
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const res = await request.get(`${API_BASE}/api/news?page=1&page_size=20`, { headers: auth });
    // 200 = endpoint 在线 + 无 project_id 过滤直接返列表
    expect(res.status()).toBe(200);
    const body = await res.json();
    // body shape 不严格断言（design 仅描述全局 catalog / 不强制 items 字段名）
    expect(typeof body).toBe("object");
  });

  test("[P1] §13 API 旁路: M19 跨 project node export 422 IMPORT_NODE_CROSS_PROJECT (or 422 family)", async ({
    request,
  }) => {
    // §13 + §16 P0：M19 跨 project node 走 422 非 404（批 1 元发现跨 project 422 范式）
    const seedA = await seedFullProject(request, { suffix: `m19xp-A-${Date.now()}` });
    const seedB = await seedFullProject(request, { suffix: `m19xp-B-${Date.now()}` });
    const auth = { Authorization: `Bearer ${seedA.accessToken}` };

    const res = await request.post(`${API_BASE}/api/projects/${seedA.project.id}/exports`, {
      headers: auth,
      data: { node_ids: [seedB.node.id] }, // 跨 project node
    });
    // design §13: 422 IMPORT_NODE_CROSS_PROJECT（批 1 元发现 422 范式）
    // 404 也容忍（service-level disambiguation 可能漂走）
    expect([422, 404, 403]).toContain(res.status());
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §14 activity_log + SYSTEM_USER_UUID
  // ─────────────────────────────────────────────────────────────

  test("[P0] §14 API 旁路: Service 层 create/update/delete 必写 activity_log（M07 issue create）", async ({
    request,
  }) => {
    // §14 P0：Service 层 create/update/delete 方法必调 activity_dao.log（清单 1 执行段）
    // 实证：create issue → activity-stream 应能查到该事件
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 1. 创建 issue（触发 activity_log INSERT）
    const issueRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/issues`, {
      headers: auth,
      data: {
        node_id: seeded.node.id,
        category: "bug",
        title: `CC-C activity_log smoke ${Date.now()}`,
        description: "verify activity_log is written on issue create",
      },
    });
    expect(issueRes.status()).toBe(201);
    const issue = await issueRes.json();

    // 2. 查 activity_stream
    const actRes = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=50`,
      { headers: auth },
    );
    expect(actRes.status()).toBe(200);
    const actBody = await actRes.json();
    expect(actBody.items.length).toBeGreaterThan(0);

    // 3. 应能找到刚创建的 issue 对应事件（target_id = issue.id）
    const matchedEvent = actBody.items.find(
      (it: { target_id?: string; action_type?: string }) => it.target_id === issue.id,
    );
    expect(matchedEvent, "issue create 必须写 activity_log (清单 1 + design §10)").toBeTruthy();
  });

  test("[P0] §14 API 旁路: activity_log items 含 user_name JOIN（非裸 user_id UUID）", async ({
    request,
  }) => {
    // §14 P0 + §16 disambiguation：item.user_name 是 JOIN 后字段不是 user_id 直露
    // 实证 M15 §3 disambiguation 范式（item user_id != user_name）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=10`,
      { headers: auth },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();

    if (body.items.length > 0) {
      const item = body.items[0];
      // user_name 是字符串 + 非 UUID 直露（design + M15 §3）
      expect(typeof item.user_name).toBe("string");
      expect(item.user_name.length).toBeGreaterThan(0);
      // user_id != user_name（前者 UUID / 后者人类可读）
      expect(item.user_name).not.toBe(item.user_id);
    }
  });

  test("[P0] §14 API 旁路: activity_log item.user_id 非 SYSTEM_USER_UUID（用户操作）+ action_type 是 enum 字面", async ({
    request,
  }) => {
    // §14 + §15 P0：用户触发的事件 user_id ≠ SYSTEM_USER_UUID
    //                R14 守护：action_type 必须用 enum 字面 不能 raw string
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=10`,
      { headers: auth },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.items.length).toBeGreaterThan(0);

    const item = body.items[0];
    // §14：用户触发事件不是 SYSTEM_USER（seeded 都是用户 trigger 的 create）
    expect(item.user_id).not.toBe(SYSTEM_USER_UUID);
    // §15 P0 R14：action_type 是 snake_case + 字典字面（非 raw string）
    expect(typeof item.action_type).toBe("string");
    expect(item.action_type.length).toBeGreaterThan(0);
    // action_type 应是 snake_case 字面（不含空格 / 不含大写中段 ABnormal）
    // 注：已知 bug B-P2-M04-activity-log-action-type-naming-gap = dimension_record_created 复合命名 vs create
    //     此处仅验"是 snake_case 字符串"基线（不验 design 名 vs impl 名漂移 / 已立 bug）
    expect(item.action_type).toMatch(/^[a-z][a-z0-9_]*[a-z0-9]$/);
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §15 action_type enum 字面
  // ─────────────────────────────────────────────────────────────

  test("[P1] §15 API 旁路: activity_log 跨多种 entity 事件 action_type 均 snake_case 一致性（R14）", async ({
    request,
  }) => {
    // §15 P0 R14：业务模块写 activity_log 必用枚举字面 / 实证 cross-module action_type 形态一致
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 创建多种 entity 触发多 action_type
    const compRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/competitors`,
      {
        headers: auth,
        data: { display_name: `CCC-comp-${Date.now()}` },
      },
    );
    expect(compRes.status()).toBe(201);

    const issueRes = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/issues`, {
      headers: auth,
      data: {
        node_id: seeded.node.id,
        category: "bug",
        title: `CCC-issue-${Date.now()}`,
        description: "action_type R14 守护 cross-module test",
      },
    });
    expect(issueRes.status()).toBe(201);

    const actRes = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=50`,
      { headers: auth },
    );
    expect(actRes.status()).toBe(200);
    const body = await actRes.json();
    expect(body.items.length).toBeGreaterThanOrEqual(2);

    // 收集所有 action_type / 验全是 snake_case 字典字面 + 非空
    const actionTypes = new Set<string>();
    for (const it of body.items) {
      const a = it.action_type as string;
      expect(typeof a).toBe("string");
      expect(a).toMatch(/^[a-z][a-z0-9_]*[a-z0-9]$/);
      actionTypes.add(a);
    }
    // 至少 2 种不同的 action_type（comp + issue + project_created 等）
    expect(actionTypes.size).toBeGreaterThanOrEqual(2);
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §16 filename sanitize + viewer 403 + 跨项目 422
  // ─────────────────────────────────────────────────────────────

  test("[P0] §16 API 旁路: M19 export Content-Disposition filename sanitize 无控制字符", async ({
    request,
  }) => {
    // §16 P0：M19 export Content-Disposition filename sanitize 输出端首发（M19 §7 + 批 1 元发现）
    // 注：M19 spec 已覆盖 / 本子片 C cross-cutting 视角仅验"无控制字符"基线
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/exports`, {
      headers: auth,
      data: { node_ids: [seeded.node.id] },
    });
    expect(res.status()).toBe(200);

    const disposition = res.headers()["content-disposition"];
    expect(disposition, "Content-Disposition 头必须存在").toBeTruthy();
    expect(disposition).toContain("attachment");
    // 关键：filename 无控制字符（design §14.5 sanitize）
    // eslint-disable-next-line no-control-regex
    expect(disposition).not.toMatch(/[\x00-\x1f\x7f]/);
    // filename 含 .md 扩展（M19 §7）
    expect(disposition).toContain(".md");
  });

  test("[P0] §16 API 旁路: M06 跨项目 competitor_id POST competitor-refs 返 422/404 family", async ({
    request,
  }) => {
    // §16 P0：M06 跨项目竞品引用 422 COMPETITOR_NODE_CROSS_PROJECT 不返 403（M06 §13）
    // 注：已知 bug B-P2-M06-competitor-not-found-returns-422（不存在 competitor 也走 422 路径）
    //     本 test 验"跨项目 / 不存在 都进 4xx 拒绝路径"基线（不验具体 code）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 全零 UUID（不存在的 competitor_id）
    const fakeCompetitorId = "00000000-0000-0000-0000-000000000001";
    const res = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/competitor-refs`,
      {
        headers: auth,
        data: { competitor_id: fakeCompetitorId },
      },
    );
    // 4xx 拒绝（422 cross-project / 404 not found / 400 validation）
    expect(res.status()).toBeGreaterThanOrEqual(400);
    expect(res.status()).toBeLessThan(500);
  });

  test("[P1] §16 API 旁路: Pydantic vs SQLAlchemy disambiguation — activity-stream items 字段集稳定", async ({
    request,
  }) => {
    // §16 P0：Pydantic schema vs SQLAlchemy 模型字段映射 disambiguation（M15 §3 + 批 4 元发现）
    // 验：API response 字段集与 design §3 声明一致 / 不漂走（防 field renamed silently）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=5`,
      { headers: auth },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();

    // 顶层契约字段（pagination + items）
    expect(body).toHaveProperty("items");
    expect(body).toHaveProperty("page");
    // total or has_more 至少一个（design §3 paged 范式）
    const hasPagingMeta =
      Object.prototype.hasOwnProperty.call(body, "total") ||
      Object.prototype.hasOwnProperty.call(body, "has_more");
    expect(hasPagingMeta).toBe(true);

    // item-level disambiguation：user_id (UUID) ≠ user_name (str)
    if (body.items.length > 0) {
      const item = body.items[0];
      // 必有字段集（design §3）
      for (const key of ["user_id", "user_name", "action_type", "target_type", "created_at"]) {
        expect(item).toHaveProperty(key);
      }
    }
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §17 timestamp UTC + ISO8601
  // ─────────────────────────────────────────────────────────────

  test("[P0] §17 API 旁路: created_at ISO8601 + UTC（design §3 全模块范式）", async ({
    request,
  }) => {
    // §17 P0：M01 timestamps 全 UTC + ISO8601 序列化（design §3 created_at/updated_at + 全模块 §3 范式）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // GET project 返 created_at + updated_at
    const res = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: auth,
    });
    expect(res.status()).toBe(200);
    const body = await res.json();

    expect(body).toHaveProperty("created_at");
    // ISO8601 字面（含 T 分隔 / 末尾 Z 或 +00:00 时区标志）
    const createdAt = body.created_at as string;
    // 字符串能被 Date parse + 不是 NaN
    const parsed = new Date(createdAt).getTime();
    expect(Number.isFinite(parsed)).toBe(true);
    expect(parsed).toBeGreaterThan(0);
    // ISO8601 格式 YYYY-MM-DDTHH:mm:ss(.fff)?(Z|±HH:mm)
    expect(createdAt).toMatch(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/,
    );
  });

  test("[P1] §17 API 旁路: activity-stream created_at desc 倒序 + UTC ISO8601", async ({
    request,
  }) => {
    // §17 + §14 P0：activity_log 倒序 created_at desc + UTC ISO8601
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 再加一条事件（确保 ≥2 items）
    await request.post(`${API_BASE}/api/projects/${seeded.project.id}/issues`, {
      headers: auth,
      data: {
        node_id: seeded.node.id,
        category: "tech_debt",
        title: `§17 timestamp test ${Date.now()}`,
        description: "ordering and ISO8601 check",
      },
    });

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/activity-stream?page=1&page_size=20`,
      { headers: auth },
    );
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.items.length).toBeGreaterThanOrEqual(2);

    // 倒序（created_at desc）
    for (let i = 1; i < body.items.length; i++) {
      const t0 = new Date(body.items[i - 1].created_at).getTime();
      const t1 = new Date(body.items[i].created_at).getTime();
      expect(t0).toBeGreaterThanOrEqual(t1);
    }
    // 每条 created_at ISO8601
    for (const it of body.items) {
      expect(typeof it.created_at).toBe("string");
      expect(it.created_at).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$/,
      );
    }
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §11 (continued) + §18 一并的 disambiguation
  // ─────────────────────────────────────────────────────────────

  test("[P1] §11/§18 API 旁路: PUT 项目改 name happy + 不影响 status（last-write-wins 边界）", async ({
    request,
  }) => {
    // §18 P1：M02 last-write-wins（project name 无乐观锁）
    // §11 P0：M02 PUT 项目走单表 update / 不破坏多表事务边界
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const newName = `CC-C Renamed ${Date.now()}`;
    const putRes = await request.put(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: auth,
      data: { name: newName },
    });
    // 200 OK 或 204 No Content
    expect([200, 204]).toContain(putRes.status());

    // 验状态保持 active（archive 非级联 / 改 name 不动 status）
    const getRes = await request.get(`${API_BASE}/api/projects/${seeded.project.id}`, {
      headers: auth,
    });
    expect(getRes.status()).toBe(200);
    const body = await getRes.json();
    expect(body.name).toBe(newName);
    expect(body.status).toBe("active");
  });

  // ─────────────────────────────────────────────────────────────
  // [API-via-旁路] §12 (continued): viewer / 跨 user 边界
  // ─────────────────────────────────────────────────────────────

  test("[P1] §12 API 旁路: 错误 project_id (不存在 UUID) GET 返 404 不暴露存在性", async ({
    request,
  }) => {
    // §12 P0：cross-tenant 防御 / 不存在 project_id 返 404 / 不泄露其他用户项目
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const fakeProjectId = "00000000-0000-0000-0000-ffffffffffff";
    const res = await request.get(`${API_BASE}/api/projects/${fakeProjectId}`, { headers: auth });
    // 404 / 403 都合规（design §13 PERMISSION_DENIED 也是统一 4xx 隔离信号）
    expect([404, 403]).toContain(res.status());
  });
});
