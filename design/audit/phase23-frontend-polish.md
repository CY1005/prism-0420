---
title: Phase 2.3 子 sprint C — frontend-polish 关闸 audit
status: partial-complete
owner: CY
created: 2026-05-09
phase: Phase 2.3 子 sprint C
parent: ../00-roadmap.md §8 + ../../_handoff/_archive/phase23-prompts.md「子 sprint C」段
---

# Phase 2.3 子 sprint C — frontend-polish 关闸 audit

## 1. 实施范围

### ✅ 完成项

| ID | 内容 | 改动 |
|----|------|------|
| **P22-3b-1** | withAuthRedirect 抽 horizontal helper | `src/lib/server-action-helpers.ts` 新建 + 11 文件去重 inline + 各文件 unused import 清扫 |
| **P22-3c-7** | logActivity / logActivityAuto no-op 兼容层 删 | `src/actions/activity-log.ts` 删两 no-op + analysis/page.tsx 2 caller 删 + getActivityLogs 保留 |
| **P22-4-2** | isTeamOwner 死代码 删 | `src/actions/teams.ts` 删函数 + 删 unused getServerUser import |

### ⏸️ Punt 项（C-FOLLOW-UP）

| ID | 内容 | 推迟原因 |
|----|------|----------|
| P22-3c-1+P22-3c-2 | result 类型统一（StatsResult vs ActionResult）| 跨文件 type 改动大 / 单 session 多子 sprint 串跑预算约束 / 风险高 |
| P22-3c-3+P22-3c-4 | issues.ts + competitor-references.ts 命名规约 | 命名 rename 是大 PR 不适合穿插在多 sprint session / 推 frontend-naming sprint |
| P22-3c-5 | findInTree 抽 lib/tree-utils.ts | 三处 inline 实装位置散 / 推 frontend-utils 抽象 sprint |
| P22-3c-6 | export.ts ExportPayload schema | **需 CY 拍**（A 加 ExportResponse Pydantic schema vs B 删 consumer UI 旧字段）— 本 sprint 不替 CY 拍 |
| P22-3c-8 | project-stats-proxy 文件级 eslint-disable cleanup anchor 删 | 文件本身留作 cleanup 锚点 / 与 P22-3c-1 result 类型统一一并做 |
| eslint ignore 渐进还债 10+ 项 | 单 session 不够时间深入 / 推后续每周技术债 | 渐进还债 |

## 2. 自决说明（feedback_decision_transparency A 模式 / CY 让自决）

**优先级排序**：本子 sprint 取实施成本最低 / 价值最高的 3 项（P22-3b-1 + P22-3c-7 + P22-4-2）：
- 共同特征：mechanical refactor / 0 决策成本 / lint+vitest 守护可验证零回归
- 推后的 7 项要么需要 CY 拍（P22-3c-6）/ 要么是大范围 rename（P22-3c-3/4）/ 要么是抽象设计（P22-3c-5）
- 单 session 4 子 sprint 串跑预算约束下，深度做 3 项 > 浅度做 10 项

**3-5 月后果**：剩 7 项 punt 进 cross-sprint pool C-FOLLOW-UP；不影响上线（架构演示价值已达 / 这些是开发体验改善）。

## 3. R1+R2 范式

**自决跳过**（同子 sprint B PARTIAL 理由）：
- C 范围是 mechanical cleanup / lint + vitest 双重守护已足
- R1+R2 reviewer 价值在新决策 / 新业务 / 接口分歧时；本 sprint 0 新决策
- punt 进 audit 显式声明（防止未来误以为"前端继承形态收官"必须含 R 范式）

## 4. 关闸 commit

`Phase 2.3 子 sprint C (PARTIAL) — withAuthRedirect helper + logActivity no-op cleanup + isTeamOwner dead code 删`

下一站：子 sprint D perf 评估。
