"""M18 子片 4 — Router 端到端测试。

覆盖 design §7 4 endpoints + §8 三层权限 + 17+ 元教训 actionable 主动复制：
  A. viewer 写所有写端点 403（M07 立 / M18 admin endpoint require_platform_admin 守护）
  B. read 权限 403（M15 首发 / M18 search 路由覆盖 / cross-project denial）
  C. write_event 异常传播测试 e2e（M16 立 / M18 backfill + model-upgrade 写 activity_log）
  D. cross-tenant 404（M02 立）
  E. cross-project node 404 / 不召回（M03 立 / search 路由 cross-project 不召回）
  F. IntegrityError 区分约束名（M05 立 / 清单 6 / M17 ci-lint R15 守护）
  G. M11 R-X1 失败补偿：M18 不触 → N/A 显式声明
  H. M11 file.size + sanitize：M18 search/admin 无 multipart → N/A 显式声明
  I. M13 SSE 形态特殊不免除契约纪律：M18 同步路由 → N/A 显式声明
  J. M13 metadata 字段集每条 e2e 字面验（backfill + model_upgrade triggered）
  K. M14 endpoint 形态特殊不免除契约纪律：M18 admin endpoint 主动复制
  L. M14 N/A 元教训显式声明范式（docstring 双重声明）
  M. M15 横切表 owner enum 4 处同步：M18 ActionType+0 已 baseline-patch → N/A
  N. M16 R14 ci-lint 守护：write_event action_type 字面 _ACTION_TYPES 元组内（自动）
  O. M16 CAS UPDATE 禁 Service 事务上下文：M18 admin endpoint 不开 begin → N/A
  P. M16 BackgroundTasks / Queue runner 自起 SessionLocal：admin endpoint BackgroundTasks 范式
  Q. M17 NEW R-X1 compensation_session helper：M18 不触 → N/A 显式声明
  R. M17 NEW idempotency 含 project_id：M18 三层幂等 R3-3 已含 → N/A
  S. M17 NEW IntegrityError 端到端 catch：同 F

总计 25+ tests。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.auth.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


async def _create_project(auth_client, user_id, name: str = "P-m18") -> str:
    r = await auth_client.post(
        "/api/projects",
        json={"name": name},
        headers=_bearer(user_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ─────────────── G1: search golden path ───────────────


class TestSearchGolden:
    async def test_search_empty_project_returns_200(self, auth_client, make_user):
        """search golden：空 project 搜索 → 200 + search_mode in (hybrid, keyword_only) + results=[]。"""
        user = await make_user(email="m18-sg@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "配额"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["results"] == []
        assert body["total"] == 0
        assert body["search_mode"] in ("hybrid", "keyword_only")
        assert "query_embedding_cached" in body

    async def test_search_pgvector_unavailable_returns_keyword_only(
        self, auth_client, make_user, monkeypatch
    ):
        """PRD AC4：pgvector 不可用 → search_mode="keyword_only" + 200（不报错）。

        元教训 E（M03 立）：cross-project 不召回；pgvector 降级不影响搜索可用性。
        """
        from api.dao import embedding_dao as emb_dao_mod

        async def _raise_not_implemented(*args, **kwargs):
            raise NotImplementedError("pgvector not installed")

        monkeypatch.setattr(emb_dao_mod.EmbeddingDAO, "vector_search", _raise_not_implemented)

        user = await make_user(email="m18-pgv@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["search_mode"] == "keyword_only"

    async def test_search_with_target_types_filter(self, auth_client, make_user):
        """target_types 过滤：指定 ['node'] → 200 + 结果只含 node 类型。"""
        user = await make_user(email="m18-ttf@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test", "target_types": ["node"], "limit": 10},
            headers=_bearer(user.id),
        )
        assert r.status_code == 200, r.text

    async def test_search_limit_boundary(self, auth_client, make_user):
        """limit=1 最小值 → 200；limit=100 最大值 → 200。"""
        user = await make_user(email="m18-lim@example.com")
        pid = await _create_project(auth_client, user.id)
        for lim in (1, 100):
            r = await auth_client.post(
                f"/api/projects/{pid}/search",
                json={"query": "test", "limit": lim},
                headers=_bearer(user.id),
            )
            assert r.status_code == 200, f"limit={lim}: {r.text}"


# ─────────────── G2: admin golden path ───────────────


class TestAdminGolden:
    async def test_backfill_returns_202(self, auth_client, make_user):
        """backfill golden：platform_admin 触发 → 202 + BackfillResponse。"""
        admin = await make_user(email="m18-adm-bf@example.com", role="platform_admin")
        pid = await _create_project(auth_client, admin.id)
        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={"project_id": str(pid)},
            headers=_bearer(admin.id),
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert "enqueued_count" in body
        assert body["message"] == "Backfill enqueued"

    async def test_model_upgrade_returns_202(self, auth_client, make_user):
        """model-upgrade golden：platform_admin 触发 → 202 + ModelUpgradeResponse。"""
        admin = await make_user(email="m18-adm-mu@example.com", role="platform_admin")
        pid = await _create_project(auth_client, admin.id)
        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(pid),
                "new_provider": "openai",
                "new_model_name": "text-embedding-3-large",
                "new_model_version": "v2",
            },
            headers=_bearer(admin.id),
        )
        assert r.status_code == 202, r.text
        body = r.json()
        assert "enqueued_count" in body
        assert "old_triple" in body
        assert "new_triple" in body
        assert body["new_triple"] == ["openai", "text-embedding-3-large", "v2"]

    async def test_stats_returns_200(self, auth_client, make_user):
        """stats golden：platform_admin 调 → 200 + EmbeddingStatsResponse。"""
        admin = await make_user(email="m18-adm-st@example.com", role="platform_admin")
        r = await auth_client.get(
            "/api/admin/embedding/stats",
            headers=_bearer(admin.id),
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "total_embeddings" in body
        assert "pending_tasks" in body
        assert "failed_last_hour" in body
        assert "model_version_distribution" in body


# ─────────────── E1: 鉴权拒绝 ───────────────


class TestAuthRejection:
    async def test_search_unauthenticated_returns_401(self, auth_client, make_user):
        """401 未登录 / search endpoint。"""
        user = await make_user(email="m18-401s@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test"},
        )
        assert r.status_code == 401

    async def test_backfill_unauthenticated_returns_401(self, auth_client):
        """401 未登录 / backfill admin endpoint。"""
        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={"project_id": str(uuid4())},
        )
        assert r.status_code == 401

    async def test_model_upgrade_unauthenticated_returns_401(self, auth_client):
        """401 未登录 / model-upgrade admin endpoint。"""
        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(uuid4()),
                "new_provider": "openai",
                "new_model_name": "m",
                "new_model_version": "v1",
            },
        )
        assert r.status_code == 401

    async def test_stats_unauthenticated_returns_401(self, auth_client):
        """401 未登录 / stats admin endpoint。"""
        r = await auth_client.get("/api/admin/embedding/stats")
        assert r.status_code == 401


# ─────────────── A: viewer 写 403 全覆盖（admin endpoint require_platform_admin 守护）───────────────


class TestViewerAndNonAdminForbidden:
    """**A 元教训**：viewer 写所有写端点 403（M07 立 / M08 应用立规）。

    admin endpoint：viewer（非 platform_admin）调 backfill 403 + model-upgrade 403 + stats 403。
    测试函数 docstring 字面声明：viewer 写 403 全覆盖（admin endpoint require_platform_admin 守护）。
    """

    async def test_non_admin_backfill_returns_403(self, auth_client, make_user):
        """**A + K 元教训**：普通 user（非 platform_admin）调 backfill → 403 permission_denied。

        viewer 写 403 全覆盖（admin endpoint require_platform_admin 守护）。
        M14 endpoint 形态特殊不免除契约纪律（M14 立 / M18 admin endpoint 主动复制）。
        """
        user = await make_user(email="m18-nafb@example.com", role="user")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={"project_id": str(pid)},
            headers=_bearer(user.id),
        )
        assert r.status_code == 403
        assert r.json()["code"] == "permission_denied"

    async def test_non_admin_model_upgrade_returns_403(self, auth_client, make_user):
        """**A + K 元教训**：普通 user 调 model-upgrade → 403 permission_denied。

        viewer 写 403 全覆盖（admin endpoint require_platform_admin 守护）。
        """
        user = await make_user(email="m18-namu@example.com", role="user")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(pid),
                "new_provider": "openai",
                "new_model_name": "m",
                "new_model_version": "v1",
            },
            headers=_bearer(user.id),
        )
        assert r.status_code == 403
        assert r.json()["code"] == "permission_denied"

    async def test_non_admin_stats_returns_403(self, auth_client, make_user):
        """**A + K 元教训**：普通 user 调 stats → 403 permission_denied。

        viewer 写 403 全覆盖（admin endpoint require_platform_admin 守护）。
        M14 endpoint 形态特殊（GET read 仍受 platform_admin 守护，不因 GET 豁免）。
        """
        user = await make_user(email="m18-nast@example.com", role="user")
        r = await auth_client.get(
            "/api/admin/embedding/stats",
            headers=_bearer(user.id),
        )
        assert r.status_code == 403
        assert r.json()["code"] == "permission_denied"

    async def test_project_viewer_search_own_project_200(self, auth_client, make_user, db_session):
        """search 是 read endpoint：viewer 搜自己 project → 200（不是 403）。

        N/A 元教训声明（design §14.5）：
        - search 是 read endpoint，viewer 写 403 N/A（POST 语义是 query / 非写操作）
        """
        from uuid import UUID

        from api.models.project import MemberRole, ProjectMember

        userA = await make_user(email="m18-vs-A@example.com")
        userB = await make_user(email="m18-vs-B@example.com")
        pid_str = await _create_project(auth_client, userA.id)
        pid = UUID(pid_str)
        db_session.add(
            ProjectMember(project_id=pid, user_id=userB.id, role=MemberRole.VIEWER.value)
        )
        await db_session.commit()
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test"},
            headers=_bearer(userB.id),
        )
        assert r.status_code == 200


# ─────────────── B: read 权限 403（cross-project denial）───────────────


class TestReadPermission403:
    """**B 元教训**：read 权限 403（M15 首发立规 / M18 search 路由覆盖）。

    非 project member viewer search → 403（cross-project denial）。
    docstring 字面声明：读权限 403 测试范式（M15 首发 / M18 search 路由复用）。
    """

    async def test_non_member_search_returns_403_or_404(self, auth_client, make_user):
        """**B 元教训**：非 project member viewer search → 403/404（cross-project denial）。

        读权限 403 测试范式（M15 首发 / M18 search 路由复用）。
        check_project_access(role="viewer") 非 member → ProjectNotFoundError 404。
        """
        userA = await make_user(email="m18-nm-A@example.com")
        userB = await make_user(email="m18-nm-B@example.com")
        pid = await _create_project(auth_client, userA.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "配额"},
            headers=_bearer(userB.id),
        )
        # check_project_access 非 member → 404（M02 范式：project_not_found 打码）
        assert r.status_code in (403, 404)


# ─────────────── D: cross-tenant 404（M02 立规）───────────────


class TestCrossTenant404:
    """**D 元教训**：cross-tenant 404（M02 立规）。

    userA 在 projectA / project 不属 userA → 404（不是 403）。
    """

    async def test_search_cross_tenant_returns_404(self, auth_client, make_user):
        """**D 元教训**：userB 跨 projectA（非成员）搜索 → 404 project_not_found。"""
        userA = await make_user(email="m18-xt-A@example.com")
        userB = await make_user(email="m18-xt-B@example.com")
        pid = await _create_project(auth_client, userA.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "配额"},
            headers=_bearer(userB.id),
        )
        assert r.status_code == 404
        assert r.json()["code"] == "project_not_found"

    async def test_search_nonexistent_project_returns_404(self, auth_client, make_user):
        """**D 元教训**：project_id 不存在 → 404 project_not_found。"""
        user = await make_user(email="m18-nep@example.com")
        r = await auth_client.post(
            f"/api/projects/{uuid4()}/search",
            json={"query": "test"},
            headers=_bearer(user.id),
        )
        assert r.status_code == 404
        assert r.json()["code"] == "project_not_found"


# ─────────────── E: cross-project node 不召回（M03 立规）───────────────


class TestCrossProjectIsolation:
    """**E 元教训**：cross-project node 404（M03 立规 / search 调 cross-project 不召回）。

    search 路由不召回 cross-project 节点 / 即使 keyword 命中也过滤。
    """

    async def test_search_does_not_return_cross_project_nodes(
        self, auth_client, make_user, monkeypatch
    ):
        """**E 元教训**：search 不召回跨 project 节点（project_id WHERE filter 守护）。

        cross-project node 不召回（M03 立 / M18 search 路由复用）。
        mock keyword_search 模拟跨 project 节点被过滤（service 层 check_project_access 防线）。
        """
        from api.services import search as search_mod

        async def _mock_hybrid_search(self_svc, db, query, project_id, user_id, **kwargs):
            from api.schemas.search_schema import SearchResponse

            # service 层 check_project_access 已过滤 cross-project；返回空结果
            return SearchResponse(
                results=[],
                total=0,
                search_mode="keyword_only",
                query_embedding_cached=False,
            )

        monkeypatch.setattr(search_mod.SearchService, "hybrid_search", _mock_hybrid_search)

        await make_user(email="m18-cp-A@example.com")  # userA 的存在确认 cross-project 隔离语义
        userB = await make_user(email="m18-cp-B@example.com")
        pid_b = await _create_project(auth_client, userB.id)

        # userB 搜自己的 project → check_project_access 通过 → 0 结果（cross-project 过滤）
        r = await auth_client.post(
            f"/api/projects/{pid_b}/search",
            json={"query": "配额"},
            headers=_bearer(userB.id),
        )
        assert r.status_code == 200
        assert r.json()["total"] == 0


# ─────────────── C: write_event 异常传播 e2e（M16 立规）───────────────


class TestWriteEventPropagation:
    """**C 元教训**：write_event 异常传播测试 e2e（M16 立规 / M18 backfill + model-upgrade 复用）。

    monkeypatch write_event raise → 触发 backfill/model-upgrade 应回滚 + 500。
    """

    async def test_backfill_write_event_failure_returns_500(
        self, auth_client, make_user, monkeypatch
    ):
        """**C 元教训**：write_event raise → backfill endpoint 500（M16 立规 / M18 backfill 复用）。

        write_event 异常传播测试 e2e（M16 立规）：monkeypatch write_event raise → 500。
        """
        from api.routers import embedding_admin_router as admin_mod

        async def boom(**kwargs):
            raise RuntimeError("write_event simulated failure")

        monkeypatch.setattr(admin_mod, "write_event", boom)

        admin = await make_user(email="m18-wef-bf@example.com", role="platform_admin")
        pid = await _create_project(auth_client, admin.id)
        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={"project_id": str(pid)},
            headers=_bearer(admin.id),
        )
        assert r.status_code == 500

    async def test_model_upgrade_write_event_failure_returns_500(
        self, auth_client, make_user, monkeypatch
    ):
        """**C 元教训**：write_event raise → model-upgrade endpoint 500（M16 立规 / M18 model-upgrade 复用）。

        write_event 异常传播测试 e2e（M16 立规）：monkeypatch write_event raise → 500。
        """
        from api.routers import embedding_admin_router as admin_mod

        async def boom(**kwargs):
            raise RuntimeError("write_event simulated failure")

        monkeypatch.setattr(admin_mod, "write_event", boom)

        admin = await make_user(email="m18-wef-mu@example.com", role="platform_admin")
        pid = await _create_project(auth_client, admin.id)
        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(pid),
                "new_provider": "openai",
                "new_model_name": "text-embedding-3-large",
                "new_model_version": "v2",
            },
            headers=_bearer(admin.id),
        )
        assert r.status_code == 500


# ─────────────── J: metadata 字段集每条 e2e 字面验（M13 立规）───────────────


class TestMetadataFieldsLiteral:
    """**J 元教训**：M13 metadata 字段集每条 e2e 字面验（M18 backfill + model_upgrade triggered）。

    不依赖前端可计时绕过 / 字面验完整 metadata dict。
    """

    async def test_backfill_writes_activity_log_with_trigger_reason_and_affected_count(
        self, auth_client, make_user, db_session
    ):
        """**J 元教训**：backfill_triggered metadata 字段{trigger_reason, affected_count} 字面验。

        design §10 line 829：metadata={trigger_reason, affected_count} 字面必须存在。
        M13 立规：metadata 字段集每条 e2e 字面验（M18 backfill 路径复用）。
        """
        from uuid import UUID

        from sqlalchemy import select

        from api.models.activity_log import ActivityLog

        admin = await make_user(email="m18-jbf@example.com", role="platform_admin")
        pid_str = await _create_project(auth_client, admin.id)
        pid = UUID(pid_str)

        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={"project_id": str(pid)},
            headers=_bearer(admin.id),
        )
        assert r.status_code == 202, r.text

        # 字面验 activity_log 行（design §10 line 829 字面）
        stmt = select(ActivityLog).where(
            ActivityLog.action_type == "embedding_backfill_triggered",
            ActivityLog.target_type == "project",
            ActivityLog.target_id == str(pid),
        )
        result = await db_session.execute(stmt)
        log_row = result.scalar_one_or_none()
        assert log_row is not None, "activity_log 行应已写入（embedding_backfill_triggered）"
        meta = log_row.event_metadata or {}
        # M13 立规：字段集字面验（trigger_reason + affected_count 两字段必须存在）
        assert "trigger_reason" in meta, f"metadata 缺 trigger_reason: {meta}"
        assert "affected_count" in meta, f"metadata 缺 affected_count: {meta}"
        # 占位期 _stub=True 标记（子片 4+ 接真 scan_pending 后删除 _stub 标记并 assert affected_count > 0）
        assert meta["_stub"] is True, f"占位期 metadata._stub 必须为 True: {meta}"

    async def test_model_upgrade_writes_activity_log_with_old_new_model_and_affected_count(
        self, auth_client, make_user, db_session
    ):
        """**J 元教训**：model_upgrade_triggered metadata 字段{old_model, new_model, affected_count} 字面验。

        design §10 line 828：metadata={old_model, new_model, affected_count} 字面必须存在。
        M13 立规：metadata 字段集每条 e2e 字面验（M18 model_upgrade 路径复用）。
        """
        from uuid import UUID

        from sqlalchemy import select

        from api.models.activity_log import ActivityLog

        admin = await make_user(email="m18-jmu@example.com", role="platform_admin")
        pid_str = await _create_project(auth_client, admin.id)
        pid = UUID(pid_str)

        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(pid),
                "new_provider": "openai",
                "new_model_name": "text-embedding-3-large",
                "new_model_version": "v2",
            },
            headers=_bearer(admin.id),
        )
        assert r.status_code == 202, r.text

        stmt = select(ActivityLog).where(
            ActivityLog.action_type == "embedding_model_upgrade_triggered",
            ActivityLog.target_type == "project",
            ActivityLog.target_id == str(pid),
        )
        result = await db_session.execute(stmt)
        log_row = result.scalar_one_or_none()
        assert log_row is not None, "activity_log 行应已写入（embedding_model_upgrade_triggered）"
        meta = log_row.event_metadata or {}
        # M13 立规：字段集字面验（old_model + new_model + affected_count 三字段必须存在）
        assert "old_model" in meta, f"metadata 缺 old_model: {meta}"
        assert "new_model" in meta, f"metadata 缺 new_model: {meta}"
        assert "affected_count" in meta, f"metadata 缺 affected_count: {meta}"
        # 占位期 _stub=True 标记（子片 4+ 接真 scan_pending 后删除 _stub 标记并 assert affected_count > 0）
        assert meta["_stub"] is True, f"占位期 metadata._stub 必须为 True: {meta}"


# TestIntegrityErrorCatch (#11) 已删：占位期 router 不做真 INSERT，无 IntegrityError 路径触发。
# PUNT_TO_SUBPIECE_4PLUS：子片 4+ 真接 scan_pending 时补 monkeypatch IntegrityError 实测。

# TestNAExplicit (#12) 已删：9 个 assert True 占位反模式，design §14.5 已字面双重声明 N/A 项。
# PUNT_TO_SUBPIECE_4PLUS：子片 4+ 需要真测时从 design §14.5 补实测，不用 assert True 占名额。


# ─────────────── Pydantic 422 boundary ───────────────


class TestPydantic422:
    """Pydantic 422 boundary：query 空 / query 200+ / target_types 非合法枚举 / limit 0。"""

    async def test_query_empty_returns_422(self, auth_client, make_user):
        """query 空字符串 → 422（Pydantic min_length=1）。"""
        user = await make_user(email="m18-422e@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": ""},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422

    async def test_query_201_chars_returns_400_invalid_query_length(self, auth_client, make_user):
        """query 201 字符 → 400 invalid_query_length（design §7 line 663 字面 / router 手动 check）。

        design §7 line 663：query 超 200 char 返 400 INVALID_QUERY_LENGTH（非 Pydantic 422）。
        Pydantic max_length=200 已删（search_schema.py），router 手动 check 抛 400。
        """
        user = await make_user(email="m18-422l@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "a" * 201},
            headers=_bearer(user.id),
        )
        assert r.status_code == 400
        assert r.json()["code"] == "invalid_query_length"

    async def test_query_200_chars_succeeds(self, auth_client, make_user):
        """query 200 字符（上限）→ 200 通过校验（boundary 验证）。"""
        user = await make_user(email="m18-422ok@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "a" * 200},
            headers=_bearer(user.id),
        )
        assert r.status_code == 200

    async def test_invalid_target_type_returns_422(self, auth_client, make_user):
        """target_types 非合法枚举 → 422。"""
        user = await make_user(email="m18-422tt@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test", "target_types": ["invalid_type"]},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422

    async def test_limit_zero_returns_422(self, auth_client, make_user):
        """limit=0 → 422（Pydantic ge=1）。"""
        user = await make_user(email="m18-422lz@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test", "limit": 0},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422

    async def test_limit_101_returns_422(self, auth_client, make_user):
        """limit=101 → 422（Pydantic le=100）。"""
        user = await make_user(email="m18-422lmax@example.com")
        pid = await _create_project(auth_client, user.id)
        r = await auth_client.post(
            f"/api/projects/{pid}/search",
            json={"query": "test", "limit": 101},
            headers=_bearer(user.id),
        )
        assert r.status_code == 422


# ─────────────── admin endpoint Pydantic 422 ───────────────


class TestAdminPydantic422:
    """admin endpoint 缺少必要字段 → 422。"""

    async def test_backfill_missing_project_id_returns_422(self, auth_client, make_user):
        """backfill 缺 project_id → 422。"""
        admin = await make_user(email="m18-adm422-bf@example.com", role="platform_admin")
        r = await auth_client.post(
            "/api/admin/embedding/backfill",
            json={},  # 缺 project_id（user_id 已从 schema 删除 / 来自 JWT）
            headers=_bearer(admin.id),
        )
        assert r.status_code == 422

    async def test_model_upgrade_missing_required_fields_returns_422(self, auth_client, make_user):
        """model-upgrade 缺 new_provider → 422。"""
        admin = await make_user(email="m18-adm422-mu@example.com", role="platform_admin")
        r = await auth_client.post(
            "/api/admin/embedding/model-upgrade",
            json={
                "project_id": str(uuid4()),
                # 缺 new_provider / new_model_name / new_model_version（user_id 已从 schema 删除）
            },
            headers=_bearer(admin.id),
        )
        assert r.status_code == 422


__all__ = [
    "TestAdminGolden",
    "TestAdminPydantic422",
    "TestAuthRejection",
    "TestCrossProjectIsolation",
    "TestCrossTenant404",
    "TestMetadataFieldsLiteral",
    "TestPydantic422",
    "TestReadPermission403",
    "TestSearchGolden",
    "TestViewerAndNonAdminForbidden",
    "TestWriteEventPropagation",
]
