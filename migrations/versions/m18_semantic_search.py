"""m18 语义搜索 — embeddings + embedding_failures + embedding_tasks + search_evaluation_log

Revision ID: m18semsearch01
Revises: m17aiimport01
Create Date: 2026-05-09

design §3 SQLAlchemy block（M18 sprint 子片 1）：
- embeddings 表（7 字段复合 PK / 3 异维列 ARRAY(Float) 占位 / 5 CHECK / 1 filter 索引）
- embedding_failures 表（失败计数 + 监控源 / R10-2 例外 / 1 CHECK / 2 索引）
- embedding_tasks 表（5 状态 / 3 CHECK / 2 索引）
- search_evaluation_log 表（2 索引）
- CREATE EXTENSION IF NOT EXISTS vector（M18 启动期 reconcile pass A 栏 A2）
- 3 ivfflat 索引用 op.execute() raw SQL（pgvector 子片 3 安装后生效）
- 不扩 ck_activity_log_action_type / ck_activity_log_target_type
  （M18 ActionType+2 baseline-patch 已落地 / TargetType 复用 'project' 不扩）

注意：embedding_512/1536/3072 暂用 ARRAY(Float) 占位（pgvector 未安装）。
子片 3 安装 pgvector 后需 ALTER COLUMN 改为 vector(N) 类型 + ivfflat 索引实装。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from api.models.embedding import _EMBEDDING_TASK_STATUSES

revision: str = "m18semsearch01"
down_revision: str | Sequence[str] | None = "m17aiimport01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _quoted_in_list(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in values)


def upgrade() -> None:
    # ---- pgvector 扩展（M18 启动期 reconcile pass A 栏 A2）----
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ---- embeddings 表（7 字段复合 PK + 3 异维列 + 4 CHECK）----
    op.create_table(
        "embeddings",
        # 7 字段复合主键
        sa.Column("project_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "modality", sa.String(16), primary_key=True, nullable=False, server_default="text"
        ),
        sa.Column("target_type", sa.Text(), primary_key=True, nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider", sa.String(32), primary_key=True, nullable=False),
        sa.Column("model_name", sa.Text(), primary_key=True, nullable=False),
        sa.Column("model_version", sa.Text(), primary_key=True, nullable=False),
        # 向量维度
        sa.Column("dim", sa.Integer(), nullable=False),
        # 3 异维列（ARRAY(Float) 占位；pgvector 子片 3 改 vector(N)）
        sa.Column(
            "embedding_512",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
        ),
        sa.Column(
            "embedding_1536",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
        ),
        sa.Column(
            "embedding_3072",
            postgresql.ARRAY(sa.Float()),
            nullable=True,
        ),
        sa.Column("content_hash", sa.Text(), nullable=False),
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
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_embeddings_project_id",
        ),
        sa.CheckConstraint(
            "modality IN ('text', 'image', 'audio')",
            name="ck_embeddings_modality",
        ),
        sa.CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embeddings_target_type",
        ),
        sa.CheckConstraint(
            "provider IN ('openai', 'bge', 'mock')",
            name="ck_embeddings_provider",
        ),
        sa.CheckConstraint(
            "dim IN (512, 1536, 3072)",
            name="ck_embeddings_dim_range",
        ),
        sa.CheckConstraint(
            "(dim = 512 AND embedding_512 IS NOT NULL AND embedding_1536 IS NULL AND embedding_3072 IS NULL) "
            "OR (dim = 1536 AND embedding_1536 IS NOT NULL AND embedding_512 IS NULL AND embedding_3072 IS NULL) "
            "OR (dim = 3072 AND embedding_3072 IS NOT NULL AND embedding_512 IS NULL AND embedding_1536 IS NULL)",
            name="ck_embeddings_dim_column_consistency",
        ),
    )
    # project filter 索引
    op.create_index(
        "ix_embeddings_project_provider_model",
        "embeddings",
        ["project_id", "provider", "model_name", "model_version"],
    )
    # ivfflat 索引：子片 3 安装 pgvector 并将列类型改为 vector(N) 后执行。
    # 当前列为 ARRAY(Float) 占位，vector_cosine_ops 不支持该类型，故暂不创建。
    # 子片 3 回写：ALTER COLUMN embedding_NNN TYPE vector(N) USING ... + 以下三条 raw SQL。
    # op.execute(
    #     "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_512 ON embeddings "
    #     "USING ivfflat (embedding_512 vector_cosine_ops) WITH (lists = 100) "
    #     "WHERE embedding_512 IS NOT NULL"
    # )
    # op.execute(
    #     "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_1536 ON embeddings "
    #     "USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100) "
    #     "WHERE embedding_1536 IS NOT NULL"
    # )
    # op.execute(
    #     "CREATE INDEX IF NOT EXISTS ix_embeddings_vector_3072 ON embeddings "
    #     "USING ivfflat (embedding_3072 vector_cosine_ops) WITH (lists = 100) "
    #     "WHERE embedding_3072 IS NOT NULL"
    # )

    # ---- embedding_failures 表（R10-2 例外 / 90 天 cron 清理）----
    op.create_table(
        "embedding_failures",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
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
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_embedding_failures_project_id",
        ),
        sa.CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embedding_failures_target_type",
        ),
    )
    op.create_index("ix_embedding_failures_failed_at", "embedding_failures", ["failed_at"])
    op.create_index(
        "ix_embedding_failures_project_target",
        "embedding_failures",
        ["project_id", "target_type", "target_id"],
    )

    # ---- embedding_tasks 表（5 状态 / zombie 兜底 / 30 天 cron 清理）----
    op.create_table(
        "embedding_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enqueued_by", sa.Text(), nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_embedding_tasks_project_id",
        ),
        sa.CheckConstraint(
            f"status IN ({_quoted_in_list(_EMBEDDING_TASK_STATUSES)})",
            name="ck_embedding_tasks_status",
        ),
        sa.CheckConstraint(
            "target_type IN ('node', 'dimension_record', 'competitor', 'issue')",
            name="ck_embedding_tasks_target_type",
        ),
        sa.CheckConstraint(
            "enqueued_by IN ('incremental', 'backfill', 'model_upgrade')",
            name="ck_embedding_tasks_enqueued_by",
        ),
    )
    op.create_index(
        "ix_embedding_tasks_status_created",
        "embedding_tasks",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_embedding_tasks_project_target",
        "embedding_tasks",
        ["project_id", "target_type", "target_id"],
    )

    # ---- search_evaluation_log 表（1% 采样 / 1 年保留）----
    op.create_table(
        "search_evaluation_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column(
            "keyword_top5",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "semantic_top5",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "hybrid_top5",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("user_clicked_target_type", sa.Text(), nullable=True),
        sa.Column("user_clicked_target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rrf_k", sa.Integer(), nullable=False),
        sa.Column("similarity_threshold", sa.Float(), nullable=False),
        sa.Column(
            "sampled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
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
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
            name="fk_search_eval_project_id",
        ),
    )
    op.create_index("ix_search_eval_sampled_at", "search_evaluation_log", ["sampled_at"])
    op.create_index(
        "ix_search_eval_project_query",
        "search_evaluation_log",
        ["project_id", "query"],
    )


def downgrade() -> None:
    op.drop_index("ix_search_eval_project_query", table_name="search_evaluation_log")
    op.drop_index("ix_search_eval_sampled_at", table_name="search_evaluation_log")
    op.drop_table("search_evaluation_log")

    op.drop_index("ix_embedding_tasks_project_target", table_name="embedding_tasks")
    op.drop_index("ix_embedding_tasks_status_created", table_name="embedding_tasks")
    op.drop_table("embedding_tasks")

    op.drop_index("ix_embedding_failures_project_target", table_name="embedding_failures")
    op.drop_index("ix_embedding_failures_failed_at", table_name="embedding_failures")
    op.drop_table("embedding_failures")

    # ivfflat 索引在子片 3 创建，downgrade 时 IF EXISTS 确保安全（子片 3 未跑时为 no-op）
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_3072")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_1536")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_vector_512")
    op.drop_index("ix_embeddings_project_provider_model", table_name="embeddings")
    op.drop_table("embeddings")

    op.execute("DROP EXTENSION IF EXISTS vector")
