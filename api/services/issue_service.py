"""M07 IssueService — design/02-modules/M07-issue/00-design.md §6.

事务边界（M02-M06 范式延续）：
  - **Router 层管 commit**；本 service 接受外部 AsyncSession，不调
    ``async with db.begin():`` / 不主动 commit / 不主动 rollback。
  - SQLAlchemy autobegin + Router endpoint 末 ``await db.commit()``；异常自动回滚。
  - **状态转换 SELECT FOR UPDATE 行锁串行化**（design §5）：
    transition 内调 dao.get_for_update → 校验状态 → UPDATE，并发请求被 PG 行锁串行。
  - R-X3 跨模块入口 ``orphan_by_node_id``（M03 delete_node R-X2 第三真注入）：
    接受外部 db session，由 caller orchestrator 控制事务。

权限三层（design §8）：
  - Server Action / Router check_project_access（外层）
  - Service _check_node_belongs_to_project（cross-project node_id 防御）
  - Service 状态机校验（IssueTransitionInvalidError / IssueClosedError）

R-X2 第三真注入方（**orphan 语义**，与 M04/M06 delete 不同）：
  - orphan_by_node_id(db, node_id, project_id, actor_user_id) → UPDATE issues
    SET node_id = NULL（不是 DELETE）+ 每条独立 orphan activity_log
  - 异常契约 (R1-C P1-01)：不 catch-all 静默吞错

# Scaffold 简化决策（2026-05-08，A6 闸门 2.5 — M18 baseline-patch get_for_embedding A 路径）
# ① 决策内容：M07 sprint 期 create / update / delete commit 后**不调** embedding_service.enqueue
#    / enqueue_delete；get_for_embedding 实装拼接 title + description（M07 无 url 字段）
# ② 简化理由：M18 own embedding_service 在 M07 sprint 期不存在（B caller）
# ③ 由 M18 sprint 扩齐：IssueService 三处 commit 后尾调 enqueue + 回归测试
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M07 §6.X 实施期处理段 status

# Scaffold 简化决策（2026-05-08 — M11/M17 batch_create_in_transaction）
# ① 决策内容：design §6 列的 batch_create_in_transaction M07 sprint 期不实装；
#    router 不暴露入口（M07 自身 create/update/delete 已覆盖回归测试需求）
# ② 简化理由：M11 cold-start / M17 ai-import 模块期不存在，无 caller（与 M04/M06 同款 punt）
# ③ 由 M11 / M17 各 sprint 启动时按需追加 service 方法
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.issue_dao import IssueDAO
from api.dao.node_dao import NodeDAO
from api.errors.exceptions import (
    IssueAssigneeRequiredError,
    IssueClosedError,
    IssueNodeCrossProjectError,
    IssueNotFoundError,
    IssueTransitionInvalidError,
)
from api.models.issue import Issue
from api.services.activity_log_service import write_event

# 状态机允许转换（design §4）
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "resolved"},
    "in_progress": {"open", "resolved"},
    "resolved": {"closed"},
    "closed": set(),  # 终态 — 任何转换 IssueClosedError
}


class IssueService:
    """M07 问题沉淀 service。"""

    def __init__(
        self,
        dao: IssueDAO | None = None,
        node_dao: NodeDAO | None = None,
    ) -> None:
        self.dao = dao or IssueDAO()
        self.node_dao = node_dao or NodeDAO()

    # ─── 内部校验 ───

    async def _check_node_in_project(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> None:
        """node_id 非空时，校验 node 属于该 project（IssueNodeCrossProjectError）。"""
        node = await self.node_dao.get_by_id(db, node_id, project_id)
        if node is None:
            raise IssueNodeCrossProjectError(node_id=str(node_id), project_id=str(project_id))

    async def _get_or_raise(self, db: AsyncSession, issue_id: UUID, project_id: UUID) -> Issue:
        i = await self.dao.get_by_id(db, issue_id, project_id)
        if i is None:
            raise IssueNotFoundError(issue_id=str(issue_id))
        return i

    # ─── 读 ───

    async def list_by_project(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        category: str | None = None,
        status: str | None = None,
        node_id: UUID | None = None,
        tag: str | None = None,
        limit: int | None = None,
    ) -> Sequence[Issue]:
        """M13 pilot 跨模块调用契约（design §6 R-X3，pass-through DAO）。"""
        return await self.dao.list_by_project(
            db,
            project_id,
            category=category,
            status=status,
            node_id=node_id,
            tag=tag,
            limit=limit,
        )

    async def get_by_id(self, db: AsyncSession, *, project_id: UUID, issue_id: UUID) -> Issue:
        return await self._get_or_raise(db, issue_id, project_id)

    # ─── 写 ───

    async def batch_create_in_transaction(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        issues_data: list[dict[str, Any]],
    ) -> list[Issue]:
        """M11/M17 调用入口（R-X3 共享外部 session，R-X1 orchestrator 模式）。

        issues_data 每条形如 {category, title, description, node_id?, tags?, assigned_to?}。
        每条独立写 create activity_log（R10-1 batch3）；任一失败由 caller 事务回滚。
        M11 sprint 接通（M07 sprint scaffold "M11/M17 sprint 期不实装" 到期，2026-05-08）。
        """
        created: list[Issue] = []
        for raw in issues_data:
            i = await self.create(
                db,
                project_id=project_id,
                category=raw["category"],
                title=raw["title"],
                description=raw["description"],
                node_id=raw.get("node_id"),
                tags=raw.get("tags"),
                assigned_to=raw.get("assigned_to"),
                actor_user_id=actor_user_id,
            )
            created.append(i)
        return created

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        category: str,
        title: str,
        description: str,
        actor_user_id: UUID,
        node_id: UUID | None = None,
        tags: list[str] | None = None,
        assigned_to: UUID | None = None,
    ) -> Issue:
        if node_id is not None:
            await self._check_node_in_project(db, node_id, project_id)
        i = Issue(
            id=uuid4(),
            project_id=project_id,
            node_id=node_id,
            category=category,
            status="open",
            title=title,
            description=description,
            tags=tags if tags is not None else [],
            created_by=actor_user_id,
            assigned_to=assigned_to,
        )
        await self.dao.create(db, i)
        await db.refresh(i, attribute_names=["created_at", "updated_at"])
        # Phase 2.2 子片 5 D 类 #3：response join 字段（node_name / created_by_name /
        # assigned_to_name）需 eager-load 三 relationship；model lazy="raise" 杜绝 async
        # lazy-load 静默失败 / 此处再走一次 dao.get_by_id（带 _JOINS 选项）拿装配实例
        loaded = await self.dao.get_by_id(db, i.id, project_id)
        assert loaded is not None  # 刚 INSERT 后 SELECT 必命中
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="issue_created",
            target_type="issue",
            target_id=str(i.id),
            summary=f"Created issue '{title}'",
            metadata={
                "node_id": str(node_id) if node_id else None,
                "category": category,
                "status": "open",
            },
        )
        return loaded

    async def update(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        issue_id: UUID,
        actor_user_id: UUID,
        fields: dict[str, Any],
    ) -> Issue:
        """更新内容（**非状态**）。状态走 transition() 路径。

        L1-α 用户路径完整性（4C.3 detach / cross-module 立规）：fields 来自 router
        ``model_dump(exclude_unset=True)``，显式传 ``None`` = detach（清 nullable FK），
        未传字段不进 fields = keep。同 M14 industry_news 范式。
        """
        existing = await self._get_or_raise(db, issue_id, project_id)
        if "node_id" in fields and fields["node_id"] is not None:
            await self._check_node_in_project(db, fields["node_id"], project_id)
        if not fields:
            return existing

        rows = await self.dao.update(db, issue_id, project_id, fields=fields)
        if rows == 0:
            raise IssueNotFoundError(issue_id=str(issue_id))
        await db.refresh(existing, attribute_names=list(fields.keys()) + ["updated_at"])
        # Phase 2.2 子片 5 D 类 #3：refetch with joins for response。
        # Sprint 2 e2e #6 暴露问题：raw UPDATE 后 SQLAlchemy identity map 仍持 existing 旧
        # selectinload 关系（node/created_by_user/assigned_to_user）；db.refresh 只刷 column
        # 不触发 selectinload 重跑；db.get_by_id 走 identity map 命中也返回同一 instance。
        # → expunge existing 让 dao.get_by_id 真重 SELECT + 触发 _JOINS selectinload。
        db.expunge(existing)
        loaded = await self.dao.get_by_id(db, issue_id, project_id)
        assert loaded is not None
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="issue_updated",
            target_type="issue",
            target_id=str(issue_id),
            summary=f"Updated issue '{loaded.title}'",
            metadata={"changed_fields": list(fields.keys())},
        )
        return loaded

    async def transition(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        issue_id: UUID,
        target_status: str,
        actor_user_id: UUID,
        assigned_to: UUID | None = None,
        note: str | None = None,
    ) -> Issue:
        """状态机转换（design §4 + §5 SELECT FOR UPDATE 行锁串行化）。

        - SELECT FOR UPDATE 锁定行 → 校验当前 status → UPDATE
        - closed → 任何 = IssueClosedError
        - 不在 _ALLOWED_TRANSITIONS = IssueTransitionInvalidError
        - open → in_progress 时 assigned_to 必填 (IssueAssigneeRequiredError)
        - in_progress → open 时 assigned_to 重置 NULL（取消认领，design §4 P5 audit F-3）
        - * → resolved 写 resolved_at
        """
        existing = await self.dao.get_for_update(db, issue_id, project_id)
        if existing is None:
            raise IssueNotFoundError(issue_id=str(issue_id))
        old_status = existing.status
        # R1-A P1-1 立修：捕获取消认领前的 assignee（in_progress→open 写独立 unassigned event）
        previous_assignee_id = existing.assigned_to

        if old_status == "closed":
            raise IssueClosedError(issue_id=str(issue_id))

        if target_status not in _ALLOWED_TRANSITIONS.get(old_status, set()):
            raise IssueTransitionInvalidError(
                issue_id=str(issue_id),
                from_status=old_status,
                to_status=target_status,
            )

        fields: dict[str, Any] = {"status": target_status}

        # open → in_progress：assigned_to 必填
        if old_status == "open" and target_status == "in_progress":
            if assigned_to is None:
                raise IssueAssigneeRequiredError(issue_id=str(issue_id))
            fields["assigned_to"] = assigned_to
        # in_progress → open：取消认领
        elif old_status == "in_progress" and target_status == "open":
            fields["assigned_to"] = None
        # * → resolved：写 resolved_at
        if target_status == "resolved":
            fields["resolved_at"] = datetime.now(UTC)

        rows = await self.dao.update(db, issue_id, project_id, fields=fields)
        if rows == 0:
            raise IssueNotFoundError(issue_id=str(issue_id))
        await db.refresh(existing, attribute_names=list(fields.keys()) + ["updated_at"])

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="issue_status_changed",
            target_type="issue",
            target_id=str(issue_id),
            summary=f"Status: {old_status} → {target_status}",
            metadata={
                "node_id": str(existing.node_id) if existing.node_id else None,
                "category": existing.category,
                "from_status": old_status,
                "to_status": target_status,
                "assigned_to": (
                    str(fields.get("assigned_to"))
                    if fields.get("assigned_to") is not None
                    else None
                ),
                "note": note,
            },
        )
        # R1-A P1-1 立修：in_progress→open 取消认领必须额外写独立 `unassigned` event
        # （design §4 P5 audit F-3 + design §10 R10-1 6 事件清单字面要求）
        if old_status == "in_progress" and target_status == "open":
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="issue_unassigned",
                target_type="issue",
                target_id=str(issue_id),
                summary=f"Unassigned issue '{existing.title}'",
                metadata={
                    "previous_assignee_id": (
                        str(previous_assignee_id) if previous_assignee_id else None
                    ),
                    "reason": note,
                },
            )
        # Phase 2.2 子片 5 D 类 #3：refetch with joins for response（get_for_update 不带 joins）
        loaded = await self.dao.get_by_id(db, issue_id, project_id)
        assert loaded is not None
        return loaded

    async def delete(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        issue_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        existing = await self._get_or_raise(db, issue_id, project_id)
        title = existing.title
        category = existing.category
        node_id = existing.node_id
        final_status = existing.status

        rows = await self.dao.delete_by_id(db, issue_id, project_id)
        if rows == 0:
            raise IssueNotFoundError(issue_id=str(issue_id))
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="issue_deleted",
            target_type="issue",
            target_id=str(issue_id),
            summary=f"Deleted issue '{title}'",
            metadata={
                "node_id": str(node_id) if node_id else None,
                "category": category,
                "final_status": final_status,
            },
        )

    # ─── R-X2 第三真注入入口（M03 delete_node 调用）───

    async def orphan_by_node_id(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """R-X2 第三真注入（**orphan 语义**，与 M04/M06 delete 不同）。

        M03 delete_node 调用：将该 node 下所有 issues 的 node_id 设为 NULL（游离化），
        每条独立写 ``orphan`` activity_log（design §10 R10-1 batch3）。
        异常契约 (R1-C P1-01)：不 catch-all 吞错；DAO/write_event 异常向上传播。
        """
        records = await self.dao.list_by_node_for_orphan(db, node_id, project_id)
        # 先批量 UPDATE SET NULL（DAO 层一次 SQL）
        rows = await self.dao.orphan_by_node_id(db, node_id, project_id)
        if rows == 0:
            return
        # 为每条受影响 issue 写独立 orphan 事件
        for rec in records:
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="issue_orphaned",
                target_type="issue",
                target_id=str(rec.id),
                summary=f"Orphaned issue '{rec.title}' (cascade from node delete)",
                metadata={
                    "old_node_id": str(node_id),
                    "category": rec.category,
                    "reason": "cascade_from_node_delete",
                },
            )

    # ─── M18 baseline-patch ───

    async def get_for_embedding(
        self, db: AsyncSession, issue_id: UUID, project_id: UUID
    ) -> str | None:
        """M18 baseline-patch（A6 A 路径）：拼接 title + description。

        M07 无 url 字段（CY 决策 4 不影响）。

        R1-C P1-01 立修：description 空字符串 "" 在 ``if X:`` 下 falsy 会被静默跳过，
        但 design §3 description 是 ``nullable=False``（永远是 str），用 ``is not None``
        语义不准。直接拼接 title + description（"" 拼出 "title\\n"，与 M16 消费契约一致）。
        """
        i = await self.dao.get_by_id(db, issue_id, project_id)
        if i is None:
            return None
        return f"{i.title}\n{i.description}"
