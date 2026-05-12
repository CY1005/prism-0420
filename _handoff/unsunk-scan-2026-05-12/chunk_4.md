# Chunk 4 Findings (05-04 ~ 05-06, 18 sessions)

## Summary

- 扫描 session 数: 18（全部读完）
- 识别 finding 数: 8（其中高置信度 3，中置信度 4，低置信度 1）
- 主要主题: 
  - prism-0420 scaffold↔design reconcile + structural audit（4 session，约 370KB）
  - kiko-os / gtd-v2 / OpenClaw / emotion / 个人成长类（11 session，约 490KB，排除）
  - 边缘 prism 相关（handoff 机制设计、tech_digest 主题 PRISM 代表作）
- 已确认已沉淀（不列为 finding）：
  - D2 token_invalidated_at iat 校验 → ADR-004 §5 + M01 00-design.md P5 token_invalidated_at ✅
  - D1 meta-decision（设计稿 vs 实现打架） → design/audit/lessons-learned.md ✅
  - P5 状态机可达性 audit → design/audit/p5-state-machine-reachability.md ✅
  - ADR-002 SYSTEM_USER_UUID cron boundary clause → ADR-002 §1.1 ✅
  - accepted-minimal + Phase 2.3 早期触发条款 → 03/04/05-spec §6/7 ✅

---

## Findings

### F-4.1. handoff 提示词内容跨 session 丢失的根因 + 解决方案

- **类型**: 技术坑 / 方法论
- **来源 session**: `11edd932` (2026-05-06), `afdea0af` (2026-05-06)
- **摘要**: session `11edd932` 末尾写了 4 条提示词（Prompt 1-4），约定"下次 session 说`继续 prism-0420，跑提示词 1`"即可衔接；但 `afdea0af` 开跑时新 Claude 找不到"提示词 1"（grep 0 命中），暴露了"提示词只活在对话 history，冷启动看不见"的跨 session 可见性盲区。补救：在 session `11edd932` 末尾重写并创建了 `_handoff/next-session.md`（commit `8e59a9c`）+ 更新 CLAUDE.md 流程（第 2 步必读 handoff）。
- **关键引用**: "教训留给我：以后跨 session 的接续指令，要么把内容落盘到 GTD，要么启动语写得能让冷启动 Claude 直接照做——不能依赖'我下次还记得'。"
- **推荐沉淀去向**: `design/audit/lessons-learned.md` 追加"跨 session handoff 可见性"教训；或 `AIQE/10-项目/Prism/` 笔记（已有 _handoff/next-session.md 作工程落地，缺方法论总结）
- **置信度**: 高（lessons-learned.md 已有 handoff 相关段，但未见"冷启动 Claude 看不到对话内 prompt"这个具体机制教训）

---

### F-4.2. M01 实施 16 块拆分计划 + top 3 risks 未落到 design 文档

- **类型**: design 决策 / 未完结 TODO
- **来源 session**: `f3e1e5c0` (2026-05-05)
- **摘要**: session `f3e1e5c0` 详细拆解了 M01 实施的 16 个 block（含时间估计 + 依赖关系 + B1-B2 代码地基和 B3-B16 功能块），并识别了 top 3 实施风险（①`token_invalidated_at` iat 校验漂移——scaffold `require_user` 缺 iat 比对；②改密码事务原子性丢失——audit 在错误 try/except scope；③Internal token 签名 `path_with_query` 客户端不一致）。这 3 个 risk 是 M01 实施前需要主动验证的约束，目前未见落盘到 M01 设计文档的 §11 风险段或 _handoff。
- **关键引用**: "scaffold 里的 require_user 只验 token 签名+过期，没有 iat 和 token_invalidated_at 的比较。设计里的这个功能是核心安全特性，不能在 sprint 里被忘掉。"
- **推荐沉淀去向**: `design/02-modules/M01-user-account/00-design.md` §11 风险段（或 §13 sprint checklist）追加 3 条 pre-implementation risk；或落到 `_handoff/next-session.md` Prompt A 的红线段
- **置信度**: 中（risk ①已在 M01 design 中有 token_invalidated_at 章节；但 risk ②③是否已落盘未确认）

---

### F-4.3. OpenClaw/prism-0420 TG 状态报告使用 push model 导致上下文截断

- **类型**: 技术坑 / 架构观察
- **来源 session**: `88bff0bf` (2026-05-05)
- **摘要**: TG 每日推送的 PRISM 状态被报为"未启动"，而实际 Phase 1 ✅已完成。根因：push model（cron 定时 claude --print）限制了 context window，Phase 1 完成记录被截出 context。结构问题：router 是为"单意图简短消息"设计的，但 CY 发的是"复合意图思考型消息"，形成"分诊台 vs 参谋型用户"错位。v3 agent mode 拟通过 pull 模式（持久 session）解决。
- **推荐沉淀去向**: `10-项目/OpenClaw/` 的 current-OpenClaw-v3.md 或 router v3 design doc（TG context staleness 作为 v3 切换的核心动机之一）；如果 v3 design doc 已有，可能已覆盖——置信度降低
- **置信度**: 低（router v3 agent mode design 已由 project_router_v3_agent.md 记录；该 context staleness 根因可能已在 v3 design 中有记录）

---

### F-4.4. tech_digest.py strip_preamble 修复 + learning loop 信号 #5 落地验证

- **类型**: bug 教训 / 技术坑
- **来源 session**: `85c3f179` (2026-05-06), `523b348e` (2026-05-06)
- **摘要**: tech_digest.py 中 Sonnet 偶发漏出英文"元思考前言"（"I have / Looking at"等），违反 prompt 硬约束，但被 `> /dev/null 2>&1` 吞掉，只有 `subtopic=?` 日志异常可见。修复方案：加 `strip_preamble()` 后处理，剥掉 `📚` 之前所有内容作为防御层（prompt 约束是治本，strip 是兜底）。`feedback_learning_loop.md` 失效信号 #5 已登记此场景，但 strip_preamble 修复本身是否也落到文档中未确认。
- **推荐沉淀去向**: `feedback_learning_loop.md` §失效信号 + 应对措施段追加"Sonnet 元思考前言 → strip_preamble 后处理"修复记录；或 AIQE `70-长期资产/研究专题/` 学习工具链设计文档
- **置信度**: 中（feedback_learning_loop.md 已有失效信号登记，但 strip_preamble 具体实现决策是否记录未验证）

---

### F-4.5. KB 两篇结构性方法论文章未在 AIQE Prism KB 创建交叉引用

- **类型**: 跨 session 收口
- **来源 session**: `2addf8c0` (2026-05-06)
- **摘要**: 本 chunk 期间向 AIQE KB `50-工具与方法论/设计与决策/` 写入了两篇文章：①`怎么找出软件设计中的结构性问题.md`（284 行，ATAM/Garcia/Rozanski&Woods 方法论）和②`设计阶段如何避免结构性漂移.md`（325 行，5 条根因 + 4 条 contracts）。这两篇文章的实践来源是 prism-0420，但 AIQE `10-项目/Prism/` 的 `_MOC.md` 或笔记区尚未添加指向这两篇文章的反向引用。
- **推荐沉淀去向**: `AIQE/10-项目/Prism/_MOC.md` 或 `学习日志.md` 追加"方法论产出：50-工具与方法论/设计与决策/怎么找出结构性问题.md + 设计阶段避免漂移.md（来源：2026-05-06 全面对账 sprint）"
- **置信度**: 中（两篇文章已推送到 gitee commit 015748f，交叉引用未在 baseline 中见到）

---

### F-4.6. _handoff 目录机制与 CLAUDE.md 冷启动流程的关系未在方法论层沉淀

- **类型**: 方法论
- **来源 session**: `11edd932` (2026-05-06), `4f810217` (2026-05-06)
- **摘要**: session `11edd932` + `4f810217` 共同确立了 prism-0420 的跨 session 接续模式：`_handoff/next-session.md`（结构化 prompt A/B/C + 历史 obsolete 区）+ CLAUDE.md 冷启动路径（第 2 步强制读 handoff，第 7 步主动报状态）。这套"handoff 文档设计模式"对未来其他项目（kiko-os、Phase 2.1 以后的各模块 sprint 管理）都有参考价值，但目前只在 prism-0420 工程层落地，方法论层未在 AIQE KB 通用化。
- **推荐沉淀去向**: `AIQE/50-工具与方法论/` 新建或补充"跨 session handoff 文档设计模式"（1-2 页，含 next-session.md 结构模板）；或合并到 PRISM 笔记区
- **置信度**: 中（prism-0420 _handoff/next-session.md 已存在为工程落地；方法论层通用化未在 baseline 见到）

---

### F-4.7. OpenClaw TG 侧 memory 与 CLI 侧 feedback 的同步机制决策

- **类型**: 架构决策 / 跨 session 收口
- **来源 session**: `92a38836` (2026-05-06)
- **摘要**: 确认了 TG 侧 `HOME=/home/openclaw` 故意不读 `/root/.claude/` memory（注释"防 user memory 反假 DONE 污染 OpenClaw"），导致 CLI 侧 feedback 文件（如 feedback_emotion_depth_probe.md）对 TG 永远不可见。解决方案：手动维护 `/home/openclaw/.claude/projects/-home-openclaw/memory/MEMORY.md`（30 行扩展为 162 行），将 18 个 CLI feedback 核心思考/分析模式提炼压缩进去，不同步工程/CLI 流程类 feedback（token 预算）。决策"不做自动 diff cron，先跑一段时间看效果"。此架构决策和同步边界选择未在 OpenClaw design 文档中记录。
- **推荐沉淀去向**: `10-项目/OpenClaw/` README.md 或 `current-OpenClaw-v3.md` 追加"TG 侧 memory 边界"段：为什么不同步 root memory + 手动 MEMORY.md 维护协议 + 何时触发 resync
- **置信度**: 中（reference_openclaw_file_deps.md 中可能有架构说明，但具体的 memory 同步边界决策未见专门记录）

---

### F-4.8. current-Prism.md 状态滞后（Phase 2.0 25%，实际 100%）已修复但路径变更

- **类型**: 其他（已处置状态跟踪）
- **来源 session**: `4f810217` (2026-05-06)
- **摘要**: session `4f810217` 开始时 Claude 发现 `current-Prism.md` 仍显示"Phase 2.0 25%"，与 roadmap 冲突（roadmap 已标 100%）。该文件已被归档（实际路径：`00-TaskScheduler/GTD/进行中/_archive/projects-2026-05-09/current-Prism.md`），说明归档时状态仍是旧值。如有历史追溯需要，此滞后窗口（2026-05-05 → 2026-05-09 归档）值得记录。
- **推荐沉淀去向**: 无需专门沉淀（已归档），但建议在 PRISM 的 `lessons-learned.md` 追加"current-Prism.md 滞后"作为 status 字面化（`feedback_gtd_status_literal`）的案例
- **置信度**: 低（已处置，无行动要求；仅供历史追溯）
