---
title: M01 用户账号 - 测试场景
status: draft
owner: CY
created: 2026-04-24
accepted: null
module_id: M01
---

# M01 用户账号 - 测试场景

按 6 类测试框架组织（golden / 边界 / 并发 / tenant / 权限 / 错误）+ M01 特有的"凭据路径"类（ADR-004）+ "预留 schema 存在性"类。

测试框架：`pytest` + FastAPI `TestClient` + SQLAlchemy fixtures（测试 DB 隔离）。

---

## 1. Golden Path（主流程正向）

| # | 场景 | 前置 | 操作 | 预期 |
|---|------|------|------|------|
| G1 | 登录成功 | 存在 active 用户 alice | POST /auth/login {email, password} | 200 + access_token（JWT） + refresh_token + user profile；DB refresh_tokens 新增 1 行（含 ip/user_agent） |
| G2 | access token 携带访问 /me | G1 已登录 | GET /auth/me `Authorization: Bearer <access>` | 200 + UserProfile |
| G3 | 续杯 | refresh_token 有效 | POST /auth/refresh {refresh_token} | 200 + 新 access_token；refresh_tokens.last_seen_at 更新 |
| G4 | 登出 | refresh_token 有效 | POST /auth/logout {refresh_token} | 200；refresh_tokens 对应行删除 |
| G5 | 改 name | 已登录 | PATCH /auth/me {expected_version, name: "Alice New"} | 200 + 新 profile（version+1）；refresh_tokens 不受影响；auth_audit_log 写 user.profile_update |
| G6 | 改密码 | 已登录，old_password 正确 | PATCH /auth/me {expected_version, old_password, new_password} | 200；users.token_invalidated_at 更新；version+1；该用户所有 refresh_tokens 被撤销；auth_audit_log 写 user.password_change + user.all_tokens_revoked |
| G7 | Admin 创建用户 | 当前 platform_admin | POST /auth/users {email, name, password, role: user} | 201 + 新 user（version=1）；auth_audit_log 写 user.admin_create |
| G8 | Admin 列表 | 当前 platform_admin | GET /auth/users | 200 + users 列表（含 version 字段） |
| G9 | Admin 改 role | 当前 platform_admin，目标 user_id != 自己 | PATCH /auth/users/{id} {expected_version, role: platform_admin} | 200；version+1；auth_audit_log 写 user.admin_update_role |
| G10 | Admin 禁用用户 | 当前 platform_admin，目标 active | PATCH /auth/users/{id} {expected_version, status: disabled} | 200；version+1；目标用户 refresh_tokens 全撤销 + token_invalidated_at 更新；auth_audit_log 写 user.admin_update_status + user.all_tokens_revoked |
| G11 | Admin 启用 | 目标 disabled | PATCH /auth/users/{id} {expected_version, status: active} | 200；version+1；不撤销 token（已是撤销状态） |
| G12 | Bootstrap env seed | DB users 表空 + env `BOOTSTRAP_ADMIN_EMAIL/PASSWORD` 已设 | 启动 api/main.py | 启动日志含"首 admin 创建"；users 表 1 行 role=platform_admin |
| G13 | Bootstrap CLI | 无论 users 表是否空 | `python -m api.cli create-admin --email --password --name` | 若 email 不冲突则创建；冲突返回错误码 1 |

---

## 2. 边界场景

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| B1 | 空 email 登录 | POST /auth/login {email: "", password: "xxx"} | 422（Pydantic min_length）|
| B2 | 非 email 格式 | POST /auth/login {email: "not-an-email", password: "xxx"} | 422（EmailStr） |
| B3 | 超长 name 创建 | POST /auth/users {name: "a" * 300} | 422（max_length=255） |
| B4 | 弱密码创建 | POST /auth/users {password: "short"} | 422（PASSWORD_TOO_WEAK，min_length=8） |
| B5 | 非法 role 创建 | POST /auth/users {role: "super_admin"} | 422（Literal 枚举） |
| B6 | 非法 status 更新 | PATCH /auth/users/{id} {status: "deleted"} | 422 |
| B7 | email 重复创建 | POST /auth/users 传已存在 email | 409 EMAIL_ALREADY_EXISTS |
| B8 | user_id 非 UUID | PATCH /auth/users/not-a-uuid | 422 |
| B9 | 不存在的 user_id | PATCH /auth/users/{random_uuid} | 404 USER_NOT_FOUND |
| B10 | refresh_token 非法字符串 | POST /auth/refresh {refresh_token: "garbage"} | 401 INVALID_REFRESH_TOKEN |
| B11 | 空 extra 字段 | PATCH /auth/me {nickname: "x"}（extra="forbid"）| 422 |
| B12 | 超长密码 | PATCH /auth/me {new_password: "a" * 200} | 422（max_length=128） |
| B13 | 并非自己的 /me 修改 | 正常登录后 PATCH /auth/me（修改别人不可能，端点锁自己） | 200，只改自己 |

---

## 3. 并发场景

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| C1 | 同 email 并发创建 | 两个 admin 同时 POST /auth/users 同一 email | 一个 201、一个 409（UNIQUE 约束）|
| C2 | 同用户并发 PATCH role/status（乐观锁冲突） | admin A 和 admin B 都读到 version=3；A 先提交 PATCH（version 3→4）；B 后提交 PATCH（expected_version=3）| A 成功 200 + version=4；B 返回 **409 VERSION_CONFLICT**；DB 最终只有 A 的变更；auth_audit_log 只写 A 的事件 |
| C3 | 登录并发 refresh | 同一 refresh_token 并发调 /auth/refresh 2 次 | 两次都可能成功（refresh_token 不一次性，除非未来加"rolling refresh"）——本期两次返回不同 access token；last_seen_at 是后写者赢 |
| C4 | 并发改密码 + 登录 | 用户 Tab A 改密码成功同时 Tab B 登录成功 | Tab B 登录发新 token，其 access_token iat 晚于 token_invalidated_at → 正常工作；Tab A 旧 token 全失效 |
| C5 | 失败次数并发计数 | 5 个并发错密码登录 | failed_login_count 最终达到或超过 5；locked_until 被设置；后续登录返回 423 |
| C6 | Admin 并发矛盾操作（Concern 1 核心场景）| admin A 发送 PATCH {status: disabled, expected_version: 5}、admin B 发送 PATCH {role: platform_admin, expected_version: 5} 同时 | 仅先到者 200；后到者 409 VERSION_CONFLICT；**最终用户状态不会出现 "disabled 的 platform_admin" 矛盾组合** |
| C7 | expected_version 不匹配 | 已知当前 version=3，传 expected_version=99 | 409 VERSION_CONFLICT（可能在 expected 过旧或客户端 bug 场景触发） |
| C8 | expected_version 缺失 | PATCH /auth/me 不传 expected_version | 422（Pydantic 必填字段） |
| C9 | 改密码事务原子性（B2）| PATCH /auth/me 改密码，mock DAO.revoke_all_for_user 抛异常 | 500 + 事务全回滚：users.password_hash 不变 / token_invalidated_at 不变 / refresh_tokens 不删 / **auth_audit_log `password_change` 和 `all_tokens_revoked` 两条都不写入**（事务内） |
| C10 | 改密码成功路径审计写入时机（B2）| 正常改密码 | auth_audit_log 2 条事件与 users UPDATE 在同一事务 commit；无中间态可见 |
| C11 | 登录失败路径 audit 独立事务 | 错密码登录 | users.failed_login_count UPDATE + `user.login_failed` 写入 auth_audit_log 在**同一独立事务**（即使失败路径也原子）|

---

## 4. Tenant 场景

**M01 无 tenant（§9 豁免声明）**，不适用跨项目越权测试。

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| T1 | users 表跨项目全局可见 | admin 查 /auth/users | 返回全部用户（无 project_id 过滤） |
| T2 | 普通 user 登录不限项目 | alice 登录后调 /me | 200，无项目上下文 |

---

## 5. 权限场景

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| P1 | 未登录访问 /me | GET /auth/me 无 Authorization | 401 UNAUTHENTICATED |
| P2 | 过期 JWT | 伪造 JWT 过期 | 401（get_current_user 返回 None）|
| P3 | 伪造 JWT 签名 | JWT_SECRET 错 | 401 |
| P4 | 禁用账号 access token 续用 | G10 后老 access token 访问 /me | 401（token_invalidated_at 比较）|
| P5 | 普通 user 调 admin 端点 | user role=user 调 GET /auth/users | 403 PERMISSION_DENIED |
| P6 | 普通 user PATCH 别人 | user role=user 调 PATCH /auth/users/{other_id} | 403（require_admin 失败） |
| P7 | Admin 自降权 | platform_admin PATCH /auth/users/{自己 id} {role: user} | 400 SELF_DOWNGRADE_FORBIDDEN |
| P8 | 禁用最后 admin | 系统只有 1 个 active admin，PATCH 他为 disabled | 400 LAST_ADMIN_PROTECTED |
| P9 | 已禁用账号登录 | disabled 用户 POST /auth/login | 403 ACCOUNT_DISABLED |
| P10 | 账号锁定中登录 | locked_until 未到的用户 | 423 ACCOUNT_LOCKED |
| P11 | pending 账号登录 | status=pending 用户（手动造） | 403 ACCOUNT_PENDING |

---

## 6. 错误处理

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| E1 | DB 不可用 | 关 DB 后调 /auth/login | 503（OperationalError 包装）|
| E2 | JWT_SECRET 缺失 | 启动时 env 不设 JWT_SECRET | 启动失败（启动期 config validator 阻断）或 fallback 到 dev 密钥 + warning log |
| E3 | INTERNAL_TOKEN < 16 字符 | env INTERNAL_TOKEN = "short" | 启动期 config validator 阻断（prod 环境）；dev 允许但 log warning |
| E4 | bcrypt 失败（极端）| 人为注入异常 | 500 服务器内部错误（不暴露细节） |
| E5 | refresh_tokens 表 FK 失效 | 人为删 users 行但 refresh_tokens 未 cascade | 测试 cascade delete 生效（FK ON DELETE CASCADE） |

---

## 7. ADR-004 凭据路径测试（M01 特有）

**核心价值**：验证 §8 声明的 P1-P4 路径在实现中是唯一的、可识别的、不漂移的。

| # | 路径 | 场景 | 操作 | 预期 |
|---|------|------|------|------|
| A1 | P1 | 有效 Bearer JWT | GET /me `Authorization: Bearer <valid>` | 200 |
| A2 | P1 | 过期 Bearer JWT | GET /me 过期 token | 401 |
| A3 | P1 | 伪造签名 | JWT 签名错 | 401 |
| A4 | P1 | type!=access（用 refresh 当 access）| 把 refresh_token 放 Authorization | 401（decode_access_token 检查 type） |
| A5 | P2 | 有效 internal token + 完整签名 4 header | GET /me `X-Internal-Token + X-User-Id + X-Internal-Timestamp + X-Internal-Signature`（签名 = HMAC-SHA256(INTERNAL_TOKEN, f"{ts}\n{method}\n{path}\n{uid}\n{body_hash}")） | 200 |
| A6 | P2 | 伪造 internal token（签名正确不可能构造） | 乱填 X-Internal-Token | 401（HMAC 比较失败） |
| A7 | P2 | internal token 正确但 X-User-Id 不存在 | | 401（user 查不到） |
| A8 | P2 | internal token 正确但 user disabled | | 401（active 状态校验） |
| A9 | P1+P2 混合（B1 新语义）| 同时发有效 Bearer 和有效 P2 | 200——**P1 优先**，走 P1 路径（resolve_from_bearer）；P2 即使有效也不用。断言：mock `resolve_from_internal` 不被调用（`assert_not_called`）|
| A9b | P2 兜底路径（NI-04）| Bearer 无效（过期/签名错）+ P2 完整有效 | 200——P1 失败后走 P2 tiebreaker。断言：mock `resolve_from_bearer` 返回 None 后 `resolve_from_internal` 被调用 1 次 |
| A9c | P1+P2 都无效 | Bearer 过期 + P2 签名错 | 401——两条路径都尝试 |
| A15 | P2 签名 | 签名材料缺一 header（X-Internal-Timestamp 缺）| 401——4 header 必须齐全 |
| A16 | P2 签名 | 时间戳超窗口（> 5min 前）| 401 |
| A17 | P2 签名 | 时间戳未来（> 5min 后）| 401 |
| A18 | P2 签名 | body 被篡改但签名是旧 body 的 | 401（body_hash 不匹配）|
| A19 | P2 签名 | path 被篡改（攻击者换 endpoint）| 401（签名材料 path 不匹配） |
| A19b | P2 签名（NI-01 修正验证）| path 相同但 query string 被篡改（`?dry_run=true` → `?dry_run=false`）| 401——签名材料含 `path_with_query`，query 变化导致 signature 不匹配 |
| A19c | P2 签名 | 原请求无 query，攻击者加 query（`PATCH /x` → `PATCH /x?foo=bar`）| 401——同上 |
| A19d | P2 签名 | query 参数顺序改变（`?a=1&b=2` → `?b=2&a=1`）| 401——**本期不做规范化**，顺序变化即签名失败；客户端需固定 query 顺序 |
| A20 | P2 签名 | method 被篡改（GET 换 POST）| 401 |
| A21 | P2 签名 | X-User-Id 在签名内但攻击者换了 header 值 | 401（签名材料 user_id 不匹配） |
| A22 | P2 签名 | 重放攻击：同一有效请求 5min 内多次发 | **本期允许重放**（nonce 防御未实装，§3.4 显式声明）——多次都 200，但 auth_audit_log 每次记录 1 行 |
| A23 | P2 签名 | 重放攻击：窗口外（> 5min）重放 | 401 |
| A10 | P3 | 有效 refresh token /refresh | | 200 + 新 access |
| A11 | P3 | 过期 refresh token /refresh | | 401 REFRESH_TOKEN_EXPIRED；refresh_tokens 行被删 |
| A12 | P3 | 已撤销 refresh token（disabled 用户）/refresh | | 401（Service 层查 user.status=disabled 拒绝）|
| A13 | P3 | token_invalidated_at 晚于 refresh 创建时刻 | 改密码后用旧 refresh | 401（ADR-004 #5）|
| A14 | P4 | 无端点（预留）| POST /auth/password-reset | 404（路由不存在） |

---

## 8. Token 失效事件测试（ADR-004 #5）

| # | 触发 | 前置 | 操作 | 验证 |
|---|------|------|------|------|
| I1 | 管理员禁用 | alice active 有 2 个 refresh_tokens | admin PATCH status=disabled | users.token_invalidated_at = now()；refresh_tokens 对应行全删；activity_log 写 user.all_tokens_revoked 1 条（metadata.reason=admin_disable） |
| I2 | 改密码 | alice 有 3 个 refresh_tokens | PATCH /me new_password | users.token_invalidated_at = now()；refresh_tokens 全删；activity_log 写 user.all_tokens_revoked（reason=password_change） |
| I3 | access token iat 早于失效时刻 | I1/I2 之后 | 用旧 access token 访问 /me | 401（get_current_user 比较 iat < token_invalidated_at 返回 None） |
| I4 | access token iat 晚于失效时刻 | I1/I2 之后重新登录 | 新 access token 访问 /me | 200 |

---

## 9. Bootstrap 测试（Q7）

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| BS1 | 首启 env seed | 清空 users，设 `BOOTSTRAP_ADMIN_EMAIL/PASSWORD`，启动 | users 新增 1 行 role=platform_admin；日志"Created bootstrap admin: xxx" |
| BS2 | 二次启动不重复 | BS1 后再次启动 | users 不变（启动钩子检测非空时 skip） |
| BS3 | env 未设 + users 空 | 不设 env，启动 | 不创建；日志 warning"No admin found and BOOTSTRAP_ADMIN_* not set" |
| BS4 | CLI 正常 | `python -m api.cli create-admin --email a@b.c --password xxx12345 --name A` | 0 退出码；users 新增 |
| BS5 | CLI 冲突 email | 同上再跑 | 非 0 退出码；stderr "Email already exists" |
| BS6 | CLI 弱密码 | `--password short` | 非 0 退出码；stderr "Password too weak" |

---

## 10. 预留 schema 存在性 + CI 守护

| # | 场景 | 操作 | 预期 |
|---|------|------|------|
| S1 | 迁移后 5 张表存在 | alembic upgrade head，查 information_schema | auth_audit_log + password_reset_tokens + invite_codes + auth_identities + email_change_requests 五表均存在 |
| S2 | users.password_hash nullable | 查 columns | is_nullable = YES |
| S3 | users.avatar_url 存在 | 查 columns | 字段存在，nullable |
| S3b | users.version 存在 | 查 columns | NOT NULL，default 1 |
| S4 | refresh_tokens 4 扩展字段存在 | 查 columns | device_info / ip / user_agent / last_seen_at 均存在 |
| S4b | auth_audit_log.action_type CHECK | 试 INSERT action_type='unknown.event' | CHECK 约束失败（仅允许 11 个值）|
| S5c | CI grep 守护 1（预留 model 禁引用）| `grep -rE "from api.models.user import .*(PasswordResetToken\|InviteCode\|AuthIdentity\|EmailChangeRequest)" api/services/ api/routers/` | 退出码 1（无匹配）|
| S5d | CI grep 守护 2（Router 禁直查 user model）| `grep -rE "from api.models.user import (User\|RefreshToken)" api/routers/ \| grep -v auth.py` | 退出码 1（无匹配）|
| S5e | CI grep 守护 3（ErrorCode ↔ AppError 数量一致）| 比较 codes.py 的枚举行数 vs exceptions.py 的 class 定义行数 | 两者相等 |
| S10 | 启动 config validator | 未设 INTERNAL_TOKEN 或 < 16 字节，prod 环境启动 | 启动失败 raise；dev 环境 warning 允许 |
| S11 | 列类型 String(N) 长度约束 | 试 INSERT email 长度 500 字符 | 失败（超 String(320)）|
| S5 | CI 静态扫描：预留 model 禁引用 | `grep -r "from api.models.user import PasswordResetToken" api/services/ api/routers/` | 无匹配（除 M01 自己 auth_service.py 也应该无引用，因为本期不用）|
| S6 | auth_identities.provider CHECK | 试 INSERT provider='facebook' | CHECK 约束失败（只允许 github/google） |
| S7 | users.role CHECK | 试 INSERT role='guest' | CHECK 失败 |
| S8 | users.status CHECK | 试 INSERT status='frozen' | CHECK 失败 |
| S9 | login 时填 refresh_tokens 扩展字段 | G1 登录后查 refresh_tokens 最新行 | ip 非空、user_agent 非空、device_info 可空 |

---

## 11. auth_audit_log 事件完备性（§10 呼应，Concern 2+3 独立表）

所有断言针对 `auth_audit_log` 表（**不是** M15 `activity_log`）。

| # | 事件 | 触发操作 | 验证 |
|---|------|---------|------|
| L1 | user.login_success | G1 | auth_audit_log 新 1 行；metadata.ip / metadata.user_agent 存在 |
| L2 | user.login_failed | 错密码登录 1 次 | auth_audit_log 新 1 行；metadata.email 存在；failed_count=1 |
| L3 | user.locked | 连续 5 次错 | auth_audit_log 最后 1 行 action_type=user.locked；metadata.locked_until 存在 |
| L4 | user.logout | G4 | auth_audit_log 新 1 行 |
| L5 | user.refresh_token | G3 | auth_audit_log 新 1 行 |
| L6 | user.profile_update | G5 | auth_audit_log 新 1 行；metadata.changed_fields=['name'] |
| L7 | user.password_change + user.all_tokens_revoked | G6 | 2 条事件；metadata.reason=password_change |
| L8 | user.admin_create | G7 | 1 条事件；metadata.created_by=admin_id |
| L9 | user.admin_update_role | G9 | 1 条事件；metadata 含 old_role/new_role/admin_id |
| L10 | user.admin_update_status + user.all_tokens_revoked | G10 | 2 条事件；metadata.reason=admin_disable |
| L11 | user_id 可为 NULL | L2 中 email 不存在的场景 | auth_audit_log 行 user_id=NULL；metadata.email 存字符串 |
| L12 | M15 activity_log 不被写入 | 所有 L1-L11 | `SELECT COUNT(*) FROM activity_log WHERE action_type LIKE 'user.%'` = 0（分表职责边界）|

---

## 12. Pilot 模板可复用性验证（第三轮 audit 重点）

| # | 验证项 | 预期 |
|---|-------|------|
| PT1 | "本期实现最简 + schema 都支持"模式可被复用 | 本设计稿 §3 附录 + CY 决策记录表结构可直接套给未来"横切源头"模块 |
| PT2 | ADR-004 凭据路径表可复用 | 未来引入新路径（P5/P6/P7）时只在 ADR-004 扩 1 行，不改业务模块设计 |
| PT3 | 预留 schema + CI 禁引用 机制可复用 | 其他模块遇到"预留但不实装"场景可套同样的"建表 + import 守护"双保险 |

---

## 测试执行纪律

- 每条测试在 CI 独立 DB fixture（`pytest-postgresql` 或 docker-compose `postgres-test`）
- bcrypt rounds 在测试环境下调为 4（加速）：`BCRYPT_ROUNDS_OVERRIDE=4`
- JWT_SECRET / INTERNAL_TOKEN 在 conftest.py 设置
- auth_audit_log 事件断言使用 helper `assert_audit(db, action_type, user_id=..., metadata_contains={...})`
- 禁止写 `assert_activity(action_type=LIKE 'user.%')`——M01 事件不进 activity_log（L12 明确守护这条边界）
- time-based 测试（locked_until / expires_at）使用 `freezegun`
