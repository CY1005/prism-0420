---
scope: cross-cutting (M01-M20 横切)
created: 2026-05-12
generator: P1-testpoint cross-cutting subagent (批 5)
references:
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-001-shadow-prism.md
  - design/adr/ADR-002-queue-consumer-tenant-permission.md
  - design/adr/ADR-003-cross-module-read-strategy.md
  - design/adr/ADR-004-auth-cross-cutting.md
  - design/adr/ADR-005-team-extension.md
  - _handoff/dogfooding/progress.md 批 1-4 元发现
  - 19 个 M<NN>-*.md（批 1-4 testpoint 输出）
---

# Cross-cutting 测试点（M01-M20 横切）

## 业务前提（1 段）

prism-0420 单租户多用户 SaaS：Tenant 锚点=project_id（M20 团队仅做分组不升 tenant 锚点）；Auth 走 ADR-004 4 凭据路径（P1 Bearer JWT 浏览器直连 / P2 HMAC 服务间签名 / P3 refresh random urlsafe / P4 一次性 token 预留）+ require_user 合并入口 + token_invalidated_at 同秒规约；跨模读双路（增量走 R-X3 共享 session / backfill 走 ADR-003 规则 2/3/4 只读豁免 + DAO 必须分文件）；异步 4 范式（M13 SSE 流式 / M16 BackgroundTasks + cron CAS / M17 arq Queue + WebSocket / M18 enqueue + Redis SET 60s debounce + advisory_xact_lock）；状态机散布 ≥5 模块（M01 user-status / M02 archived 互锁 / M07 issue 4 态 / M16 zombie cron CAS / M17 11 态 / M18 5 态 embedding_task）；幂等三层（idempotency_key 三元组 + 7 天 / advisory_xact_lock 替代 UniqueConstraint / Redis SET 60s + content_hash 7 字段 PK）；activity_log 横切表唯一 owner=M15 + SYSTEM_USER_UUID 系统任务规约（ADR-002 §1.1）。

## 测试点（H2 = 视角）

### 1. Auth flow（ADR-004 全模块通用）

- [P0] POST /auth/login happy path 200 返 access_token + 写 refresh_token httpOnly Secure SameSite=Lax cookie（ADR-004 §1 P3 + M01 §7）
- [P0] POST /auth/logout 撤销当前 refresh_token + 响应统一 {"status":"ok"} 防刺探账号是否存在（M01 §8 + ADR-004 §1）
- [P0] POST /auth/refresh 用过期 access 不刷 必须用 refresh_token 走 P3 通道（ADR-004 §4 短路保护）
- [P0] POST /auth/refresh raw refresh_token sha256 → DB refresh_tokens.token_hash 命中 + expires_at 未过返新 access（ADR-004 §3.6）
- [P0] refresh_token TTL 30 天默认 expires_at 过期后 POST /auth/refresh 401 + 前端清 cookie + 跳登录（ADR-004 §3.6 + §4）
- [P0] 403 vs 401 区分：未带 Authorization 头返 401 UNAUTHENTICATED / 带合法 token 但无权限返 403 PERMISSION_DENIED（M01 §8 + 跨 19 模块统一 ErrorCode）
- [P0] 浏览器关闭后再开 refresh_token cookie 仍在自动续杯 access_token + 业务路由 200（ADR-004 §3.6 TTL 30 天）
- [P0] 管理员 PATCH /auth/users/{id} status=disabled 触发 token_invalidated_at=now + 撤销该用户所有 refresh_tokens 同事务（ADR-004 §5 表 + M01 §8）
- [P0] 用户 PATCH /auth/me password 触发 token_invalidated_at + revoke_all_user_tokens + 强制重登录不签发新 token（ADR-004 §5 同秒边界规约）
- [P0] JWT iat ≤ token_invalidated_at_int（同秒视为已失效）安全侧倾 业务路由 401 TOKEN_INVALIDATED（ADR-004 §5 同秒边界 + M01 §8）
- [P0] 业务路由 require_user 先试 P1（Bearer JWT）再试 P2（HMAC）失败 401（ADR-004 §2 + M01 §8 全模块入口）
- [P0] M01 /auth/login + /auth/refresh 端点豁免 require_user 直接发凭据（ADR-004 §横切影响 + M01 §8）
- [P0] P2 服务间调用 X-Internal-Token + X-User-Id + X-Internal-Signature + X-Internal-Timestamp 4 header 缺一返 401（ADR-004 §3.2 Headers 契约）
- [P0] P2 HMAC 签名材料含 path_with_query（含 query string）防 ?dry_run=true → false 改参重放（ADR-004 §3.2 NI-01）
- [P0] P2 5 分钟时间窗外签名拒绝 401（ADR-004 §3.2 流程 step 2）
- [P0] P2 INTERNAL_TOKEN < 32 字节生产环境启动期阻断 raise（ADR-004 §3.3 部署约束）
- [P1] P2 hmac.compare_digest 常量时间比较 防时序攻击（ADR-004 §3.2 流程 step 1+4）
- [P1] P2 浏览器直接调 FastAPI 带 X-Internal-Token 头被禁止（INTERNAL_TOKEN 不进浏览器 / ADR-004 §3.5 错误用法）
- [P1] P3 refresh_token 误放进 Authorization: Bearer header JWT decode 失败 自然 401 不需 type 检查（ADR-004 §3.6 A4 测试）
- [P1] M13 SSE 流式走 P1 Bearer JWT 浏览器直连 FastAPI 不经 Server Action（M13 §8 + ADR-004 §1 P1）
- [P1] M17 WebSocket 握手走 URL query token 校验 + 每 ClientCommand 重校 task_id == handshake_task_id（ADR-002 §2 第 4 项 + ADR-004 §1 P6 预留）
- [P1] JWT 主动作废流中途触发 已建 SSE 流继续跑完接受 ≤5min 暴露窗口 新 save 请求 401（M13 §8 P9b + 批 4 元发现 JWT 时间窗）
- [P1] /auth/refresh 自身用 IP-based rate limit 防"无限重试 refresh"（ADR-004 §4 短路保护）
- [P1] auth_audit_log metadata.auth_path 必记 P1/P2 区分"真实 JWT 登录"vs"服务间调用"（ADR-004 §3.1 威胁模型表最后一行）
- [P2] 日志中永不打印 INTERNAL_TOKEN / 完整 signature 值 即使 debug 级别（ADR-004 §3.3）

### 2. 跨 tab / window cookie sync

- [P0] tab A POST /auth/logout 后 tab B 调业务路由 401（refresh 已撤销 cookie 全 tab 失效 / ADR-004 §1 P3 cookie 共享）
- [P0] tab A 改密码触发 token_invalidated_at tab B 已建 SSE 流接受 ≤5min 暴露窗口新业务请求 401（M13 §8 + ADR-004 §5 同秒规约）
- [P0] 多 tab 同账号 1 个 tab refresh 续杯 新 access 不写 cookie（access in memory）其他 tab 仍用旧 access 直到自己 401 再 refresh（ADR-004 §3.6 设计假设）
- [P1] tab A 管理员 disable userA tab B userA 已建流跑完 新业务请求 401 跳登录（ADR-004 §5 触发源表）
- [P1] cookie httpOnly Secure SameSite=Lax 阻止 XSS 读 cookie + 跨站 POST 携带 cookie（ADR-004 §1 P3）
- [P1] tab A 创建项目 201 tab B GET /api/projects 不自动看到（无 WebSocket 主动推 / 需手动刷新 / M02 §7）

### 3. 网络断连 / API 超时 / retry

- [P0] M13 SSE 流式 5 分钟服务器硬超时 asyncio.TimeoutError 触发 SSE error event + provider.aclose() 被调用（M13 §12A 字段⑤ + 批 4 元发现 SSE 范式）
- [P0] M13 AbortController 取消流式 server 端检测 disconnect + 不写 dimension_record（M13 §4 流式三出口 + tests.md S3）
- [P0] M17 arq Queue worker crash 中途 arq 持久化保证自动重新拉起从最后 status 继续（M17 §12 + tests.md R7）
- [P0] M17 git URL 不可达 extract 重试 3 次都失败 status=failed + dead_letter=true（M17 §12 指数退避 + tests.md R3）
- [P0] M16 BackgroundTasks AI provider 5xx 重试 3 次 status=failed 不 zombie（M16 §6 BackgroundTasks 分支 + 批 4 元发现 BackgroundTasks 范式）
- [P0] M16 zombie cron CAS race：runner 失败分支必须 cas_complete 不直 UPDATE（M16 audit B3 + 批 4 元发现 cron CAS）
- [P0] M18 embedding worker AI 调失败 3 次写 embedding_failures + monitor 三维阈值告警 CY 不通知用户（M18 §12D 失败容忍 + audit C2）
- [P1] M01 /auth/login 网络断连前端 fetch reject 用户重试不锁账号（无 rate limit / M01 §7）
- [P1] 业务 GET 端点网络超时前端 retry 友好 不写 activity_log 不污染数据（design §10 R10-3 GET 不写 log 通用）
- [P1] 业务 POST 端点网络断连前端不确定是否写入 通过 GET 查最新状态 或带 idempotency_key 走幂等（清单 4 敏感操作 + M17 idempotency 范式）
- [P1] M18 Redis SET 60s debounce 重复 enqueue 同 target 60s 内忽略不重复跑 worker（M18 §12D 字段⑤ + 批 4 元发现 Redis 60s）
- [P2] DB 连接断 require_user Depends 兜底返 5xx 不泄漏 stacktrace（design §13 规约错误兜底 / M07 P2-04）

### 4. 权限三层防御（Router 粗 / Service 细 / DAO tenant 过滤）

- [P0] Router 层 Depends(require_user) 401 未登录拦截（ADR-004 §2 + 全模块 §8）
- [P0] Router 层 check_project_access(project_id, user, role≥editor) 403 viewer 不可写（design §8 表 + M02 §8）
- [P0] Service 层 _check_node_belongs_to_project(node_id, project_id) 跨项目 node_id 防御 404（M05 §8 第三层 + 批 2 元发现 cross-tenant 防御）
- [P0] Service 层 _check_issue_belongs_to_project / _check_competitor_belongs_to_project / _check_module_relation_belongs_to_project 等"belongs_to"前缀方法跨 4+ 模块（M06/M07/M08/M05 §8）
- [P0] DAO 层所有 SELECT/UPDATE/DELETE 必显式 WHERE project_id=? 过滤（清单 5 + 全模块 §9）
- [P0] DAO 层无 project_id 过滤即扫全表 → ci-lint CI 守护扫 dao/ + 告警阻塞合并（清单 5 检查段）
- [P0] viewer 调任意写端点（POST/PUT/PATCH/DELETE）返 403 全 19 模块（M07/M08/M12 主动复制范式 + 批 3 元发现 viewer 全覆盖）
- [P0] DAO 方法签名所有方法带 project_id 入参防绕过（M07 §9 + 全模块 R-X3 契约）
- [P1] platform_admin 跨 project 访问 不经 check_project_access 走 @admin_only 装饰器（清单 5 豁免 + M01 §8 admin 路径）
- [P1] role 中途由 editor 降为 viewer 二次 POST 立即 403（design §8 Router check_project_access 每请求重查）
- [P1] M14 industry-news 全局豁免 tenant（catalog Tenant ❌）DAO 无 project_id 过滤（清单 5 豁免条件 + M14 §3 显式声明）
- [P1] M01 admin 端点 require_user + require_admin 双 Depends 顺序：先 user 再 admin（ADR-004 §2 + M01 §8）
- [P2] importlinter 禁 routers/ 直 db.query(Model) 跨层（原则 2 + 全模块 §6 分层职责表）

### 5. R-X 横切纪律（orchestrator + 上调下 + 跨事务签名 + DAO 分文件）

- [P0] R-X1 orchestrator 模式：M11 cold-start 共享 db.begin() 跨 M03/M04/M06/M07 service 任一失败全表回滚（M11 §6 + 批 1 元发现 R-X1 首例）
- [P0] R-X1 第二实例 M17 importing 阶段 single transaction 跨 M03/M04/M06/M07 batch_create_in_transaction 取消 ROLLBACK 已写入全无（M17 §4 importing 事务粒度 + audit B2）
- [P0] R-X1 第三实例 M13 AnalyzeService 聚合 RequirementAnalysisContext 调 M02/M03/M04/M07 5 上游 Service 不直查表（M13 §3 上游依赖表 + 批 4 元发现）
- [P0] R-X2 上调下：M03 节点删除显式调 M06.delete_by_node_id / M07.orphan_by_node_id / M08.delete_by_node_id 不依赖 DB CASCADE（M03 §6 R10-1 + 批 3 元发现 R-X2）
- [P0] R-X3 跨事务签名 5 真注入：M04/M06/M07/M08/M13 service 方法接受外部 db: Session 不自开事务（design §5 R-X3 + 批 2/3/4 元发现）
- [P0] R-X3 batch_create_in_transaction 签名 4 参（db, items, project_id, actor_user_id）含 actor_user_id（M07/M08 §6 命名说明 + R-X5 升级）
- [P0] R-X3 orphan_by_node_id SET NULL 语义 vs delete_by_node_id DELETE 语义命名区分（M07 §6 命名说明 batch3 决策 4）
- [P0] DAO 必须分文件：M18 增量 EmbeddingDAO（规则 1）+ backfill EmbeddingBackfillDAO（规则 4）两文件不混（M18 §6 + ADR-003 规则 4 文档要求）
- [P1] R-X3 caller 持 commit/rollback 权 callee batch_create_in_transaction 内部 db.flush() 不 commit（design §5 R-X3 规则 2）
- [P1] R-X3 第六真注入 M13 R3-5 写 M04.create_dimension_record 共享 session 任一失败回滚（M13 §13 R-X3 + 批 4 元发现）
- [P1] importlinter 禁 services/orchestrator 内 db.query(M0X.Model) 跨模块直查（原则 6 + ADR-003 规则 1）
- [P2] R-X3 sprint 期对外契约 5+ 方法集中（M04 §6 5 方法）所有 caller 必走对外契约不能内部反查（M04 §6 对外契约段）

### 6. 异步路径范式（SSE / BackgroundTasks / cron / arq Queue / WebSocket / Redis debounce / advisory_xact_lock）

- [P0] M13 SSE 流式 chunk 顺序保证 client 收顺序 = server yield 顺序 + complete event 末尾（M13 §7 + tests.md S1 + 批 4 元发现 SSE 范式）
- [P0] M13 SSE 流式 db session 在 async for 开始前释放 流式循环内不持 DB 连接 避免 PG pool 10-20 被 5 并发流式打满（M13 §5 + audit R2-02）
- [P0] M13 SSE provider.aclose() 异常路径必须被调用（M13 §12A 字段⑤ + tests.md S4）
- [P0] M16 BackgroundTasks vs zombie cron CAS race：runner 失败分支必须 cas_complete(snapshot_id, status='failed') 不直 UPDATE（M16 audit B3 + 批 4 元发现）
- [P0] M16 zombie 阈值 11min + pending 兜底 2min + cron 频率 5min ≤ 阈值/2（M16 §12 cron 参数 + audit M5）
- [P0] M17 arq Queue worker 入口 3 行：① Pydantic 校验 TaskPayload ② service.check_access ③ 业务逻辑（ADR-002 §2 入口 3 步）
- [P0] M17 WebSocket 握手校验 task_id 归属 user + 每 ClientCommand 重校 task_id == handshake_task_id（ADR-002 §2 第 4 项 + 批 4 元发现 WebSocket）
- [P0] M17 WebSocket ping-pong 30s 间隔 客户端关浏览器 60s 内 server 端检测断连（M17 §7 WebSocket protocol）
- [P0] M18 enqueue_delete 双触发链：增量 M03/M04/M06/M07 commit 后调 / backfill cron 0 点+admin 触发（M18 §12D 字段① + 批 4 元发现 enqueue 双触发链）
- [P0] M18 Redis SET 60s debounce 防 60s 内重复 enqueue 同 target（M18 §12D 字段⑤）
- [P0] M18 pg_advisory_xact_lock 双 namespace 防 hashtext 32-bit 跨 project 鸽笼碰撞（M18 §12D + audit B1）
- [P0] M16 advisory_xact_lock 替代 UniqueConstraint 实现 idempotent get-or-create（M16 audit B1+M6 + 批 4 元发现 advisory_xact_lock）
- [P1] TaskPayload 基类强制 user_id + project_id + idempotency_key | None 字段（ADR-002 §1 + 全异步模块）
- [P1] CI 静态扫描所有 queue/tasks/*.py @task 装饰函数入参类型必须是 TaskPayload 子类（ADR-002 §1 检查段）
- [P1] cron / 系统触发任务 payload.user_id = SYSTEM_USER_UUID（ADR-002 §1.1 + M16/M17/M18 cron 全用）
- [P1] consumer 入口 service.check_access(payload.user_id, payload.project_id) 必须先判 user_id == SYSTEM_USER_UUID 走 system-scoped 校验（ADR-002 §1.1 校验链规约）
- [P1] consumer 禁止用 payload.user_id is None 判断系统任务 必须用 SYSTEM_USER_UUID 常量比对（ADR-002 §1.1）
- [P1] M16 BackgroundTasks 失败代价低 + 引入成本零 → 不走 arq Queue；反悔触发器 zombie 率 ≥1% / 单次 AI 成本 ≥$0.5（M16 §6 BackgroundTasks vs arq 边界 + ADR-002 §横切影响）
- [P2] arq cron + Redis worker 进程崩溃 supervisor 自动拉起 + arq 持久化保证（M17 §12 + tests.md R7）

### 7. 幂等三层模式对照表

- [P0] M17 idempotency key 三元组 (user_id, project_id, source_hash) + 7 天过期 + 同 user 跨 project 不命中错 task（ADR-002 §3 + M17 audit B1）
- [P0] M16 advisory_xact_lock 替代 UniqueConstraint 实现幂等 get-or-create（M16 audit B1 + 批 4 元发现）
- [P0] M18 Redis SET 60s debounce + pg_advisory_xact_lock 双 namespace + embeddings 表 content_hash 7 字段 PK 三层（M18 §12D + audit B1 + 批 4 元发现幂等三层）
- [P0] 异步模块 §11 idempotency_key 章节必须显式回答"project_id 是否参与 key 计算"（ADR-002 §3 检查段）
- [P0] DELETE 端点天然幂等：重复 DELETE 同 issue_id 第二次返 204（M07 §11 + 通用 REST 范式）
- [P1] M02 AI Key last-write-wins 不加乐观锁（设计取舍 / batch 2 元发现）vs M04 dimension_records 乐观锁 version + DB UNIQUE 双防御
- [P1] 客户端生成 idempotency_key=UUID 服务端查 Redis 已处理返原结果（清单 4 + M17 audit B1）
- [P1] 敏感操作（删除 / 审批 / 发布 / 支付类）API schema 接受 idempotency_key 参数 GET 只读豁免（清单 4 适用操作）
- [P2] M16 advisory_lock 串行化豁免 docstring 字面声明（清单 6 豁免条件）

### 8. 状态机非法转换（跨 M01/M02/M07/M16/M17/M18 统一返码）

- [P0] M01 user-status active→disabled 允许 / disabled→active 允许 + 撤销 token_invalidated_at + revoke_all_user_tokens（ADR-004 §5 + M01 §4）
- [P0] M02 active→archived 状态转换允许 + activity_log archive previous_status=active（M02 §4 + tests.md G5）
- [P0] M02 archived→active 状态转换禁止 422 PROJECT_ARCHIVED 终态不可逆（M02 §4 + 批 2 元发现 archived 互锁）
- [P0] M07 issue 状态机 4 态 + 5 禁止转换：open→closed 跳 in_progress/resolved 422 ISSUE_TRANSITION_INVALID（M07 §4 + 批 3 元发现）
- [P0] M07 closed → 任何状态 422 ISSUE_CLOSED_ERROR 关闭后不可重开（M07 §4 + 批 3 元发现状态机禁转）
- [P0] M16 zombie cron CAS：snapshot_task 状态 expected=running 跑超 11min 转 failed 必须 CAS 不直 UPDATE（M16 audit B3 + 批 4 元发现）
- [P0] M17 import_task 11 状态 + 5 禁止转换补全：pending→ai_step3 跳步 / completed→任何 / cancelled→任何 / failed→任何 / awaiting_review→importing 跳过 ai_step3（M17 §4 + audit B4）
- [P0] M18 embedding_task 5 状态：succeeded → 任意 422 EMBEDDING_TASK_TERMINAL_VIOLATION 终态不可变（M18 §4 禁止转换 1）
- [P0] M18 embedding_task dead_letter → 任意 422 EMBEDDING_TASK_TERMINAL_VIOLATION 死信终态不可变（M18 §4 禁止转换 2）
- [P0] 跨模块状态机非法转换统一返 INVALID_STATUS_TRANSITION 422 + details.{current, target} 给前端（design §13 + 批 4 元发现统一返码）
- [P0] 状态转换前 SELECT FOR UPDATE 锁定行 双 user 同时触发仅一个写入另一个被串行化（M07 §5 + design §5 R-X3 竞态分析表）
- [P1] 任何"有 status 字段或状态变化"的实体设计文档必须有状态机图（原则 4 + 全模块 §4）
- [P1] M18 failed 短暂态 worker 写入后 30s 内 cron 强制转 dead_letter 同时落 embedding_failures（M18 §4 R4-3a 非常规态登记表）
- [P1] M17 partial_failed 半终态 30 天未重试 cron 清理（M17 §4 R4-3a）
- [P2] M13 自身无状态机 §4 R4-1 显式声明 流式连接 streaming→complete/error/disconnect 三出口（M13 §4 + design 必须显式 N/A 不能省）

### 9. AI Provider 集成边界

- [P0] M02 项目级 AI Provider 配置：写入 PUT /api/projects/{pid} ai_provider + ai_api_key 明文 → DB ai_api_key_enc AES-256-GCM 密文 + 响应体不含明文（M02 §3.Z + tests.md E4）
- [P0] M02 AES-256-GCM helper 建在 horizontal layer api/auth/crypto.py 不挂业务模块名下（原则 6 + M02 §7.1 横切关注三选一）
- [P0] M13 项目未配置 AI provider (Project.ai_provider=None) 流式立即返 error event ANALYSIS_PROVIDER_NOT_CONFIGURED HTTP 200（M13 §13 R13-2 + tests.md E7）
- [P0] M13 LLM red line 范式 MockProvider 设 aclose_called 标志位供测试观测（design §14.5 + M13 批 4 元发现 LLM 红线）
- [P0] M13/M16/M17 AI Provider 错误 wrap 为模块业务异常 上游错误不裸露（design §13 R13-2 跨模块 wrap）
- [P0] M17 多 provider + 配额超限 status=failed + IMPORT_QUOTA_EXCEEDED 429（M17 §13 ImportQuotaExceededError + 批 4 元发现）
- [P0] M18 三 env 同步漂移：EMBEDDING_PROVIDER + EMBEDDING_MODEL_NAME + EMBEDDING_MODEL_VERSION 三 env 全改 漏一个 fallback 全表回填（M18 §12D + audit B5 + 批 4 元发现 三 env 同步）
- [P0] M18 三 provider 抽象 openai/bge/mock 部署期固定不支持运行时切换（M18 §1 + tests.md golden_05）
- [P1] M18 query embedding Redis 5min 缓存命中第二次同 query 不调 OpenAI 返 query_embedding_cached=true 响应 <200ms（M18 §1 Q4=C + tests.md golden_04）
- [P1] M13 流式 prompt 模板 analyze_prompts.py 区分 L1/L2/L3 三档 注入 context 不硬编码 node 名（M13 §6 Prompt Template 禁止条款）
- [P1] M17 AI 输出格式错（非 JSON）step1 重试 3 次都格式错最终 status=failed + IMPORT_AI_PROVIDER_ERROR（M17 §13 + tests.md E7）
- [P1] M18 pgvector 不可用降级 SEARCH_MODE kill switch env 一键切 hybrid/keyword_only/semantic_only（M18 audit B5）
- [P2] AI Provider 集成首发 PROVIDER+MODEL_NAME+MODEL_VERSION 三 env 同步漂移检测 → ci-lint 守护候选（M18 批 4 元发现）

### 10. baseline-patch 时序契约（punt pool 累计 6 处）

- [P0] M02 反向引用 M20 baseline-patch space_id → team_id 字段重命名（M02 §3.Z + ADR-005 §3.1）
- [P0] M03 enqueue B 推迟 + scaffold TODO 留待 M18 sprint 期回写（M03 §6.X A7 + 批 2 元发现 punt #2）
- [P0] M04 enqueue B 推迟 + scaffold TODO 留待 M18 sprint 期回写（M04 §6.X A7 + 批 2 元发现 punt #3）
- [P0] M07 A7 退化路径 get_for_embedding 拼接 title + description 走 ADR-003 规则 1（M07 §6.X A7 + 批 3 元发现 punt #4）
- [P0] M13 audit B1：M02/M03/M04/M07 baseline-patch 前置 上游 Service 签名对不上时 M13 sprint 期不可启（M13 audit B1 + 批 4 元发现 punt #5）
- [P0] M15 baseline-patch project_id NULLABLE 全局事件跨模块 patch 风险（M15 §3 + 批 4 元发现 punt #6）
- [P0] baseline-patch sprint 完成前 caller 不能依赖未完成的对外契约 必须 A 路径声明 scaffold TODO（design §6.X A7 通用范式）
- [P1] baseline-patch 时序契约 punt pool 累计 ≥3 处时 → 升级 cross-sprint punt 池 + 真漏洞表追踪（progress.md 批 4 元发现）
- [P1] M20 sprint 期前置 M02 schema 重命名 space_id → team_id Alembic migration accepted（M02 §3.Z + ADR-005 §3.1）
- [P2] punt pool 6 处全部独立 cleanup sprint 处理（与立规先行防御未来匹配）

### 11. DB 部分唯一索引 race + 多表事务回滚

- [P0] M02 uq_project_owner_name_active 部分唯一索引 race：归档释放后同名 active 可创建 但并发 2 个 create 同名 IntegrityError 第二个转 PROJECT_NAME_DUPLICATE 409（M02 §3 + 批 2 元发现）
- [P0] M03 path UNIQUE 物化路径 move_subtree 并发同 parent reorder IntegrityError 转 NODE_PATH_CONFLICT（M03 §3 + 批 2 元发现）
- [P0] M05 uq_version_node_is_current 部分唯一索引 race：并发 2 个 set-current 仅一个成功另一个 IntegrityError 转 VERSION_ALREADY_CURRENT（M05 §3 + 批 2 元发现）
- [P0] M02 多表事务 4 步 with db.begin()：projects + project_members[owner] + project_dimension_configs + activity_log 任一失败全表回滚（M02 §5 + tests.md G1 + 批 2 元发现）
- [P0] M06 内联档案页 内联多表事务（competitors + competitor_refs + activity_log）任一失败回滚（M06 §5 R1-A + 批 3 元发现）
- [P0] M11 cold-start 共享 db.begin() 跨 M03/M04/M06/M07 service 失败全表回滚（M11 §6 R-X1 orchestrator）
- [P0] M12 三表事务 snapshots + items + activity_log with db.begin() 全量回滚（M12 §5 + 批 3 元发现）
- [P0] M17 importing 阶段 single transaction 跨 4 模块 batch_create_in_transaction 失败 ROLLBACK 全无（M17 §4 importing 事务粒度 + audit B2）
- [P0] M20 R-X3 跨事务签名首发：transfer_ownership / delete_team 接受外部 db: Session 共享事务（M20 §8.7 + ADR-005 Q13.2）
- [P0] Service 层 IntegrityError 必区分 constraint name → 对应业务 ErrorCode（uq_teams_creator_name → TeamNameDuplicateError / 等）（清单 6 + M20 §14.5 范式 + M05 立 + M14 link_node 范式）
- [P0] Service 层 INSERT 路径凡 UNIQUE constraint 必 try/except IntegrityError + await db.rollback() + 转业务异常 不裸抛 5xx（清单 6 执行段）
- [P1] DAO 已 catch IntegrityError → caller 不需重复（M14 link_node 范式 / 清单 6 豁免条件 1）
- [P1] INSERT 路径前置 advisory_xact_lock 已串行化 → docstring 字面"advisory_lock 串行化豁免"（清单 6 豁免条件 2 + M16 idempotent 范式）
- [P1] ci-lint R15 grep service 层 INSERT 后无 except IntegrityError 段 告警阻塞合并（清单 6 检查段）
- [P2] activity_log INSERT 与业务表 INSERT 同一隐式 transaction 任一失败回滚（design §5 SQLAlchemy autobegin + M07 §10）

### 12. cross-tenant 攻击三层防御

- [P0] Router 层 check_project_access(project_id, user, role) 跨 project 拦 403（design §8 表 + 全模块 §8）
- [P0] Service 层 _check_node_belongs_to_project(node_id, project_id) 跨 project node_id 防御 404 不暴露存在性（M05/M07/M13 §8）
- [P0] DAO 层 SELECT/UPDATE/DELETE 必 WHERE project_id=? 过滤（清单 5 + 全模块 §9）
- [P0] DAO 缺 project_id 过滤即扫全表 → ci-lint 扫描告警阻塞合并（清单 5 检查段）
- [P0] URL path projects/P1/nodes/<P2.node> 跨项目 node 混淆 返 404 不泄露 N2 存在于 P2（M13 §8 + tests.md T2）
- [P0] userA 持 projectP1 token 调 projectP2 任意端点 403 PERMISSION_DENIED Router 层拦（全模块 §8 + tests.md T1 通用）
- [P0] AnalyzeService / OverviewService 等聚合 Service 调上游 Service 必带 project_id 参数防跨项目数据泄漏（M13 §9 + 批 4 元发现）
- [P0] DAO 方法签名所有方法带 project_id 入参防绕过（全模块 §9 R-X3 契约）
- [P1] L3 SQL 兜底注入 WHERE project_id IN user_accessible_project_ids（ADR-005 Q5 + M20 user_accessible_project_ids_subquery helper）
- [P1] platform_admin 跨 project 走 @admin_only 装饰器不经 check_project_access（清单 5 豁免）
- [P1] 三层任一漏掉即"读路径越权"多租户系统最常见漏洞（清单 5 目的段）

### 13. tenant 豁免 2 类 + ADR-003 只读豁免

- [P0] M14 industry-news 全局豁免 tenant（catalog Tenant ❌）DAO 无 project_id 过滤 全 project 共享（M14 §3 + 批 1 元发现首发）
- [P0] M14 source_type='manual' 双重防护：CheckConstraint + Service 层显式校验（M14 §3 + 批 1 元发现）
- [P0] M19 import-export 跨 project node 走 422 IMPORT_NODE_CROSS_PROJECT 非 404（M19 §13 + 批 1 元发现跨 project 422 范式）
- [P0] ADR-003 规则 1 主规则：聚合读模块（M09/M18 增量）通过上游 Service.search_by_keyword / get_for_embedding 接口读取 不直查上游表（ADR-003 规则 1 + M18 §6）
- [P0] ADR-003 规则 2：M10 Overview DAO 只读 import M02/M03/M04 model 做 JOIN 聚合（ADR-003 规则 2 + M10 §3 显式声明）
- [P0] ADR-003 规则 2 M10 OverviewDAO 任何 INSERT/UPDATE/DELETE 违反 → audit 命中 + design 原则跟实施真对齐数据点（M10 §3 + 批 3 元发现）
- [P0] ADR-003 规则 3：M15 ActivityStreamDAO 直查 activity_log 横切表 无需"各业务模块日志接口"（ADR-003 规则 3 + M15 §3 显式声明）
- [P0] ADR-003 规则 4：M18 EmbeddingBackfillDAO 只读 import M03/M04/M06/M07 model + LEFT JOIN 找差异（ADR-003 规则 4 + M18 §9）
- [P0] ADR-003 规则 4 M18 backfill DAO 只读 import 严禁 INSERT/UPDATE/DELETE 上游表（ADR-003 规则 4 使用边界）
- [P0] ADR-003 规则 4 M18 双 DAO 维护：增量 EmbeddingDAO（规则 1）+ backfill EmbeddingBackfillDAO（规则 4）两文件不混（M18 §6 + ADR-003 §3.4 文档要求）
- [P1] M19 viewer 也能 export 但 export 写 activity_log（M19 §10 + 批 1 元发现 viewer 写 log）
- [P1] M14 + M09 接口签名例外（M14 search_by_keyword 无 project_id）（ADR-003 §M09+M14 例外）
- [P1] 跨项目实体统一返 422 非 403：M06 竞品 / M08 module-relation / M19 import-export 跨 3 模块连续命中（批 3 元发现）

### 14. activity_log 失败传播 + SYSTEM_USER_UUID

- [P0] M15 ActivityLog 横切表唯一 owner R10-2（M15 §3 + 批 4 元发现）
- [P0] Service 层 create/update/delete 方法必须调 activity_dao.log(user_id, action, entity_id)（清单 1 执行段）
- [P0] activity_log 写入与业务表写入同一隐式 transaction 任一失败回滚（design §5 SQLAlchemy autobegin + M07 §10）
- [P0] activity_log 失败传播范式：M16 cron / M17 import / M19 export / 全 4 模块统一（批 1 元发现 + M14 失败传播）
- [P0] cron / 系统触发任务 activity_log.user_id = SYSTEM_USER_UUID 不能用 task creator 的 user_id（违反系统操作语义 / ADR-002 §1.1 + 批 4 元发现）
- [P0] 直接 SQL 形态 cron（M16 cleanup_zombie_snapshots / M18 zombie / M18 task_cleanup）补写 activity_log user_id 落 SYSTEM_USER_UUID（ADR-002 §1.1 触发方清单 + design）
- [P0] M15 DAO 查询 WHERE user_id = SYSTEM_USER_UUID 可查询系统操作日志（ADR-002 §1.1 + M15 §9）
- [P0] 前端 next-intl 文案 user_id == SYSTEM_USER_UUID 时显示"系统"（i18n key activity.actor.system / ADR-002 §1.1）
- [P0] R10-1 N 条独立 activity_log：批量删除 / 批量插入 / batch_create_in_transaction 每条受影响 entity 写独立事件（M03 §10 + M06/M07/M08 范式）
- [P0] R10-2 activity_logs 全模块共享 唯一 owner = M15（design §10 + ADR-003 规则 3）
- [P1] 异步路径 activity_log 写入仍走同一 SQLAlchemy autobegin 失败回滚业务事务（M16 BackgroundTasks + M17 importing 事务）
- [P1] CI 扫描 Service 层变更方法必须包含 activity_log 调用（清单 1 检查段）
- [P1] R10-3 GET endpoint 不写 activity_log 通用（design §10 R10-3）
- [P2] M15 僵尸 target_id 展示（无 FK / summary 字段冻结目标名）（M15 §3 + 批 4 元发现）

### 15. action_type 同步漂移 + R14 守护

- [P0] M15 ActionType + TargetType enum + CheckConstraint + Alembic 4 处同步（M15 §3 + 批 4 元发现）
- [P0] R14 守护：业务模块写 activity_log 必须用枚举字面 不能用 raw string（M16 sprint 实证 31 处机械批量改 / 批 4 元发现）
- [P0] M14 action_type 5 个过去式 + M19 4 处过去式同步：created/updated/deleted/imported/exported（批 1 元发现 action_type 同步漂移）
- [P0] M14 link_node / unlink_node action_type 命名一致性（M14 §10 + 批 1 元发现）
- [P0] M18 ActionType + TargetType 含 EMBEDDING_MODEL_UPGRADE_TRIGGERED + EMBEDDING_BACKFILL_TRIGGERED + M15 ActionType 同步（M18 §10 + audit M1）
- [P0] M16 dot-notation action_type 待 Alembic 迁移回写 M15（M16 audit + 批 4 元发现）
- [P0] M20 team_created / team_deleted / team_renamed / team_member_added / team_member_removed / team_member_promoted_admin / team_demoted_owner / team_promoted_owner / project_joined_team / project_left_team 10 事件细粒度（ADR-005 Q10/Q10.1 + M20 §10.1）
- [P1] ci-lint R14 grep service 层 ActivityLog INSERT 用 raw string action_type 告警（R14 守护立规 + M16 sprint 内实证）
- [P1] Alembic 4 处同步：M15 SQLAlchemy enum + CheckConstraint + Alembic upgrade + Alembic downgrade（批 4 元发现 M15 4 处）
- [P1] M20 transfer-ownership 同事务 2 条 activity_log（demoted + promoted）同 correlation_id 关联（ADR-005 Q10.1①  + M20 §10.1 F2.9）
- [P2] frontmatter codes_added 新增 ActionType 与 api/errors / api/models 实际定义行数一致（design frontmatter + R13-1 CI 守护）

### 16. filename sanitize / 跨项目实体 422 / viewer 写端点 403 / Pydantic vs SQLAlchemy disambiguation

- [P0] M19 export Content-Disposition filename sanitize 输出端首发（M19 §7 + 批 1 元发现 filename sanitize）
- [P0] M19 filename 含特殊字符 / 中文 / 控制字符 都被 sanitize 不让客户端文件系统报错（M19 §13 + 批 1 元发现）
- [P0] M17 / M18 后续导出场景复用 M19 filename sanitize 范式（批 1 元发现复用）
- [P0] M19 EXPORT_EMPTY_CONTENT 422 优先空报告 不返 200 含空 zip（M19 §13 + 批 1 元发现）
- [P0] M06 跨项目竞品引用 422 COMPETITOR_NODE_CROSS_PROJECT 不返 403（M06 §13 + 批 3 元发现 422 范式）
- [P0] M08 跨项目 module-relation src/tgt node_id 跨 project 422 RELATION_NODE_CROSS_PROJECT（M08 §13 + 批 3 元发现）
- [P0] M19 跨 project node import 422 IMPORT_NODE_CROSS_PROJECT 非 404（M19 §13 + 批 1 元发现 422 范式连续 3 模块）
- [P0] M07/M08/M12 viewer 写端点 403 PERMISSION_DENIED 全覆盖（M07 §8 主动立 / M08+M12 主动复制 / 批 3 元发现 viewer 全覆盖范式）
- [P0] M12 viewer 写 3 端点 403 主动复制 M07/M08 元教训（M12 §8 + 批 3 元发现）
- [P0] M15 design §3 三处 disambiguation：Mapped[ActionType] vs str+CheckConstraint / event_metadata 重映射 / list_for_team 签名（M15 §3 + 批 4 元发现 disambiguation）
- [P0] Pydantic schema vs SQLAlchemy 模型字段映射 disambiguation：避免字段名同形但语义偏移（批 4 元发现 + M15 §3）
- [P1] M19 export action_type "exported" 4 处同步（M19 §10 + Alembic + ActionType enum + service 层枚举字面）
- [P1] M15 Mapped[ActionType] 防御性比 str + CheckConstraint 更严（M15 §3 disambiguation）

### 17. 国际化 / 时区 / mobile / 性能

- [P0] M01 timestamps 全 UTC + ISO8601 序列化（design §3 created_at/updated_at + 全模块 §3 范式）
- [P0] PostgreSQL timestamp 微秒级 vs JWT iat 秒级转换同秒按"已失效"安全侧倾（ADR-004 §5 同秒边界规约）
- [P0] M16 zombie 阈值 11min / cron 频率 5min 配置基于 UTC 时间（M16 §12 cron 参数 + ADR-002 §1.1 cron 触发）
- [P1] 移动端 ≤768px 项目列表 / node 详情 / issue 列表 / 维度面板 主要业务页面响应式可用（design §6 Component 通用）
- [P1] 移动端 SSE 流式 M13 连接保持 / 切后台 5min 内回前台流继续（M13 §4 流式三出口 + 浏览器后台 SSE 范式）
- [P1] 移动端 WebSocket M17 连接保持 / 切后台 60s 内回前台 ping-pong 重连（M17 §7 + 浏览器 WebSocket 范式）
- [P1] next-intl 文案 user_id == SYSTEM_USER_UUID 显示"系统"（i18n key activity.actor.system / ADR-002 §1.1）
- [P1] activity_log summary 字段中文 "状态变更：{old_status}→{new_status}" 跨模块统一（M07 §10 + design §10 表）
- [P1] M02 AC2 一键迁移 100 个 project 前端循环 100 次 move-team 总耗时 ≤20s（ADR-005 + M20 §1 F2.2 规模假设）
- [P1] M13 SSE 5min 长连接打满 PG pool 10-20 个流式 + db session 释放策略（M13 §5 + audit R2-02）
- [P1] M18 query embedding Redis 5min 缓存命中第二次同 query <200ms（M18 §1 Q4=C + tests.md golden_04）
- [P2] 首屏 < 3s（design 通用性能预算 / dogfooding 期观测）
- [P2] 长列表分页 page_size=20 / 50 / 100 走索引不全表扫（全模块 §9 索引设计）
- [P2] tag 过滤 JSONB @> 查询性能依赖 PG GIN 索引（M07 §7 + §9 / 未声明 GIN / dogfooding 期观测）

### 18. schema 性死债务 / cross-tenant 攻击防御

- [P0] M18 embeddings 表 7 字段 PK + 异维列 embedding_512/1536/3072 + dim 路由（M18 §3 + audit B4 schema 性死债务）
- [P0] M18 schema 性死债务：fallback 漏 env 全表回填 5 万行 1+小时不可接受（M18 audit B4 + 批 4 元发现 schema 性死债务首发）
- [P0] M04 dimension_records 乐观锁 + DB UNIQUE 双防御范式（vs M18 schema 性死债务对照）（M04 §5 + 批 2 元发现）
- [P0] M02 多表事务 4 步：projects + project_members[owner] + project_dimension_configs + activity_log 任一失败全表回滚（M02 §5 + tests.md G1）
- [P0] cross-tenant SQL 注入 L3 横切：M03-M19 query 层升级注入 WHERE project_id IN user_accessible_project_ids（ADR-005 Q5 + M20 user_accessible_project_ids_subquery）
- [P0] M18 删除一致性：except SilentFailure 不能 except Exception 否则崩溃 + orphan cleanup cron 兜底（M18 audit B1+C2 + 批 4 元发现）
- [P0] M03 path 物化路径 move_subtree 循环引用防御 + path UNIQUE race（M03 §7 + 批 2 元发现）
- [P0] M02 PG 部分唯一索引归档语义边界：归档释放 active name slot 但 archive 不级联子模块（M02 §4 P5 audit F-2 + 批 2 元发现）
- [P1] M02 archive 不级联：子模块 node / dimension_record / issue / competitor 状态不变 仅 project.status=archived（M02 §4 P5 audit F-2）
- [P1] M02 last-write-wins（AI Key + project name 无乐观锁）vs M03 reorder/move 子树不加锁 vs M01 user/M04 dimension_records 乐观锁（批 2 元发现并发策略分化）
- [P1] M12 snapshot.items.content 保存后改 M04 dim_record / 删 M03 node 都不影响 snapshot（M12 §3 G4=B 值快照不降级 + 批 3 元发现）
- [P1] M05 G-? snapshot 类语义对照 M12 G4=B（M05 §3 + 批 3 元发现 snapshot 范式呼应）
- [P2] M03 path 物化路径压缩视角数（M03 testpoint 84 vs 主流 90+ 的原因 / batch 2 实战观察）
