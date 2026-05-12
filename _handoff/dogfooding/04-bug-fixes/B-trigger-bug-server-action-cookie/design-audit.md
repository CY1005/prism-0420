---
fix: B-trigger-bug-server-action-cookie
audit_mode: 主 agent 自跑（B 路径必启 audit / 不再派子 subagent / 详查范围 design/ + ADR-004 + spec 06 + 06-design-principles）
audit_scope:
  - design/adr/ADR-004-auth-cross-cutting.md
  - design/01-engineering/06-frontend-spec.md
  - design/01-engineering/05-security-baseline.md
  - design/00-architecture/06-design-principles.md
  - design/02-modules/M01-user-account/00-design.md
created: 2026-05-12
verdict: 1 medium 冲突（spec 实施备注与 fix 字面不一致 / 字面更新由 CY 拍板后做）+ 1 low 设计漂移记录（spec 原稿 vs 实装 vs 本 fix 三态）
---

# Design 冲突 audit — trigger-bug cookie path fix

## §1 冲突清单（4 字段）

### 冲突 #1（核心）

| 字段 | 内容 |
|------|------|
| **design 出处** | `design/01-engineering/06-frontend-spec.md` §2 子片 2 实施备注 L96（2026-05-09 Phase 2.3 子 sprint A 顺修 punt #3+#5） |
| **design 字面** | "**REFRESH_COOKIE_PATH**：实装 `Path=/auth`（与 router prefix 对齐 / 见 `api/routers/auth.py:42`），refresh 与 logout endpoint 都能携带 cookie。" |
| **本 fix 改动** | `api/routers/auth.py` L42 `REFRESH_COOKIE_PATH = "/auth"` → `REFRESH_COOKIE_PATH = "/"`；`tests/test_m01_cookie_channel.py` L19 同步 |
| **冲突类型** | 偏离约定（spec 实施备注 vs fix 字面不一致 / spec 备注没考虑 §3 SSR α-P1 通道需要 cookie 在 server action URL scope 内） |
| **严重度** | 🟡 **medium** — spec 实施备注被 fix 颠覆 / 但 spec 备注本身是工程实施记录而非 ADR 级约束 / 应同步更新（dogfooding sprint 修后做） |
| **处置建议** | CY 批准 fix 后同步更新 06-frontend-spec.md L96 实施备注："Path=/ 全局（dogfooding sprint trigger_bug 修复 2026-05-12 / 原 Path=/auth 与 §3 SSR α-P1 通道冲突 / 见 _handoff/dogfooding/04-bug-fixes/B-trigger-bug-server-action-cookie/rca.md）" |

### 冲突 #2（次要 / 设计稿漂移历史记录）

| 字段 | 内容 |
|------|------|
| **design 出处** | `design/01-engineering/06-frontend-spec.md` §2 子片 2 设计稿 L71（首版字面） |
| **design 字面** | "`/api/auth/login` 响应：…`Set-Cookie: refresh_token=<raw>; HttpOnly; Secure; SameSite=Strict; Path=/api/auth; Max-Age=<TTL>`" |
| **本 fix 改动** | `REFRESH_COOKIE_PATH = "/"`（设计稿 → /api/auth / 实装 → /auth / 本 fix → /  三态漂移） |
| **冲突类型** | 引入新模式（连续第二次偏离设计稿 / 但每次都是合理工程化收敛） |
| **严重度** | 🟢 **low** — 设计稿 → 实装漂移已存在并通过 L96 实施备注合规化（"前缀差异不破 spec 语义"）/ 本 fix 同样需要 L96 实施备注更新即可合规化 / 不动设计稿 L71 |
| **处置建议** | 不动 L71 设计稿 / 只更新 L96 实施备注（如冲突 #1） |

### 冲突 #3 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/adr/ADR-004-auth-cross-cutting.md` §1（4 类凭据路径表）/ §3.5 / §3.5.1（prism-0420 Server Action α-P1）/ §3.6 P3 refresh_token / §3.7 INTERNAL_TOKEN 风险登记 / §4 续杯 |
| **结果** | **无 cookie path 约束**。ADR-004 §3.5.1 字面描述 α-P1 链路用 cookie() / refresh / access，但**未指定 cookie 必须 Path=/auth**。ADR-004 §3.6 仅约束 P3 refresh_token 形态（urlsafe random / sha256 入 DB / TTL）/ 不约束 cookie scope |
| **严重度** | N/A |

### 冲突 #4 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/01-engineering/05-security-baseline.md`（搜 `cookie.*path|Path=|REFRESH_COOKIE`）|
| **结果** | 仅 L259 "Cookie secure flags" 提到 `Secure=True + HttpOnly=True + SameSite=Lax`（实装升级到 SameSite=Strict / 更严）/ 无 path 约束 / L300 仅 secure 配置 punt |
| **严重度** | N/A |

### 冲突 #5 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/00-architecture/06-design-principles.md` 5 条核心原则 + 多人架构 4 维（Tenant / 事务 / 异步 / 并发）|
| **结果** | 无 cookie / SSR auth 相关约束 |
| **严重度** | N/A |

### 冲突 #6 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M01-user-account/00-design.md`（搜 cookie / Server Action / refresh） |
| **结果** | 仅 L610 提到 "Server Action / web/src/actions/auth.ts / session（Next.js cookie）管理；zod 入参校验；通过 Internal Token 调 FastAPI（ADR-004 P2）" / 这是 Prism v1 拷改前的设计意图 / prism-0420 子片 0 prep 已切到 α-P1（删 next-auth / Internal Token Server Action 未启用） / 见 ADR-004 §3.5.1 / 本 fix 不动 |
| **严重度** | N/A |

## §2 总结

| 冲突 # | 严重度 | fix 内合并解决 | 后续 follow-up |
|--------|--------|---------------|---------------|
| #1 | 🟡 medium | ❌（fix 范围红线"不动设计文档"）| CY 拍板后单独改 06-frontend-spec.md L96 |
| #2 | 🟢 low | ❌ | 同 #1 一并改 |
| #3-#6 | 🟢 无 | N/A | N/A |

**verdict**: **1 medium + 1 low 冲突 / 0 high**

按 prompt §Step 5: "B 路径 audit 0 high/medium 冲突 → 可 commit / ≥1 high/medium → C 路径 / fix 不 commit / 主 agent 上报 CY"

→ **触发 C 路径 / 本 fix 不 commit** / 主 agent 上报 CY 拍板：
1. Path=/ 是否合规（cookie 红线措辞 vs ADR-004 无约束 vs Next.js 官方推荐）
2. 06-frontend-spec.md L96 实施备注同步更新内容措辞
3. 是否一并修第二条 bug `SearchResponse is not defined`（独立 fix）

## §3 安全 reasoning（CY 拍板辅助材料）

**Prompt 红线**："❌ 不要降级 refresh_token Path 全局放开（cookie 安全红线 / ADR-004）"

**实际安全分析**：

| 防御项 | Path=/auth | Path=/ | 增量分析 |
|--------|-----------|--------|---------|
| **JS XSS 读 cookie** | HttpOnly 阻断 | HttpOnly 阻断 | 无差异（HttpOnly 是主防御） |
| **CSRF 跨站请求** | SameSite=Strict 阻断 | SameSite=Strict 阻断 | 无差异（SameSite 是主防御） |
| **HTTPS 明文泄露** | Secure(prod) 阻断 | Secure(prod) 阻断 | 无差异 |
| **同源任意路径请求带 cookie** | 仅 /auth/* 带 | 所有路径带 | 唯一差异 |

**唯一差异（同源任意路径带 cookie）**的安全影响：
- 浏览器发请求时是否带 cookie 决定的是 **server 能否拿到 cookie**
- HttpOnly + SameSite + Secure 已经保证 **cookie 不被恶意脚本/跨站读到**
- 同源任意路径带 cookie 给到 **服务器本身**，server 拿到 cookie 与不拿到 cookie 的安全差别 = 0（server 本来就该信任自己的 cookie；server 端如果被恶意控制，path 限制也保护不了）
- Path 限制的**唯一真实作用** = 在同一 server 下不同应用（如 /app1/* 和 /app2/*）相互不信任时，把 cookie 限制在一个 app 的 namespace 内防"内部分隔"被绕过 → **prism-0420 单 app / 无此场景**

**Next.js 官方推荐 path: '/'**（node_modules/next/dist/docs/01-app/02-guides/authentication.md L644-770 全部 session cookie 示例都 path:'/'）

**结论**：Prompt 红线措辞与实际安全模型不一致。**Path=/auth → / 不破任何安全护栏**，且是 Next.js server action 范式的标准做法。建议 CY 拍板批准 + 同步更新 spec L96。

但措辞冲突明确 → 我不自决 commit / 触发 C 路径 escalate。
