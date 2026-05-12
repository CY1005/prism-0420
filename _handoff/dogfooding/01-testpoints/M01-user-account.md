---
module: M01
name: user-account
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M01-user-account/00-design.md
  - design/02-modules/M01-user-account/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
  - design/adr/ADR-004-auth-cross-cutting.md
prd_ref: F1 用户账号 AC1-AC13
---

# M01 用户账号 测试点

## 业务流程（H1 / 1 行概述）

M01 是全系统鉴权源头：邮箱+密码登录发放 Access JWT + Refresh Token，提供 require_user/require_admin Depends，admin 可 CRUD 用户、改 role/status，禁用账号 / 改密码触发所有 session 立即失效（ADR-004 #5）。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] /auth/login 邮箱密码正确返 200 + access_token + refresh_token + UserProfile（见 design §7 Endpoints + tests.md G1）
- [P0] /auth/me Bearer JWT 返当前 UserProfile 含 version 字段（design §7 + tests.md G2）
- [P0] /auth/refresh 有效 refresh_token 返新 access_token，last_seen_at 更新（design §7 + tests.md G3）
- [P0] /auth/logout 撤销 refresh_token 后该 token 不可再用且响应统一 `{"status":"ok"}`（design §8 防刺探 + tests.md G4）
- [P0] PATCH /auth/me 改 name happy path version+1 且不撤 refresh_token（design §10 顺序约定 + tests.md G5）
- [P0] PATCH /auth/me 改密码后 token_invalidated_at 更新 + 所有 refresh_token 被撤销 + auth_audit_log 写 password_change → all_tokens_revoked 两条（design §10 多事件原子组 + tests.md G6）
- [P0] POST /auth/users platform_admin 创建用户返 201 + version=1（design §7 + tests.md G7）
- [P0] PATCH /auth/users/{id} 改 status=disabled 触发该用户 refresh_token 全撤 + token_invalidated_at 更新（design §5 多表事务 + tests.md G10）
- [P1] GET /auth/users admin 返列表含 version 字段（design §7 + tests.md G8）
- [P1] PATCH /auth/users/{id} 改 status=active 不撤销 token（已撤销态，design §10 + tests.md G11）
- [P1] PATCH /auth/me name 与现值相同且无 new_password 不 bump version 不写 audit（design §4 空请求语义 + sprint 反馈 2026-05-07）
- [P1] PATCH /auth/users/{id} 改 role + 改 status 写 audit 顺序 admin_update_role → admin_update_status（design §10 多事件原子组）
- [P2] Bootstrap env seed 首启 users 空时创建首 admin（design §1 + tests.md BS1）
- [P2] Bootstrap CLI `python -m api.cli create-admin` 0 退出码创建 admin / email 冲突非 0 退出（design §6 CLI 层 + tests.md BS4/BS5）

### 2. 边界 / 状态机

- [P0] active → disabled 状态转换允许（design §4 mermaid + tests.md G10）
- [P0] disabled → active 状态转换允许（design §4 mermaid + tests.md G11）
- [P0] active → pending PATCH 拒绝返 INVALID_STATUS_TRANSITION 400（design §4 禁止转换表 + R4-3a）
- [P0] disabled → pending PATCH 拒绝返 INVALID_STATUS_TRANSITION 400（design §4 禁止转换表）
- [P1] disabled 用户 hard delete 端点本期不存在（design §4 + §8 防越权）
- [P1] pending 账号登录拒绝返 ACCOUNT_PENDING 403（design §4 R4-3a + tests.md P11）
- [P1] PATCH /auth/me 入参完全空（无 name 也无 new_password）返 422（design §4 空请求兜底）
- [P1] name 超长 256 字符返 422（design §7 max_length=255 + tests.md B3）
- [P1] password 超长 129 字符返 422（design §7 max_length=128 + tests.md B12）
- [P1] password 短于 8 字符返 422 PASSWORD_TOO_WEAK（design §13 + tests.md B4）
- [P1] role 传 super_admin 等枚举外值返 422（design §7 Literal + tests.md B5）
- [P1] status 传 deleted 等枚举外值返 422（design §7 Literal + tests.md B6）
- [P1] email 非合法格式返 422 EmailStr（design §7 + tests.md B2）
- [P1] user_id 非 UUID 返 422（tests.md B8）
- [P1] PATCH /auth/me extra=forbid 传 nickname 等额外字段返 422（design §7 ConfigDict + tests.md B11）

### 3. 异常 / 错误

- [P0] 错密码登录返 INVALID_CREDENTIALS 401 + auth_audit_log 写 login_failed（design §13 + tests.md L2）
- [P0] 连续 5 次错密码触发账号锁 15min + auth_audit_log 写 user.locked（design §1 失败锁 + tests.md L3 + C5）
- [P0] locked_until 未到的用户登录返 ACCOUNT_LOCKED 423（design §13 + tests.md P10）
- [P0] 改密码事务失败（mock revoke_all_for_user 抛异常）users / token_invalidated_at / refresh_tokens / auth_audit_log 全回滚（design §5 多表事务 + B2 决策 + tests.md C9）
- [P1] refresh_token 非法字符串返 INVALID_REFRESH_TOKEN 401（design §13 + tests.md B10）
- [P1] refresh_token 过期返 REFRESH_TOKEN_EXPIRED 401 + 对应行被删（design §13 + tests.md A11）
- [P1] disabled 用户的 refresh_token 续杯返 401（design §8 Service 层校验 + tests.md A12）
- [P1] email 重复创建返 EMAIL_ALREADY_EXISTS 409（design §13 + tests.md B7）
- [P1] 不存在的 user_id PATCH 返 USER_NOT_FOUND 404（design §13 + tests.md B9）
- [P1] OLD_PASSWORD_MISMATCH 改密码旧密码错返 400（design §13）
- [P2] DB 不可用调 /auth/login 返 503 而非泄漏 stacktrace（tests.md E1）
- [P2] JWT_SECRET 缺失启动期 config validator 阻断（prod 环境，tests.md E2）
- [P2] INTERNAL_TOKEN < 16 字符 prod 环境启动失败 raise / dev 环境 warning 允许（design §8 + tests.md E3/S10）
- [P2] /auth/logout refresh_token 不存在也返 `{"status":"ok"}` 200 不透露 token 历史存在性（design §8 防刺探）

### 4. 权限 / Auth

- [P0] 未登录访问 /auth/me 无 Authorization 返 UNAUTHENTICATED 401（design §8 + tests.md P1）
- [P0] 过期 JWT 访问 /auth/me 返 401（design §8 P1 + tests.md A2）
- [P0] 伪造 JWT 签名（JWT_SECRET 错）返 401（tests.md A3）
- [P0] 把 refresh_token 当 access token 放 Authorization 返 401（type!=access 检查，tests.md A4）
- [P0] 普通 user role=user 调 GET /auth/users 返 PERMISSION_DENIED 403（design §8 require_admin + tests.md P5）
- [P0] 普通 user PATCH /auth/users/{other_id} 返 403（design §8 + tests.md P6）
- [P0] platform_admin PATCH 自己 role=user 返 SELF_DOWNGRADE_FORBIDDEN 400（design §8 防越权 + tests.md P7）
- [P0] 系统只剩 1 个 active admin 时禁用他返 LAST_ADMIN_PROTECTED 400（design §8 + tests.md P8）
- [P0] disabled 用户登录返 ACCOUNT_DISABLED 403（design §13 + tests.md P9）
- [P0] G10 禁用后老 access token 访问 /me 返 401（design §5 + ADR-004 #5 + tests.md P4/I3）
- [P1] /auth/login /auth/refresh /auth/logout 三端点豁免 require_user 不需 Authorization（design §8 显式豁免）
- [P1] /auth/refresh token_invalidated_at 晚于 refresh 创建时刻拒绝 401（ADR-004 #5 + tests.md A13）
- [P1] /auth/me 普通用户只能改自己 / 端点设计上无法改别人（tests.md B13）
- [P2] P4 一次性 token 端点（password_reset / invite）本期不存在返 404（tests.md A14）

### 5. Tenant 隔离

- [P0] users 表跨项目全局可见 admin 查 /auth/users 返全部用户无 project_id 过滤（design §5 + §9 豁免 + tests.md T1）
- [P1] 普通 user 登录后调 /me 无项目上下文（design §1 边界灰区 + tests.md T2）
- [P1] M01 所有 DAO 方法不接受 project_id 入参（design §9 豁免声明，CI 守护扫描）

### 6. 并发 / 乐观锁

- [P0] 同 email 两 admin 并发 POST /auth/users 一个 201 一个 409 EMAIL_ALREADY_EXISTS（UNIQUE 约束 + 设计原则清单 6 IntegrityError 转业务异常 + tests.md C1）
- [P0] admin A 与 admin B 都读 version=3 / A 先提交成功 version=4 / B 后提交 expected_version=3 返 VERSION_CONFLICT 409（design §5 R5-2 + tests.md C2）
- [P0] admin A PATCH {status=disabled, expected_version=5} 与 admin B PATCH {role=platform_admin, expected_version=5} 并发只一者成功不出现 disabled-platform_admin 矛盾态（design §5 ABA 缺口 + Concern 1 + tests.md C6）
- [P1] PATCH /auth/me 不传 expected_version 返 422 Pydantic 必填（design §7 + tests.md C8）
- [P1] expected_version=99（远超当前）返 VERSION_CONFLICT 409（tests.md C7）
- [P1] 5 个并发错密码登录 failed_login_count 达到或超过 5 触发锁定（tests.md C5）
- [P1] 同一 refresh_token 并发调 /auth/refresh 2 次本期都成功返不同 access_token / last_seen_at 后写者赢（design §11 非幂等 + tests.md C3）
- [P2] Tab A 改密码同时 Tab B 登录 / Tab B 新 access token iat 晚于 token_invalidated_at 仍可工作 / Tab A 旧 token 失效（tests.md C4）

### 7. 数据完整性

- [P0] users.version 字段 NOT NULL default 1（design §3 Concern 1 + tests.md S3b）
- [P0] users.role CHECK 约束仅允许 platform_admin/user（design §3 R3-2 + tests.md S7）
- [P0] users.status CHECK 约束仅允许 active/disabled/pending（design §3 + tests.md S8）
- [P0] users.email UNIQUE 约束自然防重（design §11 + tests.md B7）
- [P1] auth_audit_log.action_type CHECK 约束仅允许 11 个 design §10 事件值 / 'unknown.event' INSERT 失败（design §10 + tests.md S4b）
- [P1] auth_identities.provider CHECK 约束仅允许 github/google（design §3 R3-2 + tests.md S6）
- [P1] refresh_tokens 4 扩展字段 device_info/ip/user_agent/last_seen_at 存在（design §3 Q5 预留 + tests.md S4）
- [P1] users.password_hash nullable（Q4 预留 OAuth 场景，tests.md S2）
- [P1] users.avatar_url 字段存在且 nullable（Q3 预留，tests.md S3）
- [P1] String(N) 长度约束（email String(320)）INSERT 500 字符失败（tests.md S11）
- [P1] FK ON DELETE CASCADE 删 users 行 refresh_tokens 级联删除（tests.md E5）
- [P1] 5 张预留表（auth_audit_log / password_reset_tokens / invite_codes / auth_identities / email_change_requests）Alembic upgrade head 后均存在（design §3 + tests.md S1）

### 8. UI / UX

- [P1] 登录失败前端展示 INVALID_CREDENTIALS 文案"邮箱或密码错误"不暴露"该 email 不存在"（design §13 安全考虑）
- [P1] 账号被锁前端展示 ACCOUNT_LOCKED "账号已被锁定，请稍后重试"（design §13 message）
- [P1] VERSION_CONFLICT 前端 toast "数据已被他人修改，请刷新后重试"+ 触发刷新（design §5 R5-2 message）
- [P2] /auth/users admin 列表 UI 展示 version 字段供前端 PATCH 时回传（design §7 UserListItem）

### 9. 性能 / 容量

- [P1] /auth/login 部署前置 Nginx limit_req 5 req/min per IP（design §11 部署前置 + §8 ⚠️ rate limit）
- [P1] /auth/refresh 部署前置 limit_req 20 req/min per IP 防 auth_audit_log 表膨胀（design §11 M5 决策）
- [P1] /auth/logout 部署前置 limit_req 10 req/min per IP（design §11）
- [P2] auth_audit_log 单月行数 > 10 万触发 §10 m5 决策 UNION 视图预案（design §10 跨表查询预案）

### 10. ADR-004 凭据路径（M01 特有）

- [P0] P1 有效 Bearer JWT 访问 /me 返 200（design §8 + tests.md A1）
- [P0] P2 有效 internal token + 完整 4-header HMAC 签名访问 /me 返 200（design §8 ADR-004 B1 决策 + tests.md A5）
- [P0] P1+P2 同时发送 P1 优先 / mock resolve_from_internal 不被调用（design §8 B1 + tests.md A9）
- [P0] P1 失败 + P2 有效走 P2 兜底 / mock resolve_from_internal 被调用 1 次（NI-04 + tests.md A9b）
- [P0] P1+P2 都无效返 401（tests.md A9c）
- [P1] P2 签名材料缺一 header（X-Internal-Timestamp 缺）返 401（tests.md A15）
- [P1] P2 时间戳超 5min 窗口（过去/未来）返 401（tests.md A16/A17）
- [P1] P2 body 被篡改但签名是旧 body 的返 401 body_hash 不匹配（tests.md A18）
- [P1] P2 path 被篡改返 401（tests.md A19）
- [P1] P2 path 相同但 query string 被篡改（dry_run=true → false）返 401 签名材料含 path_with_query（NI-01 + tests.md A19b）
- [P1] P2 原请求无 query 攻击者加 query 返 401（tests.md A19c）
- [P1] P2 query 参数顺序变化返 401 本期不做规范化（tests.md A19d）
- [P1] P2 method 被篡改（GET→POST）返 401（tests.md A20）
- [P1] P2 X-User-Id 在签名内被换返 401（tests.md A21）
- [P1] P2 同一有效请求 5min 内重放本期允许（nonce 防御未实装）返 200 但 auth_audit_log 本期不写（design §10 P2 入站不写 audit + tests.md A22）
- [P1] P2 重放窗口外（>5min）返 401（tests.md A23）
- [P1] P2 internal token 正确但 X-User-Id user 不存在返 401（tests.md A7）
- [P1] P2 internal token 正确但 user.status=disabled 返 401（tests.md A8）

### 11. Token 失效事件（ADR-004 #5）

- [P0] admin 禁用 alice users.token_invalidated_at=now() + refresh_tokens 全删 + auth_audit_log 写 all_tokens_revoked reason=admin_disable（design §5 + tests.md I1）
- [P0] alice 改密码 token_invalidated_at=now() + 全删 refresh_tokens + auth_audit_log 写 all_tokens_revoked reason=password_change（design §10 + tests.md I2）
- [P0] I1/I2 后旧 access token iat 早于 token_invalidated_at 访问 /me 返 401（tests.md I3）
- [P1] I1/I2 后重新登录新 access token iat 晚于失效时刻访问 /me 返 200（tests.md I4）

### 12. auth_audit_log 事件完备性

- [P0] login_success 写 1 行 metadata 含 ip/user_agent（design §10 + tests.md L1）
- [P0] login_failed email 不存在场景 user_id=NULL + metadata.email 存字符串（design §10 + tests.md L11）
- [P0] M01 所有事件不写 M15 activity_log / `SELECT COUNT(*) FROM activity_log WHERE action_type LIKE 'user.%'` = 0（design §10 Concern 2+3 + tests.md L12）
- [P1] 失败路径 login_failed 在独立事务（非业务事务）内写入即使失败也留痕禁 fire-and-forget（design §5 B2 决策 + tests.md C11）
- [P1] PATCH /auth/me 改密码 + 改 name 三事件顺序 password_change → all_tokens_revoked → profile_update（design §10 顺序约定）
- [P1] PATCH /auth/users/{id} status=disabled 顺序 admin_update_status → all_tokens_revoked（design §10 顺序约定）
- [P1] admin_update_role 事件 metadata 含 old_role / new_role / admin_id（design §10 + tests.md L9）
- [P1] all_tokens_revoked 事件 metadata.revoked_count 反映被撤数（design §10）
- [P2] P2 入站请求本期不写 auth_audit_log A22 重放测试不断言 audit 行数（design §10 P2 策略 + sprint 反馈 2026-05-07）

### 13. CI 守护 / 设计漂移防御

- [P1] CI grep 守护 1：services/ routers/ 禁 import PasswordResetToken/InviteCode/AuthIdentity/EmailChangeRequest 预留 model（design §3 反向约束 + tests.md S5c）
- [P1] CI grep 守护 2：routers/ 除 auth.py 外禁直 import User/RefreshToken model（design §6 分层 + tests.md S5d）
- [P1] CI grep 守护 3：ErrorCode 枚举行数 == AppError class 定义行数（design §13 R13-1 + tests.md S5e）
- [P2] DAO 守护：M01 DAO 方法签名不接受 project_id 参数（design §9 豁免 + 防绕过纪律）

### 14. 跨模块契约（M01 是被依赖源头）

- [P1] require_user Depends 返 User 对象 / 业务模块通过 Depends 消费（design §1 + §8）
- [P1] AuthService.resolve_from_bearer/internal/refresh 三方法签名稳定 / 跨模块调用契约（design §1 被依赖契约）
- [P1] User SQLAlchemy 模型 FK ForeignKey("users.id") 被其他模块 created_by/updated_by/user_id 引用（design §1 + §3 ER 图）
- [P2] hash_password/verify_password helper 复用 CLI bootstrap / seed 脚本（design §1 + §6 CLI 层）
