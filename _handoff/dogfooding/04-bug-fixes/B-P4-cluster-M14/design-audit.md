# cluster-M14 design audit (B 路径)

> dogfooding sprint / 2026-05-15 / Phase 2.x M-frontend cluster-M14
> 触 plan §3 B 路径自评 6 项风险：改动范围高 + 跨 ≥5 新文件 → B 路径自跑 audit
> 范围：B-P2-M14-design-gap-news-ui（industry-news 全量 UI 实装）

## 审计输入

| 文档 | 章节 | 校对内容 |
|------|------|---------|
| `design/02-modules/M14-industry-news/00-design.md` | §1 业务边界 / §3 数据模型 / §6 分层职责 / §7 API 契约 / §8 权限 / §9 DAO 豁免 / §10 activity_log / §13 ErrorCode | 全局豁免 / endpoint URL / Pydantic schema / 命名规约 |
| `design/02-modules/M14-industry-news/tests.md` | §1-§7 全 | DOM/API 路径期望 |
| `design/00-architecture/06-design-principles.md` | 原则 1-5 + 5 项约束清单 | tenant / 事务 / 异步 / 并发 / 全局豁免 |
| `api/routers/industry_news_router.py` 全 253 行 | 8 endpoints | URL / status code / response schema 真后端契约 |
| `api/schemas/industry_news_schema.py` 全 105 行 | NewsCreate / NewsUpdate / NewsResponse / NewsListResponse / NodeRef / NewsNodeLinkCreate / NewsNodeLinkResponse | schema 真名 + 字段类型 |
| `app/src/types/api.ts` § News* + NodeRef | openapi 生成 TS 类型 | 类型契约一致性 |
| `app/e2e/dogfooding/M14-industry-news.spec.ts` 全 653 行 | DOM smoke + 26 API-bypass | spec contract（DOM `/industry-news` 路径 + data-testid） |
| `app/src/actions/feed.ts`（保留 stub）+ workspace.tsx / overview/page.tsx / settings/page.tsx | feed_* 引用面 | feed.ts 决策依据 |
| `_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md` §M14 | 修法范围估算 | scope 守恒 |

## findings 表（4 字段：冲突级别 / 章节 / 冲突描述 / 处置建议）

| # | 级别 | design 章节 | 冲突描述 | 处置建议 |
|---|------|-------------|---------|---------|
| F1 | **low** | §6 分层职责表 | design §6 字面要求 components 落 `web/src/components/business/news-card.tsx` 等 `business/` 子目录；prism-0420 实装 `app/src/components/` 全部扁平（peer：issue-card.tsx / feed-card.tsx / dimension-card.tsx / ai-import-wizard.tsx 全 flat）/ design §6 路径在 prism v1 时代有意义，prism-0420 拷贝层未保留 business/ 子目录范式 | **接受 + 不动 design**：与 peer 业务组件保持一致更重要（Phase 2.2 已固化 flat 范式）；本 cluster 落 flat 路径 `components/news-card.tsx` / `news-form.tsx` / `node-link-picker.tsx`。design §6 路径段是历史草案，与本项目实际目录范式漂移，但不触契约/不破分层（仍是 component 层 / 非 page 层）。元规则：与 M17 cluster F5 `import-progress.tsx` 合并到 wizard 同范式（design 字面 vs 实装合并的低风险漂移）|
| F2 | **low** | §6 Page = `web/src/app/industry-news/page.tsx` | design 字面 `web/src/app/...`（prism v1 web/ 目录） vs prism-0420 实装 `app/src/app/...`（无 web/ 前缀，单 app 目录） | **接受**：cookbook 级路径漂移（项目全局已固化 / 与 /projects /teams 同级）；不触 design 文档 |
| F3 | **medium** | §6 Server Action `web/src/actions/industry-news.ts` | design 字面这个 file 不存在；同时 `actions/feed.ts` 是 NOT_IMPLEMENTED stub（prism v1 feed_items 工作流不对应 /api/news）；workspace.tsx + overview/page.tsx + settings/page.tsx 仍依赖 feed.ts 8 个签名（getFeedItems / confirmFeedItem / getFeedItemsByNode 等）| **DONE**：新建 `app/src/actions/industry-news.ts` 接通 8 endpoints；**保留 feed.ts 不动**（feed 域 ≠ news 域 / 删除 feed.ts 会破 3 个 caller 页 / 超 cluster 范围）。RCA §2.2 + §3 注明：feed/news 双域并存到子片 5 cleanup 或 feed UI 显式删除时再收敛 |
| F4 | **none** | §7 API contract（8 endpoints）| backend 实装 `api/routers/industry_news_router.py` 全部 8 endpoints 命中（GET /api/news / GET /api/news/{id} / POST / PUT / DELETE / POST/DELETE links / GET /api/nodes/{nid}/news）；request/response schema 全 typed via openapi.json 生成 `app/src/types/api.ts`；status code 201/200/204/404/409 全对齐 | **PASS**：design 契约 100% 对齐 backend；frontend 直接消费 OpenAPI 生成类型，无字符串硬编码 |
| F5 | **none** | §3 source_type='manual' CHECK 约束 | NewsCreate schema 字面不含 source_type 字段（design §7 字面注释：service 层强制 'manual'）；frontend NewsForm 也不暴露 source_type input | **PASS**：frontend 不传 source_type / backend service 强制 'manual' / CHECK 约束兜底 |
| F6 | **none** | §8 权限三层防御 | design §8 字面要求：Server Action 校 session（getServerAccessToken 已有 / serverApiFetch 401 自动 throw UnauthenticatedError → defineAction actionError 兜底 redirect /login）；Router require_user；Service _check_news_owner_or_admin。frontend 不提前隐藏 edit/delete 按钮（admin 可改任意 / 前端不知 role） | **PASS**：与 issue-card 范式一致 / 403 由 backend 返 / handleActionResult 显示用户友好错误 |
| F7 | **none** | §9 GLOBAL DATA — NO TENANT FILTER | frontend 调用全部不传 project_id（listNews / getNews / createNews / updateNews / deleteNews 5 个动作 + linkNewsToNode / unlinkNewsFromNode），与 design §9 全局豁免 + spec test L472 `[P0] IndustryNewsDAO 全局豁免：不接受 project_id 过滤参数` 红线一致 | **PASS** |
| F8 | **none** | §10 activity_log 命名规约（过去式）| frontend 不直接写 activity_log（M15 后端责任 / R-X1 自洽 / R14 守护后端 service） | **PASS** |
| F9 | **low** | spec L628 DOM smoke 断言 `/industry-news` 返 404 | 该 DOM smoke 测试字面：`expect(newsPageRes.status(), "design §6 声称的 /industry-news 路由应 404（未实现）").toBe(404)`；cluster-M14 实装后 `/industry-news` 是 200 / 该断言会 FAIL（变成 spec 自身的 design-gap 反向证据） | **PARTIAL / 报 main agent**：spec 测试本身把"design-gap"固化为 DOM 断言；cluster 范围**不改 spec**（PUNT-REPORT 字面 scope 是 frontend 实装 / spec-fix 走另一轨道 P5b spec-fix 池）。下一次 P5 regression / spec-fix sweep 应把该断言反向（404 → 200 or removed）。Trade-off：本 cluster 选**不修 spec**以维持 cluster boundary 清晰（cf. cluster-M17 design-audit F1 sync design 不动 UI 同范式），由 main agent 在 closeout commit 评估是否归入 punt pool 7-day rule。 |

**汇总**：0 high / 1 medium DONE / 3 low（2 接受不动 design + 1 spec 断言 PARTIAL）/ 5 PASS。无 high 冲突 / 不触 escalation 中止条件。

## 设计原则 5 条 + 5 约束清单核对

| 原则 / 清单 | 触发 | 实装 |
|------------|------|------|
| 1. SQLAlchemy schema 唯一真相源 | ❌ frontend 不触 | N/A |
| 2. 分层严格 | ✅ | server action → server-http-client → backend router；component 层不直 fetch；validator/schema 单独抽 lib/validators/news.ts |
| 3. 接口 Contract First | ✅ | endpoint URL 全用 design §7 + industry_news_router.py 字面真名；request/response types 全走 `components["schemas"]["News*"]` 自 openapi.json 生成 |
| 4. 状态机显式定义 | ❌ M14 design §4 明确无状态 | N/A |
| 5. 多人架构 4 维必答 | ✅ | tenant: 全局豁免（无 project_id 参数）/ 事务: N/A（M14 无多表事务）/ 异步: N/A（M14 全同步）/ 并发: N/A（M14 无乐观锁 / DB UNIQUE 兜底） |
| 清单 1: activity_log | ✅ | 后端责任 / frontend 不直写 |
| 清单 2: 乐观锁 version | ❌ | M14 design §4/§5 明确无 version 字段 |
| 清单 3: Queue payload tenant | ❌ | M14 无 Queue（design §12）|
| 清单 4: idempotency_key | ❌ | M14 design §11 明确无幂等需求 |
| 清单 5: DAO tenant 过滤 | **全局豁免** | frontend 不调 DAO；caller 不传 project_id 与 §9 GLOBAL DATA — NO TENANT FILTER 一致 |

无原则违反。

## R-X1 自洽（M14 不直 INSERT M03/M04/M06/M07 表）

frontend cluster 完全不触后端 service / 不破 R-X1。`linkNewsToNode` 走 POST `/api/news/{nid}/links` 由 backend `IndustryNewsService.link_node` 调 NewsNodeLinkDAO 写本模块独有表 `news_node_links`；node 存在校验跨模读 M03 走 service 层（M14 design §6 `_check_news_owner_or_admin` 不直查 M03 / `link_node` 调 NodeDAO get_one）/ R-X1 + R-X3 全自洽。

## escalation 中止条件检查

- ✅ 0 high 冲突 / 0 medium design 真破设计原则 / ADR-002 / ADR-004（F3 medium 是 caller 适配选择，不破 design）
- ✅ tsc 0 错（baseline 0 → after 0）
- ✅ eslint 0 错（6 个新文件 — `app/src/lib/validators/news.ts` + `actions/industry-news.ts` + `components/news-card.tsx` + `components/news-form.tsx` + `components/node-link-picker.tsx` + `app/industry-news/page.tsx` 全部不在 ignore 列表 / 全 fresh 编写不依赖拷贝层）
- ✅ playwright --list M14 PASS（27 tests registered / 无 syntax error）
- ✅ pytest M14 全套 106/106 PASS
- ✅ spec DOM smoke L628 断言反向（F9 PARTIAL）— 不修 spec / 由 main agent 评估
- ✅ design vs backend 0 conflict（F4 PASS / 100% 对齐）
- ✅ 改动总行数估算（见 RCA §6）≈ 850 行 / 全新建 / 0 删除
- ✅ subagent cost 远 < $9 cluster cap
- ✅ 无 A/B 决策升级（design vs spec / project-scoped vs global 等）— design §1/§9 已 ack 全局 / spec 期望 `/industry-news` 字面 URL / 一致

**verdict**：**PASS / B 路径 commit allowed**
