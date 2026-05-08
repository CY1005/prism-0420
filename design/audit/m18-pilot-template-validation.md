---
title: M18 sprint pilot-template-validation（living tracker）
status: in-progress
owner: CY
sprint: M18 语义搜索 / pgvector / §12D embedding 持久化首战
started: 2026-05-09
purpose: |
  M18 §12D 子模板首次实战 sprint 实证记录。本文件记 M18 启动期 + 子片 0-5 实施期产出
  + R1=3 subagent 并行 + R2=1 合并 Opus 单审命中数据 + 元教训沉淀 + sink 立规候选。
---

# M18 sprint pilot-template-validation

## M18 启动期（2026-05-09 / 详见 design/audit/m18-startup-reconcile.md）

启动期 4 大必做项 + 闸门 2.5 reconcile pass 三栏 A 8 / B 0（第十三次实证）/ C 6 已自我消解。

- M02 ProjectSettings.rrf_k+similarity_threshold baseline-patch 历史 DONE
- pgvector image 历史 DONE / CREATE EXTENSION 留子片 1 alembic
- ActionType+2 baseline-patch 历史 DONE / TargetType+0（复用 project / design §10 line 842 字面）
- ADR-003 规则 4 历史 accepted
- M18 design fix v4.3 grep verify F1-F4+V2+V3 全清 → status: draft → accepted ✅
- M18 design §14.5 Sprint Review 拆分计划补完
- M17 bypass log #2 配套验收 ✅（M18 必继 R1=3+R2=1 不复位）

---

## M18 sprint 实施（2026-05-09 / 9 commits）

| # | commit | 子片 | 范围 | tests | R13-1 |
|---|--------|------|------|-------|-------|
| 1 | 90f7672 | 启动期 | design status flip + reconcile + bypass log #2 配套验收 | 1213 baseline | 124 |
| 2 | 6c27898 | 子片 0 prep | EmbeddingProvider mini-sprint（abstract+Mock+factory+41 tests） | 1254 (+41) | 124 |
| 3 | fbea749 | 子片 1 | 4 表 model + alembic + 54 model tests + pgvector ARRAY 占位 | 1308 (+54) | 124 |
| 4 | c7aca1f | 子片 2 | 5 DAO（含规则 4 豁免）+ 45 unit tests + 2 conftest fixtures | 1353 (+45) | 124 |
| 5 | f2da4e2 | 子片 3 | Service+Schema+12 ErrorCode+Queue+Cron+Provider stub+92 tests | 1445 (+92) | 136 (+12) |
| 6 | 76c6d9b | R1 立修 | 16 P1（3 subagent 并行审 / Opus + 2 Sonnet 合并去重） | 1447 (+2) | 136 |
| 7 | 68e981e | 子片 4 | Router 1 search + 3 admin endpoints + 42 e2e（元教训 18 类全覆盖） | 1489 (+42) | 136 |
| 8 | 92e09d3 | R2 立修 | 7 P1+P2（1 合并 Opus endpoint 单审）+ 1 PUNT | 1480 (-9 删虚假占位) | 136 |
| 9 | TBD | 子片 5 关闸 | design 回写 + audit + handoff + roadmap + cross-sprint punt 池 + M19 prompt | ≈1480 | 136 |

**最终回归**：1213 → ≈1480 PASS（+267 / 5 skipped / R13-1 124→136 / L12+L13+R14 全过 / ruff 净）

---

## R1+R2 命中数据（M02-M18 第十六数据点 / bypass log #2 配套验收）

### R1 = 3 subagent 并行审子片 1+2+3（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）

- **R1-A spec+quality Opus**：13 P1 + 11 P2 / **关键**：源头 source_text 占位 garbage / debounce 命中丢编辑 / TaskPayload 误用 Response（首次抓 / 其他 subagent 同款）
- **R1-B reuse Sonnet**：2 P1 + 4 P2 / **关键**：test_m18_dao 重复造 helper 不复用 conftest fixture / Response 错误继承 TaskPayload
- **R1-C quality+efficiency Sonnet**：5 P1 + 5 P2 / **关键**：worker 缺 asyncio.timeout（zombie 泄露）/ enqueue create() 未 catch IntegrityError（清单 6 守护）/ OpenAI api_key 从 env 直取（违反 M13 ProjectSettings AES 范式）

合并去重：20 项 → 16 立修 + 4 punt（R1-A P1-2 design 字面已锁 / P1-3 worker source_text 留子片 4 真接 / P1-4 caller commit 后语义实际无 bug / P1-11 noop 标记 design 未明示）

### R2 = 1 合并 Opus subagent endpoint 单审子片 4

- 5 P1 + 7 P2 = 12 项 / 立修 7 + punt 5
- **R2 真漏抓贡献**：
  1. BackfillRequest/ModelUpgradeRequest 继承 TaskPayload（R1-A P1-6 仅抓 Response 端 / R2 endpoint 单审独家命中 Request 端）
  2. require_platform_admin 重复定义（dependencies.py Protocol 版 vs router 内联 current_user 版 / 测试架构不兼容 PUNT 子片 5+）
  3. metadata affected_count=0 占位写 activity_log 假数据（design §10 字面 metadata 是真值 / 加 _stub: True 标记）
  4. query 200 char design 字面 400 vs 实施 422 分叉（双向违反 design §7 line 663 / 改 router 手动 check 抛 400）
  5. TestIntegrityErrorCatch 9 处虚假占位测试（assert in (202,500) 永真 / TestNAExplicit assert True 占位 9 处 / 删比假覆盖诚实）

---

## 元贡献清单（M18 sprint 实施期 7+ 项 sink）

### 1. §12D 子模板首次实战零摩擦验证

- 7 字段 PK + 异维列拆分 + 三段（provider, model_name, model_version）回填 + 双触发链 + 跨模读双路豁免 + failure 容忍 + cron 矩阵：design 全部 7 字段实装一次过
- README §12 表加 §12D 行 + 2026-10-25 复用度复盘触发器（OpenClaw cron 挂提醒）

### 2. R-X4（pgvector）未装库占位三层范式

- 子片 1 model 异维列用 ARRAY(Float) 占位 + ivfflat 索引注释保留
- 子片 2 vector_search NotImplementedError 占位
- 子片 3 SearchService.hybrid_search 走 keyword_only 降级（PRD AC4 字面 / search_mode="keyword_only" + 200 不报错）
- 子片 4+ 真装 pgvector 后回写：ARRAY → Vector / 解锁 ivfflat / vector_search 真实施 / 子片 4+ 范畴

### 3. EmbeddingProvider 抽象仿 ADR-001 §4.1 LLMProvider 范式

- abstract base + 异常族（Error/Timeout/Config）+ Mock 确定性 sha256-seeded L2 归一化 + factory
- 子片 0 prep mini-sprint scaffold 简化决策 4 字段注释（OpenAI/bge 真实装留子片 3+；M13 ClaudeProvider integration smoke 范式延续）

### 4. SilentFailure 占位期降级范式（fix v2 决策 3=B 实证）

- design line 1269-1286 字面 SilentFailure(BaseException) 严格使用约束（业务 except SilentFailure 显式 / 不能 except Exception 捕获 / 不能跨 HTTP 边界）
- 占位期 enqueue_delete 同步直删失败 → logger.warning 降级（不 raise SilentFailure）；子片 4+ 接 arq 异步后启用 SilentFailure 语义 / R1-A P1-5 抓 + 立修

### 5. R1 = 3 subagent 并行 + R2 = 1 合并 Opus endpoint 单审 16 数据点稳定

- M02-M18 sixteen 数据点 R1+R2 命中比例稳态：R1 命中数 8-13 P1 / R2 命中数 4-5 P1（R-X1+R-X2+异维列等 pilot 模块为 R2 多命中区域）
- bypass log #2 配套不复位实证：M16 bypass + M17 恢复 spawn + M18 继续 spawn = 累计 2 次 bypass / 第 3 次 bypass 触发对闸门 3.4 L1 总则 review

### 6. R10-2 例外应用第二实例（embedding_failures 表）

- M01 auth_audit_log 第一实例 + M18 embedding_failures 第二实例 / 三条件验证表 design §10 line 845-859 字面
- 系统行为 vs 业务行为分类对齐（audit M7 修订 / 非"用户主动操作"语义）

### 7. 元教训防御 actionable 主动复制 18 类完整实证

子片 4 e2e 17+ 项 actionable 主动复制 + N/A 显式声明 7 项 = 18 类完整覆盖（design §14.5 字面）。
分类：12 主动复制（write 403 / read 403 / write_event 异常传播 / cross-tenant / cross-project / IntegrityError 等）+ 7 N/A 显式（R-X1 / multipart / SSE / CAS / compensation_session / idempotency project_id / N/A 双重声明）

---

## R1+R2 sink 立规候选 4 项

### 1. **EndpointRequest schema 不应继承 TaskPayload 立规**（R2 #1 真漏抓）

- 立规：HTTP request body schema 仅继承 BaseModel；TaskPayload 严格仅供 Queue payload 继承（强制 user_id+project_id 来自 server enqueue 控制）
- ci-lint 守护候选：grep `class.*Request.*\(TaskPayload\)` 报警
- horizontal 化触发：M19+ 任何新 endpoint Request schema

### 2. **pgvector / 异维列占位三层降级范式立规**（M18 §12D 首发）

- 三层占位（model ARRAY / DAO NotImplementedError / Service keyword_only 降级）必同步标注 + 解锁触发条件字面
- 未来 vector / search / embedding 模块横切复用

### 3. **占位 metadata 必加 _stub: True 标记立规**（R2 #3）

- 任何 endpoint write_event metadata 含占位字段（如 affected_count=0）必加 `_stub: True` 防 activity_log 假数据污染历史排查
- 子片 N+ 真接业务路径时删 _stub 标记 + e2e assert affected_count > 0

### 4. **测试反模式立规：assert True / assert in (a, b) 永真不算覆盖**（R2 #11+#12）

- ci-lint 守护候选：grep `assert True\b` + 检测 `assert.*in (.*\d.*,.*\d.*)` 永真模式
- N/A 显式声明应在 design.md docstring 落 / pytest 不重复
- "PUNT" 注释标记 + 删测试比假覆盖诚实

---

## cross-sprint Punt 池接通

### 本 sprint 关闭

- **#7 R-X1 失败补偿 commit boundary** — M18 不触 R-X1 形态（design §14.5 N/A 显式声明）/ 留 punt 状态不变（M11 实例 + M17 第二实例已 DONE）

### 本 sprint 新增 5 punt

- **#20 require_platform_admin Protocol 版 vs current_user 版去重**（R2 #2）— PUNT_TO_SUBPIECE_5_OR_LATER：合并需 conftest set_auth_service fixture
- **#21 worker source_text 真接上游 Service.get_for_embedding**（R1-A P1-3）— 子片 4+ / 当前占位 garbage embedding；mock provider 测试不触发
- **#22 EmbeddingTaskInvalidTransitionError 等 noop 标记**（R1-A P1-11）— design 未明示 / P2 punt
- **#23 cron_failure_monitor PCT 维度真接 task_dao.count_completed_in_window**（R1-C P2-3 / R2 #7）— 占位期已加注释 + 子片 4+ 实施
- **#24 batch_backfill 真 batch INSERT INTO embedding_tasks SELECT FROM unnest(:ids)**（R1-C P1-4）— 占位期 N+1 / 子片 4+ 改批量 INSERT

### 触发点 A 4 项 STILL_PUNT 验证

- M04-1 (updated_by, updated_at) 联合索引未建 / M04-8 db.get(DimensionType) 3 处 / M04-9 target_type 5 处 hard-code / M04-10 race window — M18 不触 dimension_service / 推迟独立 cleanup sprint

---

## 半年回看触发器（2026-10-25）

- §12D 子模板复用度复盘（OpenClaw cron 挂提醒）
- 半年后若 §12D 仅 M18 一个实例 + §12C/§12D 字段⑥/⑦ 高度重合 → 评估降级为 §12C 扩展段落 + 删 §12D 行（防模板膨胀）
- M18 schema 演进锚点：embeddings 行数 > 50 万 → ivfflat lists reindex 评估 + 分区评估
- pgvector 真装 + OpenAI/bge 真接通的实施触发条件（子片 4+ 或下一 embedding sprint）
