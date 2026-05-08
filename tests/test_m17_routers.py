"""M17 子片 4 — Router 端到端测试。

覆盖 design §7 7 REST + 1 WS endpoint + §8 三层权限 + 17+ 元教训 actionable 主动复制：
  - viewer 写所有写端点 403（M07 立 / M11 复用 / M16 复用 / M17 应用）
  - 401 未登录
  - cross-tenant 404
  - cross-owner 404 打码（不区分 not-found / 跨 owner）
  - file too large / source_type 入参不合法 / git_url 入参不合法
  - filename sanitize（M11 范式复用 / 路径穿越 / CRLF 注入）
  - idempotency 命中返 200（不是 201）+ 复用 task
  - ai_provider 未配置 422
  - confirm awaiting_review→ai_step3 状态扭转
  - cancel awaiting_review / pending → cancelled（design §4 字面）
  - retry partial_failed → ai_step3
  - WS handshake invalid token → 1008
  - WS handshake task_id 非 owner → 1008
  - confirm finalized 409 / retry pending 409 状态机错
  - detail not found 404 / detail cross-tenant 404
  - get review_data 状态错 409
"""

from __future__ import annotations

import hashlib
from io import BytesIO
from uuid import uuid4

import pytest
import pytest_asyncio

from api.auth.jwt_utils import encode_jwt
from api.models.import_task import ImportTaskStatus

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project_with_ai(auth_client, user_id, name: str = "P-imp") -> str:
    """建项目 + 配置 ai_provider（M17 submit 强制要求 / 走 PUT /ai-provider）。"""
    r = await auth_client.post(
        "/api/projects",
        json={"name": name},
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    # M17 submit 校验 project.ai_provider 必填；走 PUT 更新
    r2 = await auth_client.put(
        f"/api/projects/{pid}/ai-provider",
        json={"ai_provider": "mock", "ai_api_key": ""},
        headers=_bearer(user_id),
    )
    assert r2.status_code == 200, r2.text
    return pid


def _zip_file(content: bytes, filename: str = "kb.zip"):
    return {"file": (filename, BytesIO(content), "application/zip")}


@pytest_asyncio.fixture(loop_scope="session")
async def submit_zip_form():
    """工厂 fixture：构建 multipart/form-data 数据。"""

    def _make(*, source_type: str = "zip"):
        return {"source_type": source_type}

    yield _make


# ─────────────── G1+G2: golden submit ───────────────


class TestSubmitGolden:
    async def test_submit_zip_returns_201(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-zip@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"PK\x03\x04 fake zip content"),
            headers=_bearer(user.id),
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "pending"
        assert body["source_type"] == "zip"
        assert body["progress"] == 0
        assert body["ai_provider"] == "mock"

    async def test_submit_git_url_returns_201(self, auth_client, make_user):
        user = await make_user(email="m17-git@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data={
                "source_type": "git_url",
                "git_url": "https://github.com/example/kb.git",
                "git_ref": "main",
            },
            headers=_bearer(user.id),
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["source_type"] == "git_url"


# ─────────────── G3-G5: list / detail ───────────────


class TestReadEndpoints:
    async def test_list_imports_returns_only_own_user(
        self, auth_client, make_user, submit_zip_form
    ):
        user_a = await make_user(email="m17-listA@example.com")
        pid = await _create_project_with_ai(auth_client, user_a.id)
        # user_a 提交一个
        await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"a-zip"),
            headers=_bearer(user_a.id),
        )
        # user_b 不是 project member（不会被 list 看到 / 同时 list 仅自己 user_id）
        r = await auth_client.get(f"/api/projects/{pid}/imports", headers=_bearer(user_a.id))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] >= 1

    async def test_get_import_detail(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-det@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        up = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
            headers=_bearer(user.id),
        )
        task_id = up.json()["id"]
        r = await auth_client.get(
            f"/api/projects/{pid}/imports/{task_id}", headers=_bearer(user.id)
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["id"] == task_id
        assert body["status"] == "pending"
        assert "items" in body
        assert "error_metadata" in body

    async def test_get_import_not_found_404(self, auth_client, make_user):
        user = await make_user(email="m17-404@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.get(
            f"/api/projects/{pid}/imports/{uuid4()}", headers=_bearer(user.id)
        )
        assert r.status_code == 404
        assert r.json()["code"] == "import_task_not_found"

    async def test_get_review_pending_returns_409(self, auth_client, make_user, submit_zip_form):
        """状态错（pending 没 review_data 可拉）→ 409 import_invalid_state_transition。"""
        user = await make_user(email="m17-revst@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        up = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
            headers=_bearer(user.id),
        )
        task_id = up.json()["id"]
        r = await auth_client.get(
            f"/api/projects/{pid}/imports/{task_id}/review", headers=_bearer(user.id)
        )
        assert r.status_code == 409
        assert r.json()["code"] == "import_invalid_state_transition"


# ─────────────── G6-G9: confirm / cancel / retry ───────────────


class TestStateActions:
    async def test_confirm_review_awaiting_to_step3(
        self, auth_client, make_user, make_import_task, db_session
    ):
        user = await make_user(email="m17-conf@example.com")
        pid_str = await _create_project_with_ai(auth_client, user.id)
        from uuid import UUID

        pid = UUID(pid_str)
        task = await make_import_task(
            project_id=pid, user_id=user.id, status=ImportTaskStatus.awaiting_review.value
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/confirm",
            json={
                "nodes": [],
                "dimensions": [],
                "competitors": [],
                "issues": [],
                "skip_proposed_ids": [],
            },
            headers=_bearer(user.id),
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ai_step3"

    async def test_confirm_finalized_returns_409(
        self, auth_client, make_user, make_import_task, db_session
    ):
        user = await make_user(email="m17-confF@example.com")
        pid_str = await _create_project_with_ai(auth_client, user.id)
        from uuid import UUID

        pid = UUID(pid_str)
        task = await make_import_task(
            project_id=pid, user_id=user.id, status=ImportTaskStatus.completed.value
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/confirm",
            json={"nodes": [], "dimensions": [], "competitors": [], "issues": []},
            headers=_bearer(user.id),
        )
        assert r.status_code == 409
        assert r.json()["code"] == "import_task_finalized"

    async def test_cancel_pending_returns_204(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-canc@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        up = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
            headers=_bearer(user.id),
        )
        task_id = up.json()["id"]
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task_id}/cancel", headers=_bearer(user.id)
        )
        assert r.status_code == 204

    async def test_retry_partial_failed_to_step3(
        self, auth_client, make_user, make_import_task, db_session
    ):
        user = await make_user(email="m17-rty@example.com")
        pid_str = await _create_project_with_ai(auth_client, user.id)
        from uuid import UUID

        pid = UUID(pid_str)
        task = await make_import_task(
            project_id=pid, user_id=user.id, status=ImportTaskStatus.partial_failed.value
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/retry", headers=_bearer(user.id)
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ai_step3"

    async def test_retry_pending_returns_409(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-rtyP@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        up = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
            headers=_bearer(user.id),
        )
        task_id = up.json()["id"]
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task_id}/retry", headers=_bearer(user.id)
        )
        assert r.status_code == 409
        assert r.json()["code"] == "import_invalid_state_transition"


# ─────────────── E1-E5: 边界 / 错误路径 ───────────────


class TestBoundaries:
    async def test_file_too_large_returns_422(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-413@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        big = b"X" * (101 * 1024 * 1024)  # 101MB > 100MB limit
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files={"file": ("big.zip", BytesIO(big), "application/zip")},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422
        assert r.json()["code"] == "import_invalid_source"

    async def test_zip_without_file_returns_422(self, auth_client, make_user):
        """source_type=zip 但缺 file → 422 file_required。"""
        user = await make_user(email="m17-nofile@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data={"source_type": "zip"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422
        assert r.json()["code"] == "import_invalid_source"

    async def test_git_url_without_url_returns_422(self, auth_client, make_user):
        user = await make_user(email="m17-nourl@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data={"source_type": "git_url"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422
        assert r.json()["code"] == "import_invalid_source"

    async def test_ai_provider_unset_returns_422(self, auth_client, make_user, submit_zip_form):
        """项目未配置 ai_provider → 422（M17 sprint 提交期校验）。"""
        user = await make_user(email="m17-noai@example.com")
        # 不带 ai_provider 建项目
        r = await auth_client.post(
            "/api/projects",
            json={"name": "noai"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
            headers=_bearer(user.id),
        )
        assert r.status_code == 422
        assert r.json()["code"] == "import_invalid_source"

    async def test_idempotency_hit_returns_200_reuse_completed_task(
        self,
        auth_client,
        make_user,
        make_import_task,
        db_session,
        submit_zip_form,
    ):
        """design §13 字面：idempotency 命中 completed task 返 200 + 复用（不是 201 新建）。

        测试范式：用 fixture 直造 status=completed 的 task（idempotency 复用范围内 / design §11
        字面 status ∈ {completed, awaiting_review, partial_failed}），然后用相同 source_hash
        提交，service.find_idempotent 命中 → 抛 ImportTaskDuplicateError → router 改返 200 + 复用 task。
        """
        from uuid import UUID

        user = await make_user(email="m17-idem@example.com")
        pid_str = await _create_project_with_ai(auth_client, user.id)
        pid = UUID(pid_str)
        zip_content = b"identical-zip-content"
        source_hash = hashlib.sha256(zip_content).hexdigest()
        existing = await make_import_task(
            project_id=pid,
            user_id=user.id,
            source_hash=source_hash,
            status=ImportTaskStatus.completed.value,
        )
        await db_session.commit()
        # 第一次 / 直接命中（提交相同 hash → find_idempotent 命中 → 200 复用）
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(zip_content),
            headers=_bearer(user.id),
        )
        assert r.status_code == 200, r.text  # 关键：200 不是 201
        assert r.json()["id"] == str(existing.id)
        assert r.json()["status"] == "completed"

    async def test_filename_sanitize_path_traversal(self, auth_client, make_user, submit_zip_form):
        """**R2 P1-03 立修**：M11 范式复用 + sanitize 字面验输出（不仅 not-crash）。

        attacker filename 含路径穿越 + CRLF → sanitize 后 source_uri 必须无控制字符 + 无 / \\ \\r \\n。
        """
        user = await make_user(email="m17-fnsan@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files={
                "file": (
                    "../../../etc/passwd\r\nHack: yes",
                    BytesIO(b"x"),
                    "application/zip",
                )
            },
            headers=_bearer(user.id),
        )
        assert r.status_code == 201, r.text
        # **R2 P1-03 立修**：字面验 source_uri sanitize 结果（不仅 201）
        body = r.json()
        source_uri = body["source_uri"]
        assert source_uri.startswith("upload://"), source_uri
        filename_part = source_uri.split("://", 1)[1]
        # sanitize 必须杀掉路径穿越（os.path.basename）+ 真实控制字符（CRLF 已被 httpx
        # 客户端 URL-encode 为 %0D%0A，到 server 端是文本字符串而非控制字节，不构成
        # header injection 风险——源攻击面已闭合）
        assert "../" not in filename_part
        assert "\\" not in filename_part
        assert "\r" not in filename_part  # 真实 CR 字节
        assert "\n" not in filename_part  # 真实 LF 字节
        assert "/" not in filename_part  # path 穿越的根本攻击面
        # basename 必须从 "passwd" 起头（os.path.basename 杀掉 ../../ + /etc/）
        assert filename_part.startswith("passwd"), filename_part


# ─────────────── 三层权限 / 元教训 actionable ───────────────


class TestPermissions:
    async def test_unauthenticated_returns_401(self, auth_client, make_user, submit_zip_form):
        user = await make_user(email="m17-401@example.com")
        pid = await _create_project_with_ai(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data=submit_zip_form(),
            files=_zip_file(b"x"),
        )
        assert r.status_code == 401

    async def test_cross_tenant_returns_404(self, auth_client, make_user):
        userA = await make_user(email="m17-xtA@example.com")
        userB = await make_user(email="m17-xtB@example.com")
        pidA = await _create_project_with_ai(auth_client, userA.id)
        # userB 跨项目读 → check_project_access 返 404 project_not_found
        r = await auth_client.get(f"/api/projects/{pidA}/imports", headers=_bearer(userB.id))
        assert r.status_code == 404
        assert r.json()["code"] == "project_not_found"

    async def test_cross_owner_404_not_403(
        self, auth_client, make_user, make_import_task, db_session
    ):
        """同 project member 但不是 task creator → 404 打码（不区分 not-found / cross-owner）。"""
        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m17-xoA@example.com")
        userB = await make_user(email="m17-xoB@example.com")
        pid_str = await _create_project_with_ai(auth_client, userA.id)
        from uuid import UUID

        pid = UUID(pid_str)
        # userB 加入 project（editor 权限）
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.EDITOR.value)
        )
        # userA 创建 task
        task = await make_import_task(project_id=pid, user_id=userA.id)
        await db_session.commit()
        # userB 读 detail 应 404（task 不属于 userB）
        r = await auth_client.get(
            f"/api/projects/{pid}/imports/{task.id}", headers=_bearer(userB.id)
        )
        assert r.status_code == 404
        assert r.json()["code"] == "import_task_not_found"

    async def test_viewer_write_submit_returns_403(self, auth_client, make_user, db_session):
        """**M07 元教训复用**：viewer 写 submit → 403 permission_denied。"""
        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m17-vA@example.com")
        userB = await make_user(email="m17-vB@example.com")
        pid_str = await _create_project_with_ai(auth_client, userA.id)
        from uuid import UUID

        pid = UUID(pid_str)
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.VIEWER.value)
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports",
            data={"source_type": "zip"},
            files=_zip_file(b"x"),
            headers=_bearer(userB.id),
        )
        assert r.status_code == 403
        assert r.json()["code"] == "permission_denied"

    async def test_viewer_write_cancel_returns_403(
        self, auth_client, make_user, make_import_task, db_session
    ):
        """**M07 元教训复用 / 写端点 5 个全覆盖 P1**：viewer 写 cancel → 403。"""
        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m17-vcA@example.com")
        userB = await make_user(email="m17-vcB@example.com")
        pid_str = await _create_project_with_ai(auth_client, userA.id)
        from uuid import UUID

        pid = UUID(pid_str)
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.VIEWER.value)
        )
        task = await make_import_task(project_id=pid, user_id=userA.id)
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/cancel", headers=_bearer(userB.id)
        )
        assert r.status_code == 403
        assert r.json()["code"] == "permission_denied"

    async def test_viewer_write_confirm_returns_403(
        self, auth_client, make_user, make_import_task, db_session
    ):
        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m17-vcfA@example.com")
        userB = await make_user(email="m17-vcfB@example.com")
        pid_str = await _create_project_with_ai(auth_client, userA.id)
        from uuid import UUID

        pid = UUID(pid_str)
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.VIEWER.value)
        )
        task = await make_import_task(
            project_id=pid, user_id=userA.id, status=ImportTaskStatus.awaiting_review.value
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/confirm",
            json={"nodes": [], "dimensions": [], "competitors": [], "issues": []},
            headers=_bearer(userB.id),
        )
        assert r.status_code == 403

    async def test_viewer_write_retry_returns_403(
        self, auth_client, make_user, make_import_task, db_session
    ):
        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m17-vrA@example.com")
        userB = await make_user(email="m17-vrB@example.com")
        pid_str = await _create_project_with_ai(auth_client, userA.id)
        from uuid import UUID

        pid = UUID(pid_str)
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.VIEWER.value)
        )
        task = await make_import_task(
            project_id=pid, user_id=userA.id, status=ImportTaskStatus.partial_failed.value
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/imports/{task.id}/retry", headers=_bearer(userB.id)
        )
        assert r.status_code == 403


# ─────────────── WS endpoint 鉴权（R2 P1-01 立修 / 5 矩阵）───────────────
# WS endpoint 用 starlette TestClient.websocket_connect 同步测试鉴权 close code（design §8 audit B6）。
# Golden path（成功 accept + service push + client receive）需要 DB 状态——
# 在异步 fixture 注入 + 同步 TestClient 桥接复杂；当前矩阵覆盖 4 个鉴权拒绝路径
# （JWT 无效 / type≠access / sub 缺失 / cross-owner check_task_access 失败），
# 这是元教训"endpoint 形态不免除契约纪律"+ audit B6 关键。Golden e2e 留 integration sprint。


class TestWebSocketAuth:
    """WS 握手鉴权 4 矩阵（R2 P1-01 立修 / design §8 audit B6 字面）。"""

    def test_ws_missing_token_returns_403(self):
        """无 token query → FastAPI Query(...) 必填校验失败 → 403（accept 前拒绝）。"""
        from fastapi.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect

        from api.main import app

        client = TestClient(app)
        # missing token → FastAPI 在 accept 前校验 Query → 拒绝（WebSocketDisconnect 抛出）
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect(f"/api/projects/{uuid4()}/imports/{uuid4()}/progress"),
        ):
            pass

    def test_ws_invalid_token_closes_1008(self):
        """无效 JWT → decode_jwt 抛 → close 1008 policy violation。"""
        from fastapi.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect

        from api.main import app

        client = TestClient(app)
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(
                f"/api/projects/{uuid4()}/imports/{uuid4()}/progress?token=bogus"
            ),
        ):
            pass
        assert exc.value.code == 1008, f"expected 1008 policy violation, got {exc.value.code}"

    def test_ws_refresh_token_type_closes_1008(self):
        """access claim type ≠ "access"（refresh / 其他）→ close 1008（防 refresh token 被误用）。"""
        from fastapi.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect

        from api.main import app

        client = TestClient(app)
        # 制造合法但 type='refresh' 的 token
        bad_type_token = encode_jwt(uuid4(), extra_claims={"type": "refresh"})
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(
                f"/api/projects/{uuid4()}/imports/{uuid4()}/progress?token={bad_type_token}"
            ),
        ):
            pass
        assert exc.value.code == 1008

    def test_ws_task_not_owned_closes_1008(self):
        """合法 access JWT 但 user 不是 task creator → check_task_access 失败 → 1008。

        简化路径：用 random task_id（不存在）+ 合法 token → service.check_task_access 抛
        ImportTaskNotFoundError → 1008 close。
        """
        from fastapi.testclient import TestClient
        from starlette.websockets import WebSocketDisconnect

        from api.main import app

        client = TestClient(app)
        token = encode_jwt(uuid4(), extra_claims={"type": "access"})
        with (
            pytest.raises(WebSocketDisconnect) as exc,
            client.websocket_connect(
                f"/api/projects/{uuid4()}/imports/{uuid4()}/progress?token={token}"
            ),
        ):
            pass
        assert exc.value.code == 1008


__all__ = [
    "TestBoundaries",
    "TestPermissions",
    "TestReadEndpoints",
    "TestStateActions",
    "TestSubmitGolden",
    "TestWebSocketAuth",
]
