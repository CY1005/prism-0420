"""activity_log 写入封装（horizontal）。

# horizontal: 是
# owner: M15（design/02-modules/M15-activity-stream/00-design.md，R10-2 主规则下 own）
# 位置: api/services/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 全模块共用 write_event 接口（M02-M19 业务 service 都调本 helper 写 activity_log）

设计来源：design/02-modules/M15-activity-stream/00-design.md（M15 是 activity_log 横切表 owner）
+ design/00-roadmap.md §5.2 B7。

本期（B2.3 stub）：write_event 仅写 structlog JSON，不插库。M15 实装时将
ActivityLog model + Alembic 迁移落地后，把本函数体替换为真实 INSERT，调用方接口不变。

调用契约（M02/M03/M04/... Service 层使用）：
    await write_event(
        db=session,                       # AsyncSession（M15 实装后才真消费；当前忽略）
        actor_user_id=current_user.id,
        project_id=ctx.project_id,        # 业务模块必传；**全局豁免模块（如 M14）传 None**
        action_type="create",             # 必须在 M15 ActionType 枚举内
        target_type="module",             # 必须在 M15 TargetType 枚举内
        target_id=str(new_module.id),
        summary=f"创建了节点『{new_module.name}』",
        metadata={"k": "v"},              # 可选；JSONB 字段
    )

# Scaffold 简化决策（2026-05-08，M14 sprint 启动）
# ① 决策内容：project_id 类型从 UUID 升级为 UUID | None；None 序列化为字符串 "global"
# ② 简化理由：M14 是首个全局豁免业务模块（design §9 + 06-design-principles 清单 5），
#    无 project_id 概念；prior M02-M13 全模块均强 project_id；此前签名 UUID 强制。
# ③ 由 M15 sprint 扩齐：M15 实装 ActivityLog model 时把"project_id 全局事件"
#    定义为 NULLABLE 列 + UI 时间线为"全局事件"分组；ActionType 枚举新增对应 M14 类型
# ④ 触发回写动作：M15 Alembic add column NULLABLE + ActionType +5（create/update/delete/link/unlink news）
"""

from typing import Any
from uuid import UUID

from api.core.logging import log


async def write_event(
    *,
    db: Any,  # AsyncSession — M15 实装时启用
    actor_user_id: UUID,
    project_id: UUID | None,
    action_type: str,
    target_type: str,
    target_id: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """写一条 activity_log 事件（M15 横切表）。

    B2.3 stub：仅打 structlog JSON。M15 实装时改为真实 DB INSERT。
    调用方代码无需任何改动（接口稳定）。

    project_id=None：M14 等全局豁免业务模块用；structlog 序列化为 "global" 字面，
    便于 M15 实装后区分项目级 vs 全局事件（详见 docstring scaffold 决策段）。
    """
    log.info(
        "activity.event",
        actor_user_id=str(actor_user_id),
        project_id=str(project_id) if project_id is not None else "global",
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        metadata=metadata,
        impl="stub",
    )
