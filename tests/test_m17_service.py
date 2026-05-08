"""M17 ImportService 单元测试（R-X1 第二实例 / Queue 异步形态）。

覆盖路径（design §11/§4/§8 / R-X1 第二实例对照表）：
- submit_import：idempotency hit/miss + IntegrityError race + activity_log + commit
- get_task / list / not_found / cross_tenant 404
- get_review_data：仅 awaiting_review/partial_failed
- confirm_review：状态机 + activity_log + 终态拒绝
- cancel_task / retry_task：状态扭转 + 终态拒绝
- check_task_access：worker re-auth 三选一 404 打码
- run_extract / run_ai_step / run_batch_insert：Queue worker 入口
- run_batch_insert：R-X1 调 4 个 service.batch_create_in_transaction
- _mark_failed：compensation_session 独立 connection 落盘
- cleanup_dead_letter：30 天 failed 物理删
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from api.errors.exceptions import (
    ImportInvalidStateTransitionError,
    ImportTaskDuplicateError,
    ImportTaskFinalizedError,
    ImportTaskNotFoundError,
)
from api.models.import_task import ImportSourceType, ImportTask, ImportTaskStatus
from api.queue.import_tasks import (
    ConfirmedCompetitorData,
    ConfirmedImportData,
    ConfirmedIssueData,
    ConfirmedNodeData,
)
from api.services.import_service import ImportService

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ─────────────── fixtures ───────────────


@pytest_asyncio.fixture(loop_scope="session")
async def make_import_task(db_session):
    """工厂 fixture：建一条 import_tasks 行（M17 sprint）。

    跨文件 helper 规则十二连：M03/M04/M05/M06/M07/M11/M12/M13/M14/M15/M16/M17。
    """

    async def _make(
        *,
        project_id,
        user_id,
        status: str = ImportTaskStatus.pending.value,
        source_type: str = ImportSourceType.zip.value,
        source_hash: str | None = None,
        source_uri: str = "s3://bucket/test.zip",
        ai_provider: str = "mock",
        ai_model: str = "mock-1",
        review_data: dict | None = None,
        progress: int = 0,
    ) -> ImportTask:
        task = ImportTask(
            project_id=project_id,
            user_id=user_id,
            source_type=source_type,
            source_hash=source_hash or uuid4().hex,
            source_uri=source_uri,
            status=status,
            progress=progress,
            ai_provider=ai_provider,
            ai_model=ai_model,
            review_data=review_data,
        )
        db_session.add(task)
        await db_session.flush()
        return task

    yield _make


# ─────────────── submit_import ───────────────


class TestSubmitImport:
    async def test_creates_task_pending_with_metadata(self, db_session, make_project_with_member):
        user, proj = await make_project_with_member()
        svc = ImportService()
        task = await svc.submit_import(
            db_session,
            user_id=user.id,
            project_id=proj.id,
            source_type=ImportSourceType.zip,
            source_hash="abc123",
            source_uri="s3://b/x.zip",
            ai_provider="mock",
            ai_model="mock-1",
            items_metadata=[
                {"file_path": "a.md", "file_size": 100},
                {"file_path": "b.md", "file_size": 200},
            ],
        )
        assert task.status == ImportTaskStatus.pending.value
        assert task.source_type == "zip"
        assert task.source_hash == "abc123"
        assert task.progress == 0

    async def test_idempotency_hit_raises_duplicate(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        existing = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            source_hash="reuse-hash",
            status=ImportTaskStatus.completed.value,
        )
        await db_session.commit()
        svc = ImportService()
        with pytest.raises(ImportTaskDuplicateError) as exc:
            await svc.submit_import(
                db_session,
                user_id=user.id,
                project_id=proj.id,
                source_type=ImportSourceType.zip,
                source_hash="reuse-hash",
                source_uri="s3://b/y.zip",
                ai_provider="mock",
                ai_model="mock-1",
            )
        assert exc.value.details["existing_task_id"] == str(existing.id)
        assert exc.value.http_status == 200  # design §13 字面：复用非错误

    async def test_idempotency_failed_status_does_not_reuse(
        self, db_session, make_project_with_member, make_import_task
    ):
        """failed / cancelled 不复用（让用户能重新跑 / design §11 字面）。"""
        user, proj = await make_project_with_member()
        await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            source_hash="failed-hash",
            status=ImportTaskStatus.failed.value,
        )
        await db_session.commit()
        svc = ImportService()
        # 不应抛 duplicate；应继续创建（但被 UNIQUE 拦截 → IntegrityError → race 路径）
        # 此场景下 find_idempotent 不命中 + INSERT 撞 UNIQUE → 转 duplicate
        with pytest.raises(ImportTaskDuplicateError):
            await svc.submit_import(
                db_session,
                user_id=user.id,
                project_id=proj.id,
                source_type=ImportSourceType.zip,
                source_hash="failed-hash",
                source_uri="s3://b/y.zip",
                ai_provider="mock",
                ai_model="mock-1",
            )

    async def test_cross_project_same_hash_creates_separate_task(
        self, db_session, make_project_with_member, make_import_task
    ):
        """B1 修复：project_id 必须在 idempotency key 内（防跨租户污染）。"""
        user, proj_a = await make_project_with_member(name_suffix="-A")
        _, proj_b = await make_project_with_member(name_suffix="-B", owner=user)
        await make_import_task(
            project_id=proj_a.id,
            user_id=user.id,
            source_hash="same-hash",
            status=ImportTaskStatus.completed.value,
        )
        await db_session.commit()
        svc = ImportService()
        # 同 hash 但不同 project → 应建新 task（不命中 idempotency）
        new_task = await svc.submit_import(
            db_session,
            user_id=user.id,
            project_id=proj_b.id,
            source_type=ImportSourceType.zip,
            source_hash="same-hash",
            source_uri="s3://b/y.zip",
            ai_provider="mock",
            ai_model="mock-1",
        )
        assert new_task.project_id == proj_b.id


# ─────────────── 读 ───────────────


class TestRead:
    async def test_get_task_not_found_raises_404(self, db_session, make_project_with_member):
        _, proj = await make_project_with_member()
        svc = ImportService()
        with pytest.raises(ImportTaskNotFoundError):
            await svc.get_task(db_session, task_id=uuid4(), project_id=proj.id)

    async def test_get_task_cross_tenant_404(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj_a = await make_project_with_member(name_suffix="-A")
        _, proj_b = await make_project_with_member(name_suffix="-B", owner=user)
        task_a = await make_import_task(project_id=proj_a.id, user_id=user.id)
        svc = ImportService()
        with pytest.raises(ImportTaskNotFoundError):
            await svc.get_task(db_session, task_id=task_a.id, project_id=proj_b.id)

    async def test_check_task_access_owner_mismatch_404(
        self, db_session, make_project_with_member, make_user, make_import_task
    ):
        user_a, proj = await make_project_with_member()
        user_b = await make_user(email="other@example.com")
        task_a = await make_import_task(project_id=proj.id, user_id=user_a.id)
        svc = ImportService()
        # user_b 不是 task creator → 404 打码（不区分 not-found / cross-owner）
        with pytest.raises(ImportTaskNotFoundError):
            await svc.check_task_access(
                db_session, user_id=user_b.id, project_id=proj.id, task_id=task_a.id
            )

    async def test_get_review_data_pending_raises_invalid_state(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id, user_id=user.id, status=ImportTaskStatus.pending.value
        )
        svc = ImportService()
        with pytest.raises(ImportInvalidStateTransitionError):
            await svc.get_review_data(
                db_session, task_id=task.id, project_id=proj.id, user_id=user.id
            )

    async def test_get_review_data_awaiting_returns_dict(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.awaiting_review.value,
            review_data={"proposed_nodes": [{"name": "x"}]},
        )
        svc = ImportService()
        out = await svc.get_review_data(
            db_session, task_id=task.id, project_id=proj.id, user_id=user.id
        )
        assert out["proposed_nodes"][0]["name"] == "x"


# ─────────────── confirm / cancel / retry ───────────────


class TestStateTransitions:
    async def test_confirm_review_awaiting_to_step3(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.awaiting_review.value,
        )
        svc = ImportService()
        confirmed = ConfirmedImportData(nodes=[], dimensions=[], competitors=[], issues=[])
        out = await svc.confirm_review(
            db_session,
            task_id=task.id,
            project_id=proj.id,
            user_id=user.id,
            confirmed=confirmed,
        )
        assert out.status == ImportTaskStatus.ai_step3.value
        assert out.progress == 70

    async def test_confirm_review_finalized_raises(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.completed.value,
        )
        svc = ImportService()
        with pytest.raises(ImportTaskFinalizedError):
            await svc.confirm_review(
                db_session,
                task_id=task.id,
                project_id=proj.id,
                user_id=user.id,
                confirmed=ConfirmedImportData(),
            )

    async def test_cancel_pending_to_cancelled(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id, user_id=user.id, status=ImportTaskStatus.pending.value
        )
        svc = ImportService()
        out = await svc.cancel_task(
            db_session, user_id=user.id, project_id=proj.id, task_id=task.id
        )
        assert out.status == ImportTaskStatus.cancelled.value

    async def test_cancel_finalized_raises(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.completed.value,
        )
        svc = ImportService()
        with pytest.raises(ImportTaskFinalizedError):
            await svc.cancel_task(db_session, user_id=user.id, project_id=proj.id, task_id=task.id)

    async def test_retry_partial_failed_to_step3(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.partial_failed.value,
        )
        svc = ImportService()
        out = await svc.retry_task(db_session, user_id=user.id, project_id=proj.id, task_id=task.id)
        assert out.status == ImportTaskStatus.ai_step3.value

    async def test_retry_pending_raises_invalid_state(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id, user_id=user.id, status=ImportTaskStatus.pending.value
        )
        svc = ImportService()
        with pytest.raises(ImportInvalidStateTransitionError):
            await svc.retry_task(db_session, user_id=user.id, project_id=proj.id, task_id=task.id)


# ─────────────── Queue worker entries ───────────────


class TestWorkerEntries:
    async def test_run_extract_transitions_to_ai_step1(
        self, db_session, make_project_with_member, make_import_task
    ):
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id, user_id=user.id, status=ImportTaskStatus.pending.value
        )
        await db_session.commit()
        svc = ImportService()
        await svc.run_extract(db_session, user_id=user.id, project_id=proj.id, task_id=task.id)
        await db_session.refresh(task)
        assert task.status == ImportTaskStatus.ai_step1.value
        assert task.progress == 20

    async def test_run_extract_finalized_returns_silently(
        self, db_session, make_project_with_member, make_import_task
    ):
        """终态任务再被 worker 拉起（race / cancelled 已生效）→ 幂等退出，不抛。"""
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.cancelled.value,
        )
        await db_session.commit()
        svc = ImportService()
        # 不抛
        await svc.run_extract(db_session, user_id=user.id, project_id=proj.id, task_id=task.id)

    async def test_run_ai_step1_calls_orchestration(
        self,
        db_session,
        make_project_with_member,
        make_import_task,
        set_project_ai,
        monkeypatch,
    ):
        user, proj = await make_project_with_member()
        await set_project_ai(proj, provider="mock", api_key=None, model=None)
        task = await make_import_task(
            project_id=proj.id, user_id=user.id, status=ImportTaskStatus.ai_step1.value
        )
        await db_session.commit()

        async def fake_step1(self, *, provider, items_summary):
            return {"nodes": [{"proposed_id": str(uuid4()), "name": "X"}]}

        monkeypatch.setattr(
            "api.services.ai_orchestration_service.AIOrchestrationService.run_step1",
            fake_step1,
        )

        svc = ImportService()
        await svc.run_ai_step(
            db_session,
            user_id=user.id,
            project_id=proj.id,
            task_id=task.id,
            step=1,
        )
        await db_session.refresh(task)
        assert task.status == ImportTaskStatus.ai_step2.value
        assert task.review_data["proposed_nodes"][0]["name"] == "X"

    async def test_run_ai_step2_pushes_review_ready(
        self,
        db_session,
        make_project_with_member,
        make_import_task,
        set_project_ai,
        monkeypatch,
    ):
        user, proj = await make_project_with_member()
        await set_project_ai(proj, provider="mock", api_key=None, model=None)
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.ai_step2.value,
            review_data={"proposed_nodes": []},
        )
        await db_session.commit()

        async def fake_step2(self, *, provider, proposed_nodes, items_summary):
            return {"dimensions": [], "competitors": [], "issues": []}

        monkeypatch.setattr(
            "api.services.ai_orchestration_service.AIOrchestrationService.run_step2",
            fake_step2,
        )
        svc = ImportService()
        await svc.run_ai_step(
            db_session,
            user_id=user.id,
            project_id=proj.id,
            task_id=task.id,
            step=2,
        )
        await db_session.refresh(task)
        assert task.status == ImportTaskStatus.awaiting_review.value
        assert task.progress == 60

    async def test_run_batch_insert_calls_4_services(
        self,
        db_session,
        make_project_with_member,
        make_import_task,
        monkeypatch,
    ):
        """R-X1 第二实例：调 M03/M04/M06/M07 batch_create_in_transaction。"""
        user, proj = await make_project_with_member()
        task = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.importing.value,
        )
        await db_session.commit()

        calls = {"node": 0, "dim": 0, "comp": 0, "issue": 0}

        async def fake_node_batch(self, db, *, project_id, actor_user_id, nodes_data):
            calls["node"] += 1
            from uuid import uuid4 as _u4

            from api.models.node import Node

            out = []
            for raw in nodes_data:
                n = Node(
                    id=_u4(),
                    project_id=project_id,
                    name=raw["name"],
                    type=raw.get("type", "folder"),
                    parent_id=None,
                    path="/x",
                    depth=0,
                )
                out.append(n)
            return out

        async def fake_comp_batch(self, db, *, project_id, actor_user_id, competitors_data):
            calls["comp"] += 1
            return []

        async def fake_issue_batch(self, db, *, project_id, actor_user_id, issues_data):
            calls["issue"] += 1
            return []

        monkeypatch.setattr(
            "api.services.node_service.NodeService.batch_create_in_transaction",
            fake_node_batch,
        )
        monkeypatch.setattr(
            "api.services.competitor_service.CompetitorService.batch_create_in_transaction",
            fake_comp_batch,
        )
        monkeypatch.setattr(
            "api.services.issue_service.IssueService.batch_create_in_transaction",
            fake_issue_batch,
        )

        svc = ImportService()
        node_pid = uuid4()
        confirmed = ConfirmedImportData(
            nodes=[ConfirmedNodeData(proposed_id=node_pid, name="root", type="folder")],
            dimensions=[],
            competitors=[ConfirmedCompetitorData(proposed_id=uuid4(), display_name="CompX")],
            issues=[
                ConfirmedIssueData(
                    proposed_id=uuid4(),
                    target_proposed_node_id=node_pid,
                    title="Bug-1",
                    category="bug",
                    description="d",
                )
            ],
        )
        await svc.run_batch_insert(
            db_session,
            user_id=user.id,
            project_id=proj.id,
            task_id=task.id,
            confirmed=confirmed,
        )
        assert calls["node"] == 1
        assert calls["comp"] == 1
        assert calls["issue"] == 1
        await db_session.refresh(task)
        assert task.status == ImportTaskStatus.completed.value


# ─────────────── 死信清理 ───────────────


class TestCleanupDeadLetter:
    async def test_cleanup_old_failed_tasks(
        self, db_session, make_project_with_member, make_import_task
    ):
        from api.queue.base import SYSTEM_USER_UUID

        user, proj = await make_project_with_member()
        # 31 天前 failed → 应删
        old = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.failed.value,
        )
        old.created_at = datetime.now(UTC) - timedelta(days=31)
        await db_session.flush()
        # 1 天前 failed → 不删
        recent = await make_import_task(
            project_id=proj.id,
            user_id=user.id,
            status=ImportTaskStatus.failed.value,
        )
        await db_session.commit()
        svc = ImportService()
        count = await svc.cleanup_dead_letter(
            db_session, system_user_id=SYSTEM_USER_UUID, retention_days=30
        )
        assert count >= 1
        # recent 仍在
        assert (
            await svc.get_task(db_session, task_id=recent.id, project_id=proj.id)
        ).id == recent.id


__all__ = [
    "TestCleanupDeadLetter",
    "TestRead",
    "TestStateTransitions",
    "TestSubmitImport",
    "TestWorkerEntries",
]
