---
title: 第一批 5 模块对抗式 reviewer audit
status: draft
owner: reviewer-agent
created: 2026-04-21
batch: 1
modules: [M05, M06, M07, M14, M19]
---

# 第一批 5 模块对抗式 reviewer audit

> **审稿立场**：独立、不附和、每条问题必须有文件路径+节号。
> **参照基线**：A 档（01-PRD / 05-module-catalog / 06-design-principles）+ B 档规约 1/5/7/11.3/12 + M04 pilot 模板。

---

## 第一轮：完整性

### M05 版本演进时间线

- **M05/00-design.md 节 1**：US 编号 US-B1.5 / US-C1.4 引用格式正确，但 US-B1.5 来源文件未验证存在（PR 业务说明仅引"根据 PRD Q3"作补充，PRD Q3 原文没有版本时间线的明确表述，是 AI 推断拼接 F5 生成的，不是真正引用 PRD 节）。

- **M05/00-design.md 节 3（Alembic 要点）**：`is_current` 切换路径描述为"Service 层先 UPDATE 旧 isCurrent=false，再 UPDATE 新 isCurrent=true（同一事务内，非多表事务）"——但 节 5 多表事务答案是 ❌。这是矛盾：同一事务内两次 UPDATE 确实是单表，技术上没错，但"先清空所有 is_current=true，再设新的"这两步若未包在事务内会产生竞态窗口（同一 node 短暂无 current 版本）。事务包裹必须显式，但 节 5 对"是否用事务"的说明不清晰，节 9 的 `clear_current_flag` 方法也没有体现是否在事务中调用。

- **M05/00-design.md 节 5 约束清单**：清单 2（乐观锁 version）答案是 ❌ N/A，但节 3 SQLAlchemy 模型没有 `version` 字段——这是合规的（无并发不需要），但节 15 checklist 没有要求"确认 version 字段不需要"的勾选；M04 模板的 checklist 没有这一项，5 个模块都如此，缺失对清单 2 的显式排除记录。

- **M05/00-design.md 节 7**：`VersionUpdate` schema 没有 `is_current` 字段（符合设计意图——切换当前版本用独立端点），但 `snapshot_data` 是否可通过 PUT 更新是 ⚠️ AI 推断待裁决，若 CY 选 A（不允许），需在 Router 层明确拒绝（schema 里没有 snapshot_data → Pydantic 自动拒绝，但文档没说这一点）。

- **M05/00-design.md 节 15 checklist**：比 M04 pilot 少了三项 reviewer audit 通关勾选（M04 有三轮 🔴 强制）。这不是格式错误，是 AI 生成时故意省略的，但降低了准入门槛一致性。

### M06 竞品参考

- **M06/00-design.md 节 1 业务背景**："US-A3.3（间接）"——US-A3.3 在 PRD 中无直接文本引用（设计文档未提供 US-A3.3 的具体原文），标注"间接"的理由不充分，疑为 AI 推断拼凑。

- **M06/00-design.md 节 5（4 维必答）**：多表事务答案是 ❌，但节 15 Q4 又明确说"新建竞品 + 同时创建对标"推荐包一个 Service 层事务（候选 B）。如果 Q4 CY 选 B，则 节 5 事务答案需变为 ✅，但两处不联动——AI 推断造成的内部矛盾，设计文档自相矛盾。

- **M06/00-design.md 节 3 Alembic 要点**：`competitors` 表没有唯一约束。文档明确说"竞品名称无唯一约束（可以有两个同名竞品）"（节 11），但这个业务决策没有在 Alembic 要点里显式说明"intentionally no UNIQUE on display_name"——默认读者不知道这是有意为之还是遗漏。

- **M06/00-design.md frontmatter**：缺少 `pilot: false` 字段（M14 / M19 有，M05 / M06 / M07 均无，不一致）。按规约 11.3 frontmatter 应全字段一致。

- **M06/tests.md 节 2 E7**："⚠️ 待 CY 裁决：A. 级联删（204）/ B. 422 阻止"——测试场景遗留未定的业务决策，不应出现在测试文件中（应在 design.md 节 1 边界灰区或节 15 Q 列表里裁决）。测试文件里有未决策的 ⚠️ 说明测试设计和业务设计脱节。

### M07 问题沉淀

- **M07/00-design.md 节 1 业务背景**：引用 "Prism ADR-012" 作为双表设计依据，但 prism-0420 是独立 fork 项目，应引用 prism-0420 自己的 ADR 或在本模块设计中显式 accept/supersede Prism ADR-012——直接引用原 Prism ADR 是设计文档依赖外部项目决策的不合规行为（规约 11.5 ADR 不变性边界）。

- **M07/00-design.md 节 4 状态机**：状态机图在"合法转换表"中列出 `in_progress → open`（重新打开）的副作用是"清空 assigned_to（可选）"。"可选"是模糊描述——Service 实现时到底清还是不清？这是未决策的实现细节，必须在设计文档中明确，否则 AI 实现时会随机选择。

- **M07/00-design.md 节 5（4 维必答）**：并发标注 ❌，理由是"issue 是单一责任人顺序操作"。但 M07 新增了 `assigned_to` 字段（Prism 无）——如果支持多人操作（A 打开 in_progress，B 同时 resolve），并发控制的判断依据就变了。节 5 的判断建立在"假设无多人"的前提上，而这个前提本身是 Q4（assigned_to 是否加）的待裁决结果，形成循环依赖。

- **M07/00-design.md 节 7**：`IssueUpdate` schema 里 `node_id` 字段允许修改（重新挂节点），但节 15 checklist 没有列"node_id 可否修改决策"为必选裁决项。这个隐含决策被 AI 默认选 A（允许），但没有提交给 CY 裁决。

- **M07/tests.md**：测试文件没有 section 7（节 7），比 M04 少一个"状态机专项测试"分类——实际 M07/tests.md 确实有 SM1-SM4 但放在了节 7，这点是 OK 的；但 tests.md 没有节 9 关联项中提到的 `activity_log 粒度覆盖测试`（只有 G1-G8 里包含 activity_log 断言，没有专门针对 activity_log 格式的验证用例）。

### M14 行业动态

- **M14/00-design.md 节 0 快速索引**：引用 "05-module-catalog.md Q3.1"，但 05-module-catalog.md 里无 Q3.1 小节（只有表格中的 4 维标注），这是无效引用。M14 是全局豁免的核心依据应引用 06-design-principles 清单 5 豁免条件，已在节 9 做到了，但节 0 的引用路径错误。

- **M14/00-design.md 节 3 数据模型**：`tags` 字段使用 `string[]`（PG text[]），但工程规约 3（Python 代码风格）和原则 1（SQLAlchemy 唯一真相源）要求 model 定义在 SQLAlchemy；ER 图里 `string[] tags` 的标注是 ERD 层的，但节 3 没有提供 SQLAlchemy model 代码（其他模块 M05/M06/M07 都提供了 SQLAlchemy class 定义），M14 只有 ER 图没有 model 代码——缺失。

- **M14/00-design.md 节 5 约束清单 4（idempotency_key）**：答案是 ❌ 不触发，直接标注 N/A，但节 11 才是 idempotency 专项说明节——节 5 的 ❌ 和节 11 的完整分析不一致（节 5 写 N/A，节 11 写了理由）。M05/M06 是"⚠️ 待裁决"，M14 直接 ❌——但清单 4 要求"显式声明"，M14 在节 5 省略了理由，与 M04 pilot 格式不一致。

- **M14/00-design.md 节 8**：写权限设计"已登录即可写"（候选 A），但 `Depends(require_editor)` 被提到用于写接口——Router 层用 `require_editor` 而 Service 层说"已登录即可"，两层权限规则矛盾，AI 没有统一。最终应在 CY 裁决 Q5 后统一，但两处矛盾没有被标注联动。

- **M14/tests.md 节 4 T4**：关联 node 跨项目的期望行为仍是"⚠️ 待 CY 裁决"——测试场景里有未决策项，同 M06 tests.md E7 问题相同，不应出现在测试文件中。

### M19 导入/导出

- **M19/00-design.md 节 0 快速索引**：PRD 关联写 "F19（v0.3 AI 增强）"，但 PRD 01-PRD.md 没有 F19 的详细描述，"v0.3 AI 增强"是 Prism 内部版本号，不是 prism-0420 的 PRD 节。引用格式不规范。

- **M19/00-design.md 节 6 分层职责表**：DAO 层写"`api/dao/export_dao.py`（或复用各模块 DAO）"——两种策略并存且有"⚠️ 待 CY 裁决"，导致分层职责表的文件路径不确定。M04 pilot 要求分层职责表"每层文件路径明确"，M19 在此节不达标。

- **M19/00-design.md 节 9 DAO tenant 过滤**：代码示例写的是 `export_dao.py` 的独立 DAO 方法，但 Q4 推荐复用各模块 DAO（候选 A）。代码示例和推荐策略不一致——如果选 A，节 9 代码应是 `DimensionDAO.get_by_node_ids()` 的调用，而不是新的 `export_dao` 方法。

- **M19/00-design.md 节 10 activity_log**：`target_type` 写的是 `project`，`target_id` 是 `project_id`。但 activity_log 的清单 1 规范（06-design-principles）要求记录"谁在什么时候改了**什么**"，导出操作的目标应是 node 集合而不是 project——使用 `project` 作为 target_type 会让 M15 数据流转无法精确定位导出了哪个具体实体。

- **M19/tests.md 节 2 E4**：全部 node 无内容时的期望行为仍是"⚠️ 待 CY 裁决"——同 M06/M14 测试文件的未决策问题。

---

## 第二轮：边界场景

### M05 is_current 切换并发安全

- **M05/00-design.md 节 3 + 节 9**：`is_current` 切换通过 `clear_current_flag`（先清）+ set is_current=true（后设）两步实现。节 3 说"同一事务内"，但节 9 代码 `clear_current_flag` 是独立方法，没有事务包裹代码。如果 Service 层调用时没有显式 `with db.begin():`，两步操作之间存在并发窗口：用户 A 清空了 is_current，用户 B 也清空了，然后 A、B 都把自己的版本设为 current，结果是两条 is_current=true，违反"同一 node 唯一约束"。设计未提供 DB 级唯一约束（如 `UNIQUE(node_id) WHERE is_current=true` 部分唯一索引），只靠 Service 层逻辑防护。**这是真实的并发 bug 风险**，M05 的并发 ❌ 标注掩盖了这个问题。

- **M05/tests.md 节 3**：并发场景只有两行说明"无并发"，但上述 is_current 切换存在竞态——测试完全没有覆盖"两个用户同时 set-current"的场景。即使不加乐观锁，也应有一条"两个请求同时 set-current 不得产生两条 is_current=true"的防御测试。

- **M05/00-design.md 节 1 Out of scope**：版本回滚写"属于 M05 能力——M04 回滚触发时通知 M04 覆写"（在 Out of scope 说明里），但 In scope 没有提"回滚"，边界说明自相矛盾（Out of scope 列的是"版本回滚（将 snapshot_data 写回维度记录）：属于 M05 能力——M04 回滚触发时通知 M04 覆写"）。实际应是：回滚属于 M04 还是 M05？设计文档把回滚同时放在 M04 Out of scope 和 M05 Out of scope，双方都不认领。

### M06 双表事务边界

- **M06/00-design.md 节 5 + Q4**：Q4 说"新建竞品 + 同时创建对标"推荐包事务（候选 B），但节 5 事务答案是 ❌。如果 CY 选 B，竞品创建成功但对标插入失败时，竞品是否孤立？节 5 的"不需要"和 Q4 的"推荐包事务"是矛盾的，且两处没有互相引用。AI 生成时在节 5 先写了 ❌，在 Q4 又改了口，造成内部逻辑不一致。

- **M06/00-design.md 节 7**：`DELETE /competitors/{competitor_id}` 注释"级联删所有对标记录"，这是 DB 级 CASCADE 操作。但如果 activity_log 需要记录"删除竞品时同时删除了 N 条对标记录"（节 10 `delete competitor` 的 metadata 里有 `ref_count`），Service 层需要先查 ref_count，再执行删除。如果删除是 DB CASCADE，Service 层查 ref_count 后执行 DELETE 时 CASCADE 会自动删 refs，但 activity_log 对 refs 的 delete 事件（节 10 有 `delete competitor_ref` 事件类型）就不会触发——因为 refs 是 DB 自动删的，不是 Service 层显式调用删除方法。这是一个典型的"级联删除绕过 Service 层 activity_log"问题，设计未解决。

- **M06/tests.md 节 3**：无并发场景，但有一个遗漏：如果两个用户同时创建同一 (node_id, competitor_id) 的 competitor_ref，DB 唯一约束会兜底，但哪一个请求收到 409？测试应验证"并发重复关联返回 409 给其中一个，另一个 201"（类似 M14 C2），但 M06 完全没有并发测试。

- **M06/tests.md 节 4**：T2 期望是 `403 PERMISSION_DENIED`，但 M06/00-design.md 节 8 Service 层说"不属于抛 NotFoundError（不暴露 forbidden 信息）"，T2 的期望值与设计不一致。

### M07 状态机并发 + 回滚

- **M07/00-design.md 节 4 状态机**：非法转换由 Service 层拦截，但 Service 层的状态检查是"先读当前状态，再判断是否合法，再写新状态"——三步操作没有乐观锁或 FOR UPDATE。如果两个请求并发提交同一 issue 的 transition（e.g., A 把 open→in_progress，B 把 open→closed），两者都读到 status=open，都通过合法性校验，都写入——最终状态取决于写入顺序，可能产生不一致。M07 的并发 ❌ 是错误的：有状态机的实体在状态转换时存在隐性并发风险。

- **M07/00-design.md 节 5**：activity_log 写入在"无事务"模式（节 5 多表事务 ❌），但状态转换（PUT issues + 写 activity_log）应该是原子的——如果 issues 状态更新成功但 activity_log 写入失败，审计记录就丢失了。M04 pilot 中事务包裹了 upsert + activity_log，M07 没有这样处理，是降级了。

- **M07/tests.md 节 7 SM2**：`resolved → open（问题复现）`，期望是"resolved_at 清空"。但 M07/00-design.md 节 4 合法转换表没有明确说 `resolved → open` 时清空 `resolved_at`（只在 `in_progress → open` 的 row 说"清空 assigned_to（可选）"）。测试和设计对 `resolved_at` 清空的触发条件不一致。

- **M07/00-design.md 节 9 DAO**：有 `list_by_project` 支持 `tag: str | None = None` 过滤，但 Pydantic schema `IssueListQueryParams` 的 tag 过滤写的是"按 tag 筛选"，DAO 里没有 tag 的 JSONB 查询实现示例（其他字段有，tag 没有）。JSONB 数组的包含查询（`@>`）语法和 SQLAlchemy 写法是非标准的，设计文档应示例，否则 AI 实现时可能写错。

### M14 全局豁免 SQL 安全

- **M14/00-design.md 节 8 + 节 9**：DAO 全局豁免，任何已登录用户可读所有动态。但节 2 说 M14 不依赖 M02（无项目上下文），则 Router 层只有 `Depends(get_current_user)`，没有项目级权限检查。这意味着一个刚注册、未加入任何项目的用户也能读取所有行业动态（节 8 候选 A 说"全局可见"——设计是这样的），但没有讨论恶意用户通过大量请求抓取全量动态的限流防护（无 rate limit 设计）。`RATE_LIMITED` ErrorCode 在 规约 7 存在，但 M14 设计没有引用。

- **M14/tests.md 节 4 T4**：关联 node 时是否校验 node 归属（跨项目 node 关联）是 ⚠️ 未裁决。但这是安全相关的边界决策——允许关联跨项目 node 意味着用户可以通过动态关联功能枚举其他项目的 node_id 是否存在（信息泄露）。设计文档没有分析这个安全隐患。

- **M14/00-design.md 节 10 activity_log**：写入模式是"非事务——activity_log 写失败不回滚主操作"。M04 pilot 是事务内写，M14 降级为非事务，理由没有说明。全项目 activity_log 写入策略应一致（否则 M15 数据流转无法保证完整性），但不同模块的策略选择需要显式 ADR 或设计决策支撑。

### M19 跨模块只读聚合

- **M19/00-design.md 节 6 + 节 9**：如果 Q4 选候选 A（复用各模块 DAO），Export Service 会 import DimensionDAO / VersionDAO / CompetitorDAO / IssueDAO，但这四个 DAO 属于不同模块（分层规约 5.3 要求模块 DAO 不能跨层被随意 import）。设计没有讨论模块间 DAO 复用的分层合规性——在 import 路径规则下，export_service 直接 import dimension_dao 是否会触发 lint 规则违反？

- **M19/00-design.md 节 7 API**：只有一个 POST endpoint，没有设计响应格式的错误路径——如果 StreamingResponse 在传输一半时遇到 DB 错误，HTTP 状态码已经返回 200，客户端拿到的是截断的 Markdown 文件。设计未说明如何处理"流式传输中途失败"的情况（即使 M19 目前不是真正流式，大文件 StreamingResponse 也有同样问题）。

- **M19/00-design.md 节 1 灰区 1 + 节 7**：node_ids 上限推荐 20，但设计没有说明单个 node 的内容量上限。一个有 100 条竞品参考 + 50 条 issue 的大节点，生成的 Markdown 可能远超预期；20 个这样的节点会超时。设计缺少对单 node 内容量的约束（如"竞品参考最多展示 N 条"）。

- **M19/tests.md 节 3 C2**：测试"导出与 M04 编辑并发"期望是"读到编辑前或编辑后的快照（均 200，不报错）"。这是正确的最终行为期望，但测试没有说明如何验证"不死锁"——即如何断言 PG 没有产生 lock wait timeout。缺少具体验证手段。

---

## 第三轮：演进 + 模板可复用性

### 半年后扩展能力评估

**M05**：`is_current` 布尔标记在当前单用户场景下够用，但多人协作时需要"谁设置的 current"可追溯。`version_records` 没有 `marked_current_by` / `marked_current_at` 字段，半年后如果有多人协作，`set_current` 的审计只能靠 activity_log，不够直接。

**M06**：`competitors` 全局于 project，但没有 `space_id` 预留（ADR-001 明确不引入空间但预留 `space_id`）。M04/M05 的模型也没有 `space_id`，但 `base.py` 的 Base 类预留了 `space_id: int | None`。M06 的 `Competitor` 和 `CompetitorRef` 没有继承 base.py（设计文档没有提及是否使用公共 Base），意味着迁移到多空间时，M06 是否支持"空间级竞品共享"是未决策的架构扩展点。

**M07**：状态机 `closed → 不可重开` 的设计在单用户场景下合理，但多人协作时 PM 可能需要重开已关闭问题。`closed` 成为终态的决策是 AI 推断（"关闭后不可重开，需重新创建 issue"），且 PRD 没有这一要求。这个决策半年后可能需要 supersede，但目前没有 ADR 记录，会造成"为什么 closed 不能重开"的信息流失。

**M14**：全局数据模型半年后扩展到多空间时面临架构冲突——`industry_news` 无 project_id 也无 space_id，若要引入"按空间过滤动态"需要全表 schema 变更 + 数据迁移，影响面大。`source_type` 字段预留是好的，但 `space_id` 扩展口完全没有考虑。

**M19**：同步 StreamingResponse 在项目规模增长后（单 node 大量数据）会超时，且没有 fallback 到异步 Queue 的设计路径。将来升级为异步时，API 合约（POST 立即返回文件 vs POST 返回 task_id 轮询）需要完全改变——没有版本化 API 的预留设计。

### 与 M04 pilot 模板的差异问题

1. **SQLAlchemy model 代码**：M04 / M05 / M06 / M07 提供了完整的 model class；**M14 缺失**（只有 ER 图，无 SQLAlchemy class），违反"原则 1 SQLAlchemy 是 schema 唯一真相源"，M14 节 3 在设计文档层面就打破了这个原则。

2. **节 15 reviewer audit 勾选**：M04 有三轮 🔴 强制 reviewer audit 勾选项；M05/M06/M07 均无，M14/M19 也无——批量生成时 AI 漏加了这三项，导致 checklist 准入门槛降低。

3. **frontmatter 字段不一致**：`pilot: false` 字段仅在 M14 / M19 出现，M05 / M06 / M07 没有。规约 11.3 要求全字段一致。M05 / M06 也没有"节 0 快速索引"（M14 / M19 有），模板结构在 5 个模块内已经出现分叉。

4. **⚠️ 标注管理问题**：M04 pilot 的 ⚠️ 都集中在"待 CY 裁决项汇总"（节 16），5 个批量模块的 ⚠️ 则分散在各节正文中，且有部分 ⚠️ 泄露到 tests.md（M06 E7、M14 T4、M19 E4），模板应要求"tests.md 里不允许出现待裁决 ⚠️"。

5. **节 4 无状态实体的声明格式**：M04 用完整段落 + 代码块声明"无状态实体"；M06 只有两行文字；M19 只有一句话。格式不统一影响后续自动扫描。

6. **节 0 快速索引**：M14 / M19 增加了节 0（frontmatter 快速索引表），M05 / M06 / M07 没有。节 0 是个有价值的添加，但应统一，或明确"低复杂度模块才加"。

---

## 总评

| 模块 | 评分(10) | vs M4 pilot | 关键缺口 |
|------|---------|------------|---------|
| M05 | 6.5 | 85% | is_current 并发窗口未解决；事务声明矛盾；版本回滚归属双方不认 |
| M06 | 6.0 | 80% | 事务 ❌ vs Q4 推荐事务矛盾；CASCADE 删除绕过 activity_log；tests.md 有 ⚠️ |
| M07 | 6.0 | 80% | 状态机并发未保护（无 FOR UPDATE）；引用外部 Prism ADR；assigned_to 并发分析缺失 |
| M14 | 5.5 | 70% | 无 SQLAlchemy model 代码；节 0 引用路径错误；权限规则两层矛盾；rate limit 缺失 |
| M19 | 6.5 | 82% | DAO 策略未定导致节 9 代码与推荐不符；StreamingResponse 中途失败未处理；模块 DAO 跨层 import 合规性未分析 |

---

## 模板调整建议（最重要）

1. **tests.md 禁止出现 ⚠️ 待裁决标注**：所有未决策项必须在 `00-design.md` 节 15 的"待 CY 裁决项汇总"中完成，tests.md 写完时默认所有决策已定。模板应在 tests.md 顶部加：`> 前置条件：本文件写完时，00-design.md 节 15 所有 ⚠️ 已裁决完毕。`

2. **节 3 SQLAlchemy model 代码为强制项**：模板节 3 必须包含完整的 SQLAlchemy class 定义（不接受只有 ER 图），与原则 1 对齐。对于纯只读模块（M19），节 3 需显式写"无主表，复用模型列表：[M03.nodes, M04.dimension_records, ...]"。

3. **节 15 reviewer audit 三轮勾选为必填**：恢复 M04 pilot 的三轮 🔴 强制勾选项，所有批量生成模块统一补充，不允许省略。这是 design-first 验证流程的核心控制点。

4. **frontmatter 全字段统一**：在模板 frontmatter 中明确所有 12 字段（含 `pilot: false`、`prism_ref`、`module_id`），批量生成时不允许字段缺失。可在 CI 或 doc-rot 扫描中加 frontmatter 字段完整性检查。

5. **有状态机实体的并发风险强制分析**：当节 4 有状态机时，节 5（4 维必答）的并发部分不能简单写 ❌；必须增加一行"状态转换是否存在并发竞态分析：是/否，理由：..."。M07 状态机 + 并发 ❌ 的组合是高风险漏洞点。

---

## 入场判断

- [ ] **这 5 个模块能转 accepted 吗？**
  - **不能**。所有模块均有未裁决的 ⚠️ 项（这是设计意图，需 CY 决策），但除此之外还有内部矛盾（M05 事务声明矛盾 / M06 4 维与 Q4 矛盾 / M07 引用外部 ADR / M14 缺 SQLAlchemy 代码 / M19 DAO 策略与代码示例不符）需要在 CY 裁决之前修正。
  
  **需补哪些 CY 决策（最小集）**：
  | 模块 | 关键裁决 | 影响 |
  |------|---------|------|
  | M05 | is_current 切换是否加 DB 级部分唯一索引 `WHERE is_current=true` | 并发安全 |
  | M06 | Q4：事务 ❌ 还是 ✅（新建竞品+对标是否原子）| 4 维和节 5 联动 |
  | M06 | 级联删竞品时对标 activity_log 如何处理（DB CASCADE vs Service 显式删）| 审计完整性 |
  | M07 | 状态转换 SQL 是否加 FOR UPDATE 或乐观锁 | 并发安全 |
  | M07 | assigned_to 保留与否 + 其对并发判断的影响 | 4 维重新确认 |
  | M14 | 补充 SQLAlchemy model 代码（强制） | 原则 1 合规 |
  | M19 | DAO 策略定稿（选 A 后节 9 代码需重写） | 分层合规 |

- [ ] **M4 pilot 模板需要修订吗？**
  - **需要**，修订项：
    1. tests.md 禁止 ⚠️ 标注（新增约束）
    2. 节 3 强制 SQLAlchemy model 代码（明确为必填）
    3. 节 15 reviewer audit 三轮勾选统一（恢复至批量模块）
    4. frontmatter 12 字段清单（补 `pilot: false`）
    5. 有状态机时节 5 并发维度强制增加竞态分析行
    6. 节 4 无状态实体声明格式统一（段落 + 显式声明，不接受单行）
