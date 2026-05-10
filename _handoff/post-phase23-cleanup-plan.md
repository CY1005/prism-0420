---
title: Post-Phase-2.3 Cleanup Plan（4 Sprint 收尾）
status: living
owner: CY
created: 2026-05-10
last_updated: 2026-05-10 (**Sprint 1 完成 / 进入 Sprint 4（路由决策见 §下方）**)
purpose: Phase 2.3 PARTIAL 关闸后所有 punt 的清扫计划——不上线，把仓库做到"真闸门 5 全 ✅、所有 STILL_PUNT 高/中风险归零"
status_sprint1: ✅ DONE 2026-05-10 / commits dae2760→2e21b63 / 8 task 全清
status_sprint2: ⏸ 暂缓（需 backend+frontend 服务端运行才能验真 e2e 断言 / CY 在线时启动）
status_sprint3: ⏸ 阻塞（GH PAT 缺 workflow scope / CY 加 scope 后 5 min 推 ci.yml）
status_sprint4: ✅ 实质已完成（plan 撰写时 fresh_verification 失败 / 真相：4A 全 4 项 + 4C.1 + 4C.2 在 2026-05-09 M-CLEANUP sprint 已做完 commits 33b5759+aabde04+5c7783d / 4B 三项 #21+#23+#24 触发条件未到（A 类占位期残留 / 等 pgvector 真接通 + 真业务 path）/ 4C.3 #6 M07 detach 等 CY 拍）
routing_decision: 修正后 — Sprint 1 ✅ → Sprint 4 实质已完成 → 进入等 CY 状态（Sprint 2 启 server / Sprint 3 加 PAT scope / Sprint 4C.3 拍 detach A/B）

## 🔴 plan 撰写期 fresh_verification 失败说明

撰写本 plan 时凭 cross-sprint pool 行级 ⏳ 状态推断 Sprint 4 9 项可做，未读 pool §"2026-05-09 M-CLEANUP sprint 关闸 8 punt 关闭" 段字面写 "B 类 真漏洞 0 项（M-CLEANUP 已清完）"。

执行期 Sprint 1 完成后启动 Sprint 4A 第一条立刻 grep dimension_service.py 看到 IntegrityError handler 已在（commit aabde04 已修），触发 fresh_verification + 拉 git log 验证才知 Sprint 4 实质已被 2026-05-09 M-CLEANUP sprint 抢做。

立规候选：plan 撰写期不仅要读 punt 行级状态，更要读 sprint 关闸笔记的 "本 sprint 关闭项"段；punt pool 行级状态有滞后期。
methodology: superpowers:writing-plans + 本仓 R1+R2 范式 + decision_transparency A 模式
---

# Post-Phase-2.3 Cleanup Plan

> **冷启动 Claude 读这份**：先读本文件 → 再读 `_handoff/next-session.md` 看上一 session 状态 → 再读 `design/00-roadmap.md` 看真实进度。
>
> **执行节奏**：Sprint 1 → 2 → 3 → 4，按顺序串跑。每个 Sprint 完成后 commit + push + 更新本文件 status + 等 CY ack 再启动下一个。

**Goal**：清空 cross-sprint pool 三类 punt（A 后置债 / B-FOLLOW-UP / C-FOLLOW-UP）+ 模块级真漏洞 high/medium 9 项，让仓库进入"随时可上线但不上"的稳态。

**不做**：post-launch perf C 类 12 项（已 DEFER_TO_POST_LAUNCH，触发条件 = 真负载 P95 > 500ms / Phase 3 数据回流）。

**Tech Stack**：FastAPI + SQLAlchemy + Alembic + Next.js 14 + Playwright + pytest + vitest。

---

## CY 已拍决策（2026-05-10 启动）

| 决策 | 拍板 |
|------|------|
| Sprint 4 模块级真漏洞是否纳入本轮 | ✅ 纳入 |
| Sprint 1 P22-3c-6 ExportPayload 选项 | ✅ A — 补 `ExportResponse` Pydantic schema |
| PAT workflow scope 加的时机 | Sprint 2 完成后（不阻塞 1/2 / Sprint 3 启动前 5 min 人工） |

---

## 总览：依赖图

```
Sprint 1 C-FOLLOW-UP (前端基础债 8 项)
   │
   ├─ P22-3c-6 ExportPayload schema   ──┐
   ├─ P22-3c-2 result 类型统一            │
   ├─ P22-3c-5 findInTree 抽 lib          │
   ├─ P22-3c-3/4 命名规约                 │
   ├─ P22-3c-1 withAuthRedirect 复用      │
   ├─ P22-3c-7 logActivity no-op 清       │
   ├─ P22-3c-8 file-level eslint 锚       │
   └─ eslint ignore 渐进还债              │
                                          ▼
Sprint 2 B-FOLLOW-UP (集成 e2e 基础设施)
   ├─ DB seed fixture
   ├─ storageState login share
   ├─ e2e #2-#10 完整断言（9 个 skeleton → 真）
   ├─ pytest-benchmark + perf 1000 seed
   └─ R1+R2 第 7 数据点
                                          ▼
                  [CY 给 PAT 加 workflow scope (5 min)]
                                          ▼
Sprint 3 A 后置债 (CI 接通)
   ├─ push .github/workflows/ci.yml
   ├─ 接通 e2e job (service container)
   └─ 关闸门 5 §8.0 + §8.1 全 ✅
                                          ▼
Sprint 4 模块真漏洞 high/medium 9 项 (后端 / 独立)
   ├─ Mini-Sprint 4A: M04 dimension 集中
   ├─ Mini-Sprint 4B: M18 worker 真接 + cron + batch
   └─ Mini-Sprint 4C: 跨模块 race + write_event e2e
```

---

# Sprint 1 — C-FOLLOW-UP 前端基础债

**为什么最先**：result 类型 / 命名规约 / 工具函数是地基，先收口 e2e 才不会返工。

**估**：cost $2-3 / 0.5-1 天 / vitest 应保持 20 PASS / eslint 0 errors / 0 warnings。

**走 R1+R2**：1 Sonnet（reuse 复用扫描）+ 1 Opus（spec 字面合规 + 跨子片同根因漂移）→ 第 6 数据点。

**完成判据**：cross-sprint pool P22-3c-1~8 全 DONE / eslint ignore 表清空残留（保留必要 _ 项）/ vitest 20 PASS。

---

## Task 1.1: P22-3c-6 ExportPayload — 补 `ExportResponse` Pydantic schema（CY 已拍 A）

**Files:**
- Modify: `api/schemas/export.py`（新建或扩展）
- Modify: `api/routers/export.py`（response_model 加 ExportResponse）
- Modify: `app/src/lib/actions/export.ts`（替换 `ExportPayload = unknown`）
- Modify: `app/src/types/openapi.d.ts`（codegen 重跑）
- Test: `tests/api/test_export_response_schema.py`

- [ ] **Step 1: 写后端 schema 失败测试**

```python
def test_export_response_schema_typed(client, project_factory):
    project = project_factory()
    resp = client.get(f"/api/projects/{project.id}/export?format=md")
    assert resp.status_code == 200
    body = resp.json()
    # 字段名 + 类型必须可被 Pydantic 校验
    assert "format" in body
    assert "filename" in body
    assert "content" in body
    assert isinstance(body["content"], str)
```

- [ ] **Step 2: 验证测试失败** — `pytest tests/api/test_export_response_schema.py -v` → FAIL（response_model=None）

- [ ] **Step 3: 实装 ExportResponse**

```python
# api/schemas/export.py
from pydantic import BaseModel, Field

class ExportResponse(BaseModel):
    format: Literal["md", "pdf", "json"] = Field(..., description="导出格式")
    filename: str = Field(..., max_length=255)
    content: str = Field(..., description="导出内容（base64 for binary, raw for md/json）")
    mime_type: str
    size_bytes: int
```

- [ ] **Step 4: router 接 response_model**

```python
# api/routers/export.py
@router.get("/{project_id}/export", response_model=ExportResponse)
async def export_project(...): ...
```

- [ ] **Step 5: 跑测试** → PASS

- [ ] **Step 6: 重跑 openapi-typescript codegen**

```bash
cd /root/workspace/projects/prism-0420 && bash scripts/codegen-frontend.sh
```

- [ ] **Step 7: 前端替换 unknown**

```ts
// app/src/lib/actions/export.ts
import type { components } from "@/types/openapi"
type ExportResponse = components["schemas"]["ExportResponse"]

export async function exportProject(...): Promise<ActionResult<ExportResponse>> { ... }
```

- [ ] **Step 8: vitest 应 20 PASS / 跑 `pnpm vitest run`**

- [ ] **Step 9: Commit**

```bash
git add api/schemas/export.py api/routers/export.py app/src/lib/actions/export.ts \
        app/src/types/openapi.d.ts tests/api/test_export_response_schema.py
git commit -m "Sprint 1 P22-3c-6 — ExportResponse Pydantic schema 收口（A 模式 / consumer UI 字段保稳）"
```

---

## Task 1.2: P22-3c-2 result 类型统一（StatsResult ↔ ActionResult）

**Files:**
- Modify: `app/src/lib/actions/types.ts`（统一导出 ActionResult）
- Modify: `app/src/lib/actions/{stats,project-stats-proxy}.ts`（StatsResult → ActionResult）
- Modify: 所有 caller（grep `StatsResult<` 找出）

- [ ] **Step 1: grep StatsResult 全引用**

```bash
cd /root/workspace/projects/prism-0420/app && grep -rn "StatsResult<" src/
```

- [ ] **Step 2: 删 `StatsResult` 定义，统一用 `ActionResult<StatsData>`**

```ts
// app/src/lib/actions/types.ts —— 保留 ActionResult，删 StatsResult
export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string; code?: string }
```

- [ ] **Step 3: 修所有 caller 类型注解**（替换 `StatsResult<X>` → `ActionResult<X>`）

- [ ] **Step 4: vitest run** → 20 PASS

- [ ] **Step 5: Commit** `Sprint 1 P22-3c-2 — result 类型 StatsResult→ActionResult 统一`

---

## Task 1.3: P22-3c-5 findInTree 抽 `lib/tree-utils.ts`

**Files:**
- Create: `app/src/lib/tree-utils.ts`
- Modify: 三处 caller（grep `findInTree` / 见 audit §3c）

- [ ] **Step 1: 写工具函数 + unit test**

```ts
// app/src/lib/tree-utils.ts
export function findInTree<T extends { id: string; children?: T[] }>(
  nodes: T[],
  predicate: (node: T) => boolean
): T | null {
  for (const node of nodes) {
    if (predicate(node)) return node
    if (node.children) {
      const found = findInTree(node.children, predicate)
      if (found) return found
    }
  }
  return null
}
```

```ts
// app/src/lib/tree-utils.test.ts
describe("findInTree", () => {
  it("returns null for empty", () => expect(findInTree([], () => true)).toBeNull())
  it("matches root", () => { /* ... */ })
  it("matches nested", () => { /* ... */ })
})
```

- [ ] **Step 2: 替换 3 处重复实装**（actions/nodes.ts / actions/relations.ts / 等）

- [ ] **Step 3: vitest run** → 应 23 PASS（+3 新测）

- [ ] **Step 4: Commit** `Sprint 1 P22-3c-5 — findInTree 抽 lib/tree-utils.ts + 3 caller 收敛`

---

## Task 1.4: P22-3c-3 issues 命名前缀统一 + P22-3c-4 competitor-references 加资源前缀

**Files:**
- Modify: `app/src/lib/actions/issues.ts`（list* / get* 命名规约）
- Modify: `app/src/lib/actions/competitor-references.ts`（加资源前缀）
- Modify: 所有 caller

- [ ] **Step 1: 制定命名规约**（写注释到 actions/types.ts 顶部）

```
- 列表：list<Resource>(...)
- 单个：get<Resource>(id)
- 创建：create<Resource>(...)
- 更新：update<Resource>(id, ...)
- 删除：delete<Resource>(id)
- 资源前缀必须 = 后端 endpoint 主资源名（issue/competitorReference/...）
```

- [ ] **Step 2: 重命名 + caller 跟改**（IDE rename symbol）

- [ ] **Step 3: vitest + tsc 检查无破** → `pnpm vitest run && pnpm tsc --noEmit`

- [ ] **Step 4: Commit** `Sprint 1 P22-3c-3+4 — actions 命名规约统一（list/get/create/update/delete + 资源前缀）`

---

## Task 1.5: P22-3c-1 search/project-stats-proxy 复用 withAuthRedirect

**Files:**
- Modify: `app/src/lib/actions/search.ts`
- Modify: `app/src/lib/actions/project-stats-proxy.ts`

- [ ] **Step 1: grep 内联 redirect 模式**

```bash
grep -nE "redirect\(.login.\)" app/src/lib/actions/{search,project-stats-proxy}.ts
```

- [ ] **Step 2: 包 withAuthRedirect**（已存在 `lib/server-action-helpers.ts`）

```ts
export const search = withAuthRedirect(async (q: string) => { ... })
```

- [ ] **Step 3: vitest run** → 20 PASS

- [ ] **Step 4: Commit** `Sprint 1 P22-3c-1 — search + project-stats-proxy 复用 withAuthRedirect`

---

## Task 1.6: P22-3c-7 logActivity no-op 兼容层 caller 全审

**Files:**
- Modify: 所有 caller（grep `logActivity\(`）→ 删调用或换实路径
- Delete: `app/src/lib/actions/activity-log.ts` 中 logActivity / logActivityAuto no-op 函数

- [ ] **Step 1: grep 残留 caller**

```bash
grep -rn "logActivity\(\|logActivityAuto\(" app/src/
```

- [ ] **Step 2: 每个 caller 决策**（删 = 该路径活动日志 backend 已自动写；改实 = 前端必须显式写）— 默认删，个例 flag 给 CY

- [ ] **Step 3: 删 no-op 函数 + tsc 检查**

- [ ] **Step 4: vitest + tsc** → 全过

- [ ] **Step 5: Commit** `Sprint 1 P22-3c-7 — logActivity no-op 兼容层删除 + N 处 caller 收敛`

---

## Task 1.7: P22-3c-8 project-stats-proxy file-level eslint-disable 锚点

**Files:**
- Modify: `app/src/lib/actions/project-stats-proxy.ts`（首行加 eslint-disable + cleanup TODO）

- [ ] **Step 1: 加文件级注释**

```ts
/* eslint-disable @typescript-eslint/no-unused-vars -- 兼容层 / 待 actions/project-stats.ts 真接通后删整文件 */
```

- [ ] **Step 2: Commit** `Sprint 1 P22-3c-8 — project-stats-proxy 加 file-level eslint 锚点`

---

## Task 1.8: eslint ignore 渐进还债

**Files:**
- Modify: `app/eslint.config.mjs`

- [ ] **Step 1: 列出当前 ignore 表**（grep `ignores:`）

- [ ] **Step 2: 一条一条删 ignore + 跑 eslint** — 能改的当场改 / 不能改的标 `// eslint-disable-next-line ... -- <原因>`（行级 + 必带原因）

- [ ] **Step 3: 跑 `pnpm eslint .`** → 0 errors 0 warnings

- [ ] **Step 4: Commit** `Sprint 1 eslint ignore 还债 — 移除 N 项文件级 ignore / 行级注释带原因`

---

## Task 1.9: Sprint 1 R1+R2 流水线 + 关闸

- [ ] **Step 1: 派 R1 Sonnet subagent**（reuse 复用扫描 / 走 `feedback_subagent_sprint.md` §4）
- [ ] **Step 2: 派 R2 Opus subagent**（spec 字面合规 + 跨子片同根因漂移检测）
- [ ] **Step 3: findings 处理**（false positive 标 SKIP / 真漏抓立修 / punt 进 cross-sprint pool）
- [ ] **Step 4: 更新 cross-sprint-punt-pool.md** — P22-3c-1~8 全标 ✅ DONE / 状态分布 STILL_PUNT 39→31
- [ ] **Step 5: 更新 design/00-roadmap.md last_updated + Phase 2.3 行**
- [ ] **Step 6: 更新本文件 Sprint 1 status: completed**
- [ ] **Step 7: Commit + push** `Sprint 1 关闸 — C-FOLLOW-UP 8 项 + R1+R2 第 6 数据点 + cross-sprint pool 39→31`

---

# Sprint 2 — B-FOLLOW-UP 集成 e2e 基础设施

**为什么第二**：闸门 5 §8.1 实质实现层。Sprint 1 类型/命名稳了，断言代码才能写得稳。

**估**：cost $5-8 / 1.5 天 / e2e 2 → 10 PASS / perf smoke 2 → benchmark 完整。

**完成判据**：闸门 5 §8.1 第 1+2 项 ✅ / e2e 10 真路径全 PASS / pytest-benchmark 1000 seed P95/P99 落字面。

---

## Task 2.1: DB seed fixture（Playwright 用）

**Files:**
- Create: `app/e2e/fixtures/seed.ts`（前端调用 API 建测试数据 / OR 直连 DB）
- Create: `tests/conftest_e2e.py`（pytest fixture / spawn FastAPI test server + seed DB）

**关键决策**（A 模式给 CY）：
- **A. seed via API**：用 fetch 调 POST endpoint 建数据（慢但路径真）
- **B. seed via DB direct**：SQLAlchemy 直插（快但绕过校验，可能跟生产路径不一致）
- **推荐 A**：和真生产路径一致，慢一点没关系（测试环境 / 一次 setup）

- [ ] **Step 1: 写 seed.ts（API 路径）**

```ts
// app/e2e/fixtures/seed.ts
import type { APIRequestContext } from "@playwright/test"
export async function seedFullProject(api: APIRequestContext, token: string) {
  const project = await api.post("/api/projects", { /* ... */ })
  // node / dimension / issue 全维度
  return { project, nodes, dimensions, issues }
}
```

- [ ] **Step 2: 写后端 fixture spawn server**

- [ ] **Step 3: pilot e2e 用 seed** → 跑通

- [ ] **Step 4: Commit** `Sprint 2.1 — DB seed fixture (e2e + pytest)`

---

## Task 2.2: storageState login share

**Files:**
- Create: `app/e2e/global-setup.ts`
- Modify: `app/playwright.config.ts`（接 globalSetup + storageState）

- [ ] **Step 1: globalSetup 跑一次 login 存 storageState.json**

```ts
// app/e2e/global-setup.ts
import { chromium, FullConfig } from "@playwright/test"
async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.goto("http://localhost:3000/login")
  await page.fill('input[name="email"]', "e2e@test.local")
  await page.fill('input[name="password"]', "Test1234!")
  await page.click('button[type="submit"]')
  await page.context().storageState({ path: "app/e2e/.auth/storage.json" })
  await browser.close()
}
export default globalSetup
```

- [ ] **Step 2: 配 use.storageState** → 所有 e2e 自动带登录态

- [ ] **Step 3: pilot 跑通** + .gitignore 加 `app/e2e/.auth/`

- [ ] **Step 4: Commit** `Sprint 2.2 — storageState login share`

---

## Task 2.3: e2e #2-#10 9 个 skeleton → 完整断言

**Files:**
- Modify: `app/e2e/02-projects.spec.ts` ... `10-team.spec.ts`（test.describe.skip → 真断言）

**9 路径**（按 cross-sprint pool / next-session.md）：
1. `02-projects.spec.ts` — 项目 CRUD + dimension 列表
2. `03-nodes-tree.spec.ts` — 节点树 CRUD + drag/drop
3. `04-relations-graph.spec.ts` — 关系图渲染 + 编辑
4. `05-issues.spec.ts` — issue create/transition/list filter
5. `06-search.spec.ts` — 跨模块搜索
6. `07-overview-stats.spec.ts` — /overview viewer + stats
7. `08-import-export.spec.ts` — md/pdf/json 导出 + zip 导入
8. `09-activity-stream.spec.ts` — activity_log 时间线
9. `10-team.spec.ts` — M20 团队页 RBAC

每条 Task 模板（以 #2 为例）：

- [ ] **Step 1: 删 test.describe.skip / 写真断言**

```ts
// app/e2e/02-projects.spec.ts
import { test, expect } from "@playwright/test"
import { seedFullProject } from "./fixtures/seed"

test.describe("M02 projects CRUD", () => {
  test("list shows seeded project", async ({ page, request }) => {
    const { project } = await seedFullProject(request, /* token */)
    await page.goto("/projects")
    await expect(page.getByText(project.name)).toBeVisible()
  })

  test("create new project", async ({ page }) => { /* ... */ })
  test("update name reflects in list", async ({ page }) => { /* ... */ })
  test("delete removes from list", async ({ page }) => { /* ... */ })
})
```

- [ ] **Step 2: 跑 `pnpm playwright test 02-projects` → PASS**

- [ ] **Step 3: Commit** `Sprint 2.3.N — e2e #N <name> 完整断言`

（#3-#10 同模板，每条独立 commit）

---

## Task 2.4: pytest-benchmark + perf 1000 seed

**Files:**
- Modify: `pyproject.toml`（add pytest-benchmark）
- Create: `tests/perf/conftest.py`（large seed fixture）
- Create: `tests/perf/test_baseline_p95.py`（5+ benchmark 测试）

- [ ] **Step 1: 装 pytest-benchmark**

```bash
cd /root/workspace/projects/prism-0420 && uv add --dev pytest-benchmark
```

- [ ] **Step 2: 写 large seed fixture**（1000 项目 / 10000 dimension / 5000 issue）

```python
# tests/perf/conftest.py
@pytest.fixture(scope="session")
def perf_seeded_db(db_session):
    # 1000 projects + 10000 dimensions + 5000 issues
    ...
```

- [ ] **Step 3: 写 benchmark 测试**

```python
# tests/perf/test_baseline_p95.py
def test_list_projects_p95(benchmark, perf_seeded_db, client):
    result = benchmark(client.get, "/api/projects")
    assert result.status_code == 200

def test_overview_stats_p95(benchmark, perf_seeded_db, client, project_factory):
    project = project_factory()
    result = benchmark(client.get, f"/api/projects/{project.id}/overview")
    assert result.status_code == 200
```

- [ ] **Step 4: 跑 benchmark + 落基线到 `tests/perf/baseline.json`**

```bash
pytest tests/perf -v --benchmark-only --benchmark-json=tests/perf/baseline.json
```

- [ ] **Step 5: 写 README**（哪些 endpoint / P95 阈值 / 怎么对比基线）

- [ ] **Step 6: Commit** `Sprint 2.4 — pytest-benchmark + 1000 seed P95 baseline`

---

## Task 2.5: Sprint 2 R1+R2 + 关闸

- [ ] **Step 1: 派 R1+R2** — 第 7 数据点（验证 R 范式在测试基础设施场景的 ROI）
- [ ] **Step 2: 闸门 5 §8.1 第 1+2 项打钩** → roadmap 更新
- [ ] **Step 3: 更新 next-session.md / 本文件 Sprint 2 status: completed**
- [ ] **Step 4: Commit + push** `Sprint 2 关闸 — B-FOLLOW-UP 完整 / 闸门 5 §8.1.1+2 ✅ / R 范式第 7 数据点`

---

# Sprint 3 — A 后置债（CI 接通）

**前置（人工）**：CY 给 GH PAT 加 `workflow` scope（GitHub → Settings → Developer settings → PAT → Edit → 勾 workflow）。

**估**：cost $1-2 / 0.5 天（主要等 CI 跑红调）。

**完成判据**：ci.yml pushed / 首次 CI run 全绿 / 闸门 5 §8.0 全 ✅。

---

## Task 3.1: push ci.yml

- [ ] **Step 1: 验证 ci.yml 还在本地 untracked**

```bash
cd /root/workspace/projects/prism-0420 && git status .github/workflows/ci.yml
```

- [ ] **Step 2: cat 检查内容（确认 7 jobs 齐 / pgvector + redis service container / codegen-drift / deps-audit cron）**

- [ ] **Step 3: add + commit + push**

```bash
git add .github/workflows/ci.yml
git commit -m "Sprint 3 A 后置债 — ci.yml workflow（7 jobs + pgvector + redis + codegen-drift + deps-audit cron）"
git push
```

- [ ] **Step 4: GitHub Actions 看首次 run** → 红了哪些调哪些（service container 启动慢 / 缺 secrets / job 顺序等常见坑）

- [ ] **Step 5: 调到全绿**（可能 1-3 个 fix commit）

---

## Task 3.2: 接通 e2e job（Sprint 2 完成的 suite）

- [ ] **Step 1: ci.yml 加 e2e job**

```yaml
e2e:
  needs: [backend-test, frontend-build]
  runs-on: ubuntu-latest
  services:
    postgres: { image: pgvector/pgvector:pg16, ... }
    redis: { image: redis:7, ... }
  steps:
    - uses: actions/checkout@v4
    - run: pnpm install
    - run: pnpm playwright install chromium
    - run: pnpm playwright test
    - uses: actions/upload-artifact@v4
      if: failure()
      with: { name: playwright-report, path: app/playwright-report }
```

- [ ] **Step 2: push + 看 e2e job 跑** → 红了调

- [ ] **Step 3: Commit** `Sprint 3.2 — CI e2e job 接通`

---

## Task 3.3: 关闸门 5

- [ ] **Step 1: 在 `design/00-phase-gate.md` 闸门 5 §8.0 全打 ✅**
- [ ] **Step 2: §8.1 第 1+2+3 项打 ✅**
- [ ] **Step 3: roadmap Phase 2.3 行 PARTIAL → ✅ 100% / 闸门 5 全 ✅**
- [ ] **Step 4: next-session.md 更新 — 状态 = "Sprint 1+2+3 完成 / 闸门 5 真全 ✅ / Sprint 4 待启动"**
- [ ] **Step 5: 本文件 Sprint 3 status: completed**
- [ ] **Step 6: Commit + push** `Sprint 3 关闸 — A 后置债 + CI 全绿 / 闸门 5 §8.0+§8.1 全 ✅`

---

# Sprint 4 — 模块真漏洞 high/medium 9 项（独立 / 后端）

**为什么最后**：跟前端 / 集成 e2e / CI 都无依赖，可独立做。但跟 Sprint 1-3 比，每条改动小、影响窄、可测试性高，留到最后做"扫尾"最合适。

**estim**：cost $5-10 / 2-3 天 / 分 3 mini-sprint。

**完成判据**：cross-sprint pool 真漏洞表 high/medium 项全 ✅ DONE / pytest 1629 → 1640+ PASS / 0 STILL_PUNT high。

---

## Mini-Sprint 4A: M04 dimension 集中（4 项）

**Files:**
- Modify: `api/services/dimension_service.py`
- Modify: `api/dao/dimension_dao.py`
- Modify: `api/models/dimension.py`
- Modify: `api/schemas/dimension.py`
- Modify: `migrations/versions/<new>_add_dimension_records_index_updated_by.py`

### Task 4A.1: 真漏洞 #11 M04 IntegrityError → 500（dimension_service.create + create_dimension_record）

- [ ] **Step 1: 写失败测试**（并发创建 dimension 触发 UNIQUE 冲突 / 期待 409 不是 500）

```python
def test_create_dimension_concurrent_unique_409(client, dimension_factory):
    # 模拟同 (node_id, dimension_type_id) UNIQUE 冲突
    with patch("api.dao.dimension_dao.add", side_effect=IntegrityError("...", "...", "...")):
        resp = client.post("/api/.../dimensions", json={...})
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "DIMENSION_DUPLICATE"
```

- [ ] **Step 2: dimension_service.create + create_dimension_record 加 IntegrityError handler**

```python
try:
    return await dao.create(...)
except IntegrityError as e:
    if "uq_dimension_node_type" in str(e.orig):
        raise DimensionDuplicateError(...)
    raise
```

- [ ] **Step 3: pytest** → PASS

- [ ] **Step 4: Commit** `Sprint 4A.1 真漏洞 #11 — M04 dimension IntegrityError → 409 (M04-4 + M04-17)`

### Task 4A.2: 真漏洞 #12 M04-9 target_type 5 处 hard-code → const

- [ ] **Step 1: 写 enum**

```python
# api/models/dimension.py
class DimensionTargetType(str, Enum):
    NODE = "node"
    PROJECT = "project"
    # ...
```

- [ ] **Step 2: 替换 dimension_service.py:327/378/436/482/516 五处**

- [ ] **Step 3: pytest** → PASS

- [ ] **Step 4: Commit** `Sprint 4A.2 真漏洞 #12 — M04-9 target_type 5 处 hard-code 改 enum`

### Task 4A.3: 真漏洞 #13 M04-1 dimension_records (updated_by, updated_at) 联合索引

- [ ] **Step 1: alembic 新迁移**

```bash
cd /root/workspace/projects/prism-0420 && alembic revision -m "add dimension_records updated_by_updated_at index"
```

```python
def upgrade():
    op.create_index(
        "ix_dimension_records_updated_by_updated_at",
        "dimension_records",
        ["updated_by", "updated_at"],
    )
def downgrade():
    op.drop_index("ix_dimension_records_updated_by_updated_at", "dimension_records")
```

- [ ] **Step 2: 跑 alembic upgrade head + 跑测试**

- [ ] **Step 3: Commit** `Sprint 4A.3 真漏洞 #13 — M04-1 dimension_records (updated_by, updated_at) 联合索引`

### Task 4A.4: 真漏洞 #14 M04-8 db.get(DimensionType) 3 处 → DAO

- [ ] **Step 1: dimension_dao.py 加 `get_dimension_type_by_id`**

- [ ] **Step 2: service:349/428/474 三处替换**

- [ ] **Step 3: pytest** → PASS

- [ ] **Step 4: Commit** `Sprint 4A.4 真漏洞 #14 — M04-8 db.get → dimension_dao.get_dimension_type_by_id`

---

## Mini-Sprint 4B: M18 worker 真接 + cron + batch（3 项）

**Files:**
- Modify: `api/services/{node,dimension,competitor,issue}_service.py`（加 `get_for_embedding` 接口）
- Modify: `api/queue/embedding_worker.py`
- Modify: `api/cron/cron_failure_monitor.py`
- Modify: `api/dao/embedding_task_dao.py`

### Task 4B.1: 真漏洞 #21 M18 worker source_text 真接（high）

- [ ] **Step 1: 写失败测试**（embedding 写入后 content_hash 应 ≠ UUID）

```python
def test_worker_source_text_real_content(node_factory, embedding_task_factory):
    node = node_factory(name="real content")
    task = embedding_task_factory(target_type="node", target_id=node.id)
    await worker.run(task)
    embedding = await dao.get_embedding(node.id)
    assert "real content" in embedding.source_text  # 不是 "node:UUID"
```

- [ ] **Step 2: 4 个 service 加 `get_for_embedding(target_id, project_id) → str`**

```python
# api/services/node_service.py
async def get_for_embedding(self, target_id: UUID, project_id: UUID) -> str:
    node = await self.dao.get_by_id(target_id, project_id)
    return f"{node.name}\n{node.description or ''}"
```

- [ ] **Step 3: worker 调真 service 而非占位符**

- [ ] **Step 4: pytest** → PASS

- [ ] **Step 5: Commit** `Sprint 4B.1 真漏洞 #21 — M18 worker source_text 真接 4 service.get_for_embedding (high)`

### Task 4B.2: 真漏洞 #23 M18 cron_failure_monitor PCT 维度真实施

- [ ] **Step 1: embedding_task_dao 加 `count_completed_in_window(window_minutes) → tuple[int, int]`**（succeeded, total）

- [ ] **Step 2: cron 算 PCT = failed / total**

- [ ] **Step 3: 写测试**（mock dao / 验证 PCT 正确触发告警阈值）

- [ ] **Step 4: Commit** `Sprint 4B.2 真漏洞 #23 — M18 cron PCT 维度真实施`

### Task 4B.3: 真漏洞 #24 M18 batch_backfill 真 batch INSERT

- [ ] **Step 1: dao 加 `batch_create(ids: list[UUID])`**

```python
async def batch_create(self, ids: list[UUID], project_id: UUID) -> int:
    stmt = text("""
        INSERT INTO embedding_tasks (id, target_type, target_id, project_id, status, created_at)
        SELECT gen_random_uuid(), 'node', x, :project_id, 'pending', NOW()
        FROM unnest(:ids) AS x
    """)
    result = await self.session.execute(stmt, {"ids": ids, "project_id": project_id})
    return result.rowcount
```

- [ ] **Step 2: backfill 改用 batch_create**

- [ ] **Step 3: 写 5 万条 perf 测试** → 单 SQL ≤ 1s

- [ ] **Step 4: Commit** `Sprint 4B.3 真漏洞 #24 — M18 batch_backfill 真 batch INSERT FROM unnest`

---

## Mini-Sprint 4C: 跨模块 race + write_event e2e（2 项 / + 顺手 1 项）

### Task 4C.1: 真漏洞 #9 多模块 `if rows == 0: continue` race window 复审

**Files:**
- Modify: `api/services/version_service.py:2, 14`
- Modify: `api/services/competitor_service.py:1`
- Modify: `api/services/issue_service.py:7`
- Modify: `api/services/module_relation_service.py:1`

**做法**：M15-B1 真 INSERT 已落（commit 959e0b4），现在每个 `rows == 0: continue` 必须复审一遍——确认 race window 不会 silently 改变行为。

- [ ] **Step 1: 一处一处审**（5 处）— 写 race 测试 / 验证现行为符合预期 / 不符合的修

- [ ] **Step 2: pytest** → PASS

- [ ] **Step 3: Commit** `Sprint 4C.1 真漏洞 #9 — 多模块 rows==0 race window 复审 + 测试覆盖`

### Task 4C.2: 真漏洞 #8 M14-B12 write_event 异常传播 e2e（3 路径）

- [ ] **Step 1: 写 update / delete / unlink 三路径 e2e**（mock write_event raise / 验证调用方异常正确传播）

- [ ] **Step 2: pytest** → PASS

- [ ] **Step 3: Commit** `Sprint 4C.2 真漏洞 #8 — M14 write_event 异常传播 e2e (update/delete/unlink)`

### Task 4C.3: 真漏洞 #6 M07 update detach（None→NULL）— **需 CY 拍**

**这一项需要产品决策**：

- [ ] **Step 1: 询问 CY** — issue.assigned_to 是否允许 detach？M14 link/unlink 已支持，M07 是否对齐？

  - **A. 允许 detach**：实装 update_with_detach（schema 显式区分 None vs not provided / partial update Pydantic ExcludeUnset）
  - **B. 不允许**：design §3 字面写"detach 不支持"+ 测试断言 None 输入返回 422

- [ ] **Step 2: 按 CY 拍板实施**

- [ ] **Step 3: Commit** `Sprint 4C.3 真漏洞 #6 — M07 issue update detach (CY 拍 A/B)`

---

## Task 4.D: Sprint 4 关闸

- [ ] **Step 1: cross-sprint pool 真漏洞表更新** — #6/#8/#9/#11/#12/#13/#14/#21/#23/#24 全 ✅ DONE / status 分布 STILL_PUNT 31→22（剩 low + UNVERIFIABLE + DEFER_TO_POST_LAUNCH）

- [ ] **Step 2: 真漏洞表"约定时机已过"列清空 high/medium**

- [ ] **Step 3: roadmap last_updated + 本文件 Sprint 4 status: completed**

- [ ] **Step 4: next-session.md 终态快照** — "Post-Phase-2.3 Cleanup 全完成 / 仓库进入稳态 / 22 项 STILL_PUNT 全 low+UNVERIFIABLE / 待 Phase 3 数据回流再触发 post-launch perf"

- [ ] **Step 5: Commit + push** `Sprint 4 关闸 — 模块真漏洞 high/medium 9 项全清 / cross-sprint pool 31→22 / 仓库稳态`

---

# 总结

| Sprint | 内容 | cost | 时长 | 关闸 commit msg |
|--------|------|------|------|----------------|
| 1 | C-FOLLOW-UP 8 项 + R 范式第 6 数据点 | $2-3 | 0.5-1 天 | `Sprint 1 关闸 — C-FOLLOW-UP 8 项 + cross-sprint pool 39→31` |
| 2 | B-FOLLOW-UP 5 动作 + R 范式第 7 数据点 | $5-8 | 1.5 天 | `Sprint 2 关闸 — B-FOLLOW-UP 完整 / 闸门 5 §8.1.1+2 ✅` |
| 3 | A 后置债 + CI 接通 | $1-2 | 0.5 天 | `Sprint 3 关闸 — A 后置债 + CI 全绿 / 闸门 5 §8.0+§8.1 全 ✅` |
| 4 | 模块真漏洞 high/medium 9 项 | $5-10 | 2-3 天 | `Sprint 4 关闸 — 真漏洞 9 项清 / cross-sprint pool 31→22` |
| **合计** | | **$13-23** | **~5 天** | — |

**最终稳态**：
- 闸门 5 全 ✅
- cross-sprint pool STILL_PUNT 39 → 22（仅剩 low + UNVERIFIABLE + 已 DEFER_TO_POST_LAUNCH）
- 真漏洞表 high/medium 全清
- pytest 1629 → ~1645 / vitest 20 → ~25 / e2e 2 → 10 / perf benchmark 完整 / CI 全绿

**下一阶段触发条件**（不在本 plan 范围）：
- 真负载 P95 > 500ms 告警 → post-launch perf sprint（C 类 12 项重新评估）
- Phase 3 数据回流 → Prism vs prism-0420 对照报告

---

## 执行模式选择（Superpowers）

按 writing-plans skill 收尾约定，给 CY 两个选项：

**1. Subagent-Driven**（推荐 / fast iteration）：每个 Task 派一个 fresh subagent / 主 session 二阶段 review / 走 `superpowers:subagent-driven-development`

**2. Inline Execution**（batch + checkpoint）：当前 session 串跑 / 每个 Sprint 关闸 checkpoint / 走 `superpowers:executing-plans`

**默认推荐**：Sprint 1+4（很多机械重命名 / 改动窄）走 Inline / Sprint 2（大量新代码 / 高决策密度）走 Subagent-Driven / Sprint 3 直接 Inline。

CY 拍后启动 Sprint 1 第一个 Task（1.1 ExportPayload schema）。
