---
last_session: 2026-05-12 night (batch 1)
phase: P1 (testpoint generation)
sub_task: M01 pilot ✅ + 批 1 (M11/M14/M19/M20) ✅ / 批 2-5 + cross-cutting 待并行
cost_cumulative: $52 (M01 pilot) + ~$3.9 (批 1 4 subagent)
status: NORMAL / 自然 checkpoint / 批 1 完成 / 可继续批 2 或切新 session
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

- **P1 testpoint** 🟡 IN_PROGRESS（5/21 完成 / 批 1 done）
  - ✅ M01 user-account / 127 testpoint（P0=45 / P1=69 / P2=13）/ 14 视角 / cost ~$2
    - 文件：`01-testpoints/M01-user-account.md`
    - 质量验证：每条引 design §N + tests.md GN / 单行 / 无 forbidden / 全 self-check 通过
  - ✅ M11 cold-start / 91 testpoint（P0=30 / P1=52 / P2=8 / 实 grep 90）/ 14 视角 / cost ~$1.5
    - 文件：`01-testpoints/M11-cold-start.md`（152 行）
    - 风险点：R-X1 orchestrator 首例 / 共享 db.begin() 跨 service 回滚 / G2/G6 无 idempotency / completed/failed 终态 409 / 10MB+1000 行同步阈值
    - PRD F11 章节未显式存在 → 改引 US-A1.5 + PRD Q3.1（frontmatter 已注）
  - ✅ M14 industry-news / 89 testpoint（P0=27 / P1=46 / P2=16）/ 14 视角 / cost ~$0.6
    - 文件：`01-testpoints/M14-industry-news.md`（151 行）
    - 风险点：首个全局豁免业务模块（GLOBAL DATA NO TENANT FILTER）/ link/unlink 权限裁决 / source_type='manual' 双重防护 / IntegrityError 区分约束名 / 过去式 action_type / activity_log 非事务
  - ✅ M19 import-export / 86 testpoint（P0=25 / P1=46 / P2=15）/ 14 视角 / cost ~$0.6
    - 文件：`01-testpoints/M19-import-export.md`（148 行）
    - 风险点：action_type "exported" 4 处同步漂移 / Content-Disposition filename sanitize 输出端首发 / 跨 project node 走 422 而非 404 / viewer 写 activity_log / EXPORT_EMPTY_CONTENT 422 优先空报告
  - ✅ M20 team / 128 testpoint（P0=61 / P1=62 / P2=5）/ 12 视角 / cost ~$1.2 / **escalation surface ≥100 → 已按 P0/P1/P2 拆好**
    - 文件：`01-testpoints/M20-team.md`（186 行）
    - 风险点：R-X3 跨事务签名首发 / L3 SQL 注入横切 M03-M19 / correlation_id F2.9 + R10-1 批量独立 N+1 / 嵌套 max(team_role, project_role) 10 组合 / archived × team 双路径互锁 F2.3
    - 复杂度最高单 sprint（design §14.5 R-X5 实证）/ P0 占比 47.7% 偏高合理
  - ⬜ M02 project
  - ⬜ M03 module-tree
  - ⬜ M04 feature-archive
  - ⬜ M05 version-timeline
  - ⬜ M06 competitor
  - ⬜ M07 issue
  - ⬜ M08 module-relation
  - ⬜ M10 overview
  - ⬜ M12 comparison
  - ⬜ M13 requirement-analysis
  - ⬜ M15 activity-stream
  - ⬜ M16 ai-snapshot
  - ⬜ M17 ai-import
  - ⬜ M18 semantic-search
  - ⬜ _cross-cutting（auth / cookie / 网络 / 跨 tab / mobile / 性能）

  ### 批 1 汇总（M11/M14/M19/M20 / 4 模块）
  - **testpoint 总数**：394（P0=143 / P1=206 / P2=44 = M01 不计 / 批 1 累计）
  - **cost**：~$3.9（远低于估 $4 / 4 subagent 4 并发）
  - **跨模块元发现**（design 推导的 surface 候选）：
    - R-X1 orchestrator 首例（M11）+ R-X3 跨事务签名首发（M20）→ design 中 R-X 系列横切纪律集中爆发 / 建议 cross-cutting 视角单立测试集
    - 全局豁免业务模块（M14 首发）+ 跨 project 只读消费（M19）→ tenant 隔离边界 2 类例外，需要 cross-cutting 集中规约
    - activity_log 失败传播 4 模块全覆盖（M16 范式 / M11/M14/M19/M20 复用）→ 已成横切纪律
    - action_type 同步漂移 M14（5 个过去式）+ M19（4 处同步）→ CI 守护 / 设计漂移防御视角必须有专项
    - filename sanitize 输出端首发（M19）→ 后续 M17/M18 导出场景复用范式

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
4. `cat _handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`（含 4 并发 invoke 示例 / 6 变量替换清单）
5. `cat _handoff/dogfooding/01-testpoints/M11-cold-start.md` 抽样看批 1 实战输出（128 testpoint 上限 / 14 视角 / 单行 / 引 design §N）

## 下一 session 任务（启 P1 剩余 14 模块 / 批 2-5）

**策略**：并行启动（按 [[feedback_usage_budget]] 信号 A 节流 / 最多 4 并发 Opus subagent）

**批 1 实战观察**（影响后续批次决策）：
- 4 个"边缘模块"实际 testpoint 数 86-128（远超估 30-50）/ 不阻塞但 cost 比估高 / 批 2-4 估算应 +50%
- M20 触发 ≥100 escalation surface 但不阻塞 / 按 P0/P1/P2 已拆好 / 后续大业务模块应预期同等触发
- 4 并发 Opus 单批次实际 cost ~$3.9（接近 $4 估）/ 单 session $10 软上限可装 2 批
- 风格红线全过（0 forbidden 真违反 / 1 false positive 词频）/ prompt 模板鲁棒
- 元发现：R-X 横切纪律 / tenant 豁免 2 类 / activity_log 失败传播 / action_type 同步漂移 / filename sanitize → cross-cutting 视角需专项

**推荐分批顺序**（按模块复杂度从低到高 / 先简单的验证 prompt 鲁棒性）：

### 批 1（边缘模块 / 30-50 testpoint each / 4 并发）✅ DONE 2026-05-12
- M11 cold-start ✅ 91
- M14 industry-news ✅ 89
- M19 import-export ✅ 86
- M20 team ✅ 128 (escalation surface)

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

**直接读** `_handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`：
- 含完整 prompt 模板（基于 M01 pilot 实际派的 / 含 briefing + 8 项 input contract + Forbidden + Self-check + Cost cap）
- 含 6 个变量替换清单（MODULE_ID / MODULE_NAME / SHORT_NAME / COMPLEXITY / DESIGN_PATH / TESTS_PATH / OUTPUT_PATH）
- 含 18 模块 → name 映射
- 含 4 并发 Agent tool invoke 示例

主 agent cold-start 流程：
1. `cat _handoff/dogfooding/prompts/phase1-testpoint-invocation-template.md`
2. 拿到当前批次 4 个模块的变量值（如批 1: M11/M14/M19/M20）
3. 在单 user message 里发 4 个 Agent tool call 并行
4. 等 4 个 subagent 都返回（约 3-5 min）
5. 抽样验证输出格式（grep H2 视角清单 / grep Forbidden 内容 / wc -l）
6. 一次性 commit `dogfooding P1 batch<N> — 4 modules / <total> testpoints`
7. 更新本 progress.md（M11-M20 列表对应 ✅ + 总数）
8. cost 节流：若本 session 已用 >$8 / 退出 / 下一 session 跑下一批

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
| 2026-05-12 night | $0（新 session）| ~$3.9 | P1 批 1 (M11/M14/M19/M20) 4 并发 / 394 testpoint | $3.9 dogfooding 累计 ~$5.9 |

**预算**：sprint 总 $130-240 / dogfooding 自身已用 ~$5.9 / 剩 $124-234 / 充足。

---

## 阻塞 / 待 CY 拍

- 无（CY 已拍 A 路径 / P1 并行启 20 module 在新 session 跑）

## 注意事项

- 每 P1 subagent prompt 必含 cost cap $3 + 完整 8 项 input contract + Forbidden 清单
- subagent 完成后**不许 commit** / 主 agent 收齐 21 个 module 后一次性 commit
- 长 module（M17/M18/M13）testpoint 数可能 >100 / 不重做 / 接受
- 边缘 module（M11/M14/M20）若 <30 testpoint / 检查是否漏覆盖视角 / 不许凑数
