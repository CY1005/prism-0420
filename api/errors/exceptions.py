"""AppError 子类横切 helper（horizontal）。

# horizontal: 是
# owner: engineering-spec §7.2（与 ErrorCode 枚举对齐 R13-1 parity）
# 位置: api/errors/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 全局异常基类 + 子类（业务模块通过 codes_added 扩展时同步加子类）
"""

from typing import Any

from api.errors.codes import ErrorCode


class AppError(Exception):
    code: ErrorCode = ErrorCode.INTERNAL_ERROR
    http_status: int = 500
    message: str = "Internal error"

    def __init__(self, message: str | None = None, **details: Any) -> None:
        if message is not None:
            self.message = message
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    code = ErrorCode.NOT_FOUND
    http_status = 404
    message = "Resource not found"


class ValidationError(AppError):
    code = ErrorCode.VALIDATION_ERROR
    http_status = 422
    message = "Validation failed"


class ConflictError(AppError):
    code = ErrorCode.CONFLICT
    http_status = 409
    message = "Concurrent modification detected"


class UnauthenticatedError(AppError):
    code = ErrorCode.UNAUTHENTICATED
    http_status = 401
    message = "Authentication required"


class RateLimitedError(AppError):
    code = ErrorCode.RATE_LIMITED
    http_status = 429
    message = "Too many requests"


class AccessTokenExpiredError(AppError):
    code = ErrorCode.ACCESS_TOKEN_EXPIRED
    http_status = 401
    message = "Access token expired"


class RefreshTokenExpiredError(AppError):
    code = ErrorCode.REFRESH_TOKEN_EXPIRED
    http_status = 401
    message = "Refresh token expired"


class AccountLockedError(AppError):
    code = ErrorCode.ACCOUNT_LOCKED
    http_status = 423
    message = "Account is locked"


# ─── M01 ─────────────────────────────────────────────


class InvalidCredentialsError(AppError):
    code = ErrorCode.INVALID_CREDENTIALS
    http_status = 401
    message = "Invalid email or password"


class AccountDisabledError(AppError):
    code = ErrorCode.ACCOUNT_DISABLED
    http_status = 403
    message = "Account disabled"


class AccountPendingError(AppError):
    code = ErrorCode.ACCOUNT_PENDING
    http_status = 403
    message = "Account pending approval"


class InvalidRefreshTokenError(AppError):
    code = ErrorCode.INVALID_REFRESH_TOKEN
    http_status = 401
    message = "Invalid refresh token"


class OldPasswordMismatchError(ValidationError):
    code = ErrorCode.OLD_PASSWORD_MISMATCH
    http_status = 400
    message = "Old password mismatch"


class PasswordTooWeakError(ValidationError):
    code = ErrorCode.PASSWORD_TOO_WEAK
    http_status = 422
    message = "Password too weak"


class EmailAlreadyExistsError(AppError):
    code = ErrorCode.EMAIL_ALREADY_EXISTS
    http_status = 409
    message = "Email already exists"


class UserNotFoundError(NotFoundError):
    code = ErrorCode.USER_NOT_FOUND
    message = "User not found"


class PermissionDeniedError(AppError):
    code = ErrorCode.PERMISSION_DENIED
    http_status = 403
    message = "Permission denied"


class SelfDowngradeForbiddenError(AppError):
    code = ErrorCode.SELF_DOWNGRADE_FORBIDDEN
    http_status = 400
    message = "Cannot change your own role"


class LastAdminProtectedError(AppError):
    code = ErrorCode.LAST_ADMIN_PROTECTED
    http_status = 400
    message = "Cannot disable the last platform admin"


class InvalidStatusTransitionError(AppError):
    code = ErrorCode.INVALID_STATUS_TRANSITION
    http_status = 400
    message = "Invalid status transition"


class VersionConflictError(AppError):
    code = ErrorCode.VERSION_CONFLICT
    http_status = 409
    message = "Version conflict — refresh and retry"


class RegistrationDisabledError(AppError):
    code = ErrorCode.REGISTRATION_DISABLED
    http_status = 403
    message = "Registration disabled"
