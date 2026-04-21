---
title: 第二批 4 模块对抗式 reviewer audit
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: 2
modules: [M02, M03, M11, M12]
---

# 第二批 4 模块对抗式 reviewer audit

> **审稿立场**：独立、不附和、找问题。每条问题引用具体文件路径+节号。
> **参照基线**：README.md 16 字段模板 + 13 硬规则（R0-1/R3-1~3/R4-1~3/R5-1~2/R7-1~3/R8-1~3/R11-1~3/R13-1~2/R14-1/R15-1/R-X1）+ M04 pilot 基线。

---

## 1. 执行摘要

第二批 4 模块整体完整度明显优于第一批——frontmatter 12 字段全部达标，R-X1 orchestrator 纪律（M11）有明确声明，R11-2 project_id 参与 key 均答复。但存在以下系统性问题：

1. **状态字段类型缺陷**：M02/M03 的 SQLAlchemy model 状态字段使用 `Mapped[str]` 加 `String(N)` 存储，而非 `Mapped[ProjectStatus]` / `Mapped[NodeType]` ——违反 R3-2（尽管定义了 Python Enum，但 mapped_column 的 SA 类型仍是 String，没有使用 `Enum` SA 类型）。
2. **M12 §5 核心决策半成品**：快照"存引用 vs 存值"标注了 ⚠️ 待裁决，但 5 个节（节 3/4/5/7/15）都以 AI 默认值 A 展开，未给出"若 CY 选 B"时的完整改回成本估算——缺少候选 B 的数据规模分析和迁移成本说明。
3. **M03 拖拽重排事务决策链断**：节 5 事务答案是 ⚠️ 待裁决，但节 7 `NodeReorder` schema 已按"需要事务"设计，内部不一致。
4. **tests.md R14-1 声称无 ⚠️ 渗漏，实为误标**：M12/tests.md 行头注明"基于 AI 默认值"，声称 R14-1 合规，但这等于把未裁决的决策当已定稿处理——R14-1 原意是"写完时所有决策已定，禁止 ⚠️ 渗漏"，而 M12/tests.md 本身在 ⚠️ 决策未定时就已写完，属于形式合规实质违规。

三轮共发现 **29 个问题**（完整性 14 / 边界场景 9 / 演进+模板 6）。

---

## 2. 三轮问题清单

### 第一轮：完整性

#### M02 项目管理（`M02-project/00-design.md`）

**M02-R1-01**（节 3，R3-2）：`Project.status` 字段声明为 `Mapped[ProjectStatus]`，但 `mapped_column` 的 SA 类型是 `String(20)`——SQLAlchemy 不会自动将 Python Enum 映射到 PG CHECK；正确写法是 `mapped_column(SAEnum(ProjectStatus), ...)` 或 `mapped_column(String(20), nullable=False, default=ProjectStatus.active)` 配合 `CheckConstraint`。同样问题出现在 `ProjectMember.role: Mapped[MemberRole] = mapped_column(String(20),...)`。Alembic 要点里只有 `CHECK status IN ('active','archived')`，但 SA Enum 类型生成的 DDL 是 `CREATE TYPE projectstatus AS ENUM ...`，两者会冲突。R3-2 要求"状态字段必用 `Mapped[StatusEnum]`"——当前写法只做到了 Python 类型注解，SA 类型层实际是裸 String，不符合 R3-2 精神。

**M02-R1-02**（节 4，R4-2）：状态机禁止转换清单标注"N = 终态数 + 1 = 2"，但 `archived` 是终态还是中间态尚未裁决（Q3：归档是否可恢复）。若 archived 是可逆中间态，终态数 = 0（无终态），则禁止转换列数 N 至少 = 1——但当前的 3 条禁止转换写法隐含 archived 是终态的假设。设计文档内部依赖未定的 Q3 而不标联动关系。

**M02-R1-03**（节 5，R5-1）：约束清单第 4 项（idempotency_key）答案是"⚠️ 邀请操作待 CY 裁决"，而节 11 已给出 AI 默认 A（无幂等），两处结论不一致。节 5 清单表格和节 11 应相互引用，而非各自标不同状态。

**M02-R1-04**（节 13，R13-1）：`PROJECT_NAME_DUPLICATE` ErrorCode 本身标注了 ⚠️（AI 推断：项目名是否唯一），但对应的 `ProjectNameDuplicateError` AppError 子类已写完。如果 CY 裁决"允许重名"，这个 ErrorCode + AppError 需整体删除——但 §15 checklist 第 13 条勾选了"ErrorCode 11 条 + 每条对应 AppError 子类"，没有标注哪条是 ⚠️ 待定，checklist 虚假完成。

#### M03 功能模块树（`M03-module-tree/00-design.md`）

**M03-R1-05**（节 3，R3-2）：同 M02-R1-01 问题。`Node.type: Mapped[NodeType] = mapped_column(String(20), ...)` 同样是 Python Enum 注解 + SA String 类型混用，违反 R3-2。ER 图里 `NodeType type` 已正确标注为枚举，但 SQLAlchemy class 实现层用的是 `String(20)`。

**M03-R1-06**（节 4，R4-1/R4-3）：状态机图缺失。节 4 声明"nodes 表无状态字段"，R4-1 显式声明无状态是合规的；但紧接着写了"若 CY 选候选 B（有状态）"的条件状态机草图——这张图不完整，`archived → [*]`（物理删除）的禁止转换只列了 3 条，但按 R4-2，N = 终态数+1 = 2（deleted 是事实终态），至少列 2 条，而第 3 条"跳过 archived 直接物理删除 active 节点"描述模糊，不是标准禁止转换格式。候选 B 的图是准备给 CY 裁决用的，但其自身质量不达标，若 CY 选 B 则直接引入缺陷。

**M03-R1-07**（节 5，R5-1，多表事务维度）：4 维必答的"多表事务"答案是"⚠️ 拖拽排序待 CY 裁决"——这不是一个有效答案，R5-1 要求"4 维必答"，未定内容应给出当前 AI 默认 + 两种路径的差异分析，而非直接在 4 维表格里放 ⚠️。第一批 batch1 audit 已指出类似问题（M06 §5 内部矛盾），M03 重蹈覆辙。

**M03-R1-08**（节 1，业务说明）：US-C1.1 被引用为 M03 的用户故事，但 US-C1.1 原文括号说明"引用 M03 数据"——这是 M10 全景图的用户故事（M10 使用 M03 数据），不是 M03 自己的需求；M03 §1 直接把 M10 的故事引入为自己的业务说明，属于边界混淆。M03 自身缺少独立的 US 故事（US-B1.1 / US-B2.1 合法，但 US-C1.1 不属于 M03）。

#### M11 冷启动（`M11-cold-start/00-design.md`）

**M11-R1-09**（节 3，R3-2）：`ColdStartTask.status: Mapped[ColdStartStatus] = mapped_column(Text, ...)` 使用 `Text` 作为 SA 类型，而非 `SAEnum(ColdStartStatus)` 或配合 `String`——与 R3-2 同类问题。Alembic 要点中 `error_report` 和 `status` 字段的 CHECK 约束列了 6 个值，但模型声明了 `partial_failed` 值（仅在候选 B 策略下使用），而 AI 默认是候选 A（全量事务，不存在 partial_failed 状态）。当前模型和默认策略不一致——`partial_failed` 状态在 AI 默认 A 下不可达，但 CHECK 约束和 Enum 定义里都有，形成僵尸状态。

**M11-R1-10**（节 4，R4-2）：状态机禁止转换声称"终态数=2，至少列 3 条禁止"——但 `completed` 和 `failed` 均是终态，加上 `partial_failed`（若 CY 选 B）是第三个终态。禁止转换第 1 条"completed/failed → 任意"把两个终态合并为一条，实际上应拆为两条（`completed → 任意` 和 `failed → 任意`），才能满足 N = 终态数+1 的数量要求（最少 3 条，但每个终态都应有独立条目）。

**M11-R1-11**（节 10，activity_log）：`cold_start.partial_failed` 事件仅在候选 B 策略下才会触发，但当前 activity_log 清单把它作为普通事件列出，没有条件注释。M04 pilot 的 activity_log 清单格式是无条件的，M11 掺入了条件事件但没有标注"仅候选 B"。

#### M12 对比矩阵（`M12-comparison/00-design.md`）

**M12-R1-12**（节 3，核心决策完整性）：快照"引用 vs 值"是 M12 核心设计决策，文档在节 3 给出了 A/B 候选分析，但**缺少候选 B 的关键量化**：N 个 node × M 个 dimension 的快照场景下，B 方案每次保存快照需要写多少行 `comparison_snapshot_items`，以及若未来选 B 需要 Alembic 迁移补表的成本说明。设计决策框架（memory `feedback_design_decision_framework.md`）要求"约束→候选→筛选→砍掉→验证"——当前文档在"砍掉"和"验证"部分对候选 B 说明不足，CY 没有足够信息来做改回成本判断。

**M12-R1-13**（节 4，R4-2）：状态机禁止转换只列了 2 条，标注"终态实质 1（deleted 即消失），至少列 N=2 条"——这是在用"删除即消失"来绕过 R4-2 的数量要求。`deleted` 虽不是枚举值，但是实体的事实终态；`saved` 本身是唯一的活跃态。按 R4-2 逻辑，终态数 = 1（删除后不可恢复），N = 2，最少列 2 条。当前 2 条中：第 1 条是"并发 rename version 不匹配"（是并发控制，不是状态转换禁止）；第 2 条是"删后操作返回 404"（是错误处理，不是状态转换禁止）。两条都不是标准的"禁止状态转换"格式，实质上 R4-2 未达标。

**M12-R1-14**（节 5，R5-2，状态转换竞态分析）：节 5 的状态转换竞态分析写在主 4 维表格之后的独立段落——这是合规的。但"读-删竞态"提到"节 6 说明降级策略"，而节 6 分层职责表中并没有"降级策略"的说明，是悬空引用。实际降级逻辑（节点被删后快照返回空 matrix）在 tests.md E7 里有测试，但设计文档节 6 无对应实现说明。

---

### 第二轮：边界场景

#### M02（`M02-project/00-design.md` + `tests.md`）

**M02-R2-01**（边界：同时邀请同一用户）：两个 owner 同时 POST 邀请同一 user_id 到同一 project——第一个成功，第二个应命中 `UNIQUE(project_id, user_id)` 约束返回 409 `MEMBER_ALREADY_EXISTS`。M02/tests.md 节 3 并发场景只有"同时归档"（C1）和"同时移除不同成员"（C2），**缺少"并发邀请同一用户"的并发测试用例**。这是 M02 最重要的并发场景（DB 唯一约束竞态），却未覆盖。

**M02-R2-02**（失败路径：创建项目多表事务回滚）：M02/tests.md ER2 场景"创建项目时 owner 写入失败"——但 M02 的创建项目事务包含 4 步：INSERT projects / INSERT project_members(owner) / INSERT project_dimension_configs（模板默认） / log activity。测试 ER2 只说"项目创建事务回滚"，没有区分"project_members 失败" vs "project_dimension_configs 失败"两种不同失败点——这两个失败点的回滚路径不同（configs 失败时 members 已写入），需要各自独立测试验证原子性。

**M02-R2-03**（边界：AI Provider 配置并发）：`ai_api_key_enc` 更新通过 PUT `/projects/{pid}`，两个 owner（或 owner 双 tab）同时更新 AI Key，最终以谁的为准？M02 §5 明确"不引入乐观锁"，但 AI Key 变更是安全敏感操作，last-write-wins 语义可能导致 Key 被静默覆盖而用户无感知。设计文档既未分析此竞态，tests.md 也无并发 AI Key 更新用例。

#### M03（`M03-module-tree/00-design.md` + `tests.md`）

**M03-R2-04**（并发：拖拽重排多节点事务 + path 一致性）：M03/tests.md C2"并发拖拽重排"只验证了 last-write-wins 无 500，但**没有验证 path 字段一致性**——若 sort_order 更新是批量 UPDATE，path 字段是否同步更新？`path` 依赖 `sort_order` 排序吗？（实际上 `path` 包含 `/rootId/parentId/thisId/`，不包含 sort_order，所以不联动）——这个关系在设计文档节 3 没有显式说明，导致测试不知道该不该验证 path。

**M03-R2-05**（失败路径：级联删除后 M04/M06/M07 孤儿数据）：M03 采用 DB 级 ON DELETE CASCADE（节 3 Alembic 要点），节点删除后 `dimension_records`（M04）/ `competitors`（M06）/ `issues`（M07）通过各自的 `node_id FK` 级联删除。但 M03/设计文档节 8 说"本期简化，直接级联删除，M04 等通过 CASCADE 处理"——这意味着 M03 删除节点时没有调用 M04 Service 的删除方法，而是依赖 DB CASCADE。这绕过了 M04/M06/M07 的 `activity_log`（各模块 Service 层才写 activity_log），级联删除后 M04 的 dimension_records 删了但无 activity_log 记录，违反清单 1（所有变更操作必须写 activity_log）。`tests.md` E4（删除有子节点的节点）没有验证下游 activity_log 是否正确记录。

**M03-R2-06**（边界：batch_create_in_transaction 的 path 计算）：M11/M17 调用 `NodeService.batch_create_in_transaction`，批量创建节点时 path 字段由 Service 层计算——但批量创建场景下，若节点之间有父子关系（CSV 第 1 行是父节点，第 2 行是其子节点），path 计算依赖父节点的 id（创建时才知道），批量操作时父节点 id 还未入库。设计文档节 6 说明了"M11 不直 INSERT"，但没有说明 `batch_create_in_transaction` 如何处理"父节点未知 id"的 path 计算问题——这是 M11 orchestrator 调用的核心技术债。

#### M11（`M11-cold-start/00-design.md` + `tests.md`）

**M11-R2-07**（失败路径：批量入库跨模块部分失败）：M11/tests.md ER3 场景"跨模块 Service 批量创建抛异常（如 NodeService）"——测试只验证了 NodeService 抛异常的情况。但 M11 顺序调用 M03/M04/M06/M07 四个 Service，若顺序是 M03 成功 → M04 成功 → M06 失败，此时 db.begin() 事务中 M03/M04 已执行（未 commit），M06 抛异常触发全量回滚——这个回滚路径有测试（ER2/ER3），但**缺少"M06/M07 失败而 M03/M04 成功时的 4 步回滚顺序"的专项测试**，仅测 NodeService 失败一个场景不够。

**M11-R2-08**（并发：同项目不同用户并发导入的节点路径冲突）：M11/tests.md C3 场景"不同用户同项目并发上传不同 CSV"期望"两个任务各自成功"——但若两个 CSV 都包含同一节点路径（如"产品线/模块A/功能1"），批量创建时 `nodes` 表没有 `UNIQUE(project_id, path)` 约束（M03 数据模型未定义），两个 CSV 会各自创建同名节点形成重复数据。设计文档未分析此场景，tests.md C3 假设"不同 CSV"但未定义"不同 CSV 包含相同节点路径时"的行为。

#### M12（`M12-comparison/00-design.md` + `tests.md`）

**M12-R2-09**（边界：快照 nodes_ref 内的 UUID 类型不一致）：M12 节 3 `nodes_ref: Mapped[list[str]]`——JSONB 存储的是 `[str(UUID), ...]`，而 `SnapshotResponse.nodes_ref: list[str]` 也是 string。但 M12 节 9 `get_matrix_data()` 的入参是 `node_ids: list[UUID]`，需要从 `nodes_ref: list[str]` 转换为 `list[UUID]`。设计文档没有说明这个类型转换在哪层做（DAO 层还是 Service 层），且 `nodes_ref` 存 str 的决定没有在节 3 注释理由（为何不存 UUID JSONB）。

---

### 第三轮：演进 + 模板可复用性

**EV-01（M02 SSO 演进）**：半年后加 SSO（SAML/OIDC），M02 的 `project_members` 靠 `UNIQUE(project_id, user_id)` 防重，但 SSO 用户可能有多个 identity provider，`user_id` 是否来自同一 M01 用户表？M02 §3 中没有 `external_identity_id` 预留字段，`space_id` 预留了但 SSO 相关字段无预留——若加 SSO 需修改 M01 + M02 + `project_members` 表，影响面没有在 M02 设计文档中评估。

**EV-02（M03 多 workspace 演进）**：M02 预留了 `space_id`（M20 扩展口），但 M03 的 `nodes` 表只有 `project_id`，无 `space_id`。若未来 workspace 概念引入，M10 全景图（依赖 M03 树结构）可能需要跨 project 查询节点——M03 当前只支持 project 级隔离，无 space 级聚合查询接口。M03 设计未评估此演进路径。

**EV-03（M11 Queue 异步演进）**：M11 §1 边界灰区说"超过 10MB/1000 行是否升级 Queue 异步"——AI 默认不升级。但 `cold_start_tasks` 表结构（status / total_rows / success_rows / failed_rows）完全兼容异步 Queue 模式（M17 模式），若未来升级只需加 Queue payload。这个演进路径成本低，建议在设计文档节 1 或节 3 明确注释"本表结构预留 Queue 升级口"，而非在边界灰区简单说"不升级"。

**EV-04（M12 快照版本化演进）**：若半年后快照需要版本化（每次编辑生成历史快照），当前 `comparison_snapshots` 表没有 `parent_snapshot_id` 或版本链字段。`version` 字段当前是乐观锁计数器，不能用于版本链。若改为值快照（候选 B），快照版本化成本更低（items 表自带历史数据），但引用快照（候选 A）需要新增 `snapshot_versions` 表。这个演进差异应在 M12 §3 快照策略决策中列为附加维度，但当前缺失。

**EV-05（跨模块命名一致性问题）**：
- M11 `cold_start_tasks` vs M17 `import_tasks`：两个 orchestrator 模块命名约定不同（`cold_start_*` vs `*_task`），未来 M18/M13 若也有任务表，缺乏统一命名规范。
- M12 `comparison_snapshots.nodes_ref` / `dimensions_ref`（str 数组）vs M04 `DimensionRecord.node_id`（UUID 字段）：M12 存 str(UUID) 而 M04 存原生 UUID，读写时需要类型转换，应在设计文档中明确约定 JSONB UUID 存储格式为 string 而非 native UUID 的原因（PG JSONB 实际上不区分，但 Python ORM 层需要明确）。
- M02 `project_dimension_configs.sort_order` vs M03 `nodes.sort_order`：两处 sort_order 字段语义相同但所属表不同，M02 batch update 接口一次更新所有维度的 sort_order，M03 reorder 接口也是批量，两者实现应保持对齐——设计文档未交叉引用。

**EV-06（模板新建议）**：
基于第二批 4 模块发现，建议 README 模板补充：
1. **§3 字段**：新增"SA Enum 类型 vs Python Enum 注解的区分"注释，防止 R3-2 被形式合规绕过——即 Python 类型注解 `Mapped[StatusEnum]` 是 ORM 注解层，SA 类型必须用 `SAEnum(StatusEnum)` 或明确的 CheckConstraint，两者须兼备。
2. **§4 禁止转换格式**：要求每条禁止转换必须格式为"状态A → 状态B：原因 + 错误码"，不允许多状态合并为"X / Y → 任意"。
3. **§3 核心决策**：对于有 ⚠️ 核心决策的模块（如 M12 引用 vs 值），模板应增加"候选 B 改回成本"必填项——量化行数/表数/迁移 Alembic 步骤。

---

## 3. 每模块评分（10 分制 vs M04 pilot 基线）

| 模块 | 分数 | 主要扣分点 |
|------|------|-----------|
| **M02** | 7.0 | R3-2 SA 类型不规范（-1）/ Q3 未裁决造成状态机内部矛盾（-1）/ 并发测试覆盖不足（-0.5）/ checklist 虚假完成（-0.5） |
| **M03** | 6.5 | R3-2 同 M02（-1）/ US-C1.1 边界混淆（-0.5）/ §5 多表事务 ⚠️ 直接放表（-1）/ DB CASCADE 绕过 activity_log（-1） |
| **M11** | 7.5 | R3-2 Text 而非 SAEnum（-0.5）/ partial_failed 僵尸状态（-0.5）/ batch_create path 计算未说明（-0.5）/ 第一轮发现数最少 |
| **M12** | 7.0 | 候选 B 改回成本分析不足（-1）/ R4-2 禁止转换格式不规范（-1）/ nodes_ref 类型转换未说明（-0.5）/ 悬空引用节 6（-0.5） |

**M11 是四模块中质量最高的**，§6 R-X1 orchestrator 纪律明确，§11 R11-2 project_id 参与 key 有理由，§12 N/A 显式声明。

---

## 4. 关键模板调整建议（3-5 条，可执行）

**TA-01**（§3 R3-2 加固）：README §3 硬规则 R3-2 补充：
> "Mapped[StatusEnum] 必须配合 `mapped_column(SAEnum(StatusEnum), ...)` 或 `String(N)` + `CheckConstraint`（双重防护）——仅有 Python Enum 类型注解不满足 R3-2，SQLAlchemy 级类型约束是必须的。审计时检查 `mapped_column(...)` 第一个参数是否为 `SAEnum` 或 String+CHECK 兼备。"

**TA-02**（§4 R4-2 格式要求加固）：README §4 硬规则 R4-2 补充：
> "禁止转换每条格式必须是'状态A → 状态B：原因 + 对应 ErrorCode'，不允许多状态合并写法（如'X/Y → 任意'）。合并写法实际只算 1 条，不满足 N 的数量要求。"

**TA-03**（§3 核心决策模块增加"改回成本"必填项）：对有 ⚠️ 核心设计决策（如存引用 vs 存值、有持久化 vs 无持久化）的模块，在节 3 核心决策块中增加：
> "**候选 B 改回成本**（必填）：若当前选 A 后需改为 B，需要的 Alembic 迁移步数 / 新增表数 / 受影响模块数。"

**TA-04**（§5 4 维必答不允许 ⚠️ 占位）：README §5 R5-1 补充：
> "4 维必答表格中禁止出现 ⚠️ 作为答案——⚠️ 只能标注在 §15 待裁决表中。4 维表格中必须给出 AI 默认值 + 候选说明，不能以'待 CY 裁决'作为 4 维答案。"

**TA-05**（§6 跨模块 CASCADE 安全说明）：README §6 新增机械检查项：
> "若本模块其他模块的 FK 设为 ON DELETE CASCADE，必须在 §6 禁止列中显式说明'DB CASCADE 不触发下游模块 activity_log，若需要 activity_log 则必须改为 Service 层调用下游 Service.delete()'。M03 是反面教材。"

---

## 5. 入场判断

| 模块 | 能/不能转 accepted | 必须补什么 |
|------|-----------------|-----------|
| **M02** | ❌ 不能 | 1. R3-2：`ProjectStatus`/`MemberRole` mapped_column 改用 `SAEnum` 或显式双重防护；2. Q3 裁决（archived 是否可逆）→ 禁止转换清单联动更新；3. tests.md 补"并发邀请同一用户"用例 C3；4. §5 清单 4 idempotency 统一为 A（或与节 11 对齐） |
| **M03** | ❌ 不能 | 1. R3-2：`NodeType` mapped_column 改用 `SAEnum`；2. §5 多表事务维度给出明确 AI 默认值（不留 ⚠️）；3. US-C1.1 从 §1 移除或改引 M10 out-of-scope 说明；4. §8 节点删除时 DB CASCADE vs Service 调用决策需明确，并标注 activity_log 影响 |
| **M11** | ⚠️ 条件通过 | 1. R3-2：`ColdStartStatus` mapped_column 从 `Text` 改为对应规范类型；2. `partial_failed` 僵尸状态处理（若 AI 默认 A=全量事务，则 Enum + CHECK 中移除 `partial_failed`，或标注"候选 B 保留"）；3. §3 `batch_create_in_transaction` 父子节点 path 计算机制需在节 6 或节 3 说明 |
| **M12** | ⚠️ 条件通过 | 1. §3 核心决策补充候选 B 改回成本（迁移步骤 + 行数估算）；2. §4 禁止转换重写（格式合规，移除并发控制/错误处理混入状态转换的条目）；3. §6 补充"节点被删后矩阵降级"实现说明（解决悬空引用）；4. `nodes_ref` str vs UUID 类型约定在 §3 显式注释 |

---

## 特别关注回答

**Q: M11 §6 是否写了跨模块 orchestrator 纪律？**
✅ **是**。M11/00-design.md 节 6 标题明确写"关键原则：M11 是 orchestrator——不直 INSERT 跨模块表，只调 M03/M04/M06/M07 的 batch_create_in_transaction（R-X1）"，并在禁止列表中列出 4 条具体禁止。这是第二批 4 模块中最值得肯定的设计纪律——但 R-X1 只解决了"不直写"，没有解决"父子节点 batch_create 时 path 计算顺序"的技术问题（见 M03-R2-06）。

**Q: M12 §5 核心决策"存引用 vs 存值"是否清晰？**
⚠️ **半清晰**。候选 A（引用）和候选 B（值）的优缺点描述完整，AI 默认值理由充分。但候选 B 的"改回成本"缺失量化——未来若需要查看历史时刻数据，从 A 迁移到 B 需要补 `comparison_snapshot_items` 表并回填历史数据，这部分成本说明缺失，CY 做决策时信息不完整。

**Q: 有没有状态字段用了裸 str 而非 Mapped[Enum]？**
⚠️ **有，且系统性**：
- M02/models/project.py：`ProjectStatus`/`MemberRole` 的 `mapped_column(String(20), ...)` — 裸 String
- M03/models/node.py：`NodeType` 的 `mapped_column(String(20), ...)` — 裸 String  
- M11/models/cold_start_task.py：`ColdStartStatus` 的 `mapped_column(Text, ...)` — 裸 Text

四个模块中 3 个存在此问题（M12 同类型：`ComparisonSnapshotStatus` 的 `mapped_column(Text, ...)`）。Python 类型注解层（`Mapped[StatusEnum]`）是对的，但 SQLAlchemy 列类型层用的都是 String/Text 而非 `SAEnum(StatusEnum)`。CheckConstraint 只做了部分 fallback（M02/M03 有 CHECK，M11/M12 的 CheckConstraint 内容是枚举值列表但 SA 列类型仍是 Text），整个第二批均违反 R3-2 的严格解释。

---

## 关联参考

- 模板基线：`/root/cy/prism-0420/design/02-modules/README.md`
- 同步 pilot：`/root/cy/prism-0420/design/02-modules/M04-feature-archive/00-design.md`
- 第一批 audit：`/root/cy/prism-0420/design/02-modules/audit-report-batch1.md`
- ADR-002（异步权限）：`/root/cy/prism-0420/design/adr/ADR-002-queue-consumer-tenant-permission.md`
