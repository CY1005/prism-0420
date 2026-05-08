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
| 2 | 2026-05-09 | 闸门 3.4 L1 | M16 sprint R1 + R2 review subagent spawn 全降级为 main agent self-checklist | M16 sprint 在同一会话连跑 7 commit（子片 0 prep + 0.5 batch×2 + 子片 1+2+3+4），context 已堆 >150k；24h usage 信号 🔴 long-context + subagent-heavy 已存在（M11+M15 sprint 余波）；spawn 1 R1 + 1 R2 Opus 会推高 cost。元教训 17 条 actionable 防御已在子片 0 prep §14.5 + 子片 4 e2e 主动写入（viewer 写 403 / cross-tenant / cross-project node / metadata 字面 / write_event 异常传播 / 双层防御 / path mismatch / 14 ErrorCode raise 全覆盖）；19 e2e tests 100% PASS + 1063 PASS 总；R13-1 116 + R14 守护通过 = self-checklist 已替代外部 reviewer 大部分覆盖面 | **下一 sprint（M17 异步 zip 导入 / 首个 arq Queue 消费者 / R-X1 orchestrator 第二实例 / 闸门 2.6 mini-sprint）必须真跑 R1=3 subagent 并行 + R2=1 合并 Opus**；不再用 main agent self-审；M17 是技术复杂度上台阶（commit boundary 重构 / TaskPayload 基类 / Redis worker 部署），外部 reviewer 价值高。同时触发对闸门 3.4 L1 总则的 review（累计绕 = 2 次 / 触发线已达）—— 在 M17 sprint 启动子片 0 prep 时把"context budget pressure 触发降级"显式写入 L1 总则的"触发例外"段（与"≥80% SKIP"并列） |

## Review 触发线

- 累计 ≥ 2 次绕闸 → 必须停下来 review 闸门规则本身（是不是闸门定错了 / 闸门项是否需要分级 / 是否需要"等价替代"明确写入）
- 当前累计：**2 次** ✅ **已 review + 修订完成 2026-05-09**（M17 启动期）
  - 修订内容：00-phase-gate.md 闸门 3.4 L1 总则"触发例外"段从 1 类（≥80% SKIP）
    扩到 3 类（a ≥80% SKIP + b context budget pressure + c 临时合并 = bypass log）
  - **b "context budget pressure" 条款双前置条件 + 3 配套承诺**（不是无条件降级）：
    - 双前置：24h 🔴 long-context + 🔴 subagent-heavy 同时 + 本 sprint ≥17 条 actionable 元教训主动写入子片 4 e2e
    - 配套：下一 sprint 必恢复 spawn / 启动期必查上一 sprint 配套承诺兑现 / 累计 self-审 ≥2 连续触发 review
  - 触发线 **不复位**，继续累计；条款 b 第 3 条要求"累计 self-审 ≥2 连续"独立触发对 b 本身 review

## 维护

- 新绕闸门 → 追加 1 行
- 触发 review → 在 `00-phase-gate.md` 修订并交叉引用本文件对应行
