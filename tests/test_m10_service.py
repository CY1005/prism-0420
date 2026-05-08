"""M10 子片 2 — OverviewService 测试（含 folder 均值算法 + 分母=0 早返回）。"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.errors.exceptions import (
    OverviewNodeNotFoundError,
    OverviewNoDimensionsError,
    OverviewProjectNotFoundError,
)
from api.models.dimension_record import DimensionRecord
from api.services.overview_service import OverviewService


@pytest.fixture
def svc():
    return OverviewService()


# ─────────────── M10-SVC-T1 早返回边界 ───────────────


async def test_svc_no_dimensions_raises_422(db_session, svc, make_project):
    """分母=0 早返回（design M10-B3）。"""
    _, proj = await make_project()
    with pytest.raises(OverviewNoDimensionsError):
        await svc.get_overview(db_session, project_id=proj.id)


async def test_svc_project_not_found_raises_404(db_session, svc):
    with pytest.raises(OverviewProjectNotFoundError):
        await svc.get_overview(db_session, project_id=uuid4())


async def test_svc_get_node_completion_no_dimensions_raises_422(
    db_session, svc, make_project, make_node
):
    _, proj = await make_project()
    node = await make_node(proj.id, name="A")
    with pytest.raises(OverviewNoDimensionsError):
        await svc.get_node_completion(db_session, project_id=proj.id, node_id=node.id)


# ─────────────── M10-SVC-T2 file 节点 completion_rate ───────────────


async def test_svc_get_overview_file_completion(
    db_session, svc, make_project, make_node, make_dim_type, make_dim_record
):
    """3 启用维度 / 1 file 节点填 2 维度 → completion_rate = 2/3 ≈ 0.667。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="A", type="file")
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    t2 = await make_dim_type(key="t2", project_id=proj.id, enabled=True)
    await make_dim_type(key="t3", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=node, dim_type_id=t1)
    await make_dim_record(user=user, project=proj, node=node, dim_type_id=t2)

    result = await svc.get_overview(db_session, project_id=proj.id)
    tree = result["tree"]
    assert len(tree) == 1
    assert tree[0]["completion_rate"] == pytest.approx(2 / 3, rel=1e-6)
    assert tree[0]["filled_count"] == 2


async def test_svc_get_overview_full_completion(
    db_session, svc, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A", type="file")
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=node, dim_type_id=t1)

    result = await svc.get_overview(db_session, project_id=proj.id)
    assert result["tree"][0]["completion_rate"] == 1.0


async def test_svc_get_overview_zero_completion(
    db_session, svc, make_project, make_node, make_dim_type
):
    _, proj = await make_project()
    await make_node(proj.id, name="A", type="file")
    await make_dim_type(key="t1", project_id=proj.id, enabled=True)

    result = await svc.get_overview(db_session, project_id=proj.id)
    assert result["tree"][0]["completion_rate"] == 0.0


# ─────────────── M10-SVC-T3 folder 均值算法 ───────────────


async def test_svc_get_overview_folder_subtree_average(
    db_session, svc, make_project, make_node, make_dim_type, make_dim_record
):
    """folder 均值 = 子树 file 节点 rate 的均值（design D-1 迭代后序遍历）。

    场景：folder f / 2 个 file 子节点 c1 (rate=1.0) + c2 (rate=0.5)
    → f.completion_rate = (1.0 + 0.5) / 2 = 0.75
    """
    user, proj = await make_project()
    f = await make_node(proj.id, name="folder", type="folder")
    c1 = await make_node(proj.id, name="c1", type="file", parent=f)
    c2 = await make_node(proj.id, name="c2", type="file", parent=f)
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    t2 = await make_dim_type(key="t2", project_id=proj.id, enabled=True)
    # c1 填 2 维度 → 1.0
    await make_dim_record(user=user, project=proj, node=c1, dim_type_id=t1)
    await make_dim_record(user=user, project=proj, node=c1, dim_type_id=t2)
    # c2 填 1 维度 → 0.5
    await make_dim_record(user=user, project=proj, node=c2, dim_type_id=t1)

    result = await svc.get_overview(db_session, project_id=proj.id)
    tree = result["tree"]
    folder_node = tree[0]
    assert folder_node["type"] == "folder"
    assert folder_node["completion_rate"] == pytest.approx(0.75, rel=1e-6)
    assert len(folder_node["children"]) == 2


async def test_svc_get_overview_empty_folder_zero(
    db_session, svc, make_project, make_node, make_dim_type
):
    """空 folder（无子 file 节点）→ 0.0。"""
    _, proj = await make_project()
    await make_node(proj.id, name="empty", type="folder")
    await make_dim_type(key="t1", project_id=proj.id, enabled=True)

    result = await svc.get_overview(db_session, project_id=proj.id)
    assert result["tree"][0]["completion_rate"] == 0.0


async def test_svc_get_overview_nested_folder(
    db_session, svc, make_project, make_node, make_dim_type, make_dim_record
):
    """嵌套 folder：root / sub / file (rate=1.0) → root + sub 都是 1.0。"""
    user, proj = await make_project()
    root = await make_node(proj.id, name="root", type="folder")
    sub = await make_node(proj.id, name="sub", type="folder", parent=root)
    f = await make_node(proj.id, name="f", type="file", parent=sub)
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=f, dim_type_id=t1)

    result = await svc.get_overview(db_session, project_id=proj.id)
    root_node = result["tree"][0]
    assert root_node["completion_rate"] == 1.0
    assert root_node["children"][0]["completion_rate"] == 1.0


# ─────────────── M10-SVC-T4 stats ───────────────


async def test_svc_stats(db_session, svc, make_project, make_node, make_dim_type, make_dim_record):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A", type="file")
    await make_node(proj.id, name="B", type="file")  # n2 不填 → 0%
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=n1, dim_type_id=t1)
    # n2 不填 → 0%

    result = await svc.get_stats(db_session, project_id=proj.id)
    s = result["stats"]
    assert s["total_nodes"] == 2
    assert s["file_nodes"] == 2
    assert s["fully_complete_nodes"] == 1
    assert s["empty_nodes"] == 1
    assert s["avg_completion_rate"] == pytest.approx(0.5, rel=1e-6)
    assert s["enabled_dimension_count"] == 1


# ─────────────── M10-SVC-T5 get_node_completion ───────────────


async def test_svc_get_node_completion_returns_rate(
    db_session, svc, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    node = await make_node(proj.id, name="A", type="file")
    t1 = await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    await make_dim_record(user=user, project=proj, node=node, dim_type_id=t1)

    result = await svc.get_node_completion(db_session, project_id=proj.id, node_id=node.id)
    assert result["completion_rate"] == 1.0
    assert result["filled_count"] == 1


async def test_svc_get_node_completion_not_found_raises(
    db_session, svc, make_project, make_dim_type
):
    _, proj = await make_project()
    await make_dim_type(key="t1", project_id=proj.id, enabled=True)
    with pytest.raises(OverviewNodeNotFoundError):
        await svc.get_node_completion(db_session, project_id=proj.id, node_id=uuid4())
