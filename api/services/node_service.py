"""M03 NodeService — design/02-modules/M03-module-tree/00-design.md §6.

# 子片 2 范围（本文件本期落地）：
#   1. NodeChildrenServiceProtocol — 跨模块 stub 注入点（A3 reconcile，scaffold S2 范式）
#   2. NodeService.get_for_embedding(db, node_id, project_id) -> str | None
#      — A 路径 M18 baseline-patch 被动接口（design §6.X A4），M03 own 现在建
#
# 子片 3 待补：create_node / update_node / delete_node / reorder / move_subtree
#                / batch_create_in_transaction + path 计算 + activity_log

# Scaffold 简化决策（2026-05-07，子片 2 — A4 enqueue B 推迟）
# ① 决策内容：M03 sprint 期 create_node / update_node / delete_node commit 后
#    **不调** embedding_service.enqueue / enqueue_delete
# ② 简化理由：M18 own embedding_service 在 M03 sprint 期不存在（B caller）；按
#    design §6.X A4 主标准 Q1 否 + Q2 caller → B 推迟
# ③ 由 M18 sprint 扩齐：create_node / update_node (name/description 改时) commit 后
#    尾调 embedding_service.enqueue(target_type="node", target_id, project_id, user_id,
#    enqueued_by="incremental")；delete_node commit 后异步 enqueue_delete +
#    SilentFailure + embedding_failures EMBEDDING_DELETE_FAILED + cleanup cron 兜底
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M03 §6 实施期处理段 status
"""

from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.node_dao import NodeDAO

# ─────────────── A3 reconcile：跨模块 stub Protocol（同 tenant_filter scaffold S2 范式）───────────────


class NodeChildrenServiceProtocol(Protocol):
    """M04 / M06 / M07 各 sprint 注入 concrete impl（design §6 R-X2）。

    delete_node 调用方按 target_type 分发：
      - target_type="dimension" → M04 DimensionService.delete_by_node_id（真删）
      - target_type="competitor" → M06 CompetitorService.delete_by_node_id（真删）
      - target_type="issue"      → M07 IssueService.orphan_by_node_id（SET NULL，FK 语义）
    各 service 自写 activity_log（防 DB CASCADE 绕过 R-X2）。
    M03 sprint 期注册表为空 → noop（M04/M06/M07 表此期不存在，无下游数据需清）。
    """

    async def __call__(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> None: ...


# Scaffold 简化决策（2026-05-07，子片 2 — A3 reconcile）
# ① 决策内容：M03 sprint 期跨模块 child service 注册表为空 noop
# ② 简化理由：M04/M06/M07 sprint 期不存在；下游表也不存在 → 无数据需清
# ③ 由 M04/M06/M07 各 sprint 启动时 register_child_service(target_type, callable)
#    在 lifespan startup 注入 concrete impl
# ④ 触发回写动作：各模块 sprint add register 调用 + 回归测试覆盖 delete 走下游 path
_child_services: dict[str, NodeChildrenServiceProtocol] = {}


def register_child_service(target_type: str, service: NodeChildrenServiceProtocol) -> None:
    """M04/M06/M07 sprint 启动时注入 concrete impl。"""
    _child_services[target_type] = service


def clear_child_services() -> None:
    """测试 fixture / 应用关停清空注册表。"""
    _child_services.clear()


def get_child_services() -> dict[str, NodeChildrenServiceProtocol]:
    """子片 3 delete_node 调用方读注册表。"""
    return dict(_child_services)


# ─────────────── NodeService（子片 2 仅含 get_for_embedding） ───────────────


class NodeService:
    """M03 业务 service（子片 2 仅 get_for_embedding；CRUD 子片 3 补齐）。"""

    def __init__(self, dao: NodeDAO | None = None) -> None:
        self.dao = dao or NodeDAO()

    async def get_for_embedding(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> str | None:
        """M18 baseline-patch 被动接口（design §6.X A4 A 路径，M03 own 现在建）。

        返回 `name + "\\n" + description`（description=None 时仅返回 name）。
        节点不存在 / 跨租户 → 返回 None（worker 拿到 None = 节点已删，noop 不嵌入）。

        死代码期：M03 sprint → M18 sprint。M18 sprint 期 worker 调用 + 回归测试覆盖
        生产路径（M18 baseline-patch 实施时回写 M03 §6.X A4 status=已落地）。
        """
        node = await self.dao.get_by_id(db, node_id, project_id)
        if node is None:
            return None
        if node.description:
            return f"{node.name}\n{node.description}"
        return node.name


# 占位以便子片 3 / 测试 import（避免再开 PR 改 __init__）
__all__ = [
    "NodeChildrenServiceProtocol",
    "NodeDAO",
    "NodeService",
    "clear_child_services",
    "get_child_services",
    "register_child_service",
]
