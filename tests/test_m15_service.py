"""M15 子片 3 — ActivityStreamService 单元测试（design §6 + §8）。

覆盖：
- _check_activity_audit_access（project 不存在 / non-member / viewer→forbidden /
  editor / owner）
- list_stream golden path（含 user_name JOIN + metadata 映射 + has_more）
- list_stream filter 转发到 DAO（ActionType/TargetType Enum → str.value）
- has_more 首页 vs 后续 page 行为差异
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    ActivityStreamForbiddenError,
    ActivityStreamProjectNotFoundError,
)
from api.models.project import ProjectMember
from api.schemas.activity_stream_schema import (
    ActionType,
    ActivityStreamFilter,
)
from api.services.activity_stream_service import ActivityStreamService


@pytest.fixture()
def svc() -> ActivityStreamService:
    return ActivityStreamService()


# ─────────────── M15-SVC-T1 _check / project 不存在 ───────────────


async def test_check_access_project_not_found_raises(db_session, make_user, svc):
    user = await make_user()
    with pytest.raises(ActivityStreamProjectNotFoundError):
        await svc._check_activity_audit_access(db_session, user.id, uuid4())


# ─────────────── M15-SVC-T2 _check / 非成员 ───────────────


async def test_check_access_non_member_raises(db_session, make_user, make_project, svc):
    user_a = await make_user()
    _, proj = await make_project()
    with pytest.raises(ActivityStreamProjectNotFoundError):
        await svc._check_activity_audit_access(db_session, user_a.id, proj.id)


# ─────────────── M15-SVC-T3 _check / viewer 403 ───────────────


async def test_check_access_viewer_raises_forbidden(db_session, make_user, make_project, svc):
    """C-5：viewer 不可审计；与 project 不存在区分语义（403 vs 404）。"""
    other = await make_user()
    owner, proj = await make_project()
    db_session.add(ProjectMember(project_id=proj.id, user_id=other.id, role="viewer"))
    await db_session.flush()
    with pytest.raises(ActivityStreamForbiddenError):
        await svc._check_activity_audit_access(db_session, other.id, proj.id)


# ─────────────── M15-SVC-T4 _check / editor 通过 ───────────────


async def test_check_access_editor_passes(db_session, make_user, make_project, svc):
    other = await make_user()
    owner, proj = await make_project()
    db_session.add(ProjectMember(project_id=proj.id, user_id=other.id, role="editor"))
    await db_session.flush()
    # 不抛即通过
    await svc._check_activity_audit_access(db_session, other.id, proj.id)


# ─────────────── M15-SVC-T5 _check / owner 通过 ───────────────


async def test_check_access_owner_passes(db_session, make_project_with_member, svc):
    owner, proj = await make_project_with_member()
    await svc._check_activity_audit_access(db_session, owner.id, proj.id)


# ─────────────── M15-SVC-T6 list_stream golden + user_name JOIN ───────────────


async def test_list_stream_returns_response_with_user_name(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
        summary="创建了项目",
    )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(),
    )
    assert resp.total == 1
    assert resp.project_id == proj.id
    assert len(resp.items) == 1
    item = resp.items[0]
    assert item.user_name == user.name
    assert item.action_type == ActionType.project_created


# ─────────────── M15-SVC-T7 list_stream metadata 映射 ───────────────


async def test_list_stream_metadata_field_mapped(
    db_session, make_project_with_member, make_activity_log, svc
):
    """SA event_metadata（Python 属性）→ schema metadata（外部字段）映射正确。"""
    user, proj = await make_project_with_member()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_updated",
        target_type="node",
        target_id="00000000-0000-0000-0000-000000000001",
        event_metadata={"updated_fields": ["title"]},
    )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(),
    )
    assert resp.items[0].metadata == {"updated_fields": ["title"]}


# ─────────────── M15-SVC-T8 list_stream 权限拒绝传播 ───────────────


async def test_list_stream_propagates_permission_error(db_session, make_user, make_project, svc):
    """non-member → ActivityStreamProjectNotFoundError 直传播（不静默降级为空 list）。"""
    other = await make_user()
    _, proj = await make_project()
    with pytest.raises(ActivityStreamProjectNotFoundError):
        await svc.list_stream(
            db_session,
            actor_user_id=other.id,
            project_id=proj.id,
            filt=ActivityStreamFilter(),
        )


# ─────────────── M15-SVC-T9 list_stream filter 转发（Enum → value）───────────────


async def test_list_stream_filter_action_type_enum_forwarded(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="node_created",
        target_type="node",
        target_id="00000000-0000-0000-0000-000000000002",
    )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(action_type=ActionType.node_created),
    )
    assert resp.total == 1
    assert resp.items[0].action_type == ActionType.node_created


# ─────────────── M15-SVC-T10 has_more 首页（total 精确）───────────────


async def test_list_stream_has_more_first_page_with_more(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    for _ in range(3):
        await make_activity_log(
            project_id=proj.id,
            user_id=user.id,
            action_type="node_created",
            target_type="node",
            target_id=str(uuid4()),
        )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(page=1, page_size=2),
    )
    assert resp.total == 3
    assert resp.has_more is True


async def test_list_stream_has_more_first_page_no_more(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    await make_activity_log(
        project_id=proj.id,
        user_id=user.id,
        action_type="project_created",
        target_type="project",
        target_id=str(proj.id),
    )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(page=1, page_size=10),
    )
    assert resp.total == 1
    assert resp.has_more is False


# ─────────────── M15-SVC-T11 has_more 后续 page（total=None / rows 撑满）───────────────


async def test_list_stream_has_more_later_page_full_means_more(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    for _ in range(5):
        await make_activity_log(
            project_id=proj.id,
            user_id=user.id,
            action_type="node_created",
            target_type="node",
            target_id=str(uuid4()),
        )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(page=2, page_size=2),
    )
    # page 2 of 5 items / page_size=2 → page 2 撑满 → has_more True
    assert resp.total is None
    assert resp.has_more is True


async def test_list_stream_has_more_later_page_partial_means_no_more(
    db_session, make_project_with_member, make_activity_log, svc
):
    user, proj = await make_project_with_member()
    for _ in range(3):
        await make_activity_log(
            project_id=proj.id,
            user_id=user.id,
            action_type="node_created",
            target_type="node",
            target_id=str(uuid4()),
        )
    resp = await svc.list_stream(
        db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        filt=ActivityStreamFilter(page=2, page_size=2),
    )
    # page 2 of 3 items / page_size=2 → page 2 仅 1 行 < 2 → has_more False
    assert resp.total is None
    assert resp.has_more is False
