---
title: prism-0420 跨 session 交接
status: living
owner: CY
last_updated: 2026-05-10 (**Post-Phase-2.3 Cleanup Sprint 1 完成 / Sprint 4 启动中 / Sprint 2+3 等 CY**)
purpose: 上一 session 留给下一 session 的"接着做什么 + 怎么做"——避免冷启动 Claude 凭印象拍板
---

# Next-session handoff

> **冷启动 Claude 读这份**：先读本文件 → 再读 `design/00-roadmap.md` 看真实进度 →
> 再读 `design/00-phase-gate.md` 看下一闸门 → 再决定从哪条 prompt 起手。

## 0. 状态快照（更新于 2026-05-10 post-Sprint-1-完成）

**Post-Phase-2.3 Cleanup 计划进度**（plan 在 `_handoff/post-phase23-cleanup-plan.md`）：
- ✅ **Sprint 1（C-FOLLOW-UP 前端基础债 8 项）**：全 ✅ DONE 2026-05-10 / commits dae2760→2e21b63
  - Task 1.1 dae2760 — P22-3c-6 ExportPayload 收口（serverApiPostDownload wrapper / 真因重定 = 前端 client 不支持 binary，非后端 schema 缺）
  - Task 1.2 2b890dd — StatsResult→ActionResult 统一（删 services/project-stats.ts 死文件）
  - Task 1.3 0507ffa — findInTree 抽 lib/tree-utils.ts（5 unit tests / 3 caller 收敛）
  - Task 1.4 ad1d040 — actions 命名规约统一（issues list/get / competitor-references 资源前缀）
  - Task 1.5 5afc6d1 — search.ts withAuthRedirect helper 复用
  - Task 1.6 — 跳过（已在 af6f78e 子 sprint C 完成）
  - Task 1.7 — 状态变更后 moot（Task 1.2 重写 proxy 后无需 anchor）
  - Task 1.8 2e21b63 — eslint ignore 渐进还债 25 项 + _ 前缀立规
  - 守护：vitest 20→30 / tsc 174→172 / eslint 全仓 0/0
  - cross-sprint pool STILL_PUNT 39→31 / DONE 32→40

- ⏸ **Sprint 2（B-FOLLOW-UP 集成 e2e 基础设施）**：暂缓
  - 需 backend (FastAPI 8000) + frontend (Next.js 3000) 服务端运行才能验 Playwright e2e 真断言
  - CY 在线时启动两端 server / Claude 即可起 prompt：`_handoff/post-phase23-cleanup-plan.md` "Sprint 2"
  - DB seed fixture / storageState login share / e2e #2-#10 / pytest-benchmark 1000 seed / R 范式第 7 数据点

- ⏸ **Sprint 3（A 后置债 / CI 接通）**：阻塞 GH PAT workflow scope
  - 本地已写完 `.github/workflows/ci.yml`（7 jobs / pgvector+redis service container / codegen-drift / deps-audit cron）
  - **CY 加 PAT workflow scope 后跑**（5 min 人工）：
    `cd /root/workspace/projects/prism-0420 && git add .github/workflows/ci.yml && git commit -m "Sprint 3 — ci.yml workflow file" && git push`
  - 然后接通 e2e job + 关闸门 5

- ▶️ **Sprint 4（模块真漏洞 high/medium 9 项）**：启动中（不依赖 server）
  - 4A M04 dimension 集中（IntegrityError 存量 + target_type enum + 联合索引 + db.get→DAO）
  - 4B M18 worker 真接 + cron PCT + batch INSERT FROM unnest
  - 4C 跨模块 race + write_event e2e + M07 detach（**M07 detach 需 CY 拍 A/B**）

**下一步推荐**：
- CY 在线时优先做 **Sprint 3** 5min 人工（PAT scope）+ 启 servers（Sprint 2）
- 不在线时 Claude 继续推 Sprint 4


## 0. 状态快照（更新于 2026-05-09 post-Phase-2.3-4-子-sprint-完成 / 闸门 5 PARTIAL）

- **Phase 2.3 4 子 sprint A+B+C+D 串跑完成**（commits a42a786 → 9a4b192 → af6f78e → 07e4007）：
  - **A 工程规约补完** ✅ `a42a786`：03-cicd / 04-observability / 05-security 三 spec accepted-minimal → accepted（§8.0 12/12 ✅）/ api/core/config.py prod CORS guard validator（§8.6 punt #1 关闭）/ spec 06 §2 路径前缀+REFRESH_COOKIE_PATH=/auth+logout body=None 备注（punt #3+#5 关闭）/ roadmap §8.0 12 checkbox 全 ✅
  - **🔴 A 后置债**：`.github/workflows/ci.yml`（7 jobs / pgvector+redis service container / codegen-drift guard / deps-audit cron）已写完但 GH PAT 缺 `workflow` scope，留本地 untracked。**CY 给 PAT 加 workflow scope 后跑**：`cd /root/workspace/projects/prism-0420 && git add .github/workflows/ci.yml && git commit -m "Phase 2.3 子 sprint A 补 — ci.yml workflow file" && git push`
  - **B 集成 e2e + 性能基线 PARTIAL** ✅ `9a4b192`：@playwright/test 1.59.1 + chromium 1217 装入 / app/playwright.config.ts / app/e2e/01-auth-flow.spec.ts 2 真跑 PASS / app/e2e/02-10 9 skeleton（test.describe.skip + 业务断言注释完整）/ tests/perf/test_baseline.py 2 smoke PASS + 1 skeleton / app/vitest.config.ts exclude e2e/ / .gitignore Playwright artifacts
  - **B-FOLLOW-UP punt**：e2e #2-#10 完整断言（DB seed fixture + storageState login share + page object）+ pytest-benchmark + 1000 seed perf + R1+R2 范式 + CI e2e job 接通（service container 全栈装配）
  - **C frontend-polish PARTIAL** ✅ `af6f78e`：P22-3b-1 withAuthRedirect 抽 horizontal helper（src/lib/server-action-helpers.ts + 11 actions 文件去重 inline + unused import 清扫）/ P22-3c-7 logActivity / logActivityAuto no-op 兼容层删（analysis/page.tsx 2 caller 删 + getActivityLogs 保留 total ?? 0）/ P22-4-2 isTeamOwner 死代码删
  - **C-FOLLOW-UP punt**：P22-3c-1+2 result 类型统一 + P22-3c-3+4 命名规约 + P22-3c-5 findInTree 抽 lib/tree-utils.ts + **P22-3c-6 export.ts ExportPayload schema 待 CY 拍**（A 补 ExportResponse Pydantic schema vs B 删 consumer UI 旧字段）+ P22-3c-8 project-stats-proxy cleanup + eslint ignore 渐进还债 10+ 项
  - **D perf 评估** ✅ `07e4007`：三选项 A 模式呈现 → 自决选项 C **DEFER_TO_POST_LAUNCH**（shadow+上线优先+数据驱动）；C 类 12 项 status 升级 STILL_PUNT → DEFER_TO_POST_LAUNCH（cross-sprint pool 元发现 #2 性能 sprint 黑洞**关闭**）；触发条件落字面（真负载 P95 > 500ms 告警 / 多租户启用 / Phase 3 数据回流）；audit/phase23-perf-evaluation.md / cross-sprint-punt-pool.md 同步
  - **守护**：backend pytest **1629 PASS** / vitest 4 files **20 tests PASS** / Playwright e2e **2 PASS** / perf smoke **2 PASS** / pre-commit hooks 全过

- **下一步推荐**：**上线 sprint 三路径任 CY 拍**
  - **路径 A（最快上线）**：CY 加 PAT workflow scope + push ci.yml（5 分钟）→ 直接进上线 sprint（前置 1+2 一并打包 / cost $8-12 / 2-3 天 / 含 e2e #2-10 完整断言 + perf 1000 seed + docker-compose prod + Caddyfile + deploy.yml）
  - **路径 B（C-FOLLOW-UP 先做）**：先清前端债 cost $2-3 / 0.5 天 / 但不解锁上线
  - **路径 C（推荐 / 解耦最清晰）**：CY push ci.yml 5 分钟 → B-FOLLOW-UP 单跑 sprint（cost $5-8 / 1.5 天 / 完整 e2e 10 路径 + perf 1000 seed + R1+R2 范式）→ 上线 sprint（cost $3-5 / 0.5-1 天 / 仅 deploy 模板+冒烟）

- **三类 punt 进 cross-sprint pool**（上线 sprint 立项依据）：
  - **B-FOLLOW-UP**（高优先级 / 阻塞闸门 5 第 1+2+3 项）：e2e + DB fixture + perf seed + R 范式
  - **C-FOLLOW-UP**（中优先级 / 不阻塞上线）：P22-3c-1~6+8 + eslint ignore 渐进还债
  - **post-launch perf**（低优先级 / 上线后启动）：M+1 月 Phase 3 数据回流后立 / C 类 12 项重新评估

- **闸门 5 状态汇总**：§8.0 ✅ / §8.1 5 项部分（e2e+perf 部分 / CI 文件齐备但未接通 / docker-compose prod 推上线 sprint）→ Phase 2.3 整体 PARTIAL，**上线 sprint 待立**

---

## 0a. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-5-完成 / Phase 2.2 100%）

- **Phase 2.2 子片 5 完成 / Phase 2.2 100% 关闸**（D 类 #3 IssueResponse + #15 DimensionResponse join 真装配 + Phase 2.2 关闸 audit + SR-P22-2/3/4/5 立规 sink + cross-sprint pool 41→39）：
  - **D 类 #3 装配**：Issue model 加 `created_by_user` + `assigned_to_user` relationship（`lazy="raise"` 防 async 隐式 lazy load）+ IssueDAO `_JOINS = (selectinload(node), selectinload(created_by_user), selectinload(assigned_to_user))` 应用到 `list_by_project` + `get_by_id` + IssueService.create/update/transition 三处 mutation 后 `refetch via dao.get_by_id` 拿带 joins 的实例 + router `_resp` 显式装配 join 字段
  - **D 类 #15 装配**：DimensionRecord model 加 `dimension_type` + `updated_by_user` relationship（同 lazy="raise"）+ DimensionDAO `_JOINS = (selectinload(dimension_type), selectinload(updated_by_user))` 应用到 `list_by_node` + `get_by_id` + `get_one` + DimensionService.create/update_with_lock 两处 mutation 后 refetch + router `_record_response` 显式装配
  - **6 backend e2e**（SR-CLEANUP-3 防假覆盖 / 字面断言响应 JSON 含 join 字段真值）：
    - M07: test_list_issues_join_fields_populated / test_get_issue_join_fields_populated / test_floating_issue_node_name_is_none
    - M04: test_list_dimensions_join_fields_populated / test_get_dimension_join_fields_populated / test_update_dimension_join_fields_after_refetch
  - **前端真用 join 字段**：当前 `app/src/app/projects/[projectId]/issues/page.tsx` + dimension 渲染均**未消费** join 字段 / OpenAPI types 已声明 optional / 任意 UI 增强自然激活 / DOM e2e 不触发本子片
  - 累计 pytest 1623 → 1629 PASS / 5 skipped / 0 failed / eslint 0 errors / ruff 0 issues
  - **Phase 2.2 关闸 audit 写完**：design/audit/p22-pilot-template-validation.md status: in_progress → completed / §3e 子片 5 findings + §6 关闸结论
  - **SR-P22 立规 sink 4 项**：SR-P22-2/4 合并 sink → feedback_subagent_sprint.md §4 附录（前端继承 R1=1 Sonnet+R2=1 Opus + R2 跨子片同根因漂移检测）/ SR-P22-3 → feedback_decision_layering.md 反模式表 / SR-P22-5 → feedback_subagent_sprint.md §6 关闸沉淀
  - **cross-sprint pool 41→39**：#3 + #15 标 ✅ DONE / 状态分布 STILL_PUNT 41→39 / DONE 30→32

- **下一步推荐**：**Phase 2.3 集成验证 + 工程规约 minimal 补完 + frontend-polish 子 sprint + cross-sprint pool C 类 12 项 perf sprint 评估**
  - 四选其一开新 session（cost 估各异 / Phase 2.3 §8.0 + §8.1 + frontend-polish 一并 or 单跑）：
    - **A. 工程规约 minimal 补完**（Phase 2.3 §8.0 / 上线前硬前置 / 03-cicd + 04-observability + 05-security 三 spec 补完 + GitHub Actions workflow 文件 + Prometheus + Sentry + .env.prod.example）
    - **B. 集成 e2e**（Phase 2.3 §8.1 / Playwright 跨 backend+frontend 真接通 / 10 核心页面 golden + 关键 E2E 链路）
    - **C. frontend-polish 子 sprint**（子片 5 关闸时 defer 的 10 items：P22-3b-1 抽 lib/server-action-helpers.ts + P22-3c-1~8 命名/dead code/兼容层清理 + P22-4-2 isTeamOwner 死代码 / 估 cost $2-3 / 0.5 天 / 单独跑可走完整 R1+R2 pipeline 出 6 数据点）
    - **D. perf sprint 评估**（cross-sprint pool C 类 12 项 / 接受 / 立专门 sprint / 推上线后）
  - 推荐顺序：A → B → C → D（工程规约不补不能上 prod / 集成 e2e 是上线 gate / frontend-polish 可与 A/B 并行 / perf 可推上线后）
  - cold-start prompt：✅ 已写 `_handoff/phase23-prompts.md`（4 子 sprint A/B/C/D 全集 / commit `7dc6878`）

- **Phase 2.2 全集进度**：✅ 7/7 子片完成（子片 0 prep + 1 + 2 + 3a-i + 3a-ii + 3b + 3c + 4 + 5）/ 累计 ~$15-20 cost / ~5-6 天工作量 / R 范式 5 数据点完整

---

## 0a. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-4-完成）

- **Phase 2.2 子片 4 完成**（M20 团队页新写 / Prism 无 / 全新写 / scope 自决 6→3 路由 + 9 actions + 1 projects-side / **errors.ts isNextRedirectError export + 3 处 client `.catch` rethrow root-cause 立修 client-side NEXT_REDIRECT 同根因新场景变体**）

---

## 0b. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-3c-完成）

- **Phase 2.2 子片 3c 完成**（actions/{competitors,competitor-references,issues,search,admin,activity-log} 完整接 + actions/{export,project-stats-proxy} 端点重写 + actions/{templates,feed} 全 punt + validators/issue.ts 加 title + **errors.ts.actionError 立修 UnauthenticatedError → redirect 一改通修 mutation 路径 401 静默吞错 root-cause**）：
  - **scope 自决收缩**（feedback_decision_transparency A 模式 / SR-P22-3 第 4 实证）：cold-start prompt「10 actions + 7 页面」→ 实际可达 6 actions 完整 + 2 端点重写 + 2 全 punt（templates/feed/openclaw/admin 用户管理/项目级 ZIP 导出 5 个域 OpenAPI 无对应路径）/ 7 页面解锁全留子片 5 集中处理
  - 16 文件改：actions/{competitors,competitor-references,issues,search,admin,activity-log,export,project-stats-proxy,templates,feed}.ts + validators/issue.ts 加 title + projectId + lib/errors.ts 立修 + eslint.config.mjs 移 10 ignore（actions 9 + validators/issue.ts）+ audit/p22-pilot-template-validation.md §3c + cross-sprint-punt-pool.md + p22-subslice-prompts.md
  - 累计 vitest 20 PASS / eslint 0 errors 0 warnings / pytest 不动（仅前端改）
  - **R1+R2 第 4 数据点**（mutation 路径契约真验证）：R1 Sonnet reuse + R2 Opus spec / R1 标 4 P1+5 P2 / R2 标 2 P1+3 P2 / 复审立修 2 项（**errors.ts.actionError 加 isUnauthenticatedError → redirect("/login") root-cause 一改通修 N+ caller** + admin.ts NOT_IMPLEMENTED 类型 string→Error）+ punt 8 项进 cross-sprint pool（P22-3c-1 ~ P22-3c-8）
  - **R 范式第 4 数据点 ROI 新维度**：R2 spec 抓到「mutation 路径 401 静默吞错」是 3a-ii 第 2 数据点 read 路径硬伤的同型 mutation 路径再发 / 3a/3b R2 漏抓 / 3c R2 闭环 — 验证 R2 spec subagent 不只是「本子片字面合规」检查器，更是「跨子片同根因漂移检测」机制（SR-P22-4 立规候选）/ R1+R2 配比 1+1 ROI 持续高于 R1=3 + R2=1
  - **scope 修订归档**：cold-start 10 actions+7 页面 → 实际 6 actions 完整 + 2 端点重写 + 2 全 punt + 0 页面真接（消费方签名漂移留子片 5 cleanup）/ SR-P22-3 第 4 实证（M01 register + 3a-ii 26 broken imports + 3b SSE/WS + 3c OpenAPI 域不对应 = 四实证 / 子片 5 关闸前 sink 已成熟）

- **下一步推荐**：**子片 4 — M20 团队页新写（Prism 无 / 全新写）**
  - prompt：`_handoff/p22-subslice-prompts.md`「子片 4」段
  - 估 cost $3-5 / 估时 1-1.5 天 / **建议开新 session**（context 累积 R1+R2 + 大量 schema 读取 / 新 session ROI 高）
  - 含：6 路由（/teams 列表 + /teams/[id] 详情 + /teams/new + /members + /transfer + /danger）+ R-X3 RBAC 前端守卫 + 轻量 design 草案 + R1+R2 第 5 数据点（全新写形态 / 验证 R 范式在「无范本拷贝」场景的 ROI）
  - **可与子片 3c 并行**（CY prompt 字面 / 但单会话不并行 / 开新会话起手）

- **Phase 2.2 全集进度**：5/7 子片完成（子片 0 prep + 1 + 2 + 3a-i + 3a-ii + 3b + 3c）/ 还需 2 子片（4 + 5）/ 总估 $4-7 + 1.5-2 天

---

## 0a. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-3b-完成）

- **Phase 2.2 子片 3b 完成**（actions/{nodes,relations,panorama} 完整改造 + actions/{import,import-ai} 全 punt + actions/analyze 部分 + errors.ts NEXT_REDIRECT 立修）：
  - **scope 自决收缩**（feedback_decision_transparency A 模式 / SR-P22-3 第 3 实证）：cold-start prompt「6 actions 完整改 + 7 页面解锁」→ 实际可达 4 actions 完整 + 1 部分 + 2 全 punt（M11/M13/M14/M17 SSE+WS+session 流程不在 prism-0420 OpenAPI 直接路径），7 页面解锁全留子片 5 集中处理
  - 9 文件改：lib/validators/node.ts schema 加 projectId / lib/errors.ts 加 isNextRedirectError 豁免（NEXT_REDIRECT 透出）/ actions/nodes.ts 完全 rewrite 23→11+2 stub / actions/relations.ts 完全 rewrite + 模块级聚合派生 / actions/panorama.ts 完全 rewrite 接 /overview / actions/import.ts 全 punt actionError(NOT_IMPLEMENTED) / actions/import-ai.ts 同 / actions/analyze.ts getAffectedNodes 实装 + 6 stub punt / eslint.config.mjs 渐进还债 6 文件移除 ignore
  - 累计 vitest 20 PASS / eslint 0 errors 0 warnings / pytest 不动（仅前端改）
  - **R1+R2 第 3 数据点**（端点契约真验证）：R1 Sonnet reuse + R2 Opus spec / R1 标 2 P1 + 3 P2 / R2 标 1 P1 + 2 P2 / 复审立修 2 项（getRelationsByNode 包 withAuthRedirect 修 spec §3 字面违反 + errors.ts NEXT_REDIRECT 透出修全 actions 通用硬伤）+ punt 6 项进 cross-sprint pool
  - **R 范式第 3 数据点 ROI**：R2 spec 仍真漏抓 1 spec 字面违反（`getRelationsByNode` 缺 redirect helper）/ R1 reuse 找出 NEXT_REDIRECT 全捕硬伤（影响所有 mutation / 跨 actions 通用）/ SR-P22-2 立规精神第 3 实证支撑 / R1+R2 配比 1+1 ROI 持续高于 R1=3 + R2=1
  - **scope 修订归档**：cold-start 6 actions+7 页面 → 实际 4 actions 完整 + 1 部分 + 2 全 punt + 0 页面真接（消费方签名漂移留子片 5 cleanup 批次）/ SR-P22-3 第 3 实证（M01 register + 3a-ii 26 broken imports + 3b SSE/WS 不在 OpenAPI 三实证）

- **下一步推荐**：**子片 3c — competitor + issue + search + admin + openclaw 长尾**
  - prompt：`_handoff/p22-subslice-prompts.md`「子片 3c」段
  - 估 cost $3-5 / 估时 1 天 / **建议开新 session**（context 累积 R1+R2 + 大量 schema 读取 / 新 session ROI 高）
  - 含：M06 competitor refs + M07 issues + M10 search + M16 stats + M19 export 长尾接入；evaluate 是否同时收尾子片 3b punt 的 M11 cold-start 真接 + M13 SSE + M17 imports（视 budget 决定）

- **Phase 2.2 全集进度**：4/7 子片完成（子片 0 prep + 1 + 2 + 3a-i + 3a-ii + 3b）/ 还需 3 子片（3c + 4 + 5）/ 总估 $7-12 + 2.5-3.5 天

---

## 0a. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-3a-ii-完成）

- **Phase 2.2 子片 3a-ii 完成**（actions/{projects,project-settings,versions} + lib/server-auth.getServerUser + /projects 列表 + /projects/new 真接 backend）：
  - 决策路径：CY 询"按架构决策原则应该选哪个" → 选 (a) 小 scope（2 页面真接 + 4 页面 ignore 留 3b/3c / 不超 subslice 边界 / 单会话 cost 在档）
  - 8 文件改：lib/server-auth.ts +getServerUser / actions/projects.ts 全改 + withAuthRedirect helper / actions/project-settings.ts 全改 + getAllDimensionTypes punt / actions/versions.ts 全改 + 签名加 projectId / app/projects/page.tsx 重写 + useAuth + snake_case + team tab 占位 / app/projects/[projectId]/page.tsx 删 unused import / app/projects/[projectId]/workspace.tsx createVersion 调用同步 / eslint.config.mjs 渐进还债 + glob workaround
  - 累计 vitest 20 PASS / pytest 不动（仅前端改）/ eslint 0 errors 0 warnings
  - **R1+R2 第 2 数据点**（首次真用 endpoint 验契约）：R1=1 Sonnet reuse + R2=1 Opus spec / R1 标 5 P1 候选 / R2 标 4 P1+8 P2 / 复审立修 3 项（ai_api_key schema 字段名 + 401 → redirect("/login") spec §3 字面合规 + projectsData mock dead 删）+ punt 8 项进 cross-sprint pool
  - **R2 真漏抓硬伤**：`api_key` → `ai_api_key`（密钥写不进 / 后端忽略未知键 / 无 TS 守卫）+ 401 静默吞错（spec 06 §3 字面违反 / page.tsx `.catch(()=>[])` 退化为空列表 / 不跳登录）— SR-P22-2 立规精神第 2 数据点实证
  - **scope 修订归档**：cold-start prompt 6 页面 → 实际可达 2 页面真接 + 4 页面 ignore（深耦合 3b/3c actions）/ broken imports 26 处中关闭 4 处 / 余 22 处随 3b/3c 关闭 / SR-P22-3 立规第二实证（M01 register 第一 + 3a-ii broken imports 第二）

- **下一步推荐**：**子片 3b — node + 模块树 + relation-graph + comparison + import**
  - prompt：`_handoff/p22-subslice-prompts.md`「子片 3b」段
  - 前置：actions/nodes 全改 server-http-client（drizzle 解锁 [projectId]/page.tsx + features/[fid]/page.tsx 详情页运行）
  - 估 cost $4-6 / 估时 1.5 天 / **建议开新 session**（context 已积累 R1+R2 spec subagent 报告 / 新 session ROI 高）

- **Phase 2.2 全集进度**：3/7 子片完成（子片 0 prep + 1 + 2 + 3a-i + 3a-ii）/ 还需 4 子片（3b + 3c + 4 + 5）/ 总估 $13-19 + 4-5 天

---

## 0a. 上一版本快照（更新于 2026-05-09 post-Phase-2.2-子片-3a-i-完成）

- **Phase 2.2 子片 3a-i 完成**（spec 06 §3 SSR auth 通道沉淀 + 服务端 fetch helpers）：
  - 决策路径：CY 询"按架构决策原则应该选哪个" → 选 α-P1（cookies → /auth/refresh → access_token → Bearer / 走 ADR-004 P1 / 不修订 spec 06 §2 + ADR-004 任何字面）
  - commit `e521656`：spec 06 §3 SSR auth 通道（α-P1 决策 / 安全模型 / API 契约 / 引用方分类 / 实施清单）+ ADR-004 §3.5.1 备注（getServerSession 已删 / Server Action 当前走 α-P1 / P2 演进保留 / Phase 2.3 评估）+ p22-subslice-prompts 跨 session 共用纪律 + 子片 3a 实施模式细化（actions 走 serverApiPost / lib/*-data.ts 走 serverApiGet / 防层级混淆 lint 准则）
  - commit `ee3a2ad`：app/src/lib/server-auth.ts（getServerAccessToken / React.cache 单请求 memo）+ server-http-client.ts（serverApiGet/Post/Patch/Put/Delete + 401 不自动 retry / 复用 ApiError 类型）+ 7 unit tests
  - 累计 vitest 20 PASS（http-client 6 + auth-context 5 + smoke 2 + server-http-client 7）
  - 模块影响评估：M01-M20 模块设计 §8 字面"鉴权走 ADR-004 P1+P2"仍正确 / 不需修订（避免过度修订 / R-X5 反模式）

- **决策落盘价值**：
  - 子片 2 决策（access 内存 / refresh cookie）字面零修订 / 完整保留
  - ADR-004 P1+P3 字面零修订
  - 客户端 + 服务端 access 通道独立 / 各层故障域隔离
  - Phase 2.3 性能优化空间充足（per-request access cache / cookie burst / P2 HMAC 升级 / 多档可选）
  - 子片 3a-ii / 3b / 3c / 4 改造范式锁定：actions/* 走 server-http-client / lib/*-data.ts 走 serverApiGet / Client 组件走 services/http-client

- **Phase 2.2 子片 2 完成**：✅ auth flow 改造（access 内存 React context + refresh httpOnly cookie + CORS）+ login/register 页面 + 13 vitest + 4 backend cookie e2e + R1+R2 第 1 数据点
  - 后端 4 项（spec 06 §2 字面）：
    - `/auth/login` 加 Set-Cookie `refresh_token` HttpOnly+Secure(prod)+SameSite=Strict+Path=/auth+Max-Age=30d（保留 body 字段做 deprecated 兼容）
    - `/auth/refresh` Cookie 优先 + body 兜底（`RefreshRequest.refresh_token` 改 Optional / ADR-004 P3 字面双通道合规 / 不修订 ADR）
    - `/auth/logout` 清 cookie + best-effort revoke
    - `api/main.py` 加 CORSMiddleware（allow_credentials=True / allow_origins from settings.cors_origins / allow_headers=["Authorization","Content-Type"]）
  - 前端 5 项（spec 06 §2 字面）：
    - `app/src/contexts/auth-context.tsx` AuthProvider + useAuth hook（login/logout/refresh 走 http-client / mount 调 refresh 续杯）
    - `app/src/services/auth-token-store.ts` 模块层 in-memory store 保留 / context 通过它桥接给非 React http-client
    - `app/src/app/layout.tsx` RootLayout 包 AuthProvider
    - `app/src/app/login/page.tsx` 重写 client 端 useAuth().login + ApiError 分支错误提示（401/403/423/5xx）
    - `app/src/app/register/page.tsx` disabled banner（M01 design §4 字面注册属未来扩展 / CY 选 (a) 跳过改造）
  - 测试：13 vitest（http-client 6 + auth-context 5 + smoke 2）+ 4 backend cookie channel e2e（test_m01_cookie_channel.py）+ M01 baseline 64 PASS 不破
  - eslint ignore 渐进还债：累计移除 7 项（services/auth.ts deleted / contexts/** narrow / lib/validators/** narrow / app/login + app/register 全删）
  - 删除：`app/src/actions/auth.ts`、`app/src/services/auth.ts`、`app/src/app/register/register-form.tsx`（next-auth / drizzle 依赖死耦）
  - **R1+R2 第 1 数据点**（合并子片 1+2）：R1=1 Sonnet reuse + R2=1 Opus spec / R1 标 2 P1（拷贝层 broken imports）经复审降 P2（已知 punt 状态 / 子片 0 prep 起就坏）+ 4 P2 进 audit / R2 0 P1 + 5 P2 进 audit / 1 P2 立修同 commit（auth-context 冗余 catch）
  - **新建 audit**：`design/audit/p22-pilot-template-validation.md`（§0 方法论 / §1 子片汇总 / §2 R2 spec P2 / §3 R1 reuse P1 复审降 P2 + P2 + 已修 / §4 SR-P22 立规候选 / §5 元贡献）
  - **拷贝层 broken imports 累计 26 处**（`@/lib/auth` 20 + `@/actions/auth` 6）— 自子片 0 prep 起就坏 / 子片 3a-3c 改造时一并修

- **下一步推荐**：**子片 3a-ii — projects 列表 + 详情 + dimension 档案 5 页面改造**
  - prompt：`_handoff/p22-subslice-prompts.md`「子片 3a-ii」段
  - 前置：后端 alive（同子片 2）/ spec 06 §3 helpers 已 ready / R1+R2 第 2 数据点会真用
  - 估 cost $4-5 / 估时 1-1.5 天 / 触发拷贝层 broken imports 一并修
  - **建议开新 session**（context 已积累 spec 06 §3 设计讨论 + R1+R2 sub-agent 报告 / 新 session ROI 高 / feedback_usage_budget v3 「>150k 强制建议 /clear」）

- **Phase 2.2 全集进度**：2/7 子片完成 / 还需 5 sessions / 总估 $14-22 + 5-6.5 天

- **决策落盘新规**：`feedback_decision_layering.md`（自检 4 问 + 决策处理流程 5 步 / SR-P22-1 已即时落自检第 4 问）

- **scope 决策记录**：CY 选 (a) 跳过 register 改造（M01 design §4 字面"开放自助注册属未来扩展（Q1=B/C/D）"/ 与 cold-start prompt 自行扩 spec scope 的对抗 / SR-P22-3 立规候选已加 audit §4）

---

## 0a. 上一版本快照（更新于 2026-05-09 post-M20-sprint-complete / **Phase 2.1 100% 收官**）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：✅ **100%**（M01-M08+M10-M20 全交付；M09 superseded by M18 不实装）
- **2026-05-09 M20 sprint 完成 / Phase 2.1 收官**（8 commit / 1613 PASS / R13-1 139 / L12+L13+R14 全过 / ruff 净 / **横切 owner + R-X3 双方法 + correlation_id F2.9 + R10-1 N+1 + 嵌套 max + F2.3 archived×team 互锁双路径 / pilot=false / complexity=medium / 最后一个 own sprint**）：
  - commits:
    - `f325b74` 启动期（reconcile pass A 8 / B 0 第十五次实证 / C 9 + §14.5 + 元教训 #19 三方对账 + Phase 2.1 收官启动 + bypass log #2 配套继续）
    - `307a137` 子片 1（api/models/teams.py + alembic m20_team.py + projects.team_id FK 启用 + 17 model tests + conftest make_team / make_team_with_owner fixture / 跨模块 helper 规则十二连）
    - `4c01f3a` 子片 2（api/dao/teams_dao.py TeamDAO + TeamMemberDAO + M20TenantContext UNION + lifespan 升级 / M02→M20 切换前后 baseline 不破 + 21 DAO tests）
    - `d84b713` 子片 3（api/services/team_service.py 11 方法 + api/schemas/teams.py 8 schemas + 8 ErrorCode raise 接通 + 状态机 4 禁止转换 + 33 service tests）
    - `49f7cff` R1 立修 8 P1（3 subagent 并行 / Opus + 2 Sonnet 合并去重 / N+1 list_for_user + delete_team residual count truncation + R-X3 violation rollback + count_owners FOR UPDATE + transfer from_role 永真 + main.py log 标签）+ 3 regression tests
    - `8ee6e3c` 子片 4（Router 10 endpoints + 20 e2e + R10-1 N+1 e2e + cross-tenant 404 + 元教训 19 类 actionable）
    - `615a5e8` R2 立修 3 P1 + 1 P2 顺修（1 合并 Opus endpoint 单审 / PATCH role 0 e2e + viewer 写 6 端点 403 + response_model）+ 9 e2e
    - 子片 5 关闸（本 commit / design 回写 + audit/m20-pilot-template-validation.md + handoff §0 + roadmap **Phase 2.1 100% 收官** + cross-sprint punt 池接通 + 闸门 4 启动条件评估）
  - **1512 → 1613 PASS (+101) / 5 skipped / R13-1 139 / L12+L13+R14 全过 / ruff 净**
  - **闸门 2.5 第十五次 B 栏 0 项实证**：M05-M20 十五连稳定
  - **bypass log #2 配套验收最终 ✅**：M16 bypass + M17/M18/M19/M20 真跑 = 累计 2 次 bypass 不复位 / 第 3 次触发闸门 3.4 L1 review
  - **R1+R2 命中数据**（M02-M20 第十七数据点 / 详 audit/m20-pilot-template-validation.md）：
    - R1=3 subagent：5 P1（spec+quality Opus）+ 1 P1（reuse Sonnet）+ 5 P1（quality+efficiency Sonnet）= 11 P1 / 合并去重 8 立修 + 7 punt
    - R2=1 合并 Opus：3 P1 + 4 P2 = 7 项 / 立修 3 + 顺修 1 + punt 4
    - **R2 真漏抓贡献**：PATCH role endpoint 0 router e2e（design §7.1 字面登记） + viewer 写所有写端点 403 主动复制覆盖度仅 1/7（M07 范式应 6/7） + PATCH role 缺 response_model
  - **元贡献 5 项**（详 audit/m20-pilot-template-validation.md "元贡献清单" 段）：
    1. **Phase 2.1 100% 收官**：M01-M08+M10-M20 全交付 / 16 own 模块（M09 superseded） / 闸门 4 启动条件评估通过 / Phase 2.2 前端继承 Prism 启动评估
    2. **R-X3 双方法 + correlation_id F2.9 + R10-1 N+1 三者交叉首发**（delete_team + transfer_ownership / SR-M20-1 立规候选）
    3. **横切 owner 模块（user_accessible_project_ids_subquery L3 SQL 注入升级）实证**：M02→M20 切换前后 M03-M19 既有 17 模块 0 改动 baseline 不破（SR-M20-2 立规候选）
    4. **元教训 #19 R2 reconcile pass 第二实证**（M19 立 + M20 验证）→ SR-M19-1 立规收敛正式立到 sprint 启动期 reconcile A 栏首条 + R2 reconcile pass 必跑
    5. **N/A 元教训显式声明范式扩展 11 项**（design §14.5 范式复用清单 20 项 / 半数 N/A / 单 sprint 历史最高密度）
  - **R-X5 子选项实证**（design §14.5 L3 留空 4 项）：
    1. 横切 owner 模块（最复杂单 sprint 形态）R1+R2 命中分布偏 R1-A spec+quality + R1-C N+1 + R2 endpoint 覆盖度
    2. L3 SQL 注入升级横切 M03-M19 17 模块 baseline 不破（1529→1548 PASS +19 全 M20 新增 / 0 regressions）
    3. Phase 2.1 100% 收官 cross-sprint punt 池零长期累计新增（R2 P2 全 sprint-internal punt 不接通 long-term pool）
    4. R-X3 + correlation_id + R10-1 三者交叉 sink 立规候选 SR-M20-1
  - **cross-sprint punt 池接通**：本 sprint 关闭 #20（require_platform_admin 重新评估不触发 / 保留至下一 platform_admin 模块）/ 新增 0（R2 P2 全 sprint-internal punt）
  - **闸门 4 启动条件评估**（Phase 2.2 前端继承 Prism）：
    - [x] M01-M05+M20 后端代码 merge ✅
    - [x] OpenAPI 契约稳定（10 M20 endpoints + 8 schemas accepted）✅
    - [ ] `npm run codegen` 准备 — 待 Phase 2.2 启动时跑
    - [ ] Phase 2.2 子片 0 prep — 待 CY 启动

## 0a. 上一版本快照（M19 sprint 完成）
- **2026-05-09 M19 sprint 完成**（8 commit / 1512 PASS / R13-1 136→139 / L12+L13+R14 全过 / ruff 净 / **纯只读导出 / pilot=false / complexity=low / R1+R2 第十七数据点 / bypass log #2 配套继续 ✅**）：
  - commits:
    - `3ad8efa` 启动期（reconcile pass A 6 / B 0 第十四次实证 / C 8 / §14.5 + bypass 验收 + punt 检查）
    - `facce18` 子片 1（ActionType+1 "exported" 4 处同步 / Alembic ALTER CHECK + 4 model tests / 子片 0 prep 合并到启动期 / 子片 2 DAO 复用接通合并到子片 3 service 构造函数）
    - `83cf44a` 子片 3（ExportService.generate_markdown + Schema 2 Request + 3 ErrorCode + 13 service tests / DAO 复用 ADR-003 规则 1 / 横切表批量预取 dim_type_index + competitor_index 防 N+1）
    - `c98e563` R1 立修 7 P1（3 subagent 并行 / Opus + 2 Sonnet 合并去重 / R14 过去式 + EXPORT_EMPTY_CONTENT 422 + EXPORT_NODE_LIMIT_EXCEEDED 业务码 + ValidationError 422 范式对齐 + include 全 False schema 阻断 + dict.fromkeys 保序去重 + select 移顶部 import）
    - `947f0e2` 子片 4（Router 2 endpoints / POST /exports + POST /nodes/{nid}/export / 12 e2e 元教训 18 类 actionable 主动复制 + N/A 显式声明 / Content-Disposition + filename sanitize 输出端首发）
    - `257ab92` R2 立修 3 P1（1 合并 Opus / tests.md ↔ design ↔ exceptions 三方 status code 字面同步漂移 + tests.md G2 3 node 顺序 e2e + tests.md E5 去重 e2e + summary 字面）
    - 子片 5 关闸（本 commit / design 回写 + audit/m19-pilot-template-validation.md + roadmap M19 + Phase 2.1 90→95% + cross-sprint punt 池 + handoff §0）
  - **1480 → 1512 PASS (+32) / 5 skipped / R13-1 136→139 / L12+L13+R14 全过 / ruff 净**
  - **闸门 2.5 第十四次 B 栏 0 项实证**：M05-M19 十四连稳定
  - **bypass log #2 配套继续 ✅**：M19 R1=3 subagent + R2=1 合并 Opus 真跑 / 累计 bypass 不复位（M16 bypass + M17 恢复 + M18 继续 + M19 继续 = 累计 2 次 bypass / 第 3 次触发闸门 3.4 L1 review）
  - **R1+R2 命中数据**（M02-M19 第十七数据点 / 详 audit/m19-pilot-template-validation.md）：
    - R1=3 subagent：5 P1（spec+quality Opus）+ 3 P1（reuse Sonnet）+ 3 P1（quality+efficiency Sonnet）= 11 P1 / 合并去重 7 立修 + 4 punt
    - R2=1 合并 Opus：3 P1 + 3 P2 = 6 项 / 立修 3 + 顺修 1 + punt 2
    - **R2 真漏抓贡献**：tests.md ↔ design ↔ exceptions 三方 status code 字面同步漂移（**元教训 #19 独家**）+ tests.md G2 3 node 顺序 e2e 缺失 + tests.md E5 去重 e2e 缺失
  - **元贡献 4 项**（详 audit/m19-pilot-template-validation.md "元贡献清单"段）：
    1. **元教训 #19：R1 局部立修触发 tests.md 第三方文件漂移** — R1 改 design §13 + exceptions.py 把 "404 → 422" 同步了，但 tests.md 成了滞后文件 / R1 三 subagent 把 tests.md 当"参照真相"而非"待同步对象" / 立规候选 SR-M19-1：tests.md ↔ design.md ↔ exceptions.py 三方 status code 字面同步 checkbox（M17 立的 R2 reconcile 仅覆盖 design ↔ 实装 / M19 第二实证扩第三方 tests.md）
    2. **R14 过去式立规精神 vs design accepted 字面对齐范式** — design §10 字面 "export" / accepted 2026-04-21；M16 R14 立规 2026-05-09 立 / 5 步分层判断：横切纪律优先于单模块字面 / 立修 4 处同步 "export" → "exported" / 立规候选 SR-M19-2：design accepted 时间早于横切立规时（如 R14） / sprint 启动期 R1 reviewer 必跑立规精神 vs design 字面对齐 grep 检查
    3. **filename sanitize 输入端 vs 输出端分门别类** — M11/M17 = 输入端（用户上传 filename / strip + 长度截断 + 特殊字符防御）/ M19 = 输出端（服务端拼装 timestamp / 控制字符 strip 纵深防御）/ 根源不同 / 立规候选 SR-M19-3：cross-sprint punt #17 第三实例 / 输出端首发不立即 horizontal / 第四实例（第二输出端）触发提取 api/utils/markdown_helpers.py
    4. **N/A 元教训显式声明范式扩展（19 项主动复制清单）** — §14.5 范式复用清单 19 项是 M02-M18 沉淀最大主动复制清单 / test_meta_lesson_na_explicit_declarations docstring 字面声明 9 项 N/A（防 R2 把"未覆盖"当 P1 抓 / docstring-only placeholder + 不构成 M18 立 #4 测试反模式 assert True 永真污染）
  - **R-X5 子选项实证**（design §14.5 L3 留空 3 项）：
    1. **纯只读模块 R1+R2 命中分布偏 R2 文档同步面 / R1 偏代码契约面**（M19 R1=7 持平平均 / R2=3 略超普通模块 0-2 P1 区间 / 元教训 #19 文档同步盲区驱动）
    2. **design §7 字面 Markdown 结构对账漏在 R1 / R2 子片 4 e2e golden test 字面验补足**
    3. **filename sanitize 输出端首发不立即触发 horizontal 化** / 第四实例（第二输出端）触发
  - **cross-sprint punt 池接通**：本 sprint 关闭 0 / 新增 4 punt（#25 _md_cell horizontal / #26 filename sanitize 输入 vs 输出分类 / #27 Cache-Control: no-store / #28 filename 含 project_name RFC 5987）/ 真漏洞 #20 require_platform_admin M19 evaluated 不触发（M19 viewer endpoint）/ M20 sprint 重新评估
  - **下一站 M20 团队**：Phase 2.1 最后一个 own sprint。M20 形态特殊：teams + team_members 双表 + space_id → team_id RENAME baseline-patch + ActionType+10 + TargetType+1 + Alembic 单 revision 合并 + 8.5 P1+P2 + 8.7 R-X3 + 10.3 R10-1 N+1。**M20 启动期 reconcile pass A 栏首条预录**：M19 元教训 #19 应用——`grep -n "404\|422\|500" tests.md` 与 `exceptions.py:http_status` + `design.md:§13` 字面比对（SR-M19-1 立规实证）。

## 0b. 上一版本快照（M18 sprint 完成）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：⏳ 90%（M01-M08+M10-M18 完成；下一站 M19 导入/导出；M09 superseded by M18 不实装）
- **2026-05-09 M18 sprint 完成**（9 commit / 1480 PASS / R13-1 124→136 / **§12D embedding 持久化首战 + pgvector ARRAY 占位三层降级范式 + R1=3 subagent 并行 + R2=1 合并 Opus 第十六数据点 + bypass log #2 配套验收最终 ✅**）：
  - commits:
    - `90f7672` 启动期（design status flip draft→accepted + 闸门 2.5 reconcile pass A 8 / B 0 / C 6 + bypass log #2 配套验收）
    - `6c27898` 子片 0 prep（EmbeddingProvider mini-sprint / abstract+Mock+factory+41 tests）
    - `fbea749` 子片 1（4 表 model + alembic + 54 model tests + pgvector ARRAY 占位 + ivfflat 索引注释保留）
    - `c7aca1f` 子片 2（5 DAO 含规则 4 豁免 + 45 unit tests + 2 conftest fixtures）
    - `f2da4e2` 子片 3（Service+Schema+12 ErrorCode+SilentFailure+Queue+Cron+Provider stub+92 tests）
    - `76c6d9b` R1 立修（16 P1 / 3 subagent 并行审 spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet 合并去重）
    - `68e981e` 子片 4（Router 1 search + 3 admin endpoints + 42 e2e / 元教训 18 类全覆盖）
    - `92e09d3` R2 立修（7 P1+P2 修齐 + 1 PUNT / 1 合并 Opus subagent endpoint 单审）
    - 子片 5 关闸（本 commit）
  - **1213 → 1480 PASS (+267) / 5 skipped / R13-1 124→136 / L12+L13+R14 全过 / ruff 净**
  - **闸门 2.5 第十三次 B 栏 0 项实证**：M05-M18 十三连稳定
  - **bypass log #2 配套验收最终 ✅**：M18 R1=3 subagent + R2=1 合并 Opus 真跑 / 累计 bypass 不复位（M16 bypass + M17 恢复 + M18 继续 = 2 次 bypass / 第 3 次触发闸门 3.4 L1 review）
  - **R1+R2 命中数据**（M02-M18 第十六数据点 / 详 audit/m18-pilot-template-validation.md）：
    - R1=3 subagent：13 P1（spec+quality Opus）+ 2 P1（reuse Sonnet）+ 5 P1（quality+efficiency Sonnet）= 20 P1 / 合并去重 16 立修 + 4 punt
    - R2=1 合并 Opus：5 P1 + 7 P2 = 12 项 / 立修 7 + punt 5（require_platform_admin 去重 PUNT 子片 5+）
    - **R2 真漏抓贡献**：BackfillRequest 继承 TaskPayload（R1-A 仅抓 Response 端）+ TestIntegrityErrorCatch/TestNAExplicit assert True 占位反模式
  - **元贡献 7 项**（详 audit/m18-pilot-template-validation.md "元贡献清单"段）：
    1. **§12D 子模板首次实战零摩擦验证** — 7 字段 PK + 异维列拆分 + 三段回填 + 双触发链 + 跨模读双路豁免 + failure 容忍 + cron 矩阵全部实装一次过 / README §12 表 §12D 行 + 2026-10-25 复用度复盘 OpenClaw cron 触发器
    2. **R-X4 pgvector 未装库占位三层范式** — model ARRAY + DAO NotImplementedError + Service keyword_only 降级（PRD AC4 字面 / search_mode="keyword_only" + 200 不报错）/ 子片 4+ 真装 pgvector 后回写
    3. **EmbeddingProvider 抽象仿 ADR-001 §4.1 LLMProvider 范式** — abstract base + 异常族（Error/Timeout/Config）+ Mock 确定性 sha256-seeded L2 归一化 + factory / 子片 0 prep mini-sprint scaffold 简化决策 4 字段注释
    4. **SilentFailure 占位期降级范式**（fix v2 决策 3=B 实证）— design line 1269-1286 字面 SilentFailure(BaseException) 严格使用约束 / 占位期 enqueue_delete logger.warning 降级（不 raise SilentFailure / 防 BaseException 冒泡崩 worker）/ 子片 4+ 启用真异步 SilentFailure 语义
    5. **R1+R2 数据点 16 稳定** — bypass log #2 配套不复位实证 / 命中比例稳态 R1 8-13 P1 / R2 4-5 P1（R-X1+R-X2+异维列等 pilot 模块为 R2 多命中区域）
    6. **R10-2 例外应用第二实例**（embedding_failures 表）— M01 auth_audit_log 第一 + M18 embedding_failures 第二 / 三条件验证表字面 / 系统行为 vs 业务行为分类对齐（audit M7 修订）
    7. **元教训防御 actionable 主动复制 18 类完整实证** — design §14.5 + 子片 4 e2e / 12 主动复制（write 403 / read 403 / write_event 异常传播 / cross-tenant / cross-project / IntegrityError / metadata 字面 / M14 admin endpoint 形态 / ActionType+0 / R14 ci-lint / BackgroundTasks）+ 7 N/A 显式声明（R-X1 / multipart / SSE / CAS / compensation_session / idempotency project_id / N/A 双重声明）
  - **R1+R2 sink 立规候选 4 项**：
    1. **EndpointRequest schema 不应继承 TaskPayload 立规** — ci-lint 守护候选 grep `class.*Request.*\(TaskPayload\)` 报警 / M19+ 横切复用
    2. **pgvector / 异维列占位三层降级范式立规** — 三层占位必同步标注 + 解锁触发条件字面 / 未来 vector/search/embedding 模块横切
    3. **占位 metadata 必加 _stub: True 标记立规** — 防 activity_log 假数据污染历史排查 / 子片 N+ 真接业务路径时删 _stub + e2e assert 数值合理
    4. **测试反模式立规：assert True / assert in (a,b) 永真不算覆盖** — ci-lint 守护候选 grep `assert True\b` + 检测永真 in 元组 / N/A 声明应在 design.md docstring 落
  - **cross-sprint punt 池接通**：本 sprint 关闭 0 / 新增 5 punt（#20 require_platform_admin 去重 PUNT 子片 5+ / #21 worker source_text 真接上游 Service.get_for_embedding / #22 noop 标记 design 未明示 / #23 PCT 维度真接 task_dao.count_completed_in_window / #24 batch_backfill 真 batch INSERT FROM unnest）/ 触发点 A 4 项 STILL_PUNT 验证（M04 不触）
  - **半年回看触发器**：2026-10-25 §12D 子模板复用度复盘（OpenClaw cron 挂提醒 / 若仅 M18 单实例则评估降级 §12C 扩展段落）

## 0a. 上一版本快照（M17 sprint 完成）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：⏳ 85%（M01-M08+M10+M11+M12+M13+M14+M15+M16+M17 完成；下一站 M18 语义搜索；M09 superseded by M18 不实装）
- **2026-05-09 M17 sprint 完成**（7 commit / 1213 PASS / R13-1 116→124 / L12+L13+R14 全过 / **首个 R-X1 第二实例 + 异步 Queue + WebSocket endpoint pilot + bypass log #2 配套已恢复**）：
  - commits:
    - `ad069c0` 启动期（闸门 2.6 mini-sprint + R-X1 helper compensation_session + L1 总则修订 3 类例外 + IntegrityError 立规清单 6 + ci-lint R15 守护立规）
    - `7a6327f` 子片 0 prep（M11 ColdStart R-X1 第一实例迁移到 compensation_session helper / cold_start_router 失败分支精简 / R2 P1-01 punt #7 关闭 / cross-sprint punt 触发点 A 4 项 STILL_PUNT 验证）
    - `b806931` 子片 1（ImportTask + ImportTaskItem model 11+5 状态 + 3 source_type + UNIQUE B1 修复 + alembic m17_ai_import + ActionType+8 + TargetType+1 + 36 model tests）
    - `f41ad25` 子片 2（ImportTaskDAO + ImportTaskItemDAO + tenant filter + find_idempotent 7d + find_dead_letter_orphans 30d + 28 unit tests）
    - `9229759` 子片 3（ImportService 1003 行 + AIOrchestrationService + Schema + 8 ErrorCode + 6 arq @task + WS handler + R-X1 第二实例 + 40 新测试 / conftest 加 import_service 到 _MODULES）
    - `d558b5f` R1 立修 8 P1（3 subagent 并行审：spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）
    - `[hash]` 子片 4（Router 7 REST + 1 WS endpoint + multipart 100MB + idempotency 200 复用 + 24 e2e）
    - `dcf7024` R2 立修 4 P1（1 合并 Opus 单审 endpoint：WS endpoint 4 鉴权拒绝矩阵 + 413/422 design 漂移裁决 + filename sanitize 字面验输出 + IntegrityError race 路径注释）
    - 子片 5 关闸（本 commit）
  - **1213 PASS / 4 skipped / R13-1 116→124 / L12+L13+R14 全过 / ruff 净**
  - **闸门 2.5 第十二次 B 栏 0 项实证**：M05-M17 十二连稳定
  - **bypass log #2 配套已恢复**：M17 R1 = 3 subagent 并行 + R2 = 1 合并 Opus（spawn prompt 含 ls/find 穷举要求 / 不复位累计触发线 / 下次 bypass 第 3 次 → 触发闸门 3.4 L1 review）
  - **R1 + R2 命中数据**：R1=3 subagent 8 P1 立修（合并去重 / spec+quality Opus 2 / reuse Sonnet 1 / quality+efficiency Sonnet 6）/ R2=1 合并 Opus 4 P1 立修；M02-M17 R1 第十五数据点 + R2 第十四数据点稳定
  - **元贡献 7 项 sink**（audit/m17-pilot-template-validation.md "M17 sprint 实施期元贡献清单" 段）：
    1. R-X1 第二实例零摩擦验证 — compensation_session helper 横切设计成本控制有效（M11 第一实例 / M17 第二实例直接复用）
    2. WebSocket endpoint Query Bearer 鉴权 + audit B6 每命令 task_id 重校 + 4 鉴权拒绝矩阵 e2e
    3. idempotency_key 含 project_id（B1 修复）实装实证 + IntegrityError 端到端 catch（清单 6 落地）
    4. N+1 防护批量 cache 范式（_upsert_dimension_type 5 dim / 2 unique key → 2 次 upsert）
    5. filename sanitize 字面验输出范式（M11 R2 P1-03 立 / M17 R2 P1-03 强化必字面验 source_uri）
    6. partial_failed IMPL-NOTE 范式（design §10 字面 vs §4 single-tx 实装 gap 显式登记）
    7. design §7 字面 status code 漂移立规 sink 候选（每 sprint R2 reconcile checkbox）
  - **R1+R2 sink 立规候选 3 项**：
    1. **WS endpoint 5-test 矩阵立规**（feedback_ws_endpoint_test_matrix.md 候选）— invalid token / wrong type claim / cross-tenant / cross-owner / golden accept；不能用 broker 单测代替 endpoint e2e
    2. **filename sanitize horizontal 化触发条件** — 第三实例（M18+ multipart 上传）触发横切到 api/utils/upload_helpers.py + sanitize 测试必须字面验输出
    3. **multipart 上限分级表**（engineering-spec §X 立）— 小文件 10MB / 大归档包 100MB / 超大场景明示
  - **cross-sprint punt 池接通**：punt #7（R-X1 失败补偿 commit boundary）✅ DONE 子片 0 prep；新增 4 punt：WS golden e2e（R2 P1-01）/ _sanitize_filename horizontal（M18+ 触发）/ confirm_review 绕 _transition（R1-A P2-3）/ 6 处 lazy import 抽 helper（R1-A P3-3）
- **2026-05-09 M16 sprint 完成**（7 commit / 1063 PASS / R13-1 116=116 / R14 守护通过 / L12+L13 / **§12B 后台 fire-and-forget 子模板首战 + L1 R14 立规重大事件 + 7 业务模块 41 处 service action_type 过去式机械批量 + 4 NEW enum + write_event 真 INSERT + R1+R2 self-审 bypass log #2**）：
  - commits:
    - `9e9eb68` 子片 0 prep（M16 design §14.5 + M15 design §10 R14 段立规 + activity_log_service docstring 修 "module"→"node"）
    - `5c592d5` 子片 0.5 L1+L3 batch（41 处 service action_type 过去式机械改：M02 7+M03 5+M04 5+M05 4+M06 7+M07 6+M08 4+M11 3 + 4 NEW enum 同步 4 处 + Alembic ALTER CHECK + ci-lint R14 grep 守护）
    - `959e0b4` write_event stub→真 INSERT + ci-lint R14 扩 routers + project_router 3 处 update_dimension_config→project_dimension_config_updated 修
    - `6007fa2` 子片 1（AISnapshotTask model + alembic + ActionType+3 + TargetType+1 + 16 model tests + SYSTEM_USER_UUID 种子 user 行）
    - `ba0afb5` 子片 2（AISnapshotTaskDAO + cas_start_running/cas_complete/cas_zombie_transition + find_idempotent + 18 unit + conftest make_ai_snapshot_task fixture）
    - `2273f90` 子片 3（AISnapshotService + Schema + 14 ErrorCode + Runner + AI Provider 接通 + queue/base SYSTEM_USER_UUID scaffold + 15 unit）
    - `043e3e2` 子片 4（Router 3 endpoints + 19 e2e + 元教训 17 条 actionable 主动复制：viewer 写 generate+save 403 / 401 / cross-tenant 404 / cross-project node 404 / 双层防御 non-creator 404 / path mismatch 422 / status not_ready 409 / invalid_dim_key 422 / metadata 字段集字面 / write_event 异常传播）
  - **1063 PASS / 4 skipped / R13-1 116=116 / R14（含 routers 扩展）守护通过**
  - **闸门 2.5 第十一次 B 栏 0 项实证**：M05-M16 十一连稳定
  - **R1+R2 self-审 bypass log #2**：context budget pressure（24h 信号 🔴 long-context+subagent-heavy）；M17 sprint 必须恢复 R1=3 subagent 并行 + R2=1 合并 Opus（详见 design/99-comparison/phase-gate-bypass-log.md #2）；累计 bypass = 2 次 → 触发对闸门 3.4 L1 总则的 review，M17 子片 0 prep 必修订 phase-gate.md 把 "context budget pressure" 显式纳入触发例外段
  - **元贡献 6 项 sink**（audit/m16-pilot-template-validation.md "M16 sprint 元贡献" 段）：
    1. **L1 R14 立规 + ci-lint 守护** —— 防御未来 7 模块再漂移；M17-M19 sprint 启动期不再触发同款 batch
    2. **§12B 后台 fire-and-forget 子模板首次实战** —— design 7 字段全实装 / 未来后台模块照抄
    3. **CAS UPDATE 防 zombie/runner 双写范式** —— cas_start_running + cas_complete + cas_zombie_transition / 内部 commit 顶层方法 docstring 字面禁 Service 事务上下文
    4. **advisory_xact_lock 幂等 get-or-create** —— 替代 DB UniqueConstraint 业务幂等含 5min 时间窗口 + status 子集（PG immutable 不支持）
    5. **自起 SessionLocal 后台 runner** —— 与请求级 Depends(get_db) 完全隔离；BackgroundTasks fire-and-forget 形态
    6. **SYSTEM_USER_UUID + queue/base scaffold** —— ADR-002 §1.1 cron user_id 边界 / 闸门 2.6 mini-sprint M17 一并补 TaskPayload 基类 / users 表 SYSTEM_USER_UUID seed 行（Alembic INSERT ... ON CONFLICT DO NOTHING）
  - **cross-sprint Punt 池关闭**：真漏洞 #1（write_event stub→真 INSERT critical）+ #2（M03-M08 service ~14 处裸 CRUD high / 实际 41 处含 M02+M11 dot-notation+M07/M08/M05/M06 4 NEW enum）+ #5（M02 ai_model 字段误判 / 实际 M02 model 已含字段不需 alembic add column）= 3 项关闭；元发现 #1 触发点 A 立规实证 1 项；累计 22→25+ DONE
  - **B1 punt 池**：M07-2 update detach（None→NULL）回写 M07 design §3 待产品决策 / 不在 M16 sprint 内做（C 栏） / M14-B12 write_event 异常传播 e2e 已在 M16 子片 4 e2e 主动复制（test_save_propagates_write_event_failure_e2e） / M04-10 race window 在 41 处过去式 batch 一并复审过
- **2026-05-08 M15 sprint 完成**（8 commit / 63 PASS / R13-1 90→101 / L12+L13 守护 / **纯读 R10-2 owner 模块 + R1=1 合并 Opus M10 范式复用 + 横切 enum owner 责任首发 + 首发"读权限 403"测试范式**）：
  - commits: 29b0aaa 子片 0 prep（§14.5 + 元教训 14 项 actionable 清单 + M14 baseline-patch 反向回写 α 路线 / 5 处 service.py + 7 处 e2e + design §10 字面 + frontmatter）+ 8889ec5 子片 1（ActivityLog model + alembic + 9 model tests + ImmutableMixin + project_id NULLABLE + 3 索引 + 2 CHECK constraint + Mapped[str] 三重防护范式）+ af9120c 子片 2（ActivityStreamDAO list_stream + list_for_team + 16 unit + 强 project_id 过滤 + JOIN users + 首页 total D-2 + page validation + conftest make_activity_log fixture 十一连）+ 0fa19ad 子片 3（Schema ActionType+TargetType StrEnum 65+16 全集 + Filter + Item + Response + 11 ErrorCode 3 M15 own + 8 M20 baseline-patch + Service _check_activity_audit_access C-5 候选 β + has_more 判定 + 21 tests）+ d527632 R1 1 P1 立修（schema InvalidFilterError 业务 code raise 替裸 ValueError）+ §14.5 self-correct（纯读 R1=1 合并 Opus / 业务 R1=3 subagent 并行）+ 4e9fd54 子片 4（Router 1 endpoint + 13 e2e 含**首发"读权限 403"测试** + cross-tenant 404 + Pydantic Filter 422 + 全局事件不召回）+ 9ca130e R2 2 P1 立修（metadata e2e 字面 M13 NEW 教训复用 + Pydantic Filter 422 边界）+ 子片 5 关闸 commit（design §3 Disambiguation 段统一回写 + ci-lint L13 守 M15 self not-write_event + service _check docstring 双层防御非 dead code 注释 + cross-tenant member-of-both e2e）
  - **63 PASS / R13-1 90→101 (+11) / L12+L13 守护通过**
  - **闸门 2.5 第十次 B 栏 0 项实证**：M05+M06+M07+M08+M10+M11+M12+M13+M14+M15 十连稳定
  - **R1 + R2 命中数据**：R1=1 合并 Opus 1 P1 立修 + 3 P2 punt（M10 纯读范式复用）/ R2=1 合并 Opus 2 P1 立修 + 2 P2 punt；M02-M15 十三数据点稳定 → M16+ 默认范式可作模板
  - **纯读 R10-2 owner 模块新教训 4 条 sink**（详见 audit/m15-pilot-template-validation.md "纯读 R10-2 owner 模块新教训" 段）：
    1. 横切表 owner 模块的 enum 字面同步责任（4 处必同步：model tuple + schema StrEnum + CHECK constraint + Alembic）
    2. 纯读模块 R1 = 1 合并 Opus（M10 范式复用 / 区别业务模块 3 subagent 并行）
    3. 双层权限防御 service unit 不可达 e2e 是合理设计而非 dead code（与 R1 P1-1 立修结论相反 / 区分 schema 注册无 raise vs router 抢先+service 防御未来）
    4. "读权限 403"是首发测试范式（M02-M14 写 403 思想横切到读 403）
  - **元教训防御 actionable 应用 14 项**：viewer 写 403 ✅ N/A + 首发读 403 / write_event 异常传播 ✅ N/A + L13 守护 / cross-tenant 404 ✅ DAO 强过滤 + 3 e2e / cross-project node ✅ N/A / IntegrityError ✅ N/A / M12 L1 锁裁决型自决 ✅ B1 命名规约 α / R1.5 reconcile ✅ / R-X1 + 文件上传 + LLM hot path ✅ N/A / M13 "3 端点全"✅ list_for_team disambiguation / M13 metadata e2e ❌→R2 P1-1 立修 / M14 write_event project_id Optional ✅ NULLABLE 实装 / M14 N/A 元教训显式声明 ✅ §14.5 字面 / M14 形态特殊不免除 ✅ R2 直接命中
  - **B1 punt 池**：write_event stub 替换为真 INSERT（design §3 R10-2 + B7 字面）/ 同时回扫 M03/M04/M05/M06/M07/M08 service action_type 是否裸 CRUD（M14 已修 5 处 / 其他模块未验证）—— 后续独立 sprint 处理 / 工作量约 2-4h

## 0a. 上一版本快照（M14 sprint 完成）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：⏳ 70%（M01-M08+M10+M11+M12+M13+M14 完成；下一站 M15 数据流转；M09 superseded by M18 不实装）
- **2026-05-08 M14 sprint 完成**（7 commit / 930 PASS / R13-1 86→90 / L12 守护 / **首个全局豁免业务模块 + write_event project_id UUID→Optional 升级 + N/A 元教训显式声明范式 + owner-or-admin 替代 viewer 写 403**）：
  - commits: 3afbbdb 子片 0 prep（§14.5）+ c2858f7 子片 1 model+alembic+9 model tests + 968b284 子片 2 DAO+18 unit（GLOBAL DATA — NO TENANT FILTER 字面）+ e184c8b 子片 3 IndustryNewsService+4 ErrorCode+Pydantic+35 unit/schema（write_event UUID→Optional 升级 / source_type 强制 manual）+ 6ab088d R1 6 P1 立修（NewsNodeLink.node + design §8 unlink disambiguation + ORM mutate + make_news conftest 十连 + page validation + tags max_length=50）+ 9028875 子片 4 Router 8 endpoints+27 e2e + 059c7ea R2 4 P1 立修（write_event e2e 2 + design §10 metadata e2e 2 + list_by_node disambiguation + source_type 守 e2e 2）+ 子片 5 关闸 commit
  - **930 PASS / 4 skipped (M13 carryover) / R13-1 86→90 (+4) / L12 守护通过**
  - **闸门 2.5 第九次 B 栏 0 项实证**：M05+M06+M07+M08+M10+M11+M12+M13+M14 九连稳定
  - **R1 + R2 命中数据**：R1=3 subagent 7 P1→去重 6 立修 / R2=1 合并 Opus 4 项；M02-M14 十二数据点稳定 → M15+ 默认范式可作模板
  - **全局豁免业务模块首发新教训 3 条 sink**（详见 audit/m14-pilot-template-validation.md "全局豁免业务模块首发新教训" 段）：
    1. write_event project_id 类型必须 Optional[UUID]（M14 首发；M15 ActivityLog NULLABLE column + ActionType +5）
    2. N/A 元教训必须显式声明（design §14.5 + 测试 docstring 双重；防 R1/R2 把"未覆盖"当 P1 抓）
    3. endpoint 形态特殊不免除契约纪律（M13 NEW 复用 + 强化；list_by_node R2 P1-3 抓出 page_size=len() or 1 漂移）
  - **元教训防御 actionable 应用 9 项**：viewer 写 403 ✅ N/A / cross-tenant 404 ✅ N/A / cross-project node 404 ✅ link 反向 / IntegrityError 区分约束 ✅ / M12 元自审 ✅ 多处自决 / M13 "3 端点全" ✅ 形态特殊不免除 / M13 metadata 字段集 ❌→R2 立修 ✅ / write_event 异常传播 R1 service ✅ R2 e2e ❌→立修 ✅ / R-X1 失败补偿 N/A / 文件上传 N/A
  - **owner-or-admin 替代 viewer 写 403 范式**（M14 全局豁免特化）：Service _check_news_owner_or_admin + e2e 双对照（non-owner 403 + platform_admin 豁免）

## 0a. 上一版本快照（M13 sprint 完成）

- **Phase 2.0 工程基线**：✅ 100%
- **Phase 2.1 业务模块**：⏳ 65%（M01-M08+M10+M11+M12+M13 完成；下一站 M14 行业新闻；M09 superseded by M18 不实装）
- **2026-05-08 M13 sprint 完成**（8 commit 73c7175→子片 5 关闸 / 827 PASS / R13-1 79→86 / L12 守护 / **LLM 集成首发 + §12A SSE pilot + R-X3 写 M04 + AES 全链路接通**）：
  - commits: 73c7175 子片 0 prep（§14.5 + DimensionService.create_dimension_record + get_latest 接通；M04 punt 到期）+ 28a127e 子片 1（AI Provider 抽象 + MockProvider 含 aclose_called + ClaudeProvider anthropic httpx stream + Registry + 19 unit + 3 integration smoke skipif ANTHROPIC_API_KEY）+ ecb1d9c 子片 2（AnalyzeService 流式分析 + 保存 + 影响节点读 + 7 ANALYSIS_* ErrorCode + AnalysisLevel + Prompt 模板 + 20 unit）+ 368f83c 子片 3（Pydantic schema Request/Response 4 + SSE event 3 + 13 unit）+ eedecd1 R1 8 P1 立修（3 subagent 并行：spec+quality Opus 5 + reuse Sonnet 3 + quality+efficiency Sonnet 4 / 去重合并 8 / conftest 迁 make_project_with_member + set_project_ai）+ 7082b90 子片 4（Router 3 endpoints SSE+save+affected-nodes + 21 e2e）+ 79fb4cc R2 4 项立修（2 P1 + P2-4 升 P1 + P2-3 顺手）+ 子片 5 关闸 commit
  - **827 PASS / 4 skipped (3 integration smoke 待真 ANTHROPIC_API_KEY + 1 ASGITransport is_disconnected 不可靠 / R13-1 79→86 / L12 守护通过**
  - **闸门 2.5 三栏第八次 B 栏 0 项实证**：M05+M06+M07+M08+M10+M11+M12+M13 八连稳定
  - **R1 + R2 命中数据**：R1=3 subagent 12 P1→去重 8 立修 / R2=1 合并 Opus 4 项立修；M02-M13 十一数据点稳定 → M14+ 默认范式可作模板
  - **LLM 集成首发新教训 4 条 sink**（详见 audit/m13-pilot-template-validation.md "LLM 集成首发新教训" 段）：
    1. PEP 533 aclose 协议必须区分自然完成 vs 显式 aclose（MockProvider try/except GeneratorExit）
    2. Anthropic SSE delta.type 多种必须显式校验（防 thinking_delta 污染输出）
    3. SSE generator 持 AsyncSession 长达 300s 占连接池（10 用户并发吃光 default 10）→ M16/M17 立异步 SSE 连接策略
    4. design §7 metadata 字段集每条都必须 e2e 验（不依赖前端可计时绕过）
  - **元自审教训**："3 端点全覆盖"原则 SSE 形态特殊不免除——R2 抓出 P1-2 SSE 端点 cross-project node 缺测立补；sink feedback_problem_layered_analysis 失效信号
  - **R-X3 写 M04 + AES 全链路实证**：M02 ProjectService → crypto.decrypt(ai_api_key_enc) → ProviderRegistry.get → ClaudeProvider/MockProvider → 流式 chunk yield → save 调 M04.create_dimension_record 写 dimension_records + 代写 activity_log
  - **AnthropicProvider httpx 直连**（不引 anthropic 库依赖）+ MockProvider aclose_called: bool + ClaudeProvider 嵌套 async with 自动 aclose 释放底层 HTTP

- **2026-05-08 M12 sprint 完成**（详见上一版本快照）



- **Phase 2.0 工程基线**：✅ 100%（B1-B10 + 决策类全 accepted；commit b91c8d5）
- **Phase 2.1 业务模块**：⏳ 60%（M01-M08+M10+M11+M12 完成；下一站 M13，M09 superseded by M18 不实装）
- **2026-05-08 M12 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 第十次实证 / 闸门 2.5 三栏第七次 B 0 项 / **常规 own + 跨模块只读 R-X3 范式实证**）：
  - commits: `63f2f93` 子片 0 prep（§14.5 + DimensionService.batch_get_by_nodes 实装 / M04 sprint scaffold "caller sprint 实装"到期 + 3 smoke）+ `9a0f039` 子片 1 model+alembic（2 表 / G4=B 值快照 / node_id ON DELETE SET NULL passive_deletes）+ 9 model tests + `3aa7415` 子片 2 ComparisonDAO+16 unit + `99105b4` 子片 3 ComparisonService+5 ErrorCode+21 service tests + `169e948` R1 4 P1 立修（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet 三 subagent 并行；nodes_count → node_ids_count metadata 漂移 / _mk_snap 迁 conftest make_snapshot fixture / rename write_event 异常传播测试 / Core UPDATE updated_at 显式刷）+ 4 coverage 补 + `589407c` 子片 4 router+6 endpoints+15 e2e（POST/PUT/DELETE/GET matrix/GET list/GET detail；viewer 写 3 端点全 403 主动复制）+ 子片 5 关闸（本 commit）
  - **742 PASS / 0 fail / ruff 净 / R13-1 74→79（+5）+ L12 守护通过**
  - **R-X3 跨模块只读范式实证**：DimensionService.batch_get_by_nodes（M04 own / M12 首 caller）+ NodeDAO.list_by_ids 校验 / 不嵌跨模块 metadata 在 response（cells-only）
  - **R2 P1 裁决型新教训 1 条**：design §7 ComparisonMatrixResponse 草案 nodes+dim_types+cells 三字段 vs 实装 cells-only — 与 ADR-003 规则 1 + M02-M11 R-X3 范式一致 → 裁决 = cells-only + scaffold disambiguation 注释（与 M01 D1 7 seam reconcile 同形态）
  - **元自审教训**（主流程错误 + 自纠）：让 CY 拍裁决型 R2 P1（matrix metadata）违反 feedback_problem_layered_analysis 失效信号 — L1 R-X3 范式已锁 → AI 应自决 + design 回写，不应让 CY 拍。下次 R-X1/R-X2/R-X3 范式既锁的裁决型 P1 不再让 CY 拍，直接落 disambiguation
  - **元教训防御 actionable 应用清单（M02-M11 沉淀 + 主动复制不等抓）**：viewer 写 3 端点 403 ✅ / write_event 异常传播 3 写端点全 ✅（rename R1-C P1-02 立修补）/ cross-tenant 404 ✅ / cross-project node 422 ✅ / IntegrityError 区分约束 N/A / R-X1 失败补偿 N/A / 文件上传 N/A
  - **R1 + R2 命中数据**：R1=4 P1（去重；3 subagent 并行）/ R2=1 P1 裁决型（1 合并 Opus）/ M02-M12 十数据点 R2 稳态 0-1 P1 区间（M11 R-X1 首发 3 P1 是异常点）
  - **闸门 2.5 三栏第七次 B 栏 0 项**：M05+M06+M07+M08+M10+M11+M12 七连稳定 → M13+ 默认范式可作模板
- **2026-05-08 M11 sprint 完成**（8 commit + R1+R2 闭环 / L1 第九数据点 / 闸门 2.5 第六次 B 0 项 / **首个 R-X1 orchestrator 范式实证**）：
  - commits: `8ef59b3` 子片 0 prep（§14.5 + 3 跨模块 batch_create_in_transaction 接通 M04 R1-A A6 + M06/M07 scaffold 全到期）+ `4ed8dbe` 子片 1 ColdStartTask model + alembic + 14 model tests + `090621a` 子片 2 ColdStartDAO + 12 unit tests + `e93057c` 子片 3 ColdStartOrchestratorService + 7 ErrorCode + 17 service tests + `2ccd579` R1 6 P1 立修（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet 三 subagent 并行；frontmatter 字面 / design §5 disambiguation / dimensions 显式抛错保护 R-X1 完整性 / _mark_failed write_event 兜底 / _make_task 进 conftest / ISSUE_CATEGORIES 跨模块导出）+ `aba873a` 子片 4 router + 4 endpoints + 11 e2e tests（POST /upload multipart / GET list / GET detail / GET /template）+ `2c39980` R2 2 P1 立修 + 1 punt（file.size 预检 + filename sanitize；commit-then-rollback boundary punt M17）
  - **674 PASS / 0 fail / ruff 净 / R13-1 67→74（+7）+ L12 守护通过**
  - **首个 R-X1 orchestrator 范式实证**：M11 不直 INSERT 跨模块表 / 调 NodeService + CompetitorService + IssueService 3 个 batch_create_in_transaction（DimensionService.batch_create 实装但 dim_key→type_id 解析延迟到下游 sprint）/ 4 service.batch_create_in_transaction 签名稳定 4 参（project_id + actor_user_id + xxx_data）
  - **R-X1 首发新教训 2 条**：
    1. **失败补偿 commit boundary**（R2 P1-01 punt）：M11 router commit-then-rollback 把 task=failed 元数据 + 部分业务 INSERT 一起 commit，违 design §1 G6 全量回滚契约。彻底修复需独立 connection 或显式 SAVEPOINT，与测试 fixture join_transaction_mode='create_savepoint' 不兼容；punt M17 sprint 抽独立 helper（异步 zip 导入将 reuse；与 R-X1 第二实例对照）。**修法 sink 候选立规**：「R-X1 orchestrator 失败补偿写入路径必须用独立 connection 或显式 SAVEPOINT，禁止与业务事务共享 commit boundary」
    2. **multipart 攻击面**：M11 是首个文件上传 endpoint；R2 抓出 file.read() 整文件后才 size check + filename 无 sanitize。立修 file.size 预检 + _sanitize_filename(basename + 控制字符 strip + 长度截断)。**修法 sink 候选立规**：「文件上传 endpoint 必须 file.size 预检 + filename sanitize；禁止裸 file.read() + raw filename 直入 DB / response header / activity_log metadata」
  - **元教训防御 actionable 应用**（M11 R1+R2 主动复制不等抓 / 首次 R-X1 模块）：
    - viewer 写所有写端点 403 全覆盖（M07 立 / M08 应用 / M11 写端点只 1 → test_viewer_write_upload_returns_403 ✅）
    - write_event 异常传播测试（M04+ 范式）✅
    - cross-tenant 404（M02 范式）✅
    - R1.5 reconcile checkpoint（M10 NEW）：R2 反向命中的不是 R1 撤销项 → 元教训不适用 / 但 R2 命中 R1 未抓的范式新教训（commit-then-rollback / 文件上传攻击面），属"R-X1 范式首发"非"反复"
  - **R1 + R2 命中数据**：R1=6 P1（去重；3 subagent 并行）/ R2=2 P1 立修 + 1 punt + 4 P2（1 合并 Opus；M11 R2 命中超平均 → R-X1 endpoint 范式独有，9 数据点中第 9 仍稳定）
  - **闸门 2.5 三栏第六次 B 栏 0 项**：M05+M06+M07+M08+M10+M11 六连稳定 → M12+ 默认范式可作模板

- **2026-05-08 M10 sprint 完成**（6 commit + R1+R2 闭环 / L1 第八数据点 / 闸门 2.5 B 0 第五次 / **纯读聚合范式首次实证** / **元教训新增 2 条**）：
  - commits: `098a2ee` 子片 0+1+2 (DAO + Service + 21 tests) + `b018aad` 子片 3 + R1 P1 立修 + 子片 4 关闸 [hash]
  - **613 PASS / 0 fail / ruff 净 / R13-1 67=67 + L12 守护通过**
  - **纯读聚合范式**（无 model/migration / ADR-003 规则 2 豁免 / **4 子片简化 / R1 三 subagent 合并为 1 Opus**）— 首次实证 M11+ 纯读模块简化模板
  - folder 均值"迭代后序遍历"D-1 算法 + 分母=0 早返回 M10-B3
  - **元教训新增 2 条 sink memory**：
    1. **纯读模块 schema-service contract drift 风险**：M02-M08 业务模块靠"写端点 + activity_log + IntegrityError"三层强契约兜底；M10 纯读全无，schema 字段语义只能靠 docstring + 测试断言守。R1 立修 folder.filled_count subtree rollup 被误连 asyncio.gather false positive 一起撤销 → R2 reviewer 抓出 schema-service drift。**修法**：纯读模块 docstring 每字段必须配套 ≥1 unit test 断言守护
    2. **R1→R2 reconcile 缺失**：R1 P1 立修被撤销但启动包陈述未同步更新 → R2 reviewer 看到代码 vs 启动包不一致。**修法**：R2 dispatch 前加 R1.5 reconcile checkpoint（grep R1 立修关键词在代码中真实存在）


- **2026-05-08 M08 sprint 完成**（9 commit + R1+R2 闭环 / L1+L2+L3 第七次实证 / 闸门 2.5 三栏 B 0 项第四次实证 / **R-X2 第四真注入双向 + delete 语义** / **元教训"M07 P1 防御 actionable 主动应用"首次实证**）：
  - commits: `eed7749` 子片 0 prep + `fc142ad` 子片 1 model + `1fe57fe` 子片 2 DAO 双向 OR + `7b3d3eb` 子片 3 Service R-X2 第四真注入(双向 delete) + `de57b28` 子片 4 Router 5 endpoints + `868d290` R1+R2 P1 共 8 项立修（5 步分层全 L3 范式应用）+ 子片 5 关闸
  - **586+ PASS / 0 fail / ruff 净 / R13-1 64=64 + L12 守护通过**
  - **R-X2 实证 4 数据点对照表**（详见 audit/m08-pilot-template-validation.md）：
    - M04: 单向 delete (CASCADE)
    - M06: 单向 delete (CASCADE)
    - M07: orphan SET NULL (passive_deletes)
    - M08: **双向 OR delete**（source/target 两 FK 同款 CASCADE）
    - 接口共享（Protocol 4 参签名）+ 业务语义分化（DELETE/UPDATE/双向）= L1 锁 + L2 决策合理抽象
  - **元教训首次实证 actionable**：M07 立的"viewer 写所有写端点 403 全覆盖"P1 范式被 M08 sprint **启动 reconcile A7 主动列入清单**+ 子片 4 router test cases 列表全覆盖 + 子片 3 service test write_event 异常传播 monkeypatch — R2 没抓出 viewer 写覆盖问题（验证元教训内化生效）。新元教训 sink 进 audit "M02-M_{N-1} 跨模块测试契约主动复制清单" actionable 范本
  - **R1 命中**：3 subagent 共 **7 P1 立修**（5 步分层全 L3 范式应用，含 RelationTypeInvalidError R13-1 注释 / docstring 双重防御消歧 / Protocol target_type 分发表 / _make_relation conftest 五连规则 / RelationNodeNotInProjectError 404→422 范式对齐 / count_by_project index-only / asyncio.gather 并行）+ 多 P2
  - **R2 命中**：1 P1 立修（self_loop code 映射 design §13 字面 drift；移 schema model_validator → service 层独家范式与 M02-M07 一致）+ 2 P2 punt


- **2026-05-08 M07 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 第六次实证 / 闸门 2.5 三栏 B 0 项第三次实证 / **R-X2 第三真注入 orphan 语义实证** / 元教训"M06 P1 范式 M07 复发立修"首次产出）：
  - commits: `b81c0d8` 子片 0 prep（§14.5 + §5 预防性消歧）+ `13152e1` 子片 1 Issue model + alembic + Node passive_deletes + `a917235` 子片 2 DAO + SELECT FOR UPDATE + orphan_by_node_id + `e6e0873` 子片 3 Service + R-X2 第三真注入 + 状态机 4 状态 + `6a1072f` R1 1 P1 立修 get_for_embedding 空字符串 + 子片 4 Router 7 endpoints + 15 e2e tests + `8246984` R2 1 P1 立修 viewer 写 4 端点全覆盖 + 子片 5 关闸
  - **538+ PASS / 0 fail / ruff 净 / R13-1 59=59 + L12 守护通过**
  - **R-X2 第三真注入 orphan 语义**（接口共享 / 行为契约分化 — UPDATE SET NULL vs DELETE）+ **7 处代码 anchor 防误读**（design / model / migration / DAO / service / Protocol / lifespan）
  - **关键元教训**（**首次"复发 + 应用立修"实证**）：M06 R2 立的"viewer 写**所有**写端点 403"P1 范式在 M07 复发；R1/R2 prompt 提了仍漏 → R2 抓到 → 立修。**根因**：单条 P1 立修不自动横切到下一模块；纯靠"下一 sprint reviewer 比对 M_{N-1} audit"被动传递；仪式化提示 ≠ 实施时真做。**修法 sink 到 feedback_problem_layered_analysis 失效信号**：跨模块测试契约（如三层权限 testpoint）应升级到 design 公共段或 testpoint 模板，让"模块 design 必须含 X testpoint"成为闸门 3 检查项
  - **R1 命中**：3 subagent 共 1 P1 立修（去重）+ 8 P2 punt；R1-A 0 P1（A7 §5 预防性消歧避免漂移）；R1-B 复用率 ~95%；R1-C 1 P1（get_for_embedding 空字符串）
  - **R2 命中**：1 合并 Opus 1 P1 立修（M06 元教训复发）+ 2 P2 punt（IssueResponse join 字段 / page_size 分页）


- **2026-05-08 M06 sprint 完成**（6 commit + R1+R2 闭环 / L1+L2+L3 节奏第五次实证 / 闸门 2.5 三栏第二次 B 栏 0 项实证 / R-X2 第二真注入零摩擦实证）：
  - commits: `c84f6f2` 子片 0 prep（§14.5 默认范式复用 + ck_clause 别名规范化 5 处一致）+ `d01c5ad` 子片 1 双表 model + alembic + Node back_populates + 8 model tests + `f7211fb` 子片 2 DAO + 18 unit tests + `86195cc` 子片 3 Service + R-X2 第二真注入 + 4 ErrorCode + 20 service tests + lifespan register_child_service("competitor") + `c792263` R1 3 P1 立修（design §5 多表事务消歧 + IntegrityError 区分约束名 + write_event 异常传播测试）+ {子片 4 commit hash} R2 0 P1 + 子片 5 关闸 commit
  - **473+ PASS / 0 fail / ruff 净 / R13-1 53=53 + L12 守护通过**
  - **L1+L2+L3 节奏第五次实证（M02-M06 五数据点稳定）**：M07-M20 默认范式可作模板（不再重复说明）
  - **R-X2 第二真注入零摩擦实证**：M04 sprint 升级 Protocol 4 参 + 5 处 design 回写的元教训"5 步分层识别 L1 跨模块契约层"，在 M06 sprint plug-in CompetitorService.delete_by_node_id 完全无修改成本 — feedback_problem_layered_analysis "防本模块绕"价值的"防御未来"实证
  - **闸门 2.5 三栏 B 栏 0 项第二次实证**（M05 立 / M06 复用，防御未来非修复存量）：8 项原候选全 grep 命中 L1/L3 锁规归 A 栏；M05 立的"自审一问必先 grep 既有规则"失效信号在 M06 是首次防御未来实证
  - **R1 命中**：3 subagent 共 3 P1（去重）+ 6 P2 punt；R1-A 抓 M06 design §5 多表事务"with db.begin()"漂移（M04 reconcile 范式漏跟进）；R1-B 命中比例 ~14% / 复用率 90%+ 优于 M02-M05 基线；R1-C 抓 IntegrityError 未区分约束名（M05 P1-01 立规回退）+ write_event 异常传播测试缺失（M04 范式未复制）
  - **R2 命中**：1 合并 Opus 0 P1 + 3 P2 punt（display_name join / pros_and_cons 类型退化 / ref 404 e2e gap）— 与 M02-M05 R2 P1 命中 0-1 区间稳定，第五次实证 1 合并 Opus 范式有效
  - **M05 punt 池接通**：ck_clause 别名规范化（5 处一致 commit c84f6f2）


- **2026-05-08 M05 sprint 完成**（6 commit + R1+R2 闭环 / L1+L2+L3 节奏第四次实证 / 闸门 2.5 三栏首次 B 栏 0 项实证）：
  - commits: `811d6bc` 子片 0 prep（§14.5 + M04 §5 消歧 + make_dim_type 抽出 4 文件 60+ 改）+ `de53192` 子片 1 model + alembic + Node back_populates + A6 covering 索引 + `d3374fe` 子片 2 DAO + 18 unit tests + `063cbd4` 子片 3 Service + 3 ErrorCode + 19 service tests + B2 不变量验证 + `5e0e239` R1 P1 立修（IntegrityError 区分约束 + _make_version 进 conftest）+ {TBD R2+子片5 commit}
  - **412 PASS / 0 fail / ruff 净 / R13-1 49=49 + L12 守护通过**
  - **L1+L2+L3 节奏第四次实证（M02 首/M03 二/M04 三/M05 四，四数据点稳定）**: R1=3 subagent + R2=1 合并 Opus + schema 子片禁单跑 + 子片 5 不单跑（≥80% SKIP 例外）= 默认范式可作 M06-M20 模板
  - **闸门 2.5 三栏首次 B 栏 0 项实证**：5 项原列 B 栏（B1 索引 / B2 并发测试 / B3 schema 校验 / B4 punt 顺修 / B5 race 转换）被 5 步分层分析法 step 1-2 识别后全收 A 栏（L1 已锁 / L3 范式 / punt 工序到期）；CY "做不出决定就是分析不对，没分清层次" 一击命中 → 失效信号已沉淀到 memory `feedback_problem_layered_analysis`
  - **R1 命中**：3 subagent 共 4 P1（去重）+ 11 P2 punt；R1-A Opus 抓 design 真相源内部矛盾（§6 ASC vs §9 DESC + 三处索引名）；R1-B Sonnet 抓 _make_version 应进 conftest（M04 R1-B C1 规则延续）；R1-C Sonnet 抓 IntegrityError 不区分约束名（is_current=True 并发场景误导 caller）
  - **R2 命中**：1 合并 Opus 3 P1 + 4 P2 punt；R2 P1-01 quality-spec 关键路径 100% 假 DONE（403 + viewer 路径零覆盖）；R2 P1-02 design §7 created_by_name 字段 M04 范式延续不实装（子片 5 删 design 字段）
  - **元教训沉淀**：闸门 2.5 自审仪式化失效首次实证；B 栏 0 项不是异常；R1 三 subagent + R2 一合并 Opus 第四数据点确认稳定


- **2026-05-07 M04 sprint 完成**（7 commit + R1+R2 闭环 / L1+L2+L3 节奏第三次实证 / 5 R-X5 子选项 + 新决 NodeChildrenServiceProtocol 4 参升级）：
  - commits: `4c3c413` 子片 1 model+migration+helpers.py + `3aea93b` 子片 2 DAO + `6fd4808` 子片 3 Service+R-X2 真注入+Protocol 升级 + `0ca7e5b` R1 修(4 P1) + `de239c2` 子片 4 Router + `5a97824` R2 修(1 P1) + `c4037a7` 子片 5 design+audit
  - **347 PASS / 0 fail / ruff 净 / R13-1 46=46 + L12 守护通过**
  - **L1+L2+L3 节奏第三次实证 (M02 首 / M03 二 / M04 三; 三数据点稳定)**: R1=3 subagent + R2=1 合并 Opus + schema/子片 5 不单跑
  - **R1 命中**: 3 subagent 共 4 P1 立修 + 10 P2 punt; R1-A Opus 抓 design 5 处 Protocol 回写漏; R1-C Sonnet 抓 service 三层防御 + DimensionTypeDisabledError 全缺口
  - **R2 命中**: 1 合并 Opus 1 P1 立修(B6.x enabled_dimension_types 字段名/SQL 不一致)，是 R1 三 subagent 没抓到的"命名 vs SQL vs design 文字"三处一致性新角度
  - **R-X5 子选项 5 项实证**:
    - 1) A5 enqueue B 推迟 + get_for_embedding A 现在建 (M03 同款复用)
    - 2) **NodeChildrenServiceProtocol 4 参升级 (M04 sprint 新决)** — 5 步分层分析法 L1 跨模块契约层定位; 5 处 design 真相源回写 (M03 §6/§8 + M06 §6 + M07 §6 + README R-X3)
    - 3) pdc-existence-strict (R1-C C3.2 立修触发新决): pdc 不存在或 enabled=False 都抛 DimensionTypeDisabledError
    - 4) _ck_clause 提取 (B1 闸门 2.5 CY 拍 A; M03 R1-B C2 punt 闭环) → migrations/helpers.py + m01/m02/m03 import 回写
    - 5) make_node fixture 位置 (B2 闸门 2.5 自我修正 → A 栏): tests/conftest.py 加 fixture + M03 内联迁移
  - **新发现 (子片 5 audit 元教训 2 条)**:
    - 1) Protocol 签名升级触发的 L1 跨模块契约层识别（feedback_problem_layered_analysis 实质性"防本模块绕"拦截价值首次产出）
    - 2) 闸门 2.5 reconcile 自我修正信号（CY "按之前流程定不下来吗" 反馈触发）

- **2026-05-07 M03 sprint 完成**（5 子片 + R1+R2 闭环 / L1+L2+L3 节奏第二次实证 / 4 R-X5 子选项复用 + 1 新决）：
- **2026-05-07 M03 sprint 完成**（5 子片 + R1+R2 闭环 / L1+L2+L3 节奏第二次实证 / 4 R-X5 子选项复用 + 1 新决）：
  - commits: `800e632` §14.5 prep + `d174e90` 子片 1 models + `4887f7c` 子片 2 DAO + get_for_embedding + `4e48cb9` 子片 3 Service + `ce73570` R1 修 + 子片 4 schema + `4a1a615` 子片 4 Router + `656e05c` R2 修 + 子片 5 design 回写
  - **285 PASS / 0 fail / ruff 净 / ci-lint R13-1 41=41 + L12 守护通过**
  - **L1+L2+L3 节奏第二次实证** (M02 首 / M03 第二; 双数据点稳定):
    - L1 总则: sprint ≥1 次 + ≥50 行 OR ≥2 文件触发 + 触发例外条款 — 全合规
    - L2 sprint 计划: §14.5 commit `800e632` (闸门 3.4 强制存在)
    - L3 实证回写: `design/audit/m03-pilot-template-validation.md` (R-X5 子选项 + R1/R2 命中比例 + PT1-PT3 + L1 双数据点)
  - **R1 命中**: 3 subagent 共 4 P1 立修 + 12 P2 punt; B reuse Sonnet ~18% 与 M02 17% 稳定
  - **R2 命中**: 1 合并 Opus subagent 4 P1 立修 + 5 P2 punt; M02 (6 P1) + M03 (4 P1) 双数据点验证 1 subagent 足够
  - **R-X5 子选项**:
    - A4 enqueue B 推迟 / get_for_embedding A 现在建: design §6.X status 改 "已落地 + commit hash"
    - A5 batch_create 拓扑责任: B 半路径推迟 + design §6.X 加 A5 段 (M11/M17 sprint 启动时拍)
    - A6 child_services 分发语义 reconcile: 全 subtree 全 service 调用 (noop 容忍) + design §6.X 加 A6 段
    - 复用 M02 4 项 (C team_id / A SearchConfig / B move-team / R13-1 标记位置)
  - **新发现 (R1-B C1)**: 跨模块 test helper 重复 → conftest.py 加 make_project fixture, 47 测试调用迁移; 未来 M04+ sprint 启动前应预查 conftest 是否已有可用 fixture

- **2026-05-07 M02 sprint 完成**（5 子片 + 2 review 闭环）：
- **2026-05-07 M02 sprint 完成**（5 子片 + 2 review 闭环）：
  - commits: `c6b97d6` 子片1 models + `a42dc81` 子片2 DAO + `10f2f54` 子片3 service+AES + `c9b0618` 子片4 router (12 endpoints) + R1 修 `e5651bf` (8 项) + R2 修 `e7b1b7f` (6 P1)
  - **205 PASS / 0 fail / ruff clean / ci-lint R13-1 34=34 + L12 + S5d-改进**
  - **L1+L2+L3 review 节奏首次实证** (commit `19acff6`): 闸门 3.4 L1 总则 + M02 §14.5 L2 sprint review 计划 + L3 子选项实证回写到 audit
  - **5 步分层分析法首次落地** (`feedback_problem_layered_analysis` memory): 用于 review 触发粒度冲突 + 4 实证子选项决策
  - **4 R-X5 实证子选项全决** (`design/audit/m02-pilot-template-validation.md`):
    - C 路径 team_id: DAO 完全允许
    - A 路径 SearchConfig owner: M02 own raw types
    - B 路径 move-team: 不实装 router → OpenAPI 不含
    - R13-1 ErrorCode 标记位置: code 注释 (不入 ci-lint 附加规则)
  - **AES helper 落地** (api/auth/crypto.py 横切层 + 14 test PASS + 05-security-baseline §4.1 回写)
  - **后置债** (M03 sprint 顺手清):
    - check_project_access vs require_owner 重复 JOIN (性能优化)
    - batch_update N 条 UPSERT 应用 PostgreSQL ON CONFLICT
    - ProjectMember.joined_at vs created_at 冗余讨论 (design 字面如此)
    - update_project exclude_none=True PATCH 语义 + setattr 白名单
- **2026-05-07 M02 design v2 升级** (commit `b0dd21b` / `0b72332` / `19acff6`):
- **2026-05-07 后续 session 产出**（M02 sprint 启动 reconcile pass 元反思 → 设计体系升级 + 11 处 baseline-patch 回扫 + 修复存量）：
  - **5 个体系盲区 + 2 体系级新原则**（详见 `design/audit/time-dimension-blindspot-2026-05-07.md`）
  - **8 条新规则落地**：
    - 6 原则 #6 横切 vs 业务关注必须显式判定（`00-architecture/06-design-principles.md` v2）
    - 04-layer Q7 横切层定义（`00-architecture/04-layer-architecture.md` v2）
    - R-X5 baseline-patch 时序契约（主标准 Q1+Q2 + 退化 A/B/C + 结构性约束 + 子选项留空待实证）+ R-X6 横切 helper 必横切层 + R3-6 启动数据细化 3 子项 + frontmatter helpers 字段约束（`02-modules/README.md` v2）
    - 闸门 2.5 S2 注释 4 字段强制 + reconcile 三栏分类（`00-phase-gate.md`）
    - accepted-minimal §7 early adopter 修订（含横切 vs 模块特定判断前置 + §7.1/§7.2）（`05-security-baseline.md` + 03/04 引用段）
  - **11 处 baseline-patch 实施期处理段回写**：M02（A1+A2+A3）/ M03/M04/M06/M07（A4-A7 同款 M18 baseline-patch）/ M15（A8+A9 enum）+ M02 §3.Y dimension_types 启动数据 + §3.Z early adopter AES helper
  - **修复存量**（T12）：10 horizontal helper docstring 加 horizontal+owner 4 字段 + 3 design 灰区（ADR-001/M18/M17）显式标 horizontal owner
  - **整体扫描结果**（T11）：0 处真正反模式存量——CY 一直凭 sense 把横切 helper 放对位置；立规价值是防御未来 sprint 漂移
  - **回归**：pytest 118 PASS / 0 fail / 0 xfail / ruff 净 / ci-lint.sh R13-1 22=22 + L12 守护通过
  - **KB 沉淀**（跨项目）：`02-技术/架构设计/设计前置方法论-补丁01-时间维度.md`（主方法论加指针）
  - **元教训 4 条**：立规分两层（结构性可前置 / 工程具体须实证）/ 立规必判 horizontal vs module-specific / 立规防御未来 vs 修复存量 / L1/L2/L3 时间维度切分
- **2026-05-07 M01 sprint 闭环**（commits c1e3acc → 2704d0f + design 回写 commit pending）：
  - 5 子片全 PASS：read-only auth / PATCH me / admin endpoints / ADR-004 P2 全 / CI 守护
  - 测试 113 PASS + C9 isolated 转 PASS（共 117+ PASS / 0 xfail）
  - design / ADR 回写（M01 实施反馈）：
    - ADR-004 §3 #5 同秒边界 + §3.5 P2 信任链 + §3.6 P3 形态
    - M01 §4 R4-2 加 active→pending 禁 + 同值豁免说明
    - M01 §10 多事件原子组顺序约定 + P2 入站不写 audit 策略
  - ci-lint.sh 加 L12 守护（M01 不调 M15 activity_log_service）
  - design/audit/m01-pilot-template-validation.md（PT1-PT3 living tracker）
- **2026-05-07 session 产出**（P5 4 🔴 + F-9 收口；commits 2e93de9 + b24f049）：
  - R4-3a 非常规态登记规约落地（02-modules/README.md）：5 类 + 严格档 + 6 字段态表 + 3 字段边表
  - M01/M16/M17/M18 四模块 mermaid 按 R4-3a 回扫（pending / cancelled / partial_failed / failed 拆出登记表）
  - ADR-002 §1.1 触发方清单从 3 → 10 条，区分 Queue 与直接 SQL 形态
  - M16/M17/M18 模块端反向引用 SYSTEM_USER_UUID（M16 §9+§10+§12B / M17 §12 / M18 §10+§12D）
  - P5 audit 5 finding 标 fixed（F-1/F-4/F-6/F-7/F-9）
- **2026-05-06 session 产出**（设计前置 audit 16h）：
  - `design/audit/lessons-learned.md`（8 元教训 + 6 校准）
  - `design/audit/scaffold-design-reconcile.md`（7 对错型 seam）
  - `design/audit/full-reconcile-pass.md`（11 结构性 seam）
  - `design/audit/contracts-draft.md`（4 条对账契约）
  - `design/audit/p5-state-machine-reachability.md`（10 findings：🔴4 / 🟡3 / 🟢3）
  - `design/00-architecture/08-namespaces.md`（命名空间登记 + 业界标准）
  - 4 个 baseline-patch commit（ErrorCode value lower / ActionType CRUD split + dot→snake / ADR-002 §1.1 SYSTEM_USER_UUID / 20 模块 references frontmatter 回填）

## 1. 推荐 prompt 顺序

### Prompt 0 — M19 sprint 启动（**当前推荐 / M18 已完成 9 commits 1480 PASS / 复制下方代码块到新 session**）

```
继续 prism-0420 M19 sprint（导入/导出 / complexity=low / pilot=false / Phase 2.1 90%→95%）。

状态快照（已 commit + push 到 origin/main）：
- M18 sprint ✅ 完成 / 1480 PASS / 5 skipped / R13-1 124→136 / L12+L13+R14 全过 / ruff 净
- 累计 9 commits（90f7672 启动期 / 6c27898 子片 0 prep / fbea749 子片 1 / c7aca1f 子片 2 / f2da4e2 子片 3 / 76c6d9b R1 立修 / 68e981e 子片 4 / 92e09d3 R2 立修 / 子片 5 关闸）
- Phase 2.1 业务模块 ⏳ 90%（M01-M08+M10-M18 完成 / M09 superseded by M18 不实装 / 下一站 M19 / M20 团队最后做）
- bypass log #2 配套验收最终 ✅（M18 R1=3 + R2=1 真跑 / 累计 bypass 不复位 / 第 3 次触发对闸门 3.4 L1 总则 review）

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + 快速上手序）
2. _handoff/next-session.md §0 状态快照（M18 完成 + 元贡献 7 项 + sink 候选 4 项 + 新 punt 5 项）
3. _handoff/cross-sprint-punt-pool.md（M18 新增 #20-#24 / 触发点 A 4 项 STILL_PUNT / 真漏洞 #11 立规已落 dimension 修存量推迟）
4. design/00-roadmap.md（Phase 2.1 90% / M19 [ ] 待启 / current_phase 字段）
5. design/00-phase-gate.md（闸门 3.4 L1 总则 3 类例外 + 闸门 2.5 reconcile pass）
6. design/02-modules/M19-import-export/00-design.md（status=accepted / pilot=false / complexity=low / 只读 export 为主）
7. design/audit/m18-pilot-template-validation.md（M18 元贡献 7 项 + R1+R2 数据点 16）
8. design/audit/m18-startup-reconcile.md（启动期 reconcile 三栏范式参考）
9. api/services/import_service.py（M17 1003 行 / R-X1 第二实例 / Service 大 Class 范式 / M19 导入路径可参考）
10. api/services/embedding.py（M18 horizontal helper / owner=M18 / 4 字段 scaffold 简化注释范式）
11. memory：feedback_subagent_sprint（聚合：sprint 启动闸门 + subagent 接口契约 T1-T6 + R1+R2 流水线）/ feedback_decision_transparency / feedback_code_first / feedback_completion_audit / feedback_self_decide_no_ask / feedback_design_first / feedback_problem_layered_analysis（5 步分层 / B 栏 0 时禁列）/ feedback_usage_budget v3（单会话 $10 / >$15 强制开新会话）

任务（M19 sprint）：

启动期（必做项 + reconcile pass）：
- 闸门 2.5 reconcile pass（A/B/C 三栏强制 / B 栏穷举 L1 锁规 / B 栏 = 0 时禁列）
- M18 sprint 配套承诺验收：bypass log #2 累计 2 → M19 必继续真跑 R1=3 + R2=1（不复位 / 不再降级）
- 检查 design status（M19 design status=accepted 已 2026-04-21 / 不需 audit）
- 检查 baseline-patch（M19 design 是否触发其他模块 baseline-patch / 看 references）
- §14.5 sprint review 拆分计划补完（参 M17/M18 范本 / 闸门 3.4 L1 总则强制段）

子片拆分预期（M19 complexity=low / 估 5+ 子片）：
- 子片 0 prep：§14.5 补齐 + scaffold 简化决策（horizontal helper 复用：write_event / TaskPayload / get_for_embedding 上游接口 / EmbeddingService.enqueue 接通 N/A 视情况）
- 子片 1：model + alembic（如需 / M19 主要只读 export 不一定有新表 / 看 design §3）+ ActionType+N + TargetType+N（看 design §10）+ tests
- 子片 2：DAO（export_service 只读复用 DimensionDAO/VersionDAO/CompetitorDAO/IssueDAO/NodeDAO ADR-003 规则 1 + 任何 import 路径 DAO 如有）+ tests
- 子片 3：ImportService / ExportService + Schema + 3+ ErrorCode（EXPORT_NODE_LIMIT_EXCEEDED / EXPORT_NODE_NOT_IN_PROJECT / EXPORT_EMPTY_CONTENT）+ tests
- 子片 4：Router + e2e（含 cross-sprint 元教训 actionable 18 类 + 主动复制 / N/A 显式声明）+ R1+R2
- 子片 5：关闸（design 回写 / audit/m19-pilot-template-validation.md / handoff §0 / roadmap M19 + Phase 2.1 90→95% / cross-sprint punt 池接通 / require_platform_admin 去重 punt #20 评估是否本 sprint 触发）

R1 + R2 范式（bypass log #2 配套继续 / 不降级 / M02-M18 第十六数据点确认稳定）：
- R1 = 3 subagent 并行覆盖子片 1+2+3 合并审（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）
- R2 = 1 合并 Opus subagent endpoint 单审（子片 4 router）
- spawn prompt 必含 ls/find 穷举要求（cross-sprint 元发现 #5 立规字面）
- spawn 后 >5min 无通知必主动 ping（feedback_subagent_completion_check）

红线（M02-M18 实证 + R14 + 启动期 + R-X1 第二实例 + M17/M18 NEW）：
- viewer 写所有写端点 403 全覆盖（admin endpoint require_platform_admin 单测 + e2e）
- read 权限 403（M15 立规 / M18 复用 / M19 export 路径 cross-project denial）
- write_event 异常传播测试 e2e 字面验
- cross-tenant 404 + cross-project node 404
- IntegrityError 区分约束名（M05 P1-01 立规 / M17 启动期 design-principles 清单 6 + ci-lint R15 守护立规）
- M11 R-X1 失败补偿 + M11 文件上传 + M13 SSE + M14 endpoint 形态 + M15 横切表 owner enum 4 处同步 + M16 R14 + CAS UPDATE + BackgroundTasks 自起 SessionLocal + M17 R-X1 第二实例 + idempotency project_id + IntegrityError 端到端 + M18 EndpointRequest schema 不继承 TaskPayload + 占位 metadata _stub:True + 测试反模式 ci-lint 守护
- M18 NEW EndpointRequest schema 不继承 TaskPayload（R2 sink 立规 #1 / M19 endpoint Request 必继承 BaseModel / TaskPayload 仅供 Queue payload）
- M18 NEW 占位 metadata _stub:True 标记（R2 sink 立规 #3 / 防 activity_log 假数据 / M19 export/import endpoint 占位期严格遵守）
- M18 NEW 测试反模式（R2 sink 立规 #4 / 不允许 assert True / assert in (永真) 占位 / N/A 声明搬 design.md docstring）

启动注意：
1. usage_budget v3 单会话 $10 上限 / >$15 强制开新会话；M19 是 complexity=low 估单会话能完成
2. 每子片间 commit；R1 / R2 跑完看 finding 决定是否 spawn 修 subagent
3. design 已 accepted 2026-04-21（无需 audit）但 spec+quality 子片 1+2+3 仍需 R1
4. 1480 PASS 是 baseline / 任何子片完不能下降
5. M20 团队是最后一个 own sprint（M19 完成后唯一剩余）

任务起点：
- 进入启动期：闸门 2.5 reconcile pass（A/B/C 三栏 / B 栏穷举 L1 锁规）+ baseline-patch 检查 + §14.5 补齐
- 子片 0 prep：scaffold 简化决策 4 字段注释（horizontal helper 复用清单）
- 子片 1: model + alembic（视 design §3）+ ActionType+N（视 §10）+ TargetType+N + tests
- ...继续子片 2 → 5
```

### Prompt 0' — M18 sprint 启动（已完成 2026-05-09，仅供历史追溯）

```
继续 prism-0420 M17 sprint 实施代码（M17 AI 导入 / Queue §12C / 首个 arq Queue 消费者 + R-X1 orchestrator 第二实例；启动期 4 大必做项已 commit ad069c0 完成 / 1063 + 16 = 1079 PASS / R13-1 116 / R14 守护 / L12+L13 / Phase 2.1 80%）。

启动期 4 大必做项已 ✅ DONE（commit ad069c0 / 11 文件 / +543 / 不再跳过）：
A. ✅ 闸门 2.6 Queue Scaffold mini-sprint — TaskPayload 基类 + dummy 子类 + 12 pytest（api/queue/base.py + tests/test_queue_base.py）
B. 🔜 R1+R2 review 恢复 spawn subagent — 在本 sprint 子片 1+2+3 R1 + 子片 4 R2 时跑（不再 self-审）
C. ✅ 闸门 3.4 L1 总则修订 — context budget pressure 触发例外段 1→3 类（design/00-phase-gate.md + bypass log #2 标 ✅ review 完成）
D. ✅ R-X1 失败补偿 helper — api/services/orchestrator_helpers.py:compensation_session + 4 pytest；M11 ColdStart 迁移留本 sprint 子片 0 prep 内做
+ A7 ✅ cross-sprint #11 IntegrityError 立规 — design-principles 清单 6（service 层 INSERT 凡 UNIQUE 必 catch 转业务异常）
+ 新失效信号 sink memory feedback_problem_layered_analysis：reconcile pass 列 B 栏前未穷举 L1 锁规候选 = 0 时仍列 B 栏

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M16-sprint-complete + 本 Prompt 0 M17 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/_handoff/cross-sprint-punt-pool.md（**Punt 池总表 / M17 启动 reconcile 必查 + 真漏洞 #4 SSE+M16 BackgroundTasks 已不触发同款问题需重新评估时机 / #7 R-X1 失败补偿 commit boundary 到期**）
4. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 80%，下一站 M17）
5. /root/workspace/projects/prism-0420/design/00-phase-gate.md（**闸门 2.6 Queue Scaffold Mini-Sprint M17 启动前必须 ✅** + 闸门 3.4 L1 review 触发例外段需修订纳入 "context budget pressure"）
6. /root/workspace/projects/prism-0420/design/99-comparison/phase-gate-bypass-log.md（#1 + #2 累计 = 2 次 触发线 → M17 子片 0 prep 必修订 phase-gate.md 闸门 3.4 L1 总则）
7. /root/workspace/projects/prism-0420/design/02-modules/M17-ai-import/00-design.md（M17 design）
8. /root/workspace/projects/prism-0420/design/audit/m16-pilot-template-validation.md（M16 sprint 实证 + L1 R14 立规重大事件 + §12B 子模板首战 + 元教训 17 条 + 元贡献 6 项 + bypass log #2）
9. memory feedback_problem_layered_analysis（含 M16 NEW 失效信号 — L1 缺规则导致跨模块漂移积累；M17 启动 reconcile 必走 5 步分层不绕 CY 拍工程量）
10. memory feedback_three_agent_pipeline + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_self_decide_no_ask + feedback_git_push_kb（标准红线集）

R-X1 第二实例对照点：M11 ColdStart 同步 orchestrator / M17 AI 导入异步 Queue orchestrator；接口共享 batch_create_in_transaction 4 参签名；行为契约分化（同步立 commit vs Queue retry + 死信 + compensation_session helper 共享）。

任务：M17 sprint TDD 实施（5+ 子片 / 严格按 M02-M16 范式 / 第十四数据点）。

启动顺序：

1. **子片 0 prep**（M17 启动期已 DONE 8 项；本子片 prep 收尾 3 项）：
   - M11 ColdStartOrchestratorService._mark_failed + cold_start_router 期望套路迁移到 compensation_session helper（cross-sprint punt #7 闭环 + M11 design §10 失败补偿 commit boundary 字面回写 + audit/m11 punt B1 标 DONE）
   - tests/conftest.py 加 SessionLocal monkeypatch fixture（join_transaction_mode='create_savepoint' 兼容；M11 现有 674 PASS 不破）
   - cross-sprint Punt 池触发点 A 4 项预查：M04-1 / M04-8 / M04-9 / M04-10 是否 M17 顺手清

2. **子片 1**：import_tasks + import_task_items model + alembic + ActionType+N + TargetType+N + 4 处 enum 字面同步（M15 NEW 立规 / model tuple + schema StrEnum + CHECK constraint + Alembic）+ model tests

3. **子片 2**：ImportTaskDAO + ImportTaskItemDAO + tenant filter + idempotency hash 查找 + zombie cron orphan + DAO unit tests

4. **子片 3**：ImportService + AIOrchestrationService + Pydantic schema + ErrorCode + queue/import_tasks.py（arq @task）+ ws/import_progress.py + R-X1 第二实例 + AI Provider 接通 + service unit tests

   👉 **R1 = 3 subagent 并行**（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）覆盖子片 1+2+3 合并审；spawn prompt 必含 ls/find 穷举要求（cross-sprint 元发现 #5 立规）

5. **子片 4**：Router 4 REST endpoints + WS endpoint + multipart file 上传（file.size 预检 + sanitize / M11 范式复用）+ idempotency 命中 200 + e2e 含 17+ 元教训 actionable 主动复制

   👉 **R2 = 1 合并 Opus subagent endpoint 单审**

6. **子片 5 关闸**：design §3 disambiguation 回写 + audit/m17-pilot-template-validation.md 元教训沉淀（实施期段）+ handoff §0 + roadmap + cross-sprint Punt 池 DONE 标记 + bypass log #2 配套承诺验收（spawn subagent 已恢复 ✅）

7. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP（§14.5 已锁）

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M15+M16 单 sprint 都堆到大 context；M17 必新窗口（启动期已合规 — 启动期 ad069c0 单独会话 / M17 实施新会话）
2. 当前周 usage（Asia/Tokyo Reset May 15 6pm；M17 启动期距 reset >5 天）—— /usage 同步基线（feedback_usage_budget.md 最近更新 2026-05-08 距今 1 天，仍在新鲜期）
3. ✅ M17 design §14.5 已补完 commit ad069c0（5+ 子片表 + R1+R2 安排 + L3 留空待实证 + 合规性自审）
4. ✅ 启动期 4 大必做项已收官 commit ad069c0（A 闸门 2.6 + C L1 修订 + D R-X1 helper 抽出；B R1+R2 spawn 在子片 1+2+3 / 4 时跑）

红线（M02-M16 实证后强化 + R14 + 启动期新增）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08-M16 全模块应用 / M14 owner-or-admin 替代）
- write_event 异常传播测试（M04+ 范式）：M17 service / router 必走 e2e 字面验
- cross-tenant 404（M02 范式）+ cross-project node 404（M13 NEW）
- IntegrityError 区分约束名（M05 P1-01 立规 / M17 启动期 design-principles 清单 6 升级到 service 层 INSERT 凡 UNIQUE 必 catch）
- M11 NEW R-X1 失败补偿 commit boundary：M17 用 compensation_session helper（不重复 M11 旧范式）
- M11 NEW 文件上传 file.size + sanitize（M17 zip 上传必复用范式）
- M13 NEW SSE 形态特殊不免除契约纪律 + metadata 字段集每条 e2e 字面验
- M14 NEW endpoint 形态特殊不免除契约纪律 + N/A 元教训显式声明范式
- M15 NEW 双层权限防御 service unit 不可达 e2e 是合理设计
- M15 NEW 横切表 owner 模块的 enum 字面同步责任（M17 若新增 ActionType/TargetType 必同步 4 处）
- M16 NEW R14：write_event 调用 action_type 必须 _ACTION_TYPES 枚举字面（ci-lint 守护 / 新增值同步 4 处流程）
- M16 NEW：CAS UPDATE 顶层方法内部 commit / 禁 Service 事务上下文（docstring 字面声明）
- M16 NEW：BackgroundTasks/Queue runner 自起 SessionLocal 与请求级 Depends(get_db) 隔离
- M17 启动期 NEW：reconcile pass 列 B 栏前必先穷举 L1 锁规 / B 栏 = 0 时禁列 B 栏
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M17 — AI 导入" + `design/02-modules/M17-ai-import/00-design.md` + `design/audit/m16-pilot-template-validation.md`。

---

### Prompt 0' — M16 sprint 启动（已完成 2026-05-09，仅供历史追溯）

```
继续 prism-0420 M16 sprint 实施代码（M16 AI 快照 / Queue 后台 §12B；M15 sprint 已收官 8 commit / 63 PASS / R13-1 90→101 / L12+L13 守护 / Phase 2.1 75%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M15-sprint-complete + 本 Prompt 0 M16 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/_handoff/cross-sprint-punt-pool.md（**🔴 跨 sprint Punt 池总表 / M15 sprint 收官后建立 / 94 项审计 / 30 STILL_PUNT / 真漏洞 Top 10 / M16 必处理项**）
4. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 75%，下一站 M16）
5. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
6. /root/workspace/projects/prism-0420/design/02-modules/M16-ai-snapshot/00-design.md（M16 design）
7. /root/workspace/projects/prism-0420/design/audit/m15-pilot-template-validation.md（M15 sprint 实证 + R1 1 P1 + R2 2 P1 + Punt 池 3 项 + 纯读 R10-2 owner 新教训 4 条 + 元教训 14 项应用情况）
8. memory feedback_problem_layered_analysis（含 M15 NEW 失效信号 — 双层防御 service unit 不可达 e2e 是合理设计 / 与 R1 P1-1 schema 注册无 raise 结论相反）
9. memory feedback_three_agent_pipeline + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb + feedback_self_decide_no_ask（标准红线集 / 含 M15 sprint 期立的 self_decide_no_ask "已批准 sprint 多子片连续做不在子片间停下来问"）

**🔴 M16 sprint 必处理 punt 项（来自 cross-sprint-punt-pool.md 真漏洞 Top 15 / 二审 M02-M04 audit 后扩 5 项）**：
- **M15-B1 + M15-B2 + 9 项历史联动**：write_event stub → 真 INSERT + M03-M08 service ~14 处裸 CRUD action_type 改过去式 + **M04-9 target_type 4 处 hard-code 同 batch const 化** + **M04-10 delete_by_node_id 并发 continue 跳 activity_log** + M05/M06/M07/M08 4 处 race window 复审（高耦合触发点 / 元发现 #1 / 工作量 4-6h）
- **M13-B16**：M02 Project.ai_model 字段 alembic add column（M14 已过未补 / 1 步迁移）
- **M13-B13**：SSE generator AsyncSession 占 300s 异步 SSE 连接策略（M16 是 Queue 后台同款 long-lived session 风险 / 必查）
- **M07-9 + M04-R2 A1**：IssueResponse + DimensionResponse 漏 join 字段（design §7 字面承诺 / 前端 N+1 / 顺手补 selectinload + schema 字段）
- **M04-4 + M04-17 IntegrityError → 500 跨模块 3 处**（M02 project create / M04 dimension create / M04 C7.1 同根因 / 触发点 B）：立通用规则（feedback 或 design §13 R13 段：service 层 INSERT 凡 UNIQUE constraint 必 catch IntegrityError 转 *DuplicateError）
- **M04-1**：dimension_records (updated_by, updated_at) 联合索引未建（M13/M14 高写入源表 / 与 M15-B1 同 sprint 评估提前建）
- **M04-8**：db.get(DimensionType) 3 处未走 DAO（service:349/428/474 / 风格统一）
- **M07-2**：update 不支持 detach (None→NULL) — 让 CY 拍是否 M16 顺手做（产品决策）
- **M14-B12**：write_event 异常传播 update/delete/unlink 三路径 e2e（与 M15-B1 同 sprint）
- **M10-5**：viewer /overview/stats 测试缺（启动顺手补）

**M16 启动闸门 2.5 reconcile A 栏首条预录**（cross-sprint 元发现 #5 触发点 A 立规）：
M04-1 联合索引 + M04-8 db.get→DAO + M04-9 target_type const + M04-10 delete cascade activity_log = 4 项指向 M16 sprint 同时处理

任务：M16 sprint TDD 实施。

M16 模块特定要素（必查）：
- Queue 后台异步范式（§12B 字面）：arq Queue + ai_snapshot_task / 与 M13 SSE 流式（§12A）/ M17 import Queue（§12C）/ M18 embedding（§12D）四种异步模式区分（不混同一 ✅）
- M11 NEW R-X1 失败补偿 commit boundary 元教训（R2 punt M17 sprint 抽独立 helper）—— M16 是否同款形态？若是必走独立 connection / 显式 SAVEPOINT
- M11 NEW 文件上传 file.size + sanitize（M16 若有 attachment 上传必复用范式）
- M13 NEW SSE generator 持 AsyncSession 300s 占连接池（10 并发吃光 default 10）—— M16 异步 Queue 形态是否触发同款问题？
- 与 M15 接口契约：write_event 仍是 stub（design §B7 字面 / M16 sprint 期 stub 不替换为真 INSERT 仍走 structlog / 真 INSERT 替换 + 回扫 M03-M08 是后续独立 sprint）
- ActionType / TargetType 若新增（如 ai_snapshot_*）必同步 4 处：model._ACTION_TYPES / schema StrEnum / CHECK constraint / 测试 enum set 比较

启动顺序（严格按 M02-M15 范式 / 第十三数据点稳定）：

1. **闸门 2.5 reconcile pass**（M16 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M15 R1-B 新增 make_activity_log；十一连规则延续）
   - grep M16 引用的所有 horizontal helper（含 write_event / api/queue/ scaffold / ActivityLog enum 字面 等）
   - 重点核 M11 R-X1 元教训：M16 后台异步是否同款失败补偿 boundary 形态？
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）

2. **闸门 3.4 L1 总则触发**：M16 design 必须含 §14.5 sprint review 拆分计划段（M02-M15 十三数据点稳定 → 业务模块 R1=3 subagent 并行 / 纯读模块 R1=1 合并 Opus / Queue 后台 M16 是业务模块走 3 subagent 并行；R2=1 合并 Opus / 子片 5 不单跑 / schema 子片合并 R1）。若缺先补。

3. **闸门 2.6 Queue Scaffold Mini-Sprint**（M16 是否触发？）：design/00-phase-gate.md 闸门 2.6 字面"M17 对话历程模块依赖 api/queue/base.py:TaskPayload"—— M16 ai_snapshot 用 Queue 后台同款依赖 → 必须 M16 启动前先建 api/queue/base.py + ADR-002 §1 形态对齐。若 M16 是首个 Queue 消费者 / mini-sprint 合并到 M16 子片 0 prep

4. **M16 写代码 5 子片**（参 M11 R-X1 + M13 SSE 范式参考）

5. **R1+R2 review 按 §14.5 计划跑**

6. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M15 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12+M13 应用 / M14 N/A / M15 N/A 但首发读 403）
- write_event 异常传播测试（M04+ 范式）：M16 是 write_event 调用方，必走 service 层覆盖 + e2e 字面验
- cross-tenant 404（M02 范式）；M16 ai_snapshot 必 tenant 过滤
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M11 NEW R-X1 失败补偿 commit boundary（必查 M16 是否同款 + 走独立 connection / SAVEPOINT）
- M11 NEW 文件上传 file.size + sanitize（M16 若有 attachment）
- M12 元自审：L1 范式既锁裁决型 P1 不让 CY 拍 / AI 自决 + sink design disambiguation
- M13 NEW SSE 形态特殊不免除契约纪律 / metadata 字段集每条 e2e 字面验
- M14 NEW endpoint 形态特殊不免除契约纪律 + N/A 元教训显式声明范式
- **M15 NEW**：双层权限防御 service unit 不可达 e2e 是合理设计而非 dead code（区分 schema 注册无 raise vs router 抢先+service 防御未来 / docstring 注释字面声明）
- **M15 NEW**：横切表 owner 模块的 enum 字面同步责任（M16 若新增 ActionType/TargetType 必同步 4 处）

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12+M13+M14+M15 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M16 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M16 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M16-ai-snapshot/00-design.md 确认；缺则子片 0 prep 补齐
4. M16 是首个 Queue 消费者 → api/queue/ scaffold 是否已建？闸门 2.6 mini-sprint 触发判定（合并到 M16 子片 0 prep 或独立）
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M16 — AI 快照" + `design/02-modules/M16-ai-snapshot/00-design.md` + `design/audit/m15-pilot-template-validation.md`。

---

### Prompt 0' — M15 sprint 启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M15 sprint 实施代码（M15 数据流转 / activity_log 横切表 own；M14 sprint 已收官 8 commit / 子片 5 关闸 aab74ce / 930 PASS / R13-1 90=90 / L12 守护 / Phase 2.1 70%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M14-sprint-complete + 本 Prompt 0 M15 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 70%，下一站 M15）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M15-activity-stream/00-design.md（M15 design）
6. /root/workspace/projects/prism-0420/design/audit/m14-pilot-template-validation.md（M14 sprint 实证 + R1 6 P1 + R2 4 项 + Punt 池 12 项 + 全局豁免业务模块首发新教训 3 条 + 元教训 9 项应用情况）
7. memory feedback_problem_layered_analysis（含 M13 NEW + M14 NEW 失效信号 — endpoint 形态特殊不免除契约纪律）
8. memory feedback_three_agent_pipeline + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M15 sprint TDD 实施。

M15 模块特定要素（必查）：
- **承接 M14 baseline-patch**：write_event project_id UUID→Optional 升级（M14 sprint 落地 / M15 实装 ActivityLog NULLABLE column + UI 时间线"全局事件"分组）
- **新增 ActionType +5**（M14 全局事件类型）：news_create / news_update / news_delete / news_link / news_unlink；ActivityLog target_type 含 industry_news / news_node_link
- M15 own：activity_log 横切表 + list_for_team F2.5 + ActionType +10 + ErrorCode +8（design 字面）
- 与 M14 的接口契约：write_event stub 当前打 structlog；M15 sprint 替换为真 INSERT + 兼容 None project_id

启动顺序（严格按 M02-M14 范式 / 第十二数据点稳定）：

1. **闸门 2.5 reconcile pass**（M15 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M14 R1-B 新增 make_news；十连规则延续）
   - grep M15 引用的所有 horizontal helper（含 write_event / activity_log_service / NodeChildrenServiceProtocol 4 参 等）
   - 重点核 M14 baseline-patch：activity_log_service.py write_event project_id Optional 升级 + scaffold 简化决策注释 4 字段（M15 sprint 必须把 stub 替换为真 INSERT 兼容 None）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）

2. **闸门 3.4 L1 总则触发**：M15 design 必须含 §14.5 sprint review 拆分计划段（M02-M14 十二数据点稳定 → R1=3 subagent / R2=1 合并 Opus / 子片 5 不单跑 = 默认范式）。若缺先补。

3. **M15 写代码 5 子片**（参 M14 sprint 范式）

4. **R1+R2 review 按 §14.5 计划跑**

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M14 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12+M13 应用 / M14 N/A 显式声明）
- write_event 异常传播测试（M04+ 范式）：M15 是 write_event 实装方，自身路径全覆盖 + 调用方契约不破
- cross-tenant 404（M02 范式）；M15 list_for_team 必须 tenant 过滤
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M12 元自审：L1 范式既锁裁决型 P1 不让 CY 拍 / AI 自决 + sink design disambiguation
- M13 元自审：design metadata 字段集每条 e2e 验
- **M14 NEW**：endpoint 形态特殊不免除契约纪律（list/反查/复用通用 schema 都需 disambiguation 注释）
- **M14 NEW**：N/A 元教训必须显式声明（design §14.5 + 测试 docstring 双重）

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12+M13+M14 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M15 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M15 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M15-activity-stream/00-design.md 确认；缺则子片 0 prep 补齐
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M15 — 数据流转" + `design/02-modules/M15-activity-stream/00-design.md` + `design/audit/m14-pilot-template-validation.md`。

### Prompt 0' — M14 sprint 启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M14 sprint 实施代码（M14 行业新闻；M13 sprint 已收官 8 commit / 子片 5 关闸 [hash] / 827 PASS / R13-1 86=86 / L12 守护 / Phase 2.1 65%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M13-sprint-complete + Prompt 0 M14 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 65%，下一站 M14）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M14-industry-news/00-design.md（M14 design）
6. /root/workspace/projects/prism-0420/design/audit/m13-pilot-template-validation.md（M13 sprint 实证 + R1 8 P1 + R2 4 项 + Punt 池 16 项 + LLM 首发新教训 4 条 + 元自审）
7. memory feedback_problem_layered_analysis（含 M13 NEW 失效信号"3 端点全覆盖"原则 SSE 形态不免除）
8. memory feedback_monkeypatch_not_verification（M13 强实证 — unit MockProvider + integration skipif）
9. memory feedback_three_agent_pipeline + feedback_problem_layered_analysis + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M14 sprint TDD 实施。

启动顺序（严格按 M02-M13 范式 / 第十一数据点稳定）：

1. **闸门 2.5 reconcile pass**（M14 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M13 R1-B 新增 make_project_with_member + set_project_ai；九连规则延续）
   - grep M14 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol 4 参 / write_event / DimensionService.create_dimension_record / IssueService.list_by_project / AI Provider 抽象等）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏

2. **闸门 3.4 L1 总则触发**：M14 design 必须含 §14.5 sprint review 拆分计划段（M02-M13 十一数据点稳定 → R1=3 subagent / R2=1 合并 Opus / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M14 写代码 5 子片**（参 M13 sprint 范式）：按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1（子片 3 完成）→ 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R2（子片 4 完成）→ 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M13 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12+M13 应用第 9-10 数据点）
- write_event 异常传播测试（M04+ 范式）
- cross-tenant 404（M02 范式）
- cross-project node 404（M06+M07+M08+M12+M13 范式 / **3 端点全覆盖含 SSE 形态特殊不免除** — M13 R2 抓出元教训）
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M12 元自审：L1 范式既锁裁决型 P1 不让 CY 拍
- M13 元自审：spec §7 metadata 字段集每条 e2e 验

M14 模块特定要素（参 design/02-modules/M14-industry-news/00-design.md）：
- 待启动时确认 design 范式（own / R-X1 / R-X2 / R-X3 / 纯读 / 流式 SSE 哪类）
- 是否复用 M13 AI Provider 抽象？若 M14 也 LLM 触发，复用 api/services/ai/ + ProviderRegistry
- prompt injection 局部防御（M13 P2-12 punt）：M14 若同样接受用户输入 + 喂 LLM 必须立 prompt-injection 防御

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12+M13 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M14 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M14 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M14-industry-news/00-design.md 确认；缺则子片 0 prep 补齐
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M14 — 行业新闻" + `design/02-modules/M14-industry-news/00-design.md` + `design/audit/m13-pilot-template-validation.md`。

### Prompt 0' — M13 sprint 启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M13 sprint 实施代码（M13 AI 需求分析；M12 sprint 已收官 7 commit / 子片 5 关闸 4bc096c / 742 PASS / R13-1 79=79 / L12 守护 / Phase 2.1 60%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M12-sprint-complete + Prompt 0 M13 启动 reconcile checklist）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 60%，下一站 M13）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M13-requirement-analysis/00-design.md（M13 design）
6. /root/workspace/projects/prism-0420/design/audit/m12-pilot-template-validation.md（M12 sprint 实证 + R1 4 P1 + R2 1 P1 裁决型 + Punt 池 13 项 + 元自审教训）
7. memory feedback_problem_layered_analysis（含 M12 NEW 失效信号"L1 范式既锁裁决型 P1 错抛 CY 拍" — M13 reviewer P1 抓 design vs 实装漂移时必走 step 1-2 grep L1 锁定项）
8. memory feedback_llm_hotpath_math（M13 接 LLM 进 hot path 必报频率×延迟×cost 4 数字 + 3 红线）
9. memory feedback_monkeypatch_not_verification（LLM monkeypatch ≠ 生产路径；DONE 必区分 unit pass vs integration pass）
10. memory feedback_three_agent_pipeline + feedback_problem_layered_analysis + feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M13 sprint TDD 实施。

启动顺序（严格按 M02-M12 范式）：

1. **闸门 2.5 reconcile pass**（M13 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（M12 R1-B 新增 make_snapshot；M04+M05+M06+M07+M08+M10+M11+M12 八连规则延续）
   - grep M13 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol 4 参 / write_event / DimensionService 跨模块只读接口 / M07 IssueService.list_by_project 跨模块 pass-through）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏
   - **M12 元自审新规主动应用**：reviewer P1 若抓 design 草案 vs 实装漂移，先 grep L1 锁定项（ADR / 跨 sprint 范式实证）；命中 → AI 自决 disambiguation 落 design + scaffold 注释，不 AskUserQuestion；grep miss 才让 CY 拍

2. **闸门 3.4 L1 总则触发**：M13 design 必须含 §14.5 sprint review 拆分计划段（M02-M12 十数据点稳定 → R1=3 subagent / R2=1 合并 Opus / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M13 写代码 5 子片**（参 M12 sprint 范式）：按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1（子片 3 完成）→ 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R2（子片 4 完成）→ 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP

红线（M02-M12 实证后强化 / 元教训防御 actionable 主动复制）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M08+M11+M12 应用）
- write_event 异常传播测试（M04+ 范式 / 三写端点全覆盖含 M12 R1-C P1-02 立修补）
- cross-tenant 404（M02 范式）
- cross-project node 422（M06+M07+M08+M12 范式）
- IntegrityError 区分约束名（M05 P1-01 立规延续）
- M12 R1-C P1-03 NEW: Core UPDATE 显式刷 updated_at（不依赖 ORM onupdate）
- M12 元自审 NEW: L1 范式既锁裁决型 P1 不让 CY 拍

M13 模块特定要素（参 _handoff/sprint-prompts-M05-M20.md M13 段）：
- **第一个真 LLM 集成模块**（feedback_llm_hotpath_math 触发：必报频率×延迟×cost 4 数字 + 3 红线 单跑<周期/2 + flock + cost ceiling）
- **流式 SSE**（design §12 A 流式 vs 同步 vs queue 三选一；design 应已决；若同步 → 接口 SLA 估算）
- **M04 punt 接通**：M13 是 M04 DimensionService.create_dimension_record + get_latest 的第一 caller → M04 service 层此 sprint 期实装两接口（含 extra_activity_metadata 合并机制）
- **M07 list_by_project 跨模块 pass-through**（已 pilot 登记）
- **LLM monkeypatch ≠ 生产路径**（feedback_monkeypatch_not_verification）：DONE 必区分 unit pass vs integration pass；端到端需真 LLM smoke
- 安全：LLM 不接管 dimension content schema 校验（jsonschema 仍 service 层做）

启动注意：
1. 不要在同一会话连续跑多个 sprint：M11+M12 单 sprint 都堆到大 context，下次开新窗口
2. 当前周 usage（Asia/Tokyo Reset 周三 6pm；本周 reset ~5/13）—— 启动 M13 前先 /usage 同步 + 更新 memory feedback_usage_budget.md 基线
3. M13 design 内是否含完整 §14.5？冷启动第一步 grep "## 14.5\\|sprint review 拆分" design/02-modules/M13-requirement-analysis/00-design.md 确认；缺则子片 0 prep 补齐
```

参考来源（详见）：`_handoff/sprint-prompts-M05-M20.md` § "## M13 — AI 需求分析" + `design/02-modules/M13-requirement-analysis/00-design.md` + `design/audit/m12-pilot-template-validation.md`。

### Prompt 0' — M12 sprint 启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M12 ..." 段（M11 sprint 已收官 commit 子片 5 关闸 / 674 PASS / Phase 2.1 55%）。

M12 sprint 启动 reconcile checkpoint（必查）：
- **元教训防御 actionable 5 + R-X1 NEW 2 条**（M11 sprint 启动 reconcile A7 主动列入清单的延续）：
  1. viewer 写**所有**写端点 403 全覆盖（M07 立 / M08+M11 应用）
  2. write_event 异常传播测试（M04+ 范式）
  3. cross-tenant 404（M02 范式）
  4. cross-project node 422（M06+M07+M08 范式）
  5. IntegrityError 区分约束名（M05 P1-01 立规延续）
  6. **NEW from M10 纯读模块**：纯读模块 docstring 每字段 ≥1 unit test 断言（业务模块不适用，但"绿测 ≠ 范式正确"通用）
  7. **NEW from M11 R-X1**：orchestrator 失败补偿独立 commit boundary（M17 sprint 实装；M12 若是 R-X1 第二实例则触发）
  8. **NEW from M11 R-X1**：文件上传 endpoint file.size 预检 + filename sanitize（M17 异步 zip 导入实装时复用 _sanitize_filename）
- **L1 review 节奏第九数据点稳定** → R1=3 subagent + R2=1 合并 Opus 默认范式作模板
- **闸门 2.5 B 0 项第六次稳定** → M12+ 启动 reconcile 自审一问"这真有候选吗"已稳定，禁制造假决策

### Prompt 0' — M11 sprint 已完成（仅供历史追溯）

M11 sprint 完成 commits 见 §0 状态快照。**M11 子片 0 prep 已完成（commit `8ef59b3` 2026-05-08）**：
- ✅ design §14.5 sprint review 拆分计划段补

**M11 子片 0 prep 已完成（commit `8ef59b3` 2026-05-08）**：
- ✅ design §14.5 sprint review 拆分计划段补
- ✅ **3 跨模块 batch_create_in_transaction 接通**（M04 punt R1-A A6 + M06/M07 scaffold "M11 期实装" 全到期）：
  - `DimensionService.batch_create_in_transaction(dimensions_data)` ✅
  - `CompetitorService.batch_create_in_transaction(competitors_data)` ✅
  - `IssueService.batch_create_in_transaction(issues_data)` ✅
  - `NodeService.batch_create_in_transaction` 已存在（M03 sprint） → **R-X1 4 接口齐全**
- ✅ 3 smoke tests / 616 PASS / R13-1 67=67

**M11 闸门 2.5 reconcile 三栏（已分析 / 第六次 B 栏 0 项实证）**：
- A 8 项（其中 4 项已落地子片 0：M04+M06+M07 batch_create + §14.5）
- B 0 项
- C 3 项（queue N/A / R-X1 不是 R-X2 / caller 拓扑责任 design §6 G5 已决）

**M11 剩余子片**（下个 session 接续）：
- **子片 1**: M11 own model `cold_start_tasks` + alembic（design §3）
- **子片 2**: ColdStartDAO（task CRUD + tenant 过滤）
- **子片 3**: ColdStartOrchestratorService（CSV parse + 4 service.batch_create 集成 + 共享 db.begin() / R-X1 严守）
- **子片 4**: Router CSV upload endpoint（multipart/form-data）+ check_project_access editor + 错误行报告
- **子片 5**: 关闸（audit/m11-pilot-template-validation.md + roadmap + handoff）

M11 模块特定要素提示：
- **第一个 R-X1 orchestrator**（不直 INSERT 跨模块表，全走 service.batch_*）
- M11 是同步 HTTP 路径（design §12 N/A queue / 无 SSE / 无 Worker）
- caller 拓扑排序契约（M11 csv 已是层序，design §6 G5 line 238）
- ⚠️ **asyncio.gather AsyncSession 同 session 不安全**（M08 立修 tests pass 是巧合 / SA 抛 "concurrent operations not permitted" / 新模块禁用 / 见 memory feedback_problem_layered_analysis 失效信号）

**M02-M10 元教训防御 actionable 清单**（M11 sprint 启动 reconcile 时主动复制不等 R2 抓）：
1. viewer 写**所有**写端点 403 全覆盖（M07 立 / M08 应用 / M10 N/A 因纯读）
2. write_event 异常传播测试（M04/M06/M07/M08 范式）
3. cross-tenant 404 / cross-project node 422 / IntegrityError 区分约束名
4. **NEW from M10**：纯读模块 docstring 每字段 ≥1 unit test 断言（M10 纯读专属，M11 业务模块不适用，但元教训"绿测 ≠ 范式正确"通用）
5. **NEW from M10**：R1.5 reconcile checkpoint — R2 dispatch 前 grep R1 立修关键词在代码中真实存在

### Prompt 0' — M10 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M10 — 全景图（overview）" 段；启动当天复制对应 prompt 段落（M08 commits eed7749 → 子片 5 关闸 / 586+ PASS / Phase 2.1 45%）。

**M09 superseded by M18 不实装**（详见 design/00-roadmap.md §6.2）。

M10 模块特定要素提示（详见 sprint-prompts M10 段）：
- 跨模块只读聚合（同 M09 范式）— 项目首页全景视图：节点树 + 维度填充率 + 最近活动
- 与 M15 activity_stream 集成（最近活动；M15 sprint 期可能仍是 B2.3 stub log）
- 全景图 hot path 性能 + ADR-003 规则 2 豁免严守
- G7 删 US-C1.1 → out of scope（M10 不实装"添加节点"功能）

**M08 sprint 元教训防御 actionable 清单**（M10 sprint 启动 reconcile 时主动复制不等 R2 抓）：
1. viewer 写**所有**写端点 403 全覆盖（M07 R2 P1-01 / M08 主动应用）
2. write_event 异常传播测试（M04/M06/M07/M08 R1-C 范式）
3. cross-tenant 404 (project_not_found，M02 范式)
4. cross-project node 422（M06+M07+M08 范式对齐）
5. IntegrityError 区分约束名（M05 P1-01 立规延续）

### Prompt 0' — M08 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M08 — 模块关系图（module-relation）" 段；启动当天复制对应 prompt 段落（M07 commits b81c0d8 → 子片 5 关闸 commit / 538+ PASS / Phase 2.1 40%）。

M08 模块特定要素提示：
- **不是 R-X2 child service**（关系图节点附属，可能走 DB CASCADE 兜过；design §10 R10-1 batch3 是否要求 per-record activity_log → sprint 启动闸门 2.5 复审）
- 双向关系 vs 单向 + OR 查询：design 应已决；闸门 2.5 不复议
- 图查询防 N+1：邻接表 vs 物化视图 vs 递归 CTE — design 应已选

**M07 sprint punt 池本期到期项核对**（详见 `design/audit/m07-pilot-template-validation.md` Punt 池总表 8 项）：
- B4 IssueCategoryInvalidError R13-1 parity 注释 → M08 sprint 启动前一并清
- B5 _make_issue 跨文件触发时迁 conftest → M08 sprint 启动前评估
- **元教训防御 actionable**：M08 sprint 启动 reconcile 时主动比对 M02-M07 R1/R2 punt 池中"跨模块测试契约"项（**viewer 写**所有**写端点 403** / write_event 异常传播测试 / cross-tenant 404 / 等），**sprint 实施时主动复制不等 R2 抓**

### Prompt 0' — M07 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M07 sprint 实施代码（M07 问题沉淀 / R-X2 第三真注入方 / orphan 语义；M06 sprint 已完成 commits c84f6f2 → 子片 5 关闸 / 473+ PASS / Phase 2.1 35%）。

参 _handoff/sprint-prompts-M05-M20.md § "## M07 — 问题沉淀（issue）" 段。

特定要素：
- R-X2 第三真注入方（orphan 语义 SET NULL，与 M04/M06 delete 不同）
- 状态机 4 状态 + SELECT FOR UPDATE 行锁串行化（design §5）
- M13 pilot list_by_project pass-through（无代码改动；service 层加 method）

红线：
- ON DELETE SET NULL + passive_deletes=True（与 M04/M06 cascade='all,delete-orphan' 显式区分）
- 7 处代码 anchor 标注 orphan 语义防误读
- viewer 写**所有**写端点 403 测试（M06 R2 P1-02 立的元教训）— **不要漏**
```

### Prompt 0'' — M06 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

参 `_handoff/sprint-prompts-M05-M20.md` § "## M07 — 问题沉淀（issue）" 段；启动当天复制对应 prompt 段落，替换 `M{N-1} commits ... / N PASS / Phase 2.1 X%` 为真实最新值（M06 commits c84f6f2 → {子片 5 关闸 commit} / 473+ PASS / Phase 2.1 35%）。

M07 模块特定要素提示：
- M07 是 R-X2 **第三真注入方**（语义不同：orphan_by_node_id SET node_id=NULL 而非 delete；issue 不被真删只变游离）
- 子片 3 实装 IssueService.orphan_by_node_id (4 参 含 actor_user_id) + lifespan register_child_service("issue", ...)
- batch3 基线补丁决策 4：命名 orphan 区分 M04/M06 的 delete（避免误以为真删）
- M13 pilot 登记 list_by_project 跨模块契约（无代码改动；pass-through DAO node_id 过滤）
- activity_log: action_type="orphan" + metadata 含 cascade_source

闸门 2.5 reconcile pass 前必查：
- M06 sprint punt 池本期到期项（详见 `design/audit/m06-pilot-template-validation.md` Punt 池总表 8 项）：B1 _make_competitor/_make_ref 跨文件需求 / B6 CompetitorRefResponse.display_name 接通 / B8 ref 404 e2e test
- M05 sprint punt 池继续（list_by_node id DESC tie-break / VersionNotFoundError reason 字段）
- M04 punt R1-C C6.1（delete_by_node_id N+1 batch 升级，M07 评估是否升级触发，FK orphan 与 delete 行为不同）

---

### Prompt 0' — M06 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M06 sprint 实施代码（M06 竞品参考；R-X2 第二真注入方；M05 sprint 已完成 commits 811d6bc → 6f489db / 412 PASS / Phase 2.1 30%）。

参 _handoff/sprint-prompts-M05-M20.md § "## M06 — 竞品参考（competitor）" 段。

冷启动按序读：
1. CLAUDE.md / _handoff/next-session.md / design/00-roadmap.md / design/00-phase-gate.md
2. design/02-modules/M06-competitor/00-design.md
3. design/audit/m05-pilot-template-validation.md（含闸门 2.5 B 0 项首次实证 + 5 步分层失效信号）
4. memory feedback_problem_layered_analysis（5 步分层 + 失效信号）
5. memory feedback_three_agent_pipeline + 标准红线集

特定要素：
- R-X2 第二真注入方（Protocol 4 参签名稳定复用）
- M18 baseline-patch get_for_embedding（拼接 name + description；url 不参与）
- 多表事务（competitors + competitor_refs 同事务，design Q4）

红线：
- 异常契约严守 delete_by_node_id 不 catch-all
- N+1 punt 接续（单 node refs 数量小不触发）
- IntegrityError race 转换 M05 同款干净起步（区分约束名）
```

### Prompt 0' — M05 sprint 实施代码启动（已完成 2026-05-08，仅供历史追溯）

```
继续 prism-0420 M05 sprint 实施代码（M05 版本时间线；M04 sprint 已完成 commits 4c3c413→c4037a7 / 347 PASS / Phase 2.1 25%）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M04-sprint-complete + Prompt 0 + §2 历史/后置债）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 25%，下一站 M05）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 + 闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M05-version-timeline/00-design.md
6. /root/workspace/projects/prism-0420/design/audit/m04-pilot-template-validation.md（M04 sprint 实证 + L1 第三数据点 + 5 R-X5 子选项 + punt 池 17 项）
7. /root/workspace/projects/prism-0420/design/audit/m03-pilot-template-validation.md（M03 sprint 实证）
8. /root/workspace/projects/prism-0420/design/audit/m01-pilot-template-validation.md（PT1-PT3 tracker — M05 sprint 闸门 2.5 时回填 M05 行）
9. memory feedback_problem_layered_analysis（5 步分层分析法 — M04 sprint 实质性产出"防本模块绕"价值）
10. memory feedback_three_agent_pipeline（v2: M02+M03+M04 三数据点稳定 / R1=3 subagent + R2=1 合并 Opus subagent）
11. memory feedback_sprint_test_helper_reuse_check（含 M04 R1-B 验证：4 migration import 形式统一）
12. memory feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

任务：M05 sprint TDD 实施。

启动顺序（严格按 M02+M03+M04 范式）：

1. **闸门 2.5 reconcile pass**（M05 sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（make_user / make_project / make_node 等；M04 sprint R1-B 实证规则延续）
   - grep M05 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol — 注意签名是 4 参 含 actor_user_id；M04 sprint R-X5 升级实证）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）输出
   - 自审一问："这真有候选吗 / 还是延续既有规则？" — 不允许把"机械应用既有规则"列为 B 栏给 CY 制造假决策（M04 sprint 元教训 2）

2. **闸门 3.4 L1 总则触发**：M05 design 必须含 §14.5 sprint review 拆分计划段（M02+M03+M04 三数据点稳定 → R1=3 subagent / R2=1 合并 Opus subagent / 子片 5 不单跑 / schema 子片禁单跑 = 默认范式）。若缺先补。

3. **M05 写代码 5 子片**（参 M04 sprint 范式）：略，按 design 拆。

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1 (子片 3 完成) → 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R1 finding P1 立修同 commit（M04 范式）；P2 punt 进 audit/m05-pilot-template-validation.md
   - R2 (子片 4 完成) → 1 合并 Opus subagent

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片 ≥80% checklist 条目天然 SKIP 可合并到下游

红线（M04 sprint 实证后强化）：
- 5 步分层分析法走（机制冲突/设计缺口）— M04 R-X5 实证此规则首次实质性"防本模块绕"
- NodeChildrenServiceProtocol 现是 4 参签名（含 actor_user_id）— M05 注入时 follow
- M04 sprint punt 池 17 项里有"M05 sprint 启动 reconcile 时消歧"项（A4 §5 vs §6 R-X3 事务边界字面冲突）— 必看
- commit 不主动 push（feedback_git_push_kb）
```

### Prompt 0' — M04 sprint 实施代码启动（已完成 2026-05-07，仅供历史追溯）

```
继续 prism-0420 M04 sprint 实施代码（M04 维度记录；M03 sprint 已完成 commits 800e632→656e05c / 285 PASS）。

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 post-M03-sprint-complete）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（Phase 2.1 20%，下一站 M04）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 3.4 L1 review 触发粒度规则）
5. /root/workspace/projects/prism-0420/design/02-modules/M04-dimension-record/00-design.md
6. /root/workspace/projects/prism-0420/design/audit/m03-pilot-template-validation.md（M03 sprint 实证 + L1 双数据点 + R-X5 子选项）
7. /root/workspace/projects/prism-0420/design/audit/m01-pilot-template-validation.md（PT1-PT3 tracker — M04 sprint 闸门 2.5 时回填 M04 行）
8. memory feedback_problem_layered_analysis（5 步分层分析法）
9. memory feedback_three_agent_pipeline + Prism-simplify-checklist.md（review 流水线原义）

任务：M04 sprint TDD 实施（参 M03 sprint 5 子片 + 2 review 范式，§14.5 sprint review 拆分计划必先存在）。

启动顺序：
1. **闸门 2.5 reconcile pass**（M04 sprint 启动当天必跑）：
   - **预查 conftest.py 已有 fixture**（M03 R1-B C1 新发现的禁忌：跨模块 helper 重复）
   - grep M04 引用的所有 horizontal helper（含 NodeChildrenServiceProtocol — M04 是 M03 R-X2 第一个注入方）
   - 按闸门 2.5 三栏分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）输出
2. **闸门 3.4 L1 总则触发**：M04 design 必须含 §14.5 sprint review 拆分计划段。若缺先补
3. **M04 写代码**：M03 R-X2 第一个真注入 — register_child_service("dimension", DimensionService.delete_by_node_id)
4. **R1+R2 review 按 §14.5 计划跑**（M03 实证: R1=3 subagent / R2=1 合并 subagent 已稳定足够）
5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发

红线（M03 sprint 实证后强化）：
- 跨模块 helper 复用：sprint 启动前 grep conftest.py / api/auth/ / api/services/ 既有 fixture
- 5 步分层分析法走（机制冲突/设计缺口）
- M04 是 M03 R-X2 第一注入方 — 验证 register_child_service 范式跑通
- M03 NodeChildrenServiceProtocol 异常契约 (R1-C P1-01): 不 catch-all 静默吞错
- commit 不主动 push（feedback_git_push_kb）
```

### Prompt 0' — M02 sprint 实施代码启动（已完成，仅供历史追溯）

```
继续 prism-0420 M02 sprint 实施代码（design 已含完整实施期处理段 + 体系级 v2 修订已落地）。

冷启动按序读：
1. 本 _handoff/next-session.md（看 §0 状态快照 + §2.1 后置债 + 体系级 v2 修订清单）
2. design/02-modules/M02-project/00-design.md（含 §3.X 实施期处理 / §3.Y 启动数据 / §3.Z early adopter AES helper）
3. design/02-modules/README.md v2（R-X5/X6 + R3-6 + frontmatter helpers 约束）
4. design/00-architecture/06-design-principles.md v2（6 原则 #6 横切 vs 业务）
5. design/00-architecture/04-layer-architecture.md v2（Q7 横切层定义）
6. design/audit/time-dimension-blindspot-2026-05-07.md（M02 sprint 启动元反思 + 4 元教训）

任务：
1. M02 sprint 闸门 2.5 reconcile pass：本次会话已确认无矛盾 ✅，可直接进 step 4 TDD 实施
2. M02 写代码顺序（参 M01 sprint 5 子片范式）：
   - 子片 1：models（Project / ProjectMember / ProjectDimensionConfig / DimensionType + 测试兜底 placeholder seed = 1 条 default 类型 alembic data migration 按 R3-6-B）
   - 子片 2：DAO + tenant_filter concrete impl 注入（M02 own only project_members 实现）
   - 子片 3：Service + AES helper 横切层 api/auth/crypto.py 实装（按 §7.1 B'）+ ai_api_key_enc 加解密
   - 子片 4：Router + 11 endpoints + check_project_access Depends（M02 own）
   - 子片 5：tests + ci-lint 守护
3. 三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）必须真跑（M01 期 bypass 已是首次，闸门 3 §3.3 不允许第二次 bypass）
4. simplify-checklist 在 ≥50 行或跨 ≥2 文件改动时跑
5. M02 sprint 启动期实证子选项（按 R-X5 子选项清单红线，sprint 写代码时拍 case-by-case + 登记到 design/audit/m02-pilot-template-validation.md）：
   - C 路径 team_id 写入策略（API 不暴露 / Schema 暴露但 service 拒绝 / DAO 完全允许）
   - A 路径 SearchConfig 类型 owner（M02 own raw types / 共享 horizontal）
   - B 路径 OpenAPI 契约层处理（不实装 router / 占位 router 501 stub）
   - R13-1 附加规则标记位置（code 注释 / design §13 加列 / ci-lint.sh 加附加规则）

红线：
- M02 sprint 写代码时严格按 design 实施期处理段走（A1=C / A2=A / A3.1=A / A3.2=B）
- 横切 helper（AES crypto）建在横切层 api/auth/crypto.py，禁止挂 M02 名下（原则 6 + R-X6）
- 三 Agent + simplify 这次必须真跑
- 实证子选项后回写 R-X5 子选项清单段（推动规则升级，元原则 1）

关联：design/audit/time-dimension-blindspot-2026-05-07.md / KB 02-技术/架构设计/设计前置方法论-补丁01-时间维度.md
```

### Prompt 0' — M01 sprint 闸门 3 检查 + M02 启动（已完成，仅供历史追溯）

```
继续 prism-0420，过闸门 3（M01 PR merge ready 检查）+ 启动 M02 sprint。

任务：
1. 闸门 3 检查（design/00-phase-gate.md 闸门 3 checklist）：
   - M01 5 子片 commits 已 push（c1e3acc → 2704d0f + design 回写 commit）
   - 测试矩阵 117+ PASS / 0 xfail / lint 全过 / pre-commit hooks 全过
   - design 反馈已回写 ADR-004 + M01 §4 §10
   - PT1-PT3 tracker 在 design/audit/m01-pilot-template-validation.md
2. 若闸门 3 通过，按 prompt A（重写自 M01 模板）启动 M02。

红线：
- M02 sprint 内必须给 PT1-PT3 第 1 次回写（M02 是否复用 M01 范式）
- M02 涉及 user 跨 project 关系，凭据路径声明段必须引 ADR-004（PT2 校准）
```

### Prompt A' — M01 sprint 已完成（保留作为 M02 起手模板参考）

```
继续 prism-0420，启动 M01 用户系统探针实施 sprint。

任务：按 design-first 方法论 + TDD 跑完 M01（auth pilot 模块）。

必读（按序）：
1. _handoff/next-session.md（本文件，看上下文）
2. design/00-roadmap.md（确认当前真实位置 = Phase 2.1 第 1 模块）
3. design/00-phase-gate.md 闸门 2.5（M01 sprint 启动当天必跑 reconcile）
4. design/02-modules/M01-user-account/00-design.md（含 references frontmatter）
5. ADR-001 + ADR-002 + ADR-004（M01 引用的 3 个 ADR）
6. design/audit/scaffold-design-reconcile.md（已知 7 seam，机械可做项 M01 sprint 第一 commit 内修掉）
7. design/audit/p5-state-machine-reachability.md F-1（M01 mermaid 与禁止转换表自相矛盾——sprint 内必拍 + 修）

启动顺序：
1. 闸门 2.5 reconcile pass：grep 7 seam，分类（机械可做 / 待 CY 拍 / 已自我消解）
2. M01 实施前决策包：把 design 中所有 ⚠️ 占位 + P5 F-1 整理成 A 模式清单（候选 + 优缺点 + 3-5 月后果）让 CY 拍
3. CY 拍完 → 落 design 文档 status=accepted
4. TDD 实施：tests/test_m01_*.py 先写 → router/service/dao 后填
5. 三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）每完成一类 endpoint 跑一次
6. simplify checklist 在 ≥50 行或跨 ≥2 文件改动时跑
7. PR 准备：含 M01 tests.md critical path 100% PASS evidence

红线：
- 闸门 3 要求 M01 PR merge 后才能开 M02——本 sprint 必须 merge-ready
- ADR-002 §1.1 SYSTEM_USER_UUID：M01 自身不是 cron 模块但其 activity_log 写入需统一对齐 ADR
- design 任何字段与本次 audit 产出（references frontmatter / namespace 登记）冲突时——design 是真相，audit 是约束 lint
- 决策点 A 模式呈现，禁打包；禁引导

关联：design/00-phase-gate.md 闸门 2.5 / 闸门 3 / feedback_three_agent_pipeline.md
```

---

### Prompt B — P5 audit 🔴 4 finding 收口（建议 M01 sprint 内夹带做）

```
跑 design/audit/p5-state-machine-reachability.md 的 4 条 🔴 finding 收口。

任务：
- F-1（M01 mermaid 与禁止转换表 pending→disabled 自相矛盾）：
  现在就修 design 文档——CY 决策哪边对（mermaid 还是禁止表为真），改另一边一致。
  A 模式呈现两种解读 + 各自语义后果让 CY 拍。
- F-4 / F-6 / F-7（M16 / M17 / M18 cron 模块端 0 处引用 SYSTEM_USER_UUID）：
  现在不写业务代码——在每个模块 §12 cron 段加 1 行明确指引：
  "本 cron 触发的 payload.user_id 必须用 api.queue.base.SYSTEM_USER_UUID 常量
   （ADR-002 §1.1）"。
  把规约从 ADR 落到模块 design 引用层，避免实施时漏。

红线：
- F-1 决策走 A 模式呈现；不预设答案
- F-4/F-6/F-7 不写业务代码，只补模块 design 的引用注释

关联：design/audit/p5-state-machine-reachability.md / ADR-002 §1.1 / feedback_decision_transparency.md
```

---

### Prompt C — 契约 2 + 契约 4 + M14 baseline-patch tail（M01 PR merge 后）

```
完成 design/audit/contracts-draft.md 的 4 条契约（已落契约 1 + 3，剩 2 + 4）+
M14 baseline-patch tail。

任务：
1. 契约 2（referenced_by 反向链）：5 ADR + engineering-spec §7/§8/§12
   + 02-modules/README.md R-X 25 条 → 各自尾部加 `referenced_by` 段。
   双向链格式：见 design/audit/contracts-draft.md §2 形态示例。
2. 契约 4：
   - scripts/structural-audit.sh 写 P1 + P2 + P3 自动扫
     （namespace collision / ADR×Module 矩阵 / Rule×Module 矩阵）
   - pre-commit hook 加 structural-audit
   - 02-modules/README.md 加"横向对账三轮"段（独立于纵向三轮）
3. M14 baseline-patch tail：M14 §10 5 个 action_type
   （create/update/delete/link/unlink）→ 改为 entity 前缀 + 过去式后回写
   M15 ActionType enum：news_created / news_updated / news_deleted /
   news_linked / news_unlinked。同步 namespace 登记表。

红线：
- 契约 2 / 4 形态严格对齐 contracts-draft §2 / §4，不发明新形态
- 与契约 1（references frontmatter）形成双向校验闭环

工时估计：契约 2 ≈ 6-7h / 契约 4 ≈ 3-4h / M14 ≈ 0.5h

关联：design/audit/contracts-draft.md / design/audit/lessons-learned.md
```

---

## 2. 历史 prompt（已完成，仅供追溯）

- ❌ ~~Prompt 0: M03 sprint 实施代码启动~~ → ✅ 2026-05-07 commits 800e632 → 656e05c（5 子片 + R1+R2 闭环；285 PASS / R13-1 41=41 / L12 守护通过）
  - L1+L2+L3 节奏第二次实证（M02 首 / M03 第二，双数据点稳定）
  - R-X5 子选项: A4 enqueue B 推迟 + get_for_embedding A 现在建 ✅ + 新决 A5 batch_create 拓扑 + A6 child_services 分发
  - design/audit/m03-pilot-template-validation.md status=accepted
  - 后置债 (M04+ sprint 顺手清):
    - R-X2 跨模块 stub: M04 sprint 是第一个真注入方 (DimensionService.delete_by_node_id)
    - R1-C R2-3 punt: NodeChildrenServiceProtocol 升级 batch 形态（M04 sprint 期评估）
    - R2-9 punt: NodeService.update_node service 层直调 type 参数测试
    - P-A-09 punt: refresh attribute_names 加 path（防御性）
    - P2-02 punt: batch_create max_sort_order O(N) TODO 注释
    - P2-03 punt: update_paths_in_subtree REPLACE 安全性 docstring
    - C2 punt (R1-B): migrations `_ck_clause` 重复 → migrations/helpers.py（M04 migration 出现前提取）

- ❌ ~~Prompt: Phase 2.0 决策类（quality-spec + engineering-spec §13）~~ → ✅ 2026-05-05 commit b91c8d5
- ❌ ~~Prompt: Phase 2.0 代码地基（5 helper + Makefile + queue scaffold）~~ → ✅ 已落地，B1-B10 全 ✅
- ❌ ~~Prompt B: P5 audit 🔴 4 finding 收口~~ → ✅ 2026-05-07 commits 2e93de9 + b24f049（含 F-9 R4-3a 模板修订一并落地）
- ❌ ~~Prompt A: M01 探针实施 sprint~~ → ✅ 2026-05-07 commits c1e3acc → 2704d0f（5 子片）+ design 回写 commit
  - 117+ tests PASS / 0 xfail / 22=22 R13-1 / L12 守护通过
  - design / ADR 回写 6 处（同秒边界 / P2 信任链 / refresh 形态 / active→pending / 同值豁免 / 多事件顺序）
  - 17 ErrorCode 新增 + 7 表 schema 落地 + ADR-004 P1+P2+P3 全打通

## 2.1 M01 sprint 后置债（不阻断 M02 启动，M02 sprint 内或后续顺手清掉）

| # | 项 | 优先级 | 触发场景 |
|---|----|------|---------|
| D1 | M03/M04/... 模块开工时验证 PT1-PT3（design/audit/m01-pilot-template-validation.md）| 🟢 | 每模块 sprint 闸门 2.5 reconcile 时 |
| D2 | tests.md A22 注释"每次记录 1 行"已被 design §10 校正为本期不写——必要时补 strikethrough | 🟢 | M01 PR review 期或下次扫 tests.md 时 |
| D3 | bcrypt 5.x deprecation warning（passlib `__about__` 缺失）| 🟢 | 升级 passlib 或换 bcrypt 直调（已是直调，仅 warning 噪音）|
| D4 | feedback_three_agent_pipeline 在本 sprint 用 main agent self-audit 替代——M02 起恢复 | 🟡 | M02 sprint 启动时 |

## 3. 维护规则

- 每次 session 结束有遗留任务 → 来这里更新 / 加新 prompt
- prompt 跑完 → 移到 §2 历史，标 commit hash + 日期
- `last_updated` 字段反映最近一次写入

## 4. 关联

- 真实进度：`design/00-roadmap.md`（权威）
- 闸门规则：`design/00-phase-gate.md`
- 协作规约：`CLAUDE.md`
- 本周方法论沉淀：`design/audit/lessons-learned.md`
