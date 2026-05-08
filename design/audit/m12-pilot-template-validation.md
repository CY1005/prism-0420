---
title: M12 sprint 实证 + R1/R2 命中比例 + L1 第十数据点（常规 own + 跨模块只读）
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M12 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀（**常规 own + 跨模块只读 R-X3 模块**）。

  - 闸门 2.5 三栏：A 4 / B 0 / C 4（**第七次 B 栏 0 项**）
  - R1=3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
  - R2=1 合并 Opus subagent endpoint 单审
  - L1+L2+L3 节奏第十次实证（十数据点稳定 / M02-M12 默认范式作 M13+ 模板）
  - design §7 ComparisonMatrixResponse 漂移裁决 = cells-only + scaffold disambiguation
last_reviewed_at: 2026-05-08
---

# M12 sprint 实证 + Review 命中比例

## 模块特性（与 M02-M11 对比）

| 维度 | M02-M08 业务 | M10 纯读 | M11 R-X1 orchestrator | **M12 own + R-X3 跨模块只读** |
|---|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅ | ✅（comparison_snapshots + items）|
| 写跨模块表 | ❌ | ❌ | ❌（强制）| ❌（只 INSERT own）|
| 调跨模块 service | 偶尔（R-X2 child）| ❌ | ✅ 4 batch_create | **✅ DimensionService.batch_get_by_nodes（R-X3 只读）** |
| 多表事务 | 偶尔 | N/A | 必须 | **必须（snapshot + items + activity_log）**|
| 乐观锁 version | 偶尔 | N/A | ❌（task 单写）| ✅（rename）|
| 文件上传 | ❌ | ❌ | ✅（首发）| ❌（N/A）|
| 失败补偿 | N/A | N/A | 首发挑战 punt | N/A |

---

## 闸门 2.5 reconcile 三栏（**第七次 B 栏 0 项**）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 4 | A1 §14.5 sprint review 计划段补 / A2 DimensionService.batch_get_by_nodes 实装（M04 sprint scaffold "caller sprint 实装" 到期，M12 是首 caller）/ A3 design 节 6/9 同步代码示例落 async / A4 元教训防御 actionable 5 主动复制（viewer 写 3 端点 403 + write_event 异常传播 + cross-tenant 404 + cross-project node 422 + IntegrityError 区分约束）|
| **B 待 CY 决策** | **0** | （第七次 B 栏 0 项 / M05+M06+M07+M08+M10+M11+M12 七连稳定）|
| **C 已自我消解** | 4 | C1 R-X1 orchestrator 失败补偿 N/A（M12 不是 R-X1）/ C2 文件上传 N/A（M12 无上传）/ C3 queue payload N/A（design §12 显式）/ C4 R-X2 child service N/A（M12 不被 NodeChildrenService 调，nodes 删走 ON DELETE SET NULL passive_deletes）|

---

## R1 review 命中（3 subagent 并行 / 子片 0+1+2+3 合并审）

### R1-A spec+quality Opus 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | delete metadata 字段名漂移：实装 `nodes_count` vs design §10 表 `node_ids_count` | **立修** commit 169e948（service.py L313）|
| P2 6 项 | rename actual_version=stale snap.version / bulk_insert_items 用 add_all 而非 insert / 0 items 边界 / set 去重导致 missing 顺序非确定 / design §13 ComparisonNodeNotFoundError(NotFoundError) vs 实装 ValidationError 漂移 / ComparisonSnapshotNameEmptyError 同款漂移 | punt 池（design 关闸回写）|

### R1-B reuse Sonnet 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1 | _mk_snap 内联 helper 跨文件重复（test_m12_dao 16 次 + test_m12_service 8 处裸构造）→ M03 R1-B C1 跨文件 helper 规则延续 | **立修** commit 169e948：迁 conftest 作 make_snapshot fixture |
| P2 2 项 | DAO 7 处 project_id where 重复（M19 punt）/ _seed_records helper 待 M13/M16 触发迁 conftest | punt 池 |
| OK | DimensionService.batch_get_by_nodes 薄 wrapper 不重复 SQL / NodeDAO.list_by_ids 复用 / write_event 8 参全对齐 / 复用率 5/12 conftest fixtures = 42%（合理：M12 全新模型无 version/relation 依赖）| ✅ |

### R1-C quality+efficiency Sonnet 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | design §13 `ComparisonNodeNotFoundError(NotFoundError)` 字面 vs 实装 `ValidationError` 422（叙述+元教训对齐 422）| design §13 关闸回写（与 R1-A P2-05 合并） |
| P1-02 | rename_snapshot write_event 异常传播测试缺失（M04+ 三写端点必有；create + delete 已有，缺 rename）| **立修** commit 169e948 补 test_rename_snapshot_write_event_failure_propagates |
| P1-03 | Core UPDATE 不触发 ORM onupdate → rename 后 updated_at 不刷新（隐性 bug）| **立修** commit 169e948：DAO update_snapshot_with_version 显式 .values(updated_at=datetime.now(UTC)) + 新测 test_rename_snapshot_updates_updated_at |
| P2 3 项 | list_snapshots 双查询 / 无 offset 分页 / unique_ids set vs dict.fromkeys 保序 | punt 池 |
| 覆盖空白 4 | rename version 多次累加 / delete 后重复 delete 404 / rename cross-tenant 404 / create items content=None 路径 | **2 补**（rename multi_increment + cross-tenant 404；其余 punt）|
| OK | N+1 selectinload + IN 查 / 静默吞错通过 / 空状态全防 / ErrorCode 字符串值与 design 字面一致 / 乐观锁 _get_or_raise + rows=0 区分 / migration 链 + 对称 / server_default 与 model default 一致 | ✅ |

**R1 P1 立修汇总（合并 4 + 4 coverage 补 = 8 改动）**：commit `169e948`
- nodes_count → node_ids_count（R1-A P1-01）
- _mk_snap 迁 conftest make_snapshot（R1-B P1）
- rename write_event 异常传播测试（R1-C P1-02）
- Core UPDATE updated_at 显式刷（R1-C P1-03）
- 覆盖补：rename cross-tenant 404 + multi_increment + updated_at 验证 + ComparisonNodeNotFoundError 422 验证

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 endpoint 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | `ComparisonMatrixResponse` 契约漂移：design §7 草案含 `nodes` + `dimension_types` + `cells` 三字段，实装只返 `cells`；前端拿 metadata 需另调 M03/M04 | **裁决 = Option B（cells-only）+ design §7 回写 disambiguation 注释**（与 M02-M11 R-X3 不嵌响应范式一致；前端用 list_tree + list_dim_types 缓存复用 / 避免字段类型重复维护）|
| P2 6 项 | description=None PUT 语义未 design 化 / get_matrix_data dedupe / matrix empty list 单测 / delete 后访问 ORM attr / description router 端到端 / 节点删后 GET detail 端到端 | punt 池 |

**R2 P1 处理**：design §7 + scaffold 注释回写（无代码改动；与 M11 R2 P1-02/03 立修路径不同 — M12 是裁决型 P1 而非攻击面型）。

**M12 R2 命中 1 P1 裁决型**（M02-M10 R2 P1 0-1 区间 / M11 R2 3 P1 R-X1 首发）→ 第十数据点 R2 范式回归 0-1 P1 稳态。

---

## L1+L2+L3 节奏第十次实证（**十数据点稳定 → M13+ 默认范式作模板**）

| 层 | 内容 |
|---|---|
| L1 总则 | sprint ≥1 次 review + ≥50 行 OR ≥2 文件触发；触发例外条款全合规 |
| L2 sprint 计划 | design §14.5 sprint review 拆分计划段（commit 63f2f93 子片 0 prep 落地）|
| L3 实证回写 | 本文件 |

**M12 默认范式（M11 复用）**：
- R1 = 3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
- R2 = 1 合并 Opus subagent endpoint 单审
- 子片 5 不单跑（≥80% SKIP 例外）
- M12 自身无 schema 子片（子片 1 = own model + alembic）

---

## 元教训防御 actionable 应用情况（**M12 R1+R2 主动复制不等抓**）

| # | 元教训 | 应用结果 |
|---|---|---|
| 1 | viewer 写**所有**写端点 403 全覆盖（M07 立 / M08+M11 应用）| ✅ test_viewer_write_returns_403_full_coverage（POST + PUT + DELETE 3 端点全 403）|
| 2 | write_event 异常传播测试（M04+ 范式）| ✅ create + rename + delete 三端点全（rename 经 R1-C P1-02 立修补）|
| 3 | cross-tenant 404（M02 范式）| ✅ test_cross_tenant_project_404 / test_get_snapshot_detail_cross_tenant_404 / test_delete_snapshot_cross_tenant_404 / test_rename_snapshot_cross_tenant_404 |
| 4 | cross-project node 422（M06+M07+M08 范式）| ✅ test_get_matrix_cross_project_node_raises / test_create_snapshot_cross_project_node_raises / test_matrix_cross_project_node_422 |
| 5 | IntegrityError 区分约束名（M05 P1-01）| N/A（M12 无 unique 约束；DAO ValueError 防空 fields 合规）|
| 6 | 纯读模块 docstring 每字段 ≥1 unit test（M10 NEW）| N/A 业务模块；"绿测 ≠ 范式正确" 通用元教训仍参考 |
| 7 | R1.5 reconcile checkpoint（M10 NEW）| ✅ R2 反向命中 R1 未抓的契约漂移（matrix metadata），属"R-X3 范式裁决型"非"反复"|
| 8 | R-X1 失败补偿 commit boundary（M11 NEW）| N/A（M12 不是 R-X1）|
| 9 | 文件上传 file.size + sanitize（M11 NEW）| N/A（M12 无上传）|

---

## design 回写（关闸 commit 同 commit）

- §7 `ComparisonMatrixResponse` 回写 cells-only + scaffold disambiguation 注释（R2 P1-01）
- §10 action_type 列从 `snapshot.create` 等点号改为 underscore `comparison_snapshot_created` 等（与 frontmatter `produces_action_types` + 实装一致；R1-A 元教训新发现）
- §13 `ComparisonNodeNotFoundError(NotFoundError)` → `(ValidationError)` 422；`ComparisonSnapshotNameEmptyError(AppError)` → `(ValidationError)`（与实装 + R-X3 元教训对齐 / R1-A P2-05/P2-06 + R1-C P1-01 合并）
- 节 6 + 节 9 同步代码示例补 async 范式说明（实施期处理段；与 M05/M06/M07 关闸回写惯例一致）
- §3 `ComparisonSnapshotItem` cascade 'all, delete-orphan' + passive_deletes=True 实装回写
- §15 完成度 checklist 三轮 reviewer audit 勾选

---

## Punt 池总表（M12 sprint 完成期 / 后续 sprint 顺手清）

| # | 项 | 来源 | 推荐时机 |
|---|----|------|---------|
| B1 | rename actual_version=stale snap.version → 文档说明或 refresh 后再抛 | R1-A P2 | 后续 sprint 顺手 |
| B2 | bulk_insert_items 用 add_all → insert(...).values(...) 性能优化 | R1-A P2 | 性能 sprint |
| B3 | create_snapshot 0 items 边界 e2e 测试（empty matrix snapshot）| R1-A P2 | 后续 sprint |
| B4 | _validate_nodes_in_project 用 dict.fromkeys 保序去重 | R1-A P2 | 5 行小改 / 后续顺手 |
| B5 | DAO 7 处 `project_id == ?` where 抽 _tenant_filter helper | R1-B P2 | M19 sprint 评估 |
| B6 | _seed_records test helper 迁 conftest（M13/M16 触发）| R1-B P2 | M13/M16 sprint 启动期 |
| B7 | list_snapshots 双查询合一（COUNT(*) OVER()）| R1-C P2 | 性能 sprint |
| B8 | list_snapshots 加 offset / cursor 分页 | R1-C P2 | UI 翻页需求时 |
| B9 | description=None PUT 语义 design §7 锁定（清空 vs 保留旧值）| R2 P2 | 子片 5 design 回写 / 否则后续 sprint |
| B10 | get_matrix_data dedupe（重复 node_ids 是否产重复 cells）| R2 P2 | 后续 sprint 顺手 |
| B11 | matrix endpoint empty list query 端到端测试 | R2 P2 | 后续 sprint |
| B12 | delete_snapshot 先 snapshot name/nodes_ref 到本地变量再 DELETE | R2 P2 | 后续 sprint 顺手（防御）|
| B13 | PUT description 端到端 + 节点删后 GET detail 端到端 | R2 P2 | 后续 sprint 端到端补 |

---

## sprint 总览数据

- **commits**：7 主提交
  - 63f2f93 子片 0 prep（§14.5 + DimensionService.batch_get_by_nodes + 3 smoke）
  - 9a0f039 子片 1（model + alembic + 9 model tests）
  - 3aa7415 子片 2（DAO + 16 unit tests）
  - 99105b4 子片 3（Service + 5 ErrorCode + 21 service tests）
  - 169e948 R1 立修（4 P1 + 4 coverage tests）
  - 589407c 子片 4（router + 6 endpoints + 15 e2e tests）
  - 子片 5 关闸 commit（本 audit + roadmap + handoff + design 回写）
- **测试**：742 PASS / 0 fail / ruff 净 / R13-1 79=79 / L12 守护通过
- **新增 ErrorCode**：5（comparison_*）→ R13-1 74→79
- **新增 endpoints**：6（GET matrix / GET list / POST create / GET detail / PUT rename / DELETE）
- **新增模型**：2（ComparisonSnapshot + ComparisonSnapshotItem）
- **新增表**：2（comparison_snapshots + comparison_snapshot_items）
- **新增横切 helper**：DimensionService.batch_get_by_nodes（M04 own / M12 首 caller）+ make_snapshot conftest fixture
- **跨模块接通**：R-X3 只读（DimensionService.batch_get_by_nodes / NodeDAO.list_by_ids）
- **复用率**：~95%（service 层 100% / 测试 conftest fixtures 5/12 = 42% 但合理 / R1-B 立修后 helper 100% 在 conftest）

---

## 关联

- design 真相源：design/02-modules/M12-comparison/00-design.md
- 上游决策：ADR-001（shadow-prism 单 ORM）+ ADR-003（跨模块只读 R-X3：聚合读走上游 service）
- 跨 sprint 元教训沉淀候选：feedback_design_scaffold_reconcile（design §7 草案 vs 实装 cells-only 漂移裁决属同形态）
