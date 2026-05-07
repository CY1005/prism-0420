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
