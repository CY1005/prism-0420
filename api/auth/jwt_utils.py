"""JWT 编解码横切 helper（horizontal）。

# horizontal: 是
# owner: ADR-004 §1 P1 Bearer JWT
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: ADR-004 横切（access token + refresh token 编解码 + claims 验证）
"""

import time
from typing import Any
from uuid import UUID

import jwt

from api.core.config import settings


def encode_jwt(user_id: UUID, extra_claims: dict[str, Any] | None = None) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + settings.jwt_access_ttl_seconds,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode + verify signature/exp; raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
