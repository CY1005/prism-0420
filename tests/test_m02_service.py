"""M02 子片 3 — ProjectService + MemberService tests (critical path + key raises)."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio


async def _make_user(db_session, email: str | None = None):
    from api.auth.password import hash_password
    from api.models.user import User

    user = User(
        email=email or f"u-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("Password123!"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture(loop_scope="session")
async def alice(db_session):
    return await _make_user(db_session, "alice-svc@example.com")


@pytest_asyncio.fixture(loop_scope="session")
async def bob(db_session):
    return await _make_user(db_session, "bob-svc@example.com")


# ─────────────── ProjectService ───────────────


async def test_create_project_inserts_project_and_owner_member(db_session, alice):
    from api.services.project_service import ProjectService

    svc = ProjectService()
    proj = await svc.create_project(db_session, owner_id=alice.id, name="P1")
    assert proj.id is not None
    assert proj.status == "active"

    # owner member created automatically
    members = await svc.members.list_by_project(db_session, proj.id)
    assert len(members) == 1
    assert members[0].user_id == alice.id
    assert members[0].role == "owner"


async def test_create_duplicate_active_name_raises(db_session, alice):
    from api.errors.exceptions import ProjectNameDuplicateError
    from api.services.project_service import ProjectService

    svc = ProjectService()
    await svc.create_project(db_session, owner_id=alice.id, name="DupP")
    with pytest.raises(ProjectNameDuplicateError):
        await svc.create_project(db_session, owner_id=alice.id, name="DupP")


async def test_get_for_user_non_member_raises_not_found(db_session, alice, bob):
    from api.errors.exceptions import ProjectNotFoundError
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="Private")
    with pytest.raises(ProjectNotFoundError):
        await svc.get_for_user(db_session, p.id, bob.id)


async def test_archive_project_idempotent_raises_already_archived(db_session, alice):
    from api.errors.exceptions import ProjectAlreadyArchivedError
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="ToArchive")
    await svc.archive_project(db_session, project_id=p.id, actor_user_id=alice.id)
    with pytest.raises(ProjectAlreadyArchivedError):
        await svc.archive_project(db_session, project_id=p.id, actor_user_id=alice.id)


async def test_archive_by_non_member_raises_not_found(db_session, alice, bob):
    """R1 P2-A 修: 非 member 抛 ProjectNotFoundError 而非 PermissionDeniedError
    (与 get_for_user 行为对齐 + 防 enumeration 攻击)."""
    from api.errors.exceptions import ProjectNotFoundError
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="OwnerOnly")
    with pytest.raises(ProjectNotFoundError):
        await svc.archive_project(db_session, project_id=p.id, actor_user_id=bob.id)


async def test_update_archived_project_raises(db_session, alice):
    """R1 P2-A 修: archived project 不可更新 (design §4 归档=只读快照)."""
    from api.errors.exceptions import ProjectArchivedError
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="ArchUpdP")
    await svc.archive_project(db_session, project_id=p.id, actor_user_id=alice.id)
    with pytest.raises(ProjectArchivedError):
        await svc.update_project(
            db_session,
            project_id=p.id,
            actor_user_id=alice.id,
            changes={"description": "new"},
        )


async def test_invite_by_non_member_raises_not_found(db_session, alice, bob):
    """R1 P2-A 修: 非 member invite_member 抛 NotFound (统一行为)."""
    from api.errors.exceptions import ProjectNotFoundError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService(psvc)
    p = await psvc.create_project(db_session, owner_id=alice.id, name="NonMemInvP")
    other = await _make_user(db_session)
    with pytest.raises(ProjectNotFoundError):
        await msvc.invite_member(
            db_session, project_id=p.id, actor_user_id=bob.id, invited_user_id=other.id
        )


async def test_update_ai_provider_encrypts_key(db_session, alice):
    from api.auth.crypto import decrypt
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="AiP")
    secret = "sk-ant-api-key-very-secret"
    p2 = await svc.update_ai_provider(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        fields={"ai_provider": "claude", "ai_api_key": secret},
    )
    assert p2.ai_provider == "claude"
    assert p2.ai_api_key_enc != secret
    assert decrypt(p2.ai_api_key_enc) == secret


async def test_update_ai_provider_detach_key(db_session, alice):
    """L1-α 4C.3: ai_api_key 显式 None 清空（撤掉 AI 配置）."""
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="AiDetachP")
    await svc.update_ai_provider(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        fields={"ai_provider": "claude", "ai_api_key": "sk-secret"},
    )
    cleared = await svc.update_ai_provider(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        fields={"ai_api_key": None},
    )
    assert cleared.ai_api_key_enc is None
    # ai_provider 保留（未传 = keep）
    assert cleared.ai_provider == "claude"


async def test_get_search_config_returns_defaults(db_session, alice):
    from api.services.project_service import ProjectService

    svc = ProjectService()
    p = await svc.create_project(db_session, owner_id=alice.id, name="SearchP")
    cfg = await svc.get_search_config(db_session, p.id)
    assert cfg.rrf_k == 60
    assert cfg.similarity_threshold == 0.3


# ─────────────── MemberService ───────────────


async def test_invite_member_creates_row(db_session, alice, bob):
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="InvP")
    m = await msvc.invite_member(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        invited_user_id=bob.id,
        role="editor",
    )
    assert m.role == "editor"
    assert m.invited_by == alice.id


async def test_invite_existing_member_raises(db_session, alice, bob):
    from api.errors.exceptions import MemberAlreadyExistsError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="InvDupP")
    await msvc.invite_member(
        db_session, project_id=p.id, actor_user_id=alice.id, invited_user_id=bob.id
    )
    with pytest.raises(MemberAlreadyExistsError):
        await msvc.invite_member(
            db_session, project_id=p.id, actor_user_id=alice.id, invited_user_id=bob.id
        )


async def test_invite_by_viewer_member_raises_permission(db_session, alice, bob):
    """非 owner 但是 member (viewer/editor) 应抛 PermissionDeniedError."""
    from api.errors.exceptions import PermissionDeniedError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService(psvc)
    p = await psvc.create_project(db_session, owner_id=alice.id, name="ViewerInvP")
    # bob 加入为 viewer
    await msvc.invite_member(
        db_session, project_id=p.id, actor_user_id=alice.id, invited_user_id=bob.id, role="viewer"
    )
    other = await _make_user(db_session)
    with pytest.raises(PermissionDeniedError):
        await msvc.invite_member(
            db_session, project_id=p.id, actor_user_id=bob.id, invited_user_id=other.id
        )


async def test_update_member_role(db_session, alice, bob):
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="RoleP")
    await msvc.invite_member(
        db_session, project_id=p.id, actor_user_id=alice.id, invited_user_id=bob.id, role="viewer"
    )
    m = await msvc.update_member_role(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        target_user_id=bob.id,
        new_role="editor",
    )
    assert m.role == "editor"


async def test_cannot_demote_owner(db_session, alice):
    from api.errors.exceptions import MemberCannotRemoveOwnerError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="OwnDemoteP")
    with pytest.raises(MemberCannotRemoveOwnerError):
        await msvc.update_member_role(
            db_session,
            project_id=p.id,
            actor_user_id=alice.id,
            target_user_id=alice.id,
            new_role="editor",
        )


async def test_cannot_remove_owner(db_session, alice):
    from api.errors.exceptions import MemberCannotRemoveOwnerError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="OwnRmP")
    with pytest.raises(MemberCannotRemoveOwnerError):
        await msvc.remove_member(
            db_session,
            project_id=p.id,
            actor_user_id=alice.id,
            target_user_id=alice.id,
        )


async def test_remove_non_existing_member_raises_not_found(db_session, alice):
    from api.errors.exceptions import MemberNotFoundError
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="RmNotFoundP")
    with pytest.raises(MemberNotFoundError):
        await msvc.remove_member(
            db_session,
            project_id=p.id,
            actor_user_id=alice.id,
            target_user_id=uuid4(),
        )


async def test_remove_member(db_session, alice, bob):
    from api.services.project_service import MemberService, ProjectService

    psvc = ProjectService()
    msvc = MemberService()
    p = await psvc.create_project(db_session, owner_id=alice.id, name="RmOkP")
    await msvc.invite_member(
        db_session, project_id=p.id, actor_user_id=alice.id, invited_user_id=bob.id
    )
    deleted = await msvc.remove_member(
        db_session,
        project_id=p.id,
        actor_user_id=alice.id,
        target_user_id=bob.id,
    )
    assert deleted == 1


# ─────────────── C 路径 sprint 实证 (team_id 写入策略) ───────────────


async def test_c_path_team_id_service_writes_existing_team_uuid(db_session, alice):
    """C 路径子选项实证（M20 sprint 升级 2026-05-09）：service 不校验 team_id 合法性
    （DAO 完全允许）/ 但写入存在的 team UUID 即可成功（FK RESTRICT 守 dangling）。

    M02 期 A1=C 中间态：service 不校验 / DAO 直写 / 任意 UUID OK（FK 未启用）。
    M20 sprint 启用 FK RESTRICT 后：service 仍不校验（不引入双源真相）/ DAO 直写 /
    但 team UUID 必须真存在（FK 守 dangling）—— 业务路径在 move-team router/service
    入口校验 team 存在性（设计契约 / 不在 ProjectDAO 层重复）。
    """
    from sqlalchemy import select

    from api.dao.project_dao import ProjectDAO
    from api.models.project import Project
    from api.models.teams import Team

    # 先建一个真 team（FK RESTRICT 守 dangling 后必须存在）
    team = Team(creator_id=alice.id, name="TeamForCPath")
    db_session.add(team)
    await db_session.flush()

    dao = ProjectDAO()
    proj = await dao.create(db_session, name="TeamWriteP", owner_id=alice.id, team_id=team.id)
    await db_session.flush()
    r = await db_session.execute(select(Project).where(Project.id == proj.id))
    assert r.scalar_one().team_id == team.id
