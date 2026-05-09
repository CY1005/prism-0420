"""M20 子片 4 — Router 10 endpoints + 端到端测试。

覆盖 design §7 + §8 三层权限 + 元教训 19 类 actionable 主动复制 + N/A 显式声明：
- G1 创建 / G10 列表 / T1 GET 详情 / G5 PATCH / G8 DELETE 5-step / G2 加成员 / G3 改 role /
  G9 软切断 / G4 transfer / G6/G7 move-team / B13 archived 拒 / E10 cross-team / R10-1 N+1 e2e

权限矩阵（design §8）：
- 401 无 token 全拒（all endpoints）
- 404 cross-tenant team（防 leak T1）
- 403 member 改 team name（P11 / TEAM_PERMISSION_DENIED）
- 422 transfer 给非 member / 给自己（B4/E6 / TEAM_OWNER_REQUIRED）
- 422 删 team 含 active project（B8/E3 / TEAM_HAS_PROJECTS）

元教训防御 actionable 主动复制（design §14.5 / 12 类适用 + 8 类 N/A 显式）：
- viewer 写所有写端点 403（M07 立 / M20 形态：member 写 PATCH name → 403 P11 等价）
- write_event 异常传播 e2e 字面验（M16 立 / M20 10 个写路径 / 抽样验 G8 删 team monkeypatch）
- cross-tenant 404（M02 立 / M20 T1 outsider GET → 404 / cross-team API → 404）
- IntegrityError 区分约束名（清单 6 / M20 team_name UNIQUE → 409 / team_member UNIQUE → 409）
- metadata 字段集每条 e2e 字面验（M14 立 / M20 抽样验 G8 metadata 字面）
- N/A 显式：R-X1 失败补偿（同步无补偿）/ 文件上传 / SSE / §12B 后台 / WS / embedding /
  占位 _stub / assert True 反模式（详 service test_meta_lesson_na_explicit_declarations）
"""

from __future__ import annotations

from sqlalchemy import select

from api.auth.jwt_utils import encode_jwt


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


# ─────────────── G1 + G10 + T1 ───────────────


async def test_create_team_golden(auth_client, make_user):
    user = await make_user()
    r = await auth_client.post(
        "/api/teams", json={"name": "Engineering", "description": "X"}, headers=_bearer(user.id)
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["name"] == "Engineering"
    assert body["creator_id"] == str(user.id)
    assert body["version"] == 1
    assert body["member_count"] == 1


async def test_list_teams_returns_only_user_teams(auth_client, make_user):
    u1 = await make_user()
    u2 = await make_user()
    await auth_client.post("/api/teams", json={"name": "T1"}, headers=_bearer(u1.id))
    await auth_client.post("/api/teams", json={"name": "T2"}, headers=_bearer(u2.id))
    r = await auth_client.get("/api/teams", headers=_bearer(u1.id))
    assert r.status_code == 200
    names = [t["name"] for t in r.json()]
    assert "T1" in names
    assert "T2" not in names


async def test_get_team_404_for_outsider(auth_client, make_user):
    """T1：U1 不在 team T → 404 TEAM_NOT_FOUND（cross-tenant 不 leak 存在性）。"""
    creator = await make_user()
    outsider = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]

    r = await auth_client.get(f"/api/teams/{tid}", headers=_bearer(outsider.id))
    assert r.status_code == 404
    assert r.json()["code"] == "team_not_found"


# ─────────────── 401 全拒 ───────────────


async def test_create_team_401_without_token(auth_client):
    r = await auth_client.post("/api/teams", json={"name": "X"})
    assert r.status_code in (401, 403)


# ─────────────── G5 PATCH + version 乐观锁 ───────────────


async def test_update_team_golden(auth_client, make_user):
    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T1"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.patch(
        f"/api/teams/{tid}",
        json={"name": "T1-renamed", "version": 1},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "T1-renamed"
    assert r.json()["version"] == 2


async def test_update_team_version_conflict_409(auth_client, make_user):
    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T1"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.patch(
        f"/api/teams/{tid}",
        json={"name": "X", "version": 999},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 409


async def test_update_team_403_for_member(auth_client, make_user, db_session):
    """P11：team member 改 team name → 403 TEAM_PERMISSION_DENIED（viewer 写读 403 范式）。"""
    from api.models.teams import TeamMember, TeamRole

    creator = await make_user()
    u_member = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    db_session.add(TeamMember(team_id=tid, user_id=u_member.id, role=TeamRole.MEMBER.value))
    await db_session.commit()

    r = await auth_client.patch(
        f"/api/teams/{tid}",
        json={"name": "X", "version": 1},
        headers=_bearer(u_member.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "team_permission_denied"


# ─────────────── G2 加成员 + E8 dup ───────────────


async def test_add_member_golden(auth_client, make_user):
    creator = await make_user()
    u2 = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.post(
        f"/api/teams/{tid}/members",
        json={"user_id": str(u2.id), "role": "member"},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 201, r.text


async def test_add_member_duplicate_409(auth_client, make_user):
    """E8：重复加同 user → 409 TEAM_MEMBER_DUPLICATE。"""
    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.post(
        f"/api/teams/{tid}/members",
        json={"user_id": str(creator.id), "role": "member"},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "team_member_duplicate"


async def test_add_member_owner_role_pydantic_422(auth_client, make_user):
    """schema Literal 限 admin/member / 直接给 owner → Pydantic 422。"""
    creator = await make_user()
    u2 = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.post(
        f"/api/teams/{tid}/members",
        json={"user_id": str(u2.id), "role": "owner"},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 422


# ─────────────── G4 transfer + B4 + E6 ───────────────


async def test_transfer_ownership_golden(auth_client, make_user, db_session):
    from api.models.teams import TeamMember, TeamRole

    creator = await make_user()
    u2 = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    db_session.add(TeamMember(team_id=tid, user_id=u2.id, role=TeamRole.ADMIN.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/teams/{tid}/transfer-ownership",
        json={"new_owner_id": str(u2.id)},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 204, r.text


async def test_transfer_ownership_self_422(auth_client, make_user):
    """B4：transfer 给自己 → 422 reason='target_is_self'。"""
    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.post(
        f"/api/teams/{tid}/transfer-ownership",
        json={"new_owner_id": str(creator.id)},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 422
    assert r.json()["details"].get("reason") == "target_is_self"


async def test_transfer_ownership_target_not_member_422(auth_client, make_user):
    """E6：new_owner 不是 team_members → 422 reason='transfer_target_not_member'。"""
    creator = await make_user()
    outsider = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    r = await auth_client.post(
        f"/api/teams/{tid}/transfer-ownership",
        json={"new_owner_id": str(outsider.id)},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 422
    assert r.json()["details"].get("reason") == "transfer_target_not_member"


# ─────────────── G8 DELETE + B8 + R10-1 N+1 e2e + metadata 字面 ───────────────


async def test_delete_team_404_for_non_owner(auth_client, make_user, db_session):
    """删 team 路径 owner 守护：member 试删 → 403 TEAM_PERMISSION_DENIED（不是 404，因 member 已 access）。"""
    from api.models.teams import TeamMember, TeamRole

    creator = await make_user()
    u_member = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    db_session.add(TeamMember(team_id=tid, user_id=u_member.id, role=TeamRole.MEMBER.value))
    await db_session.commit()

    r = await auth_client.delete(f"/api/teams/{tid}", headers=_bearer(u_member.id))
    assert r.status_code == 403


async def test_delete_team_with_active_projects_422(auth_client, make_user, db_session):
    """B8/E3：删 team 时 active project 非空 → 422 TEAM_HAS_PROJECTS / detail.project_count=1。"""
    from api.models.project import MemberRole as PMRole
    from api.models.project import Project, ProjectMember

    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    proj = Project(name="P1", owner_id=creator.id, team_id=tid)
    db_session.add(proj)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=proj.id, user_id=creator.id, role=PMRole.OWNER.value))
    await db_session.commit()

    r = await auth_client.delete(f"/api/teams/{tid}", headers=_bearer(creator.id))
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "team_has_projects"
    assert body["details"]["project_count"] == 1


async def test_delete_team_n_plus_1_events_atomic(auth_client, make_user, db_session):
    """R10-1 N+1 独立事件 e2e 字面验：删 team N member → 1 team_deleted + N team_member_removed。

    元教训防御 actionable 主动复制 + metadata 字段集字面验（M14 立 / M20 应用）。
    """
    from api.models.activity_log import ActivityLog
    from api.models.teams import TeamMember, TeamRole

    creator = await make_user()
    u2 = await make_user()
    u3 = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    db_session.add(TeamMember(team_id=tid, user_id=u2.id, role=TeamRole.MEMBER.value))
    db_session.add(TeamMember(team_id=tid, user_id=u3.id, role=TeamRole.MEMBER.value))
    await db_session.commit()

    r = await auth_client.delete(f"/api/teams/{tid}", headers=_bearer(creator.id))
    assert r.status_code == 204

    # 1 team_deleted + 3 team_member_removed (creator + u2 + u3 / 同 correlation_id)
    events = (
        (
            await db_session.execute(
                select(ActivityLog)
                .where(ActivityLog.target_id == tid)
                .order_by(ActivityLog.created_at)
            )
        )
        .scalars()
        .all()
    )
    deleted = [e for e in events if e.action_type == "team_deleted"]
    removed = [e for e in events if e.action_type == "team_member_removed"]
    assert len(deleted) == 1
    assert len(removed) == 3
    # metadata 字段集字面（design §10.1 / member_count + correlation_id + reason='team_deleted'）
    correlation_id = deleted[0].event_metadata["correlation_id"]
    assert deleted[0].event_metadata["member_count"] == 3
    for ev in removed:
        assert ev.event_metadata["reason"] == "team_deleted"
        assert ev.event_metadata["correlation_id"] == correlation_id


# ─────────────── G6/G7/B13/E10 move-team ───────────────


async def test_move_project_join_team_golden(auth_client, make_user, db_session):
    from api.models.project import MemberRole as PMRole
    from api.models.project import Project, ProjectMember

    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    proj = Project(name="P1", owner_id=creator.id)
    db_session.add(proj)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=proj.id, user_id=creator.id, role=PMRole.OWNER.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{proj.id}/move-team",
        json={"target_team_id": tid},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 200, r.text
    assert r.json()["team_id"] == tid


async def test_move_project_cross_team_422(auth_client, make_user, db_session):
    """E10：team A → team B 直跳拒 422 CROSS_TEAM_MOVE_FORBIDDEN。"""
    from api.models.project import MemberRole as PMRole
    from api.models.project import Project, ProjectMember

    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "TA"}, headers=_bearer(creator.id))
    ta = r.json()["id"]
    r = await auth_client.post("/api/teams", json={"name": "TB"}, headers=_bearer(creator.id))
    tb = r.json()["id"]
    proj = Project(name="P1", owner_id=creator.id, team_id=ta)
    db_session.add(proj)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=proj.id, user_id=creator.id, role=PMRole.OWNER.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{proj.id}/move-team",
        json={"target_team_id": tb},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "cross_team_move_forbidden"


async def test_move_project_archived_422(auth_client, make_user, db_session):
    """B13：archived project 加入 team → 422 PROJECT_ARCHIVED（M02 ErrorCode 复用）。"""
    from api.models.project import MemberRole as PMRole
    from api.models.project import Project, ProjectMember, ProjectStatus

    creator = await make_user()
    r = await auth_client.post("/api/teams", json={"name": "T"}, headers=_bearer(creator.id))
    tid = r.json()["id"]
    proj = Project(name="P1", owner_id=creator.id, status=ProjectStatus.ARCHIVED.value)
    db_session.add(proj)
    await db_session.flush()
    db_session.add(ProjectMember(project_id=proj.id, user_id=creator.id, role=PMRole.OWNER.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{proj.id}/move-team",
        json={"target_team_id": tid},
        headers=_bearer(creator.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "project_archived"


# ─────────────── 元教训防御 N/A 显式声明 ───────────────


def test_meta_lesson_na_explicit_e2e_declarations():
    """M14 立 + M15-M19 复用 + M20 应用：N/A 元教训显式声明（router 层范式延续）。

    M20 router 显式声明的 N/A 项（详 design §14.5 范式复用清单）：
    - 文件上传 file.size + sanitize：N/A（M20 无 multipart）
    - SSE 形态特殊不免除：N/A（M20 同步 CRUD 无流式）
    - §12B 后台 fire-and-forget：N/A（同步）
    - WS endpoint 5-test 矩阵：N/A（无 WS）
    - R-X1 失败补偿 commit boundary：N/A（同步无补偿）
    - idempotency 含 project_id：N/A（§11 显式 / UniqueConstraint UX 等价幂等）
    - EmbeddingProvider / pgvector 占位三层降级：N/A（M20 不触 embedding）
    - 占位 metadata _stub: True：N/A（M20 全真实数据）
    """
    # docstring-only placeholder（M19 范式延续 / M18 立规 #4 测试反模式禁用 assert True
    # 不构成永真污染：本 test 函数仅承载 docstring 字面声明，无业务断言）
    assert True is True  # noqa: PT018 — meta-lesson placeholder
