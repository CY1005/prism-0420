---
title: M20 基线补丁：M02 space_id→team_id / M15 ActionType+ErrorCode / M03-M19 横切 L3 SQL 注入升级
status: accepted
owner: CY
created: 2026-04-26
accepted: 2026-04-26
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: baseline-patch-m20
modules_affected: [M01, M02, M03, M04, M05, M06, M07, M08, M10, M11, M12, M13, M14, M15, M16, M17, M18, M19]
adrs_affected: [ADR-001(supersede §预设 3 命名), ADR-005(new)]
readme_affected: []
trigger: M20 brainstorming Q0-Q15 决策落地
---

# M20 基线补丁报告

## 0. 执行摘要

| 维度 | 数量 |
|------|------|
| 受影响业务模块（schema 改动） | 1（M02） |
| 受影响业务模块（Service 校验链） | 1（M01，Batch 2 / F3.10 提议） |
| 受影响 own 模块（M20 自身新增） | 1（M20：teams + team_members 2 张新表） |
| 受影响横切模块（L3 SQL 注入升级） | 16（M02-M19 去除 M09 superseded，仅 query 层 helper 引用） |
| 受影响 horizontal own 模块（M15） | 1（ActionType +10 / TargetType +1 / ErrorCode +8） |
| 受影响 ADR | 2（ADR-001 supersede §预设 3 命名 / ADR-005 新增） |
| 新增 schema 字段 | 0（M02 仅 RENAME + 启用 FK） |
| 新增 ActionType 枚举 | 10（team_created / team_renamed / team_description_changed / team_deleted / team_member_added / team_member_removed / team_member_promoted_admin / team_member_demoted_member / project_joined_team / project_left_team） |
| 新增 TargetType 枚举 | 1（team） |
| 新增 ErrorCode | 8（TEAM_NOT_FOUND / TEAM_NAME_DUPLICATE / TEAM_HAS_PROJECTS / TEAM_OWNER_REQUIRED / TEAM_MEMBER_NOT_FOUND / TEAM_MEMBER_DUPLICATE / TEAM_PERMISSION_DENIED / CROSS_TEAM_MOVE_FORBIDDEN） |
| Alembic 迁移步数 | 6（M20 own 2 步 + M02 baseline 2 步 + M15 baseline 2 步） |

## 1. 触发来源

CY 2026-04-26 brainstorming Q0-Q15 + Q10.1 / Q13.1 子点全部决策。完整决策对照表见 [`../adr/ADR-005-team-extension.md`](../adr/ADR-005-team-extension.md) §Decision。

---

## 2. 每模块/文档改动详情

### M02 项目管理（schema 字段重命名 + 启用 FK）

**改动类型**：High（schema 迁移 + 命名语义升级）

**现状**：
- M02 已 accepted 2026-04-21
- `projects.space_id: Mapped[PyUUID | None]`（ADR-001 §预设 3 预留口，nullable + index + 无 FK）

**M20 需求**：Q0=B 命名对齐 PRD F20 + Prism 实跑；M20 引入 teams 表后 FK 启用（Q8 强制前置迁出依赖 RESTRICT FK）

**改动**：

```python
# api/models/projects.py（M02 own，M20 baseline-patch 2026-04-26）
class Project(Base):
    # ... existing fields
    # 原 space_id 改名 team_id；nullable 保留（个人 project 语义）
    team_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="RESTRICT"),  # Q8 强制前置迁出
        nullable=True,
        index=True,
    )
```

**Alembic 迁移**（2 步）：
1. `ALTER TABLE projects RENAME COLUMN space_id TO team_id`
2. `ALTER TABLE projects ADD CONSTRAINT fk_projects_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT`
   - **顺序约束**：M20 own 的 `CREATE TABLE teams` 必须先于此步（FK 引用前提）

**M02 文档更新**：
- §3 schema 块：`space_id` 字段改 `team_id` + 加 ondelete=RESTRICT 注释
- §3 索引块：`(space_id)` 改 `(team_id)`
- §1 out of scope 表第 5 行：「团队/空间管理 → M20（本期数据模型预留 space_id，不实现）」改为「团队管理 → M20（M20 已 accepted YYYY-MM-DD，本字段已升级）」
- §15 标「M20 baseline-patch 引入」

**回归风险**：低 —— Phase 1 设计阶段无生产数据；Phase 2 实施时纯字段改名 + FK 启用

---

### M15 数据流转（ActionType +10 / TargetType +1 / ErrorCode +8）

**改动类型**：Medium（枚举扩 + Alembic CHECK 升级 + ErrorCode 注册）

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
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_MEMBER_PROMOTED_ADMIN = "team_member_promoted_admin"
    TEAM_MEMBER_DEMOTED_MEMBER = "team_member_demoted_member"
    PROJECT_JOINED_TEAM = "project_joined_team"
    PROJECT_LEFT_TEAM = "project_left_team"
```

**改动 2：TargetType 扩 1**：

```python
class TargetType(str, Enum):
    # ... existing
    TEAM = "team"  # M20 baseline-patch
```

**改动 3a：M15 ActivityLogDAO 新增 `list_for_team(team_id, user_id)` 入口**（Batch 2 / F2.5 修复）：

```python
# api/dao/activity_log.py（M15 own，M20 baseline-patch）
class ActivityLogDAO:
    def list_for_team(
        self,
        db: Session,
        team_id: PyUUID,
        user_id: PyUUID,        # L1 require_team_access(member) 已在 Router 层校验
        limit: int = 50,
        offset: int = 0,
    ):
        """
        F2.5：team_* 事件 8/10 类（team_created / team_renamed / team_description_changed /
        team_deleted / team_member_added / team_member_removed / team_member_promoted_admin /
        team_member_demoted_member）target_type='team' 且无 project_id，原 list_for_project
        召不回。新增此入口走 target_type+target_id 路径。
        """
        return (
            db.query(ActivityLog)
            .filter(
                ActivityLog.target_type == TargetType.TEAM,
                ActivityLog.target_id == team_id,
            )
            .order_by(ActivityLog.created_at.desc())
            .offset(offset).limit(limit)
            .all()
        )
```

**M15 文档更新**：§9 DAO tenant 过滤策略加行；M20 §9.1 同步引用。

**改动 3b：ErrorCode 全局表扩 8**（Q12=A 粗粒度）：

```
TEAM_NOT_FOUND                    # 404
TEAM_NAME_DUPLICATE               # 409  detail: name, creator_id
TEAM_HAS_PROJECTS                 # 422  detail: project_count, project_ids[:10]
TEAM_OWNER_REQUIRED               # 422  detail: reason ∈ {last_owner_demote, last_owner_remove, transfer_target_not_member}
TEAM_MEMBER_NOT_FOUND             # 404
TEAM_MEMBER_DUPLICATE             # 409
TEAM_PERMISSION_DENIED            # 403  detail: required_role, current_role
CROSS_TEAM_MOVE_FORBIDDEN         # 422  detail: current_team_id, target_team_id
```

**Alembic 迁移**（2 步，与 M16 / M18 已积压枚举合并执行）：
1. ALTER CONSTRAINT ck_activity_log_action_type CHECK 增 10 枚举值
2. ALTER CONSTRAINT ck_activity_log_target_type CHECK 增 1 枚举值（"team"）

**M15 文档更新**：
- §3 ActionType 枚举表加 10 行（标注 source: M20 baseline-patch 2026-04-26）
- §3 TargetType 枚举表加 1 行
- §13 ErrorCode 全局表加 8 行（每个 code 含 HTTP / detail schema / 触发场景列）

**回归风险**：无（枚举扩 CHECK 兼容已有数据）

---

### M01 用户系统（Batch 2 / F3.10 + F3.13 提议 baseline-patch）

**改动类型**：Medium（M01 删 user 入口加校验链 + 新增 2 个 ErrorCode）

**触发原因**：teams.creator_id `ondelete=RESTRICT` + team_members.user_id `ondelete=CASCADE` 内部冲突 —— DB 层 RESTRICT 守护 creator 不可随便删，但 CASCADE 会直接清 user 的 team_members 行（含 owner 行），触发"无 owner team"风险。M20 §5.3 第 6 场景登记此问题，需 M01 删 user 入口前置校验。

**改动**：

```python
# api/services/users.py（M01 own，M20 baseline-patch 提议）
class UserService:
    def delete_user(self, db: Session, user_id: PyUUID, actor_id: PyUUID) -> None:
        """删 user 前置校验（M20 baseline-patch 2026-04-26 加）"""
        # 1) 校验：U 不是任何 team 的 creator（teams.creator_id RESTRICT 守护）
        owned_teams_as_creator = db.query(Team).filter(Team.creator_id == user_id).count()
        if owned_teams_as_creator > 0:
            raise UserHasOwnedTeamsError(detail={"team_count": owned_teams_as_creator})

        # 2) 校验：U 不是任何 team 的最后 owner（防 CASCADE 清空 owner 行后无 owner team）
        last_owner_team_ids = db.query(TeamMember.team_id).filter(
            TeamMember.user_id == user_id,
            TeamMember.role == TeamRole.OWNER,
        ).filter(
            ~db.query(TeamMember).filter(
                TeamMember.team_id == TeamMember.team_id,  # correlated
                TeamMember.role == TeamRole.OWNER,
                TeamMember.user_id != user_id,
            ).exists()
        ).all()
        if last_owner_team_ids:
            raise UserIsLastTeamOwnerError(detail={"team_ids": [t[0] for t in last_owner_team_ids]})

        # 3) 通过校验后才走 DELETE users（CASCADE 清 team_members 安全）
        ...
```

**M01 ErrorCode 新增 2 个**：

```
USER_HAS_OWNED_TEAMS              # 422  detail: team_count（至少 1 个 team 的 creator_id 是 U）
USER_IS_LAST_TEAM_OWNER           # 422  detail: team_ids[]（U 是这些 team 的唯一 owner）
```

**修复路径要求 user 先**：① transfer ownership 给其他 owner（清 last-owner 风险）；② 删 team 或 transfer creator（M20 当前不支持 transfer creator —— 需走删旧 team + 重建）

**M01 文档更新**：§7 endpoint 表 DELETE /users/{uid} 加 ErrorCode 列；§13 ErrorCode 加 2 行；§5.3 状态转换加场景。

**回归风险**：低（M01 现有删 user 路径几乎不被调用 —— 用户主动注销少见；新增校验是否触发 422 完全可预测）

---

### M03-M19 横切 L3 SQL 注入升级（query 层 helper 引用）

**改动类型**：High（query 层升级，非 schema 改动）

**触发原因**：Q5=A 决策 L1+L2+L3 三层防御。原 L3 仅注入 `WHERE project_id = :pid`（单 project 上下文），M20 引入 team 后用户可访问的 project 集合扩展为 `team_members ∪ project_members`，L3 注入逻辑必须升级。

**M20 own 的公共 helper**：

```python
# api/auth/tenant_filter.py（M20 新增）
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

def user_accessible_project_ids_subquery(db: Session, user_id: UUID):
    """
    返回 user 可访问的 project_id 子查询（并集来源）：
      1. project_members WHERE user_id = X
      2. projects WHERE team_id IN (SELECT team_id FROM team_members WHERE user_id = X)

    M03-M19 DAO 在 list / get / search 入口引用此 helper 做 L3 SQL 兜底注入。
    豁免：
      - M18 embedding backfill / monitor cron DAO（无用户上下文，走 ADR-003 规则 4）
      - M15 activity_log write 路径（M15 own 表，写入由各模块 Service 主动调用，非用户查询）
    """
    from api.models.projects import Project
    from api.models.project_members import ProjectMember
    from api.models.teams import TeamMember

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
```

**升级前**（M01-M19 现状）：

```python
# api/dao/nodes.py（举例 M03，伪代码）
def list_for_project(self, db, project_id: UUID, user_id: UUID):
    return db.query(Node).filter(Node.project_id == project_id).all()
```

**升级后**（M20 引入后统一升级）：

```python
from api.auth.tenant_filter import user_accessible_project_ids_subquery

def list_for_project(self, db, project_id: UUID, user_id: UUID):
    accessible = user_accessible_project_ids_subquery(db, user_id)
    return (
        db.query(Node)
        .filter(Node.project_id == project_id)
        .filter(Node.project_id.in_(select(accessible)))   # M20 新增 L3 兜底
        .all()
    )
```

**受影响模块清单**（16 个，M09 已 superseded by M18 不计入；F2.14 修订）：

| 模块 | DAO 入口 | 升级范围 | 备注 |
|------|---------|---------|------|
| M02 | ProjectDAO.list_for_user / get_by_id | 自身入口 | owner_id 校验保留 + 加 accessible 子查询并集 |
| M03 | NodeDAO.list_for_project / get_by_id / search | list / get / search | |
| M04 | DimensionRecordDAO.list / get | list / get | |
| M05 | VersionDAO.list / get | list / get | |
| M06 | CompetitorDAO.list / get | list / get | |
| M07 | IssueDAO.list / get | list / get | |
| M08 | RelationDAO.list / get | list / get | |
| M10 | OverviewDAO.aggregate | 聚合 SQL WHERE 加并集 | 走 ADR-003 规则 2，仍需引用 helper |
| M11 | ColdStartDAO.batch_create_in_transaction | batch 入口 user_accessible 校验 | |
| M12 | ComparisonDAO.list / get | list / get | |
| M13 | RequirementAnalysisDAO.list / get | list / get（SSE 路径 + Service 层） | SSE 流式 user 校验在 stream() 入口 |
| M14 | IndustryNewsDAO.list / get | list / get | |
| M15 | ActivityLogDAO.list_for_project | list 加并集 | write 路径不走（豁免） |
| M16 | SnapshotDAO.list / get | list / get | |
| M17 | ImportTaskDAO.list / get | list / get | Queue 消费者侧 ADR-002 校验保留 |
| M18 | SearchDAO.hybrid_search / SemanticDAO query | search 入口加并集 | embedding backfill / monitor cron 走规则 4 豁免 |
| M19 | ImportExportDAO.list / get | list / get | |

**实施策略**（Phase 2 落地时）：
1. **先实现 helper**：在 `api/auth/tenant_filter.py` 实现 `user_accessible_project_ids_subquery`
2. **写测试模板**：基于 M02 / M03 验证 L3 注入正确性，其他模块复用测试模板（含 T1-T6 测试场景）+ pytest parametrize over DAO 类（每个 DAO 实例一组同形 case，CI 覆盖矩阵自动展开）
3. **逐模块改造 DAO**：每个模块 DAO 引用 helper，不重复实现 SQL
4. **回归测试**：每模块跑原有 tests.md 全套 + 新增 tenant 隔离测试（T 类用例）
5. **性能监控**：上线后观察子查询耗时；若 P95 > 100ms，引入 Redis 缓存 `user:{uid}:accessible_projects` TTL 60s（不在本期，详 ADR-005 §4 T1 失效路径预演）

### 17 模块拆批策略（Batch 3 / F3.2 锚定）

按依赖深度 + 模块域聚类拆 4 批，每批独立 PR + 独立测试模板套用，便于 review。批次内并行无依赖：

| 批 | 模块 | 共性 | PR 边界 |
|----|------|------|---------|
| 批 1（基础） | M02 + M03 + M04 | 数据模型最底层（project / node / dimension），其他模块都依赖它们 | 1 个 PR，先建 helper + parametrize 测试模板 |
| 批 2（叶子结构）| M05 + M06 + M07 + M08 | 单 project 内的版本/竞品/issue/relation 衍生，无跨模交互 | 1 个 PR |
| 批 3（聚合 + 异步）| M10 + M11 + M12 + M13 + M14 | overview 聚合 / cold-start / comparison / requirement-analysis / industry-news（含 SSE 流式） | 1 个 PR，注意 M13 SSE 路径走 stream() 入口校验 |
| 批 4（横切 own + 异步重）| M15 + M16 + M17 + M18 + M19 | activity_log own + 后台 / Queue / embedding / import-export | 1 个 PR，最复杂（含 ADR-002 / ADR-003 跨模决策），最后做 |

**单批回滚策略**：每批独立 commit，发现某批 helper 引用错就回滚那 1 个 PR，不影响其他批。

**批 1 完成判定**：M02 + M03 + M04 三模块 tests.md T 类全部 PASS + L3 注入测试模板（pytest parametrize）通过 → 才允许启动批 2。

### Alembic 三批 ActionType CHECK 合并顺序（Batch 3 / F3.4 锚定）

M16 / M18 / M20 三批 ActionType 枚举扩相互独立，但共用 `ck_activity_log_action_type` CHECK constraint，必须合并到**单 Alembic revision**（避免三次 ALTER 同 CHECK 串行 lock）：

```
revision: "20260427_m15_action_type_consolidate"
down_revision: <M15 last accepted revision>

upgrade():
    # 字母序合并三批新增枚举值（M16 → M18 → M20）
    op.execute("""
        ALTER TABLE activity_log
        DROP CONSTRAINT ck_activity_log_action_type
    """)
    op.execute("""
        ALTER TABLE activity_log
        ADD CONSTRAINT ck_activity_log_action_type CHECK (
            action_type IN (
                -- 原有枚举（保留）
                ..., 
                -- M16 新增（snapshot_*）
                'ai_snapshot_created', 'ai_snapshot_failed', 'ai_snapshot_zombie_recovered',
                -- M18 新增（embedding_*）
                'embedding_indexed', 'embedding_backfilled',
                -- M20 新增（team_* / project_*_team）
                'team_created', 'team_renamed', 'team_description_changed', 'team_deleted',
                'team_member_added', 'team_member_removed',
                'team_member_promoted_admin', 'team_member_demoted_member',
                'project_joined_team', 'project_left_team'
            )
        )
    """)
    # TargetType 同样合并
    op.execute("""
        ALTER TABLE activity_log
        DROP CONSTRAINT ck_activity_log_target_type
    """)
    op.execute("""
        ALTER TABLE activity_log
        ADD CONSTRAINT ck_activity_log_target_type CHECK (
            target_type IN (..., 'snapshot', 'embedding', 'team')
        )
    """)
```

**硬触发器**：M20 accept 当天，M15 文档 §3 ActionType / TargetType 表必须**同步回写**（不允许仅 M20 accept 但 M15 表未更新）。verify Agent 在 M20 accept 检查清单内必须验证 M15 文档已同步。

**回归风险**：中
- 改造逻辑统一，但涉及 17 模块，AI 实现时需逐个验证
- L3 注入与 L2 显式校验冗余 → 双重检查导致单请求多 1 次 DB 查询，安全优先可接受
- 跨 team 子查询性能 → 列入 ADR-005 §4 T1 trade-off

---

## 3. 实施顺序建议

依赖关系决定的顺序：

1. **先建 ADR-005**（决策对照表 + supersede ADR-001 §预设 3 命名 + 横切影响清单）—— Phase 1 设计阶段必须先做
2. **写 M20 own 设计文档**（00-design.md + tests.md）—— 已完成
3. **本 baseline-patch 文档落地** —— 当前
4. **更新 M02 文档**：§3 schema 字段改名 + §1 out of scope 表 + §15 baseline-patch 标注
5. **更新 M15 文档**：§3 ActionType / TargetType 枚举表 + §13 ErrorCode 全局表
6. **更新 README.md**：模块清单 M20 行状态 「待开」 → 「accepted」（M20 通过 reviewer audit 后）

**Phase 2 阶段（写代码）**：
- a. 先建 teams + team_members 表（CREATE TABLE，M20 own）
- b. 再 RENAME projects.space_id → team_id 并 ADD CONSTRAINT FK（M02 baseline）
- c. 实现 `api/auth/tenant_filter.py` helper
- d. 实现 M20 Service / Router / DAO + Pydantic schemas
- e. 写 M03-M19 DAO 升级 PR（17 模块，建议拆分批次）
- f. ActionType / TargetType / ErrorCode CHECK constraint 迁移（与 M16 / M18 已积压枚举合并）

---

## 4. CY 决策项

- [x] **决策 Q0-Q15**：CY 2026-04-26 brainstorming 全部 ack（参 ADR-005 §Decision 决策对照表）
- [x] **决策**：横切 L3 注入升级范围 = M03-M19 全部（不豁免任何业务模块）
- [x] **决策**：豁免清单 = M18 embedding backfill / monitor cron + M15 activity_log write 路径
- [x] **决策**：实施顺序 = Phase 1 设计先收（ADR-005 + M20 + baseline-patch + M02/M15 文档），Phase 2 实施按 a-f 顺序
- [ ] **待 CY 确认**：M03-M19 逐模块 DAO 升级 PR 是否拆批（建议每批 4-5 个模块）—— 留 Phase 2 实施前再定

---

## 5. 关联文档

- M20 主设计：[`M20-team/00-design.md`](./M20-team/00-design.md)
- M20 测试：[`M20-team/tests.md`](./M20-team/tests.md)
- 决策对照表：[`../adr/ADR-005-team-extension.md`](../adr/ADR-005-team-extension.md) §Decision
- supersede 来源：[`../adr/ADR-001-shadow-prism.md`](../adr/ADR-001-shadow-prism.md) §预设 3 命名部分
- 触发来源：CY 2026-04-26 brainstorming Q0-Q15
- 前置 baseline-patch：[`baseline-patch-m18.md`](./baseline-patch-m18.md)（M02 RRF 字段 / M15 ActionType +2）
- README：[`README.md`](./README.md) 模块清单 M20 行状态待更新（accept 后）
