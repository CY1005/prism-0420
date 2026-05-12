---
module: M12
name: comparison
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M12-comparison/00-design.md
  - design/02-modules/M12-comparison/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: US-A3.3 + PRD Q3（功能对比矩阵）
---

# M12 功能对比矩阵 测试点

## 业务流程（H1 / 1 行概述）

M12 是常规 own + 跨模块只读模块：editor 选 N 个 nodes + M 个维度 → GET /matrix 实时读 M03/M04 渲染 N×M → POST /snapshots 走 db.begin() 多表事务（snapshots + items + activity_log）存 G4=B 值快照 → PUT rename 走乐观锁 version → DELETE 物理删 + cascade items；矩阵聚合走 M04 DimensionService.batch_get_by_nodes 接口（不直查 dimension_records 表）。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] editor 选 2 个 node + 3 个维度 GET /api/projects/{pid}/comparison/matrix 返 200 + cells 6 条含 null 未填格（design §7 + tests.md G1）
- [P0] editor POST /api/projects/{pid}/comparison/snapshots 含 name + node_ids + dimension_type_ids 返 201 + snapshot_id + nodes_ref + dimensions_ref + comparison_snapshot_items N×M 行 content 副本（design §7 + tests.md G2）
- [P0] GET /api/projects/{pid}/comparison/snapshots 返 items 按 created_at 倒序 + total（design §9 list_snapshots + tests.md G3）
- [P0] GET /api/projects/{pid}/comparison/snapshots/{snapshot_id} 返 SnapshotDetailResponse 含 items N×M 副本（design §7 + tests.md G4）
- [P0] PUT /api/projects/{pid}/comparison/snapshots/{snapshot_id} 含 name + expected_version=1 返 200 + version=2（design §7 + tests.md G5）
- [P0] DELETE /api/projects/{pid}/comparison/snapshots/{snapshot_id} 返 204 + comparison_snapshot_items 级联删除（design §3 cascade all,delete-orphan + tests.md G6）
- [P1] ComparisonMatrixResponse 仅返 cells / 不嵌 nodes 或 dimension_types metadata（design §7 R-X3 cells-only 裁决）
- [P1] SnapshotResponse 字段无 status / 仅含 version 乐观锁字段（design §3 G2 移除 status + §7 schema）
- [P1] 创建快照时 description 字段可空 / 可省（design §7 Pydantic Optional + §3 nullable=True）
- [P1] PUT rename 成功后再 GET 返新 name + version=2 + updated_at 已刷（design §3 TimestampMixin + §5 乐观锁）

### 2. 边界 / 状态机

- [P0] G2 显式声明 comparison_snapshots 表无 status 字段 / Pydantic SnapshotResponse 无 status 输出（design §4 R4-1 + §3 G2/G4）
- [P0] 对已删除 snapshot_id 再 GET 返 404 COMPARISON_SNAPSHOT_NOT_FOUND（design §4 操作限制 + tests.md G6）
- [P0] 对已删除 snapshot_id 再 PUT 返 404 COMPARISON_SNAPSHOT_NOT_FOUND（design §4 操作限制）
- [P0] 对已删除 snapshot_id 再 DELETE 返 404 COMPARISON_SNAPSHOT_NOT_FOUND（design §4 + 天然幂等说明 §11）
- [P1] POST snapshots name="" 返 422 COMPARISON_SNAPSHOT_NAME_EMPTY（design §13 + tests.md E4）
- [P1] POST snapshots name=129 字符返 422（Pydantic max_length=128 拦截，tests.md E5）
- [P1] POST snapshots name=128 字符边界返 201（max_length=128 含等号，design §7 min_length=1 max_length=128）
- [P1] POST snapshots 不传 node_ids 或 node_ids=[] 返 422 COMPARISON_EMPTY_SELECTION（design §7 min_items=1 + §13 + tests.md E1）
- [P1] POST snapshots 不传 dimension_type_ids 或 dimension_type_ids=[] 返 422 COMPARISON_EMPTY_SELECTION（design §7 min_items=1 + tests.md E2）
- [P1] GET matrix 不传 node_ids query 返 422 COMPARISON_EMPTY_SELECTION（design §13 + tests.md E1）
- [P1] GET matrix 不传 dimension_type_ids query 返 422 COMPARISON_EMPTY_SELECTION（tests.md E2）
- [P1] 无刷新快照 API 端点 / 调用 POST /snapshots/{id}/refresh 返 404（design §4 操作限制 G4-4a + §11）
- [P2] comparison_snapshots.name 无 UNIQUE 约束 / 同名快照允许存在（design §3 Alembic 要点）

### 3. 异常 / 错误

- [P0] node_id 不属于该 project GET matrix 返 404 COMPARISON_NODE_NOT_FOUND 不暴露跨租户信息（design §13 + tests.md E3）
- [P0] 错误响应体格式 `{"error":{"code":"COMPARISON_SNAPSHOT_CONFLICT","message":"..."}}`（design §13 + tests.md ER1）
- [P0] 创建快照 DB 事务任一步失败全量回滚 / comparison_snapshots + items + activity_log 三表无残留（design §5 with db.begin() + tests.md ER4）
- [P1] 快照名超长 130 字符 Pydantic 422 错误响应含 max_length 提示（design §7 + tests.md E5）
- [P1] M04 DimensionService.batch_get_by_nodes 抛异常 → create_snapshot 事务回滚 + snapshots 表无该 id 行（design §5 §9 跨模块依赖）
- [P1] 乐观锁冲突响应 message="Snapshot was modified by someone else; please refresh and retry"（design §13 ComparisonSnapshotConflictError）
- [P2] DB 连接失败访问 matrix 返 503 不泄漏 stacktrace（异常 wrap 标准）

### 4. 权限 / Auth

- [P0] 未登录 GET matrix 返 401 UNAUTHENTICATED（design §8 Server Action session 校验 + tests.md P1）
- [P0] viewer 角色 POST snapshots 返 403 PERMISSION_DENIED（design §8 Router ≥editor + tests.md P3）
- [P0] viewer 角色 PUT rename snapshot 返 403 PERMISSION_DENIED（design §8 写操作 ≥editor 三端点全覆盖）
- [P0] viewer 角色 DELETE snapshot 返 403 PERMISSION_DENIED（design §8 + tests.md T5）
- [P1] viewer 角色 GET matrix 返 200 / 只读接口 viewer 允许（design §8 + tests.md P2）
- [P1] viewer 角色 GET /snapshots 列表返 200 / viewer 允许读（design §8 GET 允许 viewer）
- [P1] viewer 角色 GET /snapshots/{id} 详情返 200 / viewer 允许读（design §8 GET 允许 viewer）
- [P1] editor 持 projectA token 但 POST 到 projectB 的 snapshots 返 403 PERMISSION_DENIED（design §8 Router check_project_access）
- [P2] session 过期访问 matrix 返 401 TOKEN_EXPIRED（auth flow 范式）

### 5. Tenant 隔离

- [P0] userA 持 projectA token GET projectB 的 /snapshots 列表返 403 PERMISSION_DENIED（design §8 + tests.md T1）
- [P0] userA 拿 projectB 的 snapshot_id 但 path 含 projectA 的 GET 返 404 COMPARISON_SNAPSHOT_NOT_FOUND 不暴露 forbidden（design §8 Service 层 + tests.md T2）
- [P0] GET matrix 传入他项目 node_id + path 含本项目返 404 COMPARISON_NODE_NOT_FOUND（design §9 双重 tenant 过滤 + tests.md T3）
- [P0] ComparisonDAO.list_snapshots(other_project_id) 单元测试返空 list（design §9 + tests.md T4）
- [P0] ComparisonDAO.get_snapshot 必含 project_id 过滤 / 跨 project 查询返 None（design §9 ← tenant 过滤注释）
- [P1] comparison_snapshots.project_id 冗余字段写入与 URL path 一致（design §3 R3-3 冗余 tenant 字段）
- [P1] update_snapshot_with_version 含 project_id 过滤 / 跨 project rename 返 0 rows（design §9）
- [P1] ComparisonSnapshotItemDAO.list_items_by_snapshot JOIN snapshots 过滤 project_id / 跨项目读 items 返空（design §9 ComparisonSnapshotItemDAO）

### 6. 并发 / 乐观锁

- [P0] userA 和 userB 同时 PUT rename 同一 snapshot expected_version=1 → 第一个 200 version=2 第二个 409 COMPARISON_SNAPSHOT_CONFLICT（design §5 R5-2 + tests.md C1）
- [P0] 同项目多用户并发 POST 创建不同快照 / asyncio.gather 两个各自 201 互不干扰（design §5 R5-2 + tests.md C2）
- [P1] userA DELETE 后 userB 同时 PUT rename 同一快照 → A 204 + B 收到 404 COMPARISON_SNAPSHOT_NOT_FOUND（design §5 读-删竞态 + tests.md C3）
- [P1] PUT rename 传 expected_version=999 实际 version=1 返 409 COMPARISON_SNAPSHOT_CONFLICT + activity_log 不写（design §5 乐观锁 + tests.md E6 + ER1）
- [P1] 并发 GET matrix 时 userB PUT dimension_record 互不阻塞 / matrix 返当前最新（design §5 实时读 + tests.md C4）
- [P2] update_snapshot_with_version 返 0 rows 时区分快照不存在 vs 版本冲突 / 二次查询确认（design §9 0=冲突或不存在）

### 7. 数据完整性 / Schema 约束

- [P0] comparison_snapshots 无 status 字段 / 表结构中查询 information_schema.columns 不存在 status 列（design §3 G2 移除 + §15 完成度 checklist）
- [P0] 保存快照后修改 M04 dimension_record content / 再 GET snapshot detail items.content 仍是保存时原值（design §3 G4=B 值快照 + tests.md E7 核心场景）
- [P0] 保存快照后 DELETE M03 node / 再 GET snapshot detail items 仍有 content 数据 + node_id=NULL 不报 404 不降级（design §3 ON DELETE SET NULL + §6 不降级 + tests.md E8）
- [P0] DELETE snapshot 级联删除 comparison_snapshot_items / FK ON DELETE CASCADE（design §3 cascade all,delete-orphan）
- [P1] comparison_snapshots 索引 (project_id) 与 (user_id, project_id) 存在（design §3 Alembic 要点）
- [P1] comparison_snapshot_items 索引 (snapshot_id) 与 (node_id) 存在（design §3）
- [P1] comparison_snapshots.nodes_ref 存 list[str(UUID)] / JSONB 序列化为字符串数组非原生 UUID（design §3 G7-M12-R2-09 + §9 类型转换）
- [P1] comparison_snapshots.dimensions_ref 存 list[int] / JSONB 数组（design §3 + §7 schema）
- [P1] comparison_snapshot_items.snapshot_version 冗余 snapshot.version 字段供历史查询（design §3）
- [P1] comparison_snapshot_items.content JSONB 可为 NULL / 表示当时该格未填写（design §3 nullable=True）
- [P1] comparison_snapshots.version 字段乐观锁计数器 / 初始值=1（design §3 default=1）

### 8. activity_log 事件

- [P0] POST snapshots 写 comparison_snapshot_created 1 行 metadata 含 node_ids_count + dimension_type_ids_count + nodes_ref + dimensions_ref + items_count（design §10）
- [P0] PUT rename 写 comparison_snapshot_renamed 1 行 metadata 含 old_name + new_name + old_version + new_version（design §10）
- [P0] DELETE 写 comparison_snapshot_deleted 1 行 metadata 含 name + node_ids_count（design §10）
- [P1] action_type 字面与 frontmatter produces_action_types underscore 形态对齐 / M15 订阅靠机械字符串匹配（design §10 注 sprint 关闸回写）
- [P1] 乐观锁冲突 PUT 失败时不写 comparison_snapshot_renamed activity_log（design §10 事务内调 activity.log）
- [P1] 创建快照事务回滚时不写 comparison_snapshot_created activity_log（design §5 with db.begin() 全量回滚）
- [P1] M12 不订阅任何 M15 action_type / consumes_action_types 为空（design frontmatter）
- [P2] target_type 字面为 comparison_snapshot / target_id 为 snapshot_id UUID（design §10）

### 9. 分层职责 / 跨模块只读纪律

- [P0] comparison_service.py 调 dimension_service.batch_get_by_nodes 不直查 DimensionRecord 表（design §9 R-X1 合规 + batch3 基线补丁决策 6）
- [P0] comparison_service.py 不写 nodes / dimension_records 表 / 对 M03/M04 仅只读（design §6 禁止清单 + §2 依赖契约）
- [P0] dimension_service.batch_get_by_nodes 传入 project_id 参数 / 双重 tenant 过滤在 M04 Service 内执行（design §9 R-X3 共享外部 session + tests.md G2）
- [P1] router 持有 outer txn / service 接外部 session 不主动 begin（design §6 §14.5 sprint 关闸 async 范式回写）
- [P1] comparison_router.py 不直查 DB / DAO 不做业务判断（design §6 禁止清单）
- [P1] DAO 层 list_items_by_snapshot 通过 JOIN comparison_snapshots 过滤 project_id 不直查 items（design §9 ComparisonSnapshotItemDAO）

### 10. UI / UX

- [P1] /project/:id/compare 页面渲染 N×M 矩阵 / 节点选择器 + 维度选择器（design §6 page.tsx + PRD F12 US-A3.3）
- [P1] 矩阵未填格展示空字符串或占位符 / cells content=null 不报错（design §7 MatrixCell content Optional）
- [P1] 快照保存弹窗包含 name 输入 + 可选 description / 提交后弹列表（design §6 snapshot-panel.tsx）
- [P1] 快照列表按 created_at 倒序展示 / 含 name + version + created_at（design §9 list_snapshots order_by desc）
- [P2] 快照详情页节点已删时仍展示 content 但节点名占位 / 不展示空白矩阵（design §6 §3 不降级 + tests.md E8）

### 11. 性能 / 容量

- [P1] 矩阵渲染 3 feature × 20 dim = 60 records 单次 IN 查询 < 10ms（design §9 性能说明）
- [P1] 创建快照 N×M items bulk_insert 单事务完成不分批（design §6 bulk_insert_items + §9 ComparisonSnapshotItemDAO）
- [P2] list_snapshots 默认 limit=50 / 大量快照分页（design §9 limit 参数）

### 12. 跨模块契约（M12 是 M03/M04 的 caller）

- [P0] M12 ComparisonService 调 M04 DimensionService.batch_get_by_nodes 签名匹配 (db, node_ids, dimension_type_ids, project_id) 返 list[DimensionRecord]（design §9 + M04 §6 对外契约）
- [P1] M12 produces 3 个 action_type comparison_snapshot_created/renamed/deleted 写入 M15（design frontmatter）
- [P1] node_ids 类型转换 / Service 层 list[str] → list[UUID] / DAO 入参是 list[UUID]（design §9 类型转换说明 G7-M12-R2-09）
- [P1] M12 不读 M06 竞品表 / 不读 M07 问题表 / 仅 M03 nodes + M04 dimension_records（design §1 边界灰区 G4 + §2 依赖图）

### 13. ErrorCode 完备性（design §13）

- [P1] COMPARISON_SNAPSHOT_NOT_FOUND 对应 ComparisonSnapshotNotFoundError 继承 NotFoundError 默认 404（design §13 R13-1）
- [P1] COMPARISON_SNAPSHOT_NAME_EMPTY 对应 ComparisonSnapshotNameEmptyError 继承 ValidationError 默认 422（design §13 R1-A P2-06 关闸回写）
- [P1] COMPARISON_NODE_NOT_FOUND 对应 ComparisonNodeNotFoundError 继承 ValidationError 默认 422（design §13）
- [P1] COMPARISON_EMPTY_SELECTION 对应 ComparisonEmptySelectionError 继承 ValidationError 默认 422（design §13）
- [P1] COMPARISON_SNAPSHOT_CONFLICT 对应 ComparisonSnapshotConflictError 继承 ConflictError 默认 409（design §13）
- [P2] 复用 PERMISSION_DENIED + UNAUTHENTICATED 全局 ErrorCode（design frontmatter codes_used）

### 14. Idempotency 显式声明

- [P1] M12 无 idempotency_key 操作 / POST snapshots 不带 Idempotency-Key 头（design §11 R11-1 显式声明）
- [P1] 同 name 同 node_ids + dimension_type_ids 连续 POST 两次创建两个独立 snapshot（design §11 允许重复同名快照 + §3 name 无 UNIQUE）
- [P1] DELETE 天然幂等 / 重复 DELETE 返 404 不抛异常（design §11 + §4）
