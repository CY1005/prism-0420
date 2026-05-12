---
module: M07
name: issue
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M07-issue/00-design.md
  - design/02-modules/M07-issue/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-003-cross-module-data-access.md
prd_ref: PRD Q3"内置测试沉淀能力" + US-B1.6（编辑者录入 bug/技术债/设计缺陷到对应功能项）
---

# M07 问题沉淀 测试点

## 业务流程（H1 / 1 行概述）

M07 是问题沉淀核心：编辑者把 bug/tech_debt/design_flaw/performance 4 类问题挂到 node 或游离到 project（node_id 可 NULL，US-B1.6），4 状态机 open→in_progress→resolved→closed（in_progress 必填 assigned_to，closed 不可重开），冗余 project_id 做 tenant 过滤，所有 CRUD + transition 写 activity_log，对外暴露 R-X3 三个 db session 契约（list_by_project 给 M13/batch_create_in_transaction 给 M11/M17/orphan_by_node_id 给 M03 节点删除级联游离化）。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/issues 含 node_id+category=bug 返 201 status=open + activity_log 一条 create（design §7 + tests.md G1）
- [P0] POST /api/projects/{pid}/issues 不含 node_id 创建游离 issue 返 201 node_id=null（design §1 边界灰区 + tests.md G2）
- [P0] GET /api/projects/{pid}/issues 返 items 含节点 issue + 游离 issue 全量（design §7 + tests.md G3）
- [P0] GET /api/projects/{pid}/nodes/{nid}/issues 只含该 node 的 issue 不含游离（design §7 + tests.md G4）
- [P0] DELETE /api/projects/{pid}/issues/{id} 返 204 + activity_log delete 含 final_status（design §10 + tests.md G8）
- [P1] GET /api/projects/{pid}/issues?status=open 只返 open 状态 items（design §7 IssueListQueryParams + tests.md G5）
- [P1] GET /api/projects/{pid}/issues?category=bug 只返 category=bug items（design §9 list_by_project category 过滤）
- [P1] GET /api/projects/{pid}/issues?tag=login DAO 走 JSONB @> 包含查询命中含 login tag 的 issue（design §7 tag 查询实现 + §9）
- [P1] GET /api/projects/{pid}/issues?node_id=<nid> 等价于 nodescoped 列表返该 node 全部 issue（design §9 list_by_project node_id 过滤）
- [P1] PUT /api/projects/{pid}/issues/{id} 更新 title/description/tags 返 IssueResponse + activity_log update 含 changed_fields（design §10 + §7 IssueUpdate）
- [P1] GET /api/projects/{pid}/issues/{id} 返 IssueResponse 含 node_name + created_by_name + assigned_to_name join 字段（design §7 IssueResponse）
- [P1] PUT /api/projects/{pid}/issues/{id} 允许重新关联 node_id（design §7 IssueUpdate.node_id 允许）
- [P2] issue 列表按 created_at desc 排序（design §9 DAO order_by）
- [P2] tags 默认为空数组 [] 不为 null（design §3 SQLAlchemy default=list + §7 IssueCreate tags=[]）

### 2. 边界 / 状态机

- [P0] POST transition open→in_progress 含 assigned_to 返 200 + activity_log status_change + metadata.assigned_to（design §4 + §10 + tests.md G6）
- [P0] POST transition open→resolved 直接解决返 200 + resolved_at 写入（design §4 + tests.md G7/E6）
- [P0] POST transition in_progress→resolved 返 200 + resolved_at 写入（design §4 + tests.md G7）
- [P0] POST transition resolved→closed 返 200 status=closed + activity_log status_change（design §4）
- [P0] POST transition open→closed 返 422 ISSUE_TRANSITION_INVALID 必须经 in_progress 或 resolved（design §4 禁止转换 + tests.md SM3）
- [P0] POST transition closed→任何状态 返 422 ISSUE_CLOSED_ERROR 关闭后不可重开（design §4 + tests.md SM4）
- [P0] POST transition resolved→open 返 422 ISSUE_TRANSITION_INVALID resolved 只能→closed（design §4 + tests.md SM2）
- [P0] POST transition open→in_progress 不传 assigned_to 返 422 ISSUE_ASSIGNEE_REQUIRED（design §4 §13 + tests.md E 段隐含）
- [P1] POST transition 同状态 in_progress→in_progress 返 422 ISSUE_TRANSITION_INVALID（design §4 + tests.md E7）
- [P1] POST transition in_progress→open 取消认领 assigned_to 重置为 NULL + activity_log issue.unassigned 含 metadata.previous_assignee_id（design §4 表 + R-X5 audit F-3）
- [P1] POST transition in_progress→open 取消认领权限仅 assignee 本人或 admin（design §4 表 +"权限"列）
- [P1] 完整生命周期 open→in_progress→resolved→closed 每步成功 resolved_at 在 resolved 步写入（design §4 + tests.md SM1）
- [P1] POST /issues category=unknown 返 422 ISSUE_CATEGORY_INVALID（design §13 + tests.md E3）
- [P1] POST /issues title="" 返 422 Pydantic min_length（design §7 + tests.md E1）
- [P1] POST /issues title 超 256 字符返 422 Pydantic max_length（design §7 IssueCreate.title + tests.md E2）

### 3. 异常 / 错误

- [P0] POST /issues 含 node_id 属于其他 project 返 422 ISSUE_NODE_CROSS_PROJECT（design §13 + tests.md E4）
- [P0] DELETE 不存在的 issue_id 返 404 ISSUE_NOT_FOUND（design §13 + tests.md E8）
- [P0] 错误响应格式 `{"error":{"code":"ISSUE_TRANSITION_INVALID","message":"...","details":{"current":"closed","target":"open"}}}` 含 details（tests.md ER2）
- [P1] POST /issues tags=["valid",123] 返 422 Pydantic 类型校验（design §7 + tests.md E9）
- [P1] DB CHECK 约束 ck_issue_status 违反时兜底返 VALIDATION_ERROR 不暴露 SQL（design §3 + tests.md ER5）
- [P1] PUT 不存在 issue_id 返 404 ISSUE_NOT_FOUND（design §13）
- [P1] POST transition 不存在 issue_id 返 404 ISSUE_NOT_FOUND（design §13）
- [P2] DB 连接断 调任意端点返 5xx 不泄漏 stacktrace（规约 7 错误兜底）

### 4. 权限 / Auth

- [P0] 未登录调 GET /issues 返 401 UNAUTHENTICATED（design §8 Server Action + tests.md P1）
- [P0] viewer 调 POST /issues 返 403 PERMISSION_DENIED 写接口要 editor（design §8 + tests.md P2）
- [P0] viewer 调 GET /issues 返 200 只读允许 viewer（design §8 + tests.md P3）
- [P0] viewer 调 POST transition 返 403 PERMISSION_DENIED transition 要 editor（design §8 + tests.md P4）
- [P1] editor 调 DELETE closed 状态 issue 返 204 editor 有权删任意状态（design §8 + tests.md P5）
- [P1] role 中途由 editor 降为 viewer 二次 POST 返 403（design §8 Router check_project_access）
- [P1] session 过期后调任意端点返 401 TOKEN_EXPIRED（design §8 Server Action）
- [P2] in_progress→open 取消认领由非 assignee 非 admin 触发返 403 PERMISSION_DENIED（design §4 表"权限：仅 assignee 本人或 admin"）

### 5. Tenant 隔离

- [P0] userA 持 projectA token 调 projectB /issues 列表返 403 PERMISSION_DENIED Router 层拦（design §8 + tests.md T1）
- [P0] URL path projectA 但 issue_id 属于 projectB 返 404 ISSUE_NOT_FOUND 不暴露 forbidden（design §8 _check_issue_belongs_to_project + tests.md T2）
- [P0] IssueDAO.list_by_project(other_project_id) 直查返空 list（design §9 WHERE project_id 过滤 + tests.md T3）
- [P0] POST transition 跨 project 路径调 projectB 的 issue 返 404 Service 层 tenant check（design §8 + tests.md T4）
- [P1] Service 层创建时强制 issue.project_id = node.project_id 当 node_id 非空（design §3 一致性兜底）
- [P1] DAO 所有方法签名带 project_id 入参防绕过（design §9）
- [P1] 冗余 project_id 字段 NOT NULL（design §3 SQLAlchemy nullable=False）
- [P2] 索引 ix_issue_project_status + ix_issue_project_category tenant 主查询命中（design §3 alembic 要点）

### 6. 并发 / 乐观锁

- [P0] open→in_progress Service 层 SELECT FOR UPDATE 锁定 issue 行 双 user 同时认领仅一个写入 assigned_to 另一个被串行化（design §5 状态转换竞态分析表 row 1）
- [P1] open→resolved 直接解决 SELECT FOR UPDATE + status 校验串行化（design §5 表 row 2）
- [P1] in_progress→resolved SELECT FOR UPDATE + status + assigned_to 一致性校验（design §5 表 row 3）
- [P1] resolved→closed SELECT FOR UPDATE + status 校验（design §5 表 row 4）
- [P2] issues 表 __table_args__ 无 UniqueConstraint 强制"单 issue 单 assignee"是状态层语义不依赖 DB 约束（design §5 设计透明度声明）

### 7. 数据完整性

- [P0] FK projects ON DELETE CASCADE 删 project 后 issues 级联删除（design §3 ForeignKey）
- [P0] FK nodes ON DELETE SET NULL 删 node 后 issue.node_id 变 NULL issue 不被删（design §3 + §6 orphan_by_node_id 语义一致）
- [P0] CHECK ck_issue_status status ∈ {open,in_progress,resolved,closed}（design §3 + §3 alembic 要点）
- [P0] CHECK ck_issue_category category ∈ {bug,tech_debt,design_flaw,performance}（design §3 + §3 alembic 要点）
- [P1] FK created_by 删 user 后 issue.created_by FK 行为按 users FK 定义（design §3 ForeignKey users.id）
- [P1] FK assigned_to 删 user 后 issue.assigned_to FK 行为按 users FK 定义（design §3）
- [P1] 索引 ix_issue_node_project 按功能项聚合查询命中（design §3 alembic 要点）
- [P1] 索引 ix_issue_created_by 按创建者查询命中（design §3）
- [P1] tags 默认 [] JSONB 类型支持数组操作（design §3 default=list）
- [P2] resolved_at 在非 resolved 状态时为 NULL 仅 transition→resolved 时写入（design §3 + §4 副作用列）

### 8. UI / UX

- [P0] 档案页节点详情含 issue 区块展示该节点关联 issue 列表（design §6 Page 层 web/.../[nid]/page.tsx）
- [P0] 项目级 issue 列表页 web/.../[pid]/issues/page.tsx 展示全部 issue 含游离（design §6 Page 层）
- [P1] issue-status-badge 4 状态视觉区分 open/in_progress/resolved/closed（design §6 Component issue-status-badge.tsx）
- [P1] issue-form 创建/更新表单 category 下拉 4 选项（design §6 Component issue-form.tsx + §3 IssueCategory）
- [P1] issue 列表卡片 issue-card.tsx 展示 title + status badge + node_name + assigned_to_name（design §6 Component + §7 IssueResponse）
- [P1] 状态转换非法时前端 toast 展示 ISSUE_TRANSITION_INVALID details 含 current/target（design §13 + tests.md ER2）
- [P2] tag 过滤 UI 控件可多选 命中 tags @> 查询（design §7 tag 查询实现 + §9）

### 9. activity_log 事件完备性

- [P0] POST /issues 写 1 条 action_type=create target_type=issue metadata 含 node_id/category/status（design §10 表）
- [P0] PUT /issues 写 1 条 action_type=update metadata 含 changed_fields（design §10）
- [P0] POST transition 写 1 条 action_type=status_change metadata 含 node_id/category/note/assigned_to（design §10）
- [P0] DELETE /issues 写 1 条 action_type=delete metadata 含 node_id/category/final_status（design §10）
- [P0] in_progress→open 取消认领写 activity_log action_type=issue.unassigned metadata 含 previous_assignee_id/reason（design §4 表 + R-X5 audit F-3）
- [P1] activity_log 写入与 issues 写入同一隐式 transaction 任一失败回滚（design §5 主流程入口 SQLAlchemy autobegin）
- [P1] summary 字段格式"状态变更：{old_status}→{new_status}"含中文（design §10 表）

### 10. R-X3 跨模块契约（外部 db session 入口）

- [P0] orphan_by_node_id(db, node_id, project_id, actor_user_id) 接受外部 db session 不自开事务（design §6 R-X3 + §5 多表事务规则 2）
- [P0] orphan_by_node_id 将该 node 下所有 issues.node_id 设 NULL 不删除 issue（design §6 + §3 ON DELETE SET NULL 语义一致）
- [P0] orphan_by_node_id 每条受影响 issue 写独立 orphan activity_log 事件 metadata 含 old_node_id/reason=cascade_from_node_delete/actor_user_id（design §10 R10-1 补充）
- [P0] orphan_by_node_id 签名 4 参 含 actor_user_id（M04 sprint R-X5 升级 / 2026-05-07 与 M04/M06 同款 design §6 命名说明段）
- [P0] batch_create_in_transaction(db, issues, project_id) 接受外部 db session 不自开事务（design §6 R-X3 规则 1）
- [P0] batch_create_in_transaction 每条 issue 写独立 create activity_log 事件（design §10 R10-1 + §6）
- [P1] list_by_project(db, project_id, node_id, category, status, tag, limit) M13 pilot 跨模块调用 pass-through 不写 activity_log 不开事务（design §6 对外契约 + M13 pilot 登记）
- [P1] orphan_by_node_id 命名不沿用 M04/M06 delete_by_node_id 对齐 SET NULL 真实行为防调用方误以为真删（design §6 命名说明 batch3 决策 4）

### 11. ErrorCode 注册

- [P1] ISSUE_NOT_FOUND 注册到 api/errors/codes.py 对应 IssueNotFoundError(NotFoundError)（design §13）
- [P1] ISSUE_TRANSITION_INVALID 对应 IssueTransitionInvalidError(AppError) http_status=422（design §13）
- [P1] ISSUE_CLOSED_ERROR 对应 IssueClosedError(AppError) http_status=422（design §13）
- [P1] ISSUE_ASSIGNEE_REQUIRED 对应 IssueAssigneeRequiredError(AppError) http_status=422（design §13）
- [P1] ISSUE_CATEGORY_INVALID 对应 IssueCategoryInvalidError(ValidationError) http_status=422（design §13）
- [P1] ISSUE_NODE_CROSS_PROJECT 对应 IssueNodeCrossProjectError(AppError) http_status=422（design §13）
- [P2] frontmatter codes_added 6 个新增 ErrorCode 与 api/errors 文件实际定义行数一致（design frontmatter codes_added + R13-1 CI 守护）

### 12. 分层职责防御

- [P1] importlinter 禁 routers/issue_router.py 直 db.query(Issue)（design §6 分层职责表）
- [P1] importlinter 禁 services/issue_service.py 内 requests.get(...) 外部调用（design §6）
- [P1] DAO 新增方法签名必须含 project_id 入参防绕过（design §9）
- [P1] DAO 禁止直查 nodes 表 校验 node 归属走 NodeService（design §9 + ADR-003 规则 1）

### 13. idempotency / Queue 显式 N/A

- [P1] M07 无 idempotency_key 操作 CRUD 走 DB 校验 重复 DELETE 天然幂等返 204（design §11 显式声明）
- [P1] M07 不投递 Queue 任务 全同步用户手动录入（design §12 显式声明 + §5 异步处理 N/A）

### 14. M18 baseline-patch（embedding 时序契约 6.X A7）

- [P1] IssueService.get_for_embedding(db, issue_id, project_id) 拼接 title + description 走 ADR-003 规则 1（design §6 + §6.X A7 退化路径 A）
- [P1] get_for_embedding 返字符串或 None M07 无 url 字段（design §6 M18 baseline-patch + §6.X A7 CY 决策 4 不影响）
- [P1] M07 sprint 期 create/update commit 后不调 embedding_service.enqueue scaffold 留 TODO（design §6.X A7 B 推迟 + TODO 4 字段 target_type=issue）
- [P1] get_for_embedding unit test 覆盖默认拼接路径 生产路径 M18 sprint 期补（design §6.X A7 A 路径必声明）

### 15. 性能 / 容量

- [P2] GET /api/projects/{pid}/issues 大量 issue 列表分页 page_size=20 走索引 ix_issue_project_status（design §7 IssueListQueryParams + §3 索引）
- [P2] GET /api/projects/{pid}/nodes/{nid}/issues 走索引 ix_issue_node_project 主查询命中（design §3 alembic 要点）
- [P2] tag 过滤 JSONB @> 查询性能依赖 PG GIN 索引（design §7 + §9 tag 查询 / 未声明 GIN / dogfooding 期观测）
