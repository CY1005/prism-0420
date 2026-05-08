---
title: M13 sprint 实证 + R1/R2 命中比例 + L1 第十一数据点（LLM 集成首发 + §12A SSE pilot + R-X3 写 M04）
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M13 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀（**LLM 集成首发 + 流式 SSE 子模板首次实战 + R-X3 写 M04**）。

  - 闸门 2.5 三栏：A 4 / B 0 / C 7（**第八次 B 栏 0 项**；M05+M06+M07+M08+M10+M11+M12+M13 八连稳定）
  - R1=3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet 共 12 P1 / 去重 8 P1 立修）
  - R2=1 合并 Opus subagent endpoint 单审（2 P1 + 1 P2 升 P1 + 1 P2 顺手）
  - L1+L2+L3 节奏第十一次实证 / M02-M13 默认范式作 M14+ 模板
  - LLM 集成首发新教训 4 条 sink（PEP 533 / Anthropic SSE delta.type / SSE generator DB session / metadata spec 字面）
last_reviewed_at: 2026-05-08
---

# M13 sprint 实证 + Review 命中比例

## 模块特性（与 M02-M12 对比）

| 维度 | M02-M08 业务 | M10 纯读 | M11 R-X1 | M12 R-X3 只读 | **M13 LLM + SSE pilot** |
|---|---|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅ | ✅ | ❌（R3-5 纯读聚合）|
| 调跨模块 service 写 | 偶尔 | ❌ | 4 batch_create | ❌ | **✅ M04.create_dimension_record** |
| 调跨模块 service 读 | 偶尔 | ❌ | 偶尔 | M04.batch_get | **M02 + M03 + M07 三上游全聚合** |
| 多表事务 | 偶尔 | N/A | 必须 | 必须 | N/A（save 单方法调）|
| 文件上传 | ❌ | ❌ | ✅ | ❌ | ❌ |
| 流式 SSE | ❌ | ❌ | ❌ | ❌ | **✅（首发 §12A pilot）** |
| LLM 集成 | ❌ | ❌ | ❌ | ❌ | **✅（首发 / Mock + Claude）** |
| AES 解密接通 | M02 own | ❌ | ❌ | ❌ | **✅（M02→AES→Registry→SDK 全链路）** |
| PEP 533 aclose 协议 | ❌ | ❌ | ❌ | ❌ | **✅（design §12 字段⑥ 强制）** |
| 失败补偿 | N/A | N/A | punt M17 | N/A | N/A |

---

## 闸门 2.5 reconcile 三栏（**第八次 B 栏 0 项**）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 4 | A1 §14.5 sprint review 计划段补（含 LLM/SSE 首发增强 R1+R2 必审范式）/ A2 DimensionService.create_dimension_record + get_latest 实装（M04 sprint scaffold "M13 sprint 期实装" 到期）/ A3 dimension_types upsert "requirement_analysis"（accepted 同期补丁 #1 一并落地）/ A4 元教训防御 actionable 6 主动复制 |
| **B 待 CY 决策** | **0** | （第八次 B 栏 0 项 / 八连稳定）|
| **C 已自我消解** | 7 | C1 R-X1 失败补偿 N/A / C2 文件上传 N/A / C3 queue payload N/A（design §12A 流式不持久）/ C4 R-X2 child service N/A / C5 IntegrityError 区分约束名 N/A（R3-5 无自有 unique）/ C6 真 SDK 范围已 CY 拍 Mock+Claude / C7 LLM hot path 4 数字+3 红线 N/A（user-triggered SSE 非 cron/scan）|

---

## R1 review 命中（3 subagent 并行 / 子片 0+1+2+3 合并审 / 共 12 P1 / 去重 8 P1 立修）

### R1-A spec+quality Opus 命中（5 P1 立修 + 8 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | design §10 line 559 字面 metadata.requirement_text_hash（SHA256 审计回溯锚点）→ 实装 requirement_text_length 语义不同 | **立修** commit eedecd1 加 hash 字段保留 length |
| P1-2 | _fetch_node_context 内 NodeService.breadcrumb 在 race 下抛 NodeNotFoundError 漏 wrap | **立修** 把 _fetch_node_context + _fetch_issue_context 包进同一 try / NodeNotFoundError → AnalysisNodeNotFoundError |
| P1-3 | ClaudeProvider 解析 SSE 漏 delta.type == 'text_delta' 校验（thinking_delta / input_json_delta / signature_delta 风险）| **立修** 加显式 delta.type 校验 + test_claude_skips_non_text_delta_types 4 类全验 |
| P1-4 | 缺 _fetch_node_context 异常路径覆盖测试（与 P1-2 绑定）| **立修** monkeypatch breadcrumb raise NodeNotFound 验 wrap |
| P1-5 | save_analysis except Exception 吞 ConflictError/DimensionDuplicateError | **立修** 显式 except 透传 409（M05 P1-01 元教训延续）|
| P2 8 项 | upsert race / smoke 模型名硬编码 / dead except / strict vs permissive ai_model / 防御性 UUID 解析 / token 预算 / StrEnum 字面 / reason 取值表 | punt 池 |

### R1-B reuse Sonnet 命中（3 P1 立修 + 3 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | _set_project_ai 跨模块 helper 内联 8 次（M16-ai-snapshot 必复用）| **立修** 迁 conftest 作 set_project_ai fixture（M03 R1-B C1 跨文件 helper 规则九连）|
| P1-02 | _make_proj_with_member + _add_member 内联 26 次 | **立修** 迁 conftest 作 make_project_with_member fixture |
| P1-03 | fake_httpx 套件迁 conftest（信心 B / M16 是否复用未知）| punt（M16 sprint 启动时再评估）|
| P2 3 项 | _ScriptedProvider / _patch_get_provider M13 专属内联合理 / AnalysisInvalidLevelError 死代码 | punt 池 |

### R1-C quality+efficiency Sonnet 命中（4 P1 立修 + 6 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | analyze_stream 漏 try/finally await stream.aclose()（资源泄漏）| **立修** 加 finally aclose；test_analyze_stream_propagates_aclose_to_inner_provider 用 MockProvider.aclose_called 断言协议传播 |
| P1-02 | except httpx.HTTPStatusError: raise 死代码 + httpx.NetworkError 是 RequestError 子类冗余 | **立修** 删 dead except + 简化为单 RequestError 捕获 |
| P1-03 | AffectedNodesResult.analysis_saved_at: str → datetime（与 Pydantic AffectedNodesResponse 类型一致）| **立修** service 层不再提前 isoformat |
| P1-04 | breadcrumb 重复 get_node 性能问题 punt（需改 M03 接口签名加可选 node 参数；跨模块层 punt 性能 sprint）| punt |
| P2 6 项 | upsert race / SSEErrorEvent.error_code Enum 约束 / save returns Any → DimensionRecord / N+1 / 防御性吞错 / Pydantic 严密性 | punt 池 |

**R1 P1 立修汇总（去重合并 8 项）**：commit `eedecd1`
- A1+A4 metadata hash + 测试断言
- A2+A4 _fetch_node_context wrap + race 测试
- A3 ClaudeProvider delta.type + 4 类 skip 测试
- A5 ConflictError/DimensionDuplicateError 透传 + 2 测试
- B1 set_project_ai 迁 conftest（8 次→1 fixture）
- B2 make_project_with_member 迁 conftest（26 次→1 fixture）
- C1 analyze_stream finally aclose + propagate 测试
- C2 删死代码（dead except + NetworkError 冗余）
- C3 AffectedNodesResult datetime 类型一致 + 测试

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 endpoint 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | SSE generator 内 AnalysisNodeNotFoundError + ProjectNotFoundError 落兜底 except → 错发 analysis_provider_error code | **立修** commit 79fb4cc 加显式 except 映射 analysis_node_not_found |
| P1-2 | SSE 端点缺 cross-project node 404 测试（元教训 4/6 / 3 端点全覆盖原则破例）| **立修** 加 test_stream_requirement_cross_project_node_returns_sse_error_event |
| P2-4 升 P1 | design §7 line 437 metadata 字面要求 analysis_time_ms 字段，router 漏注 | **立修** time.monotonic() 起止时间戳 + 测试断言 |
| P2-3 顺手 | analysis_time_ms=-1 e2e 缺 | 立补 test_save_analysis_pydantic_negative_time_ms_returns_422 |
| P2-1 | SSE generator 持 AsyncSession 长达 300s 占连接池 | punt（M16/M17 流式/异步统一立异步 SSE 连接策略）|
| P2-2 | 兜底 except 路径 P1 修后无测试覆盖 | punt（M14 sprint 顺手补）|

**R2 P1 处理**：commit `79fb4cc`
- P1-1 except (AnalysisNodeNotFoundError, ProjectNotFoundError) 映射 analysis_node_not_found
- P1-2 + P2-4 + P2-3 三测试合一 commit

**M13 R2 命中 4 项**（M02-M10 R2 P1 0-1 + M11 R-X1 首发 3 + M12 1 裁决型）→ 第十一数据点 R2 范式 LLM+SSE 首发命中合理；下个 LLM 模块（M16/M17）应能压到 1-2 P1。

---

## L1+L2+L3 节奏第十一次实证（**十一数据点稳定 → M14+ 默认范式作模板**）

| 层 | 内容 |
|---|---|
| L1 总则 | sprint ≥1 次 review + ≥50 行 OR ≥2 文件触发；触发例外条款全合规 |
| L2 sprint 计划 | design §14.5 sprint review 拆分计划段（commit 73c7175 子片 0 prep 落地 / LLM/SSE 首发增强）|
| L3 实证回写 | 本文件 |

**M13 默认范式（M02-M12 复用 + LLM/SSE 首发增强）**：
- R1 = 3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
- R2 = 1 合并 Opus subagent endpoint 单审
- 子片 5 不单跑（≥80% SKIP 例外）
- M13 schema 子片合并到 R1（≥80% SKIP）
- LLM 集成首发增强：R1 必审 PEP 533 aclose / R2 必审 SSE 流式特化（chunk 顺序 + AbortController + aclose 调用断言）

---

## 元教训防御 actionable 应用情况（**M13 R1+R2 主动复制不等抓**）

| # | 元教训 | 应用结果 |
|---|---|---|
| 1 | viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12 应用 / 第 9 数据点）| ✅ 2 端点全（POST /requirement + POST /save；GET /affected-nodes 是 viewer 可读）|
| 2 | write_event 异常传播测试（M04+ 范式）| ✅ test_save_analysis_propagates_write_event_failure_via_save_failed |
| 3 | cross-tenant 404（M02 范式）| ✅ 3 端点全（SSE + save + affected-nodes）|
| 4 | cross-project node 404（M06+M07+M08+M12 范式 / 3 端点全）| **R1 已 ✅ save + affected-nodes；R2 抓出 SSE 端点缺测立修 → ✅ 3 端点全** |
| 5 | IntegrityError 区分约束名（M05 P1-01）| N/A（R3-5 无自有 unique）|
| 6 | 纯读模块 docstring 每字段 ≥1 unit test（M10 NEW）| N/A（M13 不是纯读但同思想 — Pydantic 字段全 e2e 验）|
| 7 | R1.5 reconcile checkpoint（M10 NEW）| ✅ R1 立修对 R2 dispatch 前 grep 验证 / R2 抓出 P1 与 R1 立修无冲突（属 R1 漏检不是反复）|
| 8 | R-X1 失败补偿 commit boundary（M11 NEW）| N/A（M13 调单方法非 orchestrator）|
| 9 | 文件上传 file.size + sanitize（M11 NEW）| N/A（M13 无上传）|
| 10 | M12 元自审 — L1 锁裁决型 P1 自决不让 CY 拍 | ✅ 多处自决（_check_dimension_type_enabled skip / list_tree+path 等价 subtree / aclose 协议 / ai_model getattr 兼容 / ASGITransport skip 含完整 reason）|

---

## LLM 集成首发新教训 4 条 sink（M14+ 直接复制 / sink memory）

### 新教训 1：PEP 533 aclose 协议必须区分自然完成 vs 显式 aclose
**Why**：MockProvider 的 try/except GeneratorExit + aclose_called=True 路径必须设计成"只有 aclose() 触发 GeneratorExit 时才设标志"——自然完成（迭代到末尾）不进 except 分支，aclose_called 保持 False。否则测试无法区分两种路径。
**How to apply**：M14+ 任何 LLM provider 的 mock 必须实现 aclose_called: bool 公共属性 + try/except GeneratorExit 区分语义；service 层调 provider.analyze 后必须 try/finally await stream.aclose() 否则 caller aclose 时 GeneratorExit 不传给底层资源。

### 新教训 2：Anthropic SSE delta.type 多种必须显式校验
**Why**：anthropic content_block_delta 同名事件下 delta 有多种 type（text_delta / input_json_delta / thinking_delta / signature_delta）。当模型用 tool_use / extended thinking 时 delta.text 不存在但 delta.partial_json 存在；若 anthropic 后续把 thinking_delta 加 text 字段（已有先例），会把 thinking 文本当输出 chunk 喷给用户。
**How to apply**：M16/M17 LLM 集成或任何调 anthropic SSE 协议处必须 `if event.get("delta", {}).get("type") != "text_delta": continue`；测试必须含 thinking_delta / input_json_delta / signature_delta 用例确认被 skip。

### 新教训 3：SSE generator 持 AsyncSession 占连接池
**Why**：FastAPI Depends(get_db) 在 StreamingResponse 完全 drain 前不释放连接；SSE 流最长 300s 内独占 1 PG 连接。10 用户并发 SSE 即可吃光 default 10 连接池。
**How to apply**：M16/M17（流式/异步对比模块）必须立异步 SSE 连接策略：方案 A 短事务 read 完后释放手动持的 connection / 方案 B 用 SessionLocal 自管 / 方案 C 限并发数。本 sprint M13 punt 到 M16+ 统一立。

### 新教训 4：design §7 metadata 字段集每条都必须实装
**Why**：design §7 line 437 字面要求 SSECompleteEvent.metadata 含 analysis_time_ms，router 子片 4 漏注 → R2 P2-4 抓出升 P1。spec 漂移单字段缺失对前端 SaveAnalysisRequest 拼接造成隐性破契约。
**How to apply**：M14+ 任何 design §7 列的 metadata 字段集必须 e2e 测试逐字段断言；不依赖"前端可计时绕过"等乐观假设。

---

## 元自审教训（主流程错误 + 自纠）

**事件**：R2 reviewer 抓出 P1-2（SSE 端点 cross-project node 404 缺测，元教训 4/6 应用不全 — 只覆盖 save + affected-nodes 两端点漏 SSE）。

**根因**：子片 4 router 实装时主动列了"viewer 写 2 端点 403 / cross-tenant 404 / cross-project node 404"清单，但 cross-project node 测试集合在 save + affected-nodes 全做了，SSE 路径的 cross-project node → SSE error event 这条链路被遗漏（SSE 形态特殊，错以为 SSE 端点不需要这条覆盖）。

**修法 sink 到 feedback_problem_layered_analysis 失效信号**：元教训"3 端点全覆盖"原则——SSE 端点形态不同（错误以 event:error 报）但元教训依然适用；不能因 endpoint 形态特殊免除元教训复制。

---

## design 回写（关闸 commit 同 commit）

- §6/§9 同步代码示例补 async 范式说明（M02-M12 关闸惯例延续）
- §10 metadata 字段补 requirement_text_hash 字面（与实装对齐 / R1-A P1-1 立修后回写）
- §13 7 ErrorCode AppError 子类 http_status 表（404/422/503/504/429/500/422）已与实装对齐
- §15 完成度 checklist 三轮 reviewer audit 勾选

---

## Punt 池总表（M13 sprint 完成期 / 后续 sprint 顺手清）

| # | 项 | 来源 | 推荐时机 |
|---|----|------|---------|
| B1 | _upsert_dimension_type 并发首次 race（首次部署窗口） | R1-A P2 / R1-C P2 | M16/M17 ON CONFLICT DO NOTHING |
| B2 | integration smoke 模型名硬编码 → ANTHROPIC_SMOKE_MODEL env | R1-A P2 | 子片 5 关闸顺手 |
| B3 | _build_provider reason 取值表 docstring 化 | R1-A P2 | 关闸顺手 |
| B4 | ai_model 空但已配 provider+key 的 strict vs permissive | R1-A P2 | M02 baseline-patch 加 ai_model 列时 CY 拍 |
| B5 | 防御性 UUID 解析 dead branch 简化 | R1-A P2 | 关闸 simplify |
| B6 | prompt token 预算上限 | R1-A P2 | M16/M18 sprint 期 hot-path math 统一 |
| B7 | design line 379 StrEnum 字面同步 | R1-A P2 | 子片 5 design 回写 |
| B8 | SSEErrorEvent.error_code 改 ErrorCode Enum | R1-C P2 | M14 sprint 实装时 |
| B9 | save_analysis 返回 Any → DimensionRecord 类型化 | R1-C P2 | 关闸顺手 |
| B10 | fake_httpx 套件迁 conftest | R1-B P2 | M16 sprint 启动时评估 |
| B11 | breadcrumb 重复 get_node 优化 | R1-C P1（降级 P2）| 性能 sprint |
| B12 | M14 prompt injection 局部防御（node/issue 字段未隔离）| R1-C P2 | M14+ pilot 时统一立 |
| B13 | SSE generator 占 AsyncSession 300s 占连接池 | R2 P2-1 | M16/M17 立异步 SSE 连接策略 |
| B14 | 兜底 except Exception 路径 P1 修后无测试 | R2 P2-2 | M14 sprint 顺手补 |
| B15 | save 同 (node, type) 重复 IntegrityError 语义（design 灰区）| 子片 0 prep 留 | M14 sprint AnalyzeService 重 save 路径决（overwrite vs error）|
| B16 | M02 Project ai_model 字段未实装（M02 sprint 漏） | 子片 4 disambiguation | M14+ M02 baseline-patch + alembic add column |

---

## sprint 总览数据

- **commits**：8 主提交
  - 73c7175 子片 0 prep（§14.5 + DimensionService.create_dimension_record + get_latest 接通 + 3 smoke）
  - 28a127e 子片 1（AI Provider 抽象 + MockProvider + ClaudeProvider + Registry + 19 unit + 3 integration smoke）
  - ecb1d9c 子片 2（AnalyzeService + 7 ANALYSIS_* + AnalysisLevel + Prompt 模板 + 20 unit）
  - 368f83c 子片 3（Pydantic schema 4+3 + 13 unit）
  - eedecd1 R1 8 P1 立修（5+3+4 / 3 subagent 并行去重合并）
  - 7082b90 子片 4（Router 3 endpoints + 21 e2e）
  - 79fb4cc R2 4 项立修（2 P1 + P2-4 升 P1 + P2-3 顺手）
  - 子片 5 关闸 commit（本 audit + roadmap + handoff + design 回写）
- **测试**：827 PASS / 4 skipped (3 integration smoke 待 ANTHROPIC_API_KEY + 1 ASGITransport is_disconnected) / R13-1 79→86 / L12 守护通过
- **新增 ErrorCode**：7（ANALYSIS_*）
- **新增 endpoints**：3（POST /requirement SSE / POST /save / GET /affected-nodes）
- **新增模型**：0（R3-5 纯读聚合）
- **新增表**：0（聚合写 M04 既有 dimension_records）
- **新增横切 helper**：DimensionService.create_dimension_record + get_latest（M04 own / M13 首 caller）+ AI Provider 抽象 (api/services/ai/) + Prompt 模板 (analyze_prompts.py) + 2 conftest fixture (make_project_with_member / set_project_ai)
- **跨模块接通**：R-X3 写（M04.create_dimension_record）+ R-X3 读三上游（M02 ProjectService.get_for_user / M03 NodeService.get_node+breadcrumb+list_tree / M07 IssueService.list_by_project pass-through）
- **复用率**：~95%（service 层 100% / conftest fixtures 全调用 / R1-B 立修后 helper 100% 在 conftest）
- **AES 全链路接通**：M02 ProjectService → crypto.decrypt(ai_api_key_enc) → ProviderRegistry.get(ai_provider, api_key, model) → ClaudeProvider/MockProvider → 流式 chunk yield

---

## 关联

- design 真相源：design/02-modules/M13-requirement-analysis/00-design.md
- 上游决策：ADR-001 §4.1（AI Provider stream + aclose 协议）+ ADR-003 规则 1（跨模块只读走上游 service）+ ADR-004 P1（流式端点 Bearer JWT）
- 跨 sprint 元教训沉淀候选：feedback_llm_hotpath_math（M13 N/A 但记新教训 3 SSE generator 占 DB session）/ feedback_monkeypatch_not_verification（M13 强实证 — unit MockProvider + integration skipif anthropic SDK）
