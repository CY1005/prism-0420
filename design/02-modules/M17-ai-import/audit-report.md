---
title: M17 pilot 三轮对抗 audit
status: draft
owner: reviewer-agent
created: 2026-04-21
batch: pilot-2
modules: [M17]
---

# M17 pilot 三轮对抗 audit

> **审稿立场**：独立、不附和、每条问题必须有文件路径 + 节号。
> **参照基线**：A 档（01-PRD / 04-layer-architecture / 05-module-catalog / 06-design-principles）+ B 档规约 1/5/7/11.3/12 + M04 pilot 模板 + Powerskill §四 Verify Agent 4 类抓法。

---

## 第一轮：完整性

**R1-01 节 1 US 引用不可验证**

`00-design.md §1` 引 "US-B1.8" 作为主 user story，但全文未提供 US-B1.8 原文来源文件路径（M04 pilot 在 `§ 关联参考` 引了 `/root/cy/prism/docs/product/feature-list-and-user-stories.md`）。`§15 checklist` 第 1 条勾 ✅ 但无法自验证——当前文件不能证明 US-B1.8 真实存在。PRD Q3.1 引用与 `01-PRD.md §Q3.1` 对照：Q3.1 原文 "4 步向导（上传→预览→映射→确认）+ 新增 git 导入入口" 和 `00-design.md §1 In scope` 描述基本一致，但 Q3.1 里 git 部分写的是"与 zip **单独入口**"，设计文档 §1 未明确两者入口是合并还是分离 UI，这是 PRD 原文有而设计文档未回答的细节。

**R1-02 frontmatter 字段不完整**

`00-design.md frontmatter` 有 11 字段（title / status / owner / created / accepted / supersedes / superseded_by / last_reviewed_at / module_id / prism_ref / pilot / complexity）。工程规约 11.3 模板样例有 7 个基础字段，而 M04 pilot `00-design.md` 比 M17 多了 `complexity` 字段，M17 已有，但 `tests.md frontmatter` 缺少 `supersedes` / `superseded_by` 两个字段（M04 `tests.md` 同样缺，说明模板在 tests.md 上本来就不一致，但这也是模板本身的遗漏）。`tests.md §frontmatter` 比 `00-design.md §frontmatter` 少 `module_id` 对应的 `supersedes`/`superseded_by`，与规约 11.3 "所有 design/ 下的 Markdown 必须有 frontmatter" 要求比较，缺字段是确认的问题。

**R1-03 节 4 状态机：禁止转换表不完整**

`00-design.md §4` "禁止的转换"表只列了 2 条：终态不可变 + 跳步。但以下禁止转换未显式列出：
- `partial_failed → completed`（应只能 → ai_step3）
- `awaiting_review → importing`（跳过 ai_step3）
- `failed → any`（文字提到终态，但 failed 在 mermaid 图里没有从 failed 画 `→[*]`，而只在表格里说"30 天后清理"——mermaid 和文字不一致）

原则 4 要求"图必须包含：所有状态 + 允许转换 + **非法转换** + 触发事件 + 副作用"。非法转换表仅 2 行不达标。

**R1-04 节 5 约束清单：清单 2（乐观锁）未给豁免理由**

`00-design.md §5` 清单 2 答案 "❌ 不触发（无并发编辑场景）"，理由是 "import_tasks 单 user 不会自己并发改同一任务"。但 tests.md §3 C5 明确写 "review 阶段 user-A 改 mapping，user-B（同项目 editor）也改——第二个写覆盖第一个（无乐观锁）"。也就是说，M17 实际存在多 user 并发写 review 数据的场景，但 §5 的 "❌ N/A" 没有说明这个决策——是有意不加乐观锁还是遗漏？与清单 2 的豁免条件（"单用户能编辑的实体"）不符合。

**R1-05 节 12 Queue payload 类型注解不可 type-check**

`00-design.md §12` `ImportBatchInsertPayload.confirmed_data` 类型是 `dict`（裸类型），违反工程规约 3（Python 代码风格）`mypy strict` 要求——`dict` 无 key/value 类型 = mypy 会告警。M04 pilot 中 content 用 `dict[str, Any]` 并显式 import `Any`，M17 的 `ImportBatchInsertPayload.confirmed_data: dict` 缺类型参数，CI `uv run mypy api/` 会失败。此外 `ImportAIStepPayload.chunk_id` 类型 `UUID | None` 正确，但 `ImportExtractPayload.source_type` 是 `str` 而非 `ImportSourceType` 枚举——前者无法让 mypy 静态检查枚举合法性，与原则 1（SQLAlchemy/Pydantic 是唯一真相源）精神相违。

**R1-06 节 13 AppError 子类不完整**

`00-design.md §13` ErrorCode 列了 8 个，但 AppError 子类代码块只有 5 个（缺 `ImportBatchInsertFailedError` / `ImportQuotaExceededError` / `ImportTaskDuplicateError` 对应的子类）。M04 pilot `§13` 每一个 ErrorCode 都对应一个 AppError 子类，M17 3 个 ErrorCode 无对应子类——工程规约 7.3 要求"业务错误必须用 AppError 子类，禁止裸 `raise Exception`"，缺子类意味着 AI 实现时无从继承。

**R1-07 节 15 checklist 第 3 条声称**

`§15 checklist` 第 3 条勾 ✅ 写 "SQLAlchemy class（双表 + 11 状态 + 5 状态枚举 item）"。但 `ImportTask.status` 在 SQLAlchemy model 中类型是 `Mapped[str]`（不是 `Mapped[ImportTaskStatus]`），不使用枚举类型作为列类型。这与 "11 状态枚举" 的声称不符——Python 枚举 `ImportTaskStatus` 存在，但 ORM 列没有用它。DB 层用 `CheckConstraint` 做字符串枚举防护，但 Python 层失去了类型安全。checklist 勾 ✅ 但实际有问题。

---

## 第二轮：边界场景

**R2-01 跨章节：节 3 SQLAlchemy vs 节 9 DAO：idempotency 查询缺 project_id**

`00-design.md §3` `ImportTask.__table_args__` 唯一约束是 `UNIQUE(user_id, source_hash)`。§9 `find_idempotent` 查询也只过滤 `user_id + source_hash`，**没有过滤 project_id**。这导致：用户 A 在 project-1 传了 zip-X，稍后在 project-2 传同一 zip-X，会命中 idempotency 并返回 project-1 的 task——但这个 task 属于 project-1，写入目标也是 project-1 的 nodes，结果是 project-2 的操作被"复用"到了错误 project。这是一个跨项目数据污染 bug。§5 "Tenant 隔离" 声称 Queue payload 强制带 project_id，但 idempotency 判断逻辑恰好跳过了这层。

**R2-02 取消（cancelled）状态的多阶段回滚路径不一致**

`00-design.md §4` 允许转换表写 `importing → cancelled : 已写入回滚`。tests.md §7 SM5 写 "已写入 nodes/dimensions/competitors/issues 全部回滚（事务包裹支持）"。但 §5 多表事务说明里写的是 importing 阶段 `with db.begin():` 包批量 INSERT——若 cancel 是通过 `service.cancel(task_id)` 调用触发的，而此时 Queue worker 正在执行 `db.begin()` 事务内，cancel 操作是另一个 HTTP 请求产生的独立 DB session，两个并发 session 的交互没有设计说明。具体地：worker session 的事务是否会检测到 cancel 信号并回滚？还是完成后写入再补回滚？`00-design.md §8` 写了"worker 检测 status=cancelled 中断处理"（在 tests.md C4 里描述），但 §8 和 §4 的 importing 阶段没有说明"在批量 INSERT 事务中途检测 cancel"的时机和机制——是每个 item INSERT 后检查一次 status？还是整个批量完成后？这个细节缺失意味着 AI 实现时会随机选择，产生数据一致性风险。

**R2-03 WebSocket 鉴权：每个事件入口的 task_id 归属校验缺失**

`00-design.md §8` 权限表 "WebSocket connect: 同 Router + 校验 task_id 归属"——只说 WS 握手时校验，没说每个**消息入口**是否重校。当 client 发送 `ClientCommand {type: "cancel", task_id: UUID}` 时，服务器只根据握手时验证的 task_id 处理，还是每次 command 都重新验证 `task_id` 是否属于握手 user？如果同一 WS 连接客户端发 cancel 时任意传 task_id，服务器直接调 `service.cancel(payload.task_id)`，就绕过了鉴权。`§7 WebSocket 事件 schema` `ClientCommand.task_id` 是客户端传的，没有说明服务器是否校验它等于握手时的 task_id。

**R2-04 idempotency 边界：status=partial_failed 的不复用规则与 §9 代码矛盾**

`00-design.md §11` 写 "不复用范围：`status IN ('failed', 'cancelled')` 的任务不复用"。§9 `find_idempotent` 代码写的是：
```python
ImportTask.status.in_(["completed", "awaiting_review", "partial_failed"])
```
即 `partial_failed` 会被复用。但按 §11 的文字，`partial_failed` 不在"不复用"清单里，所以 §9 代码的复用是正确的。然而 §11 和 §9 对 `partial_failed` 的处理各自表述，用户如果点"重新上传同文件"且上次是 `partial_failed`，他会拿回那个部分失败的 task——这是否符合业务预期？文档没有明确说明，且 §11 文字没写 `partial_failed` 是否复用，但代码隐含复用，两处信息不完整。

**R2-05 虚假声明：§5 事务说明与实际写入表不一致**

`00-design.md §5` 多表事务说明：`importing` 阶段批量 INSERT "① nodes ② dimension_records ③ competitors ④ issues ⑤ activity_log"。但 `00-design.md §2` 依赖模块图写 M17 写入的是 M03/M04/M06/M07——这意味着 M17 要直接向其他模块的主表（nodes / dimension_records / competitors / issues）批量 INSERT。然而 M04 pilot 明确说 `dimension_records` 是 M04 的主权表，M06 说 `competitors` 是 M06 主权表——M17 直接跨模块写其他模块的主表，违反了模块边界原则，且没有任何设计说明（"M17 是否应该调 M03/M04/M06/M07 的 Service 方法而不是直接 INSERT 表"）。这是跨模块越权写，是架构层面问题，§5 没有解释这个决策。

**R2-06 Queue 死信通知机制：WebSocket vs email 含糊**

`00-design.md §12` 死信处理写 "通知用户（WebSocket + email TBD）"。"TBD" 在设计阶段是悬置——如果用户关闭了浏览器，死信触发时无活跃 WS 连接，WebSocket 通知失效。email 是 TBD，意味着实际上死信只有 activity_log + 30 天后自动清理，用户可能完全不知道任务失败。tests.md §6 R4 只测了 "cron 任务删 task + items + S3 暂存文件"，没有测 "通知机制是否触达用户"——测试漏了死信通知路径。

**R2-07 节 3 vs 节 4：ai_step2 到 awaiting_review 的状态机 vs SQLAlchemy 枚举矛盾**

`00-design.md §4` 状态机写 `ai_step2 → awaiting_review : 提取+补全完成`。但 §3 SQLAlchemy `ImportTaskStatus` 枚举：`ai_step2 = "ai_step2"` 后面是 `ai_step3 = "ai_step3"`，枚举**顺序**是 `ai_step2 → ai_step3`，跳过了 `awaiting_review`（定义在 `ai_step3` 之前）。这不影响功能，但说明枚举定义顺序和状态机流转顺序不一致，容易给 AI 实现者造成误导。

---

## 第三轮：演进 + 模板异步字段可复用性

**R3-01 M13/M16/M18 能套用 M17 异步模板吗？——不能直接套，需要子模板**

M17 的 §12 Queue payload 基类设计（`TaskPayload` 强制 `user_id + project_id`）是优质基础，理论上可复用。但：

- **M13（流式 SSE）**：不使用 Queue，WebSocket 进度推送也不适用（SSE 是单向 HTTP 流，不需要 WS 连接管理）。M17 的 §8 权限表中 "Queue 消费者侧权限" 对 M13 无意义，"WebSocket connect" 对 M13 也无意义——M17 的异步字段模板对 M13 的适用项只有 §5（4 维必答）和 §9（DAO tenant），其余异步字段是噪音。
- **M16（后台异步，fire-and-forget）**：不用 Queue，不需要 §12 的 payload schema 章节，但需要类似的"后台任务状态管理"。M17 §12 的格式对 M16 的 "后台异步" 模式无法复用——fire-and-forget 没有 arq `@task` / 没有 `ImportExtractPayload` 这样的 payload 结构。
- **M18（Queue 嵌入，pgvector）**：和 M17 同是 Queue 异步，§12 基类设计**可以复用**，但 M18 的任务粒度是"单 node 的 embedding 计算"（小粒度，高频），M17 的批量事务模式（5 表原子写入）对 M18 过重。

**结论**：§12 需要拆成两个子模板——`Queue-heavy（M17/M18）` 和 `Queue-light（M18 嵌入）`；M13 / M16 应有独立的"流式异步模板"和"后台异步模板"，CLAUDE.md 里已经区分三种异步 emoji（🌊🪷🗂️），但模板没有对应拆分。

**R3-02 §8 Queue 消费者侧权限段应抽出为独立 ADR**

`00-design.md §8` 写 "Queue 消费者不经过 HTTP Router——若仅 Router 权限 = 越权风险，M17 必须在 Service 层做权限检查 + Queue payload 强制带 tenant 字段"。这段内容已经是架构级决策，不是 M17 特有的——它对 M18 同样适用（M18 也是 Queue 异步）。`04-layer-architecture.md §Q4` 已经有这个决策描述（"真实例子：异步路径的权限绕过"），但没有形成独立 ADR。当前状态是：这个决策同时存在于 `04-layer-architecture.md §Q4`、`06-design-principles.md 清单 3`、`M17/§8`——三处写法不一致（层级不同），未来 M18 实现时 AI 会复制 M17 的局部描述，造成漂移。**建议**：起 ADR-002 或在 `06-design-principles` 清单 3 里加 "Queue 消费者侧权限" 标准实现，M17/§8 引用，不重写。

**R3-03 半年后演进：3 步 AI 流水线 → N 步可配置——当前设计无法支撑**

`00-design.md §3` `ImportAIStepPayload.step: int` 硬编码 1/2/3，`§12` 任务清单是 `import_ai_step1` / `import_ai_step2` / `import_ai_step3` 三个独立的 arq task 函数。如果半年后业务需要 N 步可配置（如加 step4 "合规检查"），需要：新建 `import_ai_step4` arq task、修改状态机（加 `ai_step4` 状态）、修改 SQLAlchemy 枚举、修改前端进度 UI。这四处变更都必须同步——没有任何抽象（如 `ai_step_runner(step_config)` 通用函数）隔离变更影响。当前设计将步骤数硬编码进状态机（11 个状态中有 4 个是具体步骤 + extracting），扩展成本是线性的而非配置化的。

**R3-04 半年后演进：多 AI Provider 并发——当前设计会产生 token 配额竞争**

`00-design.md §1` 写 "AI Provider 配置来源：项目级配置（M02 提供，每个项目可独立选 Claude/Codex/Kimi）"。当前 `ImportTask.ai_provider` / `ai_model` 是任务级别固定的。如果用户配置了多 provider 并发（如 step1 用 Codex，step2 用 Claude），当前的 `ImportAIStepPayload(step=N)` 没有携带 provider 信息（靠 task_id 从 DB 查），而 `ImportTask` 只存一个 `ai_provider` 字段，无法记录多步骤各自的 provider。这不是紧急 blocker，但如果半年后真的支持多 provider 并发，数据模型需要改动。

**R3-05 状态机 11 状态是否过度设计？**

`00-design.md §3` 枚举 11 个状态：pending / extracting / ai_step1 / ai_step2 / ai_step3 / awaiting_review / importing / completed / partial_failed / failed / cancelled。其中 `ai_step1` / `ai_step2` / `ai_step3` 三个中间步骤状态可以合并为 `processing`（携带 `progress` 字段 0-100 已有），仅在 error_metadata 中记录具体失败 step。好处：状态机从 11 状态降到 8 状态，M17 特有的 3 个 ai_step 状态不会被 M18 复用（M18 的 embedding 只有一步），降低模板的步骤耦合。代价：调试时需要查 error_metadata 才能知道失败在哪步。当前设计没有讨论合并的可能性——对模板复用是负担，对 M18 来说 3 个 ai_step 状态完全是噪音。

---

## 总评

| 维度 | 评分(/10) | vs M04 pilot | 关键风险 |
|------|-----------|-------------|---------|
| **完整性** | 7 | M04=9 | AppError 子类 3 缺；状态机禁止转换不全；mypy 类型问题 |
| **边界场景** | 6 | M04=8 | idempotency 跨项目 bug；取消回滚并发机制不明；WS 逐 command 鉴权缺失 |
| **演进设计** | 6 | M04=N/A | 步骤硬编码无扩展抽象；Queue 消费者权限应抽 ADR；异步模板需拆子模板 |
| **跨文件一致性** | 7 | — | §11 vs §9 partial_failed 复用逻辑表述不完整 |
| **架构合规** | 6 | — | M17 跨模块直写其他模块主表（nodes/dimension_records）无设计说明 |

---

## 入场判断

- [ ] **M17 能转 accepted 吗？** **否**。存在 3 个 blocker（见下方），须修复后重新 audit。
- [ ] **异步字段模板能否被 M13/M16/M18 复用？** **不能直接复用**。§12 Queue payload 基类可复用（M18），但需要拆出 3 个子模板（Queue-heavy / 流式 / 后台异步），并将 Queue 消费者权限决策抽为 ADR 或规约清单条目。

---

## 必修问题清单（block 准入）

| # | 节 | 问题 | 优先级 |
|---|----|------|--------|
| B1 | §9 `find_idempotent` | idempotency 查询缺 `project_id` 过滤，导致跨项目 task 被复用（R2-01） | 🔴 blocker |
| B2 | §1 / §2 / §5 | M17 直接批量 INSERT 跨模块主表（nodes/dimension_records/competitors/issues），违反模块边界——缺设计说明：是直接写表还是调目标模块 Service？（R2-05） | 🔴 blocker |
| B3 | §13 AppError 子类 | `ImportBatchInsertFailedError` / `ImportQuotaExceededError` / `ImportTaskDuplicateError` 三个 ErrorCode 对应子类缺失（R1-06） | 🔴 blocker |
| B4 | §4 状态机 | 禁止转换表不完整（partial_failed→completed / awaiting_review→importing / failed→any 未列）（R1-03） | 🟠 major |
| B5 | §12 TaskPayload | `ImportBatchInsertPayload.confirmed_data: dict` 缺类型参数，mypy strict 会失败；`ImportExtractPayload.source_type` 应用 `ImportSourceType` 枚举而非 `str`（R1-05） | 🟠 major |
| B6 | §8 WebSocket | ClientCommand 中 task_id 服务器是否逐 command 重新校验归属，缺设计说明（R2-03） | 🟠 major |
| B7 | §5 清单 2 | 并发答案 ❌ 但 tests.md C5 存在多 user 并发写 review 场景，决策理由需对齐（R1-04） | 🟡 minor |

---

## 模板调整建议（M04 pilot 模板需要补的）

1. **§12 拆子模板**：当前模板 §12 "Queue payload schema（同步模块显式 N/A）"——建议改为：
   - `§12A`：Queue 异步（🗂️）：payload schema + 任务清单 + 重试策略（M17/M18 用）
   - `§12B`：流式异步（🌊）：SSE endpoint + 流式 chunk schema（M13 用）
   - `§12C`：后台异步（🪷）：job status polling schema + 轮询端点（M16 用）
   - 同步模块：§12 显式 N/A（现有方式保留）

2. **§8 新增 "Queue 消费者侧权限" 标准格式**：在 §8 权限表中强制增加第 5 行（Queue 消费者侧），对所有 Queue 模块（🗂️）为必填，其他模块显式 N/A。

3. **§3 SQLAlchemy 模型：状态枚举列类型要求**：模板应明确要求 status 字段使用 `Mapped[StatusEnum]` 而非 `Mapped[str]`，配合 `CheckConstraint` 做双重防护（Python 层 + DB 层）。

4. **§11 idempotency：需增 "project_id 是否参与 key 计算" 的显式问答**：对于 tenant 级资源，idempotency key 设计必须回答 project_id 是否在 scope 内。当前模板没有强制此问，M17 在此踩坑（R2-01）。

5. **§4 状态机：禁止转换表模板要求强化**：模板应要求"列出至少 N 条非法转换（N = 终态数 + 1）"，防止仅列 2 条就 checklist 勾 ✅。
