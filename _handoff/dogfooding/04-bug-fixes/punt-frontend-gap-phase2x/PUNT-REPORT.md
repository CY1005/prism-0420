---
title: Frontend gap cluster punt 报告 — Phase 2.x M-frontend 实装 sprint
status: living-doc
owner: CY
created: 2026-05-13
sprint: dogfooding P4 cluster-6
related:
  - _handoff/dogfooding/03-bug-queue.md
  - _handoff/dogfooding/HANDOFF-P4-CLUSTER-3-PLUS.md
  - design/02-modules/M12-comparison/00-design.md
  - design/02-modules/M13-requirement-analysis/00-design.md
  - design/02-modules/M14-industry-news/00-design.md
  - design/02-modules/M16-ai-snapshot/00-design.md
  - design/02-modules/M17-ai-import/00-design.md
---

# Frontend Gap Cluster — Punt to Phase 2.x M-frontend 实装 sprint

## 概述

dogfooding sprint P2 抽到了 5 个模块（M12 / M13 / M14 / M16 / M17）frontend 实装与 design 漂移严重的 gap：
- backend endpoints 全部已实装并通过 P3 executor / API 旁路验证
- frontend 在 Phase 2.2 前端继承期遗漏（拷 Prism 原版 UI 时未对齐 prism-0420 的 design 范式）
- 后果：用户从 DOM 主路径走到底端到端失败 / 但 API 旁路全 PASS（架构正确 / 集成漂移）

本 punt 报告把这 5 模块从 dogfooding P4 cluster-6 范围抽出 / 推到下个 sprint 一起做（建议 5 个 frontend 实装 Opus subagent 并行）。

## 5 模块 frontend gap 完整清单

### M12 — comparison page frontend 接错（design vs UI 漂移 / 重大漂移）

**OPEN bug**：
- `B-P2-M12-design-gap-comparison-page`（03-bug-queue.md L35）

**现象**：
- `comparison/page.tsx` 实装是 AI 竞品对比（generateComparisonAction / backfillRowAction / exportComparisonAction），调 M13 analyze 端点
- 完全不调 design §6/§7 声称的 6 个 `/comparison/matrix` + `/comparison/snapshots` CRUD 端点
- 节点选择器 / 维度选择器 / 快照保存弹窗 / 快照列表 UI 均未实装

**涉及 spec test**：
- M12-comparison.spec.ts 全量 DOM testpoint 不可达（仅 API 旁路验 backend 6 endpoints PASS）

**根因**：
- Phase 2.2 前端继承时 comparison/page.tsx 接的是 Prism 原版 AI 竞品对比 UI（M13 analyze 流程）
- 未对接 prism-0420 设计的 M03/M04 节点矩阵 + 快照 CRUD 端点

**修法范围估算**：
- comparison/page.tsx 重写（节点选择器 + 维度选择器 + 快照保存弹窗 + 快照列表）
- src/actions/comparison.ts 6 个 action 全接通 comparison_router.py 6 endpoints
- 估时：4-6 工时（Opus subagent cap $5-7）

### M13 — requirement-analysis frontend 链路全 dead（4 个 OPEN bug 同根因群）

**OPEN bugs**：
- `B-P2-M13-sse-proxy-url-broken`（03-bug-queue.md L50）
- `B-P2-M13-actions-stub-puntresult`（L51）
- `B-P2-M13-save-request-fields-gap`（L52）
- `B-P2-M13-design-gap-drawer-vs-fullpage`（L53）

**现象**：
- 浏览器 → POST /api/analyze/stream 全链路 500（proxy URL 签错 + API_BASE 端口错 + 不转 Authorization）
- src/actions/analyze.ts L60-96 6 个 action stub 返 puntResult（saveAnalysisAction / generateTestPointsAIAction / saveTestPointsAction / generateComparisonAction / backfillRowAction / exportComparisonAction）
- analysis/page.tsx state 缺 SaveAnalysisRequest 7 字段（requirement_text / ai_provider / ai_model / analysis_time_ms / analysis_result / analysis_level / affected_node_ids）→ 即使 stub 修后接通会立即 422
- design §6 + tests.md S9 字面声称 M13 UI 是 node 档案页挂载分析抽屉 / 实装是独立全屏 `/projects/{projectId}/analysis?nodeId=...` 页（两者交互范式完全不同）

**涉及 spec test**：
- M13-requirement-analysis.spec.ts SSE happy path / save button / generate test points / comparison batch 全 FAIL
- 仅 API 旁路 + B-P3-M13-save-btn-shows-on-error fix（已 FIX_DONE）通过

**根因**：
- 子片 3c 子片未执行（actions/analyze.ts stub puntResult 留下 / SSE proxy 路由签错 / state 字段缺）
- Phase 2.2 前端继承时拷 prism 原版独立全屏页 / 未对齐 prism-0420 design 的抽屉范式

**修法范围估算**：
- src/app/api/analyze/stream/route.ts 改 URL + 转 Authorization + API_BASE env 默认 http://localhost:8000
- src/actions/analyze.ts 6 个 action 接通真后端（M13 analyze/save + M14 comparison 批处理）
- src/app/projects/[projectId]/analysis/page.tsx state 扩 7 字段 + saveAnalysisAction 签名扩
- design §6 + §8 + tests.md S9 决策：sync UI 改回抽屉 / 还是 sync design 改成全屏页（A/B 决策 / 需 CY 拍）
- 估时：8-12 工时（最大 / Opus subagent cap $8-12）

### M14 — industry-news 全量 UI 未实装

**OPEN bug**：
- `B-P2-M14-design-gap-news-ui`（03-bug-queue.md L37）

**现象**：
- design §6 声称的 `web/src/app/industry-news/page.tsx` / `news-card.tsx` / `news-form.tsx` / `node-link-picker.tsx` / `web/src/actions/industry-news.ts` 均不存在
- `src/actions/feed.ts` 是全量 NOT_IMPLEMENTED stub
- /industry-news 路由 404

**涉及 spec test**：
- M14-industry-news.spec.ts 全量 DOM testpoint 不可达（API 旁路验 backend /api/news endpoints PASS）

**根因**：
- Phase 2.2 前端继承时 feed 域（来自 prism 原版）与 prism-0420 /api/news 域不对应
- 未实现映射；feed.ts 注释"子片 5 后切换"但子片 5 未执行 M14 UI

**修法范围估算**：
- /industry-news 全量页面 + 4 components + 1 action 全新写
- 估时：6-8 工时（Opus subagent cap $6-9）

### M16 — ai-snapshot frontend URL + 轮询架构 gap

**OPEN bugs**：
- `B-P2-M16-frontend-url-gap`（03-bug-queue.md L55）
- `B-P2-M16-frontend-no-polling`（L56）

**现象**：
- workspace.tsx handleGenerateSnapshot 调 `/api/snapshot/generate`（POST body 含 node_id/project_id）
- 真实后端端点是嵌套 `/api/projects/{pid}/nodes/{nid}/snapshot/generate`（不接受 flat body）→ 405/404
- handleSaveSnapshot 调 `/api/snapshot/save`（传 summary/dimensions 字段）与 SnapshotSaveRequest schema 完全不匹配
- workspace.tsx M16 实现同步等待 AI 结果（setSnapshotLoading=true → await fetch() → setSnapshotData），没有实装 design §1 要求的轮询架构（POST 202 立返 task_id + GET /snapshot-tasks/{id} 每 3-5s 轮询）

**涉及 spec test**：
- M16-ai-snapshot.spec.ts DOM 生成路径全 dead / 仅 API 旁路 + 轮询架构 single-step verify PASS

**根因**：
- Phase 2.2 前端继承时沿用 prism 原版同步生成 URL + 同步调用范式
- 未对齐 prism-0420 design 的异步 fire-and-forget + 轮询架构

**修法范围估算**：
- workspace.tsx handleGenerateSnapshot 改嵌套 URL（无 body）→ 读 task_id → 轮询 GET /snapshot-tasks/{task_id} 直到 succeeded → 展示 review_data
- handleSaveSnapshot payload 改为 {task_id, save_summary, selected_dimension_keys}
- useEffect poller（清 cleanup 防内存泄漏）+ toast 状态推进 + 徽标 badge + "温柔放手" 2.5min 弹出 + failed 弹出重新生成入口
- 估时：5-7 工时（Opus subagent cap $5-8）

### M17 — ai-import frontend stub + fake progress + design 漂移多发

**OPEN bugs**：
- `B-P2-M17-frontend-stub-puntresult`（03-bug-queue.md L59）
- `B-P2-M17-fake-progress-no-websocket`（L60）
- `B-P2-M17-design-gap-tab-vs-wizard`（L61）
- `B-P2-M17-design-gap-fresh-project-blocked`（L62）

**现象**：
- src/actions/import-ai.ts L106-135 全部 4 个 action（aiAnalyzeZip / aiAdjustMapping / aiConfirmImport / aiUndoImport）字面 `return actionError(AppError(PUNT_MSG, ...))`
- ai-import-wizard.tsx L524-537 用 `setTimeout(r, 150)` 模拟假进度推进 / 0 WebSocket 客户端连接
- design §6 字面「Page = 4 步向导」单一路径 / 实装是 3 tab 切换（手动映射 / AI 智能导入 / Markdown 导入）
- /import 页面无 ai_provider 配置检查（fresh project 默认 ai_provider=NULL → 422 阻断后才能从 PUNT_MSG / 422 error 猜出原因）

**涉及 spec test**：
- M17-ai-import.spec.ts 全量 DOM testpoint 不可达 / 仅 API 旁路 + WS endpoint spike PASS（B-P3-M17-ws-invalid-jwt-close-code 已 FIX_DONE）

**根因**：
- 子片 3b 拷贝层降级时把 ai-import 4 个 action 显式标 punt 等子片 3c 接入 M17 ImportTask 异步任务 + WS 进度通道
- 子片 3c 未执行
- M17 design §7 + §13 字面要求 ai_provider 必配 / 前端 UX 未承接 onboarding 链路

**修法范围估算**：
- src/actions/import-ai.ts 4 个 action 接通真后端（multipart upload + 轮询 / WS 推进 + confirm/cancel）
- ai-import-wizard.tsx 实装 WS 客户端 onmessage 取 ProgressEvent 实时刷新（删除 setTimeout 假进度）
- import-page-client.tsx tab UI 决策：sync design 加 tab / 还是 sync UI 删 tab 只留 AI 智能导入（A/B 决策 / 需 CY 拍）
- /import page.tsx ai_provider 检查 + 引导卡片
- 估时：8-10 工时（最大 / Opus subagent cap $8-12）

## design vs 实装漂移根因总结

**Phase 2.2 前端继承期遗漏（共同根因）**：
1. 子片 3b 拷贝降级时多模块标 punt 等子片 3c 接入真后端 → **子片 3c 未执行**（cf. B-P2-M13 / B-P2-M17 群）
2. 前端继承时直接拷 Prism 原版多入口 UI / 没全量审计 prism-0420 design 范式漂移（cf. B-P2-M12 / B-P2-M13-drawer / B-P2-M16 / B-P2-M17-tab）
3. 异步范式落地遗漏：prism-0420 design 要求 fire-and-forget + 轮询 + WS 进度通道 / 实装继承 prism 原版同步 await（cf. B-P2-M16 / B-P2-M17）

**架构层正确 / 集成层漂移**：
- backend endpoints / schema / state machine / activity_log 全 design-first 落地 PASS
- frontend 与 backend 集成时漂移：URL / payload schema / 异步范式 / 多入口 vs 单入口

## 建议下个 sprint 节奏

**Phase 2.x M-frontend 实装 sprint**：

| 模块 | 估时 | Opus subagent cost cap | 优先级理由 |
|------|------|----------------------|---------|
| M14 | 6-8 工时 | $6-9 | 全量 UI 缺 / 0 拷贝起点 / 最干净起手 |
| M12 | 4-6 工时 | $5-7 | comparison page 重写 / 6 endpoints 已就绪 / 测试覆盖好 |
| M16 | 5-7 工时 | $5-8 | 轮询架构 + 异步范式实装 / 同时为 M13 SSE 探路 |
| M17 | 8-10 工时 | $8-12 | A/B 决策（tab vs wizard）依赖 CY 拍 / 最复杂 |
| M13 | 8-12 工时 | $8-12 | A/B 决策（抽屉 vs 全屏）依赖 CY 拍 / SSE proxy 链路 |

**并行节奏**：
- 1 sprint 内 5 个 subagent 并行（按上表 cap 总 $32-48 / 跨 1-2 sprint）
- M14 + M12 + M16 先并发跑（无 A/B 决策依赖）
- M13 + M17 各自做 A/B 决策（先派 1 Sonnet subagent 收集证据 → CY 拍 → 再派 Opus 实装）

## STAR 价值

**Phase 3 v0.4 D2 bug 类别分布新增类别 "前端继承期遗漏"**：
- dogfooding sprint 抓到 5 模块 frontend gap × 多 OPEN bug
- 简历级实证：design-first 方法论的盲区——前端继承（拷贝改）期没人对照 design 跑漂移 audit / 各模块单测 PASS 不代表集成 PASS
- 对照 Prism 原版（边做边想 / 无 design 文档）：prism-0420 backend 完整度高 / 但 frontend 集成漂移类 bug 数 ≥ 9 条 OPEN（M12×1 + M13×4 + M14×1 + M16×2 + M17×4 = 12 条）
- 启示：design-first + 后端先做的路径下，**前端继承期是新瓶颈**——需要单独的 "design vs UI 实装漂移 audit gate" 闸门

**改进建议**：
- 下个 sprint 加 design-vs-UI 漂移 audit 子 agent（每 frontend sprint 跑一次）
- 把"前端继承期漂移"立为 phase-gate checklist 一项（@ design/00-phase-gate.md）

---

last_updated: 2026-05-13
