from enum import StrEnum


class ErrorCode(StrEnum):
    """业务错误码（前后端一致 / OpenAPI codegen 同步至前端）。

    命名规范（N1，详见 design/00-architecture/08-namespaces.md §1.1）：
    - Enum 名（左侧）：UPPER_SNAKE_CASE（PEP 8 常量风格）
    - Enum value（右侧 / HTTP body code 字段）：全小写 snake_case，含实体前缀
      （如 ``user_not_found``），可直接作前端 next-intl i18n key，对齐 Stripe /
      GitHub / Google AIP-193 业界标准。
    """

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
