---
title: Phase 2.2 子片 1-5 冷启动 prompt 集合
status: ready
owner: CY
created: 2026-05-09（子片 0 prep commit aa6dbd0 关闸后预录）
purpose: |
  Phase 2.2 全集 6.5-8 天工程量 / 单 Claude session $10 上限远不够 / 必须跨 7 sessions
  完成。每个子片一份独立冷启动 prompt / CY 开新 session 直接复制粘贴对应代码块。
parent: _handoff/p22-sprint-prompt.md（总 sprint 提示词）
related: design/01-engineering/06-frontend-spec.md（auth + codegen sanction）
---

# Phase 2.2 子片 1-5 冷启动 prompt 集合

> **使用方法**：CY 每个子片开新 Claude session → 复制对应章节代码块全文粘贴执行。
>
> **跨 session 顺序硬约束**：1 → 2 → 3a → 3b → 3c → 4 → 5（依赖链 / 不可乱序）。

---

## 计划总览

| 子片 | 范围 | 估 cost | 估时 | 依赖 | 风险 |
|------|------|---------|------|------|------|
| 1 | codegen + http-client + Bearer JWT | $2-3 | 0.5-1 天 | 子片 0 prep ✅ | 低（工具链）|
| 2 | auth flow（login/register/refresh）+ 1 e2e | $2-3 | 0.5 天 | 子片 1 + 后端 alive | 中（需 CY 跑后端验证）|
| 3a | projects 列表 + 详情 + dimension 档案 | $4-6 | 1.5 天 | 子片 2 | 高（核心页面 + UI 手测）|
| 3b | node + 模块树 + relation-graph + comparison + import | $4-6 | 1.5 天 | 子片 3a | 高（XYFlow + 复杂交互）|
| 3c | competitor + issue + search + admin + openclaw 长尾 | $3-5 | 1 天 | 子片 3b | 中 |
| 4 | M20 团队页（Prism 无 / 全新写）+ 轻量 design 草案 | $3-5 | 1-1.5 天 | 子片 3c（可与 3c 并行）| 中（shadcn pattern 新写）|
| 5 | D 类 #3+#15 join 真装配 + 关闸 audit + handoff 同步 | $1-2 | 0.5 天 | 子片 4 | 低 |

**总估**：$19-30 / 6.5-8 天 / 7 sessions。

---

## 跨 session 共用纪律（每个 prompt 内嵌引用）

1. **冷启动按序读**（每 session 前 5 分钟）：
   - CLAUDE.md（L135 后端不抄 / 前端可拷改）
   - design/01-engineering/06-frontend-spec.md §1+§2+**§3 SSR auth 通道**（codegen + 客户端 auth + 服务端 auth）
   - design/adr/ADR-001-shadow-prism.md §6（前端继承策略）
   - design/adr/ADR-004-auth-cross-cutting.md（Auth 横切 / P1 不动 / P3 已 cover Cookie / **§3.5.1 prism-0420 当前 Server Action 走 α-P1 链路**）
   - _handoff/cross-sprint-punt-pool.md 状态分布快照段
   - _handoff/p22-sprint-prompt.md（总 sprint）+ 本文件对应子片段
   - 上一子片 commit message（`git log -1 --format=%B HEAD`）

2. **eslint ignore 移除纪律**：每改一个文件 / 一个目录改造完 → 从 `app/eslint.config.mjs` globalIgnores 移除该条 → 跑 `cd app && pnpm exec eslint` 必过 → 再 commit。子片 0 prep 留下的 ignore 是债 / 子片 1-4 必须逐文件还。

3. **R1+R2 范式（试运行）**：每子片末 spawn:
   - R1 = 1 reuse subagent（Sonnet / 验 Prism 拷过来 vs prism-0420 既有 / DRY / 命名规约）
   - R2 = 1 spec subagent（Opus / 验 OpenAPI vs 前端调用契约一致 / TS types 同步）
   - finding P1 立修同 commit / P2 punt 进 audit
   - SR-P22-2 立规候选：sprint 末实证后扩 feedback_subagent_sprint §4

4. **commit 关闸**：每子片完成 → commit + push origin/main → 更新 `_handoff/next-session.md` 推荐下一子片 prompt → ack CY 等"继续"

5. **usage 自检**：每子片启动时跑 `/usage` / 若周用量 >60% 主动报 / >80% 强制开新会话延后

6. **memory 必读**：feedback_subagent_sprint / feedback_design_first / feedback_decision_layering / feedback_completion_audit / feedback_code_first / feedback_usage_budget v3

---

## 子片 1 — codegen + http-client + Bearer JWT

> **estimated cost**: $2-3 / **estimated time**: 0.5-1 天 / **依赖**: 子片 0 prep ✅

```
继续 prism-0420 Phase 2.2 子片 1：codegen + http-client + Bearer JWT。

状态快照（git log）：
- 子片 0 prep ✅ aa6dbd0（拷 130 文件 + 加 deps + 删 next-auth/drizzle / eslint 拷贝层暂禁）
- engineering-spec 06 ✅ 827da20（codegen = openapi-typescript / auth = access 内存 + refresh httpOnly cookie / 不修订 ADR）

冷启动按序读：
1. CLAUDE.md
2. design/01-engineering/06-frontend-spec.md §1（codegen）+ §2（auth）
3. design/adr/ADR-004-auth-cross-cutting.md §1 P1+P3（access Bearer header / refresh Cookie 已合规）
4. _handoff/p22-subslice-prompts.md「跨 session 共用纪律」+「子片 1」段
5. app/src/services/http-client.ts（Prism 拷过来的 / 待替换 / 当前 import drizzle/next-auth 编译炸）

实施清单（spec 06 §1+§2 驱动）：

A. OpenAPI export（不需后端 alive）：
- 写 scripts/export_openapi.py：from api.main import app; json.dump(app.openapi(), open("app/openapi.json", "w"))
- 跑 uv run python scripts/export_openapi.py 生成 app/openapi.json
- gitignore app/openapi.json（codegen 输入 / 不入库 / 每次 codegen 前重生）

B. codegen 接通：
- 改 app/package.json scripts.codegen：openapi-typescript ./openapi.json -o src/types/api.ts
  （从本地文件 / 不依赖 http://localhost:8000 / 与 spec 06 §1 一致但路径细化）
- 跑 cd app && pnpm install（首次 / 装 11 deps + openapi-typescript）
- 跑 pnpm run codegen → app/src/types/api.ts 生成
- verify：head app/src/types/api.ts 看到 components.schemas + paths

C. http-client 替换（src/services/http-client.ts）：
- 删原 Prism 实现（drizzle/next-auth 引用）
- 写新 fetch wrapper：
  - baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  - method/headers/body 标准
  - credentials: 'include'（spec 06 §2 / 携带 refresh cookie）
  - Authorization: Bearer ${getAccessToken()} （从 React context 或临时 in-memory 占位 / 子片 2 接 auth context）
  - 401 自动调 /api/auth/refresh + retry 1 次（spec 06 §2）/ 失败抛 UnauthenticatedError 给上层（子片 2 接跳登录）
  - 类型用 src/types/api.ts 的 paths/operations 推（fetch<paths["/api/projects"]["get"]>）
- 1 个最简 vitest unit 验 baseUrl + headers 拼接 + 401 retry 路径

D. eslint ignore 移除：
- app/eslint.config.mjs globalIgnores 移除 src/services/permission.service.ts（不用了 / 直接删 src/services/permission.service.ts 因 drizzle 死耦）
  （等等 / 子片 1 不删 / 留子片 3 改造）
- 移除 src/types/**（新生成 / 必通过 lint）
- 必要时 src/services/http-client.ts 单文件移除 ignore（手写新代码 / 必通过 lint）
- cd app && pnpm exec eslint 必 ✅ 才 commit

E. 关闸：
- R1+R2 试运行：spawn R1 reuse + R2 spec / finding P1 立修
- commit "Phase 2.2 子片 1 — codegen 接通 + http-client 重写 + Bearer JWT 占位 + first eslint ignore 移除"
- push origin/main
- 更新 _handoff/next-session.md 推荐子片 2 prompt

验证（CY 协助 / 不替 CY 跑）：
- pnpm install 是否过 / 拷贝层 deps 解析无冲突
- pnpm run codegen 是否生成 types/api.ts
- 不跑 pnpm dev（拷贝层编译会炸 / 子片 2-3 渐进修复）

下一步子片 2：auth flow（login/register/refresh）+ 1 e2e。
```

---

## 子片 2 — auth flow（login/register/refresh）+ 1 e2e

> **status: completed** (2026-05-09 / commit `3b9bbc1`) — register 跳过改造（M01 未来扩展 / CY 选 (a)）/ 4 backend cookie e2e + 13 vitest + R1+R2 第 1 数据点合并子片 1+2 / 见 `design/audit/p22-pilot-template-validation.md`

> **estimated cost**: $2-3 / **estimated time**: 0.5 天 / **依赖**: 子片 1 + 后端 alive（CY 启动 uvicorn）

```
继续 prism-0420 Phase 2.2 子片 2：auth flow 改造 + 1 e2e。

状态快照：
- 子片 1 ✅ <commit-hash>（codegen + http-client + Bearer JWT 占位）
- engineering-spec 06 §2 实施清单（前端 5 项 / 后端 4 项）

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「跨 session 共用纪律」+「子片 2」段
2. spec 06 §2 实施清单（后端 router 改造 + 前端 auth context）
3. ADR-004 §1 P1+P3 + §核心 5 项（auth 横切范式 / require_user 不破）
4. api/routers/auth.py（M01 现有 router / refresh endpoint 需扩 cookie 通道）
5. app/src/actions/auth.ts + app/src/services/auth.ts + app/src/lib/validators/auth.ts（Prism 拷过来 / 待改造）
6. app/src/app/login/page.tsx + register/page.tsx

前置确认：
- CY 跑 uvicorn 后端 alive（用于 cookie set + CORS 验证）
  cd /root/workspace/projects/prism-0420 && uv run uvicorn api.main:app --reload
- CY 提供 NEXT_PUBLIC_API_BASE_URL（默认 http://localhost:8000）

实施清单：

A. 后端 router 扩展（spec 06 §2 实施清单后端 4 项）：
- /api/auth/login 加 Set-Cookie refresh_token httpOnly Secure SameSite=Strict Path=/api/auth Max-Age=<refresh TTL>
  （保留 body refresh_token 字段 deprecated 兼容 / spec 06 §2 字面）
- /api/auth/refresh 优先读 Cookie / 兜底读 body（双通道 / P3 字面合规）
- /api/auth/logout 加 Set-Cookie refresh_token=; Max-Age=0（清 cookie）
- api/main.py 加 CORSMiddleware：allow_origins=[NEXT_PUBLIC_APP_URL] + allow_credentials=True + allow_methods=["*"] + allow_headers=["Authorization","Content-Type",...]
- baseline tests 不破 / 1619 PASS 维持

B. 前端 auth context（spec 06 §2 实施清单前端 5 项）：
- 新建 app/src/contexts/auth-context.tsx：access token in-memory + getAccessToken() + setAccessToken()
- http-client（子片 1 写的）的 getAccessToken 接 auth context
- 改写 src/actions/auth.ts：login → POST /api/auth/login → setAccessToken + refresh cookie 自动收 / register → POST /api/auth/register / refresh → POST /api/auth/refresh / logout → POST /api/auth/logout
- 删 src/services/auth.ts（next-auth 客户端 / 不再用）
- 删 src/lib/validators/auth.ts 内 next-auth 相关 / 保留 zod schemas
- 启动时 RootLayout 调 refresh 续杯（cookie 自动携带）/ 失败跳 /login

C. login + register 页面：
- src/app/login/page.tsx + src/app/register/page.tsx 改 form action 调新 actions
- 删 next-auth signIn / useSession 调用
- error 路径：spec 06 §2 / 401 → 提示登录失败 / 5xx → 提示后端不可用

D. 1 e2e（vitest + jsdom 或 playwright / 用 Prism 已有的 vitest baseline）：
- 验 login flow：mock fetch 返 200 + access_token + Set-Cookie → assert auth context 已设 + 跳转
- 验 401 retry：mock 第一次 401 + refresh 200 + 重试 200 → assert 重试链路

E. eslint ignore 移除：
- app/src/actions/auth.ts、app/src/contexts/auth-context.tsx、app/src/lib/validators/auth.ts、app/src/app/login/**、app/src/app/register/**
- pnpm exec eslint 必 ✅

F. 关闸：
- R1+R2 试运行（第 2 数据点 / 累计 P1 立修 + P2 punt 进 audit）
- commit "Phase 2.2 子片 2 — auth flow 改造（access 内存 + refresh cookie + CORS）+ 1 e2e + ignore 移除 5"
- push
- 更新 next-session.md 推荐子片 3a

下一步子片 3a：projects 列表 + 详情 + dimension 档案。
```

---

## 子片 3a-i — SSR auth 通道沉淀 + 服务端 fetch helpers ✅

> **status: completed** (2026-05-09 / commit `e521656` + `ee3a2ad`)
>
> 成果：
> - spec 06 §3 SSR auth 通道沉淀（α-P1 链路 / 安全模型 / API 契约 / 引用方分类）
> - ADR-004 §3.5.1 备注（getServerSession 已删 / cross-ref / P2 演进保留 / 字面零修订核心 P2 设计）
> - `app/src/lib/server-auth.ts`（cookies → /auth/refresh → access_token / React.cache 单请求 memo）
> - `app/src/lib/server-http-client.ts`（serverApiGet/Post/Patch/Put/Delete + 401 不自动 retry / 复用 ApiError 类型）
> - vitest 7 unit tests（cumulated 20 PASS）
>
> SR-P22-2 立规候选实证扩展：spec 沉淀路径在子片 2 (auth) + 3a-i (SSR auth) 重复验证 / 范式可复用到子片 4 (M20) 团队页新写。

---

## 子片 3a-ii — projects 列表 + 详情 + dimension 档案 5 页面改造

> **status: completed** (2026-05-09 / commit 待填) — scope 修订：cold-start 6 页面 → 实际 2 页面真接 backend（list + new）+ 4 页面留 3b/3c（深耦合 actions/{nodes,panorama,feed,competitors,teams,export,activity-log,project-stats-proxy,project-role-context}）/ broken imports 26 处关闭 4 处余 22 / R1+R2 第 2 数据点 / R2 真漏抓 ai_api_key + 401 静默吞错 / 见 design/audit/p22-pilot-template-validation.md §3a + §3b
>
> **estimated cost**: $4-5 / **estimated time**: 1-1.5 天 / **依赖**: 子片 3a-i ✅
>
> 注：原计划子片 3a 总估 $4-6 / 已用 $1-2 在 3a-i 沉淀 spec + helpers / 剩 $4-5 真用于页面改造 + R1+R2

```
继续 prism-0420 Phase 2.2 子片 3a：projects 列表 + 详情 + dimension 档案。

状态快照：
- 子片 2 ✅ <commit-hash>（auth flow + CORS + 1 e2e）
- 后端 M02 项目 / M04 维度 / M05 版本 endpoint OpenAPI 稳定

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「跨 session 共用纪律」+「子片 3a」段
2. design/02-modules/M02-project + M04-dimension + M05-version 详设（响应 schema / 字段含义）
3. app/src/types/api.ts（子片 1 生成 / 看 paths /api/projects + /api/dimension-records + /api/version-records）
4. app/src/actions/{projects.ts,project-settings.ts,versions.ts}
5. app/src/lib/{projects-data.ts,project-detail-data.ts}
6. app/src/app/projects/{page.tsx,[projectId]/page.tsx,[projectId]/overview/page.tsx,[projectId]/settings/page.tsx,[projectId]/features/[featureId]/page.tsx,[projectId]/templates/**}

页面范围（5 页面 + 1 详情子页）：
- /projects 列表
- /projects/new 新建
- /projects/[projectId] 详情
- /projects/[projectId]/overview 概览
- /projects/[projectId]/settings 设置
- /projects/[projectId]/features/[featureId] 功能项档案（含 dimension 渲染）

实施模式（每页面一致 / spec 06 §3 字面驱动 / α-P1 链路）：
1. 删 import drizzle / next-auth / postgres / db schema
2. actions/* (`"use server"`) 改：旧 db.query → **`serverApiPost/Patch/Delete` from `@/lib/server-http-client`** + 用 src/types/api.ts 的 operations 类型；不得 import `@/services/http-client`（spec 06 §3 防层级混淆 lint 准则）
3. lib/*-data.ts 改：旧 SQL → **`serverApiGet`** 调用 + 类型转换（异步 server function / 由 RSC 调用）
4. page.tsx：
   - **Server Component**（默认）→ 调 lib/*-data.ts → 走 server-http-client → P1 链路
   - **Client Component**（`"use client"` form / interactive UI）→ 调 actions/* Server Action → 走 server-http-client → P1 链路
   - 错误处理：捕 ApiError → 401 → redirect /login（next/navigation `redirect`）/ 5xx → error.tsx / 业务码 → toast
5. 关键交互冒烟测试：CY 协助手测过列表加载 + 创建 + 详情 + 编辑

eslint ignore 移除：
- 每改一个文件从 globalIgnores 移除 / pnpm exec eslint 必 ✅ 才 commit

R1+R2 试运行（第 3 数据点）：
- R1 reuse：grep types/api.ts 是否被 actions/* 一致引用 / 是否有 fetch 重复 wrapper
- R2 spec：验响应 schema 字段是否完整渲染 / 是否漏 join 字段（D 类 #15 DimensionResponse join 子片 5 装配 / 本子片如遇可显式标 punt）

关闸：
- commit "Phase 2.2 子片 3a — projects + dimension 5 页面改造 + N e2e + ignore 移除 N"
- push
- 更新 next-session.md 推荐子片 3b

下一步子片 3b：node + 模块树 + relation-graph + comparison + import。
```

---

## 子片 3b — node + 模块树 + relation-graph + comparison + import ✅

> **commit**: `490ad23` / **estimated cost**: $4-6 / **依赖**: 子片 3a / **status**: completed
> **scope 修订（SR-P22-3 第 3 实证）**：4 actions 完整改 + 1 部分 + 2 全 punt + errors.ts NEXT_REDIRECT 立修；7 页面解锁全 punt 子片 5。R1+R2 第 3 数据点：1 P1 立修 + 1 errors.ts 修 + 6 P2 punt。详见 `design/audit/p22-pilot-template-validation.md` §3b。

```
继续 prism-0420 Phase 2.2 子片 3b：node + 模块树 + relation-graph + comparison + import。

状态快照：
- 子片 3a ✅ <commit-hash>（projects + dimension 5 页面）
- @xyflow/react 已装（子片 0 prep）/ relation-graph 用此

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「跨 session 共用纪律」+「子片 3b」段
2. design/02-modules/M03-node + M08-module-relation + M11-cold-start + M14-comparison-snapshot 详设
3. app/src/types/api.ts paths /api/nodes + /api/module-relations + /api/cold-start + /api/comparison-snapshots
4. app/src/actions/{nodes.ts,relations.ts,panorama.ts,import.ts,import-ai.ts}
5. app/src/components/{feature-tree.tsx,relation-graph.tsx,treemap-view.tsx,ai-import-wizard.tsx}
6. app/src/app/projects/[projectId]/{modules,relation-graph,comparison,import,analysis}

页面范围：
- /projects/[projectId]/modules/[moduleId]
- /projects/[projectId]/relation-graph（XYFlow）
- /projects/[projectId]/comparison（M14 versus snapshot）
- /projects/[projectId]/import（M11 cold-start + M17 ai-import 两路）
- /projects/[projectId]/analysis（M13 analyze SSE）

特殊关注：
- relation-graph：XYFlow + 模块关系图 / 数据形态（nodes + edges）需对齐 OpenAPI
- analysis SSE：fetch 不直接支持 EventSource / 用 fetch ReadableStream + TextDecoder 解析（spec 06 后续可补 §3 SSE 范式）
- import-ai：M17 异步 zip 上传 + ws 状态推送（M17 后端 R-X4）/ 前端轮询 task status 兜底

R1+R2、ignore 移除、关闸 同 3a 模式。

下一步子片 3c：competitor + issue + search + admin + openclaw 长尾。
```

---

## 子片 3c — competitor + issue + search + admin + openclaw 长尾 ✅

> **commit**: `bccb225` / **estimated cost**: $3-5（实际 ~$6 / SR-P22-3 第 4 实证）/ **依赖**: 子片 3b / **status**: completed
> **scope 修订（SR-P22-3 第 4 实证）**：6 actions 完整改 + 2 actions 端点重写（export schema 对齐 + project-stats-proxy 端点切到 /overview）+ 2 actions 全函数 NOT_IMPLEMENTED stub（templates 无 OpenAPI 对应域 + feed 工作流不一一对应 /api/news 域）+ validators/issue.ts 加 title + projectId + **errors.ts.actionError 立修 UnauthenticatedError → redirect("/login") root-cause 一改通修 mutation 路径 401 静默吞错**；7 页面解锁全 punt 子片 5（admin 用户管理页 / openclaw 页面 OpenAPI 无对应路径需 CY 拍删 / 长尾 issue+template+search 页面消费方深耦合）。R1+R2 第 4 数据点：R2 真漏抓 mutation 路径 401 root-cause（3a-ii read 路径 401 同型 mutation 再发 / 3a/3b R2 漏抓 / 3c R2 闭环）+ admin NOT_IMPLEMENTED 类型 / R1 4 P1 候选复审：1 立修（admin 类型）+ 3 降 P2 punt（withAuthRedirect helper 5→10 文件 trend / search+stats-proxy 内联 redirect / StatsResult vs ActionResult 双类型）+ 5 P2 punt + 3 R2 P2 punt → 共 8 punt 进 cross-sprint pool。详见 `design/audit/p22-pilot-template-validation.md` §3c。

```
继续 prism-0420 Phase 2.2 子片 3c：competitor + issue + search + admin + openclaw 长尾。

状态快照：
- 子片 3b ✅ <commit-hash>（node + 模块树 + relation-graph + comparison + import）

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「子片 3c」段
2. design/02-modules/M06-competitor + M07-issue + M10-search + M16-overview-stats + M19-export 详设
3. app/src/types/api.ts paths /api/competitors + /api/issues + /api/search + /api/export + /api/admin
4. app/src/actions/{competitors.ts,competitor-references.ts,issues.ts,search.ts,export.ts,admin.ts,templates.ts,activity-log.ts,feed.ts,project-stats-proxy.ts}
5. app/src/app/{search,admin,openclaw,projects/[projectId]/{issues,product-lines,templates}}

页面范围（长尾批量）：
- /projects/[projectId]/issues
- /projects/[projectId]/product-lines/[plId]
- /projects/[projectId]/templates + [templateId]
- /search
- /admin
- /openclaw（如不属本期范围可标 punt 删页面）
- /feature

R1+R2 + ignore 移除 + 关闸 同 3a。

D 类 #3 IssueResponse 漏 join 字段 + #15 DimensionResponse 漏 join 字段：
- 子片 5 装配 / 本子片如前端真用到 join 字段（issue.node_name / dimension.dimension_type_key）→ 显式标 punt 等子片 5

下一步子片 4：M20 团队页新写。
```

---

## 子片 4 — M20 团队页新写（Prism 无） ✅ 完成

> **status**: completed 2026-05-09 / commit `0626add` / actual cost ~$3-4 / scope 自决收 6→3 路由 / R1+R2 第 5 数据点 / R2 真漏抓 client `.catch` 吞 NEXT_REDIRECT root-cause / SR-P22-3 第 5 实证 + SR-P22-4 全新写形态新场景变体 + SR-P22-5 立规候选新增
> **estimated cost**: $3-5 / **estimated time**: 1-1.5 天 / **依赖**: 子片 3c（可与 3c 并行）

```
继续 prism-0420 Phase 2.2 子片 4：M20 团队页新写（Prism 无 / 全新写）。

状态快照：
- 子片 3c ✅ <commit-hash>（competitor + issue + search + admin + openclaw 长尾）
- M20 后端 ✅ Phase 2.1 100% 收官（roadmap §6.3）/ OpenAPI 稳定 / R-X3 owner+admin+member RBAC 已实

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「子片 4」段
2. design/02-modules/M20-team/00-design.md（团队 schema + R-X3 RBAC + 转让 + 强制迁出 + soft-delete + restore）
3. app/src/types/api.ts paths /api/teams + /api/teams/{id}/members + /api/teams/{id}/transfer
4. app/src/app/teams/{page.tsx,[teamId]/page.tsx}（Prism 拷过来的 stub / 全部重写）
5. ADR-005 团队扩展（space_id → team_id / UUID / FK ondelete=RESTRICT）

页面范围：
- /teams 团队列表（owner + member 入参）
- /teams/[teamId] 团队详情（成员 + 项目归属 + 设置）
- /teams/new 新建团队
- /teams/[teamId]/members 成员管理（邀请 / 移除 / 角色变更）
- /teams/[teamId]/transfer 所有权转让（owner only）
- /teams/[teamId]/danger soft-delete + restore（owner only）

实施模式：
- 不拷 Prism / 全新写（shadcn pattern）
- 用 src/components/ui/* shadcn 已拷组件
- 类型走 src/types/api.ts paths/operations
- 错误处理走 prism-0420 ErrorCode 范式（permission_denied / team_not_found / 等）
- R-X3 RBAC 前端守卫：viewer/member/admin/owner 分别可见的按钮 disabled 状态

轻量 design 草案（ADR-001 §6.3 字面允许）：
- design/02-modules/M20-team/02-frontend-design.md 写一页
- 含：路由清单 + 组件树 + RBAC 状态机（哪个角色看哪个按钮）+ 错误处理表

R1+R2 试运行（第 5 数据点 / 全新写形态）：
- R1 reuse：与 Prism 拷过来的 components/ui shadcn 一致风格
- R2 spec：验路由 + 组件 vs design 草案 + RBAC vs M20 后端 R-X3

关闸：
- commit "Phase 2.2 子片 4 — M20 团队页新写（6 路由 + 轻量 design 草案 + R-X3 前端守卫）"
- push
- 更新 next-session.md 推荐子片 5

下一步子片 5：D 类 #3+#15 join 真装配 + 关闸 audit + handoff 同步。
```

---

## 子片 5 — D 类 join 装配 + Phase 2.2 关闸

> **estimated cost**: $1-2 / **estimated time**: 0.5 天 / **依赖**: 子片 4

```
继续 prism-0420 Phase 2.2 子片 5：D 类 #3+#15 join 真装配 + 关闸。

状态快照：
- 子片 4 ✅ <commit-hash>（M20 团队页新写）
- cross-sprint pool D 类 #3 IssueResponse + #15 DimensionResponse join 字段 schema 预留 default=None / 待真装配

冷启动按序读：
1. _handoff/p22-subslice-prompts.md「子片 5」段
2. _handoff/cross-sprint-punt-pool.md D 类 #3 + #15 段（条件触发型 / Phase 2.2 触发）
3. design/audit/m-cleanup-sprint.md §2 D 类（推迟到本子片）
4. api/services/{issue_service.py,dimension_service.py} + api/routers/{issue_router.py,dimension_router.py}
5. design/02-modules/M07-issue + M04-dimension §7 响应 schema

实施清单：

A. D 类 #3 IssueResponse join 字段（design §7 字面承诺）：
- IssueResponse schema 字段：node_name + created_by_name + assigned_to_name（已 default=None 预留）
- IssueDAO.list_by_project 加 selectinload(Issue.node, Issue.created_by_user, Issue.assigned_to_user)
- IssueService.list 装配填充 → router 响应模型 from_attributes
- e2e 字面断言：响应 JSON 含 node_name 非 None / SR-CLEANUP-3 防假覆盖

B. D 类 #15 DimensionResponse join 字段：
- DimensionResponse 字段：dimension_type_key + updated_by_name（已 default=None 预留）
- DimensionDAO.list_by_project + selectinload + Service 装配 + e2e 断言同上

C. 前端真用 join 字段（spec 06 §2 子片 3c 提示）：
- 子片 3c 长尾页面 issues / dimension 列表如已用 issue.node_name 渲染 → 子片 5 后真有数据
- 1 个 e2e（前端层）：fetch issues + assert response 含 node_name + 渲染 DOM 含

D. Phase 2.2 关闸（feedback_subagent_sprint §6 / SR-P22 立规候选 sink）：
- 写 design/audit/p22-pilot-template-validation.md：
  - §0 sprint 方法论：R 范式 R1=1+R2=1 试运行 / 5 数据点（子片 1-3a-3b-3c-4）/ SR-P22-2 实证扩 §4 立规
  - §1 子片汇总（commit hash + cost + 工作量 + R1/R2 命中数）
  - §2 D 类 join 装配实证（#3 + #15 关闭 / cross-sprint pool 41→39）
  - §3 元贡献：前端继承形态首次 / eslint ignore 渐进还债范式
- 更新 _handoff/cross-sprint-punt-pool.md：#3+#15 标 ✅ DONE
- 更新 design/00-roadmap.md §1 仪表盘：Phase 2.2 0% → 100%
- 更新 design/00-phase-gate.md 闸门 4 全 ✅ + 闸门 5 启动条件评估
- 更新 _handoff/next-session.md 推荐 Phase 2.3 集成 / 性能 sprint

E. SR-P22 立规候选 sink（3 项）：
- SR-P22-1（已即时落 feedback_decision_layering 自检第 4 问）
- SR-P22-2 扩 feedback_subagent_sprint §4：前端继承形态 R 范式适配（试运行实证后）
- SR-P22-3 加 feedback_decision_layering 反模式表（prompt 块本身分层错误识破）

关闸 commit："Phase 2.2 子片 5 — D 类 #3+#15 join 装配 + Phase 2.2 100% 关闸 audit + cross-sprint pool 41→39"

下一步：Phase 2.3 集成验证 + perf sprint 评估（roadmap §8 + cross-sprint C 类 12 项）。
```

---

## 维护

- 每子片关闸 commit 后 → 本文件对应章节 status: completed + commit-hash 填回
- 子片 prompt 跑一遍发现遗漏的纪律条目 → 本文件「跨 session 共用纪律」段补
- 估时偏离 ≥ 50% → 本文件计划总览段更新

last_updated: 2026-05-09
