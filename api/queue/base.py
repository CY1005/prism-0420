"""api.queue.base — Queue/Cron 系统任务边界基础。

闸门 2.6 mini-sprint scaffold：M16 sprint 子片 3 落地 SYSTEM_USER_UUID（M16
zombie cron + cleanup cron 用 / cron user_id 边界 ADR-002 §1.1）。
TaskPayload 基类（user_id + project_id 强制）由 M17 sprint 落地（首个 arq Queue
消费者；闸门 2.6 完整 mini-sprint 同 commit）。

# Scaffold 简化决策（2026-05-09，M16 sprint 子片 3）
# ① 决策内容：仅落 SYSTEM_USER_UUID 常量；TaskPayload 基类不在本期实装
# ② 简化理由：M16 选 BackgroundTasks 不走 arq Queue（design §6.5 字面）；
#    SYSTEM_USER_UUID 常量是 cron user_id 边界唯一刚性需求
# ③ 由 M17 sprint 扩齐：TaskPayload + arq Queue 配置 + worker 部署
# ④ 触发回写动作：M17 sprint 启动闸门 2.6 mini-sprint commit 内补完
"""

from uuid import UUID

# 系统任务专用 user_id（cron / Queue 触发 / 等系统操作）。
# 任何在 nodes / projects 表外的"代表系统"的 activity_log 行必须落此 UUID（ADR-002 §1.1）。
# 前端 next-intl 在 user_id == SYSTEM_USER_UUID 时显示 i18n key activity.actor.system "系统"。
# 该 UUID 是 RFC 4122 v4 随机但固定字面（不与任何真 user.id 撞，只在 activity_log 出现）。
SYSTEM_USER_UUID: UUID = UUID("00000000-0000-0000-0000-00000000fe00")


__all__ = ["SYSTEM_USER_UUID"]
