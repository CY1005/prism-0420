"""api.queue 命名空间。

闸门 2.6 mini-sprint：M16 sprint 子片 3（2026-05-09）落地 SYSTEM_USER_UUID 占位常量。
TaskPayload 基类等到 M17 sprint（首个 arq Queue 消费者）实装。

ADR-002 §1.1：cron / 系统任务 / Queue 触发的 activity_log.user_id 必须落
SYSTEM_USER_UUID（禁用真实 user.id 或 NULL）。
"""

from api.queue.base import SYSTEM_USER_UUID

__all__ = ["SYSTEM_USER_UUID"]
