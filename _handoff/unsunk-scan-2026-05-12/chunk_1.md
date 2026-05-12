# chunk_1 未沉淀内容扫描报告

扫描时间: 2026-05-12  
扫描范围: /tmp/prism-essences/chunk_1.json（18 个 session，2026-04-23 ~ 04-25）  
已对照基线: /tmp/prism-essences/kb-baseline.txt  
识别 findings: 15 条

---

## F-1.1 M01 Auth Pilot — Internal Token P2 全域 Root 风险（Blocker B1）未修复收口

**类型**: design决策 / 安全缺口  
**来源**: root__bff7f2e1 (04-24)  
**置信度**: 高（Reviewer 明确标为 Blocker，session 在修复前结束）

**内容**: ADR-004 P2 Internal Token 路径允许任意 X-User-Id 冒充任何用户（含 platform_admin）。INTERNAL_TOKEN 泄露（写进日志 / config 文件误 commit）= 整个系统沦陷，没有二次防线。Prism 同样有此问题但无 ADR 承认。Reviewer 标为 Blocker B1，session 在修复前结束，audit-verify.md 对应段未写。

**关键原话**: "Internal Token（P2 路径）= 全域 root 风险...如果 INTERNAL_TOKEN 泄露 → 整个系统沦陷，没有二次防线"

**建议沉淀目标**:
- `design/adr/ADR-004-auth-cross-cutting.md` P2 威胁模型段（补充"已知风险+缓解措施"）
- `design/audit/lessons-learned.md`（安全设计教训）

---

## F-1.2 M01 Auth Pilot — DAO 层自 commit 违反 R-X3（Blocker B2）未修复收口

**类型**: bug 教训 / 技术坑  
**来源**: root__bff7f2e1 (04-24)  
**置信度**: 高（代码实证：services/auth.py:62）

**内容**: M01 §9 DAO 方法没有声明"不自 commit"，Prism 原始代码在 services/auth.py:62 内部 db.commit() 违反 R-X3。M01 作为 pilot 源头模块若不修，所有未来横切模块会复制此坏范式。Session 在修复前结束。

**关键原话**: "M01 作为 pilot 如果不修，所有未来横切源头模块都会抄这个坏范式"

**建议沉淀目标**:
- `design/audit/lessons-learned.md`
- `design/02-modules/M01-user-account/audit-report.md`（补 Blocker B2 已修/未修状态）

---

## F-1.3 batch3 基线补丁 — M04/M07 两处残留决策（已部分修复但决策过程未记录）

**类型**: design决策记录  
**来源**: root__32e6e689 (04-24)  
**置信度**: 高（session 完整执行了精修+commit，但决策理由仅存在于对话中）

**内容**: batch3 基线补丁后共 6 个 CY 决策点，其中 2 处有非显而易见的逻辑：

1. **M07 方法命名**: 改为 `orphan_by_node_id`（不是 `delete_by_node_id`）——理由是方法名撒谎是长期维护黑洞（Phase 2 程序员看到 delete 系列会以为真删，写出错误代码）
2. **M12 → 改走 M04 Service 接口**（不是扩展 ADR-003 规则 2）——理由是 R-X1 精神保持，规则 2 不开例外，M04 新增 `batch_get_by_nodes` 换来接口复用

这两个决策影响未来代码方向，但 `baseline-patch-batch3.md` §7 CY 决策记录是否完整写入不确定（session 报告说已更新，但"用户故事"格式的理由没有在 lessons-learned 里）。

**建议沉淀目标**:
- `design/audit/lessons-learned.md`（命名真实行为原则 + 规则2保守扩展原则）
- `design/02-modules/baseline-patch-batch3.md` §7（核查是否已有完整决策理由）

---

## F-1.4 M04 Pilot HARD-GATE 破例修——规则演进时的 Pilot 处理策略

**类型**: 方法论 / 流程规则  
**来源**: root__32e6e689 (04-24)  
**置信度**: 高（首次明确出现此场景，且有完整决策推理）

**内容**: batch3 新规则沉淀时发现 M04（同步 pilot 范本）需要破例修改（违反"accepted pilot 不改"的 HARD-GATE 原则）。决策逻辑："pilot 早于规则"是规则进化的必然代价，不修代价太大（M03/M11/M17 三个模块调用的接口不存在）。

这是 prism-0420 设计过程中第一次正式处理"规则演进时 pilot 怎么办"的问题，但处理方式只在 session 中存在，没有进入设计规范。

**关键决策**: 当 HARD-GATE 与"接口不存在导致 Phase 2 直接撞墙"冲突时，选择破例修 pilot。

**建议沉淀目标**:
- `design/02-modules/README.md` §HARD-GATE 段（补"规则演进时的 pilot 更新策略"）
- `design/audit/lessons-learned.md`

---

## F-1.5 M13 §12A 子模板"仅服务🌊场景"的决策理由未沉淀

**类型**: design决策  
**来源**: root__883f9377 (04-25)  
**置信度**: 低（§12 README 可能已有，需验证）

**内容**: 决策明确"§12A 仅服务流式场景，M16/M18 各自独立定义字段语义"，理由是 YAGNI + M16 业务未讨论。此取舍影响未来 §12B/§12C 模板的设计边界，但决策过程（为什么不做通用扩展指南）未确认在 ADR/lessons-learned 中有记录。

**建议沉淀目标**:
- `design/audit/lessons-learned.md` 或 `design/02-modules/README.md` §12 段说明

---

## F-1.6 Prism F13 "test-points生成" 与外部 skill 业务冲突——功能边界排除决策未记录

**类型**: design决策 / 产品范围  
**来源**: root__883f9377 (04-25)  
**置信度**: 中（§1 out-of-scope 可能已有）

**内容**: M13 Q0 选 C（流式+save+affected-nodes）时，test-points 生成被排除，理由是"与外部 skill requirements-to-testpoints 业务重叠会打架（test-points 是对比的一种输出，与 M12 对比矩阵也有业务重叠，强行并入 M13 会模糊边界）"。这个排除决策影响 Prism 产品范围定义。

**建议沉淀目标**:
- `design/02-modules/M13-requirement-analysis/00-design.md` §1 out-of-scope（补 test-points 排除理由）
- 或 `design/00-architecture/01-PRD.md` F13 范围澄清

---

## F-1.7 OpenClaw 进度统计流程 9 个结构性缺陷（P1-P9）未形成 bug 单

**类型**: bug 教训 / 跨 session 收口  
**来源**: root__700c032f (04-23)  
**置信度**: 高（代码已读，问题清单完整，CY 明确要求先写 bug 单但 session 结束前未完成）

**内容**: 通过读代码发现 OpenClaw GTD 进度闭环有 9 个结构性问题，CY 要求"先 bug 单然后测试改别的"，但 session 在准备阶段结束，bug 单未写入任何地方。

**P1-P7 问题清单**:
- P1: GTD checklist 前置（需 ⬜ 行存在才能解析进度）
- P2: 跨天单管道风险（working_memory day='now' 日期 hardcode）
- P3: 问进度时上下文不足（只读 3 条 episode，偏离路径上下文缺失）
- P4: 进度数值无权威源
- P5: save_episode JSON 解析失败率
- P6: GTD_snapshot 正则只认 emoji 不认 markdown checklist
- P7: chat_history 完全只读不用（最佳回溯源浪费）

**建议沉淀目标**:
- `AIQE/10-项目/Prism/02-Bug与审计/openclaw-gtd-bugs.md`（新建）或 feedback memory

---

## F-1.8 weekly-report 超时根因（16倍 context + opus + 300s timeout 三因素）未进 KB

**类型**: 技术坑 / 系统调优  
**来源**: root__cc48ea4d (04-23)  
**置信度**: 高（代码实证：15859 chars vs 1001 chars，已修复 timeout 300→600 + chat_history 压缩）

**内容**: OpenClaw weekly-report e2e 测试发现超时根因：weekly-report context 是同样用 opus 的 job-radar 的 15.8 倍（15859 vs 1001 chars），且 weekly-report 有工具调用多步（读 4 个 current-*.md），opus + 16 倍 context + 多步 tool call + 300s timeout = 必超时。

修复已落地（timeout 600 + chat_history 3天/15条），但：
1. 修复决策背后的"context 结构性膨胀 = skill 间性能差异主因"这一通用教训未沉淀
2. weekly-report 的正确 context 设计策略（多少天/多少条是合理上限）未文档化

**建议沉淀目标**:
- `AIQE/10-项目/Prism/01-实现/VibeCoding实战经验.md` 或 OpenClaw 相关文档
- feedback memory（OpenClaw cron 调优模式）

---

## F-1.9 γ PRISM 观察禁区规则（taste-sense-system）未确认进 feedback memory

**类型**: 方法论约束  
**来源**: root__66f9e9c6 (04-23)  
**置信度**: 中（taste-sense-system README 可能已有，但 feedback_prism_behavior_observation.md 是否包含此约束未确认）

**内容**: taste-sense-system 设计时明确"γ 观察期内 PRISM 禁区：不加 checklist/校准流程/ADR 新字段，避免污染观察数据"。此规则影响 prism-0420 开发行为（不能因为 PRISM 使用中发现问题就立刻改设计），但现有 `feedback_prism_behavior_observation.md` 的内容是否包含此禁区约束不明。

**关键原话**: "观察期本身不改 PRISM，只记录。样本到位后由我汇总给你，你决定 γ 形态——甚至下架"

**建议沉淀目标**:
- `feedback_prism_behavior_observation.md`（补禁区约束段）
- 或 taste-sense-system README（验证是否已有）

---

## F-1.10 prism-0420 是 Shadow 设计训练项目而非 Prism 重写——定位澄清首次明确

**类型**: 跨 session 收口 / 项目定位  
**来源**: root__f446f3db (04-24)  
**置信度**: 中（README 已有但程度不明）

**内容**: CY 明确："0420 设计之后直接实现，prism 是为了对比质量，现在的 UI 设计可以复用"。这是对 prism-0420 定位的权威澄清：/root/prism 不是废弃仓库而是对照参照物（Shadow 对比基准）。

**关键影响**: 这个定位决定了"读 Prism 现状代码"的价值——不是"避免重复劳动"而是"找出可以做得更好的地方"。

**建议沉淀目标**:
- `AIQE/10-项目/Prism/01-实现/Prism项目实践记录.md` 或 Prism-v1-项目史志.md
- prism-0420 CLAUDE.md 的项目定位段（验证是否已清晰）

---

## F-1.11 M13 Reviewer 驳回范式——主对话驳回 + verify 独立确认的首次完整记录

**类型**: 方法论  
**来源**: root__883f9377 (04-25)  
**置信度**: 高（首次出现此场景，verify agent 独立确认驳回有效）

**内容**: Reviewer B3 要求修改 M15 签名，主对话通过读 M15 §5（"纯读，无写操作"）成功驳回，verify agent 独立确认驳回有效（M15 确实是 read-only）。

这是 prism-0420 首次"主对话驳回 reviewer + verify 确认"的完整范式记录，证明 three-agent pipeline 中 reviewer 并非必须接受，主对话可以提出有效反证。对未来 audit 流程有参考价值。

**建议沉淀目标**:
- `design/audit/lessons-learned.md`（Reviewer 驳回的有效条件：必须读实际代码/文档，不能凭推断驳回）

---

## F-1.12 GitHub fine-grained PAT 不能访问 collaborator 私有 repo

**类型**: 技术坑  
**来源**: root__569b0c34 (04-25)  
**置信度**: 高（实际踩坑，有明确结论）

**内容**: Fine-grained PAT 的 "All repositories" 只覆盖 token 所有者名下 repo，不包括作为 collaborator 在他人 repo 的权限。需要 classic token 或 OAuth 才能访问他人 repo（即使你有 collaborator 权限）。

**建议沉淀目标**:
- `feedback_external_behavior_lookup.md` 或 `reference_git_identity.md`（GitHub PAT 限制段）

---

## F-1.13 AI 启动提示词不应入 Repo——新 memory 规则（feedback_prompts_not_in_repo）

**类型**: 工程规则  
**来源**: root__32e6e689 (04-24)  
**置信度**: 高（session 已创建此规则但当前 MEMORY.md 未见此条目）

**内容**: M01-auth-startup-pack.md 被撤出 repo，原因：AI 协作提示词不是设计文档，不应该进 git 历史。此规则已沉淀为 `feedback_prompts_not_in_repo.md` 并已被 MEMORY.md 索引（session 自述），但当前 MEMORY.md（2026-05-09 重塑后）未见此条目，可能在重塑时被删除。

**关键检查**: 验证 `/root/.claude/projects/-root/memory/feedback_prompts_not_in_repo.md` 是否存在；若被重塑期间删除，需恢复。

**建议沉淀目标**:
- 验证文件是否存在，若不存在重建并加入 MEMORY.md

---

## F-1.14 Claude Thinking Effort 五档位原理文章——已落盘但 commit+push 状态未知

**类型**: 跨 session 收口 / KB 资产  
**来源**: root__aa4c941a (04-24)  
**置信度**: 高（文件已写入，路径明确）

**内容**: 文章 `02-技术/AI工具与工作流/Claude-Thinking-Effort-Token消耗分析.md` 已写入 AIQE KB，内容包括 effort 五档位原理（RL post-training + adaptive thinking）+ token 消耗差异分析 + 实操建议。但 session 结尾问"需要我顺便 commit + push 吗"后被截断，commit+push 状态未知。

**建议沉淀目标**:
- 验证文件是否存在：`/root/workspace/projects/ai-quality-engineering/02-技术/AI工具与工作流/Claude-Thinking-Effort-Token消耗分析.md`
- 若存在但未 commit，按 `feedback_git_push_kb.md` 规则补 commit+push

---

## F-1.15 OpenClaw reference_openclaw_file_deps.md 整表已重写（服务名漂移全修）

**类型**: 跨 session 收口  
**来源**: root__cc48ea4d (04-23)  
**置信度**: 高（session 已完成修改，但作为"已完成事项"是否在 MEMORY.md 里标记状态不明）

**内容**: 本 session 修复了 `reference_openclaw_file_deps.md` 的 5 处路径漂移（`00-task-scheduler→00-GTD`、`/root/cy/records→/home/openclaw/records` 等）+ `project_router_v2.md` 服务名修正（`message-router.service→openclaw-router.service`）。修改已落地。

同时发现：
- `reference_openclaw_cron.md`（当前 MEMORY.md 有此条目）是否与 session 最终的 9 任务清单一致需要验证
- weekly-report 修复（timeout+context）是否已在任何 KB 文档中记录

**建议沉淀目标**:
- 验证 `reference_openclaw_cron.md` 内容与实际 9 任务完整清单一致性
- （已完成，无需重复操作，标记为已收口参考）

---

## 附：已确认已沉淀（不需要额外操作）

以下内容在对话中出现但经过基线对比确认已沉淀：

| 内容 | 已沉淀到 |
|------|---------|
| M13 设计完整流程（§12A + Q0-Q5 决策） | `design/02-modules/M13-requirement-analysis/` (accepted) |
| batch3 基线补丁（15 处修复）| `design/02-modules/baseline-patch-batch3.md` (status=accepted) |
| ADR-004 auth 横切设计 | `design/adr/ADR-004-auth-cross-cutting.md` |
| taste-sense-system 基础框架 | `06-成长/taste-sense-system/README.md` |
| GTD 重构（current-Prism.md 重写）| `00-GTD/进行中/current-Prism.md` |
| feedback_inbox_7day_rule.md | memory 系统（但需验证 MEMORY.md 索引存在） |

---

_生成时间: 2026-05-12_
