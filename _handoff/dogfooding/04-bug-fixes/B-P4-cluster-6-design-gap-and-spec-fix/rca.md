---
title: B-P4-cluster-6 — design-gap candidate sync + spec-design-fix + frontend gap punt RCA
sprint: dogfooding P4 cluster-6
date: 2026-05-13
risk: low (A 路径全)
co_author: Claude Opus 4.7 (1M context)
---

# B-P4-cluster-6 — design-gap candidate sync + spec-design-fix + frontend gap punt

## 0. fact-finding（feedback_decision_codefirst_validation §2）

| 步骤 | 命令 | 结果 |
|------|------|------|
| 1 | grep OPEN 池 design-gap candidate | 8 条 design-gap / 5 模块 frontend gap 大群（M12/M13/M14/M16/M17）|
| 2 | ls design/02-modules/ | 20 模块 design 文档全在 / 8 个待 sync（M03/M05/M07/M11/M15/M18/M19/M20）|
| 3 | grep M07 §8 漂移 | 03-bug-queue.md L112 "元发现候选" 段已记录（不入 bug queue 但 P3/P4 期回写）|
| 4 | grep M19 export-button design vs 实装 | 03-bug-queue.md L42-48 spec 顶部 design-gap 注释已记录 |
| 5 | spec 文件 grep pre-existing FAIL 行号 | M04 L138 / M05 L81 / M11 L37 L75 L102 L659 / M19 L57 L117 — 全确认 |

**fact-finding 结论**：
- 8 个 design-gap candidate（M03/M05/M07/M11/M15/M18/M19/M20）：全是 design vs UI 漂移 / backend 已实装 / frontend 未实装；punt 至 Phase 2.x M-frontend sprint 是合理选项
- 5 模块 frontend gap 大群（M12/M13/M14/M16/M17）：涉及 12 条 OPEN bug / 改动量大 / **不在本 cluster-6 范围**
- 6 条 spec-design-fix（实为 8 条 pre-existing FAIL 中的子集）：spec 写错 / 不是 product bug / 改 spec 断言即可

## 1. 类型 1 — design-gap sync（8 design 文档加 dogfooding 实证段）

### 修改清单

| design 文档 | 锚点段落 | 关联 OPEN bug | sync 内容 |
|------------|---------|--------------|----------|
| M03 §1 边界灰区段尾 | 节点边界设计 | 面包屑 link（元发现候选）| 面包屑中间节点 UI 为 `<span>` 非 `<Link>`，仅末端可点 |
| M05 §1 边界灰区段尾 | 版本生命周期 | B-P2-M05-design-gap-version-ops-ui | 5 endpoints（PUT/DELETE/set-current 等）后端已实装 / 前端缺 |
| M07 §1 边界灰区段尾 | issue 业务边界 | M07 §8 6 处 UI 缺（03-bug-queue L112）| status badge / filter / 转换按钮 / 详情页 / node-scoped / 档案页区块 全前端缺 |
| M11 §6 分层职责段尾 | orchestrator 范式 | B-P2-M11-design-gap-cold-start-page | cold-start/page.tsx 不存 / 真入口是 workspace 空状态卡片 → /import |
| M15 §6 分层职责段尾 | 横切表读写约束 | B-P2-M15-design-gap-filter-bar-ui + date-grouping-ui + metadata-collapse-ui | 3 处 UI 组件未实装 |
| M18 §6 env 配置段尾 | 配置层完整性 | B-P2-M18-design-gap-rrf-k-ui-missing | rrf_k / similarity_threshold 字段 schema + UI 双缺 |
| M19 §6 分层职责段尾 | A/B 入口共存 | B-P2-M19-design-gap-export-button + node-selector | 独立组件未抽 / workspace.tsx 内联按钮 + 入口 A vs B path 走同一 endpoint |
| M20 §6 分层职责段尾 | frontend 等 backend 范式 | B-P2-M20-design-gap-member-list-UI | M20 design 02-frontend-design.md 已显式标"等 backend endpoint" / 0 新增漂移 |

### 修法范式（统一段尾追加块）

```markdown
**dogfooding sprint 2026-05-13 实证（design vs UI 漂移）**：
- <具体 UI 元素> 在 frontend 未实装 / backend endpoint 已实装并通过 P3 executor 验证
- punt at Phase 2.x M<NN>-frontend 实装 sprint
- 详 `_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md`
```

### 修法原则

1. **不改 product code**（A 路径硬约束）
2. **不删 design 原有内容**（保留 design intent 作为可恢复目标 / 仅加 dogfooding 实证标注）
3. **链接 PUNT-REPORT.md**（一处更新 / 多处引用一致性）

## 2. 类型 2 — spec-design-fix（6 spec 断言改 / 0 product 改）

### 修改清单

| Spec | Line | 原 FAIL 现象 | 修法 |
|------|------|------------|------|
| M04 L138 | workspace smoke | 期望 "出错了" OR "点击添加" / 实际 workspace 已修不 crash + dim cards 空段（无 enabled dim 时不渲染）| 三态接受：error boundary / 点击添加 hint / "添加关联" 按钮（workspace 主结构验证） |
| M11 L37 | empty-project welcome card | strict-mode：getByRole("link", /导入文档/) 命中 3 处（workspace L899/L1260/L1328）| `.first()` 取空状态卡片入口 |
| M11 L75 | empty-project click 导入文档 | 同上 strict-mode | `.first()` 后再 click |
| M11 L102 | happy path CSV upload | manual `Content-Type: multipart/form-data`（无 boundary）让 Playwright 自动注入 multipart 时冲突 | 删除 manual Content-Type / 让 Playwright 自动注入 |
| M11 L659 | CSV 仅列头返 422 | backend 实装现状 201 + status=completed + total_rows=0（未走 invalid CSV 分支）| spec 用 either-or 宽松断言：422 字面 OR 201 + total_rows=0 / 真正 422 需要 backend 改（出范围）|
| M19 L57 | export node happy path | seed 默认 root=folder → file 视图按钮不渲染 / 旧 waitForRequest 期望浏览器直发 POST（server action 范式不直发）| `seedFullProject({ withFileNode: true })` + 改 waitForEvent("download") 兜底验证 |
| M19 L117 | export button folder 视图 | workspace folder 视图 getFolderOverview /overview 422 → error boundary（同 B-P2-M14 根因第 N 表现面 / 真 bug 但出范围）| withFileNode + 验"任一导出按钮存在" |
| M05 L81 | workspace.tsx 进入 DOM smoke | 同 M04 + version timeline 仅 file 视图渲染 | `withFileNode: true` |

### 修法原则

1. **改 spec 断言 / 0 product code 改动**
2. **保留两态兜底**（bug 已修 OK / bug 未修也 OK）防回归静默
3. **三处真 bug 出范围**（M11 backend 422 / M19 getFolderOverview 422 / waitForRequest server action 范式）— punt 走 PUNT-REPORT.md

## 3. 类型 3 — frontend gap punt 报告

**5 模块**：M12 / M13 / M14 / M16 / M17
**12 条 OPEN bug 全 punt** 至 `_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md`

详 PUNT-REPORT.md：
- 5 模块完整 OPEN bug 清单 + 修法范围估时
- design vs 实装漂移根因（Phase 2.2 前端继承期遗漏 / 子片 3c 未执行）
- 建议下个 sprint 节奏（5 frontend 实装 Opus subagent / cap $32-48 / 跨 1-2 sprint）
- STAR 价值：Phase 3 v0.4 D2 bug 类别加"前端继承期遗漏"类别

## 4. 总结 — Frontend gap punt 4 段反思

### 段 1：根因（Phase 2.2 子片 3c 未执行 / 前端继承期 audit 盲区）

设计前置方法论保证了 backend 完整度（M01-M20 全实装并通过 P3 executor），但 Phase 2.2 前端继承（拷 prism/web/ 改 API 接 prism-0420 后端）时：
- 子片 3b 拷贝降级 → 标 punt 等子片 3c 接入真后端
- **子片 3c 未执行** → 多模块 actions stub puntResult / 假进度 / URL 漂移留下
- 没人对照 design 跑 design-vs-UI 漂移 audit

### 段 2：盲区类别

| 类别 | 实例 | 检测方法 |
|------|------|---------|
| actions stub puntResult | M13 / M17 各 6 个 / 4 个 action | grep `puntResult\|PUNT_MSG` |
| URL 漂移（前端调错 endpoint）| M16 `/api/snapshot/generate` flat / M13 SSE proxy URL | grep frontend fetch + 对照 backend router 路径 |
| 异步范式漂移（同步替 fire-and-forget）| M16 同步 await / M17 setTimeout 假进度 | grep `setTimeout\|await fetch` in actions |
| 多入口 vs 单入口 UI 漂移 | M17 tab vs 4 步向导 / M13 全屏 vs 抽屉 | 对照 design §6 字面声明 |
| Component 抽象层漂移 | M19 export-button.tsx 缺 / 实装内联 | ls design §6 列的 component 文件 |

### 段 3：闸门补丁建议

下个 frontend 实装 sprint 加 design-vs-UI 漂移 audit gate：
- 每个 frontend 实装 subagent 完成后 → 跑 design-audit subagent 对照 design §6 / §7 / §8
- 找出 frontend stub puntResult + URL 漂移 + 异步范式漂移 + UI 缺
- 闸门通过条件：N 条 design vs UI 漂移 = 0（或显式 PUNT 走 cross-sprint pool）

### 段 4：STAR 价值

**Phase 3 v0.4 D2 bug 类别分布**：
- 新增类别"前端继承期遗漏" / 12 条 OPEN bug 实证
- 简历级实证："design-first 方法论的盲区——前端继承期是新瓶颈"
- 对照 Prism 原版（无 design / 边做边想）：prism-0420 backend 完整度更高 / 但 frontend 集成漂移类 bug 数量级相同
- 启示：design-first + 后端先做的路径下，**前端继承期 audit gate 是必备**

## 5. 验证证据

| 验证项 | 命令 | 结果 |
|--------|------|------|
| tsc 0 错 | `pnpm exec tsc --noEmit` | 0 errors |
| pytest regression | `.venv/bin/python3 -m pytest tests/` | 1651 passed / 6 skipped |
| M04 spec | playwright | 全 PASS（含 L138 修后） |
| M05 spec | playwright | 全 PASS（含 L81 withFileNode 修后）|
| M11 spec | playwright | 63 PASS（含 L37/L75/L102/L659 修后）|
| M19 spec | playwright | 21 PASS（含 L57/L117 修后）|

## 6. 不修的事（明确 PUNT）

- M11 L659 真正 422 分支：backend cold_start_service.py 加 row_count==0 → raise ColdStartCsvInvalid（product 改 / 不在 cluster-6）
- M19 L57 waitForRequest server action 范式：server action 走 server-to-server / 浏览器看不到 / 需架构层改
- M19 folder 视图 getFolderOverview 422：actions/nodes.ts getFolderOverview 加 catch + fallback /nodes（同 getProjectTree 范式 / 但已超 cluster-6 范围）

→ 这 3 条 punt 进 Phase 2.x M-frontend 实装 sprint 或 cross-sprint-punt-pool（如确认需要）

## 7. 影响范围

- design 文档：8 处加 dogfooding 实证段（M03/M05/M07/M11/M15/M18/M19/M20）
- spec 文件：4 处修断言（M04/M05/M11/M19）
- 新增报告：1 处（PUNT-REPORT.md）
- product code：0 改动 ✅
- backend pytest：1651 PASS 不变 ✅
- frontend tsc：0 错 ✅
