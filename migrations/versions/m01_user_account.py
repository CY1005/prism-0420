"""m01 user account schema (drop notes scaffold + create 7 M01 tables)

Revision ID: m01useracc01
Revises: 333181a89bc8
Create Date: 2026-05-07

7 表：users / refresh_tokens / auth_audit_log（实装）+ password_reset_tokens /
invite_codes / auth_identities / email_change_requests（预留，CI 守护禁 services
/ routers import）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m01useracc01"
down_revision: str | Sequence[str] | None = "333181a89bc8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_USER_ROLES = ("platform_admin", "user")
_USER_STATUSES = ("active", "disabled", "pending")
_AUDIT_ACTIONS = (
    "user.login_success",
    "user.login_failed",
    "user.locked",
    "user.logout",
    "user.refresh_token",
    "user.profile_update",
    "user.password_change",
    "user.admin_create",
    "user.admin_update_role",
    "user.admin_update_status",
    "user.all_tokens_revoked",
)
_IDENTITY_PROVIDERS = ("github", "google")


def _ck_clause(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    # B9 self-test scaffold removed
    op.drop_table("notes")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=True),
        sa.Column("avatar_url", sa.String(1024), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_invalidated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint(_ck_clause("role", _USER_ROLES), name="ck_users_role"),
        sa.CheckConstraint(_ck_clause("status", _USER_STATUSES), name="ck_users_status"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_info", sa.String(512), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_refresh_tokens_user"
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])

    op.create_table(
        "auth_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL", name="fk_auth_audit_user"
        ),
        sa.CheckConstraint(
            _ck_clause("action_type", _AUDIT_ACTIONS), name="ck_auth_audit_action_type"
        ),
    )
    op.create_index("ix_auth_audit_log_user_id", "auth_audit_log", ["user_id"])
    op.create_index("ix_auth_audit_log_action_type", "auth_audit_log", ["action_type"])
    op.create_index("ix_auth_audit_log_created_at", "auth_audit_log", ["created_at"])

    # ── 预留 4 表 ──────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_pwd_reset_user"
        ),
        sa.UniqueConstraint("token_hash", name="uq_pwd_reset_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])

    op.create_table(
        "invite_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("used_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_invite_created_by"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], name="fk_invite_used_by"),
        sa.UniqueConstraint("code", name="uq_invite_code"),
    )

    op.create_table(
        "auth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_identity_user"
        ),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_identity_provider_user"),
        sa.CheckConstraint(
            _ck_clause("provider", _IDENTITY_PROVIDERS), name="ck_identity_provider"
        ),
    )
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    op.create_table(
        "email_change_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("new_email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE", name="fk_email_change_user"
        ),
        sa.UniqueConstraint("token_hash", name="uq_email_change_hash"),
    )
    op.create_index("ix_email_change_requests_user_id", "email_change_requests", ["user_id"])
    op.create_index("ix_email_change_requests_expires_at", "email_change_requests", ["expires_at"])


def downgrade() -> None:
    op.drop_table("email_change_requests")
    op.drop_table("auth_identities")
    op.drop_table("invite_codes")
    op.drop_table("password_reset_tokens")
    op.drop_table("auth_audit_log")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("content", sa.String(length=200), nullable=False),
    )
