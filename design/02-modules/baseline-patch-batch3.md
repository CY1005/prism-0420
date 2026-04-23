---
title: batch3 基线补丁：R10-1 / R-X3 / R10-2 回扫
status: accepted
owner: CY
created: 2026-04-24
accepted: 2026-04-24
supersedes: []
superseded_by: null
last_reviewed_at: 2026-04-24
batch: baseline-patch-3
modules_scanned: [M02, M03, M04, M06, M07, M11, M12, M17]
modules_excluded: [M08, M09, M10, M15]
---

# batch3 基线补丁扫描报告

## 1. 执行摘要

- 扫描模块数：8（含 2 个 pilot：M04 / M17）
- 不合规发现总数：15 个
- 按严重度：High 7 / Medium 5 / Low 3
- Pilot 冲突：M04 2 处 / M17 0 处（M17 自身合规，问题在下游 M04）
- R10-2 回写枚举：ActionType 需扩增 19 个值 / TargetType 需扩增 4 个值

## 2. 每模块发现

---

### M02 项目管理

**R10-1 批量 activity_log 颗粒度**：

- **F-01（⚠️ Medium）**`update_dimension_config` 汇总事件
  - 文件：`M02-project/00-design.md` §10（第 594 行）
  - 现状：PUT `/dimension-configs` 批量更新 N 个维度配置，写 **1 条** `update_dimension_config` 事件（target_type=`project`, target_id=project_id, metadata 含 `changed_configs` 数组）
  - 违规：R10-1 要求每个被影响实体写独立事件。如果一次更新了 5 个维度配置，应写 5 条独立事件
  - **灰区说明**：维度配置是"项目设置"而非独立业务实体，target_type 用的是 `project`。如果改为 N 条独立事件，需新增 target_type `project_dimension_config`。CY 裁决是否严格适用 R10-1
  - 建议改法 A：改为 N 条独立事件（target_type=`project_dimension_config`, target_id=config_id）
  - 建议改法 B：保留 1 条汇总，标注为 R10-1 已知豁免（理由：配置变更非业务实体 CRUD）

**R-X3 外部 db session**：无跨模块级联场景，合规 ✅

**R10-2 action_type 回写**：
- 需扩增 ActionType：`invite_member`, `update_member_role`, `remove_member`, `update_dimension_config`, `update_ai_provider`
- 需扩增 TargetType：无新增（`project` / `project_member` 已在 M15）

---

### M03 功能模块树

**R10-1 批量 activity_log 颗粒度**：

- **F-02（🔴 High）**`delete_node` 子树级联——子 node 无独立 activity_log
  - 文件：`M03-module-tree/00-design.md` §10（第 476 行）
  - 现状：删除 folder 时 DB CASCADE 删除 N 个子 node，只写 **1 条** `delete` 事件（target_id=被删根节点, metadata 含 `subtree_count`）
  - 违规：R10-1 要求每个被影响实体独立。删除含 10 个子节点的 folder 应写 11 条事件（根 + 10 子 node 各 1 条）
  - 建议改法：Service 层 delete_node 时先用 `list_subtree` 获取所有子节点，逐一写 delete activity_log，再执行删除。DB CASCADE 仍作兜底

- **F-03（⚠️ Medium）**`reorder` 写汇总事件
  - 文件：`M03-module-tree/00-design.md` §10（第 477 行）
  - 现状：拖拽重排 N 个同级节点，写 **1 条** `reorder` 事件（target_id=parent_id, metadata 含所有被修改 node 的 old/new_order）
  - 违规：R10-1 要求 N 条独立事件（每个被重排 node 各 1 条 target_id=node_id）
  - 建议改法：每个被修改 sort_order 的 node 写独立 `reorder` 事件

- **F-04（Low）**`move_subtree` 子树移动——灰区
  - 文件：`M03-module-tree/00-design.md` §10（第 478 行）
  - 现状：子树移动涉及 N 个 node 的 path/depth 更新，写 **1 条** `move` 事件（metadata 含 subtree_count）
  - 灰区：子树作为原子整体移动，每个子 node 的 path 变更是内部实现而非独立业务操作。CY 裁决是否适用 R10-1

**R-X3 外部 db session**：

- **F-05（🔴 High）**M03 `delete_node` 调用下游缺接口定义
  - 文件：`M03-module-tree/00-design.md` §8（第 398-401 行）
  - 现状：M03 §8 假设调用 `M04.DimensionService.delete_by_node_id(db, node_id, project_id)` / `M06.CompetitorService.delete_by_node_id(...)` / `M07.IssueService.delete_by_node_id(...)`——传了 db 参数（格式正确）
  - 问题：但 M04/M06/M07 的设计文档中**均未定义这些方法**（详见各模块 F-07/F-09/F-11）。M03 调用的是"不存在的接口"
  - 建议改法：修复方在下游模块（M04/M06/M07），补充 Service 方法签名

- **F-06（⚠️ Medium）**M07 `delete_by_node_id` 语义与 FK 定义冲突
  - 文件：M03 §8（第 401 行）+ M07 §3（第 126 行 `ON DELETE SET NULL`）
  - 现状：M03 调用 `M07.IssueService.delete_by_node_id`（方法名暗示删除），但 M07 issues.node_id 的 FK 是 `ON DELETE SET NULL`（节点删除后 issue 变游离，不被删除）
  - 问题：方法名与实际行为不一致——M07 的 issue 在节点删除时应该是"node_id 置 NULL + 写 activity_log"，而非"删除 issue"
  - 建议：M07 补充方法时命名为 `orphan_by_node_id(db: Session, node_id, project_id)` 或保持 `delete_by_node_id` 但内部实现为设 NULL。CY 裁决命名

**R10-2 action_type 回写**：
- 需扩增 ActionType：`reorder`, `move`
- 需扩增 TargetType：无新增（`node` 已在 M15）

---

### M04 功能项档案页 ★Pilot

**R10-1 批量 activity_log 颗粒度**：

- **F-07a（🔴 High · Pilot）**`batch_create_in_transaction` 未定义 activity_log 行为
  - 文件：`M04-feature-archive/00-design.md` §10（第 398-413 行）
  - 现状：M04 §10 只定义了单条 CRUD 事件（create/update/delete dimension_record）。但 M11/M17 都调用 `DimensionService.batch_create_in_transaction`——该方法在 M04 中**未定义**，更无 activity_log 写入策略
  - R10-1 要求：batch_create 应为每条新建的 dimension_record 写独立 `create` 事件
  - 建议改法：M04 补充 `batch_create_in_transaction` 方法定义 + §10 补充"批量创建时每条 dimension_record 写独立 create 事件"

**R-X3 外部 db session**：

- **F-07b（🔴 High · Pilot）**Service 方法缺少外部 db session 签名
  - 文件：`M04-feature-archive/00-design.md` §6（第 257 行）/ §9（第 341-383 行）
  - 现状：M04 pilot 所有 Service/DAO 方法使用 `self.db` 管理事务（§5 `self.db.transaction()`），无接受外部 `db: Session` 参数的方法。但 M17 §1 假设调用 `M04 DimensionService.batch_create_in_transaction(db, dimensions, project_id)`，M03 §8 假设调用 `M04.DimensionService.delete_by_node_id(db, node_id, project_id)`
  - 缺少方法：
    1. `batch_create_in_transaction(db: Session, dimensions: list, project_id: UUID)`——M11/M17 调用
    2. `delete_by_node_id(db: Session, node_id: UUID, project_id: UUID)`——M03 级联删除调用
  - R-X3 要求：这两个方法必须接受外部 db session，不得 `self.db.begin()` 另开事务

**R10-2**：合规（create/update/delete + dimension_record 均已在 M15 schema）

---

### M06 竞品参考

**R10-1 批量 activity_log 颗粒度**：

- **F-08（合规 ✅）**级联删除竞品时已逐条写 refs 日志
  - §10（第 383 行）明确："Service 层在调 delete 前先查所有关联 refs 并逐条写入 delete competitor_ref 日志"——合规

**R-X3 外部 db session**：

- **F-09（🔴 High）**Service 缺少 `batch_create_in_transaction` 和 `delete_by_node_id` 方法
  - 文件：`M06-competitor/00-design.md` §6（第 229 行）
  - 现状：M06 §6 Service 层无 `batch_create_in_transaction` 或 `delete_by_node_id` 方法定义
  - 依赖方：
    1. M11/M17 调用 `CompetitorService.batch_create_in_transaction(db, competitors, project_id)`
    2. M03 调用 `CompetitorService.delete_by_node_id(db, node_id, project_id)` 做级联删除
  - 建议改法：§6 补 Service 对外契约（R-X3 签名），§10 补 batch_create 写 N 条独立事件

**R10-2 action_type 回写**：
- 需扩增 TargetType：`competitor_ref`（M15 当前有 `competitor` 无 `competitor_ref`）

---

### M07 问题沉淀

**R10-1 批量 activity_log 颗粒度**：无批量操作，合规 ✅

**R-X3 外部 db session**：

- **F-10（🔴 High）**Service 缺少 `batch_create_in_transaction` 和 `delete_by_node_id` 方法
  - 文件：`M07-issue/00-design.md` §6（第 263 行）
  - 现状：与 M06 同——M07 §6 无这两个方法定义
  - 依赖方：
    1. M11/M17 调用 `IssueService.batch_create_in_transaction(db, issues, project_id)`
    2. M03 调用 `IssueService.delete_by_node_id(db, node_id, project_id)` 做级联处理
  - 注意：M07 的 node_id FK 是 `ON DELETE SET NULL`，所以 `delete_by_node_id` 可能实际是"orphan"操作（见 F-06）
  - 建议改法：同 M06

**R10-2 action_type 回写**：
- 需扩增 ActionType：`status_change`

---

### M11 冷启动

**R10-1 批量 activity_log 颗粒度**：

- **F-11（⚠️ Medium）**批量入库依赖下游 batch_create 写 N 条事件——但下游未定义
  - 文件：`M11-cold-start/00-design.md` §10（第 401 行）
  - 现状：M11 自身写 `cold_start.completed` 1 条汇总事件（关于 task 本身）是合理的。但 M11 作为 orchestrator 调用 M03/M04/M06/M07 的 `batch_create_in_transaction`，这些模块的 batch_create 应负责写各自实体的 N 条独立 activity_log。
  - 问题：M03 的 `batch_create_in_transaction` 已在 §6 定义，但**未在 §10 说明 batch_create 时 activity_log 写入策略**；M04/M06/M07 连 batch_create 方法都没定义（见 F-07a/F-09/F-10）
  - 建议改法：各模块补充 batch_create 的 activity_log 策略（R10-1：每条实体独立事件）

**R-X3 外部 db session**：

- M11 §5 已正确描述 `with db.begin():` 外层事务传给各模块 Service。M11 自身合规 ✅。问题在下游模块缺方法定义。

**R10-2 action_type 回写**：
- 需扩增 ActionType：`cold_start.create`, `cold_start.completed`, `cold_start.failed`
- 需扩增 TargetType：`cold_start_task`

---

### M12 对比矩阵

**R10-1 批量 activity_log 颗粒度**：

- **合规 ✅**：`snapshot.create` 写 1 条事件（含 items_count），snapshot_items 是快照值副本而非独立可审计业务实体

**R-X3 外部 db session**：无跨模块级联场景，合规 ✅

**ADR-003 跨模块读**：

- **F-12（⚠️ Medium）**矩阵渲染 DAO 直接 `db.query(DimensionRecord)` 跨模块读
  - 文件：`M12-comparison/00-design.md` §9（第 460-478 行）
  - 现状：`ComparisonDAO.get_matrix_data` 直接 `db.query(DimensionRecord).filter(...)` 读取 M04 的 model。M12 有自有表（非纯读聚合模块），不完全适用 ADR-003 规则 2（该规则给"无自有表"模块）
  - R-X1 原文："orchestrator 模块通过其他模块 Service 调用，不直查/直写其他模块的表"——直查也在禁止范围
  - 灰区：M12 对 M04 是只读 JOIN 查询（性能优于多次 Service 调用）；强制走 M04 Service 接口会增加一层抽象
  - 建议 A：标注为 ADR-003 规则 2 扩展豁免（"有主表模块的只读聚合查询"），在 ADR-003 扩展规则 2 适用条件
  - 建议 B：改为调 M04 `DimensionService.batch_get_by_nodes(db, node_ids, dim_type_ids, project_id)` Service 接口

**R10-2 action_type 回写**：
- 需扩增 ActionType：`snapshot.create`, `snapshot.rename`, `snapshot.delete`
- 需扩增 TargetType：`comparison_snapshot`

---

### M17 AI 智能导入 ★Pilot

**R10-1 批量 activity_log 颗粒度**：

- **F-13（Low · Pilot）**`import.batch_insert` 汇总事件——M17 自身合规但下游未保证
  - 文件：`M17-ai-import/00-design.md` §10（第 545 行）
  - 现状：`import.batch_insert` 写 1 条事件（target_type=import_task），关于任务本身而非导入实体。合理——导入实体的 activity_log 应由 M03/M04/M06/M07 的 batch_create 写
  - 问题：同 F-11——下游 batch_create 未定义 activity_log 策略

**R-X3 外部 db session**：

- **M17 自身合规 ✅**：§5 明确 "各 Service 共享同一 db session 不开新事务"，§1 列出了正确的调用签名（含 db 参数）
- 问题在下游 M04 pilot（F-07b）

**R10-2 action_type 回写**：
- 需扩增 ActionType：`import.create`, `import.status_change`, `import.ai_step_complete`, `import.review_confirmed`, `import.batch_insert`, `import.cancel`, `import.failed`, `import.partial_failed`
- 需扩增 TargetType：`import_task`

---

## 3. Pilot 冲突汇总（CY 决策）

| 模块 | 发现 ID | 违规点 | 触发规则 | 选项 A 修 pilot | 选项 B 标 known deviation |
|------|---------|-------|---------|----------------|------------------------|
| **M04** | F-07a | 缺 `batch_create_in_transaction` 方法 + activity_log 策略 | R10-1 / R-X3 | §6 补 Service 对外契约 2 个方法签名 + §10 补批量事件策略 | 标注"pilot 建立于 R10-1/R-X3 之前，M11/M17 实现时再补" |
| **M04** | F-07b | Service 方法不接受外部 db session | R-X3 | 同上（方法补完即含 db: Session 签名） | 同上 |
| **M17** | — | M17 自身合规 | — | 不需要改 | — |

**建议**：M04 pilot 的 F-07a/F-07b 本质是同一个缺口——M04 pilot 设计早于 R-X3/R10-1 规则，缺少"被跨模块调用"的 Service 方法。推荐**选项 A 修**，因为 M03/M11/M17 三个已 accepted 模块都依赖这些方法存在，不修会导致 Phase 2 实现时无文档依据。修改量小（补 2 个方法签名 + 2-3 行 §10 说明）。

---

## 4. M15 schema 回写清单（R10-2）

### ActionType 需扩增

合并去重各模块 §10 的 action_type 枚举值（M15 当前有：create / update / delete / import / analyze / archive）：

| action_type | 来源模块 | 中文语义 | 是否需新增 |
|------------|---------|---------|-----------|
| `create` | 全部 | 创建 | 已有 ✅ |
| `update` | 全部 | 更新 | 已有 ✅ |
| `delete` | 全部 | 删除 | 已有 ✅ |
| `archive` | M02 | 归档项目 | 已有 ✅ |
| `invite_member` | M02 | 邀请成员 | **新增** |
| `update_member_role` | M02 | 变更成员角色 | **新增** |
| `remove_member` | M02 | 移除成员 | **新增** |
| `update_dimension_config` | M02 | 更新维度配置 | **新增** |
| `update_ai_provider` | M02 | 更新 AI Provider | **新增** |
| `reorder` | M03 | 拖拽重排 | **新增** |
| `move` | M03 | 跨父移动 | **新增** |
| `status_change` | M07 | 状态流转 | **新增** |
| `cold_start.create` | M11 | 创建冷启动任务 | **新增** |
| `cold_start.completed` | M11 | 冷启动完成 | **新增** |
| `cold_start.failed` | M11 | 冷启动失败 | **新增** |
| `snapshot.create` | M12 | 创建对比快照 | **新增** |
| `snapshot.rename` | M12 | 重命名快照 | **新增** |
| `snapshot.delete` | M12 | 删除快照 | **新增** |
| `import.create` | M17 | 创建导入任务 | **新增** |
| `import.status_change` | M17 | 导入任务状态变更 | **新增** |
| `import.ai_step_complete` | M17 | AI 步骤完成 | **新增** |
| `import.review_confirmed` | M17 | 用户确认 review | **新增** |
| `import.batch_insert` | M17 | 批量入库完成 | **新增** |
| `import.cancel` | M17 | 用户取消导入 | **新增** |
| `import.failed` | M17 | 导入失败 | **新增** |
| `import.partial_failed` | M17 | 导入部分失败 | **新增** |

**新增 ActionType 共 19 个**。

### TargetType 需扩增

M15 当前有：node / dimension_record / version_record / competitor / issue / relation / project / project_member / module_relation

| target_type | 来源模块 | 中文语义 | 是否需新增 |
|------------|---------|---------|-----------|
| `project` | M02 | 项目 | 已有 ✅ |
| `project_member` | M02 | 项目成员 | 已有 ✅ |
| `node` | M03 | 节点 | 已有 ✅ |
| `dimension_record` | M04 | 维度记录 | 已有 ✅ |
| `competitor` | M06 | 竞品 | 已有 ✅ |
| `competitor_ref` | M06 | 竞品对标记录 | **新增** |
| `issue` | M07 | 问题 | 已有 ✅ |
| `cold_start_task` | M11 | 冷启动任务 | **新增** |
| `comparison_snapshot` | M12 | 对比快照 | **新增** |
| `import_task` | M17 | 导入任务 | **新增** |

**新增 TargetType 共 4 个**。

### 附注：`relation` vs `module_relation` 语义重叠

M15 当前 TargetType 同时含 `relation`（来源不明）和 `module_relation`（M08）。batch3 verify 报告 NI-3 已标注此问题。建议本次回写时厘清：
- 若 `relation` 无模块使用 → 移除
- 若 `relation` 有模块使用 → 需追溯来源

### CheckConstraint 更新

M15 §3 两个 CheckConstraint 需同步更新以包含新枚举值：
- `ck_activity_log_action_type`：从 6 值扩展到 25 值
- `ck_activity_log_target_type`：从 9 值扩展到 13 值

---

## 5. CY 决策请求

### 5.1 Pilot 冲突处理

**M04 pilot**（F-07a + F-07b）：
- **选项 A 修 pilot**（推荐）：补 2 个 Service 方法签名 + §10 批量事件策略。改动量约 20 行，不改现有设计逻辑。M03/M11/M17 都依赖这些方法。
- **选项 B 标 known deviation**：M04 锁定，标注"建立于 R10-1/R-X3 之前"，Phase 2 实现时再补。

M17 pilot 自身合规，无需改。

### 5.2 R10-1 灰区裁决

3 个灰区需 CY 一句话裁：

| ID | 灰区 | 选项 A 严格 | 选项 B 豁免 |
|----|------|-----------|-----------|
| F-01 | M02 `update_dimension_config` 汇总 | 改 N 条独立（新增 target_type `project_dimension_config`） | 保留汇总，标注"配置变更非 R10-1 适用场景" |
| F-04 | M03 `move_subtree` 子树 1 条 | 改 N 条（每个子 node 独立 move 事件） | 保留 1 条，标注"子树原子操作豁免" |
| F-06 | M07 `delete_by_node_id` 命名 | 改名 `orphan_by_node_id`（语义准确） | 保留 `delete_by_node_id`（约定俗成，内部实现为 SET NULL） |

### 5.3 M12 跨模块读（ADR-003）

**F-12**：M12 `get_matrix_data` 直接 `db.query(DimensionRecord)`：
- **选项 A**：扩展 ADR-003 规则 2 适用条件（允许"有主表模块的只读聚合查询"也豁免）
- **选项 B**：改为走 M04 Service 接口（`DimensionService.batch_get_by_nodes`）

### 5.4 修复范围

- **选项 1：全修**（15 处）—— 预计 40 min
- **选项 2：只修 High**（7 处）—— 预计 20 min（M04 pilot 决策后 + M06/M07/M03 补方法 + M03 delete_node R10-1）
- **选项 3：分批**（本轮修 High + R10-2 回写，下轮修 Medium/Low 灰区）

### 5.5 修复方式

- 修复量 < 10 处：主对话直接 Edit
- 修复量 ≥ 10 处：起 Fix Agent 机械修（Sonnet）

---

## 6. 发现汇总表

| ID | 模块 | 严重度 | 触发规则 | 问题摘要 |
|----|------|-------|---------|---------|
| F-01 | M02 | ⚠️ Medium | R10-1 | `update_dimension_config` 批量更新写 1 条汇总事件（灰区） |
| F-02 | M03 | 🔴 High | R10-1 | `delete_node` 子树 N 个子 node 无独立 delete 事件 |
| F-03 | M03 | ⚠️ Medium | R10-1 | `reorder` 多节点重排写 1 条汇总事件 |
| F-04 | M03 | Low | R10-1 | `move_subtree` 子树移动写 1 条事件（灰区） |
| F-05 | M03 | 🔴 High | R-X3 | `delete_node` 调用下游 3 个模块的方法在下游均未定义 |
| F-06 | M03→M07 | ⚠️ Medium | R-X3 | `delete_by_node_id` 方法名与 M07 FK SET NULL 语义冲突 |
| F-07a | M04 ★Pilot | 🔴 High | R10-1/R-X3 | 缺 `batch_create_in_transaction` + activity_log 策略 |
| F-07b | M04 ★Pilot | 🔴 High | R-X3 | Service 方法不接受外部 db session（缺 2 个方法签名） |
| F-08 | M06 | ✅ OK | R10-1 | 级联删竞品已逐条写 refs 日志 |
| F-09 | M06 | 🔴 High | R-X3 | 缺 `batch_create_in_transaction` + `delete_by_node_id` 方法 |
| F-10 | M07 | 🔴 High | R-X3 | 缺 `batch_create_in_transaction` + `delete_by_node_id` 方法 |
| F-11 | M11 | ⚠️ Medium | R10-1 | 下游 batch_create 的 activity_log 策略未定义 |
| F-12 | M12 | ⚠️ Medium | ADR-003 | `get_matrix_data` 直接跨模块读 M04 DimensionRecord |
| F-13 | M17 ★Pilot | Low | R10-1 | 自身合规但依赖下游 batch_create 未定义 activity_log |
| — | All | R10-2 | R10-2 | M15 ActionType 需扩增 19 值 / TargetType 需扩增 4 值 |

---

## 7. CY 决策记录（2026-04-24 ack）

6 条决策按"用户场景影响 + 后续维护坑"展开后 CY 拍板，全部落地：

| # | 决策点 | CY 拍板 | 落地文件 |
|---|-------|--------|---------|
| 1 | M04 pilot 破例修（F-07a/7b）| **A 修 pilot**——补 Service 对外契约避免 M03 级联/M11/M17 在 Phase 2 代码阶段现设计 | `M04-feature-archive/00-design.md` §6 补 `batch_create_in_transaction` + `delete_by_node_id` 契约；§10 补 R10-1 批量事件策略 |
| 2 | M02 `update_dimension_config` 灰区（F-01）| **A 严格 N 条独立**——保 R10-1 无例外分支；新 target_type `project_dimension_config` | `M02-project/00-design.md` §10；M15 schema 扩增 |
| 3 | M03 `move_subtree` 子树灰区（F-04）| **A 每子节点独立 move**——保 M15 精确回溯价值；前端靠 `triggered_by + root_node_id` 折叠 | `M03-module-tree/00-design.md` §10 |
| 4 | M07 `delete_by_node_id` 命名（F-06）| **改 `orphan_by_node_id`**——方法名符真实行为（SET NULL 非 DELETE），避免 Phase 2 调用方误以为 issue 被真删漏后续处理 | `M07-issue/00-design.md` §6/§10；`M03-module-tree/00-design.md` §1/§5/§6/§8 级联调用表同步改名 |
| 5 | M04 §5 `self.db.transaction()` 顺手修（残留 1）| **修**——pilot 作为同步模板，错误 API 不修会被抄到 3-5 个模块全崩 | `M04-feature-archive/00-design.md` §5 多表事务行：`self.db.transaction()` → `with db.begin():` + R-X3 补充说明 |
| 6 | M12 跨模块读（F-12）| **B 改走 M04 Service 接口**——不扩 ADR-003 规则 2（保持"纯读聚合专用"严格边界）；M04 新增 `batch_get_by_nodes` 接口可供 M18 等未来复用；本期数据量下性能差异 <10ms | `M04-feature-archive/00-design.md` §6 新增 `batch_get_by_nodes` 契约；`M12-comparison/00-design.md` §3 Service 草案 + §6 DAO 描述更新 + §9 矩阵渲染改走 Service |

### 决策 1-3 前会话已直接落地说明

决策 1/2/3 在前会话（2026-04-24 早些时候）已按"推荐选项"直接落地，当时未明确 CY ack。本轮重新审视全部 6 条灰区后 CY 确认：**3 条保留前会话做法**（业务影响/维护风险分析支持选 A），**3 条新改动**（决策 4/5/6 本轮补修）。

### 未扩 ADR-003 的说明

决策 6 选 B 而非 A（扩 ADR-003）——避免规则 2 边界模糊（R-X1 严格写 vs 规则 2 宽松读的不对称若扩大会失控）。M12 作为"有主表模块的跨模块读"案例走 Service 接口，与 ADR-003 规则 1 精神一致。未来类似场景（M08 模块关系图查询等）参考 M12 做法，不援引规则 2 豁免。

---

## 8. 关联

- 前置：`design/02-modules/README.md` 末尾 TODO + R10-1/R-X3/R10-2 规则定义
- 前置：`design/adr/ADR-003-cross-module-read-strategy.md` 规则 1/2/3（**决策 6 后保持不扩**）
- batch3 审计：`design/02-modules/audit-report-batch3-verify.md` NI-3（relation/module_relation 重叠，决策中已移除 `relation`）
- batch3 commit：`ff7568c`（规则制定来源）

## 9. 下一轮基线补丁触发条件

README 末尾 TODO 清单内 batch3 相关条目本轮全部消化。后续批次（batch4 及以后）若沉淀新横切规则，参考本轮流程：
1. 前会话出扫描报告（draft）
2. 主对话列"用户场景影响 + 维护坑"展开灰区
3. CY 拍板后集中修 + 更新 M15 schema（R10-2 横切表主）
4. commit 含完整决策记录（不只是"改了什么"，含"为什么这样改"）
