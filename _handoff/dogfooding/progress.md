---
last_session: 2026-05-12 evening
phase: P1 (testpoint generation)
sub_task: M01 pilot ✅ / 其他 20 模块 + cross-cutting 待并行
cost_cumulative: $50 (this session) + ~$2 (M01 subagent)
status: NORMAL / 自然 checkpoint / 切新 session
---

# Dogfooding Sprint Progress

> single source of truth。每 session 起点必 cat 本文件。每 session 结束必更新 + commit。

---

## Phase 完成状态

- **P0 preflight** ✅ DONE
  - ✅ 00-plan.md 落地（commit 256ae8e）
  - ✅ progress.md 初始化
  - ✅ 目录结构创建
  - ✅ 3 核心 prompt 落地（phase1-testpoint / phase4-fix / phase4-audit）
  - ✅ CY review 00-plan + 3 prompt → 拍 A 路径接受现状全跑

- **P1 testpoint** 🟡 IN_PROGRESS（1/21 完成）
  - ✅ M01 user-account / 127 testpoint（P0=45 / P1=69 / P2=13）/ 14 视角 / cost ~$2
    - 文件：`01-testpoints/M01-user-account.md`
    - 质量验证：每条引 design §N + tests.md GN / 单行 / 无 forbidden / 全 self-check 通过
  - ⬜ M02 project
  - ⬜ M03 module-tree
  - ⬜ M04 feature-archive
  - ⬜ M05 version-timeline
  - ⬜ M06 competitor
  - ⬜ M07 issue
  - ⬜ M08 module-relation
  - ⬜ M10 overview
  - ⬜ M11 cold-start
  - ⬜ M12 comparison
  - ⬜ M13 requirement-analysis
  - ⬜ M14 industry-news
  - ⬜ M15 activity-stream
  - ⬜ M16 ai-snapshot
  - ⬜ M17 ai-import
  - ⬜ M18 semantic-search
  - ⬜ M19 import-export
  - ⬜ M20 team
  - ⬜ _cross-cutting（auth / cookie / 网络 / 跨 tab / mobile / 性能）

- **P2 case** ⬜ NOT_STARTED
- **P3 executor** ⬜ NOT_STARTED
- **P4 闭环** ⬜ NOT_STARTED
- **P5 final** ⬜ NOT_STARTED

---

## 已发现 bug 池（前置 / dogfooding 触发）

| ID | 现象 | 来源 | status |
|----|------|------|--------|
| B-pre-1 | 创建项目后跳 login（应进项目详情）| CY dogfooding 2026-05-12 | OPEN / 待 P4 入 |

---

## 下一 session cold-start 顺序

1. `cat _handoff/dogfooding/progress.md`（本文件 / 起点）
2. `cat _handoff/dogfooding/00-plan.md`（§2 8 类 agent + §5 验收 / 拿总 plan）
3. `cat _handoff/dogfooding/prompts/phase1-testpoint.md`（P1 提示词 / 跟 M01 pilot 用同一份）
4. `cat _handoff/dogfooding/01-testpoints/M01-user-account.md` 抽样看格式（参考 pilot 输出 / 14 视角 H2 + 单行 testpoint + 引 design §N）

## 下一 session 任务（启 P1 剩余 20 模块）

**策略**：并行启动（按 [[feedback_usage_budget]] 信号 A 节流 / 最多 4 并发 Opus subagent）

**推荐分批顺序**（按模块复杂度从低到高 / 先简单的验证 prompt 鲁棒性）：

### 批 1（边缘模块 / 30-50 testpoint each / 4 并发）
- M11 cold-start
- M14 industry-news
- M19 import-export
- M20 team

### 批 2（主流业务 / 50-80 testpoint each / 4 并发）
- M02 project
- M03 module-tree
- M04 feature-archive
- M05 version-timeline

### 批 3（主流业务续 / 4 并发）
- M06 competitor
- M07 issue
- M08 module-relation
- M10 overview
- M12 comparison

### 批 4（AI / 复杂业务 / 80-120 testpoint each / 4 并发）
- M13 requirement-analysis
- M15 activity-stream
- M16 ai-snapshot
- M17 ai-import
- M18 semantic-search

### 批 5（跨模块视角）
- _cross-cutting（单独 subagent / 按视角而非模块）

### 单次 subagent prompt 模板

复制 M01 pilot prompt（见本 session git log）/ 替换 `M01 user-account` → 当前模块 / 调整 design path / output path。

### Cost 估算（P1 剩余）

- 批 1（4 module）：4 × $1 = $4
- 批 2（4 module）：4 × $2 = $8
- 批 3（5 module）：5 × $2 = $10
- 批 4（5 module）：5 × $2.5 = $12.5
- 批 5（cross-cutting）：1 × $2 = $2
- **P1 总剩余: ~$36-40**
- 跨 5-6 session（每 session 4 模块 / cap $10）

### Checkpoint

P1 全完成（21 个 testpoints 文件齐全）后：
1. CY review 抽样 3-4 模块
2. 主 agent 一次性 commit `dogfooding P1 done — 21 testpoints / N total`
3. 跑 phase3 数据脚本看 testpoint 数维度 baseline（D1）
4. 进 P2 case

---

## Cost 跟踪

| Session | 起 | 终 | 内容 | 累计 |
|---------|-----|-----|------|------|
| 2026-05-12 init | — | — | 00-plan + progress init | $0 |
| 2026-05-12 evening | $50（前置 sprint）| ~$52 | P0 prompts + M01 pilot | $52 |

**预算**：sprint 总 $130-240 / 当前已用 $2（dogfooding 自身）/ 剩 $128-238 / 充足。

---

## 阻塞 / 待 CY 拍

- 无（CY 已拍 A 路径 / P1 并行启 20 module 在新 session 跑）

## 注意事项

- 每 P1 subagent prompt 必含 cost cap $3 + 完整 8 项 input contract + Forbidden 清单
- subagent 完成后**不许 commit** / 主 agent 收齐 21 个 module 后一次性 commit
- 长 module（M17/M18/M13）testpoint 数可能 >100 / 不重做 / 接受
- 边缘 module（M11/M14/M20）若 <30 testpoint / 检查是否漏覆盖视角 / 不许凑数
