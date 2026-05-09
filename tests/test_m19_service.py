"""M19 ExportService 单元测试（子片 3）。

覆盖：
- generate_markdown 单 node / 多 node golden（入口 A 等价 B 范式）
- include 选项控制章节出现（dimensions=False / competitors=True 等）
- _validate_and_load_nodes 跨 project node → 404 ExportNodeNotInProjectError
- 全空内容 → 422 ExportEmptyContentError
- activity_log 写入字面（action_type / target_type / metadata 字段集）
- write_event 异常传播（M16 元教训 / monkeypatch raise）
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from api.errors.exceptions import (
    ExportEmptyContentError,
    ExportNodeNotInProjectError,
)
from api.models.activity_log import ActivityLog
from api.schemas.export_schema import ExportIncludeOptions
from api.services.export_service import ACTION_EXPORT, TARGET_NODE, ExportService

pytestmark = pytest.mark.asyncio


# ─────────────── helpers ───────────────


@pytest_asyncio.fixture(loop_scope="session")
async def basic_project_with_node(db_session, make_project, make_node):
    """生成 project + 1 node 给 golden / empty 测试基用。"""
    user, proj = await make_project()
    node = await make_node(proj.id, name="账号系统")
    return user, proj, node


# ─────────────── golden ───────────────


async def test_generate_markdown_single_node_with_dimensions(
    db_session, basic_project_with_node, make_dim_type, make_dim_record
):
    """入口 B 单 node + 维度内容渲染 + activity_log 落库。"""
    user, proj, node = basic_project_with_node
    type_id = await make_dim_type(key="overview", name="概览", project_id=proj.id)
    await make_dim_record(
        user=user,
        project=proj,
        node=node,
        dim_type_id=type_id,
        content={"summary": "用户登录注册"},
    )

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[node.id],
        include=ExportIncludeOptions(),
        user_id=user.id,
    )

    text = body.decode("utf-8")
    assert text.startswith("# 分析报告 — ")
    assert proj.name in text
    assert "## 账号系统" in text
    assert "### 维度信息" in text
    assert "#### 概览" in text
    assert "**summary**: 用户登录注册" in text


async def test_generate_markdown_multi_node_preserves_input_order(
    db_session, make_project, make_node, make_dim_type, make_dim_record
):
    user, proj = await make_project()
    n1 = await make_node(proj.id, name="A 模块")
    n2 = await make_node(proj.id, name="B 模块")
    n3 = await make_node(proj.id, name="C 模块")
    type_id = await make_dim_type(key="x", name="X", project_id=proj.id)
    for n in (n1, n2, n3):
        await make_dim_record(
            user=user,
            project=proj,
            node=n,
            dim_type_id=type_id,
            content={"k": f"v-{n.name}"},
        )

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[n3.id, n1.id, n2.id],  # 故意非自然顺序
        include=ExportIncludeOptions(),
        user_id=user.id,
    )
    text = body.decode("utf-8")
    idx_c = text.index("## C 模块")
    idx_a = text.index("## A 模块")
    idx_b = text.index("## B 模块")
    assert idx_c < idx_a < idx_b, "Markdown 节顺序须严格按入参 node_ids"


async def test_include_options_omit_sections(
    db_session, basic_project_with_node, make_dim_type, make_dim_record, make_version
):
    user, proj, node = basic_project_with_node
    type_id = await make_dim_type(key="t", name="T", project_id=proj.id)
    await make_dim_record(
        user=user, project=proj, node=node, dim_type_id=type_id, content={"k": "v"}
    )
    await make_version(user=user, project=proj, node=node, label="v1.0")

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[node.id],
        include=ExportIncludeOptions(
            dimensions=False, versions=True, competitors=False, issues=False
        ),
        user_id=user.id,
    )
    text = body.decode("utf-8")
    assert "### 版本时间线" in text
    assert "### 维度信息" not in text


# ─────────────── 错误路径 ───────────────


async def test_cross_project_node_raises_not_in_project(db_session, make_project, make_node):
    user_a, proj_a = await make_project(name_suffix="-A")
    user_b, proj_b = await make_project(name_suffix="-B")
    node_b = await make_node(proj_b.id, name="other")

    with pytest.raises(ExportNodeNotInProjectError):
        await ExportService().generate_markdown(
            db_session,
            project_id=proj_a.id,
            node_ids=[node_b.id],  # 跨 project
            include=ExportIncludeOptions(),
            user_id=user_a.id,
        )


async def test_nonexistent_node_id_raises_not_in_project(db_session, basic_project_with_node):
    user, proj, _ = basic_project_with_node
    with pytest.raises(ExportNodeNotInProjectError):
        await ExportService().generate_markdown(
            db_session,
            project_id=proj.id,
            node_ids=[uuid4()],
            include=ExportIncludeOptions(),
            user_id=user.id,
        )


async def test_empty_content_raises_empty_content_error(db_session, basic_project_with_node):
    """node 存在但所有 include 章节均无内容 → 422 ExportEmptyContentError。"""
    user, proj, node = basic_project_with_node
    with pytest.raises(ExportEmptyContentError):
        await ExportService().generate_markdown(
            db_session,
            project_id=proj.id,
            node_ids=[node.id],
            include=ExportIncludeOptions(),
            user_id=user.id,
        )


# ─────────────── activity_log 字面 ───────────────


async def test_activity_log_metadata_full_field_set(
    db_session, basic_project_with_node, make_dim_type, make_dim_record
):
    """M14 立 / M19 复用：metadata 字段集每条 e2e 字面验。"""
    user, proj, node = basic_project_with_node
    type_id = await make_dim_type(key="t", name="T", project_id=proj.id)
    await make_dim_record(
        user=user, project=proj, node=node, dim_type_id=type_id, content={"k": "v"}
    )

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[node.id],
        include=ExportIncludeOptions(
            dimensions=True, versions=False, competitors=False, issues=False
        ),
        user_id=user.id,
    )

    rows = (
        (
            await db_session.execute(
                select(ActivityLog).where(
                    ActivityLog.project_id == proj.id, ActivityLog.action_type == ACTION_EXPORT
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action_type == "exported"
    assert ev.target_type == TARGET_NODE
    assert ev.target_id == str(node.id)
    md = ev.event_metadata
    assert md["node_count"] == 1
    assert md["node_ids"] == [str(node.id)]
    assert md["sections"] == {
        "dimensions": True,
        "versions": False,
        "competitors": False,
        "issues": False,
    }
    assert md["file_size_bytes"] == len(body)


async def test_write_event_failure_propagates(
    db_session, basic_project_with_node, make_dim_type, make_dim_record, monkeypatch
):
    """M16 立 / M19 复用：write_event 异常必须冒泡到 caller 不被吞。"""
    user, proj, node = basic_project_with_node
    type_id = await make_dim_type(key="t", name="T", project_id=proj.id)
    await make_dim_record(
        user=user, project=proj, node=node, dim_type_id=type_id, content={"k": "v"}
    )

    async def boom(**kw):
        raise RuntimeError("activity_log down")

    monkeypatch.setattr("api.services.export_service.write_event", boom)

    with pytest.raises(RuntimeError, match="activity_log down"):
        await ExportService().generate_markdown(
            db_session,
            project_id=proj.id,
            node_ids=[node.id],
            include=ExportIncludeOptions(),
            user_id=user.id,
        )


# ─────────────── 竞品 / 问题 章节 ───────────────


async def test_competitors_section_renders_when_enabled(
    db_session, basic_project_with_node, make_competitor, make_competitor_ref
):
    user, proj, node = basic_project_with_node
    comp = await make_competitor(project=proj, user=user, name="Notion")
    await make_competitor_ref(project=proj, node=node, competitor=comp, user=user)

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[node.id],
        include=ExportIncludeOptions(
            dimensions=False, versions=False, competitors=True, issues=False
        ),
        user_id=user.id,
    )
    text = body.decode("utf-8")
    assert "### 竞品参考" in text
    assert "Notion" in text


async def test_issues_section_renders_when_enabled(db_session, basic_project_with_node, make_issue):
    user, proj, node = basic_project_with_node
    await make_issue(user=user, project=proj, node=node, title="登录闪退", category="bug")

    body = await ExportService().generate_markdown(
        db_session,
        project_id=proj.id,
        node_ids=[node.id],
        include=ExportIncludeOptions(
            dimensions=False, versions=False, competitors=False, issues=True
        ),
        user_id=user.id,
    )
    text = body.decode("utf-8")
    assert "### 问题沉淀" in text
    assert "登录闪退" in text
    assert "bug" in text


# ─────────────── schema（同步测试 / 不走 asyncio）───────────────


class TestExportSchemaSync:
    """schema-only tests grouped to avoid module-level pytestmark warning。"""

    def test_schema_multi_node_request_enforces_max_20(self):
        """R1-A P1-2 立修：业务码 ExportNodeLimitExceededError 替裸 Pydantic validation_error
        （M15 ActivityStreamFilter 范式延续 / 422 + code=export_node_limit_exceeded）。"""
        from api.errors.exceptions import ExportNodeLimitExceededError
        from api.schemas.export_schema import MultiNodeExportRequest

        too_many = [uuid4() for _ in range(21)]
        with pytest.raises(ExportNodeLimitExceededError):
            MultiNodeExportRequest(node_ids=too_many)

    def test_schema_include_options_at_least_one_section(self):
        """R1-C P1-2 立修：include 全 False 提前 422（防 Service 走完 4 DAO 才发现空内容）。"""
        from api.errors.exceptions import ValidationError as AppVE
        from api.schemas.export_schema import ExportIncludeOptions

        with pytest.raises(AppVE):
            ExportIncludeOptions(dimensions=False, versions=False, competitors=False, issues=False)

    def test_schema_multi_node_request_min_1(self):
        from pydantic import ValidationError as PydanticVE

        from api.schemas.export_schema import MultiNodeExportRequest

        with pytest.raises(PydanticVE):
            MultiNodeExportRequest(node_ids=[])

    def test_schema_include_extra_forbid(self):
        from pydantic import ValidationError as PydanticVE

        from api.schemas.export_schema import ExportIncludeOptions

        with pytest.raises(PydanticVE):
            ExportIncludeOptions.model_validate({"dimensions": True, "unknown": True})
