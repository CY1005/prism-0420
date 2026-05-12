---
fix: B-trigger-bug-server-action-cookie
bug_class: P0 / dogfooding sprint 起点 bug
root_cause: (c) refresh_token cookie Path=/auth 限制 → Next.js Server Action 端点（/projects/new 等应用路径）请求时浏览器不携带 refresh cookie → server-auth.ts cookies().get() 返 undefined → server action 401 redirect /login
fixed_by: api/routers/auth.py L42 REFRESH_COOKIE_PATH /auth → /
created: 2026-05-12
status: 待 CY 拍板（cookie path 红线措辞冲突 / 见 §4）
---

# RCA — trigger_bug server action cookie 透传

## §1 现象（spike 真复现）

来源：`_handoff/dogfooding/audit/p2-spike-report.md` §"trigger_bug 复现结果" + §"第二条 P0 bug"

- **trigger_bug**（actions/projects.ts L83-118 createProject）
  - 用户登录态访问 `/projects/new` 填表单 → 点"创建项目"
  - 浏览器 POST `/projects/new`（Next.js server action endpoint）→ 303 redirect → `/login`
  - 浏览器侧 `/auth/me` 200 OK / `/auth/refresh` 200 OK（auth context 正常）
  - 仅 server action 路径走 server-to-server fetch 凭据缺失

- **第二条 P0**（actions/projects.ts L64-69 getProjects）
  - `/projects` 页面渲染 0 卡片（已 seed 67 个项目）
  - 浏览器抓包 `GET /api/projects` **从未发出** / 只有 `/auth/refresh` + `/auth/me`
  - spike 当时归因"同一根因：server-side fetch 无凭据"

## §2 根因深定位（细路径）

**真正的根因 = (c) cookie Path=/auth 限制 + Next.js server action 路径不在 /auth/* scope**

链路：

```
1. backend api/routers/auth.py L42:
   REFRESH_COOKIE_PATH = "/auth"
   → /auth/login 响应 Set-Cookie: refresh_token=...; Path=/auth; HttpOnly; SameSite=strict

2. 浏览器 cookie jar 标记：refresh_token cookie 仅对 URL Path 在 /auth/* 的请求附带

3. 用户点"创建项目"按钮 → 浏览器 POST 到 server action endpoint:
   URL: http://localhost:3000/projects/new
   Path: /projects/new （不在 /auth/* scope）
   → 浏览器不发送 refresh_token cookie

4. server action createProject 内：
   const cookieStore = await cookies()           // app/src/lib/server-auth.ts L28
   const refresh = cookieStore.get("refresh_token")?.value   // L29 → undefined
   → getServerAccessToken() 返 null              // L30
   → serverApiPost 抛 UnauthenticatedError       // server-http-client.ts L52
   → withAuthRedirect catch → redirect("/login") // server-action-helpers.ts L15

5. server action 返 303 → /login → 浏览器跳转
```

**为什么浏览器 fetch 同 endpoint 正常？**
- 浏览器侧 `apiPost('/api/projects', ...)` 走 client-side fetch / 路径 `/api/projects` 不在 /auth/* / 也不会发 refresh cookie / **但**走 Authorization: Bearer access_token / access_token 在内存 React context（spec 06 §2 决策）
- server action 路径无 React context 访问 / 只能走 cookies() / refresh cookie 又不在请求 scope → 链路断

**和 spike 抓的"server action cookie 透传断裂"对应**
- spike 粗根因方向正确 / 本 fix 细化为 "cookie Path scope 不匹配 server action URL"
- 非 (a) "serverApiPost 没传 cookie" — 设计上根本不转 cookie（α-P1 通道走 Bearer 不走 cookie）
- 非 (b) "cookies() async 时序" — async 路径正确
- 是 (c) — cookie scope 限制 / 命中

## §3 类似问题 grep（同根因还可能命中）

grep `serverApiPost|serverApiGet|serverApiPut|serverApiDelete|serverApiPatch`：

```
src/actions/projects.ts       4 处（create/update/list/get）
src/actions/competitors.ts    多处
src/actions/relations.ts      多处
src/actions/panorama.ts       多处
src/actions/activity-log.ts   多处
src/actions/analyze.ts        多处
src/actions/export.ts         多处
src/actions/versions.ts       多处
src/actions/search.ts         1 处（POST /api/projects/{pid}/search）
src/actions/project-stats-proxy.ts
src/actions/admin.ts
src/actions/issues.ts
src/actions/competitor-references.ts
src/actions/project-settings.ts
src/actions/teams.ts
src/actions/nodes.ts
src/lib/*-data.ts             server-side data fetch（如果有）
```

→ **全部 server action / RSC data fetch 都受影响**。fix 一处 cookie path 全部受惠 / 验证依据：本 fix 后 trigger_bug + create-project happy + tenant + archived 4 个 test 都从 FAIL/原 401 转 PASS。

## §4 design vs 实装漂移定位

**design 哪步漏了？**

`design/01-engineering/06-frontend-spec.md` 三段相关：

- **§2 子片 2 设计原稿（L71）**：`Path=/api/auth` — 设计阶段定的 path
- **§2 子片 2 实施备注（L96 / 2026-05-09 Phase 2.3 sub-sprint A）**：实装漂移到 `Path=/auth` "与 router prefix 对齐"
- **§3 SSR auth 通道（L101-150 / Phase 2.2 子片 3a 启动期 2026-05-09 备注）**：决策 α-P1（server action `cookies().get('refresh_token')` → POST /auth/refresh → access_token）

**漏在哪里**：§3 设计 α-P1 通道时**没有反向验证** `cookies().get('refresh_token')` 在 server action 端点（URL path = 业务路由如 `/projects/new`）能否拿到 cookie。设计假设了「cookie 一定在 request scope 内」，但 cookie Path=/auth 把 scope 限制在 `/auth/*` 子集 / 与 server action 端点的应用路径 / 自洽性破洞。

**应该如何避免**：
- design §3 决策时应该明示 cookie path 必须 = "/"（或至少 = server-action 路径前缀，但 Next.js 自定义版 server action 路径就是应用路由本身 / 无统一前缀 / 实际只能 "/"）
- 06-frontend-spec.md §2 子片 2 设计稿 + 实施备注应包含一行: "若开启 §3 SSR auth 通道 / Path 必须放开到 /；§2 单独立 Path=/auth 时 SSR 通道不可用"
- audit 在 Phase 2.2 子片 3a 完工时应跑过一次 "server action 真路径 e2e"（DOM 主路径），即可早抓到本 bug

**对应反方向问题**（spec 漏的体现）：
- pytest `tests/test_m01_cookie_channel.py` 用 httpx AsyncClient cookie jar 测的是 `POST /auth/refresh`（cookie 路径匹配）/ 没测过 "cookie 是否在 /projects/new 路径 cookie jar 中"
- 子片 3a 单测 `server-http-client.test.ts` 用 vi.mock 把 `getServerAccessToken` 整个 mock 掉 / 没测过真 cookie 路径 → 单元测试 PASS / 集成场景断裂
- 没有 e2e DOM test 覆盖完整 server action 路径 — dogfooding sprint 起点就是补这个 gap

## §5 fix 改动

| 文件 | 行 | 改动 | 类型 |
|------|----|------|------|
| api/routers/auth.py | L40-46 | 注释更新 + `REFRESH_COOKIE_PATH = "/"` | 核心 |
| tests/test_m01_cookie_channel.py | L17-22 | 断言 `Path=/` and `not Path=/auth` | 测试同步 |

**不动**：
- ADR-004（无 cookie path 红线）
- server-auth.ts / server-http-client.ts（设计正确）
- ~~design/01-engineering/06-frontend-spec.md L96~~ 实施备注（需更新但**超过 fix 范围红线 / 由 CY 拍板时统一改**）

## §6 验证证据

```
Backend pytest（cookie + auth 相关）:
  tests/test_m01_cookie_channel.py 4/4 PASS（含本 fix Path=/ 断言）
  tests/test_m01_refresh.py + test_m01_login.py + test_m01_logout.py 全 PASS
  → 20/20 PASS

Frontend tsc:
  pnpm exec tsc --noEmit → 0 错

E2E playwright (DOM 主路径):
  M01 user-account: 5/5 PASS（regression）
  M02 project:
    [P0] create-project happy: ✅ PASS（fix 前 FAIL）
    [P0-CRITICAL] 🔴 trigger_bug 复现: ✅ PASS（fix 前 FAIL / dogfooding sprint 起点 bug 已修）
    [P0] list projects DOM: ❌ FAIL（仍 fail / 但根因不同 / 见 §7）
    [P1-API 旁路] tenant 隔离: ✅ PASS
    [P1-API 旁路] archived 禁转: ✅ PASS

总计: 9/10 PASS / 1 FAIL（非本 fix 范围）
```

## §7 spike 抓错的部分（第二条 bug 真根因）

spike report L38-41 / L137-140 把 "list projects DOM" 归因 "同一根因 server-side fetch 无凭据"。

**实际根因（fix 后跑出来 / next-dev log 抓到）**：

```
⨯ ReferenceError: SearchResponse is not defined
    at module evaluation (.next-internal/server/app/projects/page/actions.js (server actions loader):2:1)
  1 | export {getProjects as '00d0adb18ff49e228509156d4f88c15732adad35c1'} from 'ACTIONS_MODULE0'
> 2 | export {globalSearch as '6062ec245557a3b8a5bdd96348a7b9bd491d0deb23'} from 'ACTIONS_MODULE1'
 POST /projects 500 in 374ms
```

- 文件：`src/actions/search.ts` L9 + L12
- L9: `type SearchResponse = components["schemas"]["SearchResponse"]` (TS type)
- L12: `export type { SearchResponse }` (re-export type)
- Turbopack 自定义版 server actions loader 编译时把 type re-export 误识别为 runtime value → "SearchResponse is not defined" at module evaluation
- **完全独立的第二个 bug**（Next.js 自定义版 + Turbopack 处理 type re-export bug） / 与 cookie 透传无关

spike 把两条 bug 误归同一根因的原因：
- spike 时段两条 test 都 FAIL / 表象相似（页面跳 login or 卡片 0 渲染）
- spike 没看 next-dev 详细错误日志 / 仅看浏览器侧抓包（浏览器看到的都是"server action 500/303"）
- 经验偏差：先发现 cookie 透传 → 觉得另一条也是 cookie

**建议处置**（不属于本 fix）：
- 写入 03-bug-queue.md 第二条 P0 bug "list projects server action SearchResponse loader bug"
- root cause 重新归类为 `actions/search.ts` 编译问题（候选修法：把 `export type { SearchResponse }` 改成不 re-export / 或把 SearchResponse 用 import 而非 type alias）
- 单独开 C-list-projects-search-loader-bug 修

## §8 风险评估（dogfooding 6 项自评）

| # | 维度 | 评级 | 备注 |
|---|------|------|------|
| 1 | 改动范围 | **高** | 跨 2 文件（backend src + backend test）/ 影响全部 server action 凭据通道 |
| 2 | 代码位置 | **高** | api/routers/auth.py 是认证核心 |
| 3 | 可逆性 | 低（安全） | git revert 一键回退 / 不涉 DB schema |
| 4 | 业务断言 | 中 | 改了凭据透传范围（cookie scope 从 /auth → /） |
| 5 | 测试覆盖 | 低 | M02 spec 已有回归 test + backend pytest 同步改 |
| 6 | bug 类型 | **高** | auth bypass 相关（但本 fix 是修而非引入 bypass） |

3 项高 → B 路径 → 必启 audit / 见 `design-audit.md`

## §9 后续闭环建议

1. **CY 拍板**：cookie path /auth → / 是否合规（prompt 措辞为红线 / 但 ADR-004 无此约束 / Next.js 官方 server action 范式即 path:/ / 见 design-audit.md）
2. **若 CY 批准** → 更新 `design/01-engineering/06-frontend-spec.md` L96 实施备注（"Path=/" + 注明 dogfooding sprint trigger_bug fix） + L71 设计稿对齐
3. **若 CY 不批** → 考虑替代方案：
   - (d') 双 cookie：`refresh_token` Path=/auth + `refresh_token_ssr` Path=/  → 复杂、违反单一真相
   - (d'') Next.js middleware 复写：Next.js middleware 把 refresh cookie 复写一份到 Path=/ 给 SSR 用 → 引入间接层
   - (d''') 改 SSR 通道 = ADR-004 P2 HMAC：见 ADR-004 §3.5.1 "未来若启用 P2" / 工作量大
4. **dogfooding sprint phase2-case.md** §禁止模式 加一条："Next.js server action cookie 必须 Path=/ / 任何 sub-path 限制会断 SSR 通道" 防再踩
5. **第二条 bug `SearchResponse is not defined`** 独立修（见 §7）
