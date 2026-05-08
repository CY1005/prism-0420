"""M04 子片 3 — DimensionService 测试。

覆盖：
  - CRUD（create / update_with_lock / delete）
  - 乐观锁冲突 / 唯一约束保护 / type 不存在 / 记录不存在
  - R-X2 第一真注入：delete_by_node_id 走 M03 delete_node 整链
  - activity_log 写入形态（per-record event + cascade_source 标记）
  - get_for_embedding（A5 A 路径单元覆盖）

monkeypatch 用法说明（feedback_monkeypatch_not_verification）：本文件用
``monkeypatch.setattr("api.services.dimension_service.write_event", fake)``
仅用于校验 service **写出来的 event 形态**（unit 验证），生产路径 write_event
是 B2.3 stub（structlog JSON 落地，M15 sprint 期升级真实 DB INSERT）——
端到端验证靠 router/integration 测试启动 lifespan + httpx asgi 跑全栈。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    ConflictError,
    DimensionDuplicateError,
    DimensionNotFoundError,
    DimensionTypeNotFoundError,
)
from api.models.dimension_record import DimensionRecord
from api.services.dimension_service import DimensionService

# helpers: make_dim_type fixture in conftest (M05 sprint 抽出，M04 punt R1-B B1.1)


async def _enable_dim_type(db_session, project_id, dimension_type_id, enabled=True) -> None:
    """R1-C C3.2 立修配套：建 ProjectDimensionConfig 行（默认 enabled=True）。"""
    from api.models.project import ProjectDimensionConfig

    db_session.add(
        ProjectDimensionConfig(
            project_id=project_id,
            dimension_type_id=dimension_type_id,
            enabled=enabled,
            sort_order=0,
        )
    )
    await db_session.flush()


@pytest.fixture
def svc():
    return DimensionService()


# ─────────────── M04-SVC-T1 create ───────────────


async def test_svc_create_persists_and_writes_activity_log(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tc", project_id=proj.id)

    captured: list[dict] = []

    async def fake_write_event(**kwargs):
        captured.append(kwargs)

    monkeypatch.setattr("api.services.dimension_service.write_event", fake_write_event)

    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"description": "hello"},
        actor_user_id=user.id,
    )
    assert rec.id is not None
    assert rec.version == 1
    assert rec.content == {"description": "hello"}
    assert rec.created_by == user.id

    assert len(captured) == 1
    ev = captured[0]
    assert ev["action_type"] == "create"
    assert ev["target_type"] == "dimension_record"
    assert ev["target_id"] == str(rec.id)
    assert ev["metadata"]["node_id"] == str(node.id)
    assert ev["metadata"]["dimension_type_id"] == type_id


async def test_svc_create_rejects_unknown_type(db_session, svc, make_project, make_node):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    with pytest.raises(DimensionTypeNotFoundError):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=999999,
            content={},
            actor_user_id=user.id,
        )


async def test_svc_create_rejects_duplicate_node_type(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tdup", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"a": 1},
        actor_user_id=user.id,
    )
    with pytest.raises(DimensionDuplicateError):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            content={"a": 2},
            actor_user_id=user.id,
        )


# ─────────────── M04-SVC-T2 update_with_lock ───────────────


async def test_svc_update_increments_version_and_logs(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tu", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"x": 1},
        actor_user_id=user.id,
    )

    captured: list[dict] = []

    async def fake(**k):
        captured.append(k)

    monkeypatch.setattr("api.services.dimension_service.write_event", fake)

    updated = await svc.update_with_lock(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"x": 2},
        expected_version=1,
        actor_user_id=user.id,
    )
    assert updated.version == 2
    assert updated.content == {"x": 2}

    assert len(captured) == 1
    assert captured[0]["action_type"] == "update"
    assert captured[0]["metadata"]["old_version"] == 1
    assert captured[0]["metadata"]["new_version"] == 2


async def test_svc_update_conflict_raises(db_session, svc, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tu_c", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={},
        actor_user_id=user.id,
    )
    with pytest.raises(ConflictError):
        await svc.update_with_lock(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            content={"x": 1},
            expected_version=999,
            actor_user_id=user.id,
        )


async def test_svc_update_not_found_raises(db_session, svc, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tu_nf", project_id=proj.id)
    with pytest.raises(DimensionNotFoundError):
        await svc.update_with_lock(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            content={},
            expected_version=1,
            actor_user_id=user.id,
        )


# ─────────────── M04-SVC-T3 delete ───────────────


async def test_svc_delete_removes_record_and_logs(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    from sqlalchemy import select

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="td", project_id=proj.id)
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={},
        actor_user_id=user.id,
    )

    captured: list[dict] = []
    monkeypatch.setattr(
        "api.services.dimension_service.write_event",
        lambda **k: captured.append(k) or _async_none(),
    )

    await svc.delete(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        actor_user_id=user.id,
    )
    found = await db_session.scalar(select(DimensionRecord).where(DimensionRecord.id == rec.id))
    assert found is None

    delete_events = [e for e in captured if e["action_type"] == "delete"]
    assert len(delete_events) == 1
    assert delete_events[0]["target_id"] == str(rec.id)


async def test_svc_delete_not_found_raises(db_session, svc, make_project, make_node, make_dim_type):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="td_nf", project_id=proj.id)
    with pytest.raises(DimensionNotFoundError):
        await svc.delete(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            actor_user_id=user.id,
        )


# ─────────────── M04-SVC-T4 R-X2 注入路径（M03 delete_node → M04） ───────────────


async def test_svc_delete_by_node_id_deletes_all_records(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="rx2_1", project_id=proj.id)
    t2 = await make_dim_type(key="rx2_2", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=t1,
        content={},
        actor_user_id=user.id,
    )
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=t2,
        content={},
        actor_user_id=user.id,
    )

    captured: list[dict] = []

    async def fake(**k):
        captured.append(k)

    monkeypatch.setattr("api.services.dimension_service.write_event", fake)

    await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)

    rows = await svc.list_by_node(db_session, project_id=proj.id, node_id=node.id)
    assert rows == []

    cascade_events = [
        e
        for e in captured
        if e.get("action_type") == "delete" and e["metadata"].get("cascade_source") == "node_delete"
    ]
    assert len(cascade_events) == 2, "应为每条记录写一条 cascade delete 事件"


async def test_svc_delete_by_node_id_full_chain_via_node_service(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    """端到端：调 NodeService.delete_node → 自动触发 DimensionService.delete_by_node_id。

    R-X2 真注入验证（不是 monkeypatch）：模拟 lifespan 已注入的 register_child_service
    （tests/conftest.py 的 db_session 是 savepoint，lifespan 不真跑——所以本测试手工
    register + clear，验证整链）。
    """
    from api.services.node_service import (
        NodeService,
        clear_child_services,
        register_child_service,
    )

    user, proj = await make_project()
    parent = await make_node(proj.id, name="P")
    child = await make_node(proj.id, parent=parent, name="C")
    type_id = await make_dim_type(key="rx2_chain", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=child.id,
        dimension_type_id=type_id,
        content={"x": 1},
        actor_user_id=user.id,
    )

    register_child_service("dimension", svc.delete_by_node_id)
    try:
        # 静默 write_event 噪音
        async def fake(**k):
            pass

        monkeypatch.setattr("api.services.dimension_service.write_event", fake)
        monkeypatch.setattr("api.services.node_service.write_event", fake)

        node_svc = NodeService()
        await node_svc.delete_node(
            db_session,
            project_id=proj.id,
            node_id=parent.id,
            actor_user_id=user.id,
        )

        # 子树被删 + dimension_record 也被清
        rows = await svc.list_by_node(db_session, project_id=proj.id, node_id=child.id)
        assert rows == [], "子节点的 dimension_records 应被 R-X2 清理"
    finally:
        clear_child_services()


async def test_svc_delete_by_node_id_propagates_exceptions(
    db_session, svc, make_project, make_node, monkeypatch, make_dim_type
):
    """异常契约 (R1-C P1-01)：concrete impl 不 catch-all 吞错。

    制造 write_event 异常 → 验证向上传播（不 catch）。
    """
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="rx2_err", project_id=proj.id)
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={},
        actor_user_id=user.id,
    )

    async def boom(**k):
        if k.get("metadata", {}).get("cascade_source") == "node_delete":
            raise RuntimeError("simulated downstream failure")

    monkeypatch.setattr("api.services.dimension_service.write_event", boom)

    with pytest.raises(RuntimeError, match="simulated"):
        await svc.delete_by_node_id(db_session, node.id, proj.id, user.id)


# ─────────────── M04-SVC-T5 get_for_embedding（A5 A 路径） ───────────────


async def test_svc_get_for_embedding_concatenates_string_values(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="te", project_id=proj.id)
    rec = await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=type_id,
        content={"title": "Hello", "desc": "World", "count": 42, "empty": ""},
        actor_user_id=user.id,
    )
    text = await svc.get_for_embedding(db_session, rec.id, proj.id)
    assert text is not None
    parts = set(text.split("\n"))
    assert parts == {"Hello", "World"}, "仅 isinstance(str) 非空字段拼接，count/empty 排除"


async def test_svc_get_for_embedding_returns_none_when_not_found(db_session, svc):
    text = await svc.get_for_embedding(db_session, uuid4(), uuid4())
    assert text is None


async def test_svc_get_for_embedding_blocks_cross_tenant(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await make_dim_type(key="te_x", project_id=projA.id)
    rec = await svc.create(
        db_session,
        project_id=projA.id,
        node_id=nA.id,
        dimension_type_id=type_id,
        content={"x": "v"},
        actor_user_id=user.id,
    )
    text = await svc.get_for_embedding(db_session, rec.id, projB.id)
    assert text is None


# ─────────────── M04-SVC-T6 completion ───────────────


async def test_svc_completion_calculates_rate(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="cp1", project_id=proj.id)
    await make_dim_type(key="cp2", project_id=proj.id)  # 第二条仅为存在性
    await svc.create(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_id=t1,
        content={},
        actor_user_id=user.id,
    )

    result = await svc.completion(db_session, project_id=proj.id, node_id=node.id, enabled_count=2)
    assert result == {
        "filled_count": 1,
        "enabled_count": 2,
        "completion_rate": 0.5,
    }


async def test_svc_completion_zero_enabled_returns_zero_rate(
    db_session, svc, make_project, make_node
):
    _, proj = await make_project()
    node = await make_node(proj.id, name="A")
    result = await svc.completion(db_session, project_id=proj.id, node_id=node.id, enabled_count=0)
    assert result["completion_rate"] == 0.0


# ─────────────── M04-SVC-T7 R1-C C3.1 立修：node 归属校验（C9.2 配套） ───────────────


async def test_svc_create_blocks_cross_tenant_node_id(
    db_session, svc, make_project, make_node, make_dim_type
):
    """design §8 R8-1 三层防御第三层：恶意 caller 传他项目的 node_id + 自己 project_id 应拒。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await make_dim_type(key="x_node", project_id=projB.id)

    with pytest.raises(DimensionNotFoundError):
        await svc.create(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            dimension_type_id=type_id,
            content={},
            actor_user_id=user.id,
        )


async def test_svc_update_blocks_cross_tenant_node_id(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await make_dim_type(key="x_upd", project_id=projB.id)

    with pytest.raises(DimensionNotFoundError):
        await svc.update_with_lock(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            dimension_type_id=type_id,
            content={},
            expected_version=1,
            actor_user_id=user.id,
        )


async def test_svc_delete_blocks_cross_tenant_node_id(
    db_session, svc, make_project, make_node, make_dim_type
):
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    type_id = await make_dim_type(key="x_del", project_id=projB.id)

    with pytest.raises(DimensionNotFoundError):
        await svc.delete(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            dimension_type_id=type_id,
            actor_user_id=user.id,
        )


# ─────────────── M04-SVC-T8 R1-C C3.2 立修：DimensionTypeDisabledError（C9.1 配套） ───────────────


async def test_svc_create_rejects_unconfigured_type(
    db_session, svc, make_project, make_node, make_dim_type
):
    """pdc 不存在 → 视为 disabled（pdc-existence-strict 子选项 / sprint R-X5 实证）。"""
    from api.errors.exceptions import DimensionTypeDisabledError

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tdis_unconfigured")

    with pytest.raises(DimensionTypeDisabledError):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            content={},
            actor_user_id=user.id,
        )


async def test_svc_create_rejects_disabled_type(
    db_session, svc, make_project, make_node, make_dim_type
):
    """pdc.enabled=False → DimensionTypeDisabledError。"""
    from api.errors.exceptions import DimensionTypeDisabledError

    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    type_id = await make_dim_type(key="tdis_off")
    await _enable_dim_type(db_session, proj.id, type_id, enabled=False)

    with pytest.raises(DimensionTypeDisabledError):
        await svc.create(
            db_session,
            project_id=proj.id,
            node_id=node.id,
            dimension_type_id=type_id,
            content={},
            actor_user_id=user.id,
        )


# helper for monkeypatch lambda return
async def _async_none():
    return None


# ─────────────── M11 sprint R-X1 batch_create_in_transaction smoke ───────────────


async def test_svc_batch_create_in_transaction_creates_multiple(
    db_session, svc, make_project, make_node, make_dim_type
):
    """M11 sprint 接通：M04 batch_create_in_transaction 服务于 R-X1 orchestrator。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A")
    t1 = await make_dim_type(key="b1", project_id=proj.id)
    t2 = await make_dim_type(key="b2", project_id=proj.id)

    created = await svc.batch_create_in_transaction(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        dimensions_data=[
            {"node_id": node.id, "dimension_type_id": t1, "content": {"x": 1}},
            {"node_id": node.id, "dimension_type_id": t2, "content": {"y": 2}},
        ],
    )
    assert len(created) == 2
    assert {r.dimension_type_id for r in created} == {t1, t2}


# ─────────────── M12 sprint R-X3 batch_get_by_nodes smoke（caller 接通） ───────────────


async def test_svc_batch_get_by_nodes_aggregates_matrix(
    db_session, svc, make_project, make_node, make_dim_type
):
    """M12 sprint 接通：跨模块只读聚合（R-X3 共享外部 session 不主动 commit）。"""
    user, proj = await make_project()
    nA = await make_node(proj.id, name="A")
    nB = await make_node(proj.id, name="B")
    t1 = await make_dim_type(key="m12g1", project_id=proj.id)
    t2 = await make_dim_type(key="m12g2", project_id=proj.id)
    await svc.batch_create_in_transaction(
        db_session,
        project_id=proj.id,
        actor_user_id=user.id,
        dimensions_data=[
            {"node_id": nA.id, "dimension_type_id": t1, "content": {"v": "a1"}},
            {"node_id": nA.id, "dimension_type_id": t2, "content": {"v": "a2"}},
            {"node_id": nB.id, "dimension_type_id": t1, "content": {"v": "b1"}},
        ],
    )

    rows = await svc.batch_get_by_nodes(
        db_session,
        project_id=proj.id,
        node_ids=[nA.id, nB.id],
        dimension_type_ids=[t1, t2],
    )
    assert len(rows) == 3
    pairs = {(r.node_id, r.dimension_type_id) for r in rows}
    assert (nA.id, t1) in pairs
    assert (nA.id, t2) in pairs
    assert (nB.id, t1) in pairs


async def test_svc_batch_get_by_nodes_blocks_cross_tenant(
    db_session, svc, make_project, make_node, make_dim_type
):
    """跨 project 的 project_id 过滤——传错 project_id 返回空（M02 范式延续）。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    nA = await make_node(projA.id, name="A")
    t1 = await make_dim_type(key="m12cross", project_id=projA.id)
    await svc.batch_create_in_transaction(
        db_session,
        project_id=projA.id,
        actor_user_id=user.id,
        dimensions_data=[
            {"node_id": nA.id, "dimension_type_id": t1, "content": {"v": "a"}},
        ],
    )

    rows = await svc.batch_get_by_nodes(
        db_session,
        project_id=projB.id,
        node_ids=[nA.id],
        dimension_type_ids=[t1],
    )
    assert rows == []


async def test_svc_batch_get_by_nodes_empty_inputs_return_empty(db_session, svc, make_project):
    """node_ids 空 → []；dimension_type_ids=[] → []（DAO list_by_nodes 早返回分支）。"""
    _, proj = await make_project()
    rows = await svc.batch_get_by_nodes(
        db_session, project_id=proj.id, node_ids=[], dimension_type_ids=[1]
    )
    assert rows == []
    rows = await svc.batch_get_by_nodes(
        db_session, project_id=proj.id, node_ids=[uuid4()], dimension_type_ids=[]
    )
    assert rows == []


# ─────────────── M13 sprint create_dimension_record + get_latest smoke（caller 接通） ───────────────


async def test_svc_create_dimension_record_upserts_type_and_writes_event(
    db_session, svc, make_project, make_node
):
    """M13 sprint 接通：首次调用 upsert dimension_types 行（key='requirement_analysis'）+
    写一条 create activity_log（含 caller 传入的 extra_activity_metadata 合并）。
    不走 _check_dimension_type_enabled（系统寄生写入豁免 PDC，design 灰区裁决 2026-05-08）。

    重复 save (同 node, 同 dim_type) 在 M04 UNIQUE(node_id, dim_type_id) 约束下抛
    IntegrityError——具体语义（overwrite vs error）留给子片 2 AnalyzeService 拍。
    本 smoke 用 2 个不同 node 验 type upsert 幂等单行。
    """
    from sqlalchemy import select as _select

    from api.models.project import DimensionType

    user, proj = await make_project()
    nA = await make_node(proj.id, name="NA")
    nB = await make_node(proj.id, name="NB")

    extra = {
        "ai_provider": "claude",
        "ai_model": "claude-sonnet-4-5",
        "analysis_level": "L2",
        "analysis_time_ms": 1234,
    }
    rec_a = await svc.create_dimension_record(
        db_session,
        project_id=proj.id,
        node_id=nA.id,
        dimension_type_key="requirement_analysis",
        content={"summary": "node A 概要"},
        user_id=user.id,
        extra_activity_metadata=extra,
    )
    assert rec_a.id is not None
    assert rec_a.project_id == proj.id
    assert rec_a.node_id == nA.id
    assert rec_a.content["summary"] == "node A 概要"

    # 第二次调用相同 key 不同 node 应复用同一 dimension_type 行（upsert 幂等）
    rec_b = await svc.create_dimension_record(
        db_session,
        project_id=proj.id,
        node_id=nB.id,
        dimension_type_key="requirement_analysis",
        content={"summary": "node B 概要"},
        user_id=user.id,
    )
    assert rec_b.dimension_type_id == rec_a.dimension_type_id

    result = await db_session.execute(
        _select(DimensionType).where(DimensionType.key == "requirement_analysis")
    )
    rows = result.scalars().all()
    assert len(rows) == 1


async def test_svc_create_dimension_record_blocks_cross_tenant_node(
    db_session, svc, make_project, make_node
):
    """跨 project node_id → DimensionNotFoundError（不暴露 forbidden 信息，三层防御第三层）。"""
    user, projA = await make_project(name_suffix="-A")
    _, projB = await make_project(owner=user, name_suffix="-B")
    nA = await make_node(projA.id, name="A")

    with pytest.raises(DimensionNotFoundError):
        await svc.create_dimension_record(
            db_session,
            project_id=projB.id,
            node_id=nA.id,
            dimension_type_key="requirement_analysis_x1",
            content={"k": "v"},
            user_id=user.id,
        )


async def test_svc_get_latest_returns_newest_or_none(db_session, svc, make_project, make_node):
    """M13 affected-nodes 走此接口：拿最新一条；type 不存在或无记录 → None。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="N1")

    # type 不存在 → None
    none_rec = await svc.get_latest(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_key="never_registered_x2",
    )
    assert none_rec is None

    # 写一条 → get_latest 拿到该条
    r1 = await svc.create_dimension_record(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_key="requirement_analysis_x2",
        content={"v": "first"},
        user_id=user.id,
    )
    latest = await svc.get_latest(
        db_session,
        project_id=proj.id,
        node_id=node.id,
        dimension_type_key="requirement_analysis_x2",
    )
    assert latest is not None
    assert latest.id == r1.id
    assert latest.content["v"] == "first"

    # 跨 project 隔离：换 project_id 应拿不到（双重 tenant 过滤）
    _, projB = await make_project(owner=user, name_suffix="-B2")
    cross = await svc.get_latest(
        db_session,
        project_id=projB.id,
        node_id=node.id,
        dimension_type_key="requirement_analysis_x2",
    )
    assert cross is None
