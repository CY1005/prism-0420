---
title: M10 项目全景图 - 详细设计
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
module_id: M10
prism_ref: F10
pilot: false
complexity: medium
---

# M10 项目全景图 - 详细设计

> 纯读聚合模块——跨 M02/M03/M04 读，无自有写表（有选项添加缓存表，见 §3 决策点）。
> 业务节标注 ⚠️ 的项为 AI 推断，CY 复审必改。

---

## 1. 业务说明 + 职责边界

### 业务背景（引自 PRD / US）

**核心用户故事**：
- **US-C1.1**（`/root/cy/prism/docs/product/feature-list-and-user-stories.md`）：作为查看者，我想在项目全景图上看到所有模块的完善度色块，这样一眼知道哪些模块信息充分、哪些还缺。
- **PRD Q3**（`design/00-architecture/01-PRD.md`）：围绕"功能模块"组织——全景图是功能模块视角的汇总入口，让用户在不进入档案页的情况下掌握整体信息质量状态。
- **PRD Q3.1**：功能模块视角为进入项目后默认呈现（左侧模块树 + 右侧档案页）——全景图是这一默认视图的聚合摘要，位于 `/project/:id` 概览页。

**业务定位**：M10 是只读聚合视图。它以 M03 的 nodes 树为骨架，以 M02 的 dimension 配置为分母，以 M04 的 dimension_records 填充数量为分子，计算每个节点的"完善度"并以色块形式展示。

### In scope（M10 负责）

- **树形完善度展示**：按 M03 nodes 树结构，渲染每个节点的完善度色块（深色=高完善度，浅色/灰=低完善度）
- **完善度计算**：`completion_rate = 已填维度数 / 启用维度数`（启用维度数来自 M02 `project_dimension_configs`）
- **统计汇总**：项目整体完善度（所有节点均值）/ 已填完节点数 / 总节点数
- **节点列表读取**：基于 project_id 读取 M03 nodes 全树（含层级 / 排序 / path）
- **单节点完善度查询**：支持按 node_id 查单节点完善度（供 M04 档案页完善度进度条复用）

### Out of scope（其他模块负责）

| 不做的事 | 归属模块 |
|---------|---------|
| 节点 CRUD（增删改树结构）| M03 |
| 维度记录编辑 | M04 |
| 维度配置管理（启用/禁用）| M02 |
| 搜索（跨节点关键词）| M09 |
| 需求分析 AI | M13 |
| AI 快照生成 | M16 |

### 边界灰区（显式说明）

- **⚠️ 单 project vs 跨 project**（AI 推断，CY 复审必改）：US-C1.1 描述查看者在"项目全景图"看所有模块完善度——推断为单 project 视图（路径 `/project/:id`），不跨 project。候选：A 单 project（默认，US 语境），B 跨 project dashboard（需新设计）。AI 默认 A。
- **⚠️ 完善度计算分母**（AI 推断，CY 复审必改）：分母为该 project 启用的维度数（M02 `project_dimension_configs`），还是全局维度总数？推断：按 project 级配置——因为不同项目可能启用不同维度子集。候选：A 按 project 启用维度（默认），B 全局维度总数。AI 默认 A。
- **⚠️ folder 节点 vs file 节点**（AI 推断，CY 复审必改）：M03 中 folder 节点不直接绑定 dimension_records，file 节点才有。全景图对 folder 节点的完善度如何处理？推断：folder 节点显示其子节点均值完善度（汇总），file 节点显示自身完善度。候选：A 汇总均值（默认），B folder 节点不显示完善度（只显示 file 节点），C 统一显示 0%（简化）。AI 默认 A。
- **⚠️ 跨模块 Read 聚合方式**（待主对话决策是否起 ADR-003）：见 §3 核心决策点。

---

## 2. 依赖模块图

```mermaid
flowchart LR
  M01[M01 用户] --> M10
  M02[M02 项目<br/>project_dimension_configs<br/>启用维度配置] --> M10
  M03[M03 功能模块树<br/>nodes 树结构] --> M10
  M04[M04 档案页<br/>dimension_records<br/>已填数据] --> M10

  M10[M10 项目全景图<br/>纯读聚合]

  M10 -.只读出参.-> VIEWER[查看者前端<br/>树+色块渲染]
```

**前置依赖（必须先实现）**：M01 → M02 → M03 → M04

**依赖契约**（M10 假设上游提供）：
- M01：`current_user`（user_id / role）
- M02：`project_dimension_configs(project_id)` 返回启用维度列表（M10 用于计算分母）
- M03：`nodes(project_id)` 返回完整树（含 parent_id / depth / sort_order / path / type）
- M04：`dimension_records(project_id)` 返回该项目所有已填维度记录（M10 聚合分子）

**M10 对所有上游表仅执行只读操作，不写任何上游表。**

---

## 3. 数据模型（SQLAlchemy + Alembic 要点）

### 核心决策点 ⚠️（待主对话决策是否起 ADR-003）

M10 是纯读聚合模块，其数据全部来自 M02/M03/M04 跨表 JOIN。**跨模块 Read 聚合方式**直接影响 M10 的数据模型和实现复杂度，必须在主对话裁决后才能定稿。

**三种候选方案**：

| 方案 | 描述 | 优点 | 缺点 | 是否起 ADR-003 |
|------|------|------|------|---------------|
| **A. 实时 JOIN** | 每次请求时 M10 DAO 直接 JOIN nodes + project_dimension_configs + dimension_records | 数据实时准确；无缓存失效问题；无额外表 | 项目节点数多时查询慢（N+1 风险）；跨模块 JOIN 可能违反分层 | 否（M10 独立 DAO 直查） |
| **B. 缓存快照表** | 维护 `overview_cache` 表，由 M04 写入时触发异步更新或定时刷新 | 查询 O(1)；前端响应快 | 引入缓存失效逻辑；数据有延迟；M04 需要感知 M10 | 可选（缓存更新方式影响是否需要 ADR） |
| **C. ADR-003 Read Model 统一层** | 建立跨模块 Read Model 服务，M10/M09/M15 统一走 Read 层 | 全局一致；解耦 | 新增一层架构复杂度；需主对话出 ADR-003 决策 | 是 |

⚠️ **AI 推断，CY 复审必改**：AI 暂时以方案 A（实时 JOIN）为基线写后续节，因其最简单无副作用。若主对话决策选 B 或 C，§3/§6/§7/§9 需联动修改。

**候选 B/C 改回成本（R3-4）**：
- A→B：新增 1 张 `overview_cache` 表 + Alembic 迁移 2-3 步；M04 Service 需增 cache 更新调用（1 个模块联动）；历史数据需重建缓存（可脚本，可逆）
- A→C：起 ADR-003；新增 Read Model 层文件；M10/M09/M15 同步联动修改（3 个模块）；架构层面新增 1 层（影响分层架构文档）

---

### M10 无自有实体表（基线方案 A）

**M10 无自有实体表——只读上游**

M10 在方案 A 下不创建任何新表。完善度数据通过查询以下上游表计算得出：

| 上游表 | 归属模块 | M10 操作 | 用途 |
|--------|---------|---------|------|
| `nodes` | M03 主 | 只读（SELECT）| 获取项目节点树结构（骨架）|
| `project_dimension_configs` | M02 主 | 只读（SELECT）| 获取启用维度数（计算分母）|
| `dimension_records` | M04 主 | 只读（SELECT COUNT GROUP BY node_id）| 统计每节点已填维度数（计算分子）|
| `projects` | M02 主 | 只读（SELECT）| 校验 project 存在 + tenant 归属 |

### SQLAlchemy 视角（只读引用，无新 model 文件）

M10 不定义新的 SQLAlchemy model。DAO 层直接 import 并 query 上游模型：

```python
# api/dao/overview_dao.py
# M10 只读 DAO——引用上游模型，不定义新实体

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from uuid import UUID as PyUUID

from api.models.node import Node                                    # M03 模型
from api.models.project_dimension_config import ProjectDimensionConfig  # M02 模型
from api.models.dimension_record import DimensionRecord             # M04 模型


class OverviewDAO:
    """
    M10 只读 DAO。
    方案 A：实时 JOIN，不写任何表。
    ⚠️ 若主对话决策选方案 B/C，此 DAO 需联动重写。
    """

    def count_enabled_dimensions(self, db: Session, project_id: PyUUID) -> int:
        """返回项目启用维度数（全局分母，不区分节点类型）"""
        return (
            db.query(func.count(ProjectDimensionConfig.id))
            .filter(
                ProjectDimensionConfig.project_id == project_id,  # tenant 过滤
                ProjectDimensionConfig.enabled == True,
            )
            .scalar()
        ) or 0

    def list_nodes_with_fill_count(
        self, db: Session, project_id: PyUUID
    ) -> list[dict]:
        """
        返回项目所有节点 + 每节点已填维度数。
        一条 SQL：nodes LEFT JOIN dimension_records GROUP BY node_id。
        """
        rows = (
            db.query(
                Node.id,
                Node.parent_id,
                Node.name,
                Node.type,
                Node.depth,
                Node.sort_order,
                Node.path,
                func.count(DimensionRecord.id).label("filled_count"),
            )
            .outerjoin(
                DimensionRecord,
                and_(
                    DimensionRecord.node_id == Node.id,
                    DimensionRecord.project_id == project_id,  # tenant 过滤（冗余字段）
                ),
            )
            .filter(Node.project_id == project_id)             # tenant 过滤
            .group_by(Node.id)
            .order_by(Node.depth, Node.sort_order)
            .all()
        )
        return [row._asdict() for row in rows]
```

### Alembic 要点

- M10 方案 A：**无 Alembic 迁移**——不新增表，依赖上游已有表。
- 方案 B：需新增 `overview_cache` 表（待 CY 决策后补充）。

---

## 4. 状态机（无状态显式说明）

M10 无自有实体表，无状态字段，无状态机。

显式声明（按原则 4）：**M10 无状态实体**。

M10 是纯读聚合，每次请求返回当前时刻的聚合快照；完善度数值不持久化为状态，由查询实时计算得出（方案 A）。

---

## 5. 多人架构 4 维必答

按原则 5 + 约束清单逐项答（即使是"不涉及"也显式写）。

| 维度 | 答案 | 实现细节 |
|------|------|---------|
| **Tenant 隔离** | ✅ project_id | DAO 层所有 SELECT 强制带 `WHERE nodes.project_id = ?` / `WHERE project_dimension_configs.project_id = ?` / `WHERE dimension_records.project_id = ?`；Service 层校验 project 归属用户 |
| **多表事务** | ❌ N/A | M10 纯读，无写操作，无事务需求 |
| **异步处理** | ❌ N/A | M10 全同步 GET——全景图是用户即时浏览，无后台任务、无 Queue、无流式 |
| **并发控制** | ❌ N/A | M10 纯读，无并发写冲突场景。多用户同时读全景图不产生冲突 |

### 约束清单逐项检查（呼应 06-design-principles 的 5 项清单）

| 清单项 | M10 是否触发 | 实现 |
|-------|-------------|------|
| 1. activity_log（所有变更操作必须写）| ❌ 不触发——M10 纯读，无变更操作 | 节 10 显式说明 |
| 2. 乐观锁 version | ❌ 不触发——纯读无并发写 | N/A |
| 3. Queue payload tenant | ❌ 不触发——无 Queue | N/A |
| 4. idempotency_key | ❌ 不触发——纯读 GET | 节 11 显式说明 |
| 5. DAO tenant 过滤 | ✅ 触发——三张上游表均需 tenant 过滤 | 节 9 列具体 DAO 实现 |

---

## 6. 分层职责表（呼应 04-layer-architecture）

| 层 | M10 涉及文件 | 该层职责 |
|----|------------|---------|
| **Page** | `web/src/app/projects/[pid]/page.tsx` | SSR 渲染项目概览页；包含全景图树 + 完善度色块 + 统计数字；调 Server Action 拿全景图数据 |
| **Component** | `web/src/components/business/overview-tree.tsx`<br>`web/src/components/business/completion-badge.tsx` | 树形结构渲染 + 色块着色逻辑（根据 completion_rate 映射颜色）；folder 节点展开/折叠 |
| **Server Action** | `web/src/actions/overview.ts` | session 校验 / 调 FastAPI GET 全景图 |
| **Router** | `api/routers/overview_router.py` | 路由定义 / `Depends(check_project_access)` / Pydantic schema 出参；纯 GET，无写操作 |
| **Service** | `api/services/overview_service.py` | 聚合逻辑：调 DAO 拿 nodes + fill_count + enabled_count → 计算每节点 completion_rate → 计算 folder 节点汇总均值；tenant 二次校验 |
| **DAO** | `api/dao/overview_dao.py` | 只读 SQL：nodes + dimension_records JOIN + project_dimension_configs 查询；强制 tenant 过滤 |
| **Model** | 无新 model 文件——引用 M02/M03/M04 的 `node.py` / `project_dimension_config.py` / `dimension_record.py` | 上游 SQLAlchemy 模型复用 |
| **Schema** | `api/schemas/overview_schema.py` | Pydantic 响应 schema（OverviewResponse / NodeOverview / OverviewStats）|

**禁止**（呼应规约）：
- ❌ Router 直 `db.query(Node)` 跳过 Service
- ❌ OverviewDAO 内写任何 INSERT / UPDATE / DELETE
- ❌ Service 直接 import 其他 Service（应通过 DAO 读上游数据）

---

## 7. API 契约（Pydantic + OpenAPI 路径表）

### Endpoints

| 方法 | 路径 | 用途 | Pydantic 入参 | 出参 |
|------|------|------|--------------|------|
| GET | `/api/projects/{project_id}/overview` | 项目全景图（全树 + 完善度）| — | `OverviewResponse` |
| GET | `/api/projects/{project_id}/overview/stats` | 项目整体统计数字 | — | `OverviewStatsResponse` |
| GET | `/api/projects/{project_id}/nodes/{node_id}/completion` | 单节点完善度（M04 档案页复用）| — | `NodeCompletionResponse` |

### Pydantic schema 草案

```python
# api/schemas/overview_schema.py
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from enum import Enum


class NodeType(str, Enum):
    folder = "folder"
    file = "file"


class NodeOverview(BaseModel):
    """单节点完善度信息"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_id: UUID | None
    name: str
    type: NodeType
    depth: int
    sort_order: int
    path: str
    # 完善度字段
    filled_count: int            # 已填维度数（file 节点实际值；folder 节点为子树汇总）
    enabled_count: int           # 项目启用维度数（分母，全 project 一致）
    completion_rate: float       # 0.0 - 1.0
    # 子节点（嵌套展开，前端树渲染用）
    children: list["NodeOverview"] = []


class OverviewStats(BaseModel):
    """项目整体统计"""
    total_nodes: int             # 节点总数（含 folder + file）
    file_nodes: int              # file 节点数
    fully_complete_nodes: int    # completion_rate = 1.0 的 file 节点数
    empty_nodes: int             # completion_rate = 0.0 的 file 节点数
    avg_completion_rate: float   # 所有 file 节点均值
    enabled_dimension_count: int # 项目启用维度数


class OverviewResponse(BaseModel):
    """项目全景图完整响应"""
    project_id: UUID
    tree: list[NodeOverview]     # 顶层节点列表（含嵌套 children）
    stats: OverviewStats


class OverviewStatsResponse(BaseModel):
    """仅统计数字（轻量接口）"""
    project_id: UUID
    stats: OverviewStats


class NodeCompletionResponse(BaseModel):
    """单节点完善度（M04 档案页完善度进度条复用）"""
    node_id: UUID
    filled_count: int
    enabled_count: int
    completion_rate: float
```

**说明**：
- `NodeOverview.children` 嵌套结构由 Service 层在内存中组装（从 DAO flat list → 树形）
- ⚠️ 若节点数量极大（>1000），嵌套组装可能有性能问题——此为潜在优化点，初版不处理

---

## 8. 权限三层防御点（呼应 04-layer-architecture Q4）

| 层 | 检查 | 实现 |
|----|------|------|
| **Server Action** | session 是否有效 | `getServerSession()`；无则 401 |
| **Router** | 用户对 project 是否有 ≥ viewer 权限 | `Depends(check_project_access(project_id, role="viewer"))`；全景图查看者权限即可访问 |
| **Service** | project_id 是否真实存在 + 用户真实有权限访问 | `_check_project_access(user_id, project_id)`；project 不存在或用户不在成员表抛 NotFoundError |

**异步路径**：M10 无异步，三层即足够（无 Queue 消费者侧权限）。

---

## 9. DAO tenant 过滤策略（呼应原则 5 清单 5）

### 三张上游表 tenant 过滤规则

| 上游表 | 过滤条件 | 字段来源 |
|--------|---------|---------|
| `nodes` | `WHERE nodes.project_id = :project_id` | M03 nodes 直接带 project_id |
| `dimension_records` | `WHERE dimension_records.project_id = :project_id` | M04 冗余 project_id 字段（批量统一规则）|
| `project_dimension_configs` | `WHERE project_dimension_configs.project_id = :project_id` | M02 直接带 project_id |

### 豁免清单

无——M10 所有查询都在单 project 边界内。

### 防绕过纪律

- OverviewDAO 所有方法**强制带 project_id 入参**，DAO 内部不从外部推断 project_id
- Router 层 project_id 来自 path 参数，Service 层二次校验用户是否真实有权
- M10 DAO 不接受无 project_id 的查询入参

---

## 10. activity_log 事件清单（呼应清单 1）

**M10 无 activity_log 事件**。

理由：
- M10 纯读聚合，无任何写操作（INSERT / UPDATE / DELETE）
- 约束清单 1 规定"所有变更操作必须写 activity_log"——M10 无变更操作，豁免
- 用户浏览全景图的行为（page view）**不写 activity_log**（⚠️ AI 推断，CY 复审必改：若业务需要"谁查看了全景图"的审计追踪，需追加此事件；当前推断不需要）

---

## 11. idempotency_key 适用操作清单（呼应清单 4）

**M10 无 idempotency_key 操作**。

显式声明（按原则 5 清单 4 要求）：M10 全部为 GET 只读操作，天然幂等，无需 idempotency_key。

---

## 12. Queue payload schema（异步模块；同步 N/A）

**N/A**——M10 无异步处理，无 Queue 任务。

显式声明（按 §12 分支规则）：**M10 不投递 Queue 任务**。

---

## 13. ErrorCode 新增清单（呼应规约 7）

### 新增 ErrorCode（注册到 `api/errors/codes.py`）

```python
class ErrorCode(str, Enum):
    # ... 已有
    # 模块（M10）
    OVERVIEW_PROJECT_NOT_FOUND = "OVERVIEW_PROJECT_NOT_FOUND"    # project 不存在或无权限
    OVERVIEW_NODE_NOT_FOUND    = "OVERVIEW_NODE_NOT_FOUND"       # 单节点查询 node 不存在
    OVERVIEW_NO_DIMENSIONS     = "OVERVIEW_NO_DIMENSIONS"        # 项目未配置任何启用维度（分母=0，无法计算完善度）
```

### 新增 AppError 子类（`api/errors/exceptions.py`）

```python
class OverviewProjectNotFoundError(NotFoundError):
    code = ErrorCode.OVERVIEW_PROJECT_NOT_FOUND
    message = "Project not found or access denied"

class OverviewNodeNotFoundError(NotFoundError):
    code = ErrorCode.OVERVIEW_NODE_NOT_FOUND
    message = "Node not found in this project"

class OverviewNoDimensionsError(AppError):
    code = ErrorCode.OVERVIEW_NO_DIMENSIONS
    http_status = 422
    message = "Project has no enabled dimensions configured; completion rate cannot be calculated"
```

### 复用已有

- `PERMISSION_DENIED` / `UNAUTHENTICATED`——复用
- `NOT_FOUND`——上游表通用 404 复用；M10 特化为以上两个子类

---

## 14. 测试场景

详见独立文件：[`tests.md`](./tests.md)

主文档只列大纲：
- **golden path**：查询全景图树 + 统计 / 单节点完善度 / folder 节点汇总均值
- **边界**：空项目（无节点）/ 无启用维度 / 节点只有 folder 无 file / 所有节点完善度 0%
- **并发**：M10 纯读无并发场景（显式说明）
- **tenant**：跨项目越权读 / DAO 过滤覆盖
- **权限**：未登录读 / viewer 正常读 / 无成员读
- **错误处理**：project 不存在 / 无启用维度返回 422

---

## 15. 完成度判定 checklist + ⚠️ 待 CY 裁决项

### checklist

- [x] 节 1：职责边界 in/out scope 完整；引 PRD Q3 / Q3.1 / US-C1.1
- [x] 节 2：依赖图覆盖所有上游模块（M01/M02/M03/M04）
- [x] 节 3：无自有表显式声明；三候选方案给完整对比；改回成本量化（R3-4）；OverviewDAO 草案代码
- [x] 节 4：无状态实体显式声明（按原则 4 要求）
- [x] 节 5：4 维必答（含"不涉及"显式说明）；5 项清单逐项标注；⚠️ 不出现在 4 维表格（符合 R5-1）
- [x] 节 6：分层职责表完整（每层文件路径明确）
- [x] 节 7：3 个 API endpoint + Pydantic schema 草案（含枚举 NodeType）
- [x] 节 8：权限三层防御 + 异步路径声明（M10 无异步）
- [x] 节 9：三张上游表 tenant 过滤规则 + 豁免清单（无）
- [x] 节 10：activity_log 无事件显式说明
- [x] 节 11：idempotency 无显式声明
- [x] 节 12：Queue 显式 N/A
- [x] 节 13：3 个 ErrorCode + 对应 AppError 子类（R13-1 满足）
- [x] 节 14：tests.md 场景大纲
- [x] 节 15：⚠️ 待 CY 裁决项汇总表
- [ ] **🔴 第一轮 reviewer audit（完整性）通过**
- [ ] **🔴 第二轮 reviewer audit（边界场景）通过**
- [ ] **🔴 第三轮 reviewer audit（演进 / 模板可复用性）通过**
- [ ] CY 全文复审通过 → status 转 accepted

### ⚠️ 待 CY 裁决项汇总表

| # | 节 | 裁决点 | AI 推断默认值 | 候选 | 影响范围 |
|---|-----|-------|------------|------|---------|
| D1 | §1 | 全景图范围：单 project vs 跨 project | A 单 project | A 单 project / B 跨 project dashboard | 若选 B：需新增跨 project 聚合 API；路径变为 `/projects/overview` |
| D2 | §1 | 完善度分母：project 启用维度 vs 全局维度 | A project 启用维度 | A project 级配置 / B 全局维度总数 | 若选 B：DAO 不查 project_dimension_configs，改查 dimension_types 总数 |
| D3 | §1/§7 | folder 节点完善度：子树均值 vs 不显示 vs 显示 0% | A 子树均值 | A 汇总均值 / B 仅 file 节点展示 / C 统一 0% | 影响 Service 层组装逻辑 + 前端色块渲染规则 |
| D4 | §3 | 跨模块 Read 聚合方式 | A 实时 JOIN | A 实时 JOIN / B 缓存快照表 / C ADR-003 Read Model | **核心架构决策**：是否起 ADR-003；影响 §3/§6/§7/§9 |
| D5 | §10 | 是否记录"用户查看全景图"的 page view 事件 | 不记录 | 不记录 / 记录 view 事件 | 若记录：增加 activity_log `view` action_type + view 事件 ErrorCode |

---

## 关联参考

- 上游设计：
  - `design/00-architecture/01-PRD.md`（Q3 / Q3.1）
  - `design/00-architecture/04-layer-architecture.md`（5 层 / 三层权限）
  - `design/00-architecture/05-module-catalog.md`（M10 4 维标注）
  - `design/00-architecture/06-design-principles.md`（原则 5 + 5 项清单）
- Prism 对照参考：
  - `/root/cy/prism/web/src/db/schema.ts`（nodes / dimension_records / project_dimension_configs 现状）
  - `/root/cy/prism/docs/product/feature-list-and-user-stories.md`（US-C1.1）
- 相关模块设计：
  - `design/02-modules/M03-module-tree/00-design.md`（nodes 树结构，M10 读取来源）
  - `design/02-modules/M04-feature-archive/00-design.md`（dimension_records，M10 读取来源）
  - `design/02-modules/M02-project/00-design.md`（project_dimension_configs，完善度分母来源）
