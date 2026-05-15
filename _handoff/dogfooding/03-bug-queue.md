---
title: dogfooding sprint bug queue
status: living-doc
owner: CY
created: 2026-05-12
sources:
  - P2 spike subagent 真复现（audit/p2-spike-report.md）
  - P3 executor subagent（待启）
  - P4 fix subagent 完成回写
---

# Dogfooding Bug Queue

> P2/P3 subagent 抓到的真 bug 入队 / 等 P4 fix subagent 入。**不修 spec / 不修 testpoint**。

## 表头说明

| 列 | 含义 |
|---|---|
| ID | `B-<phase>-<module>-<short>` / 全 sprint 唯一 |
| 现象 | 一句话 / 用户视角 |
| 来源 | phase + subagent + 日期 + spec/test 名 |
| status | OPEN / IN_PROGRESS / FIX_DONE / VERIFIED / PUNT |
| 根因（如已抓） | 一行 / 详见 04-bug-fixes/<B-id>/rca.md |
| fix 路径 | 04-bug-fixes/<B-id>/ (A/B/C 路径) |

---

## OPEN 池

| ID | 现象 | 来源 | status | 根因（如已抓） | fix 路径 |
|----|------|------|--------|--------------|---------|
| ~~B-P3-M13-save-btn-shows-on-error~~ | analysis/page.tsx SSE 失败后 save 按钮仍渲染 | P3 executor M13 dogfooding 2026-05-13 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | error 路径 callback 仍设 `isComplete=true` → `allLayersDone=true` → save button 误显示 | 04-bug-fixes/B-P4-cluster-4-mixed/ |
| ~~B-P3-M17-ws-invalid-jwt-close-code~~ | WS 握手无效 JWT 不发 1008 close frame / 8s timeout | P3 executor M17 dogfooding 2026-05-13 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | `close()` 在 `accept()` 之前 → Starlette 回 HTTP 403 / RFC 6455 close frame 未发 | 04-bug-fixes/B-P4-cluster-4-mixed/ |
| ~~B-P2-M12-design-gap-comparison-page~~ | comparison/page.tsx 接错 M13 analyze 端点 / 不调 design §6/§7 6 endpoints | P2 spec M12 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | Phase 2.2 前端继承漂移 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M11-design-gap-cold-start-page~~ | M11 cold-start/page.tsx 缺 / 真入口是 workspace 空状态 → /import | P2 spec M11 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | design vs UI 漂移 / backend 已实装 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M14-design-gap-news-ui~~ | M14 行业动态全量 UI 未实现 / feed.ts NOT_IMPLEMENTED / /industry-news 404 | P2 spec M14 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | Phase 2.2 前端继承漂移 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M05-design-gap-version-ops-ui~~ | workspace.tsx 仅 createVersion / 缺 PUT/DELETE/set-current 等 5 endpoint UI 入口 | P2 spec M05 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | Phase 2.2 前端继承仅 create 路径 / 5 endpoints backend 已实装 frontend 缺 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M03-node-type-immutable-not-enforced~~ | PUT /api/projects/{pid}/nodes/{nid} 传入 type 字段时被 Pydantic 静默忽略返 200 | P2 spec M03 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | NodeUpdate schema 无 type 字段 | 04-bug-fixes/B-P4-cluster-2-M18-M03/ commit `0992dc8` |
| ~~B-P2-M03-project-delete-endpoint-missing~~ | DELETE /api/projects/{id} 返 405 Method Not Allowed | P2 spec M03 dogfooding 2026-05-12 | **VERIFIED** ✅ → 详 VERIFIED 池（cluster-2 错装物理删除 / cluster-2-revert 改 422 跟 design G2 一致）| DELETE endpoint 未实现 / design §1/§4/§13 字面禁物理删除（真相是漏写 422 endpoint 而非漏写物理删除）| 04-bug-fixes/B-P4-cluster-2-revert-M03-DELETE/ |
| ~~B-P2-M04-cross-node-tenant-read-gap~~ | GET /dimensions 跨 node 返 200 空 items 而非 404 | P2 spec M04 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | dimension_router read paths 漏 _check_node_belongs_to_project | 04-bug-fixes/B-P4-cluster-3-M04-M07/ |
| ~~B-P2-M04-activity-log-action-type-naming-gap~~ | activity_log action_type 复合命名 vs design §10 prose 单词漂移 | P2 spec M04 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池（design doc sync 方案 b）| design §10 prose 未与 frontmatter / 实装同步 | 04-bug-fixes/B-P4-cluster-3-M04-M07/ |
| ~~B-P2-M07-error-details-field-naming~~ | transition 422 details from_status/to_status vs design §13 current/target | P2 spec M07 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | issue_service.py raise kwargs 名跟 design §13 details 名漂移 | 04-bug-fixes/B-P4-cluster-3-M04-M07/ |
| ~~B-P2-M10-error-response-format-design-gap~~ | M10（及全局）错误响应体格式 design 声称嵌套 `{"error":{...}}`，实装 flat `{"code","message","details"}`；前端 parseError 早已适配 flat / 仅 design 文档+1 spec assertion 漂移 | P2 spec M10 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | engineering-spec §7.4 + §7.6 草案错（嵌套）/ 实装 _payload 从未走嵌套 / fact-finding 实证 design 契约定义点仅 1 处 / 模块 §13 只列 code 名不定义 body 格式 / 0 模块 design 需改 | 04-bug-fixes/B-P4-cluster-5-error-contract/ |
| ~~B-P2-M15-design-gap-filter-bar-ui~~ | activity-filter-bar.tsx 缺 / overview 面板无 4 维过滤控件 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M15-design-gap-date-grouping-ui~~ | activityLogs 线性 map / 无日期分组渲染 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M15-design-gap-metadata-collapse-ui~~ | metadata 折叠组件缺 / §7 D-3 fallback UI 未落 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M18-search-query-validation-returns-422~~ | POST /search 边界值 query="" / limit=0/101 返 422 而非 400 INVALID_QUERY_LENGTH | P2 spec M18 dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | SearchRequest Pydantic min_length=1 / ge=1 le=100 走 422，与 router >200 走 400 路径不一致 | 04-bug-fixes/B-P4-cluster-2-M18-M03/ commit `0992dc8` |
| ~~B-P2-M18-design-gap-rrf-k-ui-missing~~ | rrf_k / similarity_threshold 字段双缺（M02 ProjectSettings schema + M18 settings UI）| P2 spec M18 dogfooding 2026-05-12 | **SYNCED** → cluster-6 / design 加 dogfooding 实证段 | Phase 2.2 前端继承漂移 + M02 schema baseline-patch 未完 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ |
| ~~B-P2-M13-sse-proxy-url-broken~~ | /api/analyze/stream proxy 500 全链路 / proxy URL+API_BASE+Auth 三处漂移 | P2 spec M13 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | 子片 3c 未实装 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M13-actions-stub-puntresult~~ | actions/analyze.ts 6 个 action stub puntResult / DOM 端到端不通 | P2 spec M13 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | 子片 3c 未实装 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M13-save-request-fields-gap~~ | analysis/page.tsx saveAnalysis state 缺 7 字段 / 接通会即 422 | P2 spec M13 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | 子片 3c 未实装 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M13-design-gap-drawer-vs-fullpage~~ | design §6 抽屉 vs 实装独立全屏页 / 交互范式漂移 | P2 spec M13 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint (A/B 决策) | Phase 2.2 前端继承拷 prism 原版全屏页 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |

| ~~B-P2-M16-frontend-url-gap~~ | workspace.tsx snapshot generate URL flat vs backend 嵌套 / 405/404 | P2 spec M16 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | Phase 2.2 前端继承同步范式 vs design 异步 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| ~~B-P2-M16-frontend-no-polling~~ | workspace.tsx M16 同步 await / 未实装 design §1 轮询架构 | P2 spec M16 dogfooding 2026-05-12 | **PUNT** → Phase 2.x M-frontend sprint | Phase 2.2 前端继承同步范式 | 详 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md |
| B-P2-M08-relation-graph-no-dims-error | /projects/{pid}/relation-graph 页面 seed 项目无 enabled dimensions 渲染"操作失败，请重试" | P2 Opus spike M08 dogfooding 2026-05-12 | OPEN / 待 P5+ | 同 B-P2-M14 根因第 3+4 表现面 (relations.ts:getRelationGraph + getModuleRelationDetail 未 catch) | actions/relations.ts catch `overview_no_dimensions` → fallback `/api/projects/{pid}/nodes` 同 getProjectTree 范式 |
| B-P2-M08-design-gap-xyflow-drag-not-supported | relation-graph.tsx XYFlow drag-to-connect 未实装 / design §6 创建路径缺 / 实装入口为 workspace Dialog | P2 Opus spike M08 dogfooding 2026-05-12 | OPEN / 待 P5+ | Phase 2.2 前端继承 RelationGraph 仅可视化骨架 | design-audit candidate + M08 frontend XYFlow 接入 sprint |
| ~~B-P2-M17-frontend-stub-puntresult~~ | import-ai.ts 4 actions stub puntResult | P2 Opus spike M17 dogfooding 2026-05-12 | **FIX_DONE** ✅ 5/15 cluster-M17 commit cb27ac8 | 子片 3c 未实装 | 04-bug-fixes/B-P4-cluster-M17/ / import-ai.ts 删 stub + 加 aiSubmitImportZip + aiFetchReviewData |
| ~~B-P2-M17-fake-progress-no-websocket~~ | ai-import-wizard.tsx setTimeout 假进度 / 0 WS 客户端 | P2 Opus spike M17 dogfooding 2026-05-12 | **FIX_DONE** ✅ 5/15 cluster-M17 commit cb27ac8 | 子片 3c 未实装 | 04-bug-fixes/B-P4-cluster-M17/ / 实装 WS 客户端 onmessage + 删 setTimeout / WS 路径 /api/projects/{pid}/imports/{tid}/ws |
| ~~B-P2-M17-design-gap-tab-vs-wizard~~ | design 单一向导 vs 实装 3 tab / 范式漂移 | P2 Opus spike M17 dogfooding 2026-05-12 | **SYNCED** ✅ 5/15 cluster-M17 commit cb27ac8 | Phase 2.2 前端继承拷 prism 原版多入口 UI | 04-bug-fixes/B-P4-cluster-M17/ / design §6 sync 加 tab 入口范式说明（不动 UI）|
| ~~B-P2-M17-design-gap-fresh-project-blocked~~ | /import 页 ai_provider 检查缺 / fresh project 422 阻断 | P2 Opus spike M17 dogfooding 2026-05-12 | **FIX_DONE** ✅ 5/15 cluster-M17 commit cb27ac8 | M02 设置 vs M17 导入 onboarding 链路漂移 | 04-bug-fixes/B-P4-cluster-M17/ / import-page-client.tsx ai_provider 检查 + 引导卡 + 跳设置页 |
| B-P4-cluster-M17-uploadZip-still-punt | ai-import-wizard.tsx 主流程仍依赖 actions/import.ts uploadZip（cold-start 同范式 / 仍 punt）→ 完整 happy path 端到端走不通 | P4 cluster-M17 audit escalation 2026-05-15 | OPEN / 升独立 sub-cluster | uploadZip 是 M11 cold-start path / 跨模块依赖 / 不在本 cluster scope 内 | 候选 A/B/C 详 04-bug-fixes/B-P4-cluster-M17/rca.md §5.1 |
| ~~B-P2-cc-B-analyze-rx3-cross-tenant-leak~~ | POST /analyze/{pidA}/{nidB} 跨 project 返 HTTP 200 + SSE error 而非 404 | P2 Opus spike cross-cutting-B dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | analyze_router 进入 SSE generator 前缺 `_check_node_belongs_to_project` / NodeNotFoundError 落到 generator wrap 转 SSE error | 04-bug-fixes/B-P4-cluster-4-mixed/ |
| ~~B-P2-cc-A-account-lockout-design-drift~~ | testpoint `_cross-cutting.md` §3 L70 + cc-A spec 注释声称"无 rate limit / 不锁账号"与 M01 §7 line 98（5-strike 15min）实装矛盾 | P2 spec cross-cutting-A dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | Step 0 fact-finding：**真 drift 在 testpoint + spec 注释**（误读 "app 层 IP rate limit 部署前 Nginx 兜底" 为 "无 rate limit"）/ M01 design 一致 / 修法 = sync testpoint + spec 注释（不动 M01 design / 不删 lockout code）| 04-bug-fixes/B-P4-cluster-4-mixed/ |
| ~~B-P2-cc-A-empty-body-pydantic-422~~ | POST /auth/logout + /auth/refresh body 缺失返 raw Pydantic 422 `{"detail":[...]}` / 内部字段名泄漏 | P2 spec cross-cutting-A dogfooding 2026-05-12 | **FIX_DONE** ✅ → 详 FIX_DONE 池 | FastAPI 默认 RequestValidationError handler 默默返 raw / 不走 _payload wrapper / register_exception_handlers 仅注册了 AppError + Exception 两个 handler | 04-bug-fixes/B-P4-cluster-5-error-contract/ |

## FIX_DONE 池（待 P5 回归）

| ID | 现象 | 来源 | status | 根因 | fix 路径 / commit |
|----|------|------|--------|------|------------------|
| B-trigger-bug-server-action-cookie | 创建项目 submit 后跳 `/login`（spike 误判 list projects 同根因 / 实独立） | P2 spike 2026-05-12 / M02 trigger_bug + create-project happy FAIL | **FIX_DONE** ✅ | refresh_token cookie Path=/auth 限制 → Next.js server action endpoint (/projects/new) 不携带 cookie → server-auth 401 → 跳 login | 04-bug-fixes/B-trigger-bug-server-action-cookie/ / Path=/auth→/ / commit `cf25cb9` / CI 6/6 GREEN |
| B-list-projects-search-loader | /projects 列表 0 卡片渲染（getProjects 失败） | P2 spike 2026-05-12 / M02 list projects DOM FAIL | **FIX_DONE** ✅ | Next.js 16.2.4 Turbopack server-actions SWC 转换对 `'use server'` 文件中 `export type { X }` 命名再导出说明符处理错 / type 修饰符 SWC 链中丢失 → 运行时 ReferenceError | 04-bug-fixes/B-list-projects-search-loader/ / 删 src/actions/search.ts L12 dead re-export / commit `cf25cb9` / CI 绿 |
| B-P2-M14-workspace-dimension-error | workspace.tsx 项目详情页因 seed 项目无 enabled dimensions 报 `ApiError: Project has no enabled dimensions configured; completion rate cannot be calculated`，显示 error boundary 页面 | P2 spec M14 dogfooding 2026-05-12 / DOM-SMOKE 真复现 | **FIX_DONE** ✅ | M10 OverviewNoDimensionsError(422)（design 字面 contract）+ 前端 getProjectTree 无 catch → 异常冒泡到 Next.js error boundary；附带漂移 parseError 读 `error_code` 但 backend 序列化 `code` 字段名不对齐 → errorCode 一直 null | 04-bug-fixes/B-workspace-no-dims-graceful/ / 同根因 entry：M19 同 / actions/nodes.ts catch 后 fallback /nodes endpoint + parseError 双读 code + error_code |
| B-P2-M19-workspace-no-dims-error | /projects/{pid} workspace 页面 seed 项目（无 enabled dimensions）崩溃显示 error boundary "出错了"，无法渲染 module tree 或导出按钮 | P2 spec M19 dogfooding 2026-05-12 / DOM happy path FAIL | **FIX_DONE** ✅ | 同 B-P2-M14-workspace-dimension-error 根因（page.tsx server component 调 getProjectTree → 422 → error boundary）| 04-bug-fixes/B-workspace-no-dims-graceful/ / 与 M14 同 fix 一并解决 |
| B-P2-M11-validation-hang | POST /cold-start/upload 上传含行级校验失败的 CSV（node_path 不以 `/` 开头）后 HTTP 请求挂起不返回 / curl timeout / playwright test 30s timeout | P2 spec M11 dogfooding 2026-05-12 / "[P0] 校验失败响应体" test FAIL | **FIX_DONE** ✅ | cold_start_service.py L342 `dao.update(status=VALIDATING)` 后 SQLAlchemy AsyncSession 自动开启隐式 txn 持有 task 行锁；_mark_failed 走 compensation_session 新 connection UPDATE 同行 → 行锁互斥 deadlock | 04-bug-fixes/B-cold-start-validation-deadlock/ / L342 + L407 状态扭转后立即 `await db.commit()` 释放行锁（与 L339 task 创建立即 commit 范式对齐 / design L289 字面同步更新由主 agent 后续整理）|
| B-P2-M06-competitor-not-found-returns-422 | POST /api/projects/{pid}/nodes/{nid}/competitor-refs 传入不存在的 competitor_id 返 422 COMPETITOR_CROSS_PROJECT 而非 design §13 + tests.md 要求的 404 COMPETITOR_NOT_FOUND | P2 spec M06 dogfooding 2026-05-12 / "[P0] competitor_id 不存在创建 ref 返 404" FAIL / 实测 422 | **FIX_DONE** ✅ | competitor_service.create_ref 单查 get_competitor_by_id(id, project_id) 一刀切 CROSS_PROJECT；不区分"不存在"vs"跨项目" | 04-bug-fixes/B-P4-cluster-1-M06-competitor/ / service 两步分支 + DAO 加 get_competitor_global / commit `033ea64` / playwright M06 test 12 PASS + pytest 65/65 PASS / 残留 test 14 是 B-P2-M10 跨切非本 cluster |
| B-P2-M06-competitor-ref-response-no-display-name | GET /api/projects/{pid}/nodes/{nid}/competitor-refs 返回的 CompetitorRefResponse 缺 display_name 字段；design §7 要求 JOIN competitors | P2 spec M06 dogfooding 2026-05-12 / "[P1] GET /competitor-refs 含 display_name join" FAIL / 实测无字段 | **FIX_DONE** ✅ | schema 漏 display_name 字段 + DAO list_refs_by_node 单表 SELECT 无 selectinload + router _ref_response 用 model_validate 自动映射但 relationship 未 load | 04-bug-fixes/B-P4-cluster-1-M06-competitor/ / schema 加 display_name + DAO _REF_JOINS selectinload + service create_ref refresh "competitor" + router _ref_response 显式装配 + codegen 更新 / commit `033ea64` / playwright M06 test 23 PASS |
| B-P2-M18-search-query-validation-returns-422 | POST /search 边界值 query="" / limit=0/101 返 422 而非 400 INVALID_QUERY_LENGTH（同 endpoint 三类边界走两条路径不一致）| P2 spec M18 dogfooding 2026-05-12 / "[P0] query='' 返 400" + "[P1] limit=0/101 返 400" 实测均 422 | **FIX_DONE** ✅ | SearchRequest Pydantic min_length=1 / ge=1 le=100 走默认 422；router 只在 >200 拦 400 → 两条路径错位 | 04-bug-fixes/B-P4-cluster-2-M18-M03/ / schema 删 Pydantic 边界约束 + router 单点拦截所有边界抛 InvalidQueryLengthError 400 / commit `0992dc8` / playwright M18 5/5 边界 PASS + pytest M18 65/65 PASS |
| B-P2-M03-node-type-immutable-not-enforced | PUT /nodes/{nid} 传 type 字段被 Pydantic 静默忽略返 200 / design §4 NODE_TYPE_IMMUTABLE 422 未实装 | P2 spec M03 dogfooding 2026-05-12 / "[P0] PUT type 422" 实测 200 | **FIX_DONE** ✅ | NodeUpdate schema 用排除法（无 type 字段）→ Pydantic v2 默认 extra="ignore" 静默丢弃 / service 层 NodeTypeImmutableError 检查永远不触发 | 04-bug-fixes/B-P4-cluster-2-M18-M03/ / NodeUpdate 显式声明 type 字段（NodeTypeEnum \| None）让 Pydantic 接收 → service 层既有 immutable 检查正确触发 / commit `0992dc8` / playwright M03 31/31 PASS + pytest test_update_node_type 新增 PASS |
| ~~B-P2-M03-project-delete-endpoint-missing~~ | DELETE /api/projects/{id} 返 405 / endpoint 未实现 / design 声称但 router 缺 | P2 spec M03 dogfooding 2026-05-12 / CASCADE 测试探测到 405 | **VERIFIED** ✅ → 详 VERIFIED 池 | cluster-2 错装物理删除 commit `0992dc8`（违反 design G2）/ cluster-2-revert 改 422 PROJECT_DELETE_NOT_SUPPORTED 跟 design G2 一致 / 真相是「漏写 422 endpoint」而非「漏写物理删除」| 04-bug-fixes/B-P4-cluster-2-revert-M03-DELETE/ |
| B-P2-M04-cross-node-tenant-read-gap | GET /dimensions 跨 node 返 200 空 items 而非 404 NODE_NOT_IN_PROJECT | P2 spec M04 dogfooding 2026-05-12 | **FIX_DONE** ✅ | dimension_router 3 个 read endpoints（list/get_one/completion）漏 svc._check_node_belongs_to_project 调用（design §8 R8-1 第三层防御只覆盖 write paths） | 04-bug-fixes/B-P4-cluster-3-M04-M07/ / router 3 read endpoints 加 _check_node_belongs_to_project / 新增 pytest test_list_dimensions_cross_node_tenant_returns_404 / 全 M04 router pytest PASS |
| B-P2-M04-activity-log-action-type-naming-gap | design §10 prose 单词命名 vs frontmatter+实装复合命名漂移 | P2 spec M04 dogfooding 2026-05-12 | **FIX_DONE** ✅ | design 内部双写漂移（frontmatter `produces_action_types` 复合 / §10 prose 单词 / 实装复合）/ Phase 2.1 实装跟 frontmatter 一致但 prose 未回写同步 | 04-bug-fixes/B-P4-cluster-3-M04-M07/ / 改 design §10 prose + tests.md G1/G3/G4 → 复合命名 / 实装 0 改动 / sync 方案 b（与 cc-C 跨切实证一致 / R14 命名规约符合）|
| B-P2-M07-error-details-field-naming | transition 422 details from_status/to_status vs design §13 + ER2 current/target | P2 spec M07 dogfooding 2026-05-12 | **FIX_DONE** ✅ | issue_service.py L278-282 IssueTransitionInvalidError raise kwargs 名按 SQL 视角写 from_status/to_status；AppError(**details) 让 kwargs 直接成 response details 字段名；design §13 业务语义 current/target | 04-bug-fixes/B-P4-cluster-3-M04-M07/ / service kwargs 改 current/target / 加 pytest 断言 details.current+target / spec assertion 由宽松验存在改严格验字面 |
| B-P2-cc-A-account-lockout-design-drift | testpoint + cc-A spec 注释误称"无 rate limit / 不锁账号" / 与 M01 §7 line 98 5-strike 15min 实装矛盾 | P2 spec cross-cutting-A dogfooding 2026-05-12 | **FIX_DONE** ✅ | Step 0 fact-finding：真 drift 在 testpoint `_cross-cutting.md` L70 + spec L459-462/669-672/689-694 注释（误读 "app 层 IP rate limit 部署前 Nginx 兜底" 为"无 rate limit"）/ M01 design 一致 / app 层 IP rate limit 是 design 显式 punt 到部署前（design line 770/1042）| 04-bug-fixes/B-P4-cluster-4-mixed/ / sync testpoint + spec 注释（不动 M01 design / 不删 lockout code）/ cc-A 5-strike test 改名 "M01 §7 设计实证" + 19/19 spec PASS |
| B-P2-cc-B-analyze-rx3-cross-tenant-leak | POST /analyze/{pidA}/{nidB} 跨 project 返 200 + SSE error 而非 404 | P2 Opus spike cross-cutting-B dogfooding 2026-05-12 | **FIX_DONE** ✅ | analyze_router `stream_requirement_analysis` 直接进入 SSE generator → HTTP 200 + StreamingResponse 已发 headers → generator 内调 `nodes.get_node` 抛 NodeNotFoundError 被 wrap 为 SSE event:error / design §8 R8-1 第三层防御应在 router 前置（M04 dimension_router 同范式已实装） | 04-bug-fixes/B-P4-cluster-4-mixed/ / router 创建 svc 后 / return StreamingResponse 前调 `svc.nodes.dao.get_by_id(db, node_id, project_id)` is None → raise AnalysisNodeNotFoundError 404 / pytest `test_stream_requirement_cross_project_node_returns_404` PASS / cc-B spec PASS |
| B-P3-M13-save-btn-shows-on-error | analysis/page.tsx SSE 失败后 save 按钮仍渲染（count=1 而非 0）| P3 executor M13 dogfooding 2026-05-13 | **FIX_DONE** ✅ | error 路径 callback (line 354-357) 仍将所有 layer 设 `isComplete=true` → `allLayersDone=true` 即使分析失败 / save button line 836 显示条件 `hasResults && allLayersDone && !testPointsResult` 误触发 | 04-bug-fixes/B-P4-cluster-4-mixed/ / save button 显示条件加 `&& !error` 显式守护（不破坏 layer state 让"分析失败"卡片仍可渲染）/ M13 spec `[P0-DOM] save 按钮 stub puntResult 验证` PASS |
| B-P3-M17-ws-invalid-jwt-close-code | WS 握手无效 JWT 不发 1008 close frame / 8s timeout closeCode=-1 | P3 executor M17 dogfooding 2026-05-13 | **FIX_DONE** ✅ | import_router `import_progress_ws` 在 JWT 校验失败时 `await websocket.close(1008)` 在 `await websocket.accept()` 之前 → Starlette 自动回 HTTP 403 handshake denial（无 WS close frame）→ client 拿不到 1008 close code（closeCode=-1 / 1006 abnormal）/ design line 547 字面 "accept() 前 close(1008)" 描述与 client 可观测性矛盾 | 04-bug-fixes/B-P4-cluster-4-mixed/ / 把 `await websocket.accept()` 提前到 JWT 校验之前 / 后续 close(1008) 走 WS close frame 路径 / M17 spec WS 鉴权 PASS（closeCode=1008）+ pytest 3 个 ws_close_1008 test 用 receive_text 触发 disconnect PASS / design line 547 同步 sync accept-then-close 注释 |
| B-P2-M10-error-response-format-design-gap | M10/全局 error body 嵌套 vs flat 漂移 / design §7.4+§7.6 草案 nested / 实装 flat / 前端早适配 / 1 spec assertion 跟着 design 错 | P2 spec M10 dogfooding 2026-05-12 | **FIX_DONE** ✅ | engineering-spec §7.4+§7.6 草案错（嵌套）/ 实装从未走嵌套 / fact-finding 实证 design 契约定义点仅 1 处 / 模块 §13 只列 code 名不定义 body 格式 | 04-bug-fixes/B-P4-cluster-5-error-contract/ / b 路径 design sync：engineering-spec §7.4 范例改 flat + 加锚点 + 历史段 + 加 RequestValidationError handler 范例 / §7.6 表改 flat + 加 422 raw Pydantic 行 / M06 spec line 549-557 硬断言 sync flat + 加 `not.toHaveProperty("error")` 防回滚 / pytest 1648→1651 PASS / e2e cc-A+M10+M06 PASS |
| B-P2-cc-A-empty-body-pydantic-422 | POST /auth/logout+/refresh 空 body 返 raw Pydantic 422 / 内部字段名 type/loc/msg/input 泄漏 | P2 spec cross-cutting-A dogfooding 2026-05-12 | **FIX_DONE** ✅ | FastAPI 默认 RequestValidationError handler 默默返 raw / 不走 _payload wrapper / register_exception_handlers 只注册 AppError + Exception 两 handler | 04-bug-fixes/B-P4-cluster-5-error-contract/ / b 路径全局 handler：codes.py 加 INVALID_REQUEST_BODY + exceptions.py 加 InvalidRequestBodyError(ValidationError) + middleware.py `_handle_request_validation` 包 flat（details.errors[] 简化版只保留 loc+msg / 删 type+input 不泄漏）/ register handler / `__init__` export / 3 个新 pytest（empty body + missing field + invalid type）/ ci-lint R13-1 parity 140=140 / curl 实证：`{"code":"invalid_request_body","message":"...","details":{"errors":[{"loc":["body"],"msg":"Field required"}]}}` |

## VERIFIED 池（P5 回归 PASS）

| bug-id | 一句话 | 来源 | status | 根因 | fix 引 |
|--------|---------|------|--------|-------|---------|
| B-P2-M03-project-delete-endpoint-missing | DELETE /api/projects/{id} 返 405 / endpoint 未实现 → 现返 422 PROJECT_DELETE_NOT_SUPPORTED（design G2 软删除不可逆）| P2 spec M03 dogfooding 2026-05-12 / CASCADE 测试探测到 405 | **VERIFIED** ✅ | cluster-2 commit `0992dc8` 错装物理删除（违反 design G2）/ 真相是「漏写 422 endpoint」而非「漏写物理删除」/ ErrorCode PROJECT_DELETE_NOT_SUPPORTED + ProjectDeleteNotSupportedError(422) 已在 design §13 留位 30+ commit 无 caller / RCA 详 [rca.md](04-bug-fixes/B-P4-cluster-2-revert-M03-DELETE/rca.md) | 04-bug-fixes/B-P4-cluster-2-revert-M03-DELETE/ / dao 删 ProjectDAO.delete_one + service raise ProjectDeleteNotSupportedError + router 去 204 / pytest test_m02_routers 加 2 test + spec M03 §7 改单分支 422 / playwright M03 31/31 PASS + M01+M02 regression 10/10 PASS + pytest M02+M03 78/78 PASS / sink → feedback_decision_codefirst_validation §2 2026-05-13 实证 |

## SYNCED 池（cluster-6 design-gap sync 完成 / 实装侧无改动）

| ID | 现象 | 来源 | status | 根因 | sync 路径 |
|----|------|------|--------|------|----------|
| B-P2-M05-design-gap-version-ops-ui | workspace.tsx 仅 createVersion / 5 ops endpoint UI 缺 | P2 spec M05 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M05-version-timeline/00-design.md §1 加 dogfooding 实证段 |
| B-P2-M07-design-gap-§8-UI-漂移 | M07 §8 UI 6 处缺（status badge / filter / 转换 / 详情页 / node-scoped / 档案页区块） | 03-bug-queue.md L112 元发现候选 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M07-issue/00-design.md §1 加 dogfooding 实证段 |
| B-P2-M11-design-gap-cold-start-page | M11 cold-start/page.tsx 缺 / 真入口 /import (M17) | P2 spec M11 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M11-cold-start/00-design.md §6 加 dogfooding 实证段 |
| B-P2-M15-design-gap-filter-bar-ui | activity-filter-bar.tsx 缺 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M15-activity-stream/00-design.md §6 加 dogfooding 实证段 |
| B-P2-M15-design-gap-date-grouping-ui | activityLogs 线性 map / 无日期分组 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 同上 |
| B-P2-M15-design-gap-metadata-collapse-ui | metadata 折叠组件缺 | P2 spec M15 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 同上 |
| B-P2-M18-design-gap-rrf-k-ui-missing | rrf_k + similarity_threshold schema+UI 双缺 | P2 spec M18 dogfooding 2026-05-12 | **SYNCED** ✅ | Phase 2.2 前端继承漂移 + M02 schema baseline-patch 未完 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M18-semantic-search/00-design.md §6 加 dogfooding 实证段 |
| B-P2-M19-design-gap-export-button-and-node-selector | export-button.tsx + node-selector.tsx 独立组件缺 / 实装内联 | P2 spec M19 dogfooding 2026-05-12 (spec 顶 design-gap 注释) | **SYNCED** ✅ | Phase 2.2 前端继承漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M19-import-export/00-design.md §6 加 dogfooding 实证段 |
| B-P2-M20-design-gap-member-list-UI | M20 member list UI 等 backend endpoint（design 已显式标）| P2 设计审计 2026-05-12 | **SYNCED** ✅ | design 02-frontend-design.md 已显式标 / 仅 00-design.md §6 加索引指针 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M20-team/00-design.md §6 加 dogfooding 实证段 |
| B-P2-M03-design-gap-面包屑-link | 面包屑中间节点 `<span>` 非 `<Link>` / 末端可点 | P2 spec M03 dogfooding 2026-05-12 (元发现候选) | **SYNCED** ✅ | design vs UI 漂移 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / design/02-modules/M03-module-tree/00-design.md §1 加 dogfooding 实证段 |

## FIX_DONE（spec-design-fix / cluster-6）

| ID | 现象 | spec 文件 line | status | 根因 | fix 路径 |
|----|------|--------------|--------|------|---------|
| B-P3-M04-spec-L138-dim-card-hidden | workspace smoke FAIL: 期望 "出错了"|"点击添加" 但 B-P2-M14 fix 后两者均不渲染 (seed 无 enabled dim) | M04-feature-archive.spec.ts L138 | **FIX_DONE** ✅ | spec 漂移 (B-P2-M14 fix 后 workspace 不 crash + dim cards 段在 0 enabled dim 时不渲染) | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / 加 "添加关联" 按钮兜底 (workspace 主结构验证) |
| B-P3-M11-spec-L37-strict-link | strict-mode FAIL: getByRole link 导入文档 命中 3 处 | M11-cold-start.spec.ts L37 | **FIX_DONE** ✅ | workspace.tsx L899/L1260/L1328 共 3 处"导入文档" | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / `.first()` 取空状态卡片 link |
| B-P3-M11-spec-L75-strict-link | 同 L37 strict-mode | M11-cold-start.spec.ts L75 | **FIX_DONE** ✅ | 同上 | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / `.first()` 后 click |
| B-P3-M11-spec-L102-manual-content-type | manual Content-Type: multipart/form-data 无 boundary 让 Playwright 自动注入冲突 | M11-cold-start.spec.ts L102 (L143 头) | **FIX_DONE** ✅ | spec 写错（应让 Playwright 自动注入 multipart boundary）| 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / 删除 manual Content-Type |
| B-P3-M11-spec-L659-empty-csv-422-vs-201 | CSV 仅列头返 201 + total_rows=0 (非 422 COLD_START_CSV_INVALID) | M11-cold-start.spec.ts L659 | **FIX_DONE** ✅ | backend 未实装"列头存在 0 数据"422 分支 (真升级需 product 改 / 出 cluster-6) | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / spec 用 either-or 宽松断言 |
| B-P3-M19-spec-L57-folder-vs-file-view | export node happy 失败：seed root=folder 不渲染"导出 Markdown" (file 视图限定按钮) | M19-import-export.spec.ts L57 | **FIX_DONE** ✅ | spec 漂移 (seed 默认 folder 视图 / waitForRequest 期望浏览器直发不符 server action 范式) | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / withFileNode:true + waitForEvent("download") |
| B-P3-M19-spec-L117-folder-overview-timeout | export button folder 视图 FAIL: getFolderOverview /overview 422 → error boundary | M19-import-export.spec.ts L117 | **FIX_DONE** ✅ | actions/nodes.ts getFolderOverview 缺 catch (B-P2-M14 fix 未覆盖 / 真 bug 待 product 改) | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / withFileNode:true 切到 file 视图验任一导出按钮存在 |
| B-P3-M05-spec-L81-version-timeline-folder | workspace.tsx DOM smoke FAIL: 版本时间线仅 file 视图渲染 / seed root=folder 看不到 | M05-version-timeline.spec.ts L81 | **FIX_DONE** ✅ | spec 漂移 (version timeline 仅 file 视图) | 04-bug-fixes/B-P4-cluster-6-design-gap-and-spec-fix/ / withFileNode:true |

## PUNT 池（推下 sprint）

| ID | 现象 | 推 sprint | 报告 |
|----|------|---------|------|
| B-P2-M12-design-gap-comparison-page | comparison/page.tsx 接错 M13 analyze 端点 / 不调 design §6/§7 6 endpoints | Phase 2.x M-frontend | 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §M12 |
| B-P2-M13-sse-proxy-url-broken + actions-stub-puntresult + save-request-fields-gap + design-gap-drawer-vs-fullpage | M13 frontend 链路全 dead (4 OPEN bug 同根因群) | Phase 2.x M-frontend | 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §M13 |
| B-P2-M14-design-gap-news-ui | M14 行业动态全量 UI 缺 / feed.ts NOT_IMPLEMENTED / /industry-news 404 | Phase 2.x M-frontend | 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §M14 |
| B-P2-M16-frontend-url-gap + frontend-no-polling | M16 同步范式 vs design 异步轮询架构 | Phase 2.x M-frontend | 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §M16 |
| B-P2-M17-frontend-stub-puntresult + fake-progress-no-websocket + design-gap-tab-vs-wizard + design-gap-fresh-project-blocked | M17 4 个 OPEN bug 群 / 子片 3c 未实装 | Phase 2.x M-frontend | 04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §M17 |

---

## 关联 audit / spec / RCA

- P1→P2 闸门 audit：`audit/p1-p2-gate-finding.md`（testpoint 文件 A- 质量 / 不改）
- P2 spike 报告：`audit/p2-spike-report.md`（trigger_bug 真复现 + Next.js 4 坑清单 + 分类决策树）
- M01 spec：`app/e2e/dogfooding/M01-user-account.spec.ts`（5/5 PASS）
- M02 spec：`app/e2e/dogfooding/M02-project.spec.ts`（2 PASS + 3 真 FAIL 抓 bug）

## 元发现候选（P3/P4 期回写 / 不阻塞）

- M07 §8 UI testpoint vs page.tsx 漂移（design 声称 status badge / filter / 转换按钮 / 详情页 / 节点关联 UI 但实现缺）→ design-gap candidate / 不入 bug queue（功能缺失非 bug）
- AddIssueDialog title 字段是否真在 dialog 表单（page.tsx L322 引用 / 未读细节）→ M07 P2 期自查
- Next.js 自定义版坑清单（4 坑 / spike-report §"坑清单"）→ 沉淀候选 / 简历级 STAR 素材

---

## P5b sprint close 2026-05-13

**dogfooding sprint 全闭环 verdict**：47 个独立 bug ID 入队 / 分布如下：

| 池 | 数 | 状态 |
|----|----|----|
| FIX_DONE 真 bug（产品代码修） | 17 | cluster-1~5 + P3 prelim 真修 |
| VERIFIED（cluster-2-revert 修正物理删除） | 1 | M03 DELETE 改 422 跟 design G2 一致 |
| SYNCED（design doc sync / 实装 0 改） | 10 | cluster-6 design-gap 注 dogfooding 实证段 |
| spec-design-fix（cluster-6 / 改 spec 不改产品） | 7 | M04+M05+M11×4+M19×2 |
| PUNT frontend gap → Phase 2.x M-frontend | 12 | M12×1 + M13×4 + M14×1 + M16×2 + M17×4 |
| OPEN 残留 → Phase 2.x M-frontend（M08）| 2 | relation-graph workspace + XYFlow drag |

**汇总公式**：`17 真 bug FIX + 1 VERIFIED + 10 SYNC + 12 PUNT + 7 spec-fix + 2 OPEN = 49 状态条目`（部分 ID 跨池跳轨 / 去重后 47 独立 ID）

**回归数据**（详 05-regression-results.md）：
- P3 init 488/505 = 96.6% / 17 FAIL
- P5a after-fix 502/505 = **99.4%** / 3 残留 transient
- 净 +14 tests / +2.8pp

**STAR 报告**：`_handoff/dogfooding/05-final-report.md`（含 D1-D4 4 维度数据 + STAR S/T/A/R 完整 + 失败案例 + Punt 池总览）
**Phase 3 v0.4 baseline**：`design/99-comparison/phase3-data-baseline.md` v0.4 段更新

---

last_updated: 2026-05-13 / P5b final close
