# cluster-M17 design audit (B 路径)

> dogfooding sprint / 2026-05-15 / Phase 2.x M-frontend cluster-M17
> 触 plan §3 B 路径自评 6 项风险：改动范围高 + 跨 ≥4 文件 + 改 design 文件 → B 路径自跑 audit
> 范围：B-P2-M17-frontend-stub-puntresult + fake-progress-no-websocket + design-gap-tab-vs-wizard + design-gap-fresh-project-blocked

## 审计输入

| 文档 | 章节 | 校对内容 |
|------|------|---------|
| `design/02-modules/M17-ai-import/00-design.md` | §1 业务边界 / §6 分层 / §7 API 契约 / §12 Queue payload | API endpoints / 状态机 / WS 协议 |
| `design/adr/ADR-002-queue-consumer-tenant-permission.md` | §2 WebSocket task_id 鉴权 | WS 鉴权范式 |
| `design/00-architecture/06-design-principles.md` | 原则 1-5 + 5 项约束清单 | tenant / 事务 / 异步 / 并发 |
| `api/routers/import_router.py` 全 444 行 | endpoints + WS handshake | 真后端契约 |
| `api/schemas/import_schema.py` 全 244 行 | ImportTaskResponse / ReviewConfirmRequest / ProgressEvent / ClientCommand | schema 真名 |
| `app/src/actions/import-ai.ts`（改造后）+ `ai-import-wizard.tsx`（改造后）+ `import-page-client.tsx`（改造后） | server actions + WS hook + page guard | frontend 改动 |

## findings 表（4 字段：冲突级别 / 章节 / 冲突描述 / 处置建议）

| # | 级别 | design 章节 | 冲突描述 | 处置建议 |
|---|------|-------------|---------|---------|
| F1 | **low** | §6 Page 入口 | design 早期草案 §6 字面只写「Page = 4 步向导」单一形态；实装是「3 tab + AI tab 内嵌 4 步」/ B-P2-M17-design-gap-tab-vs-wizard | **DONE**：本 cluster 已 sync design §6 加 §6.0「Page 入口范式」段说明 3 tab 入口 + AI tab 内嵌 4 步向导。不动 UI（cf. 主 agent 拍板 / 同 cluster-6 sync 路径）|
| F2 | **medium** | §1 In scope / onboarding 链路 | design 假设「项目级 AI Provider 已配」/ fresh project 默认 ai_provider=NULL → 422 阻断后才知道；design 未写 onboarding 引导（B-P2-M17-design-gap-fresh-project-blocked）| **DONE**：本 cluster 在 `import-page-client.tsx` 进 AI 智能导入 tab 前加 `AIProviderUnsetGuide` 引导卡（跳 settings 配置）。design 文档暂不动（onboarding 链路属 UX 实装层 / 待 Phase 3 onboarding sprint 系统化）|
| F3 | **medium** | §6 + §7 + §12 异步范式（G1）| design 异步 Queue + WS 范式 vs 老 Prism 同步 `aiAnalyzeZip → mapping_rows` 范式根本差异；caller `ai-import-wizard.tsx` 仍按老范式（step2 显示完整 mapping_rows）/ 后端 `submit_import` 立返 task_id + status=pending、mapping 数据在 awaiting_review 后才有 | **PARTIAL**：本 cluster 改 `aiAnalyzeZip` 显式 return error 引导改调 `aiSubmitImportZip(file)`；新加 `aiFetchReviewData(projectId, taskId)` 走 GET /review；wizard 主流程暂保留老形态（caller 重构 ≥200 行 / 超 cluster 范围）。完整 happy path 端到端依赖：① import.ts `uploadZip` 实装（另一 punt） ② wizard step 流程改造（独立 sprint）。**escalation 已上报 RCA** |
| F4 | **low** | §7 confirm endpoint（G2 + G3）| backend confirm 接受 ReviewConfirmRequest（按 type 分组 nodes/dimensions/competitors/issues）；caller `aiConfirmImport(mappingRows: MappingRow[])` 按 row 形态；后端无 review 中间调整 endpoint（aiAdjustMapping）；后端 cancel 是 task 级 vs caller aiUndoImport 是 per-node | **DONE**：本 cluster 在 `aiConfirmImport` 内做 MappingRow → ReviewConfirmRequest 最小转换（dimensions[] / skip_proposed_ids[]）；`aiAdjustMapping` 改 no-op + 注释 G2 design-gap；`aiUndoImport` 改调 task 级 cancel + 注释 G3 design-gap。design 文档**不改**（cluster 范围 / 业务语义 caller 适配 backend 而非反过来）|
| F5 | **low** | §6 WebSocket 客户端 | design §6 列 `web/src/components/business/import-progress.tsx` WebSocket 客户端；实装在 `ai-import-wizard.tsx` 内嵌 hook（未拆独立组件） | **接受**：design §6 字面是模块预期分层职责；实装合并到 wizard 内不破契约（不违反「禁止：Router 直查 / Service 直接调 AI」三条字面规约）。WS 协议层完全对齐 §7 + §12 + ADR-002 / 不重新拆组件 |
| F6 | **none** | ADR-002 §2 WS 握手鉴权 | 后端实装：`accept()` → `decode_jwt(query.token)` → `check_task_access` → 失败 `close(1008)` / 成功进主循环；frontend WS hook：`new WebSocket(url?token=<JWT>)` → onmessage 收 ProgressEvent → onclose 取 code 显示 | **PASS**：完全对齐 ADR-002 §2 范式 + B-P3-M17-ws-invalid-jwt-close-code FIX_DONE 路径（accept-then-close 让 client 拿 1008）|
| F7 | **none** | §10 activity_log + §13 ErrorCode | frontend 改动不触 activity_log（backend 内部）/ ErrorCode 复用 backend 字面 `import_invalid_source` 422 | **PASS** |

**汇总**：0 high / 2 medium / 3 low / 2 PASS。无 high 冲突 / 不触 escalation 中止条件。

## 设计原则 5 条 + 5 约束清单核对

| 原则 / 清单 | 触发 | 实装 |
|------------|------|------|
| 1. SQLAlchemy schema 唯一真相源 | ❌ frontend 不触 | N/A |
| 2. 分层严格 | ✅ | server action 调 server-http-client / WS hook 在 component 内（spec 06 允许）|
| 3. 接口 Contract First | ✅ | endpoint URL 全用 design §7 + import_router.py 字面真名 |
| 4. 状态机显式定义 | ✅ | WS hook onmessage 取 ProgressEvent.status 字段不改字面 |
| 5. 多人架构 4 维必答 | ✅ | tenant: 走 server-http-client 带 Bearer + project_id URL / 异步: WS task_id / 并发: design §5 last-write-wins 已 ack |
| 清单 3: Queue payload tenant | ❌ frontend 不触 | N/A (后端责任) |
| 清单 4: idempotency_key | ❌ frontend 不触 | N/A (后端 source_hash 自动算) |
| 清单 5: DAO tenant 过滤 | ❌ frontend 不触 | N/A (后端责任) |

无原则违反。

## R-X1 自洽（M17 不直 INSERT M03/M04/M06/M07 表）

frontend cluster 完全不触后端 service / 不破 R-X1。`aiConfirmImport` 走 POST /confirm 经 backend service 层调用 batch_create_in_transaction / 全链路 R-X1 自洽。

## escalation 中止条件检查

- ✅ 0 high / 0 medium 真破设计原则 / ADR-002 / ADR-004
- ✅ tsc 0 错（baseline + after）
- ✅ eslint 0 错（--no-warn-ignored / 3 文件中 2 文件在已存的 Phase 2.2 拷贝层 ignore 列表内 / 1 文件 import-ai.ts 不在列表 grep PASS）
- ✅ pytest M17 134/134 PASS
- ✅ WS 客户端 design §12 协议明确 / 不留 [AMBIGUOUS]
- ✅ 改动总行数估算（见 RCA）<400
- ✅ subagent cost 远 < $8

**verdict**：PASS / B 路径 commit allowed
