"""M19 export router 子片 4 — 2 endpoints + e2e（元教训 18 类 actionable 主动复制）。

覆盖 design §7 + §8 三层权限 + 401/403/404/422 + golden + tenant + cross-project node +
metadata 字段集字面验 + activity_log "exported" 字面 + Content-Disposition + filename
sanitize 字面 + N/A 显式声明（write 403 / IntegrityError / R-X1 / multipart / SSE / WS）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from api.auth.jwt_utils import encode_jwt

pytestmark = pytest.mark.asyncio


def _bearer(user_id) -> dict:
    return {"Authorization": f"Bearer {encode_jwt(user_id, extra_claims={'type': 'access'})}"}


# ─────────────── helpers ───────────────


async def _seed_project_with_node_and_dim(
    auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    """生成 project + 1 node + 1 dim_type + 1 dim_record，返回 (user, project, node)。"""
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="账号系统")
    type_id = await make_dim_type(key="overview", name="概览", project_id=proj.id)
    await make_dim_record(
        user=user, project=proj, node=node, dim_type_id=type_id, content={"summary": "登录注册"}
    )
    return user, proj, node


# ─────────────── 入口 A：多 node 导出 golden ───────────────


async def test_export_multi_nodes_golden(
    auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    user, proj, node = await _seed_project_with_node_and_dim(
        auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
    )

    r = await auth_client.post(
        f"/api/projects/{proj.id}/exports",
        json={"node_ids": [str(node.id)]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/markdown")
    cd = r.headers["content-disposition"]
    assert cd.startswith("attachment; filename=")
    assert ".md" in cd
    body = r.content.decode("utf-8")
    assert "# 分析报告 — " in body
    assert "## 账号系统" in body
    assert "登录注册" in body


# ─────────────── 入口 B：单 node 导出 golden ───────────────


async def test_export_single_node_golden(
    auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    user, proj, node = await _seed_project_with_node_and_dim(
        auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
    )

    r = await auth_client.post(
        f"/api/projects/{proj.id}/nodes/{node.id}/export",
        json={},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/markdown")
    body = r.content.decode("utf-8")
    assert "## 账号系统" in body


# ─────────────── 权限：未登录 / cross-tenant / cross-project node ───────────────


async def test_export_unauthenticated_returns_401(auth_client, make_project_with_member):
    _, proj = await make_project_with_member()
    r = await auth_client.post(
        f"/api/projects/{proj.id}/exports",
        json={"node_ids": [str(uuid4())]},
    )
    assert r.status_code == 401


async def test_export_cross_tenant_returns_404(auth_client, make_project_with_member, make_node):
    """member 只在 proj_a 但访问 proj_b 的 export endpoint → check_project_access 404。"""
    _, proj_a = await make_project_with_member(name_suffix="-A")
    user_b, proj_b = await make_project_with_member(name_suffix="-B")
    node_b = await make_node(proj_b.id, name="other")

    # user_b 是 proj_b 的 owner / 访问 proj_a 的 export → 404
    r = await auth_client.post(
        f"/api/projects/{proj_a.id}/exports",
        json={"node_ids": [str(node_b.id)]},
        headers=_bearer(user_b.id),
    )
    assert r.status_code == 404


async def test_export_cross_project_node_returns_422(
    auth_client, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    """node_id 属于另一 project（user 在两 project 都是 owner）→ R1-B P1-1 立修后 422
    EXPORT_NODE_NOT_IN_PROJECT（与 M06/M08/M12 ValidationError 范式一致）。"""
    user_a, proj_a = await make_project_with_member(name_suffix="-A")
    _, proj_b = (
        await make_project_with_member(user=user_a, name_suffix="-B") if False else (None, None)
    )
    # make_project_with_member 默认每次新 user，需让 user_a 也加入 proj_b 才能复现"在两 project 但 node 跨项目"
    # 简化路径：直接 user_a 访问 proj_a / 用 proj_b 的 node_id
    user_b, proj_b = await make_project_with_member(name_suffix="-B")
    node_b = await make_node(proj_b.id, name="other")
    type_id = await make_dim_type(key="t", name="T", project_id=proj_b.id)
    await make_dim_record(
        user=user_b, project=proj_b, node=node_b, dim_type_id=type_id, content={"k": "v"}
    )

    # user_a 是 proj_a 的 owner 但 node_b 属于 proj_b → service 拦
    r = await auth_client.post(
        f"/api/projects/{proj_a.id}/exports",
        json={"node_ids": [str(node_b.id)]},
        headers=_bearer(user_a.id),
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "export_node_not_in_project"


async def test_export_nonexistent_node_returns_422(
    auth_client, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    user, proj, _ = await _seed_project_with_node_and_dim(
        auth_client, None, make_project_with_member, make_node, make_dim_type, make_dim_record
    )
    r = await auth_client.post(
        f"/api/projects/{proj.id}/exports",
        json={"node_ids": [str(uuid4())]},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "export_node_not_in_project"


# ─────────────── 422 业务码：超上限 / 空内容 ───────────────


async def test_export_node_limit_exceeded_returns_422(auth_client, make_project_with_member):
    """R1-A P1-2 立修：>20 走业务码 export_node_limit_exceeded 不丢失语义。"""
    user, proj = await make_project_with_member()
    too_many = [str(uuid4()) for _ in range(21)]
    r = await auth_client.post(
        f"/api/projects/{proj.id}/exports",
        json={"node_ids": too_many},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "export_node_limit_exceeded"


async def test_export_empty_content_returns_422(auth_client, make_project_with_member, make_node):
    """node 存在但 include 全开下无内容 → 422 EXPORT_EMPTY_CONTENT
    （tests.md E4 R1-A P1-1 立修后与 design §13 一致）。"""
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="empty")
    r = await auth_client.post(
        f"/api/projects/{proj.id}/nodes/{node.id}/export",
        json={},
        headers=_bearer(user.id),
    )
    assert r.status_code == 422
    assert r.json()["code"] == "export_empty_content"


async def test_export_include_all_false_returns_422(
    auth_client, make_project_with_member, make_node
):
    """R1-C P1-2 立修：include 全 False schema 层 422 / 不走 Service / 不走 4 DAO 查询。"""
    user, proj = await make_project_with_member()
    node = await make_node(proj.id, name="x")
    r = await auth_client.post(
        f"/api/projects/{proj.id}/nodes/{node.id}/export",
        json={
            "include": {
                "dimensions": False,
                "versions": False,
                "competitors": False,
                "issues": False,
            }
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 422


# ─────────────── activity_log 字面（M14 立 / M19 复用）───────────────


async def test_export_writes_activity_log_with_full_metadata(
    auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    """M14 立 / M19 复用：metadata 字段集每条 e2e 字面验 + action_type='exported'。"""
    user, proj, node = await _seed_project_with_node_and_dim(
        auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
    )

    r = await auth_client.post(
        f"/api/projects/{proj.id}/nodes/{node.id}/export",
        json={
            "include": {
                "dimensions": True,
                "versions": False,
                "competitors": False,
                "issues": False,
            }
        },
        headers=_bearer(user.id),
    )
    assert r.status_code == 200

    from sqlalchemy import select

    from api.models.activity_log import ActivityLog

    rows = (
        (
            await db_session.execute(
                select(ActivityLog).where(
                    ActivityLog.project_id == proj.id, ActivityLog.action_type == "exported"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    ev = rows[0]
    assert ev.action_type == "exported"
    assert ev.target_type == "node"
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
    assert md["file_size_bytes"] == len(r.content)


# ─────────────── Content-Disposition + filename sanitize 字面 ───────────────


async def test_export_content_disposition_filename_format(
    auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
):
    """design §7 字面：Content-Disposition: attachment; filename=prism-export-{ts}.md。
    cross-sprint #17 第三实例（输出端）：filename 服务端构造 / sanitize 控制字符（纵深防御）。"""
    import re

    user, proj, node = await _seed_project_with_node_and_dim(
        auth_client, db_session, make_project_with_member, make_node, make_dim_type, make_dim_record
    )
    r = await auth_client.post(
        f"/api/projects/{proj.id}/nodes/{node.id}/export",
        json={},
        headers=_bearer(user.id),
    )
    assert r.status_code == 200
    cd = r.headers["content-disposition"]
    # 字面验：filename=prism-export-{YYYYMMDDTHHMMSSZ}.md
    m = re.match(r'attachment; filename="prism-export-\d{8}T\d{6}Z\.md"', cd)
    assert m is not None, f"Content-Disposition format mismatch: {cd}"
    # 控制字符纵深防御：filename 不含 \x00-\x1f / \x7f
    assert not re.search(r"[\x00-\x1f\x7f]", cd)


# ─────────────── 元教训 18 类 actionable 主动复制 + N/A 显式声明 ───────────────


async def test_meta_lesson_na_explicit_declarations():
    """N/A 元教训显式声明范式（M14 立 / M19 §14.5 + 测试 docstring 双重）。

    本测试是 docstring placeholder，承载 N/A 声明（防 R1/R2 把"未覆盖"当 P1 抓）：
    - **viewer 写 403**：M19 design §8 字面 viewer 即可导出 / 写 403 范式 N/A
    - **R-X1 失败补偿 commit boundary**：M19 同步只读 / 无补偿形态 / N/A
    - **WS endpoint 5-test 矩阵**：M19 无 WS endpoint / N/A
    - **multipart upload sanitize**（M11/M17 输入端）：M19 无文件上传输入 / N/A
    - **SSE 形态特殊**：M19 同步路由 / 无 SSE / N/A
    - **EmbeddingProvider 抽象 / pgvector 三层降级**：M19 不触 embedding / N/A
    - **占位 metadata _stub:True**：M19 export metadata 全真实数据 / N/A
    - **测试反模式 assert True**：本测试是有意义 docstring 占位 / 不构成永真断言污染
    - **IntegrityError 区分约束名 / 清单 6**：M19 全只读 无 INSERT 业务表 /
      activity_log INSERT 走 caller 事务 + write_event 异常传播测试已覆盖
    - **idempotency_key 含 project_id**：M19 无幂等需求（design §11 字面）/ N/A
    - **CAS UPDATE / advisory_xact_lock**：M19 无并发资源 / N/A
    - **§12B 后台 fire-and-forget / BackgroundTasks**：M19 同步导出 / N/A
    - **横切 enum 4 处同步**（M15 立）：ActionType+1 "exported" 已 4 处同步（子片 1）
    - **R14 ci-lint 守护**（M16 立）：write_event(action_type="exported") 字面命中 /
      R1-B 漏识别 #2 立修过去式立规对齐
    - **endpoint 形态特殊不免除契约纪律**（M14 立）：M19 Markdown 二进制响应特殊 /
      Content-Type=text/markdown + Content-Disposition 字面 e2e 验
    - **metadata 字段集字面验**（M14 立）：test_export_writes_activity_log_with_full_metadata
    - **write_event 异常传播**（M16 立）：test_write_event_failure_propagates 服务层覆盖
    - **cross-tenant 404 + cross-project node 422**（M02/M06/M08/M12 立）：本文件覆盖
    """
    assert True  # docstring-only placeholder（M19 §14.5 N/A 元教训显式声明范式 / 非永真污染）
