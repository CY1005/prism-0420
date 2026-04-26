# ADR-005：团队扩展（M20 引入团队作为 project 容器）

- **状态**：accepted
- **日期**：2026-04-26
- **决策者**：CY
- **supersedes**：[ADR-001 §预设 3 整段] —— 涵盖三件实质变更：① 命名 `space_id → team_id`；② 类型 `INT NULL → UUID NULL`（对齐 PRD F20 + Prism 实跑）；③ 启用 FK（原"无 FK 预留口"放弃，正式 `ondelete=RESTRICT`）。supersede 范围**不仅"命名"**，决策对照表与 Consequences §中性段同步精确化。
- **superseded_by**：null

---

## Context（背景）

- M01-M19 全部 accepted（M09 superseded by M18）；M20「团队/空间」是 Phase 1 收官最后一块
- ADR-001 §预设 3 原文「所有 project 相关表预留 `space_id INT NULL` 字段，本期不建 spaces 表，不加 FK」
- PRD F20（`/root/prism/docs/product/PRD.md §5.5`）AC1-AC3：
  - AC1：创建团队后可将项目归入团队
  - AC2：现有个人项目可一键迁移到团队
  - AC3：团队成员可查看项目（复用 F1 权限模型）
  - 设计决策原文：「团队化做最小实现——分组+权限复用 F1。不做评论、通知、协作编辑等重协作功能」
- Prism 实跑 schema（`/root/prism/api/models/tables.py:354-376`）：teams + team_members(role default "member") + users.team_id（用户主属团队）
- 三概念张力：PRD 用「团队」/ ADR-001+M02 用「space_id」/ Prism 实跑用 team + users.team_id 维度
- M20 brainstorming 2026-04-26 收敛 Q0-Q15 共 16 个决策点

---

## Decision（决策）

**核心定位**：M20 引入 **team** 作为 project 的容器（人的集合 + 分组标签），对齐 PRD F20 与 Prism 实跑命名；team 仅作分组，**不升级 tenant 锚点**（仍 project_id 单 tenant）；权限走 **嵌套式叠加**（team baseline + ProjectMember 提权，取并集 max）；删 team **强制前置迁出**（不级联）；移成员 **软切断**（不级联清 ProjectMember）；跨 team **不允许直跳**（必须先回个人）。

### Q0-Q15 决策对照表（核心决策矩阵）

| # | 决策点 | 选项 | 关键衍生 |
|---|--------|------|---------|
| **Q0** | 核心概念取舍 | **B 纯 Team** | M02 baseline-patch：space_id → team_id（仍 nullable + index + 无 FK） |
| **Q1** | Team 与 ProjectMember 衔接 | **B 嵌套式（baseline + 叠加提权）** | 权限解析 `max(team_role_mapped, project_member_role)` 落 Service 层 |
| **Q2** | Team role → Project role 映射 | **B 三角色 owner/admin/member → owner/editor/viewer** | team_members.role 三重防护 + team 必至少 1 owner 守护 |
| **Q3** | 删 team_member 是否级联清 ProjectMember | **A 软切断（保留 ProjectMember）** | API 响应附残留 ProjectMember 数量与列表，前端做提醒（非强制） |
| **Q4** | Tenant 隔离边界 | **A project_id 单 tenant，team 仅分组标签** | M03-M19 衍生表 schema 完全不动，零 schema baseline-patch |
| **Q5** | Space-level access check 落层 | **A L1 粗 + L2 精 + L3 SQL 兜底（三层全做）** | L3 SQL 自动注入 `WHERE project_id IN user_accessible_project_ids`（M03-M19 query 层升级） |
| **Q6** | §12 异步形态 | **A 纯同步 CRUD** | 无 Worker / Queue / SSE，AC2 一键迁移走前端循环 |
| **Q7** | 跨 team 操作边界 | **A 仅个人 ↔ team，不支持 team A ↔ team B 直跳** | API 拒 422 `CROSS_TEAM_MOVE_FORBIDDEN`；强制两步操作 |
| **Q8** | 删 team 时 project 处置 | **B 强制前置迁出（projects.team_id 必须为空）** | 422 `TEAM_HAS_PROJECTS`；UX 风险登记，未来视痛点决定批量 API |
| **Q9** | 乐观锁 version 字段 | **A teams 加 / team_members 不加** | 与 M02 projects/project_members 范式 1:1 对齐 |
| **Q10** | activity_log 事件粒度 | **B 细粒度 10+ 事件** | M15 action_type CHECK 扩 10 个枚举 |
| **Q10.1①** | 转让 owner 事件数 | **B 2 条（demoted + promoted）** | 同事务原子写入，审计需关联 actor + timestamp |
| **Q10.1②** | team 改字段事件 | **B 拆分（team_renamed / team_description_changed）** | 未来加字段需加新事件类型 |
| **Q10.1③** | 删 team 是否级联写 N 条 member_removed | **B 写 1 条 team_deleted + N 条 team_member_removed(reason="team_deleted")** | 同事务 N+1 条事件原子写 |
| **Q11** | Auth 横切路径 | **A 全部 P1+P2（require_user 合并入口，对齐 ADR-004 §79）** | 不涉及 P3/P4，token_invalidated_at 不扩展 |
| **Q12** | ErrorCode 粒度 | **A 粗粒度 8 个**（细粒度场景靠 detail 补） | 与 M02 范式 1:1 对齐 |
| **Q13** | teams 表 owner_id 设计 | **C creator_id（创建者只读，不随 transfer 变）** | 当前 owner 由 team_members.role='owner' 单独查询 |
| **Q13.1①** | team name 唯一约束 | **A 同 creator 下唯一** | UI 显示 team name 附 creator 名缓解 transfer 后语义偏 |
| **Q13.1②** | team_members FK CASCADE/RESTRICT | **B RESTRICT** | Service 层显式 5 步删 team 流程，DB 层 RESTRICT 兜底 |
| **Q13.1③** | teams 通用字段 | **A 完全照搬 M02 范式** | id UUID / creator_id / name String(100) / description Text / version / created_at / updated_at |
| **Q13.2** | Service 跨事务签名（删 team / transfer owner） | **A 接受外部 `db: Session`（R-X3）** | M20 §8.7 给 `delete_team(self, db, ...)` / `transfer_ownership(self, db, ...)` 签名草案；Router 持 commit/rollback 权；写 activity_log 复用同一 db |
| **Q14** | 模块依赖声明 | **C 标准依赖 + ADR-005 承担横切影响清单** | requires=[M01,M02,M15] / extends=[M02,M15]，横切影响入本 ADR §3 |
| **Q15** | Out of scope 清单 | **A 完整 15 项** | 按 6 组分类显式列出，防 AI 自由发挥 |

---

## §3 baseline-patch 完整影响清单

### 3.1 直接 baseline-patch（schema / 文档级）

#### M02 项目管理（schema 字段重命名）

**改动类型**：High（schema 迁移 + 命名语义）

**现状**：M02 `projects.space_id: Mapped[PyUUID | None]`（ADR-001 §预设 3 预留口）

**改动**：
```python
# api/models/projects.py（M02 own）
class Project(Base):
    # ... existing
    # M20 baseline-patch（2026-04-26）：space_id 重命名 team_id（语义对齐 PRD F20 + Prism 实跑）
    team_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="RESTRICT"),
        nullable=True, index=True
    )
```

**说明**：
- 原 ADR-001 §预设 3「无 FK」放弃 —— M20 引入 teams 表后 FK 启用
- ondelete=RESTRICT 与 Q8「强制前置迁出」一致（删 team 前 project 必须先解绑）
- nullable=True 保留个人 project 语义（team_id IS NULL = 不属于任何团队）

**Alembic 迁移**（2 步）：
1. `ALTER TABLE projects RENAME COLUMN space_id TO team_id`
2. `ALTER TABLE projects ADD CONSTRAINT fk_projects_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT`

**M02 文档更新**：§3 schema 块（字段重命名 + 加 FK 注释）/ §1 out of scope 表第 5 行更新文案 / §15 标「M20 baseline-patch 引入」

**回归风险**：低 —— Phase 1 设计阶段无生产数据；Phase 2 实施时纯字段改名

---

#### M15 数据流转（ActionType 枚举扩 10 + ErrorCode 注册 8）

**改动类型**：Medium（枚举扩 + Alembic CHECK 升级）

**现状**：M15 own activity_log + ActionType / TargetType 枚举（R10-2 主规则）

**改动 1：ActionType 扩 10 个枚举**（Q10.1 全 B 决策）：
```python
# api/models/activity_log.py（M15 own）
class ActionType(str, Enum):
    # ... existing
    # M20 baseline-patch（2026-04-26）
    TEAM_CREATED = "team_created"
    TEAM_RENAMED = "team_renamed"
    TEAM_DESCRIPTION_CHANGED = "team_description_changed"
    TEAM_DELETED = "team_deleted"
    TEAM_MEMBER_ADDED = "team_member_added"
    TEAM_MEMBER_REMOVED = "team_member_removed"           # detail.reason: "manual" | "team_deleted"
    TEAM_MEMBER_PROMOTED_ADMIN = "team_member_promoted_admin"   # detail.to_role: "admin" | "owner"（含 transfer 中升 owner）
    TEAM_MEMBER_DEMOTED_MEMBER = "team_member_demoted_member"   # detail.to_role: "member" | "admin"（含 transfer 中降 admin）
    PROJECT_JOINED_TEAM = "project_joined_team"
    PROJECT_LEFT_TEAM = "project_left_team"
```

**改动 2：TargetType 扩 1 个**：
```python
class TargetType(str, Enum):
    # ... existing
    TEAM = "team"  # M20 baseline-patch
```

**改动 3：ErrorCode 表扩 8 个**（Q12 粗粒度决策）：
```
TEAM_NOT_FOUND                    # 404
TEAM_NAME_DUPLICATE               # 409
TEAM_HAS_PROJECTS                 # 422  detail: project_count, project_ids[:10]
TEAM_OWNER_REQUIRED               # 422  detail: reason ∈ {last_owner_demote, last_owner_remove, transfer_target_not_member, target_is_self}
TEAM_MEMBER_NOT_FOUND             # 404
TEAM_MEMBER_DUPLICATE             # 409
TEAM_PERMISSION_DENIED            # 403  detail: required_role, current_role
CROSS_TEAM_MOVE_FORBIDDEN         # 422  detail: current_team_id, target_team_id
```

**Alembic 迁移**（2 步，与 M16 / M18 已积压枚举合并执行）：
- ALTER CONSTRAINT ck_activity_log_action_type CHECK 扩 10 个枚举值
- ALTER CONSTRAINT ck_activity_log_target_type CHECK 扩 1 个枚举值

**M15 文档更新**：§3 ActionType / TargetType 枚举表加行（注明 source: M20 baseline-patch 2026-04-26）+ §13 ErrorCode 全局表加 8 行

**回归风险**：无（枚举扩 CHECK 兼容已有数据）

---

### 3.2 横切 baseline-patch（M03-M19 全部模块的 L3 SQL 注入升级）

**改动类型**：High（query 层中间件升级，非 schema 改动）

**触发原因**：Q5 决策 L1 粗 + L2 精 + L3 SQL 兜底三层防御。原 L3 仅注入 `WHERE project_id = :pid`（单 project 上下文），M20 引入 team 后用户可访问的 project 集合扩展为 `team_members ∪ project_members`，L3 注入逻辑必须升级。

**升级前**（M01-M19 现状）：
```python
# api/dao/base.py（伪代码 — 各模块 DAO 单独实现）
def list_for_project(self, db, project_id: UUID, user_id: UUID):
    return db.query(self.model).filter(self.model.project_id == project_id).all()
```

**升级后**（M20 引入后统一升级）：
```python
# api/auth/tenant_filter.py（M20 新增 helper）
def user_accessible_project_ids_subquery(db, user_id: UUID):
    """
    返回 user 可访问的 project_id 子查询。
    并集来源：
      1. project_members WHERE user_id = X
      2. projects WHERE team_id IN (SELECT team_id FROM team_members WHERE user_id = X)
    """
    return (
        db.query(ProjectMember.project_id).filter(ProjectMember.user_id == user_id)
        .union(
            db.query(Project.id).filter(
                Project.team_id.in_(
                    db.query(TeamMember.team_id).filter(TeamMember.user_id == user_id)
                )
            )
        )
    ).subquery()

# 各模块 DAO list/get 操作改为
def list_for_project(self, db, project_id: UUID, user_id: UUID):
    accessible = user_accessible_project_ids_subquery(db, user_id)
    return (
        db.query(self.model)
        .filter(self.model.project_id == project_id)
        .filter(self.model.project_id.in_(select(accessible)))   # M20 新增 L3 兜底
        .all()
    )
```

**受影响模块清单**（M03-M19 全部 17 个）：

| 模块 | DAO 入口 | 升级范围 |
|------|---------|---------|
| M02 | ProjectDAO.list_for_user / get_by_id | 自身入口（owner_id 校验保留 + 加 accessible 子查询并集） |
| M03 | NodeDAO.list_for_project / get_by_id | list / get / search |
| M04 | DimensionRecordDAO.list / get | list / get |
| M05 | VersionDAO.list / get | list / get |
| M06 | CompetitorDAO.list / get | list / get |
| M07 | IssueDAO.list / get | list / get |
| M08 | RelationDAO.list / get | list / get |
| M09 | superseded by M18 — 仅 M18 SearchDAO 升级 |
| M10 | OverviewDAO.aggregate | 聚合 SQL WHERE 子句加并集 |
| M11 | ColdStartDAO.batch_create_in_transaction | batch_create 入口 user_accessible 校验 |
| M12 | ComparisonDAO.list / get | list / get |
| M13 | RequirementAnalysisDAO.list / get | list / get（SSE 路径 + Service 层） |
| M14 | IndustryNewsDAO.list / get | list / get |
| M15 | ActivityLogDAO.list_for_project | list 加并集 |
| M16 | SnapshotDAO.list / get | list / get |
| M17 | ImportTaskDAO.list / get | list / get（Queue 消费者侧 ADR-002 校验保留） |
| M18 | SearchDAO.hybrid_search / SemanticDAO | search 入口加并集（embedding backfill 走规则 4 不走此路径） |
| M19 | ImportExportDAO.list / get | list / get |

**实施策略**（Phase 2 落地时）：
1. 先在 `api/auth/tenant_filter.py` 实现 `user_accessible_project_ids_subquery` helper
2. 各模块 DAO 改造时引用 helper（不重复实现 SQL）
3. 写 1 套 L3 注入回归测试（基于 M02 / M03 验证），其他模块复用测试模板
4. 性能监控：上线后观察子查询耗时，超阈值时引入 Redis 缓存 `user:{uid}:accessible_projects`（不在本期）

**回归风险**：中
- 改造逻辑统一，但涉及 17 个模块，AI 实现时需逐个验证
- L3 注入与 L2 显式校验冗余 → 双重检查导致性能下降可接受（安全优先）
- 跨 team 子查询性能 → 列入 trade-off（§4）

---

## §4 Trade-offs（重要权衡）

| # | trade-off | 决策 | 缓解 / 演进退路 |
|---|-----------|------|----------------|
| T1 | Q4 单 tenant + Q5 三层注入 → 跨 team 子查询性能 | 接受性能开销，安全优先 | 上线后 P95 > 100ms 引入 Redis 缓存 `user:{uid}:accessible_projects` TTL 60s。**失效路径预演（Batch 3 / F3.5）**：① U 加入 team → DEL key；② U 移出 team → DEL key；③ 删 team → DEL key for all members；④ project 加入 team → DEL key for all team members；⑤ project 移出 team → DEL key for all team members（含目标 team）。任一路径漏失效都会导致权限残留 ≤ 60s，必须在 Service 层 5 处显式 DEL（不靠 TTL 过期兜底） |
| T2 | Q8 强制前置迁出 → 删 team UX 重（N+1 步操作） | 接受 UX 代价，强一致优先 | 未来视痛点决定加批量「迁出 + 删 team」组合 API |
| T3 | Q10 细粒度事件 + Q12 粗粒度错误 → 非对称结构 | 接受非对称（事件审计需细 / 错误客户端处理不需细） | 文档显式标注此 trade-off |
| T4 | Q13.1 ① team name 同 creator 唯一 → transfer 后语义偏 | 接受语义偏，PRD「私域分组」优先 | UI 显示 team name 附 creator 名缓解 |
| T5 | M03-M19 横切 L3 SQL 注入升级 → 17 模块改造工作量 | Phase 2 实施时统一改造 + 公共 helper | 实施前先写 1 套测试模板供复用 |
| T6 | 转让 owner 拆 2 条事件（demote + promote） → 审计需关联推断 | 与 Q10 细粒度风格一致 | 同事务 + 同 actor + timestamp 邻近三条件可推断（Batch 2 后已加 metadata.correlation_id 硬关联） |
| T7（F2.11+F3.6） | Q3 软切断（删 team_member 不级联清 ProjectMember）vs Q8 强制前置迁出（删 team 拒留 project）非对称防误哲学 | 接受非对称，原则：**「越靠近资源越严格」** —— project 是「资源」、team_member 是「关系」；删一个「关系」不应殃及「资源」（软），删一个「容器」不应让「资源」漂移成孤儿（严）| 演进延伸原则（未来 organization 层）：org_member 删除走软切断（与 Q3 一致），org 删除走强制前置迁出 team（与 Q8 一致）；任何引入新「关系层」时按此原则取默认 |

---

## §5 Consequences（影响）

### 正向

- PRD F20 AC1-AC3 全部覆盖，命名对齐 Prism 实跑
- M20 schema 工作量小（仅 2 张新表 + 1 字段重命名）
- 与 M01-M19 已 accepted 决策风格高度一致（M02 范式复刻 + R10-2 主规则 + 三重防护）
- 完成 Phase 1 全 20 模块设计，可进入 Phase 2 实施
- 横切 L3 注入升级一次性补齐多 tenant 入口，未来加 organization 层时只改 helper 不改各模块

### 负向

- 横切影响 17 模块的 L3 SQL 注入升级，Phase 2 实施时工作量集中
- 跨 team 子查询性能未在本期验证，依赖上线后监控数据
- 删 team UX 重，可能在实际使用时被 CY 自己嫌烦
- 非对称的事件细 / 错误粗 结构，文档需显式说明避免后续 reviewer 质疑

### 中性

- ADR-001 §预设 3 **整段**被 supersede —— 三件实质变更：① 命名 space_id → team_id；② 类型 INT NULL → UUID NULL；③ 启用 FK ondelete=RESTRICT（原"无 FK"放弃）。「预留口」精神（先 nullable 再补 FK）保留，「无 FK 升级路径"字面"」改写。
- M20 后续若引入 organization 层，再走一次类似的 baseline-patch（team_id → org_id 链路扩展），对照本 ADR §3 模板

---

## §6 Alternatives Considered（替代方案）

### 方案 1（Q0=A）：纯 Space 命名

**否决理由**：
- PRD F20 AC1-AC3 字面用「团队」，纯 Space 命名与产品语言断裂
- Prism 实跑用 team + team_members，Shadow 项目对照价值削弱
- 仅工程视角对齐 ADR-001 预留口字面，但 ADR-001 本就是预留口（命名可改）

### 方案 2（Q0=C）：Space 容器 + Team 人集合 + SpaceTeamGrant 双并存

**否决理由**：
- 违反 PRD「最小实现 + 非协作平台」原则（YAGNI 红线）
- 三概念 + 关联表，半年回归概率高
- 引入 organization 概念需额外决策

### 方案 3（Q1=A）：覆盖式（Team 角色直接吞 ProjectMember）

**否决理由**：
- 失去 per-project 微调能力
- AC2 一键迁移时原 ProjectMember 数据被吞，权限突变
- 未来若想做「团队项目对外开放某人 viewer」必须重构

### 方案 4（Q4=B）：双 tenant (team_id, project_id) 全表冗余

**否决理由**：
- M03-M19 全部 17 个模块衍生表 schema 改造，工作量爆炸
- 违反 ADR-001 §预设 3「最小预留」精神
- 数据冗余违反第三范式
- project 移动 team 不再原子（需事务批量 UPDATE 衍生表）

---

## §7 未来 organization 层演进路径（占位 / Batch 3 F3.3）

> 本节非本期 accepted 决策，仅记录"若未来引入 org 层"时必须回头决策的 4 个锚点。M20 accept 不依赖此节定稿；本节仅防止"零锚点跳跃式扩展"。

### 8.1 触发器

- 触发条件：单实例 ≥ 2 个独立组织 / 跨组织数据严格隔离 / 计费按组织独立结算 任一发生
- 触发后阅读：本节 4 决策点 + ADR-005 §3 baseline-patch 范本 + ADR-001 §预设 3 supersede 范本

### 8.2 4 决策点（必答）

| # | 决策点 | 候选选项 | 与 M20 现状的对偶 |
|---|--------|---------|---------------------|
| **O1** | 唯一约束：team name 同 creator 唯一（Q13.1①）→ org 层引入后是否改"同 org 唯一" | A 维持 creator 唯一 / B 改 org 唯一（带迁移）/ C 双层（org+creator 都唯一） | M20 当前 creator 唯一（uq_teams_creator_name），引入 org 后语义偏；建议 B（同 org 唯一），但需迁移 + 改 ErrorCode detail |
| **O2** | 二维空白态：org_id IS NULL = 个人 / team_id IS NULL = 个人，组合后是否有 (org_id IS NULL, team_id NOT NULL) 这种 hybrid 态 | A 禁止（org_id NOT NULL 是 team 加入 org 的前提）/ B 允许（团队可不属于任何 org） | 建议 A（避免 hybrid 态权限歧义），强制 team 加 org 前先创建 org |
| **O3** | helper 形态：`user_accessible_project_ids_subquery` 升级为 `user_accessible_org_ids` × team × project 三层并集 | A 一次性扩 helper（17 模块 DAO 不动）/ B 各模块 DAO 显式三层 join | A（与 M20 引入 helper 一致原则）；性能下降时再引 Redis 缓存 |
| **O4** | 对称延伸（T7 哲学）：org_member 删除走软切断 / org 删除走强制前置迁出 team | 沿用 ADR-005 §4 T7「越靠近资源越严格」原则 | 不重复决策，直接延伸 |

### 8.3 baseline-patch 模板

参照本 ADR §3 模板：① ER 加 organizations + organization_members 表（参 teams + team_members 范式）；② teams 加 org_id FK ondelete=RESTRICT；③ M03-M19 横切 helper 升级；④ M15 ActionType 扩 org_* 系列；⑤ M01 删 user 校验链加 org_owned 校验（与 F3.10 同模式）。

预估工作量：约 M20 baseline-patch 的 1.2x（多一层 + 横切 helper 升级范围已锚定）。

---

## §8 完成度判定

- [x] Context 4 点（M20 定位 / ADR-001 §预设 3 / PRD F20 / Prism 实跑对照）
- [x] Decision 16 决策点 + Q10.1 / Q13.1 子点全收敛
- [x] §3 baseline-patch 完整清单（M02 + M15 + M03-M19 横切）
- [x] §4 Trade-offs 6 项显式登记
- [x] Consequences 正向 5 条 + 负向 4 条 + 中性 2 条
- [x] Alternatives 4 方案各有否决理由
- [x] supersede ADR-001 §预设 3 命名部分（实质保留）
- [x] 决策对照表覆盖 Q0-Q15 + 子决策
