"""m02 project schema (4 tables) + R3-6-B placeholder seed (default dimension type)

Revision ID: m02project01
Revises: m01useracc01
Create Date: 2026-05-07

4 表：projects / project_members / project_dimension_configs / dimension_types

实施期处理段（design §3.X，2026-05-07）：
- A1=C 中间态：projects.team_id 仅 UUID nullable 列，**不加 FK**（teams 表 M20 期建）
- A2=A 现在建：rrf_k + similarity_threshold + 2 CHECK 约束本期落地（M18 baseline-patch）

R3-6-B placeholder seed（design §3.Y）：
- dimension_types 必种 1 条 (key='default', name='默认维度') 兜底测试（M03/M04/M07 fixture）
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m02project01"
down_revision: str | Sequence[str] | None = "m01useracc01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PROJECT_STATUSES = ("active", "archived")
_MEMBER_ROLES = ("owner", "editor", "viewer")


# M04 sprint R1-B C2 闭环：_ck_clause 三处重复 → migrations/helpers.py
from migrations.helpers import ck_clause as _ck_clause  # noqa: E402


def upgrade() -> None:
    # ── dimension_types （全局字典；R3-6-B seed 在本 revision 末段 INSERT）──
    op.create_table(
        "dimension_types",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("icon", sa.String(100), nullable=False, server_default="FileText"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("field_schema", postgresql.JSONB(), nullable=True),
        sa.UniqueConstraint("key", name="uq_dimension_type_key"),
    )

    # ── projects ─────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("template_type", sa.String(50), nullable=False, server_default="custom"),
        sa.Column(
            "hierarchy_labels",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("""'["层级1","层级2","层级3"]'::jsonb"""),
        ),
        sa.Column("version_mode", sa.String(20), nullable=False, server_default="release"),
        sa.Column("ai_provider", sa.String(50), nullable=True),
        sa.Column("ai_api_key_enc", sa.String(1000), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        # A1=C 中间态：UUID nullable，无 FK constraint（M20 sprint ALTER ADD CONSTRAINT）
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        # A2=A：M18 baseline-patch
        sa.Column("rrf_k", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("similarity_threshold", sa.Float(), nullable=False, server_default="0.3"),
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
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name="fk_projects_owner"),
        sa.CheckConstraint("name <> ''", name="ck_project_name_not_empty"),
        sa.CheckConstraint(_ck_clause("status", _PROJECT_STATUSES), name="ck_project_status"),
        sa.CheckConstraint("rrf_k > 0 AND rrf_k <= 200", name="ck_project_rrf_k_range"),
        sa.CheckConstraint(
            "similarity_threshold >= 0.0 AND similarity_threshold <= 1.0",
            name="ck_project_similarity_threshold_range",
        ),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.create_index("ix_projects_team_id", "projects", ["team_id"])
    # G3 部分唯一索引：同 owner 下 active 项目名唯一
    op.create_index(
        "uq_project_owner_name_active",
        "projects",
        ["owner_id", "name"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # ── project_members ──────────────────────────────────────────────
    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_member_project"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_member_user"
        ),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], name="fk_member_invited_by"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        sa.CheckConstraint(_ck_clause("role", _MEMBER_ROLES), name="ck_member_role"),
    )
    op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
    op.create_index("ix_project_members_user_id", "project_members", ["user_id"])

    # ── project_dimension_configs ────────────────────────────────────
    op.create_table(
        "project_dimension_configs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension_type_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE", name="fk_dim_cfg_project"
        ),
        sa.ForeignKeyConstraint(
            ["dimension_type_id"], ["dimension_types.id"], name="fk_dim_cfg_type"
        ),
        sa.UniqueConstraint("project_id", "dimension_type_id", name="uq_proj_dim_config"),
    )
    op.create_index(
        "ix_project_dimension_configs_project_id",
        "project_dimension_configs",
        ["project_id"],
    )

    # ── R3-6-B placeholder seed（design §3.Y）──────────────────────────
    op.execute(
        sa.text(
            "INSERT INTO dimension_types (key, name, icon, description, field_schema) "
            "VALUES ('default', '默认维度', 'FileText', "
            "'M02 R3-6-B 测试兜底 placeholder（design §3.Y）', NULL)"
        )
    )


def downgrade() -> None:
    op.drop_table("project_dimension_configs")
    op.drop_table("project_members")
    op.drop_index("uq_project_owner_name_active", table_name="projects")
    op.drop_table("projects")
    op.drop_table("dimension_types")
