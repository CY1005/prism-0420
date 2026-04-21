---
title: M06 竞品参考 - 详细设计
status: draft
owner: CY
created: 2026-04-21
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
module_id: M06
prism_ref: F6
pilot: false
complexity: low
---

# M06 竞品参考 - 详细设计

**协作约定**：
- ✅ 已定稿节：直接采用（来自架构规约 + 4 维标注）
- ⚠️ **待 CY 裁决**：AI 推断，给候选 + 我的倾向 + 你裁决
- 🔗 关联到 A/B 档规约均给链接

---

## 1. 业务说明 + 职责边界

### 业务背景（引自 PRD / US）

根据 PRD Q3"内置产品评价能力"，竞品参考是围绕功能模块的结构化竞品对标能力。

**核心用户故事**：
- **US-B1.4**：作为编辑者，我想为功能项添加竞品参考（竞品名称 / 版本 / 功能覆盖 / 技术方案 / 优劣势），这样竞品信息结构化
- **US-A3.3**（间接）：作为项目管理员，我想选择多个竞品生成对比矩阵——M06 提供竞品数据，M12 消费

**设计背景（Prism ADR-011）**：竞品是项目级全局实体（`competitors` 表），确保名称统一、跨功能项复用；功能项级的对标信息在 `competitor_references` 表。

### In scope（M06 负责）

- **竞品实体 CRUD**（项目级）：在项目维度创建 / 编辑 / 删除竞品全局条目（名称 / 网站 / 描述）
- **功能项竞品对标录入**：在某个功能项下关联竞品 + 填写对标内容（覆盖度 / 技术方案 / 优劣势 / 竞品版本号）
- **功能项竞品参考列表展示**：档案页内竞品参考卡片列表
- **竞品全局列表**：项目设置页展示所有已录入竞品（复用时从列表选择）

### Out of scope（其他模块负责）

| 不做的事 | 归属模块 |
|---------|---------|
| 跨功能项竞品对比矩阵（横向对比多个功能项的竞品）| M12 |
| 需求分析中的竞品维度使用 | M13（读 M06 数据） |
| 行业动态关联到竞品 | M14 |

### 边界灰区（显式说明）

- **竞品实体归属**：`competitors` 是"项目级全局"，不是某个功能项私有；所以"竞品管理入口"应在项目设置页，而非档案页。但档案页内可直接创建新竞品并同时创建对标记录。⚠️ 待 CY 裁决（见节 15 Q3）。

---

## 2. 依赖模块图

```mermaid
flowchart LR
  M01[M01 用户] --> M06
  M02[M02 项目] --> M06
  M03[M03 模块树<br/>nodes 表] --> M06

  M06[M06 竞品参考] -.竞品数据.-> M12[M12 对比矩阵]
  M06 -.竞品数据.-> M13[M13 AI 需求分析]
  M06 -.事件.-> M15[M15 数据流转]
```

**前置依赖**：M01 → M02 → M03（M04 档案页是 M06 UI 入口，但数据层不依赖 M04）

**依赖契约**：
- M01：`current_user`（user_id）
- M02：`project_id`（tenant 根）
- M03：`nodes(node_id)` 含 project_id

---

## 3. 数据模型（SQLAlchemy + Alembic 要点）

### 两表设计（参考 Prism ADR-011，但字段重新命名）

**设计说明**：Prism 已确认两表设计（`competitors` 全局实体 + `competitor_references` 功能项级对标记录），prism-0420 沿用此决策但用 SQLAlchemy 重新定义，字段名遵循 snake_case 并补充 tenant 字段。

```python
# api/models/competitor.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from uuid import UUID as PyUUID, uuid4
from typing import Any
from .base import Base, TimestampMixin

class Competitor(Base, TimestampMixin):
    """项目级竞品全局实体（可被多个功能项引用）"""
    __tablename__ = "competitors"
    __table_args__ = (
        Index("ix_competitor_project", "project_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)            # 竞品名称（重命名自 Prism name）
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)       # 官网（重命名自 Prism website）
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    refs = relationship("CompetitorRef", back_populates="competitor", cascade="all, delete-orphan")


class CompetitorRef(Base, TimestampMixin):
    """功能项级竞品对标记录（重命名自 Prism competitor_references）"""
    __tablename__ = "competitor_refs"
    __table_args__ = (
        UniqueConstraint("node_id", "competitor_id", name="uq_competitor_ref_node_competitor"),
        Index("ix_competitor_ref_node_project", "node_id", "project_id"),
        Index("ix_competitor_ref_project", "project_id"),
        Index("ix_competitor_ref_competitor", "competitor_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    node_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    competitor_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)  # 冗余 tenant
    competitor_version: Mapped[str | None] = mapped_column(Text, nullable=True)   # 竞品版本号（重命名自 Prism version，避免与系统 version 混淆）
    feature_coverage: Mapped[str | None] = mapped_column(Text, nullable=True)     # 功能覆盖度描述
    tech_approach: Mapped[str | None] = mapped_column(Text, nullable=True)        # 技术方案（重命名自 Prism technicalApproach）
    pros_and_cons: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"pros": [...], "cons": [...]}
    created_by: Mapped[PyUUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    competitor = relationship("Competitor", back_populates="refs")
```

> ⚠️ **AI 推断，CY 复审必改**：
> - `competitor_references` 重命名为 `competitor_refs`（更短）；若 CY 倾向保留全称可改回
> - `display_name` 重命名自 `name`；`website_url` 重命名自 `website`；`tech_approach` 重命名自 `technicalApproach`
> - `competitor_version` 重命名自 `version`（防止与乐观锁 version 字段语义混淆）
> - `project_id` 冗余在 `competitor_refs` 上（见 Q1）

### ⚠️ 待 CY 裁决 Q1：competitor_refs 是否冗余 project_id

| 候选 | 优 | 劣 |
|------|----|----|
| **A: 不冗余** | 范式干净；project_id 通过 competitors 反查 | DAO 查询需 JOIN competitors |
| **B: 冗余 project_id**（推荐） | DAO 简单；跨 tenant 越权防护更直接 | 写时须与 competitor.project_id 一致 |

**我倾向 B**——保持全项目 DAO tenant 过滤策略一致。

### ER 图（候选 B）

```mermaid
erDiagram
    projects ||--o{ competitors : "1:N"
    projects ||--o{ competitor_refs : "1:N (冗余 tenant)"
    competitors ||--o{ competitor_refs : "1:N"
    nodes ||--o{ competitor_refs : "1:N"
    users ||--o{ competitor_refs : "created_by"
    users ||--o{ competitors : "created_by"
    activity_logs }o--|| competitor_refs : "target_id"

    competitors {
        uuid id PK
        uuid project_id FK
        string display_name
        string website_url
        string description
        uuid created_by FK
        timestamp created_at
        timestamp updated_at
    }

    competitor_refs {
        uuid id PK
        uuid node_id FK
        uuid competitor_id FK
        uuid project_id FK "冗余 tenant"
        string competitor_version
        string feature_coverage
        string tech_approach
        jsonb pros_and_cons
        uuid created_by FK
        timestamp created_at
        timestamp updated_at
    }
```

### Alembic 要点

- 唯一约束：`UNIQUE(node_id, competitor_id)`（同一功能项不重复关联同一竞品）
- 索引：
  - `(node_id, project_id)` 主查询（按功能项找对标记录）
  - `(project_id)` 竞品全局列表查询 + tenant 过滤
  - `(competitor_id)` 反向查询（某竞品被哪些功能项关联）

---

## 4. 状态机

M06 无 status 枚举实体。

`competitors` 和 `competitor_refs` 均无状态字段；竞品条目的生命周期是 active（存在）或 deleted（硬删除）。

显式声明（原则 4）：**M06 无状态实体**。

---

## 5. 多人架构 4 维必答

| 维度 | 答案 | 实现细节 |
|------|------|---------|
| **Tenant 隔离** | ✅ project_id | `competitors` 直接带 project_id；`competitor_refs` 冗余 project_id（候选 B） |
| **多表事务** | ❌ 不需要 | "新建竞品 + 同时创建对标记录"是两步操作，Service 层可包事务，但不是强依赖（可分两步）。⚠️ 待 CY 裁决 Q4 |
| **异步处理** | ❌ N/A | 全同步，用户手动录入 |
| **并发控制** | ❌ N/A | 05-module-catalog 标注无并发；竞品录入不是高频协同编辑场景 |

### 约束清单逐项检查

| 清单项 | M06 是否触发 | 实现 |
|-------|-------------|------|
| 1. activity_log | ✅ 触发（竞品创建/更新/删除 + 对标记录 CRUD）| 节 10 |
| 2. 乐观锁 version | ❌ 不触发（无并发场景）| N/A |
| 3. Queue payload tenant | ❌ 不触发（无 Queue）| N/A |
| 4. idempotency_key | ⚠️ 待裁决 | 节 11 |
| 5. DAO tenant 过滤 | ✅ 触发 | 节 9 |

---

## 6. 分层职责表

| 层 | M06 涉及文件 | 该层职责 |
|----|------------|---------|
| **Page** | `web/src/app/projects/[pid]/settings/page.tsx`（竞品全局管理）<br>`web/src/app/projects/[pid]/nodes/[nid]/page.tsx`（档案页竞品卡片）| SSR 渲染竞品列表 / 对标卡片 |
| **Component** | `web/src/components/business/competitor-list.tsx`<br>`web/src/components/business/competitor-ref-card.tsx`<br>`web/src/components/business/competitor-ref-form.tsx` | 竞品列表 / 对标卡片 / 新建表单 |
| **Server Action** | `web/src/actions/competitor.ts` | session 校验 / 参数校验 / fetch FastAPI |
| **Router** | `api/routers/competitor_router.py` | 路由定义 / `Depends(check_project_access)` / Pydantic 校验 |
| **Service** | `api/services/competitor_service.py` | 业务规则（竞品属于本项目校验）/ tenant 校验 / 写 activity_log |
| **DAO** | `api/dao/competitor_dao.py` | SQL 构建 + 强制 tenant 过滤 |
| **Model** | `api/models/competitor.py` | SQLAlchemy 模型 |
| **Schema** | `api/schemas/competitor_schema.py` | Pydantic 请求/响应 |

---

## 7. API 契约

### Endpoints

#### 竞品全局实体（项目级）

| 方法 | 路径 | 用途 | 入参 | 出参 |
|------|------|------|------|------|
| GET | `/api/projects/{project_id}/competitors` | 拉取项目所有竞品 | — | `CompetitorListResponse` |
| POST | `/api/projects/{project_id}/competitors` | 创建竞品全局条目 | `CompetitorCreate` | `CompetitorResponse` |
| PUT | `/api/projects/{project_id}/competitors/{competitor_id}` | 更新竞品信息 | `CompetitorUpdate` | `CompetitorResponse` |
| DELETE | `/api/projects/{project_id}/competitors/{competitor_id}` | 删除竞品（级联删所有对标记录）| — | 204 |

#### 功能项竞品对标记录

| 方法 | 路径 | 用途 | 入参 | 出参 |
|------|------|------|------|------|
| GET | `/api/projects/{project_id}/nodes/{node_id}/competitor-refs` | 拉取功能项所有对标记录 | — | `CompetitorRefListResponse` |
| POST | `/api/projects/{project_id}/nodes/{node_id}/competitor-refs` | 创建对标记录（关联已有竞品）| `CompetitorRefCreate` | `CompetitorRefResponse` |
| PUT | `/api/projects/{project_id}/nodes/{node_id}/competitor-refs/{ref_id}` | 更新对标内容 | `CompetitorRefUpdate` | `CompetitorRefResponse` |
| DELETE | `/api/projects/{project_id}/nodes/{node_id}/competitor-refs/{ref_id}` | 删除对标记录 | — | 204 |

### Pydantic schema 草案

```python
# api/schemas/competitor_schema.py

class ProsAndCons(BaseModel):
    pros: list[str] = []
    cons: list[str] = []

class CompetitorCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=128)
    website_url: str | None = Field(None, max_length=512)
    description: str | None = None

class CompetitorUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=128)
    website_url: str | None = None
    description: str | None = None

class CompetitorResponse(BaseModel):
    id: UUID
    project_id: UUID
    display_name: str
    website_url: str | None
    description: str | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

class CompetitorListResponse(BaseModel):
    items: list[CompetitorResponse]
    total: int

class CompetitorRefCreate(BaseModel):
    competitor_id: UUID                     # 必须是本项目内的竞品
    competitor_version: str | None = None
    feature_coverage: str | None = None
    tech_approach: str | None = None
    pros_and_cons: ProsAndCons | None = None

class CompetitorRefUpdate(BaseModel):
    competitor_version: str | None = None
    feature_coverage: str | None = None
    tech_approach: str | None = None
    pros_and_cons: ProsAndCons | None = None

class CompetitorRefResponse(BaseModel):
    id: UUID
    node_id: UUID
    competitor_id: UUID
    project_id: UUID
    display_name: str       # join 自 competitors.display_name
    competitor_version: str | None
    feature_coverage: str | None
    tech_approach: str | None
    pros_and_cons: ProsAndCons | None
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime

class CompetitorRefListResponse(BaseModel):
    items: list[CompetitorRefResponse]
    total: int
```

⚠️ **AI 推断，CY 复审必改**：
- `pros_and_cons` 是否用 `ProsAndCons` 强类型 vs `dict[str, list[str]]`——我倾向强类型

---

## 8. 权限三层防御

| 层 | 检查 | 实现 |
|----|------|------|
| **Server Action** | session 是否有效 | `getServerSession()`；无则 401 |
| **Router** | 用户对 project 权限 | GET 允许 viewer；POST/PUT/DELETE 要求 editor；`Depends(check_project_access(project_id, role))` |
| **Service** | 竞品/对标记录是否属于该 project | `_check_competitor_belongs_to_project(competitor_id, project_id)`；不属于抛 `NotFoundError` |

**M06 无异步路径**，三层即覆盖。

---

## 9. DAO tenant 过滤策略

```python
# api/dao/competitor_dao.py

class CompetitorDAO:
    def list_by_project(self, db: Session, project_id: UUID) -> list[Competitor]:
        return (
            db.query(Competitor)
            .filter(Competitor.project_id == project_id)   # ← tenant 过滤
            .order_by(Competitor.display_name.asc())
            .all()
        )

    def list_refs_by_node(self, db: Session, node_id: UUID, project_id: UUID) -> list[CompetitorRef]:
        return (
            db.query(CompetitorRef)
            .filter(
                CompetitorRef.node_id == node_id,
                CompetitorRef.project_id == project_id,    # ← tenant 过滤
            )
            .all()
        )
```

### 豁免清单

无——M06 所有查询均在 project tenant 边界内。

---

## 10. activity_log 事件清单

| action_type | target_type | target_id | summary | metadata |
|-------------|-------------|-----------|---------|----------|
| `create` | `competitor` | `<competitor_id>` | 新增竞品：{display_name} | `{project_id}` |
| `update` | `competitor` | `<competitor_id>` | 更新竞品：{display_name} | `{changed_fields}` |
| `delete` | `competitor` | `<competitor_id>` | 删除竞品：{display_name} | `{ref_count}` 关联对标记录数 |
| `create` | `competitor_ref` | `<ref_id>` | 创建对标：{node_name}×{competitor_name} | `{node_id, competitor_id}` |
| `update` | `competitor_ref` | `<ref_id>` | 更新对标：{node_name}×{competitor_name} | `{node_id, competitor_id, changed_fields}` |
| `delete` | `competitor_ref` | `<ref_id>` | 删除对标：{node_name}×{competitor_name} | `{node_id, competitor_id}` |

---

## 11. idempotency_key 适用操作

### ⚠️ 待 CY 裁决 Q2：是否需要幂等

| 候选 | 理由 | 我的倾向 |
|------|------|---------|
| **A: 全无（推荐）** | 竞品名称无唯一约束（可以有两个同名竞品，版本不同）；删除幂等天然成立；创建频次低 | ⭐ |
| **B: 竞品创建加 idempotency_key** | 防止网络重试创建重复竞品条目 | 业务上允许同名竞品（不同版本）；服务端无法判断是否"重复" |

**我倾向 A**——M06 无高风险幂等场景。

显式声明（清单 4）：**M06 无 idempotency_key 操作**。

---

## 12. Queue payload schema

**N/A**——M06 无异步处理，无 Queue 任务。

显式声明（清单 3）：**M06 不投递 Queue 任务**。

---

## 13. ErrorCode 新增清单

```python
# api/errors/codes.py 新增（模块 M06）

class ErrorCode(str, Enum):
    # 模块 M06
    COMPETITOR_NOT_FOUND = "COMPETITOR_NOT_FOUND"
    COMPETITOR_REF_NOT_FOUND = "COMPETITOR_REF_NOT_FOUND"
    COMPETITOR_REF_DUPLICATE = "COMPETITOR_REF_DUPLICATE"   # (node_id, competitor_id) 唯一约束
    COMPETITOR_CROSS_PROJECT = "COMPETITOR_CROSS_PROJECT"   # 引用了其他项目的竞品
```

```python
# api/errors/exceptions.py 新增

class CompetitorNotFoundError(NotFoundError):
    code = ErrorCode.COMPETITOR_NOT_FOUND
    message = "Competitor not found"

class CompetitorRefNotFoundError(NotFoundError):
    code = ErrorCode.COMPETITOR_REF_NOT_FOUND
    message = "Competitor reference not found"

class CompetitorRefDuplicateError(AppError):
    code = ErrorCode.COMPETITOR_REF_DUPLICATE
    http_status = 409
    message = "This competitor is already referenced for this node"

class CompetitorCrossProjectError(AppError):
    code = ErrorCode.COMPETITOR_CROSS_PROJECT
    http_status = 422
    message = "Cannot reference a competitor from another project"
```

---

## 14. 测试场景大纲

详见 [`tests.md`](./tests.md)

- **golden path**：创建竞品全局条目 / 创建对标记录 / 读取 / 更新 / 删除
- **边界**：竞品名为空 / 超长 / 引用不存在竞品 / 跨项目竞品引用 / 重复关联
- **并发**：无并发场景（05-catalog 标注❌）
- **tenant**：跨项目越权读竞品列表 / 越权写对标记录
- **权限**：viewer 写 / 未登录读
- **错误处理**：DB 唯一冲突 / 竞品不存在 / 跨项目竞品引用

---

## 15. 完成度判定 checklist + ⚠️ 待 CY 裁决项汇总

### Checklist

- [ ] 节 1：职责边界 in/out scope 完整（引 US-B1.4 / US-A3.3）
- [ ] 节 2：依赖图完整
- [ ] 节 3：数据模型 ER 图（两表）+ Alembic 要点 + ⚠️ project_id 冗余决策
- [ ] 节 4：无状态实体显式声明
- [ ] 节 5：4 维必答 + 5 项清单逐项
- [ ] 节 6：分层文件路径明确（两个页面入口）
- [ ] 节 7：所有 API endpoint（8 个）+ schema + ⚠️ pros_and_cons 类型决策
- [ ] 节 8：权限三层
- [ ] 节 9：DAO tenant 过滤 + 豁免清单（无）
- [ ] 节 10：activity_log 6 种事件
- [ ] 节 11：idempotency 显式 N/A
- [ ] 节 12：Queue 显式 N/A
- [ ] 节 13：ErrorCode 4 个新增
- [ ] 节 14：tests.md 完整
- [ ] 节 15：本 checklist 全勾过
- [ ] **🔴 第一轮 reviewer audit（完整性）通过**
- [ ] **🔴 第二轮 reviewer audit（边界场景）通过**
- [ ] **🔴 第三轮 reviewer audit（演进 / 模板可复用性）通过**
- [ ] CY 全文复审通过 → status 转 accepted

> ✅ 三轮 reviewer audit 已完成 2026-04-21（见 audit-report-batch1.md），但发现 8 条问题需 fix + CY 裁决，转 accepted 前还需 CY 复审。

### ⚠️ 待 CY 裁决项汇总

| # | 节 | 决策点 | 候选 | 我的倾向 |
|---|----|-------|------|---------|
| Q1 | 3 | competitor_refs 是否冗余 project_id | A 不冗余 / B 冗余 | **B** |
| Q2 | 11 | idempotency 范围 | A 全无 / B 竞品创建加 key | **A** |
| Q3 | 1 | 竞品创建入口：项目设置 vs 档案页直接新建 | A 只在设置页 / B 档案页可内联新建并关联 | **B**（用户体验更流畅） |
| Q4 | 5 | "新建竞品 + 同时创建对标"是否包一个事务 | A 两步独立操作 / B Service 层包事务 | **B**（原子性更好，避免竞品创建成功但对标失败） |

> ⚠️ **以上所有判断均为 AI 推断，CY 复审必改**

---

## 关联参考

- 上游：`design/00-architecture/04-layer-architecture.md` / `05-module-catalog.md` / `06-design-principles.md`
- 工程规约：`design/01-engineering/01-engineering-spec.md`
- Prism 对照：`/root/cy/prism/web/src/db/schema.ts`（competitors + competitorReferences，字段已重命名）
- 业务源：`/root/cy/prism/docs/product/feature-list-and-user-stories.md`（US-B1.4 / US-A3.3）
