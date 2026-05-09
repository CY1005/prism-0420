"""M19 ExportService — design/02-modules/M19-import-export/00-design.md §6.

业务能力：
  - generate_markdown(db, project_id, node_ids, include, user_id) -> bytes
    入口 A 多 node 与入口 B 单 node 共享此方法（B = A with node_ids=[node_id]）。

事务边界（M02-M18 共享范式）：Router 管 commit；service 接受外部 AsyncSession，
不调 ``async with db.begin():``。M19 全只读 + 仅写 1 条 activity_log（write_event 走
caller 事务）。

DAO 复用（ADR-003 规则 1 / CY ack 2026-04-21 Q4）：
  - DimensionDAO.list_by_node / VersionDAO.list_by_node /
    CompetitorDAO.list_refs_by_node / IssueDAO.list_by_project(node_id=) /
    NodeDAO.list_by_ids（cross-project 校验）
  各上游 DAO 已内置 project_id tenant 过滤；ExportService 不重复写查询。

DimensionType / Competitor / Project 横切表无独立 list_by_ids DAO（M02 owns）→
ExportService 直接 select 命中 PK / project_id 索引（M12 ComparisonService 范式延续）。

权限三层防御（design §8）：
  Server Action / Router check_project_access(role="viewer") 已防外层（design §8 字面：
  viewer 即可导出）；
  Service 层 _validate_and_load_nodes 防 cross-project 越权（不暴露 forbidden）。
"""

from __future__ import annotations

import json as _json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.competitor_dao import CompetitorDAO
from api.dao.dimension_dao import DimensionDAO
from api.dao.issue_dao import IssueDAO
from api.dao.node_dao import NodeDAO
from api.dao.version_dao import VersionDAO
from api.errors.exceptions import (
    ExportEmptyContentError,
    ExportNodeNotInProjectError,
)
from api.models.competitor import Competitor
from api.models.dimension_record import DimensionRecord
from api.models.node import Node
from api.models.project import DimensionType, Project
from api.schemas.export_schema import ExportIncludeOptions
from api.services.activity_log_service import write_event

# action_type / target_type 字面（design §10 / R14 ci-lint 守护 + R1 过去式立规对齐）
# R1-B 漏识别 #2 立修：M16 R14 立规精神过去式 + snake_case；design §10 字面 "export" sprint
# 子片 1 R1 立修对齐范式 / design §10 + frontmatter line 51-53 同步回写 "exported"
ACTION_EXPORT = "exported"
TARGET_NODE = "node"


class ExportService:
    def __init__(
        self,
        dimension_dao: DimensionDAO | None = None,
        version_dao: VersionDAO | None = None,
        competitor_dao: CompetitorDAO | None = None,
        issue_dao: IssueDAO | None = None,
        node_dao: NodeDAO | None = None,
    ) -> None:
        self.dimension_dao = dimension_dao or DimensionDAO()
        self.version_dao = version_dao or VersionDAO()
        self.competitor_dao = competitor_dao or CompetitorDAO()
        self.issue_dao = issue_dao or IssueDAO()
        self.node_dao = node_dao or NodeDAO()

    # ─────────────── public ───────────────

    async def generate_markdown(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_ids: list[UUID],
        include: ExportIncludeOptions,
        user_id: UUID,
    ) -> bytes:
        """两入口共享。返回 UTF-8 编码的 Markdown bytes。

        校验顺序（M07/M12 范式延续）：
        1. NodeDAO.list_by_ids 跨 project 校验（任一不属于本 project → 404 NotFound）
        2. 渲染前若所有 node 在 include 选项下均无内容 → 422 EXPORT_EMPTY_CONTENT
        3. write_event(action_type="exported", target_type="node", target_id=node_ids[0])
        """
        nodes = await self._validate_and_load_nodes(db, project_id, node_ids)
        project = await self._load_project(db, project_id)

        per_node_data: list[tuple[Node, dict[str, list]]] = []
        any_content = False
        for node in nodes:
            data = await self._fetch_node_data(db, node, project_id, include)
            if data["dimensions"] or data["versions"] or data["competitors"] or data["issues"]:
                any_content = True
            per_node_data.append((node, data))

        if not any_content:
            raise ExportEmptyContentError()

        # 横切表批量预取（避免 lazy-load + N+1）
        dim_type_index = await self._batch_load_dimension_types(db, per_node_data)
        competitor_index = await self._batch_load_competitors(db, project_id, per_node_data)

        markdown = self._render_markdown(
            project, per_node_data, include, dim_type_index, competitor_index
        )
        body = markdown.encode("utf-8")

        # activity_log（design §10 / target_type=node 让 M15 数据流转能精确定位导出了哪些 node）
        await write_event(
            db=db,
            actor_user_id=user_id,
            project_id=project_id,
            action_type=ACTION_EXPORT,
            target_type=TARGET_NODE,
            target_id=str(nodes[0].id),
            summary=f"导出 Markdown 报告（{len(nodes)} 个模块）",
            metadata={
                "node_ids": [str(n.id) for n in nodes],
                "node_count": len(nodes),
                "sections": include.model_dump(),
                "file_size_bytes": len(body),
            },
        )

        return body

    # ─────────────── 内部 ───────────────

    async def _validate_and_load_nodes(
        self, db: AsyncSession, project_id: UUID, node_ids: list[UUID]
    ) -> list[Node]:
        """所有 node_id 必须属于该 project；任一不命中 → 404 ExportNodeNotInProjectError。

        M12 ComparisonService._validate_nodes_in_project 范式延续；保留入参顺序排序
        让 Markdown 输出顺序与用户传入一致（list_by_ids 顺序不保证）。
        """
        # R1-A P1-3 + R1-C P1-1 立修：dict.fromkeys 保序去重 / 消除原 set 推导 + 二段 seen
        # 双重去重逻辑（结果原本正确但鲁棒性低）
        unique_ids = list(dict.fromkeys(node_ids))
        rows = await self.node_dao.list_by_ids(db, unique_ids, project_id)
        if len(rows) != len(unique_ids):
            found = {n.id for n in rows}
            missing = [nid for nid in unique_ids if nid not in found]
            raise ExportNodeNotInProjectError(
                project_id=str(project_id),
                missing_node_ids=[str(nid) for nid in missing],
            )
        by_id = {n.id: n for n in rows}
        return [by_id[nid] for nid in unique_ids]

    async def _load_project(self, db: AsyncSession, project_id: UUID) -> Project:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            # check_project_access 已在 Router 层防御；此处兜底（不应触发 / cross-tenant 已 NodeDAO 拦）
            raise ExportNodeNotInProjectError(project_id=str(project_id))
        return project

    async def _fetch_node_data(
        self,
        db: AsyncSession,
        node: Node,
        project_id: UUID,
        include: ExportIncludeOptions,
    ) -> dict[str, list]:
        data: dict[str, list] = {
            "dimensions": [],
            "versions": [],
            "competitors": [],
            "issues": [],
        }
        if include.dimensions:
            records = await self.dimension_dao.list_by_node(
                db, node_id=node.id, project_id=project_id
            )
            data["dimensions"] = list(records)
        if include.versions:
            records = await self.version_dao.list_by_node(
                db, node_id=node.id, project_id=project_id
            )
            data["versions"] = list(records)
        if include.competitors:
            refs = await self.competitor_dao.list_refs_by_node(
                db, node_id=node.id, project_id=project_id
            )
            data["competitors"] = list(refs)
        if include.issues:
            issues = await self.issue_dao.list_by_project(
                db, project_id=project_id, node_id=node.id
            )
            data["issues"] = list(issues)
        return data

    async def _batch_load_dimension_types(
        self, db: AsyncSession, per_node_data: list[tuple[Node, dict[str, list]]]
    ) -> dict[int, DimensionType]:
        type_ids: set[int] = set()
        for _, data in per_node_data:
            for record in data["dimensions"]:
                type_ids.add(record.dimension_type_id)
        if not type_ids:
            return {}
        result = await db.execute(select(DimensionType).where(DimensionType.id.in_(type_ids)))
        return {dt.id: dt for dt in result.scalars().all()}

    async def _batch_load_competitors(
        self,
        db: AsyncSession,
        project_id: UUID,
        per_node_data: list[tuple[Node, dict[str, list]]],
    ) -> dict[UUID, Competitor]:
        comp_ids: set[UUID] = set()
        for _, data in per_node_data:
            for ref in data["competitors"]:
                comp_ids.add(ref.competitor_id)
        if not comp_ids:
            return {}
        result = await db.execute(
            select(Competitor).where(
                Competitor.id.in_(comp_ids),
                Competitor.project_id == project_id,
            )
        )
        return {c.id: c for c in result.scalars().all()}

    # ─────────────── Markdown 渲染（design §7 字面结构） ───────────────

    def _render_markdown(
        self,
        project: Project,
        per_node_data: list[tuple[Node, dict[str, list]]],
        include: ExportIncludeOptions,
        dim_type_index: dict[int, DimensionType],
        competitor_index: dict[UUID, Competitor],
    ) -> str:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        lines: list[str] = [
            f"# 分析报告 — {project.name}",
            f"> 生成时间：{now}",
            "",
            "---",
            "",
        ]

        for node, data in per_node_data:
            lines.append(f"## {node.name}")
            lines.append("")
            if node.path:
                lines.append(f"> 路径：{node.path}")
                lines.append("")

            if include.dimensions and data["dimensions"]:
                lines.append("### 维度信息")
                lines.append("")
                for record in data["dimensions"]:
                    dim_type = dim_type_index.get(record.dimension_type_id)
                    title = dim_type.name if dim_type else f"维度 #{record.dimension_type_id}"
                    lines.append(f"#### {title}")
                    lines.append("")
                    lines.append(_render_dimension_content(record))
                    lines.append("")

            if include.versions and data["versions"]:
                lines.append("### 版本时间线")
                lines.append("")
                lines.append("| 版本号 | 变更类型 | 摘要 | 创建时间 |")
                lines.append("|--------|---------|------|---------|")
                for v in data["versions"]:
                    summary = _md_cell(v.summary or "")
                    created = v.created_at.isoformat(timespec="seconds") if v.created_at else ""
                    lines.append(
                        f"| {_md_cell(v.version_label)} | {_md_cell(v.change_type)} | "
                        f"{summary} | {created} |"
                    )
                lines.append("")

            if include.competitors and data["competitors"]:
                lines.append("### 竞品参考")
                lines.append("")
                lines.append("| 竞品 | 版本 | 覆盖情况 | 优劣势 |")
                lines.append("|------|------|---------|--------|")
                for ref in data["competitors"]:
                    competitor = competitor_index.get(ref.competitor_id)
                    name = _md_cell(competitor.display_name) if competitor else "-"
                    coverage = _md_cell(ref.feature_coverage or "")
                    pros_cons = _render_pros_cons(ref.pros_and_cons)
                    lines.append(
                        f"| {name} | {_md_cell(ref.competitor_version or '-')} | "
                        f"{coverage} | {pros_cons} |"
                    )
                lines.append("")

            if include.issues and data["issues"]:
                lines.append("### 问题沉淀")
                lines.append("")
                lines.append("| 类型 | 标题 | 状态 |")
                lines.append("|------|------|------|")
                for issue in data["issues"]:
                    lines.append(
                        f"| {_md_cell(issue.category)} | {_md_cell(issue.title)} | "
                        f"{_md_cell(issue.status)} |"
                    )
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)


def _md_cell(text: str) -> str:
    """Markdown 表格单元格转义：| → \\| / 换行 → 空格。"""
    return (text or "").replace("|", "\\|").replace("\n", " ").replace("\r", "")


def _render_dimension_content(record: DimensionRecord) -> str:
    content = record.content or {}
    if not content:
        return "_（空）_"
    out: list[str] = []
    for k, v in content.items():
        if isinstance(v, (dict, list)):
            out.append(f"- **{k}**:")
            out.append("  ```json")
            for line in _json.dumps(v, ensure_ascii=False, indent=2).splitlines():
                out.append(f"  {line}")
            out.append("  ```")
        else:
            out.append(f"- **{k}**: {v}")
    return "\n".join(out)


def _render_pros_cons(pros_and_cons: dict | None) -> str:
    if not pros_and_cons:
        return "-"
    pros = pros_and_cons.get("pros") or []
    cons = pros_and_cons.get("cons") or []
    parts: list[str] = []
    if pros:
        parts.append("优势: " + "; ".join(str(p) for p in pros))
    if cons:
        parts.append("劣势: " + "; ".join(str(c) for c in cons))
    return _md_cell(" / ".join(parts) or "-")
