---
title: 第二批 4 模块 fix v2 verify 报告（第三轮 verification-before-completion）
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: 2
verify: true
modules: [M02, M03, M11, M12]
---

# 第二批 4 模块 fix v2 verify 报告

> **审稿立场**：独立、不附和 fix Agent 自报告、每条必须有文件路径+节号引用。
> **参照基线**：README.md 16 字段模板（含 R3-2/R3-4/R4-2/R5-1/R-X2 新规则）+ M04 pilot + audit-report-batch2.md 29 条问题 + CY 8 组决策。
> **方法**：独立读所有文件，对照 29 条问题清单 + G1-G7 逐项验证，不引用 fix Agent 自报告结论。

---

## 1. 执行摘要

Fix v2 在大部分决策落地上做了真实修复，但存在若干**遗漏和新引入问题**，fix Agent 的"全清零"自报告是不准确的。

**核心发现**：

1. **M11 `expires_at` 字段残留 idempotency 语义注释**（medium blocker）：G2/G6 已明确移除 idempotency，但 M11/00-design.md §3 SQLAlchemy class 中 `expires_at` 字段的注释仍写"idempotency 有效期（AI 推断：7 天，同 M17）"，与 G2/G6 决策直接矛盾。
2. **M11/tests.md §7 DAO 覆盖率目标残留"idempotency 查询"描述**（medium blocker）：同样违反 G2/G6 决策，fix Agent 声称 tests.md 全清零但此处遗漏。
3. **M12 §5 "多表事务"仍写"若未来选方案 B"**（high blocker）：G4=B 已 ack，但 §5 4 维表中"多表事务"实现细节仍写"若未来选方案 B（值快照），还需 INSERT comparison_snapshot_items"——设计已在 B 方案上落地（§6 已有 bulk_insert_items），§5 描述未同步，形成内部自洽性矛盾。
4. **M03 §10 activity_log 缺 `move` 事件**（medium blocker）：G5 实现 move_subtree，§7 有 move API，tests.md G8 期望 `activity_log 'move' 一条`，但 §10 activity_log 清单只有 `create/update/delete/reorder` 4 条，无 `move` 事件——design.md vs tests.md 不一致，fix Agent 引入的新问题。
5. **M02 §3 部分唯一索引未出现在 `__table_args__`**（low，已有注释，可接受）：G3 要求 PG 部分唯一索引，设计选择在 Alembic 中用 `op.create_index` 实现而非 `__table_args__`，代码块有注释说明，但 Check 项"§3 是否有 `Index(...postgresql_where=...)` 或等价语法"技术上未满足，因有替代方案注释故降为低优先。

**准入判断矩阵**：

| 模块 | 能/不能转 accepted | 状态 |
|------|-----------------|------|
| M02 | ❌ 不能 | 1 个 low blocker（部分唯一索引语法），整体质量好，修复后可转 |
| M03 | ❌ 不能 | 1 个 medium blocker（activity_log 缺 move 事件） |
| M11 | ❌ 不能 | 2 个 medium blocker（expires_at 注释 + tests.md DAO 覆盖率目标） |
| M12 | ❌ 不能 | 1 个 high blocker（§5 "若未来选方案 B" 内部矛盾） |

---

## 2. 决策落地验证结果（G1-G7 × 4 模块）

### G1 SA Enum 三重防护

**M02 ProjectStatus / MemberRole**：
- ✅ `M02-project/00-design.md` §3 SQLAlchemy class（第 198-199 行）：`status: Mapped[ProjectStatus] = mapped_column(String(20), nullable=False, default=ProjectStatus.active)` —— Python 类型注解 `Mapped[ProjectStatus]` ✅ / SA 列类型 `String(20)` ✅ / `__table_args__` 中 `CheckConstraint("status IN ('active','archived')", name="ck_project_status")` ✅ — 三重齐备。
- ✅ `ProjectMember.role: Mapped[MemberRole] = mapped_column(String(20), ...)` + `CheckConstraint("role IN ('owner','editor','viewer')", name="ck_member_role")` — 三重齐备。
- Alembic 要点（第 284 行）明确：`（G1 三重防护 R3-2 合规：String(20) + CheckConstraint + Mapped[ProjectStatus]）`

**M03 NodeType**：
- ✅ `M03-module-tree/00-design.md` §3 SQLAlchemy class：`type: Mapped[NodeType] = mapped_column(String(20), nullable=False, default=NodeType.folder)` + `CheckConstraint("type IN ('folder','file')", name="ck_node_type")` — 三重齐备。
- 注释第 152 行：`# G1 三重防护：NodeType CheckConstraint（R3-2 合规：String(20)+CheckConstraint+Mapped[NodeType]）`

**M11 ColdStartStatus**：
- ✅ `M11-cold-start/00-design.md` §3（第 144-146 行）：`status: Mapped[ColdStartStatus] = mapped_column(String(20), nullable=False, default=ColdStartStatus.pending)` — Text 已改为 `String(20)` ✅（G6 决策 Q6：原 Text 改为 String(20)）。
- ✅ `CheckConstraint("status IN ('pending','validating','importing','completed','failed')", name="ck_cold_start_status")` — 枚举值列出，**不含 partial_failed** ✅。
- 注释（第 124 行）：`# G1 三重防护：CheckConstraint 枚举值显式列出（R3-2 合规：String(20)+CheckConstraint+Mapped[ColdStartStatus]）`

**M12 ComparisonSnapshot**：
- ✅ `M12-comparison/00-design.md` §3：`ComparisonSnapshot` class 无 `status` 字段（G2 移除，状态最小集）— SQLAlchemy class 中无 `status` 相关代码、无 CheckConstraint 针对 status。
- `__table_args__` 只含两个 Index，无 status CheckConstraint ✅。

**G1 总评**：✅ 4/4 三重防护落地；M11 Text→String(20) 已修；M12 status 字段已彻底移除。

---

### G2 横切（归档不可逆/无 idempotency/状态最小集/activity_log/tenant 冗余）

**M11 UNIQUE(user_id, project_id, source_hash) 约束**：
- ✅ `M11-cold-start/00-design.md` §3 `__table_args__`（第 123-130 行）：仅含 `CheckConstraint` + 两个 `Index`，**无 `UniqueConstraint`** — UNIQUE 约束已删除。
- 注释第 123 行：`# G2/G6 决策：无 idempotency，移除 UNIQUE(user_id, project_id, source_hash)`

**M11 §11 idempotency 章节**：
- ✅ §11 标题"决策（G2/G6）：M11 无 idempotency" — 改为"无幂等"，理由清晰。
- ✅ R11-1 / R11-2 显式声明均在。

**M11 §9 DAO find_idempotent 方法**：
- ✅ §9 DAO class 代码块（第 358-388 行）：只有 `list_by_project` 和 `get_by_id` 两个方法，末尾注释"G2/G6 决策：无 idempotency，find_idempotent 方法已移除" — 方法已删除。

**M11 §13 COLD_START_DUPLICATE ErrorCode**：
- ✅ §13 ErrorCode 清单无 `COLD_START_DUPLICATE`，末尾注释"G2/G6 决策：移除 COLD_START_DUPLICATE（无 idempotency）" — ErrorCode 已移除；AppError 子类也已移除（注释"G2/G6 决策：ColdStartDuplicateError 已移除"）。

**M03 nodes 表 archived 字段**：
- ✅ `M03-module-tree/00-design.md` §3 SQLAlchemy class：Node model 只有 id / project_id / parent_id / name / type / depth / sort_order / path / created_by / updated_by 字段，**无 archived 字段** — G2 状态最小集落地。
- §4 显式声明（第 232-234 行）：`nodes 表无状态字段，G2 决策：状态最小集——M03 nodes 无 archived 字段`。

**M12 快照 status 彻底移除**：
- ✅ `M12-comparison/00-design.md` §3 ComparisonSnapshot class：无 status 字段、无 status CheckConstraint。
- ✅ §7 Pydantic SnapshotResponse：注释"G2/G4 决策：无 status 字段" ✅。
- ✅ §4 显式声明（无状态，R4-1）。
- ✅ §13 ErrorCode 清单无 status 相关 code。

**⚠️ M11 `expires_at` 字段残留 idempotency 注释（新发现，fix Agent 漏改）**：
- ❌ `M11-cold-start/00-design.md` §3 第 154-156 行：
  ```python
  expires_at: Mapped[datetime | None] = mapped_column(
      nullable=True
  )  # idempotency 有效期（AI 推断：7 天，同 M17）
  ```
  G2/G6 已明确移除 idempotency，但 `expires_at` 字段的注释仍保留"idempotency 有效期（AI 推断：7 天，同 M17）"。G2/G6 移除了 UNIQUE 约束、find_idempotent 方法、COLD_START_DUPLICATE ErrorCode，但未处理 `expires_at` 字段本身及其注释。若无 idempotency，`expires_at` 无用途（或需改为"任务清理过期时间"并重新注释）。这是 fix Agent 的漏改项。

**G2 总评**：主要项 ✅，但 M11 `expires_at` 字段注释残留 idempotency 语义（medium blocker，参见 §4 blocker 清单 B2）。

---

### G3 M02 同名禁止

**M02 `__table_args__` 部分唯一索引**：
- ⚠️ `M02-project/00-design.md` §3 `__table_args__`（第 186-193 行）：只含 `CheckConstraint("name != ''", ...)` 和 `CheckConstraint("status IN (...)", ...)`，代码注释第 191-192 行写"G3-a：同 owner 下 active 项目名唯一（PG 部分唯一索引，归档后释放名字）/ 注：PG 部分唯一索引在 Alembic 中用 op.create_index 创建，不在 `__table_args__` 中"。
- Alembic 要点（第 285 行）：`CREATE UNIQUE INDEX uq_project_owner_name_active ON projects(owner_id, name) WHERE status='active'`。
- 判断：设计选择在 Alembic 中实现而非 SQLAlchemy `__table_args__`，有明确注释说明，技术上合理（PG 部分唯一索引 SQLAlchemy ORM 层表达能力有限）。G3 要求"§3 是否有 `Index(...postgresql_where=...)` 或等价语法"——采用了等价的 Alembic 注释方案，认为**条件通过**（low 风险，可接受）。

**PROJECT_NAME_DUPLICATE ErrorCode 保留**：
- ✅ §13（第 627 行）：`PROJECT_NAME_DUPLICATE = "PROJECT_NAME_DUPLICATE"  # G3=B：同 owner 下 active 项目名唯一（部分唯一索引）`
- ✅ `ProjectNameDuplicateError` AppError 子类存在（第 658-661 行）

**tests.md G3 测试用例**：
- ✅ `M02-project/tests.md` §2 边界场景：E8（同 owner 同名 active → 409 `PROJECT_NAME_DUPLICATE`）✅、E9（归档后同名 → 201）✅、E10（不同 owner 同名 → 两者 201）✅
- ✅ §3 并发场景：C3（并发邀请同一用户，G7-M02-R2-01）✅

**G3 总评**：✅ 主体落地完整；部分唯一索引采用 Alembic 方案（有注释说明），条件通过。

---

### G4 M12 快照存值（B）

**ComparisonSnapshotItem 新表**：
- ✅ `M12-comparison/00-design.md` §3：`ComparisonSnapshotItem` class 完整定义（第 149-176 行），含 snapshot_id FK / node_id FK（允许 NULL，节点删除后保留值）/ dimension_type_id FK / content JSONB / snapshot_version 字段。
- ✅ ER 图（第 184-208 行）已更新含 `comparison_snapshot_items`。

**R3-4 候选 B 改回成本块**：
- ✅ §3 决策块（第 88-94 行）：明确写出"候选 B 改回成本（R3-4）"，含 Alembic 迁移步数（2-3 步）/ 新增表数（1 张）/ 受影响模块数（M12 本身）/ 数据迁移不可逆性（高，历史快照值数据永久丢失）。

**§6 Service 层快照保存流程**：
- ✅ §6（第 278-298 行）：`create_snapshot` 方法伪代码完整，含"遍历选中 node×dim 拷贝 content 到 items 表" + `bulk_insert_items` 调用。
- ✅ `§6 节点删除降级策略（G7-M12-R1-14）`（第 301-305 行）：明确写"不降级（无节点删除后快照显示空矩阵逻辑）"。

**§9 ComparisonSnapshotItemDAO**：
- ✅ §9（第 482-505 行）：`ComparisonSnapshotItemDAO` class 新增，含 `bulk_insert_items` + `list_items_by_snapshot`（含 tenant 过滤 JOIN）。

**§10 activity_log `items_count`**：
- ✅ §10（第 526 行）：`snapshot.create` 事件 metadata 含 `items_count`。

**tests.md "保存后原数据改变快照不变"用例**：
- ✅ `M12-comparison/tests.md` §2 E7：`保存后原数据改变，快照内容不变（G4=B 核心场景）` — 步骤明确，期望"items 中 content 仍是保存时的原值" ✅。
- ✅ E8：`node 被删后快照仍展示原值（G4=B 不降级）` ✅。

**⚠️ M12 §5 多表事务"若未来选方案 B"残留（新发现，高风险内部矛盾）**：
- ❌ `M12-comparison/00-design.md` §5 4 维必答"多表事务"列（第 242 行）：
  `"Service 层 with db.begin(): 包：① INSERT comparison_snapshots ② log activity；任一失败回滚。若未来选方案 B（值快照），还需 INSERT comparison_snapshot_items"`
  G4=B 已经是 **当前已定方案**（§1 in scope、§3、§6、§9 全部基于 B），§5 却仍用"若未来选方案 B"的假设性表述。§5 应改为：`INSERT comparison_snapshots + bulk_insert_items + log activity（G4=B 值快照）`。
  这是 fix Agent 未同步更新 §5 导致的内部矛盾（high blocker）。

**G4 总评**：主体大部分落地 ✅，但 §5 多表事务描述有高风险内部矛盾（参见 §4 blocker B1）。

---

### G5 M03 跨父+无限深度

**§7 move API + NodeMove schema**：
- ✅ `M03-module-tree/00-design.md` §7 endpoints 表（第 300 行）：`POST /api/projects/{project_id}/nodes/{node_id}/move` 存在，入参 `NodeMove`，出参 `NodeResponse`。
- ✅ §7 Pydantic schema（第 369-372 行）：`NodeMove` class 含 `new_parent_id: Optional[UUID]`，注释"目标父节点不能是被移动节点的子孙"。

**§6 NodeService.move_subtree + 循环引用检测**：
- ✅ §6 分层职责表 Service 行（第 276 行）：明确写"path 字段计算 / 拖拽排序事务 / 写 activity_log / **对外契约**：`batch_create_in_transaction(db, project_id, nodes_data)` 供 M11/M17 调用"。
- ✅ §8 特殊规则（第 403 行）：`move_subtree（G5）：NodeService.move_subtree(node_id, new_parent_id) 实现见 §3 path 计算策略`。
- ✅ §3 move_subtree 代码块（第 213-222 行）：含 `UPDATE nodes SET path = REPLACE(path, old_prefix, new_prefix) WHERE path LIKE old_prefix || '%'` + 循环引用检查 `target.path NOT LIKE source.path || '%'`。

**§3 path 字段 Text**：
- ✅ `M03-module-tree/00-design.md` §3 Node class（第 171-173 行）：`path: Mapped[str] = mapped_column(Text, nullable=False, default="")  # 物化路径："/rootId/parentId/thisId/"；G5 决策：path 为 Text（无长度限制，支持无限深度树）`。

**§3 batch_create 拓扑排序**：
- ✅ §3 "G5 path 计算策略" 块（第 207-211 行）：`拓扑排序后单阶段处理——先按 parent_id → child 关系排序，确保父节点先入库拿到 id`，明确"拓扑排序先父后子"逻辑。

**§6 delete_node R-X2 流程**：
- ✅ §8 特殊规则（第 397-404 行）：`NodeService.delete_node` 执行顺序明确：先调 M04/M06/M07 delete_by_node_id，最后 `DELETE FROM nodes`（DB CASCADE 兜底），并注明"理由：DB ON DELETE CASCADE 不触发下游 activity_log"（R-X2）。

**§5 4 维无 ⚠️ 占位（R5-1）**：
- ✅ §5 4 维表（第 248-252 行）：多表事务答案"✅ 三处事务（G5）"，有具体实现细节，无 ⚠️。
- ✅ checklist（第 589 行）：`[x] 节 5：4 维必答（多表事务已决策 G5；R5-1 无 ⚠️ 占位）`。

**§4 候选 B 草图已删除**：
- ✅ §4（第 228-242 行）：只有"显式声明（R4-1）：nodes 表无状态字段，type 是不可变类型枚举"和禁止操作清单，**无候选 B 草图** — 已删除（G7-M03-R1-06）。

**⚠️ M03 §10 activity_log 缺 `move` 事件（新引入问题）**：
- ❌ `M03-module-tree/00-design.md` §10（第 470-477 行）：activity_log 清单只有 4 条：`create / update / delete / reorder`，**无 `move` 事件**。
- 但 `M03-module-tree/tests.md` §1 G8（第 29 行）期望"activity_log `move` 一条"，design.md §8（第 403 行）也说"move_subtree：实现见 §3 path 计算策略"（§3 写"Service 记录日志：{moved_nodes_count, elapsed_ms}"）。
- design.md §10 未定义 `move` 事件的 action_type / target_type / metadata，与 tests.md 期望不一致，且 §3 的"Service 记录日志"不是标准 activity_log 格式。这是 fix Agent 新引入的问题（medium blocker）。

**G5 总评**：主体落地 ✅，但 activity_log 缺 move 事件（参见 §4 blocker B3）。

---

### G6 M11 全量回滚+持久化+固定列

**Enum ColdStartStatus partial_failed 移除**：
- ✅ `M11-cold-start/00-design.md` §3 `ColdStartStatus` Enum（第 112-118 行）：只有 `pending / validating / importing / completed / failed`，**无 partial_failed** — 已移除，末尾注释"G6 决策：移除 partial_failed（全量回滚语义下不存在部分失败状态）"。

**CheckConstraint 不含 partial_failed**：
- ✅ §3 `__table_args__` CheckConstraint（第 125-128 行）：`"status IN ('pending','validating','importing','completed','failed')"`，不含 partial_failed ✅。

**activity_log cold_start.partial_failed 删除**：
- ✅ §10（第 403-406 行）：activity_log 清单只有 3 条：`cold_start.create / cold_start.completed / cold_start.failed`，**无 `cold_start.partial_failed`** — 已删除。

**§4 禁止转换 R4-2 格式（独立列）**：
- ✅ `M11-cold-start/00-design.md` §4（第 225-233 行）：4 条禁止转换，格式为"状态A → 状态B：原因 + ErrorCode"，独立列：
  - `completed → 任意 状态` ✅（独立一条）
  - `failed → 任意 状态` ✅（独立一条）
  - `importing → validating（逆向）` ✅
  - `pending → importing（跳过 validating）` ✅
  - 终态数=2，N=3，满足 R4-2 要求（4条 ≥ 3条）✅。

**Pydantic ColdStartStatusEnum partial_failed 移除**：
- ✅ §7 `ColdStartStatusEnum`（第 303-309 行）：只有 `pending / validating / importing / completed / failed`，注释"G6 决策：移除 partial_failed（全量回滚语义）" — partial_failed 已移除。

**G6 总评**：✅ 全部落地。partial_failed 在 Enum、CheckConstraint、Pydantic schema、activity_log 四处均已移除。

---

### G7 机械修复抽样

**M02-R2-01 C3 并发邀请用例**：
- ✅ `M02-project/tests.md` §3 并发场景（第 57 行）：C3"并发邀请同一用户（G7-M02-R2-01）"存在，描述完整：两个 tab 同时 POST 邀请同一 user_id，期望第一个 201，第二个 409 `MEMBER_ALREADY_EXISTS` ✅。

**M03-R1-08 US-C1.1 移除**：
- ✅ `M03-module-tree/00-design.md` §1（第 33 行）：`注：US-C1.1（全景图色块）属于 M10 out-of-scope，M10 消费 M03 数据（G7-M03-R1-08）` — 已改为 out-of-scope 说明 ✅。

**M12-R2-09 nodes_ref str 类型转换说明**：
- ✅ `M12-comparison/00-design.md` §3（第 130-134 行）：注释"G7-M12-R2-09：nodes_ref 存 str(UUID) 而非原生 UUID——理由：...；Service 层做 str↔UUID 转换（get_matrix_data 入参 list[UUID]）" ✅。
- ✅ §9 类型转换说明（第 508-512 行）：明确"Service 层 get_matrix_data() 调用前做转换：`node_ids = [UUID(s) for s in snapshot.nodes_ref]`" ✅。

**M12-R1-13 禁止转换格式**：
- ✅ `M12-comparison/00-design.md` §4（第 226-233 行）：无状态机，R4-2 不适用；改为操作限制 3 条，含 ErrorCode；checklist 第 622 行：`[x] 节 4：状态机（无状态显式声明 G2；操作限制 3 条含 ErrorCode；R4-2 无状态显式）` ✅。

**G7 总评**：抽样 4 项全部 ✅。

---

## 3. 引入新问题（独立发现，不附和"无新问题"）

### NI-1（high）M12 §5 多表事务描述内部矛盾

**文件**：`M12-comparison/00-design.md`，§5（第 242 行）

**现象**：§5 "多表事务"实现细节写"若未来选方案 B（值快照），还需 INSERT comparison_snapshot_items"。但 G4=B 已经是当前决策（§1/§3/§6/§9 全部基于 B 展开），不是"若未来"。§5 的描述停留在 B 尚未决策的状态，与全文其他节矛盾。

**影响**：读者（实现者）看 §5 会误认为 comparison_snapshot_items 的写入是可选或未来扩展，导致实现时遗漏事务内的 bulk_insert_items 步骤。

**修复**：§5 多表事务改为"`Service 层 with db.begin(): 包：① INSERT comparison_snapshots ② 遍历 node×dim bulk INSERT comparison_snapshot_items ③ log activity（G4=B 值快照）；任一失败回滚`"。

---

### NI-2（medium）M11 `expires_at` 字段保留 idempotency 语义注释

**文件**：`M11-cold-start/00-design.md`，§3 SQLAlchemy class（第 154-156 行）

**现象**：
```python
expires_at: Mapped[datetime | None] = mapped_column(
    nullable=True
)  # idempotency 有效期（AI 推断：7 天，同 M17）
```
G2/G6 已移除 idempotency，UNIQUE 约束和 find_idempotent 方法均已删除，但 `expires_at` 字段的注释仍写"idempotency 有效期"。

**影响**：如果 `expires_at` 仅服务于 idempotency，G2/G6 后此字段无用途；如果有其他用途（如任务清理），注释没有说明新用途，造成语义混淆。ER 图（第 179 行）也仍包含此字段。

**修复选项**：
- A：确认 `expires_at` 在 G2/G6 后仍有用途（如 30 天任务清理）→ 更新注释为新用途说明；
- B：无用途 → 从 SQLAlchemy class + ER 图中移除。

---

### NI-3（medium）M03 §10 activity_log 缺 `move` 事件

**文件**：`M03-module-tree/00-design.md`，§10（第 470-477 行）；`M03-module-tree/tests.md`，§1 G8（第 29 行）

**现象**：
- §10 activity_log 清单：`create / update / delete / reorder`（4 条）
- tests.md G8 期望：`activity_log 'move' 一条`
- §3 path 计算策略（第 222 行）写"Service 记录日志：{moved_nodes_count, elapsed_ms}"，但这是性能日志，不是标准 activity_log 格式

设计文档和测试文件关于 `move` 是否写 activity_log、写什么格式存在不一致。

**影响**：实现者不知道 move 操作是否应该写 activity_log，以及写哪种格式的 metadata，会在实现时自行发明。

**修复**：在 §10 添加 `move` 事件行：
```
| `move` | `node` | `<node_id>` | `{project_id, old_parent_id, new_parent_id, old_path, new_path, subtree_count, moved_nodes_count}` |
```
并将 §3 "Service 记录日志" 注释改为明确 activity_log 调用。

---

### NI-4（low）M11/tests.md §7 DAO 覆盖率目标残留"idempotency 查询"

**文件**：`M11-cold-start/tests.md`，§7（第 96 行）

**现象**：`| DAO | ≥ 95% | 含 tenant 过滤每条分支 + idempotency 查询 |`

G2/G6 决策已移除 idempotency，DAO `find_idempotent` 方法已删除，但测试覆盖率目标描述仍写"+ idempotency 查询"，是 fix Agent 的遗漏清理项。

**修复**：删除" + idempotency 查询"，改为"含 tenant 过滤每条分支"。

---

### NI-5（observation，不构成 blocker）M11 §5 并发控制描述残留 idempotency 假设

**文件**：`M11-cold-start/00-design.md`，§5（第 245 行）

**现象**：`"M11 写操作为'导入批次'级别，同一用户在同项目重传同 CSV 走 idempotency 复用；多用户同时导入不同 CSV 互不影响；无乐观锁需求"`

其中"同一用户在同项目重传同 CSV 走 idempotency 复用"与 G2/G6"无 idempotency"矛盾。虽然 §11 已有明确声明"无 idempotency，每次上传都是新任务"，此处属于 §5 描述未同步更新。

**修复建议**：将 §5 并发控制改为"M11 写操作为'导入批次'级别，同一用户重传同 CSV 创建新任务（无 idempotency，G2/G6）；多用户同时导入不同 CSV 互不影响；无乐观锁需求"。

（因 §11 有权威声明，此处属于描述不一致而非决策冲突，降为 observation。）

---

## 4. Blocker 清单

### High（阻塞 accept，必须修）

| # | 模块 | 描述 | 位置 |
|---|------|------|------|
| B1 | M12 | §5 多表事务"若未来选方案 B"内部矛盾——G4=B 已定，§5 仍用假设性表述，实现时可能遗漏 bulk_insert_items 步骤 | `M12-comparison/00-design.md` §5 第 242 行 |

### Medium（阻塞 accept，必须修）

| # | 模块 | 描述 | 位置 |
|---|------|------|------|
| B2 | M11 | `expires_at` 字段注释残留"idempotency 有效期"，与 G2/G6 矛盾；字段用途不明 | `M11-cold-start/00-design.md` §3 第 154-156 行 |
| B3 | M03 | §10 activity_log 缺 `move` 事件，tests.md G8 期望 `activity_log 'move' 一条`，内部不一致 | `M03-module-tree/00-design.md` §10；`M03-module-tree/tests.md` §1 G8 |
| B4 | M11 | tests.md §7 DAO 覆盖率目标写"含 idempotency 查询"，G2/G6 已移除 idempotency | `M11-cold-start/tests.md` §7 第 96 行 |

### Low（不阻塞 accept，建议修）

| # | 模块 | 描述 | 位置 |
|---|------|------|------|
| B5 | M11 | §5 并发控制描述"同一用户在同项目重传同 CSV 走 idempotency 复用"与 §11 无 idempotency 不一致（观察性） | `M11-cold-start/00-design.md` §5 第 245 行 |
| B6 | M02 | §3 部分唯一索引未在 `__table_args__` 中使用 `Index(...postgresql_where=...)` 语法，仅在 Alembic 注释；有代码注释说明，接受此方案 | `M02-project/00-design.md` §3 第 191-192 行 |

**Blocker 汇总**：1 high / 4 medium / 2 low（共 7 个）

---

## 5. Suggestion 清单（不阻塞，优化建议）

| # | 模块 | 建议 |
|---|------|------|
| S1 | M03 | §3 "Service 记录日志" 注释（第 222 行）措辞为"Service 记录日志：{moved_nodes_count, elapsed_ms}"，建议改为明确"Service 在 activity_log 记录 move 事件 + 性能指标"，与 §10 对应 |
| S2 | M11 | §3 ER 图（第 179 行）仍含 `expires_at` 字段，若 B5 决定移除字段，ER 图同步更新 |
| S3 | M12 | §5 状态转换竞态分析（第 256-261 行）第 4 条"读-删竞态"描述"G4=B 模式降级策略：由于快照是值快照，节点删除不影响已保存快照的显示——快照仍展示原值（节 6 实现说明）"——这段"降级策略"用词与 §6 "不降级"措辞不一致，建议改为"G4=B 不降级——节点删除后快照仍展示原值副本" |
| S4 | M02 | §3 `ai_api_key_enc` 字段 String(1000) 注释"AES-256-GCM 加密后 base64"，建议在 Alembic 要点中补充此字段长度选择理由（AES-GCM 加密膨胀系数，防止实现者随意改小）|
| S5 | M11/M12 | 两个模块 §10 activity_log 表都比 M03/M02 多了 `summary` 列（5 列），而 M02/M03 是 4 列（无 summary）。建议统一为 5 列或在 README 说明 summary 列可选 |

---

## 6. Fix Agent 是否如实报告

**结论：部分真实，存在漏改（非完全撒谎）**

Fix Agent 声称"业务 ⚠️ 清零（4 tests.md 全 0，4 design.md 仅元引用）"——经 grep 验证：
- tests.md ⚠️ 真实清零 ✅（4 个 tests.md 无业务 ⚠️）
- design.md 的业务 ⚠️ 清零 ✅（4 个 design.md 无业务 ⚠️）

Fix Agent 声称"G1-G7 全覆盖，无保留疑点"——存在以下误报：
- ❌ M11 `expires_at` 注释未处理（G2 漏改，NI-2）
- ❌ M11 tests.md §7 DAO 覆盖率目标残留 idempotency 描述（NI-4）
- ❌ M12 §5 多表事务"若未来选方案 B"未同步（NI-1，G4 落地不完整）
- ❌ M03 §10 缺 move activity_log（新引入问题，NI-3）

Fix Agent 声称"无引入新业务决策"——属实，发现的问题均是描述不一致或漏清理，无新业务决策。

**Fix Agent 自报告等级**：**漏改**（非撒谎）——大部分工作是真实完成的，但存在 4 处遗漏/残留，主要集中于：一是 idempotency 相关清理不彻底（M11 两处），二是 M12 §5 描述更新遗漏，三是 M03 新增 API 未同步 §10。

---

## 7. 每模块准入判断

### M02 项目管理

**能/不能转 accepted**：❌ 不能（1 个 low blocker）

**需补什么**：
1. **B6（low，推荐修）**：评估是否在 §3 `__table_args__` 补 `Index("uq_project_owner_name_active", "owner_id", "name", unique=True, postgresql_where=text("status='active'"))` — 如果 CY 确认 Alembic 注释方案可接受，可降为 suggestion 并转 accepted。

**整体质量**：**优良**——G1/G2/G3 全部落地，tests.md 29 条问题中 M02 相关的 4 条（R2-01/R2-02/R2-03/R3）均已修复（C3 并发邀请 ✅、ER2b 多步事务回滚 ✅、C4 AI Key 并发说明 ✅）。如果 B6 确认可接受，M02 质量可转 accepted。

---

### M03 功能模块树

**能/不能转 accepted**：❌ 不能（1 个 medium blocker）

**需补什么**：
1. **B3（medium，必修）**：§10 activity_log 添加 `move` 事件（action_type=move / target_type=node / target_id=node_id / metadata={project_id, old_parent_id, new_parent_id, old_path, new_path, subtree_count}），并将 §3 "Service 记录日志" 改为明确 activity_log 调用。

**整体质量**：**良好**——G2/G5 全部落地，R-X2 delete_node 流程 ✅，move_subtree ✅，batch_create 拓扑排序 ✅，§4 无状态显式 ✅，§5 无 ⚠️ 占位 ✅，29 条问题中 M03 相关的 5 条已修复 4 条（M03-R1-05/R1-06/R1-07/R1-08），仅 B3 是 fix Agent 新引入。修复 B3 后可转 accepted。

---

### M11 冷启动支持

**能/不能转 accepted**：❌ 不能（2 个 medium blocker）

**需补什么**：
1. **B2（medium，必修）**：处理 `expires_at` 字段注释（决策 A：改注释为新用途 / 决策 B：移除字段）。
2. **B4（medium，必修）**：tests.md §7 DAO 覆盖率目标删除"+ idempotency 查询"。
3. **B5（low，建议修）**：§5 并发控制描述改为无 idempotency 语义。

**整体质量**：**良好**——G1/G2/G6 全部核心落地，partial_failed 全链路移除 ✅，String(20) 改对 ✅，UNIQUE 约束和 find_idempotent 已删 ✅，四条禁止转换 R4-2 格式正确 ✅。仅剩清理类问题，修复后可转 accepted。

---

### M12 对比矩阵

**能/不能转 accepted**：❌ 不能（1 个 high blocker）

**需补什么**：
1. **B1（high，必修）**：§5 多表事务实现细节改为 G4=B 当前状态描述（三步事务：INSERT snapshots + bulk_insert_items + log activity）。
2. **S3（suggestion，建议修）**：§5 竞态分析"降级策略"措辞改为"不降级"，与 §6 对齐。

**整体质量**：**良好**——G2/G4 主体落地完整，ComparisonSnapshotItem 新表 ✅，R3-4 改回成本块 ✅，§6 Service 流程 ✅，DAO 新增 ✅，activity_log items_count ✅，tests.md E7/E8 ✅。仅 §5 描述一处遗漏，修复后质量可达 accepted 门槛。

---

## 关联参考

- 模板基线：`/root/cy/prism-0420/design/02-modules/README.md`
- 第二批 audit：`/root/cy/prism-0420/design/02-modules/audit-report-batch2.md`
- 第一批 verify 范本：`/root/cy/prism-0420/design/02-modules/audit-report-batch1-verify.md`
- M02：`/root/cy/prism-0420/design/02-modules/M02-project/`
- M03：`/root/cy/prism-0420/design/02-modules/M03-module-tree/`
- M11：`/root/cy/prism-0420/design/02-modules/M11-cold-start/`
- M12：`/root/cy/prism-0420/design/02-modules/M12-comparison/`
