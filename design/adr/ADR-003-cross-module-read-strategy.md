---
title: ADR-003 跨模块读取策略（聚合读模块 §3 规范 + 2 豁免规则）
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
supersedes: []
superseded_by: null
last_reviewed_at: 2026-04-21
related_modules: [M09, M10, M15, M18, 未来聚合读模块]
---

# ADR-003：跨模块读取策略

## Context（背景）

prism-0420 多个模块涉及"读多个上游模块数据做聚合"场景：
- **M09 全局搜索**：跨 M03 nodes / M04 dimension_records / M06 competitors / M07 issues / M14 industry_news / M08 module_relations 六模块聚合搜索
- **M10 项目全景图**：读 M02 project_dimension_configs（分母）+ M04 dimension_records（分子）+ M03 nodes（骨架）算完善度
- **M15 数据流转可视化**：读 activity_log 横切表展示操作时间线
- **M18 语义搜索**（待设计）：跨多模块 embedding 聚合

R-X1（ADR-001 精神）约束了"orchestrator 模块不直写跨模块表"（M17 教训），但**对"只读跨模块"场景没有明确规则**，导致：

**batch3 audit 实战抓出的 3 类问题**：
1. **M09 DAO 自相矛盾**（F1）：§3 候选 A 描述"各模块 Service 暴露 search 接口"，但 §9 DAO 草案直接 `db.query(Node)/db.query(Issue)`——跨模块 import model，实现路径与描述矛盾
2. **M10 R3-1 误勾**（F3）：§3 用 DAO 代码块代替 SQLAlchemy class 满足 R3-1，但 R3-1 原意是"有主表模块"——纯读聚合模块实际豁免
3. **M15 横切表语义冲突**（隐含）：activity_log 是全模块共享的横切表，M15 直查此表是"查账本"而非"跨模块读"——硬套 R-X1 会导致设计畸形（强制让 M02/M03/M04 各自提供"自己的日志接口"，M15 聚合时失去时间顺序的连贯性）

**痛点**：没有锚点决策，3 模块各自 ⚠️ 预警，reviewer 无法定稿，Fix v1 无法推进。

---

## Decision（决策）

**采纳候选 A 为基线 + 2 条豁免规则**。

### 核心规则（3 条）

#### 规则 1：聚合读模块通过上游 Service 接口读取（主规则）

聚合读模块（M09 搜索 / M18 语义搜索 / 未来类似模块）的 Service 层**必须通过调用上游模块的 Service 接口**获取数据，不得在自己的 DAO 层直接 `db.query(上游 Model)`。

上游模块需要为聚合读场景**显式暴露接口**，命名规范：
- 搜索类：`search_by_keyword(query: str, project_id: UUID, limit: int) -> list[...]`
- 列表类：`list_by_xxx(project_id: UUID, filters: ...) -> list[...]`
- 详情类：`get_by_id(xxx_id: UUID, project_id: UUID) -> ...`

**示例**（M09 搜索）：

```python
# ❌ 错误：M09 DAO 直 import 上游 model
class SearchDAO:
    def search(self, db, query, project_id):
        nodes = db.query(Node).filter(...)     # 违反 R-X1 精神
        dims = db.query(DimensionRecord).filter(...)
        ...

# ✅ 正确：M09 Service 调上游 Service
class SearchService:
    def search(self, db, query, project_id, user_id):
        results = []
        results += self.node_service.search_by_keyword(db, query, project_id)
        results += self.dimension_service.search_by_keyword(db, query, project_id)
        results += self.competitor_service.search_by_keyword(db, query, project_id)
        # ...
        return self._merge_and_rank(results)
```

**改动要求**：M03/M04/M06/M07/M14 各自在 Service 层新增 `search_by_keyword` 方法（本 ADR accepted 后，各模块设计文档需追加此方法签名；已 accepted 模块走"基线补丁"列入 TODO）。

#### 规则 2：M10 型"聚合计算"豁免 —— 只读 import 上游 model

适用条件（必须全部满足）：
- 模块定位是"基于多个上游表做**计算/聚合**"（如完善度比率、统计报表），而非"搜索/列表展示"
- 查询逻辑用 SQL JOIN + GROUP BY 等方式在 DB 层聚合，**无法自然拆解为"每个上游提供一个 list 接口"**（强拆会产生"M04 专为 M10 造一个接口"的畸形设计）

豁免内容：
- 聚合读 DAO 可以 `from api.models.xxx import Xxx` **只读 import 上游 SQLAlchemy model**，执行 `db.query(Xxx).join(...)` 等只读查询
- **严禁**在聚合读 DAO 中执行 INSERT / UPDATE / DELETE（写入必须走各模块自己的 Service）

**示例**（M10 全景图）：

```python
# ✅ M10 豁免：只读 import + JOIN 查询
class OverviewDAO:
    def list_nodes_with_fill_count(self, db, project_id):
        # 只读 import Node / ProjectDimensionConfig / DimensionRecord
        return (
            db.query(
                Node.id, Node.name, Node.parent_id,
                func.count(DimensionRecord.id).label("filled_count"),
            )
            .outerjoin(DimensionRecord, DimensionRecord.node_id == Node.id)
            .filter(Node.project_id == project_id)
            .group_by(Node.id)
            .all()
        )

# ❌ 禁止：同一个 DAO 里混写入
class OverviewDAO:
    def update_something(self, db, ...):  # 违反豁免边界
        db.execute(update(...))
```

**文档要求**：采用本豁免的模块 §3 必须显式声明"适用 ADR-003 规则 2：只读 import 豁免"，并列出所有只读 import 的上游 model 清单。

#### 规则 3：横切共享表消费模块豁免 —— 直查横切表

适用条件：
- 被消费的表是"全项目/全模块共享的横切表"（当前唯一：`activity_log`；未来若新增则在本 ADR 扩展清单）
- 横切表**不归属任何单一业务模块**（由专门模块 own 治理——见 README R10-2）
- 消费模块的核心职责就是"展示该横切表内容"（M15）

豁免内容：
- 消费模块 DAO 可以直接 `db.query(activity_log)` 查询和过滤，**不需要**通过调"各业务模块的日志接口"
- 保留时间顺序的连贯性（横切表的核心价值就是按时间连起来审计）

**示例**（M15 数据流转）：

```python
# ✅ M15 豁免：直查 activity_log 横切表
class ActivityStreamDAO:
    def list_by_project(self, db, project_id, filters):
        return (
            db.query(ActivityLog)
            .filter(ActivityLog.project_id == project_id)
            .filter(...)   # 按 user_id / action_type / created_at 过滤
            .order_by(ActivityLog.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
            .all()
        )
```

**文档要求**：采用本豁免的模块 §3 必须显式声明"适用 ADR-003 规则 3：横切共享表豁免"，并列出所消费的横切表名。

---

#### 规则 4：embedding/索引派生模块的批量 backfill 豁免（M18 baseline-patch 引入，2026-04-26）

适用条件（**必须全部满足**）：
- 模块定位是"为业务表生成派生索引数据"（embedding / 全文索引 / 物化统计），而非"展示业务内容"
- 单条增量必须走规则 1（保持分层），但批量回填的性能要求使规则 1 不可行（示例：5 万条调 5 万次上游 Service 接口，本项目场景下 ≥ 1 小时不可接受）
- 仅做 **只读 SELECT**（含 LEFT JOIN），禁止 UPDATE / DELETE

豁免内容：
- backfill DAO 可以 `from api.models.xxx import Xxx` 只读 import 上游 SQLAlchemy model
- 跑 LEFT JOIN 自有表（embeddings 等）+ WHERE project_id 等批量 SELECT
- **严禁** 在豁免 DAO 中执行 INSERT / UPDATE / DELETE 上游表

使用边界（CY 决策 1，2026-04-25）：
- **仅 backfill 路径走规则 4**，其他所有场景（含增量单条 / search 关键词路径）仍走规则 1
- 不允许"backfill 顺手做点修复 UPDATE"——若需修复必须独立 cron + 调上游 Service.update

与规则 2 的边界：
- 规则 2 = "DB 层聚合计算"（M10 完善度统计，使用 GROUP BY / aggregate 函数）
- 规则 4 = "派生索引批量构建"（M18 backfill，使用 LEFT JOIN 找差异）
- 两者不重叠，避免规则 2 边界稀释

**示例**（M18 backfill）：

```python
# ✅ 规则 4 豁免：embedding backfill DAO 只读 import + LEFT JOIN
from api.models.nodes import Node            # 只读 import 上游 model
class EmbeddingBackfillDAO:
    def list_pending_node_ids(self, db, project_id, provider, model_name, model_version, limit):
        return (
            db.query(Node.id, Node.name)
            .outerjoin(
                Embedding,
                (Embedding.target_type == "node")
                & (Embedding.target_id == Node.id)
                & (Embedding.provider == provider)
                & (Embedding.model_name == model_name)
                & (Embedding.model_version == model_version),
            )
            .filter(Node.project_id == project_id)
            .filter(Embedding.target_id.is_(None))
            .limit(limit)
            .all()
        )
```

**文档要求**：
- 采用规则 4 的模块 §3 必须显式声明"适用 ADR-003 规则 4：embedding/索引专用豁免"
- 列出所有只读 import 的上游 model 清单
- §6 分层职责表必须把"增量 DAO（规则 1）"和"backfill DAO（规则 4）"分文件

---

### 对 M09 / M10 / M15 / M18 的具体应用

| 模块 | 适用规则 | 实施要求 |
|------|---------|---------|
| M09 全局搜索 | **规则 1**（主规则）| Service 层调上游 Service.search_by_keyword；M14 例外见下。**注**：M09 已 superseded by M18（2026-04-26），保留接口体系供 M18 增量路径复用 |
| M10 全景图 | **规则 2**（只读 import 豁免）| DAO 只读 import M02/M03/M04 model 做 JOIN 聚合，禁止写入 |
| M15 数据流转 | **规则 3**（横切表豁免）| DAO 直查 activity_log，无需调各模块"日志接口" |
| M18 语义搜索 | **双路：规则 1 增量 + 规则 4 backfill**（M18 baseline-patch 2026-04-26）| 增量 worker 调上游 `Service.get_for_embedding(target_id, project_id)` 走规则 1；backfill DAO 只读 import M03/M04/M06/M07 跑 LEFT JOIN 走规则 4 |

### M09 + M14 的接口签名例外（规则 1 的唯一例外）

M14 行业动态是**全局无 project_id 模块**（catalog Tenant ❌），其 `search_by_keyword` 接口签名与其他 5 模块不一致：

```python
# 其他 5 模块统一签名
def search_by_keyword(query: str, project_id: UUID, limit: int) -> list[...]:
    ...

# M14 签名例外（无 project_id）
def search_by_keyword(query: str, limit: int) -> list[...]:
    ...
```

M09 Service 层在聚合时对 M14 调用做分支处理：

```python
results += self.industry_news_service.search_by_keyword(db, query, limit)  # M14 无 project_id
results += self.competitor_service.search_by_keyword(db, query, project_id, limit)  # 其他模块
```

**此例外仅限 M14**——未来若新增全局无 project_id 模块需在本 ADR 扩展例外清单。

---

## Consequences（后果）

### 正面

- **M09 DAO 矛盾解除**：Fix v1 可以按规则 1 落地 `SearchService` 调上游 Service，`SearchDAO` 消失（M09 无主表无自有 DAO）
- **M10 R3-1 误勾修正**：按规则 2 显式声明"只读 import 豁免"，§15 checklist 正确勾选
- **M15 设计合理性确认**：按规则 3 横切表豁免，无需造 6 个"日志接口"
- **未来模块有明确基线**：新增聚合读模块必须在 §3 引用本 ADR 声明采纳哪条规则
- **上游模块 Service 接口沉淀**：M03/M04/M06/M07/M14 补完 `search_by_keyword` 后，未来任何新搜索场景可直接复用

### 负面

- **上游模块追加接口开发量**：5 个模块各自需实现 `search_by_keyword`（已 accepted 模块列入基线补丁 TODO）
- **聚合读延迟略高**：调 Service 比直 JOIN 多一层抽象，但本项目数据量下差异 < 10ms 可忽略
- **豁免规则理解成本**：新人读 R-X1 + ADR-003 要消化"写禁跨模块 / 读分四类（主规则+3豁免）"的规则层次（M18 baseline-patch 加规则 4 后从 3 类升 4 类）
- **M18 规则 4 引入双 DAO 维护成本**：embedding 模块需维护两套 DAO（增量走规则 1 / backfill 走规则 4），照抄子模板的 future embedding 模块同样负担

### 演进退路

- **派生索引模块超过 3 个时**抽公共 backfill 框架（M18 baseline-patch 引入规则 4 时 ack）：当前仅 M18 单实例，半年回看（2026-10-25）若新增 ≥ 2 个 embedding/索引模块，评估抽 `BaseBackfillDAO` 公共框架收敛 LEFT JOIN 模式
- 若未来数据量增长到规则 1 的 "6 次 Service 调用"性能不足（当前单 project 数据量下无此问题），可扩展 **规则 5：物化视图**（注：原稿这里的"规则 4"被 M18 baseline-patch 抢占，物化视图退路升 5）——
  - 建 `search_index` 物化视图聚合所有可搜索字段
  - 上游写入时 trigger 刷新，或定时 REFRESH CONCURRENTLY
  - **现阶段不引入**，避免维护成本 vs 收益失衡

---

## Alternatives（备选方案）

### A. 主规则（采纳）

**优势**：符合 R-X1 精神；数据实时一致；接口可复用；与 M08 已有 `search_by_keyword` 草案一致

**劣势**：前期 5 模块开发量；多次 Service 调用的分散延迟

### B. 物化视图统一搜索表

**优势**：性能最好；DAO 层简单

**劣势**：
- **"边改边搜"场景（CY 核心用法）体验恶化**——刚改的数据要等刷新后才可搜，用户困惑
- REFRESH 策略复杂（实时 trigger vs 定时）
- schema 变更需同步视图定义，未来加模块要改同步逻辑
- 对本期单用户 / 小数据量场景过度设计

**拒绝理由**：实时一致性 vs 性能的 trade-off 在本项目中前者远重于后者；演进到超大数据量时再考虑

### C. DAO 直 JOIN 业务表

**劣势**：违反 R-X1 精神（跨模块直读破坏分层隔离）；未来模块 schema 变更会级联破坏聚合读模块

**拒绝理由**：基线原则冲突，明确否决

---

## 引用方

- `design/02-modules/M09-search/00-design.md`（本 ADR 核心受众，规则 1）
- `design/02-modules/M10-overview/00-design.md`（规则 2 豁免）
- `design/02-modules/M15-activity-stream/00-design.md`（规则 3 豁免）
- `design/02-modules/M18-semantic-search/00-design.md`（accepted 2026-04-26，适用 **规则 1（增量）+ 规则 4（backfill）双路**——M18 baseline-patch 引入规则 4）
- **基线补丁 TODO**：M03/M04/M06/M07/M14 已 accepted 模块需追加 `search_by_keyword` Service 接口设计——见 `design/02-modules/README.md` 末尾 TODO

## 关联

- `design/adr/ADR-001-shadow-prism.md`（R-X1 分层原则起源）
- `design/adr/ADR-002-queue-consumer-tenant-permission.md`（另一条横切决策范式）
- `design/02-modules/README.md` R-X1（跨模块写约束）/ R3-5 纯读聚合 §3 规范 / R10-2 activity_log 归属
- `design/02-modules/audit-report-batch3.md` T3（本 ADR 推动理由）
