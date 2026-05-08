"""M05 VersionService — design/02-modules/M05-version-timeline/00-design.md §6.

事务边界（R1-A P1 + R1-C P1-01 立修，2026-05-08）：
  - **Router 层管 commit**（与 M02-M04 一致范式）；本 service 接受外部 AsyncSession，
    不调 ``async with db.begin():`` / 不主动 commit / 不主动 rollback。
  - SQLAlchemy autobegin：第一次 add/execute 自动启动 implicit transaction，
    Router 在 endpoint 末尾 ``await db.commit()`` 是唯一 commit 点；中途异常由
    FastAPI 框架捕获不调 commit → autobegin transaction 自动回滚（含 set_current
    路径的 clear_current_flag + INSERT + write_event 三段，原子性由 implicit
    transaction 兜底）。
  - design §3 / §9 sample 中的 ``with db.begin():`` 是设计期写法，sprint 关闸
    audit 时统一回写为本 docstring 范式（M02-M05 同款 docstring 漂移）。

权限：三层防御
  - Server Action / Router check_project_access（外层）
  - Service _check_node_belongs_to_project（本层；防 cross-tenant node_id 攻击）

snapshot_data 边界（B3 闸门 2.5 C 栏决策 / design §1 Out of scope）：
  M05 不做 AI 解析；接受任意 dict[str, Any]；ErrorCode VERSION_SNAPSHOT_INVALID 保留扩展点
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.node_dao import NodeDAO
from api.dao.version_dao import VersionDAO
from api.errors.exceptions import (
    ConflictError,
    VersionLabelDuplicateError,
    VersionNotFoundError,
)
from api.models.version_record import VersionRecord
from api.services.activity_log_service import write_event


class VersionService:
    """M05 版本时间线 service。

    职责（design §6）：
      - 版本 CRUD（create / get / list / update_metadata / delete）
      - set_current 互斥切换（事务原子 + DB 部分唯一索引兜底）
      - count_by_node（M16 pilot 基线补丁对外契约）
    """

    def __init__(
        self,
        dao: VersionDAO | None = None,
        node_dao: NodeDAO | None = None,
    ) -> None:
        self.dao = dao or VersionDAO()
        self.node_dao = node_dao or NodeDAO()

    # ─── 内部校验 ───

    async def _check_node_belongs_to_project(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> None:
        """三层防御第三层：防 cross-tenant node_id 攻击。

        node 不属于该 project → 抛 VersionNotFoundError 不暴露 forbidden（与 M04 同款）。
        """
        node = await self.node_dao.get_by_id(db, node_id, project_id)
        if node is None:
            raise VersionNotFoundError(node_id=str(node_id), reason="node_not_in_project")

    # ─── 读 ───

    async def list_by_node(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        limit: int | None = None,
    ) -> Sequence[VersionRecord]:
        """节点版本时间线（按 created_at DESC）。R-X3 对外契约可被跨模块调用。

        本方法**不开事务**（纯读 + ADR-003 规则 2 豁免不写 activity_log）。
        """
        await self._check_node_belongs_to_project(db, node_id, project_id)
        return await self.dao.list_by_node(db, node_id, project_id, limit=limit)

    async def count_by_node(self, db: AsyncSession, *, project_id: UUID, node_id: UUID) -> int:
        """节点版本数（M16 pilot 基线补丁；纯读）。

        R1-C P1-02 立修：cross-tenant node_id 静默返 0 是安全盲区，加 node 归属校验
        与 list_by_node 行为一致；M16 R-X3 caller 拿到 NotFoundError 而非 0 误判。
        """
        await self._check_node_belongs_to_project(db, node_id, project_id)
        return await self.dao.count_by_node(db, node_id, project_id)

    async def get_by_id(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        version_id: UUID,
    ) -> VersionRecord:
        """单条版本详情。不存在 → VersionNotFoundError。"""
        await self._check_node_belongs_to_project(db, node_id, project_id)
        rec = await self.dao.get_by_id(db, version_id, project_id)
        if rec is None or rec.node_id != node_id:
            raise VersionNotFoundError(version_id=str(version_id))
        return rec

    # ─── 写 ───

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        version_label: str,
        summary: str,
        details: str | None = None,
        change_type: str = "added",
        release_mode: str = "release",
        is_current: bool = False,
        snapshot_data: dict[str, Any] | None = None,
        actor_user_id: UUID,
    ) -> VersionRecord:
        """事务: 校验 + INSERT + 可选 set_current（互斥）+ activity_log。

        race 处理（A9 + B5 闸门 2.5 实证）：
          - UNIQUE(node_id, version_label) 冲突 → IntegrityError → VersionLabelDuplicateError
          - 部分唯一索引 uq_version_node_is_current 冲突（is_current=true 同 node 已存在）
            → 由 caller 走 set_current 路径而非 create with is_current=True；本方法
            如收到 is_current=True 在事务内先 clear_current_flag 再 INSERT
        """
        await self._check_node_belongs_to_project(db, node_id, project_id)

        rec = VersionRecord(
            id=uuid4(),
            node_id=node_id,
            project_id=project_id,
            version_label=version_label,
            summary=summary,
            details=details,
            change_type=change_type,
            release_mode=release_mode,
            is_current=is_current,
            snapshot_data=snapshot_data,
            created_by=actor_user_id,
        )
        # is_current=True 时先清旧 current（同事务原子）
        if is_current:
            await self.dao.clear_current_flag(db, node_id, project_id)
        try:
            await self.dao.create(db, rec)
        except IntegrityError as e:
            # R1-C P1-01 立修：区分约束名，避免错误码语义误导 caller。
            # uq_version_node_label: (node_id, version_label) 重复 → VersionLabelDuplicateError
            # uq_version_node_is_current: 部分唯一索引（is_current=true 同 node 已存在）
            #   并发场景下 clear_current_flag 后另一连接重新 set_current → IntegrityError
            #   → ConflictError（"另一并发请求已设当前版本，请刷新后重试"）
            err_text = str(e.orig) if e.orig else str(e)
            if "uq_version_node_is_current" in err_text:
                raise ConflictError(
                    "Another version was concurrently set as current; please refresh"
                ) from e
            # 默认归到 label 重复（含 uq_version_node_label 命中 + 未知 IntegrityError 兜底）
            raise VersionLabelDuplicateError(
                node_id=str(node_id),
                version_label=version_label,
            ) from e

        await db.refresh(rec, attribute_names=["created_at", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="version_record_created",
            target_type="version_record",
            target_id=str(rec.id),
            summary=f"Created version '{version_label}'",
            metadata={
                "node_id": str(node_id),
                "version_label": version_label,
                "change_type": change_type,
                "is_current": is_current,
            },
        )
        return rec

    async def update_metadata(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        version_id: UUID,
        actor_user_id: UUID,
        summary: str | None = None,
        details: str | None = None,
        change_type: str | None = None,
        release_mode: str | None = None,
    ) -> VersionRecord:
        """事务：UPDATE 元数据 + activity_log。

        snapshot_data 不接受 PUT 更新（design Q3，schema 层已拦）；
        is_current 切换走专用 set_current 路径。
        """
        existing = await self.get_by_id(
            db, project_id=project_id, node_id=node_id, version_id=version_id
        )

        fields: dict[str, Any] = {}
        if summary is not None:
            fields["summary"] = summary
        if details is not None:
            fields["details"] = details
        if change_type is not None:
            fields["change_type"] = change_type
        if release_mode is not None:
            fields["release_mode"] = release_mode

        if not fields:
            # No-op update：直接返回现有；不写 activity_log
            return existing

        rows = await self.dao.update_metadata(db, version_id, project_id, fields=fields)
        if rows == 0:
            # get_by_id 后被并发删
            raise VersionNotFoundError(version_id=str(version_id))

        await db.refresh(existing, attribute_names=list(fields.keys()) + ["updated_at"])

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="version_record_updated",
            target_type="version_record",
            target_id=str(version_id),
            summary=f"Updated version '{existing.version_label}'",
            metadata={
                "node_id": str(node_id),
                "version_label": existing.version_label,
                "changed_fields": list(fields.keys()),
            },
        )
        return existing

    async def delete(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """事务：DELETE + activity_log。不存在 → 404。"""
        existing = await self.get_by_id(
            db, project_id=project_id, node_id=node_id, version_id=version_id
        )
        was_current = existing.is_current
        version_label = existing.version_label

        rows = await self.dao.delete_by_id(db, version_id, project_id)
        if rows == 0:
            # 极少见竞态：get_by_id 后被并发删
            raise VersionNotFoundError(version_id=str(version_id))

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="version_record_deleted",
            target_type="version_record",
            target_id=str(version_id),
            summary=f"Deleted version '{version_label}'",
            metadata={
                "node_id": str(node_id),
                "version_label": version_label,
                "was_current": was_current,
            },
        )

    async def set_current(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        version_id: UUID,
        actor_user_id: UUID,
    ) -> VersionRecord:
        """事务原子：清旧 current + 标记新 current + activity_log。

        DB 部分唯一索引 uq_version_node_is_current 在事务边界兜底"同 node 至多 1 当前"。
        前置校验确保 version 属于该 node + project（防 cross-tenant 攻击）。
        """
        existing = await self.get_by_id(
            db, project_id=project_id, node_id=node_id, version_id=version_id
        )
        previous_current = await self.dao.get_current(db, node_id, project_id)
        previous_current_id = previous_current.id if previous_current else None

        # 同事务内：先清旧 current → 再标新 current
        await self.dao.clear_current_flag(db, node_id, project_id)
        rows = await self.dao.set_current_flag(db, version_id, project_id)
        if rows == 0:
            raise VersionNotFoundError(version_id=str(version_id))

        await db.refresh(existing, attribute_names=["is_current", "updated_at"])

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="version_record_set_current",
            target_type="version_record",
            target_id=str(version_id),
            summary=f"Marked version '{existing.version_label}' as current",
            metadata={
                "node_id": str(node_id),
                "version_label": existing.version_label,
                "previous_current_id": (str(previous_current_id) if previous_current_id else None),
            },
        )
        return existing
