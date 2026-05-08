"""M17 AI 导入 WebSocket handler（design §6 + §7 + §8 / audit B6 修复）。

横切目录归属（design §6）：业务 owner=M17，位置 api/ws/ 横切目录。

权限三层（design §8）：
- 握手时校验 task_id 归属当前 user（ImportService.check_task_access 第三层）
  + project membership ≥ viewer（FastAPI 路由层 check_project_access 已拦截）
- 每 ClientCommand 入口重校 command.task_id == 握手 task_id（audit B6 修复 / 防同
  连接 cancel 任意 task）
- close code 1008 = policy violation（不通过权限）；4400 = 业务错（task 已终态）

服务器 → 客户端事件（design §7）：
- progress_update / status_change / review_ready / completed / error

客户端 → 服务器命令（design §7）：
- cancel（触发 ImportService.cancel_task）
- ping（保活，回 pong）
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from fastapi import status as ws_status
from pydantic import ValidationError as PydanticValidationError

from api.schemas.import_schema import ClientCommand, ProgressEvent

log = logging.getLogger(__name__)


# ─────────────── 进程内 broker（M17 sprint scaffold；后续 sprint 切换到 Redis pub/sub）───────────────


class _ProgressBroker:
    """task_id → 多个 connected WebSocket 的进程内广播。

    M17 sprint 范围：单进程 broker（同一 worker 进程内 service push 与 ws handler 互通）。
    生产部署多 worker 时由 Redis pub/sub 替换（design §6 列在 future-work 待落地子片）。
    """

    def __init__(self) -> None:
        self._subscribers: dict[UUID, set[asyncio.Queue[ProgressEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, task_id: UUID) -> asyncio.Queue[ProgressEvent]:
        q: asyncio.Queue[ProgressEvent] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._subscribers[task_id].add(q)
        return q

    async def unsubscribe(self, task_id: UUID, q: asyncio.Queue[ProgressEvent]) -> None:
        async with self._lock:
            subs = self._subscribers.get(task_id)
            if subs is not None:
                subs.discard(q)
                if not subs:
                    self._subscribers.pop(task_id, None)

    async def publish(self, event: ProgressEvent) -> None:
        """Service 层 push 进度事件入口；广播给所有订阅 task_id 的 ws 连接。"""
        async with self._lock:
            subs = list(self._subscribers.get(event.task_id, set()))
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # 慢消费者丢弃；下一帧 progress_update 仍能拿到最新状态
                log.warning("import_ws: subscriber queue full task=%s; drop event", event.task_id)


_broker = _ProgressBroker()


def get_broker() -> _ProgressBroker:
    """testable hook；service 层通过 publish_progress() 调用。"""
    return _broker


@asynccontextmanager
async def _subscribe(task_id: UUID) -> AsyncIterator[asyncio.Queue[ProgressEvent]]:
    q = await _broker.subscribe(task_id)
    try:
        yield q
    finally:
        await _broker.unsubscribe(task_id, q)


async def publish_progress(event: ProgressEvent) -> None:
    """Service 层调用入口（import_service.py 在状态扭转时调）。"""
    await _broker.publish(event)


# ─────────────── handler 主循环 ───────────────


async def handle_import_progress_ws(
    websocket: WebSocket,
    *,
    task_id: UUID,
    handshake_user_id: UUID,
    handshake_project_id: UUID,
) -> None:
    """WebSocket 主循环（router 层完成 accept 之前的握手校验后调入）。

    Args:
        websocket: 已 accept 的 WebSocket
        task_id: URL path 中的 task_id（router 层已校验归属 user）
        handshake_user_id: 握手时认证的 user.id
        handshake_project_id: URL path 中的 project_id（confirm/cancel 转发用）

    流程：
    1) subscribe broker(task_id)
    2) 并行：① 从 broker queue 取事件推给客户端 ② 接收客户端 ClientCommand 转发处理
    3) WebSocketDisconnect / cancel 命令成功 → 退出循环
    """
    async with _subscribe(task_id) as q:
        recv_task = asyncio.create_task(
            _recv_loop(websocket, task_id, handshake_user_id, handshake_project_id)
        )
        send_task = asyncio.create_task(_send_loop(websocket, q))
        try:
            done, pending = await asyncio.wait(
                {recv_task, send_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception()
                if exc is not None and not isinstance(exc, WebSocketDisconnect):
                    log.exception("import_ws task=%s loop error", task_id, exc_info=exc)
        finally:
            for t in (recv_task, send_task):
                if not t.done():
                    t.cancel()


async def _send_loop(websocket: WebSocket, q: asyncio.Queue[ProgressEvent]) -> None:
    """从 broker 取事件，序列化 JSON 推给客户端。"""
    while True:
        event = await q.get()
        await websocket.send_json(event.model_dump(mode="json"))
        if event.type in ("completed", "error"):
            # 终态事件后保持连接打开 1s 让客户端读完，然后 server 主动关
            await asyncio.sleep(1.0)
            await websocket.close(code=ws_status.WS_1000_NORMAL_CLOSURE)
            return


async def _recv_loop(websocket: WebSocket, task_id: UUID, user_id: UUID, project_id: UUID) -> None:
    """接收 ClientCommand 并处理（cancel / ping / 不认识的丢弃）。"""
    from api.core.db import SessionLocal
    from api.services.import_service import ImportService

    while True:
        try:
            raw: dict[str, Any] = await websocket.receive_json()
        except WebSocketDisconnect:
            return
        try:
            cmd = ClientCommand.model_validate(raw)
        except PydanticValidationError as e:
            log.info("import_ws task=%s invalid command: %s", task_id, e)
            continue

        # audit B6 修复：每命令 task_id 重校
        if cmd.task_id != task_id:
            log.warning(
                "import_ws task=%s cross-task command rejected (cmd.task_id=%s)",
                task_id,
                cmd.task_id,
            )
            await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
            return

        if cmd.type == "ping":
            await websocket.send_json({"type": "pong", "task_id": str(task_id)})
            continue

        if cmd.type == "cancel":
            service = ImportService()
            async with SessionLocal() as db:
                try:
                    await service.cancel_task(
                        db,
                        user_id=user_id,
                        project_id=project_id,
                        task_id=task_id,
                    )
                    await db.commit()
                    await websocket.send_json(
                        {"type": "ack", "task_id": str(task_id), "command": "cancel"}
                    )
                except Exception:
                    log.exception("import_ws task=%s cancel failed", task_id)
                    await websocket.send_json(
                        {"type": "error", "task_id": str(task_id), "command": "cancel"}
                    )
            return  # cancel 命令处理完关闭连接


__all__ = [
    "get_broker",
    "handle_import_progress_ws",
    "publish_progress",
]
