"""M03 子片 1 — models 子片 schema 验证。

覆盖 design/02-modules/M03-module-tree/00-design.md §3：
- nodes 表存在 + 字段元数据（含 A2 reconcile 加的 description）
- 三重防护：type CHECK 拒非法值（A1 范式：Mapped[str] + DB CHECK）
- name/depth/sort_order CHECK
- path 物化路径 Text 无长度限制 + ix_nodes_path text_pattern_ops 索引存在
- FK 自关联 ON DELETE CASCADE（删父节点 → 子节点级联）
- FK to projects ON DELETE CASCADE
- 默认值：type='folder' / depth=0 / sort_order=0 / path=''
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

# ─────────────── M03-T1 表存在 + 字段 ───────────────


async def test_m03_t1_nodes_table_exists(db_session):
    rows = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name='nodes'"
        )
    )
    assert rows.one_or_none() is not None, "nodes 表应存在"


def test_m03_t2_node_model_fields_introspect():
    """ORM 层字段元数据：与 design §3 SQLAlchemy block 对齐 + A2 reconcile description。"""
    from sqlalchemy import String, Text
    from sqlalchemy.dialects.postgresql import UUID

    from api.models.node import Node

    cols = Node.__table__.c
    for required in (
        "id",
        "project_id",
        "parent_id",
        "name",
        "description",  # A2 reconcile
        "type",
        "depth",
        "sort_order",
        "path",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    ):
        assert required in cols, f"Node 缺字段 {required}"

    assert isinstance(cols["name"].type, String)
    assert cols["name"].type.length == 200
    assert cols["name"].nullable is False

    assert isinstance(cols["description"].type, String)
    assert cols["description"].type.length == 2000
    assert cols["description"].nullable is True

    # A1 范式：type 是 String(20) 非 Enum；DB CHECK 兜底
    assert isinstance(cols["type"].type, String)
    assert cols["type"].type.length == 20
    assert cols["type"].nullable is False

    # G5：path 是 Text 无 length 限制
    assert isinstance(cols["path"].type, Text)
    assert cols["path"].type.length is None

    # project_id FK to projects
    pid_fks = list(cols["project_id"].foreign_keys)
    assert any(fk.column.table.name == "projects" for fk in pid_fks)

    # parent_id 自关联 FK to nodes
    parent_fks = list(cols["parent_id"].foreign_keys)
    assert any(fk.column.table.name == "nodes" for fk in parent_fks)
    assert cols["parent_id"].nullable is True

    assert isinstance(cols["id"].type, UUID)


# ─────────────── M03-T3/T4 三重防护 CHECK ───────────────


async def _make_user_and_project(db_session):
    from api.auth.password import hash_password
    from api.models.project import Project
    from api.models.user import User

    user = User(
        email=f"u-{uuid4().hex[:8]}@example.com",
        name="X",
        password_hash=hash_password("Password123!"),
        role="user",
        status="active",
        failed_login_count=0,
        version=1,
    )
    db_session.add(user)
    await db_session.flush()

    proj = Project(name=f"P-{uuid4().hex[:8]}", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()
    return user, proj


async def test_m03_t3_node_type_check_rejects_unknown(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    bad = Node(project_id=proj.id, name="X", type="weirdtype")
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "nodes.type CHECK 应拒未知值"


async def test_m03_t4_node_name_empty_rejected(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    bad = Node(project_id=proj.id, name="")
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "ck_node_name_not_empty 应拒空 name"


async def test_m03_t5_depth_negative_rejected(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    bad = Node(project_id=proj.id, name="X", depth=-1)
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "ck_node_depth_non_negative 应拒 depth<0"


async def test_m03_t6_sort_order_negative_rejected(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    bad = Node(project_id=proj.id, name="X", sort_order=-1)
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "ck_node_sort_order_non_negative 应拒 sort_order<0"


# ─────────────── M03-T7 默认值 ───────────────


async def test_m03_t7_node_defaults(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    n = Node(project_id=proj.id, name="Default")
    db_session.add(n)
    await db_session.flush()
    await db_session.refresh(n)

    assert n.type == "folder"
    assert n.depth == 0
    assert n.sort_order == 0
    assert n.path == ""
    assert n.parent_id is None
    assert n.description is None


# ─────────────── M03-T8 FK 自关联 CASCADE 删除子树 ───────────────


async def test_m03_t8_parent_delete_cascades_children(db_session):
    """删父节点 → 子节点级联（DB 层兜底；M03 §6 R-X2 Service 层显式调下游另测）。"""
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    root = Node(project_id=proj.id, name="root", path="/", depth=0)
    db_session.add(root)
    await db_session.flush()

    child = Node(
        project_id=proj.id,
        parent_id=root.id,
        name="child",
        path=f"/{root.id}/",
        depth=1,
    )
    db_session.add(child)
    await db_session.flush()

    rid = root.id
    cid = child.id

    await db_session.execute(text("DELETE FROM nodes WHERE id = :id"), {"id": rid})
    await db_session.flush()

    r = await db_session.execute(text("SELECT COUNT(*) FROM nodes WHERE id = :id"), {"id": cid})
    assert r.scalar_one() == 0, "子节点应被 ON DELETE CASCADE 清理"


# ─────────────── M03-T9 FK to projects CASCADE ───────────────


async def test_m03_t9_project_delete_cascades_nodes(db_session):
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    n = Node(project_id=proj.id, name="orphan-test")
    db_session.add(n)
    await db_session.flush()

    pid = proj.id
    await db_session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})
    await db_session.flush()

    r = await db_session.execute(
        text("SELECT COUNT(*) FROM nodes WHERE project_id = :pid"), {"pid": pid}
    )
    assert r.scalar_one() == 0, "项目删除 → nodes 应被 CASCADE 清理"


# ─────────────── M03-T10 path 长字符串接受 ───────────────


async def test_m03_t10_path_accepts_long_string(db_session):
    """G5：path Text 无长度限制（深度树支持）。"""
    from api.models.node import Node

    _, proj = await _make_user_and_project(db_session)
    long_path = "/" + "/".join([uuid4().hex for _ in range(50)]) + "/"
    n = Node(project_id=proj.id, name="DeepNode", path=long_path, depth=50)
    db_session.add(n)
    await db_session.flush()
    await db_session.refresh(n)
    assert n.path == long_path
    assert len(n.path) > 1500


# ─────────────── M03-T11 ix_nodes_path text_pattern_ops 索引 ───────────────


async def test_m03_t11_ix_nodes_path_uses_text_pattern_ops(db_session):
    """G5：path LIKE 前缀子树查询需 text_pattern_ops opclass。"""
    r = await db_session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE schemaname='public' AND indexname='ix_nodes_path'"
        )
    )
    row = r.one_or_none()
    assert row is not None, "ix_nodes_path 索引应存在"
    indexdef = row[0]
    assert "text_pattern_ops" in indexdef, (
        f"ix_nodes_path 应使用 text_pattern_ops opclass，indexdef={indexdef!r}"
    )


# ─────────────── M03-T12 NodeType 枚举值 ───────────────


def test_m03_t12_node_type_enum_values():
    from api.models.node import NodeType

    assert NodeType.FOLDER.value == "folder"
    assert NodeType.FILE.value == "file"
    assert {t.value for t in NodeType} == {"folder", "file"}
