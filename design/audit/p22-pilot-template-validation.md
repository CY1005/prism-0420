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

## §4 SR-P22 立规候选 sink（待 5 数据点后实证）

| 立规 ID | 描述 | 立规时机 |
|---------|------|----------|
| SR-P22-1 | feedback_decision_layering 自检第 4 问（已即时落） | ✅ 已立 |
| SR-P22-2 | feedback_subagent_sprint §4 — 前端继承形态 R 范式适配（R1=1 Sonnet + R2=1 Opus 而非 R1=3 + R2=1 / 第 2 数据点实证 R2 真漏抓硬伤 ROI 高于 R1）| 5 数据点后实证 sink |
| SR-P22-3 | feedback_decision_layering 反模式表 — prompt 块本身分层错误识破（M01 register + 3a-ii broken imports + 3b SSE/WS 路径完全不在 OpenAPI = 三实证）| 子片 5 关闸前 sink |

## §5 元贡献（实证）

- **前端继承形态首次走通**：拷贝 130 文件 → 选择性删 next-auth/drizzle → 渐进改造 → 子片 1 codegen + 子片 2 auth flow 接通；为子片 3a-3c 业务页面改造范式提供模板。
- **eslint ignore 渐进还债范式**：子片 1 移 `services/http-client.ts` + `auth-token-store.ts` + `types/**`；子片 2 移 `services/auth.ts`（删）+ `contexts/auth-context.{tsx,test.tsx}`（新写）+ `lib/validators/auth.ts` + `app/login/**` + `app/register/**`。每改一文件 → 移除 ignore → eslint ✓ 才 commit；累计移除 N=11 项。
- **R 范式合并数据点 ROI**：子片 1 仅工具链（http-client mock 充分）/ 子片 2 真用 endpoint（cookie + CORS + e2e）；合并跑使 R2 spec 验证有真锚点（schema 同步 / cookie 通道 / CORS 配置全字面对照），ROI 显著高于子片 1 单独跑。

---

last_updated: 2026-05-09
