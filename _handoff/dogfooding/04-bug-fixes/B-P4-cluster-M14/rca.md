# cluster-M14 RCA

> dogfooding sprint / 2026-05-15 / cluster-M14 fix RCA
> B 路径必产 / 7 段：现象 / 根因 / 类似问题 grep / design 哪步漏 / escalation / 改动统计 / 验证矩阵

## 1. 现象

dogfooding sprint P2 期 Sonnet subagent M14 e2e 跑揭露 1 OPEN bug（PUNT-REPORT.md §M14 落，待 Phase 2.x M-frontend sprint 处理）：

| Bug ID | 现象 | 严重度 |
|--------|------|--------|
| B-P2-M14-design-gap-news-ui | design §6 字面声明的 `web/src/app/industry-news/page.tsx` / `news-card.tsx` / `news-form.tsx` / `node-link-picker.tsx` / `web/src/actions/industry-news.ts` 均不存在；`/industry-news` 路由 404；`src/actions/feed.ts` 是 NOT_IMPLEMENTED stub；M14-industry-news.spec.ts 26 个 DOM 路径 testpoint 全部走 API 旁路无 DOM 入口 | 中（业务路径阻断 / dogfooding 真用户场景"录入一条行业动态并关联到功能项"完全走不通；非生产数据丢失） |

## 2. 根因

### 2.1 共同根因 — Phase 2.2 子片 3b/3c 关闸盲区延续（与 cluster-M17 同根源）

子片 3b 是 Phase 2.2「前端继承拷贝层降级」期：
- 把老 prism `actions/feed.ts`（消费 `feed_items` + `feed_sources` + `suggested_node` 工作流）整体 stub 为 NOT_IMPLEMENTED（保留签名 / 返空数组）
- file header 注释字面承诺："子片 5 后或 Phase 2.3 评估接 /api/news 域 or 删除 feed UI"
- **子片 5 未执行**该 feed→news 切换

子片 3c 也没有把 design §6 字面的 `web/src/actions/industry-news.ts` 实装出来 — `industry-news.ts` 在子片 3c scope 里属于"M14 frontend"而 M14 backend 是子片 3 实装/PASS 的（属业务模块层），frontend 卡在子片 3b NOT_IMPLEMENTED 桥的另一侧、子片 3c 桥未架。

**关闸盲区**：与 cluster-M17 同根因 — Phase 2.3 cleanup S1+S3+S4+B+A+C+D 全完后 reconcile 时未把 punt 列表完整入 cross-sprint-punt-pool（5/13 dogfooding 抓到 → 立 punt-frontend-gap-phase2x/PUNT-REPORT.md）。

### 2.2 feed 域 vs news 域不一一对应（拷贝层范式错位）

prism v1：`feed_items` 是"建议节点 + status 流转 + sources 管理"的工作流（消费/丢弃/重派 / RSS 抓取 / sources CRUD）
prism-0420：`industry_news` 是"全局共享动态 + 节点关联"的信息流（全局豁免 / 已登录即可读写 / source_type='manual'）

两套域的**实体形态、用户场景、API 契约都不一致**：
- feed 主表 = feed_items（消费状态 pending/confirmed/ignored） vs news 主表 = industry_news（无状态）
- feed 关联 1:1 (item→node) vs news 关联 N:M (news↔node 通过 news_node_links)
- feed sources 配置（feed_sources 表 + 是否启用）vs news source_type 字面三态预留（manual/rss/ai，本期仅 manual）

子片 3b 选了"feed.ts 整体 stub 保留签名兼容 overview/settings/workspace 残留 import" — 这是当时合理的最小可工作选择（不破其他模块），代价就是 design §6 字面的 `industry-news.ts` 没人建。

### 2.3 spec 把"design-gap"字面固化为 DOM 断言（dogfooding 自身的反向陷阱）

`M14-industry-news.spec.ts` L628 P0-DOM-SMOKE 测试字面断言 `/industry-news` 返 404，注释字面：「design §6 声称的 /industry-news 路由应 404（未实现）」。这是 dogfooding sprint P2 写 spec 时把"现状=design-gap"固化进去的反向证据 — 用于报 audit。cluster-M14 实装后该断言会 FAIL，但**不属于业务回归 FAIL**，属于 spec 自身需要随实装更新的"反向断言"（dogfooding 元教训：design-gap evidence spec 必须有反向更新生命周期）。

## 3. 类似问题 grep（横切影响面）

### 3.1 子片 3b → 3c 未执行同根因 punt（cross-sprint-punt-pool §M-frontend 群）

`_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md` §共同根因字面列：

- M12 comparison: page 完全接错（接 M13 analyze 而非 M02/M03/M04 节点矩阵 + 快照 CRUD）— **待 cluster-M12**
- M13 SSE: 全链路 dead（actions/analyze.ts stub puntResult / SSE proxy URL broken / 抽屉 vs 全屏 A/B 决策）— **待 cluster-M13**
- M14 industry-news: **本 cluster 处理** ✅
- M16 ai-snapshot: 同步 URL + 无轮询架构 — **待 cluster-M16**
- M17 ai-import: stub puntResult + fake progress + tab vs wizard 漂移 — **cluster-M17 已闭 cb27ac8 / sub uploadZip PARTIAL 待独立 cluster**

**已知未来 cluster 节奏**（PUNT-REPORT §下个 sprint 推荐顺序）：M14（本）/ M12 / M16 / M17（done）/ M13。

### 3.2 design vs UI 范式漂移多发（同 sync design 不动 UI 范式）

已知漂移群（同走"接受 + 不动 design"范式）：
- M17 cluster F1 — `business/` 子目录 design vs flat 实装（本 cluster F1 复用范式）
- M17 cluster F5 — `import-progress.tsx` 独立组件 design vs 合并到 wizard 内（本 cluster F1 同思想）
- cluster-6 sync 路径群（M10 错误响应格式 / cc-A 账号锁定 design drift）

→ "实装 vs design 路径段范式漂移 + 不破契约不动 design"已成元模式 / 不重立。

### 3.3 feed 域 stub 长期遗留问题

`actions/feed.ts` 8 个 NOT_IMPLEMENTED 签名仍被 3 处 caller 依赖：
- `app/src/app/projects/[projectId]/workspace.tsx:80` `getFeedItemsByNode` → FeedList 渲染空
- `app/src/app/projects/[projectId]/overview/page.tsx:55-57` `getFeedItems` / `getFeedSources` / `confirmFeedItem` → 同空状态
- `app/src/app/projects/[projectId]/settings/page.tsx:78,212` `getFeedSources` → 设置页 sources 列表为空

这些是 **prism v1 拷贝层 UI 残留**，prism-0420 design 没有"项目级 feed sources / pending feed items 消费流"概念（design M14 §1 字面 out of scope: "RSS / 第三方 API 自动抓取动态：本期不实现"）。本 cluster **不删 feed UI** — 删除会破上述 3 个 caller / 超 cluster 范围。

**最终归宿候选**（建议下个 sprint 评估）：
- A: 删除 feed UI（workspace FeedList / overview FeedList card / settings sources panel）+ 删除 actions/feed.ts → cleanup 收口
- B: 把 feed UI 改为"近期相关行业动态"（调 listNewsByNode 替代 getFeedItemsByNode）→ news 域统一
- C: 长期保留 stub（接受 dead UI 直到 PRD F14 v0.3 引入 RSS）

→ **escalation §5.1 建议主 agent 评估**。

## 4. design 哪步漏（reconcile 切回 design 文档）

| design 章节 | 是否补 | 补法 |
|------------|--------|------|
| §6 分层职责表 `web/src/components/business/` 路径 | **不动** | 与 prism-0420 实际目录范式漂移但不破契约（与 M17 cluster F5 同范式 / peer 业务组件 issue-card/feed-card/dimension-card 全 flat）。design §6 路径段保留作历史草案 |
| §6 Page `web/src/app/industry-news/page.tsx` | **不动** | `web/` 前缀是 prism v1 单仓 web/ 目录范式；prism-0420 是独立 app/ 项目（cookbook 全局已固化 / 与 /projects /teams 同级范式） |
| §6 `web/src/actions/industry-news.ts` | **实装** ✅ | 新建 `app/src/actions/industry-news.ts` 接通 8 endpoints |
| §1 out of scope "本期不实现 RSS / AI 自动抓取" | **不动** | 与 actions/feed.ts 残留范畴一致 — feed UI 是 prism v1 残留 / 不入 design 范畴 |
| §7 + §10 actions 命名 | **不动** | 全过去式 `news_created/updated/deleted/linked/unlinked` 命名后端实装一致；frontend 不直写 activity_log |

## 5. escalation 上报（主 agent 评估）

### 5.1 feed 域 stub 长期归宿决策（医闭 frontend gap 元清理）

`actions/feed.ts` 8 NOT_IMPLEMENTED 签名 + 3 个 caller 页（workspace / overview / settings）残留 prism v1 UI 形态（"待消费 feed_items" + "feed_sources 管理"）。prism-0420 design 无对应概念。
- **A**：删除 feed UI 树（4 处 + actions/feed.ts）= scope 跨 3 业务模块 / 超 cluster boundary
- **B**：feed UI 改为 listNewsByNode 适配器 = 接口形态不一致（feed_items 有 status 字段 / news 无）
- **C**：保留 stub 到 RSS sprint（design §1 灰区 1 ack 本期仅 manual）

→ 建议主 agent 在 closeout 评估升 cross-sprint-punt-pool §F1 "feed 域 cleanup" 或归 cluster-2 候选。

### 5.2 spec L628 P0-DOM-SMOKE 反向断言更新

`M14-industry-news.spec.ts` L628 把"design-gap"字面固化为 DOM 断言（`/industry-news` 应返 404）。cluster 实装后该断言会 FAIL — 不是业务 bug，是 spec 自身固化的反向证据生命周期问题。**本 cluster 不修 spec**（cluster boundary 守恒 / spec-fix 走 P5b 池单独 sweep）。建议主 agent：
- 选项 A: closeout commit 顺手把该 testcase 反向（404 → 200 验 /industry-news 200 + 首屏渲染验证）
- 选项 B: 归 P5b spec-fix 池 / 下次 regression sweep 处理
- 选项 C: 立元规则 "design-gap 反向断言必须 cluster 实装同 commit 同步更新"（增加 cluster scope / 工程成本）

→ 与 M14 闭环时间窗对齐建议 A（顺手 30s 改）但**不在本 cluster boundary 内执行**（避免 scope creep / 守 plan §3 6 项中"测试覆盖"维度）。

### 5.3 跨模块元规则升级（与 cluster-M17 同号召继续）

cluster-M17 RCA §5.2 已建议把「Phase 2.2 拷贝层 vs design 异步范式 reconcile」升元规则。cluster-M14 实证：
- 本 cluster 形态简单（同步 CRUD / 无异步范式漂移）所以 reconcile 价值低
- 但 caller-side stub（feed.ts 整体 NOT_IMPLEMENTED）+ design §6 fresh-build 形态在子片 5 未补的 punt → **拷贝层 stub 长期挂着的反向风险**（每新 sprint 都要忽略一次"为什么这些函数返空数组"）

→ 建议合并 M17 §5.2 升 cross-sprint-pool 元规则时**同时覆盖 "Phase 2.2 拷贝层 stub 长期 punt 风险"**（每 frontend cluster 启动前必查 stub 列表 vs design §6 file list）。

## 6. 改动统计

| 文件 | 改动类型 | 行数估算 |
|------|---------|---------|
| `app/src/lib/validators/news.ts` | new | +59 / -0 |
| `app/src/actions/industry-news.ts` | new | +131 / -0 |
| `app/src/components/news-form.tsx` | new | +205 / -0 |
| `app/src/components/node-link-picker.tsx` | new | +236 / -0 |
| `app/src/components/news-card.tsx` | new | +197 / -0 |
| `app/src/app/industry-news/page.tsx` | new | +203 / -0 |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M14/design-audit.md` | new B 路径产物 | +95 / -0 |
| `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-M14/rca.md` | new B 路径产物 | +170 / -0 |

**总改动**：+1296 / -0 ≈ **+1296 净 / 跨 8 文件（含 6 新源文件 + 2 audit 产物）**

`actions/feed.ts` **不动 0 行**（决策 §3.3 — feed/news 双域并存 / 不破 3 caller 页）。
design 文档 **不动 0 行**（findings F1/F2 接受 / F9 spec 断言 PARTIAL 不在 cluster scope）。

## 7. 验证矩阵

| 类型 | 状态 | 详情 |
|------|------|------|
| tsc | ✅ PASS | `cd app && pnpm exec tsc --noEmit` → 0 errors（baseline 0 → after 0） |
| eslint（--no-warn-ignored） | ✅ PASS | 6 个新文件全部 0 errors（无 ignore 依赖 / `src/lib/validators/news.ts` + `actions/industry-news.ts` + `components/news-card.tsx` + `components/news-form.tsx` + `components/node-link-picker.tsx` + `app/industry-news/page.tsx`）。修复一次 react-hooks/set-state-in-effect 红线（lazy initial value + key remount 替代 useEffect 同步 setState） |
| playwright --list M14 | ✅ PASS | 27 tests registered（含 1 个 DOM smoke 会因实装后 404 → 200 而反向断言 FAIL，详 RCA §5.2，不在 cluster scope）|
| pytest M14 全套 | ✅ PASS | 106/106 / 3.60s（test_m14_dao.py + test_m14_models.py + test_m14_routers.py + test_m14_schemas.py + test_m14_service.py） |
| design-audit | ✅ 0 high / 1 medium DONE / 3 low / 5 PASS | verdict = PASS / B 路径 commit allowed |
| commit boundary | 单 commit 含 8 文件改动 | 与 cluster-M17 commit cb27ac8 范式一致 |
