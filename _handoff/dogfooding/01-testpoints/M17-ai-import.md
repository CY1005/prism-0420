---
module: M17
name: ai-import
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M17-ai-import/00-design.md
  - design/02-modules/M17-ai-import/tests.md
  - design/02-modules/M17-ai-import/audit-report.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F17 AI 智能导入 / US-B1.8 / PRD Q3.1（4 步向导 + git URL + .git 包）
pilot: true
complexity: high
async_mode: Queue（arq + Redis）+ WebSocket 双向
---

# M17 AI 智能导入 测试点

## 业务流程（H1 / 1 行概述）

M17 是异步 pilot 模块：3 种输入形态（zip / git URL / .git 包）经 4 步向导（上传 → 预览 → 映射 review → 确认入库），后端 arq Queue 跑 3 步 AI 流水线（拆分+归类 / 提取+补全 / 关联+去重+差异标注），WebSocket 双向推进度+收 cancel 命令，importing 阶段 M17 作为 orchestrator 调 M03/M04/M06/M07 各 Service 的 batch_create_in_transaction 共享单一 db.begin() 外层事务，idempotency key = (user_id, project_id, source_hash) 7 天复用。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/imports 上传 zip happy path 返 201 + task_id + status=pending + Queue 拉起 extract（design §7 + tests.md G1）
- [P0] WebSocket 推 status_change 序列 pending → extracting → ai_step1 → ai_step2 → awaiting_review → ai_step3 → importing → completed 8 状态全推（design §4 + §7 ProgressEvent + tests.md G1）
- [P0] GET /api/projects/{pid}/imports/{tid}/review 在 awaiting_review 阶段返 ReviewDataResponse 含 proposed_nodes + proposed_dimensions + proposed_competitors + proposed_issues + confidence_scores（design §7 ReviewDataResponse）
- [P0] POST /api/projects/{pid}/imports/{tid}/confirm 用户调整后 nodes/dimensions/skip_items 触发 ai_step3 + importing 入库（design §7 ReviewConfirmRequest + tests.md G4）
- [P0] importing 完成后 activity_log 写齐 8 类事件 import.create / status_change / ai_step_complete×3 / review_confirmed / batch_insert / 终态 1 条（design §10）
- [P0] git URL 形态 extract 阶段走 git clone 成功后流程同 zip（design §1 in scope + tests.md G2）
- [P0] .git 包形态 extract 解压识别 bare repo 流程同 zip（design §1 in scope + tests.md G3）
- [P1] POST /api/projects/{pid}/imports/{tid}/cancel 在 awaiting_review 状态返 204 + status=cancelled + S3 暂存清理（design §7 + tests.md SM4）
- [P1] POST /api/projects/{pid}/imports/{tid}/retry partial_failed 状态触发 ai_step3 重跑仅处理 failed items（design §7 + tests.md R6）
- [P1] GET /api/projects/{pid}/imports 列表返按 created_at DESC 默认 limit 50（design §9 list_by_project）
- [P1] GET /api/projects/{pid}/imports/{tid} 返 ImportTaskResponse 含 progress 0-100 + error_message + expires_at（design §7 ImportTaskResponse）
- [P1] confirm 用户改 node 名 + 跳过 2 个 item 最终入库结果 nodes 含用户调整命名 skip_items 不写入（tests.md G4）
- [P1] zip 内全二进制/图片 step1 识别 0 模块 status=completed + 空 review_data + activity_log "0 modules detected"（tests.md E6）
- [P2] git_ref 不传默认 main/master（design §7 ImportCreateRequest git_ref Optional）

### 2. 边界 / 状态机

- [P0] pending → ai_step3 跳步返 409 IMPORT_INVALID_STATE_TRANSITION（design §4 禁止表 + tests.md SM1）
- [P0] completed → 任何状态返 409 IMPORT_TASK_FINALIZED 终态不可变（design §4 + tests.md SM2）
- [P0] cancelled → 任何状态返 409 IMPORT_TASK_FINALIZED（design §4 + tests.md SM3）
- [P0] failed → 任何状态返 409 IMPORT_TASK_FINALIZED（design §4 audit B4 修复后补全）
- [P0] partial_failed → 仅 ai_step3 / cancelled 合法其他出边抛 IMPORT_INVALID_STATE_TRANSITION（design §4 非常规态登记表 R4-3a）
- [P0] awaiting_review → importing 跳过 ai_step3 返 409（design §4 audit B4 修复）
- [P1] 任意 → pending 拒绝 pending 仅创建时（design §4 audit B4 修复）
- [P1] importing 阶段事务粒度 = 整任务 single transaction 任一 batch_create_in_transaction 失败全 ROLLBACK 未 commit INSERT（design §4 importing 事务粒度 P5 audit F-5）
- [P1] importing 状态用户 cancel SQLAlchemy with 块 raise CancelledError 自动 ROLLBACK 已写入 nodes/dimensions/competitors/issues 全无（design §4 cancel 副作用 + tests.md SM5）
- [P1] partial_failed 半终态 30 天未重试 cron 清理转 [*]（design §4 R4-3a）
- [P1] cancelled 24h 后自动删除（design §4 mermaid 终态出边）
- [P1] failed 30 天后清理任务 + items + S3 暂存（design §4 + tests.md R4）
- [P2] source_type 非 zip/git_url/git_bundle 三值返 422 CHECK constraint 拦截（design §3 ck_import_source_type）

### 3. 异常 / 错误

- [P0] zip 损坏 extract 阶段 status=failed + IMPORT_INVALID_SOURCE（design §13 + tests.md E2）
- [P0] git URL 不可达 extract 重试 3 次都失败 status=failed + IMPORT_INVALID_SOURCE + error_metadata.dead_letter=true（design §12 重试策略 + tests.md E3）
- [P0] AI 调用失败 1 次自动 1s 后重试 progress 不变 activity_log 写一条 retry（design §12 指数退避 + tests.md R1）
- [P0] AI 调用失败 2 次 4s 后重试（tests.md R2）
- [P0] AI 调用失败 3 次 status=failed + IMPORT_AI_PROVIDER_ERROR + dead_letter=true（design §12 + tests.md R3）
- [P0] AI 输出格式错（非 JSON）step1 重试 3 次都格式错最终 status=failed + IMPORT_AI_PROVIDER_ERROR（tests.md E7）
- [P0] importing 阶段 batch_create_in_transaction 部分 item 失败整任务事务 ROLLBACK + status=partial_failed + items 状态保留可重试（design §4 + tests.md R5）
- [P1] 超大 zip >500MB 返 422 "单 zip 上限 500MB"（tests.md E1）
- [P1] git URL 私有 repo 无 token extract 失败 error_message 含 "authentication failed"（tests.md E4）
- [P1] .git 包格式错（非 git bare repo）返 422 IMPORT_INVALID_SOURCE（tests.md E5）
- [P1] confirm 在非 awaiting_review 状态返 409 IMPORT_INVALID_STATE_TRANSITION（tests.md E9）
- [P1] AI Provider 配额超限 status=failed + IMPORT_QUOTA_EXCEEDED 429（design §13 ImportQuotaExceededError）
- [P1] Queue worker crash 中途 arq 持久化保证自动重新拉起从最后 status 继续（tests.md R7）
- [P1] review_data 超大 >50MB JSONB 写 PG TOAST 自动压缩可读出（design §3 review_data TOAST + tests.md E8）
- [P1] activity_log 写失败不回滚主业务事务（design §10 与 M14 范式一致）
- [P2] 死信 30 天后 cron 删 task + items + S3 暂存文件 + activity_log 一条 cleanup（design §12 + tests.md R4）
- [P2] 死信通知 WebSocket 推送 + email TBD 用户关浏览器时 WS 失效仅 activity_log 留底（audit R2-06）

### 4. 权限 / Auth

- [P0] viewer 角色 POST /imports 返 403 PERMISSION_DENIED（design §8 Router check_project_access role=editor + tests.md P1）
- [P0] 未登录 POST /imports 返 401 UNAUTHENTICATED（design §8 Server Action getServerSession + tests.md P2）
- [P0] Service 层 _check_task_belongs_to_user_and_project task 不属于 user+project 返 404 IMPORT_TASK_NOT_FOUND（design §8 + §13）
- [P0] Queue 消费者入口必先 TaskPayload.parse() 后 service.check_access(user_id, project_id, task_id) 双校验（design §8 + §12 Queue 消费者入口校验）
- [P0] WebSocket 握手阶段 task_id 归属 user 不通过 close(1008)（design §8 WebSocket connect 握手校验 + tests.md T5）
- [P0] WebSocket 每命令入口 ClientCommand.task_id 必等于握手 task_id 不等则 close(1008)（design §8 audit B6 修复 + audit R2-03）
- [P1] role 中途降级 editor → viewer 已提交任务 Queue 继续跑（Queue 不查实时权限）新提交被拒（tests.md P3）
- [P1] 项目删除时进行中任务级联删 FK CASCADE + 已写入数据级联删 + Queue worker 检测 task 不存在中断（tests.md P4）
- [P1] Server Action 层文件上传到 S3 前必 session 校验（design §6 Server Action）
- [P2] cancel/retry/confirm 三 endpoint 同样三层防御（Server Action / Router / Service）

### 5. Tenant 隔离

- [P0] userA 用 projectA token 访问 projectB 的 task_id 返 404 IMPORT_TASK_NOT_FOUND 不暴露 forbidden（design §9 DAO tenant 过滤 + tests.md T1）
- [P0] Queue payload 篡改 user_id 直接 Redis 投递 service.check_access 失败任务标 failed + 安全日志（design §8 Queue 消费者侧 + tests.md T2）
- [P0] Queue payload 缺 project_id Pydantic 校验失败 ValidationError → 任务死信（design §12 TaskPayload 强制字段 + tests.md T3）
- [P0] DAO.get_by_id 必 WHERE project_id=? AND user_id=? 双过滤（design §9 + tests.md T4）
- [P0] idempotency find_idempotent 必含 project_id 过滤防 userA 在 projectA 传 zip-X 在 projectB 命中 projectA 的 task 跨租户污染（design §9 B1 修复 + §11 + audit R2-01）
- [P0] DB 唯一约束 UNIQUE(user_id, project_id, source_hash) 同 zip 不同 project 不命中（design §3 uq_import_user_project_hash + audit B1）
- [P1] WebSocket 握手 URL path 中 task_id 归属 user 才 accept 否则 401（tests.md T5）
- [P1] DAO.list_by_project 必 WHERE project_id + user_id 双过滤不泄露他 user 任务（design §9 list_by_project）
- [P1] activity_log 写入 user_id 用 Queue payload 传入 user_id 而非 Queue worker 进程身份（design §10 + 清单 3）
- [P1] cron import_cleanup_dead_letter Queue payload user_id=SYSTEM_USER_UUID + project_id=None 显式跨 tenant 清理（design §12 cron user_id 边界 ADR-002 §1.1）

### 6. 并发 / 乐观锁

- [P0] 同 user 1s 内重复提交同 zip 两次都返 200 + 同一 task_id idempotency 命中只跑一次 AI（design §11 + tests.md C1）
- [P0] 同 user 不同 zip-A + zip-B 并发提交两独立 task 独立 Queue 处理互不阻塞（tests.md C2）
- [P0] 多 user 同 project 同时提交 user_id 不同 idempotency 不命中 Queue 隔离正确（tests.md C3）
- [P1] 用户 cancel 同时 Queue worker 在跑 worker 检测 status=cancelled 中断处理 + 已写入数据回滚 + WS 推 cancelled（tests.md C4）
- [P1] review 阶段 userA 改 mapping userB（同项目 editor）也改 last-write-wins 第二写覆盖第一不丢数据（design §5 并发列 + tests.md C5）
- [P1] review 阶段无乐观锁 version 字段 接受设计风险（design §5 清单 2 ❌ 不触发 + audit R1-04 + B7）
- [P1] importing 阶段 partial_failed 后用户 retry 与另一 user 操作同 task 并发 retry 仅一个生效（design §4 + tests.md R6）
- [P2] DB UNIQUE(user_id, project_id, source_hash) 并发 INSERT 竞态触发 IntegrityError service 层 catch 转 ImportTaskDuplicateError（design 06 清单 6）

### 7. 数据完整性

- [P0] import_tasks 11 状态 CHECK constraint 拒绝非枚举值（design §3 ck_import_task_status）
- [P0] import_task_items 5 状态 CHECK constraint 拒绝非枚举值（design §3 ck_import_item_status）
- [P0] source_hash zip=SHA256(zip内容) / git_url=SHA256(git_url+git_ref) / git_bundle=SHA256(.git 包) 算法一致（design §11 source_hash 算法）
- [P0] importing 单事务包 M03 NodeService + M04 DimensionService + M06 CompetitorService + M07 IssueService + activity_log 共享同 db session 任一失败全 ROLLBACK（design §4 + §5 多表事务）
- [P0] M17 不直 INSERT 跨模块表必经 batch_create_in_transaction Service（design §1 + audit B2 修复 + R-X1）
- [P1] cascade ondelete CASCADE project_id 删除时 import_tasks 级联删 + items relationship cascade="all, delete-orphan"（design §3 ForeignKey ondelete + relationship cascade）
- [P1] expires_at 字段双用 idempotency 7 天 vs 死信 30 天按 status 区分（design §3 + §11）
- [P1] idempotency status 复用范围 IN ('completed','awaiting_review','partial_failed') 不复用 ('failed','cancelled')（design §9 find_idempotent + §11 + audit R2-04）
- [P1] target_node_id FK ondelete SET NULL 即使 node 被删 item 不丢（design §3 ImportTaskItem.target_node_id）
- [P1] retry_count integer 默认 0 单 item 重试上限 3 次后 status=failed（design §3 + §12 重试策略）
- [P2] progress 0-100 整数 status_change 时同步更新（design §3 + §10 metadata）

### 8. UI / UX

- [P0] 4 步向导 page.tsx 上传 → 预览 → 映射 → 确认 步骤指示器（design §6 Page）
- [P0] import-progress.tsx WebSocket 客户端连接进度条实时刷新（design §6 Component）
- [P0] review-mapping.tsx 用户可改 node 名 / 重新归属 / 删除 / 跳过 item（design §7 ReviewConfirmRequest）
- [P1] 进度条卡死信号客户端 30 秒无 progress_update 时降级提示（design §7 ProgressEvent + audit R3-05 隐含）
- [P1] failed 状态 UI 展示 error_message + dead_letter 标识 + 不允许重试按钮（design §3 error_metadata）
- [P1] partial_failed 状态 UI 显示"重试失败 items"按钮（design §4 + tests.md R6）
- [P1] cancel 按钮 awaiting_review / importing 状态可见 已 completed/failed/cancelled 时隐藏（design §4 状态机）
- [P2] confidence_scores 在 review UI 展示 AI 自评置信度低于阈值时高亮提示（design §7 ReviewDataResponse）

### 9. 性能（如适用）

- [P1] 1MB zip 10 文件端到端 < 5 分钟（design §12 token 时间代价 3-10 分钟范围下沿）
- [P1] review_data >50MB JSONB 读出性能下降但可用（PG TOAST 自动压缩 + tests.md E8）
- [P1] 大 zip 分 chunk ImportAIStepPayload.chunk_id 可选机制（design §12 + audit R3-3 隐含）
- [P2] DAO list_by_project limit 50 + index ix_import_user_created 查询 < 100ms（design §3 索引 + §9）
- [P2] 同 project 多任务 ix_import_project_status 索引查询 < 100ms（design §3 ix_import_project_status）

### 10. WebSocket 协议（M17 异步 pilot 专项）

- [P0] WS 握手成功后 100ms 内推当前 status + progress（tests.md WS1）
- [P0] 客户端发 ClientCommand{type:"cancel", task_id} 服务器调 service.cancel + 推 cancelled 事件（tests.md WS2）
- [P0] 客户端发未知 type 推 error 事件连接保留（tests.md WS3）
- [P1] 长连接 30 分钟无事件服务器推 ping 客户端无回应关闭（tests.md WS4）
- [P1] 任务完成后新客户端连接推 final status + completed 后关闭（tests.md WS5）
- [P1] WS 握手期 task_id 不属当前 user close(1008)（design §8 + tests.md T5）
- [P1] WS 每命令 ClientCommand.task_id != 握手 task_id close(1008) 防同连接 cancel 任意 task（design §8 audit B6）
- [P2] ProgressEvent.metadata 失败时含 step + retry_count 客户端可展示（design §7 ProgressEvent.metadata）

### 11. Queue 异步路径（M17 pilot 核心）

- [P0] TaskPayload 基类强制 user_id + project_id 缺则 Pydantic ValidationError（design §12 + design 06 清单 3）
- [P0] Queue 任务清单 6 个 import_extract / ai_step1 / ai_step2 / ai_step3 / batch_insert / cleanup_dead_letter 全部 payload 继承 TaskPayload（design §12 任务清单）
- [P0] 重试策略单步 3 次指数退避 1s/4s/16s（design §12 + tests.md R1-R3）
- [P0] 死信 error_metadata.dead_letter=true + 30 天保留（design §12 + tests.md R4）
- [P1] ImportExtractPayload.source_type 必用 ImportSourceType 枚举非裸 str（design §12 audit B5 修复 mypy strict）
- [P1] ImportAIStepPayload.step Literal[1,2,3] 限定取值非 int（design §12 audit B5）
- [P1] ImportBatchInsertPayload.confirmed_data 强类型 ConfirmedImportData 非裸 dict（design §12 audit B5 + ConfirmedNodeData/ConfirmedDimensionData）
- [P1] Queue worker crash arq 持久化重新拉起从最后 status 继续不丢任务（tests.md R7）
- [P1] idempotency_key payload 字段任务级去重防重复 enqueue（design §12 TaskPayload.idempotency_key）
- [P2] cron import_cleanup_dead_letter daily 跑删 expires_at < NOW() 的 failed 任务（design §3 + §12）

### 12. Idempotency

- [P0] idempotency 命中返 200 + ImportTaskDuplicateError http_status=200（非错误）+ 复用上次 task_id（design §13 + §11）
- [P0] idempotency key = (user_id, project_id, source_hash) 三元组缺一不命中（design §11 + audit B1 修复）
- [P0] 复用范围 status IN ('completed','awaiting_review','partial_failed')（design §9 + §11）
- [P0] 不复用范围 status IN ('failed','cancelled') 让用户重新跑（design §11）
- [P1] created_at > NOW() - INTERVAL '7 days' 才命中过期 task 不复用（design §11 + §9）
- [P1] 同 user 同 project 不同 source_hash 不命中（design §3 UNIQUE 三元组）
- [P1] 不同 user 同 project 同 source_hash 不命中 user_id 是 key 一部分（design §3 + §11）
- [P1] 同 user 不同 project 同 source_hash 不命中 防跨项目数据污染（audit R2-01 B1 修复）

### 13. ErrorCode 映射

- [P0] IMPORT_TASK_NOT_FOUND 404 task 不存在或不属于 user/project（design §13）
- [P0] IMPORT_TASK_FINALIZED 409 终态不可变 completed/cancelled/failed → 任意（design §13）
- [P0] IMPORT_INVALID_SOURCE 422 zip 损坏 / git URL 无效 / .git 包格式错（design §13）
- [P0] IMPORT_AI_PROVIDER_ERROR 503 AI 调用重试用尽（design §13）
- [P0] IMPORT_INVALID_STATE_TRANSITION 409 状态机非法转换（design §13 audit B4）
- [P1] IMPORT_BATCH_INSERT_FAILED 500 入库阶段失败事务 ROLLBACK（design §13 audit B3 修复）
- [P1] IMPORT_QUOTA_EXCEEDED 429 用户/项目 AI 配额超限（design §13 audit B3 修复）
- [P1] IMPORT_TASK_DUPLICATE 200（非错误） idempotency 命中复用（design §13 audit B3 修复）

### 14. activity_log 事件

- [P0] import.create 创建任务写 metadata {source_hash, source_uri_hash, file_size}（design §10）
- [P0] import.status_change 状态转换写 metadata {old_status, new_status, progress}（design §10）
- [P0] import.ai_step_complete 每步完成写 metadata {step, items_processed, ai_tokens_used, cost}（design §10）
- [P1] import.review_confirmed 用户确认 review 写 {nodes_count, skip_count, modified_count}（design §10）
- [P1] import.batch_insert 批量入库完成写 {nodes, dimensions, competitors, issues}（design §10）
- [P1] import.cancel 用户取消写 {at_status, cleanup_count}（design §10）
- [P1] import.failed 任务失败写 {step, error_code, retry_count}（design §10）
- [P1] import.partial_failed 部分失败写 {success_count, failed_count, failed_items}（design §10）

### 15. 演进 / 演进风险（audit 推导）

- [P1] AI Provider 任务级别固定 ai_provider/ai_model 多 provider 并发（step1 用 Codex / step2 用 Claude）当前数据模型不支持（audit R3-04）
- [P1] 3 步 AI 流水线硬编码若未来加 step4 合规检查 状态机/枚举/Queue/前端 4 处变更未抽 ai_step_runner 通用函数（audit R3-03）
- [P2] 死信通知 WebSocket + email TBD email 路径未实现 用户关浏览器时仅 activity_log 留底无主动通知（audit R2-06）
- [P2] M17 §12 Queue payload 基类对 M18 可复用 但批量事务模式（5 表原子写入）对 M18 单 node embedding 计算过重（audit R3-01）
- [P2] 11 状态枚举 ai_step1/2/3 三状态 M18 复用时是噪音 是否合并 processing + progress 字段 当前未讨论（audit R3-05）
