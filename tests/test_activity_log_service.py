"""activity_log_service.write_event 实装测试（M16 sprint 子片 0.5 batch / 真 INSERT 接通）。

stub 期（B2.3）只验 structlog；M16 sprint 子片 0.5 升级为真 DB INSERT 后，本文件
重写为真 SQL 验证：行落表 + 字段映射 + project_id NULL 全局豁免 + IntegrityError
异常传播（R14 / CHECK constraint 违反 caller 必感知）。

structlog 副作用仍打（impl="db"），但不再是核心契约——核心契约是行落 activity_logs。
"""

import json
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.core.logging import configure_logging
from api.models.activity_log import ActivityLog
from api.services.activity_log_service import write_event


async def _make_user_proj(db_session, make_project):
    user, proj = await make_project()
    return user, proj


async def test_write_event_inserts_row(db_session, make_project, capsys):
    configure_logging()
    user, proj = await _make_user_proj(db_session, make_project)
    target_id = str(uuid4())

    await write_event(
        db=db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        action_type="node_created",
        target_type="node",
        target_id=target_id,
        summary="创建了节点『登录流程』",
        metadata={"importance": "high"},
    )

    rows = (await db_session.execute(select(ActivityLog))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.user_id == user.id
    assert row.project_id == proj.id
    assert row.action_type == "node_created"
    assert row.target_type == "node"
    assert row.target_id == target_id
    assert row.summary == "创建了节点『登录流程』"
    assert row.event_metadata == {"importance": "high"}

    # observability 副作用：structlog impl 升级为 "db"
    captured = capsys.readouterr().out.strip().splitlines()
    payload = json.loads(captured[-1])
    assert payload["impl"] == "db"
    assert payload["action_type"] == "node_created"


async def test_write_event_metadata_optional(db_session, make_project):
    user, proj = await _make_user_proj(db_session, make_project)
    await write_event(
        db=db_session,
        actor_user_id=user.id,
        project_id=proj.id,
        action_type="project_deleted",
        target_type="project",
        target_id=str(proj.id),
        summary="x",
    )
    row = (await db_session.execute(select(ActivityLog))).scalar_one()
    assert row.event_metadata is None


async def test_write_event_global_event_project_id_null(db_session, make_user):
    """M14 全局豁免业务模块范式：project_id=None 写入 NULL，时间线 UI 分组『全局事件』。"""
    user = await make_user()
    await write_event(
        db=db_session,
        actor_user_id=user.id,
        project_id=None,
        action_type="news_created",
        target_type="industry_news",
        target_id=str(uuid4()),
        summary="news",
        metadata={"source_type": "manual"},
    )
    row = (await db_session.execute(select(ActivityLog))).scalar_one()
    assert row.project_id is None


async def test_write_event_invalid_action_type_raises_integrity_error(db_session, make_project):
    """R14 防御未来：caller 误传非枚举字面 → CHECK constraint 违反 → IntegrityError 抛回。

    生产路径上 ci-lint.sh R14 在 commit 前已拦截，此测试守护"绕过 ci-lint 直接调用"
    场景的 DB 兜底（缺 ci-lint 预审的非项目代码 / 误开发分支）。
    """
    user, proj = await _make_user_proj(db_session, make_project)
    with pytest.raises(IntegrityError):
        await write_event(
            db=db_session,
            actor_user_id=user.id,
            project_id=proj.id,
            action_type="bogus_not_in_enum",  # CHECK constraint 必拒
            target_type="node",
            target_id=str(uuid4()),
            summary="x",
        )
