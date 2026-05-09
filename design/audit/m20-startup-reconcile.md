---
title: M20 sprint 启动期 reconcile pass — 三栏分类 + 配套继续验收
status: accepted
owner: CY
created: 2026-05-09
sprint: M20 团队 / complexity=medium / pilot=false / Phase 2.1 95%→100% 收官（最后一个 own sprint）
trigger: M19 sprint 完成（commit b0ec39b / 1512 PASS）后启动 M20
related:
  - design/02-modules/M20-team/00-design.md（status=accepted 2026-04-26）
  - design/adr/ADR-005-team-extension.md（团队扩展核心决策 Q0-Q15）
  - design/00-phase-gate.md（闸门 2.5 reconcile pass + 闸门 3.4 L1 总则 + 闸门 4 启动条件）
  - _handoff/cross-sprint-punt-pool.md（M19 新增 #25-#28 + 触发点 D 元教训 #19）
  - design/99-comparison/phase-gate-bypass-log.md（#2 配套继续：M16 bypass + M17/M18/M19 真跑 ✅ / M20 必继续）
---

# M20 sprint 启动期 reconcile pass

> 闸门 2.5 三栏强制分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）。
> B 栏前先穷举 L1 锁规候选（feedback_problem_layered_analysis 失效信号 /
> M17 启动期 R1-A P1-1 立规：B 栏 = 0 时禁列 B 栏）。
> M20 是 Phase 2.1 最后一个 own sprint / **complexity=medium**（区别于 M19 low / M18 medium）。

## 0. 执行摘要

| 栏目 | 项数 | 状态 |
|------|------|------|
| **A 机械可做** | **8** | 全 ✅（本 commit 内修完 / 部分留子片 1+2+3 落地） |
| **B 待 CY 决策** | **0** | M20 design accepted 2026-04-26 / Q0-Q15+Q13.2 全锁 / 三轮 reviewer audit 已过 / Phase 1 sync 6 轮独立审 39 finding 全收敛 |
| **C 已自我消解** | **9** | 横切 helper 已稳定 / 复用 M02-M19 范式 / pilot=false 不需新模板 / baseline-patch 已预录 |

**B 栏 = 0 第十五次实证**（M05-M19 十四连 + M20 第十五）。

---

## 1. A 栏：机械可做（8 项）

### A1 [本启动期] §14.5 Sprint Review 拆分计划补完

闸门 3.4 L1 总则强制段。已 append 到 design/02-modules/M20-team/00-design.md（节 14.5 / 5 子片拆分 + R1=3 + R2=1 + 范式复用清单 20 项 + L3 留空 4 项）。

### A2 [本启动期] bypass log #2 配套继续验收 ✅

M16 bypass + M17 恢复 + M18 继续 + M19 继续 = 累计 2 次 bypass 不复位 / 第 3 次触发闸门 3.4 L1 review。M20 必继续 R1=3 subagent 并行 + R2=1 合并 Opus 真跑（不再降级 / 不复位累计触发线）。spawn prompt 必含 ls/find 穷举要求；spawn 后 >5min 无通知必主动 ping。

### A3 [本启动期] cross-sprint punt 池本 sprint 命中检查

| # | punt | 本 sprint 命中？ | 处置 |
|---|------|-----------------|------|
| #3 | IssueResponse 漏 join 字段 | M20 不触 IssueResponse / N/A | STILL_PUNT |
| #6 | M07 update detach（None→NULL） | M20 不触 M07 / N/A | STILL_PUNT |
| #11 | IntegrityError 转换缺口 M04 dimension B3+C7.1 | M20 不触 dimension / N/A 显式声明 | STILL_PUNT |
| #12 | M04-9 target_type hard-code | M20 不触 dimension_service / N/A | STILL_PUNT |
| #13 | M04-1 (updated_by, updated_at) 联合索引 | M20 不写 dimension_records / N/A | STILL_PUNT |
| #14 | M04-8 db.get(DimensionType) 三处 | M20 不触 dimension_service / N/A | STILL_PUNT |
| #15 | M04-R2 A1 DimensionResponse 缺 join | M20 不返回 DimensionResponse / N/A | STILL_PUNT |
| #17 | _sanitize_filename horizontal | M20 无 filename 路径 / N/A 显式声明 | STILL_PUNT |
| #20 | require_platform_admin 去重 | **M20 重新评估**：M20 §7 endpoint table 全部走 require_user + L1 require_team_access(role) + L2 assert_team_role(role)；**无 platform_admin endpoint**（删 team 由 owner 自决，非平台级 admin）→ **不触发**；STILL_PUNT 保留至下一含 platform_admin 模块（如未来 platform-admin 独立模块） |
| #21 | M18 worker source_text 真接 | M20 不触 embedding worker / N/A | STILL_PUNT |
| #22 | M18 noop 转 succeeded | 同上 | STILL_PUNT |
| #23 | M18 cron PCT 维度 | 同上 | STILL_PUNT |
| #24 | M18 batch_backfill | 同上 | STILL_PUNT |
| #25 | _md_cell + _render_dimension_content + _render_pros_cons horizontal | M20 不触 Markdown 渲染 / 留 M19 第二渲染场景（如团队报告导出）独立触发 / N/A 显式声明 | STILL_PUNT |
| #26 | filename sanitize 输入端 vs 输出端分类 | M20 无 filename 路径 / N/A 显式声明 | STILL_PUNT |
| #27 | Cache-Control: no-store header | M20 不返回敏感 user 上下文响应（CRUD 响应 ≠ user 上下文聚合）/ N/A 显式声明 | STILL_PUNT |
| #28 | filename 含 project_name RFC 5987 | M20 无 filename 路径 / N/A | STILL_PUNT |

**触发点 D（M19 元教训 #19）**：M20 启动期已应用 — tests.md status code 矩阵（404/422/409/403/500）与 design §13 ErrorCode 表（同 codes / status code）+ exceptions.py（同 code / http_status）三方字面对账 ✅ 全同步（详 A8）。

### A4 [子片 1 责任] api/models/teams.py 双表 + 三重防护 + 三索引 + UniqueConstraint + CheckConstraint

design §3.2 字面已锁。Team + TeamMember 双表 + TeamRole Enum (owner/admin/member) + 三重防护（Mapped[TeamRole] + String(20) + CheckConstraint role IN (...) / 与 M02-M19 11 模块同款范式）+ uq_teams_creator_name + uq_team_members_team_user + ix_team_members_user_team + ck_teams_name_length + ck_teams_version_positive + ck_team_members_role_valid。子片 1 落地。

### A5 [子片 1 责任] Alembic m20_team.py（CREATE TABLE 双表 + ALTER projects FK）

design §3.4 字面已锁：
1. CREATE TABLE teams + 索引 + UniqueConstraint + CheckConstraint
2. CREATE TABLE team_members + 索引 + UniqueConstraint + CheckConstraint  
3. ALTER TABLE projects ADD CONSTRAINT fk_projects_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE RESTRICT

**M02 baseline-patch RENAME 验证**：现 api/models/projects.py:101 line 已是 `team_id: Mapped[PyUUID | None]` UUID nullable column（未挂 ForeignKey）/ S2 模板注释 line 99-100 已字面锁 "M20 sprint 启动时：ALTER ADD CONSTRAINT FK ondelete=RESTRICT + 此处加 ForeignKey('teams.id')" → 子片 1 同步落实（model 加 ForeignKey 引用 + alembic 加 FK constraint）。

**M15 baseline-patch 已预录验证**：api/models/activity_log.py 字面已含 10 个 team_* ActionType（line 126-135）+ "team" TargetType（line 157）+ R14 ci-lint 全过去式 ✅。子片 1 仅需 alembic ALTER CHECK constraint 同步（重建 ck_activity_log_action_type + ck_activity_log_target_type 含新枚举）。

### A6 [子片 1 责任] ci-lint R14 验证（10 个 team_* 全过去式立规对齐）

M16 sprint 立的 R14（write_event 调用 action_type 必须 _ACTION_TYPES 枚举字面 + 全过去式 + snake_case / ci-lint grep 守护）：M20 service write_event(action_type=...) 必字面命中：
- team_created / team_renamed / team_description_changed / team_deleted（4 个 team CRUD）
- team_member_added / team_member_removed / team_member_promoted_admin / team_member_demoted_member（4 个 member 状态）
- project_joined_team / project_left_team（2 个 cross-module）

**全过去式 ✅ 验证**（grep 已跑）：10 个全过去式 + snake_case / R14 立规对齐。

**M19 元教训 #19 应用**（SR-M19-1 立规候选实证）：sprint 启动期 R1 reviewer 必跑立规精神 vs design 字面对齐 grep 检查 + tests.md 第三方文件状态码同步 → A8 已字面对账完成。

### A7 [子片 2 责任] 8 ErrorCode + 8 AppError 子类 + tenant_filter L3 升级

design §13 字面已锁，**M15 sprint baseline-patch 已注册 8 ErrorCode**（grep api/errors/codes.py:171-178 + api/errors/exceptions.py:701-738 已存）：
- TEAM_NOT_FOUND / TEAM_NAME_DUPLICATE / TEAM_HAS_PROJECTS / TEAM_OWNER_REQUIRED
- TEAM_MEMBER_NOT_FOUND / TEAM_MEMBER_DUPLICATE / TEAM_PERMISSION_DENIED / CROSS_TEAM_MOVE_FORBIDDEN

子片 2/3 仅需 raise caller + e2e 回归（exceptions.py 注册期 R13-1 parity 守护已通过）。

**tenant_filter.py 升级**（子片 2 责任 / ADR-005 L3 SQL 注入横切）：现 api/auth/tenant_filter.py:45 line 已字面预录 `def user_accessible_project_ids_subquery(db, user_id) -> Any` 通过 _ctx Protocol 注入 / S2 scaffold 简化决策注释（M02/M20 各自补 concrete impl）→ 子片 2 落实 concrete UNION（ProjectMember UNION teams via team_members）+ lifespan startup 注入。

### A8 [本启动期] M19 元教训 #19 应用 — tests.md ↔ design §13 ↔ exceptions.py 三方字面对账 ✅

M19 sprint 立的 SR-M19-1 立规：tests.md ↔ design.md ↔ exceptions.py 三方 status code 字面同步 checkbox / R2 reconcile 必跑。

**M20 启动期对账（grep 已跑）**：

| ErrorCode | tests.md HTTP | design §13 HTTP | exceptions.py http_status | 一致 |
|-----------|--------------|-----------------|--------------------------|------|
| TEAM_NOT_FOUND | 404 (E1, T1) | 404 | NotFoundError (默认 404) | ✅ |
| TEAM_NAME_DUPLICATE | 409 (B5, B5b, E2) | 409 | ConflictError (默认 409) | ✅ |
| TEAM_HAS_PROJECTS | 422 (B8, B14, E3, C5) | 422 | ValidationError (默认 422) | ✅ |
| TEAM_OWNER_REQUIRED | 422 (B4, C2, E4-E6, E6b, P14) | 422 | ValidationError (默认 422) | ✅ |
| TEAM_MEMBER_NOT_FOUND | 404 (E7) | 404 | NotFoundError (默认 404) | ✅ |
| TEAM_MEMBER_DUPLICATE | 409 (E8) | 409 | ConflictError (默认 409) | ✅ |
| TEAM_PERMISSION_DENIED | 403 (P11, P12, P15, E9) | 403 | http_status = 403 (line 733 直接写) | ✅ |
| CROSS_TEAM_MOVE_FORBIDDEN | 422 (E10) | 422 | ValidationError (默认 422) | ✅ |
| CONFLICT (复用 / version 冲突) | 409 (C1, C6, E11) | 409 | ConflictError | ✅ |
| VALIDATION_ERROR (复用 Pydantic) | 422 (B1, E12, E13) | 422 | ValidationError | ✅ |
| PROJECT_ARCHIVED (M02 复用) | 422 (B13) | 422 | ValidationError | ✅ |
| 500 (E14 activity_log 写入失败) | 500 | — (非业务 ErrorCode / 通用错误) | — | ✅ |

**结论**：12 项三方字面同步 ✅ / 元教训 #19 R2 reconcile checkbox 启动期已通过 / 子片 5 关闸前 R2 必复跑（防 R1 立修触发漂移）。

---

## 2. B 栏：待 CY 决策（0 项 / 第十五次实证）

### B 栏 = 0 穷举 L1 锁规候选清单（防"反正都锁了 / 没看见决策点 = 没锁规"认知漂移）

| # | 候选决策点 | 是否已锁规 | 锁规来源 |
|---|-----------|----------|---------|
| 1 | Team 核心概念（Team / Space / Org 多层）| ✅ 锁 | CY ack 2026-04-26 / Q0=B 纯 Team / ADR-005 §Decision |
| 2 | Team 与 ProjectMember 衔接（嵌套式 / 覆盖式）| ✅ 锁 | CY ack 2026-04-26 / Q1=B 嵌套式 / §8.6 max 解析 |
| 3 | Team role 映射（直接复用 ProjectRole / 三角色映射）| ✅ 锁 | CY ack 2026-04-26 / Q2=B 三角色 owner/admin/member → owner/editor/viewer |
| 4 | 删 team_member 是否级联清 ProjectMember（软切断 / 级联）| ✅ 锁 | CY ack 2026-04-26 / Q3=A 软切断 / §1 边界灰区 |
| 5 | Tenant 边界（单 tenant / 双 tenant）| ✅ 锁 | CY ack 2026-04-26 / Q4=A 单 tenant / §5.2 4 维 |
| 6 | 三层防御层数（L1+L2+L3 / 仅 L1+L2）| ✅ 锁 | CY ack 2026-04-26 / Q5=A 全做 / §8.1 |
| 7 | §12 异步形态（同步 / Queue / SSE）| ✅ 锁 | CY ack 2026-04-26 / Q6=A 同步 / §12 N/A 显式 |
| 8 | 跨 team 操作（cross-team 直跳 / 仅个人 ↔ team）| ✅ 锁 | CY ack 2026-04-26 / Q7=A 仅个人 ↔ team / E10 测试 |
| 9 | 删 team 时 project（孤儿化 / 强制前置迁出）| ✅ 锁 | CY ack 2026-04-26 / Q8=B 强制前置迁出 / §1 + B14 archived 双路径 |
| 10 | 乐观锁 version（teams 加 / 全加 / 全不加）| ✅ 锁 | CY ack 2026-04-26 / Q9=A teams 加 / team_members 不加 |
| 11 | 事件粒度（粗粒度 5 / 细粒度 10+）| ✅ 锁 | CY ack 2026-04-26 / Q10=B 细粒度 10 + Q10.1 ①②③ 全 B / §10.1 |
| 12 | Auth 路径（全 P1+P2 合并入口 / 含 P4）| ✅ 锁 | CY ack 2026-04-26 / Q11=A / ADR-004 §79 对齐 |
| 13 | Service 跨事务签名（外部 db: Session / 内部独立）| ✅ 锁 | CY ack 2026-04-26 / Q13.2=A 接受外部 db / §8.7 R-X3 共享 |
| 14 | ErrorCode 粒度（粗粒度 8 / 细粒度 N）| ✅ 锁 | CY ack 2026-04-26 / Q12=A 粗粒度 8 / §13.1 |
| 15 | teams owner 字段（owner_id 可改 / creator_id 永不变）| ✅ 锁 | CY ack 2026-04-26 / Q13=C creator_id（创建者只读）/ §3.2 |
| 16 | team name 唯一约束（全局 / 同 creator 下唯一）| ✅ 锁 | CY ack 2026-04-26 / Q13.1①=A 同 creator 下唯一 / B5b transfer 后边界 |
| 17 | team_members FK（CASCADE / RESTRICT）| ✅ 锁 | CY ack 2026-04-26 / Q13.1②=B RESTRICT / §3.5 改回成本 |
| 18 | 模块依赖声明（标准依赖 / + ADR-005 横切）| ✅ 锁 | CY ack 2026-04-26 / Q14=C / §2 |
| 19 | F2.3 archived×team 互锁路径（仅源头 / 仅历史 / A+C 组合）| ✅ 锁 | design §1 边界灰区字面 / A+C 组合（C 源头拒 + A 历史兜底自动解绑） |
| 20 | F2.7 project 归属变更端点（复用 PATCH /projects / 独立 POST /move-team）| ✅ 锁 | design §7.1 字面 / 独立端点 / Q10.1 ② event 命名清晰 |
| 21 | F2.9 correlation_id（无 / 有 / metadata schema 改）| ✅ 锁 | design §10.1 字面 / 有 / 0 schema 改（jsonb metadata 字段内填） |
| 22 | F3.10 / F3.13 删 user 含 team owner 处理（baseline-patch 提议 M01）| ⏸️ punt M01 后续 sprint | M01 own / M20 sprint 仅触发提议（USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER ErrorCode 已注册）/ 不阻塞业务路径 |

→ B 栏 = 0 项（第十五次实证 / M05-M20 十五连）。第 22 项是 M01 own punt 提议，不是 M20 业务决策。

---

## 3. C 栏：已自我消解（9 项）

| # | 项 | 消解原因 |
|---|---|---------|
| C1 | M02 model team_id 列已预录 | api/models/projects.py:101 line UUID nullable / S2 scaffold 注释 line 99-100 字面已锁 "M20 sprint 启动时加 ForeignKey" / 子片 1 落实 |
| C2 | M15 ActionType+10 已预录 | api/models/activity_log.py:126-135 字面已含 team_created/renamed/desc_changed/deleted + member_added/removed/promoted/demoted + project_joined_team/left_team / 全过去式 + snake_case ✅ |
| C3 | M15 TargetType+1 "team" 已预录 | api/models/activity_log.py:157 字面已含 / 子片 1 仅 alembic ALTER CHECK 同步 |
| C4 | 8 ErrorCode + 8 AppError 子类已注册 | M15 sprint baseline-patch 已落（codes.py:171-178 + exceptions.py:701-738）/ R13-1 parity 守护已通过 / 子片 2/3 仅 raise caller |
| C5 | tenant_filter.py user_accessible_project_ids_subquery Protocol 已预录 | api/auth/tenant_filter.py:45 字面已含 _ctx Protocol 注入点 / S2 scaffold 注释字面 / 子片 2 仅注入 concrete UNION impl |
| C6 | conftest fixture 复用预查（feedback_subagent_sprint §1）| make_user / make_project / make_project_with_member 已存（line 205/243/641）/ M20 子片 1+ 测试不内联同名 helper / 子片 1 加 make_team / make_team_with_member fixture（防内联重复） |
| C7 | Phase 1 sync 6 轮独立审 39 finding 全收敛 | design accepted 2026-04-26 / 三轮 reviewer audit + audit-verify v1-v4 已过 / 不需要 sprint 启动期 audit flip |
| C8 | M19 立的 cross-sprint punt 池 #25-#28 + 触发点 D | 全 STILL_PUNT 不触发 M20 sprint（详 A3 表）/ 元教训 #19 已应用 A8 三方对账 ✅ |
| C9 | 26 cross-sprint punt 项中无任何项需 M20 子片业务路径修存量 | 触发点 D 元教训 #19 = 立规防御未来（M20 启动期已应用 / 不修存量）/ 触发点 A 4 项 M04 dimension 不触 M20 范围 |

---

## 4. 启动期完成 checklist

- [x] §14.5 Sprint Review 拆分计划补完（design 节 14.5 / 5 子片 + R1=3 + R2=1 + 范式复用 20 项 + L3 留空 4 项）
- [x] bypass log #2 配套继续验收 ✅（M20 必继续 R1=3 + R2=1 不复位）
- [x] cross-sprint punt 池本 sprint 命中检查（17 项 STILL_PUNT 全 N/A 显式声明 / #20 重新评估不触发 / 触发点 D 元教训 #19 已应用 A8）
- [x] B 栏 = 0 穷举 L1 锁规候选清单（22 项 / 第十五次实证）
- [x] C 栏 9 项自我消解（baseline-patch 全预录到位 / 仅 alembic + concrete impl 落地差异）
- [x] design status accepted 2026-04-26 不需 audit flip / Phase 1 sync 39 finding 全收敛已过
- [x] baseline-patch 检查：M02 model team_id 已预录 / M15 ActionType+10 + TargetType+1 已预录 / exceptions.py 8 TEAM_* + codes.py 8 ErrorCode 已注册 / tenant_filter.py Protocol 已预录
- [x] M19 元教训 #19 应用：tests.md ↔ design §13 ↔ exceptions.py 三方 status code 字面对账 ✅（A8）
- [x] R14 过去式立规验证：10 个 team_* + project_joined_team + project_left_team 全过去式 + snake_case ✅
- [x] M18 真漏洞 #20 重新评估：M20 endpoint 全走 require_user + assert_team_role / 无 platform_admin → 不触发 / STILL_PUNT 保留
- [x] baseline 1512 PASS 不破 ✅

---

## 5. 元贡献候选（sprint 完成后回写 m20-pilot-template-validation.md）

- M20 是 Phase 2.1 **最后一个 own sprint**（**Phase 2.1 95→100% 收官**）
- M20 形态特殊性：**横切 owner 模块**（user_accessible_project_ids_subquery L3 SQL 注入升级 / M03-M19 既有 DAO 自动受益）+ **跨事务 R-X3 双方法**（delete_team 5-step + transfer_ownership 6-step）+ **R10-1 批量独立 N+1**（删 team N member 写 1+N 条）+ **嵌套 max 权限解析**（resolve_project_role）+ **F2.3 archived×team 互锁双路径**（C 源头拒 + A 历史兜底自动解绑）—— 区别于 M14（全局豁免）/ M15（横切表 owner）/ M19（纯只读导出）
- pilot=false / complexity=medium → R1+R2 数据点 17 → 18 是否仍稳定（M02-M19 17 数据点稳态验证 / M20 形态最复杂可能突破 R1+R2 命中峰值区间）
- **Phase 2.1 100% 收官触发评估**：
  1. cross-sprint punt 池累计 N 项（M02-M19 总计 ≥40 项）+ M20 自身贡献
  2. 闸门 4 启动条件确认（M01-M05+M20 后端代码 merge / OpenAPI 契约稳定 / `npm run codegen` 准备 / Phase 2.2 前端继承 Prism 启动）
  3. R1+R2 范式 17 数据点 → 是否升级为方法论稳定结论（M21+ 模块如出现新形态需重新定数据点）
- N/A 元教训显式声明范式应用（§14.5 范式复用清单 20 项 / 11+ N/A 项 / 单 sprint N/A 历史最高密度）
- ADR-005 L3 SQL 注入横切 M03-M19 实证：lifespan 注入 set_tenant_context 切换前后 baseline 1512 PASS 不破

---

last_updated: 2026-05-09
