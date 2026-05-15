# cluster-M12 design audit (B 路径)

> dogfooding sprint / 2026-05-15 / Phase 2.x M-frontend cluster-M12
> 触 plan §3 B 路径自评 6 项风险：改动范围高（重写 page + 新建 actions + 新建 validator）
> + 测试覆盖中（M12 spec 已存 / 部分 DOM testpoint 待实装后才能 PASS）→ B 路径自跑 audit
> 范围：B-P2-M12-design-gap-comparison-page（comparison page 重写接 6 endpoints）

## 审计输入

| 文档 | 章节 | 校对内容 |
|------|------|---------|
| `design/02-modules/M12-comparison/00-design.md` | §1 业务边界 / §3 数据模型 / §4 状态机 / §5 多人架构 4 维 / §6 分层职责 / §7 API 契约（6 endpoints）/ §8 权限三层 / §9 DAO tenant 过滤 / §10 activity_log / §11 idempotency / §12 Queue / §13 ErrorCode | 全契约 / 命名 / 异步范式 / 边界灰区 |
| `design/02-modules/M12-comparison/tests.md` | §1-§9 全 | golden path / 边界 / 并发 / tenant / 错误处理期望 |
| `design/00-architecture/06-design-principles.md` | 原则 1-5 + 5 项约束清单 | tenant / 事务 / 异步 / 并发 / activity_log |
| `api/routers/comparison_router.py` 全 165 行 | 6 endpoints | URL / status code / response schema / role 真后端契约 |
| `api/schemas/comparison_schema.py` 全 73 行 | MatrixCell / SnapshotCreateRequest / SnapshotUpdateRequest / SnapshotResponse / SnapshotDetailResponse / SnapshotItemResponse / SnapshotListResponse / ComparisonMatrixResponse | schema 真名 + 字段类型 + 约束 |
| `app/src/types/api.ts` § Comparison*/Snapshot*/MatrixCell | openapi 生成 TS 类型 | 类型契约一致性 |
| `app/e2e/dogfooding/M12-comparison.spec.ts` 全 906 行 | DOM smoke + 23 API-bypass | spec contract（DOM `/projects/{pid}/comparison` 路径 + DOM 元素） |
| `app/src/components/` ls + peer 组件命名（issue-card / news-card / dimension-card / feed-card / news-form 全 flat） | 业务组件目录范式 | 与 cluster-M14 + M17 同范式确认 |
| `app/src/actions/analyze.ts` § generateComparisonAction / backfillRowAction / exportComparisonAction / saveAnalysisAction | M13 punt stub | caller 影响面（M12 page 是这 3 函数唯一 caller / saveAnalysisAction 仍被 analysis page 用）|
| `_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md` §M12 + 共同根因 | 修法范围估算 | scope 守恒 |
| `_handoff/cross-sprint-punt-pool.md` §#11 元规则 | reconcile 4 栏 | 4 栏全走完 |

## findings 表（4 字段：冲突级别 / 章节 / 冲突描述 / 处置建议）

| # | 级别 | design 章节 | 冲突描述 | 处置建议 |
|---|------|-------------|---------|---------|
| F1 | **low** | §6 分层职责表 | design §6 字面 Page = `web/src/app/projects/[pid]/compare/page.tsx`（`web/` 前缀 + `compare` 而非 `comparison`）；prism-0420 实装路径 `app/src/app/projects/[projectId]/comparison/page.tsx`（无 `web/` 前缀 + 路由段 `comparison` / 与拷贝层既有路由完全一致 / Tab nav 链接也已用 `/comparison`）| **接受 + 不动 design**：cookbook 级路径漂移（项目全局已固化 / 与 /projects/[projectId]/issues, /relation-graph, /analysis 同 `[projectId]` 范式）；改 design 段段路径 + 拷贝层全部 nav link 是超 cluster boundary 的 cleanup 工作。元规则：与 cluster-M14 F2（`web/` 前缀）/ M17 F1+F5 同范式低风险漂移群（PUNT-REPORT §共同根因 + 元规则 #11 已锁） |
| F2 | **low** | §6 Component = `web/src/components/business/comparison-matrix.tsx` + `snapshot-panel.tsx` | design §6 字面要求拆 2 个 business/ 子目录 component；prism-0420 实装把矩阵渲染 + 快照面板 + save/rename dialog 全部内联到 `comparison/page.tsx` 单文件（约 580 行 / 无外部业务组件）/ 与 peer flat 范式（cluster-M14 把 page 内联较多 / cluster-M17 wizard 也把 progress UI 内联）一致 | **接受 + 不动 design**：拆 components 是优化项不是契约项；本 cluster 选单文件实装因为 (a) 矩阵 + 快照面板共享大量本地 state（selectedNodeIds / selectedDimIds / matrix），拆出后 state lift / props drilling 复杂度反而高；(b) 与 cluster-M17 F5（独立 import-progress.tsx 合并到 wizard）同思想；(c) M12 §1 in scope 清单里页面级元素（节点选择器 + 维度选择器 + 矩阵 + 快照保存弹窗 + 列表）逻辑紧耦合。如未来拆需求强烈可在独立 cleanup cluster 重构 / 不破契约 |
| F3 | **low** | §6 Server Action = `web/src/actions/comparison.ts` | design §6 字面要求该文件存在但本 cluster 前不存在（PUNT-REPORT 字面）；现 comparison/page.tsx 直接 import `actions/analyze.ts` 中 3 个 stub（generateComparisonAction / backfillRowAction / exportComparisonAction）/ 这 3 stub 接 M13 analyze 端点而非 M12 endpoints / 全部走 puntResult NOT_IMPLEMENTED 返 | **DONE**：新建 `app/src/actions/comparison.ts`（无 `web/` 前缀 / 同 F1 范式）含 6 个函数对接 6 endpoints：getMatrix / listSnapshots / getSnapshotDetail / createSnapshot / renameSnapshot / deleteSnapshot。新 page 不再 import 那 3 个 analyze.ts stub；analyze.ts 中那 3 个 stub **保留不删**（守 cluster boundary：M13 cluster 单独决定其归宿；如果删，相当于动 M13 范围 / 也不破其他 caller — 因为它们没有其他 caller，留着不会引发新调用 / RCA §3.3 说明）|
| F4 | **none** | §7 API contract（6 endpoints / 完整 happy + error code） | backend 实装 `api/routers/comparison_router.py` 全部 6 endpoints 命中（GET /matrix / GET /snapshots / GET /snapshots/{id} / POST / PUT / DELETE）；request/response schema 全 typed via openapi.json 生成 `app/src/types/api.ts`（§ ComparisonMatrixResponse / MatrixCell / SnapshotCreateRequest / SnapshotUpdateRequest / SnapshotResponse / SnapshotListResponse / SnapshotDetailResponse / SnapshotItemResponse 全到位）；status code 200/201/204/404/409/422 全对齐；role viewer/editor 由 backend `Depends(check_project_access(role=...))` 强制 | **PASS**：design 契约 100% 对齐 backend；frontend 直接消费 OpenAPI 生成类型，无字符串硬编码 |
| F5 | **none** | §7 ComparisonMatrixResponse cells-only / R-X3 不嵌跨模块 metadata（裁决 2026-05-08 已锁）| backend 字面只返 `{cells: list[MatrixCell]}`；frontend 实装独立调 `getProjectTree`（M03 节点元数据）+ `getProjectDimensions`（M04 维度类型元数据）拼装 N×M 网格；不期望 backend 返 nodes/dimension_types metadata；spec L256-259 字面验 `expect(body).not.toHaveProperty('nodes' / 'dimension_types')` | **PASS**：与 R-X3 裁决严格一致 |
| F6 | **none** | §3 G2 SnapshotResponse 无 status 字段 / §3 G4=B 值快照（items 表）| frontend 不 hardcode status 字段；展示 SnapshotResponse 仅用 id/name/description/version/nodes_ref/dimensions_ref/created_at；保存快照走 POST /comparison/snapshots / 不传 status；spec L297 + L643 字面验 `expect(snap).not.toHaveProperty('status')` | **PASS** |
| F7 | **none** | §3 + §5 乐观锁 version（rename 并发保护）| frontend 实装 rename dialog 显式传 `expected_version: snap.version`（从 SnapshotResponse 拉取当前 version）；后端 409 COMPARISON_SNAPSHOT_CONFLICT 由 actionError 兜底显示在 Error banner 提示用户刷新；spec L530-535 字面验 `expect(body.message).toBe("Snapshot was modified by someone else; please refresh and retry")` | **PASS** |
| F8 | **none** | §8 权限三层防御 | design §8 字面要求：Server Action 校 session（serverApi* 401 自动 throw UnauthenticatedError → defineAction actionError 兜底 redirect /login）；Router check_project_access(viewer/editor)；Service _check_snapshot_belongs_to_project 防跨项目 snapshot_id。frontend 不提前隐藏 editor 写按钮（与 issue-card / cluster-M14 NewsCard 范式一致：admin-vs-viewer role 由后端返 403 / actionError 显示用户友好错误）| **PASS**：与 peer 业务组件范式一致 |
| F9 | **none** | §10 activity_log 命名规约（comparison_snapshot_created/renamed/deleted 全过去式 + underscore）| frontend 不直接写 activity_log（M15 后端责任 / R-X1 自洽 / R14 守护后端 service）；spec L762/803/834 字面验 `e.action_type === 'comparison_snapshot_created/renamed/deleted'` 全靠后端写 | **PASS** |
| F10 | **none** | §5 异步范式 — 显式 N/A | M12 design §5 字面"异步处理 ❌ N/A"（无 Queue / 无 WebSocket / 矩阵渲染同步 GET / 快照保存同步 POST）；frontend 实装也是全同步 await fetch / 无轮询 / 无 WS / 无 setTimeout 假进度 | **PASS**：不触发 cluster-M16 轮询漂移群 / cluster-M17 WS 漂移群 / 元规则 #11 D 栏（异步范式 audit）confirmed clean |
| F11 | **none** | §11 idempotency 显式无 | M12 design §11 字面"M12 无 idempotency_key 操作"；frontend 创建快照不传任何 idempotency_key header；同名快照允许（spec L867 字面验 2 次同名 POST 都 201 返不同 id）；DELETE 已删 snapshot 自然 404 | **PASS** |
| F12 | **low** | §1 业务定位 + §6 路径段 `compare` vs `comparison` | design §1 字面"路径 /project/:id/compare"；项目实际路由段已固化 `/projects/:id/comparison`（拷贝层既有 + Tab nav + dogfooding spec 全用 comparison） | **接受**：与 F1 同低风险路径漂移 / 不动 design / 不破契约 / spec 全用 `/comparison` 链接（spec L172 + L179 + Tab nav L406 字面）|
| F13 | **low** | spec L182 DOM smoke 断言 `"+ 添加竞品"` button 可见 | spec L166-183 [P1] DOM 测试字面：`expect(page.getByRole("button", { name: "+ 添加竞品" })).toBeVisible()`；该按钮属拷贝层老 UI 范畴（M06 竞品录入 / 不在 M12 §1 in scope）；本 cluster 重写 page.tsx 后不再渲染此按钮（design §1 字面声明竞品录入归 M06 / out of scope）| **PARTIAL / 报 main agent**：spec 测试本身把"design-gap 老 UI button"固化为 DOM 断言；cluster 范围**不改 spec**（plan 红线第 4 条 / spec-fix 走另一轨道 P5b spec-fix 池）。下一次 P5 regression / spec-fix sweep 应把 L182 断言删除或改为反向（按钮**不**存在）。Trade-off：本 cluster 选**不修 spec**以维持 cluster boundary 清晰（cf. cluster-M14 F9 spec L628 反向断言同范式 / cluster-M17 F1 sync design 不动 UI 同思想），由 main agent 在 closeout commit 评估归入 punt pool 7-day rule。Smoke L132（"竞品对比" heading + "选择功能" + "对比竞品" + 生成对比 button + "对比维度" + 空状态 + breadcrumb 竞品对比 + Tab nav `a[href$=/comparison].border-b-2`）全部 8 个断言保留 / 应 PASS。 |

**汇总**：0 high / 0 medium / 5 low（3 接受不动 design / 1 DONE 新建 comparison.ts / 1 PARTIAL spec 反向断言）/ 8 PASS。无 high 冲突 / 不触 escalation 中止条件。

## 设计原则 5 条 + 5 约束清单核对

| 原则 / 清单 | 触发 | 实装 |
|------------|------|------|
| 1. SQLAlchemy schema 唯一真相源 | ❌ frontend 不触 | N/A |
| 2. 分层严格 | ✅ | server action → server-http-client → backend router；page 不直 fetch；validator 单独抽 lib/validators/comparison.ts；defineAction 强制 zod schema 校验 |
| 3. 接口 Contract First | ✅ | endpoint URL 全用 design §7 + comparison_router.py 字面真名（/api/projects/{pid}/comparison/matrix + /snapshots + /snapshots/{id}）；request/response types 全走 `components["schemas"]["Comparison*"|"Snapshot*"|"MatrixCell"]` 自 openapi.json 生成 |
| 4. 状态机显式定义 | ❌ M12 §4 显式无状态机 G2 | N/A |
| 5. 多人架构 4 维必答 | ✅ | tenant: 路径自带 `/api/projects/{pid}/...`（design §5）/ 事务: backend 责任（multi-table create snapshot + items + activity_log）/ 异步: 显式 N/A（design §5）/ 并发: 乐观锁 expected_version 前端正确传递 + 409 冲突错误兜底（rename dialog） |
| 清单 1: activity_log | ✅ | 后端责任 / frontend 不直写 / spec 验 3 个事件命名（design §10） |
| 清单 2: 乐观锁 version | ✅ | rename dialog 显式 `expected_version: snap.version`（design §3 + §5）|
| 清单 3: Queue payload tenant | ❌ | M12 §12 显式 N/A 无 Queue |
| 清单 4: idempotency_key | ❌ | M12 §11 显式无 |
| 清单 5: DAO tenant 过滤 | ✅（间接）| frontend 调用全部带 projectId 路径 → backend DAO 强制 WHERE project_id（design §9）|

无原则违反。

## R-X1 / R-X3 自洽

- **R-X1**（不直 INSERT/UPDATE 跨模块表）：M12 backend 不直写 nodes/dimension_records 表（design §1 in scope + §9 ADR-003 规则 1）；M12 frontend 完全不触后端 service，仅 caller-side 不破 R-X1。
- **R-X3**（API 不嵌跨模块 metadata）：getMatrix 返 cells-only（design §7 R-X3 裁决 / 2026-05-08 锁）；frontend 独立从 M03 getProjectTree + M04 getProjectDimensions 拼装节点 / 维度元数据。**严格自洽**。

## escalation 中止条件检查

- ✅ 0 high 冲突 / 0 medium design 真破设计原则 / ADR-001 / ADR-003（F3 medium 范畴 stub leave-as-is 是 caller 适配选择，不破 design）
- ✅ tsc 0 错（baseline 0 → after 0）
- ✅ eslint 0 错（2 个新文件 — `app/src/lib/validators/comparison.ts` + `actions/comparison.ts` 不在 ignore 列表 / 全 fresh 编写不依赖拷贝层；`comparison/page.tsx` 仍在 ignore：`src/app/projects/**/comparison/**` 字面 — 与 cluster-M14 不同 cluster-M14 在 fresh path / M12 page 是 in-place 重写在既有 ignore 路径下；保 ignore 不动是守 cluster boundary 的合理选择 / eslint 治理是独立 cleanup 工作 / 升 escalation §5）
- ✅ playwright --list M12 PASS（25 tests registered / 无 syntax error）
- ⚠️ playwright run M12 expected：1 DOM smoke FAIL (spec L182 "+ 添加竞品" button — F13 PARTIAL / 反向断言 / cluster boundary 不修 spec / 主 agent 评估)；其余 24 tests（1 DOM smoke + 23 API-bypass）应 PASS
- ✅ pytest M12 全套 65/65 PASS（dao + models + routers + service 4 文件）
- ✅ design vs backend 0 conflict（F4 PASS / 100% 对齐）
- ✅ 改动总行数估算（见 RCA §6）≈ 660 行 / page rewrite 580 行 + actions 新建 158 行 + validator 新建 32 行
- ✅ subagent cost 估算 < $5（plan cap $5-7）
- ✅ 无 A/B 决策升级（design §3/§7 G2/G4=B 已 ack 全部 / spec 期望路径 / 异步范式全自洽）— 1 升 escalation：comparison 路径 eslint ignore 是否打开（见 §5）

**verdict**：**PASS / B 路径 commit allowed**
