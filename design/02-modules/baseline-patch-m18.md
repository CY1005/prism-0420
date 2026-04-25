---
title: M18 基线补丁：M02 RRF 参数 / M09 superseded / M03/M04/M06/M07 embedding 接口 / M15 ActionType / ADR-003 规则 4 / R10-2 文字修订
status: draft
owner: CY
created: 2026-04-25
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: baseline-patch-m18
modules_affected: [M02, M03, M04, M06, M07, M09, M15]
adrs_affected: [ADR-003]
readme_affected: [§10 R10-2 例外文字]
trigger: M18 brainstorming Q0-Q11 决策落地
---

# M18 基线补丁报告

## 0. 执行摘要

| 维度 | 数量 |
|------|------|
| 受影响业务模块 | 6（M02 / M03 / M04 / M06 / M07 / M15） |
| 受影响文档模块 | 1（M09 status superseded） |
| 受影响 ADR | 1（ADR-003 扩规则 4） |
| 受影响 README 规则 | 1（R10-2 例外条件 3 文字修订） |
| 新增 Service 接口数 | 8（4 模块 × `get_for_embedding` + `embedding_service.delete_by_target` 调用接入） |
| 新增 schema 字段数 | 2（M02 ProjectSettings.rrf_k + similarity_threshold） |
| 新增 ActionType 枚举 | 2（EMBEDDING_MODEL_UPGRADE_TRIGGERED + EMBEDDING_BACKFILL_TRIGGERED） |
| Alembic 迁移步数 | 3（M02 加 2 列 / M15 ActionType CHECK 扩 / embeddings + embedding_failures + embedding_tasks 三表） |

## 1. 触发来源

CY 2026-04-25 brainstorming 12 决策：
- Q6=C 项目级 RRF 参数化 → M02 ProjectSettings 扩字段
- Q11=A M18 升级 superseded M09 → M09 status 改 + 文档归档说明
- Q10=D 增量走规则 1 + backfill 走规则 4 → M03/M04/M06/M07 加 `get_for_embedding` 接口 + ADR-003 扩规则 4
- Q1=D 增量触发链 → M03/M04/M06/M07 在 create/update Service 内尾调 `embedding_service.enqueue`
- 删除一致性（R-X2/R-X3）→ M03/M04/M06/M07 在 delete_by_id 内尾调 `embedding_service.delete_by_target`，共享外部 session
- Q7=C R10-2 例外条件 3 文字修订 → README §10 R10-2 改 1 行
- §10 写 backfill/model_upgrade 触发事件 → M15 ActionType 扩 2 枚举

## 2. 每模块/文档改动详情

---

### M02 项目管理（schema 扩字段）

**改动类型**：High（schema 迁移）

**现状**：M02 ProjectSettings 无 RRF 参数（M02 已 accepted 2026-04-21）

**M18 需求**：search 路由按 project 取 `rrf_k` + `similarity_threshold`，让 CY 在不同 project 调优搜索质量

**改动**：

```python
# api/models/projects.py（M02 own）
class ProjectSettings(Base, TimestampMixin):
    # ... existing fields

    # M18 baseline-patch（2026-04-25）
    rrf_k: Mapped[int] = mapped_column(default=60, nullable=False)
    similarity_threshold: Mapped[float] = mapped_column(default=0.3, nullable=False)

    __table_args__ = (
        # ... existing
        CheckConstraint("rrf_k > 0 AND rrf_k <= 200", name="ck_project_settings_rrf_k_range"),
        CheckConstraint(
            "similarity_threshold >= 0.0 AND similarity_threshold <= 1.0",
            name="ck_project_settings_threshold_range",
        ),
    )
```

**新增 Service 接口**：

```python
# api/services/projects.py
class ProjectService:
    def get_search_config(self, db: Session, project_id: UUID) -> SearchConfig:
        """M18 search 路由调，返回 (rrf_k, similarity_threshold) 元组对象"""
        settings = self.dao.get_settings(db, project_id)
        return SearchConfig(rrf_k=settings.rrf_k, similarity_threshold=settings.similarity_threshold)
```

**Alembic 迁移**（1 步）：
- ALTER TABLE project_settings ADD COLUMN rrf_k INT NOT NULL DEFAULT 60
- ALTER TABLE project_settings ADD COLUMN similarity_threshold REAL NOT NULL DEFAULT 0.3
- ADD CONSTRAINT ck_project_settings_rrf_k_range CHECK ...
- ADD CONSTRAINT ck_project_settings_threshold_range CHECK ...

**M02 文档更新**：M02 §3 schema 块 + §6 Service 表 + §7 API 契约（可选：扩 ProjectSettings 编辑端点入参）+ §15 标 "M18 baseline-patch 引入"

**回归风险**：低——纯加字段带默认值，已有数据不受影响

---

### M03 nodes（新增 2 接口 + 删除调链）

**改动类型**：High（新接口 + 删除一致性）

**现状**：M03 已 accepted。已有 `search_by_keyword`（batch3 沉淀）。`delete_node` 已接受外部 session（R-X3 batch3 已修）。

**M18 需求**：
1. 增量 worker 走 ADR-003 规则 1 调 `get_for_embedding(target_id, project_id) -> str | None`
2. node 删除时同步删 embeddings（避免 embeddings 表孤儿数据 + 无效召回）

**改动 1：新增 `get_for_embedding` Service 接口**

```python
# api/services/nodes.py
class NodeService:
    def get_for_embedding(self, db: Session, node_id: UUID, project_id: UUID) -> str | None:
        """
        M18 embedding worker 调用——返回该 node 用于 embedding 计算的拼接文本。
        返回 None 表示节点已删除（worker 跳过 noop，不算失败）。

        拼接策略（M18 ack）：name + description（如果有）。后续若需更多字段再扩。
        """
        node = self.dao.get_by_id(db, node_id, project_id)
        if node is None:
            return None
        parts = [node.name]
        if node.description:
            parts.append(node.description)
        return "\n".join(parts)
```

**改动 2：delete_node 内尾调 embedding 清理**

```python
# api/services/nodes.py
class NodeService:
    def delete_node(self, db: Session, node_id: UUID, project_id: UUID) -> None:
        with db.begin():
            # ... 原有：删 M04/M06/M07/M08 关联（已 R-X3 共享 session）
            self.dao.delete_by_id(db, node_id, project_id)

            # M18 baseline-patch：删 embeddings
            self.embedding_service.delete_by_target(
                db, target_type="node", target_id=node_id, project_id=project_id
            )

            # ... 原有：写 activity_log
```

**改动 3：create_node / update_node 触发增量 enqueue**

```python
# api/services/nodes.py
class NodeService:
    def create_node(self, db, ...):
        with db.begin():
            node = self.dao.create(...)
            # ... activity_log
        # commit 后 enqueue（不进事务——enqueue 失败不该回滚业务写入）
        self.embedding_service.enqueue(
            project_id=node.project_id,
            target_type="node",
            target_id=node.id,
            user_id=current_user.id,
            enqueued_by="incremental",
        )
        return node

    def update_node(self, db, node_id, project_id, **fields):
        # 同 create——若 fields 中含 name/description（影响 embedding 内容），enqueue
        with db.begin():
            node = self.dao.update(...)
            # ... activity_log
        if "name" in fields or "description" in fields:
            self.embedding_service.enqueue(...)
        return node
```

**M03 文档更新**：§6 Service 表加 `get_for_embedding` 行 / §3 schema 不变 / §10 不变（embedding 不写 activity_log）

**回归风险**：中——delete_node 多调一个 Service，要测"embedding_service 失败时是否拖累节点删除"（建议：embedding_service.delete_by_target 失败仅日志不抛，不阻塞主事务）

---

### M04 dimension_records（同 M03 模式）

**改动类型**：High

**现状**：M04 已 accepted。pilot 1 范本，已被多次 baseline-patch（M13 + M16）

**改动**：与 M03 同模式（3 处改动 + 同种回归测试）

**新增接口**：

```python
# api/services/dimensions.py
class DimensionService:
    def get_for_embedding(
        self, db: Session, record_id: UUID, project_id: UUID
    ) -> str | None:
        """拼接 content JSONB 内可搜索字段（M18 + M04 商定）"""
        record = self.dao.get_by_id(db, record_id, project_id)
        if record is None:
            return None
        # JSONB content 是动态结构——M18 仅取 string 类型字段
        # 例如：{"summary": "...", "details": "..."} → 拼接 summary + details
        # 数组 / 嵌套对象 / 数字 / boolean 跳过
        parts = []
        for key, value in (record.content or {}).items():
            if isinstance(value, str) and value.strip():
                parts.append(f"{key}: {value}")
        return "\n".join(parts) if parts else None
```

**delete + create/update 调链**：同 M03

**M04 特殊点**：M04 的 `create_dimension_record` 已被 M13 + M16 baseline-patch 多次扩展，本次再扩 enqueue 调用要确保不破坏 M13/M16 已用契约——建议：enqueue 调用放在 Service 末尾，不影响返回值。

**回归风险**：中（多 patch 叠加，要 verify 三个 baseline-patch 共存无冲突）

---

### M06 competitors / M07 issues（同 M03 模式，简）

**改动类型**：High

**改动**：与 M03 同模式（`get_for_embedding` + delete 调链 + create/update enqueue）

**M06 拼接**：name + description + url（如果 url 文本化有价值——可能不要，audit 时定）
**M07 拼接**：title + description

**回归风险**：低（M06/M07 schema 简单，未叠加多 patch）

---

### M09 全局搜索（status 改 superseded）

**改动类型**：Medium（文档 status + 路由迁移）

**现状**：M09 已 accepted 2026-04-21

**改动**：
1. M09/00-design.md frontmatter 改：`status: superseded`，`superseded_by: M18`，`last_reviewed_at: 2026-04-25`
2. M09/00-design.md 头部加一段说明：
   ```markdown
   > **M09 已被 M18 升级取代（2026-04-25）**
   >
   > - PRD F18 明确"升级 F9 不并存"
   > - M18 接管 `/api/projects/{pid}/search` 路由
   > - M09 batch3 沉淀的 `search_by_keyword` 接口体系**保留**——M18 增量路径继续复用
   > - 本文档归档作历史，新功能见 [`M18-semantic-search/00-design.md`](../M18-semantic-search/00-design.md)
   ```
3. design/02-modules/README.md 模块清单 M09 行加 "(superseded by M18)" 标注

**实施代码影响**：Phase 2 写代码时 `api/routers/search.py` 由 M18 own，M09 不再单独存在路由文件（合并到 M18）

**回归风险**：无（仅文档 status，无 schema 改动）

---

### M15 数据流转（ActionType 枚举扩 2）

**改动类型**：Medium（枚举 + Alembic）

**现状**：M15 own activity_log schema + ActionType / TargetType 枚举（R10-2 主规则）

**改动**：

```python
# api/models/activity_log.py（M15 own）
class ActionType(str, Enum):
    # ... existing
    EMBEDDING_MODEL_UPGRADE_TRIGGERED = "embedding_model_upgrade_triggered"
    EMBEDDING_BACKFILL_TRIGGERED = "embedding_backfill_triggered"

# TargetType 不需扩——复用 'project'
```

**Alembic 迁移**（1 步）：
- ALTER CONSTRAINT ck_activity_log_action_type CHECK 增加 2 个枚举值
- 与 M16 已积压的 ActionType +3 + TargetType +1（README 标注 Phase 2 一并迁移）合并执行

**M15 文档更新**：§3 ActionType 枚举表加 2 行（注明 source: M18 baseline-patch 2026-04-25）

**回归风险**：无（枚举扩 CHECK 兼容已有数据）

---

### ADR-003 跨模块读取策略（扩规则 4）

**改动类型**：High（ADR 修订）

**现状**：ADR-003 accepted 2026-04-21，3 条规则（规则 1 主 + 规则 2 聚合计算 + 规则 3 横切表）

**M18 需求**：embedding backfill 批量场景规则 1（5 万次 Service 调用）性能不可行，规则 2（DB 聚合计算）语义不匹配（embedding 不是聚合而是派生），需新规则 4

**改动**：在 ADR-003 §Decision 加规则 4

```markdown
#### 规则 4：embedding/索引派生模块的批量 backfill 豁免

适用条件（必须全部满足）：
- 模块定位是"为业务表生成派生索引数据"（embedding / 全文索引 / 物化统计），而非"展示业务内容"
- 单条增量必须走规则 1（保持分层），但批量回填的性能要求使规则 1 不可行
  （示例：5 万条调 5 万次上游 Service 接口，本项目场景下 ≥ 1 小时不可接受）
- 仅做**只读 SELECT**（含 LEFT JOIN），禁止 UPDATE / DELETE

豁免内容：
- backfill DAO 可以 `from api.models.xxx import Xxx` 只读 import 上游 SQLAlchemy model
- 跑 LEFT JOIN 自有表（embeddings 等）+ WHERE project_id 等批量 SELECT
- 严禁在豁免 DAO 中执行 INSERT / UPDATE / DELETE 上游表

与规则 2 的边界：
- 规则 2 = "DB 层聚合计算"（M10 完善度统计，使用 GROUP BY / aggregate 函数）
- 规则 4 = "派生索引批量构建"（M18 backfill，使用 LEFT JOIN 找差异）
- 两者不重叠，避免规则 2 边界稀释

文档要求：
- 采用规则 4 的模块 §3 必须显式声明"适用 ADR-003 规则 4：embedding/索引专用豁免"
- 列出所有只读 import 的上游 model 清单
- §6 分层职责表必须把"增量 DAO（规则 1）"和"backfill DAO（规则 4）"分文件
```

**ADR-003 §Consequences 加**：
- 正面：M18 backfill 性能可控（10min 完成 5 万条 vs 规则 1 的 1h+）
- 负面：模块需维护两套 DAO（增量 vs backfill）
- 演进退路：未来若派生索引模块超过 3 个 → 抽公共 backfill 框架

**ADR-003 §引用方加**：M18 规则 4 backfill DAO

**回归风险**：低（仅扩条款，原 3 条规则不变）

---

### README §10 R10-2 例外条件 3 文字修订

**改动类型**：Low（1 行文字调整）

**现状**：README §10 R10-2 例外条件 3 写"事件无 `project_id` 归属（系统级 / 跨项目事件）"

**M18 challenge**：embedding_failures 有 project_id（用于按 project 监控）但事件本身是系统级（worker 后台触发，用户无感）

**改动**：

```markdown
# 修改前
3. 事件无 `project_id` 归属（系统级 / 跨项目事件）

# 修改后
3. 事件为系统级（用户无主动操作语义）—— 是否带 project_id 仅为索引/分析需要，不影响判定
```

**M01 兼容性验证**：M01 auth_audit_log 仍满足新表述（auth 事件确实是系统级，无论是否带 project_id）

**回归风险**：无（M01 是唯一已采用此例外的模块，新表述向下兼容）

---

## 3. 实施顺序建议

依赖关系决定的顺序：

1. **先扩 ADR-003 规则 4**（M18 §3 + §9 都引用，Reviewer audit 阻塞项）
2. **改 README R10-2 文字**（M18 §10 引用，audit 阻塞项）
3. **M02 加 RRF 字段**（M18 §6 search.py 调用 get_search_config，audit 阻塞项）
4. **M03/M04/M06/M07 加 `get_for_embedding`** + delete 调链 + create/update enqueue（M18 §6 + §9 引用）
5. **M15 ActionType 扩 2**（合并到 Phase 2 Alembic 集中迁移，与 M16 已积压的 +3 一起）
6. **M09 status superseded**（仅文档，最后做）

**Phase 1 阶段（设计文档）**：1+2+6 必须做（影响 M18 audit 通过）；3+4+5 可与 M18 audit 并行（Phase 2 写代码前必须 ack）

**Phase 2 阶段（写代码）**：3+4+5 必须先于 M18 实施代码

## 4. CY 决策项

- [ ] **决策 1**：ADR-003 规则 4 文字是否需要进一步收紧？（如规定"仅 backfill 路径，所有其他场景仍走规则 1"——已写入草案，确认即可）
- [ ] **决策 2**：M02 ProjectSettings 加 RRF 参数后，UI 是否暴露给非管理员？（建议：仅 admin 改，viewer 看不到——与 M02 现有权限模型一致）
- [ ] **决策 3**：M04 dimension_records.content JSONB 拼接策略——是否扩展为"所有 string 字段"还是"仅显式标注 embeddable 的字段"？（草案选前者，简单；后者需 M04 schema 加白名单字段）
- [ ] **决策 4**：M06 competitors 的 url 字段是否参与 embedding？（建议否——url 文本对语义召回价值低，可能产生噪音）
- [ ] **决策 5**：embedding_service.delete_by_target 失败时是否阻塞业务删除？（建议否——仅日志，留给 M18 zombie cron 兜底清理孤儿 embedding）

## 5. 关联文档

- M18 主设计：[`M18-semantic-search/00-design.md`](./M18-semantic-search/00-design.md)
- 本批次触发来源：CY 2026-04-25 brainstorming Q0-Q11
- 前置 baseline-patch：[`baseline-patch-batch3.md`](./baseline-patch-batch3.md)（M02/M03/M04/M06/M07 上一轮改动基线）
- ADR：[`adr/ADR-003-cross-module-read-strategy.md`](../adr/ADR-003-cross-module-read-strategy.md) 待扩规则 4
- README：[`README.md`](./README.md) §10 R10-2 例外文字修订 + §12 表 §12D 行已加
