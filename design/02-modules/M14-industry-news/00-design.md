---
title: M14 行业动态 - 详细设计
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
supersedes: []
superseded_by: null
last_reviewed_at: 2026-04-21
module_id: M14
prism_ref: F14
pilot: false
complexity: low
---

# M14 行业动态 - 详细设计

> **特殊说明**：M14 是全局共享数据模块，无 tenant 隔离（06-design-principles 清单 5 豁免条件：全局数据）。
> DAO 层 tenant 过滤执行全局豁免，但必须显式声明（见节 9）。

**协作约定**：
- ✅ 已定稿节：直接采用（4 维机械推导已确定）
- 🔗 关联到 A/B 档规约的均给链接

---

## 0. Frontmatter 快速索引

| 字段 | 值 |
|------|-----|
| 模块 | M14 行业动态 |
| PRD 关联 | F14（v0.2 - 能分析、能对比、能追踪） |
| 用户故事 | US-B2.4（编辑者录入动态并关联功能项） |
| 复杂度分层 | 🟢 低复杂度（全局数据 / 基础 CRUD） |
| 4 维 | Tenant ❌全局 / 事务 ❌ / 异步 ❌ / 并发 ❌ |
| 前端形态 | 信息流（列表卡片 + 关联功能项 tag） |
| 模板版本 | C 档 v1（基于 M04 pilot 模板） |

---

## 1. 职责边界（in scope / out of scope）

### In scope（M14 负责）

- **行业动态录入**：编辑者录入一条行业动态（标题 / 摘要 / 来源链接 / 发布日期 / 标签）（US-B2.4）
- **动态列表展示**：所有已登录用户查看全局动态信息流（时间倒序分页）
- **关联功能项**：将一条动态关联到一个或多个功能项 node（US-B2.4 "关联到具体功能项"）
- **动态删除**：录入者或管理员删除一条动态
- **动态编辑**：录入者或管理员修改已录入的动态内容

### Out of scope（其他模块负责）

| 不做的事 | 归属模块 |
|---------|---------|
| RSS / 第三方 API 自动抓取动态 | 本期不实现（`source_type` 枚举预留） |
| AI 自动分类 / 摘要生成 | 本期不实现（`source_type` 枚举预留） |
| 功能项信息录入 / CRUD | M03 / M04 |
| 操作日志展示（数据流转） | M15（消费 activity_log） |

### 边界灰区（显式说明）

#### 灰区 1：数据来源（CY 2026-04-21 ack）

**决策：本期仅手动录入**（CY 2026-04-21 ack）。
- `source_type='manual'` 强制约束（CHECK 约束）
- `rss` / `ai` 枚举值预留扩展，本期 service 层拒绝创建非 manual 的记录
- `source_type` 字段已加入 schema，避免后期 Alembic 迁移

#### 灰区 2：动态可见范围

**决策：全局可见（已登录即可读）**（CY 2026-04-21 ack）。所有已登录用户均可见，无项目隔离，与 06-design-principles 清单 5 全局豁免一致。

---

## 2. 依赖模块图（M? → M?）

```mermaid
flowchart LR
  M01[M01 用户<br/>登录态] --> M14
  M03[M03 功能模块树<br/>nodes 表] -.关联目标.-> M14

  M14[M14 行业动态<br/>全局共享] -.事件.-> M15[M15 数据流转<br/>消费 activity_log]

  subgraph 全局数据（无 tenant）
    M14
  end
```

**前置依赖（必须先实现）**：M01（用户鉴权）

**依赖契约（M14 假设上游提供）**：
- M01：`current_user` 可拿到 `user_id` + `role`
- M03：`nodes(node_id)` 存在校验（关联功能项时校验 node 存在，但不过滤 project）

**独立性说明**：M14 不依赖 M02 / M04，可独立实现（全局数据，无项目上下文）。

---

## 3. 数据模型（SQLAlchemy + Alembic 要点）

### 决策：本期仅 `source_type='manual'`（CY 2026-04-21 ack）

`rss` / `ai` 预留扩展，本期 service 层拒绝创建非 manual 的记录（`CHECK (source_type = 'manual')` 约束可在扩展时改）。

### ER 图

```mermaid
erDiagram
    users ||--o{ industry_news : "created_by"
    industry_news ||--o{ news_node_links : "1:N"
    nodes ||--o{ news_node_links : "1:N"
    activity_logs }o--|| industry_news : "target_id 关联"

    industry_news {
        uuid id PK
        string title "动态标题（最长 200 字）"
        text summary "摘要（可空）"
        string source_url "来源链接（可空）"
        date published_date "发布日期（可空）"
        string source_type "枚举：manual/rss/ai（本期只 manual，CHECK 约束）"
        string[] tags "标签数组（PG text[]）"
        uuid created_by FK
        uuid updated_by FK
        timestamp created_at
        timestamp updated_at
    }

    news_node_links {
        uuid id PK
        uuid news_id FK
        uuid node_id FK "关联的功能项 node"
        uuid linked_by FK
        timestamp linked_at
    }
```

### SQLAlchemy 模型

```python
# api/models/industry_news.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint, Index, Text, Date, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import String
from datetime import date, datetime
from uuid import UUID as PyUUID, uuid4
from .base import Base, TimestampMixin

class IndustryNews(Base, TimestampMixin):
    """行业动态全局实体（无 project_id —— M14 全局无 tenant）"""
    __tablename__ = "industry_news"
    __table_args__ = (
        # 注意：M14 全局数据，无 project_id 约束
        # 本期 source_type 只允许 manual；后期扩展 rss/ai 时修改此 CHECK 约束
        CheckConstraint("source_type = 'manual'", name="ck_industry_news_source_type_manual"),
        Index("ix_industry_news_created_at", "created_at"),
        Index("ix_industry_news_created_by", "created_by"),
        Index("ix_industry_news_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)           # 动态标题（最长 200 字）
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)   # 摘要（可空）
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # 来源链接（可空）
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 发布日期（可空）
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    # source_type 枚举：manual/rss/ai（本期只 manual，CHECK 约束限制；rss/ai 预留，service 层本期拒绝）
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)  # 标签数组（PG text[]）
    created_by: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    node_links = relationship("NewsNodeLink", back_populates="news", cascade="all, delete-orphan")


class NewsNodeLink(Base):
    """行业动态与功能项 node 的关联表"""
    __tablename__ = "news_node_links"
    __table_args__ = (
        UniqueConstraint("news_id", "node_id", name="uq_news_node_link"),
        Index("ix_news_node_link_node", "node_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    news_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("industry_news.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    linked_by: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(nullable=False)

    news = relationship("IndustryNews", back_populates="node_links")
```

### 表说明

| 表 | 归属模块 | M14 操作 |
|----|---------|---------|
| `industry_news` | **M14 主** | CRUD |
| `news_node_links` | **M14 主** | C/D（建立/解除关联） |
| `nodes` | M03 主 | 只读（校验 node 存在） |
| `activity_logs` | 横切 | W（每次 C/U/D 都写） |

### Alembic 要点

- `industry_news.source_type` 默认值 `'manual'`；CHECK 约束 `ck_industry_news_source_type_manual`（本期强制）
- `news_node_links` 唯一约束：`UNIQUE(news_id, node_id)`（防重复关联）
- 索引：
  - `(created_at DESC)` 时间倒序分页
  - `(created_by)` 用户录入历史
  - `(tags)` GIN 索引（数组检索）
  - `news_node_links.(node_id)` 反查某功能项的相关动态

---

## 4. 状态机（无状态 / 有状态显式说明）

### 决策：M14 无状态字段（CY 2026-04-21 ack 统一最小集）

**理由**：PRD 未定义"草稿/发布"区分；全局动态直接可见；避免过度设计。

**显式声明（按原则 4）**：**M14 无状态实体**

`industry_news` 和 `news_node_links` 均无 `status` 字段，无状态机。

---

## 5. 多人架构 4 维必答

按原则 5 + 约束清单逐项答。

| 维度 | 答案 | 实现细节 |
|------|------|---------|
| **Tenant 隔离** | ❌ 全局豁免 | industry_news 是全局共享数据；DAO 层**无** project_id 过滤；豁免显式声明（见节 9） |
| **多表事务** | ❌ N/A | M14 写操作仅单表（industry_news）或两表非原子（news_node_links 关联可独立重试）；不涉及必须原子的跨表写 |
| **异步处理** | ❌ N/A | M14 全同步——手动录入是即时 CRUD，无后台任务、无 Queue、无流式 |
| **并发控制** | ❌ N/A | 行业动态无多人同时编辑场景（全局信息流，录入者各管各的），无乐观锁需求 |

### 约束清单逐项检查（呼应 06-design-principles 的 5 项清单）

| 清单项 | M14 是否触发 | 实现 |
|-------|-------------|------|
| 1. activity_log | ✅ 触发（变更操作：创建/编辑/删除动态 + 建立/解除关联） | 见节 10 |
| 2. 乐观锁 version | ❌ 不触发（无并发编辑场景） | N/A |
| 3. Queue payload tenant | ❌ 不触发（无 Queue） | N/A |
| 4. idempotency_key | ❌ 不触发（CY ack 无幂等需求，见节 11） | N/A |
| 5. DAO tenant 过滤 | **豁免**（全局数据，06-design-principles 清单 5 豁免条件） | 节 9 显式声明豁免 |

---

## 6. 分层职责表（呼应 04-layer-architecture）

| 层 | M14 涉及文件 | 该层职责 |
|----|------------|---------|
| **Page** | `web/src/app/industry-news/page.tsx` | 渲染动态列表页 SSR；调 Server Action 拿初始数据 |
| **Component** | `web/src/components/business/news-card.tsx`<br>`web/src/components/business/news-form.tsx`<br>`web/src/components/business/node-link-picker.tsx` | 动态卡片 / 录入表单 / 关联功能项 picker |
| **Server Action** | `web/src/actions/industry-news.ts` | session 校验 / zod 入参校验 / fetch FastAPI |
| **Router** | `api/routers/industry_news_router.py` | 路由定义 / `Depends(get_current_user)` 读；写接口加 `Depends(require_authenticated)` / Pydantic schema 入参出参 |
| **Service** | `api/services/industry_news_service.py` | 业务规则 / node 存在校验 / 写操作权限校验（本人或管理员）/ 写 activity_log |
| **DAO** | `api/dao/industry_news_dao.py` | SQL 构建 + **全局查询（无 tenant 过滤，显式豁免注释）** |
| **Model** | `api/models/industry_news.py`<br>`api/models/news_node_link.py` | SQLAlchemy 模型（schema 真相源） |
| **Schema** | `api/schemas/industry_news_schema.py` | Pydantic 请求 / 响应 |

**权限统一**：Router 层已登录即可读；写接口（POST/PUT/DELETE）`Depends(require_authenticated)` 鉴权；删除/编辑在 Service 层再校验 `created_by == current_user.id OR is_admin`。

**禁止**（呼应分层原则）：
- ❌ Router 直 `db.query(IndustryNews)`
- ❌ DAO 内 `if news.source_type == 'rss': ...` 业务判断

---

## 7. API 契约（Pydantic + OpenAPI 路径表）

### Endpoints

| 方法 | 路径 | 用途 | Pydantic 入参 | 出参 |
|------|------|------|--------------|------|
| GET | `/api/news` | 动态列表（全局，分页） | `?page=&page_size=&tag=` | `NewsListResponse` |
| GET | `/api/news/{news_id}` | 动态详情 | — | `NewsResponse` |
| POST | `/api/news` | 创建动态 | `NewsCreate` | `NewsResponse` |
| PUT | `/api/news/{news_id}` | 更新动态 | `NewsUpdate` | `NewsResponse` |
| DELETE | `/api/news/{news_id}` | 删除动态 | — | 204 |
| POST | `/api/news/{news_id}/links` | 关联功能项 | `NewsNodeLinkCreate` | `NewsNodeLinkResponse` |
| DELETE | `/api/news/{news_id}/links/{node_id}` | 解除关联 | — | 204 |
| GET | `/api/nodes/{node_id}/news` | 某功能项的相关动态 | — | `NewsListResponse` |

### Pydantic schema 草案

```python
# api/schemas/industry_news_schema.py

class NewsCreate(BaseModel):
    title: str = Field(..., max_length=200)
    summary: str | None = None
    source_url: str | None = Field(None, description="URL 格式校验")
    published_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    # source_type 固定为 'manual'，不暴露给用户；service 层强制

class NewsUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    summary: str | None = None
    source_url: str | None = None
    published_date: date | None = None
    tags: list[str] | None = None

class NewsResponse(BaseModel):
    id: UUID
    title: str
    summary: str | None
    source_url: str | None
    published_date: date | None
    source_type: str
    tags: list[str]
    linked_nodes: list[NodeRef]    # join 关联功能项简要信息
    created_by: UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime

class NewsListResponse(BaseModel):
    items: list[NewsResponse]
    total: int
    page: int
    page_size: int

class NewsNodeLinkCreate(BaseModel):
    node_id: UUID

class NewsNodeLinkResponse(BaseModel):
    news_id: UUID
    node_id: UUID
    node_name: str    # join 出来
    linked_by: UUID
    linked_at: datetime
```

---

## 8. 权限三层防御点（呼应 04-layer-architecture Q4）

**决策：已登录即可写**（CY 2026-04-21 ack）。

| 层 | 检查 | 实现 |
|----|------|------|
| **Server Action** | session 是否有效 | `getServerSession()`；无则 401 |
| **Router** | 已登录即可读；写操作已登录即可 | `Depends(get_current_user)` 读；写接口同样只需 `Depends(get_current_user)`（无需 editor 角色，M14 全局数据无项目级角色）|
| **Service** | 删除/编辑：校验 `created_by == current_user.id` OR 平台管理员 | Service 层 `_check_news_owner_or_admin()` |

**异步路径**：M14 无异步，三层即足够。

---

## 9. DAO tenant 过滤策略（呼应原则 5 清单 5）

### 全局豁免显式声明

```python
# api/dao/industry_news_dao.py

class IndustryNewsDAO:
    """
    ⚠️ GLOBAL DATA — NO TENANT FILTER
    M14 行业动态是全局共享数据（见 06-design-principles.md 清单 5 豁免条件：全局数据）。
    本 DAO 所有查询均无 project_id / user_id 过滤（访问控制在 Service 层）。
    豁免理由：全局行业动态，所有已登录用户均可见。
    """

    def list_all(
        self, db: Session, page: int = 1, page_size: int = 20,
        tag: str | None = None
    ) -> tuple[list[IndustryNews], int]:
        q = db.query(IndustryNews)
        if tag:
            q = q.filter(IndustryNews.tags.contains([tag]))
        total = q.count()
        items = q.order_by(IndustryNews.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def get_one(self, db: Session, news_id: UUID) -> IndustryNews | None:
        # 全局数据，无 tenant 过滤
        return db.query(IndustryNews).filter(IndustryNews.id == news_id).first()
```

### 豁免清单

| 豁免项 | 理由 | 清单 5 豁免条件 |
|--------|------|----------------|
| `IndustryNewsDAO` 所有查询 | 全局共享数据，无 project_id 概念 | "全局数据：全局行业动态"（06-design-principles 清单 5） |

---

## 10. activity_log 事件清单（呼应清单 1）

### 决策：操作粒度 + metadata（CY 2026-04-21 ack 全模块统一）

**理由**：折中方案，metadata 留 hash/size 等扩展点供 M15/M13/M16 后续消费。

| action_type | target_type | target_id | summary | metadata |
|-------------|-------------|-----------|---------|----------|
| `create` | `industry_news` | `<news_id>` | 录入行业动态：{title} | `{source_type, tags_count}` |
| `update` | `industry_news` | `<news_id>` | 更新行业动态：{title} | `{updated_fields: [...]}` |
| `delete` | `industry_news` | `<news_id>` | 删除行业动态：{title} | `{title}` |
| `link` | `news_node_link` | `<news_id>` | 关联功能项：{node_name} | `{node_id}` |
| `unlink` | `news_node_link` | `<news_id>` | 解除关联：{node_name} | `{node_id}` |

**实现位置**：Service 层每个 C/U/D 操作后调 `self.activity.log(...)`（非事务——M14 无多表事务，activity_log 写失败不回滚主操作）。

---

## 11. idempotency_key 适用操作清单（呼应清单 4）

### 决策：本模块无 idempotency 需求（CY 2026-04-21 ack 全模块统一）

**理由**：CRUD 走乐观锁/DB 唯一约束已防；删除天然幂等。具体：
- 创建：`title` + `created_by` + `published_date` 组合无 DB 唯一约束（允许录入相同标题的不同动态）；重复提交风险可接受
- 删除：天然幂等（重复 DELETE 返回 204）
- 关联：`UNIQUE(news_id, node_id)` DB 约束防重

**显式声明（按原则 5 清单 4 要求）**：**M14 无 idempotency_key 操作**。

---

## 12. Queue payload schema（异步模块；同步 N/A）

**N/A**——M14 无异步处理，无 Queue 任务。

显式声明（按原则 5 清单 3 要求）：**M14 不投递 Queue 任务**。

> 若 CY 未来决定采用 RSS 自动拉取，需补充 arq Queue 任务设计（本期不在范围）。

---

## 13. ErrorCode 新增清单（呼应规约 7）

### 新增 ErrorCode（注册到 `api/errors/codes.py`）

```python
class ErrorCode(str, Enum):
    # ... 已有

    # M14 行业动态
    NEWS_NOT_FOUND = "NEWS_NOT_FOUND"
    NEWS_LINK_DUPLICATE = "NEWS_LINK_DUPLICATE"     # (news_id, node_id) 重复关联
    NEWS_LINK_NOT_FOUND = "NEWS_LINK_NOT_FOUND"
    NEWS_FORBIDDEN = "NEWS_FORBIDDEN"               # 非本人/非管理员尝试删除/编辑
```

### 新增 AppError 子类（`api/errors/exceptions.py`）

```python
class NewsNotFoundError(NotFoundError):
    code = ErrorCode.NEWS_NOT_FOUND
    message = "Industry news not found"

class NewsLinkDuplicateError(AppError):
    code = ErrorCode.NEWS_LINK_DUPLICATE
    http_status = 409
    message = "This node is already linked to the news"

class NewsLinkNotFoundError(NotFoundError):
    code = ErrorCode.NEWS_LINK_NOT_FOUND
    message = "News-node link not found"

class NewsForbiddenError(AppError):
    code = ErrorCode.NEWS_FORBIDDEN
    http_status = 403
    message = "Only the creator or platform admin can modify this news"
```

### 复用已有

- `UNAUTHENTICATED`——未登录
- `NOT_FOUND`——node_id 找不到时（关联时校验 node 存在）

---

## 14. 测试场景

详见独立文件：[`tests.md`](./tests.md)

主文档只列大纲：
- **golden path**：创建动态 / 列表读取 / 编辑 / 删除 / 关联功能项 / 解除关联
- **边界**：标题超长 / 空列表 / 无关联 node / 分页边界
- **并发**：M14 无乐观锁，仅测同时删除幂等
- **Tenant（全局豁免验证）**：确认所有已登录用户均可读全局列表；确认无 project 过滤
- **权限**：未登录读 / 非本人删除 / 平台管理员删除他人动态
- **错误处理**：重复关联 / node_id 不存在 / news_id 不存在

---

## 15. 完成度判定 checklist

定稿前必须全部勾过：

- [x] 节 1：职责边界 in/out scope 完整；数据来源决策已定（CY ack）
- [x] 节 2：依赖图覆盖所有上下游
- [x] 节 3：数据模型 ER 图 + SQLAlchemy class + Alembic 要点完整；source_type 字段预留 + 本期只 manual（CY ack）
- [x] 节 4：状态机无状态显式声明（CY ack）
- [x] 节 5：4 维必答 + 5 项清单逐项标注
- [x] 节 6：分层职责表完整（每层文件路径明确）；权限规则统一（已登录即可写）
- [x] 节 7：所有 API endpoint + Pydantic schema 列全
- [x] 节 8：权限三层防御；写权限粒度决策已定（CY ack）
- [x] 节 9：DAO 全局豁免显式声明（含注释代码示例）
- [x] 节 10：activity_log 事件清单 + 操作粒度+metadata（CY ack）
- [x] 节 11：idempotency 无（CY ack）
- [x] 节 12：Queue N/A 显式声明
- [x] 节 13：ErrorCode 新增清单
- [x] 节 14：tests.md 测试场景写完
- [x] 节 15：本 checklist 全勾过
- [ ] **🔴 第一轮 reviewer audit（完整性）通过**
- [ ] **🔴 第二轮 reviewer audit（边界场景）通过**
- [ ] **🔴 第三轮 reviewer audit（演进 / 模板可复用性）通过**
- [ ] CY 全文复审通过 → status 转 accepted

> ✅ 三轮 reviewer audit 已完成 2026-04-21（见 audit-report-batch1.md），但发现 7 条问题需 fix + CY 裁决，转 accepted 前还需 CY 复审。

---

## CY 决策记录（2026-04-21 批量统一）

| # | 节 | 决策点 | 决定 |
|---|----|-------|------|
| Q1 | 1 灰区 1 | 数据来源 | **A 手动录入**（`source_type='manual'`，rss/ai 预留） |
| Q2 | 1 灰区 2 | 动态可见范围 | **A 全局可见**（所有已登录用户） |
| Q3 | 3 | source_type 字段是否预留 | **A 预留**（本期 CHECK 约束限 manual，后期扩展改约束） |
| Q4 | 4 | status 字段 | **A 无状态**（统一最小集） |
| Q5 | 8 | 写权限粒度 | **A 已登录即可**（无项目 editor 要求，全局数据） |
| Q6 | 11 | idempotency 范围 | **A 无幂等**（统一） |

---

## 关联参考

- 上游设计：
  - `design/00-architecture/04-layer-architecture.md`（5 层 / 三层权限 / 事务边界）
  - `design/00-architecture/05-module-catalog.md`（4 维标注 / 全局无 tenant）
  - `design/00-architecture/06-design-principles.md`（原则 5 + 5 项清单 / 清单 5 豁免条件）
  - `design/00-architecture/07-capability-matrix.md`（M14 能力定位）
- 工程规约：
  - `design/01-engineering/01-engineering-spec.md` 规约 1 / 5 / 7 / 11 / 12
- 用户故事来源：
  - `feature-list-and-user-stories.md` US-B2.4（编辑者录入动态并关联功能项）
  - F14（v0.2 行业动态）
