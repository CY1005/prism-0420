"""api.queue.base — Queue/Cron 系统任务边界基础。

闸门 2.6 mini-sprint 完整落地（2026-05-09 M17 sprint 启动期）：
- SYSTEM_USER_UUID 常量（M16 sprint 子片 3 已落 / cron user_id 边界 ADR-002 §1.1）
- TaskPayload 基类（M17 sprint 启动期落 / 首个 arq Queue 消费者使用）
- M17 业务子类（ImportExtractPayload / ImportAIStepPayload / ImportBatchInsertPayload）
  在 M17 sprint 子片 3 落（design §12 字面）

ADR-002 §1.1：cron / 系统任务 / Queue 触发的 activity_log.user_id 必须落
SYSTEM_USER_UUID（禁用真实 user.id 或 NULL）。
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

# 系统任务专用 user_id（cron / Queue 触发 / 等系统操作）。
# 任何在 nodes / projects 表外的"代表系统"的 activity_log 行必须落此 UUID（ADR-002 §1.1）。
# 前端 next-intl 在 user_id == SYSTEM_USER_UUID 时显示 i18n key activity.actor.system "系统"。
# 该 UUID 是 RFC 4122 v4 随机但固定字面（不与任何真 user.id 撞，只在 activity_log 出现）。
SYSTEM_USER_UUID: UUID = UUID("00000000-0000-0000-0000-00000000fe00")


class TaskPayload(BaseModel):
    """所有 arq Queue task payload 必须继承——强制带 user_id + project_id。

    多人架构清单 3（异步任务 payload 必须带 user_id + project_id）的实施载体；
    Queue 消费者入口校验：

        async def import_extract(ctx, raw: dict):
            payload = ImportExtractPayload.model_validate(raw)  # 强制校验
            await service.check_access(payload.user_id, payload.project_id, payload.task_id)
            ...

    extra='forbid' 防上游漂移（多打字段 / 拼错字段名静默丢失）。
    """

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    """触发任务的 user_id；cron / 系统任务必须用 SYSTEM_USER_UUID。"""

    project_id: UUID
    """租户隔离字段；Queue 消费者必须用 payload.project_id 校验访问权。"""


__all__ = ["SYSTEM_USER_UUID", "TaskPayload"]
