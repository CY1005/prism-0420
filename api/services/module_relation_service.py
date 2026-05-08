"""M08 ModuleRelationService — design/02-modules/M08-module-relation/00-design.md §6.

事务边界（M02-M07 范式延续）：Router 管 commit / autobegin / 异常自动回滚。

R-X2 **第四真注入方**（与 M04/M06 同 delete 语义，与 M07 orphan 对照；双向 OR）：
  - delete_by_node_id(db, node_id, project_id, actor_user_id) → DELETE WHERE
    source=node OR target=node + 每条独立 delete activity_log
  - 异常契约 (R1-C P1-01)：不 catch-all 静默吞错

# Scaffold 简化决策（2026-05-08，A6 闸门 2.5 — M11/M17 batch_create_in_transaction）
# ① 决策内容：design §6 列的 batch_create_in_transaction M08 sprint 期不实装
# ② 简化理由：M11/M17 caller 不存在（与 M04/M06/M07 同款 punt）
# ③ 由 M11 / M17 各 sprint 启动时按需追加
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.module_relation_dao import ModuleRelationDAO
from api.dao.node_dao import NodeDAO
from api.errors.exceptions import (
    RelationDuplicateError,
    RelationNodeNotInProjectError,
    RelationNotFoundError,
    RelationSelfLoopError,
)
from api.models.module_relation import ModuleRelation
from api.services.activity_log_service import write_event


class ModuleRelationService:
    def __init__(
        self,
        dao: ModuleRelationDAO | None = None,
        node_dao: NodeDAO | None = None,
    ) -> None:
        self.dao = dao or ModuleRelationDAO()
        self.node_dao = node_dao or NodeDAO()

    # ─── 内部校验 ───

    async def _check_nodes_belong_to_project(
        self,
        db: AsyncSession,
        source_node_id: UUID,
        target_node_id: UUID,
        project_id: UUID,
    ) -> None:
        """校验 source/target 都属于该 project（design §8 第三层防御）。

        R1-C P1-02 立修（2026-05-08）：两次 node 校验独立无依赖，
        用 ``asyncio.gather`` 并行执行 → 节省 1 次 DB RTT（每次 create 必走路径）。
        """
        import asyncio

        s, t = await asyncio.gather(
            self.node_dao.get_by_id(db, source_node_id, project_id),
            self.node_dao.get_by_id(db, target_node_id, project_id),
        )
        if s is None or t is None:
            raise RelationNodeNotInProjectError(
                source_node_id=str(source_node_id),
                target_node_id=str(target_node_id),
                project_id=str(project_id),
            )

    async def _get_or_raise(
        self, db: AsyncSession, relation_id: UUID, project_id: UUID
    ) -> ModuleRelation:
        r = await self.dao.get_by_id(db, relation_id, project_id)
        if r is None:
            raise RelationNotFoundError(relation_id=str(relation_id))
        return r

    # ─── 读 ───

    async def list_by_project(
        self, db: AsyncSession, *, project_id: UUID, limit: int | None = None
    ) -> Sequence[ModuleRelation]:
        return await self.dao.list_by_project(db, project_id, limit=limit)

    async def list_by_node(
        self, db: AsyncSession, *, project_id: UUID, node_id: UUID
    ) -> Sequence[ModuleRelation]:
        return await self.dao.list_by_node(db, node_id, project_id)

    async def get_by_id(
        self, db: AsyncSession, *, project_id: UUID, relation_id: UUID
    ) -> ModuleRelation:
        return await self._get_or_raise(db, relation_id, project_id)

    async def search_by_keyword(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        query: str,
        limit: int = 50,
    ) -> Sequence[ModuleRelation]:
        """M09 pilot pass-through。"""
        return await self.dao.search_by_keyword(db, query, project_id, limit=limit)

    # ─── 写 ───

    async def create_relation(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        source_node_id: UUID,
        target_node_id: UUID,
        relation_type: str,
        actor_user_id: UUID,
        notes: str | None = None,
    ) -> ModuleRelation:
        """事务: 节点归属校验 + INSERT + activity_log。

        race 处理（M05 P1-01 立规延续 / design §13 IntegrityError handler）：
          - uq_module_relation_src_tgt_type → RelationDuplicateError (409)
          - 其他 IntegrityError 透传
        """
        if source_node_id == target_node_id:
            raise RelationSelfLoopError(node_id=str(source_node_id))

        await self._check_nodes_belong_to_project(db, source_node_id, target_node_id, project_id)

        r = ModuleRelation(
            id=uuid4(),
            project_id=project_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation_type=relation_type,
            notes=notes,
            created_by=actor_user_id,
        )
        try:
            await self.dao.create(db, r)
        except IntegrityError as e:
            err_text = str(e.orig) if e.orig else str(e)
            if "uq_module_relation_src_tgt_type" in err_text:
                raise RelationDuplicateError(
                    source_node_id=str(source_node_id),
                    target_node_id=str(target_node_id),
                    relation_type=relation_type,
                ) from e
            raise

        await db.refresh(r, attribute_names=["created_at", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="create",
            target_type="module_relation",
            target_id=str(r.id),
            summary=f"Created relation: {source_node_id} → {target_node_id} [{relation_type}]",
            metadata={
                "source_node_id": str(source_node_id),
                "target_node_id": str(target_node_id),
                "relation_type": relation_type,
            },
        )
        return r

    async def update_notes(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        relation_id: UUID,
        notes: str | None,
        actor_user_id: UUID,
    ) -> ModuleRelation:
        existing = await self._get_or_raise(db, relation_id, project_id)
        old_notes_len = len(existing.notes or "")
        new_notes_len = len(notes or "")

        rows = await self.dao.update_notes(db, relation_id, project_id, notes=notes)
        if rows == 0:
            raise RelationNotFoundError(relation_id=str(relation_id))

        await db.refresh(existing, attribute_names=["notes", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="update",
            target_type="module_relation",
            target_id=str(relation_id),
            summary=f"Updated relation notes: {existing.source_node_id} → {existing.target_node_id}",
            metadata={
                "relation_type": existing.relation_type,
                "old_notes_length": old_notes_len,
                "new_notes_length": new_notes_len,
            },
        )
        return existing

    async def delete_relation(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        relation_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        existing = await self._get_or_raise(db, relation_id, project_id)
        meta: dict[str, Any] = {
            "source_node_id": str(existing.source_node_id),
            "target_node_id": str(existing.target_node_id),
            "relation_type": existing.relation_type,
        }
        rows = await self.dao.delete_by_id(db, relation_id, project_id)
        if rows == 0:
            raise RelationNotFoundError(relation_id=str(relation_id))
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="delete",
            target_type="module_relation",
            target_id=str(relation_id),
            summary=f"Deleted relation: {meta['source_node_id']} → {meta['target_node_id']}",
            metadata=meta,
        )

    # ─── R-X2 第四真注入入口（M03 delete_node 调用）───

    async def delete_by_node_id(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """R-X2 第四真注入（双向 + delete 语义）。

        与 M04/M06 同款 delete（DELETE FROM）；与 M07 orphan（UPDATE SET NULL）不同。
        双向：source=node OR target=node 全部删除 + 每条独立 delete activity_log。
        """
        records = await self.dao.list_by_node_for_delete(db, node_id, project_id)
        rows = await self.dao.delete_by_node_id(db, node_id, project_id)
        if rows == 0:
            return
        for rec in records:
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="delete",
                target_type="module_relation",
                target_id=str(rec.id),
                summary=f"Deleted relation (cascade from node delete): {rec.source_node_id} → {rec.target_node_id}",
                metadata={
                    "source_node_id": str(rec.source_node_id),
                    "target_node_id": str(rec.target_node_id),
                    "relation_type": rec.relation_type,
                    "triggered_by": "node_deletion",
                },
            )
