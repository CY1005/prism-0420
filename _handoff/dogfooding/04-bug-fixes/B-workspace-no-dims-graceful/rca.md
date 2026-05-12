---
fix: B-workspace-no-dims-graceful
bug_class: P0 / 共性高（影响 6 已完模块 + 未来 8 模块 DOM 主路径）
root_cause: workspace 入口 server component 调 getProjectTree → GET /api/projects/{pid}/overview / 后端 overview_service.py L62 在 enabled_count==0 时 raise OverviewNoDimensionsError(422)（design M10-B3 字面 contract）/ 前端 getProjectTree 无 catch → 异常冒泡到 Next.js error boundary（projects/error.tsx）"出错了" 页面 → workspace 全部不渲染 → seed 项目 + 任何无 enabled dimensions 的 custom-template 项目 DOM 主路径全阻塞
fixed_by: app/src/actions/nodes.ts getProjectTree catch overview_no_dimensions errorCode → fallback GET /api/projects/{pid}/nodes（NodeTreeResponse / 保留真实节点树，completionPercent=0）+ logger.warn 可观测；附带 parseError 同步读取后端真实字段名 `code`（修字段对齐漂移）
created: 2026-05-12
status: 已修 / M03 + M14 workspace DOM smoke 转 PASS / M01 + M02 + M20 regression OK / next build PASS / tsc 0 错
---

# RCA — B-workspace-no-dims-graceful

## §1 现象

来源：`_handoff/dogfooding/03-bug-queue.md` OPEN 池 `B-P2-M14-workspace-dimension-error` + 同根因 entry `B-P2-M19-workspace-no-dims-error` + M03/M04/M05/M06 spec DOM-SMOKE 全部撞同一 error boundary。

- 入口：用户 / e2e 登录后 goto `/projects/{pid}`（或 `/projects/{pid}/features/{nid}`）
- 现象：浏览器渲染 Next.js error boundary（`app/src/app/projects/error.tsx` L12 `<h2>出错了</h2>`）+ 错误文案 "Project has no enabled dimensions configured; completion rate cannot be calculated"
- 影响范围：seed 项目（`/api/projects` create with `template_type: "custom"` 默认无 enabled dimension config）+ 任何用户手工新建未启用维度的项目
- 触发链：
  ```
  ProjectPage server component (page.tsx L11)
    → getProjectTree(projectId) [actions/nodes.ts L109]
      → serverApiGet<OverviewResponse>(`/api/projects/{pid}/overview`) [actions/nodes.ts L111]
        → backend overview_router.GET /overview
          → OverviewService.get_overview [api/services/overview_service.py L47]
            → dao.count_enabled_dimensions(db, pid) = 0
              → raise OverviewNoDimensionsError(422) [L62]
        → backend 返 422 + body `{code:"overview_no_dimensions", message:"...", details:{project_id:"..."}}`
      → frontend parseError [src/lib/server-http-client.ts L24]
        → throw new ApiError(422, errorCode=null, message, ...)
    → 异常冒泡 → Next.js error boundary 触发 → render "出错了"
  ```

## §2 根因深定位

### §2.1 backend contract（design 字面 / 不动）

`design/02-modules/M10-overview/00-design.md` §3 "分母=0 处理时机说明（M10-B3）" L255:

> **若返回值 == 0，立即 raise `OverviewNoDimensionsError(422)`**，不进入节点聚合查询（不调 `list_nodes_with_fill_count`）

设计意图：避免"部分节点已计算但最终 422 中断"半成品状态。后端 contract 是正确的 / **本 fix 不动后端**。

### §2.2 前端 getProjectTree 无降级路径

`app/src/actions/nodes.ts` L104-114 旧代码：

```ts
export async function getProjectTree(projectId: string): Promise<TreeNode[]> {
  return withAuthRedirect(async () => {
    const data = await serverApiGet<OverviewResponse>(`/api/projects/${projectId}/overview`);
    return data.tree.map((n) => overviewToTreeNode(n, projectId));
  });
}
```

设计漂移：M10 后端的 422 是"完善度无法计算"的合法业务返回，前端拿到 422 应该理解为"完善度未配置 / 但节点树仍存在"，而不是当通用错误抛给 error boundary。

### §2.3 parseError 字段名漂移（连带修）

`api/errors/middleware.py` L18 后端 AppError → JSONResponse 序列化字段名：

```python
body: dict = {"code": code.value, "message": message}
```

实测 curl `/api/projects/{pid}/overview` 响应体：

```json
{"code":"overview_no_dimensions","message":"...","details":{"project_id":"..."}}
```

`app/src/lib/server-http-client.ts` L31 旧代码：

```ts
const errorCode = typeof body.error_code === "string" ? body.error_code : null;
```

实测 next-dev 日志：`ApiError ... errorCode: null`（即使后端有 code 字段也读不到）。

**字段名漂移**：
- backend 序列化字段 = `code`
- frontend parser 期望字段 = `error_code`
- 历史 mock（`server-http-client.test.ts` L78）用 `error_code` → 单测全 PASS 因为 mock 形态自洽 / 但生产路径与真实 backend 不对齐

**为什么本 fix 必须连带修**：
- catch 必须用 `errorCode === "overview_no_dimensions"` 精确分发（不要靠 status 422 + 字符串 message 匹配脆弱）
- 如不修 parseError 字段对齐，本 fix 的 errorCode 判断永远 false，等于没修

附带价值：M06 spec L520 已经在用 `body?.error?.code ?? body?.code ?? body?.error_code` 兜底读三态 / 间接证明这是横向问题。

## §3 类似问题 grep 清单

### §3.1 同根因可能阻塞的 server actions / page entries

```bash
cd /root/workspace/projects/prism-0420/app
grep -rln "OverviewResponse\|/overview" src/ --include="*.ts" --include="*.tsx"
```

结果：

| # | 文件 | 调用点 | 风险 | 处置 |
|---|------|-------|------|------|
| 1 | src/actions/nodes.ts L111 | getProjectTree | 🔴 高（本 fix） | 修 |
| 2 | src/actions/project-stats-proxy.ts L29 | getProjectStatsAction | 🟡 中 | 返 ActionResult 已被 caller 解构 / r.success 兜底 / 暂不动 |
| 3 | src/actions/project-stats-proxy.ts L42 | getProjectTreeOverviewAction | 🟡 中 | 同上 / 暂不动 |
| 4 | src/app/projects/[projectId]/overview/page.tsx | 直接调 getProjectStatsAction | 🟢 低 | 已有 overview/error.tsx 兜底 / 即使 422 也只影响 overview 子页 |
| 5 | src/app/projects/[projectId]/page.tsx L11 | 间接调 getProjectTree | 🔴 高（受本 fix 修复影响） | 自动 fix（getProjectTree 修） |
| 6 | src/app/projects/[projectId]/features/[featureId]/page.tsx L16 | 间接调 getProjectTree | 🔴 高 | 自动 fix |

**本 fix 改的是 getProjectTree 一处 / 受益的 page 是 2 个**（`/projects/{pid}` 主页 + `/projects/{pid}/features/{nid}`）。其他 OverviewResponse 调用点走 ActionResult 包装范式 / 无 error boundary 风险。

### §3.2 parseError errorCode 横向消费方扫描

```bash
grep -rn "errorCode\b\|error\.errorCode" src/ --include="*.ts" --include="*.tsx"
```

主要消费方：
- `src/actions/auth.ts`, `src/components/auth-context.tsx` — 用 errorCode 做 ACCOUNT_DISABLED / ACCOUNT_LOCKED 分发
- `src/components/global-search-bar.tsx`, `src/services/http-client.ts` test mock
- 多数业务 action 走 `actionError(error)` helper / 间接消费 errorCode 转 ActionResult

**parseError 字段名漂移影响范围**：所有想按 error_code 做 UX 分发的路径（已修 `code` fallback / 行为对所有这些路径 additive 升级 / 不破现有 `error_code` mock）。

### §3.3 punt 清单

- F-NEXT-2026Q3：把 frontend `error_code` 命名彻底迁到 `code` + 移除 fallback / 当前 sprint 保持兼容性（后端 + test mock 双对齐）

## §4 design vs 实装漂移定位

### §4.1 design 哪步漏了？

- `design/02-modules/M10-overview/00-design.md` §3 字面定义 422 早返回 / 但 **没指定前端遇到 422 应如何降级**（design 默认让前端各自处理）
- `design/01-engineering/06-frontend-spec.md`（Phase 2.2）继承 Prism 前端时拷改 getProjectTree / 当时假设 backend overview 永远成功（旧 prism 用 drizzle 直查 / 无 422 早返回）
- M10 sprint 期 R2 Reviewer 未审 "前端如何降级 422" 这一垂直切片（reviewer 只读单元 + 集成测试 / e2e DOM 路径覆盖盲区）
- e2e DOM smoke gap（本 dogfooding sprint 才补）：之前没有 test 跑过 "seed 项目 → /projects/{pid}" 真实路径

### §4.2 parseError 字段名漂移历史

- 子片 3a 启动期（Phase 2.2 子片 0 prep）：拷改 `services/http-client.ts` 时按 prism v1 旧后端契约用 `error_code`（旧 prism FastAPI middleware 序列化字段名）
- prism-0420 重写 backend `api/errors/middleware.py` 时改用 `code`（M02 + ADR-004 sprint 期约定 / 与 OpenAPI Problem Details / RFC 9457 更接近）
- 前端 parser **未同步对齐** / 单测 mock 用 `error_code` 自循环 → spike 期未抓到
- M06 spec 524 P0 test "错误响应格式符合规约 error.code + error.message" 实际是从用户视角验"前端能不能拿到 code 字段"（响应体 nested `error.code` 形态是 spec 期望 / 实际后端 flat `code` / **这部分是后端契约问题不在本 fix 范围**）

### §4.3 应该如何避免

**dogfooding sprint phase2-case.md §禁止模式 候选补充**：

1. **business 422 与系统错误必须分层处理**：每个 server action / RSC 必须显式列出哪些 backend 错误码是 "business 合法返回 / 需 UX 降级"，哪些是 "真异常 / 透传 error boundary"。不能默认全部抛。
2. **前后端 error 字段命名 contract 守护**：CI lint 候选 grep `error_code` 同时 grep backend `middleware.py` 序列化字段 / 不一致告警。
3. **R-X 类 contract 漂移 CI 守护**：定期跑 `curl backend → parse frontend → 验 errorCode 非 null` 端到端 contract test。

**design/01-engineering/06-frontend-spec.md 候选补段**：
- 服务端 action 调 backend `/overview` 类 endpoint 时，遇到 422 业务错误必须显式 catch 转空状态 / 不要直接抛到 error boundary。

## §5 fix 改动

| 文件 | 行 | 改动 | 类型 |
|------|----|------|------|
| app/src/actions/nodes.ts | L5-12 + L104-167 | import ApiError + getProjectTree catch overview_no_dimensions → fallback /nodes endpoint + 注释；新增 nodeWithChildrenToTreeNode adapter | 核心 |
| app/src/lib/server-http-client.ts | L18-46 | FastApiErrorBody 加 `code` 字段 + parseError fallback 读 code | 横向（连带修） |
| app/src/services/http-client.ts | L35-58 | 同上（client-side parser 同步） | 横向 |

**未动**：
- 后端 `api/services/overview_service.py`（design contract 字面 / 不动）
- 后端 `api/errors/middleware.py` 字段命名（已是 `code` / 不动）
- workspace.tsx（client component / 通过 props 接 tree / 自然适配空 + nodes-only 两态）
- `app/src/app/projects/error.tsx`（仍保留 error boundary 给其他真异常路径）
- M04/M05/M19 spec（设计上是 "bug 未修 OR bug 已修" 两态断言 / fix 让 spec 走 "已修" 分支 / 部分 spec 假设 file-view 节点但 seed 用 folder / **属于 spec 设计偏差不属于本 fix**）

### dogfooding 6 项自评

| # | 维度 | 评级 | 备注 |
|---|------|------|------|
| 1 | 改动范围 | **中** | 跨 3 文件（actions/nodes.ts + server-http-client.ts + http-client.ts / ≤80 行）/ 比 plan 预估"低≤30 行"略多 / 但仍单功能域 |
| 2 | 代码位置 | 低 | actions/ + lib/ 业务 helper 层 / 不动 auth / middleware / config |
| 3 | 可逆性 | 低（安全） | git revert 一键回退 / 不涉 schema / 不涉运行时配置 / parseError 加 fallback 向后兼容（test mock `error_code` 仍工作） |
| 4 | 业务断言 | 中 | 改 getProjectTree fallback 行为 / 引入 nodes-only tree 路径 / completionPercent=0 替代真实值（无 dim 配置时合理）|
| 5 | 测试覆盖 | 中 | M03 + M14 workspace DOM smoke 转 PASS / M01 + M02 + M20 regression OK / parseError 既有 18 单测全 PASS（含 `error_code` mock） / next build PASS |
| 6 | bug 类型 | 中 | UI 渲染 + 前后端 contract 漂移 / 非 auth / 非数据丢 |

**预判 0 项高 / 3 项中（范围、断言、覆盖、bug 类型） → A 路径直推 + 写一份 design-audit.md（标 0 冲突 / 仅记录 design 漂移登记）**。

## §6 验证证据

### §6.1 tsc

```bash
cd app/ && pnpm exec tsc --noEmit
→ exit=0（0 错）
```

### §6.2 next build（Turbopack 真编译）

```
▲ Next.js 16.2.4 (Turbopack)
✓ Compiled successfully in 8.2s
27 routes 全部 PASS（含 /projects + /projects/[projectId] + /projects/[projectId]/features/[featureId]）
```

### §6.3 frontend 单测

```
pnpm exec vitest run src/lib/server-http-client.test.ts src/services/http-client.test.ts
→ 18/18 PASS（含 "非 401 错误抛 ApiError 含 errorCode" 用 error_code mock / 向后兼容验证）
```

### §6.4 E2E Playwright DOM smoke

```
M03 workspace.tsx DOM smoke: ✅ PASS（修前 FAIL on error boundary）
M14 workspace FeedList 区域 DOM smoke: ✅ PASS（修前 FAIL on error boundary）
M01 user-account: 5/5 PASS（regression）
M02 project: 5/5 PASS（regression）
M20 team: 26/26 PASS（regression）

M04/M05/M19/M06 部分 spec 仍 FAIL — 但与本 fix 无关（pre-existing 测试设计问题：
  - M04 workspace smoke：spec 断言 "出错了" OR "点击添加..." / 修后两态都不匹配（dim 列表为空时 "点击添加" 文案不渲染）
  - M05 版本演进区域：spec 要求 file-view "版本演进" 文字 / seed 是 folder type 不走 file 视图
  - M19 export node happy path：spec 要求 file-view "导出 Markdown" 按钮 / seed 是 folder 显示 "导出模块"
  - M06 #459/524/770：本 sprint 已入 OPEN 池的独立 bug B-P2-M06-* 不在本 fix 范围
  - M11 #37/75/102/659：pre-existing test bugs（strict-mode 双 link / Content-Type override / backend 0 行 CSV 处理）
）
```

### §6.5 backend pytest

```
tests/test_m11_service.py + test_m11_routers.py + test_m11_dao.py + test_m11_models.py
+ test_m03_service.py + test_m03_dao.py + test_m04_service.py + test_m04_dao.py
+ test_m14_service.py + test_m14_routers.py
→ 217/217 PASS
```

## §7 design 漂移落盘建议（不属于本 fix 实施 / 由主 agent 决定）

1. **app/CLAUDE.md（或 app/AGENTS.md）补红线**：
   ```
   🔴 backend AppError 序列化字段是 `code`（api/errors/middleware.py L18）/ 前端 parseError 必须双读 `code` + `error_code` 兼容 / 单测 mock 与生产路径对齐
   ```

2. **design/02-modules/M10-overview/00-design.md §3 补段**：
   - "前端 getProjectTree / getProjectStatsAction 遇 OverviewNoDimensionsError(422) 必须 catch 转空状态 / 不抛 error boundary"

3. **cross-sprint pool 候选**（不阻塞本 sprint）：
   - F-CONTRACT-1：CI 端到端 contract test（curl backend 真响应 → parse frontend → 验 errorCode 非 null）
   - F-NEXT-2026Q3：彻底迁 `error_code` → `code` + 移除 fallback / 当前 sprint 保持双读

## §8 后续闭环

- 同根因 OPEN 池 entries 一并标 FIX_DONE：B-P2-M14-workspace-dimension-error + B-P2-M19-workspace-no-dims-error
- M04/M05 workspace smoke 测试设计修正（spec 改 seed 节点类型 / 或加 file-view 节点 seed） — punt 下次 sprint（不在本 fix 范围）
- 本 fix 间接揭露：seed_full_project fixture 不创建 file-type node + 不启用 dimensions / 多个 DOM-SMOKE spec 假设 file-view 路径 → seed 改造 punt
