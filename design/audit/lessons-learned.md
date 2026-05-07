---
title: 设计前置 audit 实战经验沉淀（2026-05-06 单会话）
status: draft
owner: CY
created: 2026-05-06
trigger: 本会话从 D1 接口决策出发，意外开出"全面结构性 audit + 4 条对账契约 + 业界标准命名规范 + 2 篇 KB 方法论文章"。CY 提议沉淀本会话所有元教训，避免等 PRISM 跑完时丢失对话过程信息。
purpose: 为未来"设计前置启动包"提供素材库，含决策路径 / 砍掉候选 / 元教训 / 工作流模板
---

# 设计前置 audit 实战经验沉淀

## 0. 为什么单独沉淀这份

读 git log + design 文档能 recover 决策**结果**，但读不出 4 类信息：

- 决策路径（怎么从 A 想到 B）
- 砍掉的候选 + 理由
- 元教训（AI / 协作过程犯的错）
- 实时校准（CY 反馈逼出转向的瞬间）

这 4 类只活在对话里。本文档是把对话信息固化下来。

---

## 1. 本会话工作流（时间线 + 卡点 + 突破）

```
起点：M01 D1 决策（AuthServiceProtocol 1 法 vs ADR-004 4 法）
       ↓
[约 30min] 给 D1 列 A/B/C 三候选 + 推荐 A
       ↓
🔴 卡点 1：CY 不接受单独决策 D1
   "这和第一个问题是一个问题——之前让你找所有对账问题的结论呢？"
       ↓
[约 30min] 重定位 D1 = 7 seam 中的 S1，结构性思考根因
       ↓
[手工 grep + 自审] 全面 scaffold↔design reconcile pass-1
       ↓ 产出
   design/audit/scaffold-design-reconcile.md（7 个对错型 seam）
       ↓
🔴 卡点 2：CY 校准"这是问题，但不是我想象的结构性问题"
   "横向规则单看 OK / 模块单看 OK / 组合时才暴露 — 这种才是结构性"
       ↓
[CY 提议] 搜权威方法论
       ↓
[Agent 1h] 调研 ATAM (SEI) + Rozanski & Woods + Garcia 架构坏味道
   产出 14 类结构性 seam taxonomy + 5 个检测 procedures
       ↓
[手工 grep + Agent 数据] 全面 reconcile pass-2（应用 P1-P5）
       ↓ 产出
   design/audit/full-reconcile-pass.md（11 个结构性 seam）
       ↓
[根因诊断] 11 个 seam 全部归到 5 条限制位空着
       ↓
[起草防御机制] 4 条对账契约
       ↓ 产出
   design/audit/contracts-draft.md
       ↓
🔴 卡点 3：CY 问"5 条限制是流程错还是限制不足"
   逼出元层面诊断："不是流程错，是 audit agenda 只看纵向"
       ↓
[CY 提议] 写两篇方法论文章
       ↓
[2 次 Write] KB 文章
   ai-quality-engineering/50-工具与方法论/设计与决策/
     ├── 怎么找出软件设计中的结构性问题.md
     └── 设计阶段如何避免结构性漂移.md
       ↓
🔴 卡点 4：CY 不 get"3 个判断点"
   "用具体场景描述哪个场景做哪个不做"
       ↓
[Bash verify] 先看原始代码：业务代码 0 行确认
       ↓
[再 Agent 1h] 调研业界标准命名规范
   产出 N1/A1/Q1-3/S1-5 + Stripe/GitHub/FastAPI 来源链接
       ↓
[整合] 命名空间登记表骨架 + 4 类规范
       ↓ 产出
   design/00-architecture/08-namespaces.md
   design/00-architecture/namespace-data/errorcodes-full.md（125 条）
       ↓
🔴 卡点 5：CY 问"两个修订实际落地有什么区别"
   逼出"用真实业务场景 + 真实代码片段 + 真实 SQL 查询对比"
       ↓
[CY 拍] ActionType 按业界标准拆 / ErrorCode 大小写"看你"
       ↓
🔴 卡点 6：CY 问"等 PRISM 跑完再沉淀启动包会不会丢东西？"
       ↓
[本文档诞生]

───
关键时间分布：
- D1 单点决策：30 min
- 卡点 1 转向（"全面 audit"）：1.5h
- pass-1 对错型：2h
- 卡点 2 转向（"结构性"）：2h（含 agent 调研）
- pass-2 结构性：3h
- 4 条契约 + 根因诊断：1.5h
- 2 篇方法论文章：2h
- 卡点 4-5 校准 + 命名空间表：3h
- 本文档：30min
───

总时长 ~16h（含 agent 时间）
原计划：D1 单点决策 30min + M01 实施
实际产出：1 个完整结构性 audit pass + 4 条对账契约 + 业界标准命名 + 2 篇 KB 方法论文章 + 1 份命名空间表
```

---

## 2. 决策路径与砍掉的候选

### 2.1 D1 — AuthServiceProtocol 接口形态

**演进**：

```
v1（最初）：A/B/C 三候选并列摆台，推荐 A 守 scaffold
   ↓ CY 拒绝（"这是更深的问题"）
v2（重摆）：D1 = 11 seam 中的 S1，元决策是"设计稿 vs 实现打架认哪边"
   ↓ 提议 C 让实现迁就设计稿（PRISM 是方法论 shadow 项目）
v3（CY 重讲）：用商场比喻讲 A/B/C
   ↓ CY 说看不懂（不要比喻）
v4（最终）：用 PRISM 真实代码场景重讲，确认 D2 拍 A 后 D1 选 A 仍然合理
   ↓ 拍 A
```

**砍掉的理由**：
- B（Protocol 加 4 法但只调 1 法）：死代码，违反"3-5 月可读性"——半年后看到 4 法只调 1 个会愣住
- C（require_user 调 4 法 service）：3h 重写横向 helper + 5-6 个测试改写，PRISM 是 shadow 项目，ROI 不值

**真实信心度**：A 不是"完美选择"是"够用选择"——选 A 半年后想升 C 是几小时 refactor 不是地震，可逆决策给时间盒。

### 2.2 命名规范 — N1 大小写

**演进**：

```
v1（我直觉）：Python PEP 8 → 用 UPPER_SNAKE_CASE（包括 enum value）
   ↓ Agent 调研业界标准
v2（业界事实）：Stripe/GitHub/Google AIP-193 全是 lowercase 实体前缀
   ↓ 我推荐"全小写"，标"修订工作量大"让 CY 拍
v3（CY 校准）：你应该自动判断不让我拍
   ↓ 重新审视
v4（项目阶段判断）：业务代码 0 行 → 改 enum value 零运行代价 → 自动应用业界标准
```

**砍掉的理由**：
- "保留 UPPER_SNAKE_CASE" 选项：i18n key 习惯小写、Stripe / GitHub 都是小写、对监控工具索引友好——但**实际差异很小**，对 PRISM 量级几乎可忽略
- 最终 CY 说"看你"——这是真实的"风格 ≠ 功能"判断

### 2.3 命名规范 — A1 ActionType 拆 CRUD vs 不拆

**演进**：

```
v1（我直觉）：保留 CRUD 通用 + target_type 区分实体（PRISM 现状）
   ↓ Agent 调研（事件溯源 + Kafka 社区）
v2（业界事实）：Greg Young / Vaughn Vernon 收敛到 {entity}_{past_verb} 不分两套
   ↓ 推荐拆但标"工作量大"让 CY 拍
v3（CY 问"实际有什么区别"）：用 M15 时间线 UI 真实代码场景对比
   ↓ 暴露真正差异：拼 i18n key 单字段 vs 双字段
v4（CY 拍）：拆——因为 M15 时间线是 PRISM 核心功能，i18n 拼 key 是真实痛点
```

**砍掉的理由**：
- "保留 CRUD 通用"：enum 数量更少（41 vs 50-60）—— 但代价是前端每加一个 target 要加 2 个 i18n key（action × target_type 双字段拼），漏一个就显示英文 fallback
- 真实功能性差异胜过"enum 数量精简"

### 2.4 沉淀启动包时机

**演进**：

```
v1：建议"PRISM 完整跑完再沉淀启动包"含金量高
   ↓ CY 反问"会不会丢东西"
v2：诚实承认我读代码不能 recover 4 类信息（决策路径 / 砍候选 / 元教训 / 实时校准）
   ↓ 提议现在做 lessons-learned.md
v3：A（启动包）+ A'（lessons-learned）混合——启动包等 PRISM 跑完，但元素材现在固化
```

---

## 3. 元教训清单

### 教训 1：方法论文章 ≠ 可执行启动包

**症状**：写了 2 篇 284+325 行的方法论文章，看起来"沉淀完整"。但 CY 下个项目启动时**没有可 cp 的模板文件**——还是要从零搭 frontmatter / 横向规约文档 / 命名空间表 / CI 脚本。

**根因**：文章是"理解材料"（解释为什么），启动包是"执行材料"（直接 copy 用）。两者不能互相替代。

**应用**：未来任何"沉淀方法论"的任务，必须问"读完后能 cp 什么开干？" 答不上 → 沉淀不完整。

### 教训 2：判断点分级 — 工业标准 vs 项目特定 vs 业务

**症状**：我把 3 个判断点（漏引 / 命名规范 / 违规处理）一股脑儿包装成"必须 CY 拍"。CY 反问"这些应该有标准做法吧" + "我们没写代码直接改即可"。

**根因**：我没区分判断的性质：
- A 类：工业标准查得到（命名规范）—— **不应让 CY 拍**，应该 agent 调研
- B 类：项目特定状态决定（违规处理）—— **不应让 CY 拍**，应该 verify 状态自动判
- C 类：真业务/价值判断（要不要这个功能）—— **才让 CY 拍**

**应用**：列"判断点"时先自审分级。A 类自动调研，B 类先 verify，C 类才呈现给 CY。

### 教训 3：业界标准查询应该前置不是后置

**症状**：我先草拟了 N1-N5 / A1-A3 / Q1-Q3 / S1-S4 命名规范（基于直觉），然后才让 agent 查业界标准。结果业界标准回来后，我的草案有 30% 要修订（N1 大小写错 / S1-S4 选错 FastAPI 风格）。

**根因**：当涉及"通行规则"时（命名 / 协议 / API 风格），业界先例的搜寻成本远低于自己拍的修正成本。

**应用**：任何涉及"普适规则"的设计决策，先 30min agent 调研业界，再起草。

### 教训 4：对错型 seam vs 结构性 seam 在 review 启动时必须声明

**症状**：第一次跑 reconcile pass 找出 7 个 seam，CY 说"这是问题，但不是结构性"。我才意识到自己在找"对错型"（命名拼写、引用错误、单文档错），CY 想要的是"结构性"（组合时才暴露）。

**根因**：reviewer 默认 agenda 是"找单文档错"——这是大多数 review 的范畴。结构性 review 是另一种 agenda，需要显式声明 + 不同的检测工具（ATAM / R&W / Garcia）。

**应用**：任何 review 启动时，先**显式声明**"我们找哪一类问题"——对错型 / 结构性 / 性能 / 安全 / 兼容性。混着找会两边都不深。

### 教训 5：纵向 audit 永远找不到结构性问题

**症状**：PRISM-0420 每模块跑了三轮对抗 reviewer audit（M16 跑 19 项 / M18 跑 6 轮独立审），加起来上百个 finding——**没有一项**是"4 ADR 同时适用边界"或"125 个 ErrorCode 命名空间冲突"这种结构性问题。

**根因**：纵向 audit agenda 是"模块自身完整性"——每条 review 项都在问"这个模块写得对吗"。结构性问题不在任何模块内部，永远漏审。

**应用**：audit agenda 必须显式分两组：纵向（模块 self-completeness）+ 横向（cross-reference completeness）。两组独立跑、独立 sign-off。

### 教训 6：先 verify 原始数据再判断"违规怎么处理"

**症状**：我列"违规处理三选项（直接改 / deprecated 兼容 / 接受现状）"让 CY 拍。CY 说"我们没写代码嘛，按规范直接改就行——你先去看原始代码"。

**根因**：我假设了"违规处理是有代价的难题"，但实际项目阶段（业务代码 0 行 / DB 0 数据 / 前端 0 消费）让代价 = 0，三选项坍缩为单选。

**应用**：任何"难题"先 verify 当前真实状态——可能根本不是难题。

### 教训 7：用真实场景对比规则的实际差异

**症状**：我把 2 个修订（ErrorCode 大小写 / ActionType 拆）描述为"业界推荐 vs 现状选择"。CY 说"实际落地有什么区别"。我才意识到没用具体业务场景对比，只在抽象层讨论。

**根因**：抽象规则不能驱动决策——必须降到具体后果（前端代码长什么样 / DB 行什么样 / 查询语句什么样 / i18n 文件什么结构）。

**应用**：任何规则推荐附"现状代码片段 vs 新规约代码片段"对比，最少 2-3 处具体场景。

### 教训 8：agent 并行调研是设计阶段的 force multiplier

**症状**：本会话两次派 agent（结构性方法论调研 / 业界命名标准调研）背景跑，主线程同步做其他工作（命名空间表骨架建立）。Agent 回来后产出直接整合。

**根因**：调研型任务和构建型任务可以并行——不需要主 session 等。

**应用**：每次设计决策卡住"我需要先了解 XX"时，立刻 spawn agent 背景跑，主线程继续做不依赖该信息的工作。

---

## 4. 实时校准触发的 6 次转向

每次 CY 校准都对应一个元教训源头。本表是 lessons-learned 的"原始触发点"。

| # | CY 校准的话 | 触发的转向 | 对应教训 |
|---|-----------|----------|---------|
| 1 | "这和第一个问题是一个问题啊——当时让你帮忙把所有对账问题找出来" | D1 → 全面 audit | — |
| 2 | "不是我想象的结构性问题——你可以搜一下有没有权威方法论" | 对错型 → 结构性 + 调研 ATAM/R&W/Garcia | 教训 4 |
| 3 | "你说的判断点我没 get——给我描述具体场景哪个做哪个不做" | 抽象 → 具体场景 | 教训 7 |
| 4 | "我们没写代码嘛——你先看原始的代码或者设计稿" | 假难题 → verify 后单选 | 教训 6 |
| 5 | "这两个在实际落地有什么区别？" | 抽象规则 → 真实代码片段 | 教训 7 |
| 6 | "等 PRISM 跑完再沉淀会不会丢东西？" | 启动包延后 → lessons-learned 现在做 | 教训 1 |

---

## 5. 本会话产出地图

### PRISM-0420 内（10 commit，未 push）

| commit | 文件 | 性质 |
|--------|------|-----|
| 313c80a | design/audit/scaffold-design-reconcile.md | 对错型 seam（7 个）|
| c462e9e | api/models/base.py + tests/test_models_base.py | 横向 Mixin 实装 |
| df060b4 | design/01-engineering/01-engineering-spec.md | 模块编号修订 |
| 57eb550 | api/errors/{codes,exceptions,__init__}.py + spec | ErrorCode 重命名 + 子类 |
| 9de4047 | scripts/ci-lint.sh + .pre-commit-config.yaml | R13-1 grep 守护 |
| 4860d0d | design/00-phase-gate.md | 闸门 2.5 / 2.6 |
| **c9a580d** | **design/audit/full-reconcile-pass.md** | **结构性 seam（11 个）**|
| **e8bae80** | **design/audit/contracts-draft.md** | **4 条对账契约形态** |
| **3506276** | **design/00-architecture/08-namespaces.md** + namespace-data/errorcodes-full.md | **命名空间登记 + 业界标准** |
| _本 commit_ | **design/audit/lessons-learned.md** | **元教训沉淀**（本文档）|

### KB（已 push gitee）

| commit | 文件 | 性质 |
|--------|------|-----|
| 015748f | 50-工具与方法论/设计与决策/怎么找出软件设计中的结构性问题.md | 思维方法论文章 |
| 015748f | 50-工具与方法论/设计与决策/设计阶段如何避免结构性漂移.md | 实操防御文章 |

---

## 6. 启动包素材（等 PRISM 跑完汇总用）

未来做"设计前置启动包"时，从以下来源合成：

| Templates 子目录 | 来源 |
|------------------|-----|
| 横向草案模板/ | design/adr/ + design/01-engineering/ + 02-modules/README.md（dejecify）|
| 模块设计模板/ | M04 / M17 pilot 模板 + frontmatter references 字段 |
| 命名空间表模板/ | design/00-architecture/08-namespaces.md（dejecify）+ 业界标准段 |
| CI 脚本/ | scripts/ci-lint.sh（已有）+ structural-audit.sh（待建）|
| 闸门 checklist/ | design/00-phase-gate.md（已有）+ 闸门 2.5 reconcile + 教训 4-5 audit agenda |
| 实战案例/ | 本文档（lessons-learned.md）+ 两篇 KB 方法论 |

**等触发时机**：
- PRISM-0420 Phase 2.1 M01-M05 跑完
- 即添加"实战中又踩了什么坑"
- 合成启动包发布到 ai-quality-engineering/Templates/设计前置启动包/

---

## 6.5 2026-05-07 续追：模板缺规则 + 存量回扫 4 步流程

### 触发

P5 audit F-1 揭出 M01 mermaid `pending → disabled (预留)` 与禁止表 `pending → disabled` 自相矛盾。本以为是单点 patch，CY 追问"为什么会出现这种矛盾"——根因是**R4 模板缺一条规则**（"非常规态独立登记"），导致作者把"未来全图"思维混进"本期硬约束"思维。

### 4 步通用流程（沉淀，给未来同类问题用）

| 步 | 动作 | 红线 |
|---|---|---|
| 1 识别根因升级 | audit 抓到 finding 时先问"是作者疏忽还是模板缺规则"。template-gap → 升级为模板修订事项，不在单点 patch 浪费 | 跳过此步 → 修一处放过同类十处 |
| 2 改规则（权威 spec）| 在权威规约位置（如 02-modules/README.md R4）加新规则 + 样例 + 反例。一个 baseline-patch commit | 跳过此步 → 规则散落注释 |
| 3 扫存量（grep 全仓） | 列出所有符合 trigger 的模块，按新规则 patch；CY 拍可合大 commit 也可逐模块 | 跳过此步 → 旧矛盾不会自动消失 |
| 4 加自动化守护 | structural-audit.sh + pre-commit hook 加 lint 规则；未来漏写直接 fail commit | 跳过此步 → 半年后再踩 |

### 何时不加自动化守护（步 4）

本次实操 CY 拍砍掉步 4，理由：`scripts/structural-audit.sh` 还不存在（在 contracts-draft §4 才规划新建），现在新建独立 hook = 散落基础设施，等 contracts §4 落地时合并实现。**判别条件**：步 4 工具已存在 → 必加；不存在 → 评估"是否值得为这一条规则单独建工具"——不值得就把规则记入 contracts/structural audit TODO，等下次合并实现。

### 元教训：用 superpower 起草规则文本

CY 在本次明确指示"找问题→分析原因→写修复规则"必须用 superpower。本次用 `superpowers:brainstorming` 走完整流程：探索 context → 一次一个问题 → 起草 v1 → 起 Agent 查 5+ 业界项目（K8s/Temporal/Step Functions/Stripe/Shopify/UML PSSM/SCXML）实证 v1 合理性 → 修订 v2（仅接受 1 项业界证据强的修订）→ CY 审通过 → 落地。

**关键判断**：业界证据强的修订（加 since 字段——K8s/Stripe/Shopify 都有）接受；业界主流但与项目偏好冲突的（放松严格档——CY 不接受，认为留口子让人偷懒）拒绝；超出当前需求的（5 类扩展为支持降级/迁移态）保留 YAGNI 但 CY 选择保留扩展空间。**外部证据 ≠ 直接照抄**——证据进决策，决策权在 CY。

### F-1 的两层时间视角教训

mermaid 用"未来全图"思维画（覆盖完整生命周期）+ 禁止表用"本期硬约束"思维写（覆盖本期跑得通的代码路径）——两次思维上下文切换之间没人喊停说"等等，这两份是同一个状态机的两个时间切片，要么都画未来要么都画本期"，结果同一条边一处当未来允许、一处当本期禁止。

**适用范围广**：不止状态机。任何"现在文档" + "未来预留" 共存的设计文档都有此风险——API 契约里的 deprecated 字段、配置项的 reserved key、ErrorCode 表里的"暂不抛出但保留"——都需要"主表只列本期可用 + 非本期独立登记"的硬规约。

### 本次产出

| 文件 | 性质 | commit |
|------|-----|-------|
| 02-modules/README.md R4-3a | 模板修订（规则 + 5 类 + 6 字段态表 + 3 字段边表 + 反例对照）| 2e93de9 |
| M01/M16/M17/M18 00-design.md | 4 模块按 R4-3a 回扫（mermaid 删 + 登记表加）| 2e93de9 |
| ADR-002 §1.1 | 触发方清单 3 → 10 + Queue/SQL 形态区分 | b24f049 |
| M16/M17/M18 模块端 cron user_id 反向引用 | 双向链补全 | b24f049 |

---

## 7. 关联

- 触发：M01 D1 决策（详见 commit `c9a580d` audit § 触发）
- 全套 audit 文档：design/audit/scaffold-design-reconcile.md / full-reconcile-pass.md / contracts-draft.md
- 命名空间真相源：design/00-architecture/08-namespaces.md
- 思维方法论：ai-quality-engineering/50-工具与方法论/设计与决策/怎么找出软件设计中的结构性问题.md
- 实操防御：ai-quality-engineering/50-工具与方法论/设计与决策/设计阶段如何避免结构性漂移.md
- 启动包（待建）：ai-quality-engineering/Templates/设计前置启动包/
- **2026-05-07 时间维度盲区元反思**：[`time-dimension-blindspot-2026-05-07.md`](./time-dimension-blindspot-2026-05-07.md)
  - M02 sprint 启动暴露 5 个体系盲区（含横切 vs 业务元维度）→ 加 6 原则 + R-X5/R-X6/R3-6 + 04-layer Q7 + §7 修订
  - 4 案例 + 4 元教训（立规分两层 / 横切 vs 业务边界 / 立规防御未来 vs 修复存量 / L1/L2/L3 时间维度切分）
  - 11 处 baseline-patch 实证 + T11/T12 排查修复存量
