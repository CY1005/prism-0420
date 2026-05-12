---
module: M11
name: cold-start
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M11-cold-start/00-design.md
  - design/02-modules/M11-cold-start/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: US-A1.5 + PRD Q3.1（4 步向导 / CSV 直入库路径）
---

# M11 冷启动支持 测试点

## 业务流程（H1 / 1 行概述）

M11 是 R-X1 orchestrator 首例：editor 上传标准 CSV → Service 同步校验 → 经 db.begin() 共享事务调 M03/M04/M06/M07 的 batch_create_in_transaction → 写 cold_start_tasks 状态 + activity_log；终态 completed/failed 不可重操，无 idempotency，无 Queue。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] editor 上传含 4 类列（节点路径/维度/竞品/问题）的合法 CSV 返 200 status=completed + success_rows=N（design §7 + tests.md G1）
- [P0] 仅含节点路径列的最小 CSV 上传返 completed + nodes 创建成功 + dimensions/competitors/issues 计数为 0（design §1 in scope + tests.md G2）
- [P0] GET /api/projects/{pid}/cold-start/{task_id} 返 status=completed + success_rows + completed_at 非 null + error_report=null（design §7 + tests.md G3）
- [P0] GET /api/projects/{pid}/cold-start/template 返 200 Content-Type text/csv 含标准列头（design §7 + tests.md G4）
- [P1] GET /api/projects/{pid}/cold-start 返 items 按 created_at 倒序（design §9 list_by_project + tests.md G5）
- [P1] CSV 含全部 4 类列数据时 metadata 写入 nodes_created/dimensions_created/competitors_created/issues_created 四个计数（design §10 cold_start.completed metadata）
- [P1] activity_log 写 cold_start.create + cold_start.completed 两条独立事件（design §10 R10-1 批量写 N 条独立 + tests.md G1）
- [P2] source_filename 字段回显在 ColdStartTaskResponse 中（design §7 Pydantic schema）

### 2. 边界 / 状态机

- [P0] pending → validating → importing → completed 完整正向流转一次跑过（design §4 mermaid）
- [P0] validating → failed 校验阶段失败转换允许 + 不进 importing（design §4 + tests.md E3）
- [P0] importing → failed 入库阶段任一 service 抛异常转换允许 + 全量回滚（design §4 + tests.md ER2/ER4/ER5）
- [P0] completed 任务再 POST upload 返 409 COLD_START_TASK_FINALIZED（design §4 禁止转换表 + tests.md ER6）
- [P0] failed 任务再触发状态转换返 409 COLD_START_TASK_FINALIZED（design §4 终态不可变）
- [P1] CSV 仅含列头 0 数据行返 422 COLD_START_CSV_INVALID（design §13 + tests.md E1）
- [P1] CSV 缺必填列 node_path 返 422 COLD_START_CSV_INVALID（design §13 + tests.md E2）
- [P1] 第 N 行 node_path 为空字符串返 422 COLD_START_ROW_VALIDATION_FAILED + error_report 含 row+field（design §13 + tests.md E3）
- [P1] node_path 非 `/` 分隔格式返 422 COLD_START_ROW_VALIDATION_FAILED message=invalid format（tests.md E4）
- [P1] CSV 文件 > 10MB（MAX_FILE_BYTES）返 413 COLD_START_FILE_TOO_LARGE（design §1 G6 + tests.md E5）
- [P1] CSV 行数 > 1000（MAX_ROWS）返 422 COLD_START_CSV_INVALID（design §1 G6 同步阈值）
- [P1] summary 字段 > 5000 字符返 422 COLD_START_ROW_VALIDATION_FAILED field=summary（tests.md E7）
- [P1] competitor.node_path 引用 CSV 内不存在的路径返 422 COLD_START_ROW_VALIDATION_FAILED（tests.md E8）
- [P1] importing → validating 逆向状态转换返 409 COLD_START_INVALID_STATE_TRANSITION（design §4 R4-2）
- [P1] pending → importing 跳过 validating 返 409 COLD_START_INVALID_STATE_TRANSITION（design §4 R4-2）

### 3. 异常 / 错误

- [P0] M06 CompetitorService.batch_create_in_transaction 抛异常 → M03/M04 已写入数据全量回滚 + cold_start_task.status=failed + error_report 含 stage（design §4 + tests.md ER4）
- [P0] M07 IssueService.batch_create_in_transaction 抛异常（四步最后一步失败）→ M03/M04/M06 已写入数据全量回滚（design §4 共享事务 + tests.md ER5）
- [P0] batch_create 异常返 500 COLD_START_BATCH_INSERT_FAILED + nodes/dimensions/competitors/issues 表无残留（design §13 + tests.md ER2）
- [P0] 校验失败返响应体 `{"error":{"code":"COLD_START_ROW_VALIDATION_FAILED","message":"...","details":[{row,field,message}]}}`（design §13 + tests.md ER1）
- [P1] 跨模块 Service NodeService 抛 ValidationError → M11 wrap 为 COLD_START_BATCH_INSERT_FAILED（design §13 R13-2 跨模块 wrap + tests.md ER3）
- [P1] 非 .csv MIME 类型（.xlsx）返 422 COLD_START_CSV_INVALID（tests.md ER7）
- [P1] node_path 含 SQL 注入字符串 `'; DROP TABLE nodes;--` 不执行 SQL 仅做行校验或正常入库（design + tests.md E6）
- [P2] DB 连接失败上传期间返 503 不泄漏 stacktrace（异常 wrap 标准）

### 4. 权限 / Auth

- [P0] 未登录（无 session）POST upload 返 401 UNAUTHENTICATED（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 角色 POST upload 返 403 PERMISSION_DENIED（design §8 Router check_project_access editor + tests.md T5）
- [P0] editor 持有 projectA token 但 POST 到 projectB 的 upload 返 403 PERMISSION_DENIED（design §8 + tests.md T1）
- [P1] role 降级中（editor → viewer）再次上传返 403 PERMISSION_DENIED（tests.md P3）
- [P1] session 过期上传返 401 TOKEN_EXPIRED（tests.md P2）
- [P1] GET /cold-start/template 需 session 校验 / 未登录返 401（design §9 豁免清单注明仍需 session）

### 5. Tenant 隔离

- [P0] userA 查询 userB 在 projectB 创建的 task_id 返 404 NOT_FOUND 不暴露 PERMISSION_DENIED（design §9 DAO project_id 过滤 + tests.md T2）
- [P0] ColdStartDAO.list_by_project(other_project_id) 单元测试返空 list（design §9 tenant 过滤 + tests.md T3）
- [P0] URL 路径 project_id=A 但 CSV 内 competitor.node_path 引用 projectB 节点 → Service 拒绝（design §1 节点 project_id 校验 + tests.md T4）
- [P1] cold_start_tasks.project_id 冗余字段写入与 URL path 一致（design §3 R3-3 冗余 tenant 字段）
- [P1] ColdStartDAO.get_by_id(task_id, project_id) 过滤双键（design §9 + 防越权查询）

### 6. 并发 / 数据完整性

- [P0] 同用户同项目重传同一 CSV（同 source_hash）创建第二条独立任务并执行（G2/G6 无 idempotency + tests.md C1）
- [P0] 不同用户同项目并发上传不同 CSV / asyncio.gather 同时跑两个任务各自成功互不影响（design §5 4 维 + tests.md C3）
- [P1] 不同用户同项目并发上传含相同 node_path 的 CSV → M03 nodes 表产生重复同名节点（G7-M11-R2-08 已知行为 + tests.md C4）
- [P1] 同用户不同项目传同 CSV 各自独立任务独立入库不串项目（tests.md C2）

### 7. 数据完整性 / Schema 约束

- [P0] cold_start_tasks.status CHECK 约束仅允许 5 个枚举值 / INSERT 'partial_failed' 失败（design §3 G1 三重防护 + G6 移除）
- [P0] cold_start_tasks.status 字段 String(20) + Mapped[ColdStartStatus] 三重防护（design §3 R3-2）
- [P1] cold_start_tasks 索引 (project_id, status) 与 (user_id, created_at) 存在（design §3 Alembic 要点）
- [P1] cold_start_tasks 无 UNIQUE(user_id, project_id, source_hash) 约束 / 同 hash 重复 INSERT 不冲突（design §3 G2/G6 移除）
- [P1] cold_start_tasks.error_report JSONB 列结构 [{row, field, message}] 可读出（design §3）
- [P1] cold_start_tasks 表无 expires_at 字段（design §3 G2/G6 移除）
- [P1] source_hash 字段非 null 写入（SHA256(CSV bytes)），供错误报告/审计用非幂等（design §3）

### 8. activity_log 事件

- [P0] cold_start.create 写 1 行 metadata 含 source_hash/source_filename/total_rows（design §10）
- [P0] cold_start.completed 写 1 行 metadata 含 total_rows/success_rows/nodes_created/dimensions_created/competitors_created/issues_created（design §10）
- [P0] cold_start.failed 写 1 行 metadata 含 stage/failed_rows/error_code（design §10）
- [P1] 校验失败路径只写 cold_start.create + cold_start.failed / 不写 cold_start.completed（design §10 + tests.md ER1）
- [P1] batch_create 异常路径写 cold_start.failed metadata.stage=importing（design §10）
- [P1] M11 不订阅 M15 activity_log（consumes_action_types 为空，design frontmatter）

### 9. 分层职责 / R-X1 orchestrator 纪律

- [P0] cold_start_service.py 不直接 db.execute INSERT INTO nodes/dimension_records/competitors/issues（design §6 禁止清单 + R-X1）
- [P0] cold_start_service.py 调 NodeService.batch_create_in_transaction 传入 project_id（design §1 依赖契约）
- [P0] cold_start_service.py 调 DimensionService/CompetitorService/IssueService 各 batch_create_in_transaction 全部传入 project_id（design §1）
- [P1] router 持有 outer txn / service 不主动 begin/commit/rollback（design §5 sprint 实装范式 P1-01 注释 2026-05-08）
- [P1] service 在 raise 前 dao.update task=failed + error_report / router 提交该状态后 rollback 业务数据（design §5）
- [P1] cold_start_router.py 不直查 DB / DAO 不做业务校验（design §6 禁止）

### 10. UI / UX

- [P1] 项目首次进入若节点数=0 展示"上传 CSV 快速开始"引导入口（design §1 空状态引导）
- [P1] CSV 上传向导 4 步（上传 → 预览 → 映射 → 确认）/ PRD Q3.1 沿用 Prism 范式（PRD Q3.1）
- [P1] 错误行报告 UI 展示 row+field+message 列表（design §1 + tests.md ER1）
- [P2] 上传中 status=validating/importing 前端展示进度文案（design §4 状态机）
- [P2] 终态 completed 跳转项目模块树页 / failed 停留并展示重传 CTA（design §4 + §1 空状态引导）

### 11. 性能 / 容量

- [P1] CSV 1000 行 + 10MB 阈值边界同步处理在 HTTP timeout 内完成（design §1 G6 同步阈值 / MAX_FILE_BYTES + MAX_ROWS 真实代码 line 65-66）
- [P1] 超阈值不升级 Queue 直接返提示用户分批（design §1 G6 暂不升级声明）
- [P2] cold_start_tasks 表无过期清理 / 历史任务保留可查询（design §4 completed 状态保留）

### 12. CSV 解析 / 文件处理

- [P0] CSV 文件解析 io.StringIO 构造测试用 CSV 流不依赖真实文件（tests.md 测试要点）
- [P1] CSV 编码 UTF-8 BOM 头被正确处理不当 node_path 一部分（CSV 解析常见坑）
- [P1] CSV 含 CRLF 与 LF 混合换行符均能解析（CSV 解析鲁棒性）
- [P1] CSV 字段值含 `,` 但被双引号包裹正确解析不分列（CSV 标准转义）
- [P2] CSV 末行无 `\n` 仍能解析最后一行不丢失（CSV 解析鲁棒性）

### 13. ErrorCode 完备性（design §13）

- [P1] COLD_START_TASK_NOT_FOUND 对应 ColdStartTaskNotFoundError 子类存在 http_status 继承 NotFoundError（design §13 R13-1）
- [P1] COLD_START_CSV_INVALID 对应 422 子类（design §13）
- [P1] COLD_START_ROW_VALIDATION_FAILED 对应 422 子类（design §13）
- [P1] COLD_START_BATCH_INSERT_FAILED 对应 500 子类（design §13）
- [P1] COLD_START_TASK_FINALIZED 对应 409 子类（design §13）
- [P1] COLD_START_INVALID_STATE_TRANSITION 对应 409 子类（design §13）
- [P1] COLD_START_FILE_TOO_LARGE 对应 413 子类（design §13）
- [P2] COLD_START_DUPLICATE 已移除 / 枚举与子类均不存在（design §13 G2/G6 移除）

### 14. 跨模块契约（M11 是 M03/M04/M06/M07 的 caller）

- [P1] NodeService.batch_create_in_transaction 节点传入按拓扑排序父先子后（design §3 G5 + tests.md）
- [P1] M11 不订阅任何 M15 action_type / consumes_action_types 为空（design frontmatter）
- [P1] M11 produces 3 个 action_type cold_start.create/completed/failed 写入 M15（design frontmatter）
- [P2] M17 同接口 batch_create_in_transaction 复用 / M11 同步 caller / M17 Queue caller 互不影响（design §1 边界灰区）
