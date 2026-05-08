"""api.queue 命名空间。

闸门 2.6 mini-sprint 完整落地（2026-05-09 M17 sprint 启动期）：
- SYSTEM_USER_UUID（M16 sprint 子片 3 落）
- TaskPayload 基类（M17 sprint 启动期落 / 首个 arq Queue 消费者）

ADR-002 §1.1：cron / 系统任务 / Queue 触发的 activity_log.user_id 必须落
SYSTEM_USER_UUID（禁用真实 user.id 或 NULL）。
"""

from api.queue.base import SYSTEM_USER_UUID, TaskPayload

__all__ = ["SYSTEM_USER_UUID", "TaskPayload"]
