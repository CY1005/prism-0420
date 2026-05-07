---
title: Phase Gate Bypass Log
status: living
owner: CY
created: 2026-05-07
purpose: |
  CY 自我约束机制（00-phase-gate.md "CY 自我约束"段）：
  每次想绕闸门必须写一条理由到本文件。累计绕 ≥ 2 次 → 触发对闸门规则本身的 review。
---

# Phase Gate Bypass Log

| # | 日期 | 闸门 | 绕的项 | 理由 | 配套承诺 |
|---|------|------|--------|------|---------|
| 1 | 2026-05-07 | 闸门 3 | 第 3 项「simplify-checklist 三 Agent 流水线在 M01 PR 上实际跑过一次」 | M01 范式简单（read-only auth + admin endpoints，118 PASS / 0 xfail / lint 净），三 Agent reviewer 在已稳定代码上只能挑 minor finding；M02（项目管理：跨 project 关系 / ADR-004 凭据路径 / PROJECT_ARCHIVED 状态机 / tenant 隔离 / 可能 baseline-patch space_id→team_id）技术复杂度上一台阶，三 Agent + simplify 在 fresh code 上首跑训练价值更高 | M02 sprint **必须真跑**三 Agent + simplify checklist；不能再用 main agent self-audit 替代，否则触发对闸门规则本身的 review（已是第 2 次） |

## Review 触发线

- 累计 ≥ 2 次绕闸 → 必须停下来 review 闸门规则本身（是不是闸门定错了 / 闸门项是否需要分级 / 是否需要"等价替代"明确写入）
- 当前累计：**1 次**

## 维护

- 新绕闸门 → 追加 1 行
- 触发 review → 在 `00-phase-gate.md` 修订并交叉引用本文件对应行
