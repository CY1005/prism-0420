"""M01 子片 1 — bootstrap (G12-13, BS1-BS6)."""

from __future__ import annotations

from sqlalchemy import select

from api.models.user import User
from api.services.auth_service import AuthService


async def test_bootstrap_admin_creates_first_admin_when_users_empty(db_session):
    svc = AuthService()
    user = await svc.bootstrap_admin_if_empty(
        db_session,
        email="boot@example.com",
        password="bootstrap123",
        name="First Admin",
    )
    assert user is not None
    assert user.role == "platform_admin"
    assert user.status == "active"


async def test_bootstrap_admin_skipped_when_users_exist(make_user, db_session):
    await make_user()
    svc = AuthService()
    result = await svc.bootstrap_admin_if_empty(
        db_session,
        email="boot2@example.com",
        password="bootstrap123",
        name="X",
    )
    assert result is None
    rows = (await db_session.execute(select(User))).scalars().all()
    assert all(u.email != "boot2@example.com" for u in rows)


async def test_bootstrap_admin_rejects_weak_password(db_session):
    from api.errors.exceptions import PasswordTooWeakError

    svc = AuthService()
    try:
        await svc.bootstrap_admin_if_empty(
            db_session, email="weak@example.com", password="short", name="X"
        )
        raise AssertionError("expected PasswordTooWeakError")
    except PasswordTooWeakError:
        pass


async def test_create_admin_service_rejects_duplicate_email(make_user, db_session):
    from api.errors.exceptions import EmailAlreadyExistsError

    await make_user(email="dup@example.com")
    svc = AuthService()
    try:
        await svc.create_admin(
            db_session, email="dup@example.com", password="hunter2hunter", name="Dup"
        )
        raise AssertionError("expected EmailAlreadyExistsError")
    except EmailAlreadyExistsError:
        pass


def test_cli_argparse_smoke():
    """CLI argparse 不接 DB（_create_admin 才接）；这里只验 module 可被解析为 -m 入口。"""
    import api.cli as cli

    assert callable(cli.main)
    # 缺参数 → SystemExit
    raised = False
    try:
        cli.main([])
    except SystemExit:
        raised = True
    assert raised
