"""activity_log 写入封装（horizontal）。

# horizontal: 是
# owner: M15（design/02-modules/M15-activity-stream/00-design.md，R10-2 主规则下 own）
# 位置: api/services/（横切层，对齐原则 6 + R-X6 + 04-layer Q7）
# 范畴: 全模块共用 write_event 接口（M02-M19 业务 service 都调本 helper 写 activity_log）

设计来源：design/02-modules/M15-activity-stream/00-design.md（M15 是 activity_log 横切表 owner）
+ design/00-roadmap.md §5.2 B7。

实装：M16 sprint 子片 0.5 L1+L3 batch（2026-05-08）— 由 B2.3 stub 升级为真实 DB INSERT。
M15 sprint 已落 ActivityLog model + Alembic 迁移；本 commit 把 write_event 真接通。
caller 接口稳定不变（M02-M14 七模块零改动）。

调用契约（M02/M03/M04/... Service 层使用）：
    await write_event(
        db=session,                       # AsyncSession（必传，本期真消费）
        actor_user_id=current_user.id,
        project_id=ctx.project_id,        # 业务模块必传；**全局豁免模块（如 M14）传 None**
        action_type="node_created",       # ★ R14（M16 sprint 立）：必须用 _ACTION_TYPES 枚举值字面
                                          # （过去式 + snake_case），禁用裸 "create"/"update"/"delete"/"snapshot.x"。
                                          # ci-lint.sh R14 grep 守护。详见 M15 design §10 R14 段。
        target_type="node",               # 必须在 _TARGET_TYPES 枚举内（snake_case 单数形）
        target_id=str(new_node.id),
        summary=f"创建了节点『{new_node.name}』",
        metadata={"k": "v"},              # 可选；JSONB 字段（写入 ActivityLog.event_metadata 列名 "metadata"）
    )

事务边界：write_event 走 `db.add()` + `db.flush()`，**不 commit**——加入 caller 事务，
caller commit 时一并落库；caller rollback 时 activity_log 行也回滚（业务-审计原子性）。
异常传播：CHECK constraint 违反 / FK 违反 → IntegrityError 抛回 caller（M04+ 范式
e2e 必走异常传播测试）。

# Scaffold 简化决策（2026-05-08，M14 sprint 启动；M16 sprint 子片 0.5 batch 实装关闸）
# ① 决策内容：project_id 类型从 UUID 升级为 UUID | None；None 写入 NULL（M14 全局豁免）
# ② 简化理由：M14 是首个全局豁免业务模块（design §9 + 06-design-principles 清单 5），
#    无 project_id 概念；prior M02-M13 全模块均强 project_id。
# ③ 已扩齐（M15 sprint）：ActivityLog.project_id NULLABLE column + UI 时间线"全局事件"分组
# ④ 已扩齐（M15 sprint）：Alembic add column NULLABLE + ActionType +5（news_*）
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.logging import log
from api.models.activity_log import ActivityLog


async def write_event(
    *,
    db: AsyncSession,
    actor_user_id: UUID,
    project_id: UUID | None,
    action_type: str,
    target_type: str,
    target_id: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """写一条 activity_log 事件（M15 横切表 / R10-2 owner）。

    M16 sprint 子片 0.5 实装：真 DB INSERT 接通；走 db.add + db.flush，
    不 commit（加入 caller 事务，caller commit/rollback 决定落库）。

    project_id=None：M14 等全局豁免业务模块用；写入 NULL（UI 时间线"全局事件"分组）。
    structlog 仍同步打 observability 日志（便于运行时 grep + 异步 trace），
    impl 字段从 "stub" 升级为 "db"。
    """
    ev = ActivityLog(
        id=uuid4(),
        project_id=project_id,
        user_id=actor_user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        event_metadata=metadata,  # Python 属性 event_metadata → SQL 列名 "metadata"
    )
    db.add(ev)
    await db.flush()  # 触发 CHECK constraint / FK 校验，IntegrityError 立刻抛回 caller

    log.info(
        "activity.event",
        actor_user_id=str(actor_user_id),
        project_id=str(project_id) if project_id is not None else "global",
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        summary=summary,
        metadata=metadata,
        impl="db",
    )
