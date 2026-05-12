---
title: prism-0420 _handoff 文件索引
status: living-doc
owner: CY
created: 2026-05-12
last_updated: 2026-05-12
purpose: |
  集中索引 _handoff/ 全部文件，按"做的内容"分类 + 每个加状态。
  新 session cold-start 先看本文件判断从哪入手。
---

# _handoff/ 索引

> **状态枚举**：✅ DONE / 🟡 PARTIAL / ⬜ TODO / 📁 living-doc（持续更新 / 不归类完成）/ 📦 归档候选

---

## 🔴 必读 / 跨 session 元（permanent living-doc）

| 文件 | 用途 | 状态 | 最后更新 |
|------|------|------|---------|
| **[INDEX.md](INDEX.md)** | 本文件 / 全 handoff 索引 | 📁 | 2026-05-12 |
| **[cross-sprint-punt-pool.md](cross-sprint-punt-pool.md)** | 跨 sprint Punt 池总表 + 真漏洞表 + 8 个元发现 | 📁 | 2026-05-12（元发现 #8 立规）|
| **[next-session.md](next-session.md)** | 跨 session 交接旧总表（被 progress.md 部分取代）| 📁 已过时 | 2026-05-12（Sprint 3.1+3.2 状态 / 未含 dogfooding sprint）|

---

## 1️⃣ 设计 / 规划类（Plan / Roadmap）

| 文件 | 对应 sprint | 状态 | 备注 |
|------|------------|------|------|
| **[dogfooding/00-plan.md](dogfooding/00-plan.md)** | Dogfooding 全功能测试 sprint（5-phase / 8 agent / 3 路径决策）| 📁 living | 2026-05-12 落地 / CY 拍 A 路径全跑 |
| [post-phase23-cleanup-plan.md](post-phase23-cleanup-plan.md) | Post-Phase-2.3 cleanup 4 sprint plan | 🟡 PARTIAL | Sprint 1+2+3+4 部分跑过；2026-05-10 后续被 phase23-integration-cleanup-prompts.md 取代 / 候选归档 📦 |

---

## 2️⃣ 实施 / 写代码类（Sprint 启动 prompt 集）

| 文件 | 对应 sprint | 状态 | 备注 |
|------|------------|------|------|
| [sprint-prompts-M05-M20.md](sprint-prompts-M05-M20.md) | M05-M20 后端 16 模块 sprint 启动 prompt | ✅ DONE | 2026-05-07 落地 / 17 模块全 accepted+implemented（M09 superseded by M18）|
| [m20-sprint-prompt.md](m20-sprint-prompt.md) | M20 团队模块（最后一个 own 模块）单独 sprint | ✅ DONE | 2026-05-09 落地 / M20 已完成 |
| [p22-sprint-prompt.md](p22-sprint-prompt.md) | Phase 2.2 前端继承 总 sprint | ✅ DONE | 2026-05-09 落地 / Phase 2.2 100%（但揭露关闸盲区 #2 数据形态迁移半完成）|
| [p22-subslice-prompts.md](p22-subslice-prompts.md) | Phase 2.2 子片 1-5 冷启动 prompts | ✅ DONE | 2026-05-09 落地 / 7/7 子片完 |
| [phase23-prompts.md](phase23-prompts.md) | Phase 2.3 集成验证 + 上线准备 4 子 sprint A/B/C/D | ✅ DONE | 2026-05-09 落地 / A/B/C/D 都跑过 / 被 phase23-integration-cleanup-prompts.md 接续 |
| [phase23-integration-cleanup-prompts.md](phase23-integration-cleanup-prompts.md) | Phase 2.3 cleanup S1-S10 子片 prompts | ✅ DONE | 2026-05-12 跑完（S1+S3+S4+B+A+C+D）/ tsc 88→0 / next build PASS / pytest 1643 PASS / CI 6/6 绿 |

---

## 3️⃣ 测试类（Dogfooding sprint / 当前在跑）

### 3.1 dogfooding/ 总览

| 文件 / 目录 | 用途 | 状态 |
|-----------|------|------|
| **[dogfooding/00-plan.md](dogfooding/00-plan.md)** | 总 sprint plan（同上 §1）| 📁 living |
| **[dogfooding/progress.md](dogfooding/progress.md)** | single source of truth / 每 session 起点必读 | 📁 living（2026-05-12 evening：P0 ✅ / P1 1/21 进展）|

### 3.2 dogfooding/prompts/（subagent 提示词）

| 文件 | Phase / Role | 状态 | 备注 |
|------|------------|------|------|
| [phase1-testpoint.md](dogfooding/prompts/phase1-testpoint.md) | P1 单模块测试点生成（Opus / $3 cap）| 🟡 PARTIAL | M01 pilot ✅ / 剩 20 模块 + cross-cutting |
| [phase4-fix.md](dogfooding/prompts/phase4-fix.md) | P4 bug 修复 + 6 项风险自评（Opus / $5）| ⬜ TODO | 待 P3 产出 bug-queue 后启 |
| [phase4-audit.md](dogfooding/prompts/phase4-audit.md) | P4 design-conflict-audit（Opus / $4）| ⬜ TODO | 同上 |
| _phase2-case.md_ | P2 testpoint → playwright spec | ⬜ TODO | 待 P1 完后再写 |
| _phase3-executor.md_ | P3 跑 playwright + 失败入队 | ⬜ TODO | 待 P2 完后再写 |
| _phase4-rca.md_ | P4 RCA 4 段 + 类似问题 grep | ⬜ TODO | 待 P4 fix 完后再写 |
| _phase5a-regression.md_ | P5 regression 重跑 | ⬜ TODO | 待 P4 完后再写 |
| _phase5b-report.md_ | P5 final report + phase3 v0.4 | ⬜ TODO | 待 P5a 完后再写 |

### 3.3 dogfooding/01-testpoints/（P1 输出）

| 文件 | 模块 | 状态 | testpoint 数 |
|------|------|------|-------------|
| [M01-user-account.md](dogfooding/01-testpoints/M01-user-account.md) | M01 auth pilot | ✅ DONE | 127（P0=45 / P1=69 / P2=13）|
| _M02-M20 + cross-cutting_ | 其他 20 模块 + 跨视角 | ⬜ TODO | 估 ~1500 累计 |

### 3.4 dogfooding/02-cases/ + 04-bug-fixes/（待跑）

| 目录 | 内容 | 状态 |
|------|------|------|
| dogfooding/02-cases/ | P2 输出占位（实际 spec 落到 app/e2e/dogfooding/）| ⬜ TODO |
| dogfooding/04-bug-fixes/B*/ | 每 bug 一目录（case + fix + audit + rca + regression）| ⬜ TODO |

---

## 4️⃣ 归档候选（📦 / 已被取代或过时）

| 文件 | 建议 | 理由 |
|------|------|------|
| post-phase23-cleanup-plan.md | 📦 移到 _archive/ | 2026-05-10 文档 / 被 phase23-integration-cleanup-prompts.md 5/12 完整 cleanup sprint 取代 |
| phase23-prompts.md | 📦 移到 _archive/ | 原计划 4 子 sprint A/B/C/D / 被 cleanup-prompts S1-S10 接续 / 历史价值仍在但不再活跃 |
| m20-sprint-prompt.md / p22-sprint-prompt.md / p22-subslice-prompts.md / sprint-prompts-M05-M20.md | 📦 一组打包归档 | 全 sprint 已完成 / 历史价值仍在 |
| next-session.md | ⚠️ 严重过时（5/10 状态 / 未含 dogfooding）/ 短期保留 | dogfooding sprint 接力点已迁到 dogfooding/progress.md / 候选废弃或刷新 |

**归档建议**：建 `_handoff/_archive/` 目录 / 把 ✅ DONE 类历史 sprint 文件 mv 进去 / 保留 README 索引。

---

## 状态汇总

| 状态 | 数 | 占比 |
|------|-----|------|
| 📁 living-doc（永久跟踪）| 4 | 19% |
| ✅ DONE（已运行）| 6 + M01 pilot = 7 | 33% |
| 🟡 PARTIAL（部分运行）| 3（dogfooding P1 + cleanup-plan + dogfooding-prompt phase1）| 14% |
| ⬜ TODO（未运行）| 7（dogfooding P2-P5 + M02-M20 testpoints）| 33% |

---

## 推荐 cold-start 决策树

```
新 session 起手:
  ↓
  cat _handoff/INDEX.md（本文件 / 拿全图）
  ↓
  当前活跃 sprint?
  ├── dogfooding 测试 sprint（最新 / 2026-05-12 起）
  │     → cat dogfooding/progress.md
  │     → cat dogfooding/00-plan.md
  │     → cat dogfooding/prompts/phase<N>-*.md
  │     → 进具体任务
  │
  └── 没在跑活跃 sprint / 想做其他事
        → cat cross-sprint-punt-pool.md 看真漏 + 元发现
        → cat next-session.md 看历史交接（注意已过时）
```

---

## 维护

- 每完成一个 sprint → 把对应 sprint-prompt 文件状态从 ✅ DONE → 📦 归档候选 / 更新本 INDEX.md
- 新建 sprint → 在对应分类下追加 / 含 created / 对应 sprint / 状态
- 跨 session 元（punt pool / progress / index）→ 持续更新 / 不归档
