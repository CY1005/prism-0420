---
module: M20
name: team
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M20-team/00-design.md
  - design/02-modules/M20-team/tests.md
  - design/02-modules/M20-team/02-frontend-design.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-005-team-extension.md
prd_ref: F20 团队/空间 AC1-AC3
---

# M20 团队 测试点

## 业务流程（H1 / 1 行概述）

M20 引入 team 作为 project 容器：creator_id 永不变 + owner/admin/member 三角色 + teams 乐观锁 version；project 归属 individual ↔ team 单步切换（禁 team A→team B 直跳）；权限并集 max(team_role_mapped, project_member_role)；删 team 强制前置迁出（archived project 走豁免自动解绑）；transfer owner 与 delete team 是 R-X3 跨事务 Service（共享外部 db: Session）；新增 user_accessible_project_ids_subquery 横切 helper 供 M03-M19 L3 SQL 兜底注入。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/teams happy path 201 返 TeamRead + 单事务原子写入 teams + team_members(creator, role=owner) + activity_log 写 team_created + team_member_added（design §7 + tests.md G1）
- [P0] GET /api/teams 返当前用户通过 team_members 关联的所有 team 含 member_count 聚合字段（design §7 + §9.1 list_for_user + tests.md G10）
- [P0] GET /api/teams/{tid} L1 require_team_access(member) 通过返 team 详情含 members 列表（design §7 + §8.1 + tests.md T2）
- [P0] PATCH /api/teams/{tid} 改 name happy path 200 + teams.version 自增 + activity_log 写 team_renamed detail.from_name/to_name（design §7 + §10.1 + tests.md G5）
- [P0] POST /api/teams/{tid}/members 加成员 201 + DB 写入 + activity_log 写 team_member_added detail.role（design §7 + tests.md G2）
- [P0] PATCH /api/teams/{tid}/members/{uid} promote member→admin 200 + activity_log 写 team_member_promoted_admin detail.from_role/to_role（design §10.1 + tests.md G3）
- [P0] POST /api/teams/{tid}/transfer-ownership 200 单事务原子 U1→admin + U2→owner + 同事务 2 条 activity_log（demoted + promoted + 同 correlation_id）+ teams.version+1（design §8.7 + §10.1 F2.9 + tests.md G4）
- [P0] DELETE /api/teams/{tid}/members/{uid} 软切断 200 + project_members 不动 + 响应附 residual_project_members 列表 + activity_log detail.reason="manual"（design §7 §10.1 Q3 + tests.md G9）
- [P0] DELETE /api/teams/{tid} 5 步事务原子（前置 projects 空 + 查 N members + 写 1 条 team_deleted + N 条 team_member_removed + 删 team_members + 删 teams）204（design §8.7 + tests.md G8）
- [P0] POST /api/projects/{pid}/move-team target_team_id=tid happy path（个人 project 加入 team）200 + project.team_id 改 + activity_log 写 project_joined_team（design §7 端点拆分 F2.7 + tests.md G6）
- [P0] POST /api/projects/{pid}/move-team target_team_id=null 移回个人 200 + activity_log 写 project_left_team detail.from_team_id（design §7 + tests.md G7）
- [P1] POST /api/teams description=null 允许 201 + DB 存 NULL（design §7 Pydantic + tests.md B2）
- [P1] PATCH /api/teams/{tid} 改 description 写 activity_log team_description_changed detail.from/to_description（design §10.1 Q10.1② + tests.md G5 衍生）
- [P1] 创建 team 时 creator 自动成为 owner 单事务失败任一步整体回滚（design §3 §8.7 + tests.md B11）
- [P1] AC2 一键迁移 100 个 project 前端循环 100 次 move-team 全部 200 / 总耗时 ≤ 20s（design §1 F2.2 规模假设 + tests.md B12）

### 2. 边界 / 状态机

- [P0] name 长度边界 "" / 101 字符 → 422 VALIDATION_ERROR；1 字符 / 100 字符 → 201（design §3.2 CheckConstraint + §7 Pydantic min/max + tests.md B1）
- [P0] team_members.role 状态机 member→admin 允许（promote actor 至少 admin）（design §4.2 mermaid + tests.md G3）
- [P0] team_members.role 禁止转换 owner → [*] team_member_removed 拒 422 TEAM_OWNER_REQUIRED reason="last_owner_remove"（design §4.2 禁止转换 + tests.md E5）
- [P0] team_members.role 禁止转换 member → owner 跨级直升拒 422（Pydantic schema 限 Literal["admin","member"]）（design §4.2 + §7.2 + tests.md P13）
- [P0] team_members.role 禁止转换 owner → admin 非 transfer 场景（最后 owner demote）拒 422 TEAM_OWNER_REQUIRED reason="last_owner_demote"（design §4.2 + tests.md E4 + P14）
- [P0] team_members.role 禁止转换 owner → member 直降任何路径拒 422 TEAM_PERMISSION_DENIED（schema Literal 限 + 必须先 transfer 再 demote）（design §4.2 第 4 条 + tests.md P14 衍生）
- [P0] teams 物理删除后不可复活：同 creator 用同 name 再创建是新 team（id 不同）旧 team_id activity_log 不可反查（design §4.1 禁止转换注解）
- [P1] B3 team_members N=1 删 team 流程仍走 5 步：写 1 条 team_member_removed (reason="team_deleted") + 1 条 team_deleted（design §8.7 + tests.md B3）
- [P1] B4 transfer 给自己 U1→U1 拒 422 TEAM_OWNER_REQUIRED reason="target_is_self"（design §13.1 detail.reason 枚举 + tests.md B4 + E6b）
- [P1] B5 同 creator 不同 team 同名第二个 409 TEAM_NAME_DUPLICATE detail.{name, creator_id}（design §3.2 UniqueConstraint + tests.md B5）
- [P1] B5b transfer 后 creator 再用同名仍拒 409 TEAM_NAME_DUPLICATE（creator_id 永不变）（design §1 边界灰区 + tests.md B5b）
- [P1] B6 不同 creator 同名 team 两个都 201（uq_teams_creator_name 仅同 creator 唯一）（design §3.2 + tests.md B6）
- [P1] B8 删 team 时 projects 非空 N=5 拒 422 TEAM_HAS_PROJECTS detail.{project_count=5, project_ids[:10]}（design §13.1 + tests.md B8）
- [P1] B13 archived project 拒加入 team 422 PROJECT_ARCHIVED（M02 ErrorCode 复用 F2.3 源头）（design §1 边界灰区 + tests.md B13）
- [P1] B14 删 team 时 archived project 自动解绑（active P_a 先迁出后删 team 触发 P_b team_id=NULL + activity_log project_left_team reason="team_deleted_archived_auto_unbind"）（design §1 F2.3 历史兜底 + tests.md B14）
- [P1] B9 移成员但 U 在 0 个 project 有 ProjectMember 时 residual_count=0 / residual_project_members=[]（design §7.2 + tests.md B9）
- [P1] B10 移成员但 U 在 100 个 project 有 ProjectMember 时 residual_count=100 完整列出不截断（design §7.2 TeamMemberRemoveResponse + tests.md B10）

### 3. 异常 / 错误

- [P0] PATCH /api/teams/{tid} 用过期 version expected=1 但当前 version=2 拒 409 CONFLICT（design §3.2 乐观锁 + §13.2 + tests.md E11 + C6）
- [P0] activity_log INSERT 抛错时整个删 team 事务回滚（teams + team_members 不删）500（design §8.7 失败整体回滚 + tests.md E14 + Q13.2 R-X3）
- [P0] transfer-ownership 流程中第 4 步 INSERT activity_log 抛错时第 3 步 UPDATE 全回滚（teams.version 不变）（design §8.7 + tests.md E14 衍生）
- [P0] CROSS_TEAM_MOVE_FORBIDDEN：POST /move-team target=B 但 project 当前 team_id=A（非 null）拒 422（design §13.1 Q7 + tests.md E10）
- [P0] TEAM_MEMBER_DUPLICATE：POST /api/teams/{tid}/members 重复加同 user 拒 409 detail.{team_id, user_id}（design §3.2 UniqueConstraint + tests.md E8）
- [P1] GET /api/teams/{随机不存在 UUID} 拒 404 TEAM_NOT_FOUND（design §13.1 + tests.md E1）
- [P1] DELETE /api/teams/{tid}/members/{随机 user UUID} 拒 404 TEAM_MEMBER_NOT_FOUND（design §13.1 + tests.md E7）
- [P1] transfer 给非 team 成员 new_owner_id 不在 team_members 拒 422 TEAM_OWNER_REQUIRED reason="transfer_target_not_member"（design §13.1 + tests.md E6）
- [P1] PATCH /api/teams/{tid}/members/{uid} role 传 "owner" 字面值 Pydantic 拒 422 VALIDATION_ERROR（schema 限 Literal["admin","member"]）（design §7.2 + tests.md P13）
- [P1] POST /api/teams { name: 101 字符 } 拒 422 VALIDATION_ERROR Pydantic max_length（design §7.2 + tests.md E13）
- [P1] DELETE /api/teams/{tid} 第二次调（已删）拒 404 TEAM_NOT_FOUND（design §11.1 UX 等价幂等）
- [P1] Service 层 IntegrityError 必区分约束名 uq_teams_creator_name → TeamNameDuplicateError / uq_team_members_team_user → TeamMemberDuplicateError（design §14.5 范式复用清单 M05 立 + 06-design-principles 清单 6）

### 4. 权限 / Auth

- [P0] 未登录访问任何 /api/teams 端点拒 401 UNAUTHENTICATED（design §8.5 require_user 合并入口 + 06-design-principles 原则 5）
- [P0] T1 U1 既非 team_members 也非 ProjectMember 关联 T 时 GET /teams/{T} 拒 404 TEAM_NOT_FOUND 不 leak 存在性（design §8.1 L1 + tests.md T1）
- [P0] L2 assert_team_role(admin)：member 尝试 PATCH /teams/{tid} 改 name 拒 403 TEAM_PERMISSION_DENIED detail.{required="admin", current="member"}（design §8.1 + tests.md P11）
- [P0] L2 assert_team_role(owner)：admin 尝试 POST /transfer-ownership 拒 403 TEAM_PERMISSION_DENIED detail.{required="owner", current="admin"}（design §8.1 + tests.md P12）
- [P0] L2 assert_team_role(target, admin)：non-team-member 尝试 POST /api/projects/{pid}/move-team 加入 target_team 拒 403 TEAM_PERMISSION_DENIED（design §8.1 + tests.md P15 + design §7 双 role 校验 F1.10）
- [P0] L2 assert_project_role(owner)：project 非 owner 用户尝试 move-team 拒 403（design §7 端点拆分 + tests.md P15 衍生）
- [P0] resolve_project_role P1 仅 team baseline member → viewer / P2 admin → editor / P3 owner → owner（design §8.6 Q2=B 三角色映射 + tests.md P1-P3）
- [P0] resolve_project_role P5 双重叠加取 max(member→viewer, editor) = editor（design §8.6 嵌套式 + tests.md P5）
- [P0] resolve_project_role P7 双重叠加取 max(owner→owner, viewer) = owner（design §8.6 + tests.md P7）
- [P0] resolve_project_role P8 都无 (无 team_role 无 pm_role) 返 None 拒访问（design §8.6 + tests.md P8）
- [P1] resolve_project_role P4 仅 ProjectMember viewer 无 team 关联返 viewer（design §8.6 + tests.md P4）
- [P1] resolve_project_role P9 project 不属 team（team_id IS NULL 个人 project）仅 ProjectMember 路径返 viewer（design §8.6 + tests.md P9）
- [P1] T5 U1 被 DELETE from team T 后立即 GET /projects/{P}（P 属 team T，U1 不在 ProjectMember）拒 404/403 权限实时算不依赖 token 失效（design §8.5 token_invalidated_at 不扩展 + tests.md T5）
- [P1] P14 admin 尝试 demote 最后 owner（非 transfer 流程）拒 422 TEAM_OWNER_REQUIRED reason="last_owner_demote"（design §4.2 + tests.md P14）

### 5. Tenant 隔离

- [P0] T3 L3 SQL 兜底注入：U1 是 team A 的 owner 直接构造 query 访问 team B 下 project 的 dimension_records 返空集（design §9.2 user_accessible_project_ids_subquery + tests.md T3）
- [P0] T4 U1 在 team T 但不在 P 的 ProjectMember，team T 下有 project P → U1 通过 L3 注入并集可访问 P 下 nodes（design §9.2 union 子查询 + tests.md T4）
- [P0] cross-tenant 404：U1 非 team T 成员尝试任何写端点（POST member / PATCH team / DELETE team）拒 404 TEAM_NOT_FOUND 不 leak 存在性（design §14.5 范式复用 M02-M19 cross-tenant 404 + tests.md T1）
- [P1] T6 M18 embedding backfill / monitor cron worker 系统级跑 backfill 走 ADR-003 规则 4 不引用 user_accessible_project_ids_subquery 不被 tenant 过滤（design §9.3 豁免 + tests.md T6）
- [P1] M15 activity_log write 路径不走 user_accessible_project_ids_subquery（M15 own，写入由 Service 主动调用非用户查询入口）（design §9.3 豁免）
- [P1] M20 自身 teams / team_members 操作走 team_members 子查询而非 user_accessible_project_ids（语义不同：teams 不是 project）（design §9.3 豁免）
- [P1] user_accessible_project_ids_subquery union 路径：ProjectMember WHERE user_id=X UNION projects WHERE team_id IN (team_members WHERE user_id=X)（design §9.2 helper impl）

### 6. 并发 / 乐观锁

- [P0] C1 同时 transfer owner：U1 把 owner 同时转给 U2 和 U3 → teams.version 乐观锁守护 / 先到 commit 成功 后到 409 CONFLICT / 最终 owner 唯一（design §5.3 + §8.7 第 6 步 + tests.md C1）
- [P0] C2 同时 demote 最后 owner：A 和 B 都 demote owner U1 → 一个成功一个 422 TEAM_OWNER_REQUIRED / Service SELECT FOR UPDATE team_members WHERE role='owner' 守护（design §5.3 + tests.md C2）
- [P0] C3 删 team 与加 member 并发：A DELETE /teams/{tid} 持锁 B POST /members 阻塞 → A 完成后 B 报 404 TEAM_NOT_FOUND（design §5.3 RESTRICT FK + tests.md C3）
- [P0] C6 同时改 team name version 冲突：两人都读到 version=1 → 第一个 version=2 成功 / 第二个 WHERE version=1 影响行数 0 → 409 CONFLICT（design §5.3 + tests.md C6 + E11）
- [P1] C4 同时 promote 同一 user：A 和 B 都把 U→admin → UniqueConstraint(team_id, user_id) 守护 + 最后写入获胜（role 一致即可）（design §5.3 + tests.md C4）
- [P1] C5 跨 team 移 project 与删 team A 并发：A 先 commit 解绑 → B 删成功；B 先获锁 → A 解绑后 B 拒 422 TEAM_HAS_PROJECTS（design §5.3 + tests.md C5）
- [P1] F3.10 删 user U（U 是 team T 唯一 owner）与 transfer 并发：M01 入口 assert_user_has_no_owned_teams + assert U 不是 last team owner 拒 422 USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER（design §5.3 F3.10 + tests.md C2 衍生 + M01 baseline-patch 提议）

### 7. 数据完整性

- [P0] teams.creator_id FK ondelete=RESTRICT：删 user 时若 U 是任何 team creator 拒（M01 baseline 提议 422 USER_HAS_OWNED_TEAMS）（design §3.2 + §13.2 + design §5.3 F3.10）
- [P0] team_members.team_id FK ondelete=RESTRICT：删 teams 行前 Service 必须先 DELETE team_members（直接 DELETE teams 触发 FK violation）（design §3.2 §8.7 + tests.md G8）
- [P0] team_members.user_id FK ondelete=CASCADE：删 user 行时其所有 team_members 行自动级联清空（与 M01 用户删除范式对齐）（design §3.2）
- [P0] projects.team_id FK ondelete=RESTRICT：删 team 前 SELECT projects WHERE team_id 必须为空（B14 archived 自动解绑除外）（design §3.3 baseline-patch + tests.md B8）
- [P0] team_members.role CHECK 约束 IN ('owner','admin','member')：INSERT role='foo' 失败（design §3.2 R3-2 三重防护 + 06-design-principles 原则 5）
- [P0] teams.name CHECK char_length(name) >= 1 AND <= 100：INSERT name=101 字符失败（design §3.2 + tests.md B1）
- [P0] teams.version CHECK >= 1：INSERT version=0 失败（design §3.2）
- [P0] UniqueConstraint uq_teams_creator_name(creator_id, name)：INSERT 同 creator 同 name 第二行失败 → IntegrityError → TeamNameDuplicateError 409（design §3.2 + tests.md E2）
- [P0] UniqueConstraint uq_team_members_team_user(team_id, user_id)：重复加同 user 失败 → IntegrityError → TeamMemberDuplicateError 409（design §3.2 + tests.md E8）
- [P1] Index ix_team_members_user_team(user_id, team_id) 存在（反向索引：高频 U 所在所有 team 查询）（design §3.2）
- [P1] R3-2 三重防护：team_members.role 模型层 Mapped[TeamRole] + 数据库 String(20) + CheckConstraint 三方同步（design §3.2 + 06-design-principles）
- [P1] Team / TeamMember 不继承 TimestampMixin 直接声明 DateTime 列（created_at / updated_at / joined_at server_default=func.now()）（design frontmatter helpers.models.mixins=no_dependency + §3.2）
- [P1] Alembic m20_team 迁移正向 upgrade head 创建 teams + team_members + ALTER projects ADD CONSTRAINT fk_projects_team 全成功（design §3.4）
- [P1] ck_activity_log_action_type CHECK 扩 10 个 team_* 枚举：INSERT action_type='unknown_team_event' 失败（design §3.4 §10.1 + 14.5 范式复用 M15）
- [P1] ck_activity_log_target_type CHECK 扩 "team"：INSERT target_type='foo' 失败（design §3.4）

### 8. UI / UX

- [P1] 团队列表 UI 附 creator 名缓解 transfer 后语义偏（teams.creator_id 永不变 vs 当前 owner 由 team_members 单独查）（design §1 边界灰区 T4 trade-off）
- [P1] 删 team UI 二次确认（防误删，Q11=A 不引入 P4 一次性 token）（design §8.5 第 2 段）
- [P1] 移成员 UI 提醒：响应 residual_project_members 列表提示「U 仍以 ProjectMember 身份保留对 N 个 project 的访问权」（design §1 Q3 软切断 + tests.md G9）
- [P1] B5b transfer 后 creator 想再用同名前端文案「您之前创建过 X（已转让给他人）」基于 detail.creator_id 区分（design §1 边界灰区 + tests.md B5b）
- [P1] CONFLICT 前端 toast 「数据已被他人修改，请刷新后重试」+ 触发刷新（design §3.2 乐观锁 + 06-design-principles 原则 5 R5-2）
- [P2] AC2 一键迁移前端进度条 N/100 + 失败重试由前端维护（design §12 + tests.md B12）

### 9. activity_log 事件完备性

- [P0] 10 个 team_* / project_*_team action_type 全过去式（team_created / team_renamed / team_description_changed / team_deleted / team_member_added / team_member_removed / team_member_promoted_admin / team_member_demoted_member / project_joined_team / project_left_team）符合 R14 ci-lint 守护（design §10.1 + §14.5 范式复用 M16 R14）
- [P0] team_deleted target_type='team' target_id=team_id（不是 user_id，与 G8 测试断言对齐）（design §10.3 R10-1 字段约束）
- [P0] team_member_removed × N 条 target_id=team_id（聚焦"在哪个 team 里删了人"非 user 自己事件）+ metadata.user_id 必填 + metadata.reason='team_deleted' 或 'manual' 区分（design §10.3）
- [P0] 删 team N+1 条 activity_log 严格独立写入（禁汇总成 1 条带 member_user_ids 数组的 metadata）违反 R10-1（design §10.3 禁止做法）
- [P0] 删 team 写入顺序：先 1 条 team_deleted 后 N 条 team_member_removed 按 team_members.joined_at 升序（design §10.3 写入顺序）
- [P0] transfer-ownership 同事务 2 条事件 + 同 correlation_id（uuid4 Service 入口生成同流程共享）F2.9（design §10.1 + §8.7 + tests.md G4）
- [P0] 删 team N+1 条事件同 correlation_id 共享（F2.9）让审计跨条目硬关联不靠 timestamp 推断（design §10.1 F2.9 + §8.7）
- [P1] team_member_removed metadata 必填 residual_project_count + residual_project_ids[:10]（manual 和 team_deleted 路径都填）F2.4 让 audit 追溯软切断后残留 ProjectMember 状况（design §10.1 F2.4）
- [P1] team_renamed metadata.{from_name, to_name} 字段集（design §10.1）
- [P1] team_description_changed metadata.{from_description, to_description}（design §10.1 拆分 Q10.1②）
- [P1] team_member_promoted_admin to_role 含 "admin" 或 "owner"（transfer 中升 owner 也用此 action_type，命名偏差 F3.7 已记 README 设计回看触发器）（design §10.1 注解 + §16 F3.7）
- [P1] team_member_demoted_member to_role 含 "member" 或 "admin"（transfer 中降 admin 也用此）（design §10.1 注解）
- [P1] project_joined_team target_type='project' target_id=project_id + metadata.team_id（design §10.1）
- [P1] project_left_team target_type='project' + metadata.from_team_id + 自动解绑路径 detail.reason='team_deleted_archived_auto_unbind'（design §10.1 + §1 F2.3）
- [P1] M01 所有 M20 事件不写 auth_audit_log 仅写 activity_log（design §10.2 R10-2 主规则）
- [P1] M15 list_for_team(team_id, user_id) DAO 入口 F2.5 修复：team_* 事件 8/10 类无 project_id 原 list_for_project 召不回 → 新增 WHERE target_type='team' AND target_id=:tid + L1 require_team_access(member)（design §9.1 F2.5）

### 10. 跨模块契约 / 横切

- [P0] M02 ProjectDAO.list_for_user 双重过滤：内层 WHERE id IN user_accessible_project_ids_subquery 保证 tenant 隔离 + 外层 OR owner_id=:uid 保证个人 project 召回（design §16 F2.13 + Phase 2 T2/T4 验证）
- [P0] L3 SQL 注入升级横切 M03-M19：既有 DAO 在 set_tenant_context 切换前后 baseline 测试 1512 PASS 不破（design ADR-005 §3.2 + §14.5 R-X5 实证）
- [P0] R-X3 共享外部 db: Session：delete_team / transfer_ownership 接受 Router 持有的 transaction context 不在 Service 内部 commit/rollback（design §6 + §8.7 Q13.2）
- [P0] M02 baseline-patch projects.space_id → team_id RENAME + FK RESTRICT 启用 ALTER 在 Alembic upgrade head 后生效 + 既有 project 行 team_id IS NULL 保留个人语义（design §3.3 + §3.4）
- [P0] M15 baseline-patch ActionType 10 个 team_* 枚举 + TargetType "team" 4 处同步（model tuple + schema StrEnum + CHECK constraint + Alembic）M15 own 表（design §14.5 范式复用 M15 横切表 owner enum + 关联产出 §15）
- [P1] M15 ErrorCode 表扩 8 个 TEAM_* 注册（TEAM_NOT_FOUND / TEAM_NAME_DUPLICATE / TEAM_HAS_PROJECTS / TEAM_OWNER_REQUIRED / TEAM_MEMBER_NOT_FOUND / TEAM_MEMBER_DUPLICATE / TEAM_PERMISSION_DENIED / CROSS_TEAM_MOVE_FORBIDDEN）字面对账 design §13.1 ↔ exceptions.py http_status ↔ tests.md status code 矩阵（design §14.5 元教训 #19 + §16 F1.11）
- [P1] AppError 子类映射：TeamNotFoundError(404) / TeamNameDuplicateError(409) / TeamHasProjectsError(422) / TeamOwnerRequiredError(422) / TeamMemberNotFoundError(404) / TeamMemberDuplicateError(409) / TeamPermissionDeniedError(403) / CrossTeamMoveForbiddenError(422)（design §13.3）
- [P1] M01 baseline-patch 提议：删 user 入口 assert_user_has_no_owned_teams + USER_IS_LAST_TEAM_OWNER + USER_HAS_OWNED_TEAMS 422（design §5.3 F3.10 + §13.2）
- [P1] write_event 异常传播 e2e 字面验：monkeypatch raise 时事务整体回滚（design §14.5 范式复用 M16 立）
- [P2] M18 embedding backfill DAO 走 ADR-003 规则 4 豁免不引用 user_accessible_project_ids_subquery（design §9.3 + frontmatter helpers）

### 11. 异步 / 幂等显式 N/A

- [P1] §11.1 idempotency_key 显式声明 N/A：所有操作同步 CRUD 无 Queue 重投递场景 / UniqueConstraint 守护 UX 等价幂等（design §11.1 + 06-design-principles 清单 4）
- [P1] §11.2 project_id 参与 idempotency key 计算 显式 N/A（M20 无 idempotency key）（design §11.2 + 14.5 范式复用 M17 idempotency 含 project_id N/A）
- [P1] §12 同步模块显式声明：4 子模板（§12A SSE / §12B fire-and-forget / §12C Queue / §12D embedding）全部 N/A（design §12 排除表 + 06-design-principles 原则 5 异步）
- [P1] §8.3 Queue 消费者侧权限 N/A + §8.4 WebSocket 重校 N/A（design §8.3 §8.4）
- [P1] R-X1 第二实例 compensation_session helper N/A（M20 同步无补偿形态，M17 立的范式不适用）（design §14.5）

### 12. 性能（F3.5 锚定 Phase 2 实施前必跑）

- [P1] C7 user_accessible_project_ids_subquery 压测：U 加入 20 个 team 每 team 50 个 project（共 1000 project）在 M03-M19 各 list 入口 P95 < 100ms 通过（design §5.3 F3.5 + tests.md C7）
- [P2] C7 P95 > 100ms 触发 ADR-005 §4 T1 Redis 缓存路径 + 实施 5 处失效路径（U 加入/移出 team / 删 team / project 加入/移出 team）（design §1 F2.2 超阈值触发器 + ADR-005）
- [P2] 单 team 成员数 > 200 触发删 team 异步化决策（当前同步 N+1 条 activity_log 写入超阈值）（design §1 F2.2 超阈值触发器）
- [P2] 用户所在 team 数 > 20 触发 ADR-005 §4 T1 Redis 缓存决策（L3 SQL 子查询 team_members WHERE user_id 性能基线）（design §1 F2.2 超阈值触发器）
