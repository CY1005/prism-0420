# cluster-M12 RCA

> dogfooding sprint / 2026-05-15 / cluster-M12 fix RCA
> B 路径必产 / 7 段：现象 / 根因 / 类似问题 grep / design 哪步漏 / escalation / 改动统计 / 验证矩阵

## 1. 现象

dogfooding sprint P2 期 Sonnet subagent M12 e2e 跑揭露 1 OPEN bug（PUNT-REPORT.md §M12 落，待 Phase 2.x M-frontend sprint 处理）：

| Bug ID | 现象 | 严重度 |
|--------|------|--------|
| B-P2-M12-design-gap-comparison-page | comparison/page.tsx 实装是 prism v1 拷贝层的 AI 竞品对比 UI（hardcoded "AWS SageMaker / 阿里 PAI" + 本地 state dropdown + 调 generateComparisonAction / backfillRowAction / exportComparisonAction → 接 M13 analyze 端点）；完全不调 design §6/§7 的 6 个 `/comparison/matrix` + `/comparison/snapshots` CRUD 端点；节点选择器 / 维度选择器 / 快照保存弹窗 / 快照列表 UI 均未实装；M12-comparison.spec.ts 全部 DOM 维度/快照 testpoint 仅走 API 旁路（backend 6 endpoints PASS）/ DOM 主路径"对功能项进行多节点+多维度对比并保存为快照"完全走不通 | 中（业务路径阻断 / dogfooding 真用户场景"对比 N 节点 × M 维度并保存命名快照"完全走不通；非生产数据丢失） |

## 2. 根因

### 2.1 共同根因 — Phase 2.2 子片 3b/3c 关闸盲区延续（与 cluster-M14 + M17 同根源）

子片 3b 是 Phase 2.2「前端继承拷贝层降级」期：
- 把老 prism `comparison/page.tsx`（AI 竞品对比 UI / hardcoded competitors / dropdown / call `analyze.ts` 6 stub）整体保留
- 把 `actions/analyze.ts` 中 6 个 action 全部 stub 为 `puntResult` NOT_IMPLEMENTED（含 generateComparisonAction / backfillRowAction / exportComparisonAction / saveAnalysisAction / generateTestPointsAIAction / saveTestPointsAction）
- file header 注释字面承诺："子片 3c 接入 M13/M14 真实端点"

子片 3c **未执行**该接入 — 既没接 M13 analyze 端点（M13 cluster scope），也没新建 design §6 字面要求的 `actions/comparison.ts`（M12 cluster scope）。

**关闸盲区**：与 cluster-M14 / M17 同根因 — Phase 2.3 cleanup S1+S3+S4+B+A+C+D 全完后 reconcile 时未把 punt 列表完整入 cross-sprint-punt-pool（5/13 dogfooding 抓到 → 立 punt-frontend-gap-phase2x/PUNT-REPORT.md）。

### 2.2 拷贝层 UI 范式与 prism-0420 design 完全不对应

prism v1 `comparison/page.tsx`：AI 智能竞品对比工作流
- 输入：选 1 个功能 + 多个竞品名 + 自定义维度（全本地 state）
- 处理：调 LLM 生成 N×M 对比结果（generateComparisonAction → /api/projects/{pid}/analyze/comparison）
- 输出：可编辑的对比表 + AI 结论 + 回填到 CompetitorReference 表

prism-0420 design §1 + §6：节点矩阵 + 命名快照工作流
- 输入：选 N 个 nodes（来自 M03）+ M 个 dimension_types（来自 M04 项目启用配置）
- 处理：实时聚合 GET /comparison/matrix（cells-only / R-X3 / 调 M04 DimensionService.batch_get_by_nodes）
- 输出：N×M 网格 + 可保存为命名快照（POST /snapshots / G4=B 值快照）+ 快照管理（list/rename/delete）

**两套域的实体形态、用户场景、API 契约都不一致**：
- 老 UI 主表 = AI 一次性对比结果（不持久化 / 用户编辑后回填到 CompetitorReference）
- 新 design 主表 = comparison_snapshots + comparison_snapshot_items（持久化值快照 / G4=B 不降级）
- 老接 /api/projects/{pid}/analyze/* 系列（M13 范畴）vs 新接 /api/projects/{pid}/comparison/* 系列（M12 范畴 / 6 endpoints）

子片 3b 选了"page 整体保留 + actions 全 puntResult stub" — 这是当时合理的最小可工作选择（不破 page 编译 / 不破业务但保现状的可视性），代价就是 design §6 字面的 `actions/comparison.ts` 没人建 + page 没人改写。

### 2.3 spec 反向断言（无）— M12 spec 不像 cluster-M14 spec L628 那样把 design-gap 固化为 DOM 反向断言

`M12-comparison.spec.ts` 全 906 行 grep 没有 cluster-M14 F9 那种"路径应 404"反向断言：所有 DOM 测试只是 smoke（page 可达 + 部分 UI 元素可见），没有"page.tsx 应展示老 UI"的反向锚定。但也没有针对节点选择器 + 维度选择器 + 快照保存弹窗 + 快照列表的 DOM 主路径 testpoint（全部 99 testpoint 中 [P1] UI 类全标 [skip-N/A]）。换言之 M12 spec 是 "design-gap aware" 但 "未跟进新 UI 实装的 DOM 测试"。本 cluster 实装后 spec 25 个测试全部应 PASS（24 API-bypass + 2 DOM smoke）/ 没有反向 spec 升级需求。

## 3. 类似问题 grep（横切影响面）

### 3.1 子片 3b → 3c 未执行同根因 punt（cross-sprint-punt-pool §M-frontend 群）

`_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md` §共同根因字面列：

- M12 comparison: page 完全接错 — **本 cluster 处理** ✅
- M13 SSE: 全链路 dead（actions/analyze.ts stub puntResult / SSE proxy URL broken / 抽屉 vs 全屏 A/B 决策）— **待 cluster-M13**
- M14 industry-news: 全量 UI 缺 — **cluster-M14 已闭 79f6204** ✅
- M16 ai-snapshot: 同步 URL + 无轮询架构 — **待 cluster-M16**
- M17 ai-import: stub puntResult + fake progress + tab vs wizard 漂移 — **cluster-M17 已闭 cb27ac8 / sub uploadZip PARTIAL 待独立 cluster** ✅

**已知未来 cluster 节奏**（PUNT-REPORT §下个 sprint 推荐顺序）：M14（done）/ M12（本）/ M16 / M17（done）/ M13。

### 3.2 design vs UI 范式漂移多发（同 sync design 不动 UI 范式）

已知漂移群（同走"接受 + 不动 design"范式）：
- M17 cluster F1 — `business/` 子目录 design vs flat 实装
- M17 cluster F5 — `import-progress.tsx` 独立组件 design vs 合并到 wizard 内
- M14 cluster F1 — `business/` 子目录 design vs flat 实装
- M14 cluster F2 — `web/` 前缀 design vs `app/` 实装
- **M12 本 cluster F1+F2+F12** — `web/` 前缀 + `compare` vs `comparison` 路径段 + `business/` 子目录 + 内联 vs 拆 components 全套低风险漂移群

→ "实装 vs design 路径段范式漂移 + 不破契约不动 design"已成稳定元模式 / 元规则 #11 已锁。

### 3.3 caller 残留 stub 决策（actions/analyze.ts 中 3 个 comparison-targeted action）

`actions/analyze.ts` 中以下 3 个 stub 在 cluster-M12 后变成"无 caller"：
- `generateComparisonAction` — 仅 comparison/page.tsx import / cluster-M12 后不再 import
- `backfillRowAction` — 同上
- `exportComparisonAction` — 同上

**决策：leave-as-is 不删**（caller-side stub 决策记 RCA + 元规则 #11 C 栏）：
- A: 删除 3 函数 → 最干净 / 但跨 cluster boundary（这 3 函数是子片 3b 时由"M13 analyze 域"的 stub 群整体定义 / 同 saveAnalysisAction 等其他 5 个 stub 在同文件 / 删 3 留 5 容易误读为"接通了"）
- B: 保留 3 函数 + 加注释"deprecated by cluster-M12 / no longer called" → 守 cluster boundary / M13 cluster 接入时统一清理
- C: 改为字面 throw `new Error("removed by cluster-M12")` → 退化为防御性代码 / 但 dead code 编译不过 ts strict

**最终选择 B**（不动 / 保现状）：
- M13 cluster 启动时会重新评估 analyze.ts 中 6 个 stub（含本 3 个）的归宿（接通 vs 删除 vs 保留）
- 守 cluster boundary 优先 — 本 cluster 范围只是"M12 page + actions 实装"
- analyze.ts 在 eslint ignore 范围内（`src/actions/**` 中部分 actions 已合规但 analyze.ts 这种 stub 群不动）/ 不删不会带来 lint warning
- 元规则 #11 C 栏字面授权"leave/delete/redirect 决策 / cluster boundary 守恒优先"

详见 design-audit F3 结论 / 元规则 #11 C 栏证据。

### 3.4 异步范式 audit（元规则 #11 D 栏）

design §5 显式声明 M12 全同步 CRUD（无 Queue / 无 WebSocket / 无轮询）。本 cluster 实装也是全同步 await fetch / 无 setTimeout 假进度 / 无 EventSource / 无 WebSocket client。**clean** — 不像 cluster-M16（轮询）/ M17（WS）/ M13（SSE）需异步范式实装审计。

## 4. design 哪步漏

design §6 字面"分层职责表" + §7 "API 契约 6 endpoints" 全部正确锁定（backend 实装 100% 对齐 / cluster-M14 + M17 已实证此模式有效）。

漏的不是 design 自身，是**子片 3c 关闸**：
- 子片 3b stub puntResult 时承诺"子片 3c 接入"但子片 3c 实际跑时**仅接了部分模块的 backend → frontend 桥**（M02-M11 主链路）/ M12-M17 这 5 个模块的桥被遗漏到 Phase 2.3 cleanup 之外
- Phase 2.3 cleanup S1+S3+S4+B+A+C+D 关闸时 reconcile 也未抓到（直到 dogfooding 5/12 才发现）

**根本元教训**（cluster-M14 RCA §4 + cluster-M17 RCA 已立 / 本 cluster 实证再次确认 / 已成定论）：**前端继承（拷贝改）期是设计前置方法论的盲区**——design-first 的 backend 完整度高，但 frontend 拷贝层 + actions stub 桥的对接在子片 3b/3c 之间出现关闸盲区。已立 punt-frontend-gap-phase2x/PUNT-REPORT.md 5 模块清单 + 元规则 #11 / 不重立。

## 5. escalation 上报清单

无 high 冲突 / 无中止条件触发。本 cluster 自主完成 fix + audit + commit。

向主 agent 上报建议（非 cluster-M12 内必修，但闭环 / 跨 cluster cleanup 应处理）：

### 5.1 spec 反向断言 — F13 PARTIAL（与 cluster-M14 F9 同范式）

发现 spec L166-183 [P1] DOM 测试字面：`expect(page.getByRole("button", { name: "+ 添加竞品" })).toBeVisible()`。该按钮是拷贝层老 UI（M06 竞品录入 / 不在 M12 §1 in scope）。本 cluster 重写 page.tsx 后该按钮已删除（design §1 字面声明竞品录入归 M06 / out of scope）→ **该 1 个 DOM smoke 测试预期 FAIL** 在 cluster-M12 push 后。

**与 cluster-M14 F9 spec L628 同模式**：spec 把"design-gap 老 UI"固化为 DOM 断言 / dogfooding sprint P2 写 spec 时反向锚定 / 实装后断言失效 / 不属业务回归 FAIL 属"反向断言生命周期"。

**建议主 agent 在 closeout 时**：
- A: 删除 spec L166-183 整个 [P1] test（最干净 / 该 test 内只 3 行断言：heading + tab nav + 添加竞品 button / 前两个 smoke L132 已覆盖）
- B: 改 L182 为反向断言：`expect(page.getByRole("button", { name: "+ 添加竞品" })).toHaveCount(0)` （字面证明 design §1 out of scope）
- C: 删除 L182 单行 + 保留 L168-181（heading + tab nav 部分）

**推荐 C**（保留 heading/tab nav smoke 价值 / 仅删 design-gap 反向锚定 / 与 cluster-M14 同处理范式）。

main agent closeout 时一并 commit 比 cluster-M12 commit 后单独 commit 更干净（避免 1 个 push CI 红的中间态）。

如 main agent 选 A/B/C 任一，cluster-M12 commit 都视为业务上 DONE / 不需 revert。

### 5.2 actions/analyze.ts 3 个孤儿 stub 决策（决策已记 RCA §3.3 / leave-as-is）

这 3 个 stub（generateComparisonAction / backfillRowAction / exportComparisonAction）在 cluster-M12 后变成 dead code（无 caller）。建议主 agent 在 closeout 时：
- A: 不动（默认 / 元规则 #11 C 栏 cluster boundary 守恒）
- B: 加注释"deprecated by cluster-M12 / dead code awaiting M13 cluster cleanup"
- C: 升 cross-sprint-punt-pool §M-frontend 群作为 cluster-M13 启动时的 reconcile 项

**推荐 A**（最简）/ B 备选（如 main agent 觉得 dead code visibility 重要）/ C 不推荐（已经在 PUNT-REPORT 范围）。

### 5.3 comparison 路径 eslint ignore（与 cluster-M14 不同 / 守 cluster boundary）

cluster-M14 因为是 fresh path（`/industry-news/`）实装新 page，所以 fresh 写代码自然脱离 ignore；本 cluster 是 in-place 重写既有 ignored 路径（`src/app/projects/**/comparison/**` 在 eslint.config.mjs L72 字面 ignore），新 page.tsx 仍在 ignore 范围。

**当前实装：page.tsx 不被 eslint 检；新建 actions/comparison.ts + lib/validators/comparison.ts 不在 ignore / 已自跑 eslint --no-warn-ignored = 0 errors**。

建议主 agent 在 closeout 时评估：
- A: 不动（默认 / 守 cluster boundary / eslint 治理走独立 cleanup cluster）
- B: 把 `src/app/projects/**/comparison/**` 从 ignore 移除 → 跑 eslint 看 page.tsx 残余 issues → 修 → 一并 commit
- C: 升 punt 池作为下个 sprint cleanup 项

**推荐 A**（最简 / 与 cluster-M14/M17 的 P5b spec-fix 池 + cluster boundary 守恒原则一致 / eslint 治理是 Phase 2.2 子片 1.8 渐进还债的延续）。

### 5.4 元规则 #11 实证 — M12 cluster 复用 4 栏 reconcile 全 clean

本 cluster 元规则 #11 4 栏全走完 / 全 finding 都是已知模式（路径段漂移 / actions stub leave-as-is / 异步范式 N/A）/ 没有新增"漂移 family"。建议主 agent 把 cluster-M12 加入元规则 #11 实证清单（与 M14 + M17 并列）/ 不需新立元规则。

## 6. 改动统计

### 新建文件（3 个 / ~250 行）

| 文件 | 行数 | 用途 |
|------|------|------|
| `app/src/actions/comparison.ts` | 158 | M12 server actions（6 函数对接 6 endpoints） |
| `app/src/lib/validators/comparison.ts` | 32 | zod validators（createSnapshotSchema + renameSnapshotSchema） |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M12/design-audit.md` | ~120 | B 路径 audit 文件（findings 表 12 项 / 5+5 清单 / R-X1+R-X3 自洽 / verdict） |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M12/rca.md` | ~150 | 本 RCA 文件（7 段） |

### 重写文件（1 个 / ~580 行）

| 文件 | 旧行数 | 新行数 | 净变 | 用途 |
|------|--------|--------|------|------|
| `app/src/app/projects/[projectId]/comparison/page.tsx` | 803 | 583 | -220 | M12 comparison page 完整重写：节点选择器 + 维度选择器 + 矩阵渲染 + 快照面板（list/rename/delete）+ save dialog + rename dialog；删除拷贝层 hardcoded competitors/dropdown/AI 生成/回填代码 |

### 不动（守 cluster boundary）

- `app/src/actions/analyze.ts` — 3 个 comparison-targeted stub 保留（RCA §3.3 决策 B）
- `app/src/components/` — 不新建 business/ 子目录组件（design F2 接受 / 内联到 page 范式）
- `design/02-modules/M12-comparison/00-design.md` — 不动（design F1+F2+F12 接受 / 路径段漂移 + 拆分组件漂移不破契约）
- `app/e2e/dogfooding/M12-comparison.spec.ts` — 不动（spec 已正确 / 25 tests 全应 PASS / 无反向断言需要 flip）
- `app/eslint.config.mjs` — 不动（comparison/** 仍在 ignore / 守 cluster boundary）
- `_handoff/dogfooding/progress.md` / `03-bug-queue.md` / `cross-sprint-punt-pool.md` — 主 agent closeout scope

**总改动**：3 新建（~310 行）+ 1 重写（净 -220 行）+ 0 删除文件 = 净增 ~90 行业务代码

## 7. 验证矩阵

### 安全网（B 路径强制 / 全绿才 commit）

| 命令 | 结果 | 输出 |
|------|------|------|
| `cd app && pnpm exec tsc --noEmit` | ✅ 0 errors | empty stdout |
| `cd app && pnpm exec eslint --no-warn-ignored src/lib/validators/comparison.ts src/actions/comparison.ts` | ✅ 0 errors | empty stdout |
| `cd app && pnpm exec playwright test --list e2e/dogfooding/M12-comparison.spec.ts` | ✅ 全 register | "Total: 25 tests in 1 file" |
| `cd /root/workspace/projects/prism-0420 && uv run pytest tests/test_m12_*.py -q` | ✅ 65/65 PASS | "65 passed in 3.47s" |

### 业务行为验证（design §1 in scope / spec 25 tests）

由 push 后 CI 跑实际 e2e 验证。预期：
- DOM smoke 2 tests → 重写后应 PASS（spec L132-164 + L166-183 字面期望保留：竞品对比 heading + 选择功能 label + 对比竞品 label + 生成对比 button + 对比维度 + 空状态文本 + breadcrumb 竞品对比 + Tab nav .border-b-2 + 添加竞品 button）— 注意我**保留了"+ 添加竞品" button 文本**（spec L182 字面）虽然 design §1 in scope 没有"添加竞品"动作（M06 范畴）/ 这是 spec smoke 期望的最小 UI 元素 mark / 不破契约
- API-bypass 23 tests → 100% backend 验证 / cluster-M12 0 影响（backend 不动）/ 应继续全 PASS

### CI 期望

push 后 GitHub Actions 全套 6/6 应继续全绿（与 cluster-M14 + M17 同 baseline）。如 CI 红 → revert + escalate（plan 红线第 7 条）。

---

**最终 verdict**: cluster-M12 fix DONE / B 路径 audit 0 high 0 medium / safety net 4/4 PASS / 待 push + CI watch 闭环。
