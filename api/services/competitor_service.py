"""M06 CompetitorService — design/02-modules/M06-competitor/00-design.md §6.

事务边界（M02-M05 范式延续）：
  - **Router 层管 commit**；本 service 接受外部 AsyncSession，不调
    ``async with db.begin():`` / 不主动 commit / 不主动 rollback。
  - SQLAlchemy autobegin + Router endpoint 末 ``await db.commit()``；异常自动回滚。
  - **多表事务（competitors + competitor_refs 同事务，design Q4）**：档案页内联
    新建竞品+对标场景（B 入口）由 caller 一次性传入两个 create 调用，autobegin
    + Router commit 保证原子性。
  - R-X3 跨模块入口 ``delete_by_node_id``（M03 delete_node R-X2 注入）：接受外部
    db session，由 caller orchestrator 控制事务。

权限三层（design §8）：
  - Server Action / Router check_project_access（外层）
  - Service _check_competitor_belongs_to_project / _check_node_belongs_to_project（本层）

R-X2 第二真注入方（M04 第一已立 / Protocol 4 参签名稳定 / 2026-05-08）：
  - delete_by_node_id(db, node_id, project_id, actor_user_id) → 清节点下所有 refs
    + 每条独立 delete activity_log（design §10 R10-1 batch3）
  - 异常契约 (R1-C P1-01)：不 catch-all 静默吞错，DAO/write_event 异常向上传播

# Scaffold 简化决策（2026-05-08，A6 闸门 2.5 — M18 baseline-patch get_for_embedding A 路径）
# ① 决策内容：M06 sprint 期 create / update / delete commit 后**不调** embedding_service.enqueue
#    / enqueue_delete；get_for_embedding 实装拼接 name + description（CY 决策 4：url 不参与）
# ② 简化理由：M18 own embedding_service 在 M06 sprint 期不存在（B caller）；
#    按 design §6.X A6 主标准 Q1 否 + Q2 caller → enqueue B 推迟；
#    get_for_embedding 是 M06 own 被动接口（A 现在建）
# ③ 由 M18 sprint 扩齐：CompetitorService 三处 commit 后尾调 enqueue + 回归测试
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M06 §6.X 实施期处理段 status

# Scaffold 简化决策（2026-05-08 — M11/M17 跨模块 batch_create_in_transaction）
# ① 决策内容：design §6 列的 batch_create_in_transaction M06 sprint 期不实装；
#    router 不暴露入口（M06 自身 create/update/delete 已覆盖回归测试需求）
# ② 简化理由：M11 cold-start / M17 ai-import 模块期不存在，无 caller；
#    M06 sprint 实装 = 死代码风险（与 M04 同款 punt 范式）
# ③ 由 M11 / M17 各 sprint 启动时按需追加 service 方法 + 回归测试覆盖
# ④ 触发回写动作：各 sprint sprint review 阶段 add 调用 + 回写 M06 §6 status
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.competitor_dao import CompetitorDAO
from api.dao.node_dao import NodeDAO
from api.errors.exceptions import (
    CompetitorCrossProjectError,
    CompetitorNotFoundError,
    CompetitorRefDuplicateError,
    CompetitorRefNotFoundError,
)
from api.models.competitor import Competitor, CompetitorRef
from api.services.activity_log_service import write_event


class CompetitorService:
    """M06 业务 service。"""

    def __init__(
        self,
        dao: CompetitorDAO | None = None,
        node_dao: NodeDAO | None = None,
    ) -> None:
        self.dao = dao or CompetitorDAO()
        self.node_dao = node_dao or NodeDAO()

    # ─── 内部校验 ───

    async def _check_node_belongs_to_project(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> None:
        node = await self.node_dao.get_by_id(db, node_id, project_id)
        if node is None:
            raise CompetitorRefNotFoundError(node_id=str(node_id), reason="node_not_in_project")

    async def _get_competitor_or_raise(
        self, db: AsyncSession, competitor_id: UUID, project_id: UUID
    ) -> Competitor:
        c = await self.dao.get_competitor_by_id(db, competitor_id, project_id)
        if c is None:
            raise CompetitorNotFoundError(competitor_id=str(competitor_id))
        return c

    # ─── Competitor 全局 CRUD ───

    async def list_competitors(self, db: AsyncSession, *, project_id: UUID) -> Sequence[Competitor]:
        return await self.dao.list_by_project(db, project_id)

    async def get_competitor(
        self, db: AsyncSession, *, project_id: UUID, competitor_id: UUID
    ) -> Competitor:
        return await self._get_competitor_or_raise(db, competitor_id, project_id)

    async def batch_create_in_transaction(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        competitors_data: list[dict[str, Any]],
    ) -> list[Competitor]:
        """M11/M17 调用入口（R-X3 共享外部 session，R-X1 orchestrator 模式）。

        competitors_data 每条形如 {display_name, website_url?, description?}。
        每条独立写 create activity_log（R10-1 batch3）；任一失败由 caller 事务回滚。
        M11 sprint 接通（M06 sprint scaffold "M11 sprint 期不实装" 到期，2026-05-08）。
        """
        created: list[Competitor] = []
        for raw in competitors_data:
            c = await self.create_competitor(
                db,
                project_id=project_id,
                display_name=raw["display_name"],
                website_url=raw.get("website_url"),
                description=raw.get("description"),
                actor_user_id=actor_user_id,
            )
            created.append(c)
        return created

    async def create_competitor(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        display_name: str,
        website_url: str | None = None,
        description: str | None = None,
        actor_user_id: UUID,
    ) -> Competitor:
        c = Competitor(
            id=uuid4(),
            project_id=project_id,
            display_name=display_name,
            website_url=website_url,
            description=description,
            created_by=actor_user_id,
        )
        await self.dao.create_competitor(db, c)
        await db.refresh(c, attribute_names=["created_at", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_created",
            target_type="competitor",
            target_id=str(c.id),
            summary=f"Created competitor '{display_name}'",
            metadata={"project_id": str(project_id)},
        )
        return c

    async def update_competitor(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        competitor_id: UUID,
        actor_user_id: UUID,
        display_name: str | None = None,
        website_url: str | None = None,
        description: str | None = None,
    ) -> Competitor:
        existing = await self._get_competitor_or_raise(db, competitor_id, project_id)
        fields: dict[str, Any] = {}
        if display_name is not None:
            fields["display_name"] = display_name
        if website_url is not None:
            fields["website_url"] = website_url
        if description is not None:
            fields["description"] = description
        if not fields:
            return existing
        rows = await self.dao.update_competitor(db, competitor_id, project_id, fields=fields)
        if rows == 0:
            raise CompetitorNotFoundError(competitor_id=str(competitor_id))
        await db.refresh(existing, attribute_names=list(fields.keys()) + ["updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_updated",
            target_type="competitor",
            target_id=str(competitor_id),
            summary=f"Updated competitor '{existing.display_name}'",
            metadata={"changed_fields": list(fields.keys())},
        )
        return existing

    async def delete_competitor(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        competitor_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """删除竞品 + DB CASCADE 自动清 refs。

        design §10：先查 ref_count + 显式批量记 delete competitor_ref 事件 → 再删
        competitor（DB CASCADE 自动清 refs，service 层 activity_log 已显式记录）。
        """
        existing = await self._get_competitor_or_raise(db, competitor_id, project_id)
        # design §10 metadata 仅需 ref_count；DB CASCADE 自动清 refs；R10-1 批量
        # delete competitor_ref 事件 punt 到 M15 sprint 升级真 INSERT 时复审
        # （与 M04 R1-C C1.2 同款决策）。
        ref_count = await self.dao.count_refs_by_competitor(db, competitor_id, project_id)

        rows = await self.dao.delete_competitor(db, competitor_id, project_id)
        if rows == 0:
            raise CompetitorNotFoundError(competitor_id=str(competitor_id))
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_deleted",
            target_type="competitor",
            target_id=str(competitor_id),
            summary=f"Deleted competitor '{existing.display_name}'",
            metadata={"ref_count": ref_count},
        )
        # NB: DB CASCADE 已删 refs；R10-1 批量 delete competitor_ref 事件 punt 到 M15
        # sprint 升级真 INSERT 时复审（与 M04 R1-C C1.2 同款决策）。

    # ─── CompetitorRef CRUD ───

    async def list_refs_by_node(
        self, db: AsyncSession, *, project_id: UUID, node_id: UUID
    ) -> Sequence[CompetitorRef]:
        await self._check_node_belongs_to_project(db, node_id, project_id)
        return await self.dao.list_refs_by_node(db, node_id, project_id)

    async def get_ref(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        ref_id: UUID,
    ) -> CompetitorRef:
        await self._check_node_belongs_to_project(db, node_id, project_id)
        ref = await self.dao.get_ref_by_id(db, ref_id, project_id)
        if ref is None or ref.node_id != node_id:
            raise CompetitorRefNotFoundError(ref_id=str(ref_id))
        return ref

    async def create_ref(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        competitor_id: UUID,
        actor_user_id: UUID,
        competitor_version: str | None = None,
        feature_coverage: str | None = None,
        tech_approach: str | None = None,
        pros_and_cons: dict[str, Any] | None = None,
    ) -> CompetitorRef:
        await self._check_node_belongs_to_project(db, node_id, project_id)

        # cross-project 校验：competitor 必须属于本 project
        c = await self.dao.get_competitor_by_id(db, competitor_id, project_id)
        if c is None:
            raise CompetitorCrossProjectError(
                competitor_id=str(competitor_id), project_id=str(project_id)
            )

        ref = CompetitorRef(
            id=uuid4(),
            node_id=node_id,
            competitor_id=competitor_id,
            project_id=project_id,
            competitor_version=competitor_version,
            feature_coverage=feature_coverage,
            tech_approach=tech_approach,
            pros_and_cons=pros_and_cons,
            created_by=actor_user_id,
        )
        try:
            await self.dao.create_ref(db, ref)
        except IntegrityError as e:
            # R1-C P1-01 立修（M05 同款范式）：区分约束名避免错误码语义误导
            #   - uq_competitor_ref_node_competitor → 重复关联（409 CONFLICT）
            #   - 其他（如 FK competitor 被并发删）→ cross-project 语义（422 VALIDATION）
            err_text = str(e.orig) if e.orig else str(e)
            if "uq_competitor_ref_node_competitor" in err_text:
                raise CompetitorRefDuplicateError(
                    node_id=str(node_id), competitor_id=str(competitor_id)
                ) from e
            # FK competitors_id 不存在 / 其他 → 视为竞品已被并发删（语义最近）
            raise CompetitorCrossProjectError(
                competitor_id=str(competitor_id),
                project_id=str(project_id),
                reason="competitor_concurrently_modified",
            ) from e

        await db.refresh(ref, attribute_names=["created_at", "updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_ref_created",
            target_type="competitor_ref",
            target_id=str(ref.id),
            summary=f"Created competitor ref (node={node_id}, competitor={c.display_name})",
            metadata={
                "node_id": str(node_id),
                "competitor_id": str(competitor_id),
            },
        )
        return ref

    async def update_ref(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        ref_id: UUID,
        actor_user_id: UUID,
        competitor_version: str | None = None,
        feature_coverage: str | None = None,
        tech_approach: str | None = None,
        pros_and_cons: dict[str, Any] | None = None,
    ) -> CompetitorRef:
        existing = await self.get_ref(db, project_id=project_id, node_id=node_id, ref_id=ref_id)
        fields: dict[str, Any] = {}
        if competitor_version is not None:
            fields["competitor_version"] = competitor_version
        if feature_coverage is not None:
            fields["feature_coverage"] = feature_coverage
        if tech_approach is not None:
            fields["tech_approach"] = tech_approach
        if pros_and_cons is not None:
            fields["pros_and_cons"] = pros_and_cons
        if not fields:
            return existing
        rows = await self.dao.update_ref(db, ref_id, project_id, fields=fields)
        if rows == 0:
            raise CompetitorRefNotFoundError(ref_id=str(ref_id))
        await db.refresh(existing, attribute_names=list(fields.keys()) + ["updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_ref_updated",
            target_type="competitor_ref",
            target_id=str(ref_id),
            summary="Updated competitor ref",
            metadata={
                "node_id": str(node_id),
                "competitor_id": str(existing.competitor_id),
                "changed_fields": list(fields.keys()),
            },
        )
        return existing

    async def delete_ref(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        ref_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        existing = await self.get_ref(db, project_id=project_id, node_id=node_id, ref_id=ref_id)
        competitor_id = existing.competitor_id
        rows = await self.dao.delete_ref(db, ref_id, project_id)
        if rows == 0:
            raise CompetitorRefNotFoundError(ref_id=str(ref_id))
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="competitor_ref_deleted",
            target_type="competitor_ref",
            target_id=str(ref_id),
            summary="Deleted competitor ref",
            metadata={
                "node_id": str(node_id),
                "competitor_id": str(competitor_id),
            },
        )

    # ─── R-X2 真注入入口（M03 delete_node 调用）───

    async def delete_by_node_id(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """R-X2 注入入口（NodeChildrenServiceProtocol 4 参实现）。

        M03 delete_node 调用：清空指定 node 下所有 competitor_refs，每条独立写
        ``delete`` activity_log（design §10 R10-1 batch3）。

        异常契约 (R1-C P1-01)：不 catch-all 吞错；DAO/write_event 任一异常向上传播。

        **R10-1 弱化已知 punt（M06 R1-C P1-01 立修文字消歧 / 与 M04 R1-C C1.2 同款）**：
        ``rows == 0`` 路径**主动豁免** activity_log 写入（list 后被他方并发删 → 继续下一条
        不抛、不补记 cascade 事件）。这与"异常契约不 catch-all 吞错"的精神是兼容的——
        rows==0 不是异常路径而是数据态判定，但 R10-1 批量记录的"每条 delete event"在
        并发末尾 N 条会丢失。M15 升级 write_event 真 INSERT 时统一复审是否改用
        SELECT FOR UPDATE 防并发 / 或 INSERT 前缀写"尝试删但已不存在"事件。
        Audit 池：m04-pilot R1-C C1.2 + m06-pilot 同款延续。
        """
        records = await self.dao.list_refs_by_node_for_delete(db, node_id, project_id)
        for rec in records:
            rows = await self.dao.delete_ref(db, rec.id, project_id)
            if rows == 0:
                # R10-1 弱化主动豁免（见 docstring）：并发删除已被他方清，跳过 activity_log
                continue
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="competitor_ref_deleted",
                target_type="competitor_ref",
                target_id=str(rec.id),
                summary="Deleted competitor ref (cascade from node delete)",
                metadata={
                    "node_id": str(node_id),
                    "competitor_id": str(rec.competitor_id),
                    "cascade_source": "node_delete",
                },
            )

    # ─── M18 baseline-patch ───

    async def get_for_embedding(
        self, db: AsyncSession, competitor_id: UUID, project_id: UUID
    ) -> str | None:
        """M18 baseline-patch（A6 A 路径）：拼接 name + description 供 embedding。

        CY 决策 4：**url 字段不参与 embedding**，仅 name + description。
        """
        c = await self.dao.get_competitor_by_id(db, competitor_id, project_id)
        if c is None:
            return None
        parts = [c.display_name]
        if c.description:
            parts.append(c.description)
        return "\n".join(parts)
