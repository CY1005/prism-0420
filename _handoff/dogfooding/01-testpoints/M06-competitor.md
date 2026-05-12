---
module: M06
name: competitor
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M06-competitor/00-design.md
  - design/02-modules/M06-competitor/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-003-cross-module-data-access.md
prd_ref: F6 竞品参考（PRD Q3 内置产品评价能力 / US-B1.4 + US-A3.3）
---

# M06 竞品参考 测试点

## 业务流程（H1 / 1 行概述）

M06 是围绕功能模块的结构化竞品对标能力：competitors 表为项目级全局竞品实体（display_name 无唯一约束 / project_id tenant），competitor_refs 表为 node 级对标记录（冗余 project_id / UNIQUE(node_id, competitor_id) / 关联竞品填功能覆盖+技术方案+pros_and_cons JSONB），M06 无状态机/无并发/无 idempotency/无 Queue，对外暴露 R-X3 两个外部 db session 契约（batch_create_in_transaction 给 M11/M17、delete_by_node_id 4 参给 M03 级联），所有 C/U/D 写 activity_log（含级联删除前显式批量写 delete competitor_ref 日志），多表事务走 Router commit 单点 + SQLAlchemy autobegin（M06 R1-A A1 立修与 M04 §5 同步消歧）。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/competitors 创建竞品返 201 + activity_log create competitor 含 project_id metadata（design §7 + §10 + tests.md G1）
- [P0] GET /api/projects/{pid}/competitors 返 items 按 display_name asc 排序 + total 正确（design §9 list_by_project order_by + tests.md G2）
- [P0] POST /api/projects/{pid}/nodes/{nid}/competitor-refs 关联已有竞品返 201 + activity_log create competitor_ref（design §7 + §10 + tests.md G5）
- [P0] DELETE /api/projects/{pid}/competitors/{cid} 有 N 条 refs 时返 204 + activity_log 先写 N 条 delete competitor_ref 再写 1 条 delete competitor（含 ref_count=N，design §10 级联策略 + tests.md E7）
- [P0] CompetitorRefResponse 含 join 自 competitors.display_name 字段（design §7 schema）
- [P1] PUT /api/projects/{pid}/competitors/{cid} 改 description 返 200 + updated_at 更新 + activity_log update 含 changed_fields metadata（design §7 + §10 + tests.md G3）
- [P1] PUT /api/projects/{pid}/nodes/{nid}/competitor-refs/{rid} 改 tech_approach 返 200 + activity_log update competitor_ref（design §7 + tests.md G7）
- [P1] DELETE /api/projects/{pid}/nodes/{nid}/competitor-refs/{rid} 返 204 + activity_log delete competitor_ref（design §10 + tests.md G8）
- [P1] GET /api/projects/{pid}/nodes/{nid}/competitor-refs 返 items 含 display_name join 展示（design §7 CompetitorRefResponse + tests.md G6）
- [P1] DELETE 无 refs 的竞品返 204 + activity_log delete competitor 含 ref_count=0 metadata（design §10 + tests.md G4）
- [P1] CompetitorCreate 仅 display_name 必填 website_url 和 description 均可空（design §7 Pydantic + §3 nullable=True）
- [P1] CompetitorRefCreate 仅 competitor_id 必填 / competitor_version + feature_coverage + tech_approach + pros_and_cons 均可空（design §7 schema）
- [P2] pros_and_cons={"pros":["fast"],"cons":["expensive"]} JSONB 存读返一致（design §3 + §7 ProsAndCons）

### 2. 边界 / 状态机

- [P0] M06 无状态机 / competitors 与 competitor_refs 均无 status 字段（design §4 显式声明 + §15 CY ack）
- [P0] DB UNIQUE(node_id, competitor_id) 同节点二次关联同一竞品返 409 COMPETITOR_REF_DUPLICATE（design §3 + §13 + tests.md E6）
- [P0] display_name 同名不同竞品允许创建（design §3 intentionally no UNIQUE display_name + alembic 要点）
- [P1] display_name="" 空字符串返 422 Pydantic min_length=1（design §7 + tests.md E1）
- [P1] display_name 超 128 字符返 422 Pydantic max_length=128（design §7 + tests.md E2）
- [P1] website_url 超 512 字符返 422 Pydantic max_length=512（design §7 + tests.md E3）
- [P1] pros_and_cons={"pros":"not-a-list"} 类型非法返 422 Pydantic VALIDATION_ERROR（design §7 + tests.md E8 + ER4）
- [P1] DELETE 重复调（已删 competitor）返 204 天然幂等（design §11 显式声明 + tests.md G4）
- [P1] DELETE 重复调（已删 competitor_ref）返 204 天然幂等（design §11 显式声明）
- [P2] CompetitorUpdate 全字段 None partial update 返 200 不改任何字段（design §7 schema 所有字段 Optional）

### 3. 异常 / 错误

- [P0] competitor_id 不存在创建 ref 返 404 COMPETITOR_NOT_FOUND（design §13 + tests.md E4 + ER1）
- [P0] competitor_id 属于 projectB 在 projectA 下建 ref 返 422 COMPETITOR_CROSS_PROJECT（design §13 + §8 Service 层 _check_competitor_belongs_to_project + tests.md E5 + T5 + ER3）
- [P0] 错误响应格式符合规约 7 `{"error":{"code":"COMPETITOR_NOT_FOUND","message":"..."}}`（design §13 + tests.md ER1-ER3）
- [P0] 主流程入口事务失败（mock activity_log.log 抛异常）competitors INSERT 自动回滚（design §5 Router commit 单点 + autobegin）
- [P0] 档案页内联"新建竞品+对标"双 service 调用其中之一失败时两条 INSERT 均回滚（design §5 multi-table tx + §6 inline create + Q4 决策）
- [P1] competitor_ref_id 不存在 PUT 返 404 COMPETITOR_REF_NOT_FOUND（design §13 + tests.md ER1）
- [P1] competitor_id 不存在 DELETE 返 404 COMPETITOR_NOT_FOUND 不暴露 forbidden（design §8 抛 NotFoundError 而非 PermissionDenied）
- [P1] DB UNIQUE 唯一约束冲突 IntegrityError 被 service 层 catch 转 COMPETITOR_REF_DUPLICATE（design §13 + 06-principles 清单 6 INSERT UNIQUE catch）
- [P1] pros_and_cons 格式错误响应含 details 字段定位失败字段（design §7 + tests.md ER4）
- [P2] DB 不可用调任意端点返 503 不泄漏 stacktrace（规约 7 错误兜底）

### 4. 权限 / Auth

- [P0] 未登录 GET /competitors 无 session 返 401 UNAUTHENTICATED（design §8 Server Action + tests.md P1）
- [P0] viewer 角色调 POST /competitors 返 403 PERMISSION_DENIED（design §8 Router 写要求 editor + tests.md P2）
- [P0] viewer 角色调 GET /competitors 返 200（design §8 读允许 viewer + tests.md P3）
- [P0] editor 角色调 DELETE /competitors/{cid} 有 refs 返 204 + 级联（design §8 + tests.md P4）
- [P1] viewer 调 POST /competitor-refs 返 403 PERMISSION_DENIED（design §8 Router 写要求 editor）
- [P1] viewer 调 PUT /competitor-refs/{rid} 返 403 PERMISSION_DENIED（design §8 Router 写要求 editor）
- [P1] viewer 调 DELETE /competitor-refs/{rid} 返 403 PERMISSION_DENIED（design §8 Router 写要求 editor）
- [P1] session 过期后调任意端点返 401 TOKEN_EXPIRED（design §8 Server Action 层）
- [P1] role 由 editor 降为 viewer 后二次 PUT 返 403（design §8 Router 层 check_project_access 每次校验）

### 5. Tenant 隔离

- [P0] userA 持 projectA token 访问 projectB 的 /competitors 返 403 PERMISSION_DENIED Router 层拦（design §8 + tests.md T1）
- [P0] URL projectA 但 node_id 实属 projectB 访问 /competitor-refs 返 404 NOT_FOUND DAO tenant 过滤生效不暴露 forbidden（design §8 + §9 + tests.md T2）
- [P0] CompetitorDAO.list_by_project(other_project_id) 直查返空 list（design §9 WHERE project_id 过滤 + tests.md T3）
- [P0] CompetitorDAO.list_refs_by_node(node_id, other_project_id) 直查返空 list（design §9 + tests.md T4）
- [P0] Service 层创建 competitor_ref 时强制 ref.project_id=competitor.project_id 不允许传入跨项目（design §3 一致性兜底 + tests.md T5）
- [P1] competitor_id 属于 projectB 在 projectA path 下建 ref 返 422 COMPETITOR_CROSS_PROJECT Service 层 _check_competitor_belongs_to_project（design §8 + §13）
- [P1] DAO 所有查询均带 project_id 入参 / 无豁免清单（design §9 豁免清单：无）
- [P1] M06 无 admin_only 跨 tenant 接口（design §8 三层即覆盖 + 06-principles 清单 5 例外）
- [P2] DELETE projects/{pid} 级联（M02 ondelete=CASCADE）会带走 competitors 与 competitor_refs（design §3 FK ondelete=CASCADE）

### 6. 并发 / 乐观锁

- [P0] M06 无并发场景 / 无 version 字段（design §5 4 维表 + §15 CY ack + 05-catalog ❌）
- [P1] 两 editor 同时 POST 同一 (node_id, competitor_id) 一成功一返 409 COMPETITOR_REF_DUPLICATE（design §3 DB UNIQUE 防并发重复 + §5 表注释）
- [P1] 两 editor 同时 PUT 同一 competitor 后者覆盖前者无冲突保护（design §5 无乐观锁 / last-write-wins）
- [P2] 同时 DELETE competitor 与 POST competitor_ref 引用之 → 后者 IntegrityError 或 ref 已 CASCADE 删（design §3 ondelete=CASCADE）

### 7. 数据完整性

- [P0] competitor 级联删除 competitor_refs 通过 SQLAlchemy cascade="all, delete-orphan" + DB ON DELETE CASCADE（design §3 + alembic 要点）
- [P0] 级联删除前 Service 层显式批量写每条被删 competitor_ref 的 delete activity_log（R10-1 批量 N 条 / design §10 + §6 对外契约）
- [P0] delete_by_node_id 4 参签名 (db, node_id, project_id, actor_user_id) 删该 node 下所有 refs + 写每条 delete activity_log（design §6 R-X5 升级 / M03 级联调用）
- [P1] batch_create_in_transaction 给 M11/M17 调用每条 competitor 写独立 create activity_log 事件（R10-1 / design §6 对外契约）
- [P1] competitor_refs.project_id 冗余字段必须与 competitor.project_id 一致（design §3 一致性兜底 service 层强制）
- [P1] competitors.created_by FK users.id 但 nullable=True（design §3 created_by 可空）
- [P1] CompetitorRefResponse.display_name join 自 competitors 不冗余存储（design §3 + §7 schema）
- [P2] competitors 索引 ix_competitor_project / competitor_refs 三索引 ix_competitor_ref_node_project + ix_competitor_ref_project + ix_competitor_ref_competitor 全 alembic 落地（design §3 alembic 要点）

### 8. UI / UX

- [P0] 项目设置页 /projects/[pid]/settings 竞品全局列表渲染 competitor-list 组件（design §6 Page + Component）
- [P0] 档案页 /projects/[pid]/nodes/[nid] 渲染 competitor-ref-card 列表 + competitor-ref-form 新建表单（design §6 Component）
- [P1] 档案页内联"新建竞品+同时建对标"B 入口走单事务 / 失败两条均回滚（design §1 边界灰区 + §5 Q4 决策 + §6 service 多表事务）
- [P1] 档案页 ref 列表展示 display_name + competitor_version + feature_coverage + pros_and_cons 拆 pros/cons 两区（design §7 ProsAndCons + §3 JSONB）
- [P2] pros_and_cons 为空时 UI 显示占位"暂无"不报错（design §7 Optional）
- [P2] 跨 tab 创建 competitor 后切到另一 tab 列表需刷新可见（design §6 SSR 渲染 / 无 SSE / 无 realtime）

### 11. 集成 / 跨模块契约

- [P0] M03 delete_node 调 competitor_service.delete_by_node_id(db, node_id, project_id, actor_user_id) 接受外部 db session 不自开事务（design §5 R-X3 + §6 对外契约）
- [P0] M11/M17 调 batch_create_in_transaction(db, competitors, project_id) 接受外部 db session 不自开事务（design §6 对外契约 + R-X3）
- [P1] M12 对比矩阵读 competitors 数据走 Service 层 get_for_embedding 或 list_by_project 不直 SQL（design §2 依赖 + ADR-003 跨模块读规则 1）
- [P1] M18 baseline-patch get_for_embedding(db, competitor_id, project_id) 拼接 display_name + description（不含 url，CY 决策 4，design §6 + §6.X）
- [P1] M06 sprint 期 create/update commit 后 enqueue embedding 留 TODO 不调（M18 sprint 期补，design §6.X B 推迟 + scaffold S2 4 字段）
- [P1] activity_log produces action_types 含 6 类 competitor_created/updated/deleted + competitor_ref_created/updated/deleted（design frontmatter produces_action_types）
- [P2] M14 行业动态关联竞品不在 M06 scope（design §1 Out of scope）
- [P2] M13 需求分析中竞品维度仅读 M06 数据 / 不写（design §1 Out of scope + §2 依赖图）

### 13. 错误码 / 错误响应契约

- [P0] COMPETITOR_NOT_FOUND http_status=404（design §13 + NotFoundError 基类）
- [P0] COMPETITOR_REF_NOT_FOUND http_status=404（design §13 NotFoundError）
- [P0] COMPETITOR_REF_DUPLICATE http_status=409（design §13 AppError）
- [P0] COMPETITOR_CROSS_PROJECT http_status=422（design §13 AppError）
- [P1] 错误响应统一 `{"error":{"code":"...","message":"..."}}` 不暴露 SQL / stacktrace（规约 7 + tests.md ER1-ER4）
- [P1] Pydantic VALIDATION_ERROR 响应带 details 字段（design helpers.errors.codes_used + tests.md ER4）
- [P1] UNAUTHENTICATED / PERMISSION_DENIED 错误码复用横切层 v3 不在 M06 新增（design frontmatter codes_used）

### 15. 配置 / 闸门 / 显式 N/A

- [P0] M06 无 Queue payload / 无异步处理 显式 N/A（design §12 + §5 4 维表）
- [P0] M06 无 idempotency_key 操作 显式 N/A（design §11 + 06-principles 清单 4）
- [P1] M06 sprint 闸门 R1 三 subagent 跑 spec+quality+reuse+efficiency / R2 单 subagent 跑 schema 子片 ≥80% SKIP（design §14.5 sprint review 计划）
- [P1] alembic ondelete=CASCADE on competitors.project_id + competitor_refs.project_id/node_id/competitor_id 四个 FK（design §3 SQLAlchemy）
- [P1] M06 frontmatter produces_action_types 与 activity_log §10 6 事件一一对应（design frontmatter + §10）
- [P2] M06 helpers.errors.version=v3 / 新增 4 个 codes / 复用 3 个 codes_used（design frontmatter helpers.errors）
