---
module: M18
name: semantic-search
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M18-semantic-search/00-design.md
  - design/02-modules/M18-semantic-search/tests.md
  - design/02-modules/M18-semantic-search/audit-report.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F18 语义搜索 / US-B1.5 配额管理同义召回 / US-B1.6 用户无感混合 + pgvector 降级
pilot: true
complexity: high
supersedes: M09
async_mode: §12D embedding 持久化（arq Queue 双触发链 + 失败容忍 + 模型版本回填）
---

# M18 语义搜索 测试点

## 业务流程（H1 / 1 行概述）

M18 升级 superseded M09 接管 search 路由，搜索框不变 / 后端自动 BM25 关键词 + pgvector 语义双路 RRF 融合 + project filter；写入路径双触发链（增量：M03/M04/M06/M07 Service commit 后调 enqueue / Backfill：cron 0 点 + 启动 + admin 触发）走 arq Queue → embed_single worker（Redis 60s debounce + advisory_xact_lock 双 namespace + content_hash 三层幂等）；embeddings 表 7 字段复合主键 (project_id, modality, target_type, target_id, provider, model_name, model_version) + 异维列 embedding_512/1536/3072 + dim 路由；失败容忍（3 次重试 → 写 embedding_failures + monitor 三维阈值告警 CY 不通知用户）；pgvector 不可用降级 keyword_only 200 不报错；OpenAI/bge/Mock 三 provider 抽象，部署期固定不支持运行时切换。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/search query="配额" hybrid 模式同时返关键词命中 node + 语义同义 node 按 RRF 排序（design §1 US-B1.5 + tests.md golden_03）
- [P0] 增量路径 M03 create_node commit 后尾调 enqueue → Redis SET debounce + Queue 拉起 + worker 调 OpenAI + upsert embeddings 表 1 行 PK 7 字段（design §12D 字段① 双触发链 + tests.md golden_01）
- [P0] Backfill 路径 admin POST /api/admin/embedding/backfill 返 202 + EmbeddingBackfillDAO 规则 4 LEFT JOIN 扫差异 + 按 project 分批 enqueue enqueued_by="backfill"（design §9 规则 4 + tests.md golden_02）
- [P0] POST /api/admin/embedding/model-upgrade 切 EMBEDDING_PROVIDER+MODEL_NAME+MODEL_VERSION 后扫旧三元组分批 enqueue enqueued_by="model_upgrade" 新旧共存于不同 PK 行（design §12D 字段⑦ + tests.md golden_05）
- [P0] SearchResponse 返 search_mode + query_embedding_cached + 每条 matched_by=["keyword"|"semantic"|"keyword","semantic"] 透明给用户/调试（design §7 SearchResultItem）
- [P0] activity_log 写 EMBEDDING_MODEL_UPGRADE_TRIGGERED + EMBEDDING_BACKFILL_TRIGGERED 各 1 条 target_type=project metadata 含 old/new + affected_count（design §10 + audit M1）
- [P1] query embedding Redis 5min 缓存命中第二次同 query 不调 OpenAI 返 query_embedding_cached=true 响应 < 200ms（design §1 Q4=C + tests.md golden_04）
- [P1] GET /api/admin/embedding/stats 返 failure 率 + pending task 数 + (provider, model_name, model_version) 分布（design §7 endpoints）
- [P1] SearchRequest target_types=[node,issue] filter 仅返 2 类 target 排除 dimension_record + competitor（design §7 SearchRequest）
- [P1] SearchRequest limit=50 返恰好 ≤50 条结果（design §7 SearchRequest ge=1 le=100）
- [P1] hybrid 模式仅关键词命中无语义命中时 search_mode 仍 "hybrid" matched_by 仅 ["keyword"]（design §1 + tests.md boundary_06）
- [P1] 业务表已写但 embedding pending 时立即搜 query 关键词路径命中语义路径不命中（design §1 RAW 一致性 + tests.md boundary_06 + consistency_01）
- [P1] M14 industry_news 不接入 search 路由结果不含 industry_news target_type（design §1 边界灰区 + tests.md boundary_08）

### 2. 边界 / 状态机

- [P0] embedding_task pending → running → succeeded 正常路径 worker 拉起后 30 天 cron 物理清理（design §4 mermaid 状态机）
- [P0] succeeded → 任意 状态抛 EMBEDDING_TASK_TERMINAL_VIOLATION 终态不可变（design §4 禁止转换 1）
- [P0] dead_letter → 任意 状态抛 EMBEDDING_TASK_TERMINAL_VIOLATION 死信终态不可变（design §4 禁止转换 2）
- [P0] pending → succeeded 跳过 running 抛 EMBEDDING_TASK_INVALID_TRANSITION 必须经 worker（design §4 禁止转换 3）
- [P0] failed 短暂态 worker 写入后 30s 内 cron 强制转 dead_letter 同时落 embedding_failures 一条记录（design §4 R4-3a 非常规态登记表）
- [P0] SearchRequest query="" 返 400 / INVALID_QUERY_LENGTH Pydantic min_length=1（design §7 + tests.md boundary_01）
- [P0] SearchRequest query="a"×200 通过校验正常搜索（design §7 max_length=200 + tests.md boundary_02）
- [P0] SearchRequest query="a"×201 返 400 / INVALID_QUERY_LENGTH 超上限（design §7 + tests.md boundary_03）
- [P1] SearchRequest limit=0 返 400 ge=1 拦截（design §7 SearchRequest ge=1）
- [P1] SearchRequest limit=101 返 400 le=100 拦截（design §7 SearchRequest le=100）
- [P1] dim=768 写 embedding 触发 CHECK ck_embeddings_dim_range violation 包装为 EmbeddingProviderFailedError + 写 failures EMBEDDING_DIM_NOT_SUPPORTED 死信（design §3 dim IN {512,1536,3072} + tests.md boundary_07）
- [P1] embeddings 行只填一个 dim 列其余 NULL 违反 ck_embeddings_dim_column_consistency 抛 CHECK violation（design §3 互斥约束）
- [P1] modality 写 'video' CHECK ck_embeddings_modality 拒绝仅允许 text/image/audio（design §3 R3-2）
- [P1] provider 写 'cohere' CHECK ck_embeddings_provider 拒绝仅允许 openai/bge/mock（design §3 R3-2）
- [P1] embedding_tasks.status 写 'foo' CHECK ck_embedding_tasks_status 拒绝仅 5 态（design §3 EmbeddingTaskStatus + audit m1）
- [P2] embedding_tasks.enqueued_by 写 'manual' CHECK ck_embedding_tasks_enqueued_by 拒绝仅 incremental/backfill/model_upgrade（design §3）

### 3. 异常 / 错误

- [P0] mock OpenAI 持续 503 worker 失败 3 次（1s/4s/16s 指数退避）→ task failed → 写 embedding_failures EMBEDDING_PROVIDER_FAILED → 30s 后 cron 转 dead_letter 不通知用户（design §12D 字段⑥ + tests.md error_01）
- [P0] zombie cron 每 5min 扫 status='running' AND created_at < NOW-2min CAS UPDATE 转 failed + EMBEDDING_ZOMBIE 防 worker OOM 死锁（design §12D 字段⑦ + tests.md error_03）
- [P0] pgvector 扩展不可用 search 路由返 200 + search_mode="keyword_only" + 写 1 条 embedding_failures PGVECTOR_UNAVAILABLE 每小时去重 PRD AC4 不报错（design §3 Alembic 要点 + tests.md boundary_04）
- [P0] query embedding OpenAI 超时 1s 触发 SearchTimeoutError → SearchService 降级 keyword_only 返 200 不计入 SLA + 写 failures EMBEDDING_PROVIDER_TIMEOUT（design §12D 字段⑤ M5 + tests.md boundary_05）
- [P0] 业务表已删 worker 反查 Service.get_for_embedding 返 None → wrap EmbeddingTargetNotFoundError → task succeeded noop 不重试不写 failures（design §13 R13-2 + tests.md error_04）
- [P0] M03.delete_node commit 后 enqueue_delete 抛 SilentFailure → logger.warning + 写 failures EMBEDDING_DELETE_FAILED 业务删除不回滚（design §9 删除策略 B1 修复 + tests.md error_05）
- [P0] monitor cron 每 1h 三维阈值任一超阈告警 CY：单小时全局 ≥500 / 失败率 ≥5% / 单 project ≥100（design §12D 字段⑥ M10 + tests.md error_02）
- [P0] 重复 POST /api/admin/embedding/backfill 已在跑返 409 / EMBEDDING_BACKFILL_ALREADY_RUNNING（design §13 + tests.md error_06）
- [P1] 启动时 EMBEDDING_MODEL_NAME 不存在 EmbeddingProvider 初始化失败 startup 报错 EMBEDDING_MODEL_UPGRADE_INVALID（design §13 + tests.md error_07）
- [P1] search 路由顶层超时 keyword 路径上游 Service 卡 5s 触发 asyncio.timeout 返 504 / SEARCH_TIMEOUT（design §13 + tests.md error_08）
- [P1] search 上游 ErrorCode 透传不 wrap（M02 search_by_keyword 抛 NodeAccessDeniedError）+ metadata['from_module']='M03' 标记便于调试（design §13 R13-2 M2 修复 audit）
- [P1] _validate_current_model_on_startup current_triple 不在 embeddings 表 distinct 集合时 logger.warning + 自动 fallback _effective_model_for_search 到 latest 三元组避免全 miss（design §9 audit M6 + tests.md provider_switch_01）
- [P1] mock provider 启动时 EMBEDDING_MODEL_NAME 非 'mock-*' 前缀抛 ConfigError 进程退出（design §9 fix v4.2 R2=A + tests.md provider_switch_02）
- [P2] EmbeddingDeleteFailedError 继承 SilentFailure（BaseException）调用方 except SilentFailure 才能捕获普通 except Exception 会冒泡崩溃（design §13 SilentFailure 使用约束）
- [P2] embedding_failures 90 天后 cron 物理删除（design §3 保留策略）
- [P2] dead_letter task 90 天后 cron 物理删除（design §4 + §12D 字段⑦）

### 4. 权限 / Auth

- [P0] 无 Bearer token POST /api/projects/{pid}/search 返 401 / UNAUTHENTICATED（design §8 L2 require_user + tests.md perm_01）
- [P0] user_1 仅 project_X 成员调 POST /api/projects/project_Y/search 返 403 / PROJECT_FORBIDDEN L3 SearchService.check_project_access 拦截（design §8 L3 + tests.md perm_02）
- [P0] 非 platform_admin user 调 POST /api/admin/embedding/backfill 返 403 require_platform_admin 拦截（design §8 L2 + tests.md perm_03）
- [P0] 非 platform_admin user 调 POST /api/admin/embedding/model-upgrade 返 403 require_platform_admin 拦截（design §8 L2）
- [P0] 非 platform_admin user 调 GET /api/admin/embedding/stats 返 403（design §8 L2）
- [P0] Queue 消费者 worker 入口 check_payload_consistency 反查业务表 target.project_id != payload.project_id → task failed + 写 failures 防 enqueue 调用方串 project（design §8 L4 + tests.md tenant_03 + perm_05）
- [P1] viewer user 在 project_X 设置页 UI 不渲染 rrf_k/similarity_threshold 输入框 + POST projectSettings 携带 rrf_k 返 403 assertProjectRole admin（design §8 L1 + tests.md perm_04）
- [P1] embedding worker 内部 enqueue 接口不暴露 HTTP 仅业务模块 Service 层信任调用不做 project access check（design §8 L3 EmbeddingService.enqueue）
- [P1] R10-2 例外条件 3 验证 embedding 失败写 embedding_failures 不写 M15 activity_log + M01 auth_audit_log 仍合规系统行为分类（design §10 audit M7 + tests.md perm_06）
- [P2] embedding CRUD 端点不对外暴露 GET/POST/PUT/DELETE /api/embeddings/* 全 404 用户视角看不见 embedding（design §7 关键不暴露）

### 5. Tenant 隔离

- [P0] project_X node_A "配额管理" + project_Y node_B "配额管理" 各自有 embedding user_1 仅 project_X 成员搜 "配额" 仅返 node_A 不返 node_B 即使余弦相似度更高（design §1 Q5+Q9 + tests.md tenant_01）
- [P0] 向量路径 SQL WHERE project_id=:pid AND provider=:p AND model_name=:mn AND model_version=:mv + dim 路由 + ivfflat ORDER BY 严格 tenant filter（design §9 EmbeddingDAO.vector_search）
- [P0] 关键词路径调上游 Service.search_by_keyword(query, project_id, limit) 由上游负责 project_id filter 不跨 project（design §9 规则 1 主规则）
- [P0] EmbedSinglePayload 强制带 user_id + project_id 继承 TaskPayload 基类 ADR-002 Queue 消费者侧（design §8 L4 + §5 5 项清单 #3）
- [P0] EmbeddingBackfillDAO.list_pending 规则 4 豁免 LEFT JOIN WHERE Node.project_id=:pid 仅扫单 project 不串库（design §9 规则 4 + tests.md golden_02）
- [P0] M02 project 硬删 FK ondelete='CASCADE' 自动清理 embeddings + embedding_tasks + embedding_failures 三表所有 project_X 行（design §9 删除策略 + tests.md tenant_02）
- [P1] M02 project 软删 deletedAt search 路由按 accessible_project_ids 过滤掉已软删 project embeddings 表保留（design §9 删除策略 + tests.md tenant_02）
- [P1] project_X rrf_k=60 + project_Y rrf_k=80 同 user 切 project 各取自己 RRF 参数（design §1 Q6=C + tests.md tenant_04）
- [P1] 同 user 跨 project 搜同 query 结果不同排序受 project 级 similarity_threshold 影响（design §6 SearchService + tests.md golden_06）
- [P1] cron 任务 user_id 填 SYSTEM_USER_UUID 不允许填 task creator 或 NULL 符合 ADR-002 §1.1 规约（design §12D 字段⑦ cron user_id 边界）
- [P1] embedding_failures 未来加 user_id 列必须落 SYSTEM_USER_UUID R10-2 例外推论（design §10 末段）
- [P1] EmbedSinglePayload 内 enqueued_by="model_upgrade" 仍需 user_id=SYSTEM_USER_UUID + project_id 跨 project 时分批 enqueue 不混淆（design §12D 字段⑦）
- [P2] search_evaluation_log 1% 采样写入按 project_id + user_id 关联便于按 project 离线分析（design §3 自有表 4）

### 6. 并发 / 幂等

- [P0] 60s 内同 (project_id, target_type, target_id) 5 次连续 update 仅 1 次 OpenAI 调用 Redis SET debounce 第 2-5 次 enqueue skip 最终内容是第 5 次（design §11 enqueue debounce + tests.md concurrent_01）
- [P0] 2 个 worker 同时拿 (project_id, target_id) 任务 pg_advisory_xact_lock(hashtext('m18_text_embedding'), hashtext(project_id||'/'||target_id)) 双 namespace 互斥 后跑 worker content_hash 比对相同 skip OpenAI（design §11 advisory lock + tests.md concurrent_02）
- [P0] worker 内 content_hash key = (project_id, modality, target_type, target_id, provider, model_name, model_version, content_hash) 7 字段 PK + hash 比对相同跳过 Provider 调用（design §11 worker 内 + audit fix v4.3 F2）
- [P0] backfill cron 入队 100 task + 同时增量 enqueue 1 task 同 target_id advisory lock 互斥 + content_hash 比对 → 总 OpenAI 调用 100 次增量被去重（design §5 R5-2 + tests.md concurrent_03）
- [P0] worker 内事务边界 advisory_xact_lock 在 worker 入口 + commit 时锁释放 单 task 单事务不跨多 task 大事务（design §5 4 维 事务列）
- [P1] 模型升级回填期间 search 用 current_triple filter 只命中新 embedding 旧 embedding 不参与召回但保留 PK 物理共存（design §4 行级状态 + tests.md concurrent_04）
- [P1] 3 user 同时搜同一 query cache 空允许竞态 OpenAI 调用 ≤3 不强制 =1 后续 5min 内同 query 命中缓存（design §1 Q4=C + tests.md concurrent_05）
- [P1] RRF 参数 admin update 时正在 search 的 race read-after-write stale 允许 此次 search 用旧 rrf_k 下次用新 rrf_k 最长 stale 窗口 ≤ 3s（design audit M8 + tests.md concurrent_06）
- [P1] _job_id=f"backfill_recovery:{task.id}" arq 1h 内幂等去重防 cron + startup 并发触发的重复入队风暴（design §6 backfill_recovery + audit fix v3 决策 2）
- [P1] hashtext 32-bit 鸽笼 5 万行 ~0.06% 跨 project 碰撞 双 namespace + project_id 入 lock key 防御（design §11 R11-2 M4 修复 + verify L3）
- [P2] embedding_tasks 表不建 unique 约束 业务幂等条件含时间窗口 + 终态过滤 PG partial index 谓词必须 immutable 做不到 靠 ORM + advisory_lock 模式（design §11 task 表 unique 约束）

### 7. 数据完整性

- [P0] embeddings 表 7 字段 PK (project_id, modality, target_type, target_id, provider, model_name, model_version) 同 (target_type, target_id) 不同三元组物理共存（design §3 + audit fix v4.1 R5'=B）
- [P0] embedding_1536 列写入 dim 字段必须 =1536 否则 ck_embeddings_dim_column_consistency CHECK 违反（design §3 异维列互斥约束）
- [P0] ix_embeddings_vector_1536 ivfflat partial index WHERE embedding_1536 IS NOT NULL postgresql_using='ivfflat' lists=100 + vector_cosine_ops（design §3 三独立 ivfflat 索引）
- [P0] ix_embeddings_project_provider_model (project_id, provider, model_name, model_version) 联合索引支持 Q5=B project filter 路径（design §3）
- [P0] backfill 中断恢复 detect_and_resume_pending_backfill 启动钩子 + arq cron 1h 一次扫 status='pending' AND enqueued_by='backfill' AND created_at < NOW-1h 真 enqueue 回 arq（design §12D Backfill 中断恢复 + audit fix v3 决策 2 + tests.md recovery_01）
- [P0] task_cleanup cron 每日 0 点 succeeded > 30 天 DELETE + failed+dead_letter > 90 天 DELETE（design §15 cron 矩阵）
- [P0] failure_cleanup cron 每日 0 点 failed_at > 90 天 DELETE（design §3 保留策略 + §15 cron 矩阵）
- [P0] orphan_cleanup cron 每周一次 周日 0 点 按 target_type 分组 LEFT JOIN business 表 WHERE business.id IS NULL AND embeddings.created_at < NOW-30d DELETE 兜底业务删除 enqueue 失败（design §9 + §15 cron 矩阵）
- [P0] model_version_cleanup cron 每周一次 (provider, model_name, model_version) != current_triple AND created_at < NOW-30d DELETE 模型升级旧版本 30 天宽限（design §15 cron 矩阵 fix v4.2 B3）
- [P0] search_eval_cleanup cron 每月一次 sampled_at > 1 年 DELETE 评估日志 1 年保留（design §3 保留策略 + §15 cron 矩阵）
- [P1] embedding_failures 写入 provider+model_name+model_version 三段对齐 embeddings PK 便于 Phase 2 监控按 (provider, model_name) 切片分桶（design §3 fix v4.2 B5 + audit V1 死字段备注）
- [P1] embedding_tasks 写入 provider+model_name+model_version 三段 backfill recovery 时从 task 表取三段填 enqueue payload（design §3 fix v4.2 B5 + O5）
- [P1] search_evaluation_log 1% 采样写 keyword_top5 + semantic_top5 + hybrid_top5 三模式各 JSONB 数组 + rrf_k + similarity_threshold 当时值（design §3 自有表 4 audit M13）
- [P1] /api/search-eval/{eval_id}/click 用户点击事件前端独立 endpoint 上报回写 user_clicked_target_type + user_clicked_target_id 便于离线分析（design §3 采样逻辑）
- [P1] Alembic 启用 CREATE EXTENSION IF NOT EXISTS vector + 4 表一次迁移 + ivfflat 三索引同步建立（design §3 Alembic 要点）
- [P2] 新增 dim（如 768）必须停服窗口或 expand-then-contract 两阶段同步改 ck_embeddings_dim_range + ck_embeddings_dim_column_consistency + 加 embedding_<dim> 列 + 加 ivfflat 索引 breaking 迁移（design §3 Alembic 要点 N8）

### 8. UI / UX

- [P0] 搜索框用户无感不显示"语义/关键词模式"切换器 search_mode 字段仅给前端调试用（design §1 US-B1.6）
- [P0] M02 项目设置页 admin 可编辑 rrf_k + similarity_threshold 输入框（design §6 actions/projectSettings.ts + tests.md golden_06）
- [P0] viewer 用户打开 M02 设置页 UI 不渲染 rrf_k/similarity_threshold 输入框（design §8 L1 + tests.md perm_04）
- [P1] SearchResultItem.matched_by 前端可视化展示哪条路径命中（关键词高亮 vs 语义召回标签）便于用户理解（design §7 SearchResultItem）
- [P1] SearchResultItem.snippet 关键词高亮 or 语义摘要前端渲染（design §7）
- [P1] SearchResultItem.breadcrumb 复用 M09 已有面包屑路径展示 node 在模块树位置（design §7）
- [P2] pgvector 不可用降级 keyword_only 前端无错误提示 search_mode 字段透明降级用户无感（design §1 PRD AC4）

### 9. 性能 / SLA

- [P0] search 路由 ≤3s PRD 6.1 SLA query embedding 1s + RRF + DB 留预算（design §6 QUERY_EMBEDDING_TIMEOUT_MS=1000 + audit M5）
- [P0] query embedding cache 命中响应 < 200ms 比 OpenAI 200ms 调用快（design §1 Q4=C + tests.md golden_04）
- [P1] 5 万条 backfill 时长 ≤ 15min ADR-001 §4.2 ai_embedding=15min 验证规则 4 豁免性能收益（design tests.md §8 performance baseline）
- [P1] 单 embedding task 超时 EMBEDDING_TASK_TIMEOUT_S=60s OpenAI/bge 调用兜住 asyncio.timeout（design §12D 字段⑤ + §6 env 表）
- [P1] batch backfill 整批超时 BACKFILL_BATCH_TIMEOUT_S=900s 对齐 ADR-001（design §12D 字段⑤）
- [P1] query_embedding_timeout_total Prometheus counter 单独埋点 超时不计入 SLA M12 演进可观测性基础（design §12D 字段⑤ M12 修复 + audit M12）
- [P2] 50 万行规模触发 IVFFLAT_LISTS 从 100 调到 sqrt(N)~700 reindex 评估锚点 design §15 演进锚点 audit M9
- [P2] embedding_tasks 50 万行规模触发 partition / 归档表演进 zombie cron 5min 扫表压力大（design §15 演进锚点 audit M11 + R3 E3）

### 10. 兼容性 / 降级

- [P0] pgvector 扩展不可用 FastAPI 启动时探测 → search 路由全程 keyword_only PRD AC4 + embedding 写入直接 noop 不报错（design §3 Alembic 要点 + tests.md boundary_04）
- [P0] SEARCH_MODE env kill switch 三档 hybrid/keyword_only/semantic_only 一键回退 audit B5 修复（design §6 env 表）
- [P0] OpenAI / bge / Mock 三 provider 部署期 env 静态选不支持运行时切换 audit C3=C 决策（design §3 Provider 切换路径 + tests.md provider_switch_01）
- [P1] provider 切换同维度（OpenAI v3-small → 同维度 bge）改 env + 重启 + 触发 model_upgrade 回填新 provider 行 重启窗口秒级（design §3 Provider 切换路径表）
- [P1] provider 切换不同维度（OpenAI 1536 → bge-small-zh 512）异维列拆分支持 新行写新列旧 1536 列 30 天宽限保留回滚（design §3 Provider 切换路径表 fix v2 改进）
- [P1] 双 provider 并行 schema 物理支持 PK 多行共存但 EmbeddingProvider 抽象仅单 instance 演进退路见 R3 E6（design §3 Provider 切换 + audit R3）
- [P2] OpenAI 旧 embedding 30 天宽限保留 回滚改 env EMBEDDING_MODEL_NAME 回旧 model 立即恢复参与召回无需重算（design §4 回滚场景）

### 11. 跨模块依赖

- [P0] M03/M04/M06/M07 各加 get_for_embedding(target_id, project_id) -> str Service 接口 增量 worker 调用（design §1 baseline-patch + §6 §9 规则 1）
- [P0] M03/M04/M06/M07 各加 search_by_keyword(query, project_id, limit) Service 接口（M09 batch3 沉淀）M18 复用关键词路径（design §1 + §9 规则 1）
- [P0] M03/M04/M06/M07 delete_by_id Service commit 后调 enqueue_delete 异步清理 audit B1 + C2=A 决策（design §9 删除策略 + baseline-patch 修订）
- [P0] M02 ProjectSettings 加 rrf_k + similarity_threshold 字段 SearchService 入口取 project 级参数（design §1 Q6=C + baseline-patch M02）
- [P0] M15 ActionType 加 EMBEDDING_MODEL_UPGRADE_TRIGGERED + EMBEDDING_BACKFILL_TRIGGERED 2 个枚举值（design §10 baseline-patch M15）
- [P0] M09 status=superseded_by=M18 + 文档归档 + 不删除 search_by_keyword 接口体系 M18 复用（design §1 边界灰区 + baseline-patch M09）
- [P0] ADR-003 扩规则 4 全文 M18 accepted 时与 ADR-003 修订同步生效 embedding/索引派生模块批量 backfill 豁免（design §9 规则 4 audit B3 修复）
- [P1] EmbeddingService 横切归属 horizontal helper owner=M18 位置在 api/services/ 禁止挂业务模块名下（design §6 [horizontal, owner=M18]）
- [P1] EmbeddingProvider 横切归属 horizontal helper owner=M18 仿 ADR-001 §4 LLM provider 抽象（design §6 + ADR-001）
- [P1] M14 industry_news 全局无 project_id 不接入 M18 自己在"行业动态"页内搜避免跨域权限混乱（design §1 边界灰区 + tests.md boundary_08）
- [P1] M11 batch_create_in_transaction 路径 enqueued_by="batch_import" 第 4 枚举值走 backfill 模式不走单条 enqueue（design audit M3 + §15 未完成项）
- [P2] M16 §12B fire-and-forget AI 快照 vs M18 §12D 被动派生 用户感知边界不同（design §1 边界灰区 + §12D 与 §12A/B/C 对比）

### 12. 配置 / 部署

- [P0] EMBEDDING_PROVIDER env 部署期固定三选一 openai/bge/mock 启动 EmbeddingProvider 抽象层按 env 加载（design §6 env 表 + Provider 切换）
- [P0] EMBEDDING_MODEL_NAME env provider-level 模型名（如 text-embedding-3-small）+ mock provider 必须 'mock-*' 前缀 startup sanity check 强制（design §6 env 表 + fix v4.2 R2=A）
- [P0] EMBEDDING_MODEL_VERSION env product-level 业务版本号（如 v1）与 model_name 拆分（design §6 env 表 fix v4.1 R5'=B）
- [P0] 模型升级 CY 必须同时改 EMBEDDING_PROVIDER + EMBEDDING_MODEL_NAME + EMBEDDING_MODEL_VERSION 三个 env 漏 NAME 会导致 sanity check fallback 全表（design §12D 字段⑦ fix v4.2 verify O7）
- [P1] IVFFLAT_LISTS=100 env 配置 演进锚点行数 > 50 万 调到 sqrt(N)~700 不写死 ORM Index audit M9（design §6 env 表）
- [P1] EMBEDDING_FAILURE_THRESHOLD_ABS=500 / PCT=5 / PER_PROJECT=100 三维独立阈值 任一超过告警 CY 避免单维死参数（design §6 env 表 + §12D 字段⑥ M10）
- [P1] SEARCH_EVAL_SAMPLE_RATE=0.01 search 路由 1% 采样写 search_evaluation_log M13 离线评估（design §6 env 表 + §3 自有表 4）
- [P1] arq Redis AOF appendonly=yes 必开启 第一道保险 worker 重启 task 不丢 detect_and_resume 是第二道保险（design §12D Backfill 中断恢复 + ADR-001 §基础设施）
- [P2] FastAPI lifespan startup 钩子调一次 detect_and_resume_pending_backfill 防 cron 第一次 fire 前丢残留（design §6 Lifespan 行 + fix v4.1）

### 13. 演进 / 半衰期

- [P2] §12D 子模板 2026-10-25 半年回看若仅 M18 一个实例使用且与 §12C 字段⑥/⑦ 高度重合 评估降级为 §12C 扩展段落删 §12D 行（design §12 未来后果触发器 + audit R5）
- [P2] 双 provider 并行需求出现时 §6 EmbeddingProvider 抽象升级 ProviderRegistry 演进退路 audit R3 E6（design §3 Provider 切换 + §15 演进锚点）
- [P2] 多 modality（图片/音频）模块引入时评估 §12D 字段⑦ N/A 声明 audit C1=B opt-in 决策（design §12D 字段⑦ + §15 演进锚点）
- [P2] search_evaluation_log 1 年后离线分析 RRF k=60 vs k=80 / cache hit ratio / matched_by 路径占比 PRD F18 质量评估补盲（design §3 自有表 4 + §15 演进锚点 audit M13）
- [P2] embedding_failures 表 fix v4.2 加的 provider+model_name 字段本期 monitor cron 暂不分桶 留作 Phase 2 监控扩展用（design §15 cron 矩阵 V1 死字段备注 + audit fix v4.3）

