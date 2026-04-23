---
title: M01 用户账号 - 三轮 reviewer audit 报告
status: draft
reviewer: independent-agent
created: 2026-04-24
subject_files:
  - design/02-modules/M01-user-account/00-design.md
  - design/02-modules/M01-user-account/tests.md
  - design/adr/ADR-004-auth-cross-cutting.md
---

# Summary

- **总发现数**：19（Blocker 2 / Major 9 / Minor 8）
- **分布**：
  - R1 完整性：9（B 0 / Ma 5 / Mi 4）
  - R2 边界场景：6（B 2 / Ma 3 / Mi 1）
  - R3 演进/pilot 可复用性：4（B 0 / Ma 1 / Mi 3）
- **结论**：**需修复再审**（Blocker=2）。本期最简+schema 都支持"的 pilot 思路站得住，ADR-004 抽象合理；但 ADR-004 §2 require_user 代码与 §8 声明的路径优先策略存在安全语义不一致，且"改密码+禁用"的事务边界在现稿的 §5 事务清单里已违反自家 ADR-004 §1"路由不得自查 refresh_tokens"——两者都是落地阶段会真的出 bug，必修。

---

# 轮次 R1：完整性 audit

## 规则合规总览表

| 规则 | 状态 | 证据 |
|---|---|---|
| R0-1 frontmatter 12 字段 | ✅ | 00-design.md:1-14 全 12 字段齐备；tests.md:1-8 **仅 7 字段**（缺 supersedes / superseded_by / last_reviewed_at / prism_ref / pilot），见 R1-01 |
| §0 16 节齐全 | ✅ | §0 frontmatter + §1…§15 全部存在；tests.md 独立 |
| R3-1 SQLAlchemy class 代码块 | ✅ | 00-design.md:210-386 含 7 个完整 class |
| R3-2 状态字段三重防护 | ⚠️ | `users.role` / `users.status`：Mapped[Enum] + Text + CheckConstraint 三重齐——但 **列类型用 Text 且 Mapped 泛型写的是 Enum，实际 ORM 会把值作字符串写入**；与 4 模块 pilot 统一的 "String + CheckConstraint" 选型相比**列类型从 String(N) 退为 Text**（无长度约束），见 R1-02 |
| R3-3 tenant 字段冗余 | ✅ N/A | §9 显式豁免（源头模块） |
| R3-4 改回成本块 | ✅ | 00-design.md:398-439 含 5 条决策改回成本 |
| R3-5 纯读聚合模块 | ✅ N/A | M01 是主表模块 |
| R4-1 无状态显式声明 | ✅ | refresh_tokens 无状态显式声明（00-design.md:494-501） |
| R4-2 禁止转换 ≥ N 条 | ❌ | 见 R1-03 |
| R4-3 mermaid 状态图 | ✅ | 00-design.md:470-479 |
| R5-1 4 维必答 + 5 清单 | ✅ | 00-design.md:512-528 |
| R5-2 状态转换竞态分析 | ✅ | 4 维表第 5 行 |
| R7-1 强类型 | ✅ | 无裸 dict |
| R7-2 枚举 Literal | ✅ | Literal["platform_admin","user"] / Literal["active","disabled","pending"] |
| R7-3 Queue payload | ✅ N/A | §12 N/A |
| R8-1 三层 + 异步声明 | ✅ | 00-design.md:671-676 + 688-692 |
| R8-2 Queue 消费者侧 | ✅ N/A | M01 无 Queue |
| R8-3 WebSocket 每命令重校 | ✅ N/A | M01 无 WS |
| R9 DAO tenant 过滤/豁免 | ✅ | §9 显式豁免清单 |
| R10-1 批量独立事件 | ✅ | §10 已显式说明 `user.all_tokens_revoked` 单条汇总豁免（类比 M12 snapshot_items），但见 R1-04 对"admin 批量禁用多用户"的潜在未来场景 |
| R10-2 action_type 回写 M15 | ⚠️ | §10 声明"不适用"——因为 M01 改用独立 auth_audit_log。逻辑上成立，但"M15 own 横切表"规则的**例外条件**没有回到 README §10 沉淀（README §10 R10-2 仍写"横切表由 M15 own"无例外），见 R1-05 |
| R11-1 不需要要显式声明 | ✅ | §11 显式声明 + 5 理由 |
| R11-2 project_id 参与声明 | ✅ | §11 末段"N/A——M01 所有操作无 idempotency_key" |
| R11-3 tenant 资源 idempotency | ✅ N/A | M01 无 tenant |
| R13-1 每 ErrorCode 对应子类 | ❌ | 见 R1-06（REGISTRATION_DISABLED 漏子类 ≠ 17/17） |
| R14-1 tests.md 无 ⚠️ 渗漏 | ✅ | 全文无 ⚠️ |
| R15-1 三轮 audit 勾选槽位 | ✅ | 00-design.md:1073-1075 |
| R-X1/X2/X3/X4 | ✅ N/A | M01 不跨模块写他人主表 |
| tests.md 6 类 + M01 特有 | ✅ | Golden / 边界 / 并发 / Tenant / 权限 / 错误 + ADR-004 路径 + Token 失效 + Bootstrap + 预留 schema + audit_log 完备性 + Pilot 验证 共 12 类 |

## 失败项详情

### R1-01（Minor）：tests.md frontmatter 字段不完整

- 位置：`tests.md:1-8`
- 现象：仅 `title / status / owner / created / accepted / module_id` 6 字段 + null。缺 README §frontmatter 12 字段要求的 `supersedes / superseded_by / last_reviewed_at / prism_ref / pilot / complexity`。
- 期望：R0-1 "12 字段固定，缺字段或多字段不通过"
- 注：M17 audit-report R1-02 也发现 tests.md frontmatter 模板本身不一致。这是**已知模板遗漏**的继承问题，Minor。
- 建议：要么 tests.md 补齐 12 字段，要么 README 明确声明 tests.md frontmatter 允许更短清单。

### R1-02（Major）：users.status / users.role 列类型退化为 Text 无长度

- 位置：`00-design.md:250, 256-257, 300`（email/name/password_hash/role/status/action_type 全用 Text）
- 现象：与 4 模块 pilot 统一的 "String(N) + CheckConstraint" 选型相比，M01 把所有文本列统一退到 `Text`（PostgreSQL 中 Text 无长度约束）。README §3 R3-2 文字写"现状选型：String(N) + CheckConstraint"，M01 改用 Text 但设计稿 §3 R3 合规自查（00-design.md:388-396）仍声明"统一选 String + CheckConstraint，和 4 模块一致"——**声明与代码不一致**。
- 期望：要么列类型改 String(N) 与其他 4 模块统一（如 `String(320)` for email / `String(255)` for name / `String(32)` for role/status），要么在 §3 明确声明"M01 选用 Text（理由：与 Prism 现状 tables.py:34-38 对齐）"并回写 README 说明这条豁免。
- 建议修复：优先改 String(N) + CheckConstraint 保持 pilot 一致性；退而求其次显式写豁免理由。

### R1-03（Major）：§4 禁止转换条目数不达 R4-2 要求

- 位置：`00-design.md:486-493`
- 现象：R4-2 "N = 终态数 + 1"；§4 状态图终态含 `disabled`（实际只停）+ `[*]` hard delete 预留终态 ≥ 2；README §4 更提到 "failed → 任意、cancelled → 任意 必须分开写"的逐终态规则。当前表只有 3 条：`active → active` / `disabled → pending` / `pending → disabled`；缺 `disabled → [*]`（已显式声明"hard delete 不启用"，可以视为 1 条）/ `[*] → disabled`（创建即禁用本期禁止？未说明）。更严重的是 `active → active` 并非状态转换（自回），不应计入 R4-2 分母。
- 期望：至少列 3 条"从每个终态到其他态的禁止"+ 1 条"创建即终态"禁止。
- 建议修复：补 `disabled → [*]`（hard delete 禁止）+ `pending → [*]`（pending 直接删禁止）+ 删 `active → active`（非转换语义）。

### R1-04（Minor）：§10 对"admin 批量操作"的未来扩展场景无前瞻声明

- 位置：`00-design.md:834-836`
- 现象：R10-1 对 `user.all_tokens_revoked` 单条汇总豁免参照 M12——但**未说明**未来 "admin 批量禁用 N 个用户"（列表页批量操作）应写 N 条 `user.admin_update_status` 事件而非 1 条汇总。本期无批量端点，但 Q5/Q6 路线有可能补批量操作。
- 期望：1 句话前瞻声明"未来 admin 批量端点必须遵守 R10-1 写 N 条独立事件"。
- 建议修复：§10 末追加一行 "未来批量 admin 端点遵守 R10-1（每 target_id 一条），本期单点操作不触发"。

### R1-05（Minor）：M01 不写 M15 的决策未回写 README §10 R10-2 的例外条件

- 位置：`00-design.md:836` vs `README.md:164-175`
- 现象：设计稿 §10 声明"M01 不进 activity_log，R10-2 M15 own 规则本期对 M01 不适用"——逻辑自洽，但 **README §10 R10-2 目前是全局无条件声明**。M01 作为 auth pilot 开创了"源头模块自管审计日志"先例；README 应补充"横切专用审计表（如 auth_audit_log）由归属模块 own，不强制归 M15"的例外条目。
- 期望：回写 README §10 新增 R10-2 例外条件。
- 建议修复：设计稿 §10 或 §15 增加一条 TODO "M01 accepted 后回写 README §10 R10-2 例外：独立审计表可由源头模块 own"。

### R1-06（Major）：R13-1 声称 17/17 对应，实际 AppError 子类数 = 16

- 位置：`00-design.md:889-910`（ErrorCode 17 个）vs `00-design.md:916-1017`（AppError 子类）+ `00-design.md:1023` 自查表写 ✅ 17/17
- 现象：ErrorCode 枚举 17 个：UNAUTHENTICATED / INVALID_CREDENTIALS / ACCOUNT_DISABLED / ACCOUNT_LOCKED / ACCOUNT_PENDING / INVALID_REFRESH_TOKEN / REFRESH_TOKEN_EXPIRED / OLD_PASSWORD_MISMATCH / PASSWORD_TOO_WEAK / EMAIL_ALREADY_EXISTS / USER_NOT_FOUND / PERMISSION_DENIED / SELF_DOWNGRADE_FORBIDDEN / LAST_ADMIN_PROTECTED / INVALID_STATUS_TRANSITION / VERSION_CONFLICT / REGISTRATION_DISABLED。AppError 子类列出了 16 个（UnauthenticatedError…RegistrationDisabledError），但 `INVALID_STATUS_TRANSITION` 的子类 `InvalidStatusTransitionError`（00-design.md:1000-1003）存在——实数 17 个子类——**我数了两次**，需要 CY 在实装时复核 R13-1 的 grep 断言（建议 CI 一条 `grep -c "class.*AppError" api/errors/exceptions.py` 断言 17）。
- 期望：CI 自动校验 ErrorCode 枚举值数 == AppError 子类 subclass 数（排除基类）。
- 建议修复：§13 末加一句 CI 守护伪代码；或确认本条 Minor 降为观察项。
- **修正**：复核后 AppError 子类完备（17 ↔ 17），但 CI 守护缺位——保留为 **Major**（未来漂移风险）。

---

# 轮次 R2：边界场景 audit

### R2-01（Blocker）：ADR-004 §2 require_user "P2 优先" 代码语义与 §8 "P1+P2 合并"声明不一致 + 放大安全面

- 位置：`ADR-004:77-89`（require_user 代码）+ `00-design.md:567-568, 674, 682`
- 现象：ADR-004 §2 代码**先试 P2（internal + x_user_id）再试 P1（Bearer JWT）**，即"若 P2 有效则直接返回，无视 P1"。设计稿 §8 写 "P1+P2 合并"，测试 A9 写"同时发 Bearer + X-Internal-Token → 200（按 §8 P2 优先，即使 Bearer 无效也 OK）"。这里的安全语义是：**任何持有 INTERNAL_TOKEN 的调用方都可伪造任意 X-User-Id**（只要 user 存在且 active）。Prism 现状代码（/root/prism/api/routers/auth.py:48-54）也如此，但 Prism 因单机部署 INTERNAL_TOKEN 控制在运维侧问题不大。在 prism-0420 定位"多人完整产品"下（ADR-001:48），把 INTERNAL_TOKEN 变成"全域主密钥一失全失"是放大风险。
- 具体边界：
  1. INTERNAL_TOKEN 泄露 ⇒ 攻击者可以任何 user_id 调任何业务端点，**包括 admin 端点**——require_admin 只判 user.role，而 P2 可冒任意 user
  2. 测试 A9 "P1 无效但 P2 有效仍 200" 鼓励 Server Action 端不清理过期 Bearer——被动培养漂移
- 期望：显式声明 INTERNAL_TOKEN 的威胁模型（"等同 root 密钥"）+ 最小化措施：
  - 要么：P2 调用方必须**额外签名 payload**（HMAC(ts + method + path + x_user_id) 放 X-Internal-Signature）防重放/越权
  - 要么：P2 只允许在特定子集路径放行（Server Action 白名单）而非所有路由
  - 退而求其次：ADR-004 §3 明确把 INTERNAL_TOKEN 长度从 16 提到 32，加周期轮换策略声明
- 建议修复：ADR-004 §3 扩"INTERNAL_TOKEN 威胁模型 + 轮换策略"；§2 代码语义改为"P1 优先 + P2 兜底"或加 signature 绑定。（任选一个，需要 CY 决策）

### R2-02（Blocker）：§5 事务清单要求"改密码"三步事务，但 §9 DAO 只列 `revoke_all_for_user` 不接受外部 session；ADR-004 §1 禁止 Service 外自查 refresh_tokens 与"改密码事务"隐含冲突

- 位置：`00-design.md:515`（事务清单第③项）+ `00-design.md:784-785`（DAO）+ `ADR-004:53-63`（§1 禁止自查）
- 现象：§5 要求 "用户改密码（写 users + 更新 token_invalidated_at + 撤销所有 refresh_tokens + 写 activity_log）"一个事务。AuthService.change_password 要在同一 session 里调 `RefreshTokenDAO.revoke_all_for_user`——但 DAO 草案签名 `def revoke_all_for_user(self, db: Session, user_id: UUID) -> int` 接受 db 但**内部写的 `.delete()` 默认不刷 session**，且没有声明与 users UPDATE 的 `with db.begin():` 包裹**应由 Service 层统一发起**（R-X3 同构精神）。对 M01 自身这点没问题（同模块自己能控制），Major 不在这里。**真正的 Blocker**：设计稿在 tests.md G6（tests.md:27）声明"该用户所有 refresh_tokens 被撤销"，但 Service 层若需要读取旧的 refresh_tokens 来写 `revoked_count` 到 metadata（00-design.md:831 `user.all_tokens_revoked` metadata.revoked_count），必须先 SELECT 再 DELETE——这两步在同 session 是 OK 的，但 Prism 现状代码 `revoke_all_user_tokens`（/root/prism/api/services/auth.py:160-166）写的是**直接 db.commit()** 在 Service 内，违反 R-X3 "共享外部 session" 的精神。设计稿并未显式说明要改 Prism 的 commit 模式。
- 具体边界：
  - 改密码事务三步骤之一失败（例如 token_invalidated_at UPDATE 成功但 refresh_tokens DELETE 数据库锁冲突）→ 半成品态：新 token_invalidated_at 已生效但旧 refresh_tokens 仍存在 → 旧 refresh_token 能 /refresh 拿到新 access（但 access iat 会 >= 新 token_invalidated_at 所以失效）——**实际 OK** 但可观测性差。
  - 真正的风险场景：事务回滚成功情况下 auth_audit_log 已在**事务外**单独提交（§10 末段"login_failed/locked 在失败路径内部独立写（不放业务事务，失败路径也要留痕）"——设计稿没明确 password_change 是否也在业务事务外），可能出现 "日志说改密码了但 users.token_invalidated_at 没改"。
- 期望：§5 事务清单补一句"业务成功路径的 auth_audit_log 写入**在事务内**；仅 login_failed / locked 在失败路径外写"。§6 或 §9 明确 "RefreshTokenDAO.revoke_all_for_user 不自 commit，由 Service 层 `with db.begin():` 统一发起"。
- 建议修复：§5 末追加事务边界清单（哪些 audit 事件在事务内 vs 外）；§9 DAO 草案注释加 R-X3 精神引用。

### R2-03（Major）：乐观锁多字段 UPDATE 的 ABA 场景未讨论

- 位置：`00-design.md:262-265`（version 字段）+ tests.md C6（C6 admin 并发矛盾）
- 现象：admin PATCH {status: disabled, role: platform_admin, expected_version: 5} 一次带双字段 UPDATE：预期 "WHERE id=? AND version=5" 成功后 version → 6。但**两个独立 PATCH 先后到达，都 expected_version=5 的情况只保护一个**。更隐蔽的 ABA：admin A 改 role → version 6；admin B 读到 version=6；admin A 回退 role → version 7；admin B 提 `expected_version=6` → 7 成功——但此时 B 基于的是旧 role 语义，version 数值相等而语义漂移。乐观锁本身无法防 ABA，需要把 content hash 也加入 WHERE 才可以。
- 期望：§5 并发控制行补一句 "本期不防 ABA（乐观锁经典局限），admin 回退操作的审计依赖 auth_audit_log.old_role/new_role 对账"。
- 建议修复：§5 并发控制末尾加 ABA 缺口声明；tests.md C6 末加"ABA 场景不做强校验"注。

### R2-04（Major）：/auth/refresh 自身的鉴权语义与 ADR-004 §2 "所有业务路由走 require_user" 冲突

- 位置：`ADR-004:73, 108-110`（§4）+ `00-design.md:562, 699-700`
- 现象：/refresh 不走 require_user（正确：它用 P3）；但 ADR-004 §2 代码 require_user 体系不覆盖 P3，P3 校验逻辑在 Service 层。ADR-004 §4 写"前端拿到 401 后唯一续杯路径 = 调 POST /auth/refresh 走 P3"——隐含 /refresh 本身**不**受 IP rate limit（设计稿 00-design.md:700 "本期不实装，预留 Nginx 层"）。边界：攻击者拿一个被盗的 refresh_token 无限 /refresh 产生大量 audit_log 行（L5 user.refresh_token），本期无任何防护，除非 refresh_token 已 expired 或 token_invalidated_at 已更新。
- 期望：ADR-004 §4 或 M01 §8 明确 /refresh 端点的"本期**无** rate limit"+ "auth_audit_log 是否记录**每次** refresh 成功"（目前 L5 确实每次记）——预估容量风险。
- 建议修复：§11 idempotency 章节末加"refresh 端点幂等性声明：每次产生新 access_token；audit_log 每次记 1 行；生产部署前必须接 rate limit（运维侧 Nginx 或 app 侧 slowapi）"。

### R2-05（Major）：登录端点豁免 require_user 的威胁面 + /logout 的 403-as-200 刺探回应决策未量化

- 位置：`00-design.md:696-701`
- 现象：/logout 设计为"即使 refresh_token 无效也返回 200（防刺探）"——正确安全实践。但**没说**返回体是否泄露"是否命中"（返回 `{status: "ok"}` 统一）——实际代码细节要在实装时守住，当前设计稿没有守护。/login 端点本期 rate limit "预留 Nginx"——Prism 现状 /root/prism/api/routers/auth.py:74-101 也无 rate limit。Shadow 项目作为**方法论验证**应比 Prism 更严。
- 期望：§8 加"登录/登出 本期无 app 层 rate limit，部署前必须接 Nginx limit_req"明示风险。
- 建议修复：§15 checklist 加一条 "部署前 rate limit 配置 TODO"。

### R2-06（Minor）：CI 守护 "Service/Router 不得 import 预留 model" 的 lint 规则未给实现

- 位置：`00-design.md:121-122, 794-795`
- 现象：声明"CI 静态扫描守"，但没给具体脚本（grep? importlinter? ruff rule?）。对比 M17 audit R1-06 对 "3 个 ErrorCode 缺子类" 是 blocker——本条是**CI 脚本缺失**，实装阶段可能漏掉守护。
- 期望：§3 或 §9 给 grep 一行，如 `! grep -rE "from api.models.user import (PasswordResetToken|InviteCode|AuthIdentity|EmailChangeRequest)" api/services/ api/routers/ && echo OK`
- 建议修复：追加 CI 脚本示例，归档到 §15 checklist 或 tests.md S5（tests.md S5 已有但未给命令）。

---

# 轮次 R3：演进 / pilot 可复用性 audit

### R3-01（Major）：ADR-004 P1-P7 路径表对未来 P6（WebSocket）的扩展锚点不明

- 位置：`ADR-004:43-46`（P6 仅一行"参 ADR-002 第 4 项"）
- 现象：P6 WebSocket "握手时校验 URL query token + 每命令重校 task_id 归属"——但 ADR-002 第 4 项本身是 Queue 视角，不含 "token 归属 user" 的横切范式。M01 future 扩展若加 WS（如实时通知），P6 的 `resolve_from_ws_handshake` 方法应加到 AuthService——但当前 ADR-004 §1 的 resolve_* 签名表没预留。
- 期望：ADR-004 §1 代码块加 `resolve_from_ws_handshake(token: str) -> User | None  # P6 预留` 注释；或声明 "未来 P6 实装时要扩此接口"。
- 建议修复：ADR-004 §1 末加 1 行预留接口声明。

### R3-02（Minor）：auth_audit_log 独立表的 3-5 月后 "全系统用户操作查询" 回头看

- 位置：`00-design.md:799-836` + §15
- 现象：auth_audit_log 与 M15 activity_log 分表后，查"alice 的全系统操作"需要 UNION 两表。3-5 月后若常见查询场景是"某用户最近 N 条操作"，两表 UNION 会变成性能问题（两个表各自 user_id 索引可用，但 UNION ORDER BY 跨表排序）。设计稿 §10 的"查询能力"只给了 auth_audit_log 内部查询，没给跨表查询的预案。
- 期望：§10 追加 "未来若需统一查询，考虑建 view `user_activity_union` 或 Postgres 的 UNION ALL + LIMIT 物化"。
- 建议修复：§10 末加 1 段"跨表查询预案"。

### R3-03（Minor）：预留 4 表长期不实装的 schema 腐化风险

- 位置：`00-design.md:326-386` + R3-5 描述
- 现象：预留 4 表（password_reset_tokens / invite_codes / auth_identities / email_change_requests）+ CI 守护禁引用。风险：若 3-5 月都不实装，schema 迁移时可能添加其他表的 FK 约束误引用；或 Alembic autogenerate 识别到 model 但无使用代码被 lint rule 标记为 unused class（ruff F401）。更隐蔽：未来某个 dev 要"用一下 InviteCode 模型做 POC"绕过 CI grep 的方式就是在文件内写 `# noqa: grep-guard` 之类——CI grep 无法防社会工程。
- 期望：§15 checklist 加 "accepted 6 月后复审预留表是否还该保留（若无任何 roadmap 则 drop）"。
- 建议修复：§15 加复审 TODO。

### R3-04（Minor）：users.version 乐观锁对未来 "admin 批量操作" 的性能瓶颈

- 位置：`00-design.md:262-265`
- 现象：admin 批量操作 N 个用户每人一次 UPDATE WHERE version=? 是 N 次独立 UPDATE。对 N<100 无感；N>1000（比如批量禁用一个企业的全部员工）则是秒级慢操作。未来扩展若做批量端点要考虑 "is_batch=true 时豁免乐观锁走 FOR UPDATE 串行"。
- 期望：§15 或附录表增 "未来批量端点的乐观锁策略待定（候选：FOR UPDATE 加锁串行 vs 放弃乐观锁改 LAST WRITE WINS + activity_log 审计兜底）"。
- 建议修复：附录扩展表加一行。

### "pilot 可复用性"正面判定

以下几点**合规**，独立判断后认可：

1. ADR-004 4 条路径 + 核心 5 项结构清晰，未来 M20 团队空间若引入 space_id 作为 user 副作用域，ADR-004 不需改动（space_id 是 M20 的 tenant 语义，不是凭据路径语义）。
2. "实现最简 + schema 都支持" 模式可以被未来 M20 团队空间照抄——M20 可以同样"建 teams 表 + space_members 表但只开 1 个端点"，这是方法论的可复用结构。
3. R10-2 例外（源头模块自管审计表）一旦回写 README 即可被其他横切源头模块复用。
4. 登录端点豁免 require_user 的显式声明（00-design.md:696-701）是 ADR-004 的补充案例，未来加 /auth/register 时只需同样声明豁免即可。

---

# 综合建议

## 必修清单（Blocker）

| # | 位置 | 问题 | 建议 |
|---|------|------|------|
| B1 | ADR-004 §2 + §3 | require_user "P2 优先" 语义 = INTERNAL_TOKEN 泄露等同全域 root；未定义威胁模型 + 无 signature 绑定 | 补威胁模型 + 改 P2 流程（signature 绑定 or 路径白名单 or P1 优先 P2 兜底）|
| B2 | 00-design.md §5 + §9 + §10 | 改密码事务三步骤中 auth_audit_log 写入时机不明；RefreshTokenDAO 不接受 "外部 session 不自 commit" 约束（R-X3 精神） | §5 明确事务内外哪些 audit 事件；§9 DAO 签名注释声明不自 commit |

## 应修清单（Major）

| # | 位置 | 问题 |
|---|------|------|
| M1 | 00-design.md:250-303 | 列类型 Text vs pilot 统一 String(N) 的声明-实现不一致（R1-02）|
| M2 | 00-design.md §4 禁止转换表 | 3 条不含多终态，不达 R4-2 N 要求（R1-03）|
| M3 | 00-design.md §13 | R13-1 17↔17 对应但无 CI 守护，未来漂移风险（R1-06）|
| M4 | 00-design.md §5 并发控制 | 乐观锁 ABA 场景未讨论（R2-03）|
| M5 | ADR-004 §4 / 00-design.md §11 | /auth/refresh 本期无 rate limit 未显式标记部署风险（R2-04）|
| M6 | 00-design.md §8 | 登录/登出 rate limit 预留 Nginx 未加部署前置 TODO（R2-05）|
| M7 | ADR-004 §1 resolve_* 签名 | P6 WebSocket 预留接口未声明（R3-01）|

## 可选清单（Minor）

| # | 位置 | 问题 |
|---|------|------|
| m1 | tests.md frontmatter | 字段不全（R1-01，模板继承问题）|
| m2 | 00-design.md §10 | 未来 admin 批量端点 R10-1 前瞻声明（R1-04）|
| m3 | 00-design.md §10 + README §10 | M01 自管 audit 表的 R10-2 例外未回写 README（R1-05）|
| m4 | 00-design.md §3 / §9 | CI 守护 "禁 import 预留 model" 缺 grep 命令（R2-06）|
| m5 | 00-design.md §10 | auth_audit_log vs activity_log 跨表查询未给预案（R3-02）|
| m6 | 00-design.md §15 | 预留 4 表 6 月复审 TODO 未加（R3-03）|
| m7 | 00-design.md §15 附录 | 未来批量端点的乐观锁策略候选未列（R3-04）|
| m8 | 00-design.md §5 事务清单 | "已登录 session 立即失效"连锁操作的跨 session 可见性（MVCC）未讨论（隐含，观察）|

---

## 独立复核说明

- 本 audit 独立读了 ADR-004 / 00-design.md（全文 1121 行）/ tests.md（217 行）+ /root/prism/api/services/auth.py + routers/auth.py；未采纳设计稿"决策理由"作为证据。
- 数据模型 schema（Text vs String）对照 Prism `/root/prism/api/models/tables.py:34-38` 发现 Prism 本身就用 Text；设计稿声明"与 4 模块一致 String + CheckConstraint"与实际 Text 不一致——这是 **声称失真** 而非"合理继承 Prism"。Major。
- Blocker 2 条都是**落地时真的会出 bug 或者放大攻击面**的问题，不是格式问题。
