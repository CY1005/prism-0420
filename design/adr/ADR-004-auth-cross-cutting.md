---
title: ADR-004 Auth 横切范式（用户/Session/权限源头）
status: draft
owner: CY
created: 2026-04-24
accepted: null
supersedes: []
superseded_by: null
last_reviewed_at: null
related_modules: [M01, M02, M15, 所有需要 require_user 的路由, 所有需要 TaskPayload.user_id 的异步模块]
---

# ADR-004：Auth 横切范式

## Context（背景）

prism-0420 所有需要"当前用户"的代码路径——同步 HTTP 路由、异步 Queue 任务、Server Action、Next.js 服务间调用、CLI bootstrap——都要从某处拿到 `user_id`。如果没有单一范式，每条路径会各自发明"鉴权"写法，产生下列已在 Prism 实战中出现过的漂移：

1. Queue 消费者"接到任意 user_id 的 payload 即执行"的越权（已由 ADR-002 修正）
2. Server Action → FastAPI 的服务间调用用明文 user_id，被伪造即越权（Prism 用 HMAC internal token 修了，但没文档）
3. 忘密/邀请码/OAuth 回调等"半认证"端点（拿一次性 token 代替 JWT）各自写校验逻辑，审计成本高
4. Access Token 失效后的"续杯"路径不一致（前端 refresh / WebSocket 重新握手 / Server Action 降级 各不同）

Prism 代码现状验证了"没有横切范式"的代价：`/root/prism/api/routers/auth.py:40-62` 的 `require_user` 依赖同时混合了 Bearer JWT + `X-Internal-Token` + `X-User-Id` 三种凭据的判定逻辑。一旦逻辑漂移（加一种凭据类型），全系统路由要改。

M01 作为用户账号的"源头模块"，是抽出范式的最佳锚点。

## Decision（决策）

**auth 横切范式 = 4 类凭据路径 + 1 张凭据→主体映射表 + 每路径的校验清单**。

所有模块的 §8"权限三层"都基于本 ADR 声明："我用的是哪条凭据路径"。

### 4 类凭据路径

| # | 路径 | 凭据载体 | 映射到 | 适用层 | 典型端点/场景 |
|---|------|---------|-------|-------|--------------|
| **P1** | Bearer JWT access token | `Authorization: Bearer <jwt>` | `users.id`（通过 JWT `sub`）| Router 层 Depends | 浏览器→FastAPI 所有业务路由 |
| **P2** | Internal service token（HMAC）| `X-Internal-Token: <hmac>` + `X-User-Id: <uuid>` | `users.id`（header 显式）| Router 层 Depends | Next.js Server Action → FastAPI 服务间调用 |
| **P3** | Refresh token | Cookie 或 request body `refresh_token` | `refresh_tokens.id` → `users.id` | 专用 `/auth/refresh` 端点 | Access token 过期后续杯 |
| **P4** | 一次性 token（forgot-password / invite / email-change）| URL query 或 body 的一次性 string | 预留表的 token_hash → `users.id` | 专用半认证端点 | 本期仅**预留 schema**，未开放 |

**其他路径（本期不开放，未来扩展）**：
- **P5** OAuth provider callback：`auth_identities.provider_user_id` → `users.id`（Q4 扩展时启用）
- **P6** WebSocket 握手：握手时校验 URL query token 归属 user + 每命令重校 task_id 归属（参 [ADR-002](./ADR-002-queue-consumer-tenant-permission.md) 第 4 项，本期 M01 不涉及）
- **P7** Queue TaskPayload：`payload.user_id`（参 [ADR-002](./ADR-002-queue-consumer-tenant-permission.md) 第 1-3 项，M01 本身不用）

### 核心 5 项

#### 1. 凭据→主体映射统一走 M01 Service

所有凭据路径的"从凭据拿到 User"逻辑集中在 `api/services/auth_service.py`。路由/异步任务/Server Action 代理**不得**自己解析 JWT / 查 refresh_tokens。

```python
# api/services/auth_service.py
class AuthService:
    def resolve_from_bearer(self, db: Session, token: str) -> User | None: ...     # P1
    def resolve_from_internal(                                                     # P2 (with signature)
        self,
        db: Session,
        token: str,
        user_id: UUID,
        signature: str,
        timestamp: str,
        method: str,
        path: str,
        body: bytes,
    ) -> User | None: ...
    def resolve_from_refresh(self, db: Session, raw_refresh: str) -> tuple[User | None, str | None]: ...  # P3
    def resolve_from_one_time(self, db: Session, token: str, purpose: Literal["password_reset", "invite", "email_change"]) -> User | None: ...  # P4 预留
    # 未来扩展接口（本期不实装，签名预留以便 ADR 扩展时无需回改 M01 Service）：
    # def resolve_from_oauth(self, db: Session, provider: str, provider_user_id: str) -> User | None: ...  # P5 预留 (Q4 OAuth)
    # def resolve_from_ws_handshake(self, db: Session, ws_token: str) -> User | None: ...  # P6 预留 (WebSocket，参 ADR-002 第 4 项 task_id 重校)
    # def resolve_from_task_payload(self, db: Session, payload: TaskPayload) -> User | None: ...  # P7 (Queue，参 ADR-002 第 1-3 项)
```

**检查**：CI 静态扫描 `routers/` 下禁止 `import jwt` / 禁止 `db.query(RefreshToken)`（M01 router 本身豁免）。

#### 2. `require_user` Depends 是 P1+P2 的唯一合并入口（P1 优先 + P2 带签名兜底）

所有 Router 层的 `Depends(require_user)` 由 M01 提供，内部**先试 P1（Bearer JWT）再试 P2（internal token + 签名）**，失败 401。

**为什么改 P1 优先**（相比 Prism 现状的 P2 优先）：若 P2 优先，INTERNAL_TOKEN 泄露即等同全域 root（攻击者可冒任意 user_id 含 platform_admin）。P1 优先 + P2 带请求签名的方案把 P2 的"泄露即失守"降到"泄露 + 抓包才能重放"，防御深度 +1 层。

```python
# api/routers/auth.py
from fastapi import Request

async def require_user(
    request: Request,
    authorization: str | None = Header(None),
    x_internal_token: str | None = Header(None),
    x_user_id: str | None = Header(None),
    x_internal_signature: str | None = Header(None),
    x_internal_timestamp: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    svc = AuthService()
    # P1 优先（浏览器 / 真实用户凭据）
    if authorization and authorization.startswith("Bearer "):
        user = svc.resolve_from_bearer(db, authorization[7:])
        if user:
            return user
    # P2 兜底（Next.js Server Action → FastAPI 服务间调用，须带签名）
    if (x_internal_token and x_user_id and
        x_internal_signature and x_internal_timestamp):
        body = await request.body()
        user = svc.resolve_from_internal(
            db=db,
            token=x_internal_token,
            user_id=UUID(x_user_id),
            signature=x_internal_signature,
            timestamp=x_internal_timestamp,
            method=request.method,
            path=request.url.path,
            body=body,
        )
        if user:
            return user
    raise HTTPException(401, "未登录")
```

**禁止**在业务路由里手写 JWT 解析或 internal token 校验。

#### 3. Internal Token 威胁模型 + 签名协议（B1 审计决策落地）

##### 3.1 威胁模型

| 威胁 | 原 P2 无签名设计下的影响 | 本 ADR 带签名设计下的影响 |
|------|----------------------|------------------------|
| INTERNAL_TOKEN 泄露（写入日志 / config 误 commit / 内网扫描）| ⚠️ **系统沦陷**：任意冒充任意用户（含 admin）| 🟢 需同时抓包到有效签名请求样本才能重放，且每个请求 5min 窗口 |
| 中间人抓包单个 P2 请求 | ⚠️ **可复用**：token 相同无时间校验 | 🟢 签名绑定 ts + method + path + user_id + body_hash，5min 窗口外失效；换路径/参数签名失效 |
| INTERNAL_TOKEN 弱强度（< 32 字节）| ⚠️ 可暴力枚举 | 🟢 config validator 启动期阻断 < 32 字节 token |
| Server Action 代码泄露（含签名算法）| ⚠️ 同上 | ⚠️ 同上——签名算法是**可公开**的，保密的只是 INTERNAL_TOKEN 本身 |
| 攻击者持有 P2 凭据 + 签名能力 | ⚠️ 可冒 admin | 🟡 P1 优先策略下，P2 访问被审计时可区分"真实 JWT 登录"vs"服务间调用"——auth_audit_log metadata.auth_path 必记 |

**绝对约束**：INTERNAL_TOKEN 是**主密钥**，泄露后必须轮换；运维侧要求：① 只通过 secrets manager / env 注入，禁止写配置文件 ② 日志禁打印 ③ 周期轮换（建议季度）④ 生产环境长度 ≥ 64 字节（随机）。

##### 3.2 签名协议

**签名材料**（newline 分隔的规范化字符串）：
```
{timestamp}\n{HTTP_METHOD}\n{URL_PATH}\n{X-User-Id}\n{SHA256_HEX(request_body)}
```

**签名算法**：`HMAC-SHA256(INTERNAL_TOKEN, signature_material)` → hex 小写。

**Headers 契约**（Next.js Server Action 发送方 / FastAPI 接收方）：

| Header | 内容 | 必填 |
|--------|------|------|
| `X-Internal-Token` | INTERNAL_TOKEN 原值 | ✅ |
| `X-User-Id` | 目标用户 UUID（服务代某用户发起的操作）| ✅ |
| `X-Internal-Timestamp` | Unix 秒级时间戳（UTC）| ✅ |
| `X-Internal-Signature` | 上述 HMAC-SHA256 hex | ✅ |

**校验流程**（`AuthService.resolve_from_internal`）：

```python
def resolve_from_internal(
    self, db, token, user_id, signature, timestamp, method, path, body,
) -> User | None:
    # 1. 常量时间比较 token（防时序攻击）
    if not hmac.compare_digest(token, INTERNAL_TOKEN):
        return None
    # 2. 时间窗口（5 分钟）
    try:
        ts = int(timestamp)
    except ValueError:
        return None
    now = int(time.time())
    if abs(now - ts) > 300:
        return None
    # 3. 重建签名材料
    body_hash = hashlib.sha256(body).hexdigest()
    material = f"{timestamp}\n{method}\n{path}\n{user_id}\n{body_hash}"
    expected_sig = hmac.new(
        INTERNAL_TOKEN.encode(), material.encode(), hashlib.sha256
    ).hexdigest()
    # 4. 常量时间比较签名
    if not hmac.compare_digest(signature, expected_sig):
        return None
    # 5. 查 user 且 active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != UserStatus.ACTIVE.value:
        return None
    return user
```

##### 3.3 部署约束

**启动期 config validator**（`api/main.py` startup hook）：
- 生产环境 `INTERNAL_TOKEN` < 32 字节 → 阻断启动并 raise
- dev 环境允许 ≥ 16 字节 + 打印 warning
- `hmac.compare_digest` 比较（禁用 `==`）
- 日志中**永不**打印 INTERNAL_TOKEN / 完整 signature 值（即使 debug 级别）

##### 3.4 重放窗口 + 未实装的 nonce 防御

5 分钟窗口内同一签名**可以重放**。对 M01 大多数端点（POST/PATCH 操作），重放的危害 ≤ "同用户同操作做了两次"（幂等或乐观锁兜底）。**未实装 nonce 防御**的理由：需要 Redis 存已用 nonce，本期 Redis 被 arq Queue 独占，加 auth nonce store 会引入新依赖 + 清理策略。

**未来扩展方向**（不在本期）：当 Next.js 实例数 > 1 或 P2 端点含强安全敏感操作（财务/权限变更）时，加 Redis nonce store（`SETNX auth:nonce:{signature} "" EX 300` 防重放）。

#### 4. Access token 失效后的续杯策略

前端（浏览器）拿到 401 后**唯一**的续杯路径 = 调 `POST /auth/refresh` 走 P3。禁止前端在 401 后自动调 P1 用旧 JWT 重试。

**短路保护**：若 refresh 也 401，前端清 refresh token + 跳登录页。禁止"无限重试 refresh"（P3 端点本身用 IP-based rate limit，本期不实装但在 ADR 声明）。

#### 5. Token 失效事件有单一触发源

下列 4 个事件触发"用户所有 session 失效"（access + refresh 都无效）：

| 事件 | 触发 | 实现 |
|------|------|------|
| 管理员禁用账号（`status=disabled`）| PATCH /auth/users/{id} | 撤销该用户所有 refresh_tokens；`token_invalidated_at = now()` |
| 用户自己改密码 | PATCH /auth/me (password)| 同上 |
| 管理员强制登出（Q5 Session 管理页扩展）| DELETE /auth/users/{id}/sessions | 同上 |
| 刷新令牌被盗告警（未来扩展）| 内部触发 | 同上 |

`token_invalidated_at` 是 `users` 表字段（Prism 已有）。Access token 校验时比较 JWT 的 `iat` 与 `token_invalidated_at`，iat 早则拒绝。

**检查**：CI 静态扫描 M01 Service 层"凡是写 `user.status = 'disabled'` 的代码必须同步调 `revoke_all_user_tokens`"。

---

## Consequences（后果）

### 正面

- **Router 层无鉴权细节**：新模块写 `user: User = Depends(require_user)` 即可，永远不关心 P1/P2/P3 差异
- **横切审计单点**：审计"谁能拿到 user_id"只需读 `auth_service.py` 的 4 个 `resolve_*` 方法
- **未来扩展锚点**：P4（一次性 token）/ P5（OAuth）实装时只加 `resolve_from_oauth` 不改业务路由
- **与 ADR-002 互补**：ADR-002 覆盖 P7（Queue TaskPayload），ADR-004 覆盖 P1-P4；未来 P6（WebSocket）由引用两者的模块各自补

### 负面

- AuthService 承载 4 个 resolve 方法，文件略长（预计 250 行）——接受，单一模块内部长度可控
- Prism 现状的 `require_user` 混合写法需要重写——M01 pilot 重新定义，不兼容 Prism 现有代码（shadow 项目允许）

### 横切影响

- **所有业务模块** §8 必须引本 ADR，声明"本模块用 P1 / P2"（绝大多数是 P1+P2）
- **M01 本身**：`/auth/login` 端点**不**走 require_user（它本身产出凭据），需单独声明"豁免鉴权"；`/auth/refresh` 走 P3（单独校验）；`/auth/users/*` admin 端点走 P1+P2 + `require_admin` 装饰器
- **M15 activity_log**：所有凭据路径映射出的 user_id 都要进 activity_log 的 `user_id` 字段——无匿名操作
- **Queue 模块**（M17 等）：继续遵守 ADR-002（P7），不变

---

## Alternatives（备选方案）

### A. 不抽 ADR，每模块各写 Depends

- 劣势：Prism 已经漂移过一次，shadow 项目再踩同样坑无意义
- **拒绝**

### B. 抽到 06-design-principles 清单里

- 劣势：principles 是"原则"，凭据路径表是"实现契约"——抽象层级不对
- **拒绝**

### C. 起独立 ADR（采纳）

- 优势：和 ADR-002 并列形成"横切三 ADR"（001 分层 / 002 Queue tenant / 003 跨模读 / 004 auth），完整覆盖横切面
- **采纳**

---

## 引用方

- `design/02-modules/M01-user-account/00-design.md` §8 / §1（auth pilot 模板）
- 所有业务模块 §8：声明"本模块鉴权走 ADR-004 P1+P2（与异步 Queue 路径见 ADR-002）"
- 未来 OAuth 实装时扩展本 ADR 加 P5 段落

## 关联

- [ADR-001](./ADR-001-shadow-prism.md)（shadow 项目定位、分层原则起源）
- [ADR-002](./ADR-002-queue-consumer-tenant-permission.md)（P7 Queue TaskPayload 路径 = 本 ADR 的补集）
- [ADR-003](./ADR-003-cross-module-read-strategy.md)（横切三 ADR 的读路径部分）
- `design/02-modules/README.md` §8 R8-1/R8-2/R8-3（权限三层 + Queue 消费者侧 + WebSocket 重校）
- Prism 现状：`/root/prism/api/routers/auth.py:40-62` require_user 混合凭据 = 本 ADR 要整洁替代的反例
