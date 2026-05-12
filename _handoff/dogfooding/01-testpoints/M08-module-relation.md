---
module: M08
name: module-relation
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M08-module-relation/00-design.md
  - design/02-modules/M08-module-relation/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F8 模块关系图（PRD Q3 / US-B1.7 + US-C1.2）
---

# M08 模块关系图 测试点

## 业务流程（H1 / 1 行概述）

M08 管理同 project 内节点间的有向关联（depends_on / related_to / conflicts_with），(source, target, type) 三元组唯一 + 自环防护 + 节点同 project 校验，Service 层创建/更新/删除写 activity_log，对外提供 delete_by_node_id（M03 R-X2 级联）+ batch_create_in_transaction（M11/M17 编排）+ search_by_keyword（M09 聚合）三个外部 session 契约接口。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/relations source!=target + depends_on 返 201 + relation_id + activity_log create 一条（design §7 + tests.md G1）
- [P0] POST 创建 related_to 含 notes 返 201 + notes 持久化 + metadata 含 source/target/type（design §10 + tests.md G2）
- [P0] GET /api/projects/{pid}/relations 返 RelationListResponse items+total 含全部关联（design §7 + tests.md G3）
- [P0] GET /api/projects/{pid}/nodes/{nid}/relations 返该 node 作 source 或 target 的所有关联（design §9 list_by_node OR + tests.md G4）
- [P0] PATCH /api/projects/{pid}/relations/{rid} 更新 notes 返 200 + activity_log update + metadata 含 old_notes_length/new_notes_length（design §10 + tests.md G5）
- [P0] DELETE /api/projects/{pid}/relations/{rid} 返 204 + activity_log delete 一条（design §10 + tests.md G6）
- [P0] DELETE /api/projects/{pid}/nodes/{nid}/relations 清除该节点全部关联返 204 + 每条关联写独立 delete 事件 metadata.triggered_by=node_deletion（design §9 R10-1 + §10）
- [P1] ModuleRelationService.delete_by_node_id(db, node_id, project_id) 接受外部 db session 不自开事务（design §6 R-X3 + §9 注释）
- [P1] ModuleRelationService.batch_create_in_transaction(db, relations_data, project_id, user_id) 接受外部 db session 每条写独立 create activity_log（design §6 R-X3 + §9 R10-1）
- [P1] ModuleRelationDAO.search_by_keyword(query, project_id) 按 notes ILIKE 过滤返 list（design §9 + ADR-003 规则 1）
- [P1] 同一对 (source, target) 不同 type 三次 POST（depends_on/related_to/conflicts_with）均返 201（design §3 候选 A-2 多类型允许）

### 2. 边界 / 状态机

- [P0] POST source_node_id == target_node_id 返 422 RELATION_SELF_LOOP（design §7 Pydantic model_validator + §13 + tests.md E1）
- [P0] POST 同三元组 (source, target, type) 二次返 409 RELATION_DUPLICATE（design §3 uq_module_relation_src_tgt_type + §13 + tests.md E2）
- [P0] POST relation_type=blocks 非枚举值返 422（Pydantic RelationType 枚举先拦 + DB CHECK 兜底 + tests.md E5）
- [P0] DB CHECK ck_module_relation_no_self_loop 直接 INSERT source==target 失败（design §3 R3-2 三重防护）
- [P0] DB CHECK ck_module_relation_type_valid 直接 INSERT 非法 relation_type 失败（design §3 R3-2 三重防护）
- [P1] PATCH/DELETE 不存在的 relation_id 返 404 RELATION_NOT_FOUND（design §13 + tests.md E7）
- [P1] POST notes 超长 >5000 字符返 422（design §7 + tests.md E6）
- [P1] PATCH notes=null 显式清空备注返 200 + 字段为空（design §7 RelationUpdate Optional）
- [P1] 声明：M08 无 status 字段无状态机无乐观锁（design §4 + §5 多人架构 4 维必答异步=N/A 并发=N/A）
- [P2] notes 含特殊字符（'、%、\\、emoji）持久化无 SQL 注入（design §9 search_by_keyword ILIKE 参数化）

### 3. 异常 / 错误

- [P0] POST source_node 不存在返 404 NODE_NOT_FOUND（design §8 Service _check_nodes_belong_to_project + tests.md E8）
- [P0] POST source 属于另一 project 返 422 RELATION_NODE_NOT_IN_PROJECT（design §13 R1-B P1-02 立修 422 不是 404 + tests.md E3）
- [P0] POST target 属于另一 project 返 422 RELATION_NODE_NOT_IN_PROJECT（design §13 + tests.md E4）
- [P0] POST source 属于 projectA + target 属于 projectB + URL=projectA 返 422 RELATION_NODE_NOT_IN_PROJECT（design §8 Service 校验 + tests.md T5）
- [P0] 错误响应格式统一 {"error":{"code":"RELATION_DUPLICATE","message":"..."}} 不暴露 SQL（design §13 + tests.md ER1-5）
- [P1] IntegrityError constraint name=uq_module_relation_src_tgt_type 转 RelationDuplicateError 409（design §13 IntegrityError 捕获说明 M08-B5）
- [P1] IntegrityError 其他 constraint（如 FK）原样透传不 wrap 为 409（design §13 M08-B5 不暴露语义混淆）
- [P1] M03 删除节点过程中 delete_by_node_id 抛异常 → caller 事务整体回滚 nodes 不删 + activity_log 不写（design §5 R-X3 caller 事务边界）
- [P1] M03 节点删除后残留 module_relations 通过 delete_by_node_id 清理 + N 条独立 delete activity_log（design §10 R10-1 + R-X2）
- [P2] 未识别 IntegrityError 返 CONFLICT 兜底不暴露 SQL（tests.md ER5）

### 4. 权限 / Auth

- [P0] 未登录 POST /relations 无 cookie 返 401 UNAUTHENTICATED（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 角色 POST /relations 返 403 PERMISSION_DENIED（design §8 Router 写操作 editor + tests.md P2）
- [P0] viewer 角色 PATCH /relations/{rid} 返 403 PERMISSION_DENIED（design §8 + R2 元教训 viewer 写所有写端点全覆盖）
- [P0] viewer 角色 DELETE /relations/{rid} 返 403 PERMISSION_DENIED（design §8 + R2 元教训）
- [P0] viewer 角色 DELETE /nodes/{nid}/relations 返 403 PERMISSION_DENIED（design §8 节点级联端点同 editor 要求 + R2 元教训）
- [P1] viewer GET /relations 返 200（design §8 读操作允许 viewer + tests.md P3）
- [P1] viewer GET /nodes/{nid}/relations 返 200（design §8 读操作允许 viewer）
- [P1] session 过期后 POST /relations 返 401 TOKEN_EXPIRED（tests.md P4）
- [P1] Service _check_nodes_belong_to_project 不属于 project 抛 NodeNotFoundError 不暴露 PermissionDenied（design §8 细粒度防御不泄存在性）

### 5. Tenant 隔离

- [P0] userA 持 projectA token 访问 GET /api/projects/projectB/relations 返 403 PERMISSION_DENIED（design §8 Router check_project_access + tests.md T1）
- [P0] URL=projectA + body source/target 都属于 projectB 返 422 RELATION_NODE_NOT_IN_PROJECT（design §8 Service 拦 + tests.md T2）
- [P0] ModuleRelationDAO.list_by_project(otherProjectId) 单元测试返空 list（design §9 主查询 WHERE project_id=? + tests.md T3）
- [P0] ModuleRelationDAO.list_by_node(node, otherProjectId) tenant 过滤生效返空 list（design §9 双过滤 project_id + node_id）
- [P0] 创建关联后 DB 查 module_relations.project_id == source_node.project_id（design §3 R3-3 Service 强制赋值 + tests.md T4）
- [P0] ModuleRelationDAO.search_by_keyword(query, projectA) 不返 projectB 任何 notes 匹配（design §9 + ADR-003 M09 调用）
- [P0] ModuleRelationDAO.delete_by_node(nid, projectA) 不删 projectB 含同 node_id（理论不可能但 tenant 防御）的关联（design §9 双 WHERE）
- [P1] 冗余 project_id 字段所有 DAO 查询不 JOIN nodes（design §3 R3-3 性能 + §9 主查询模式）
- [P1] DELETE /api/projects/projectA/relations/{rid_of_projectB} 返 404 RELATION_NOT_FOUND 不暴露存在性（design §8 跨租户不暴露）

### 6. 并发

- [P1] 两请求并发 POST 同 (source, target, type) 三元组：第一返 201 + 第二返 409 RELATION_DUPLICATE DB 唯一约束兜底无 500（design §3 uq + tests.md C1）
- [P1] 两请求并发 DELETE 同 relation_id：第一返 204 + 第二返 404 RELATION_NOT_FOUND 幂等无 500（tests.md C2）
- [P1] M03 删节点 + M08 GET /nodes/{nid}/relations 并发：读返空 list 或 404 不报 500（tests.md C3）
- [P2] 并发 PATCH 同 relation_id notes 不同值：last-write-wins 无 version 冲突（design §5 并发 N/A + design §4 显式声明）

### 7. 数据完整性

- [P0] module_relations.project_id NOT NULL + FK ON DELETE CASCADE：删 project 行 → 关联全删（design §3 ForeignKey ondelete=CASCADE）
- [P0] module_relations.source_node_id / target_node_id FK ON DELETE CASCADE：DB 层兜底但 R-X2 要求 M03 显式调 delete_by_node_id 先（design §3 + §6 R-X2）
- [P0] CHECK ck_module_relation_project_id_not_null DB 层兜底 project_id null INSERT 失败（design §3）
- [P0] activity_log delete_by_node_id 调用：N 条关联 → N 条独立 delete 事件每条 target_id=relation_id 不汇总（design §10 R10-1）
- [P0] activity_log create metadata 含 source_node_id + target_node_id + relation_type（design §10）
- [P0] activity_log delete 由 M03 级联触发 metadata.triggered_by=node_deletion + 含 node_id（design §10）
- [P1] activity_log update metadata 含 relation_type + old_notes_length + new_notes_length 不含 notes 字面量（design §10 PII 防御）
- [P1] delete_by_node_id 先 list_by_node 取关联再 delete 保证 N 条 log 能拿到 source/target 信息（design §9 服务代码注释 + R10-1）
- [P1] batch_create_in_transaction 每条写独立 create 事件不汇总（design §9 R10-1 + R-X3）
- [P1] ix_module_relations_source_project + ix_module_relations_target_project 索引存在支持按节点查询（design §3 Alembic 要点）

### 8. UI / UX

- [P1] 关系图页面 /projects/{pid}/relations React Flow 力导向图渲染节点 + 关联线（design §6 Component + PRD F8 可视化）
- [P1] 关系线颜色按 relation_type 区分（depends_on/related_to/conflicts_with）（PRD F8 关系类型可视）
- [P1] 创建关联表单选 source/target/type/notes 提交后图同步刷新（design §6 relation-form.tsx）
- [P1] RELATION_SELF_LOOP 错误前端 toast "源节点和目标节点不能相同"（design §13 message）
- [P1] RELATION_DUPLICATE 错误前端 toast "该关联已存在"（design §13 message）
- [P1] RELATION_NODE_NOT_IN_PROJECT 错误前端 toast "节点不属于当前项目"（design §13 message）
- [P1] 单节点详情页"依赖"段调 GET /nodes/{nid}/relations 展示出入向关联（US-C1.2 支撑）
- [P1] *_node_name / created_by_name 由前端 N+1 lookup 不依赖后端 outerjoin（design §7 RelationResponse 注释 M08 R2 P1-01 立修）
- [P2] 删除关联前弹确认弹窗"确定删除该关联？"（前端兜底 UX）

### 9. 跨模块契约 / 集成

- [P0] M03 NodeService.delete_node 显式调 ModuleRelationService.delete_by_node_id(db, nid, pid) 而非依赖 DB CASCADE（design §1 边界灰区 + R-X2）
- [P0] delete_by_node_id 双向 OR 条件 (source==nid OR target==nid) 同时清理出入向关联（design §9 DAO list_by_node + delete_by_node）
- [P1] M11/M17 AI 导入调 batch_create_in_transaction(db, ...) 共享外部 caller 事务（design §6 R-X3 + §9）
- [P1] M09 全局搜索调 ModuleRelationDAO.search_by_keyword(query, project_id) 走 notes ILIKE（design §9 ADR-003 规则 1）
- [P1] delete_by_node_id 返 deleted_count 整数供 M03 logger 输出（design §9 dao.delete return）
- [P2] M03 删节点事务中 delete_by_node_id 异常向上传播触发 caller 整事务回滚（design §5 R-X3 不自开事务）

### 10. 设计漂移防御 / CI 守护

- [P1] Router 不直 db.query(ModuleRelation) 必走 service 层（design §6 禁止）
- [P1] M08 不直接 INSERT/UPDATE nodes 表（design §6 R-X1 禁止）
- [P1] M03 删节点不依赖 DB CASCADE 触发 activity_log（design §6 R-X2 禁止）
- [P1] activity_log 事件 action_type ∈ {create, update, delete} target_type=module_relation（design §10）
- [P1] ErrorCode 5 个枚举值 + AppError 5 个子类一一对应（design §13 R13-1）
- [P2] RelationResponse 不含 source_node_name / target_node_name / created_by_name 三字段（design §7 M08 R2 P1-01 立修 punt 决策）

### 11. 性能 / 容量

- [P1] GET /relations 大项目 500+ 关联返首屏 <500ms（design §3 ix_module_relations_project 索引）
- [P1] GET /nodes/{nid}/relations 双向索引覆盖 <100ms（design §3 ix source/target_project 索引）
- [P2] delete_by_node_id N=100 关联单事务删除 + N 条 activity_log 写入 <300ms（design §9 + R10-1）
- [P2] search_by_keyword ILIKE %query% 大表 1000+ 关联返 <200ms（设计未加 trigram 索引 / punt M09 sprint 期评估）
