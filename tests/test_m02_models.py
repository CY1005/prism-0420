"""M02 子片 1 — models 子片 schema 验证。

覆盖 design/02-modules/M02-project/00-design.md §3：
- 4 表存在 (projects / project_members / project_dimension_configs / dimension_types)
- 三重防护：status / role CHECK 拒非法值
- G3 部分唯一索引：同 owner 下 active 项目名唯一，archived 释放
- M18 baseline-patch：rrf_k / similarity_threshold range check
- M20 baseline-patch (A1=C 中间态)：team_id 是 UUID nullable 但 **不带 FK constraint**
- R3-6-B placeholder seed：dimension_types 表至少 1 条 default 行
- 默认值：hierarchy_labels JSONB / status='active'
- FK CASCADE：project_members 在 project 删除时级联
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

# ─────────────── M02-T1 4 表存在 ───────────────


M02_TABLES = ("projects", "project_members", "project_dimension_configs", "dimension_types")


async def test_m02_t1_all_four_tables_exist(db_session):
    rows = await db_session.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name = ANY(:names)"
        ),
        {"names": list(M02_TABLES)},
    )
    found = {r[0] for r in rows}
    missing = set(M02_TABLES) - found
    assert not missing, f"missing tables: {missing}"


# ─────────────── M02-T2/T3 三重防护 CHECK ───────────────


async def _make_user(db_session):
    from api.auth.password import hash_password
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
    return user


async def test_m02_t2_projects_status_check_rejects_unknown(db_session):
    from api.models.project import Project

    user = await _make_user(db_session)
    bad = Project(name="X", status="frozen", owner_id=user.id)
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "projects.status CHECK 应拒 'frozen'"


async def test_m02_t3_project_members_role_check_rejects_unknown(db_session):
    from api.models.project import Project, ProjectMember

    user = await _make_user(db_session)
    proj = Project(name="P1", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()

    bad = ProjectMember(project_id=proj.id, user_id=user.id, role="superadmin")
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "project_members.role CHECK 应拒 'superadmin'"


# ─────────────── M02-T4 G3 部分唯一索引 ───────────────


async def test_m02_t4_active_project_name_unique_per_owner(db_session):
    """同 owner 同 name 同 active → 第二条冲突。"""
    from api.models.project import Project

    user = await _make_user(db_session)
    p1 = Project(name="DupName", owner_id=user.id)
    db_session.add(p1)
    await db_session.flush()

    p2 = Project(name="DupName", owner_id=user.id)
    db_session.add(p2)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "uq_project_owner_name_active 部分唯一索引应拒同名 active 项目"


async def test_m02_t5_archived_project_releases_name(db_session):
    """归档后释放 name → 同 owner 同 name 新建 active 不冲突（G3-b）。"""
    from api.models.project import Project

    user = await _make_user(db_session)
    p1 = Project(name="ReuseName", owner_id=user.id, status="archived")
    db_session.add(p1)
    await db_session.flush()

    p2 = Project(name="ReuseName", owner_id=user.id, status="active")
    db_session.add(p2)
    await db_session.flush()  # 不应抛
    assert p2.id is not None


# ─────────────── M02-T6/T7 M18 baseline-patch range check ───────────────


@pytest.mark.parametrize("rrf_k", [0, -1, 201, 1000])
async def test_m02_t6_rrf_k_out_of_range_rejected(db_session, rrf_k):
    from api.models.project import Project

    user = await _make_user(db_session)
    bad = Project(name=f"R{rrf_k}", owner_id=user.id, rrf_k=rrf_k)
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, f"rrf_k={rrf_k} 应被 ck_project_rrf_k_range 拒"


@pytest.mark.parametrize("threshold", [-0.1, 1.1, 2.0])
async def test_m02_t7_similarity_threshold_out_of_range_rejected(db_session, threshold):
    from api.models.project import Project

    user = await _make_user(db_session)
    bad = Project(name=f"T{threshold}", owner_id=user.id, similarity_threshold=threshold)
    db_session.add(bad)
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, f"similarity_threshold={threshold} 应被 ck_project_similarity_threshold_range 拒"


# ─────────────── M02-T8 M20 baseline-patch A1=C 中间态：team_id 无 FK ───────────────


async def test_m02_t8_team_id_is_nullable_uuid_no_fk(db_session):
    """A1=C 中间态验证：team_id 列存在 + 类型 UUID + nullable=YES + 无 FK constraint。

    M20 sprint 才 ALTER ADD CONSTRAINT FK ondelete=RESTRICT。
    本测试保证 M02-M19 期可写任意 UUID 不被拒（teams 表此期间不存在）。
    """
    r = await db_session.execute(
        text(
            "SELECT data_type, is_nullable FROM information_schema.columns "
            "WHERE table_name='projects' AND column_name='team_id'"
        )
    )
    data_type, is_nullable = r.one()
    assert data_type.lower() == "uuid"
    assert is_nullable == "YES"

    # 检查 projects.team_id 上无 FK constraint
    fks = await db_session.execute(
        text(
            "SELECT tc.constraint_name "
            "FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "  ON tc.constraint_name = kcu.constraint_name "
            "WHERE tc.table_name='projects' AND tc.constraint_type='FOREIGN KEY' "
            "  AND kcu.column_name='team_id'"
        )
    )
    fk_names = list(fks.scalars())
    assert not fk_names, f"M02 期 projects.team_id 不应有 FK（A1=C 中间态）；found: {fk_names}"


async def test_m02_t9_team_id_accepts_arbitrary_uuid(db_session):
    """M02-M19 期写任意 UUID 到 team_id（teams 表不存在，无 FK 拒绝）。"""
    from api.models.project import Project

    user = await _make_user(db_session)
    arbitrary = uuid4()
    proj = Project(name="TeamProj", owner_id=user.id, team_id=arbitrary)
    db_session.add(proj)
    await db_session.flush()  # 不应抛
    assert proj.team_id == arbitrary


# ─────────────── M02-T10 R3-6-B placeholder seed ───────────────


async def test_m02_t10_dimension_types_has_default_seed(db_session):
    """R3-6-B：alembic data migration 必种 1 条 key='default' 行（测试兜底 placeholder）。"""
    r = await db_session.execute(text("SELECT key, name FROM dimension_types WHERE key='default'"))
    row = r.one_or_none()
    assert row is not None, "R3-6-B placeholder seed 缺失：dimension_types 应有 key='default' 行"
    assert row[1] == "默认维度"


# ─────────────── M02-T11 默认值 ───────────────


async def test_m02_t11_project_defaults(db_session):
    """status / hierarchy_labels / template_type / version_mode / rrf_k / similarity_threshold 默认值。"""
    from api.models.project import Project

    user = await _make_user(db_session)
    proj = Project(name="DefaultProj", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()
    await db_session.refresh(proj)

    assert proj.status == "active"
    assert proj.hierarchy_labels == ["层级1", "层级2", "层级3"]
    assert proj.template_type == "custom"
    assert proj.version_mode == "release"
    assert proj.rrf_k == 60
    assert proj.similarity_threshold == 0.3


# ─────────────── M02-T12 唯一约束 ───────────────


async def test_m02_t12_project_member_unique_per_user(db_session):
    """UNIQUE(project_id, user_id) 拒重复加入。"""
    from api.models.project import Project, ProjectMember

    user = await _make_user(db_session)
    proj = Project(name="UniqProj", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()

    db_session.add(ProjectMember(project_id=proj.id, user_id=user.id, role="owner"))
    await db_session.flush()

    db_session.add(ProjectMember(project_id=proj.id, user_id=user.id, role="viewer"))
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "uq_project_member 应拒同 (project_id, user_id) 重复"


async def test_m02_t13_dimension_config_unique_per_project_per_type(db_session):
    """UNIQUE(project_id, dimension_type_id) 拒重复配置。"""
    from api.models.project import Project, ProjectDimensionConfig

    user = await _make_user(db_session)
    proj = Project(name="DimUniqProj", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()

    # 用 R3-6-B seed 的 default 类型 id
    r = await db_session.execute(text("SELECT id FROM dimension_types WHERE key='default'"))
    dim_type_id = r.scalar_one()

    db_session.add(
        ProjectDimensionConfig(project_id=proj.id, dimension_type_id=dim_type_id, enabled=True)
    )
    await db_session.flush()

    db_session.add(
        ProjectDimensionConfig(project_id=proj.id, dimension_type_id=dim_type_id, enabled=False)
    )
    raised = False
    try:
        await db_session.flush()
    except Exception:
        raised = True
    finally:
        await db_session.rollback()
    assert raised, "uq_proj_dim_config 应拒同 (project_id, dimension_type_id) 重复"


# ─────────────── M02-T14 字段元数据 introspection ───────────────


def test_m02_t14_project_model_fields_introspect():
    """ORM 层字段元数据：与 design §3 SQLAlchemy block 对齐。"""
    from sqlalchemy import String
    from sqlalchemy.dialects.postgresql import JSONB, UUID

    from api.models.project import Project

    cols = Project.__table__.c
    # 关键字段存在
    for required in (
        "id",
        "name",
        "description",
        "status",
        "template_type",
        "hierarchy_labels",
        "version_mode",
        "ai_provider",
        "ai_api_key_enc",
        "owner_id",
        "team_id",
        "rrf_k",
        "similarity_threshold",
        "created_at",
        "updated_at",
    ):
        assert required in cols, f"Project 缺字段 {required}"

    # ai_api_key_enc 长度 1000 (AES-GCM base64)
    assert isinstance(cols["ai_api_key_enc"].type, String)
    assert cols["ai_api_key_enc"].type.length == 1000
    assert cols["ai_api_key_enc"].nullable is True

    # hierarchy_labels JSONB
    assert isinstance(cols["hierarchy_labels"].type, JSONB)
    assert cols["hierarchy_labels"].nullable is False

    # owner_id UUID FK to users（这条保留 FK；A1=C 仅针对 team_id）
    assert isinstance(cols["owner_id"].type, UUID)
    assert cols["owner_id"].nullable is False
    owner_fks = list(cols["owner_id"].foreign_keys)
    assert any(fk.column.table.name == "users" for fk in owner_fks), "owner_id 应 FK to users"

    # team_id UUID nullable 无 FK（A1=C 中间态；ORM 层也不挂 ForeignKey）
    assert isinstance(cols["team_id"].type, UUID)
    assert cols["team_id"].nullable is True
    team_fks = list(cols["team_id"].foreign_keys)
    assert not team_fks, (
        "M02 期 ORM 层 projects.team_id 不应挂 ForeignKey（A1=C 中间态；M20 sprint 启用）"
    )


# ─────────────── M02-T15 FK CASCADE 行为 ───────────────


async def test_m02_t15_project_member_cascade_on_project_delete(db_session):
    """删 project → project_members 级联清理（CASCADE）。"""
    from api.models.project import Project, ProjectMember

    user = await _make_user(db_session)
    proj = Project(name="CascadeProj", owner_id=user.id)
    db_session.add(proj)
    await db_session.flush()
    pid = proj.id

    db_session.add(ProjectMember(project_id=pid, user_id=user.id, role="owner"))
    await db_session.flush()

    await db_session.execute(text("DELETE FROM projects WHERE id = :pid"), {"pid": pid})
    await db_session.flush()

    r = await db_session.execute(
        text("SELECT COUNT(*) FROM project_members WHERE project_id = :pid"), {"pid": pid}
    )
    assert r.scalar_one() == 0, "project_members 应被 CASCADE 清理"
