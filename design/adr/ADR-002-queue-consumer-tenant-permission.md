---
title: ADR-002 Queue 消费者侧 tenant + permission 标准
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
supersedes: []
superseded_by: null
last_reviewed_at: 2026-04-21
related_modules: [M13, M16, M17, M18]
---

# ADR-002：Queue 消费者侧 tenant 隔离 + 二次权限校验标准

## Context（背景）

prism-0420 多个模块涉及异步任务（M13 流式 / M16 后台 / M17 Queue / M18 Queue 嵌入），异步路径**不经过 HTTP Router**——若仅依赖 Router 层权限，Queue 消费者会出现"接到任意 user_id 的 payload 即执行"的越权风险。

**实战发现**（来自 M17 pilot 三轮 audit）：
- M17 §8 单独写"Queue 消费者侧权限"段，描述了 `TaskPayload 基类强制 user_id + project_id + Queue 消费者入口校验` 模式
- 但同样的设计要求 M18 / M13 / M16 都需要——若每模块各自重写，未来必然产生漂移
- `04-layer-architecture.md §Q4` 已写过"异步路径权限绕过"教育性段落，但未形成可引用的标准

**痛点**：横切决策散落在多模块文档，没有锚点。

---

## Decision（决策）

**横切标准**：所有异步模块（🌊 流式 / 🪷 后台 / 🗂️ Queue 三种 emoji 标注）必须按本 ADR 的"Queue 消费者侧 tenant + 权限"标准实现。

### 核心 4 项

#### 1. TaskPayload 基类强制 tenant 字段

`api/queue/base.py` 定义全局基类：

```python
from pydantic import BaseModel
from uuid import UUID

class TaskPayload(BaseModel):
    """所有 Queue/异步 task payload 必须继承——强制带 user_id + project_id"""
    user_id: UUID
    project_id: UUID
    idempotency_key: str | None = None
```

每个异步模块的 payload 必须继承：

```python
class ImportExtractPayload(TaskPayload):    # 继承基类
    task_id: UUID
    source_type: ImportSourceType
```

**检查**：CI 静态扫描所有 `queue/tasks/*.py` 中 `@task` 装饰函数的入参类型必须是 `TaskPayload` 子类。

#### 2. Queue 消费者入口 3 步校验

每个异步 task 函数体的**前 3 行**：

```python
async def import_extract(ctx, raw_payload: dict):
    payload = ImportExtractPayload.parse_obj(raw_payload)        # ① Pydantic 校验
    service = get_import_service(ctx)
    service.check_access(payload.user_id, payload.project_id, payload.task_id)  # ② 二次权限
    # ③ 业务逻辑
    await service.extract(payload.task_id)
```

**禁止跳过任一步**——绕过校验 = 同 SQL 注入级别风险（跨租户数据访问）。

#### 3. idempotency key 必含 project_id

异步任务的 idempotency key 设计**必须包含 project_id**：

✅ 正确：`(user_id, project_id, source_hash)`
❌ 错误：`(user_id, source_hash)`——同 user 跨项目会命中错 task（M17 audit B1 教训）

**检查**：每个异步模块 §11 idempotency_key 章节必须显式回答"project_id 是否参与 key 计算"。

#### 4. WebSocket 异步反馈：每命令重校 task_id

含 WebSocket 进度推送的异步模块（如 M17）：
- WS 握手时校验 URL path 中 task_id 归属 user
- **每个 ClientCommand 处理函数第一行**重校 `command.task_id == handshake_task_id`
- 防同连接的 cancel/操作命令带任意 task_id 绕过鉴权

```python
async def handle_client_command(self, command: ClientCommand):
    assert command.task_id == self.handshake_task_id, \
        "task_id mismatch with handshake"
    if command.type == "cancel":
        await self.service.cancel(command.task_id, self.user_id)
```

---

## Consequences（后果）

### 正面

- **异步模块横切一致**：M13 / M16 / M17 / M18 都遵循同一标准
- **CI 可扫描**：基类 + 入参类型 + idempotency 文档要求都可静态校验
- **AI 实现时无歧义**：新异步模块的设计文档 §8 引本 ADR 即可，不重复描述
- **跨租户安全兜底**：3 项检查任一项防漏，避免单点失效

### 负面

- 每个异步模块都要写 `__init__` 调 base 校验代码（boilerplate）—— 接受
- TaskPayload 基类的 user_id/project_id 字段对"系统级任务"（无 user 上下文，如 cron 清理任务）显得多余——通过显式 `system_user_id = UUID('00000000-...')` 解决，并在 ADR 备注

### 横切影响

- M13（流式 SSE）：M13 pilot 已结论（2026-04-25 accepted）——流式鉴权走 ADR-004 P1（浏览器 fetch + Authorization Bearer JWT 直连 FastAPI），本 ADR 不覆盖；流式无客户端→服务器命令通道，连接级 auth 已覆盖，无 chunk 级鉴权需求。参见 [M13-requirement-analysis/00-design.md §8](../02-modules/M13-requirement-analysis/00-design.md)
- M16（后台 fire-and-forget）：M16 pilot 已结论（2026-04-25 accepted）—— **不**走 arq Queue，用 FastAPI BackgroundTasks 同进程异步；本 ADR 不覆盖。决策依据：失败代价低（Q5 ack A 用户手动重发）+ 引入成本零；**反悔触发器**：zombie 率 ≥1% / 单次 AI 成本 ≥$0.5 → 迁移到 arq（迁移成本 ~50 行 + Redis worker）。详见 [M16-ai-snapshot/00-design.md §6 BackgroundTasks vs arq 边界](../02-modules/M16-ai-snapshot/00-design.md)
- M18（Queue 嵌入）：完全适用本 ADR

---

## Alternatives（备选方案）

### A. 不抽 ADR，每模块各自写

- 优势：每模块文档自洽
- 劣势：M17 / M18 / M13 / M16 4 处描述必然漂移
- **拒绝理由**：违反"单一真相源"（规约 11.2）

### B. 写到 06-design-principles.md 清单 3 里

- 优势：复用现有清单结构
- 劣势：清单 3 当前只有"Queue payload 必须带 user_id + project_id"一句话，扩展为完整 4 项会冲淡其他清单
- **拒绝理由**：信息密度失衡

### C. 起独立 ADR（采纳）

- 优势：横切决策有独立锚点；引用清晰；未来扩展空间大
- 劣势：增加一个文档
- **采纳理由**：符合 ADR 的"重大架构决策独立记录"定位

---

## 引用方

- `design/02-modules/M17-ai-import/00-design.md` §8 / §11 / §12 引本 ADR
- `design/02-modules/M18-semantic-search/00-design.md`（待开）引本 ADR
- `design/02-modules/M13-requirement-analysis/00-design.md`（待开）选择性引本 ADR（流式部分扩展）
- `design/02-modules/M16-ai-snapshot/00-design.md`（待开）引本 ADR

## 关联

- `design/00-architecture/04-layer-architecture.md` Q4（教育性背景）
- `design/00-architecture/06-design-principles.md` 清单 3（基础约束）
- `design/02-modules/README.md` §8 R8-2 / §11 R11-2 / §12 异步形态分支表
- `design/02-modules/M17-ai-import/audit-report.md` R3-02（推动本 ADR 起的发现）
