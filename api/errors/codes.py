"""ErrorCode 枚举横切 helper（horizontal）。

# horizontal: 是
# owner: engineering-spec §7.2（统一错误码命名表）
# 位置: api/errors/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 全局错误码注册表（业务模块通过 codes_added frontmatter 字段扩展）
# R13-1 守护: 每个 ErrorCode 必有对应 AppError 子类（ci-lint.sh 校验 parity）
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    INTERNAL_ERROR = "internal_error"
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"

    UNAUTHENTICATED = "unauthenticated"
    ACCESS_TOKEN_EXPIRED = "access_token_expired"
    REFRESH_TOKEN_EXPIRED = "refresh_token_expired"
    ACCOUNT_LOCKED = "account_locked"

    INVALID_CREDENTIALS = "invalid_credentials"
    ACCOUNT_DISABLED = "account_disabled"
    ACCOUNT_PENDING = "account_pending"
    INVALID_REFRESH_TOKEN = "invalid_refresh_token"
    OLD_PASSWORD_MISMATCH = "old_password_mismatch"
    PASSWORD_TOO_WEAK = "password_too_weak"
    EMAIL_ALREADY_EXISTS = "email_already_exists"
    USER_NOT_FOUND = "user_not_found"
    SELF_DOWNGRADE_FORBIDDEN = "self_downgrade_forbidden"
    LAST_ADMIN_PROTECTED = "last_admin_protected"
    INVALID_STATUS_TRANSITION = "invalid_status_transition"
    VERSION_CONFLICT = "version_conflict"
    REGISTRATION_DISABLED = "registration_disabled"

    # M02 项目管理 (design §13)
    PROJECT_NOT_FOUND = "project_not_found"
    PROJECT_ALREADY_ARCHIVED = "project_already_archived"
    PROJECT_ALREADY_ACTIVE = "project_already_active"
    PROJECT_DELETE_NOT_SUPPORTED = "project_delete_not_supported"
    PROJECT_NAME_DUPLICATE = "project_name_duplicate"
    MEMBER_NOT_FOUND = "member_not_found"
    MEMBER_ALREADY_EXISTS = "member_already_exists"
    MEMBER_CANNOT_REMOVE_OWNER = "member_cannot_remove_owner"
    MEMBER_ROLE_INVALID = "member_role_invalid"
    DIMENSION_CONFIG_INVALID = "dimension_config_invalid"
    AI_KEY_ENCRYPT_FAILED = "ai_key_encrypt_failed"
    # F2.3 M20 baseline-patch (move-team scaffold caller 子片 4 推迟 / R-X5 子选项实证标记位置=code 注释)
    PROJECT_ARCHIVED = "project_archived"

    # M03 功能模块树 (design §13)
    # R-X5 子选项实证 (M02 sprint 末): R13-1 未实装期 ErrorCode 标记位置 = code 注释
    # NODE_NAME_EMPTY: Pydantic min_length=1 拦得早, ErrorCode 保留备用 (R13-1 parity)
    # NODE_DELETE_HAS_CHILDREN: G2 决策硬删除级联, 此码保留备用不触发 (R13-1 parity)
    NODE_NOT_FOUND = "node_not_found"
    NODE_NAME_EMPTY = "node_name_empty"
    NODE_PARENT_NOT_FOUND = "node_parent_not_found"
    NODE_TYPE_IMMUTABLE = "node_type_immutable"
    NODE_REORDER_INVALID = "node_reorder_invalid"
    NODE_DELETE_HAS_CHILDREN = "node_delete_has_children"
    NODE_MOVE_CYCLE_DETECTED = "node_move_cycle_detected"

    # M04 功能项档案页 / 维度记录 (design §13)
    DIMENSION_NOT_FOUND = "dimension_not_found"
    DIMENSION_TYPE_DISABLED = "dimension_type_disabled"
    DIMENSION_TYPE_NOT_FOUND = "dimension_type_not_found"
    DIMENSION_CONTENT_INVALID = "dimension_content_invalid"
    DIMENSION_DUPLICATE = "dimension_duplicate"

    # M05 版本演进时间线 (design §13)
    # B3 (闸门 2.5) C 栏决策：snapshot_data 不深校验，VERSION_SNAPSHOT_INVALID 保留作未来扩展点
    VERSION_NOT_FOUND = "version_not_found"
    VERSION_LABEL_DUPLICATE = "version_label_duplicate"
    VERSION_SNAPSHOT_INVALID = "version_snapshot_invalid"

    # M06 竞品参考 (design §13)
    COMPETITOR_NOT_FOUND = "competitor_not_found"
    COMPETITOR_REF_NOT_FOUND = "competitor_ref_not_found"
    COMPETITOR_REF_DUPLICATE = "competitor_ref_duplicate"
    COMPETITOR_CROSS_PROJECT = "competitor_cross_project"

    # M07 问题沉淀 (design §13)
    ISSUE_NOT_FOUND = "issue_not_found"
    ISSUE_TRANSITION_INVALID = "issue_transition_invalid"
    ISSUE_CLOSED_ERROR = "issue_closed_error"
    ISSUE_ASSIGNEE_REQUIRED = "issue_assignee_required"
    ISSUE_CATEGORY_INVALID = "issue_category_invalid"
    ISSUE_NODE_CROSS_PROJECT = "issue_node_cross_project"

    # M08 模块关系图 (design §13)
    RELATION_NOT_FOUND = "relation_not_found"
    RELATION_DUPLICATE = "relation_duplicate"
    RELATION_SELF_LOOP = "relation_self_loop"
    RELATION_NODE_NOT_IN_PROJECT = "relation_node_not_in_project"
    RELATION_TYPE_INVALID = "relation_type_invalid"

    # M10 项目全景图 (design §13；纯读聚合)
    OVERVIEW_PROJECT_NOT_FOUND = "overview_project_not_found"
    OVERVIEW_NODE_NOT_FOUND = "overview_node_not_found"
    OVERVIEW_NO_DIMENSIONS = "overview_no_dimensions"

    # M11 冷启动支持 (design §13；G2/G6 移除 COLD_START_DUPLICATE)
    COLD_START_TASK_NOT_FOUND = "cold_start_task_not_found"
    COLD_START_CSV_INVALID = "cold_start_csv_invalid"
    COLD_START_ROW_VALIDATION_FAILED = "cold_start_row_validation_failed"
    COLD_START_BATCH_INSERT_FAILED = "cold_start_batch_insert_failed"
    COLD_START_TASK_FINALIZED = "cold_start_task_finalized"
    COLD_START_INVALID_STATE_TRANSITION = "cold_start_invalid_state_transition"
    COLD_START_FILE_TOO_LARGE = "cold_start_file_too_large"

    # M12 功能对比矩阵 (design §13)
    COMPARISON_SNAPSHOT_NOT_FOUND = "comparison_snapshot_not_found"
    COMPARISON_SNAPSHOT_NAME_EMPTY = "comparison_snapshot_name_empty"
    COMPARISON_NODE_NOT_FOUND = "comparison_node_not_found"
    COMPARISON_EMPTY_SELECTION = "comparison_empty_selection"
    COMPARISON_SNAPSHOT_CONFLICT = "comparison_snapshot_conflict"

    # M14 行业动态 (design §13)
    NEWS_NOT_FOUND = "news_not_found"
    NEWS_LINK_DUPLICATE = "news_link_duplicate"
    NEWS_LINK_NOT_FOUND = "news_link_not_found"
    NEWS_FORBIDDEN = "news_forbidden"

    # M13 AI 需求分析 (design §13)
    ANALYSIS_NODE_NOT_FOUND = "analysis_node_not_found"
    ANALYSIS_PROVIDER_NOT_CONFIGURED = "analysis_provider_not_configured"
    ANALYSIS_PROVIDER_ERROR = "analysis_provider_error"
    ANALYSIS_TIMEOUT = "analysis_timeout"
    ANALYSIS_QUOTA_EXCEEDED = "analysis_quota_exceeded"
    ANALYSIS_SAVE_FAILED = "analysis_save_failed"
    ANALYSIS_INVALID_LEVEL = "analysis_invalid_level"

    # M15 数据流转 (design §13)
    ACTIVITY_STREAM_PROJECT_NOT_FOUND = "activity_stream_project_not_found"
    ACTIVITY_STREAM_FORBIDDEN = "activity_stream_forbidden"
    ACTIVITY_STREAM_INVALID_FILTER = "activity_stream_invalid_filter"

    # M16 AI 快照 (design §13 / §12B 后台 fire-and-forget)
    SNAPSHOT_NODE_NOT_FOUND = "snapshot_node_not_found"
    SNAPSHOT_INSUFFICIENT_VERSIONS = "snapshot_insufficient_versions"
    SNAPSHOT_PROVIDER_NOT_CONFIGURED = "snapshot_provider_not_configured"
    SNAPSHOT_PROVIDER_ERROR = "snapshot_provider_error"
    SNAPSHOT_TIMEOUT = "snapshot_timeout"
    SNAPSHOT_QUOTA_EXCEEDED = "snapshot_quota_exceeded"
    SNAPSHOT_SAVE_FAILED = "snapshot_save_failed"
    SNAPSHOT_TASK_NOT_FOUND = "snapshot_task_not_found"
    SNAPSHOT_NOT_READY = "snapshot_not_ready"
    SNAPSHOT_TASK_FINALIZED = "snapshot_task_finalized"
    SNAPSHOT_INVALID_STATE_TRANSITION = "snapshot_invalid_state_transition"
    SNAPSHOT_ZOMBIE = "snapshot_zombie"
    SNAPSHOT_PARSE_FAILED = "snapshot_parse_failed"
    SNAPSHOT_INVALID_DIMENSION_KEY = "snapshot_invalid_dimension_key"
    SNAPSHOT_TASK_PATH_MISMATCH = "snapshot_task_path_mismatch"

    # M17 AI 智能导入 (design §13 / R-X1 第二实例 / Queue 异步 pilot)
    IMPORT_TASK_NOT_FOUND = "import_task_not_found"
    IMPORT_TASK_FINALIZED = "import_task_finalized"
    IMPORT_INVALID_SOURCE = "import_invalid_source"
    IMPORT_AI_PROVIDER_ERROR = "import_ai_provider_error"
    IMPORT_BATCH_INSERT_FAILED = "import_batch_insert_failed"
    IMPORT_QUOTA_EXCEEDED = "import_quota_exceeded"
    IMPORT_TASK_DUPLICATE = "import_task_duplicate"
    IMPORT_INVALID_STATE_TRANSITION = "import_invalid_state_transition"

    # M20 团队 (M15 sprint baseline-patch / design §13 / 未实装期 ErrorCode）
    # M15 sprint 期仅注册 + R13-1 parity；生产路径 M20 sprint 期补 raise caller + e2e 回归
    TEAM_NOT_FOUND = "team_not_found"
    TEAM_NAME_DUPLICATE = "team_name_duplicate"
    TEAM_HAS_PROJECTS = "team_has_projects"
    TEAM_OWNER_REQUIRED = "team_owner_required"
    TEAM_MEMBER_NOT_FOUND = "team_member_not_found"
    TEAM_MEMBER_DUPLICATE = "team_member_duplicate"
    TEAM_PERMISSION_DENIED = "team_permission_denied"
    CROSS_TEAM_MOVE_FORBIDDEN = "cross_team_move_forbidden"

    # M18 语义搜索 (design §13 line 1195-1221)
    # M18 search
    INVALID_QUERY_LENGTH = "invalid_query_length"
    SEARCH_TIMEOUT = "search_timeout"
    PGVECTOR_UNAVAILABLE = "pgvector_unavailable"

    # M18 embedding worker
    EMBEDDING_PROVIDER_FAILED = "embedding_provider_failed"
    EMBEDDING_PROVIDER_TIMEOUT = "embedding_provider_timeout"
    EMBEDDING_TARGET_NOT_FOUND = "embedding_target_not_found"
    EMBEDDING_ZOMBIE = "embedding_zombie"
    EMBEDDING_TASK_TERMINAL_VIOLATION = "embedding_task_terminal_violation"
    EMBEDDING_TASK_INVALID_TRANSITION = "embedding_task_invalid_transition"

    # M18 admin
    EMBEDDING_BACKFILL_ALREADY_RUNNING = "embedding_backfill_already_running"
    EMBEDDING_MODEL_UPGRADE_INVALID = "embedding_model_upgrade_invalid"

    # M18 删除一致性（baseline-patch 决策 5）
    EMBEDDING_DELETE_FAILED = "embedding_delete_failed"

    # M19 导入/导出 (design §13 / 只读 / pilot=false / complexity=low)
    EXPORT_NODE_LIMIT_EXCEEDED = "export_node_limit_exceeded"
    EXPORT_NODE_NOT_IN_PROJECT = "export_node_not_in_project"
    EXPORT_EMPTY_CONTENT = "export_empty_content"
