---
title: 06 前端工程规约（codegen + auth 通道）
status: accepted
owner: CY
created: 2026-05-09
phase: Phase 2.2 启动期沉淀
related_adrs: [ADR-001 §6（前端继承策略 / db drizzle 删 / Server Actions 范式继承）, ADR-004 §1 P1+P3 凭据路径]
sanction_path: AI 自决（feedback_decision_layering 5 步流程跑后判定为 engineering-spec 级 / CY 看 spec 后保留否决权）
---

# 06 前端工程规约

> **本规约定位**：Phase 2.2 前端继承 Prism + 改造形态下，沉淀 codegen + auth 两项工程层决策。
> 不修订 ADR-001 / ADR-004 字面。CY 看本 spec 后可否决并升级到 ADR 流程。

## §1 codegen 工具：openapi-typescript（仅 TS types）

### 决策
**openapi-typescript**（仅生成 TS interface / fetch 自己写）。

### 候选淘汰理由

| 候选 | 淘汰理由 |
|---|---|
| orval（types + react-query hooks）| **被 ADR-001 §6.1 字面间接排除**："actions/* Server Actions → call prism-0420 API" 已锁继承 Prism 的 Server Actions 范式 / orval 强制 react-query hook 与 Server Actions 范式打架（页面要么 hook 要么 Server Action / 不能混）|
| openapi-generator-cli（多语言通用）| Java 依赖重 / TS 输出非 idiomatic / 生成代码巨大 / prism-0420 3-5 月内无多语言 SDK 需求 |

### 实施

```json
// app/package.json devDependencies
"openapi-typescript": "^7.x"

// app/package.json scripts
"codegen": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts"
```

- 生成位置：`app/src/types/api.ts`
- 调用范式：fetch 自己写（继承 Prism 既有 fetch 范式 / 与 Server Actions 兼容）
- 同步纪律：后端 endpoint 增删改 → `npm run codegen` 一键同步 / 类型漂移 0
- CI 守护：Phase 2.3 上线前补 CI step「pre-commit `npm run codegen` + 检查 git diff 为空」防开发者忘跑

### 3-5 月后果
- 类型漂移 0 / 维护成本最低
- 不强制 react-query / 与 Prism 既有 fetch 范式继承零摩擦
- 后续如需 hook 抽象 → 可手写 thin wrapper / 不引入 codegen 工具切换成本

---

## §2 auth 通道：access token 内存 + refresh token httpOnly cookie

### 决策
**B 方案**：access token 仅放内存（短 TTL 15min / 走 ADR-004 P1 Authorization Bearer header）+ refresh token 走 httpOnly cookie（走 ADR-004 P3）。

### 与 ADR-004 关系（关键 / 不修订 ADR）

- **P1 字面不动**：access token 仍走 `Authorization: Bearer <jwt>` / 后端 dependencies.py:54 不改
- **P3 字面已 cover Cookie**：ADR-004 §1 P3 字面 "Cookie 或 request body refresh_token" / 当前 router 实装走 body / 本规约引导改走 Cookie 是字面已合规扩展 / 不修订 ADR
- **第 4 问验证通过**：feedback_decision_layering 自检第 4 问跑过——B 方案不需 ADR 修订

### 候选淘汰理由

| 候选 | 淘汰理由 |
|---|---|
| A：access+refresh 都 localStorage | XSS 全失守 / refresh 被偷 = 永久 session / 安全收益 0 |
| C：access+refresh 都 httpOnly cookie | 安全增量微小（access TTL 15min 损失上限本就 ≤15min）/ 但需修订 ADR-004 P1 字面接 Cookie 兜底 + 改 dependencies.py:54 增 Cookie 读取分支 / 修订成本不值 |

### 实施清单

**后端**（M01 auth router 扩展 / 不破契约）：
- [ ] `/api/auth/login` 响应：access_token 留 body / refresh_token 改 `Set-Cookie: refresh_token=<raw>; HttpOnly; Secure; SameSite=Strict; Path=/api/auth; Max-Age=<TTL>`（保留 body 字段兼容做 deprecated）
- [ ] `/api/auth/refresh` 接收：优先读 `Cookie: refresh_token=...` / 兜底读 body（保留 P3 字面"Cookie 或 body"双通道）
- [ ] `/api/auth/logout` 响应：`Set-Cookie: refresh_token=; Max-Age=0`（清 cookie）
- [ ] FastAPI CORS middleware 配置：`allow_origins=[NEXT_PUBLIC_APP_URL]` + `allow_credentials=True` + `allow_methods=["*"]` + `allow_headers=["Authorization", "Content-Type", ...]`

**前端**（Phase 2.2 子片 1+2 实施）：
- [ ] access token 存 React context（内存 / 不入 localStorage / 不入 cookie）
- [ ] 所有 fetch 加 `credentials: 'include'` 自动携带 refresh cookie
- [ ] access token 401 → 自动调 `/api/auth/refresh`（cookie 自动携带）→ 拿新 access → 重试原请求 / 失败跳登录
- [ ] 页面刷新启动时调 `/api/auth/refresh` 用 cookie 续杯 access / 失败跳登录
- [ ] 登出按钮调 `/api/auth/logout` + 清内存 access

### 3-5 月后果
- 上线后 XSS 抵御达标（refresh 不可读 / access 损失上限 ≤15min）/ Phase 2.3 安全 review 一次通过
- 与 ADR-004 P1+P3 既有契约零摩擦 / 后端 P1 路径不破 / P3 路径仅扩 Cookie 通道（字面已合规）
- 后续若安全等级要升 → 切 C 方案（access 也 cookie）成本中等（改 dependencies.py:54 + ADR-004 v2）/ B 不锁死 C

### 引用方
- M01 auth router：本期实装（独立 sprint 或随 Phase 2.2 子片 2 auth flow 改造）
- Phase 2.2 子片 0 prep：前端拷过来时 fetch wrapper 加 credentials:'include'
- Phase 2.2 子片 2：auth flow 改造按本 spec 实施清单跑

### 实施备注（2026-05-09 / Phase 2.3 子 sprint A 顺修 punt #3+#5）

- **路径前缀**：本 spec 字面写 `/api/auth/*`；当前实装 router prefix=`/auth`（即 `/auth/login` / `/auth/refresh` / `/auth/logout`）。Next.js 前端通过 `NEXT_PUBLIC_API_URL` 拼接 → 实际请求 URL 仍是 `<api-host>/auth/*`。前缀差异不破 spec 语义。
- **REFRESH_COOKIE_PATH**：实装 `Path=/` 全局（2026-05-09 初版 `Path=/auth` 已废）。**dogfooding sprint trigger_bug 修复 2026-05-12**：原 `Path=/auth` 与 §3 SSR α-P1 通道冲突——Next.js Server Action 端点（如 `/projects/new`）请求时浏览器不携带 refresh cookie → `server-auth.ts cookies().get(refresh_token)` 返 undefined → server action 全部 401 → `withAuthRedirect` 跳 `/login`。修为 `Path=/` 让所有同源请求带 refresh cookie。**安全护栏不变**：HttpOnly + Secure(prod) + SameSite=Strict 仍是核心防御 / Path 限制唯一真作用是同 server 多 app namespace 隔离 / prism-0420 单 app 无此场景 / Next.js 官方推荐 `path: '/'`。详见 `_handoff/dogfooding/04-bug-fixes/B-trigger-bug-server-action-cookie/rca.md`。
- **logout body**：当前实装 204 + 清 cookie 即可；refresh_token 不需要 body 携带（cookie 已带）。前端调用形式：`fetch('/auth/logout', { method: 'POST', credentials: 'include' })`，body 不必填。

---

## §3 SSR auth 通道（Server Component / Server Action 鉴权）

### 决策

**α-P1**：Server 端 `cookies().get('refresh_token')` → `POST /auth/refresh` → access_token → `Authorization: Bearer` 调后端业务 endpoint（走 ADR-004 P1 字面）。

不走 ADR-004 P2 HMAC 通道（**原因**：P2 §3.5 信任链字面假设 Next.js Server Action 已通过 next-auth `getServerSession` 拿到 user_id；prism-0420 子片 0 prep 删 next-auth / Server Action 当前没 user_id；要走 P2 必须先通过 refresh cookie 推 user_id，与 α-P1 成本相同 / α-P1 路径更短）。

### 与既有决策的关系

- **spec 06 §2（access 内存 / refresh cookie）**：✅ 字面零修订。客户端仍 access in memory；服务端独立 refresh→access 链路 / 两条互不污染。
- **ADR-004 P1**：✅ 字面零修订。Bearer 仍是后端唯一 access 通道 / `dependencies.py:54` `_resolve_bearer` 不变。
- **ADR-004 P3**：✅ 字面合规。P3 「Cookie 或 body refresh_token」/ 服务端读 cookie 已是字面允许。
- **ADR-004 P2**：保留作演进选项 / Phase 2.3 评估是否启用（强安全敏感操作 / 防御深度需求）/ 见 ADR-004 §3.5 备注。

### 安全模型

| 层 | 客户端 | 服务端（Server Action / RSC）|
|---|---|---|
| access token 存储 | React context（内存）| 单次请求生命期内（不持久化 / 不入 cookie / 不入 module 全局）|
| access token 来源 | login response body | 服务端 refresh cookie → `/auth/refresh` 现拿现用 |
| refresh token | httpOnly cookie 自动携带 | 同 cookie 由 Server `cookies()` 读 |
| XSS 抵御 | access 内存（无 JS 可读 cookie 路径漏出 access）| 服务端无 JS 执行环境 / N/A |
| latency cost | 0 | 每个 Server Action / RSC 数据 fetch +1 refresh hop（80-150ms / Phase 2.3 可加 in-process 单请求 memo cache 优化为每请求 1 次）|

### 实施 layout

```
app/src/lib/
├── server-auth.ts          # cookies() → /auth/refresh → access_token (单请求 memo)
└── server-http-client.ts   # serverApiGet/Post/Patch/Delete + ApiError 类型化（与 client http-client.ts 对齐）

app/src/services/
├── http-client.ts          # 客户端（spec 06 §2 子片 1 / 不动）
└── auth-token-store.ts     # 客户端（spec 06 §2 子片 2 / 不动）
```

### API 契约（server-auth.ts）

```typescript
// app/src/lib/server-auth.ts
import { cookies } from "next/headers";
import { cache } from "react";  // RSC tree 内同请求 memo

/**
 * 服务端获取当前请求的 access_token。
 * - 同请求多次调用（一个 RSC 树 / 一个 Server Action 内）只触发一次 /auth/refresh
 * - 无 cookie / refresh 失效 → 返 null（调用方决定 redirect /login 或抛 UnauthenticatedError）
 */
export const getServerAccessToken = cache(async (): Promise<string | null> => { ... });
```

```typescript
// app/src/lib/server-http-client.ts
import { getServerAccessToken } from "./server-auth";
import { ApiError, UnauthenticatedError } from "@/services/http-client";

export async function serverApiFetch<T>(path: string, options?: RequestOptions): Promise<T>;
export const serverApiGet, serverApiPost, serverApiPatch, serverApiDelete;
// 401 不自动 retry（refresh 失败已在 getServerAccessToken 处理 / Server 端无第二次机会）
```

### 引用方

- **Server Actions** (`app/src/actions/*.ts`)：`"use server"` / 全部走 `serverApiPost/Patch/Delete` + `getServerAccessToken`
- **Server Components 数据 fetch** (`app/src/lib/*-data.ts`)：异步 server function / 走 `serverApiGet`
- **Client Components**（pages with `"use client"` / 含 form）：仍走 `services/http-client.ts`（spec 06 §2 子片 1 / §2 子片 2 已立）

### 实施清单（子片 3a 起）

- [ ] `app/src/lib/server-auth.ts`（~30 行 + tests）
- [ ] `app/src/lib/server-http-client.ts`（~60 行 + tests）
- [ ] 子片 3a-3c-4 各业务页面 / actions / lib data 按引用方分类逐个改造
- [ ] eslint ignore 渐进还债（同 spec 06 §2 范式）
- [ ] CI guard：Phase 2.3 上线前补「Server-only fetch 不得 import `services/http-client.ts` / Client 组件不得 import `lib/server-*.ts`」lint 规则（防层级混淆）

### 3-5 月后果

- ✅ 客户端 + 服务端 access 通道分离 / 安全模型清晰 / 故障域独立
- ✅ Prism SSR 范式继承零冲突（Server Components + Server Actions 仍是主范式）
- ✅ Phase 2.3 性能优化空间充足（per-request access cache / cookie burst / P2 HMAC 升级 / 多档可选）
- ❌ 每 Server Action / RSC 数据 fetch +80-150ms refresh hop（用户感知 typically 看不出 / cache 优化空间充足）

---

## §4 后续条目占位

前端规约后续如需补（lint 规则 / 路由约定 / state 管理 / error boundary 等）→ 本文件继续 §4 §5 加 / 防 spec 文件爆炸。

---

last_updated: 2026-05-09（§3 SSR auth 通道沉淀 / 子片 3a 启动期）
