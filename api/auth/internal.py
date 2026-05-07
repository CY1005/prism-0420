"""Internal token 签名横切 helper（horizontal）。

# horizontal: 是
# owner: ADR-004 §1 P2 internal token（Server Action → FastAPI 转发签名）
# 位置: api/auth/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: ADR-004 横切（HMAC P2 签名 / 时间戳防回放 / 签名校验）
"""

import hashlib
import hmac
import time
from uuid import UUID

from api.core.config import settings


def _signing_string(
    timestamp: str,
    method: str,
    path_with_query: str,
    user_id: UUID,
    body: bytes,
) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    return f"{timestamp}\n{method}\n{path_with_query}\n{user_id}\n{body_hash}"


def compute_signature(
    timestamp: str,
    method: str,
    path_with_query: str,
    user_id: UUID,
    body: bytes,
    token: str | None = None,
) -> str:
    secret = (token or settings.internal_token).encode("utf-8")
    material = _signing_string(timestamp, method, path_with_query, user_id, body).encode("utf-8")
    return hmac.new(secret, material, hashlib.sha256).hexdigest()


def verify_internal_signature(
    token: str,
    user_id: UUID,
    signature: str,
    timestamp: str,
    method: str,
    path_with_query: str,
    body: bytes,
) -> bool:
    """Returns True iff token + timestamp window + signature all valid (constant-time compares)."""
    if not hmac.compare_digest(token, settings.internal_token):
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > settings.internal_signature_window_seconds:
        return False
    expected = compute_signature(timestamp, method, path_with_query, user_id, body)
    return hmac.compare_digest(expected, signature)
