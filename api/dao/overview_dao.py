"""M10 OverviewDAO (async) — design/02-modules/M10-overview/00-design.md §3 + §9.

ADR-003 规则 2 豁免：本 DAO 只读 import 上游 model 做 JOIN 聚合，禁止
INSERT/UPDATE/DELETE。方案 A 实时 JOIN，不写任何表。

主查询模式：所有查询强制 ``WHERE project_id = ?`` tenant 过滤；豁免清单：无。
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ADR-003 规则 2 豁免：只读 import 上游 model
from api.models.dimension_record import DimensionRecord
from api.models.node import Node
from api.models.project import ProjectDimensionConfig


class OverviewDAO:
    """M10 只读聚合 DAO — 跨 M02 + M03 + M04 实时 JOIN（方案 A）。"""

    async def count_enabled_dimensions(self, db: AsyncSession, project_id: UUID) -> int:
        """项目启用维度数（completion_rate 分母）。"""
        result = await db.execute(
            select(func.count()).where(
                ProjectDimensionConfig.project_id == project_id,
                ProjectDimensionConfig.enabled.is_(True),
            )
        )
        return int(result.scalar_one())

    async def list_nodes_with_fill_count(
        self, db: AsyncSession, project_id: UUID
    ) -> list[dict[str, Any]]:
        """项目所有节点 + 每节点已填维度数（一条 SQL：nodes LEFT JOIN dimension_records）。

        返回 dict 形态供 service 层组装；ORDER BY (depth, sort_order, id) 保证树形展开顺序稳定。
        """
        stmt = (
            select(
                Node.id,
                Node.parent_id,
                Node.name,
                Node.type,
                Node.depth,
                Node.sort_order,
                Node.path,
                func.count(DimensionRecord.id).label("filled_count"),
            )
            .outerjoin(
                DimensionRecord,
                and_(
                    DimensionRecord.node_id == Node.id,
                    DimensionRecord.project_id == project_id,
                ),
            )
            .where(Node.project_id == project_id)
            .group_by(Node.id)
            .order_by(Node.depth, Node.sort_order, Node.id)
        )
        result = await db.execute(stmt)
        rows = result.all()
        return [
            {
                "id": r.id,
                "parent_id": r.parent_id,
                "name": r.name,
                "type": r.type,
                "depth": r.depth,
                "sort_order": r.sort_order,
                "path": r.path,
                "filled_count": int(r.filled_count or 0),
            }
            for r in rows
        ]

    async def get_node_fill_count(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> dict[str, Any] | None:
        """单节点 fill_count（M04 档案页完善度进度条复用）。

        返回 None 表示节点不存在；返 dict 含 id / type / filled_count（folder 节点
        本方法仅返自身 dimension_records 数，不做子树汇总——汇总走 list_nodes_with_fill_count）。
        """
        stmt = (
            select(
                Node.id,
                Node.type,
                func.count(DimensionRecord.id).label("filled_count"),
            )
            .outerjoin(
                DimensionRecord,
                and_(
                    DimensionRecord.node_id == Node.id,
                    DimensionRecord.project_id == project_id,
                ),
            )
            .where(
                Node.id == node_id,
                Node.project_id == project_id,
            )
            .group_by(Node.id)
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if row is None:
            return None
        return {
            "id": row.id,
            "type": row.type,
            "filled_count": int(row.filled_count or 0),
        }
