"""M14 行业动态 SQLAlchemy 模型（design/02-modules/M14-industry-news/00-design.md §3）。

2 表：
- industry_news（**全局共享 / 无 project_id**——design §9 + 06-design-principles 清单 5 全局豁免）
- news_node_links（与 nodes 1:N 关联表）

# 全局豁免（design §1 灰区 2 + §9 + 06-design-principles 清单 5）：
# industry_news 无 project_id 字段；DAO 层无 tenant 过滤；所有已登录用户均可读。
# 关联跨项目 node 允许（design §1 灰区 2 ack）—— 全局动态可关联任意 node，仅校验 node 存在。

# source_type 三重防护（design §1 灰区 1 + §3 + R3-2）：
# Mapped[str] + Text + CheckConstraint(source_type='manual')；本期仅 manual，
# rss/ai 预留扩展走 Alembic ALTER CHECK。

# Node back_populates 策略（与 M08 module_relation 同款）：
# design §3 SQLAlchemy block 无 Node 端反向 relationship 字面要求；FK ondelete=CASCADE
# DB 兜底已足够（node 删除时 news_node_links 行自动级联删）。不加 Node.news_node_links
# 避免双向耦合（M14 全局 / Node 项目级，语义混淆）。
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.models.base import Base, TimestampMixin


class IndustryNews(Base, TimestampMixin):
    """industry_news 表（design §3 SQLAlchemy block）。

    R3-1：含完整 SQLAlchemy class
    R3-2：source_type 三重防护（Text + CheckConstraint + Mapped[str]）
    R3-3：**无 project_id**——全局豁免显式（design §9 + 06-design-principles 清单 5）
    R10-1：单条写不批量；create / update / delete 各 1 条 activity_log
    """

    __tablename__ = "industry_news"
    __table_args__ = (
        # 本期仅 manual；后期扩展 rss/ai 走 Alembic ALTER CHECK（design §1 灰区 1）
        CheckConstraint(
            "source_type = 'manual'",
            name="ck_industry_news_source_type_manual",
        ),
        Index("ix_industry_news_created_at", "created_at"),
        Index("ix_industry_news_created_by", "created_by"),
        Index("ix_industry_news_tags", "tags", postgresql_using="gin"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    created_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    updated_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    node_links: Mapped[list[NewsNodeLink]] = relationship(
        "NewsNodeLink",
        back_populates="news",
        cascade="all, delete-orphan",
    )


class NewsNodeLink(Base):
    """news_node_links 表（design §3 SQLAlchemy block）。

    UNIQUE(news_id, node_id) 防重复关联；并发重复 INSERT 由 DB 约束兜底
    → DAO 区分约束名映射 NEWS_LINK_DUPLICATE（M05 P1-01 IntegrityError 区分约束名范式延续）。
    """

    __tablename__ = "news_node_links"
    __table_args__ = (
        UniqueConstraint("news_id", "node_id", name="uq_news_node_link"),
        Index("ix_news_node_link_node", "node_id"),
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    news_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("industry_news.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    linked_by: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    news: Mapped[IndustryNews] = relationship("IndustryNews", back_populates="node_links")
