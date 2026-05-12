---
module: M04
name: feature-archive
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M04-feature-archive/00-design.md
  - design/02-modules/M04-feature-archive/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-001-shadow-prism.md
  - design/adr/ADR-003-cross-module-data-access.md
prd_ref: F4 功能项档案页（PRD Q3.1 功能模块视角 + 测试沉淀）
---

# M04 功能项档案页 测试点

## 业务流程（H1 / 1 行概述）

M04 是功能项档案页核心：基于项目维度配置动态渲染维度卡片，支持空卡片直接编辑（US-B1.3）/ 折叠展开（US-B2.2）/ 完善度进度条（US-B2.3），dimension_records 无状态走乐观锁 version，所有 C/U/D 写 activity_log，对外暴露 R-X3 5 个外部 db session 契约方法供 M03/M11/M12/M13/M17/M18 调用。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/nodes/{nid}/dimensions 创建首条维度返 201 + version=1 + activity_log 一条 create（design §7 + tests.md G1）
- [P0] GET /api/projects/{pid}/nodes/{nid}/dimensions 返 items 含已填 + enabled_dimension_types 含未填（design §7 DimensionListResponse + tests.md G2）
- [P0] PUT /api/projects/{pid}/nodes/{nid}/dimensions/{type_id} 带 expected_version=1 成功返 version=2 + activity_log update 含 old/new version（design §7 + §10 + tests.md G3）
- [P0] DELETE /api/projects/{pid}/nodes/{nid}/dimensions/{type_id} 返 204 + activity_log 一条 delete（design §10 + tests.md G4）
- [P0] GET /api/projects/{pid}/nodes/{nid}/completion 返 enabled_count/filled_count/completion_rate=K/N（design §7 CompletionResponse + tests.md G5）
- [P1] GET /api/projects/{pid}/nodes/{nid}/dimensions/{type_id} 单维度拉取返 DimensionResponse 含 join 字段 dimension_type_key/updated_by_name（design §7）
- [P1] DimensionResponse 含 version 字段供前端 PUT 时回传作 expected_version（design §7 + tests.md G3）
- [P1] DimensionListResponse.enabled_dimension_types 顺序按 project_dimension_configs.sort_order 排序（design §1 In scope + M02 契约）
- [P1] completion_rate 当 enabled_count=0 返 0.0 不抛除零异常（design §1 完善度 + §7）
- [P1] 空内容卡片 GET 时不在 items 但 enabled_dimension_types 含该 type（design §1 US-B1.3 空卡片直接编辑）

### 2. 边界 / 状态机

- [P0] dimension_records 无 status 字段无状态机（design §4 显式声明 + §15 CY ack）
- [P0] DB UNIQUE(node_id, dimension_type_id) 同节点同类型二次 POST 返 409 DIMENSION_DUPLICATE（design §3 + tests.md E5）
- [P1] content={} 空对象返 422 DIMENSION_CONTENT_INVALID（field_schema 校验失败，tests.md E1）
- [P1] content JSON 序列化 > 1MB 返 413 或 422（规约 12.4 边界校验，tests.md E2）
- [P1] dimension_type 在 project_dimension_configs 中 disabled 后 POST 该 type 返 422 DIMENSION_TYPE_DISABLED（design §13 + tests.md E3）
- [P1] dimension_type_id=999 不存在返 404 DIMENSION_TYPE_NOT_FOUND（design §13 + tests.md E4）
- [P1] node_id 已被删除后 POST 返 404 NOT_FOUND node（design §8 _check_node_belongs_to_project + tests.md E6）
- [P1] PUT 不传 expected_version 字段返 422 Pydantic 必填（design §7 DimensionUpdate）
- [P1] DELETE 重复调（已删）返 204 天然幂等（design §11 idempotency 显式声明）
- [P2] content 含 dimension_types.field_schema 未声明字段（extra=forbid）返 422 DIMENSION_CONTENT_INVALID（design §7 ConfigDict）

### 3. 异常 / 错误

- [P0] 乐观锁冲突 PUT 带过期 expected_version 返 409 CONFLICT message"Concurrent modification detected"（design §5 + tests.md ER2）
- [P0] DB UNIQUE 唯一约束冲突响应 `{"error":{"code":"DIMENSION_DUPLICATE"}}`（design §13 + tests.md ER1）
- [P0] dimension_types.field_schema jsonschema 校验失败返 422 DIMENSION_CONTENT_INVALID 带 details（design §7 + tests.md ER3）
- [P0] 主流程入口事务失败（mock activity_log.log 抛异常）dimension_records 写入回滚（design §5 with db.begin + R10-1）
- [P1] 未识别 IntegrityError 兜底返 409 CONFLICT 不暴露 SQL（design §13 + tests.md ER4）
- [P1] node 已删并发场景 PUT 返 404 DIMENSION_NOT_FOUND 而非 CONFLICT（design §8 + tests.md C4）
- [P1] dimension_record_id 不存在的 PUT 返 404 DIMENSION_NOT_FOUND（design §13）
- [P2] DB 不可用调任意端点返 503 不泄漏 stacktrace（规约 7 错误兜底）

### 4. 权限 / Auth

- [P0] 未登录调 GET /dimensions 无 session 返 401 UNAUTHENTICATED（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 角色调 PUT /dimensions 返 403 PERMISSION_DENIED（design §8 Router 写接口要求 editor + tests.md T5）
- [P0] viewer 角色调 GET /dimensions 返 200 允许（design §8 读接口允许 viewer）
- [P0] role 中途由 editor 降为 viewer 二次 PUT 返 403（design §8 Router 层 check_project_access）
- [P1] session 过期后调任意端点返 401 TOKEN_EXPIRED（design §8 Server Action 层）
- [P1] editor 调 POST/PUT/DELETE 三写接口均允许（design §8 三层权限）
- [P1] platform_admin 跨项目调 GET 仍受 check_project_access 限制（design §8 不暴露 forbidden 信息）

### 5. Tenant 隔离

- [P0] userA 持 projectA token 访问 projectB 的 node 返 403 PERMISSION_DENIED（design §8 Router check_project_access + tests.md T1）
- [P0] URL path 是 projectA 但 node_id 实属 projectB 返 404 NOT_FOUND 不暴露 forbidden（design §8 Service _check_node_belongs_to_project + tests.md T2/T4）
- [P0] DimensionDAO.list_by_node(node_id, other_project_id) 直查返空 list（design §9 WHERE project_id 过滤 + tests.md T3）
- [P0] DimensionDAO.update_with_version 跨 project_id 调用 rows=0 视为冲突或越权（design §9 update_with_version + tests.md T3）
- [P1] 创建时 service 层强制 record.project_id = node.project_id（design §3 一致性兜底 + §6.X）
- [P1] DAO 所有新增方法必须带 project_id 入参（design §9 防绕过纪律）
- [P1] alembic CHECK 约束 ck_dim_project_id_not_null 保证 project_id NOT NULL（design §3）
- [P2] PG 14+ generated column 强制 project_id = node.project_id 一致性（design §3 候选 B 兜底）

### 6. 并发 / 乐观锁

- [P0] 同 user 双 tab 并发 PUT 都带 expected_version=1 第一个返 200 v=2 第二个返 409 CONFLICT activity_log 仅 1 条（design §5 + tests.md C1）
- [P0] 不同 user A/B 都拉 v=1，A 先 PUT 成功，B 后 PUT 返 409 提示含 updated_by={A_name}（design §5 + tests.md C2）
- [P0] update_with_version SQL `WHERE version=expected` rows=0 抛 ConflictError（design §9）
- [P1] userA 改 type=1 userB 改 type=2 并发都成功（不同 dimension_records 行 design §3 + tests.md C3）
- [P1] userA DELETE 与 userB PUT 并发 A 返 204 B 返 404 DIMENSION_NOT_FOUND（design §5 + tests.md C4）
- [P1] expected_version=99 远超当前 v=2 返 409 CONFLICT（design §5 + tests.md C2）
- [P2] DimensionDAO.update_with_version 返 rows 数值（0 = 冲突或不存在或越权）调用方分辨（design §9 注释）

### 7. 数据完整性

- [P0] dimension_records UNIQUE(node_id, dimension_type_id) 约束生效（design §3 uq_dim_node_type + tests.md E5）
- [P0] dimension_records.version 默认 1 NOT NULL（design §3 SQLAlchemy + §5）
- [P0] dimension_records.project_id NOT NULL CHECK 约束 ck_dim_project_id_not_null（design §3）
- [P0] dimension_records.content JSONB 无 CHECK 约束运行时 jsonschema 校验（design R3-2 + §7 决策）
- [P1] FK node_id ON DELETE CASCADE 删 node 后 dimension_records 级联删除（design §3 ForeignKey）
- [P1] FK project_id ON DELETE CASCADE 删 project 后 dimension_records 级联删除（design §3）
- [P1] FK dimension_type_id ON DELETE 行为按 dimension_types FK 定义（design §3）
- [P1] 索引 (node_id, dimension_type_id) 主查询命中（design §3 alembic 要点）
- [P1] 索引 (project_id) tenant 过滤候选 B 命中（design §3）
- [P1] 索引 (updated_by, updated_at) activity 检索命中（design §3）

### 8. UI / UX

- [P0] 空维度卡片点击直接进入编辑无独立"添加"按钮（design §1 US-B1.3）
- [P1] 维度区块折叠/展开状态可持久化（design §1 US-B2.2）
- [P1] 完善度进度条实时显示 K/N + 百分比（design §1 US-B2.3）
- [P1] 409 CONFLICT 前端 toast"有人刚改过，请刷新重试"+ 触发刷新（design §5 R5-2 message）
- [P1] DIMENSION_CONTENT_INVALID 前端展示 details 字段定位（design §7 + §13 details）
- [P1] DimensionResponse.updated_by_name 字段 join 出来供前端展示（design §7）
- [P2] 卡片渲染按 enabled_dimension_types 排序顺序展示（design §1 + M02 配置）

### 9. activity_log 事件完备性

- [P0] POST 创建写 1 条 action_type=create target_type=dimension_record metadata 含 node_id/type_id/content_size（design §10）
- [P0] PUT 更新写 1 条 action_type=update metadata 含 node_id/type_id/old_version/new_version（design §10）
- [P0] DELETE 删除写 1 条 action_type=delete metadata 含 node_id/type_id（design §10）
- [P0] activity_log 写入与 dimension_records 写入同事务 任一失败回滚（design §5 多表事务 主流程入口）
- [P1] summary 字段含维度 type_name 中文（design §10 表）

### 10. 对外契约（R-X3 外部 db session 入口）

- [P0] batch_create_in_transaction(db, dimensions, project_id) 接受外部 db session 不自开事务（design §6 R-X3 + R-X3 规则 1）
- [P0] batch_create_in_transaction 每条新建写独立 create activity_log 事件（design §10 R10-1 批量补充）
- [P0] delete_by_node_id(db, node_id, project_id) 接受外部 db session 不自开事务返被删记录数（design §6）
- [P0] delete_by_node_id 每条被删写独立 delete activity_log 事件（design §10 R10-1）
- [P0] batch_get_by_nodes(db, node_ids, dimension_type_ids, project_id) 只读不写 activity_log 不开事务（design §6 batch3 决策 6）
- [P0] batch_get_by_nodes 双重 tenant 过滤 project_id + node_id IN 防越权（design §6）
- [P0] create_dimension_record(db, ...) 单条创建按 dimension_type_key upsert dimension_types id（design §6 M13 baseline-patch）
- [P0] create_dimension_record 写 1 条 create activity_log 含 extra_activity_metadata 合并（design §6）
- [P1] get_latest(db, project_id, node_id, dimension_type_key) 纯读 ORDER BY created_at DESC LIMIT 1（design §6 M13 baseline-patch）
- [P1] get_latest 双重 tenant 过滤 project_id + node_id 防越权（design §6）
- [P1] get_for_embedding(db, dimension_record_id, project_id) 拼接 JSONB content 所有 string 字段返字符串或 None（design §6.X A5 + §6 M18 baseline-patch）
- [P1] get_for_embedding 仅 isinstance str 字段参与拼接非 string 字段跳过（design §6 CY 决策 3 运行期 isinstance 过滤）
- [P1] M04 sprint 期 create/update/delete commit 后不调 embedding_service.enqueue（design §6.X A5 B 路径 推迟到 M18）

### 11. 跨模块契约（ADR-003 边界）

- [P1] dimension_service 读 M02 project_dimension_configs 走 ADR-003 规则 2 只读 import 豁免（design frontmatter cross_module_reads）
- [P1] dimension_service 读 M02 dimension_types 字典走 ADR-003 规则 3 横切表豁免（design frontmatter）
- [P1] dimension_service 校验 M03 nodes 归属走 NodeService 接口非直查（design frontmatter + ADR-003 规则 1）
- [P1] DAO 禁止直查 nodes 表（design §9 防绕过纪律）
- [P1] M12 对比矩阵调 batch_get_by_nodes 不直查 DimensionRecord（design §6 batch3 决策 6 严格边界）

### 12. ErrorCode 注册

- [P1] DIMENSION_NOT_FOUND 注册到 api/errors/codes.py 对应 DimensionNotFoundError(NotFoundError)（design §13）
- [P1] DIMENSION_TYPE_DISABLED 对应 DimensionTypeDisabledError(AppError) http_status=422（design §13）
- [P1] DIMENSION_TYPE_NOT_FOUND 对应 AppError（design §13 + frontmatter codes_added）
- [P1] DIMENSION_CONTENT_INVALID 对应 DimensionContentInvalidError(ValidationError)（design §13）
- [P1] DIMENSION_DUPLICATE 对应 DimensionDuplicateError(AppError) http_status=409（design §13）
- [P1] CI 守护 ErrorCode 枚举行数 == AppError class 定义行数（R13-1）
- [P2] 前端 ErrorCode 同步走 OpenAPI 自动生成 CI diff 校验（design §13 + 规约 7.5）

### 13. 分层职责防御（呼应规约 5.4 反例）

- [P1] importlinter 禁 routers/dimension_router.py 直 `db.query(DimensionRecord)`（design §6 禁止反例）
- [P1] importlinter 禁 services/dimension_service.py 内 `requests.get(...)` 外部调用（design §6 反例）
- [P1] importlinter 禁 dao/dimension_dao.py 内业务判断如 `if record.dimension_type_id == 5`（design §6 反例）
- [P1] DAO 新增方法签名必须含 project_id 入参（design §9 防绕过 + CI 守护）

### 14. idempotency / Queue 显式 N/A

- [P1] M04 无 idempotency_key 操作 update 走乐观锁 create 走 UNIQUE 约束 delete 天然幂等（design §11 显式声明）
- [P1] M04 不投递 Queue 任务 无异步处理（design §12 显式声明）

### 15. 性能 / 容量

- [P2] GET /dimensions 单节点 N 个维度返回时间 < 200ms（design §3 索引主查询）
- [P2] GET /completion 计算 < 100ms 走 enabled_count - filled_count 两个 COUNT（design §1 实时计算）
- [P2] batch_get_by_nodes M12 调用支持 ≥50 nodes × ≥10 types 聚合查询（design §6 对比矩阵聚合读取）
