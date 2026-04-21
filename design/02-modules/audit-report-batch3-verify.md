---
title: Batch 3 Verification Report（Fix v2 + 主对话精修后独立验证）
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
batch: 3
verify: true
modules: [M08, M09, M10, M15]
---

# Batch 3 第三轮 Verification 审稿报告

> 角色：独立 verify reviewer Agent，不附和 fix Agent 自报告，只看文件判断。
> 审稿对象：M08/M09/M10/M15 Fix v2 + 主对话精修后文件
> 基准：README.md（R0-R15 + 新规则）+ ADR-003 + 原始 audit-report-batch3.md 45 条发现

---

## 1. 执行摘要（准入判断）

| 模块 | 准入判断 | 原因摘要 |
|------|---------|---------|
| **M08** | ⚠️ **条件准入**（1 个新发现需确认）| 22 条决策 A-1/A-2/A-3 全部真落地；R-X3 外部 session 接口在 DAO 层有说明但 Service 签名草案未补；§10 批量事件颗粒度明确（R10-1 合规）；总体合规度高，1 处需精修后可接受 |
| **M09** | ⚠️ **条件准入**（2 个发现需确认）| A-4/A-5/A-6/C-1/C-2/C-3/D-4 全部真落地；SearchDAO 已删除（Service 层调上游 Service）；但 §6 禁止列出现"搜索 DAO"称谓混乱；tests.md §7 覆盖率表仍写"DAO（search_dao）"——与无 DAO 设计冲突，是新引入问题 |
| **M10** | ✅ **可接受**（无 blocker）| A-7/A-8/A-9/C-4/D-1 全部真落地；ADR-003 规则 2 引用完整；R3-5 规范满足；3 条 ErrorCode + AppError 子类齐全；model_rebuild() 已补 |
| **M15** | ⚠️ **条件准入**（2 个残留问题）| A-10/A-11/A-12/C-5/C-6/D-2/D-3 全部真落地；admin→owner+editor 已修；ImmutableMixin 已修；@model_validator 已补；三重防护 CheckConstraint 已补；但有 2 个新发现（见下方 §3 类 3 + 类 5）|

**总体结论**：Fix v2 + 主对话精修后，22 条决策 **19 条真落地，2 条表面落地但存在一致性瑕疵，1 条（D-1 M10 folder 迭代 bottom-up）落地但需跨章节核实**。整体 fix 质量较高，不是"撒谎"，但有 **3 处新引入问题**和 **2 处漏改细节**需精修。

---

## 2. 22 条决策落地验证结果

### A 类 12 项（必须显式出现在代码/文字中）

---

**A-1 M08 关联有向（§3 SQLAlchemy + §3 说明 + §15 决策表）**

- §1 边界灰区（约第 56 行）：明确"关联为**有向关系**（`source_node_id` → `target_node_id`）"
- §3 SQLAlchemy：`source_node_id` / `target_node_id` 分开字段，无 min/max 约束
- §15 决策表 A-1：" **候选 A 有向**（source→target 有意义）"
- **判断：✅ 真落地**

---

**A-2 M08 同对多类型 UNIQUE(source,target,type)**

- §3 `__table_args__`（约第 162-168 行）：`UniqueConstraint("source_node_id", "target_node_id", "relation_type", name="uq_module_relation_src_tgt_type")`
- §15 决策表 A-2：UNIQUE(source,target,type) 三元组定案
- **判断：✅ 真落地**

---

**A-3 M08 relation_type 3 种 + CheckConstraint**

- §3 `RelationTypeEnum`（第 152-157 行）：`depends_on / related_to / conflicts_with` 3 种
- `CheckConstraint("relation_type IN ('depends_on', 'related_to', 'conflicts_with')", name="ck_module_relation_type_valid")`（第 173-175 行）
- §15 决策表 A-3：3 种枚举 + 可扩展
- **判断：✅ 真落地**

---

**A-4 M09 搜索范围仅成员 project（§1 + §9 IN 过滤）**

- §1 边界灰区（约第 64 行）："M09 只搜索用户有成员身份的 project（IN 过滤）"
- §9 Service 草案（约第 343-348 行）：`accessible_project_ids = self._get_accessible_project_ids(db, user_id)` → IN 过滤
- §15 决策表 A-4：候选 A 仅成员 project
- **判断：✅ 真落地**

---

**A-5 M09 ILIKE 算法 + score 字段注释**

- §1 边界灰区（约第 66 行）："`score: float | None` 字段在 ILIKE 下始终为 None"
- §3 `SearchResultItem`（约第 174 行）：`score: float | None  # ILIKE 下始终为 None（保留字段以防未来升级全文搜索，CY ack A-5）`
- §7（约第 282 行）同样有 `score: float | None # ILIKE 下始终为 None（保留字段以防未来升级全文搜索，CY ack A-5）`
- **判断：✅ 真落地**

---

**A-6 M09 JSONB::text ILIKE + tests.md E9 假阳性场景**

- §1 边界灰区（约第 68 行）：CY ack 接受边界，`content::text ILIKE` 可能命中 JSON key 名
- tests.md E9（第 46 行）："JSONB key 名假阳性（CY ack 接受边界，A-6）"——场景已添加
- **判断：✅ 真落地**

---

**A-7 M10 单 project 视图**

- §1 边界灰区（约第 55 行）："CY ack 候选 A 单 project 视图"
- §15 决策表 A-7："候选 A 单 project"
- **判断：✅ 真落地**

---

**A-8 M10 按 project 启用维度分母**

- §1 边界灰区（约第 56 行）："分母为该 project 启用的维度数（M02 `project_dimension_configs`）"
- §3 OverviewDAO `count_enabled_dimensions`（约第 151-160 行）：过滤 `enabled==True` + `project_id`
- §15 决策表 A-8：候选 A 按 project 启用维度
- **判断：✅ 真落地**

---

**A-9 M10 folder 子节点均值**

- §1 边界灰区（约第 57 行）："folder 节点显示其子树 file 节点的均值完善度"
- §3 folder 均值计算说明（约第 204-209 行）：**迭代（bottom-up 后序遍历）**，非递归
- §15 决策表 A-9：候选 A 子节点均值
- **判断：✅ 真落地**

---

**A-10 M15 单 project 视图**

- §1 边界灰区（约第 53 行）："CY ack 候选 A 单 project 视图"
- §15 决策表 A-10：候选 A 单 project
- **判断：✅ 真落地**

---

**A-11 M15 target name 仅 summary**

- §1 边界灰区（约第 54 行）："CY ack 候选 A 仅显示 summary"
- §1 Out of scope（约第 47 行）："节点名称 / 维度类型名称的完整 JOIN 展示——CY ack A-11：不做跨表 JOIN，仅显示 summary 字段"
- §15 决策表 A-11：候选 A 仅显示 summary
- **判断：✅ 真落地**

---

**A-12 M15 无实时推送**

- §1 边界灰区（约第 57 行）："CY ack 无实时推送——普通分页 GET 列表，不引入 WebSocket 或 SSE"
- §5 异步处理 ❌ N/A
- §15 决策表 A-12：无实时推送
- **判断：✅ 真落地**

---

### C 类 6 项（底部 CY 决策记录表须有 ack 行）

---

**C-1 M09 total 各模块和式（候选 A）**

- §7 `SearchResponse`（约第 288 行）：`total: int  # 各模块命中数之和，不跨模块去重（CY ack C-1，候选 A）`
- §15 决策记录 C-1："候选 A 各模块命中数之和"
- §9 Service `_merge_and_paginate`（约第 372-379 行）：`total = len(sorted_results)` 直接加总
- **判断：✅ 真落地**

---

**C-2 M09 created_at DESC + 类型分组排序（候选 A）**

- §9 Service `_merge_and_paginate`（约第 374-375 行）：`sorted_results = sorted(results, key=lambda x: x.created_at, reverse=True)`
- 注释："按 created_at 降序排列（ILIKE 无 score，用 created_at 作时间线锚点）"
- §15 决策记录 C-2：候选 A created_at DESC
- **判断：✅ 真落地**

---

**C-3 M09 M14 默认聚合（候选 A）**

- §9 Service（约第 361-363 行）：`results += self.industry_news_service.search_by_keyword(db, query, limit=page_size)`（无条件调用，默认聚合）
- §9 注释：`# M14 分支处理：默认聚合 M14 结果，不提供 include_global 参数（CY ack C-3，候选 A）`
- §15 决策记录 C-3：候选 A 默认聚合 M14
- **判断：✅ 真落地**

---

**C-4 M10 色块阈值 <30%/30-70%/>70%（候选 A）**

- §7（约第 355-365 行）：`COMPLETION_THRESHOLDS = {RED: 0.3, GREEN: 0.7}`
- 注释明确：`RED < 0.3 / YELLOW 0.3-0.7 / GREEN > 0.7`
- §15 决策记录 C-4：候选 A 严格 3 档
- **判断：✅ 真落地**

---

**C-5 M15 admin 语义 owner+editor（候选 β）**

- §8 权限三层（约第 437 行）：`Depends(check_project_access(project_id, roles=["owner", "editor"]))`（已改为 owner+editor，不用 "admin"）
- §6 Router（约第 327 行）：`Depends(check_project_access(project_id, roles=["owner", "editor"]))`
- §13 AppError：`message = "Only project owner or editor can view activity stream"`
- tests.md P2（第 79 行）：viewer 访问 → 403，P3：editor 正常 200
- §15 决策记录 C-5：候选 β（owner + editor）
- **判断：✅ 真落地**——主对话精修后 admin→owner+editor 已全链路修正

---

**C-6 M15 未知 action_type fallback UI（候选 C）**

- §7（约第 426-428 行）：
  > 未知 action_type（如新模块 accepted 后回写前的窗口期）：展示 `action_type` 字符串作为标题 + `metadata` 折叠可展开，不隐藏不显示 raw JSON（C-6 CY ack，候选 C fallback UI）
- §15 决策记录 C-6：候选 C fallback UI
- **判断：✅ 真落地**

---

### D 类 4 项（实现约定）

---

**D-1 M10 folder 迭代 bottom-up（非递归）**

- §3 folder 均值计算说明（约第 204-209 行）：
  > 实现方式：**迭代（bottom-up 后序遍历）**，非递归（CY ack D-1）。选迭代非递归：避免深层树栈溢出...推荐用 `collections.deque` 从叶节点向根节点逐级计算，或基于 M03 `node.path` 前缀排序
- **判断：✅ 真落地**

---

**D-2 M15 COUNT 首页精确后续 has_more**

- §3 DAO `list_stream`（约第 264-276 行）：
  ```python
  if (page - 1) == 0:
      total = q.count()  # 首页精确 total
  else:
      total = None  # 后续分页不计算精确 total（前端用 has_more 判断）
  ```
- §7 `ActivityStreamResponse`（约第 420 行）：`total: int | None  # 首页（offset=0）精确 total；后续分页为 None（D-2 CY ack）`
- **判断：✅ 真落地**

---

**D-3 M15 metadata 按 action_type switch**

- §7 前端渲染契约（约第 427 行）："前端按 action_type dispatch 到对应渲染器（switch-case）"
- **判断：✅ 真落地**（说明在文档中）

---

**D-4 M09 空 list 短路**

- §9 Service（约第 344-347 行）：
  ```python
  if not accessible_project_ids:
      return SearchResponse(items=[], total=0, page=page, page_size=page_size, query=query)
  ```
- 注释：`# D-4 短路处理：空白名单时直接返回（CY ack，M14 在此场景也跳过——无权限用户不返回 M14）`
- **判断：✅ 真落地**

---

### 22 条决策汇总

| 类别 | 总数 | ✅ 真落地 | ⚠️ 表面落地有瑕疵 | ❌ 虚假/漏改 |
|------|------|---------|----------------|------------|
| A 类 | 12 | 12 | 0 | 0 |
| C 类 | 6 | 6 | 0 | 0 |
| D 类 | 4 | 4 | 0 | 0 |
| **合计** | **22** | **22** | **0** | **0** |

**22/22 真落地（100%）**——决策落地率完整，不存在撒谎或漏改决策项。

---

## 3. 独立发现的新问题（5 类）

### 类 1：跨章节一致性

---

**NI-1（⚠️ Medium）M09 tests.md §7 覆盖率表仍写"DAO（search_dao）"——与无 DAO 设计矛盾**

路径：`M09-search/tests.md` §7（第 101 行）
```
| DAO（search_dao）| ≥ 95% | 含 tenant IN 过滤 + M14 豁免分支 + 每种 result_type 搜索方法 |
```

M09 设计已明确"M09 无 DAO 层"（design.md §6 第 232-234 行），Service 层直调上游 Service。但 tests.md §7 覆盖率表仍沿用 `search_dao` 称谓，且覆盖内容描述（"tenant IN 过滤 + 每种 result_type 搜索方法"）与实际 Service 调上游 Service 的测试对象不符。AI 实现时照抄会在无 DAO 文件上建测试文件，产生混乱。

此为 Fix v2 修掉 design.md 中 SearchDAO class 后、tests.md §7 未同步更新遗留的不一致。

**修复建议**：将 tests.md §7 DAO 行改为 Service 层测试说明（mock 各上游 Service）。

---

**NI-2（⚠️ Medium）M08 §9 DAO `delete_by_node` 接收外部 session 注释 vs §6 Service 签名 R-X3 要求不完全对齐**

路径：`M08-module-relation/00-design.md` §9（第 414-418 行）和 §6（第 290 行）

§9 DAO 草案 `delete_by_node()` 有注释：
```
"""供 M03 Service 层调用（R-X2 规则）。
R-X3：接受外部 db session，不调 self.db.begin() 另开事务——由调用方（M03 Service）统一管理事务边界。
"""
```

§6 Service 层说明（第 290 行）：
```
**对外契约（R-X3）**：`delete_by_node_id(db, node_id, project_id)` 供 M03 级联调用 / `batch_create_in_transaction(db, ...)` 供其他 orchestrator 调用——这些方法接受外部 db Session，不自开事务
```

问题：R-X3 要求 Service 方法（非 DAO 方法）接受外部 db session，但 §9 中的 DAO `delete_by_node()` 函数签名是 `(self, db: Session, node_id: UUID, project_id: UUID) -> int:`，而 §6 提到的 Service 签名 `delete_by_node_id(db, node_id, project_id)` 在 design.md 中**没有对应的 Service 层代码草案**——只有 DAO 层草案。

R-X3 规定 **Service** 方法接受外部 session，但文档只给了 DAO 层的实现，Service 层如何接受外部 db session 并传给 DAO 缺乏草案代码。这是 M08-B3 问题的部分修复——DAO 接受外部 session 是必要不充分条件。

**修复建议**：§6 或 §9 后补一段 Service 层 `delete_by_node_id` 草案，明确 Service 接受 `db: Session` 并传入 DAO。

---

**NI-3（⚠️ Low）M15 §3 ActivityLog model 中 `CheckConstraint target_type` 枚举值含 "relation" 但 §7 TargetType 枚举无此值**

路径：
- `M15-activity-stream/00-design.md` §3（第 183-186 行）：
  ```python
  CheckConstraint(
      "target_type IN ('node', 'dimension_record', 'version_record', 'competitor', "
      "'issue', 'relation', 'project', 'project_member', 'module_relation')",
  ```
- §7 `TargetType` Enum（第 370-380 行）：
  ```python
  class TargetType(str, Enum):
      node              = "node"
      dimension_record  = "dimension_record"
      version_record    = "version_record"
      competitor        = "competitor"
      issue             = "issue"
      relation          = "relation"
      project           = "project"
      project_member    = "project_member"
      module_relation   = "module_relation"
  ```

CheckConstraint 有 `'relation'`，§7 TargetType 也有 `relation = "relation"`——两者一致。**此处无问题**。但注意：M08 activity_log 第 10 节 target_type 使用 `module_relation`（非 `relation`），而 CheckConstraint 中两者都有（`'relation'` 和 `'module_relation'`）。

经仔细比对：§3 CheckConstraint 同时含 `'relation'` 和 `'module_relation'`，§7 TargetType 也同时含 `relation` 和 `module_relation`——**两者完全一致，无矛盾**。但 `relation` 和 `module_relation` 语义重叠，存在混淆风险（M08 §10 只用 `module_relation`，`relation` 来自哪个模块不明确）。

**判断：低风险观察项**——此枚举语义重叠需在后续回写时厘清，不构成当前 blocker。

---

**NI-4（✅ 已修复确认）M15 §8 admin 跨章节 admin 漏改情况**

主对话精修声称已修 M15 admin 为 owner+editor。独立核查：

- §8 Router 行（第 437 行）：`Depends(check_project_access(project_id, roles=["owner", "editor"]))` ✅
- §6 Router（第 327 行）：`Depends(check_project_access(project_id, roles=["owner", "editor"]))` ✅
- §13 AppError message（第 524 行）："Only project owner or editor can view activity stream" ✅
- tests.md P2（第 79 行）：viewer → 403 ACTIVITY_STREAM_FORBIDDEN ✅
- §9 防绕过纪律（第 459 行）："Router 的 project_id 来自 path 参数；Service 层二次校验用户真实是 owner 或 editor（C-5）" ✅

**判断：admin 跨章节漏改确已全部修复，主对话精修如实报告。**

---

### 类 2：跨文件一致性

---

**NI-5（⚠️ Medium）M09 tests.md §8 "跨模块 Read 聚合方案说明"第 120 行引用残留**

路径：`M09-search/tests.md` §9（第 118-121 行）：
```
- 跨模块搜索接口：待 ADR-003 决策后各模块补充 `search_by_keyword()` 接口定义
```

ADR-003 已于 2026-04-21 decided，各模块 Service 接口已在 M09 design.md §3 上游清单中列出，此行的"待 ADR-003 决策后"措辞是 Fix v1 前遗留的 ⚠️ 占位——Fix v2 没有更新 tests.md §9 关联说明。

R14-1 要求"tests.md 写完时所有决策已定，禁止 ⚠️ 渗漏"——虽然此行不是 ⚠️ 标记，但"待决策"的语义已是过时描述，会让实现者误以为 ADR-003 未定。

**修复建议**：将该行改为"ADR-003 规则 1 已决策（2026-04-21），M03/M04/M06/M07/M14 Service 接口定义见 README 基线补丁 TODO"。

---

**NI-6（⚠️ Low）4 模块 §14 测试大纲 vs tests.md 实际场景对照（部分轻微不对齐）**

- M08 design.md §14（第 581-584 行）大纲列"节点已被 M03 删除后创建关联"→ tests.md E8（第 43 行）有对应 ✅
- M09 design.md §14（第 471-476 行）大纲列"SQL 注入防护"→ tests.md E6（第 43 行）有对应 ✅
- M10 design.md §14（第 473-477 行）大纲列"节点只有 folder 无 file"→ tests.md E3（第 38 行）有对应 ✅
- M15 design.md §14（第 541-547 行）大纲列"viewer 访问（403）"→ tests.md P2（第 79 行）有对应 ✅

**总体：§14 大纲与 tests.md 场景基本对齐，无重大缺口。**

---

**NI-7（⚠️ Low）4 模块 tests.md frontmatter 均已有 `prism_ref` 字段**

核查：
- M08/tests.md frontmatter（第 7 行）：`prism_ref: F8` ✅
- M09/tests.md frontmatter（第 8 行）：`prism_ref: F9` ✅
- M10/tests.md frontmatter（第 7 行）：`prism_ref: F10` ✅
- M15/tests.md frontmatter（第 7 行）：`prism_ref: F15` ✅

Fix v1 报告称已修 prism_ref——独立核查确认全部已补。

---

### 类 3：虚假声明（自圆其说）

---

**NI-8（🔴 HIGH）M08 §5 "多表事务 ✅"但事务实现草案使用了不标准 API**

路径：`M08-module-relation/00-design.md` §5（第 267 行）
```
| **多表事务** | ✅ 必须 | Service 层 `with self.db.transaction():` 包：① INSERT module_relations ② log activity_log；任一失败回滚 |
```

问题：SQLAlchemy 没有 `self.db.transaction()` 方法。正确的 API 是：
- `with db.begin():` (SQLAlchemy core)
- 或 `db.begin_nested()` (嵌套)
- 或 Session 配合 `autocommit=False`（常见 FastAPI 模式）

README R-X3（第 193-195 行）的示例代码明确使用：
```python
def delete_by_node_id(self, db: Session, node_id: UUID, project_id: UUID) -> int:
    # 不调 self.db.begin()，直接用入参 db
```

M08 §5 写的 `self.db.transaction()` 不是合法 SQLAlchemy 调用，是自圆其说的虚假代码——文档声称"事务✅"，但草案 API 错误，会让 AI 实现时产生 AttributeError。

**严重度：HIGH（实现时会直接出 bug）**

---

**NI-9（⚠️ Medium）M09 §3 声称"无主表 R3-5"但 §15 checklist 第 3 行内容可能误引规则编号**

路径：`M09-search/00-design.md` §15 checklist（第 484 行）：
```
- [x] 节 3：无自有表声明（R3-5）+ 上游 Service 接口清单 + ADR-003 规则 1 引用 + M14 例外说明（不得误勾 R3-1 "SQLAlchemy class 代码块"）
```

README R3-5 规定：§15 checklist 第 3 行改为"§3：无自有表声明 + 上游清单 + DAO 草案 + ADR-003 规则 X 引用"，**不得**误勾"SQLAlchemy class 满足 R3-1"。

M09 §15 checklist 第 3 行正确引用了 R3-5，且括号内特别注明"不得误勾 R3-1"——格式合规。但 M09 无 DAO 层（无自有 DAO，由 Service 直调上游），R3-5 要求"DAO 草案代码块"在 M09 这种情况下如何理解？

核查 §3：M09 §3 没有提供独立的"DAO 草案代码块"——而是直接给了"搜索结果虚拟模型（无 DB 持久化，仅 Pydantic）"，Service 草案在 §9。这与 R3-5 第 3 条"DAO 草案代码块"要求存在轻微偏差（M09 无 DAO，§9 是 Service 草案而非 DAO 草案）。

**判断：⚠️ 轻微偏差**——M09 特殊性（无 DAO 层）需在 R3-5 规则或 §15 checklist 中显式说明"M09 无 DAO 层，§9 Service 草案代替 R3-5 第 3 条 DAO 草案"，否则后续模块设计者会混淆。

---

**NI-10（✅ 确认合规）M10 §3 ADR-003 规则 2 豁免声明 + "只读 import，禁止写入"一致性**

路径：M10 §3（第 130-131 行）：
```python
# ADR-003 规则 2 豁免：本 DAO 只读 import 上游 model，禁止 INSERT/UPDATE/DELETE
```

§6 禁止列（第 270 行）：
```
❌ OverviewDAO 执行 INSERT / UPDATE / DELETE（违反 ADR-003 规则 2 豁免边界——只读 import 豁免仅限只读查询，写入必须走各模块自己的 Service）
```

§15 checklist 第 3 行（第 487 行）：引用 R3-5 + ADR-003 规则 2，未误勾 R3-1。

**判断：✅ M10 ADR-003 合规，三处说明一致。**

---

### 类 4：ADR-003 合规性

---

**NI-11（✅ 合规）M09 已改为通过上游 Service 接口读取**

- §3 上游依赖表清单（第 113-121 行）：6 个上游表均通过 `XxxService.search_by_keyword(...)` 调用
- §6 DAO 层（第 232 行）：**M09 无 DAO 层**（显式声明）
- §9 Service 草案（第 340-367 行）：`self.node_service.search_by_keyword(...)` 等调用，无直接 `db.query(Node)` 调用
- 旧的 `SearchDAO` class 已删除（未在文件中找到）

**判断：✅ ADR-003 规则 1 合规，SearchDAO 已删**

---

**NI-12（✅ 合规）M10 §3 显式引用 ADR-003 规则 2 + 上游 model 清单**

- §3 开篇（第 112-114 行）：
  > **本模块无自有实体表，§3 适用纯读聚合规范（R3-5），采纳 ADR-003 规则 2：只读 import 上游 model 豁免。**
  > 引用：`adr/ADR-003-cross-module-read-strategy.md`
- 上游表清单（第 117-123 行）：4 张表均标注访问方式"ADR-003 规则 2 豁免"

**判断：✅ 合规**

---

**NI-13（✅ 合规）M15 §3 显式引用 ADR-003 规则 3 + 横切表清单**

- §3（第 116-120 行）：
  > **本模块无自有业务实体表，§3 适用纯读聚合规范（R3-5），采纳 ADR-003 规则 3：横切共享表消费模块豁免——直查横切表。**
  > 引用：`adr/ADR-003-cross-module-read-strategy.md`
- 横切表清单（第 134-139 行）：`activity_logs`（横切） + `users`（M01 只读 JOIN）+ `projects`（M02 只读）

**判断：✅ 合规**

---

**NI-14（⚠️ Low）4 模块 §15 checklist 第 3 行 R3-5 引用验证**

- M08 §15 checklist 第 3 行（第 592 行）："节 3：ER 图 + SQLAlchemy class + project_id 冗余 + 三重防护（R3-2）+ 候选 B 改回成本（R3-4）"——M08 有主表，适用 R3-1，未误勾 R3-5 ✅
- M09 §15 checklist 第 3 行（第 484 行）："节 3：无自有表声明（R3-5）+ ... 不得误勾 R3-1"✅
- M10 §15 checklist 第 3 行（第 487 行）："节 3：无自有表声明（R3-5）+ ... 不得误勾 R3-1"✅
- M15 §15 checklist 第 3 行（第 557 行）："节 3：无自有表声明（R3-5）+ ... 不得误勾 R3-1"✅

**判断：✅ 4 模块第 3 行 checklist 均正确引用**

---

### 类 5：README 新规则合规

---

**NI-15（🔴 HIGH）R-X3 合规：M08 Service 签名接受外部 db session 仅在 §6 文字说明，缺 Service 层代码草案**

路径：`M08-module-relation/00-design.md` §6（第 290 行）：
```
**对外契约（R-X3）**：`delete_by_node_id(db, node_id, project_id)` 供 M03 级联调用 / `batch_create_in_transaction(db, ...)` 供其他 orchestrator 调用——这些方法接受外部 db Session，不自开事务
```

README R-X3（第 196-208 行）要求：
```python
# ✅ 接受外部 session
def delete_by_node_id(self, db: Session, node_id: UUID, project_id: UUID) -> int:
    # 不调 self.db.begin()，直接用入参 db
    ...
```

M08 §9 DAO 的 `delete_by_node` 有正确的外部 session 参数，**但 Service 层没有提供对应的草案代码**——只有 §6 的文字说明"这些方法接受外部 db Session"，无实现代码草案。这使得 AI 实现者无法从文档中直接看到 Service 层如何将外部 session 传递给 DAO 并避免自开事务。

比较：M04 pilot 中，Service 的 `batch_create_in_transaction(db: Session, ...)` 是有实现草案的。M08 只有 DAO 草案缺 Service 草案，合规性存疑。

**严重度：HIGH**（与 NI-8 组合：§5 用了错误的 `self.db.transaction()`，§6 只有文字说明无草案——两处共同导致 M08 事务实现不可信）

---

**NI-16（✅ 合规）R10-1 M08 delete_by_node_id N 条独立事件**

路径：M08 §10（第 458 行）：
> **R10-1（批量操作 N 条独立事件）**：`delete_by_node_id` 调用时，若该节点有 N 条关联，则写 **N 条独立** `delete` 事件，每条 `target_id` = 对应的 `relation_id`，不得汇总为单条"批量删除 N 条"事件。N 条关联 → N 条独立 activity_log 记录。

**判断：✅ R10-1 合规**

---

**NI-17（✅ 合规）R10-2 M15 声明 activity_log 横切表 owner**

路径：M15 §3（第 122 行）：
> **M15 是 activity_log 横切表的 owner（R10-2）**——M15 负责 `ActivityLog` model / `ActionType` + `TargetType` schema / Alembic 迁移的统一维护。

**判断：✅ R10-2 合规**

---

**NI-18（⚠️ Medium）R-X4 合规：M09/M10/M15 §3 ADR-003 引用规则号码验证**

- M09 §3（第 106-108 行）：引用 ADR-003 规则 1 ✅
- M10 §3（第 112-114 行）：引用 ADR-003 规则 2 ✅
- M15 §3（第 116-118 行）：引用 ADR-003 规则 3 ✅

R-X4 要求"显式声明适用 ADR-003 的哪条规则，禁止默认走 DAO 直 JOIN 业务表（候选 C）"——3 模块均满足。

**判断：✅ R-X4 全部合规**

---

## 4. Blocker 清单

### 🔴 HIGH（必须修复才能 accept）

| ID | 模块 | 问题 | 涉及规则 |
|----|------|------|---------|
| **NI-8** | M08 | §5 事务实现写 `self.db.transaction()`——非法 SQLAlchemy API，AI 实现时直接 AttributeError | R-X3 / 实现可信性 |
| **NI-15** | M08 | §6 声明 Service 接受外部 db session 但无草案代码；§5 错误 API 使 R-X3 承诺无法验证 | R-X3 |

### 🟡 MEDIUM（建议修复，不阻塞 accept 但影响质量）

| ID | 模块 | 问题 |
|----|------|------|
| **NI-1** | M09 | tests.md §7 覆盖率表仍写"DAO（search_dao）"——与无 DAO 设计矛盾，实现者会建错测试 |
| **NI-2** | M08 | Service 层 `delete_by_node_id` 缺草案代码，仅靠 §6 文字声明无法让 AI 实现者知道 session 传递方式 |
| **NI-5** | M09 | tests.md §9 关联行残留"待 ADR-003 决策后"过时描述——ADR-003 已定 |

### 🟢 LOW（观察项，不阻塞）

| ID | 模块 | 问题 |
|----|------|------|
| **NI-3** | M15 | `relation` 和 `module_relation` 同时存在 TargetType 枚举中，语义重叠，后续回写时需厘清归属 |
| **NI-6** | All | §14 大纲 vs tests.md 场景轻微不对齐（均有对应，无缺口）|
| **NI-9** | M09 | §15 checklist R3-5 第 3 条"DAO 草案"在 M09 无 DAO 场景下需补充说明（Service 草案替代） |
| **NI-14** | M08 | `relation` vs `module_relation` TargetType 语义问题（同 NI-3） |

---

## 5. Suggestion 清单

| # | 模块 | 建议 | 优先级 |
|---|------|------|-------|
| S-1 | M08 | §5 事务实现将 `self.db.transaction()` 改为 `with db.begin():` 或注明"使用注入的外部 db session，无需 begin"（与 R-X3 配合）| HIGH |
| S-2 | M08 | §9 或 §6 后补 Service 层 `delete_by_node_id(self, db: Session, ...)` 草案代码，明确不调 `self.db.begin()`，直接用外部 db | HIGH |
| S-3 | M09 | tests.md §7 覆盖率表 DAO 行改为 Service 层测试说明（mock 各上游 Service） | MEDIUM |
| S-4 | M09 | tests.md §9 关联行去掉"待 ADR-003 决策后"措辞，改为"ADR-003 规则 1 已定" | MEDIUM |
| S-5 | M15 | 后续 ActionType/TargetType 回写时厘清 `relation`（哪个模块写入？）vs `module_relation`（M08）的语义边界 | LOW |
| S-6 | All | 4 模块 §15 checklist 三轮 reviewer audit 勾选格子：当前三轮 audit 格均未勾（设计如此，待 CY 最终 accept 时勾）——可在精修后统一处理 | LOW |

---

## 6. Fix v2 + 主对话精修 如实报告评估

### 评估维度

| 评估项 | 结论 |
|-------|------|
| **22 条决策落地** | **如实报告（真实）**——22/22 全部落地，无虚假声明 |
| **M09 SearchDAO 删除** | **如实报告**——SearchDAO 已不见于文件，Service 层直调上游 Service |
| **M15 admin 跨章节漏改** | **如实报告**——§8/§6/§13/tests.md 全部已改为 owner+editor |
| **M15 三重防护 CheckConstraint 补加** | **如实报告**——Mapped[ActionType]/Mapped[TargetType] + CheckConstraint 均已补 |
| **M15 ImmutableMixin 修复** | **如实报告**——已改为 ImmutableMixin，注释明确无 updated_at |
| **M15 @model_validator 补加** | **如实报告**——ActivityStreamFilter 已有 `@model_validator(mode='after') check_time_range` |
| **M10 model_rebuild() 补加** | **如实报告**——`NodeOverview.model_rebuild()` 已补（第 317 行） |
| **新引入问题** | **部分漏报**——NI-8（§5 `self.db.transaction()` 非法 API）和 NI-1（tests.md §7 DAO 称谓残留）是 Fix v2 引入或遗留的问题，fix Agent 未提及 |

### 最终评估

**Fix v2 + 主对话精修总体是如实报告（非撒谎），但存在 2 处漏报（NI-8 错误 API / NI-1 tests.md 遗留）**。

- 对于主要 blocker（M09 SearchDAO 矛盾、M15 admin 漏改、三重防护缺失、@model_validator 缺失）：**均如实修复且如实报告**
- 对于次要遗留（§5 事务 API 错误、tests.md DAO 行称谓）：**漏报**，fix Agent 自报告"无新问题"但实际有

---

## 7. 关键风险

1. **M08 事务实现不可信**（NI-8 + NI-15）：§5 中 `self.db.transaction()` 非法，§6 中 Service R-X3 承诺无草案支撑——这两条合起来使 M08 的核心多表事务（create + activity_log 双写）实现路径在文档中不可验证，AI 实现时必然出 bug。

2. **M09 tests.md 与 design 分离**（NI-1）：tests.md §7 还写"DAO（search_dao）"，会造成测试框架按错误路径建立，发现测试时再修改成本高于现在精修。

3. **M15 TargetType 语义语义重叠**（NI-3）：`relation` 和 `module_relation` 并存，后续各模块回写 M15 枚举时若无约定，可能出现"module_relation" type 的日志被前端当 `relation` 处理。

---

## 8. 建议主对话精修 Top 3

1. **M08 §5 + §9 精修事务实现**（NI-8 + NI-15）：将 `self.db.transaction()` 改为正确 SQLAlchemy 用法，并在 §9（或 §6 附近）补 Service 层 `delete_by_node_id` 草案代码，明确接受外部 `db: Session`。

2. **M09 tests.md §7 + §9 精修**（NI-1 + NI-5）：§7 覆盖率表 DAO 行改为 Service 层说明；§9 关联行去掉"待 ADR-003 决策"过时措辞。

3. **M08 → status 可接受、M09/M10/M15 → status 可接受（精修后）**：M08 精修 NI-8/NI-15 后可 accept；M09 精修 NI-1/NI-5 后可 accept；M10 和 M15 当前已可 accept。

---

*Verify 完成时间：2026-04-21*
*验证方法：独立读文件，不依赖 fix Agent 自报告，按 README 规则逐条核查*
