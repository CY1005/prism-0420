"""m06 competitor (2 tables: competitors + competitor_refs)

Revision ID: m06competitor01
Revises: m05versiontl01
Create Date: 2026-05-08

design §3 SQLAlchemy block + §3 ER + §9 主查询模式：
- competitors：项目级全局；display_name **无**唯一约束（允许同名版本不同）
- competitor_refs：功能项级对标；UNIQUE(node_id, competitor_id) 防同节点重复关联
- project_id 冗余兜底（design §3 CY ack）
- 索引：(node_id, project_id) 主查询 / (project_id) 全局列表 / (competitor_id) 反向查询
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m06competitor01"
down_revision: str | Sequence[str] | None = "m05versiontl01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # competitors
    op.create_table(
        "competitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_competitor_project"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_competitor_created_by"),
    )
    op.create_index("ix_competitor_project", "competitors", ["project_id"])

    # competitor_refs
    op.create_table(
        "competitor_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("competitor_version", sa.Text(), nullable=True),
        sa.Column("feature_coverage", sa.Text(), nullable=True),
        sa.Column("tech_approach", sa.Text(), nullable=True),
        sa.Column("pros_and_cons", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["node_id"], ["nodes.id"], ondelete="CASCADE", name="fk_competitor_ref_node"
        ),
        sa.ForeignKeyConstraint(
            ["competitor_id"],
            ["competitors.id"],
            ondelete="CASCADE",
            name="fk_competitor_ref_competitor",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_competitor_ref_project"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_competitor_ref_created_by"),
        sa.UniqueConstraint("node_id", "competitor_id", name="uq_competitor_ref_node_competitor"),
    )
    op.create_index("ix_competitor_ref_node_project", "competitor_refs", ["node_id", "project_id"])
    op.create_index("ix_competitor_ref_project", "competitor_refs", ["project_id"])
    op.create_index("ix_competitor_ref_competitor", "competitor_refs", ["competitor_id"])


def downgrade() -> None:
    op.drop_index("ix_competitor_ref_competitor", table_name="competitor_refs")
    op.drop_index("ix_competitor_ref_project", table_name="competitor_refs")
    op.drop_index("ix_competitor_ref_node_project", table_name="competitor_refs")
    op.drop_table("competitor_refs")
    op.drop_index("ix_competitor_project", table_name="competitors")
    op.drop_table("competitors")
