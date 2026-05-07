"""M04 DimensionService — design/02-modules/M04-feature-archive/00-design.md §6.

事务边界：所有"产生副作用 + 写 activity_log"的方法用 ``async with db.begin():`` 包裹。
M11/M17 batch_create_in_transaction / M03 delete_by_node_id 接受外部 db session（R-X3），
不自开事务。

# Scaffold 简化决策（2026-05-07，子片 3 — A5 enqueue 推迟 / get_for_embedding A 现在建）
# ① 决策内容：M04 sprint 期 create / update / delete commit 后**不调** embedding_service.enqueue
#    / enqueue_delete；get_for_embedding 实装拼接 JSONB content 所有 string 字段
#    （unit test 仅覆盖默认拼接路径，生产路径 M18 sprint 期补）
# ② 简化理由：M18 own embedding_service 在 M04 sprint 期不存在（B caller）；
#    按 design §6.X A5 主标准 Q1 否 + Q2 caller → enqueue B 推迟；
#    get_for_embedding 是 M04 own 被动接口（A 现在建）
# ③ 由 M18 sprint 扩齐：DimensionService 三处 commit 后尾调
#    embedding_service.enqueue(target_type="dimension_record", target_id, project_id, user_id,
#    enqueued_by="incremental")；delete commit 后异步 enqueue_delete + SilentFailure +
#    embedding_failures EMBEDDING_DELETE_FAILED + cleanup cron 兜底
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M04 §6.X 实施期处理段 status

# Scaffold 简化决策（2026-05-07，子片 3 — M11/M17/M13 跨模块接口）
# ① 决策内容：design §6 列的 batch_create_in_transaction / create_dimension_record / get_latest
#    M04 sprint 期不实装；router 不暴露入口（M04 自身 create/update/delete 已覆盖 sprint 内
#    回归测试需求）
# ② 简化理由：M11 cold-start / M13 requirement-analysis / M17 ai-import 模块期不存在，
#    无 caller；M04 sprint 实装 = 死代码风险
# ③ 由 M11 / M13 / M17 各 sprint 启动时按需追加 service 方法 + 回归测试覆盖
# ④ 触发回写动作：各 sprint sprint review 阶段 add 调用 + 回写 M04 §6 status
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.dimension_dao import DimensionDAO
from api.errors.exceptions import (
    ConflictError,
    DimensionDuplicateError,
    DimensionNotFoundError,
    DimensionTypeNotFoundError,
)
from api.models.dimension_record import DimensionRecord
from api.models.project import DimensionType
from api.services.activity_log_service import write_event


class DimensionService:
    """M04 业务 service。

    职责（design §6）：
      - 维度记录 CRUD（含乐观锁 update）
      - 完善度计算（已填维度数）
      - delete_by_node_id（R-X2 注入：M03 delete_node 调用清下游）
      - get_for_embedding（M18 baseline-patch 被动接口；A5 A 路径）
    """

    def __init__(self, dao: DimensionDAO | None = None) -> None:
        self.dao = dao or DimensionDAO()

    # ─── 读 ───

    async def list_by_node(
        self, db: AsyncSession, *, project_id: UUID, node_id: UUID
    ) -> list[DimensionRecord]:
        return list(await self.dao.list_by_node(db, node_id, project_id))

    async def get_one_record(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        dimension_type_id: int,
    ) -> DimensionRecord:
        rec = await self.dao.get_one(db, node_id, project_id, dimension_type_id)
        if rec is None:
            raise DimensionNotFoundError(node_id=str(node_id), dimension_type_id=dimension_type_id)
        return rec

    async def completion(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        enabled_count: int,
    ) -> dict[str, Any]:
        """档案页完善度：filled / enabled。

        enabled_count 由 caller 从 project_dimension_configs 统计（横切 router/service
        负责装配；本方法只做 filled 数 + 比率）。
        """
        filled = await self.dao.count_by_node(db, node_id, project_id)
        rate = (filled / enabled_count) if enabled_count > 0 else 0.0
        return {
            "filled_count": filled,
            "enabled_count": enabled_count,
            "completion_rate": rate,
        }

    async def get_for_embedding(
        self, db: AsyncSession, record_id: UUID, project_id: UUID
    ) -> str | None:
        """M18 baseline-patch 被动接口（design §6.X A5 A 路径）。

        拼接 JSONB ``content`` 内所有 string 类型字段（运行期 isinstance 过滤；
        CY 决策 3：不引入白名单 schema 改动）。记录不存在 / 跨租户 → None。
        """
        rec = await self.dao.get_by_id(db, record_id, project_id)
        if rec is None:
            return None
        parts = [v for v in (rec.content or {}).values() if isinstance(v, str) and v]
        if not parts:
            return None
        return "\n".join(parts)

    # ─── 写 ───

    async def create(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        dimension_type_id: int,
        content: dict[str, Any],
        actor_user_id: UUID,
    ) -> DimensionRecord:
        """事务: 校验 type 存在 + tenant 一致性 + INSERT + activity_log。"""
        # type 存在校验
        dt = await db.get(DimensionType, dimension_type_id)
        if dt is None:
            raise DimensionTypeNotFoundError(dimension_type_id=dimension_type_id)

        # 唯一约束保护（DB UNIQUE 兜底，service 层友好提示）
        existing = await self.dao.get_one(db, node_id, project_id, dimension_type_id)
        if existing is not None:
            raise DimensionDuplicateError(node_id=str(node_id), dimension_type_id=dimension_type_id)

        rec = DimensionRecord(
            id=uuid4(),
            node_id=node_id,
            project_id=project_id,
            dimension_type_id=dimension_type_id,
            content=content or {},
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        await self.dao.insert(db, rec)
        await db.refresh(rec, attribute_names=["created_at", "updated_at"])

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="create",
            target_type="dimension_record",
            target_id=str(rec.id),
            summary=f"Created dimension '{dt.key}'",
            metadata={
                "node_id": str(node_id),
                "dimension_type_id": dimension_type_id,
                "dimension_type_key": dt.key,
                "content_size": len(str(content or {})),
            },
        )
        return rec

    async def update_with_lock(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        dimension_type_id: int,
        content: dict[str, Any],
        expected_version: int,
        actor_user_id: UUID,
    ) -> DimensionRecord:
        """事务: 乐观锁 UPDATE + activity_log。

        rows=0 → 区分"记录不存在"（404）vs"version 冲突"（409）。
        """
        existing = await self.dao.get_one(db, node_id, project_id, dimension_type_id)
        if existing is None:
            raise DimensionNotFoundError(node_id=str(node_id), dimension_type_id=dimension_type_id)
        old_version = existing.version

        rows = await self.dao.update_with_version(
            db,
            existing.id,
            project_id,
            expected_version=expected_version,
            content=content or {},
            updated_by=actor_user_id,
        )
        if rows == 0:
            # 记录存在但 version 不匹配 → 乐观锁冲突
            raise ConflictError("Dimension record was modified by another user; please refresh")

        await db.refresh(existing, attribute_names=["version", "content", "updated_at"])

        # type 名（写 summary 用，不阻断主流程）
        dt = await db.get(DimensionType, dimension_type_id)
        type_key = dt.key if dt else f"type#{dimension_type_id}"

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="update",
            target_type="dimension_record",
            target_id=str(existing.id),
            summary=f"Updated dimension '{type_key}'",
            metadata={
                "node_id": str(node_id),
                "dimension_type_id": dimension_type_id,
                "old_version": old_version,
                "new_version": existing.version,
            },
        )
        return existing

    async def delete(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        dimension_type_id: int,
        actor_user_id: UUID,
    ) -> None:
        """事务: DELETE + activity_log。

        记录不存在 → 404（router 转 204 是 caller 决策——本层抛真错）。
        """
        existing = await self.dao.get_one(db, node_id, project_id, dimension_type_id)
        if existing is None:
            raise DimensionNotFoundError(node_id=str(node_id), dimension_type_id=dimension_type_id)
        rec_id = existing.id

        rows = await self.dao.delete_one(db, rec_id, project_id)
        if rows == 0:
            # 极少见竞态：get_one 后被并发删；视为不存在
            raise DimensionNotFoundError(node_id=str(node_id), dimension_type_id=dimension_type_id)

        dt = await db.get(DimensionType, dimension_type_id)
        type_key = dt.key if dt else f"type#{dimension_type_id}"

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="delete",
            target_type="dimension_record",
            target_id=str(rec_id),
            summary=f"Deleted dimension '{type_key}'",
            metadata={
                "node_id": str(node_id),
                "dimension_type_id": dimension_type_id,
            },
        )

    async def delete_by_node_id(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """R-X2 注入入口（NodeChildrenServiceProtocol 实现）。

        M03 delete_node 调用：清空指定 node 下所有 dimension_records，每条独立写
        ``delete`` activity_log（design §10 R10-1 batch3）。

        异常契约 (R1-C P1-01)：不 catch-all 吞错；DAO/write_event 任一异常向上传播。
        """
        records = await self.dao.list_by_node_for_delete(db, node_id, project_id)
        for rec in records:
            rows = await self.dao.delete_one(db, rec.id, project_id)
            if rows == 0:
                # 并发删除导致 list 后被他方清掉——继续下一条，不抛
                continue
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="delete",
                target_type="dimension_record",
                target_id=str(rec.id),
                summary="Deleted dimension (cascade from node delete)",
                metadata={
                    "node_id": str(node_id),
                    "dimension_type_id": rec.dimension_type_id,
                    "cascade_source": "node_delete",
                },
            )
