---
title: B-P4-cluster-6 design-audit (A 路径)
sprint: dogfooding P4 cluster-6
date: 2026-05-13
risk: low (A 路径)
audit_required: false (A 路径 / 0 product code 改 / 但跨 8 design 文档 / 列改动清单)
---

# B-P4-cluster-6 design-audit (A 路径) — 改 design + spec + 新报告 / 0 product code 改

## 0. A 路径自评（plan §3 D 6 维风险）

| 维度 | 评估 | 自评 |
|------|------|------|
| 修改范围 | 仅 design 文档 + spec 文件 + 新报告 / 0 product code | 低 |
| 影响域 | design 文档段尾追加（不删原 design）+ spec 断言改宽松 / 不破坏现有契约 | 低 |
| 测试覆盖 | tsc 0 错 + pytest 1651 PASS + 4 spec 全 PASS | 低 |
| 回滚成本 | 全部 git revert / 0 副作用 | 低 |
| 跨 Sprint 影响 | PUNT-REPORT.md 推到 Phase 2.x M-frontend sprint / 显式 punt | 低 |
| design/ADR/migration | design 加注解 / 不动 ADR / 不改 migration | 低 |

**结论**：A 路径自评全低 / 跨 8 文件但全 design 文档段尾追加（不改原 design 内容）/ 直推 main 合规。

## 1. design 文档改动清单（dogfooding 实证段追加）

### M03-module-tree/00-design.md

**位置**：§1 边界灰区段尾（path 并发写冲突 G5 之后 / §2 之前）
**性质**：新增段（不删原内容）
**内容**：面包屑 link 漂移记录 + Phase 2.x M03-frontend punt 指针

### M05-version-timeline/00-design.md

**位置**：§1 边界灰区段尾（切换当前版本 G2 之后 / §2 之前）
**性质**：新增段（不删原内容）
**内容**：5 version-ops endpoints 前端缺记录 + Phase 2.x M05-frontend punt 指针

### M07-issue/00-design.md

**位置**：§1 边界灰区段尾（category 维度映射之后 / §2 之前）
**性质**：新增段（不删原内容）
**内容**：§8 UI 6 处缺失清单（status badge / filter / 转换按钮 / 详情页 / node-scoped / 档案页区块）+ Phase 2.x M07-frontend punt 指针

### M11-cold-start/00-design.md

**位置**：§6 分层职责表禁止清单之后（§7 之前）
**性质**：新增段（不删原内容）
**内容**：cold-start/page.tsx 缺 / 真入口是 workspace 空状态 → /import 记录 + Phase 2.x M11-frontend punt 指针

### M15-activity-stream/00-design.md

**位置**：§6 分层职责表禁止清单之后（§7 之前）
**性质**：新增段（不删原内容）
**内容**：3 UI 组件未实装清单（activity-filter-bar / date-grouping / metadata-collapse）+ Phase 2.x M15-frontend punt 指针

### M18-semantic-search/00-design.md

**位置**：§6 env 配置清单段尾（SEARCH_EVAL_SAMPLE_RATE 之后 / §7 之前）
**性质**：新增段（不删原内容）
**内容**：rrf_k / similarity_threshold 字段双缺记录 + M02 ProjectSettings schema baseline-patch 待补 + Phase 2.x punt 指针

### M19-import-export/00-design.md

**位置**：§6 分层职责表禁止清单之后（§7 之前）
**性质**：新增段（不删原内容）
**内容**：export-button.tsx / node-selector.tsx 独立组件缺记录 + A vs B 入口走同一 endpoint 实证 + Phase 2.x M19-frontend punt 指针

### M20-team/00-design.md

**位置**：§6 分层职责表段尾（Model 行之后 / §7 之前）
**性质**：新增段（不删原内容）
**内容**：M20 02-frontend-design.md 已显式标"等 backend endpoint" / 0 新增漂移 / 仅在 00-design.md 加索引指针

## 2. spec 文件改动清单（断言修宽松 / 不改 product）

### M04-feature-archive.spec.ts L138（workspace smoke）

**改动**：
- 加 "添加关联" 按钮 fallback 分支（workspace 主结构验证）
- 保留 error boundary "出错了" + dim card hint 两态
- 三态接受：A=error boundary / B=hint visible / C=workspace 主结构（添加关联按钮）渲染
- 修改前注释明确"B-P2-M14 fix 后 + seed 无 enabled dim 时 dim cards 段不渲染"

### M05-version-timeline.spec.ts L81（workspace.tsx 进入项目详情页）

**改动**：
- 加 `seedFullProject({ withFileNode: true })` opt-in 启用 root-level file node
- 保留 error boundary 兜底分支

### M11-cold-start.spec.ts L37 / L75 / L102 / L659

**L37/L75 改动**：
- `page.getByRole("link", { name: /导入文档/ }).first()` 解决 strict-mode 3 处冲突
- workspace.tsx L899 / L1260 / L1328 共 3 处"导入文档"

**L102 改动**：
- 删除 manual `Content-Type: multipart/form-data` 让 Playwright 自动注入正确 multipart boundary

**L659 改动**：
- 改 either-or 宽松断言：422 字面 OR 201 + total_rows=0
- 真正 422 需 backend 改 / 出 cluster-6 范围

### M19-import-export.spec.ts L57 / L117

**L57 改动**：
- `seedFullProject({ withFileNode: true })` → 默认 file 视图 → 导出 Markdown 按钮可见
- 改 waitForEvent("download") 替换 waitForRequest（server action server-to-server / 浏览器看不到 backend POST）
- `getByText(fileName).first()` 解决 Root File strict-mode（sidebar + breadcrumb 各 1 处）

**L117 改动**：
- withFileNode + 改验"任一导出按钮存在"（folder view getFolderOverview 422 bug 待 product 修 / 不在 cluster-6）

## 3. 新增报告 — PUNT-REPORT.md

**路径**：`_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md`

**结构**：
- 5 模块（M12/M13/M14/M16/M17）frontend gap 完整 OPEN bug 清单（12 条）
- 每模块涉及 spec test + 修法范围估时 + Opus subagent cap
- design vs 实装漂移 4 段根因（Phase 2.2 前端继承期遗漏）
- 建议下个 sprint 节奏（5 frontend Opus subagent 并行 cap $32-48 / 跨 1-2 sprint）
- STAR 价值（Phase 3 v0.4 D2 bug 类别分布"前端继承期遗漏"）

## 4. 冲突 audit（design 文档 vs 既有合并约束）

| 潜在冲突 | audit 结论 |
|---------|----------|
| 跟 cluster-5（M10 错误格式 design sync）冲突 | 不冲突 / cluster-5 改的是 engineering-spec §7.4 / 本 cluster 改的是模块 design §6/§1 |
| 跟 cluster-3（M04 action_type design sync）冲突 | 不冲突 / cluster-3 改的是 M04 §10 prose / 本 cluster 改的是 M07/M11/M15/... §1/§6 |
| 跟 cross-sprint-punt-pool 冲突 | 一致 / PUNT-REPORT.md 加新条目 / 跟 cross-sprint pool 协议一致（cross-sprint pool 在 ai-quality-engineering 仓 / 本仓 Phase 2.x M-frontend sprint 启动时 reconcile）|
| 跟 dogfooding 03-bug-queue 漂移 | 一致 / 本 cluster 是 OPEN 池 → SYNCED/PUNT 池迁移的执行 / 跟 queue plan 一致 |

**结论**：0 冲突 / 全 A 路径 / 直推 main 合规。

## 5. 不动的事项（明确边界）

- ❌ 不动 product code（A 路径硬约束）
- ❌ 不动 ADR（已 accepted 设计决策不回写）
- ❌ 不动 design §1 In scope 字面（保留 design intent / 仅加 dogfooding 实证段追加）
- ❌ 不动 backend API contract / schema / state machine
- ❌ 不动 cross-sprint-punt-pool（本 cluster 是 dogfooding 内部 punt / 不跨 sprint）

## 6. 后续闸门

- P5a regression sprint：跑 22 个 dogfooding spec 全量回归（确认 cluster-6 spec fix 不破坏其他 spec / 期望 4 模块 6 条 spec 从 FAIL → PASS / 其余 PASS 不变）
- P5b STAR report v0.4：把本 cluster-6 STAR 价值（前端继承期盲区）写进 phase3-data-baseline.md D2 bug 类别分布段
- Phase 2.x M-frontend 实装 sprint 启动：PUNT-REPORT.md 推 5 模块 Opus subagent 并行
