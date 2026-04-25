---
title: M18 语义搜索 - 测试场景（§14）
status: draft
owner: CY
created: 2026-04-25
module_id: M18
related_design: ./00-design.md
---

# M18 测试场景（§14）

> 6 类必覆盖：Golden / 边界 / 并发 / Tenant / 权限 / 错误。
>
> **Pilot 6 §12D 首次实战**——双触发链 + 失败容忍 + 模型版本回填 + 跨模读双路豁免均需有专项 case。
>
> 命名约定：`tc_M18_<分类>_<序号>_<行为名>`

---

## 1. Golden 场景（核心正向流程）

### tc_M18_golden_01_增量路径成功（双触发链 - 增量）

**前提**：M03 NodeService 已接入 enqueue 调用；arq worker 运行；OpenAI 可用

**步骤**：
1. CY 在 project_X 调 `M03.create_node(name="配额管理")`
2. 节点 commit 成功
3. NodeService 尾调 `embedding_service.enqueue(target_type="node", target_id=node.id, project_id=project_X)`
4. Redis SET `embedding:debounce:project_X:node:{node.id}` 标记（TTL 60s）
5. arq Queue 收到 `EmbedSinglePayload`
6. worker 拉起 → advisory_xact_lock → 调 `NodeService.get_for_embedding` 拿 "配额管理" → 调 OpenAI embed → upsert embeddings 表

**期望**：
- embeddings 表新增 1 行 `(project_X, node, node.id, current_model_version)`
- embedding 维度 = 1536（OpenAI default）
- content_hash 非空
- embedding_tasks 表新增 1 行 status=succeeded
- 60s 后 Redis SET key 自动过期

---

### tc_M18_golden_02_backfill 路径成功（双触发链 - backfill）

**前提**：embeddings 表已有 100 行（cur_model）；100 行 nodes 写入时未触发增量（模拟历史数据）

**步骤**：
1. platform_admin 调 `POST /api/admin/embedding/backfill`
2. 端点检查无并发 backfill 在跑（防 EMBEDDING_BACKFILL_ALREADY_RUNNING）
3. EmbeddingBackfillDAO（规则 4 豁免）跑批量 SELECT：`SELECT n.id FROM nodes n LEFT JOIN embeddings e ON ... WHERE e.target_id IS NULL AND n.project_id=...`
4. 找出 100 个待补 node_id
5. 按 project 分批 enqueue（enqueued_by="backfill"）
6. worker 逐个跑（同 increment 路径合流）

**期望**：
- 100 个 task 全部 succeeded
- embeddings 表 +100 行
- 已有 100 行（与 backfill 触发的 node 不重叠）不动
- embedding_tasks.enqueued_by="backfill"
- 端点返回 202 Accepted + estimated_duration_seconds

---

### tc_M18_golden_03_混合搜索关键词+语义双命中（PRD AC1+AC2+AC3）

**前提**：project_X 有 3 条数据：
- node_A: "配额管理"（关键词 + 语义命中）
- node_B: "额度限制策略"（仅语义命中——内容相关但无字面词）
- node_C: "用户登录"（不命中）

均已有 embedding（current_model）

**步骤**：
1. CY 搜 query="配额"
2. M18 search 路由：
   - 关键词路径：`SearchService` 调 `NodeService.search_by_keyword(db, "配额", project_X, limit=20)` → 返回 [node_A]
   - 语义路径：调 OpenAI embed("配额") → 缓存 miss → ivfflat 召回 + WHERE project_id=project_X AND model_version=current → 返回 [node_A(0.85), node_B(0.62)]（>0.3 阈值）
   - RRF 融合（k=60）：node_A score 高（双命中）/ node_B score 低（仅语义）

**期望**：
- 结果列表：[node_A, node_B]，node_A 在前
- node_A.matched_by = ["keyword", "semantic"]
- node_B.matched_by = ["semantic"]
- node_C 不在结果
- search_mode = "hybrid"
- query_embedding_cached = false（首次）

---

### tc_M18_golden_04_query embedding 缓存命中（Q4=C）

**前提**：tc_03 刚跑过，Redis 缓存有 "配额"+current_model→vector

**步骤**：
1. CY 5min 内再搜 query="配额"
2. EmbeddingService.embed_query：Redis HIT
3. 走向量路径无需调 OpenAI

**期望**：
- query_embedding_cached = true
- 总响应时间 < 200ms（cache 命中没 OpenAI 200ms）

---

### tc_M18_golden_05_模型升级回填路径（Q3=A + §12D ⑦）

**前提**：embeddings 表 5 万行（model_version=`text-embedding-3-small`）；env 改为 `DEFAULT_EMBEDDING_MODEL=text-embedding-4`；服务重启

**步骤**：
1. platform_admin 调 `POST /api/admin/embedding/model-upgrade`
2. 端点扫所有 `embeddings WHERE model_version != current_model`（5 万行）
3. 按 project 分批 enqueue（enqueued_by="model_upgrade"）
4. worker 用新 model 算 + 写入新行（PK 含 model_version 物理共存）
5. 回填期间 search 路由按 `current_model=text-embedding-4` filter，旧 embedding 不参与召回但保留
6. 30 天后 cron 扫 `model_version != current AND created_at < NOW-30d` → 物理删除旧行

**期望**：
- 回填中 embeddings 表行数从 5 万 → 10 万（新旧共存）
- 回填期间 search 仍可用（仅命中 5 万新 embedding）
- 30 天后行数回落 5 万
- activity_log 写入 1 条 `EMBEDDING_MODEL_UPGRADE_TRIGGERED`（target_type=project）

---

### tc_M18_golden_06_RRF 项目级参数生效（Q6=C + baseline-patch 决策 2）

**前提**：project_X 配置 `rrf_k=60, similarity_threshold=0.3`；project_Y 配置 `rrf_k=80, similarity_threshold=0.5`

**步骤**：
1. admin 在 project_Y UI 改 similarity_threshold=0.5
2. 同 query 在 project_X 和 project_Y 各搜一次
3. project_Y 的语义召回中相似度 0.4 的结果被过滤（阈值 0.5）

**期望**：
- project_X 返回相似度 ≥0.3 的结果
- project_Y 返回相似度 ≥0.5 的结果
- viewer 用户**无 UI 入口**改 RRF 参数（决策 2，权限模型）

---

## 2. 边界场景

### tc_M18_boundary_01_query 空字符串

**步骤**：CY 搜 query=""

**期望**：返 400 / `INVALID_QUERY_LENGTH`（Pydantic min_length=1）

---

### tc_M18_boundary_02_query 200 字符（上限）

**步骤**：CY 搜 query="a" * 200

**期望**：通过校验，正常搜索

---

### tc_M18_boundary_03_query 201 字符（超上限）

**步骤**：CY 搜 query="a" * 201

**期望**：返 400 / `INVALID_QUERY_LENGTH`

---

### tc_M18_boundary_04_pgvector 不可用降级（PRD AC4）

**前提**：FastAPI 启动时探测 `CREATE EXTENSION vector` 不可用（模拟）

**步骤**：
1. CY 搜 query="配额"
2. SearchService 检测 `is_pgvector_available()=false`
3. 仅走关键词路径 + skip 向量路径

**期望**：
- 返 200 + `search_mode="keyword_only"`
- 结果仅含关键词命中
- 同时写一条 embedding_failures `error_code=PGVECTOR_UNAVAILABLE`（每小时去重 1 条，不刷屏）

---

### tc_M18_boundary_05_OpenAI 超时降级 fallback

**前提**：mock OpenAI 返回延迟 5s（超过 search 路径 2s 超时）

**步骤**：
1. CY 搜 query="配额"
2. EmbeddingService.embed_query 触发 `asyncio.timeout(2)` → SearchTimeoutError
3. SearchService 捕获 → 降级为 keyword_only

**期望**：
- 返 200 + `search_mode="keyword_only"` + `query_embedding_cached=false`
- 不算 5xx（不影响 SLA）
- 写一条 embedding_failures `error_code=EMBEDDING_PROVIDER_TIMEOUT`

---

### tc_M18_boundary_06_业务表无 embedding 时搜索（fallback 自然）

**前提**：node_X 已写但 embedding 任务还在 pending（增量路径 enqueue 后未跑）

**步骤**：CY 立即搜 node_X 内容关键词

**期望**：
- 关键词路径命中（来自 NodeService.search_by_keyword）
- 语义路径不命中（embeddings 表无该行）
- node_X 出现在结果中（matched_by=["keyword"]）

---

### tc_M18_boundary_07_embedding 维度不匹配（切 provider 后未迁移）

**前提**：env 切 bge（512 维）但 Alembic 未跑（embeddings.embedding 仍 1536 维）

**步骤**：worker 跑增量 task 写入

**期望**：
- pgvector 报错 → AppError EmbeddingProviderFailedError
- 写 embedding_failures `error_code=EMBEDDING_PROVIDER_FAILED + error_message="vector dimension mismatch"`
- 重试 3 次仍失败 → dead_letter
- monitor cron 阈值告警 CY

---

### tc_M18_boundary_08_M14 不接入 search（边界灰区）

**步骤**：CY 搜 query="行业动态"

**期望**：
- M18 search 路由仅调 M03/M04/M06/M07，**不**调 M14.search_by_keyword
- M14 行业动态在自己的页内搜（M18 不接管）
- 结果不含 industry_news target_type

---

## 3. 并发场景

### tc_M18_concurrent_01_同一 target 5 次连续编辑（debounce 验证 - Q8=D）

**前提**：CY 60s 内 5 次调 `update_node(node_X, name="...")`

**步骤**：
1. 第 1 次 enqueue：Redis SET 标记成功，task 入队
2. 第 2-5 次 enqueue：Redis SET 已存在 → enqueue skip
3. 60s 后 Redis SET 过期，但此时 task 已跑完

**期望**：
- 仅 1 个 embedding task 入队
- 仅 1 次 OpenAI 调用
- 最终 embedding 是第 5 次更新后的内容（worker 跑时拿 latest）
- token 成本 = 1× 而非 5×

**反例验证**：如果第 5 次更新发生在第 1 次 task 跑完后（60s 外），则会再 enqueue 1 次（接受——避免 task 永不更新）

---

### tc_M18_concurrent_02_同一 target 跨 worker 并发（advisory lock）

**前提**：debounce 已过期；2 个 worker 同时拿到同 (target_id) 的 task（罕见但可能）

**步骤**：
1. worker_A 入口：`pg_advisory_xact_lock(hashtext(target_id))` → 成功
2. worker_B 入口：同 lock → 等待
3. worker_A 调 OpenAI + 写 embedding + commit → lock 释放
4. worker_B 拿到 lock → SELECT 已有 embedding → content_hash 比对
5. 若 hash 相同 → skip OpenAI 调用（兜底去重）
6. 若 hash 不同 → 重算（说明 2 个 task 间内容已变）

**期望**：
- 不会出现"两个 worker 同时调 OpenAI 写同一行"
- 总 OpenAI 调用 = 1 次（content 未变）or 2 次（content 变了，正确语义）

---

### tc_M18_concurrent_03_backfill 与增量 worker 并发

**前提**：cron 跑 backfill 入队 100 个 task；同时 CY 增量编辑 1 个 node

**步骤**：
1. backfill enqueue 100 task
2. 增量 enqueue 1 task（同 target_id 在 backfill 列表中）
3. 任一 worker 先跑：advisory_xact_lock 互斥
4. 后跑的 worker：content_hash 比对 → skip

**期望**：
- embeddings 行最终一致（无重复无丢失）
- 总 OpenAI 调用 = 100 次（增量被去重）

---

### tc_M18_concurrent_04_search 时 embedding 正在重算（model_version 切换瞬间）

**前提**：env 已切新 model 但 backfill 进行中（5 万旧 + 1 万新已写）

**步骤**：CY 此时搜索

**期望**：
- search 按 `current_model_version` filter → 只命中 1 万新 embedding
- 关键词路径仍全量召回
- 结果可能"语义召回少"但不出错（PRD AC4 精神：不阻塞用户）
- search_mode 仍 "hybrid"

---

### tc_M18_concurrent_05_3 用户同时搜同一 query（cache 验证）

**前提**：缓存空

**步骤**：用户 A/B/C 同时搜 query="配额"（同一秒）

**期望**：
- 第一个到达的 worker 调 OpenAI + 写缓存
- 后两个有可能：(a) 等待第一个写完后命中缓存 / (b) 同时调 OpenAI（缓存竞态）
- 验收：调用次数 ≤ 3，**不验收必须 = 1**（race condition 不阻塞，仅成本影响）
- 后续 5min 内同 query 命中缓存

---

## 4. Tenant 场景

### tc_M18_tenant_01_跨 project 不召回（Q5=B + Q9=B 核心）

**前提**：
- project_X: node_A 内容"配额管理"，已有 embedding
- project_Y: node_B 内容"配额管理"，已有 embedding
- user_1 仅 project_X 成员

**步骤**：user_1 在 project_X 搜 query="配额"

**期望**：
- 仅返回 node_A
- node_B 完全不出现（关键词路径上游 search_by_keyword 已 filter；向量路径 SQL `WHERE project_id=project_X` filter）
- 即使 node_B embedding 余弦相似度更高也不返回

---

### tc_M18_tenant_02_project 删除 CASCADE 清理

**前提**：project_X 有 1000 条 embedding + 200 条 embedding_failures + 50 条 embedding_tasks

**步骤**：CY 软删 project_X（与 M02 行为一致 deletedAt）

**期望**（取决于 M02 是软删还是硬删）：
- 软删：embeddings 表不动（M02 deletedAt 软删）；search 路由按 `accessible_project_ids` 过滤掉已软删 project
- 硬删（极端）：DB FK ondelete='CASCADE' 自动清理三表所有 project_X 行

**测试 backup**：admin 触发硬删 → 验证三表对应行被清空

---

### tc_M18_tenant_03_Queue payload 串 project_id 被反查抓出（防 enqueue bug）

**前提**：mock 一个 bug，调 `enqueue(project_id=project_Y, target_type="node", target_id=project_X_node_id)`（target 实际归 project_X）

**步骤**：worker 入口 `embedding_service.check_payload_consistency` 反查业务表 → 发现 node.project_id=project_X != payload.project_id=project_Y

**期望**：
- task 直接 `failed` + error_code=`EMBEDDING_PROVIDER_FAILED + tenant mismatch`
- 写 embedding_failures
- 不写 embedding（防跨租户污染）
- monitor cron 抓出告警 CY（疑似 bug）

---

### tc_M18_tenant_04_M02 RRF 参数严格按 project 取（决策 2）

**前提**：project_X rrf_k=60；project_Y rrf_k=80

**步骤**：
1. user 在 project_X 搜 → SearchService 调 `ProjectService.get_search_config(project_X)` → rrf_k=60
2. 同 user 切到 project_Y 搜 → 取 rrf_k=80

**期望**：
- 两次 RRF 融合参数不同
- 结果差异可观测（同 query 不同排名）

---

## 5. 权限场景

### tc_M18_perm_01_未登录 search 返 401

**步骤**：无 Bearer token 调 `POST /api/projects/{pid}/search`

**期望**：401 / `UNAUTHORIZED`（来自 require_user 依赖）

---

### tc_M18_perm_02_跨 project search 返 403

**前提**：user_1 仅 project_X 成员

**步骤**：user_1 调 `POST /api/projects/project_Y/search`（pid 是 project_Y）

**期望**：403 / `PROJECT_FORBIDDEN`（SearchService.check_project_access 抓出）

---

### tc_M18_perm_03_admin endpoint 非 platform_admin 返 403

**前提**：user_1 是 project admin 但不是 platform_admin

**步骤**：user_1 调 `POST /api/admin/embedding/backfill`

**期望**：403（require_platform_admin 抓出）

---

### tc_M18_perm_04_RRF 参数 viewer 无入口（决策 2）

**前提**：user_1 是 project_X viewer

**步骤**：
1. user_1 打开 M02 项目设置页
2. UI 不渲染 rrf_k / similarity_threshold 输入框
3. 即使 user_1 直接 POST `/api/projects/project_X/settings` 携带 rrf_k=80 也被拒

**期望**：
- UI 隐藏（决策 2 前端实现）
- 后端 Server Action `assertProjectRole(project_X, "admin")` 抛 ForbiddenError

---

### tc_M18_perm_05_Queue 消费者 payload tenant 校验（ADR-002）

**前提**：mock 恶意 payload `EmbedSinglePayload(user_id=evil_user, project_id=project_X, target_id=...)` 直接塞 Queue

**步骤**：worker 入口 `payload = parse_obj` → `service.check_payload_consistency` 反查业务表 + 验 user 与 project 关系

**期望**：
- check_payload_consistency 抛 → task failed
- 不写 embedding
- 写 embedding_failures（按 ADR-002 + §8 L4）

---

### tc_M18_perm_06_R10-2 例外条件 3（系统级事件验证）

**步骤**：触发 embedding 失败

**期望**：
- 写 `embedding_failures` 表（M18 own）
- **不**写 M15 activity_log（条件 3：系统级，无用户主动操作语义）
- 验证 R10-2 文字修订（baseline-patch 改动）后 M01 auth_audit_log 仍合规

---

## 6. 错误场景

### tc_M18_error_01_worker 失败 3 次写 failures + 死信

**前提**：mock OpenAI 持续 503

**步骤**：
1. worker 跑 task → 失败 → 重试 1s
2. 重试 → 失败 → 重试 4s
3. 重试 → 失败 → 重试 16s
4. 第 4 次失败 → task `status=failed` + 写一条 embedding_failures
5. 30s 后 cron 转 `status=dead_letter`

**期望**：
- embedding_failures 1 行 (error_code=EMBEDDING_PROVIDER_FAILED)
- embedding_tasks status=dead_letter
- **不通知用户**（CY ack: Q7=C 容忍）
- 90 天后 cron 物理删除 dead_letter task

---

### tc_M18_error_02_monitor cron 阈值告警

**前提**：mock 一小时内有 100 个 enqueue + 6 个失败（>5% 阈值）

**步骤**：monitor cron 跑 `SELECT COUNT(*) FROM embedding_failures WHERE failed_at > NOW() - INTERVAL '1 hour'`

**期望**：
- 计数 6
- 6/100 = 6% > 5% 阈值
- 触发告警通道（webhook / email / log——本期日志足够）
- 告警内容含 project_id 分布 + error_code 聚合

---

### tc_M18_error_03_zombie cron 转 failed

**前提**：mock worker 进程被 kill（或 OOM）后 task 永远 status=running

**步骤**：
1. task 入 running 状态 + created_at = NOW()
2. 经过 2min（M18 单 task 60s 超时 + commit buffer 60s）
3. zombie cron 跑（每 5min）扫 `status='running' AND created_at < NOW - 2min`
4. CAS UPDATE → status=`failed` + error_code=`EMBEDDING_ZOMBIE`

**期望**：
- 单条 CAS UPDATE 不与正常 worker 双写
- 用户感知失败延迟 ≤ 5min cron 间隔 + 2min 阈值 = 7min（与 M16 §12B 字段⑦同思想）

---

### tc_M18_error_04_业务表已删 noop（EMBEDDING_TARGET_NOT_FOUND）

**前提**：node_X 已删，但 embedding task 仍在队列（debounce 未过期时被入队，删除前已 enqueue）

**步骤**：
1. worker 入口反查 NodeService.get_for_embedding(node_X) → 返回 None
2. AppError `EmbeddingTargetNotFoundError` 被捕获

**期望**：
- task 直接 succeeded（noop）+ 不算失败（不写 embedding_failures）
- 不重试（target 已删，重试无意义）

---

### tc_M18_error_05_embedding_service.delete_by_target 失败不阻塞业务删除（决策 5）

**前提**：mock embedding DB 不可用

**步骤**：
1. CY 调 `M03.delete_node(node_X)`
2. 事务内：dao.delete_by_id 成功 → activity_log 写入成功
3. 尾调 `embedding_service.delete_by_target` 抛 DB error
4. NodeService 捕获 → logger.error + 写 embedding_failures `EMBEDDING_DELETE_FAILED`
5. 主事务 commit 成功（业务删除完成）

**期望**：
- 节点删除成功
- 用户感知正常
- embedding 行残留（孤儿 embedding） + 1 行 embedding_failures
- 后续：M18 zombie/cleanup cron 扫"target 不在业务表的 embedding 行" → 物理删除（90 天宽限）

---

### tc_M18_error_06_backfill 并发触发（防 EMBEDDING_BACKFILL_ALREADY_RUNNING）

**前提**：admin 已触发一次 backfill 在跑

**步骤**：admin 再次调 `POST /api/admin/embedding/backfill`

**期望**：
- 返 409 / `EMBEDDING_BACKFILL_ALREADY_RUNNING`
- 不重复入队

---

### tc_M18_error_07_切到不存在的 model（model_upgrade 验证）

**前提**：env 改 `DEFAULT_EMBEDDING_MODEL=text-embedding-foo`（不存在）

**步骤**：
1. 服务启动时 EmbeddingProvider 抽象层尝试初始化失败 → 启动报错
2. （或 admin 调 model-upgrade 端点提交不存在的 model）

**期望**：
- 启动失败明示报错 `EMBEDDING_MODEL_UPGRADE_INVALID`（启动阶段就拦住）
- 不允许进入运行态产生脏数据

---

### tc_M18_error_08_search 路由总超时

**前提**：mock 关键词路径上游 Service 卡 5s

**步骤**：CY 搜 query

**期望**：
- 路径触发 `asyncio.timeout` → `SearchTimeoutError`
- 返 504 / `SEARCH_TIMEOUT`
- 不挂搜索 SLA：search 路由本身有顶层超时保护

---

## 6.5 audit M8 补漏 case（4 项）

### tc_M18_recovery_01_backfill 中断恢复（audit M8 #1）

**前提**：admin 触发 backfill 入队 5000 task，跑到 2500 时服务重启（OOM / 主动 kill）

**步骤**：
1. backfill 跑前在 `embedding_tasks` 写一行 `enqueued_by="backfill"` 标识批次（或专用 backfill_run 表）
2. 服务重启 → 启动时 backfill cron 检测"上次 backfill 未完成"（有 status=pending 且 enqueued_by="backfill" 的 task）
3. cron 不重新扫差异 enqueue（避免重复），仅触发 worker 继续消费 Queue 中残留 task
4. arq Queue 持久化（Redis AOF）保证 task 不丢

**期望**：
- 重启后剩余 2500 task 自然继续跑
- 不重复 enqueue 已 succeeded 的 2500 task
- 总 OpenAI 调用 = 5000 次（不是 7500）
- 启动 logger.info "resumed backfill, 2500 pending"

---

### tc_M18_concurrent_06_RRF 参数 update 时正在 search 的 race（audit M8 #2）

**前提**：admin 此刻发起改 project_X rrf_k 60→80

**步骤**：
1. admin 调 PATCH /api/projects/{pid}/settings rrf_k=80
2. 同时 user 在 project_X 搜索（已经在 SearchService 内读了 rrf_k=60 准备融合）
3. admin 的 update commit
4. user 的 search 用 rrf_k=60 完成融合返回

**期望**：
- 不报错（read-after-write 一致性允许临时 stale read）
- user 此次结果用旧 rrf_k=60（acceptable）
- 下次 search 用新 rrf_k=80
- **明示契约**：M18 不保证 RRF 参数 update 后立即生效，**最长 stale 窗口 = 单次 search 路径耗时 ≤ 3s**

---

### tc_M18_consistency_01_RAW 一致性契约明示（audit M8 #3）

**前提**：CY 写一条新 dimension_record（增量 enqueue）

**步骤**：
1. write commit + enqueue
2. CY 立即（< 100ms）搜该内容关键词
3. 关键词路径命中（同步），返回结果

**期望（明示契约）**：
- ✅ 关键词路径**保证**立即可搜（同步路径）
- ❌ 语义路径**不保证** N 秒内可搜——embedding 异步计算，最长延迟 = enqueue debounce 60s + Queue 等待 + worker 处理（OpenAI 1-2s）+ commit = **典型 3-30s，最坏 15min（task 超时）**
- 用户体验：刚写的内容关键词搜得到，语义召回需等待几秒到分钟级
- **不写入文档/前端 UI 提示用户"等待"**——用户感知 fallback 到关键词路径已足够（Q7=C 容忍哲学）

**测试断言**：
- assert keyword_search_returns_new_record_within(100ms) == True
- assert semantic_search_returns_new_record_within(60s) **NOT** required（may or may not）

---

### tc_M18_provider_switch_01_mock 切换后已有 OpenAI embedding 处理（audit M8 #4）

**前提**：embeddings 表已有 5000 行 `provider='openai', model_version='v1'`，env 改 `EMBEDDING_PROVIDER=mock`

**步骤**：
1. 服务重启（部署期一次性切 provider，audit C3=C 决策）
2. M6 启动 sanity check：`EmbeddingService._validate_current_model_on_startup`
3. 检测 current=`('mock', 'v1')` 不在 `embeddings` 已有 distinct (provider, model_version) 集合中
4. logger.warning + 自动 fallback `_effective_model_for_search = ('openai', 'v1')`（latest）
5. CY 收到 warning 决定：(a) 触发 `model-upgrade` 端点回填 mock embedding / (b) 接受语义路径暂时用 OpenAI 已有 embedding

**期望**：
- 不出现"全 miss"（M6 fallback 抓住）
- search 仍可用（用 OpenAI 旧 embedding）
- CY 收到 warning 启动回填决策
- 回填完成后所有 embedding 都是 mock provider，OpenAI 旧行 30 天后 cron 清理

---

## 7. 测试覆盖矩阵

| §0-15 章节 | 覆盖 case |
|-----------|----------|
| §3 数据模型（4 字段 PK 含 model_version）| golden_05 模型升级共存 / boundary_07 维度不匹配 |
| §4 状态机 5 状态 | error_01 死信 / error_03 zombie / error_04 noop succeeded / error_05 delete 失败 |
| §5 4 维 | tenant_01 Tenant / concurrent_02 并发 advisory lock / golden_02 异步 backfill |
| §7 endpoints 4 个 | golden_03 search / golden_02 backfill / golden_05 model-upgrade / 隐式 stats |
| §8 三层 + L4 | perm_01-06 全覆盖 |
| §9 三类查询 + 规则 4 | golden_02 backfill DAO 规则 4 / tenant_01 search project filter / tenant_03 worker 反查 |
| §10 不写 activity_log + R10-2 | perm_06 系统级验证 / golden_05 + golden_02 写 admin 触发事件 |
| §11 三层幂等 | concurrent_01 debounce / concurrent_02 advisory lock / concurrent_03 hash |
| §12D 7 字段 | 字段① concurrent_01+golden_02 / 字段② golden_05 / 字段③ golden_02 / 字段④ perm_03+05 / 字段⑤ boundary_05+error_08 / 字段⑥ error_01+02 / 字段⑦ golden_05+error_03 |
| §13 ErrorCode | 全 12 个 ErrorCode 至少 1 case 触发 |

---

## 8. 测试实施约束

- **必须真实跑 OpenAI**（或 Mock provider，按 baseline-patch 决策 3 的 string 字段拼接走）—— 单元测试 mock，集成测试可跑 Mock provider 全链路
- **pgvector 测试需 Postgres 16 + extension 启用**（CI 环境约束）
- **arq Queue 集成测试需 Redis** —— 用 docker-compose 起测试环境
- **并发测试用 pytest-asyncio + asyncio.gather** 模拟多 worker
- **performance baseline**：5 万条 backfill 时长 ≤ 15min（验证规则 4 豁免性能收益）
- **audit m7 监控阈值**：tc_concurrent_05 cache 击穿率 > 30% 时引入 singleflight（Phase 2 实施观察）

---

## 9. 关联

- 主设计：[`./00-design.md`](./00-design.md)
- baseline-patch：[`../baseline-patch-m18.md`](../baseline-patch-m18.md)
- §12 子模板对照：M13 / M16 / M17 各自 tests.md
- 测试方法论：`design/06-design-principles.md`（如有）
