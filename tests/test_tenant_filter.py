from uuid import UUID, uuid4

import pytest

from api.auth import (
    set_tenant_context,
    user_accessible_project_ids_subquery,
)


class _StubCtx:
    def __init__(self):
        self.calls: list[tuple[object, UUID]] = []

    def user_accessible_project_ids_subquery(self, db, user_id):
        self.calls.append((db, user_id))
        return f"subquery:{user_id}"


def test_raises_when_uninitialized():
    set_tenant_context(None)
    with pytest.raises(NotImplementedError, match="tenant_context not initialized"):
        user_accessible_project_ids_subquery(object(), uuid4())


def test_delegates_to_injected_context():
    ctx = _StubCtx()
    set_tenant_context(ctx)
    try:
        db = object()
        uid = uuid4()
        result = user_accessible_project_ids_subquery(db, uid)
        assert result == f"subquery:{uid}"
        assert ctx.calls == [(db, uid)]
    finally:
        set_tenant_context(None)
