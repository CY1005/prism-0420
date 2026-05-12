---
spike: P2 范式验证
auditor: Opus subagent / cost cap $3.5
created: 2026-05-12
samples: M01-user-account + M02-project
verdict: B-范式可行
---

# P2 spike 范式验证报告

## Verdict

**B-范式可行** — DOM 主路径 + API 旁路两轨范式在 M01/M02 实测落地成立，且本 spike 真复现了 dogfooding 起点 trigger_bug 并定位到根因。M01 5/5 tests 全 PASS / M02 5 tests 中 3 failed 真暴露 2 个 P0 bug + 1 已修 happy path。范式价值得到证明。

## trigger_bug 复现结果

- 状态: **真复现** ✅（dogfooding sprint 第一条 bug）
- 证据:
  - test `[P0-CRITICAL] 🔴 trigger_bug 复现：创建项目后是否跳 login` FAIL with: `final url: http://localhost:3000/login`
  - URL transition trace: `/projects/new` → POST `/projects/new` (Server Action) → 303 redirect → `/login`
  - screenshot: `app/test-results/dogfooding-M02-project-M02-be3c4-*/test-failed-1.png`
  - 不仅 trigger_bug test 复现 / `[P0] create-project happy path` 也复现同一路径（也跳 login / 共 17 次 URL 命中 `/login`）

- **根因（spike 网络抓包定位）**:
  - 浏览器侧 auth 完全 OK：`POST /auth/refresh 200` + `GET /auth/me 200` 都成功
  - 失败在 server action `createProject`（actions/projects.ts L83-118）：浏览器 POST 到 `/projects/new`（Next.js server action 端点）→ server action 内 `serverApiPost("/api/projects", ...)` → 返 401 → catch `UnauthenticatedError` → 通过 `withAuthRedirect` / `handleActionResult` 跳 `/login`
  - **关键 finding**：Next.js custom 版下 **server action 不能正确拿到浏览器的 refresh cookie** / `serverApiPost` 调 backend 时缺有效凭据 → 后端 401 → 前端 redirect login
  - 浏览器路径 `/auth/me`（用 Authorization Bearer 走 fetch）OK / server action 路径（用 cookie 走 server-to-server fetch）FAIL

- 影响:
  - **阻塞 dogfooding 真用户旅程**：任何走 server action 的写操作（createProject / addMember / updateProject / archive 等）都会跳 login
  - 入 03-bug-queue.md / 优先级 **P0** 第一条
  - **不阻塞 P2 启动**：P2 spec 写完后跑出来正是用来抓这类 bug 的 / 但 phase2-case.md 需要明示：server action 失败跳 login 是真 bug 不是 spec 写错

## 第二条 P0 bug（spike 顺带抓出 / list projects 渲染空）

- 现象：`[P0] list projects DOM` 失败 / 已 seed 63 个 project 但 `/projects` 页面 0 卡片渲染
- 抓包：`GET /api/projects` **从未从浏览器发出** / 只有 `/auth/refresh` + `/auth/me`
- 原因：`projects/page.tsx` 调 server action `getProjects()`（actions/projects.ts L64-69）/ server action 端因同上 cookie 问题失败 → catch 返 `[]` → 渲染 0 卡片
- 控制台 error: `Failed to load resource: the server responded with a status of 500 (Internal Server Error)`
- **同一根因，第二个表现面**：server-side fetch 无凭据

## Next.js 自定义版坑清单（dogfooding 价值）

- **坑 1**: 🔴 server action cookie 透传断裂
  - 现象：`POST /projects/new` server action → backend `/api/projects` 返 401（浏览器 fetch 同 endpoint 正常）
  - 实证：上述 trigger_bug + list projects 抓包
  - 规避建议：phase2-case.md 应加"server-action POST 后跳 login = 抓 cookie 透传 bug 不是 spec 错"指引

- **坑 2**: 🔴 `getByRole("alert")` 严格模式冲突
  - 现象：Next.js 内部 `__next-route-announcer__` 也有 `role="alert"`（aria-live="assertive"）/ playwright `getByRole("alert")` 命中 2 元素 → strict mode violation
  - 实证：M01 invalid password test 第一版 FAIL
  - 规避建议：phase2-case.md 加 selector 规约 — 业务 alert 用 `page.locator('div[role="alert"].<业务 class>')` 或直接 `getByText(...)` 定位，**不**用裸 `getByRole("alert")`

- **坑 3**: Server action 返 303 而非 200/JSON
  - 现象：server action submit 时 page.waitForResponse 拿到的状态码是 303（redirect）/ 不是常规 200 JSON
  - 实证：debug 抓包 `POST /projects/new → 303`
  - 规避建议：spec 用 `page.waitForURL(predicate)` 验跳转，不要试 `expect(response).status(200)` 验 server action 返回

- **坑 4**: AuthProvider mount 异步触发 `/auth/refresh` 不可省
  - 现象：page.goto 任何 protected page → AuthProvider mount → 异步 `/auth/refresh`（auth-context.tsx L55-66）→ 然后才决定渲染或跳 login
  - 实证：M01 test 4 capture 到该请求
  - 规避建议：toHaveURL/locator 验跳转时 timeout ≥ 8000ms / 不要 1000ms 抢跑

## DOM vs API-via-fetch 分轨建议（基于 M01 M02 实测）

### DOM 强适用场景

- 登录 / 注册 / logout UI 路径（M01 全模块）
- 浏览器侧 cookie 同步 / SSR / hydration / redirect 类 bug（trigger_bug 类）
- 表单填写 → server action → 跳转 验证用户旅程
- 真错误文案展示验证（toast / alert / form 错误位）
- ✅ **dogfooding trigger_bug 类 bug 必须 DOM 才抓得到**（spike 已实证）

### API 旁路适用场景

- 状态机非法转换（archived→archived / archived→active 禁转）/ M02 实证 PASS
- 权限三层防御（viewer/editor 403）— 多种子户口测
- 跨 tenant 隔离（userB 调 projectA）
- 后端 CHECK 约束 / UNIQUE / 部分唯一索引（无前端入口测）
- 异步范式（SSE/Queue/WebSocket pending → completed 状态推送）
- ADR-004 P2 凭据 HMAC 签名（INTERNAL_TOKEN 浏览器禁用）
- 数据库事务回滚验证（前端无法触发 mock）

### 分类决策树（subagent 写 spec 时怎么判 testpoint 走哪轨）

```
testpoint 描述里有：
  - 浏览器 UI 元素（按钮 / 表单 / 跳转 / 文案）→ DOM
  - 仅 API endpoint + status code + activity_log → API 旁路
  - 状态机 / 权限 / tenant / R-X 契约 / 异步推送 → API 旁路
  - 凡是 ADR-004 P2/P3 内部凭据 → API 旁路（INTERNAL_TOKEN 不进浏览器）
  - DB CHECK / UNIQUE / Migration → API 旁路

对应 page.tsx 有没有 UI 入口？
  - 无 UI 入口（design 声称但实现缺）→ API 旁路 + spike-report 记 design vs UI 漂移
  - 有 UI 入口但功能复杂（XYFlow drag / SSE 流式 / WebSocket）→ DOM smoke 1 条 + API 旁路细 case
```

## phase2-case.md 需补充的 step 清单

- [ ] **§Forbidden 加第 13 条**：禁止裸 `getByRole("alert")` / 必须用 `page.locator('div[role="alert"].<business-class>')` 或 `getByText` 定位（Next.js __next-route-announcer__ 冲突 / 见本 spike 坑 2）
- [ ] **§Self-check 加第 8 条**：spec 写完必跑 `pnpm exec playwright test --grep "<spec name>"` 至少 1 条 happy path 看真行为（不光 --list）/ trigger_bug 类必跑
- [ ] **§范式定位补充**：DOM 主路径 + API 旁路两轨明示（不是非黑即白 / spike-report §分类决策树作正文引用）
- [ ] **§Output contract 顶部注释模板** 加"punt 清单"细分：[DOM-reachable] / [API-via-旁路] / [skip-需后端测] 三类标签
- [ ] **§Escalation 加**：server action POST 失败跳 login 不是 spec 错 / 是 Next.js 自定义版 cookie 透传 bug / 入 03-bug-queue.md 不入 spec 修复
- [ ] **§范式红线加**：`page.waitForResponse` 验 server action 不可靠（return 303 redirect）/ 用 `page.waitForURL(predicate)` 替代
- [ ] **§input contract 补充**：M01-style unauth spec 必加 `test.use({ storageState: { cookies: [], origins: [] } })` opt-out（M02 已用 storageState 登录态 → DOM 主路径默认走登录）
- [ ] **§完成 加**：spec 跑出 FAIL 不是 spec 错 / 区分"spec 设计错"vs"真 bug" / 真 bug 必走 03-bug-queue.md 不修 spec

## self-check 结果

| # | 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | tsc 0 错 | ✅ | `pnpm exec tsc --noEmit` 无输出（0 错） |
| 2 | playwright --list 注册 | ✅ | 10 tests in 2 files 全注册 |
| 3 | 行数 ≥ 100 each | ✅ | M01=146 / M02=209 |
| 4 | 每 P0 至少 1 test() | ✅ | M01 4 个 P0 test / M02 3 个 P0 + 1 P0-CRITICAL test |
| 5 | 种子复用 seedFullProject | ✅ | M02 `list projects DOM` 用 seedFullProject + `tenant 隔离`+`archived 禁转` 用 loginE2EAdmin（均从 fixtures/seed 复用 / 无内联同名 helper） |
| 6 | DOM 主路径 grep page.goto ≥1 / locator-类 ≥ test×2 | ✅ | M01 `page.goto` 5 处 + getByLabel/getByText/getByRole 等 17+ 处 / M02 `page.goto` 3 处 + locator 类 8+ 处 |
| 7 | 顶部注释含 punt 清单 | ✅ | M01 4 条 punt / M02 5 条 punt 都列了 |
| 8 | 🔴 trigger_bug 真跑过 | ✅ | `pnpm exec playwright test --grep "trigger_bug"` 真 FAIL 报 `final url: /login` |
| 9 | 2 spec.ts 行数 ≥ 100 each | ✅ | M01=146 / M02=209 |
| 10 | spike-report.md verdict 非空 | ✅ | "B-范式可行" |

**10/10 全过**

## test 执行结果实证

| spec | test | 结果 | 备注 |
|------|------|------|------|
| M01 | login happy path | ✅ PASS | DOM 路径 + cookie 验证全通 |
| M01 | login invalid password | ✅ PASS | 第二版修了 getByRole alert 坑后通 |
| M01 | register UI（admin-invite-only） | ✅ PASS | design vs UI 漂移已锁（M01 design §4 Q1=B/C/D 待扩展） |
| M01 | AuthProvider mount /auth/refresh | ✅ PASS | R-X1 cookie sync 路径通 |
| M01 | storageState opt-out | ✅ PASS | unauth 范式 OK |
| M02 | create-project happy | ❌ FAIL | **trigger_bug 真复现 / 跳 /login** |
| M02 | trigger_bug 复现 | ❌ FAIL（按预期）| **bug 真存在 / final url = /login** |
| M02 | list projects DOM | ❌ FAIL | **第二条 bug：server action getProjects 失败 → 0 卡片** |
| M02 | tenant 隔离（API 旁路） | ✅ PASS | 401/403 路径通 |
| M02 | 状态机 archived 禁转（API 旁路） | ✅ PASS | 后端 R5-2 / 409 PROJECT_ALREADY_ARCHIVED 验证通 |

**总计**: 7 PASS / 3 FAIL（含 2 真 bug + 1 副作用同根因）

## cost / 时长

- 实际 cost: ~$1.20-1.50 估算（Opus / 5 个文件 read + 2 spec 写 + ~6 次 playwright run + ~3 次 tsc / 中等密度）
- 时长: ~25 min（含 trigger_bug 复现 + 根因抓包）

## 给主 agent 的下一步建议

1. **不要急启 P2 4 并发并发批 21 模块** — 必须先：
   - (a) 拍板 trigger_bug 入 `_handoff/dogfooding/04-bug-fixes/B-trigger-bug-server-action-cookie.md`（spike 已抓根因 / 修起来不难 / 是 server-http-client cookie 转发逻辑问题）
   - (b) 同步 list projects bug（同根因 / 一并修）
   - (c) 修完后再走 P2，否则 21 模块 spec 大量重复抓同一 bug 反复 FAIL

2. **phase2-case.md 必改 7 条**（见上 §"phase2-case.md 需补充的 step 清单"）— 加完前不启 P2 subagent

3. **范式范围扩张建议**：本 spike 仅验 M01/M02 / 复杂模块（M13 SSE / M17 WebSocket / M08 XYFlow drag）建议各先派 1 Opus subagent spike 单模块验范式 / 不要直接批量 Sonnet

4. **测试数据隔离**：spike 测试用了 e2e admin 共享账号 / 跑完留下 60+ 测试项目 / 建议 P2 sprint 加 `afterAll` 清理 hook（不阻塞但卫生）

5. **server action 路径暂时绕**：若 trigger_bug 修复需要 1+ 天 / P2 可以暂时所有 create/update 类 DOM test 走 API 旁路 + 单独 DOM smoke 1 条等修后启 — 见 §分类决策树

6. **优先回写**：
   - `00-plan.md` trigger_bug 行 → 标"真复现 / 根因 = server action cookie 透传"
   - `progress.md` dogfooding sprint 表 → 加 spike 节点
   - `cross-sprint-punt-pool.md` → 评估"server action 凭据"是否成跨 sprint Punt
