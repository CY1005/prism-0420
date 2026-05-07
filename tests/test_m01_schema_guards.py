"""M01 子片 5 — schema 存在性 + CI 守护 (S1-S11)。

通过 information_schema / pg_catalog 查询直接验证 Alembic 迁移落地正确，
+ subprocess 跑 grep 验 CI 守护规则。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parent.parent


# ─────────────── S1 表存在 ───────────────

EXPECTED_TABLES = (
    "users",
    "refresh_tokens",
    "auth_audit_log",
    "password_reset_tokens",
    "invite_codes",
    "auth_identities",
    "email_change_requests",
)


async def test_s1_all_seven_tables_exist(db_session):
    rows = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name = ANY(:names)"
        ),
        {"names": list(EXPECTED_TABLES)},
    )
    found = {r[0] for r in rows}
    missing = set(EXPECTED_TABLES) - found
    assert not missing, f"missing tables: {missing}"


# ─────────────── S2 / S3 / S3b users 字段 ───────────────


async def test_s2_users_password_hash_nullable(db_session):
    r = await db_session.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='password_hash'"
        )
    )
    assert r.scalar_one() == "YES"


async def test_s3_users_avatar_url_exists_nullable(db_session):
    r = await db_session.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='avatar_url'"
        )
    )
    assert r.scalar_one() == "YES"


async def test_s3b_users_version_not_null_default_1(db_session):
    r = await db_session.execute(
        text(
            "SELECT is_nullable, column_default FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='version'"
        )
    )
    nullable, default = r.one()
    assert nullable == "NO"
    assert default and "1" in default


# ─────────────── S4 refresh_tokens 4 扩展字段 ───────────────


async def test_s4_refresh_tokens_4_extension_fields_exist(db_session):
    cols = (
        (
            await db_session.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='refresh_tokens'"
                )
            )
        )
        .scalars()
        .all()
    )
    cols_set = set(cols)
    for required in ("device_info", "ip", "user_agent", "last_seen_at"):
        assert required in cols_set, f"refresh_tokens missing {required}"


# ─────────────── S4b auth_audit_log CHECK ───────────────


async def test_s4b_auth_audit_action_type_check_rejects_unknown(db_session):
    """尝试 INSERT 一个非允许值 → CHECK 约束失败。"""
    from uuid import uuid4

    from api.auth.password import hash_password
    from api.models.user import AuthAuditLog, User

    user = User(
        email=f"check-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("hunter2hunter"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()

    bad = AuthAuditLog(user_id=user.id, action_type="user.unknown_event_type", metadata_={})
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception as exc:
        msg = str(exc)
        raised = True
        assert "ck_auth_audit_action_type" in msg or "check" in msg.lower()
    finally:
        await db_session.rollback()
    assert raised


# ─────────────── S6 / S7 / S8 CHECK 约束 ───────────────


async def test_s7_users_role_check_rejects_unknown(db_session):
    from uuid import uuid4

    from api.auth.password import hash_password
    from api.models.user import User

    bad = User(
        email=f"r-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("hunter2hunter"),
        role="super_admin",  # 非法
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised


async def test_s8_users_status_check_rejects_unknown(db_session):
    from uuid import uuid4

    from api.auth.password import hash_password
    from api.models.user import User

    bad = User(
        email=f"s-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("hunter2hunter"),
        role="user",
        status="frozen",  # 非法
        failed_login_count=0,
        version=1,
    )
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised


# ─────────────── S5c / S5d CI grep 守护 ───────────────


def test_s5c_no_reserved_model_imported_in_services_or_routers():
    """预留 4 model 在 services / routers 下零引用（design §9 R-X 守护）。"""
    forbidden = ["PasswordResetToken", "InviteCode", "AuthIdentity", "EmailChangeRequest"]
    pattern = r"from api\.models\.user import .*(" + "|".join(forbidden) + ")"
    result = subprocess.run(
        ["grep", "-rE", pattern, "api/services/", "api/routers/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, f"reserved model leaked into services/routers:\n{result.stdout}"


def test_s5d_no_router_directly_calls_user_dao_or_auth_service_except_auth():
    """S5d (M02 子片 4 修): 守护精确化 — 除 routers/auth.py 外的 router 禁直调 user_dao / auth_service。

    原规则 grep `from api.models.user import (User|RefreshToken)` 误命中 M02 router 合法
    type hint (current_user 返回 User);改为 grep dao/service 业务 import,允许 model type hint.
    """
    pattern = r"from api\.(dao\.user_dao|services\.auth_service) import"
    result = subprocess.run(
        ["grep", "-rE", pattern, "api/routers/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    leaks = [line for line in result.stdout.splitlines() if "api/routers/auth.py" not in line]
    assert not leaks, (
        f"non-auth router directly imports M01 dao/service (走 routers/auth.current_user 复用):\n"
        f"{leaks}"
    )


def test_s5e_ci_lint_script_is_runnable_and_passes():
    """ci-lint.sh 自身能跑通 + R13-1 守护通过（22=22）。"""
    result = subprocess.run(
        ["bash", "scripts/ci-lint.sh"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "R13-1" in result.stdout


# ─────────────── S11 列长度约束 ───────────────


async def test_s11_email_max_length_320_rejects_overlong(db_session):
    from uuid import uuid4

    from api.auth.password import hash_password
    from api.models.user import User

    bad = User(
        email=("a" * 350) + f"{uuid4().hex[:4]}@example.com",
        name="X",
        password_hash=hash_password("hunter2hunter"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised
