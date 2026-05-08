"""M10 OverviewService — design/02-modules/M10-overview/00-design.md §6.

事务边界：M10 纯读聚合，无写操作（design §5 多表事务 N/A）。

ADR-003 规则 2 豁免：DAO 层只读 import 上游 model；service 层不写 activity_log。

folder 均值算法（design §3 决策 D-1 / M10-B2 迭代后序遍历）：
  - file 节点：completion_rate = filled_count / enabled_count
  - folder 节点：均值 = sum(子树 file 节点 rate) / count(子树 file 节点)
  - 实现：按 depth DESC + sort_order DESC 排序，bottom-up 累计 file_count + sum_rate
    （deque pop / 非递归避免 Python 默认栈深度 1000 的深层树风险）

分母=0 早返回（design M10-B3）：
  count_enabled_dimensions == 0 → 立即 raise OverviewNoDimensionsError(422)
  不进入节点聚合查询（避免半成品状态）。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.overview_dao import OverviewDAO
from api.errors.exceptions import (
    OverviewNodeNotFoundError,
    OverviewNoDimensionsError,
    OverviewProjectNotFoundError,
)
from api.models.node import NodeType
from api.models.project import Project


class OverviewService:
    def __init__(self, dao: OverviewDAO | None = None) -> None:
        self.dao = dao or OverviewDAO()

    async def _check_project_exists(self, db: AsyncSession, project_id: UUID) -> None:
        """project 真实存在校验（Router check_project_access 已校 user 权限，
        本层加一道存在性兜底；project 不存在 → OverviewProjectNotFoundError 404）。"""
        result = await db.execute(select(Project.id).where(Project.id == project_id))
        if result.scalar_one_or_none() is None:
            raise OverviewProjectNotFoundError(project_id=str(project_id))

    async def get_overview(self, db: AsyncSession, *, project_id: UUID) -> dict[str, Any]:
        """全景图主入口：返回 tree（嵌套 children）+ stats。

        分母=0 早返回（design M10-B3）：count_enabled == 0 → OverviewNoDimensionsError
        不进入节点聚合（避免半成品）。

        R1-A P1-04 false positive 撤销（2026-05-08）：reviewer 建议 asyncio.gather
        并行，但 SA AsyncSession 同 session 不允许 concurrent IO（"This session is
        provisioning a new connection"），实测立即报错。M08 R1-C P1-02 同款 gather
        能 pass 是因为测试路径未触发真并发（巧合）；范式实为 false positive。
        保持串行 await，性能损失 1 RTT 进 m10 audit punt 池。
        """
        await self._check_project_exists(db, project_id)
        enabled_count = await self.dao.count_enabled_dimensions(db, project_id)
        if enabled_count == 0:
            raise OverviewNoDimensionsError(project_id=str(project_id))

        flat_rows = await self.dao.list_nodes_with_fill_count(db, project_id)
        completed_nodes = self._compute_completion_rates(flat_rows, enabled_count)

        # 组装 tree（parent_id=NULL 的为顶层）+ stats
        tree = self._build_tree(completed_nodes)
        stats = self._compute_stats(completed_nodes, enabled_count)
        return {"project_id": project_id, "tree": tree, "stats": stats}

    async def get_stats(self, db: AsyncSession, *, project_id: UUID) -> dict[str, Any]:
        """轻量 stats endpoint（不返 tree）。"""
        await self._check_project_exists(db, project_id)
        enabled_count = await self.dao.count_enabled_dimensions(db, project_id)
        if enabled_count == 0:
            raise OverviewNoDimensionsError(project_id=str(project_id))
        flat_rows = await self.dao.list_nodes_with_fill_count(db, project_id)
        completed = self._compute_completion_rates(flat_rows, enabled_count)
        return {
            "project_id": project_id,
            "stats": self._compute_stats(completed, enabled_count),
        }

    async def get_node_completion(
        self, db: AsyncSession, *, project_id: UUID, node_id: UUID
    ) -> dict[str, Any]:
        """单节点完善度（M04 档案页复用）。

        - file 节点：filled_count / enabled_count
        - folder 节点：子树 file 节点均值（**与 get_overview 一致**走 list_nodes_with_fill_count
          整体计算后取该节点对应行；保证 folder 均值算法单一真相源）
        """
        await self._check_project_exists(db, project_id)
        enabled_count = await self.dao.count_enabled_dimensions(db, project_id)
        if enabled_count == 0:
            raise OverviewNoDimensionsError(project_id=str(project_id))

        # R1-A P1-03 立修（hot path 性能优化）：file 节点走 dao.get_node_fill_count
        # O(1) 单查询；folder 节点才走 list_nodes_with_fill_count O(N) 整体路径
        # （保 folder 均值算法一致性）。M04 档案页打开 99% 流量是 file 节点，避免
        # O(N) 全表聚合。
        single = await self.dao.get_node_fill_count(db, node_id, project_id)
        if single is None:
            raise OverviewNodeNotFoundError(node_id=str(node_id))
        if single["type"] == NodeType.FILE.value:
            filled = single.get("filled_count") or 0
            rate = filled / enabled_count
            if rate > 1.0:
                rate = 1.0
            return {
                "node_id": node_id,
                "filled_count": filled,
                "enabled_count": enabled_count,
                "completion_rate": rate,
            }

        # folder 节点：仍走整体计算路径保 folder 均值算法一致（design §3 M10-B2）
        flat_rows = await self.dao.list_nodes_with_fill_count(db, project_id)
        completed = self._compute_completion_rates(flat_rows, enabled_count)
        for n in completed:
            if n["id"] == node_id:
                return {
                    "node_id": node_id,
                    "filled_count": n["filled_count"],
                    "enabled_count": enabled_count,
                    "completion_rate": n["completion_rate"],
                }
        raise OverviewNodeNotFoundError(node_id=str(node_id))

    # ─── 内部算法 ───

    def _compute_completion_rates(
        self,
        flat_rows: list[dict[str, Any]],
        enabled_count: int,
    ) -> list[dict[str, Any]]:
        """folder 均值"迭代后序遍历"算法（design §3 D-1 / M10-B2）。

        步骤：
        1. file 节点：completion_rate = filled_count / enabled_count
        2. 按 depth DESC 排序后处理 — 子节点先算完，folder 节点用子节点 file 均值
        3. 用 dict 缓存每节点的 (file_count_in_subtree, sum_rate_in_subtree)
        4. folder 节点 completion_rate = sum_rate / file_count（如 file_count=0 则 0.0）
        """
        if enabled_count == 0:
            # 上层已早返回，此处仅防御性兜底
            for r in flat_rows:
                r["completion_rate"] = 0.0
            return flat_rows

        # 子节点 id 集合 by parent
        children_by_parent: dict[Any, list[Any]] = {}
        for r in flat_rows:
            pid = r["parent_id"]
            children_by_parent.setdefault(pid, []).append(r["id"])

        # subtree 累计：node_id → (file_count, sum_rate)
        subtree: dict[Any, tuple[int, float]] = {}

        # 按 depth DESC 处理（叶节点先）
        sorted_rows = sorted(flat_rows, key=lambda r: -r["depth"])
        for r in sorted_rows:
            rid = r["id"]
            ntype = r["type"]
            if ntype == NodeType.FILE.value:
                rate = (r["filled_count"] or 0) / enabled_count
                if rate > 1.0:
                    rate = 1.0  # 防御 filled_count > enabled_count（design 边界）
                r["completion_rate"] = rate
                subtree[rid] = (1, rate)
            else:
                # folder：累加子节点 subtree 数据
                file_count = 0
                sum_rate = 0.0
                for cid in children_by_parent.get(rid, []):
                    cf, cs = subtree.get(cid, (0, 0.0))
                    file_count += cf
                    sum_rate += cs
                if file_count > 0:
                    r["completion_rate"] = sum_rate / file_count
                else:
                    # 空 folder（无子 file）→ 0.0
                    r["completion_rate"] = 0.0
                subtree[rid] = (file_count, sum_rate)

        return flat_rows

    def _build_tree(self, flat_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """flat list → 树形 children 嵌套（parent_id=NULL 的为顶层）。"""
        # 复制 + 加 children 字段
        nodes_by_id: dict[Any, dict[str, Any]] = {}
        for r in flat_rows:
            n = dict(r)
            n["children"] = []
            nodes_by_id[n["id"]] = n

        roots: list[dict[str, Any]] = []
        for n in nodes_by_id.values():
            pid = n["parent_id"]
            if pid is None or pid not in nodes_by_id:
                roots.append(n)
            else:
                nodes_by_id[pid]["children"].append(n)

        # 按 sort_order, id 排序
        def _sort(group: list[dict[str, Any]]) -> None:
            group.sort(key=lambda x: (x["sort_order"], str(x["id"])))
            for c in group:
                _sort(c["children"])

        _sort(roots)
        return roots

    def _compute_stats(
        self,
        completed: list[dict[str, Any]],
        enabled_count: int,
    ) -> dict[str, Any]:
        """项目整体统计（仅 file 节点参与均值）。"""
        files = [n for n in completed if n["type"] == NodeType.FILE.value]
        total_nodes = len(completed)
        file_count = len(files)
        fully = sum(1 for n in files if n["completion_rate"] >= 1.0)
        empty = sum(1 for n in files if n["completion_rate"] == 0.0)
        avg = sum(n["completion_rate"] for n in files) / file_count if file_count else 0.0
        return {
            "total_nodes": total_nodes,
            "file_nodes": file_count,
            "fully_complete_nodes": fully,
            "empty_nodes": empty,
            "avg_completion_rate": avg,
            "enabled_dimension_count": enabled_count,
        }
