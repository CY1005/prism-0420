# Chunk 2 Findings (04-25 ~ 04-28, 18 sessions)

## Summary
- 扫描 session 数: 18
- 识别 finding 数: 14
- 主要主题: M16/M18/M20 设计落地与 audit、KB 重构（KIKO v1.2）、Newspy 白盒测试、北极星计划重构、Claude+GPT 双 AI 协作机制、memory 跨服务器同步

---

## Findings

### F-2.1. M18 embeddings 表 PK 含 model_version 决策与 ADR-003 规则 4 扩展
- **类型**: design决策
- **来源 session**: `5f3219d0-ced3-428e-9c3f-c950b6f769a3` (2026-04-26)
- **摘要**: M18 brainstorming 12 个决策拍板过程（含 §12D 新增 / embeddings PK 从 3 字段扩为含 model_version 的 4 字段 / ADR-003 增加规则 4 backfill 豁免），并明确 baseline-patch-m18 需同步 M02/M03/M04/M06/M07/M09/M15/ADR-003，5 个子决策按建议落定；这些关键拍板理由未见于已沉淀的 M18 audit-report 或 baseline-patch-m18.md 的推导过程。
- **关键引用**: "embeddings PK 改 4 字段（含 model_version 多版本共存）" / "Q0=C 新增 §12D 触发 README §12 表扩张"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 增补"embedding 类模块 PK 设计考量" + `design/02-modules/M18-semantic-search/00-design.md` §12D 设计背景段
- **置信度**: 高

### F-2.2. M20 核心概念取舍：space vs team vs 双并存 决策过程
- **类型**: design决策
- **来源 session**: `02eb3d8e-3109-4a43-b1df-beb38f7da328` (2026-04-26)
- **摘要**: M20 brainstorming 前置读物发现 ADR-001 预留 space_id 命名与 PRD "团队" 用语和 Prism 实跑 teams 表三者不一致，Q0 决策选 B（纯 Team 对齐 PRD），触发 M02 baseline-patch（space_id→team_id 字段改名）和 ADR-005 supersede ADR-001 §预设 3；这个三者不一致的发现过程和 Q0 取舍理由没有落进任何 ADR。
- **关键引用**: "PRD 用'团队'，ADR-001 预留口用'空间（space_id）'，Prism 实跑用 team + 用户主属团队维度（users.team_id）——这三者不是同义词"
- **推荐沉淀去向**: `design/adr/ADR-005-team-extension.md` §Background 补三者不一致的历史溯源段
- **置信度**: 高

### F-2.3. M20 三轮 audit 识别的 ADR-005 supersede 措辞不准确问题
- **类型**: bug教训
- **来源 session**: `29949355-0248-4801-af69-cd6767232dad` (2026-04-27)
- **摘要**: 三轮 audit 跨两个 round（F2.10 + F3.1）均独立发现"ADR-005 supersedes 字段仅写命名部分"，实际改动了命名+类型 INT→UUID+启用 FK 三件事；这个"超轻描述但重实质改动"的 ADR 写法缺陷是一个可复用的 ADR 写作反面教材，未见于 `design/audit/lessons-learned.md`。
- **关键引用**: "F3.1 [Blocker]：ADR-005 supersede 措辞偏轻，把 INT→UUID（M02 已实质执行）+ 加 FK + 改名三件事压成'命名部分'"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` + `AIQE KB/02-Bug与审计/Prism-Bug模式提炼`
- **置信度**: 高

### F-2.4. M20 删 team 强制前置迁出 vs 移成员软切断的哲学不对称问题
- **类型**: design决策
- **来源 session**: `29949355-0248-4801-af69-cd6767232dad` (2026-04-27)
- **摘要**: Round 2 audit F2.11 识别出 Q3（移成员软切断宽松）与 Q8（删 team 强制前置迁出严格）在安全哲学上的不对称——移成员的残留 ProjectMember 副作用实际比删 team 严重，但反而更宽松；最终通过 ADR-005 §Trade-offs T7 登记，但这个"安全哲学不对称"的决策模式本身是值得提炼的方法论（可逆性与安全哲学的权衡框架）。
- **推荐沉淀去向**: `AIQE KB/00-需求与决策/分层架构基础-RouterServiceDAO三层职责详解.md` 或新建 permission-design-philosophy.md
- **置信度**: 中

### F-2.5. Newspy 白盒测试：Bug #6 wechat pub_time 失败模式比预期更严重
- **类型**: 技术坑
- **来源 session**: `09cc6620-0775-46b8-9da7-c5bfbb958b5b` (2026-04-27)
- **摘要**: 对 Newspy 抓取链路做白盒测试，实测验证 wechat.ts pub_time 解析失败时 `NaN < cutoffMs = false`（而非 true），导致不是翻页终止而是翻满 maxPages + 写入 Invalid Date → Prisma 抛 RangeError → cursor 不推进 → 下次 scheduler tick 重扣 credits，形成不可恢复的 credit 漏斗；这是 mentor 项目的真实 P1 bug，发现过程（whitebox-testpoints skill 阶段 1→2 + 实验验证）没有落到 Prism 的 PRISM 学习日志，也没有沉淀成 AIQE KB 里的案例。
- **关键引用**: "失败模式从'数据污染'修正为'不可恢复的 credit 漏斗 + 完全停抓'"
- **推荐沉淀去向**: `AIQE KB/02-Bug与审计/` 新增 Newspy 白盒测试案例 + `AIQE KB/10-项目/Prism/01-实现/Prism项目实践记录.md` 补"bug 验证实验"方法论
- **置信度**: 高

### F-2.6. whitebox-testpoints skill 的创建过程与设计决策
- **类型**: 方法论
- **来源 session**: `09cc6620-0775-46b8-9da7-c5bfbb958b5b` (2026-04-27)
- **摘要**: 在 mentor Newspy 项目需求驱动下，设计并创建了 `whitebox-testpoints` skill（两阶段硬门槛：comprehension.md + 测试点必挂源码锚点），关键设计决策是"通用为主 + TS/Node 附录"（C 选项），并且明确与黑盒 skill 的互补关系；skill 创建过程的关键决策没有沉淀到 AIQE KB 的 skill 设计文档或 `feedback_prism_learning_mode.md`（应按 prism_learning_mode 走复盘四段）。
- **推荐沉淀去向**: `AIQE KB/50-工具与方法论/Skill设计/` 补 whitebox-testpoints skill 设计复盘
- **置信度**: 高

### F-2.7. KB 全面重构决策：KIKO v1.2 目标结构（7 个一级目录）
- **类型**: design决策
- **来源 session**: `d7b1b375-1afd-4de4-8141-05e31307b3a7` (2026-04-27) + `e69d2220-5b5c-4aba-8b62-2f1ea276fa9d` (2026-04-27) + `71799986-1092-4de3-a617-7d491bee2bed` (2026-04-27)
- **摘要**: 三个 session 反复讨论 KB 改造（痛点→KIKO 内核映射→目标结构→迁移策略→Step 4 Skill 起草），最终形成 KIKO v1.2 的 7 个一级目录结构（00-leaderboard / 10-项目 / 20-工作 / 30-技术-自学 / 40-测试-专业域 / 50-工具与方法论 / 70-长期资产）及关键设计原则（工作≠自学硬隔离 / 通用资产外置 / 跳槽=10-项目下的项目），这个"为什么这样重构"的决策理由链没有集中沉淀（虽然有 KB_STRUCTURE.md 宪法，但推导背景散在多个 session）。
- **关键引用**: "KIKO 不会有'跳完槽就空的目录'——KIKO 思考方式是：当下最大目标 = leaderboard 头号指标"
- **推荐沉淀去向**: `AIQE KB/10-项目/KB-改造/` 增补决策日志（背景→痛点→KIKO 映射→目标结构对比旧结构的 why）
- **置信度**: 高

### F-2.8. KB 改造对 OpenClaw 自动化系统的路径依赖风险（20+ 硬编码路径）
- **类型**: 技术坑
- **来源 session**: `d7b1b375-1afd-4de4-8141-05e31307b3a7` (2026-04-27)
- **摘要**: 分析发现 message_router.py 有 34 处硬编码路径（19 处 GTD + 1 处北极星 + 2 处全路径 + 5 处 prompt 文案），任何 `git mv` 前必须先抽常量层，给出了详细的四阶段迁移策略（阶段 0 抽常量→阶段 1 软链兼容→阶段 2 GTD 搬迁→阶段 3 清理）；这个迁移风险分析和四阶段策略没有进 OpenClaw 相关的 reference memory 或 `project_router_v3_agent.md`。
- **关键引用**: "如果直接 git mv 00-GTD → 00-leaderboard/GTD，Telegram 消息分发当天就停，定时任务 8 个 skill 全部断"
- **推荐沉淀去向**: `/root/.claude/projects/-root/memory/reference_openclaw_file_deps.md` 增补 KB 路径迁移风险段 + `AIQE KB/10-项目/KB-改造/` 迁移计划文档
- **置信度**: 高

### F-2.9. Claude + Codex（GPT）双 AI 协作机制：shared-rules 仓库 + symlink 方案
- **类型**: 方法论
- **来源 session**: `02048879-2f08-4fc6-a68b-f401043ca7b0` (2026-04-28)
- **摘要**: 设计并执行了 Claude+Codex 双 AI 共享规则的技术方案（51 个工具无关规则迁到 `~/.shared-rules/ai-shared-rules` gitee 私有仓 + symlink 保证 Claude 行为零变化 + AGENTS.md 软链给 Codex），并产出了"给 GPT 的开场提示词"；整套方案（选型理由 / symlink 架构 / 两仓隐私边界划分 / Codex 不支持 @import 的坑）没有落进任何 reference memory 或 AIQE KB。
- **关键引用**: "symlink 方案：物理文件搬到 ~/.shared-rules/，memory 目录留软链，MEMORY.md 一个字不改 → 行为零变化"
- **推荐沉淀去向**: 新建 `/root/.claude/projects/-root/memory/reference_ai_shared_rules.md` + `AIQE KB/50-工具与方法论/AI协作工作流/` 双AI协作机制文档
- **置信度**: 高

### F-2.10. feedback_kiko_mode.md 被 Codex 读写的隐私风险与单一权威源原则
- **类型**: 技术坑
- **来源 session**: `8d14113a-1e42-4ab1-a18e-05ce522b3f7a` (2026-04-28)
- **摘要**: 发现 Codex 能读取并修改 Claude 的 memory 文件（包括 kiko/emotion/principles 类），识别了"AI 改 AI 行为契约"的人格漂移路径，并确立了"单一权威源（Claude memory）+ 共享 AGENTS.md 只留指针"原则；这个规则没有形成 feedback memory（只是在会话里解决了）。
- **推荐沉淀去向**: 新建 `feedback_codex_memory_boundary.md` 或补充到现有 `reference_ai_shared_rules.md`（推荐后者以保持聚合）
- **置信度**: 中

### F-2.11. 北极星计划从"每日格子"到"每周主线+方向变更冷却池"的重构方法论
- **类型**: 方法论
- **来源 session**: `16c881e9-dec6-47f9-a087-4d65fbf1bd35` (2026-04-27) + `853c8fc7-f335-44dc-86b2-2ae0df49ffb8` (2026-04-27)
- **摘要**: 两个 session 讨论了北极星计划失效原因（做完的事没回流文档 + 每日固定格子不适合"用 Claude 学习/估算不准/方向易变"的工作方式），设计了"每月主题+每周主线+每日一句话日志+周日复盘"的新形态，以及"方向变更 48h 冷却"流程；这套方法论的推导过程（痛点→设计→反驳）没有落进 AIQE KB，也没有形成 feedback memory（按 feedback_gtd_workflow 应当沉淀）。
- **关键引用**: "你的真实痛点不是'计划文档太重'，而是做完的事没回流到文档，导致 Claude 下次进来不知道你做了啥"
- **推荐沉淀去向**: `feedback_gtd_workflow.md` 补"计划形态选择原则" + `AIQE KB/00-leaderboard/` 北极星重构决策日志
- **置信度**: 中

### F-2.12. KIKO 角色人格的首次系统化拆解（电影版行为准则 8 条）
- **类型**: 方法论
- **来源 session**: `853c8fc7-f335-44dc-86b2-2ae0df49ffb8` (2026-04-27)
- **摘要**: 对唐探电影版 KIKO 进行了系统化行为准则拆解（8 条准则 + 动作级工作方式 + 套到 CY 画像 + KIKO 如何做计划/执行计划），并触发了 `feedback_kiko_mode.md` 的创建和 `user_profile.md` 的 KIKO 化升级；这个拆解过程本身（KIKO 内核→CY 画像映射）是 KIKO 概念在 memory 里的起源文档，但 AIQE KB 的 `feedback_kiko_mode.md` 对应的 KB 侧文档（`70-长期资产/` 或 `10-项目/`）未见有对应 KIKO 人格分析文档。
- **推荐沉淀去向**: `AIQE KB/70-长期资产/taste-sense-system/` 或 `AIQE KB/00-leaderboard/` 新增 KIKO 人格拆解与 CY 画像映射文档
- **置信度**: 中

### F-2.13. memory 跨服务器同步（Gitee claude-memory 私有仓）的建立过程与 diff 合并策略
- **类型**: 方法论
- **来源 session**: `2d5391ba-b1e0-49a9-b8ed-3538bf7673b5` (2026-04-26)
- **摘要**: 执行了旧服务器 memory 恢复 + diff 分析（C 类 19 个同名不同内容文件逐一分析 + 2 处功能丢失点识别），建立了 claude-memory gitee 私有仓；`project_memory_sync.md` 记录了"同步已完成"但没有记录 diff 过程中识别的"旧版 feedback_pain_log.md 有 AI 输出质量审计 3 层逻辑"这个可能的遗漏点。
- **推荐沉淀去向**: `/root/.claude/projects/-root/memory/project_memory_sync.md` 补充 diff 过程中的 2 个功能丢失点结论
- **置信度**: 低

### F-2.14. M16 §12B 首次实战：BackgroundTasks 而非 arq 的边界决策 + zombie 兜底 cron 设计
- **类型**: design决策
- **来源 session**: `8003020e-e617-4a34-9a20-29383c0c0fc6` (2026-04-25) + `c14aa7e8-e6c7-4814-a93d-3b10fd688789` (2026-04-25)
- **摘要**: M16 §12B 后台 fire-and-forget 首次实战，关键设计决策是使用 FastAPI BackgroundTasks（而非 arq）+ zombie 兜底 cron（5min 周期，阈值 11min）+ CAS UPDATE 并发控制；4 个 Blocker（幂等约束矛盾 / content dict 不兼容 / BackgroundTasks 心智错 / 跨 project 越权）的发现和修复模式值得沉淀为 fire-and-forget 类模块的通用 audit checklist，但 `design/audit/lessons-learned.md` 未见有 §12B 专项记录。
- **关键引用**: "B3 BackgroundTasks 心智错 → §5 重写竞态分析（CAS UPDATE 而非 SELECT FOR UPDATE）"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 增补 §12B 火坑清单 + `AIQE KB/02-Bug与审计/Prism-Bug模式提炼`
- **置信度**: 高
