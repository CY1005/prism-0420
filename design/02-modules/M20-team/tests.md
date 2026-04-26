---
title: M20 团队 - 测试场景
status: draft
owner: CY
created: 2026-04-26
module_id: M20
parent_design: ./00-design.md
---

# M20 团队 - 测试场景（§14）

> 6 类：Golden / 边界 / 并发 / Tenant / 权限 / 错误。覆盖 Q0-Q15 全部决策落地点。

---

## G — Golden Path（正向主流程）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建 team | U1 POST /api/teams { name: "Engineering", description: "X" } | 201 + 返回 TeamRead；DB 写入 teams + team_members(creator=U1, role=owner) 单事务；activity_log 写 1 条 team_created + 1 条 team_member_added |
| G2 | 加成员 | U1 (admin) POST /api/teams/{tid}/members { user_id: U2, role: "member" } | 201；DB 写入 team_members；activity_log 写 1 条 team_member_added (detail.role="member") |
| G3 | 升级 admin | U1 PATCH /api/teams/{tid}/members/{U2} { role: "admin" } | 200；DB role 改 admin；activity_log 写 1 条 team_member_promoted_admin (detail: from_role=member, to_role=admin) |
| G4 | 转让 owner | U1 (owner) POST /api/teams/{tid}/transfer-ownership { new_owner_id: U2 } | 200；单事务原子：U1 → admin + U2 → owner；activity_log 同事务写 2 条（demoted + promoted），actor 都是 U1，timestamp 相同 |
| G5 | 改 team 名 | U1 (admin) PATCH /api/teams/{tid} { name: "Eng-renamed", version: 1 } | 200；teams.version 自增至 2；activity_log 写 1 条 team_renamed (detail: from_name, to_name) |
| G6 | project 加入 team | U1 (project owner + team admin) PATCH /api/projects/{pid} { team_id: tid }（前提 project.team_id IS NULL） | 200；project.team_id 改；activity_log 写 1 条 project_joined_team (detail: team_id=tid) |
| G7 | project 移回个人 | U1 PATCH /api/projects/{pid} { team_id: null }（前提 project.team_id = tid） | 200；project.team_id 改 null；activity_log 写 1 条 project_left_team (detail: from_team_id=tid) |
| G8 | 删 team（前置已清空） | U1 (owner) DELETE /api/teams/{tid}（前提 projects WHERE team_id=tid 为空） | 204；Service 5 步执行：① 校验 projects 空 ② 查 N 个 team_members ③ 写 N 条 team_member_removed (reason="team_deleted") + 1 条 team_deleted ④ 删 N 条 team_members ⑤ 删 1 条 teams；同事务原子 |
| G9 | 软切断移成员 | U1 (admin) DELETE /api/teams/{tid}/members/{U3}（U3 在 team 下 2 个 project 有 ProjectMember 记录） | 200；team_members 删 1 行，project_members 不动；响应 `{removed_user_id: U3, residual_project_members: [pid1, pid2], residual_count: 2}`；activity_log 写 1 条 team_member_removed (detail.reason="manual") |
| G10 | 列出 U 所在所有 team | U1 GET /api/teams | 200；返回 U1 通过 team_members 关联的所有 team（含 member_count 聚合字段） |

---

## B — 边界（极值 / 空值 / 临界态）

| ID | 场景 | 输入 | 期望 |
|----|------|------|------|
| B1 | name 长度边界 | name = "" / "a" / 100 字符 / 101 字符 | 空 / 101 → 422 VALIDATION_ERROR；1 / 100 → 201 |
| B2 | description 为 null | POST /api/teams { name: "X", description: null } | 201；DB description = NULL |
| B3 | team_members 为 0 删 team | 创建 team 后立即 DELETE（仅 creator 一个 member） | 200；删 team 流程仍走 5 步：N=1 → 写 1 条 team_member_removed (reason="team_deleted") + 1 条 team_deleted |
| B4 | transfer 给自己 | U1 (owner) POST /transfer-ownership { new_owner_id: U1 } | 422 TEAM_OWNER_REQUIRED (detail.reason="transfer_target_not_member" 或专门处理"target_is_self") —— 或 Service 层接受成 noop（设计阶段倾向拒绝，归 Phase 2 实施时定） |
| B5 | 同 creator 不同 team 同名 | U1 创建两个 team 都叫 "X" | 第二个 409 TEAM_NAME_DUPLICATE |
| B6 | 不同 creator 同名 team | U1 创建 "X" + U2 创建 "X" | 两个都 201（uq_teams_creator_name 仅同 creator 唯一） |
| B7 | team 下 0 个 project 时删 team | 仅 creator 是 member，无 project | 204 |
| B8 | team 下 N 个 project 时删 team | projects WHERE team_id=tid 有 5 个 | 422 TEAM_HAS_PROJECTS, detail: project_count=5, project_ids=[...前 10 个] |
| B9 | 移成员但 U 在 0 个 project 有 ProjectMember | U3 在 team 下无 ProjectMember 记录 | 200；residual_count=0, residual_project_members=[] |
| B10 | 移成员但 U 在 100 个 project 有 ProjectMember | U3 在 team 下 100 个 project 有 ProjectMember | 200；residual_count=100, residual_project_members 完整列出（不截断） |
| B11 | 创建 team 时 creator 自动成为 owner | 单事务原子：teams INSERT + team_members INSERT(creator_id, role=owner) | 失败任一步整体回滚 |

---

## C — 并发（竞态分析对应 §5.3）

| ID | 场景 | 期望 |
|----|------|------|
| C1 | 同时 transfer owner | U1 同时把 owner 转给 U2 和 U3 | teams.version 乐观锁守护：先到的 commit 成功，后到的 409 CONFLICT；最终 owner 唯一 |
| C2 | 同时 demote 最后 owner | A demote owner U1，B 也 demote owner U1（team 仅 1 个 owner） | 一个成功 + 一个 422 TEAM_OWNER_REQUIRED；Service 层 SELECT FOR UPDATE team_members WHERE role='owner' 守护 |
| C3 | 删 team 与加 member 并发 | A DELETE /teams/{tid}，B POST /teams/{tid}/members 同时 | RESTRICT FK + 单事务串行：A 持 teams 行锁期间 B 阻塞；A 完成后 B 报 404 TEAM_NOT_FOUND |
| C4 | 同时 promote 同一 user | A 把 U → admin，B 也把 U → admin | UniqueConstraint(team_id, user_id) 守护 + 最终一致；最后写入获胜（role 字段一致即可） |
| C5 | 跨 team 移 project 与删 team A 并发 | A 把 project 移出 team T，B 同时删 team T | 若 A 先 commit：B 删 team T 成功（projects 空）；若 B 先获锁：A 解绑后 B 拒 422 TEAM_HAS_PROJECTS |
| C6 | 同时改 team name 触发 version 冲突 | 两人读到 version=1 后都 PATCH | 第一个写 version=2 成功；第二个 WHERE version=1 影响行数 0 → 抛 ConflictError → 409 CONFLICT |

---

## T — Tenant 隔离（Q4 + Q5 三层防御）

| ID | 场景 | 期望 |
|----|------|------|
| T1 | U1 不在 team T 不能 GET /teams/{T} | U1 既无 team_members 也无 ProjectMember 关联 T | 404 TEAM_NOT_FOUND（不 leaked 存在性） |
| T2 | U1 在 team T 是 member 可 GET /teams/{T} | L1 require_team_access(min_role=member) 通过 | 200 |
| T3 | L3 SQL 兜底注入：U1 直接构造 query 访问跨 team project | U1 是 team A 的 owner，尝试访问 team B 下 project 的 dimension_records | DAO 层 user_accessible_project_ids_subquery 排除 → 返回空集 |
| T4 | M03 NodeDAO.list_for_project 在 team 加入后召回扩大 | U1 在 team T，team T 下有 project P；U1 不在 P 的 ProjectMember | L3 注入并集 = ProjectMember(空) ∪ projects WHERE team_id IN team_members(T)；P 在并集内 → U1 可访问 P 下 nodes |
| T5 | 移出 team 后即时失访 project | U1 在 team T → DELETE U1 from team T → U1 立即 GET /projects/{P}（P 属 team T，U1 不在 ProjectMember） | 404 / 403（权限实时算，不依赖 token 失效） |
| T6 | M18 embedding backfill 不走 helper | embedding worker 系统级跑 backfill | 走 ADR-003 规则 4，不引用 user_accessible_project_ids_subquery；不被 tenant 过滤 |

---

## P — 权限（Q1 + Q2 嵌套式 max + 三层防御）

| ID | 场景 | team_role | project_member_role | resolve_project_role 期望 |
|----|------|-----------|---------------------|--------------------------|
| P1 | 仅 team baseline | member | (无) | viewer |
| P2 | 仅 team baseline | admin | (无) | editor |
| P3 | 仅 team baseline | owner | (无) | owner |
| P4 | 仅 ProjectMember | (无) | viewer | viewer |
| P5 | 双重叠加取 max | member (→ viewer) | editor | editor（max(viewer, editor) = editor） |
| P6 | 双重叠加取 max | admin (→ editor) | viewer | editor（max(editor, viewer) = editor） |
| P7 | 双重叠加取 max | owner (→ owner) | viewer | owner |
| P8 | 都无 | (无) | (无) | None（拒访问） |
| P9 | project 不属 team（个人 project） | N/A | viewer | viewer（仅 ProjectMember 路径） |
| P10 | project 不属 team + 无 ProjectMember | N/A | (无) | None |

| ID | 场景 | 期望 |
|----|------|------|
| P11 | member 尝试改 team name | L2 assert_team_role(admin) → 403 TEAM_PERMISSION_DENIED (detail: required="admin", current="member") |
| P12 | admin 尝试 transfer owner | L2 assert_team_role(owner) → 403 TEAM_PERMISSION_DENIED (detail: required="owner", current="admin") |
| P13 | admin 尝试 promote member 直接到 owner | PATCH /members/{uid} { role: "owner" } → Pydantic 拒 422（schema 限 Literal["admin", "member"]） |
| P14 | admin 尝试 demote owner（非 transfer 流程） | 拒 422 TEAM_OWNER_REQUIRED detail.reason="last_owner_demote"（如 owner 是最后一个）或 Pydantic 拒（role 不能直接到 owner→x，需走 transfer） |
| P15 | non-team-member 尝试加 project 到 team | L2 assert_team_role(target_team, admin) → 403 TEAM_PERMISSION_DENIED |

---

## E — 错误（ErrorCode 全 8 个 + Pydantic + lifecycle）

| ID | 场景 | ErrorCode | HTTP |
|----|------|-----------|------|
| E1 | GET /teams/{随机 UUID} | TEAM_NOT_FOUND | 404 |
| E2 | 同 creator 创建同名 team | TEAM_NAME_DUPLICATE | 409 |
| E3 | 删 team 时 projects 非空 | TEAM_HAS_PROJECTS | 422 |
| E4 | demote 最后 owner | TEAM_OWNER_REQUIRED (reason="last_owner_demote") | 422 |
| E5 | remove 最后 owner | TEAM_OWNER_REQUIRED (reason="last_owner_remove") | 422 |
| E6 | transfer 给非 team 成员 | TEAM_OWNER_REQUIRED (reason="transfer_target_not_member") | 422 |
| E7 | DELETE /teams/{tid}/members/{随机 UUID} | TEAM_MEMBER_NOT_FOUND | 404 |
| E8 | POST /teams/{tid}/members 重复加 user | TEAM_MEMBER_DUPLICATE | 409 |
| E9 | member 尝试 admin 操作 | TEAM_PERMISSION_DENIED | 403 |
| E10 | PATCH /projects/{pid} 从 team A 直接到 team B | CROSS_TEAM_MOVE_FORBIDDEN | 422 |
| E11 | PATCH /teams/{tid} 用过期 version | CONFLICT（复用全局） | 409 |
| E12 | POST /teams { name: "" } | VALIDATION_ERROR（Pydantic min_length=1） | 422 |
| E13 | POST /teams { name: 101 字符 } | VALIDATION_ERROR | 422 |
| E14 | activity_log 写入失败回滚整个事务 | 模拟 activity_log INSERT 抛错 → teams 删除整体回滚 | 500 |

---

## 测试覆盖度陈述

| 决策点 | 覆盖测试 ID |
|--------|------------|
| Q0/Q1/Q2 嵌套 + 映射 | P1-P10 |
| Q3 软切断 | G9, B9, B10 |
| Q4 单 tenant | T3, T4 |
| Q5 三层防御 | T1-T6, P11-P15 |
| Q6 同步 | G1-G10 全覆盖（无异步路径） |
| Q7 跨 team 禁止 | E10 |
| Q8 强制前置迁出 | B7, B8, E3, C5 |
| Q9 乐观锁 | C1, C6, E11 |
| Q10/Q10.1 细粒度事件 | G1-G9 各步 activity_log assertion |
| Q11 auth P1 | T5（移出 team 即时失访）、所有 endpoint 默认走 require_user |
| Q12 ErrorCode | E1-E14 |
| Q13/Q13.1 schema | B1-B6, B11 |

**覆盖陈述**：6 类共 51 个测试用例；Q0-Q15 全部决策有至少 1 个测试 case 覆盖；critical path（G1-G10 + C1-C6 + E1-E14）必须 100% 通过才允许 accept。

---

## 待 Phase 2 实施时补充

- 实际 SQL 注入子查询性能测试（user_accessible_project_ids_subquery 在 N=1000 project 时的耗时）
- L3 注入对 M03-M19 的回归测试（基于公共 helper 编写测试模板，各模块复用）
- transfer owner 在高并发下的 version 冲突重试策略（Phase 2 决定是否加自动重试）
