---
title: Phase 2.2 R 范式试运行 + findings 沉淀
status: in_progress
owner: CY
created: 2026-05-09（子片 2 关闸）
purpose: |
  Phase 2.2 子片 1+2 合并 R1+R2 第 1 数据点 / SR-P22-2 立规候选实证基础。
  累计 5 数据点（子片 1+2 合并 → 3a → 3b → 3c → 4）后 sink 到 feedback_subagent_sprint §4。
parent: design/01-engineering/06-frontend-spec.md（auth + codegen sanction）
related:
  - feedback_subagent_sprint.md（R 范式立规来源）
  - feedback_decision_layering.md（5 步流程）
  - _handoff/cross-sprint-punt-pool.md（子片 3 punt 项）
---

# Phase 2.2 R 范式试运行 + findings 沉淀

## §0 sprint 方法论

- **R 范式**：R1=1 reuse subagent (Sonnet) + R2=1 spec subagent (Opus) — feedback_subagent_sprint §4 简化基线
- **数据点节奏**：子片 1+2 合并跑（首次真用 endpoint 验契约更高 ROI）+ 3a + 3b + 3c + 4 = 5 个数据点
- **finding 处置**：P1 立修同 commit / P2 punt 进本文件 §2-3 / SR-P22-2 实证后扩 §4 立规

## §1 子片汇总

| 子片 | commit | 范围 | cost 估 | R1 P1/P2 | R2 P1/P2 |
|------|--------|------|---------|----------|----------|
| 1 | `12cc62c` | codegen + http-client + Bearer JWT | $2-3 | — (deferred) | — (deferred) |
| 2 | `3b9bbc1` | auth flow + CORS + cookie 通道 + 4 e2e | $3-4 | 0 立修 / 4 punt | 0 / 5 punt |
| 3a-i | `e521656`+`ee3a2ad` | spec 06 §3 SSR auth 通道 + server-auth/server-http-client + 7 unit tests | $1-2 | — (sink only) | — (sink only) |
| 3a-ii | `1a5e3d6` | actions/{projects,project-settings,versions} + lib/server-auth getServerUser + /projects 列表 + /projects/new 真接 backend | ~$5 | 5 立修候选 / 复审 3 立修 + 2 punt | 4 P1 立修 / 8 P2 punt |
| 3b | `490ad23` | actions/{nodes,relations,panorama} 完整改造 + actions/{import,import-ai} 全 punt + actions/analyze getAffectedNodes 实装 / 6 stub punt + errors.ts isRedirectError 豁免 | ~$5 | 2 P1 候选 / 复审 1 立修 + 1 降 P2 punt | 1 P1 立修 / 2 P2 punt |
| 3c | `bccb225` | actions/{competitors,competitor-references,issues,search,admin,activity-log} 完整接 + actions/{export,project-stats-proxy} 端点重写 + actions/{templates,feed} 全 punt + validators/issue.ts 加 title + **errors.ts.actionError 立修 UnauthenticatedError → redirect 一改通修 mutation 路径 401 静默吞错** | ~$6 | 4 P1 候选 / 复审 1 立修 + 3 降 P2 punt | 2 P1 立修（mutation 401 root-cause + admin NOT_IMPLEMENTED 类型） / 3 P2 punt |
| 4 | `0626add` | actions/teams.ts 全 rewrite（10 actions / 含 moveProjectTeam）+ validators/team.ts 全 rewrite + 3 路由全新写（/teams 列表 + /teams/new + /teams/[teamId] 合并 5 cards info/edit/members/transfer/danger）+ 02-frontend-design.md 轻量草案 + **errors.ts isNextRedirectError export + 3 处 client `.catch` rethrow root-cause 立修（teams/page + teams/[teamId] + projects/page）** + scope 自决收 6→3 路由（SR-P22-3 第 5 实证）+ M20 后端 4 项 gap 进 cross-sprint pool P22-4-backend-gap | ~$3-4 | 0 P1 / 3 P2 punt | 2 P1 立修（client `.catch` 吞 NEXT_REDIRECT root-cause / projects/page 同根因连带修） + 1 降 P2 + 2 P2 punt |

**R1+R2 第 2 数据点结论**：
- R1 reuse 5 P1 候选 / 复审：3 立修（projectsData mock dead / createVersion releaseMode workspace.tsx 在 ignore 范围 punt / handleCreateVersion 错误吞 workspace.tsx 在 ignore 范围 punt / eslint glob `[projectId]` 字面 char class 已 workaround / `getProjects` 401 处理与 R2 同根因合并立修）
- R2 spec 4 P1 / 全立修（**R2 真漏抓贡献最大**：P1-1 `api_key` → `ai_api_key` schema 字段名错 / P1-3+P1-4 401 静默吞错 spec §3 字面违反）
- 立修 3 项：(1) ai_api_key 字段名 / (2) UnauthenticatedError → `redirect("/login")` 统一 read action 错误处理 / (3) projectsData mock dead export 删
- punt 8 项进 §3
- **元教训**：R2 spec 在前端继承形态上**真漏抓硬伤**（schema 字段名 + spec 字面违反），ROI 显著高于 R1 reuse；SR-P22-2 立规精神得到第 2 数据点支撑

## §2 子片 2 spec findings（R2 输出 / 全 P2）

P2 进 punt pool / 子片 3+ 或 Phase 2.3 处理：

1. **CORS prod guard 缺失** — `api/core/config.py:37` `cors_origins` default 含 localhost；`_validate_startup_config()`（`main.py:43`）建议补：prod 环境若 `cors_origins` 仍含 localhost 则 raise / log warning。**punt 时机**：Phase 2.3 启动包必做项。
2. **dev 环境 cookie secure=False guard** — `api/routers/auth.py:52` `secure=settings.app_env != "local"`；建议在 `_validate_startup_config()` 显式断言 `prod → secure=True` + startup log。**punt 时机**：与 #1 合并 Phase 2.3。
3. **spec 06 §2 路径前缀 symbolic 不一致** — spec 写 `/api/auth/...` 实装 `/auth/...`（无网关）；建议在 spec 06 §2 文末加备注「symbolic 写法 / 实装 router prefix `/auth` / 待 Phase 2.3 引入网关再改」。**punt 时机**：随 Phase 2.3 网关引入一并处理。
4. **OpenAPI codegen drift CI guard** — spec 06 §1 已 punt 至 Phase 2.3；本子片改 `RefreshRequest.refresh_token` (required→optional) 已手动 export+codegen 同步；建议进 cross-sprint pool 显式登记防遗忘。**punt 时机**：Phase 2.3 启动包。
5. **`logout` body 仍 require RefreshRequest** — cookie 模式下前端发空 body / schema 已 optional / 字面合规；语义上 logout 在 cookie 模式可改 body=None；spec 06 §2 备注「logout body 仅做 backward-compat 兜底」。**punt 时机**：与 #3 同 spec 备注一并修。

## §3 子片 2 reuse findings（R1 输出 / P1 复审降 P2）

### R1 标 P1 降 P2 复审

R1 标 2 项 P1（均为拷贝层 broken imports）：

1. **`@/actions/auth` 6 处 import 残留** — `src/lib/use-page-context.ts:5` + `src/app/teams/{page.tsx,[teamId]/page.tsx}` + `src/app/projects/{page.tsx,[projectId]/{overview,settings}/page.tsx}`
2. **`@/lib/auth` 20 处 import** — 全部 `src/actions/*.ts` import `requireAuth from "@/lib/auth"` / 该文件从未存在于 prism-0420（next-auth 删后留下的拷贝层引用）

**复审降级理由**（feedback_completion_audit + handoff next-session.md 字面）：
- next-session.md 字面记「拷贝层编译会炸 / 子片 2-3 渐进修复 / 不跑 pnpm dev」— **build 自子片 0 prep 起就一直坏，已知 punt 状态**
- 这 26 处 broken import 在子片 0 prep 拷过来时即已存在；**子片 2 删除 actions/auth.ts + services/auth.ts 没让事情更糟**（消费方文件本来就因 `@/lib/auth` 缺失而炸）
- 全部消费方在 eslint globalIgnores 内（`src/actions/**` + `src/lib/use-page-context.ts` + `src/app/{teams,projects}/**`）/ 不破 lint
- vitest 不触及这些 import / 不破 13 项测试
- **降 P2 / 进子片 3a-3c 改造范围**：3a 修 `src/app/projects/**` + `src/lib/use-page-context.ts` + `src/actions/projects.ts` 等；3c 长尾扫剩余 actions

### R1 P2 已修

- **`auth-context.tsx:51-54` 冗余 catch 路径** — 已修：删 `if (err instanceof ...)` 分支、删 `ApiError` import、统一 `catch { ... return null; }`（同 commit 内）

### R1 P2 punt

- **double `/auth/refresh` on mount（401 路径）** — context 调 apiPost("/auth/refresh") + http-client 401 retry 触发 2 次实际 refresh；属网络浪费但功能正确 / 子片 3+ 优化（apiFetch 加 `skipRetry` 选项 / context 改裸 fetch 绕 retry）。**punt 时机**：子片 3a 评估或 Phase 2.3 perf。
- **`registerSchema` / `RegisterInput` dead code** — `src/lib/validators/auth.ts:8-15`；CY 选 (a) 跳过 register 改造 / 保留 schema 备 M01 未来扩展。**punt 时机**：M01 register 落地或下一 sprint cleanup。
- **`getAccessToken` re-export from auth-context** — `auth-context.tsx:104` re-export 当前无消费方 / 子片 3+ 评估清理。**punt 时机**：子片 5 关闸 cleanup。

## §3b 子片 3b findings（R1+R2 第 3 数据点）

### R2 spec P1 立修（1 项 / 已修）

1. **`getRelationsByNode` 缺 `withAuthRedirect`** — `actions/relations.ts:85-97` 原版裸 try/catch 把 UnauthenticatedError 吞入 actionError / spec 06 §3「access token 拿不到 → redirect /login」字面违反。**已修**：read action 包 withAuthRedirect。

### R1 reuse P1 复审

- **R1 P1-1 workspace.tsx dimension CRUD 签名不匹配**（updateDimensionRecord/deleteDimensionRecord 老调用缺 projectId/nodeId/dimensionTypeId）— workspace.tsx 在 eslint ignore + tsc baseline 已含此类错 → **降 P2 punt 子片 5 cleanup**（SR-P22-3 实证：消费方页面在 3b scope 外）
- **R1 P1-2 `actionError` 全捕吞 NEXT_REDIRECT**（影响所有 mutation）— 是真硬伤 / 跨所有 action 通用 / 已修：`errors.ts` 加 isNextRedirectError 豁免（按 digest 字面识别）

### R1 reuse P2 punt（3 项进 cross-sprint 池）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-3b-1 | `withAuthRedirect` helper 在 5 个 action 文件重复 / 抽到 lib/server-helpers.ts | projects.ts + nodes.ts + relations.ts + panorama.ts + analyze.ts | 子片 3c/5 cleanup |
| P22-3b-2 | `findInTree` 工具函数在 nodes.ts + relations.ts + panorama.ts 重复 / 抽到 lib/tree-utils.ts | nodes.ts:282 + relations.ts inline + panorama.ts inline | 子片 3c/5 cleanup |
| P22-3b-3 | `getModuleRelations` stub 死代码留 nodes.ts 内 / consumer 真用 relations.ts.getRelationGraph | nodes.ts:404 | 子片 5 cleanup（删 stub）|
| P22-3b-4 | workspace.tsx dimension CRUD 调用签名不匹配 | workspace.tsx:688/712 | 子片 5 cleanup（消费方页面解锁批次）|

### R2 spec P2 punt（2 项进 pool）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-3b-5 | `getRelationGraph` 串行 fetch 两次（overview + relations）/ 无单请求 memo | relations.ts:123 | Phase 2.3 perf |
| P22-3b-6 | `getPanoramaData` parentId 无效时静默返空 / UX 有歧义 | panorama.ts:49 | UX 验证轮 |

### 子片 3b prompt-vs-reality 漂移（SR-P22-3 第 3 实证）

cold-start prompt「子片 3b」段写「6 actions 完整改造 + 7 页面解锁运行 + R1+R2」/ 实际可达：
- ✅ 4 actions 完整改造（nodes / relations / panorama / analyze:getAffectedNodes）
- ⏸ 2 actions 显式 punt（import.ts ZIP 流程 + import-ai.ts AI 导入 + analyze.ts 6 SSE/test-points/comparison stubs）— 路径完全不在 prism-0420 OpenAPI / M17/M13/M14 真端点接入留子片 3c
- ⏸ 7 页面 unlock — actions 改造后 page consumer 签名漂移（workspace.tsx + features + modules + relation-graph + comparison + import + analysis）/ 全在 eslint ignore / 子片 5 cleanup 集中处理

**根因**：cold-start prompt 把「actions 改 + 7 页面跑通 + R1+R2」并联成单子片 / 实际「actions 多文件 + 大 SSE/WS 流程 + 页面消费方深耦合」3 块串联工作 / 单 session $4-6 budget 承受不了 / SR-P22-3 第 3 实证「prompt 块本身分层错」（M01 register + 3a-ii broken imports + 3b SSE/WS 三实证 → 子片 5 关闸前 sink 立规）。

**3b scope 修订归档**：
- 4 actions 完整接 backend / 1 action 部分接（getAffectedNodes）+ 6 stub
- 2 actions 完全 punt（import + import-ai）/ 显式 actionError(NOT_IMPLEMENTED) 不静默吞错
- errors.ts 立修 NEXT_REDIRECT 透出（影响全 actions）
- 7 页面深耦合解锁全 punt 子片 5（workspace.tsx 在 ignore / 不破 lint / 消费方签名漂移留 cleanup 批次集中处理）

## §3a 子片 3a-ii findings（R1+R2 第 2 数据点）

### R2 spec P1 立修（4 项 / 已修）

1. **`ai_api_key` schema 字段名错** — `actions/projects.ts:179` 原写 `api_key` / OpenAPI 真值 `ai_api_key`（types/api.ts:1632）/ 后端会忽略未知键 → 密钥永远写不进 / 静默失败。**已修**：用 `components["schemas"]["AiProviderUpdate"]` 类型守卫拼 body。
2. **401 静默吞错** — `getProjects` 等 read action 抛 UnauthenticatedError 跨边界 / page.tsx `.catch(() => [])` 把 401 退化为空列表 / 不跳登录 / spec 06 §3「access token 拿不到 → redirect /login」字面违反。**已修**：actions/projects.ts 加 `withAuthRedirect` helper / read action 包裹 / UnauthenticatedError → `redirect("/login")` from "next/navigation"（Server 端直接生效 / NEXT_REDIRECT 通过 Server Action 边界）。
3. （P1-3 + P1-4 同根因合并立修）

### R1 reuse P1 复审

- **R1 P1-1 createVersion 漏 release_mode 配置** — workspace.tsx 在 ignore + 当前未真用 continuous mode → 降 P2 punt 进子片 3b（workspace 改造时）
- **R1 P1-2 handleCreateVersion 错误吞** — workspace.tsx 在 ignore + 既有缺陷 → 降 P2 punt 进子片 3b
- **R1 P1-3 getProjects 401 静默** — 与 R2 P1-3+P1-4 同根因 / 已合并立修
- **R1 P1-4 eslint glob `[projectId]` 字面 char class** — 已 workaround（`**/projects/**/[projectId]/page.tsx` 仍是 char class 但 [projectId]/page.tsx 已无 lint 问题 / workaround 路径不准但 effective）→ P2 punt（cosmetic / 子片 5 cleanup 时真转义）
- **R1 P1-5 projectsData mock dead** — 已立修（删常量 / 保 projectsStrings i18n）

### R2 spec P2 punt（8 项进 cross-sprint 池）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-3a-1 | server-http-client 间接 import services/http-client 把 auth-token-store module state 拉进 server bundle / 抽 `lib/api-errors.ts` 解耦 | `lib/server-http-client.ts:14` | 子片 5 关闸 cleanup |
| P22-3a-2 | ProjectUpdate validators/project.ts 未用（绕过 zod 校验） | `actions/projects.ts:74` | 子片 5 cleanup |
| P22-3a-3 | getMyProjectRole 串行 2-3 fetch / 无单请求 memo | `actions/projects.ts:147` | Phase 2.3 perf |
| P22-3a-4 | server-auth.ts cookie 值未做 url-encode | `lib/server-auth.ts:32` | base64url 安全但加注释 / 子片 5 |
| P22-3a-5 | template_type 非 enum / frontend fallback | `app/projects/page.tsx:71` | 后端补 enum / 非本 sprint |
| P22-3a-6 | createVersion release_mode 硬编码（R1 P1-1 降级）| `actions/versions.ts:57` | 子片 3b workspace 改造 |
| P22-3a-7 | handleCreateVersion ActionResult 不查 success（R1 P1-2 降级）| `workspace.tsx:729` | 子片 3b |
| P22-3a-8 | eslint glob `[projectId]` workaround / 真转义 | `eslint.config.mjs:113` | 子片 5 cleanup |

## §3b prompt-vs-reality 漂移记录（SR-P22-3 立规候选实证）

cold-start prompt「子片 3a-ii」段写 6 页面（projects 列表 + new + [id] + overview + settings + features/[fid]），实际可达：

- ✅ /projects 列表 — 真接 backend / login 跳登录路径 / R2 P1-3 修后 spec §3 字面合规
- ✅ /projects/new — 调 createProject / 走 server-http-client / 合规
- ⏸ /projects/[projectId] + features/[fid] — 依赖 actions/nodes（drizzle 引用 / subslice 3b 改造）/ 仍 ignore
- ⏸ /projects/[projectId]/overview — 920 行 / 深耦合 actions/{panorama,activity-log,feed,project-stats-proxy,project-role-context} / 子片 3b/3c scope
- ⏸ /projects/[projectId]/settings — 1011 行 / 深耦合 actions/{competitors,feed,export,teams} / 子片 3c scope

**根因**：cold-start prompt 起草时未与 subslice 边界（teams 锁 4 / nodes/issues 锁 3b/3c）对齐 / "全修 26 broken imports" 字面与 subslice 边界冲突 / SR-P22-3 立规精神得到第二实证（M01 register 是第一实证）。

**3a-ii scope 修订归档**：
- 2 页面真接 backend（list + new）
- 4 页面降级到子片 3b/3c（仍在 eslint ignore / 不破 build）
- actions/{projects, project-settings, versions} 三件套改 server-http-client / 顺手删 4 处 requireAuth import（projects + project-settings + versions + 它们调用方）
- broken imports 26 处中本子片关闭 4 处（projects + project-settings + versions + 顺手 workspace.tsx createVersion 签名同步）/ 余 22 处随 3b/3c 关闭

## §3c 子片 3c findings（R1+R2 第 4 数据点）

### R2 spec P1 立修（2 项 / 已修）

1. **mutation 路径全栈 401 静默吞错（root-cause）** — `lib/errors.ts.actionError` 仅豁免 NEXT_REDIRECT 未豁免 UnauthenticatedError / defineAction 顶层 catch 把 UnauthenticatedError 吞为 actionError fallback / 影响 3a/3b/3c 全栈所有 mutation（updateCompetitor / deleteCompetitor / updateReference / deleteReference / deleteIssue / transitionIssue / triggerBackfill / triggerModelUpgrade / globalSearch / exportNodes / exportSingleNode + defineAction 包的 createCompetitor / createReference / createIssue / updateIssue 等）/ 用户停留原页继续点表单 / 与 read 路径 withAuthRedirect 行为不一致 / 是 3a-ii 第 2 数据点 read 路径 401 静默吞错的同型 mutation 路径再发 / 3a/3b R2 漏抓 / **R2 真漏抓贡献第 4 数据点最大**。**已修**：errors.ts 加 `isUnauthenticatedError` 按 name 字面识别（防 UnauthenticatedError 类 import 把 client-only auth-token-store 漏入 server bundle / P22-3a-1 已 pool）+ actionError 内 `if (isUnauthenticatedError(e)) redirect("/login")` 一改通修 N+ caller。
2. **admin.ts NOT_IMPLEMENTED 声明类型不一致** — admin.ts:70 是 string 后续用 `new Error(NOT_IMPLEMENTED)` 包；templates.ts:54 / feed.ts:13 直接 `const NOT_IMPLEMENTED = new Error(...)`。**已修**：admin.ts 改为 Error 类型 / 三个 stub 文件统一声明模式。

### R1 reuse P1 复审（4 P1 候选）

- **R1 P1-1 withAuthRedirect helper 5→10 文件重复** — 是 P22-3b-1（cross-sprint pool 已立）的 trend update / 3c 新增 5 处（competitors+competitor-references+issues+admin+activity-log）/ 现状 10 处全栈重复 / **不重新立 P1 / 趋势继续累计 / 抽 lib/server-action-helpers.ts 时机已成熟（子片 5 cleanup 抽）**
- **R1 P1-2 search.ts / project-stats-proxy.ts 内联 redirect 不复用 withAuthRedirect** — 是 P1-1 子集 / **降 P2 punt 进子片 5 cleanup**（与 P22-3b-1 抽 helper 同批处理 / search.ts catch 内 if instanceof + project-stats-proxy.ts fetchOverview 包裹器都收敛进 helper）
- **R1 P1-3 admin.ts NOT_IMPLEMENTED string vs Error 不一致** — 立修同 R2 P1-2 合并
- **R1 P1-4 project-stats-proxy.ts StatsResult vs ActionResult 双 result 类型** — **降 P2 punt 进子片 5 cleanup**（兼容层意图保留 consumer 残留 import / 子片 5 切换到 panorama.getProjectStats 时同时迁 result 格式）

### R1 reuse P2 punt（5 项进 cross-sprint 池）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-3c-1 | search.ts / project-stats-proxy.ts 内联 redirect / 不复用 withAuthRedirect / 是 P22-3b-1 子集 | search.ts:41 + project-stats-proxy.ts:24 | 子片 5 cleanup（与 P22-3b-1 同批抽 lib/server-action-helpers.ts）|
| P22-3c-2 | StatsResult&lt;T&gt; vs ActionResult&lt;T&gt; 双 result 类型并行 | project-stats-proxy.ts:13 | 子片 5 cleanup（consumer 迁到 panorama 时同时迁 result 格式）|
| P22-3c-3 | issues.ts 命名前缀混用 list/get（listIssues vs getIssue / getIssuesByNode / getIssuesByCategory）| issues.ts:138 | 子片 5 命名规约统一 |
| P22-3c-4 | competitor-references 命名过于通用（createReference vs createCompetitor / createNode 资源名前缀缺）| competitor-references.ts:34 | 子片 5 重命名 createCompetitorRef 等 |
| P22-3c-5 | findInTree 三处重复 / nodes.ts module-level + panorama.ts inline + relations.ts inline | nodes.ts:283 + panorama.ts inline + relations.ts inline | 子片 5 抽 lib/tree-utils.ts（P22-3b-2 同源 / trend update）|

### R2 spec P2 punt（3 项进 pool）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-3c-6 | export.ts ExportPayload = unknown / OpenAPI 真不约束 200 响应 schema / consumer UI 解析 旧 `{filename, content}` 字段不再保证 | export.ts:30+53 | 子片 5 cleanup CY 拍补 ExportResponse schema or 显式删 consumer |
| P22-3c-7 | activity-log.logActivity / logActivityAuto no-op 兼容层 / 残留 caller 未审计 | activity-log.ts:38 | 子片 5 grep caller 全删 + 删函数 |
| P22-3c-8 | project-stats-proxy 注释提兼容层但缺 file-level eslint-disable cleanup anchor | project-stats-proxy.ts:17 | 子片 5 cleanup（删本文件时一并）|

### 子片 3c prompt-vs-reality 漂移（SR-P22-3 第 4 实证）

cold-start prompt「子片 3c」段写「10 actions + 7 页面 + R1+R2」/ 实际可达：

- ✅ 6 actions 完整改造接真后端（competitors / competitor-references / issues / search / admin embedding / activity-log）
- 🟡 1 action 端点 shape 重写（export / 旧 port 8001 INTERNAL_TOKEN /api/export/nodes → /api/projects/{pid}/exports + /nodes/{nid}/export）
- 🟡 1 action 端点真接 + 兼容层（project-stats-proxy / 旧 /api/projects/{pid}/stats 微服务 → /api/projects/{pid}/overview）
- ⏸ 2 actions 显式全函数 NOT_IMPLEMENTED stub（templates 无 prism-0420 OpenAPI 对应路径 + feed 工作流不一一对应 prism-0420 /api/news 域）
- ⏸ 7 页面 unlock 全 punt 子片 5（消费方签名漂移 + admin 页面深耦合 用户管理 stub + openclaw 页面 OpenAPI 无对应路径需 CY 拍删）

**根因**：cold-start prompt 假设 10 actions 全有真后端 / 实际 OpenAPI grep 出 4 个域无对应路径（templates / openclaw / feed 工作流 / admin 用户管理 / 项目级 ZIP 导出）/ 启动期 30min ls 穷举 + types/api.ts grep 是 SR-P22-3 真值（M01 register + 3a-ii broken imports + 3b SSE/WS + 3c OpenAPI 域不对应 = 四实证 / 子片 5 关闸前 sink 立规候选已成熟）。

**3c scope 修订归档**：6 actions 完整接 / 2 actions 端点重写 / 2 actions 全 punt / 0 页面真接（ignore 留子片 5）/ R1+R2 第 4 数据点 + 立修 root cause。

## §3d 子片 4 findings（R1+R2 第 5 数据点 / 全新写形态）

### R2 spec P1 立修（2 项 / 已修 root-cause）

1. **client `.catch` 吞 NEXT_REDIRECT（root-cause / 子片 3b NEXT_REDIRECT 硬伤的 client-side 同根因新场景）** — `teams/page.tsx:29` + `teams/[teamId]/page.tsx:54` 调 `getTeams()` / `getTeam()` 的 `.then().catch(() => setX([]))` 把 server action `withAuthRedirect → redirect("/login")` 抛的 NEXT_REDIRECT 当业务错误吞 / 401 退化为「空列表」或「团队不存在」非跳 /login / 违反 spec 06 §3「mutation 路径 401 不静默吞错」+ design 02-frontend-design.md §4 表 UNAUTHORIZED 行 + errors.ts:91 NEXT_REDIRECT 必透出。**真漏抓 root-cause**：`projects/page.tsx:55-57` 同款（子片 3a-ii 已合规 page）也吞 NEXT_REDIRECT — 不是子片 4 引入硬伤 / 是历史子片同根因。**已修**：errors.ts `isNextRedirectError` 加 `export` 关键字 + 3 处 `.catch` 重写为 `if (isNextRedirectError(error)) throw error;` 后再退化。一改通修 N+ caller / R 范式第 5 数据点新发现。
2. **TeamMemberAdd response schema 字面漂移** — backend `teams_router.py:161-166` 返回 dict（id/team_id/user_id/role）/ teams.ts:205 类型标注 `<{id: string}>` 仅消费 id 字段当前未误用 → **R2 自降为 P2 punt**（OpenAPI dict 无字面 contract / consumer 当前正确）。

### R2 spec P2 punt（2 项进 pool）

| # | 描述 | file:line | 触发时机 |
|---|------|-----------|----------|
| P22-4-1 | TeamMemberRemoveResponse.residual_project_members UI 未消费仅展示 count | teams/[teamId]/page.tsx:304 + actions/teams.ts:283 | Phase 2.3 GET members endpoint 上线后统一展示残留成员详情 |
| P22-4-2 | isTeamOwner action 死代码 / page 直接 `user?.id === team.creator_id` 推断未调用 | actions/teams.ts:67 | 子片 5 cleanup 决定保留（Phase 2.3 server component 预留）or 删除 |

### R1 reuse P1 / P2

- **R1 P1**：无（teams.ts 范式与 projects.ts 命名 / 错误处理 / handleActionResult 调用 / shadcn 组件 / Dialog 模式全对齐）
- **R1 P2-1 / withAuthRedirect 11 处重复（trend update of P22-3b-1 / P22-3c-1）**：teams.ts +1 = 累计 11 处 / 早过抽 helper 临界点 5 / 已 trend 持续密集 / 子片 5 cleanup Phase 2.3 启动前必抽 lib/server-action-helpers.ts
- **R1 P2-2 / header 高度 h-16 vs h-14 不一致**：teams 页 hard-code `h-16 + border-slate-200 bg-white` / projects 页 `h-14 + border-border bg-card` shadcn token / 推 Phase 2.3 layout shell 统一时一并修
- **R1 P2-3 / confirm-by-name Dialog 内联 2 次（transfer + delete）**：当前仅 teams/[teamId]/page.tsx 内重复 / 未达跨文件 3+ 临界 / 观察点 / Phase 2.3 有其他 danger zone 操作再评估抽 ConfirmByNameDialog 组件

### 子片 4 prompt-vs-reality 漂移（SR-P22-3 第 5 实证 / 第 5 数据点 sink 时机）

cold-start prompt「子片 4」段写「6 路由 + R-X3 RBAC + soft-delete + restore」/ 实际可达：

- ✅ 3 路由真接（/teams + /teams/new + /teams/[teamId] 合并 5 cards）
- ✅ 9 actions + 1 projects-side moveProjectTeam（getTeams / getTeam / isTeamOwner / createTeam / updateTeam / deleteTeam / transferOwnership / addMember / updateMemberRole / removeMember / moveProjectTeam）
- ⏸ /members /transfer /danger 三独立路由 → 合并到 /teams/[teamId] 单页 cards（backend 缺 GET members + 候选 owner 检索 endpoint / 独立路由意义稀薄）
- ❌ soft-delete + restore → **prompt 字面错记**（M20 design §3 Q8=B 字面已决 hard delete + RESTRICT FK / 不是 backend 缺口 / **撤销该选项 / 不立项**）
- ⏸ M20 后端 4 项 gap 进 cross-sprint pool P22-4-backend-gap：(a) GET /api/teams/{tid}/members + (b) GET 候选用户检索 + (c) GET /me-role / Phase 2.3 集成期合并

**根因**：handoff prompt 凭印象描述 backend endpoint / 没在写 prompt 时 grep schema/router 字面 / SR-P22-3 第 5 实证（前 4：M01 register + 3a-ii broken imports + 3b SSE/WS + 3c OpenAPI 域不对应 / 第 5：3c handoff 写 prompt 凭印象 → 子片 4 启动期 ls 穷举触发识破）。

**4 scope 修订归档**：3 路由真接 + 10 actions + 1 projects-side / R1+R2 第 5 数据点 + R2 真漏抓 client `.catch` 吞 redirect root-cause / SR-P22-3 第 5 实证支撑 / SR-P22-4 跨子片同根因检测**全新写形态新场景变体**实证（root-cause 不在 server actionError 而在 client useEffect catch / 历史 子片 3a-ii projects/page.tsx 同根因连带修）。

## §4 SR-P22 立规候选 sink（待 5 数据点后实证）

| 立规 ID | 描述 | 立规时机 |
|---------|------|----------|
| SR-P22-1 | feedback_decision_layering 自检第 4 问（已即时落） | ✅ 已立 |
| SR-P22-2 | feedback_subagent_sprint §4 — 前端继承形态 R 范式适配（R1=1 Sonnet + R2=1 Opus 而非 R1=3 + R2=1 / 第 2 数据点实证 R2 真漏抓硬伤 ROI 高于 R1）| 5 数据点后实证 sink |
| SR-P22-3 | feedback_decision_layering 反模式表 — prompt 块本身分层错误识破（M01 register + 3a-ii broken imports + 3b SSE/WS 路径完全不在 OpenAPI + 3c OpenAPI 域不对应 4 个 actions = 四实证 / 已成熟）| 子片 5 关闸前 sink |
| SR-P22-4 | feedback_subagent_sprint §4 — R2 spec subagent **跨子片同根因漂移检测**是核心 ROI 维度（mutation 路径 401 静默吞错是 3a-ii read 路径硬伤的 mutation 同型 / 3a/3b R2 漏抓 / 3c R2 闭环 / 抓 root-cause 修一处通修 N+ caller / **第 5 数据点新场景变体实证**：root-cause 不限 server actionError / client useEffect `.catch` 吞 NEXT_REDIRECT 是同根因 client-side 新场景 / 子片 4 R2 闭环 + 历史 projects/page.tsx 同根因连带修） | 第 5 数据点支撑 / 子片 5 关闸前 sink |
| SR-P22-5 | feedback_subagent_sprint §6 关闸沉淀 — handoff prompt 写 endpoint 字面前必 grep schema/router（5 数据点 5 实证：M01 register + 3a-ii broken imports + 3b SSE/WS + 3c OpenAPI 域不对应 + 4 prompt 凭印象写 soft-delete restore / 子片 4 启动期 ls 穷举耗 30min 才识破 / handoff prompt 写时 grep 一次省下游 sprint 反复识破成本） | 子片 5 关闸前 sink |

## §5 元贡献（实证）

- **前端继承形态首次走通**：拷贝 130 文件 → 选择性删 next-auth/drizzle → 渐进改造 → 子片 1 codegen + 子片 2 auth flow 接通；为子片 3a-3c 业务页面改造范式提供模板。
- **eslint ignore 渐进还债范式**：子片 1 移 `services/http-client.ts` + `auth-token-store.ts` + `types/**`；子片 2 移 `services/auth.ts`（删）+ `contexts/auth-context.{tsx,test.tsx}`（新写）+ `lib/validators/auth.ts` + `app/login/**` + `app/register/**`。每改一文件 → 移除 ignore → eslint ✓ 才 commit；累计移除 N=11 项。
- **R 范式合并数据点 ROI**：子片 1 仅工具链（http-client mock 充分）/ 子片 2 真用 endpoint（cookie + CORS + e2e）；合并跑使 R2 spec 验证有真锚点（schema 同步 / cookie 通道 / CORS 配置全字面对照），ROI 显著高于子片 1 单独跑。
- **R2 spec 跨子片同根因检测 ROI**（第 4 数据点新发现）：3c R2 抓到 mutation 路径 401 静默吞错是 3a-ii read 路径硬伤的同型再发 / root-cause 在 errors.ts.actionError 一改通修 11 mutation + 4 defineAction caller / 3a/3b R2 漏抓但 3c R2 闭环 / 验证 R2 spec subagent 不只是「本子片字面合规」检查器，更是「跨子片同根因漂移检测」机制 — 是 SR-P22-4 立规候选基础。

---

last_updated: 2026-05-09
