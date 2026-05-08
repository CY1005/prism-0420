"""M12 ComparisonService — design/02-modules/M12-comparison/00-design.md §6.

业务能力：
  - get_matrix_data：实时矩阵渲染（跨模块只读 R-X3：调 M04 batch_get_by_nodes + node existence 验证）
  - create_snapshot：G4=B 值快照（多表事务 INSERT snapshots + bulk INSERT items + activity_log）
  - list_snapshots / get_snapshot_detail：快照查询
  - rename_snapshot：乐观锁 + activity_log
  - delete_snapshot：CASCADE 自动清 items + activity_log

事务边界（M02-M11 共享范式）：Router 管 commit；service 接受外部 AsyncSession，
不调 ``async with db.begin():``；异常由 FastAPI 捕获不调 commit → implicit transaction
自动回滚保证多表原子性。

R-X3 跨模块只读：
  - DimensionService.batch_get_by_nodes（M04 sprint scaffold "caller sprint 实装"到期）
  - NodeDAO.get_by_id 单 node 校验（M07 IssueService 范式延续）

权限三层防御（design §8）：
  Server Action / Router check_project_access(role) 已防外层；
  Service 层 _get_or_raise(snapshot_id, project_id) 防 snapshot_id 跨项目越权（不暴露 forbidden）。
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.comparison_dao import ComparisonDAO
from api.dao.node_dao import NodeDAO
from api.errors.exceptions import (
    ComparisonEmptySelectionError,
    ComparisonNodeNotFoundError,
    ComparisonSnapshotConflictError,
    ComparisonSnapshotNameEmptyError,
    ComparisonSnapshotNotFoundError,
)
from api.models.comparison_snapshot import ComparisonSnapshot, ComparisonSnapshotItem
from api.models.dimension_record import DimensionRecord
from api.services.activity_log_service import write_event
from api.services.dimension_service import DimensionService

# action_type 映射（design §10；与 frontmatter produces_action_types 一致 underscore 形态）
ACTION_SNAPSHOT_CREATED = "comparison_snapshot_created"
ACTION_SNAPSHOT_RENAMED = "comparison_snapshot_renamed"
ACTION_SNAPSHOT_DELETED = "comparison_snapshot_deleted"
TARGET_SNAPSHOT = "comparison_snapshot"


class ComparisonService:
    """M12 功能对比矩阵 service。"""

    def __init__(
        self,
        dao: ComparisonDAO | None = None,
        node_dao: NodeDAO | None = None,
        dimension_service: DimensionService | None = None,
    ) -> None:
        self.dao = dao or ComparisonDAO()
        self.node_dao = node_dao or NodeDAO()
        self.dimension_service = dimension_service or DimensionService()

    # ─────────────── 内部校验 ───────────────

    async def _validate_nodes_in_project(
        self, db: AsyncSession, node_ids: list[UUID], project_id: UUID
    ) -> None:
        """所有 node_id 必须属于该 project。任一不命中 → ComparisonNodeNotFoundError(422)。

        M07 IssueService._check_node_in_project 范式延续；批量版用 NodeDAO.list_by_ids
        一次 IN 查（design §9 双重 tenant 过滤）。
        """
        if not node_ids:
            return
        # 去重防多算
        unique_ids = list({nid for nid in node_ids})
        rows = await self.node_dao.list_by_ids(db, unique_ids, project_id)
        if len(rows) != len(unique_ids):
            found = {n.id for n in rows}
            missing = [nid for nid in unique_ids if nid not in found]
            raise ComparisonNodeNotFoundError(
                project_id=str(project_id),
                missing_node_ids=[str(nid) for nid in missing],
            )

    async def _get_or_raise(
        self, db: AsyncSession, snapshot_id: UUID, project_id: UUID
    ) -> ComparisonSnapshot:
        snap = await self.dao.get_snapshot(db, snapshot_id, project_id)
        if snap is None:
            raise ComparisonSnapshotNotFoundError(snapshot_id=str(snapshot_id))
        return snap

    @staticmethod
    def _validate_name(name: str) -> str:
        stripped = (name or "").strip()
        if not stripped:
            raise ComparisonSnapshotNameEmptyError()
        return stripped

    @staticmethod
    def _validate_selection(node_ids: list[UUID], dimension_type_ids: list[int]) -> None:
        if not node_ids or not dimension_type_ids:
            raise ComparisonEmptySelectionError()

    # ─────────────── 读 ───────────────

    async def get_matrix_data(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_ids: list[UUID],
        dimension_type_ids: list[int],
    ) -> list[DimensionRecord]:
        """实时矩阵渲染：跨模块只读 R-X3（调 M04 service 接口）。

        - 验空选择 → ComparisonEmptySelectionError(422)
        - 验 node 属于 project → ComparisonNodeNotFoundError(422)
        - 调 DimensionService.batch_get_by_nodes 拿 records（M04 双重 tenant 过滤兜底）
        - 不写 activity_log（design §10 仅 C/U/D 事件 + ADR-003 规则 1 精神）
        """
        self._validate_selection(node_ids, dimension_type_ids)
        await self._validate_nodes_in_project(db, node_ids, project_id)
        return list(
            await self.dimension_service.batch_get_by_nodes(
                db,
                project_id=project_id,
                node_ids=node_ids,
                dimension_type_ids=dimension_type_ids,
            )
        )

    async def list_snapshots(
        self, db: AsyncSession, *, project_id: UUID, limit: int = 50
    ) -> tuple[list[ComparisonSnapshot], int]:
        """SnapshotListResponse 数据：(items, total)。"""
        rows = await self.dao.list_snapshots(db, project_id, limit=limit)
        total = await self.dao.count_snapshots(db, project_id)
        return list(rows), total

    async def get_snapshot_detail(
        self, db: AsyncSession, *, project_id: UUID, snapshot_id: UUID
    ) -> ComparisonSnapshot:
        """SnapshotDetailResponse：eager load items（G4=B 值快照不降级；node 删后仍展示原值）。"""
        snap = await self.dao.get_snapshot_with_items(db, snapshot_id, project_id)
        if snap is None:
            raise ComparisonSnapshotNotFoundError(snapshot_id=str(snapshot_id))
        return snap

    # ─────────────── 写 ───────────────

    async def create_snapshot(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        name: str,
        description: str | None,
        node_ids: list[UUID],
        dimension_type_ids: list[int],
    ) -> ComparisonSnapshot:
        """G4=B 值快照创建（多表事务）。

        流程：
          1. validate name + selection + nodes-in-project
          2. INSERT comparison_snapshots（含 nodes_ref / dimensions_ref 元数据）
          3. 调 DimensionService.batch_get_by_nodes 拿当前 content
          4. bulk INSERT comparison_snapshot_items（G4=B 值副本）
          5. write_event activity_log（snapshot_created）

        事务由 router 控管 commit；任一步骤抛异常 → implicit rollback 全量回滚（design §5）。
        """
        clean_name = self._validate_name(name)
        self._validate_selection(node_ids, dimension_type_ids)
        await self._validate_nodes_in_project(db, node_ids, project_id)

        snap = ComparisonSnapshot(
            id=uuid4(),
            project_id=project_id,
            user_id=actor_user_id,
            name=clean_name,
            description=description,
            nodes_ref=[str(nid) for nid in node_ids],
            dimensions_ref=list(dimension_type_ids),
            version=1,
        )
        await self.dao.insert_snapshot(db, snap)

        records = await self.dimension_service.batch_get_by_nodes(
            db,
            project_id=project_id,
            node_ids=node_ids,
            dimension_type_ids=dimension_type_ids,
        )
        items = [
            ComparisonSnapshotItem(
                id=uuid4(),
                snapshot_id=snap.id,
                node_id=rec.node_id,
                dimension_type_id=rec.dimension_type_id,
                content=rec.content,
                snapshot_version=snap.version,
            )
            for rec in records
        ]
        await self.dao.bulk_insert_items(db, items)

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type=ACTION_SNAPSHOT_CREATED,
            target_type=TARGET_SNAPSHOT,
            target_id=str(snap.id),
            summary=f"创建对比矩阵快照：{clean_name}",
            metadata={
                "node_ids_count": len(node_ids),
                "dimension_type_ids_count": len(dimension_type_ids),
                "nodes_ref": [str(nid) for nid in node_ids],
                "dimensions_ref": list(dimension_type_ids),
                "items_count": len(items),
            },
        )
        return snap

    async def rename_snapshot(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        snapshot_id: UUID,
        actor_user_id: UUID,
        name: str,
        description: str | None,
        expected_version: int,
    ) -> ComparisonSnapshot:
        """乐观锁 rename（design §5 / §13 COMPARISON_SNAPSHOT_CONFLICT）。

        - 先 _get_or_raise 验存在 + tenant（不存在/跨租户 → 404）
        - 再 update_with_version：rows=0 → ComparisonSnapshotConflictError(409)
        - 成功后 write_event(rename) + 返回新 snapshot 状态
        """
        clean_name = self._validate_name(name)
        snap = await self._get_or_raise(db, snapshot_id, project_id)
        old_name = snap.name
        old_version = snap.version

        rows = await self.dao.update_snapshot_with_version(
            db,
            snapshot_id,
            project_id,
            expected_version=expected_version,
            name=clean_name,
            description=description,
        )
        if rows == 0:
            raise ComparisonSnapshotConflictError(
                snapshot_id=str(snapshot_id),
                expected_version=expected_version,
                actual_version=snap.version,
            )

        await db.refresh(snap)
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type=ACTION_SNAPSHOT_RENAMED,
            target_type=TARGET_SNAPSHOT,
            target_id=str(snapshot_id),
            summary=f"重命名快照：{old_name} → {clean_name}",
            metadata={
                "old_name": old_name,
                "new_name": clean_name,
                "old_version": old_version,
                "new_version": snap.version,
            },
        )
        return snap

    async def delete_snapshot(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        snapshot_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """删除快照（CASCADE 自动清 items）+ activity_log。

        - 先 _get_or_raise 验存在 + tenant（不存在/跨租户 → 404）
        - delete_snapshot DAO 返回 1（已 _get_or_raise 保证存在）
        - write_event(delete) 含 metadata.name + nodes_ref count
        """
        snap = await self._get_or_raise(db, snapshot_id, project_id)
        rows = await self.dao.delete_snapshot(db, snapshot_id, project_id)
        if rows == 0:
            # 理论上不可达（_get_or_raise 已保证存在）；同 M07 范式留此防御
            raise ComparisonSnapshotNotFoundError(snapshot_id=str(snapshot_id))

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type=ACTION_SNAPSHOT_DELETED,
            target_type=TARGET_SNAPSHOT,
            target_id=str(snapshot_id),
            summary=f"删除快照：{snap.name}",
            metadata={
                "name": snap.name,
                "node_ids_count": len(snap.nodes_ref or []),
            },
        )


def get_comparison_service() -> ComparisonService:
    """FastAPI dependency hook（router 层 Depends 使用）。"""
    return ComparisonService()
