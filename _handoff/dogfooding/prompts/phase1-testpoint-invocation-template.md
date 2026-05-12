# P1 subagent invocation 模板

> 主 agent 派 P1 subagent 时直接复制本模板 / 替换变量 / Agent tool 发出。
> 基于 2026-05-12 M01 pilot 真实 invoke 复用 / commit 70050ae 之前 Agent invoke 记录。

---

## 变量替换清单

派 subagent 前替换以下 6 个变量：

| 变量 | M11 例 | M14 例 | M19 例 | M20 例 | M17 例 |
|------|-------|-------|-------|-------|-------|
| `{MODULE_ID}` | M11 | M14 | M19 | M20 | M17 |
| `{MODULE_NAME}` | cold-start | industry-news | import-export | team | ai-import |
| `{SHORT_NAME}` | cold-start | industry-news | import-export | team | ai-import |
| `{COMPLEXITY}` | 边缘 / 30-50 估 | 边缘 / 30-50 | 边缘 / 30-50 | 边缘 / 30-50 | 复杂 / 80-120 |
| `{DESIGN_PATH}` | `design/02-modules/M11-cold-start/00-design.md` | `design/02-modules/M14-industry-news/00-design.md` | ... | ... | ... |
| `{TESTS_PATH}` | `design/02-modules/M11-cold-start/tests.md`（如存在） | ... | ... | ... | ... |
| `{OUTPUT_PATH}` | `_handoff/dogfooding/01-testpoints/M11-cold-start.md` | ... | ... | ... | ... |

模块 ID → name 映射（按 `design/02-modules/` 目录）：

```
M02 = project
M03 = module-tree
M04 = feature-archive
M05 = version-timeline
M06 = competitor
M07 = issue
M08 = module-relation
M10 = overview
M11 = cold-start
M12 = comparison
M13 = requirement-analysis
M14 = industry-news
M15 = activity-stream
M16 = ai-snapshot
M17 = ai-import
M18 = semantic-search
M19 = import-export
M20 = team
```

（M01 已完成 / M09 superseded by M18 / 跳过）

---

## Agent tool invoke 参数

```yaml
description: P1 testpoint pilot {MODULE_ID}
subagent_type: general-purpose
model: opus
prompt: <见下方完整 prompt>
```

---

## 完整 Prompt 模板（替换 6 个 {{变量}} 后复制）

```markdown
你是 prism-0420 dogfooding sprint 的 **P1-testpoint subagent**。任务：为 **{{MODULE_ID}} {{MODULE_NAME}} 模块** 生成测试点。

## 你不知道的项目背景（briefing）

prism-0420 是 CY 的 Shadow 项目 / 跟 prism v1 同需求 / 用"设计前置 → AI 实现"策略重写 / 目标是验证方法论价值。Phase 2.3 集成验证刚完成（tsc 0 / 1643 PASS / next build 全绿 / CI 全 6 jobs 绿）/ 现在启动 dogfooding 全功能测试 sprint。

你是这个 sprint 的 Phase 1 一个 subagent / Phase 1 共 21 个 subagent 跑（20 模块 + 1 cross-cutting）/ M01 pilot 已跑通 / 其他模块批量并行。

## Cost cap

$3。超即 commit 当前进度 + 退出 / 不无限跑。

## Input contract（必读 / 按顺序）

1. `/root/workspace/projects/prism-0420/_handoff/dogfooding/00-plan.md`（§2 8 类 agent / §5 验收 / 你的角色：P1 行）
2. `/root/workspace/projects/prism-0420/_handoff/dogfooding/prompts/phase1-testpoint.md`（你的完整提示词 / **必读** / 包含 self-check 5 项 + Forbidden 清单 + Output 模板）
3. `/root/workspace/projects/prism-0420/{{DESIGN_PATH}}`（{{MODULE_ID}} 完整 design / 重点：§1 业务说明 / §3 数据模型 / §4 状态机 / §7 API 契约 / §8 权限 / §10 activity_log / §11 idempotency / §14 测试场景）
4. `/root/workspace/projects/prism-0420/{{TESTS_PATH}}`（已有测试场景 / 不重复但要覆盖 / 如文件不存在跳过）
5. `/root/workspace/projects/prism-0420/design/00-architecture/01-PRD.md`（PRD 验收条件 AC）
6. `/root/workspace/projects/prism-0420/design/00-architecture/06-design-principles.md`（5 核心 + 5 约束 / 推导风险点）
7. `/root/.claude/projects/-root/memory/feedback_testpoint_style.md`（**风格红线 2 条 / 绝对不许违反**）
8. `/root/.claude/skills/requirements-to-testpoints/references/结构化思维框架.md`（15 角度框架）

## Forbidden（违反 = 重做）

按 `phase1-testpoint.md` Forbidden 清单：

- ❌ 子项 / 步骤 / 断言 / 业务影响（feedback_testpoint_style 红线 / 叶子单行）
- ❌ 凭印象写 / 必须基于 design 文档具体内容
- ❌ 跳过权限 / tenant 隔离视角（除非该模块明文 N/A）
- ❌ 跨模块测试点写在本模块（属于后续 `_cross-cutting.md`）

## Output contract

写入：`/root/workspace/projects/prism-0420/{{OUTPUT_PATH}}`

格式严格按 `phase1-testpoint.md` Output contract 模板（含 frontmatter + H1 + H2 按 15 角度 + 叶子单行 `- [P0/P1/P2] <内容>`）。

## Self-check（缺任一 → 重做）

1. 行数 ≥10 testpoint（不含 H1 / H2 标题）
2. 每 testpoint **单行**：`- [P<0/1/2>] <内容>` 不许换行 / 不许子项 / 不许"步骤"/ 不许"断言"
3. 至少含 §1 功能性 / §3 异常 / §4 权限 / §5 tenant
4. P0 测试点 ≥3
5. 引用 design 文档时显式引 §N 节号

## 完成后

- **不 commit**（主 agent 会一次性 commit 全部 P1 输出）
- 返回简短报告（不超过 500 字）含：
  - testpoint 总数 + P0/P1/P2 分布
  - 覆盖的视角（15 角度中的哪几个）
  - 主要风险点（来自 design 推导）
  - cost 实际花费
  - 任何 escalation（design 不一致 / testpoint 数 ≥100 / 等）

## 不许做的

- 不许并发派其他 subagent
- 不许改 design 文档
- 不许跳 fact-finding（按 [[feedback_decision_codefirst_validation]] 必读 design / grep 真实代码定位）
- 不许凭印象自创 testpoint（每条必有 design 出处）

开干。读完 8 项 input → 设计 → 写输出文件 → 简短报告。
```

---

## 主 agent 派 4 并发示例（cold-start P1 批 1）

新 session 起手 / 主 agent 派 M11/M14/M19/M20 4 并发：

```
（在单个 user message 里 4 个 Agent tool call 并行）

Agent {
  description: "P1 testpoint M11"
  subagent_type: "general-purpose"
  model: "opus"
  prompt: <上方完整 Prompt 模板 / {{MODULE_ID}}=M11 / {{MODULE_NAME}}=cold-start / ...>
}

Agent {
  description: "P1 testpoint M14"
  ...
}

Agent {
  description: "P1 testpoint M19"
  ...
}

Agent {
  description: "P1 testpoint M20"
  ...
}
```

4 个 subagent 并发跑 / 主 agent 等全部返回后 / commit `dogfooding P1 batch1 — 4 modules` / 更新 progress.md / 退出 session（或继续批 2）。

---

## 注意事项

- M17 ai-import / M18 semantic-search / M13 requirement-analysis 业务面宽 / 预估 80-120 testpoint / 不阻塞但触发 escalation report
- 边缘模块 M11/M14/M19/M20 预估 30-50 / 若 <30 / 检查是否漏覆盖视角 / 不许凑数
- 每 subagent prompt 必含 cost cap $3 + 完整 8 项 input contract + Forbidden 清单
- subagent 完成后**不许 commit** / 主 agent 收齐 4 个 module 后一次性 commit
