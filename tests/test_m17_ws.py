"""M17 WebSocket broker 单元测试（不起 FastAPI / 不连真 WS）。

覆盖：
- subscribe / unsubscribe 计数
- publish 多订阅者广播
- queue full 不抛异常（慢消费者丢弃）
- 多 task 互相隔离
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from api.schemas.import_schema import ImportTaskStatusEnum, ProgressEvent
from api.ws.import_progress import _ProgressBroker

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _evt(task_id, status=ImportTaskStatusEnum.pending, progress=0):
    return ProgressEvent(
        type="status_change",
        task_id=task_id,
        progress=progress,
        status=status,
        message="m",
    )


class TestBroker:
    async def test_subscribe_publish_receive(self):
        broker = _ProgressBroker()
        tid = uuid4()
        q = await broker.subscribe(tid)
        await broker.publish(_evt(tid, progress=42))
        evt = await asyncio.wait_for(q.get(), timeout=1.0)
        assert evt.progress == 42
        await broker.unsubscribe(tid, q)

    async def test_two_subscribers_both_receive(self):
        broker = _ProgressBroker()
        tid = uuid4()
        q1 = await broker.subscribe(tid)
        q2 = await broker.subscribe(tid)
        await broker.publish(_evt(tid))
        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e1.task_id == tid
        assert e2.task_id == tid

    async def test_unsubscribe_stops_receiving(self):
        broker = _ProgressBroker()
        tid = uuid4()
        q = await broker.subscribe(tid)
        await broker.unsubscribe(tid, q)
        await broker.publish(_evt(tid))
        # 没人订阅；publish 不抛
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q.get(), timeout=0.1)

    async def test_different_tasks_isolated(self):
        broker = _ProgressBroker()
        t_a = uuid4()
        t_b = uuid4()
        q_a = await broker.subscribe(t_a)
        q_b = await broker.subscribe(t_b)
        await broker.publish(_evt(t_a))
        evt_a = await asyncio.wait_for(q_a.get(), timeout=1.0)
        assert evt_a.task_id == t_a
        # b 队列空
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(q_b.get(), timeout=0.1)

    async def test_queue_full_does_not_raise(self):
        broker = _ProgressBroker()
        tid = uuid4()
        q = await broker.subscribe(tid)
        # 灌满 maxsize=128
        for _ in range(200):
            await broker.publish(_evt(tid))
        # 应该没抛；后续仍可发
        await broker.publish(_evt(tid, progress=99))
        # q 内至少有 1 条
        evt = await asyncio.wait_for(q.get(), timeout=1.0)
        assert evt is not None
