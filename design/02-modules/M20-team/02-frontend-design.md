---
title: M20 团队 - 前端设计（Phase 2.2 子片 4 轻量草案）
status: accepted
owner: CY
created: 2026-05-09
accepted: 2026-05-09
module_id: M20
prism_ref: F20
references:
  parent_design: ./00-design.md
  adrs:
    - ADR-001 §6.3（前端继承策略 / M20 团队页 Prism 无 / 全新写）
    - ADR-005（team 架构 / Q0-Q15 / projects.space_id→team_id baseline-patch）
  spec:
    - design/01-engineering/06-frontend-spec.md §3 SSR auth（α-P1 链路）
  audit:
    - design/audit/p22-pilot-template-validation.md §3-4（R 范式 5 数据点）
---

# M20 团队 - 前端设计（轻量草案）

> **scope 自决**：子片 4 启动期 ls 穷举发现 prompt 字面 6 路由其中 3 路由依赖的 backend 能力缺位（GET members / 候选 owner 检索 / soft-delete 已被 design §3 Q8=B 字面决为 hard delete + RESTRICT FK）。按 feedback_decision_layering + feedback_self_decide_no_ask 自决收 scope 到 **3 路由 + 9 actions**，4 项 backend gap 进 cross-sprint pool `P22-4-backend-gap`（默认 Phase 2.3 集成期合并）。
> 
> 此 design 仅描述子片 4 真接的范围，不预设 Phase 2.3 的扩展方案。

---

## 1. 路由清单（3 路由 / 单页 cards 合并形态）

| 路径 | 类型 | 说明 |
|---|---|---|
| `/teams` | Server Component | 列出我所在的 team（owner+admin+member 自动并集 / backend list_teams） |
| `/teams/new` | Client Component | 新建 team 表单（zod validator + Server Action） |
| `/teams/[teamId]` | Client Component | 详情页：team 元信息 + 编辑 name/description（admin+owner）+ 成员管理 cards（add by user_id / change role / remove）+ 转让所有权（owner only）+ 删除 team（owner only） |

**为什么合并到单页**：M20 design §3 Q8=B 决策 hard delete + RESTRICT FK / 删除前必前置迁出，无 soft-delete + restore，独立 `/danger` 路由意义稀薄；`/transfer` 和 `/members` 被 backend gap 卡住（无候选 owner 下拉数据源、无 GET members endpoint），合到主页 cards 比独立路由更诚实。

## 2. 组件树

```
/teams (Server Component, withAuthRedirect)
├─ TeamListCard × N（id / name / description / member_count / created_at + Link to detail）
└─ "+ 新建" button → /teams/new

/teams/new (Client)
├─ TeamForm（zod createTeamSchema / Server Action createTeam）
└─ Breadcrumb: 团队 / 新建

/teams/[teamId] (Client / 主入口拉数据后 hydrate)
├─ TeamHeader（name + description + 编辑按钮 disabled by RBAC）
├─ TeamInfoCard（creator_id / member_count / created_at / version 显示）
├─ TeamEditCard（admin+owner 可见 / inline name+description + 乐观锁 version）
├─ TeamMembersCard
│   ├─ "添加成员"（admin+owner 可见 / by user_id 输入框 / 不带候选下拉 / Phase 2.3 接 user 检索）
│   └─ ⚠️ 提示：「成员列表展示等 Phase 2.3 backend GET members endpoint 上线后启用（cross-sprint pool P22-4-backend-gap）」
├─ TeamTransferCard（owner only / 二次确认 dialog / 输入 new_owner_id / 不带候选下拉）
└─ TeamDangerCard（owner only / 删除 team / 二次确认 dialog / hard delete / 提示「先迁出所有 project」）
```

## 3. RBAC 状态机（design §6 R-X3 + 子片 4 前端守卫）

> **关键约束**：M20 backend `TeamRead` schema 不返回当前用户在该 team 内的角色，前端 RBAC 守卫只能基于 `creator_id == me.id` 推断 owner，admin/member 无法区分。

| 角色 | 列表页 | 详情查看 | 编辑 name/description | 添加成员 | 改成员角色 | 移除成员 | 转让所有权 | 删除 team |
|---|---|---|---|---|---|---|---|---|
| owner（`creator_id == me.id`） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| admin（推断不到 / 子片 4 退化为 viewer） | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| member（推断不到 / 子片 4 退化为 viewer） | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

> **子片 4 退化说明**：admin/member 在 backend 真实有写权限（design §6.3 / R-X3 5-step），但前端无角色信息只能按 viewer 展示按钮。**真触发后端 403** 由 `actionError(error)` 透出 toast / 不静默吞错（errors.ts.actionError + spec 06 §3 字面）。Phase 2.3 backend 加 `team_role` 字段或 GET `/teams/{tid}/me-role` endpoint 后启用真守卫（cross-sprint pool）。

## 4. 错误处理表（M20 design §11 ErrorCode + 前端 fallback）

| backend ErrorCode | 触发场景 | 前端处理 |
|---|---|---|
| `UNAUTHORIZED` (401) | refresh cookie 过期 | `actionError` → `redirect("/login")`（errors.ts 立修自动覆盖） |
| `TEAM_NOT_FOUND` (404) | URL 中 teamId 无效 / 已被删 | toast + 返回 /teams |
| `TEAM_PERMISSION_DENIED` (403) | 非 owner/admin 操作 | toast 「无权限执行此操作」 |
| `TEAM_NAME_DUPLICATE` (409) | 同名 team | inline 表单错误提示 |
| `TEAM_HAS_PROJECTS` (422) | 删 team 时尚有 project | dialog 列出阻塞原因 + 跳 /projects 引导先迁出 |
| `TEAM_OWNER_REQUIRED` (422) | transfer 失败 / target 非 admin/member | toast 「目标用户必须先是团队成员」 |
| `TEAM_MEMBER_NOT_FOUND` (404) | remove/update 不存在的成员 | toast |
| `TEAM_MEMBER_DUPLICATE` (409) | add 已存在的成员 | toast |
| `CONFLICT` (409) | 乐观锁 version 不匹配 | toast 「内容已被他人修改 / 请刷新」+ refresh page |
| `VALIDATION_ERROR` (400) | 入参校验失败 | inline 表单错误 |
| `USER_HAS_OWNED_TEAMS` / `USER_IS_LAST_TEAM_OWNER` | M01 baseline-patch 删用户场景 | M20 前端不直接触发 |
| `PROJECT_ARCHIVED` (422) | move-team 时 project archived | toast |
| `CROSS_TEAM_MOVE_FORBIDDEN` (422) | team A → team B 直跳 | toast 「请先移回个人再加入新 team」 |

## 5. 子片 4 不做（cross-sprint pool P22-4-backend-gap）

1. **GET `/api/teams/{tid}/members`**：列成员名单 + role + user_name（M20 backend 当前只回 member_count）
2. **GET 候选用户检索 endpoint**：transfer dialog + add member 下拉数据源（current 只能 by 已知 user_id 输入）
3. **GET `/api/teams/{tid}/me-role`**：admin/member RBAC 真守卫数据源
4. **soft-delete + restore**：M20 design §3 Q8=B 字面已决 hard delete + RESTRICT FK / **不是缺口** / 不在本 pool / prompt 字面错记纠正

> **何时做**：Phase 2.3 集成期评估（按 cross-sprint pool 机械工序）。

---

last_reviewed_at: 2026-05-09
