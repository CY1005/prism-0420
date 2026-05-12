---
module: M13
name: requirement-analysis
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M13-requirement-analysis/00-design.md
  - design/02-modules/M13-requirement-analysis/tests.md
  - design/02-modules/M13-requirement-analysis/audit-report.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-001-shadow-prism.md
  - design/adr/ADR-003-cross-module-read-strategy.md
  - design/adr/ADR-004-auth-credentials.md
prd_ref: PRD F13 AC1-AC4 + US-B1.13（editor 写需求让 AI 流式分析 / 保存 / 关系图高亮）
---

# M13 需求分析 测试点

## 业务流程（H1 / 1 行概述）

M13 是流式 SSE pilot（§12A 子模板首发）：editor 在 node 档案页对功能项写需求文本 → POST /analyze/requirement 流式吐 AI 分析（L1/L2/L3 三档深度 / 5min 硬超时 / AbortController 取消 / aclose 协议）→ 用户满意点保存 POST /analyze/save 经 M04 DimensionService.create_dimension_record 寄生写 dimension_records（M13 无自有表 / R3-5 纯读聚合 / activity_log 由 M04 代写）→ GET /analyze/affected-nodes 取 AI 识别的受影响 node 给 M08 关系图高亮；三端点 URL 嵌套 project_id+node_id / Tenant 由上游 Service 强制 / 流式走 ADR-004 P1 Bearer JWT 浏览器直连 FastAPI / save+affected-nodes 走 ADR-004 P2 经 Server Action。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/nodes/{nid}/analyze/requirement L2 流式返 SSE 5 chunk + 1 complete event 顺序正确 full_result=join(chunks)（design §7 + tests.md G1）
- [P0] complete event metadata 含 ai_provider/ai_model/analysis_level/analysis_time_ms/matched_template_id 5 字段（design §7 SSECompleteEvent + tests.md S7）
- [P0] POST /api/projects/{pid}/nodes/{nid}/analyze/save 含 full_result + affected_node_ids 返 200 SaveAnalysisResponse 含 dimension_record_id + analysis_saved_at ISO8601（design §7 + tests.md G1）
- [P0] save 后 M04 dimension_records 新增 1 行 dimension_type_key="requirement_analysis" content.analysis_result=full_result（design §1 in-scope + tests.md G1）
- [P0] GET /api/projects/{pid}/nodes/{nid}/analyze/affected-nodes 返 affected_node_ids + analysis_record_id + analysis_saved_at 与 save response 同时间戳（design §7 AffectedNodesResponse + tests.md G1）
- [P0] analysis_level=L1 流式 2 chunk 总耗时 ~200ms metadata.analysis_level="L1"（design §7 AnalysisLevel + tests.md G2）
- [P0] analysis_level=L3 流式 20 chunk 总耗时 30s 正常 complete 不触超时（design §7 + tests.md G3）
- [P1] save 时 affected_node_ids=[] 空数组成功写入 affected-nodes 返空数组（design §7 default_factory=list + tests.md G4）
- [P1] 初次访问无历史分析 GET affected-nodes 返 affected_node_ids=[] analysis_record_id=null analysis_saved_at=null（design §7 + tests.md G5）
- [P1] AnalyzeService 聚合 RequirementAnalysisContext 调 M02.get_by_id_for_user + M03.get_by_id + M03.list_subtree(depth=2) + M04.list_by_node + M07.list_by_project(node_id=) 5 个上游 Service（design §3 上游依赖表 + §6 Service 层）
- [P1] L1/L2/L3 三档由 prompt 模板 analyze_prompts.py 区分 prompt 注入 context 不硬编码 node 名（design §6 Prompt Template + 禁止条款）
- [P2] dimension_types 表首次调 create_dimension_record 时 upsert key="requirement_analysis" 幂等（design §2 M04 接口 + accept 补丁 #1）

### 2. 边界 / 状态机

- [P0] requirement_text="" 返 422 Pydantic min_length=1 无 activity_log 写入（design §7 + tests.md B1）
- [P0] requirement_text=5000 字 边界通过 Pydantic 流式正常启动（design §7 max_length=5000 + tests.md B2）
- [P1] requirement_text=5001 字 返 422 Pydantic max_length（design §7 + tests.md B3）
- [P1] requirement_text 含特殊字符 "'; DROP TABLE users; --\n# H\n🎉" 正常处理 prompt 参数化拼装 DB 无异常（design §6 Prompt Template 禁止硬编码 + tests.md B4）
- [P1] affected_node_ids=50 个 UUID save 成功 affected-nodes 返 50（design §7 + tests.md B5）
- [P1] affected_node_ids=500 个 metadata JSONB <1MB PG TOAST 自动压缩不报错（design §7 + tests.md B5）
- [P1] analysis_result 100KB Markdown save 成功 affected-nodes 查询 <100ms（只读 metadata 不读 analysis_result）（design §7 + tests.md B6）
- [P1] MockProvider 0 chunk 直接 complete event full_result="" save 接受空文本（design §7 客户端消费策略 + tests.md B7）
- [P1] analysis_level 非 L1/L2/L3 返 422 ANALYSIS_INVALID_LEVEL（design §13 + tests.md E 段隐含）
- [P2] M13 自身无状态机 R4-1 显式声明 流式连接 streaming→complete/error/disconnect 三出口（design §4 mermaid 占位）
- [P2] 未流完调 /analyze/save 无服务器拦截 save 透明接受任意文本 前端 SDK 在 complete event 后才启用按钮（design §4 禁止转换表 row1）

### 3. 异常 / 错误

- [P0] AI Provider 第 3 chunk 抛异常 SSE 发前 2 chunk + 1 error event error_code=ANALYSIS_PROVIDER_ERROR HTTP 200 SSE 已开始（design §13 + tests.md E1）
- [P0] AI Provider 首次调用即抛异常 SSE 只发 1 error event 无 chunk HTTP 200（design §13 + tests.md E2）
- [P0] 5 分钟服务器硬超时 asyncio.TimeoutError 触发 SSE 发 error event error_code=ANALYSIS_TIMEOUT + provider.aclose() 被调用（design §12A 字段⑤ + tests.md E3）
- [P0] provider quota 耗尽抛 RateLimitError error event error_code=ANALYSIS_QUOTA_EXCEEDED 无 activity_log（design §13 + tests.md E4）
- [P0] save 时 M04.create_dimension_record 抛异常返 500 error_code=ANALYSIS_SAVE_FAILED 事务回滚 dimension_records 无残留 activity_log 无残留（design §13 R-X3 共享 session + tests.md E5）
- [P0] 项目未配置 AI provider (Project.ai_provider=None) 流式立即返 error event error_code=ANALYSIS_PROVIDER_NOT_CONFIGURED HTTP 200 区别于 ANALYSIS_PROVIDER_ERROR（design §13 R13-2 + tests.md E7）
- [P1] save 时 affected_node_ids 含非法 UUID/跨项目 node/软删 node 接受保存不做存在性校验 关系图高亮由 M08 自行过滤（design §1 边界灰区 + tests.md E6）
- [P1] M02 错误 wrap 为 ANALYSIS_PROVIDER_NOT_CONFIGURED M04 错误 wrap 为 ANALYSIS_SAVE_FAILED M03 None 返 ANALYSIS_NODE_NOT_FOUND 上游错误不裸露（design §13 R13-2 跨模块 wrap）
- [P1] SSE error event 后用户点"保存已收到部分"按钮 save 成功 dimension_records 存部分结果 metadata 可选标 {partial:true}（design §7 客户端消费策略 + tests.md S3）
- [P1] AnalysisProviderError http 503 区别于 AnalysisProviderNotConfiguredError http 422 区别于 AnalysisTimeoutError http 504（design §13 AppError http_status）
- [P2] DB 连接断 流式启动前 require_user 拦截兜底返 5xx 不泄漏 stacktrace（design §13 + 规约错误兜底）

### 4. 权限 / Auth

- [P0] 未登录无 Authorization header POST /analyze/requirement 返 401 UNAUTHENTICATED（design §8 + tests.md P1）
- [P0] viewer 调 POST /analyze/requirement 流式 返 403 PERMISSION_DENIED role≥editor（design §8 check_project_access + tests.md P2）
- [P0] viewer 调 POST /analyze/save 返 403 PERMISSION_DENIED 写端点 role≥editor（design §8 + tests.md P3）
- [P0] viewer 调 GET /analyze/affected-nodes 返 200 只读允许 viewer（design §8 + tests.md P4）
- [P0] editor 调 POST /analyze/requirement + save 正常通过（design §8 + tests.md P5）
- [P0] 流式端点走 ADR-004 P1 Bearer JWT 浏览器直连 FastAPI 不经 Server Action（design §8 流式 auth 特殊说明 + 字段④）
- [P0] save / affected-nodes 走 ADR-004 P2 Server Action 注入 X-Internal-Token + X-User-Id + X-Internal-Timestamp + X-Internal-Signature HMAC-SHA256（design §8 表 + audit R2-01）
- [P1] project_admin 流式 + save 继承 editor 权限正常通过（design §8 + tests.md P6）
- [P1] platform_admin 跨项目流式 + save 正常通过（design §8 + tests.md P7）
- [P1] JWT 自然过期 exp 到期 中途 流继续跑完 HTTP 长连接不重校 新 save 请求返 401（design §8 (a) + tests.md P8）
- [P1] JWT 主动作废 token_invalidated_at 触发（管理员禁用/改密/强制登出/refresh 被盗）流开始前拦 401 P9a（design §8 (b) + tests.md P9a）
- [P1] JWT 主动作废 流中途触发 已建流继续跑完接受 ≤5min 暴露窗口（M13 §8 已知脱节非 bug）新 save 401 P9b（design §8 + tests.md P9b）
- [P1] 流式无 chunk 级鉴权 连接级 auth 已覆盖（design §8 无 chunk 级鉴权需求 + §12A 字段④）

### 5. Tenant 隔离

- [P0] userA 持 projectP1 token 调 POST /api/projects/P2/nodes/<P2.node>/analyze/requirement 返 403 PERMISSION_DENIED Router check_project_access 拦（design §8 + tests.md T1）
- [P0] URL projects/P1/nodes/<P2.node> 跨项目 node 混淆 返 404 ANALYSIS_NODE_NOT_FOUND node_service.get_by_id(N2,P1)=None wrap 404 不泄露 N2 存在于 P2（design §8 Service 层 + tests.md T2）
- [P0] save 时 URL node_id 跨项目 返 404 ANALYSIS_NODE_NOT_FOUND 无 dimension_record 写入 无 activity_log（design §8 + tests.md T3）
- [P0] GET /analyze/affected-nodes 跨项目 返 404（design §8 + tests.md T4）
- [P0] AnalyzeService 内部聚合 context 时 M03/M04/M07 Service 调用均带 project_id 参数防跨项目数据泄漏（design §9 上游 Service tenant 过滤 + tests.md T5）
- [P1] M02.get_by_id_for_user 内部 WHERE project_id=? AND user-is-project-member 双过滤（design §9）
- [P1] M03.get_by_id(node_id, project_id) 跨项目返 None M13 wrap AnalysisNodeNotFoundError 404（design §9 + §13）
- [P1] M04 dimension_records 写入 WHERE project_id=? 强制 tenant 过滤（design §9）
- [P1] M07.list_by_project(project_id, node_id, limit=20) 内部 WHERE project_id=? AND node_id=?（design §9）

### 6. 并发 / 乐观锁

- [P0] 同 user 同 node 并发 3 个流式请求 3 个 HTTP 连接独立 yield chunks 无互斥锁错误 无 DB 唯一键冲突（design §5 并发列 + tests.md C1）
- [P0] 流式期间 db session 在 async for 开始前释放 流式循环内不持 DB 连接 避免 Postgres pool 10-20 被 5 并发流式打满（design §5 流式 DB session 释放策略 + audit R2-02）
- [P0] save 由前端新起 POST 另开 request scope session 不复用流式 session（design §5 并发列 + R-X3）
- [P1] 同 user 不同 node 并发 N1/N2/N3 三个流互不影响 context 拼装严格按各自 node_id 独立（design §5 + tests.md C2）
- [P1] 同 user 同 full_result save 3 次 后端允许 dimension_records 新增 3 行 activity_log 3 条 affected-nodes 返最新一条（M04.get_latest ORDER BY created_at DESC）（design §11 + tests.md C3）
- [P1] 不同 user A/B 都是 P1 editor 并发 save 同 node 两条 dimension_record 各自 created_by 区分 affected-nodes 返最新（design §11 + tests.md C4）
- [P1] M13 无幂等 idempotency_key 不参与 流式每次结果可能不同（AI 非确定性）/ save 多次=多条历史合法（design §11 + §5 项 4）
- [P1] M13 无乐观锁 version save 是 INSERT 非 UPDATE（design §5 项 2）
- [P2] 流式期间 5 分钟长连接占用 DB 连接池压力监控指标（design §5 并发列 + audit R2-02 非功能性断言）

### 7. 数据完整性

- [P0] M13 无自有 SQLAlchemy model R3-5 纯读聚合规范 frontmatter mixins=no_dependency（design §3 + frontmatter）
- [P0] M13 禁直 JOIN dimension_records 或 nodes 表 走 M04/M03 Service（design §3 禁止条款 + ADR-003 规则 1）
- [P0] M13 禁直 INSERT dimension_records 经 M04.create_dimension_record Service 接口（design §3 + §6 Service 层禁止）
- [P0] M13 禁直写 activity_log 由 M04 在 create_dimension_record 内代写（design §3 + §10 + ADR-003 规则 3 横切豁免）
- [P0] save 调 M04.create_dimension_record(db, ..., extra_activity_metadata={...}) 注入 7 字段 dimension_type_key/analysis_level/affected_node_count/ai_provider/ai_model/analysis_time_ms/requirement_text_hash（design §10 metadata + §2）
- [P1] activity_log 一条 action_type=create target_type=dimension_record 不新增 action_type 不扩 M15 CHECK 枚举 不需 Alembic 迁移（design §10 R10-2 + accepted 决策）
- [P1] activity_log metadata 合并 M04 默认 {node_id, type_id, content_size} ∪ M13 注入 7 字段（design §10 表）
- [P1] affected_node_count 只存计数 不存 ID 数组 避免 metadata 膨胀（design §10 metadata 字段说明）
- [P1] requirement_text_hash = SHA256(requirement_text) 留审计锚点不存明文（5000 字过大）（design §10 metadata 字段说明）
- [P1] save 调 M04 用 with self.db.begin() 包裹 单事务内写 dimension_record + activity_log 两表 R-X3 共享 session（design §5 多表事务列 + audit R2-03）
- [P2] AI usage tracking（token 消耗 / 谁用得多）未来另起 ai_usage_log 表 不复用 activity_log（design §10 只 1 条理由）

### 8. UI / UX

- [P0] node 档案页 web/.../[pid]/nodes/[nid]/page.tsx 挂载 M13 分析抽屉 UI + 保存按钮 + 关系图高亮触发（design §6 Page 层）
- [P0] analyze-drawer.tsx 抽屉 UI + analyze-sse-client.ts fetch ReadableStream 解析 SSE + AbortController 取消 + 保存按钮防抖（design §6 Component 层）
- [P0] [E2E] 保存按钮点第 1 次立即变 disabled+loading 用户疯点 10 次 network 只 1 个 /analyze/save 请求 DB 仅 1 新行（design §6 防抖 + tests.md C3b + audit R2-04）
- [P0] [E2E] 同一 full_result SHA256 hash 在本抽屉生命周期内拒绝二次 save 防用户清空再输相同文本误操作（design §6 Component + tests.md C3b）
- [P1] [E2E] Playwright 流式 UI 完整交互：登录→打开 node→点 AI 分析→抽屉打开→第 1 chunk 显示→点取消→fetch 断开→再分析→完整流→点保存→抽屉关闭→历史列表出新记录（tests.md S9）
- [P1] 前端 fetch 不绕过 AbortController 管理 否则取消机制失效（design §6 禁止条款）
- [P1] error event 后展示已累积 chunks + 显示错误提示 + 保留"保存已收到部分"按钮供用户选择（design §7 客户端消费策略）
- [P1] complete event 后 chunk 累积区定稿 + 启用保存按钮 save 时用 complete.full_result + complete.metadata 构造 SaveAnalysisRequest（design §7 客户端消费策略）
- [P2] 流式响应 header Content-Type=text/event-stream + Cache-Control=no-cache（tests.md S8）
- [P2] X-Accel-Buffering=no 若过 Nginx 反代避免 buffer 缓冲整个流（tests.md S8）

### 9. SSE 流式特化（§12A 子模板 7 字段）

- [P0] 字段② SSE event 类型枚举 chunk（高频每秒 5-50）+ complete（1 次/流）+ error（0 或 1 次/流 与 complete 互斥）（design §12A 字段② + tests.md S2）
- [P0] 字段⑤ 超时策略 服务器侧 asyncio.timeout(300) 包住 async for chunk 参 ADR-001 TASK_TIMEOUTS["need_analysis"]=300s（design §12A 字段⑤）
- [P0] 字段⑥ 取消机制 前端 AbortController.abort() 服务器 Request.is_disconnected() 在每次 yield 后检查 断开时停止 async for + provider.aclose() + 不发任何 SSE event（连接已断）（design §12A 字段⑥ + tests.md S4）
- [P0] 字段⑥ AsyncIterator aclose 协议依赖 PEP 533 真 SDK anthropic ≥0.x / openai ≥1.x / Kimi SDK streaming 对象均实现 aclose（design §12A 字段⑥）
- [P0] 字段⑥ MockProvider 必须实装 aclose_called: bool 标志可断言 供 S4 验证（design §12A + tests.md MockProvider fixture + 14.5 LLM 红线）
- [P0] chunk 顺序保证 MockProvider 按顺序 yield 10 chunk 客户端拼起来=原 order 无乱序无丢失无重复（tests.md S1）
- [P0] complete event 只发 1 次 互斥 error event（tests.md S2）
- [P1] 字段① SSE 端点 POST /api/projects/{pid}/nodes/{nid}/analyze/requirement Content-Type=application/json Accept=text/event-stream Authorization=Bearer <jwt>（design §12A 字段①）
- [P1] 字段③ 每个 event data payload 走 Pydantic BaseModel 序列化 R7-1 强类型不裸 dict（design §12A 字段③ + §7 SSEChunkEvent）
- [P1] 字段⑥ 取消接受 AI token 浪费（已发请求的部分 token 已扣费）对齐 M17 Q5 精神（design §12A 字段⑥ 副作用）
- [P1] 字段⑦ 断线重连不支持续传 前端检测断开 → "连接中断 请重新分析" → 重新发 POST 全新流（不使用 SSE Last-Event-ID header）（design §12A 字段⑦ + tests.md S5）
- [P1] SSE 不走 Server Action 浏览器直连 FastAPI 原因 Server Action 是 JSON response 不支持 ReadableStream 转发会缓冲成单 response（design §8 流式 auth 特殊说明）
- [P1] SSE 传输格式严格 "event: <type>\ndata: <json>\n\n"（design §7 SSE 传输格式样例）
- [P2] chunk 极端 1MB 单 chunk SSE 协议承载 + 前端能解析（tests.md S6）
- [P2] chunk 极端 10000 个 1 字节 chunk 服务器顺序发出 + 前端顺序接收（tests.md S6）
- [P2] 服务器 uvicorn kill 模拟重启 前端 fetch promise reject UI 提示"连接中断"服务器重启后用户点再分析正常 无 DB 残留（tests.md S5）
- [P2] §12A 7 字段仅服务🌊流式 SSE 场景 M16/M18 另起 §12B/§12C 不复用（design §12A 适用范围 + audit R3-01）

### 10. ErrorCode 注册（R13-1 + R13-2）

- [P1] ANALYSIS_NODE_NOT_FOUND 注册 api/errors/codes.py 对应 AnalysisNodeNotFoundError(NotFoundError) http=404（design §13）
- [P1] ANALYSIS_PROVIDER_NOT_CONFIGURED 对应 AnalysisProviderNotConfiguredError(AppError) http=422（design §13）
- [P1] ANALYSIS_PROVIDER_ERROR 对应 AnalysisProviderError(AppError) http=503 瞬时故障提示重试（design §13）
- [P1] ANALYSIS_TIMEOUT 对应 AnalysisTimeoutError(AppError) http=504（design §13）
- [P1] ANALYSIS_QUOTA_EXCEEDED 对应 AnalysisQuotaExceededError(AppError) http=429（design §13）
- [P1] ANALYSIS_SAVE_FAILED 对应 AnalysisSaveFailedError(AppError) http=500（design §13）
- [P1] ANALYSIS_INVALID_LEVEL 对应 AnalysisInvalidLevelError(AppError) http=422 Pydantic Enum 兜底（design §13）
- [P1] R13-2 跨模块 wrap M04 DimensionWriteError→ANALYSIS_SAVE_FAILED / M02 Project.ai_provider=None→ANALYSIS_PROVIDER_NOT_CONFIGURED / AI SDK 5xx→ANALYSIS_PROVIDER_ERROR / M03 get_by_id=None→ANALYSIS_NODE_NOT_FOUND（design §13）
- [P2] frontmatter codes_added 7 个新增 ErrorCode 与 api/errors 文件实际定义一致（design frontmatter + R13-1 CI 守护）

### 11. 分层职责 / R-X3 跨模块契约

- [P0] M04.DimensionService.create_dimension_record(db, *, project_id, node_id, dimension_type_key, content, user_id, extra_activity_metadata) 接受外部 db session R-X3 不自开事务（design §2 + audit R2-03）
- [P0] M04.create_dimension_record 内部代写 activity_log 在同一事务 M13 不直写（design §10 + audit R2-03）
- [P0] M04.DimensionService.get_latest(db, *, project_id, node_id, dimension_type_key) 接受外部 db session（design §2 + R-X3）
- [P0] M07.list_by_project(db, project_id, node_id=None, limit=20) node_id 可选参数（M13 pilot 基线补丁追加）（design §2）
- [P1] M02/M03/M04/M07 上游 Service 接口由 baseline-patch 落地为 accept 前置条件（audit B1 + audit B5 + design §15）
- [P1] importlinter 禁 routers/analyze.py 直查任何 DB 表（design §6 禁止条款）
- [P1] importlinter 禁 services/analyze_service.py 直写 dimension_records 或直查其他模块表（design §6 禁止条款 + R-X1）
- [P1] Service 层 AnalyzeService.__init__ 依赖注入 project_service/node_service/dimension_service/issue_service/activity_service/ai_client 6 个上游 Service（design §3 DAO 草案）
- [P1] AI Client api/clients/ai_client.py 多 provider 统一流式接口 async def analyze(prompt, context)→AsyncIterator[str] 与 M17 共享 ADR-001 §4.1（design §6 + §2）

### 12. idempotency 显式 N/A

- [P1] M13 三端点均无 idempotency key R11-2 显式声明 project_id 不参与 key 计算（因不存在 key）（design §11）
- [P1] POST /analyze/requirement 无 idempotency 理由 AI 非确定性 幂等=缓存命中违背用户重分析语义（design §11）
- [P1] POST /analyze/save 无 idempotency 理由 用户重复保存=多条历史合法 Q6 业务决策 加 idempotency 会隐式去重让用户困惑（design §11）
- [P1] GET /analyze/affected-nodes N/A GET 本身幂等无需应用层 key（design §11）

### 13. 关系图联动（F13 AC4）

- [P0] save 返 200 后立即 GET affected-nodes 无缓存延迟立即返回最新数据（tests.md R1）
- [P0] 多次 save 后 affected-nodes 返最后一次 save 的 affected_node_ids（M04.get_latest ORDER BY created_at DESC）（tests.md R2）
- [P1] 全新 node 无历史分析 GET affected-nodes 返空数组 + analysis_record_id=null（tests.md R3）
- [P1] save 后 node 被 M03 软删/硬删 GET affected-nodes 行为由 M04.get_latest 定义 不在 M13 tests（属 M03 级联删测试范畴）（tests.md R4）
- [P1] M08 关系图渲染 + 节点高亮 UI 不在 M13 范围 M13 只返 affected_node_ids 清单（design §1 out-of-scope）

### 14. LLM 集成专属（M13 是 LLM 集成首发 / audit 14.5）

- [P0] 本 sprint 实装 Mock + Claude（anthropic httpx stream）真 SDK MockProvider 必含 aclose_called 可断言（design §14.5 真 SDK 范围 + LLM 红线）
- [P1] AES 解密 Project.ai_api_key_enc → ProviderRegistry.get(provider, api_key) → SDK 全链路打通（design §14.5 AES 接通范围 CY 拍）
- [P1] Integration smoke tests/integration/test_provider_smoke.py @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY')) CI 默认跳过 本机手动跑（design §14.5）
- [P1] DONE 区分 unit pass（全 MockProvider）vs integration pass（≥1 真 anthropic SDK 验 aclose 协议）NEEDS_CONTEXT 标 integration smoke 是否真跑过（design §14.5 LLM 红线）
- [P1] Kimi/Codex/DeepSeek 后续 sprint 顺手抄 prism 本 sprint 不实装（design §14.5 真 SDK 范围）
- [P2] feedback_llm_hotpath_math 4 数字+3 红线 N/A M13 是 user-triggered SSE 不是 cron/scan/per-event hot path（design §14.5 LLM 红线）

### 15. Phase 2 Prism→prism-0420 迁移

- [P1] URL 形态 Prism 扁平 /analyze/requirement (project_id/node_id 在 body) → M13 嵌套 /api/projects/{pid}/nodes/{nid}/analyze/requirement 前端 analyze-sse-client.ts URL 拼装 + Server Action analyze.ts 转发 URL + RequirementAnalysisRequest 删 project_id/node_id 字段（design §2 迁移成本表）
- [P1] 鉴权 Prism 无显式 Depends(require_user) → M13 走 ADR-004 P1 + check_project_access 双层 Router 增 Depends 测试 fixture 补 auth header（design §2 迁移成本表）
- [P1] dimension_record 写入 Prism Router 直 db.add+db.commit 违反分层 → M13 Service 层经 M04.create_dimension_record 重构 save endpoint（design §2 迁移成本表）
- [P2] affected-nodes URL Prism /analyze/affected-nodes?node_id= → M13 /api/projects/{pid}/nodes/{nid}/analyze/affected-nodes 前端改 ~10 行（design §2 迁移成本表）
- [P2] SSE event 命名 chunk/complete/error Prism 与 M13 一致 0 改动（design §2 迁移成本表）
- [P2] 总预估 Phase 2 迁移 ~100-150 行前后端代码改动含测试 fixture 计入对照 Prism 时间成本（design §2 迁移成本表）
