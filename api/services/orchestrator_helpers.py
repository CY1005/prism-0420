"""api.services.orchestrator_helpers — R-X1 orchestrator 横切 helper。

cross-sprint punt #7 + M11 R2 P1-01 立修（2026-05-09 M17 sprint 启动期）：
R-X1 失败补偿 commit boundary 必独立 connection / 禁与业务事务共享 commit。

立规来源：feedback_rx1_orchestrator_design L1 字面 +
design/00-architecture/06-design-principles.md 清单 6（commit boundary 隔离）。

# Scaffold 简化决策（2026-05-09，M17 sprint 启动期 / 闸门 2.6 mini-sprint 同 commit）
# ① 决策内容：抽 compensation_session helper 文件 + 单元测试；M11 ColdStart 暂未迁移
# ② 简化理由：M11 已 674 PASS / 立即迁移引大回归；本期立 helper + design 字面 disambiguation
#    + M17 直接用 helper（首个 caller）；M11 迁移在 M17 sprint 子片 0 prep 内做
# ③ 由 M17 sprint 子片 0 prep 扩齐：M11 ColdStartOrchestratorService._mark_failed +
#    router 期望套路（docstring 字面）迁移到 compensation_session
# ④ 触发回写动作：M17 sprint 子片 0 prep commit 内 M11 service.py + cold_start_router.py
#    迁移；audit/m17 元教训沉淀 R-X1 第二实例 vs 第一实例对照
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.db import SessionLocal


@asynccontextmanager
async def compensation_session() -> AsyncIterator[AsyncSession]:
    """R-X1 orchestrator 失败补偿专用 session（独立 connection / 与业务事务隔离）。

    使用范式（M11 ColdStart / M17 AI 导入复用）：

        try:
            await orchestrate(db, ...)  # 业务 R-X1 跨模块 batch_create_in_transaction
            await db.commit()
        except OrchestrationError as e:
            await db.rollback()  # G6 全量回滚契约：业务 INSERT 全 rollback
            async with compensation_session() as comp_db:
                await dao.mark_failed(comp_db, task_id, error_code=e.code, ...)
                await write_event(comp_db, ..., action_type='*_failed', ...)
                await comp_db.commit()  # 失败补偿独立 commit
            raise

    G6 全量回滚契约（design §1）：

    - 业务 INSERT 路径：commit 失败时全量 rollback（不留部分写入）
    - 失败补偿路径：task=failed + activity_log 走独立 connection commit；
      可见性立即（caller 无须等业务事务）

    与 ai_snapshot_runner.py（M16 §12B BackgroundTasks）范式同构：

    - M16 runner 整体跑在自起 SessionLocal，无业务事务嵌套问题
    - M11/M17 R-X1 主流程跑在请求级 / Queue 业务 session，失败时才需此 helper
      自起独立 session 隔离 commit boundary

    测试 fixture 兼容性（join_transaction_mode='create_savepoint'）：

    - 默认实现走真实 SessionLocal → 独立 connection（生产路径）
    - 测试需 monkeypatch SessionLocal 工厂 → 同 connection 的 session（防
      'create_savepoint' fixture 期间冲突）；改造模式见 tests/test_orchestrator_helpers.py
      + M17 sprint 子片 0 prep 内 conftest fixture 设计

    R-X1 实例对照表（design/audit/m17-pilot-template-validation.md "R-X1 第二实例
    新教训" 段）：

    | 维度 | M11 ColdStart（第一实例） | M17 AI 导入（第二实例） |
    |---|---|---|
    | 形态 | 同步 orchestrator | 异步 Queue orchestrator |
    | session 来源 | 请求级 Depends(get_db) | Queue worker 自起 SessionLocal |
    | 失败补偿 | 本 helper（M17 子片 0 prep 迁移）| 本 helper |
    | 重试 | 不重试，failed 终态 | arq retry + 死信 30d |
    | 接口共享 | batch_create_in_transaction 4 参 | batch_create_in_transaction 4 参 |
    """
    async with SessionLocal() as comp_db:
        yield comp_db


__all__ = ["compensation_session"]
