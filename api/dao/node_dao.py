"""M03 DAO（async）— design/02-modules/M03-module-tree/00-design.md §9.

R-X3 精神：DAO 接受外部 session、不自 commit / 不自 begin。
事务由 Service 层 `async with db.begin():` 包裹。

主查询模式（design §9）：所有 list/get 强制 `WHERE project_id = ?` tenant 过滤。
M03 范围内全部查询都在 tenant 边界内（豁免清单：无）。
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import case, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.node import Node


class NodeDAO:
    # ─────────── 读 ───────────

    async def list_by_project(self, db: AsyncSession, project_id: UUID) -> Sequence[Node]:
        """获取项目下所有节点（前端构建树形）。

        按 (depth, sort_order) 排序——保证父节点先于子节点（前端可顺序构建嵌套）。
        """
        result = await db.execute(
            select(Node)
            .where(Node.project_id == project_id)
            .order_by(Node.depth.asc(), Node.sort_order.asc(), Node.id.asc())
        )
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> Node | None:
        """tenant 过滤：单节点查询强制带 project_id。"""
        result = await db.execute(
            select(Node).where(Node.id == node_id, Node.project_id == project_id)
        )
        return result.scalar_one_or_none()

    async def list_children(
        self, db: AsyncSession, parent_id: UUID | None, project_id: UUID
    ) -> Sequence[Node]:
        """同级子节点（reorder 范围验证用）。

        parent_id=None 表示根层级。
        """
        if parent_id is None:
            stmt = select(Node).where(Node.project_id == project_id, Node.parent_id.is_(None))
        else:
            stmt = select(Node).where(Node.project_id == project_id, Node.parent_id == parent_id)
        result = await db.execute(stmt.order_by(Node.sort_order.asc(), Node.id.asc()))
        return result.scalars().all()

    async def list_subtree(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> Sequence[Node]:
        """通过 path LIKE 获取子树（含自身）。

        前置：先 get_by_id 拿到 anchor.path，再以其作为 LIKE 前缀查询。
        text_pattern_ops 索引（ix_nodes_path）支撑高效前缀匹配。
        """
        anchor = await self.get_by_id(db, node_id, project_id)
        if anchor is None:
            return []
        result = await db.execute(
            select(Node)
            .where(
                Node.project_id == project_id,
                Node.path.like(f"{anchor.path}%"),
            )
            .order_by(Node.depth.asc(), Node.sort_order.asc(), Node.id.asc())
        )
        return result.scalars().all()

    async def max_sort_order(
        self, db: AsyncSession, parent_id: UUID | None, project_id: UUID
    ) -> int | None:
        """同级节点最大 sort_order（新建节点追加末尾用）。"""
        if parent_id is None:
            stmt = select(Node.sort_order).where(
                Node.project_id == project_id, Node.parent_id.is_(None)
            )
        else:
            stmt = select(Node.sort_order).where(
                Node.project_id == project_id, Node.parent_id == parent_id
            )
        result = await db.execute(stmt.order_by(Node.sort_order.desc()).limit(1))
        return result.scalar_one_or_none()

    # ─────────── 写 ───────────

    async def create(self, db: AsyncSession, **fields: Any) -> Node:
        node = Node(**fields)
        db.add(node)
        await db.flush()
        return node

    async def update_fields(self, db: AsyncSession, node: Node, **fields: Any) -> Node:
        for k, v in fields.items():
            setattr(node, k, v)
        await db.flush()
        return node

    async def delete_one(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> int:
        """硬删除单节点（CASCADE 兜底删子树 + project_members）。

        返回删除行数（0 = 节点不存在 / 跨租户）。
        """
        result = await db.execute(
            delete(Node).where(Node.id == node_id, Node.project_id == project_id)
        )
        await db.flush()
        return result.rowcount or 0

    async def bulk_update_sort_order(
        self,
        db: AsyncSession,
        project_id: UUID,
        parent_id: UUID | None,
        items: list[tuple[UUID, int]],
    ) -> int:
        """同级节点批量更新 sort_order（reorder 用）。

        用 CASE WHEN 一条 UPDATE 完成 N 条更新，避免 N+1（M02 R2 优化范式）。
        全部 WHERE 强制 (project_id, parent_id) 双过滤防越界。
        """
        if not items:
            return 0
        node_ids = [nid for nid, _ in items]
        case_expr = case(
            {nid: so for nid, so in items},
            value=Node.id,
        )
        if parent_id is None:
            parent_clause = Node.parent_id.is_(None)
        else:
            parent_clause = Node.parent_id == parent_id
        stmt = (
            update(Node)
            .where(
                Node.project_id == project_id,
                parent_clause,
                Node.id.in_(node_ids),
            )
            .values(sort_order=case_expr)
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount or 0

    async def update_paths_in_subtree(
        self,
        db: AsyncSession,
        project_id: UUID,
        old_prefix: str,
        new_prefix: str,
        depth_delta: int,
    ) -> int:
        """move_subtree 子树 path 批量重写 + depth 同步更新（G5）。

        一条 SQL：REPLACE(path, old_prefix, new_prefix) + depth = depth + delta。
        WHERE path LIKE old_prefix || '%' 限定子树。
        """
        from sqlalchemy import func as sa_func

        stmt = (
            update(Node)
            .where(
                Node.project_id == project_id,
                Node.path.like(f"{old_prefix}%"),
            )
            .values(
                path=sa_func.replace(Node.path, old_prefix, new_prefix),
                depth=Node.depth + depth_delta,
            )
        )
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount or 0
