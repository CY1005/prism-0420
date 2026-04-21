---
title: 第一批 5 模块 fix v2 verify 报告
status: draft
owner: reviewer-agent
created: 2026-04-21
batch: 1
verify_round: 3
modules: [M05, M06, M07, M14, M19]
---

# 第一批 5 模块 fix v2 verify 报告

> **审稿立场**：独立、不附和 fix Agent 自报告、每条必须有文件路径+节号引用。
> **参照基线**：M04 pilot（`M04-feature-archive/00-design.md`）+ README.md 模板规则 + audit-report-batch1.md 42 条问题。

---

## 第一层：决策落地验证

### 决策 1（tenant 冗余 project_id）

- **M5**: ✅ — `M05-version-timeline/00-design.md` 节 3 SQLAlchemy class `VersionRecord` 第 121 行含 `project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)  # 冗余 tenant 字段`。节 3 首段决策标题也明确 "CY 2026-04-21 ack 批量统一冗余"。
- **M6**: ✅ — `M06-competitor/00-design.md` 节 3 两个 class 均有 project_id：`Competitor` 第 108 行含 project_id；`CompetitorRef` 第 130 行含 project_id（标注"冗余 tenant 字段"）。节 3 决策标题含 `CY 2026-04-21 ack`。
- **M7**: ✅ — `M07-issue/00-design.md` 节 3 `Issue` class 第 125 行含 `project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)  # 冗余 tenant 字段`。
- **M14**: ✅ — `M14-industry-news/00-design.md` 节 3 SQLAlchemy class `IndustryNews` 注释第 153-154 行明确 `# 注意：M14 全局数据，无 project_id 约束`，无 project_id 字段。节 1 灰区 2 决策明确"全局无项目隔离"，符合"全局表无 project_id"设计。
- **M19**: ✅ — `M19-import-export/00-design.md` 节 3 明确"M19 无主表（决策：不记录导出历史，CY 2026-04-21 ack）"，节 9 说明"DAO 复用各模块"，代码注释说明复用上游 DAO。

**决策 1 总评**：5/5 ✅ 落地完整。

---

### 决策 2（idempotency 全无）

- **M5 节 11**: ✅ — `M05-version-timeline/00-design.md` 节 11 标题"决策：本模块无 idempotency 需求（CY 2026-04-21 ack 全模块统一）"，显式声明"M05 无 idempotency_key 操作"。
- **M5 节 5 清单 4**: ✅ — 节 5 约束清单第 4 项标 `❌ 不触发（CY ack 无幂等需求）`。
- **M6 节 11**: ✅ — 节 11 标题"决策：本模块无 idempotency 需求（CY 2026-04-21 ack 全模块统一）"，显式声明"M06 无 idempotency_key 操作"。
- **M6 节 5 清单 4**: ✅ — 约束清单第 4 项标 `❌ 不触发（CY ack 无幂等需求）`。
- **M7 节 11**: ✅ — 节 11 标题同格式，含 CY ack，显式声明"M07 无 idempotency_key 操作"。
- **M7 节 5 清单 4**: ✅ — 约束清单第 4 项标 `❌ 不触发（CY ack 无幂等需求）`。
- **M14 节 11**: ✅ — 节 11 标题同格式，含 CY ack，显式声明"M14 无 idempotency_key 操作"。
- **M14 节 5 清单 4**: ✅ — 约束清单第 4 项标 `❌ 不触发（CY ack 无幂等需求，见节 11）`。
- **M19 节 11**: ✅ — 节 11 标题同格式，含 CY ack，显式声明"M19 无 idempotency_key 操作"。
- **M19 节 5 清单 4**: ✅ — 约束清单第 4 项标 `❌ 不触发（见节 11）`。

**决策 2 总评**：5/5 ✅ 落地完整，所有模块节 11 + 节 5 清单 4 一致对齐。

---

### 决策 3（状态字段最小集）

- **M5 节 4**: ✅ — `M05-version-timeline/00-design.md` 节 4 标题"决策：仅 `is_current` 布尔，无 `status` 字段（CY 2026-04-21 ack 统一最小集）"，并显式声明"M05 无 status 枚举实体"。
- **M6 节 4**: ✅ — `M06-competitor/00-design.md` 节 4 标题"决策：M06 无状态字段（CY 2026-04-21 ack 统一最小集）"，显式声明"M06 无状态实体"。
- **M7 节 4**: ✅ — `M07-issue/00-design.md` 节 4 标题"决策：保留 4 状态机（CY 2026-04-21 ack）"，有 mermaid stateDiagram-v2 图（open/in_progress/resolved/closed 四态），有允许转换表（4 行）和禁止转换表（2 行，`open → closed` 和 `closed → 任何状态`）。
- **M14 节 4**: ✅ — `M14-industry-news/00-design.md` 节 4 标题"决策：M14 无状态字段（CY 2026-04-21 ack 统一最小集）"，显式声明"M14 无状态实体"。
- **M19 节 4**: ✅ — `M19-import-export/00-design.md` 节 4 显式声明"M19 无状态实体"。

**决策 3 总评**：5/5 ✅ 落地完整。M7 4 状态机完整，mermaid 图 + 允许/禁止转换表均已落地。

---

### 决策 4（activity_log 操作 + metadata）

- **M5 节 10**: ✅ — `M05-version-timeline/00-design.md` 节 10 标题"决策：操作粒度 + metadata（CY 2026-04-21 ack 全模块统一）"，事件清单含 action_type / target_type / target_id / summary / metadata 五列，4 种事件（create / update / delete / set_current）。
- **M6 节 10**: ✅ — `M06-competitor/00-design.md` 节 10 同格式，6 种事件，五列完整。
- **M7 节 10**: ✅ — `M07-issue/00-design.md` 节 10 同格式，4 种事件（create / update / status_change / delete），五列完整，含 CY ack。
- **M14 节 10**: ✅ — `M14-industry-news/00-design.md` 节 10 同格式，5 种事件（create / update / delete / link / unlink），五列完整，含 CY ack。
- **M19 节 10**: ✅ — `M19-import-export/00-design.md` 节 10 同格式，含 CY ack，含 target_type=node 的说明。

**决策 4 总评**：5/5 ✅ 落地完整，全部模块节 10 含五列事件清单表 + CY ack。

---

### 决策 5（M7 状态转换细化）

- **M7 `assigned_to` 字段**: ✅ — `M07-issue/00-design.md` 节 3 SQLAlchemy class 第 133 行含 `assigned_to: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 责任人；状态转 in_progress 时必填`。
- **M7 节 5 状态转换竞态分析表**: ✅ — 节 5 含"状态转换竞态分析（节 4 有状态时强制）"表，共 6 行（含 2 行禁止转换 N/A 说明），满足 5+ 行要求。该表替代了原 audit 报告所批评的 ⚠️ 占位。
- **M7 节 4 禁止转换**: ✅ — 节 4 禁止转换表明确列出 `open → closed（禁）` 和 `closed → 任何状态（禁）`，符合决策 5 要求。
- **M7 `assigned_to` 必填约束位置**: ⚠️ **新问题** — 节 4 的允许转换表写"状态变 `in_progress` 时必填（Service 层校验）"，节 5 竞态分析表写 "open → in_progress DB UNIQUE 防重"（`DB 唯一约束 (issue_id)（一个 issue 单 assignee）`）。但 SQLAlchemy class 中 `assigned_to` 是 `nullable=True`，没有 DB 级 CHECK 约束强制"in_progress 时 assigned_to 不能为 NULL"。DB 层实际无法直接加 CHECK `(status != 'in_progress' OR assigned_to IS NOT NULL)`（SQLAlchemy 定义中未见该约束），只靠 Service 层软强制。节 5 竞态分析说 "DB UNIQUE 防重" 但实际 issues 表上并无 UNIQUE(assigned_to, issue_id) 这样的约束——这是**误导性描述**。

**决策 5 总评**：主体落地 ✅，但 `assigned_to` 约束层级说明存在误导性描述（节 5 竞态分析表行 1 写 "DB 唯一约束 (issue_id)" 无实际对应 SQLAlchemy 代码）。

---

### 决策 6（M14 仅手动）

- **M14 节 3 `source_type` 字段**: ✅ — `M14-industry-news/00-design.md` 节 3 SQLAlchemy class 含 `source_type: Mapped[str] = mapped_column(Text, nullable=False, default="manual")`，`__table_args__` 含 `CheckConstraint("source_type = 'manual'", name="ck_industry_news_source_type_manual")`。
- **M14 节 1 业务说明**: ✅ — 节 1 灰区 1 明确"决策：本期仅手动录入（CY 2026-04-21 ack）"，说明 `rss/ai` 枚举预留，本期 service 层拒绝非 manual 记录。

**决策 6 总评**：2/2 ✅ 落地完整。

---

### 决策 7（M19 AB 共存）

- **M19 节 7 两个 endpoint**: ✅ — `M19-import-export/00-design.md` 节 7 Endpoints 表有两行：`POST /api/projects/{project_id}/exports`（入口 A）和 `POST /api/projects/{project_id}/nodes/{node_id}/export`（入口 B）。
- **M19 Pydantic schema**: ✅ — 节 7 含 `MultiNodeExportRequest`、`SingleNodeExportRequest`、`ExportIncludeOptions` 三个 Pydantic class，均有完整字段定义。
- **ExportService 共享逻辑**: ✅ — 节 7 ExportService 接口说明"两入口（A/B）共享此方法"，节 9 代码示例显示 `_fetch_node_data` 方法被两入口复用。
- **节 1 业务说明覆盖两入口场景**: ✅ — 节 1 In scope 明确分别说明"入口 A（多 node 选择）"场景（评审/汇报）和"入口 B（单 node）"场景（单点交付/写在 PR 里）。

**决策 7 总评**：4/4 ✅ 落地完整。

---

### 决策 8（reviewer 内部矛盾修复）

- **M5 节 5 多表事务声明一致性**: ✅（部分）— `M05-version-timeline/00-design.md` 节 5 多表事务答案改为"❌ 主流程同步无多表事务；`is_current` 切换走单表 UPDATE 原子（同一表不同行的 set true/false）+ 事务包裹保证原子"，节 9 Service 层代码示例也有 `with db.begin():` 事务包裹。节 5 与节 9 已一致。节 5 实现细节列："Service 层 `with db.begin():` 包裹两次 UPDATE（同表），非跨表事务"。
- **M5 节 9 activity_log 事务外写入**: ❌ **未修复问题** — 节 9 `set_current` Service 代码中，`self.activity.log(...)` 在 `with db.begin():` 块**之外**（见节 9 代码第 360-362 行，`# DB 部分唯一索引...在 commit 时兜底` 后跟 `self.activity.log(...)`）。这意味着 is_current 切换成功但 activity_log 写入失败时，审计记录会丢失。M04 pilot 是事务内写 activity_log，M05 降级了，且与 audit-report-batch1 第二轮问题中"M07/00-design.md 节 5：activity_log 写入在无事务模式"批评一致但 M05 未同步修。
- **M6 节 5 多表事务**: ✅ — `M06-competitor/00-design.md` 节 5 多表事务答案已改为"✅ 创建竞品+引用走多表事务（competitors + competitor_refs 同一事务包裹）"，与 Q4 决策（选 B Service 层包事务）已对齐，内部矛盾已修。
- **M19 tests E2 对齐**: ✅（部分）— `M19-import-export/tests.md` E4 原 audit 报告说有 ⚠️ 待裁决，现 E4 已改为"200 + Markdown 含章节标题但各区块均显示"（暂无内容）"（不报 422，导出空报告仍成功）"，无 ⚠️，决策已定。E2（node_ids 为空）也已明确为 422 VALIDATION_ERROR。tests.md 整体无 ⚠️ 符合模板规则。

**决策 8 总评**：M6 节 5 矛盾已修 ✅；M19 tests 无 ⚠️ ✅；M5 activity_log 事务外写入**未修复** ❌（新发现，原 audit 对 M05 的批评集中在事务声明矛盾，fix v2 修了声明但 activity_log 在事务外这个子问题仍存在）。

---

## 第二层：新问题独立寻找

### NI-1：M19 入口 B 省略 project_id 的隐患

**位置**：`M19-import-export/00-design.md` 节 7，入口 B endpoint `POST /api/projects/{project_id}/nodes/{node_id}/export`

**问题**：入口 B URL 同时含 `project_id` 和 `node_id`。节 7 说"入口 B 等价于入口 A 传 `node_ids=[node_id]`（service 内部复用同一逻辑）"，`SingleNodeExportRequest` schema 中不含 `node_ids`（node_id 来自 URL path param），也不含 `project_id`（project_id 同样来自 URL path param）。

两个入口在业务上等价，但 `MultiNodeExportRequest` 需要 client 显式传 node_ids list，而 `SingleNodeExportRequest` 的 node_id 来自 URL——这实际上没有差异，**但 tests.md G6 测试"入口 B 等价入口 A 单 node"只断言"两者返回相同 Markdown 内容"**，没有验证 project_id 校验路径是否完全一致（入口 B 的 project_id 来自 URL，不在 request body 里；入口 A 的 node_ids 包含的节点需要和 URL project_id 做匹配）。这本身设计合理，但 **G6 测试没有区分两入口的 tenant 校验代码路径**，导致潜在差异无覆盖。

**风险级别**：低（设计合理，测试覆盖不充分）

---

### NI-2：M7 `assigned_to` 约束只靠 Service 层但竞态分析说"DB 唯一约束"

**位置**：`M07-issue/00-design.md` 节 5 竞态分析表，第一行"open → in_progress | ❌ 无（assigned_to 字段记录单 user 认领，DB UNIQUE 防重）| DB 唯一约束 (issue_id)（一个 issue 单 assignee）"

**问题**：SQLAlchemy model（节 3）中 `issues` 表 `__table_args__` 只有：`CheckConstraint (status IN ...)`, `CheckConstraint (category IN ...)` 和若干 `Index`。**没有** `UniqueConstraint("id", ...)` 或 `UniqueConstraint("assigned_to")` 来保证"一个 issue 单 assignee"。"DB 唯一约束 (issue_id)" 的描述是虚假描述——`id` 是 PK 本来就唯一，和"单 assignee"防重毫无关系。

实际防护：Service 层在 `open → in_progress` 时要求 `assigned_to` 非空，这是一个**单步校验**，不是并发防护。两个请求若同时提交 `open → in_progress`（A、B 各传不同的 `assigned_to`），都读到 `status=open`，都通过 Service 层 `assigned_to` 非空校验，都写 `status=in_progress` + 各自的 `assigned_to`——最终结果取决于写入顺序，无 DB 级唯一约束防护。这与 audit-report-batch1 第二轮批评的原始并发问题完全相同，**fix v2 给的竞态分析表是虚假的**（引用了不存在的 DB 约束来自圆）。

**风险级别**：中（设计文档声称 DB 防护实际不存在；并发窗口虽然小但理论上可触发双 in_progress）

---

### NI-3：M5 activity_log 在事务外写入

**位置**：`M05-version-timeline/00-design.md` 节 9 Service 层 `set_current` 代码块

```python
def set_current(...):
    with db.begin():                                          # ← 事务包裹
        self.version_dao.clear_current_flag(...)
        record = self.version_dao.get_one(...)
        if not record:
            raise VersionNotFoundError()
        record.is_current = True
    # DB 部分唯一索引 UNIQUE(node_id) WHERE is_current=true 在 commit 时兜底
    self.activity.log(...)    # ← 在事务 commit 之后写！
    return record
```

**问题**：`self.activity.log(...)` 在 `with db.begin():` 块外部调用，即在 is_current 切换提交之后才写 activity_log。若 activity_log 写入失败（DB 抖动 / activity_logs 表不可用），is_current 已提交无法回滚，但审计记录丢失。M04 pilot（`M04-feature-archive/00-design.md` 节 5）的事务模式是"Service 层 `with self.db.transaction():` 包：① upsert dimension_records ② log activity_log；任一失败回滚"，M05 没有遵循此模式。

audit-report-batch1 在 M07 章节批评了"activity_log 写入在无事务模式"，fix v2 在 M07 中将节 5 多表事务答案改为"❌ 不需要"并在说明里写"状态转换（UPDATE issues + 写 activity_log）在 Service 层同方法内调用，遵循 M04 pilot 事务模式（Service 层包裹）"——但 M07 节 5 仍是"❌ 不需要"而不是 ✅，实际是否加了事务还需看 M07 节 9（DAO 层没有事务代码）。M05 的问题比 M07 更明显（代码直接可见）。

**风险级别**：中（审计丢失不影响业务，但违反 M04 pilot 事务约定的一致性）

---

### NI-4：M14 `source_type` CHECK 约束未来 migration 成本未分析

**位置**：`M14-industry-news/00-design.md` 节 3，`CheckConstraint("source_type = 'manual'", name="ck_industry_news_source_type_manual")`

**问题**：当前 CHECK 约束是等值约束 `source_type = 'manual'`，而不是枚举 `source_type IN ('manual', 'rss', 'ai')`。这意味着：
1. 现在：插入 `source_type='rss'` 会因为 CHECK 约束失败（正确行为）
2. 未来扩展 rss/ai：必须 DROP + ADD 约束（Alembic migration），还需要 lock table（PG 的 `ALTER TABLE` ADD CONSTRAINT 需要 AccessShareLock 但 DROP CONSTRAINT 需要 AccessExclusiveLock）
3. audit-report-batch1 第三轮提到了这个扩展隐患，但 fix v2 节 3 的注释只写了"后期扩展 rss/ai 时修改此 CHECK 约束"，没有分析 migration 成本/锁策略

这本身不是 blocker（设计决策已定），但 fix v2 自报告"无新问题"而实际上这个 migration 路径风险仍未分析。

**风险级别**：低（not a blocker，但技术债无文档）

---

### NI-5：M7 节 5 多表事务说明含糊

**位置**：`M07-issue/00-design.md` 节 5 多表事务答案

原文："❌ 不需要 | issue CRUD 只涉及 issues 单表；activity_log 写入在同 Service 方法内；状态转换（UPDATE issues + 写 activity_log）在 Service 层同方法内调用，遵循 M04 pilot 事务模式（Service 层包裹）"

**问题**：答案是 ❌（不需要），但说明文字说"遵循 M04 pilot 事务模式（Service 层包裹）"——如果真的遵循 M04 pilot 事务模式，那就是 ✅ 需要（M04 pilot 节 5 多表事务是 ✅）。这是一个自相矛盾的描述：答案说不需要，理由说遵循了需要的模式。实际从 M07 节 9 DAO 代码和整体设计看，没有显式事务包裹 `with db.begin():`，只有 Service 方法内的顺序调用。

这与 audit-report-batch1 批评"M07 节 5 多表事务 ❌ 与 activity_log 原子性问题"未完全对齐，fix v2 修改了说明文字但引入了新的自相矛盾。

**风险级别**：中（设计文档含糊；AI 实现时可能随机选择是否加事务）

---

### NI-6：M05 部分唯一索引声明与 Alembic 要点不一致

**位置**：`M05-version-timeline/00-design.md` 节 3 `__table_args__` vs Alembic 要点

SQLAlchemy class `__table_args__` 内已有 `Index("ix_version_is_current", "node_id", postgresql_where="is_current = true")`（这是普通索引，不是唯一约束）。

Alembic 要点段落写"防并发窗口：PG 部分唯一索引 `UNIQUE (node_id) WHERE is_current = true` 在 DB 层保证同一 node 最多 1 条 is_current=true（Alembic 迁移中加入）"。

**矛盾**：`__table_args__` 中用的是 `Index`（普通索引），Alembic 要点说的是 `UNIQUE`（唯一约束）。`Index` 不会强制唯一性，`UniqueConstraint` 才会。如果实现时按 SQLAlchemy class 来（只有 Index），并发防护失效；如果按 Alembic 要点来（UNIQUE），需要改 class 用 `UniqueConstraint(..., postgresql_where="is_current = true")`。这是**两处定义不一致的 bug**——SQLAlchemy 是 schema 唯一真相源（原则 1），那 class 里的 Index 才是事实，DB 级唯一约束实际上**没有落地**。

**风险级别**：高（这是 audit-report-batch1 第一批发现的核心并发安全问题，fix v2 在 Alembic 要点文字上描述了防护，但 SQLAlchemy class 代码未同步用 UniqueConstraint，按原则 1 class 是 schema 真相源，该防护实际无效）

---

### NI-7：M6 tests.md E7 原 ⚠️ 已去除但决策细节需确认

**位置**：`M06-competitor/tests.md` E7

原 audit-report-batch1 批评 E7 是"⚠️ 待裁决"。现 E7 已改为："204 + 级联删所有关联对标记录；activity_log 先写各 ref 的 `delete competitor_ref`，再写 `delete competitor`（含 ref_count）"。

这符合 M06 节 3 Alembic 要点的说明（"Service 层在 CASCADE 前显式批量记录"）。⚠️ 已去除 ✅，不是新问题。

---

### NI-8：M14 节 10 activity_log 写入模式与 M04 pilot 不一致但无 ADR

**位置**：`M14-industry-news/00-design.md` 节 10 末尾

"实现位置：Service 层每个 C/U/D 操作后调 `self.activity.log(...)`（非事务——M14 无多表事务，activity_log 写失败不回滚主操作）"

audit-report-batch1 第二轮批评了这个问题（"M04 pilot 是事务内写，M14 降级为非事务，理由没有说明。全项目 activity_log 写入策略应一致"）。fix v2 在括号里增加了"（非事务——M14 无多表事务，activity_log 写失败不回滚主操作）"的解释，但：
1. M04 pilot 的 activity_log 写入在事务内（节 5 明确 ✅ 多表事务）
2. M14 的 activity_log 写入在事务外，且未经 ADR 形式显式豁免
3. 这意味着"全项目 activity_log 一致性"问题没有通过 ADR 显式裁决，只是在各模块文档里自行选择

**风险级别**：低（设计意图清晰，但缺少横切 ADR）

---

### NI-9：M19 节 9 与 tests T3 的 DAO 方法名不一致

**位置**：`M19-import-export/00-design.md` 节 9 代码 vs `M19-import-export/tests.md` T3

节 9 代码示例：
```python
data["dimensions"] = self.dimension_dao.list_by_node(db, node_id=node_id, project_id=project_id)
```

tests.md T3：
```
单元测试：调 `DimensionDAO.list_by_node(node_id=projectB_node, project_id=projectA_id)` | 返回空 list
```

两者方法名一致（`list_by_node`）。✅ 这部分是对齐的。

但 audit-report-batch1 第一轮批评"节 9 代码示例写的是 `export_dao.py` 的独立 DAO 方法，但 Q4 推荐复用各模块 DAO，代码示例和推荐策略不一致"——fix v2 已将节 9 代码改为 `dimension_dao.list_by_node` 等复用各模块 DAO 的方式。**这条原始问题已修复**。

---

## 第三层：accept 准入判断

### 节 15 checklist + ⚠️ 状态 + 内部一致性

| 模块 | 节 15 checklist | tests.md ⚠️ 数 | design.md 剩余 ⚠️ | 内部一致 | 准入 |
|------|----------------|---------------|-------------------|---------|------|
| M05 | 15 项已勾 + 3 轮 🔴 强制已添加 | 0 | 1 处（节 9 activity_log 事务外写，描述隐性矛盾） | ❌ SQLAlchemy `Index` vs Alembic 要点 `UNIQUE` 不一致（NI-6） | ❌ 暂不准入 |
| M06 | 15 项已勾 + 3 轮 🔴 强制已添加 | 0 | 0 | ✅ | ✅ 准入（CY 复审后） |
| M07 | 15 项已勾 + 3 轮 🔴 强制已添加 | 0 | 1 处（节 5 多表事务 ❌ 但说明文字自相矛盾） | ❌ 节 5 多表事务答案与说明矛盾（NI-5）；竞态分析引用了不存在的 DB 约束（NI-2） | ❌ 暂不准入 |
| M14 | 15 项已勾 + 3 轮 🔴 强制已添加 | 0 | 0 | ✅ | ✅ 准入（CY 复审后） |
| M19 | 15 项已勾 + 3 轮 🔴 强制已添加 | 0 | 0 | ✅ | ✅ 准入（CY 复审后） |

### frontmatter 12 字段检查

| 模块 | pilot 字段 | 12 字段完整性 |
|------|-----------|-------------|
| M05 | ✅ `pilot: false` 已有 | ✅ 12 字段完整（title/status/owner/created/accepted/supersedes/superseded_by/last_reviewed_at/module_id/prism_ref/pilot/complexity） |
| M06 | ✅ `pilot: false` 已有 | ✅ 12 字段完整 |
| M07 | ✅ `pilot: false` 已有 | ✅ 12 字段完整 |
| M14 | ✅ `pilot: false` 已有 | ✅ 12 字段完整 |
| M19 | ✅ `pilot: false` 已有 | ✅ 12 字段完整 |

> 注：audit-report-batch1 批评 M05/M06/M07 缺 `pilot: false`，fix v2 已全部补齐。

### tests.md ⚠️ 检查

所有 5 个模块的 tests.md 均无 ⚠️ 标注。原 audit 批评的 M06 E7、M14 T4、M19 E4 三处 ⚠️ 均已去除，并给出了明确的期望行为。✅

### "待 CY 裁决项汇总" 表格格式检查

| 模块 | 末尾格式 |
|------|---------|
| M05 | 末尾有"CY 决策记录（2026-04-21 批量统一）"表，Q1-Q5，无"待 CY 裁决项汇总" ✅ |
| M06 | 末尾有"CY 决策记录（2026-04-21 批量统一）"表，Q1-Q4，无"待 CY 裁决项汇总" ✅ |
| M07 | 末尾有"CY 决策记录（2026-04-21 批量统一）"表，Q1-Q5，无"待 CY 裁决项汇总" ✅ |
| M14 | 末尾有"CY 决策记录（2026-04-21 批量统一）"表，Q1-Q6，无"待 CY 裁决项汇总" ✅ |
| M19 | 末尾有"CY 决策记录（2026-04-21 批量统一）"表，Q1-Q6，无"待 CY 裁决项汇总" ✅ |

所有模块均按 M04 pilot 范式改为"CY 决策记录"表。✅

---

## 总评

| 模块 | 评分 | vs fix v2 自报 | 关键风险 | 准入 |
|------|------|--------------|---------|------|
| M05 | 7.5/10 | 漏改——自报"0 ⚠️"但 SQLAlchemy Index vs UniqueConstraint 不一致是高风险漏洞，activity_log 事务外写入未修 | SQLAlchemy class 实际无 DB 级唯一约束（NI-6），并发防护声称存在但实际无效 | ❌ 暂不准入 |
| M06 | 9.0/10 | 真实——事务矛盾已修，tests.md ⚠️ 已清，两表 project_id 均已落地 | 无 blocker | ✅ 准入 |
| M07 | 7.0/10 | 漏改——竞态分析表引用了不存在的 DB 约束（NI-2），节 5 多表事务说明自相矛盾（NI-5） | assigned_to 约束声称 DB 级防护但 SQLAlchemy model 无对应约束 | ❌ 暂不准入 |
| M14 | 9.0/10 | 真实——SQLAlchemy model 已补全，frontmatter 完整，⚠️ 均清 | source_type CHECK 约束 migration 路径未分析（低风险，不 block） | ✅ 准入 |
| M19 | 9.0/10 | 真实——节 9 DAO 复用代码已对齐，⚠️ 已清，AB 两入口完整 | 入口 B tenant 校验代码路径测试覆盖不充分（低风险） | ✅ 准入 |

---

## 必修问题清单（block 准入）

### BLOCK-1（M05）：SQLAlchemy model 缺 UniqueConstraint 但 Alembic 要点声称有 UNIQUE

**文件**：`M05-version-timeline/00-design.md` 节 3

**位置**：
- `__table_args__` 内有 `Index("ix_version_is_current", "node_id", postgresql_where="is_current = true")`（普通索引，不强制唯一）
- Alembic 要点写"防并发窗口：PG 部分唯一索引 `UNIQUE (node_id) WHERE is_current = true`"（声称有唯一约束）

**修复方向**：按原则 1（SQLAlchemy 是 schema 唯一真相源），在 `__table_args__` 中将 `Index` 改为 `UniqueConstraint` + `postgresql_where` 条件，或显式加一条 `UniqueConstraint("node_id", name="uq_version_node_is_current", postgresql_where="is_current = true")`。Alembic 要点应与 class 保持同步。

---

### BLOCK-2（M05）：activity_log 写在 `with db.begin():` 外

**文件**：`M05-version-timeline/00-design.md` 节 9

**位置**：`set_current` Service 方法，`self.activity.log(...)` 在 `with db.begin():` 块之外（即事务提交后）

**修复方向**：将 `self.activity.log(...)` 移至 `with db.begin():` 内，或显式说明"M05 activity_log 采用非事务模式（与 M14 一致）——接受 activity_log 丢失风险"并在 CY 决策记录里记录。若继续保持在事务外，至少要保持设计文档内部一致（不能说"遵循 M04 pilot 事务模式"同时又不在事务内）。

---

### BLOCK-3（M07）：竞态分析表引用了不存在的 DB UniqueConstraint

**文件**：`M07-issue/00-design.md` 节 5 竞态分析表第一行

**位置**：`open → in_progress | ❌ 无（assigned_to 字段记录单 user 认领，DB UNIQUE 防重）| DB 唯一约束 (issue_id)（一个 issue 单 assignee）`

**实际情况**：SQLAlchemy class `Issue` 的 `__table_args__` 无任何 `UniqueConstraint`（只有 CheckConstraint 和 Index），`assigned_to` 是 nullable FK，issues.id 是 PK——`id` 本来就唯一，这和"单 assignee"完全无关。

**修复方向**：要么（a）在 `issues` 表加 `UniqueConstraint("id", "assigned_to", ...)` 并分析业务语义是否正确；要么（b）诚实地将竞态分析表改为"❌（无 DB 防护，仅靠 Service 层先读后写——存在极低概率并发窗口，现阶段接受）"并在 CY 决策记录里记录接受风险。

---

### BLOCK-4（M07）：节 5 多表事务答案 ❌ 但说明文字自相矛盾

**文件**：`M07-issue/00-design.md` 节 5 多表事务行

**位置**：答案列写 `❌ 不需要`，实现细节列写"遵循 M04 pilot 事务模式（Service 层包裹）"

**矛盾**：M04 pilot 节 5 多表事务是 ✅（Service 层事务包裹 upsert + activity_log）。如果 M07 说"遵循 M04 pilot 事务模式"，答案应该是 ✅；如果答案是 ❌，说明文字不能说"遵循 M04 pilot"。

**修复方向**：明确选择一个一致的立场，并更新对应说明。

---

## 可选优化清单（不阻塞但建议）

### OPT-1（M07）：assigned_to 强制约束的正式设计

如果 CY 认为"并发双 in_progress"风险需要 DB 防护，可考虑：
- Service 层使用 `SELECT ... FOR UPDATE` 锁定 issue 行再检查 status
- 或接受"纯 Service 层防护"并在 CY 决策记录里明确记录（替代虚假的 DB 约束声明）

**文件**：`M07-issue/00-design.md` 节 5 竞态分析表 + 节 3

---

### OPT-2（M14）：source_type 未来 migration 策略文档化

建议在节 3 Alembic 要点增加一条："扩展 rss/ai 时，需要 Alembic migration：`ALTER TABLE industry_news DROP CONSTRAINT ck_industry_news_source_type_manual; ALTER TABLE ... ADD CONSTRAINT ck_industry_news_source_type CHECK (source_type IN ('manual', 'rss', 'ai'))`，注意 AccessExclusiveLock 影响，建议在业务低峰期执行。"

**文件**：`M14-industry-news/00-design.md` 节 3 Alembic 要点

---

### OPT-3（M05 / M07 / M14）：activity_log 写入策略全项目统一决策

三个模块对 activity_log 是否在事务内写有不同选择（M04 在事务内 ✅；M05 在事务外；M07 含糊；M14 明确非事务）。建议通过横切 ADR 或 06-design-principles 补充说明，统一全项目策略（接受非事务 = 允许 activity_log 偶发丢失；或全部改为事务内）。

---

### OPT-4（M19）：测试 G6 补充代码路径差异说明

`M19-import-export/tests.md` G6 测试"入口 B 等价入口 A 单 node"，建议补充验证两入口的 project_id 校验代码路径（确认入口 B 的 URL path param 和入口 A 的 body 都经过同一 `check_project_access` 依赖）。

**文件**：`M19-import-export/tests.md` G6

---

## fix v2 自报告核实结论

| 声明 | 实际情况 |
|------|---------|
| "8 组决策全部落地" | **基本真实，但有细节漏洞**——决策 5 竞态分析表 M07 引用了不存在的 DB 约束（BLOCK-3）；决策 8 M05 activity_log 事务外写入未修（BLOCK-2） |
| "内部矛盾已修" | **部分漏改**——M05 Index vs UniqueConstraint 不一致是新引入的（或原有未发现的）矛盾；M07 节 5 多表事务说明引入了新的自相矛盾（BLOCK-4） |
| "0/1 ⚠️ 剩余" | **真实**——所有模块 tests.md 和 design.md 无 ⚠️ 占位符残留 |
| "无新问题" | **不真实**——NI-6（M05 Index vs UNIQUE 不一致）是高风险新发现；NI-2（M07 虚假 DB 约束声明）是未修原问题变体 |

**总结**：fix Agent 对 ⚠️ 清理是真实的，对决策落地文字是基本真实的，但对两处关键技术细节（M05 并发防护代码路径、M07 竞态分析引用）存在**漏改或引入新问题**——不是主观撒谎，而是机械修了文字但没有仔细核对 SQLAlchemy class 代码与文字描述的一致性。

---

*verify report 生成时间：2026-04-21*
*生成方：独立 reviewer-agent（未附和 fix Agent 自报告）*
