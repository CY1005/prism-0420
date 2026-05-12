# P2 case subagent prompt — 两轨范式（DOM 主路径 + API 旁路）

> 启动方式：主 agent 在 prism-0420 根目录派 Sonnet subagent / 跑 1 个模块。复杂模块（M13 SSE / M17 AI 异步 / M18 search / M08 XYFlow drag / _cross-cutting）各先派 1 Opus spike 验范式后再批量。

---

## Role
P2-case / Sonnet（复杂模块 Opus）/ 单模块 playwright e2e spec 生成 / **两轨范式（DOM 主路径 + API 旁路）**

## Cost cap
$1.5（超即 commit 当前进度 + 退出 / 不无限跑）/ Opus escalate cap $3

## 范式定位（开工前必读 / 决定写法路径）

**dogfooding sprint 选择两轨范式**（CY 拍板 / spike 实证可行 / 不是非黑即白）：

### 轨 1：DOM 主路径（page.goto + locator + 真浏览器）

走真用户旅程：登录 / 注册 / logout UI / 表单填写 → server action → 跳转 / 浏览器 cookie 同步 / SSR / hydration / redirect 类 bug 验证 / 真错误文案展示 / dogfooding trigger_bug 类 bug 必须 DOM 才能抓到。

### 轨 2：API 旁路（request fixture 直接打 backend）

走 backend-only P0：状态机非法转换（archived → archived 禁转）/ 权限三层防御（viewer/editor 403）/ 跨 tenant 隔离 / 后端 CHECK / UNIQUE / 部分唯一索引 / 异步范式（SSE/Queue/WebSocket 状态推送）/ ADR-004 P2 凭据 HMAC（INTERNAL_TOKEN 浏览器禁用）/ DB 事务回滚验证。

### 分类决策树（subagent 写 spec 时怎么判 testpoint 走哪轨 / spike-report §"分类决策树"权威）

```
testpoint 描述里有：
  - 浏览器 UI 元素（按钮 / 表单 / 跳转 / 文案）→ DOM
  - 仅 API endpoint + status code + activity_log → API 旁路
  - 状态机 / 权限 / tenant / R-X 契约 / 异步推送 → API 旁路
  - 凡是 ADR-004 P2/P3 内部凭据 → API 旁路（INTERNAL_TOKEN 不进浏览器）
  - DB CHECK / UNIQUE / Migration → API 旁路

对应 page.tsx 有没有 UI 入口？
  - 无 UI 入口（design 声称但实现缺）→ API 旁路 + 报 escalation（design vs UI 漂移 / dogfooding 价值 / design-audit candidate）
  - 有 UI 入口但功能复杂（XYFlow drag / SSE 流式 / WebSocket）→ DOM smoke 1 条 + API 旁路细 case
  - 有 UI 入口 + 功能简单 → DOM 主路径 + API 旁路兜底（如验 activity_log / backend state）
```

### 实证 ref（必读 / 不读则范式偏）

- `_handoff/dogfooding/audit/p2-spike-report.md` §"DOM 强适用场景" / §"API 旁路适用场景" / §"分类决策树" / §"Next.js 自定义版坑清单 §坑 1-4"
- `app/e2e/dogfooding/M01-user-account.spec.ts`（DOM 主路径 pilot / 5/5 PASS 实证）
- `app/e2e/dogfooding/M02-project.spec.ts`（两轨混合 pilot / DOM 3 条 + API 旁路 2 条 / trigger_bug 真抓到）

## Input contract（开工前 ls + read / 缺任一中止）

### 必读 testpoint 输入
1. `_handoff/dogfooding/01-testpoints/M<NN>-<short>.md`（本模块 testpoint / 主输入）
2. `_handoff/dogfooding/audit/p1-p2-gate-finding.md`（如存在 / 主 agent 已修 P0 finding / 仍含 P1/P2 关注事项）

### 必读范式输入
3. **第一步穷举**：`cd app/ && ls e2e/*.spec.ts` 列全 10 个现有 spec
4. 全读 `app/e2e/fixtures/seed.ts`（seedFullProject 等 helper / **禁止内联同名**）
5. 全读 `app/e2e/global-setup.ts`（storageState login 范式）
6. 全读 `app/playwright.config.ts`（baseURL / workers: 1 / fullyParallel: false / unauth opt-out 语法）
7. 抽读 ≥2 个现有 spec（看 API 路径范式 / 学 fixture 用法但**不抄 API 范式**）

### 必读业务输入
8. `design/02-modules/M<NN>/00-design.md`（按需 grep / 重点 §1 业务 §4 状态机 §7 API §8 权限 §10 activity_log）
9. **前端 page**：`app/src/app/<path>/page.tsx`（对应本模块 UI 入口 / 见下表）
10. `design/00-architecture/01-PRD.md`（PRD F<NN> 验收条件 AC）
11. **`app/CLAUDE.md` + `app/AGENTS.md`**（🔴 Next.js 是定制版警告 / breaking changes / 必读）
12. `_handoff/dogfooding/audit/p2-spike-report.md` §"Next.js 自定义版坑清单"（4 坑 / 范式红线源头 / 不读 = 重蹈覆辙）

### 模块 → 前端 page 路径对照（M01-M20）

| Module | 前端 page | 说明 |
|--------|-----------|------|
| M01 user-account | `app/src/app/login/page.tsx` + `app/src/app/register/page.tsx` | auth 入口 / unauth opt-out 必加 |
| M02 project | `app/src/app/projects/page.tsx` + `app/src/app/projects/new/page.tsx` + `app/src/app/projects/[projectId]/page.tsx` | 列表+新建+详情 |
| M03 module-tree | `app/src/app/projects/[projectId]/page.tsx` + `modules/[moduleId]/page.tsx` + `workspace.tsx` | 节点树 UI / 详情 |
| M04 feature-archive | `app/src/app/projects/[projectId]/features/[featureId]/page.tsx` + `app/src/app/feature/page.tsx` + `workspace.tsx` archive 操作 | 归档功能 |
| M05 version-timeline | `app/src/app/projects/[projectId]/page.tsx` + `workspace.tsx`（timeline 区域） | 时间线 |
| M06 competitor | `app/src/app/projects/[projectId]/product-lines/[plId]/page.tsx` + `workspace.tsx`（competitor 区域） | 竞品 |
| M07 issue | `app/src/app/projects/[projectId]/issues/page.tsx` | 问题列表 |
| M08 module-relation | `app/src/app/projects/[projectId]/relation-graph/page.tsx` | XYFlow 图 / drag 复杂 |
| M10 overview | `app/src/app/projects/[projectId]/overview/page.tsx` | 概览 |
| M11 cold-start | `app/src/app/projects/[projectId]/page.tsx` 首次创建路径 + `templates/page.tsx` | 冷启动流程 |
| M12 comparison | `app/src/app/projects/[projectId]/comparison/page.tsx` | 对比 |
| M13 requirement-analysis | `app/src/app/projects/[projectId]/analysis/page.tsx` | SSE 流式 / 复杂 |
| M14 industry-news | `app/src/app/projects/[projectId]/page.tsx` + `workspace.tsx`（news 区域） | 行业新闻 |
| M15 activity-stream | `app/src/app/projects/[projectId]/page.tsx` + `workspace.tsx`（activity 侧栏） | 活动流 |
| M16 ai-snapshot | `app/src/app/projects/[projectId]/workspace.tsx`（AI 快照按钮 / Dialog） | AI 快照 |
| M17 ai-import | `app/src/app/projects/[projectId]/import/page.tsx` | AI 导入 / WebSocket 进度 |
| M18 semantic-search | `app/src/app/projects/[projectId]/search/page.tsx` | 语义搜索 |
| M19 import-export | `app/src/app/projects/[projectId]/import/page.tsx` + 导出按钮 | 导入导出 |
| M20 team | `app/src/app/teams/page.tsx` + `app/src/app/teams/new/page.tsx` + `app/src/app/teams/[teamId]/page.tsx` | 团队 |
| _cross-cutting | 全部 page（auth flow / 跨 tab / 网络 / 权限三层 / mobile） | 跨模块视角 |

> **重要**：上表是 grep 出来的真实路径，但**业务区域可能在 `workspace.tsx` 子组件**而非顶层 page.tsx。subagent 第一步：`grep -l "<模块关键词>" app/src/app/projects/[projectId]/*.tsx` 确认真实 UI 位置 / 找不到→Escalation 报主 agent。

> **不许跳 page.tsx**：找不到对应 page 直接中止上报主 agent（不是所有 testpoint 都能 DOM 化 / 仅 backend 路径需主 agent 决策）。

## Output contract

写入 `app/e2e/dogfooding/M<NN>-<short>.spec.ts`：

```typescript
import { test, expect } from "@playwright/test";

import { seedFullProject, loginE2EAdmin } from "../fixtures/seed";

// M<NN> <模块中文名> dogfooding spec
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M<NN>-<short>.md
// 覆盖（按分类决策树拆三类标签）:
//   [DOM-reachable]    N 条  → 走 page.goto + locator
//   [API-via-旁路]     M 条  → 走 request fixture（无 UI 入口 / backend-only / ADR-004 P2 凭据）
//   [skip-N/A]         K 条  → punt 下次 sprint（需 fixture 缺失 / 复杂度超 sprint 范围）
//
// punt 清单（必写 / 无 punt 也写"无 punt"）:
//   - [P0/P1] [skip-N/A] testpoint X — 推迟理由（如：WebSocket 范式未 spike / XYFlow drag 复杂 / mobile 浏览器外）
//   - ...
//
// design vs UI 漂移（dogfooding 价值 / design-audit candidate / 报主 agent 入 audit/）:
//   - [P0] testpoint Y — design §N 声称有 X UI 但 page.tsx 无 / 走 API 旁路 + 标 design-gap

// unauth spec 必加（M01 login/register）:
// test.use({ storageState: { cookies: [], origins: [] } });

test.describe("M<NN> <模块中文名> dogfooding", () => {
  test("[P0] <testpoint 内容> — DOM 路径", async ({ page, request }) => {
    // 1. 种子（API 路径，仅 setup）
    const seeded = await seedFullProject(request);

    // 2. DOM 路径（page.goto + locator + 真浏览器）
    await page.goto(`/projects/${seeded.project.id}`);
    await expect(page).toHaveURL(/\/projects\//);  // 关键：waitForURL/toHaveURL 验跳转
    await page.getByRole("button", { name: /创建|新建/ }).click();
    await page.getByLabel(/名称/).fill("Test Item");
    await page.getByRole("button", { name: /提交|保存/ }).click();
    await expect(page.getByText("Test Item")).toBeVisible();

    // 3. 后端断言兜底（API 验状态 / 仅 DOM 不便处）
    // const res = await request.get(`${API_BASE}/api/.../activity-stream/...`);
    // expect((await res.json()).events).toContainEqual(expect.objectContaining({ action_type: "..." }));
  });

  // ... 其余 P0/P1 testpoint
});
```

## Self-check（缺任一 → 重做）

1. **tsc 通过**：`cd app/ && pnpm exec tsc --noEmit` 0 错（**必跑**）
2. **playwright --list 注册**：`cd app/ && pnpm exec playwright test --list app/e2e/dogfooding/M<NN>-*.spec.ts` 全注册成功 / 无 syntax error
3. **行数 ≥ 模块 P0 数 × 0.5**（粗保单不空 / e.g. M01 P0=45 → spec ≥ 22 行业务断言；不算 import + 注释）
4. **每 P0 至少 1 test()**：grep `test(` 数 ≥ 模块 P0 testpoint 覆盖数（顶部注释 punt 清单的不计）
5. **种子复用 seedFullProject / loginE2EAdmin**：grep 至少 1 处 / 禁止内联 `request.post("/auth/login")` 自造 helper
6. **轨道分配合理**：grep `page.goto` ≥ 1 处（DOM 轨）+ grep `request.(get|post|put|delete)` ≥ 0 处（API 旁路 / 仅当有 [API-via-旁路] 标签时）/ 总 locator 类（getByRole|getByLabel|getByText|locator(）≥ DOM test 数 × 2
7. **顶部注释含三类标签 punt 清单**：[DOM-reachable] / [API-via-旁路] / [skip-N/A] 三标签必齐 / 即使 0 punt 也写"无 punt"防漂走
8. **🔴 真跑 happy path**：spec 写完必跑 `cd app/ && pnpm exec playwright test e2e/dogfooding/M<NN>-*.spec.ts --grep "happy"` 至少 1 条 happy path / 看真实行为不光 --list 注册（spike 实证：trigger_bug 类只有真跑才暴露 / [[feedback_subagent_sprint]] §2 T2 dry-run 测设计不测连通 / 本 sprint 必跑 ≥1 真证据）

## Forbidden（违反 → 重做）

### 工程红线
- ❌ 内联 `loginE2EAdmin` / `seedFullProject` 复制版本（[[feedback_subagent_sprint]] §1 闸门 / 禁同名重复 helper）
- ❌ 纯 API 路径 spec（无 `page.goto`）当成模块主交付（DOM-reachable testpoint 都给走 API 是范式违规 / API 旁路只 cover backend-only）
- ❌ 凭印象写 selector（`getByText("xxx")` 但 page.tsx 无该文本）/ 必须先读 page.tsx 确认 UI 文案
- ❌ try/catch 静默吞错（[[feedback_subagent_sprint]] §2 T1）/ assertion 失败必让 test 报错
- ❌ skip / fixme / xfail（除非 testpoint 明文 punt 且写顶部注释三标签 [skip-N/A]）
- ❌ `test.use({ storageState: ... })` 漏给 unauth spec（M01 login/register 必加 opt-out / 不然进 page 就被 auth 重定向）

### 范式红线（spike-report §"Next.js 自定义版坑清单"来源）
- ❌ 把 testpoint 描述当 assertion 文本（"创建项目跳转项目详情页" ≠ test 名 / test 名要写具体动作）
- ❌ 用 `waitForTimeout(N)` 替代 `expect().toBeVisible({ timeout })` / hard sleep 是 flaky 信号
- ❌ 写完 spec 不实际跑 tsc / playwright --list / 至少 1 条真 happy path 就 DONE（[[feedback_subagent_sprint]] §2 T2+T5 + 本 prompt §Self-check 第 8 条）
- ❌ 🔴 **裸 `getByRole("alert")`**（Next.js 内部 `__next-route-announcer__` 也有 `role="alert"` / strict mode 冲突 / spike 坑 2 实证）→ 必须用 `page.locator('div[role="alert"].<business-class>')` 或 `getByText(...)` 定位业务 alert
- ❌ 🔴 **`page.waitForResponse` 验 server action 返回**（server action 返 303 redirect 不是 200 JSON / spike 坑 3 实证）→ 必须用 `page.waitForURL(predicate)` 或 `expect(page).toHaveURL(/pattern/)` 验跳转
- ❌ AuthProvider mount 路径用 ≤1000ms timeout（异步 `/auth/refresh` 需要时间 / spike 坑 4 实证）→ 所有 protected page 的 toHaveURL/locator 等跳转判定必须 `{ timeout: 8000 }` 以上

### 范围红线
- ❌ 写跨模块 testpoint 到本 spec（属 `_cross-cutting.md` 对应 spec）
- ❌ 编造 testpoint 文件没的 case（只能 spec testpoint 已列 / 漏的报主 agent 别自加）

## Escalation（主动报主 agent）

- ⚠️ 模块对应的前端 page.tsx 不存在 / UI 入口不可达（说明 frontend 缺实现 / 不阻塞但报，记 design-audit candidate 进 audit/）
- ⚠️ ≥3 条 P0 testpoint 标 [API-via-旁路]（说明 design vs UI 漂移多 / 不是 spec 错而是 dogfooding 真发现 / 报主 agent 记 audit/<M-name>-design-gap.md）
- ⚠️ 模块复杂度高（SSE / WebSocket / XYFlow drag / iframe）→ 主 agent 决策 escalate Opus / 复杂模块单 spike 验范式
- ⚠️ playwright --list 失败但 tsc 过 → playwright config / fixture 引用错 / 报主 agent
- ⚠️ cost 接近 $1.5（Sonnet）/ $3（Opus）→ commit 当前进度 + 上报，不无限跑

### 🔴 真 bug vs spec 错的区分（spike 实证 / dogfooding 核心价值）

- ⚠️ **server action POST 后跳 `/login`** = 这是真 bug 不是 spec 写错（spike trigger_bug 抓到 / 根因 = Next.js 自定义版 cookie 透传断裂 / 已立 `04-bug-fixes/B-trigger-bug-server-action-cookie/`）
- ⚠️ **`GET /api/projects` 浏览器抓包看不到** = server action getProjects 同根因失败 / 标真 bug 不修 spec
- ⚠️ **任何 protected page goto 后被 redirect 到 `/login`** 而 AuthProvider 已 mount → 同根因系列 / 标记真 bug 不修 spec
- ⚠️ DOM selector 找不到 / 文案不对 → 先 grep page.tsx 确认 / 真不存在则 design-gap（candidate）/ 不是 spec 错

**规则**：spec 写完跑出 FAIL → 必判定"spec 设计错"（locator 错 / 时序错 / 时间窗短）还是"真 bug"（功能不工作 / 数据丢 / 跳转错）。**真 bug 必走 `_handoff/dogfooding/03-bug-queue.md`**（追加新行 / status=OPEN / 等 P4 入），**不修 spec**。spec 错则自修 + 重跑。

> 不区分 = 把真 bug 当 spec 错 fix 调 → dogfooding 失效。

## 完成

不 commit（主 agent 收齐批内 N 个 spec 后单批 commit `dogfooding P2/batch<N> cases — M<NN> + M<NN> + ...`）。

返主 agent 报告（4 态 / [[feedback_four_state_report]]）：

```
status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
模块: M<NN>
spec 文件: app/e2e/dogfooding/M<NN>-<short>.spec.ts (N 行)
test() 数: M
testpoint 覆盖分轨: [DOM] N / [API-via-旁路] M / [skip] K（顶部三标签 punt 清单需对齐）
self-check: tsc ✅ / --list ✅ / 真跑 happy ✅ / 全 8 项过
端到端 trace: 真跑 ≥1 happy path 的 playwright 输出（PASS / FAIL + URL trace）
真 bug 入队（如有）: 03-bug-queue.md 追加 N 行（B-id / 现象 / 来源 / status=OPEN）
escalation（如有）: <内容 / design-gap candidate / 复杂度 escalate Opus 建议>
cost: $X.XX
```

### 端到端 trace 红线

`[[feedback_subagent_sprint]]` §2 T4+T5：DONE 必含端到端 trace + 真证据。本 sprint **要求**：
- ✅ `pnpm exec tsc --noEmit` 0 错
- ✅ `pnpm exec playwright test --list <spec>` 注册成功
- ✅ **`pnpm exec playwright test <spec> --grep "happy"` 至少 1 条真跑**（不光 --list / spike 实证：trigger_bug 类只有真跑才暴露）
- ✅ 顶部注释三标签 punt 清单写齐
- ✅ 真 bug 入 03-bug-queue.md（不修 spec）

### 真 bug 入队模板（追加到 `_handoff/dogfooding/03-bug-queue.md` 末尾表格）

```
| B-P2-M<NN>-<short> | <现象一句话> | P2 spec M<NN> dogfooding 2026-MM-DD | OPEN / 待 P4 入 |
```

不创建 04-bug-fixes/ 子目录（P4 fix subagent 期再建）/ 只入队等 P4。

---

## 启动 prompt 模板（拷给 subagent）

```
你是 P2-case subagent / 任务：为 prism-0420 模块 M<NN> 生成 playwright e2e spec（两轨范式 DOM 主路径 + API 旁路）。

cost cap $1.5（Sonnet）/ $3（Opus 升级版）。

按 _handoff/dogfooding/prompts/phase2-case.md 跑：
1. 全读 input contract 12 项 / 第 3 项 ls 穷举现有 spec / 第 11+12 项 Next.js 自定义版坑必读
2. 学 fixtures/seed.ts + global-setup.ts 范式 / 禁止内联同名 helper
3. 学 app/e2e/dogfooding/M01-user-account.spec.ts + M02-project.spec.ts 实证 pilot（两轨混合 / spike 实证可行）
4. 按"分类决策树"给每条 testpoint 标 [DOM-reachable] / [API-via-旁路] / [skip-N/A]
5. 写 app/e2e/dogfooding/M<NN>-<short>.spec.ts（含顶部三标签 punt 清单 + design-gap candidate 段）
6. self-check 8 项（含 tsc + playwright --list + 真跑 ≥1 happy path）
7. forbidden 15+ 项（含 Next.js 4 坑红线 / getByRole alert / waitForResponse / AuthProvider mount timeout）
8. 真 bug 入 03-bug-queue.md / 不修 spec
9. 完成不 commit / 返主 agent 4 态报告

当前模块：M<NN>=<填> / short-name=<填> / 前端 page=<对照表查 + grep workspace.tsx 子组件位置>
```
