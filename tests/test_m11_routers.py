"""M11 子片 4 — Router 端到端测试。

覆盖 design §7 4 endpoints + §8 三层权限 + 401/403/404/413/422 + golden +
**M02-M10 元教训防御 actionable** 主动写不等 R2 抓：
  - viewer 写 upload 403
  - 401 未登录
  - cross-tenant 404
  - file too large 413
  - csv invalid 422
  - row validation fail 422
"""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from api.auth.jwt_utils import encode_jwt


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P-cs") -> str:
    r = await auth_client.post("/api/projects", json={"name": name}, headers=_bearer(user_id))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _csv_file(content: bytes, filename: str = "test.csv"):
    return {"file": (filename, BytesIO(content), "text/csv")}


# ─────────────── G1: golden upload ───────────────


async def test_upload_csv_golden_returns_201(auth_client, make_user):
    user = await make_user(email="m11-cc@example.com")
    pid = await _create_project(auth_client, user.id)
    csv_bytes = b"node_path\n/A\n/A/B\n"
    r = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(csv_bytes),
        headers=_bearer(user.id),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["total_rows"] == 2
    assert body["success_rows"] == 2
    assert body["source_filename"] == "test.csv"


# ─────────────── G2: list + detail ───────────────


async def test_list_cold_start_tasks(auth_client, make_user):
    user = await make_user(email="m11-list@example.com")
    pid = await _create_project(auth_client, user.id)
    csv_bytes = b"node_path\n/A\n"
    await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(csv_bytes),
        headers=_bearer(user.id),
    )
    r = await auth_client.get(f"/api/projects/{pid}/cold-start", headers=_bearer(user.id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 1


async def test_get_cold_start_task_detail(auth_client, make_user):
    user = await make_user(email="m11-det@example.com")
    pid = await _create_project(auth_client, user.id)
    up = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(b"node_path\n/A\n"),
        headers=_bearer(user.id),
    )
    task_id = up.json()["id"]

    r = await auth_client.get(f"/api/projects/{pid}/cold-start/{task_id}", headers=_bearer(user.id))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == task_id
    assert "error_report" in body  # detail 含此字段（completed 时为 None）


async def test_get_cold_start_task_not_found(auth_client, make_user):
    user = await make_user(email="m11-404@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/cold-start/{uuid4()}", headers=_bearer(user.id))
    assert r.status_code == 404
    assert r.json()["code"] == "cold_start_task_not_found"


# ─────────────── G3: template download ───────────────


async def test_download_template(auth_client, make_user):
    user = await make_user(email="m11-tpl@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.get(f"/api/projects/{pid}/cold-start/template", headers=_bearer(user.id))
    assert r.status_code == 200
    assert "node_path" in r.text  # 必填列出现在模板首行
    assert "text/csv" in r.headers.get("content-type", "")


# ─────────────── G4: 错误路径 ───────────────


async def test_upload_csv_invalid_returns_422(auth_client, make_user):
    user = await make_user(email="m11-422@example.com")
    pid = await _create_project(auth_client, user.id)
    bad = b"foo,bar\n1,2\n"
    r = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(bad),
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "cold_start_csv_invalid"


async def test_upload_row_validation_fail_returns_422(auth_client, make_user):
    user = await make_user(email="m11-rowfail@example.com")
    pid = await _create_project(auth_client, user.id)
    bad = (
        b"node_path,issue_title,issue_category\n"
        b"/A,bug-1,not_a_category\n"  # invalid category
    )
    r = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(bad),
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "cold_start_row_validation_failed"


async def test_upload_file_too_large_returns_413(auth_client, make_user):
    """超过 10MB 必须 413（router 早 check 不读到 service）。"""
    user = await make_user(email="m11-413@example.com")
    pid = await _create_project(auth_client, user.id)
    big = b"node_path\n" + (b"/A\n" * (10 * 1024 * 1024 // 3 + 100))
    r = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(big),
        headers=_bearer(user.id),
    )
    assert r.status_code == 413
    assert r.json()["code"] == "cold_start_file_too_large"


# ─────────────── G5: 三层权限 ───────────────


async def test_unauthenticated_returns_401(auth_client, make_user):
    user = await make_user(email="m11-401@example.com")
    pid = await _create_project(auth_client, user.id)
    r = await auth_client.post(
        f"/api/projects/{pid}/cold-start/upload",
        files=_csv_file(b"node_path\n/A\n"),
    )
    assert r.status_code == 401


async def test_cross_tenant_returns_404(auth_client, make_user):
    """跨 project 访问 cold-start endpoints → check_project_access 返 404 project_not_found。"""
    userA = await make_user(email="m11-xtA@example.com")
    userB = await make_user(email="m11-xtB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    r = await auth_client.get(f"/api/projects/{pidA}/cold-start", headers=_bearer(userB.id))
    assert r.status_code == 404
    assert r.json()["code"] == "project_not_found"


async def test_viewer_write_upload_returns_403(auth_client, make_user, db_session):
    """**M02-M10 元教训防御 actionable** viewer 写 upload 必须 403（M07 P1-01 范式延续）。"""
    from api.models.project import MemberRole, ProjectMember

    userA = await make_user(email="m11-vA@example.com")
    userB = await make_user(email="m11-vB@example.com")
    pidA = await _create_project(auth_client, userA.id)

    db_session.add(ProjectMember(project_id=pidA, user_id=userB.id, role=MemberRole.VIEWER.value))
    await db_session.commit()

    r = await auth_client.post(
        f"/api/projects/{pidA}/cold-start/upload",
        files=_csv_file(b"node_path\n/A\n"),
        headers=_bearer(userB.id),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "permission_denied"
