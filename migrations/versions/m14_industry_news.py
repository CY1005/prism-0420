"""m14 industry news (2 tables: industry_news + news_node_links)

Revision ID: m14industrynews01
Revises: m12comparison01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER：
- industry_news 表：**全局共享 / 无 project_id**（design §9 + 06-design-principles 清单 5 全局豁免）
- news_node_links 表：M14 与 M03 nodes 1:N 关联（UNIQUE(news_id, node_id) 防重复）
- CHECK 约束：source_type = 'manual'（design §1 灰区 1 / 本期仅 manual）
- 索引：(created_at DESC) / (created_by) / tags GIN / news_node_link.(node_id)
- M13 是纯读模块（无 model/migration）→ M14 直接接续 M12 comparison。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m14industrynews01"
# down_revision 链：M13 是纯读 LLM 集成模块（无 model/migration / R3-5 纯读聚合）→ M14 接续 M12。
down_revision: str | Sequence[str] | None = "m12comparison01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "industry_news",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column(
            "source_type",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_industry_news_created_by"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_industry_news_updated_by"),
        sa.CheckConstraint(
            "source_type = 'manual'",
            name="ck_industry_news_source_type_manual",
        ),
    )
    op.create_index("ix_industry_news_created_at", "industry_news", ["created_at"])
    op.create_index("ix_industry_news_created_by", "industry_news", ["created_by"])
    op.create_index(
        "ix_industry_news_tags",
        "industry_news",
        ["tags"],
        postgresql_using="gin",
    )

    op.create_table(
        "news_node_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("news_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("linked_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["news_id"],
            ["industry_news.id"],
            ondelete="CASCADE",
            name="fk_news_node_link_news",
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["nodes.id"],
            ondelete="CASCADE",
            name="fk_news_node_link_node",
        ),
        sa.ForeignKeyConstraint(["linked_by"], ["users.id"], name="fk_news_node_link_linked_by"),
        sa.UniqueConstraint("news_id", "node_id", name="uq_news_node_link"),
    )
    op.create_index("ix_news_node_link_node", "news_node_links", ["node_id"])


def downgrade() -> None:
    op.drop_index("ix_news_node_link_node", table_name="news_node_links")
    op.drop_table("news_node_links")
    op.drop_index("ix_industry_news_tags", table_name="industry_news")
    op.drop_index("ix_industry_news_created_by", table_name="industry_news")
    op.drop_index("ix_industry_news_created_at", table_name="industry_news")
    op.drop_table("industry_news")
