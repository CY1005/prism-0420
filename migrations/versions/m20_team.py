"""m20 团队 — teams + team_members 双表 + projects.team_id 启用 FK + ALTER ck CHECK

Revision ID: m20team01
Revises: m19export01
Create Date: 2026-05-09

design §3 SQLAlchemy block + §3.4 Alembic 迁移（M20 sprint 子片 1）：
- M20 own：CREATE TABLE teams（含 UniqueConstraint creator_id+name + 2 CheckConstraint
  name 长度 / version 非负 + creator_id 索引）+ CREATE TABLE team_members（含
  UniqueConstraint team_id+user_id + CheckConstraint role 三重防护 + ix_team_members_user_team
  反向索引 + RESTRICT FK 双 FK）
- M02 baseline-patch：ALTER TABLE projects ADD CONSTRAINT fk_projects_team FOREIGN KEY
  (team_id) REFERENCES teams(id) ON DELETE RESTRICT（Q8=B 强制前置迁出 / Q13.1②=B）。
  原列 team_id 已存在（M02 sprint A1=C 中间态 / 不需 ADD COLUMN）
- M15 baseline-patch：ALTER ck_activity_log_action_type CHECK 重建（含 M20 新增 10 个
  team_* 枚举 + project_joined_team / project_left_team） + ALTER
  ck_activity_log_target_type CHECK 重建（含 "team"）

枚举字面来源：api/models/activity_log.py:_ACTION_TYPES + _TARGET_TYPES（M15 横切表 owner
4 处同步范式 / M20 baseline-patch 已预录于 model tuple line 126-135 + 157）。

ALTER projects FK 引用顺序：先 CREATE TABLE teams（FK target 必须存在）→ 再 ALTER projects
ADD CONSTRAINT fk_projects_team。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.models.activity_log import _ACTION_TYPES, _TARGET_TYPES
from api.models.teams import _TEAM_ROLES

revision: str = "m20team01"
down_revision: str | Sequence[str] | None = "m19export01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # ---- 1. CREATE TABLE teams ----
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
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
            ["creator_id"],
            ["users.id"],
            ondelete="RESTRICT",
            name="fk_teams_creator_id",
        ),
        sa.UniqueConstraint("creator_id", "name", name="uq_teams_creator_name"),
        sa.CheckConstraint(
            "char_length(name) >= 1 AND char_length(name) <= 100",
            name="ck_teams_name_length",
        ),
        sa.CheckConstraint("version >= 1", name="ck_teams_version_positive"),
    )
    op.create_index("ix_teams_creator_id", "teams", ["creator_id"])

    # ---- 2. CREATE TABLE team_members ----
    op.create_table(
        "team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["team_id"],
            ["teams.id"],
            ondelete="RESTRICT",
            name="fk_team_members_team_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_team_members_user_id",
        ),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        sa.CheckConstraint(
            f"role IN ({_quoted_in_list(_TEAM_ROLES)})",
            name="ck_team_members_role_valid",
        ),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    # 反向索引：高频「U 所在所有 team」查询（L3 user_accessible_project_ids_subquery 性能基线）
    op.create_index("ix_team_members_user_team", "team_members", ["user_id", "team_id"])

    # ---- 3. M02 baseline-patch：ALTER projects ADD FK fk_projects_team ----
    # 原列 team_id 已存在（M02 A1=C 中间态）/ 仅 ADD CONSTRAINT
    op.create_foreign_key(
        "fk_projects_team",
        "projects",
        "teams",
        ["team_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # ---- 4. M15 baseline-patch：重建 ck_activity_log_action_type CHECK ----
    # 包含 M20 新增 10 个 team_* 枚举 + project_joined_team / project_left_team
    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_ACTION_TYPES)})",
    )

    # ---- 5. M15 baseline-patch：重建 ck_activity_log_target_type CHECK ----
    # 包含 M20 新增 "team"
    op.drop_constraint("ck_activity_log_target_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_target_type",
        "activity_logs",
        f"target_type IN ({_quoted_in_list(_TARGET_TYPES)})",
    )


def downgrade() -> None:
    # 回退到 m19 baseline 的 _ACTION_TYPES / _TARGET_TYPES（不含 team_* 10 + "team"）。
    # 注意：若已存在 action_type IN team_* / target_type='team' 的行会导致 downgrade 失败
    # ——这是设计契约，回退前需手工清洗 activity_logs 行。
    _OLD_ACTION_TYPES = tuple(
        v
        for v in _ACTION_TYPES
        if v
        not in (
            "team_created",
            "team_renamed",
            "team_description_changed",
            "team_deleted",
            "team_member_added",
            "team_member_removed",
            "team_member_promoted_admin",
            "team_member_demoted_member",
            "project_joined_team",
            "project_left_team",
        )
    )
    _OLD_TARGET_TYPES = tuple(v for v in _TARGET_TYPES if v != "team")

    op.drop_constraint("ck_activity_log_target_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_target_type",
        "activity_logs",
        f"target_type IN ({_quoted_in_list(_OLD_TARGET_TYPES)})",
    )

    op.drop_constraint("ck_activity_log_action_type", "activity_logs", type_="check")
    op.create_check_constraint(
        "ck_activity_log_action_type",
        "activity_logs",
        f"action_type IN ({_quoted_in_list(_OLD_ACTION_TYPES)})",
    )

    # 删 FK fk_projects_team（保留 team_id 列 / 回退到 A1=C 中间态）
    op.drop_constraint("fk_projects_team", "projects", type_="foreignkey")

    # 删 team_members 表（含索引 + UNIQUE + CHECK + FK 自动 CASCADE）
    op.drop_index("ix_team_members_user_team", table_name="team_members")
    op.drop_index("ix_team_members_user_id", table_name="team_members")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")

    # 删 teams 表
    op.drop_index("ix_teams_creator_id", table_name="teams")
    op.drop_table("teams")
