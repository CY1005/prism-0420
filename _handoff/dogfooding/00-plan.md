---
title: prism-0420 全功能 Dogfooding 测试 Sprint Plan
status: living-doc
owner: CY
created: 2026-05-12
last_updated: 2026-05-12
scope: M01-M20 全功能 + 跨模块用户旅程
trigger_bug: 创建项目后跳 login（dogfooding 触发）
methodology: Approach 3 阶段化 + checkpoint（5 phase × subagent 并行）
references:
  - skill: requirements-to-testpoints（Phase 1 风格）
  - skill: product-quality-audit（5-phase 闭环结构 / 模型分配）
  - memory: [[feedback_subagent_sprint]] T1-T6 接口契约
  - memory: [[feedback_testpoint_style]] 测试点风格红线
  - memory: [[feedback_decision_codefirst_validation]] 决策类 fact-finding 3 步
  - memory: [[feedback_remote_access_audit]] 远程访问 6 项 audit checklist
  - memory: [[feedback_usage_budget]] 单 session $10 软上限 / cost 节流
  - punt pool 元发现 #6 / #7 / #8 / 关闸盲区 #1 / #2 / #3
---

# Dogfooding 测试 Sprint — 总 Plan

> **single source of truth**。每次 session 起点必读。任何进度变化必更新本文件 + `progress.md`。

---

## 0. 项目定位重申

- **目标**：通过 dogfooding 全功能测试，把 prism-0420 从"测试通过/可上线"水位推到"真用得起来"水位（dogfooding 6/8 + 6/15 北极星节点解锁）
- **STAR 价值**：Phase 3 数据对照 v0.4 加 4 dogfooding 维度（testpoint 数 / bug 类别 / 类似 bug 关联率 / design-audit 命中率）
- **触发起点**：dogfooding 时 CY 撞到"创建项目后跳 login"bug → 暴露**测试覆盖+设计审计**双层缺口
- **方法论交付**：6 类 agent + 3 路径 commit 决策 + 跨 session 接力 = 可复用的 AI 测试自动化体系（任何前后端分离 SaaS 都能套）

---

## 1. 5 Phase 架构

```
Phase 1: 测试点生成     [Opus × 21 / 并行]       → 01-testpoints/M<NN>-*.md + _cross-cutting.md
   ↓ checkpoint: testpoints.md ≥1 round CY review
Phase 2: 用例编写       [Sonnet × 20 / 并行]    → app/e2e/dogfooding/M<NN>-*.spec.ts
   ↓ checkpoint: tsc 0 错 / playwright --list 全注册
Phase 3: 测试执行       [Sonnet × 1-2 / 并行]   → 03-bug-queue.md
   ↓ checkpoint: 全 spec 真跑完 / fail case 全入队
Phase 4: bug 闭环       [Opus × N / 串行 + audit] → 04-bug-fixes/B<id>/{case,fix,rca,audit,regression}.md
   ↓ checkpoint: bug-queue.md 全 status=FIX_DONE
Phase 5a: 回归重跑      [Sonnet × 1]              → 05-regression-results.md
Phase 5b: 报告 + STAR   [Opus × 1]               → 05-final-report.md + phase3-data v0.4
   ↓ sprint 结束 / CY review
```

### Phase 间串行 / Phase 内并行

- 跨 phase 严格串行（不允许 P3 没完就开 P4）
- phase 内 subagent 并行（按 [[feedback_usage_budget]] 信号 A 节流 / 最多 4 并发）
- 每 phase checkpoint 必跑 phase 自验证 + commit + 等 CY ack（首次 / 后续可 self-decide）

---

## 2. 8 类 Agent 速查表

| Agent | 模型 | 输入 | 输出 | self-check | commit | escalation |
|-------|------|------|------|-----------|--------|------------|
| **P1 testpoint** | Opus | `design/02-modules/M<NN>/00-design.md` + `design/00-architecture/01-PRD.md` | `01-testpoints/M<NN>-*.md`（[[feedback_testpoint_style]] 叶子单行+[Px]）| preflight + 风格红线 2 条 + 行数 ≥10 | 写文件不 commit | 缺 design→中止 |
| **P2 case** | Sonnet | `01-testpoints/M<NN>-*.md` + `app/e2e/02-create-project.spec.ts` 模板 | `app/e2e/dogfooding/M<NN>-*.spec.ts` | `pnpm exec tsc --noEmit` 0 错 + `pnpm playwright test --list` 注册成功 | 单 commit `dogfooding P2/M<NN> cases` | tsc 错→中止 / 复杂 case escalate Opus |
| **P3 executor** | Sonnet | `app/e2e/dogfooding/M<NN>-*.spec.ts` | `03-bug-queue.md` 追加（失败入队）+ `progress.md` | playwright 真跑完返结果 / 不 skip | 单 commit `dogfooding P3/M<NN> exec — N pass M fail` | 全 fail→中止上报 |
| **P4 fix** | **Opus** | `03-bug-queue.md` 中 1 个 OPEN bug | 风险分级判定 + fix 代码 + `04-bug-fixes/B<id>/fix.patch` | 修复后**真跑 fail case 验证 PASS** + tsc + 相关 unit test + lint | **A/B/C 三路径**（§3） | 风险不确定→C 路径 / [AMBIGUOUS] 标 |
| **P4 audit** | **Opus** | fix.patch（未 commit）+ 改动摘要 + bug 上下文 | `04-bug-fixes/B<id>/design-audit.md` | 已查 ≥6 类文档 / 冲突清单含 4 字段 | 不 commit / 报主 agent | ≥1 冲突→escalate CY |
| **P4 rca** | **Opus** | fix.patch + bug-queue 上下文 + audit 输出 | `04-bug-fixes/B<id>/rca.md`（4 段：现象/根因/类似问题 grep/design 哪步漏）+ punt pool 元发现候选 | 4 段全填 + 类似问题真 grep + 引用 ≥1 design 章节 | 单 commit `RCA B<id> — <one-liner>` | 类似 bug 关联 ≥3→升级元发现候选 |
| **P5a regression-run** | Sonnet | `03-bug-queue.md` + 全 `app/e2e/dogfooding/` | 全套重跑结果（write 到 `05-regression-results.md`）| 100% PASS（或残留入 punt pool）| 单 commit `dogfooding P5a run — <pass-rate>` | <100% 且非合法 punt→escalate |
| **P5b report** | **Opus** | `05-regression-results.md` + 全 `04-bug-fixes/B*/rca.md` + phase3-data v0.3 | `05-final-report.md` + phase3-data v0.4（4 dogfooding 维度）| STAR 4 维度齐全 + 真数据 / 不编造 | 单 commit `dogfooding P5b report — v0.4` | 数据空/缺→escalate |

---

## 3. D 风险分级 + 3 路径 commit 决策

### 6 项自评（P4 fix subagent 必填）

任一 "高" → 启 audit subagent。

| # | 维度 | 低风险 | 中高 |
|---|------|--------|------|
| 1 | 改动范围 | 单文件 ≤30 行 | 跨 ≥2 文件 OR >30 行 |
| 2 | 代码位置 | UI 文案 / 类型 / dev script | backend service / dao / migration / auth / actions schema / api router |
| 3 | 可逆性 | git revert 安全 / 不依赖 schema | 含 migration / data backfill / cookie/session |
| 4 | 业务断言 | 没改业务规则 | 改了状态机 / 权限校验 / 事务边界 / idempotency |
| 5 | 测试覆盖 | 修复后跑现有 test 全绿 | 修复无对应 test / 需新建 |
| 6 | bug 类型 | 类型漂移 / 字段名 / null guard / typo | 数据丢 / 权限绕过 / race / auth bypass |

### 3 路径决策

```
顺序判定（先 AMBIGUOUS / 再高低）：

1. 6 项中任一 AMBIGUOUS / 不确定 → [C escalate CY] / 终止
2. 满足以下任一 → [B 启 audit subagent]
   - 6 项中任一 "高"
   - 改 ≥3 文件
   - 改 design / ADR / migration 文件
3. 全 6 低 + 改 <3 文件 + 不动 design → [A 直推 main]

B 路径 audit 结果：
   ├ 0 冲突 → 同 A 路径 commit + push + 记 audit log
   ├ 仅 low 冲突 → B 路径 commit / commit msg 注 audit-low / 跟 RCA 一起入 04-bug-fixes/B<id>/
   └ ≥1 high/medium 冲突 → [C escalate CY] / fix 不落
```

### Commit 模板

```
# A 路径直推 main:
dogfooding fix B<id> — <one-line>

Risk: low（6/6 通过自评）
Test: <修复后跑的 test 命令 + 结果>
RCA: 见 04-bug-fixes/B<id>/rca.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

# B 路径（audit 通过后直推）:
dogfooding fix B<id> — <one-line>

Risk: medium（自评 N/6 高，audit 0 冲突）
Audit: 04-bug-fixes/B<id>/design-audit.md
Test: <...>
RCA: 04-bug-fixes/B<id>/rca.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### 安全网（每 commit 后强制）

1. `pnpm exec tsc --noEmit` 必 0 错
2. `pytest tests/test_m<NN>_*.py` 相关 unit test 必 PASS
3. push 后 watch `gh run watch` 1-2 min CI 全绿才进下一 bug
4. CI 红 → 立即 revert + 升 PR + 标 [CI-CAUGHT]

---

## 4. 跨 Session 接力

### `progress.md` single source of truth

任何 session 起点 / 第一行 cat 它。任何 session 结束前最后一步更新 + commit 它。

### Cold-start 4 步

1. `cat _handoff/dogfooding/progress.md` 拿状态
2. `cat _handoff/dogfooding/00-plan.md` 拿总 plan
3. `cat _handoff/dogfooding/prompts/phase<N>-<role>.md` 拿当前 agent 提示词
4. `cat <当前任务文件>` 进入具体上下文

### Session cost 节流

按 [[feedback_usage_budget]]：

- session cost > **$5** → 报 CY 预算 + 让 CY 拍是否继续
- session cost > **$10**（软上限）→ 强制 commit + 退出 + 写 progress.md / 新会话续

### Sprint 总 cost 估算

| Phase | 模型 × 数 | 单价 | 估 |
|-------|----------|------|-----|
| P1 testpoint | Opus × 21 (20 模块 + 1 cross-cutting) | $2-3 | $40-60 |
| P2 case | Sonnet × 20（1-2 复杂 escalate Opus）| $1 | $20-25 |
| P3 executor | Sonnet × 1-2 | $1 | $2-3 |
| P4 fix | Opus × 8-15 bug | $3-5 | $30-75 |
| P4 audit | Opus × (8-15 × 30-40% 触发) | $3-5 | $10-25 |
| P4 rca | Opus × 8-15 | $2-3 | $20-45 |
| P5a regression run | Sonnet × 1 | $2 | $2 |
| P5b report | Opus × 1 | $3-5 | $3-5 |
| **总** | | | **$130-240 / 跨 8-12 session** |
- 每 phase 结束（首次跑）→ 100% 退出等 CY ack / 后续可 self-decide
- 全 sprint 估 **$130-240** / 跨 **8-12 session**

---

## 5. 验收标准

### 单 phase 验收 (checkpoint)

- P1 ✅: 21 个 `M<NN>-*.md` + `_cross-cutting.md` 全产 / 每模块 ≥10 testpoint / 风格红线全过
- P2 ✅: `app/e2e/dogfooding/M<NN>-*.spec.ts` 全产 / `tsc --noEmit` 0 错 / playwright --list 全注册
- P3 ✅: 全 spec 真跑 / `03-bug-queue.md` 列全失败 + status
- P4 ✅: bug-queue 全 status → FIX_DONE / `04-bug-fixes/B<id>/` 三件套（A 路径）或四件套（B 路径）齐全
- P5 ✅: regression **100% PASS**（或残留入 punt pool）/ `05-final-report.md` 写完

### 整体 Sprint 验收

- ✅ 100% test PASS 或残留**全部入 punt pool 真漏洞表**（不许悄悄 punt）
- ✅ design-audit 0 冲突 unresolved
- ✅ phase3-data-baseline.md 加 dogfooding 4 维度 → v0.4
- ✅ CI 6/6 jobs 全绿
- ✅ punt pool 元发现新增（如发现新模式）

---

## 6. Final Report 数据维度（phase3 v0.4）

继 v0.3 STAR 三维度（天数 1.77x / commits 3.44x / fix commits 0.61x → 减 39% bug），v0.4 加 4 dogfooding 维度：

| 维度 | 计算 | STAR 价值 |
|------|------|----------|
| **D1 testpoint 总数 / pass rate** | M01-M20 行数 sum + pass率（init / after fix）| "200+ testpoint 覆盖全功能 / 一次跑过 N% / fix 后 100%" |
| **D2 bug 类别分布** | RCA 文件 grep 模式（契约漂移 / cookie / shape / SSR/hydration / auth）| "design-first 残余 bug 几乎全是工程/集成类 / 0 业务逻辑 bug" |
| **D3 类似 bug 关联率** | RCA "类似问题 grep" 段 / 平均挖出 N 处隐藏同模式 | "每 bug 平均挖出 N 个同根因隐藏 bug → RCA 闭环 multiplier" |
| **D4 design-audit 命中率** | N 个 fix 触发 audit / M 个找出真冲突 | "<5% audit 命中 = 设计原则跟实施真对齐" |

---

## 7. 与 ROADMAP 关系

- ✅ 6/8 dogfooding 启动节点：本 sprint 启动即达成
- ✅ 6/15 dogfooding 全量节点：本 sprint Phase 5 完成时达成
- 🟢 Phase 3 报告 v0.4：本 sprint 直接产出
- 🟢 M5 STAR 素材 +N：每 bug 一个完整闭环 = 简历级素材

---

## 8. 失败信号（Sprint 失效）

- ❌ 单 bug fix 跑超 4 个 session 仍未关闭 → 强制 escalate CY + 评估 punt 还是降级 sprint
- ❌ Phase 4 audit 连 ≥3 个 bug 报冲突 → sprint 暂停 / 评估 design 是否需要更新
- ❌ phase3 data v0.4 跑出来 fix 数 ≥ v1 → 重新评估方法论（理论 design-first 应减 bug）
- ❌ 跨 session 第 3 次 progress.md 丢失/未更新 → sprint 流程失效 / 用 cron 强制 sync
