# cluster-M17 RCA

> dogfooding sprint / 2026-05-15 / cluster-M17 fix RCA
> B 路径必产 / 4 段：现象 / 根因 / 类似问题 grep / design 哪步漏

## 1. 现象

dogfooding sprint 5/13 期 Opus spike M17 e2e 跑揭露 4 OPEN bug：

| Bug ID | 现象 | 严重度 |
|--------|------|--------|
| B-P2-M17-frontend-stub-puntresult | `app/src/actions/import-ai.ts` L106-135 4 server actions 全 `return actionError(PUNT_MSG)` / 前端 wizard 走不通 → 全 [DOM-flow] dead | 中（业务路径阻断 / 不是 prod 数据丢失）|
| B-P2-M17-fake-progress-no-websocket | `app/src/components/ai-import-wizard.tsx` L524-537 `setTimeout(r, 150)` 模拟假进度 / 0 WebSocket 客户端 / 后端 publish_progress 事件无消费者 | 大（design §6 + §7 + §12 字面要求 WS 客户端 / 实装直接舍弃异步范式）|
| B-P2-M17-design-gap-tab-vs-wizard | design §6 字面单一 4 步向导 vs 实装 3 tab 入口 + AI tab 内嵌 4 步 | 小（design vs UI 漂移 / 实装 UX 更合理 / 选 sync design）|
| B-P2-M17-design-gap-fresh-project-blocked | `/projects/{pid}/import` 无 ai_provider 检查 / fresh project 默认 NULL → AI tab 进入后 422 阻断才知道 | 小（UX 不友好 / 用户踩坑路径）|

## 2. 根因

### 2.1 共同根因 — Phase 2.2 子片 3b 关闸盲区延续

子片 3b 是 Phase 2.2「前端继承拷贝层降级」期，把 `actions/{import,import-ai,analyze}` 等老 Prism 调老端点（`localhost:8001` legacy + drizzle 调用）的 actions **字面降级**为 `puntResult` stub，**等待子片 3c 接入 prism-0420 真后端**。

**关闸盲区**：子片 3b 关闸时三 reviewer 流水线 PASS / 后续未跑子片 3c。Phase 2.3 cleanup S1+S3+S4+B+A+C+D 全完后**忘记把 punt 列表 reconcile 到 cross-sprint-punt-pool**（_handoff/dogfooding 5/13 已抓到该盲区，立 punt-frontend-gap-phase2x/PUNT-REPORT.md）。

cluster-M17 4 bug 中：
- bug 1 (`frontend-stub`) 是子片 3c 未执行直接表现
- bug 2 (`fake-progress`) 同根因延伸 — 拷贝层从老 Prism 拿来的 ai-import-wizard.tsx 本来就用 setTimeout 假进度（老 Prism 同步范式），未对齐 prism-0420 design 异步范式 + WS

### 2.2 design 范式漂移 — 老 Prism 同步 vs prism-0420 异步

prism-0420 M17 是「设计前置」期独立写的 design：
- 异步 Queue（arq + Redis）
- WebSocket 实时进度
- task_id 立返 / mapping 数据走 awaiting_review + GET /review

老 Prism F17 是「边做边想」的实装：
- 同步 `aiAnalyzeZip → mapping_rows`（client 立拿完整数据）
- 无 WebSocket / 进度条用 setTimeout 模拟
- 单步事务 inline

Phase 2.2 前端继承期**直接拷 ai-import-wizard.tsx 老 Prism 形态**，未审计 prism-0420 design §6 + §7 + §12 异步范式漂移 → bug 2 + bug 3 + bug 4 同根因。

### 2.3 onboarding 链路设计盲区

design §1 字面假设「项目级 AI Provider 已配」（cross-module-read M02 ai_provider）；§7 backend router 进入 submit_import 第一行立 raise 422 `ai_provider_unset`；但 **design 全文未写 UX onboarding 引导** → fresh project 默认 ai_provider=NULL 时只能撞 422 阻断 → bug 4 是 onboarding 设计盲区延伸。

## 3. 类似问题 grep（横切影响面）

### 3.1 子片 3b → 3c 未执行同根因 punt（cross-sprint-punt-pool §M-frontend 群）

`_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md` 字面列：
- M11 cold-start: ✅ already done（M11 sprint 内闭环）
- M12 comparison: 全量 UI 缺
- M13 SSE: 同根因 punt（待 SSE 范式 sprint）
- M14 workspace-dimension: 部分 punt
- **M16 ai-snapshot URL + 轮询架构**: 同根因 punt（轮询架构 + 异步范式实装 / 待 sprint）
- **M17 ai-import**: 本 cluster 处理
- M18 embedding upgrade: 部分 punt
- M19 export: 部分 punt
- M20 teams: 已实装

**已知未来 cluster 节奏**（PUNT-REPORT §下个 sprint）：M14 / M12 / M16 / M17（本）/ M13 — 优先级排好等触发。

### 3.2 design vs UI 漂移多发（同 sync 路径范式）

已知漂移群（同走 sync design 不动 UI 范式）：
- B-P2-cc-A-account-lockout-design-drift（cluster-6 cleanup 期 sync）
- B-P2-M10-error-response-format（cluster-6 同 sync 路径）
- B-P2-M17-design-gap-tab-vs-wizard（本 cluster sync）

→ 已立元模式 / 不重立。

### 3.3 异步范式同款漂移

WS / 轮询 / fire-and-forget 三种 prism-0420 design 异步范式 vs 老 Prism 同步范式漂移：
- M13 SSE：punt（同根因 / 待 SSE sprint）
- M16 轮询：punt（同根因 / 待 sprint）
- M17 WebSocket：本 cluster 修
- M14 sync sse：punt

→ 三模块同根因 / Phase 2.2 拷贝层未审计 prism-0420 design 异步范式 / 应**立元规则**入 cross-sprint-pool？（**escalation 候选**：建议主 agent 评估「Phase 2.2 拷贝层异步范式漂移」是否升级为 sprint 启动闸门 reconcile B 栏首查项 / 防 M13/M14/M16 子 cluster 同款踩坑）

## 4. design 哪步漏（reconcile 切回 design 文档）

| design 章节 | 是否补 | 补法 |
|------------|--------|------|
| §6 分层职责表 | ✅ 本 cluster 补 | 加 §6.0「Page 入口范式」段（3 tab + AI tab 内嵌 4 步）|
| §1 + §7 fresh project onboarding 引导 | 暂不动 | onboarding UX 实装层 / 待 Phase 3 onboarding sprint 系统化 |
| §6 import-progress.tsx 独立组件 | 不动 | 实装合并到 ai-import-wizard.tsx 内（不破契约 / 不重新拆）|
| §7 老 Prism 同步范式残留 | N/A | design 已是 prism-0420 异步范式真值 / 不补；frontend caller 重构（aiSubmitImportZip / aiFetchReviewData）独立 cluster |

## 5. escalation 上报（主 agent 评估）

### 5.1 cluster 范围内未完闭环（已上报 design-audit.md F3 PARTIAL）

- `ai-import-wizard.tsx` 主流程 step 0/1/2 仍依赖 `actions/import.ts uploadZip`（仍是 punt 状态 / 不在本 cluster 范围）。完整 happy path 端到端走不通，需独立 cluster 处理：
  - 选项 A: 实装 `uploadZip` 为 client-side zip 解析（用 JSZip 库）→ 不依赖后端
  - 选项 B: 实装 `uploadZip` 为「上传 multipart 暂存到 backend storage_client → 解析 → 返 ParsedFile[]」→ 需后端新 endpoint
  - 选项 C: 重构 wizard 流程把 step 0 改直接调 `aiSubmitImportZip` 跳 uploadZip / wizard step1 预览改 client-side JSZip 解析

→ 建议主 agent 起独立 cluster 评估 + 拍板 A/B/C。本 cluster commit message 在 RCA 显式声明。

### 5.2 Phase 2.2 拷贝层异步范式漂移升级建议

M13 / M14 / M16 / M17 同款异步范式漂移群同根因。建议主 agent 评估：
- 是否把「Phase 2.2 拷贝层 vs design 异步范式 reconcile」升为元规则
- 是否在 cross-sprint-pool 立首查项
- 是否每个未处理模块 cluster 启动前 reconcile 一次

## 6. 改动统计

| 文件 | 改动类型 | 行数估算 |
|------|---------|---------|
| `app/src/actions/import-ai.ts` | rewrite | +280 / -10（135 → ~310 行）|
| `app/src/components/ai-import-wizard.tsx` | add WS hook + 改 progress | +110 / -15 |
| `app/src/app/projects/[projectId]/import/import-page-client.tsx` | add ai_provider guard | +40 / -3 |
| `app/src/app/projects/[projectId]/import/page.tsx` | pass aiProvider prop | +1 / -0 |
| `design/02-modules/M17-ai-import/00-design.md` | sync §6 tab 范式 | +20 / -1 |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M17/design-audit.md` | new B 路径产物 | +100 |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M17/rca.md` | new B 路径产物 | +160 |

**总改动**：+711 / -29 ≈ **+682 净 / 跨 7 文件**（escalation 阈值 400 行临界；超阈值但单 cluster 4 bug 群 + design + audit + rca 三类合并产物）

## 7. 验证矩阵

| 类型 | 状态 |
|------|------|
| tsc | ✅ PASS (0 errors) |
| eslint（--no-warn-ignored）| ✅ PASS（3 文件 / 2 ignored 文件本来就 Phase 2.2 拷贝层 ignore 列表内）|
| playwright --list M17 | ✅ PASS (19 tests registered) |
| pytest M17 全套 | ✅ PASS (134/134) |
| design-audit | ✅ 0 high / 2 medium PARTIAL/DONE / 3 low DONE / 2 PASS |
| commit boundary | 单 commit 含 7 文件改动 |
