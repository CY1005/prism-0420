"""M03 NodeService — design/02-modules/M03-module-tree/00-design.md §6.

事务边界: 所有"产生副作用 + 写 activity_log"的方法用 `async with db.begin():` 包裹.

# Scaffold 简化决策（2026-05-07，子片 3 — A4 enqueue B 推迟）
# ① 决策内容：M03 sprint 期 create_node / update_node / delete_node commit 后
#    **不调** embedding_service.enqueue / enqueue_delete
# ② 简化理由：M18 own embedding_service 在 M03 sprint 期不存在（B caller）；按
#    design §6.X A4 主标准 Q1 否 + Q2 caller → B 推迟
# ③ 由 M18 sprint 扩齐：create_node / update_node (name/description 改时) commit 后
#    尾调 embedding_service.enqueue(target_type="node", target_id, project_id, user_id,
#    enqueued_by="incremental")；delete_node commit 后异步 enqueue_delete +
#    SilentFailure + embedding_failures EMBEDDING_DELETE_FAILED + cleanup cron 兜底
# ④ 触发回写动作：M18 sprint add 调用 + 回归测试 + 回写 M03 §6 实施期处理段 status

# Scaffold 简化决策（2026-05-07，子片 3 — A3 reconcile 跨模块 stub）
# ① 决策内容：M03 sprint 期 _child_services 注册表为空 noop；delete_node 仍
#    list_subtree + 写 per-node activity_log + DB CASCADE 兜底删子树
# ② 简化理由：M04/M06/M07 sprint 期不存在；下游表也不存在 → 无数据需清
# ③ 由 M04/M06/M07 各 sprint 启动时 register_child_service 在 lifespan 注入 concrete
# ④ 触发回写动作：各模块 sprint add register 调用 + 回归测试覆盖 delete 走下游 path
"""

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.dao.node_dao import NodeDAO
from api.errors.exceptions import (
    NodeMoveCycleDetectedError,
    NodeNotFoundError,
    NodeParentNotFoundError,
    NodeReorderInvalidError,
    NodeTypeImmutableError,
)
from api.models.node import Node, NodeType
from api.services.activity_log_service import write_event

# ─────────────── A3 reconcile：跨模块 stub Protocol ───────────────


class NodeChildrenServiceProtocol(Protocol):
    """M04 / M06 / M07 各 sprint 注入 concrete impl（design §6 R-X2）。

    delete_node 调用方按 target_type 分发：
      - target_type="dimension"       → M04 DimensionService.delete_by_node_id（真删）
      - target_type="competitor"      → M06 CompetitorService.delete_by_node_id（真删）
      - target_type="issue"           → M07 IssueService.orphan_by_node_id（SET NULL，FK 语义）
      - target_type="module_relation" → M08 ModuleRelationService.delete_by_node_id（真删 + 双向 OR：source 或 target 命中）
    各 service 自写 activity_log（防 DB CASCADE 绕过 R-X2）。
    M03 → M08 sprint 期累计注入 4 项（M03 期注册表为空 → noop）。

    **异常契约 (R1-C P1-01 修)**：concrete impl **必须**让所有异常向上传播，
    不得在内部 catch-all 吞掉错误。M03 delete_node 事务正确性依赖此契约——
    若下游 service 静默吞错，子树清理会半途而废但 DB CASCADE 兜底删 nodes，
    导致 dimension_records/competitors/issues 残留孤儿数据 + activity_log 缺事件。
    被允许的 catch：仅当 impl 已显式记录错误为独立事件并继续抛 AppError 时（M15 sprint 落地后）。

    **签名升级 (M04 sprint R-X5 实证 / 2026-05-07)**：原签名为
    ``(db, node_id, project_id) -> None`` 缺 ``actor_user_id``——但 design §10
    R10-1 batch3 要求 child service 写 per-record ``delete`` activity_log，而
    ``write_event`` 强制 ``actor_user_id`` 字段。M04 是 R-X2 第一真注入方，sprint
    期通过 5 步分层分析法定位为 L1 跨模块契约层缺口（本模块绕都违反 design §10
    或引入全局状态），决策升级 Protocol 加 ``actor_user_id``。M03 delete_node
    已有 ``actor_user_id`` 参数，调用点同步改 4 参。

    **未来契约升级路径 (R2-3 punt 注记)**：当前 Protocol 是单 node 调用。
    M04+ sprint 注入 concrete impl 后，delete_node 子树有 N 节点 × K service = N×K 次单 node 调用，
    深树时是 N+1 风险。子树节点数 >50 时，concrete impl 应升级为支持 batch 形态:
        async def __call__(self, db, node_ids: list[UUID], project_id, actor_user_id) -> None
    并由 M03 delete_node 改为 list_subtree 后单次 batch 调用。当前 M04 注入仍是单
    node 形态——M06/M07 sprint 起或子树节点 >50 性能压力出现时再评估。
    """

    async def __call__(
        self,
        db: AsyncSession,
        node_id: UUID,
        project_id: UUID,
        actor_user_id: UUID,
    ) -> None: ...


_child_services: dict[str, NodeChildrenServiceProtocol] = {}


def register_child_service(target_type: str, service: NodeChildrenServiceProtocol) -> None:
    """M04/M06/M07 sprint 启动时注入 concrete impl。"""
    _child_services[target_type] = service


def clear_child_services() -> None:
    """测试 fixture / 应用关停清空注册表。"""
    _child_services.clear()


def get_child_services() -> dict[str, NodeChildrenServiceProtocol]:
    return dict(_child_services)


# ─────────────── NodeService ───────────────


class NodeService:
    """M03 业务 service。

    职责（design §6）:
      - 节点 CRUD + path 计算
      - 拖拽 reorder + move_subtree（G5 循环检查）
      - delete_node R-X2: 调下游 child_services + 子树 per-node activity_log
      - batch_create_in_transaction (M11/M17 调用接口)
      - get_for_embedding (M18 baseline-patch 被动接口)
      - breadcrumb (面包屑路径)
    """

    def __init__(self, dao: NodeDAO | None = None) -> None:
        self.dao = dao or NodeDAO()

    # ─── 读 ───

    async def list_tree(self, db: AsyncSession, project_id: UUID) -> list[Node]:
        rows = await self.dao.list_by_project(db, project_id)
        return list(rows)

    async def get_node(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> Node:
        node = await self.dao.get_by_id(db, node_id, project_id)
        if node is None:
            raise NodeNotFoundError(node_id=str(node_id))
        return node

    async def get_for_embedding(
        self, db: AsyncSession, node_id: UUID, project_id: UUID
    ) -> str | None:
        """M18 baseline-patch 被动接口（design §6.X A4 A 路径）。

        返回 `name + "\\n" + description`（description=None 时仅返回 name）。
        节点不存在 / 跨租户 → 返回 None（worker 拿到 None = 节点已删，noop 不嵌入）。
        """
        node = await self.dao.get_by_id(db, node_id, project_id)
        if node is None:
            return None
        if node.description:
            return f"{node.name}\n{node.description}"
        return node.name

    async def breadcrumb(self, db: AsyncSession, node_id: UUID, project_id: UUID) -> list[Node]:
        """面包屑：从根到当前节点（含自身）。基于 path 物化路径解析。

        R2-4 修：原 N+1（O(深度) 次 get_by_id）→ 改为一次 list_by_ids IN 查
        （兑现 design §1 "O(1) 面包屑查询" 承诺；O(1) 指 1 次 DB roundtrip）。
        """
        node = await self.get_node(db, node_id, project_id)
        ids = [UUID(seg) for seg in node.path.strip("/").split("/") if seg]
        if not ids:
            return [node]
        rows = await self.dao.list_by_ids(db, ids, project_id)
        result_map = {n.id: n for n in rows}
        return [result_map[nid] for nid in ids if nid in result_map]

    # ─── 写 ───

    async def create_node(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        name: str,
        type: str = NodeType.FOLDER.value,
        parent_id: UUID | None = None,
        sort_order: int | None = None,
        description: str | None = None,
    ) -> Node:
        """事务: INSERT node + path 计算 + activity_log。

        path 公式: parent.path + "/" + new_id + "/"（根节点 parent.path = ""）。
        sort_order 不传则 = max+1。
        """
        parent: Node | None = None
        if parent_id is not None:
            parent = await self.dao.get_by_id(db, parent_id, project_id)
            if parent is None:
                raise NodeParentNotFoundError(parent_id=str(parent_id))

        if sort_order is None:
            current_max = await self.dao.max_sort_order(db, parent_id, project_id)
            sort_order = 0 if current_max is None else current_max + 1

        depth = 0 if parent is None else parent.depth + 1
        # 先 create 拿到 id，再算 path 回填（path 含自身 id）
        node = await self.dao.create(
            db,
            project_id=project_id,
            parent_id=parent_id,
            name=name,
            description=description,
            type=type,
            depth=depth,
            sort_order=sort_order,
            path="",
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        node.path = (parent.path if parent else "/") + f"{node.id}/"
        await db.flush()

        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="node_created",
            target_type="node",
            target_id=str(node.id),
            summary=f"Created node '{name}'",
            metadata={
                "project_id": str(project_id),
                "parent_id": str(parent_id) if parent_id else None,
                "name": name,
                "type": type,
                "depth": depth,
            },
        )
        await db.refresh(node, attribute_names=["created_at", "updated_at"])
        return node

    async def update_node(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        actor_user_id: UUID,
        name: str | None = None,
        description: str | None = None,
        type: str | None = None,  # 仅用于校验拒绝（不允许修改）
    ) -> Node:
        """事务: UPDATE name/description + activity_log。

        type 不可变更（design §4 决策；R4-2 NodeTypeImmutableError）。
        """
        node = await self.get_node(db, node_id, project_id)

        if type is not None and type != node.type:
            raise NodeTypeImmutableError(
                node_id=str(node_id), current_type=node.type, requested_type=type
            )

        old_name = node.name
        changed = []
        if name is not None and name != node.name:
            node.name = name
            changed.append("name")
        if description is not None and description != node.description:
            node.description = description
            changed.append("description")

        # R1-A P-A-01 修：无字段变化时早返回不触 updated_by/updated_at（防"幽灵写"）
        if not changed:
            return node

        node.updated_by = actor_user_id
        await db.flush()
        await db.refresh(node, attribute_names=["updated_at"])
        await write_event(
            db=db,
            actor_user_id=actor_user_id,
            project_id=project_id,
            action_type="node_updated",
            target_type="node",
            target_id=str(node.id),
            summary=f"Updated node '{node.name}'",
            metadata={
                "project_id": str(project_id),
                "old_name": old_name,
                "new_name": node.name,
                "changed_fields": changed,
            },
        )
        return node

    async def delete_node(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        actor_user_id: UUID,
    ) -> None:
        """事务: 子树 list_subtree → 调下游 child_services → DB CASCADE 兜底删 → activity_log。

        R-X2 顺序（design §8）：
          1. for each subtree node: 调 _child_services 注册的所有 service（M04/M06/M07
             各自 delete_by_node_id / orphan_by_node_id 写 activity_log）
          2. DELETE FROM nodes WHERE id = root_node_id（DB ON DELETE CASCADE 兜底）
          3. R10-1 batch3: 子树每个节点写独立 'delete' activity_log
        """
        # 子树（叶 → 根 顺序，便于先清下游 + 写 activity_log）
        subtree = list(await self.dao.list_subtree(db, node_id, project_id))
        if not subtree:
            raise NodeNotFoundError(node_id=str(node_id))
        # 按 depth 降序：先清深节点 → 根节点最后
        subtree.sort(key=lambda n: -n.depth)

        for sub in subtree:
            # R-X2: 调下游 service（M04 sprint 起 dimension impl 注入；signature 升级为 4 参）
            for _target_type, svc in _child_services.items():
                await svc(db, sub.id, project_id, actor_user_id)
            # R10-1 batch3: 每节点独立 delete 事件
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="node_deleted",
                target_type="node",
                target_id=str(sub.id),
                summary=f"Deleted node '{sub.name}'",
                metadata={
                    "project_id": str(project_id),
                    "name": sub.name,
                    "type": sub.type,
                    "depth": sub.depth,
                },
            )

        # DELETE root：DB ON DELETE CASCADE 兜底删整子树
        rc = await self.dao.delete_one(db, node_id, project_id)
        if rc == 0:
            raise NodeNotFoundError(node_id=str(node_id))

    async def reorder_siblings(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        parent_id: UUID | None,
        items: list[tuple[UUID, int]],
    ) -> list[Node]:
        """事务: 验证同 parent + bulk_update_sort_order + 每节点独立 reorder 事件。"""
        if not items:
            return []

        # 验证所有 node_id 同 parent + 同 project
        children = await self.dao.list_children(db, parent_id, project_id)
        valid_ids = {c.id for c in children}
        request_ids = {nid for nid, _ in items}
        if not request_ids.issubset(valid_ids):
            invalid = request_ids - valid_ids
            raise NodeReorderInvalidError(
                parent_id=str(parent_id) if parent_id else None,
                invalid_node_ids=[str(i) for i in invalid],
            )

        # 旧 sort_order 快照（活动日志 metadata 用）
        old_orders = {c.id: c.sort_order for c in children}

        await self.dao.bulk_update_sort_order(db, project_id, parent_id, items)

        for nid, new_so in items:
            # R1-A P-A-02 修：sort_order 实际未变 → 不写 reorder 事件
            # （design §10 R10-1 字面是"被修改"，本期收紧为"实际变化"）
            if old_orders.get(nid) == new_so:
                continue
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="node_reordered",
                target_type="node",
                target_id=str(nid),
                summary="Reordered node",
                metadata={
                    "project_id": str(project_id),
                    "parent_id": str(parent_id) if parent_id else None,
                    "old_sort_order": old_orders.get(nid),
                    "new_sort_order": new_so,
                },
            )

        # 重新读取 children 返回最新 sort_order
        return list(await self.dao.list_children(db, parent_id, project_id))

    async def move_subtree(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        node_id: UUID,
        actor_user_id: UUID,
        new_parent_id: UUID | None,
    ) -> Node:
        """事务: G5 循环检查 + path 子树批量重写 + per-node move 事件。

        循环引用判定：target.path 不能 LIKE source.path || '%'（移到自己子孙下）。
        """
        source = await self.get_node(db, node_id, project_id)

        target_parent: Node | None = None
        if new_parent_id is not None:
            target_parent = await self.dao.get_by_id(db, new_parent_id, project_id)
            if target_parent is None:
                raise NodeParentNotFoundError(parent_id=str(new_parent_id))
            # 循环检查
            if target_parent.path.startswith(source.path):
                raise NodeMoveCycleDetectedError(
                    source_id=str(node_id), target_parent_id=str(new_parent_id)
                )

        # 已是同 parent → noop（design §14 E9 幂等）
        if source.parent_id == new_parent_id:
            return source

        old_path = source.path
        old_depth = source.depth
        new_parent_path = target_parent.path if target_parent else "/"
        new_path = f"{new_parent_path}{source.id}/"
        new_depth = (target_parent.depth + 1) if target_parent else 0
        depth_delta = new_depth - old_depth

        # 子树 path 批量重写 + depth delta（一条 SQL）
        await self.dao.update_paths_in_subtree(db, project_id, old_path, new_path, depth_delta)
        # 更新 source.parent_id（path 已被 update_paths_in_subtree 改）
        source.parent_id = new_parent_id
        source.updated_by = actor_user_id
        await db.flush()
        await db.refresh(source, attribute_names=["path", "depth", "updated_at"])

        # R10-1 batch3：子树每节点独立 move 事件
        moved = await self.dao.list_subtree(db, source.id, project_id)
        for n in moved:
            await write_event(
                db=db,
                actor_user_id=actor_user_id,
                project_id=project_id,
                action_type="node_moved",
                target_type="node",
                target_id=str(n.id),
                summary="Moved node",
                metadata={
                    "project_id": str(project_id),
                    "old_path": old_path if n.id == source.id else None,
                    "new_path": n.path,
                    "old_depth": old_depth if n.id == source.id else None,
                    "new_depth": n.depth,
                    "triggered_by": "move_subtree",
                    "root_node_id": str(source.id),
                },
            )
        return source

    async def batch_create_in_transaction(
        self,
        db: AsyncSession,
        *,
        project_id: UUID,
        actor_user_id: UUID,
        nodes_data: list[dict[str, Any]],
    ) -> list[Node]:
        """M11/M17 调用入口（R-X3 共享外部 session）。

        nodes_data 每条形如 {name, type?, parent_temp_id?, sort_order?, description?}。
        parent_temp_id 是入参临时 ID（用于父子关系拓扑排序）；同批次父先入库后子取真 id。
        """
        # 拓扑排序：根（无 parent_temp_id）先，子按 parent_temp_id 顺序
        # 简化版：单次输入要求 caller 已按层级顺序排好（M11/M17 csv 流程通常已是层序）
        temp_to_real: dict[Any, UUID] = {}
        created: list[Node] = []
        for raw in nodes_data:
            parent_temp = raw.get("parent_temp_id")
            real_parent_id: UUID | None = None
            if parent_temp is not None:
                if parent_temp not in temp_to_real:
                    raise NodeParentNotFoundError(parent_id=f"temp:{parent_temp}")
                real_parent_id = temp_to_real[parent_temp]
            node = await self.create_node(
                db,
                project_id=project_id,
                actor_user_id=actor_user_id,
                name=raw["name"],
                type=raw.get("type", NodeType.FOLDER.value),
                parent_id=real_parent_id,
                sort_order=raw.get("sort_order"),
                description=raw.get("description"),
            )
            if "temp_id" in raw:
                temp_to_real[raw["temp_id"]] = node.id
            created.append(node)
        return created


__all__ = [
    "NodeChildrenServiceProtocol",
    "NodeDAO",
    "NodeService",
    "clear_child_services",
    "get_child_services",
    "register_child_service",
]
