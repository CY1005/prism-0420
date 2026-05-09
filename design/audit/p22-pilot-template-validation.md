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
| 2 | (本次关闸) | auth flow + CORS + cookie 通道 + 1 e2e | $3-4 | 0 立修 / 4 punt | 0 / 5 punt |

**R1+R2 合并第 1 数据点结论**：spec 维度 0 P1（可关闸）/ reuse 维度 0 真 P1（R1 标的 2 P1 经复审降 P2，理由见 §3）/ 累计 P2 = 9 项（4 reuse + 5 spec）。

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

## §4 SR-P22 立规候选 sink（待 5 数据点后实证）

| 立规 ID | 描述 | 立规时机 |
|---------|------|----------|
| SR-P22-1 | feedback_decision_layering 自检第 4 问（已即时落） | ✅ 已立 |
| SR-P22-2 | feedback_subagent_sprint §4 — 前端继承形态 R 范式适配（R1=1 Sonnet + R2=1 Opus 而非 R1=3 + R2=1）| 5 数据点后实证 sink |
| SR-P22-3 | feedback_decision_layering 反模式表 — prompt 块本身分层错误识破（如 cold-start prompt 自行扩 spec scope，本期 register 案例）| 子片 5 关闸前 sink |

## §5 元贡献（实证）

- **前端继承形态首次走通**：拷贝 130 文件 → 选择性删 next-auth/drizzle → 渐进改造 → 子片 1 codegen + 子片 2 auth flow 接通；为子片 3a-3c 业务页面改造范式提供模板。
- **eslint ignore 渐进还债范式**：子片 1 移 `services/http-client.ts` + `auth-token-store.ts` + `types/**`；子片 2 移 `services/auth.ts`（删）+ `contexts/auth-context.{tsx,test.tsx}`（新写）+ `lib/validators/auth.ts` + `app/login/**` + `app/register/**`。每改一文件 → 移除 ignore → eslint ✓ 才 commit；累计移除 N=11 项。
- **R 范式合并数据点 ROI**：子片 1 仅工具链（http-client mock 充分）/ 子片 2 真用 endpoint（cookie + CORS + e2e）；合并跑使 R2 spec 验证有真锚点（schema 同步 / cookie 通道 / CORS 配置全字面对照），ROI 显著高于子片 1 单独跑。

---

last_updated: 2026-05-09
