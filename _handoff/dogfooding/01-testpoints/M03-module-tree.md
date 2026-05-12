---
module: M03
name: module-tree
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M03-module-tree/00-design.md
  - design/02-modules/M03-module-tree/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F3 功能模块树（PRD Q3 / Q3.1 功能模块视角）
---

# M03 功能模块树 测试点

## 业务流程（H1 / 1 行概述）

M03 是 M04-M10 子模块的结构锚点：editor 在项目左侧树上 CRUD/拖拽/跨父移动节点，path 物化路径支撑 O(1) 面包屑与子树查询，硬删除时 Service 层显式调 M04/M06/M07 写各自 activity_log（R-X2 防 CASCADE 绕过），多人编辑 last-write-wins 不加锁。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/nodes 创建根节点 parent_id=null 返 201 + depth=0 + path="/{new_id}/" + sort_order=0（design §3 G5 path 计算 + tests.md G1）
- [P0] POST /api/projects/{pid}/nodes 创建子节点返 201 + depth=parent.depth+1 + path=parent.path+new_id+"/"（design §3 R1 P2-05 校准 + tests.md G2）
- [P0] GET /api/projects/{pid}/nodes 返完整嵌套树按 depth+sort_order 排序（design §9 list_by_project + tests.md G3）
- [P0] PUT /api/projects/{pid}/nodes/{nid} 改 name 返 200 + activity_log update 含 old_name/new_name（design §10 + tests.md G4）
- [P0] DELETE /api/projects/{pid}/nodes/{nid} 叶子节点返 204 + activity_log delete 一条（design §10 + tests.md G6）
- [P0] DELETE 含子节点和 M04/M06/M07 关联数据返 204 + 子树全删 + M04 dimension_records 删 + M07 issues.node_id 置 NULL + 各下游 activity_log 各自写一条（R-X2 design §8 + tests.md G9）
- [P0] POST /reorder 同级节点批量更新 sort_order 返 200 + 每节点写独立 reorder 事件（design §10 R10-1 batch3 + tests.md G5）
- [P0] POST /nodes/{nid}/move 跨父移动返 200 + path 重计算 + 子树 path REPLACE 同步 + depth 更新 + 子树每节点写独立 move 事件 metadata 含 triggered_by+root_node_id（design §3 + §10 + tests.md G8）
- [P0] GET /nodes/{nid}/breadcrumb 返从根到当前节点顺序 items（含 id/name/depth）（design §7 + tests.md G7）
- [P1] NodeService.batch_create_in_transaction 由 M11/M17 调用每节点写独立 create 事件 + 接受外部 db session 不自开事务（design §6 R-X3 + R10-1）
- [P1] NodeService.get_for_embedding 返 name+"\n"+description 拼接 / 节点不存在或软删返 None（design §6 M18 baseline-patch + commit 4887f7c）
- [P1] move 节点到当前同一 parent 返 200 + path 不变 + depth 不变（NOOP 幂等，tests.md E9）
- [P1] sort_order 不传时新建节点追加到同级末尾（design §7 NodeCreate ge=0 + 业务默认）

### 2. 边界 / 状态机

- [P0] type 字段创建后 PUT 改 type 返 422 NODE_TYPE_IMMUTABLE（design §4 + §13 + tests.md E5）
- [P0] move 节点到其子孙节点返 422 NODE_MOVE_CYCLE_DETECTED（Service path NOT LIKE source.path||'%' + tests.md E8）
- [P0] NodeType 枚举仅 folder/file / DB CHECK type IN ('folder','file') 拦截非法值（design §3 R3-2 三重防护）
- [P1] name 空字符串返 422 VALIDATION_ERROR（Pydantic min_length=1 + DB ck_node_name_not_empty + tests.md E1）
- [P1] name 超长 201 字符返 422 VALIDATION_ERROR（design §7 max_length=200 + tests.md E2）
- [P1] description 超长 2001 字符返 422（design §3 description String(2000)）
- [P1] depth 负值 INSERT 失败 ck_node_depth_non_negative（design §3 CheckConstraint）
- [P1] sort_order 负值入参 422（design §7 Field ge=0 + DB ck_node_sort_order_non_negative）
- [P1] 单节点（根）面包屑返 items=[{id,name,depth=0}] 仅自己（tests.md E7）
- [P1] move new_parent_id=null 移到根层级返 200 + depth=0 + path="/{nid}/"（design §7 NodeMove Optional）
- [P2] 极深树（depth>50）操作正常无 path 长度上限崩溃（design §3 G5 path=Text 无限深度）

### 3. 异常 / 错误

- [P0] DELETE 不存在的 node_id 返 404 NODE_NOT_FOUND（design §13 + tests.md ER1）
- [P0] GET breadcrumb 不存在 node_id 返 404 NODE_NOT_FOUND（tests.md ER2）
- [P0] POST 创建时 parent_id 不存在返 404 NODE_PARENT_NOT_FOUND（design §13 + tests.md E3）
- [P0] POST /reorder items 含跨父节点 ID 返 422 NODE_REORDER_INVALID（design §13 + tests.md E6）
- [P0] 错误响应格式统一 {"error":{"code":"NODE_NOT_FOUND","message":"..."}}（设计原则规约 7 + tests.md ER1-6）
- [P1] POST /reorder items 含不存在 node_id 返 404 NODE_NOT_FOUND（tests.md ER4）
- [P1] move 时下游 DimensionService.delete_by_node_id 抛异常整事务回滚 / nodes 不删 + 上游 activity_log 不写（design §5 多表事务 R-X2）
- [P1] delete_node commit 后 embedding_service.enqueue_delete 抛 SilentFailure 写 embedding_failures EMBEDDING_DELETE_FAILED + 主事务不回滚（design §6 M18 baseline-patch CY 决策 5）
- [P2] DB 临时不可达调 GET /nodes 返 503 不泄漏 stacktrace（设计原则规约 7）

### 4. 权限 / Auth

- [P0] 未登录 GET /nodes 无 Authorization 返 401 UNAUTHENTICATED（design §8 Server Action + tests.md P1）
- [P0] 项目非成员 GET /nodes 返 403 PERMISSION_DENIED（Router check_project_access role=viewer + tests.md T1）
- [P0] viewer 角色 POST /nodes 创建返 403 PERMISSION_DENIED（Router 写接口要求 editor + tests.md P2）
- [P0] viewer DELETE /nodes/{nid} 返 403 PERMISSION_DENIED（tests.md P3）
- [P0] viewer POST /reorder 返 403 PERMISSION_DENIED（design §8 写接口 editor）
- [P0] viewer POST /move 返 403 PERMISSION_DENIED（design §8 写接口 editor）
- [P1] editor GET /nodes 返 200（读接口 viewer 及以上 + tests.md P4）
- [P1] Service _check_node_belongs_to_project 跨项目越权 node 抛 NodeNotFoundError 而非 PermissionDenied 不暴露存在性（design §8 细粒度）
- [P1] DELETE 删除完成后用 actor_user_id 写 activity_log created_by（design §6 R-X5 4 参签名 + R10-1）

### 5. Tenant 隔离

- [P0] userB 是 projectB 成员 PUT projectA 的 node_id 返 403（Router 拦 + tests.md T2）
- [P0] NodeDAO.list_by_project(projectA_id) 返回结果不含 projectB 节点（design §9 + tests.md T3）
- [P0] NodeDAO.list_subtree(node_from_projectA, project_id=projectB) 返空列表 tenant 过滤（design §9 + tests.md T5）
- [P0] GET /nodes of projectA 响应不含 projectB 任何 path 片段（tests.md T4）
- [P1] POST 创建时 parent_id 属于其他项目返 404 NODE_PARENT_NOT_FOUND 不暴露跨租户（tests.md ER3）
- [P1] move new_parent_id 属于其他项目返 404 NODE_PARENT_NOT_FOUND（design §8 细粒度 + §13）
- [P1] nodes.project_id 冗余字段所有 DAO 查询强制 WHERE project_id=?（design §3 R3-3 + §9 主查询模式）

### 6. 并发 / 乐观锁

- [P1] 两 editor 并发 POST 同父下创建子节点两者均 201 / sort_order 由 DB INSERT 顺序决定不冲突（design §5 G2 last-write-wins + tests.md C1）
- [P1] 并发 POST /reorder 覆盖相同节点最后一次 sort_order 生效无 500 / path 不含 sort_order 重排不改 path（design §5 + tests.md C2）
- [P1] 并发 move_subtree 同节点到不同目标父最后到达者生效 / 子树 path 一致无中间残留（tests.md C3）
- [P2] 同时编辑同 node name 双 PUT 后写者赢 last-write-wins 不引入 version 字段（design §5 清单 2 不触发）

### 7. 数据完整性

- [P0] nodes.project_id NOT NULL + ON DELETE CASCADE 删 project 行 nodes 全删（design §3）
- [P0] nodes.parent_id ON DELETE CASCADE DB 层兜底删子树（design §3 + §8 R-X2 Service 显式删先于 CASCADE）
- [P0] activity_log delete 事件 target_id=被删 node_id 子树从叶到根逐一写 N 条（design §10 R10-1 batch3）
- [P0] DB CHECK type IN ('folder','file') INSERT 非法 type 失败（design §3 R3-2 三重防护）
- [P0] R-X2 删除节点先调 M04.delete_by_node_id + M06.delete_by_node_id + M07.orphan_by_node_id 再 DELETE nodes（design §8 顺序约定）
- [P1] activity_log create metadata 含 project_id/parent_id/name/type/depth（design §10）
- [P1] activity_log move metadata root_node 含 old_path/old_depth + 子节点该字段 None（design §10 R2-5）
- [P1] activity_log reorder metadata 含 project_id/parent_id/old_sort_order/new_sort_order（design §10）
- [P1] path 物化路径格式 "/{id1}/{id2}/{thisId}/" 以 / 开头结尾 LIKE 前缀查询匹配（design §3 path 格式约定）
- [P1] M07 IssueService.orphan_by_node_id 语义为 SET node_id=NULL 而非 DELETE 与 FK ON DELETE SET NULL 一致（design §8）
- [P1] ix_nodes_path text_pattern_ops 索引存在支持子树 LIKE 前缀查询（design §3 Alembic 要点）
- [P2] batch_create_in_transaction 拓扑乱序输入 raise NodeParentNotFoundError（design §6 A5 caller 未排序契约）

### 8. UI / UX

- [P1] editor 右键节点菜单含"添加子节点"/"重命名"/"删除"（PRD US-B1.1 录入门槛最低）
- [P1] 拖拽节点同级排序触发 POST /reorder 完成后树渲染同步新顺序（PRD US-B2.1）
- [P1] 拖拽节点到不同父节点触发 POST /move（design §1 边界灰区 G5）
- [P1] NODE_MOVE_CYCLE_DETECTED 前端 toast "不能将节点移到其子节点下"（design §13 message）
- [P1] 删除节点前若有子节点弹确认弹窗"将级联删除 N 个子节点"（design §13 G2 决策直接级联 / 前端兜底 UX 建议）
- [P1] 面包屑展示从根到当前节点导航 / 点击中间节点跳转到对应节点档案页（PRD F3 面包屑）
- [P2] 节点 type=folder 显示文件夹图标 / type=file 显示文件图标（NodeTypeEnum 视觉区分）

### 9. 性能 / 容量

- [P1] GET /nodes 大项目 1000+ 节点首屏返回 <500ms（design §3 ix_nodes_project_parent 复合索引）
- [P1] list_subtree 1000 节点 path LIKE 查询 <100ms（design §3 ix_nodes_path 索引）
- [P2] move_subtree 子树 500 节点 path REPLACE 单 SQL 批量 <200ms / activity_log 异步批写（design §3 + §10 elapsed_ms metadata）

### 10. 跨模块契约（M03 是被依赖源头）

- [P1] NodeService.batch_create_in_transaction(db, project_id, nodes_data) 签名稳定供 M11/M17 调用（design §6 对外契约）
- [P1] NodeService.get_for_embedding(db, node_id, project_id) -> str|None ADR-003 规则 1 供 M18 worker 调用（design §6 baseline-patch + commit 4887f7c）
- [P1] delete_by_node_id / orphan_by_node_id 4 参签名（db, node_id, project_id, actor_user_id）M04/M06/M07 实装一致（design §6 M04 sprint R-X5 升级）
- [P2] nodes(node_id, project_id) 存在校验接口供下游模块引用（design §1 被依赖契约）
- [P2] commit 后 embedding_service.enqueue B 推迟在 M18 sprint 期接通 / TODO 注释 4 字段在 service 文件（design §6.X A4 scaffold）

### 11. 设计漂移防御 / CI 守护

- [P1] Router 不直 db.query(Node) / 走 service 层（design §6 禁止 + 分层架构）
- [P1] M11/M17 router 不直 INSERT INTO nodes / 必走 NodeService.batch_create_in_transaction（design §6 禁止）
- [P1] DAO 不计算 path 字段 / path 计算归 service 层（design §6 禁止）
- [P2] activity_log 事件 action_type ∈ {create,update,delete,reorder,move} target_type=node（design §10）
