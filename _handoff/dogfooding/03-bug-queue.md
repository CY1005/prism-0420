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
| B-P2-M11-design-gap-cold-start-page | design §6 列 `web/src/app/projects/[pid]/cold-start/page.tsx`（M11 专用 CSV 向导）但实现缺该 page；真实冷启动入口为 workspace.tsx 空状态卡片 → /import（M17 zip/AI 向导），M11 /cold-start/upload 后端端点存在但无专用前端向导页 | P2 spec M11 dogfooding 2026-05-12 | OPEN / 待 P4 入 | design vs UI 漂移：M11 前端向导页未实现 / 后端端点已实现 | design-audit candidate |
| B-P2-M14-design-gap-news-ui | M14 行业动态全量 UI 未实现：design §6 声称的 `web/src/app/industry-news/page.tsx`、`news-card.tsx`、`news-form.tsx`、`node-link-picker.tsx`、`web/src/actions/industry-news.ts` 均不存在；`src/actions/feed.ts` 是全量 NOT_IMPLEMENTED stub；/industry-news 路由 404 | P2 spec M14 dogfooding 2026-05-12 | OPEN / 待 P4 入 | Phase 2.2 前端继承时 feed 域（来自 prism 原版）与 prism-0420 /api/news 域不对应，未实现映射；未完成清理（feed.ts 注释"子片 5 后切换"但子片 5 未执行 M14 UI）| design-audit + M14 frontend 实现 sprint |
| B-P2-M05-design-gap-version-ops-ui | workspace.tsx 仅暴露 createVersion 操作（对应 POST /versions）；design §1 In scope 声称的版本更新（PUT）/ 删除（DELETE）/ 标记当前版本（set-current）在前端无 UI 入口；set-current 按钮未实现 | P2 spec M05 dogfooding 2026-05-12 / workspace.tsx grep 确认缺 set-current / deleteVersion / updateVersion UI 按钮 | OPEN / 待 P4 入 | design vs UI 漂移：Phase 2.2 前端继承仅实现 create 路径，其余 5 endpoints 后端已实装但前端入口缺失 | design-audit candidate + M05 frontend UI sprint |
| B-P2-M06-competitor-not-found-returns-422 | POST /api/projects/{pid}/nodes/{nid}/competitor-refs 传入不存在的 competitor_id（如全零 UUID）时后端返 422 COMPETITOR_CROSS_PROJECT 而非 design §13 规定的 404 COMPETITOR_NOT_FOUND；service 层 _check_competitor_belongs_to_project 在 competitor 不存在时走了跨项目逻辑而非先判断存在性 | P2 spec M06 dogfooding 2026-05-12 / "[P0] API 旁路: competitor_id 不存在创建 ref 返 404 COMPETITOR_NOT_FOUND" FAIL / 实测 422 | OPEN / 待 P4 入 | competitor_service._check_competitor_belongs_to_project 先查 project_id 匹配，不存在的 UUID project_id=null → 触发跨项目 422 而非先返 404 | api/services/competitor_service.py _check_competitor_belongs_to_project：先检查 competitor 存在性（not found → 404）再检查 project_id 归属 |
| B-P2-M03-node-type-immutable-not-enforced | PUT /api/projects/{pid}/nodes/{nid} 传入 type 字段时被 Pydantic 静默忽略返 200（type 值不变），而非 design §4 要求的 422 NODE_TYPE_IMMUTABLE。NodeUpdate schema 直接排除 type 字段，Pydantic v2 默认 ignore 未知字段 | P2 spec M03 dogfooding 2026-05-12 / "[P0] PUT 改 type 返 422 NODE_TYPE_IMMUTABLE" 实测 200 | OPEN / 待 P4 入 | NodeUpdate schema 无 type 字段 / Pydantic v2 model_config extra="ignore" 默认值 → 静默丢弃；design §4 要求显式 422 拒绝 | api/schemas/node_schema.py NodeUpdate + api/services/node_service.py：接收到 type 字段时检查并抛 NodeTypeImmutableError |
| B-P2-M03-project-delete-endpoint-missing | DELETE /api/projects/{id} 返 405 Method Not Allowed；当前 /api/projects/{id} 只有 GET + PUT；design §7 声称 nodes.project_id ON DELETE CASCADE 但无法通过 API 验证删除入口 | P2 spec M03 dogfooding 2026-05-12 / CASCADE 测试探测到 405 | OPEN / 待 P4 入 | DELETE /api/projects/{project_id} endpoint 未实现；OpenAPI spec 确认 /api/projects/{project_id} 仅 GET+PUT | api/routers/project_router.py 添加 DELETE endpoint；project_service.delete_project() 实现 |
| B-P2-M06-competitor-ref-response-no-display-name | GET /api/projects/{pid}/nodes/{nid}/competitor-refs 返回的 CompetitorRefResponse 缺少 display_name 字段；design §7 明确声称"CompetitorRefResponse 含 join 自 competitors.display_name 字段"但实际响应只有 competitor_id，前端 CompetitorReferenceList 只能通过前端 join competitors 列表补全名称（不符合 API contract） | P2 spec M06 dogfooding 2026-05-12 / "[P1] API 旁路: GET /competitor-refs 返回含 display_name join 的 CompetitorRefResponse" FAIL / 实测 response 无 display_name 字段 | OPEN / 待 P4 入 | CompetitorRefResponse schema 未实现 join competitors.display_name；DAO list_refs_by_node 未做 JOIN / 仅返回 competitor_refs 自身字段 | api/schemas/competitor.py CompetitorRefResponse 加 display_name 字段 + DAO list_refs_by_node JOIN competitors |
| B-P2-M04-cross-node-tenant-read-gap | GET /api/projects/{pid}/nodes/{nid}/dimensions 当 node_id 属于其他 project 时返 200 空 items（而非 design §8 声称的 404）；dimension_router.py L109 注释写明"不校验 node 归属（只读 P3）"，跳过 _check_node_belongs_to_project；同 user 拥有多 project 时跨 node 访问不被 404 拦截 | P2 spec M04 dogfooding 2026-05-12 / "[P0] 跨 tenant：userA token 访问 projectA URL 但 node_id 属 projectB" WARN / 实测返 200+empty | OPEN / 待 P4 入 | dimension_router.py list_by_node 仅做 project-level auth check（check_project_access），未调 service._check_node_belongs_to_project；design §8 T2 声称"404 NOT_FOUND 不暴露越权"但实现跳过该 check | api/routers/dimension_router.py list_by_node 加 node 归属 check（参考 write endpoints 的 svc._check_node_belongs_to_project 调用）|
| B-P2-M04-activity-log-action-type-naming-gap | activity_log action_type 实际为 "dimension_record_created" / "dimension_record_updated" / "dimension_record_deleted"（复合命名），而 design §10 声称 action_type="create"/"update"/"delete"（简单动词）；activity-stream API 返回字段名为 "items" 而非 design 声称的 "events" | P2 spec M04 dogfooding 2026-05-12 / activity_log 断言实测发现 | OPEN / 待 P4 入 | dimension_service.py 写 activity_log 时 action_type 用 {target_type}_{past_tense} 复合命名惯例，与 design §10 表格单列 "create/update/delete" 不一致；activity-stream router 返回 key 为 items | 文档同步（design §10 更新 action_type 命名）或 service 规范化为简单动词 |

## FIX_DONE 池（待 P5 回归）

| ID | 现象 | 来源 | status | 根因 | fix 路径 / commit |
|----|------|------|--------|------|------------------|
| B-trigger-bug-server-action-cookie | 创建项目 submit 后跳 `/login`（spike 误判 list projects 同根因 / 实独立） | P2 spike 2026-05-12 / M02 trigger_bug + create-project happy FAIL | **FIX_DONE** ✅ | refresh_token cookie Path=/auth 限制 → Next.js server action endpoint (/projects/new) 不携带 cookie → server-auth 401 → 跳 login | 04-bug-fixes/B-trigger-bug-server-action-cookie/ / Path=/auth→/ / commit `cf25cb9` / CI 6/6 GREEN |
| B-list-projects-search-loader | /projects 列表 0 卡片渲染（getProjects 失败） | P2 spike 2026-05-12 / M02 list projects DOM FAIL | **FIX_DONE** ✅ | Next.js 16.2.4 Turbopack server-actions SWC 转换对 `'use server'` 文件中 `export type { X }` 命名再导出说明符处理错 / type 修饰符 SWC 链中丢失 → 运行时 ReferenceError | 04-bug-fixes/B-list-projects-search-loader/ / 删 src/actions/search.ts L12 dead re-export / commit `cf25cb9` / CI 绿 |
| B-P2-M14-workspace-dimension-error | workspace.tsx 项目详情页因 seed 项目无 enabled dimensions 报 `ApiError: Project has no enabled dimensions configured; completion rate cannot be calculated`，显示 error boundary 页面 | P2 spec M14 dogfooding 2026-05-12 / DOM-SMOKE 真复现 | **FIX_DONE** ✅ | M10 OverviewNoDimensionsError(422)（design 字面 contract）+ 前端 getProjectTree 无 catch → 异常冒泡到 Next.js error boundary；附带漂移 parseError 读 `error_code` 但 backend 序列化 `code` 字段名不对齐 → errorCode 一直 null | 04-bug-fixes/B-workspace-no-dims-graceful/ / 同根因 entry：M19 同 / actions/nodes.ts catch 后 fallback /nodes endpoint + parseError 双读 code + error_code |
| B-P2-M19-workspace-no-dims-error | /projects/{pid} workspace 页面 seed 项目（无 enabled dimensions）崩溃显示 error boundary "出错了"，无法渲染 module tree 或导出按钮 | P2 spec M19 dogfooding 2026-05-12 / DOM happy path FAIL | **FIX_DONE** ✅ | 同 B-P2-M14-workspace-dimension-error 根因（page.tsx server component 调 getProjectTree → 422 → error boundary）| 04-bug-fixes/B-workspace-no-dims-graceful/ / 与 M14 同 fix 一并解决 |
| B-P2-M11-validation-hang | POST /cold-start/upload 上传含行级校验失败的 CSV（node_path 不以 `/` 开头）后 HTTP 请求挂起不返回 / curl timeout / playwright test 30s timeout | P2 spec M11 dogfooding 2026-05-12 / "[P0] 校验失败响应体" test FAIL | **FIX_DONE** ✅ | cold_start_service.py L342 `dao.update(status=VALIDATING)` 后 SQLAlchemy AsyncSession 自动开启隐式 txn 持有 task 行锁；_mark_failed 走 compensation_session 新 connection UPDATE 同行 → 行锁互斥 deadlock | 04-bug-fixes/B-cold-start-validation-deadlock/ / L342 + L407 状态扭转后立即 `await db.commit()` 释放行锁（与 L339 task 创建立即 commit 范式对齐 / design L289 字面同步更新由主 agent 后续整理）|

## VERIFIED 池（P5 回归 PASS）

（空）

## PUNT 池（推下 sprint）

（空）

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
