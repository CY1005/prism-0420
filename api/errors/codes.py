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
