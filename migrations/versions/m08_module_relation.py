"""m08 module_relations (1 table)

Revision ID: m08modulerel01
Revises: m07issue01
Create Date: 2026-05-08

design §3:
- UNIQUE(source_node_id, target_node_id, relation_type) 三元组（候选 A）
- CHECK relation_type IN (3 values) / CHECK no self-loop / project_id NOT NULL
- 索引：(project_id) tenant / (source_node_id, project_id) source 查询 /
       (target_node_id, project_id) target 查询
- 双向关系策略（候选 A）：有向；A→B 与 B→A 不同记录
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.helpers import ck_clause as _ck_clause

revision: str = "m08modulerel01"
down_revision: str | Sequence[str] | None = "m07issue01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "module_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
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
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_relation_project"
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["nodes.id"], ondelete="CASCADE", name="fk_relation_source"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["nodes.id"], ondelete="CASCADE", name="fk_relation_target"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_relation_created_by"),
        sa.UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="uq_module_relation_src_tgt_type",
        ),
        sa.CheckConstraint(
            _ck_clause("relation_type", ("depends_on", "related_to", "conflicts_with")),
            name="ck_module_relation_type_valid",
        ),
        sa.CheckConstraint(
            "source_node_id != target_node_id",
            name="ck_module_relation_no_self_loop",
        ),
    )
    op.create_index("ix_module_relation_project", "module_relations", ["project_id"])
    op.create_index(
        "ix_module_relation_source", "module_relations", ["source_node_id", "project_id"]
    )
    op.create_index(
        "ix_module_relation_target", "module_relations", ["target_node_id", "project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_module_relation_target", table_name="module_relations")
    op.drop_index("ix_module_relation_source", table_name="module_relations")
    op.drop_index("ix_module_relation_project", table_name="module_relations")
    op.drop_table("module_relations")
