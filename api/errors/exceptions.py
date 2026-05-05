from typing import Any

from api.errors.codes import ErrorCode


class AppError(Exception):
    """所有业务错误的基类。Service/Router 层禁止裸 raise Exception。"""

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


class PermissionDeniedError(AppError):
    code = ErrorCode.PERMISSION_DENIED
    http_status = 403
    message = "Permission denied"


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
