---
title: Scaffold ↔ Design 对齐缺口审计
status: draft
owner: CY
created: 2026-05-05
trigger: M01 实施前 D1 决策（AuthServiceProtocol 1 法 vs ADR-004 4 法）暴露 scaffold/ADR 真空带，全面排查
---

# Scaffold ↔ Design 对齐缺口审计

## 背景

Phase 2.0 工程基线（B1-B10）2026-05-05 收官 100%，14 commit / 27 pytest passed。M01 实施前首次系统性对照 scaffold 实际代码 vs 上游 design（ADR / engineering-spec / module README / 各模块 design），发现 **7 处 scaffold 与 design 不一致 / 真空带**。

**根因模式**：scaffold 阶段（B 项）做工程简化决策时，**没有强制机制要求把简化决策回写到对应 design 文档**，导致 design 说一种话、scaffold 代码说另一种话，下一个模块实施时只能猜。

---

## 7 处 Seam 清单

### 🔴 S1 — AuthServiceProtocol 接口形态不一致

**Design 真相**（ADR-004 § 1）：

```python
class AuthService:
    def resolve_from_bearer(...)     # P1
    def resolve_from_internal(...)   # P2
    def resolve_from_refresh(...)    # P3
    def resolve_from_one_time(...)   # P4 预留
```

**Scaffold 真相**（`api/auth/dependencies.py:11-17`）：

```python
class AuthServiceProtocol(Protocol):
    """本期 B2 仅冻结接口，concrete 实现归 M01。set_auth_service() 注入。"""
    async def get_user_by_id(self, user_id: UUID) -> Any | None: ...
```

scaffold 仅 1 法，且 P1（decode_jwt）+ P2（verify_internal_signature）的解码**直接 inline 写在 require_user 函数体**。

**冲突**：ADR 设计 4 法横切门面、scaffold 简化为 1 法 + inline 解码，**两边都标 accepted**，无 disambiguation 注释。

**Reconcile 选项**（M01 D1 决策点）：
- A 守 scaffold + ADR 加注释（最小工作量）
- B 扩 Protocol 加 4 法但不调（有死代码）
- C 改 require_user 全调 4 法（撞"M01 不重写 horizontal helper"红线）

**状态**：M01 实施前必拍。

---

### 🔴 S4 — ErrorCode 数 ≠ AppError 子类数（违反 R13-1）

**Design 真相**（02-modules/README.md § 13 R13-1）：每个 ErrorCode 必有对应 AppError 子类（M17 教训）。M01 § 9 末有 CI grep 守护脚本。

**Scaffold 真相**：

```python
# api/errors/codes.py — 9 个 ErrorCode
INTERNAL_ERROR / NOT_FOUND / PERMISSION_DENIED / VALIDATION_ERROR / CONFLICT
RATE_LIMITED / UNAUTHENTICATED / TOKEN_EXPIRED / LOGIN_LOCKED

# api/errors/exceptions.py — 7 个 AppError 子类
NotFoundError / PermissionDeniedError / ValidationError / ConflictError
UnauthenticatedError / RateLimitedError(+ AppError 基类)
```

**缺**：`TokenExpiredError` / `LoginLockedError` 两个子类未建。

**冲突**：scaffold B5 commit 时漏写 2 个子类。M01 § 9 CI grep 一跑就红。

**Reconcile**：M01.1 实施时**强制**补两个子类，并把 R13-1 的 CI grep 脚本提前到 M01.1 commit 内（不等 M01.10 router 才上）。

---

### 🔴 S5 — `api/queue/base.py` TaskPayload 基类未建

**Design 真相**：
- `engineering-spec § (line 70)`: `api/queue/base.py # TaskPayload 基类（强制 user_id + project_id）`
- `ADR-002 § 1`: 完整定义 TaskPayload 形态
- `M17 § 6`：依赖 `api/queue/base.py:TaskPayload` 子类化

**Scaffold 真相**：`api/queue/` 目录**不存在**。Phase 2.0 phase-gate B1-B10 没单列 queue scaffold（B1.2 docker-compose 含 redis7 但仅 infra，无 Python queue 抽象）。

**冲突**：M17 实施时会**找不到基类**——要么 M17 自己建 `api/queue/base.py`（违反 horizontal owner 边界），要么前置补 scaffold。M01 不直接受影响（M01 无 Queue 任务）。

**Reconcile**：
- 短期：M01 sprint 内不动（M01 不依赖）
- 中期：M17 实施前**必须**先做"queue scaffold mini-sprint"建 `api/queue/base.py:TaskPayload` + `api/queue/__init__.py`；登记到 phase-gate 闸门 3
- 立即动作：phase-gate 添加"M17 前置 queue scaffold"checkbox

---

### 🔴 S6 — TimestampMixin / ImmutableMixin / SoftDeleteMixin **无人定义**

**Design 真相**：
- M01 § 3 SQLAlchemy class 直接用 `class User(Base, TimestampMixin):`
- engineering-spec § (line 64): `base.py # Base + 通用字段（id/created_at/updated_at/version）`——**注**：spec 描述是"基类含通用字段"形态，**不是** Mixin 形态
- 各业务模块 design 隐含使用 `TimestampMixin`（Mapped 注解 created_at/updated_at）

**Scaffold 真相**（`api/models/base.py`）：

```python
class Base(DeclarativeBase):
    pass

# 注释：Mixin（TimestampMixin / ImmutableMixin / SoftDeleteMixin）由 M01 实装时按
# engineering-spec §3 增量加入。本期 B9 仅落基础 Base 让 fixture + dummy 表可用。
```

**双重冲突**：
1. scaffold 注释引用"engineering-spec § 3"——但 engineering-spec 没有"§ 3 Mixin 定义"段落，spec 描述的是 Base 含字段形态而非 Mixin 形态
2. M01 design 直接 import `TimestampMixin`——但**没有任何 design 文档定义 TimestampMixin 的具体字段**

**Reconcile**：M01.2（models + migration）**第一件事**：

```python
# api/models/base.py
from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

class ImmutableMixin:
    """禁止 update（用于 audit log 等只 INSERT 表）"""
    # 实装方式：__mapper_args__ = {'confirm_deleted_rows': False} 或 listen-event 拦 update

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**回写 design**：M01 accepted 后，把 Mixin 定义补到 engineering-spec § 3 或新增 § 3.1，建立"Base + Mixin"形态作为 schema 规约。

---

### 🟡 S3 — ErrorCode 命名漂移

**Design 真相**（M01 § 13）：
- `ACCOUNT_LOCKED`（账号锁，failed_login_count 达 5 触发）
- `REFRESH_TOKEN_EXPIRED`（refresh token 过期）
- `INVALID_REFRESH_TOKEN`（refresh token 非法）

**Scaffold 真相**（`api/errors/codes.py`）：
- `LOGIN_LOCKED`
- `TOKEN_EXPIRED`（含义模糊：access 还是 refresh？）

**冲突**：scaffold 沿用 engineering-spec § 7.2 旧命名（含 LOGIN_LOCKED / TOKEN_EXPIRED）；M01 design 重命名为更精确的 ACCOUNT_LOCKED / REFRESH_TOKEN_EXPIRED 但**没回写 engineering-spec**。

**Reconcile**：M01.1 实施时**直接重命名** scaffold 那两个 code（删 LOGIN_LOCKED → ACCOUNT_LOCKED，删 TOKEN_EXPIRED → REFRESH_TOKEN_EXPIRED + 新增 ACCESS_TOKEN_EXPIRED 区分），并同步改 engineering-spec § 7.2 表 + 影响的现有 scaffold tests（test_errors.py 若 hardcode 这两名字）。

---

### 🟡 S7 — engineering-spec § 7.2 注释用旧模块编号

**Design 真相**（current 05-module-catalog）：M01 = 用户账号 / M03 = 模块树。

**Scaffold/Design 真相**：engineering-spec § 7.2 line 765-767：

```python
# 模块（M01）           ← 旧编号，应为 M03
MODULE_NOT_FOUND = "MODULE_NOT_FOUND"
MODULE_ARCHIVED = "MODULE_ARCHIVED"
```

**冲突**：engineering-spec 写于早期，当时 M01 = 模块；后续 module-catalog 改 M01 = 用户。spec 注释未同步。

**Reconcile**：M01.1 commit 时顺手改 engineering-spec § 7.2 注释 `# 模块（M01）` → `# 模块（M03）`。轻度文字。

---

### 🟢 S2 — TenantContextProtocol（已自我消解，无需额外处理）

**Scaffold 真相**：`api/auth/tenant_filter.py` 含 1 个方法 + **22 行 docstring**：

> 本期（B2.4 scaffold）：表 project_members / projects / team_members 由 M02/M20 owns，尚未落地。helper 定义 Protocol + set_tenant_context 注入点；**M02 上线时注入"仅 project_members"实现，M20 上线时注入 UNION 实现**。

**判定**：scaffold 注释**已经清楚指明 M02 / M20 各自补什么形态**，TODO 显式可见——这是 S1 的反例：S2 做对了"过渡说明回写"，所以无 reconcile 缺口。

**可作为模板**：未来 scaffold 简化决策都按 S2 写法（注释里点名"哪个模块负责什么形态"）。

---

## 根因 + 防御机制

### 根因模式

| 阶段 | 应该做的 | S1/S4/S5/S6/S3/S7 实际做的 |
|-----|---------|---------------------------|
| 1. design accepted | ADR / engineering-spec / 模块 design 写定 | ✅ 都做了 |
| 2. scaffold 实施时遇阻 | 选简化方案 | ✅ 都做了 |
| 3. **回写 design 或在 scaffold 留 TODO** | 注释 / ADR 加 disambiguation / 留 reconcile checkbox | ❌ **6/7 漏做**（仅 S2 做对）|
| 4. 后续模块实施 | 读 design 对齐 scaffold | ❌ 发现两边不一致，只能猜 |

### 防御机制建议（写入 phase-gate）

加一道闸门检查：**任何 scaffold B 项 commit 前**，作者必须自检：

- [ ] 我的实装和上游 design（ADR / engineering-spec / 引用模块 design）**完全对齐**？
- [ ] 如果不对齐，我已经在 **scaffold 注释** OR **对应 design 文档** 里写明"这是简化决策，X 模块实施时扩齐到 Y 形态"？
- [ ] 如果有未建的 horizontal helper（如 S5 的 queue/）影响**非当前模块**实施，我已在 **phase-gate** 添加 reconcile checkbox？

不过任一项 → 不许 commit。

---

## 立即行动清单（按优先级）

| # | Seam | 谁做 | 何时 |
|---|------|-----|------|
| 1 | S6 Mixin 定义 | M01.2（models 块） | 必须先于 M01.2 任何 model 定义 |
| 2 | S4 补 2 个 AppError 子类 + R13-1 CI grep | M01.1（errors 块） | 第一个 commit |
| 3 | S3 ErrorCode 重命名 + engineering-spec 同步 | M01.1（errors 块） | 与 #2 同 commit |
| 4 | S7 engineering-spec 模块编号注释修正 | M01.1（errors 块） | 与 #2 同 commit |
| 5 | S1 D1 决策 + ADR-004 加 disambiguation 注释 | M01 sprint 启动前（CY 拍）| 立即 |
| 6 | S5 phase-gate 加"M17 前置 queue scaffold"checkbox | 现在 | 立即 |
| 7 | 防御机制 — phase-gate 加 reconcile 自检三问 | 现在 | 立即 |

---

## 关联

- 触发事件：M01 实施前 D1 决策（AuthServiceProtocol 1 法 vs ADR-004 4 法）
- 关联 design：ADR-004 § 1 / engineering-spec § 7.2 / 02-modules/README.md § 13 R13-1 / M01 § 13 / M17 § 6 / ADR-002 § 1
- 关联 scaffold：`api/auth/dependencies.py` / `api/auth/tenant_filter.py` / `api/errors/codes.py` / `api/errors/exceptions.py` / `api/models/base.py` / `api/queue/`（不存在）
- 方法论沉淀：memory `feedback_design_scaffold_reconcile.md`（通用模式）
