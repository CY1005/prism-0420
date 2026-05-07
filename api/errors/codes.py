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
