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

---

## §3 后续条目占位

前端规约后续如需补（lint 规则 / 路由约定 / state 管理 / error boundary 等）→ 本文件继续 §3 §4 加 / 防 spec 文件爆炸。

---

last_updated: 2026-05-09
