from api.auth.dependencies import AuthServiceProtocol, require_user, set_auth_service
from api.auth.internal import compute_signature, verify_internal_signature
from api.auth.jwt_utils import decode_jwt, encode_jwt
from api.auth.tenant_filter import (
    TenantContextProtocol,
    set_tenant_context,
    user_accessible_project_ids_subquery,
)

__all__ = [
    "AuthServiceProtocol",
    "TenantContextProtocol",
    "compute_signature",
    "decode_jwt",
    "encode_jwt",
    "require_user",
    "set_auth_service",
    "set_tenant_context",
    "user_accessible_project_ids_subquery",
    "verify_internal_signature",
]
