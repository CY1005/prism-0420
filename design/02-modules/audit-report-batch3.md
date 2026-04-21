---
title: Batch 3 对抗式 Audit 报告
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: 3
verify: false
modules: [M08, M09, M10, M15]
---

# Batch 3 对抗式 Audit 报告

> Reviewer 角色：独立资深架构师，不附和 implementer，所有发现引文件路径 + 节号/行号。
> 审稿对象：M08 模块关系图 / M09 全局搜索 / M10 项目全景图 / M15 数据流转可视化
> 基准：M04 pilot + README.md R0-R15 硬规则 + batch2 沉淀规则

---

## 第一轮：完整性审查

### M08 模块关系图

**M08-F1：§3 候选 B 改回成本块不完整（R3-4 违反）**

路径：`M08-module-relation/00-design.md` §3 "候选 B 改回成本"块（第 229-235 行）

仅量化了"有向改无向"和"唯一约束切换"的改回成本，但 §15 待 CY 裁决项还有 Q3（relation_type 枚举值增减），此类变更会触发 CheckConstraint 修改 + Alembic 迁移。R3-4 要求"核心设计决策必须有候选 B 改回成本块"——Q3 枚举扩展也属于核心决策，缺对应的改回成本量化（迁移步数 / 受影响模块数）。

**M08-F2：§3 SQLAlchemy model 缺 `updated_at` 字段声明来源**

路径：`M08-module-relation/00-design.md` §3 SQLAlchemy model 代码块（第 158-218 行）

model 继承 `TimestampMixin`，但未在文件内声明 TimestampMixin 的内容（含 `created_at` + `updated_at`）。ER 图（第 111-119 行）显示 `module_relations` 有 `timestamp created_at` 和 `timestamp updated_at`，但 M08 是硬删除（DELETE）模块，`updated_at` 只在 PATCH notes 时有意义——应在 §3 说明 TimestampMixin 包含哪些字段，避免实现时歧义。此外 M04 pilot 在 `base.py` 说明里有 TimestampMixin 定义，M08 引用但未给路径。

**M08-F3：§8 权限表"editor 写、viewer 读"的 Router 层区分未量化到全部 endpoint**

路径：`M08-module-relation/00-design.md` §8（第 361-369 行）

§8 表格写"Router：`Depends(check_project_access(project_id, role="editor"))` 写操作；读操作允许 viewer"，但 §7 endpoint 表（第 298-305 行）有 6 个 endpoint，其中 DELETE `/nodes/{node_id}/relations`（M03 级联调用）未在 §8 说明其权限层级——此接口是内部服务调用还是也经过 Router？若经过 Router，角色要求是什么？若不经过 Router，§8 异步路径声明需补"内部服务调用路径无 Router 层"说明。

**M08-F4：§10 activity_log delete_by_node_id 批量删除事件颗粒度未定义**

路径：`M08-module-relation/00-design.md` §10（第 437-445 行）

§10 脚注写"M03 级联删除节点时由 `ModuleRelationService.delete_by_node_id` 写 `delete` 事件"，但未说明：若一个节点有 N 条关联，是写 N 条 `delete` 事件，还是写一条"删除节点 X 的全部关联（N 条）"汇总事件？action_type / target_type / target_id 三列表格没有对应 `delete_by_node_id` 的行——违反 §10 表格完整性要求。

**M08-F5：§3 三重防护中 `Mapped[RelationTypeEnum]` + `String(32)` 搭配需补理由**

路径：`M08-module-relation/00-design.md` §3 "关键设计决策"（第 129-133 行）

R3-2 规定三重防护：`Mapped[RelationTypeEnum]` + `mapped_column(String(N))` + `CheckConstraint`。M08 选 `String(32)` 而非 `SAEnum`，文字说明引用了 batch2 统一规则，但 M08 是第三批——未说明"第三批沿用 batch2 统一选 String 不升 SAEnum"的决策依据（README.md R3-2 有说明，但 M08 §3 应显式引用 README §3 规则的"现状选型"行，而非仅写"三重防护"）。M09/M10/M15 无主表故不涉及，但此处 M08 需补显式引用。

---

### M09 全局搜索

**M09-F1：§3 "无主表"声明缺 DAO 草案代码中跨模块 import 的分层合规性说明**

路径：`M09-search/00-design.md` §3 / §9（第 104-339 行）

§9 DAO 草案代码（第 316-338 行）中 `SearchDAO` 直接 `db.query(Node)` / `db.query(Issue)`——这意味着 M09 DAO 直接 import M03 / M07 的 SQLAlchemy model。§6 禁止列（第 222 行）写了"M09 DAO 直 JOIN 其他模块表（候选 C 违反 R-X1）"，但候选 A 的 DAO 草案本质上也在跨模块 import model 类，与"候选 C 直 JOIN"的分层违反区别仅在 import 方式，而非是否引用了其他模块的 ORM 类。这一矛盾在文档中未解释——候选 A 应明确说明"各模块 Service 暴露 `search_by_keyword()` 接口"时 M09 Service 只调各模块 **Service 方法**，M09 DAO 不应 import 其他模块 model，§9 代码草案与 §3 描述的候选 A 存在实现路径矛盾。

**M09-F2：§5 清单 5 IN 过滤的 N+1 查询风险未声明**

路径：`M09-search/00-design.md` §5 约束清单（第 197-205 行）

清单 5 回答"DAO tenant 过滤 ✅"，§9 实现了 IN 过滤，但"先查 `project_members` 得到 project_ids，再做 IN 过滤"这一模式存在 N+1 风险：若用户有 100 个 project，IN 列表过大会导致 PG 全表扫描而非索引命中。此性能边界在 §5 / §9 均未提及，也未说明"是否对 project_ids 数量设上限"或"何时退化为子查询"。

**M09-F3：frontmatter `complexity: medium` 与实际复杂度不匹配**

路径：`M09-search/00-design.md` frontmatter（第 1-14 行）

M09 是跨 6 模块聚合 + 权限 IN 过滤 + snippet 生成的读聚合模块，`05-module-catalog.md` 中 M09 标为"🟡 中复杂度"，`complexity: medium` 与 catalog 一致。但 frontmatter 12 字段符合规范（R0-1 满足）。此条为观察项，不构成 blocker。

**M09-F4：§7 `SearchRequest` 用 `BaseModel` 处理 query params 的分层实现问题**

路径：`M09-search/00-design.md` §7（第 278-285 行）

`SearchRequest` 使用 `BaseModel`，注释写"FastAPI 自动从 query string 解析"。但 FastAPI 中 `BaseModel` 作为 query params 解析需要显式用 `Depends()`，直接 `SearchRequest` 入参会被解析为 request body（FastAPI 422 报错）。正确做法应用 `Query()` 注解或 `Depends()` 包装。此处实现草案存在明确技术错误，R7-1 要求 Pydantic schema 强类型，但 query param 解析方式错误会导致 AI 实现时直接套用出 bug。

**M09-F5：§1 US-C2.2 引用路径未核实**

路径：`M09-search/00-design.md` §1（第 30-32 行）

文档引用 `feature-list-and-user-stories.md` 中的 US-C1.3 / US-C2.2，但未给具体路径（与 M08 不同，M08 §1 引用了路径）。R1 要求"必须引 PRD/US 编号"——US 编号存在但路径未给，不完整。

---

### M10 项目全景图

**M10-F1：§3 DAO 草案 `count_enabled_dimensions` 与 `list_nodes_with_fill_count` 分两次查询，未说明是否有事务保证一致性**

路径：`M10-overview/00-design.md` §3 DAO 草案代码（第 146-188 行）

Service 层需要先调 `count_enabled_dimensions()` 拿到分母，再调 `list_nodes_with_fill_count()` 拿分子。两次查询不在同一事务内，存在中间状态：若两次查询之间 M02 修改了 `project_dimension_configs`（关闭一个维度），则分母与分子使用的维度集不一致，导致 `completion_rate > 1.0` 的异常值。§5 多表事务回答 `❌ N/A`（纯读无需事务）是正确的，但 §3 DAO 草案未说明"两次查询建议在同一 DB session 的 snapshot 内执行"或"使用 REPEATABLE READ 隔离级别"。此为边界场景缺口，但完整性审查阶段先标出。

**M10-F2：§7 `NodeOverview.children: list["NodeOverview"]` 递归嵌套未给 Pydantic v2 的 `model_rebuild()` 调用声明**

路径：`M10-overview/00-design.md` §7 Pydantic schema（第 275-291 行）

`NodeOverview` 含 `children: list["NodeOverview"]` 前向引用。Pydantic v2 中自引用模型需要在定义后调用 `NodeOverview.model_rebuild()` 才能正确解析类型注解，否则运行时报 `PydanticUserError`。文档没有 `model_rebuild()` 调用说明——AI 实现时照抄会有隐性 bug。

**M10-F3：§3 "无自有实体表"声明与 R3-1 要求的矛盾未显式解决**

路径：`M10-overview/00-design.md` §3（第 110-193 行）

R3-1 要求"必含 SQLAlchemy class 代码块"，M10 §3 提供的是 `OverviewDAO` 代码（DAO 层）而非 SQLAlchemy model class。§15 checklist（第 449 行）勾选"节 3：无自有表显式声明；...OverviewDAO 草案代码"。但 README.md R3-1 原文明确要求"SQLAlchemy class 代码块"——DAO class 不等同于 SQLAlchemy model class。M10 §3 应显式说明"R3-1 适用于有主表的模块，纯读聚合模块豁免——此豁免需 README.md 补充规则（见第三轮演进）"，而非直接在 §15 打勾视为满足。

**M10-F4：§6 `Service 直接 import 其他 Service` 禁止与上游 model 直接引用的矛盾**

路径：`M10-overview/00-design.md` §6（第 243-247 行）

§6 禁止"Service 直接 import 其他 Service（应通过 DAO 读上游数据）"，但 §3 DAO 草案（第 133-136 行）中 OverviewDAO 直接 import `api.models.node.Node`、`api.models.project_dimension_config.ProjectDimensionConfig`、`api.models.dimension_record.DimensionRecord`——这是跨模块 model import，与 R-X1 精神（"orchestrator 模块不直查/直写其他模块的表"）存在张力。§3 的 ⚠️ 标注承认这是"方案 A 下暂时的实时 JOIN"，但 §6 禁止列没有对应豁免说明，存在文档内自相矛盾。

---

### M15 数据流转可视化

**M15-F1：§3 `ActivityLog.action_type` / `target_type` 字段用 `String(50)` 而非枚举三重防护——违反 R3-2**

路径：`M15-activity-stream/00-design.md` §3 SQLAlchemy model（第 161-166 行）

`action_type: Mapped[str] = mapped_column(String(50), ...)` 和 `target_type: Mapped[str] = mapped_column(String(50), ...)` 缺少：
1. Python 类型注解应为 `Mapped[ActionTypeEnum]`（而非 `Mapped[str]`）
2. 缺 `CheckConstraint` 枚举值列出

§7 Pydantic schema（第 321-341 行）定义了 `ActionType` 和 `TargetType` 枚举，但 SQLAlchemy model 层未与其对齐。注释仅写"取值：'create' | 'update' | ..."文字注释，不满足 R3-2 三重防护中的 `Mapped[Enum]` + `CheckConstraint` 要求。这是横切共享表（activity_logs），影响所有写入模块对 action_type 的类型安全保证。

**M15-F2：§8 admin-only 权限——"admin" 角色在 M02 中的具体定义未引用**

路径：`M15-activity-stream/00-design.md` §8（第 381-389 行）

`Depends(check_project_access(project_id, role="admin"))` 的"admin"语义依赖 M02 的角色体系。M02 定义了什么角色枚举（owner / admin / editor / viewer？）在 M15 中未引用，仅写"项目管理员"。若 M02 最终的角色枚举中没有"admin"字符串（如用"owner"替代），M15 的实现会直接出 bug。缺少对 M02 角色定义的显式引用路径。

**M15-F3：§3 activity_logs `TimestampMixin` 只含 `created_at`，与全模块统一 `TimestampMixin`（含 `updated_at`）矛盾**

路径：`M15-activity-stream/00-design.md` §3 model（第 142-144 行）

注释"TimestampMixin 只含 created_at（不含 updated_at——日志不可修改）"，但 `base.py`（按工程规约 §1）定义的 `TimestampMixin` 是全局共享的——若全局 `TimestampMixin` 含 `updated_at`，则 `ActivityLog` 继承后会有 `updated_at` 字段，与"日志不可修改"的设计意图冲突。文档未提供解决方案（如：定义独立的 `ImmutableMixin` 只含 `created_at`，或覆盖 `TimestampMixin`）。

**M15-F4：§9 `count()` 在分页前执行可能引起 N+1**

路径：`M15-activity-stream/00-design.md` §3 DAO 草案（第 228-238 行）

`total = q.count()` 先执行全量 COUNT，再执行 OFFSET/LIMIT 分页查询——两次 SQL。对于大 project（百万级日志），`COUNT(*)` 不走索引的场景下性能差。文档未提及是否接受此性能代价，也未提出替代方案（如：只返回 `has_more` 而非精确 total，或用 Window Function 合并 COUNT 与 SELECT）。§7 `ActivityStreamResponse` 同时要求 `total` 和 `has_more`，但 total 的精确性与性能之间的 tradeoff 未在 §3 量化说明。

**M15-F5：frontmatter 12 字段完整，tests.md frontmatter 缺 `prism_ref` 字段**

路径：`M15-activity-stream/tests.md` frontmatter（第 1-8 行）

`tests.md` frontmatter 缺 `prism_ref` 字段（M15 对应 F15）。同样问题在 M08/M09/M10 的 tests.md frontmatter 也存在——4 个 tests.md 的 frontmatter 都缺 `prism_ref`。虽然 README.md 对 tests.md 的 frontmatter 字段要求未明确与 00-design.md 相同，但与 M04 pilot 的 tests.md 比较后确认此为风格不一致项，非强制 blocker。

---

**第一轮发现汇总：17 条**（M08: 5 / M09: 5 / M10: 4 / M15: 4，其中 M15-F5 为观察项）

---

## 第二轮：边界场景审查

### M08 边界场景

**M08-B1：自环防护仅有 DB CHECK，缺 Pydantic 层与 Service 层双重拦截的完整路径说明**

路径：`M08-module-relation/00-design.md` §3（第 176-179 行）、§7（第 348-353 行）

DB `CHECK(source_node_id != target_node_id)` 是最终兜底，Pydantic `@model_validator` 校验也有（§7 第 349 行），但 Service 层没有显式的自环检查（§8 Service 层只写了"节点归属校验"）。当 `RelationCreate.check_no_self_loop` 校验失败时，是抛 `ValueError`（Pydantic 默认）还是应该映射为 `RELATION_SELF_LOOP` ErrorCode？§13 定义了 `RelationSelfLoopError(http_status=422)`，但文档未说明 Pydantic `ValueError` 如何被 FastAPI exception handler 转换为此 ErrorCode。M04 pilot 中 exception handler 映射未在 M08 §13 中说明。

**M08-B2：反向关系冗余问题——未显式定义**

路径：`M08-module-relation/00-design.md` §1 边界灰区（第 55-58 行）、§3（第 161-169 行）

M08 存储有向关系（A→depends_on→B），当业务需要查"B 被哪些模块依赖"时，需要查询 `WHERE target_node_id = B`。§7 的 `GET /nodes/{node_id}/relations` 端点实现了"source 或 target 为该节点"的双向查询（§9 DAO `list_by_node` 第 394-397 行），但文档未定义：`depends_on` 的反向语义是什么？前端展示时如何区分"A 依赖 B"（source=A）和"C 依赖 A"（target=A）的方向展示？此为业务边界未定义，会导致前端实现歧义。

**M08-B3：R-X2 级联场景——M03 删除节点时 `delete_by_node` 跨事务的原子性**

路径：`M08-module-relation/00-design.md` §1 边界灰区（第 60-61 行）、§9（第 404-415 行）

M03 Service 调 `ModuleRelationService.delete_by_node_id(node_id, project_id)` + 写 activity_log，然后 M03 再删自己的 node。若 M08 的 delete + activity_log 成功，但 M03 删 node 失败回滚——此时 M08 的关联已删、log 已写，但 node 仍存在，产生数据不一致。R-X2 规则本身没有解决跨模块事务的原子性问题，M08 文档也没有说明这个场景——整个删除流程应该在 M03 Service 的一个事务内调 M08 Service（共享同一 db session），但 M08 提供的接口草案未说明是否支持传入外部 session。

**M08-B4：relation_type 枚举扩展——业务添加新类型时的 Alembic 迁移风险**

路径：`M08-module-relation/00-design.md` §3（第 151-153 行）、§15 裁决项 Q3

§15 Q3 说明"CY 可增减枚举值，但每次变更需同步 CheckConstraint + Alembic 迁移"，但未量化：若已有 `depends_on` 类型的 1000 条数据，新增 `includes` 类型只需 ALTER TABLE（无数据丢失）；删除已有类型则需要先清理该类型数据再改约束（有数据丢失风险）。删除操作的不可逆性在 §3 候选 B 改回成本块中未覆盖（R3-4 要求的"数据迁移不可逆性"缺失此路径）。

**M08-B5：并发创建"同三元组"关联时，DB IntegrityError 捕获后转换为 RELATION_DUPLICATE 的实现路径未说明**

路径：`M08-module-relation/00-design.md` §13（第 497-501 行）

`RelationDuplicateError` 定义了 `http_status = 409`，tests.md C1 场景（并发创建同三元组）期望"第二个 409 RELATION_DUPLICATE"。但 Service 层如何捕获 `sqlalchemy.exc.IntegrityError` 并区分"唯一约束冲突"与"其他完整性错误"（如 FK 不存在），文档未说明 catch 分支逻辑。M04 pilot §13 也未建立此惯例，但 M08 是第一个依赖 UniqueConstraint 防重的模块，此实现细节缺失会导致 AI 实现时要么 catch 太宽（所有 IntegrityError 都返回 409）要么太窄（只 catch 特定 constraint 名）。

---

### M09 边界场景

**M09-B1：跨模块聚合方案 A/B/C 未量化性能对比——无法做出有据可依的决策**

路径：`M09-search/00-design.md` §3 候选表（第 112-118 行）

三个候选方案的"优缺点"列只有定性描述，缺定量：候选 A 的"N 次 DB 查询"中 N = 6（当前搜索范围 6 个模块），6 次查询的并行 vs 串行延迟是多少？候选 B 的物化视图刷新延迟是秒级还是分钟级？候选 C 明确不推荐。README.md R3-4 要求"核心设计决策必须有候选 B 改回成本"，但此处更关键的是候选间的量化对比——没有数字，CY 无法据此做出有依据的决策（这也是 feedback_decision_business_view.md 强调的"业务场景 + 两种选择体验"原则）。

**M09-B2：JSONB `content::text ILIKE` 的精度问题在测试中未覆盖**

路径：`M09-search/00-design.md` §1 边界灰区（第 68 行）、`M09-search/tests.md` §2

§1 指出"JSONB::text ILIKE 精度低，可能匹配 JSON key 名"，但 tests.md §2 边界场景 8 条中没有一条测试"搜索词命中 JSON key 名而非 JSON value 的假阳性"场景。R14-1 要求"tests.md 写完时所有决策已定，禁止 ⚠️ 渗漏"——此 ⚠️ 决策点（Q3）渗漏到了 tests.md 中（tests.md 第 12 行注释"G2 命中 dimension_record"隐含此风险但未测试假阳性）。

**M09-B3：`_get_accessible_project_ids()` 结果为空 list 时的搜索行为未定义**

路径：`M09-search/00-design.md` §8（第 292-297 行）、§9（第 304-349 行）

若用户无任何 project 成员身份，`_get_accessible_project_ids()` 返回空 list，此时 `WHERE project_id IN ()` 在 PostgreSQL 中是合法的 SQL（返回 0 行），但某些 ORM 版本会在 IN 空 list 时抛异常或生成无效 SQL。文档未说明如何处理空 project_ids 的情况（是短路直接返回空结果，还是继续执行 SQL）。

**M09-B4：`industry_news` 搜索在候选 A（各模块 Service 提供接口）下如何处理？M14 是全局无 project_id 模块**

路径：`M09-search/00-design.md` §2（第 98 行）、§3 搜索字段表（第 121-129 行）

候选 A 要求"M14 提供 `search_by_keyword(query, project_id)` 接口"，但 M14 是全局无 project_id 模块（catalog Tenant ❌）。M14 Service 的 `search_by_keyword` 接口签名如果必须有 `project_id` 入参，则接口设计不自然；若不带 `project_id`，则与其他 5 个模块的接口签名不一致，聚合逻辑需要分支处理。此边界场景在文档中未显式处理。

**M09-B5：搜索结果排序策略未定义——ILIKE 无分数，结果顺序不确定**

路径：`M09-search/00-design.md` §3（第 158-165 行），§7 `SearchResultItem.score: float | None`

ILIKE 搜索下 `score` 填 `None`，但返回结果的排序规则文档未定义（§9 DAO 草案无 ORDER BY）。`total: int` 计数在多模块聚合后可能跨模块重复计算（6 模块各自 count 再加总不等于去重后总数）——文档未说明 total 的语义是"各模块命中数之和"还是"去重结果数"。

---

### M10 边界场景

**M10-B1：实时 JOIN 的 SQL 查询数量和耗时未量化——大项目性能边界缺失**

路径：`M10-overview/00-design.md` §3 候选表（第 96-106 行）、§7（第 327 行注释）

§7 注释"若节点数 > 1000，嵌套组装可能有性能问题——初版不处理"，但未量化：1000 nodes + 10 dims 的项目，一次 `/overview` 请求需要执行几条 SQL？`list_nodes_with_fill_count` 是 1 条 JOIN SQL（实际是一次查询，已 GROUP BY），`count_enabled_dimensions` 是 1 条，合计 2 次 SQL，这是可接受的。但 Service 层在内存组装 flat→nested 树时，1000 节点的时间复杂度是 O(N²) 还是 O(N)（取决于是否有 parent_id 索引优化）？文档未说明内存组装算法，留下实现不确定性。

**M10-B2：folder 节点均值计算的递归深度问题——深层嵌套时的栈溢出风险**

路径：`M10-overview/00-design.md` §1 边界灰区（第 57 行）、`M10-overview/tests.md` E7

tests.md E7 测试了"depth > 5 的深层嵌套树"，但 §1 中"folder 节点显示子节点均值完善度（汇总）"若递归实现，对 depth 很深的树（如 depth = 20）可能出现 Python 递归栈限制（默认 1000）。文档未说明均值计算是递归实现还是迭代实现，也未说明最大支持 depth 是多少（M03 中是否有 depth 限制约束）。

**M10-B3：冷启动时（无 `dimension_records`）`completion_rate` 为 0.0 vs `OVERVIEW_NO_DIMENSIONS` 的区分逻辑**

路径：`M10-overview/00-design.md` §13（第 395-402 行）、`M10-overview/tests.md` E2/E6

两个边界：(a) 项目未配置任何启用维度（分母=0）→ 422 `OVERVIEW_NO_DIMENSIONS`；(b) 项目有启用维度但所有 file 节点都未填（分子=0）→ completion_rate=0.0 正常返回。E2 测试了 (a)，E6 测试了 (b)。但 Service 层判断"分母=0"的时机文档未说明：是 `count_enabled_dimensions()` 返回 0 时立即抛 422，还是在聚合计算时发现 0/0？若在聚合时才发现，部分节点数据已计算但 422 中断——事务一致性（实际为无事务读，但响应一致性）需要明确。

**M10-B4：`OverviewNoDimensionsError` http_status=422 但用途是"业务规则不满足"，而非"请求参数非法"**

路径：`M10-overview/00-design.md` §13（第 407-419 行）

`OVERVIEW_NO_DIMENSIONS` 的 `http_status = 422` 在 HTTP 语义上是"Unprocessable Entity"，通常用于请求参数校验失败。但"项目未配置维度"是服务端状态问题（数据不满足业务前提），更符合 `409 Conflict` 或 `424 Failed Dependency` 的语义。M04 pilot 中此类"业务前提不满足"的错误使用了什么 http_status 未在 M10 中对照说明——存在 ErrorCode 语义设计不一致风险。

---

### M15 边界场景

**M15-B1：百万级 `activity_logs` 的 COUNT(*) 性能问题——分页 total 字段的计算代价**

路径：`M15-activity-stream/00-design.md` §3 DAO 草案（第 227-228 行）

`total = q.count()` 在 `activity_logs` 有过滤条件（user_id / action_type 等）时，若过滤字段没有复合索引，COUNT(*) 需要全表扫描过滤字段。§3 `__table_args__` 索引（第 148-150 行）定义了 `(project_id, created_at)`、`(user_id, project_id)`、`(target_type, target_id)` 三个索引，但没有 `(project_id, action_type)` 或 `(project_id, user_id, action_type)` 的复合过滤索引。按 action_type 过滤时 COUNT 会走 `(project_id, created_at)` 再额外过滤，性能有问题。文档未量化过滤场景的查询计划。

**M15-B2：删除节点/项目后，`activity_log` 历史记录中的 `target_id` 成为僵尸 ID——前端展示策略未定义**

路径：`M15-activity-stream/00-design.md` §3 model（第 152 行），§1 out of scope（第 43-48 行）

`target_id: Mapped[str]`（无 FK 约束，Text 类型），这是有意设计——日志不应因目标被删而丢失。但前端展示时，若 `target_type=node`、`target_id=<已删除的 node UUID>`，M15 仅返回 `summary` 字段（"删除了节点 XXX"可能由写入方在 summary 里写了名字），但若前端需要点击 `target_id` 跳转到对应节点，已删除节点会 404。此场景文档的 §1 out of scope 和 §7 均未说明处理策略，属于边界灰区未覆盖。

**M15-B3：admin 权限语义——M02 项目 role 体系未对齐，若 M02 最终 role 枚举无 "admin"**

路径：`M15-activity-stream/00-design.md` §8（第 386 行）

延续第一轮 M15-F2，此处指出边界场景：若 M02 项目的角色分为 `owner / editor / viewer`（无独立 "admin"），则 `check_project_access(role="admin")` 会永远拒绝访问（或永远通过，取决于实现）。US-A2.2 说"项目管理员"，但 M02 最终的角色枚举未在 M15 中引用——此不对齐是功能性 bug 来源，非仅文档问题。

**M15-B4：`from_dt > to_dt` 的过滤参数校验在 Pydantic `BaseModel` query params 中如何触发**

路径：`M15-activity-stream/00-design.md` §7（第 342-350 行）、`M15-activity-stream/tests.md` E3

tests.md E3 期望 `from_dt > to_dt` 时返回 422 `ACTIVITY_STREAM_INVALID_FILTER`。但 `ActivityStreamFilter` 是 `BaseModel`（query params 解析）——Pydantic v2 中跨字段校验需要 `@model_validator(mode='after')`，文档 §7 未包含此 validator 代码，只有字段定义。AI 实现时照抄会导致 E3 测试场景直接 pass（返回 200 空结果而非 422）。与 M08 §7 有 `@model_validator` 的做法（第 347-352 行）不一致。

---

**第二轮发现汇总：19 条**（M08: 5 / M09: 5 / M10: 4 / M15: 4，另含 M08-B3 跨模块事务性问题为本批最高严重度）

---

## 第三轮：演进 + 模板可复用性审查

### 演进风险

**E1：半年后多用户场景下 M09 IN 过滤会成为性能瓶颈——设计无扩展出口**

路径：`M09-search/00-design.md` §9（第 306-349 行）

用户有 100+ project 时，`project_id IN (...)` 变为 `IN (100 UUIDs)`，PG 可能走全表扫描。当前设计无上限截断、无分片策略、无缓存层。演进到多人团队（一个用户可能是几十个项目的成员）时，此查询模式会首先塌方。文档未说明"project_ids 数量超过 N 时的降级策略"，也未说明是否计划引入 Redis 缓存 project_ids（§9 脚注提到但标 ⚠️ 未决策）。

**E2：M15 `activity_logs` 无归档/分区策略——数据增长无界**

路径：`M15-activity-stream/00-design.md` §3 `__table_args__`（第 148-150 行）

`activity_logs` 是 append-only 横切表，随业务操作无限增长。当前设计无分区表（partition by created_at）、无 TTL 归档策略、无"超过 N 天的日志压缩"机制。tests.md E7 仅测试 500 条记录，未说明 10 万条 / 100 万条时的性能预期。半年后中大型项目的 activity_logs 将严重影响 M15 查询性能（COUNT(*) 尤甚，见 M15-B1）。此为演进设计缺位。

**E3：M10 folder 节点完善度均值算法——跨 project 扩展时分母定义可能不一致**

路径：`M10-overview/00-design.md` §1 D2 / D3 裁决点（第 470-474 行）

若未来跨 project dashboard（D1 选 B）时，不同 project 启用的维度数不同（D2），folder 节点的完善度"均值"会混合不同分母的比率（有的 project 3 个维度，有的 5 个）——此时均值无意义。当前设计将 D1/D2/D3 作为独立裁决点，但未分析三者组合后的一致性约束，演进时会遇到此问题。

**E4：M08 `relation_type` 枚举与 M15 `target_type` 枚举未统一管理——两处硬编码，增加类型时需双改**

路径：`M08-module-relation/00-design.md` §3（第 151-153 行）、`M15-activity-stream/00-design.md` §7（第 335-341 行）

M15 `TargetType` 包含 `relation = "relation"`（第 340 行），M08 `RelationTypeEnum` 定义关联类型。两者独立，未建立引用关系。当 M08 新增 relation_type 时，如果业务需要在 M15 展示"relation 类型变更"的 activity_log，M15 的 TargetType 和 ActionType 枚举也可能需要更新——但无交叉引用，漂移风险高。

---

### 模板可复用性

**T1："无主表模块" R3-1 豁免规则缺失——README.md 需补充**

路径：`README.md`（第 112-113 行 R3-1）；`M09-search/00-design.md` §3 / `M10-overview/00-design.md` §3 / `M15-activity-stream/00-design.md` §3

R3-1 原文"必含 SQLAlchemy class 代码块"，三个纯读聚合模块（M09/M10/M15）都是"无主表"场景，提供的是 DAO 草案代码或 Pydantic-only schema，而非 SQLAlchemy model class。三个模块都在 §15 打勾声称满足 R3-1，但这是错误的自我评估——它们满足的是"提供了某种数据访问代码块"而非 R3-1 本义。

**建议 README.md 补充"R3-1 扩展：纯读聚合模块 §3 规范"**，必填清单应包含：
1. 显式声明"本模块无主表，§3 适用纯读聚合规范"
2. 上游表引用清单（表名 / 归属模块 / 操作类型：只读 SELECT）
3. DAO 草案代码块（含 tenant 过滤模式）
4. 若有 Pydantic-only 聚合结构，明确标注"无 SQLAlchemy model"
5. 候选 B/C 改回成本（R3-4 照常适用）

**T2：M09/M10/M15 三模块 §15 checklist 都将 R3-1 打勾为"通过"——需修正为"豁免 + 引用新规则"**

路径：`M09-search/00-design.md` §15（第 443 行）、`M10-overview/00-design.md` §15（第 449 行）、`M15-activity-stream/00-design.md` §15（第 503 行）

三个模块的 §15 checklist 关于"节 3"都打勾，但实际上都是以"无主表声明 + DAO 草案"代替"SQLAlchemy class 代码块"——这是对 R3-1 的误读。Fix v1 阶段需要统一修正为"§3 满足纯读聚合规范（R3-1 扩展，待 README 补充）"，而非现在的"R3-1 满足"。

**T3：ADR-003 横切决策——建议起草，采纳候选 A，对 M09/M10/M15 统一约束**

路径：`M09-search/00-design.md` §3（第 108-118 行）、`M10-overview/00-design.md` §3（第 90-106 行）、`M15-activity-stream/00-design.md` §3（第 88-103 行）

三个模块均显式预警 ADR-003，M15 分析指出"M15 只消费 activity_logs 单一横切表，ADR-003 对 M15 价值较低"，M10 认为"ADR-003 对 M10 价值更高"。

**ADR-003 建议内容**（4 项核心）：

1. **候选对比**：A（各模块 Service 暴露 search/read 接口）/ B（物化视图）/ C（DAO 直 JOIN，已否决）
2. **建议采纳**：**候选 A**——理由：符合 R-X1 分层原则；各模块 Service 接口是已有模式（M08 已为 M09 提供 `search_by_keyword()`）；物化视图 B 引入 REFRESH 刷新复杂度，对本期单用户场景过度设计；候选 C 已明确违反 R-X1 否决
3. **对 M09/M10/M15 的应用**：M09 → 各上游 Service 暴露 `search_by_keyword(query, project_id)` 接口（M14 例外：无 project_id 参数）；M10 → Service 层通过 DAO 直读上游 model（当前方案 A 的实质是 DAO 跨模块 import，ADR-003 应明确此为"只读 import 上游 model"的豁免规则，而非通过 Service 调 Service）；M15 → 方案 A 独立 DAO 直查 activity_logs（activity_logs 是横切共享表，不属于任何单一模块的"跨模块"读取，应豁免）
4. **对未来模块的约束**：新增聚合读模块必须在 §3 显式引用 ADR-003，声明采纳哪种候选，禁止默认走候选 C

**T4：第二批 M02/M03/M11/M12 规则对照——M08 activity_log 批量删除事件颗粒度与 M03 不一致风险**

路径：`M08-module-relation/00-design.md` §10（第 445 行）、`M03-module-tree/00-design.md`（参考路径）

M08 §10 说明"M03 级联删除节点时写 delete 事件"，但颗粒度未定（N 条独立事件 vs 1 条汇总事件）。M03 在 R-X2 规则下调 M08 Service 批量删除，若两模块对"一次批量操作写几条 activity_log"的理解不同，会导致 M15 展示的操作流水混乱（删一个有 20 条关联的节点显示 20 条 delete 事件 vs 1 条）。第二批未确立此约定，第三批应补充。

**T5：M15 `action_type` / `target_type` 枚举的"横切对齐清单"缺失——各模块 accepted 后需汇总**

路径：`M15-activity-stream/00-design.md` §15 D6 裁决点（第 533 行）

D6 已识别"ActionType / TargetType 枚举完整性需与各模块 activity_log 事件清单逐一对齐"，但裁决时机依赖"待各模块 accepted 后汇总"。这意味着 M15 当前 schema 中的 `ActionType` / `TargetType` 枚举是不完整的占位版本——若 M15 先于 M13/M16/M18 accepted，后续补充枚举需要 Alembic 迁移（若 ActivityLog model 改用 SAEnum）或修改 Pydantic schema（若只改 Pydantic）。此演进路径需在 ADR 或模板规则中明确约定。

---

**第三轮发现汇总：9 条**（演进 4 条 / 模板 5 条）

---

## 总发现汇总

| 轮次 | M08 | M09 | M10 | M15 | 合计 |
|------|-----|-----|-----|-----|------|
| 第一轮（完整性） | 5 | 5 | 4 | 4（+1 观察）| 17 |
| 第二轮（边界） | 5 | 5 | 4 | 4 | 19 |
| 第三轮（演进/模板）| 横切 | 横切 | 横切 | 横切 | 9 |
| **合计** | 10 | 10 | 8 | 8 | **45** |

---

## 关键 Blocker 分级

### 🔴 BLOCKER（必须修复才能 accept）

| ID | 模块 | 问题 | 涉及规则 |
|----|------|------|---------|
| M15-F1 | M15 | `action_type` / `target_type` 用 `Mapped[str]` 缺枚举三重防护 | R3-2 |
| M09-F1 | M09 | §9 DAO 草案与§3 候选 A 描述矛盾（DAO 直 import 上游 model vs Service 提供接口）| R-X1 / R3-1 |
| M08-B3 | M08 | M03→M08 跨模块删除的原子性问题未说明（共享 db session 策略缺失）| R-X2 |
| M09-B4 | M09 | M14 全局无 project_id 表在候选 A 接口签名下的不一致问题未处理 | 分层一致性 |
| M09-F4 | M09 | `SearchRequest BaseModel` 用作 query params 的 FastAPI 解析错误（技术 bug）| R7-1 |
| M15-B4 | M15 | `from_dt > to_dt` 跨字段校验缺 `@model_validator`，E3 测试会直接失败 | R7-1 |
| M15-F3 | M15 | `ActivityLog` 继承全局 `TimestampMixin` 含 `updated_at` 与"不可修改"语义冲突 | R3-1 |

### 🟡 需要在 CY 决策后补充（不阻塞 Fix v1，阻塞 accept）

| ID | 模块 | 问题 |
|----|------|------|
| M08-F4 | M08 | `delete_by_node_id` 批量操作的 activity_log 颗粒度未定义 |
| M10-F3 | M10 | R3-1 豁免未显式声明，checklist 误勾 |
| M15-F2 / M15-B3 | M15 | "admin" 角色与 M02 角色枚举未对齐 |
| M10-B3 | M10 | 分母=0 抛 422 的时机与 Service 逻辑需明确 |
| M08-B1 | M08 | Pydantic ValueError → RELATION_SELF_LOOP ErrorCode 的 exception handler 映射未说明 |

### 🟢 观察项（不阻塞，建议下个批次统一处理）

- M08-F2：TimestampMixin 路径未引用
- M09-F5：US 引用缺路径
- M10-F2：`model_rebuild()` 未声明
- M10-B4：`OVERVIEW_NO_DIMENSIONS` http_status=422 语义争议
- E2：activity_logs 无归档策略（长期演进）
- T5：ActionType/TargetType 枚举对齐时机约定缺失

---

## 入场判断（能否转 accepted）

| 模块 | 当前状态 | 是否能转 accepted | 必须补充 |
|------|---------|-----------------|---------|
| **M08** | draft | ❌ 不能 | 修复 M08-B3（跨模块事务原子性）；补 M08-F4（批量删除 log 颗粒度）；明确 M08-B1（exception handler 映射）；CY 裁决 Q1/Q2/Q3 |
| **M09** | draft | ❌ 不能 | 修复 M09-F1（DAO 与候选 A 矛盾）；修复 M09-F4（SearchRequest query param 解析 bug）；处理 M09-B4（M14 接口签名不一致）；CY 裁决 Q1（ADR-003）后联动修改 |
| **M10** | draft | ❌ 不能 | 修复 M10-F3（R3-1 误勾）；补 M10-F2（model_rebuild）；明确 M10-B3（分母=0 处理时机）；CY 裁决 D3/D4 |
| **M15** | draft | ❌ 不能 | 修复 M15-F1（三重防护缺失，最高优先）；修复 M15-F3（TimestampMixin 冲突）；修复 M15-B4（@model_validator 缺失）；CY 确认 M02 角色枚举 |

**4 个模块全部不能转 accepted，均需 Fix v1 后 Verify。**

---

## 关键模板调整建议（3-5 条）

1. **补充 "R3-1 扩展：纯读聚合模块 §3 规范"**（`README.md`）：明确无主表模块的 §3 必填内容（上游表引用清单 + DAO 草案 + 无 model 声明），避免 M09/M10/M15 式的 R3-1 误判。

2. **起 ADR-003，采纳候选 A，约束未来聚合读模块**：三模块均预警 ADR-003，建议在 Fix v1 前由主对话出 ADR-003 决策文档，否则 M09 §9 的 DAO 草案无法定稿（矛盾 M09-F1 无法修复）。

3. **activity_logs 横切表归属声明**（`README.md` 或新 ADR）：明确 activity_logs model 由谁 own、谁来维护 Alembic 迁移、ActionType/TargetType 枚举变更流程（各模块 accepted 后汇总 → M15 schema 更新 → Alembic 迁移），避免 T5 的漂移问题。

4. **跨模块级联删除的事务原子性约定**（`README.md` R-X2 扩展）：R-X2 目前只规定"Service 显式调 delete_by_xxx 写 activity_log"，但未约定共享 db session 模式。补充"被级联删除方 Service 必须支持传入外部 db session"，确保 M03→M08 类操作的原子性。

5. **activity_log 批量操作颗粒度约定**（`README.md` §10 规则补充）：约定"批量操作（delete_by_node_id 等）写 N 条独立 delete 事件，每条 target_id 独立记录，不做汇总"或反之——二者均可，但必须全局统一，避免 M15 展示时的 UI 体验不一致。

---

## ADR-003 明确建议

**建议：起 ADR-003。**

- **是否起**：是。三个模块（M09/M10/M15）独立预警且均以 ⚠️ 占位，主对话不决策则 Fix v1 无法修复 M09-F1（DAO 实现路径矛盾）。
- **建议采纳候选**：**候选 A**（各模块 Service 暴露 read/search 接口，M10/M15 例外处理见下）
- **理由**：
  - 符合 R-X1（orchestrator 不直 JOIN 其他模块表）
  - M08 已为 M09 预设了 `search_by_keyword()` 接口草案（M08 §9 第 417-428 行），候选 A 已有实战先例
  - 候选 B（物化视图）对本期单用户场景是过度设计，且 REFRESH 刷新策略复杂
- **M10/M15 的例外处理**：
  - M10 的 OverviewDAO 直接 import 上游 SQLAlchemy model 属于"只读 model import"，ADR-003 应为此建立豁免规则（"聚合读 DAO 可 import 上游 model 进行只读查询，不得写入"），与候选 A 的"通过 Service 接口"并行约束
  - M15 的 activity_logs 是横切共享表（非任何单一模块私有），M15 直查 activity_logs 不属于"跨模块 Read"问题，ADR-003 应明确排除横切共享表的限制范围
- **对未来模块的约束**：新增聚合读模块必须在 §3 引用 ADR-003，声明采纳哪条规则（候选 A Service 接口 / 只读 model import 豁免 / 横切表豁免），不得默认走候选 C（DAO 直 JOIN 业务表）
