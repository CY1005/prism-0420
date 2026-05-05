---
title: 全局命名空间登记
status: draft
owner: CY
created: 2026-05-06
trigger: full-reconcile-pass.md S-A1/A2/A3 + contracts-draft.md 契约 3
purpose: 全项目共享标识符的单一真相源
---

# 全局命名空间登记

> 单一真相源。所有模块新增标识符前先查本表，新增后必须登记一行。

## 0. 状态说明

- **数据**：从 design/02-modules/M*/00-design.md + design/adr/*.md 自动提取（2026-05-06）
- **命名规范段**：✅ 业界标准调研已整合（Stripe / GitHub / Google AIP-193 / FastAPI 官方 / Greg Young 事件溯源）
- **违规标记**：⚠️ 标 = 与新规则冲突；走 baseline-patch 批量修订
- **完整性**：业务代码 0 行 / DB 0 数据 / 前端 0 消费 → **直接重命名零代价**

## 0.1 4 条核心规则一句话版

| # | 规则 | 一句话 |
|---|------|--------|
| **N1** | ErrorCode | Python enum 名 UPPER_SNAKE，**enum value 全小写** `entity_verb` snake（如 `user_not_found`），直接作 next-intl i18n key |
| **A1** | ActionType | `{entity}_{past_verb}` snake_case（如 `cold_start_completed`），CRUD 与特定动作统一格式，禁 dot/命令式 |
| **Q1-Q2** | Queue Task | `{module}_{action}` snake，与 Python 函数名 1:1，cron 任务用 SYSTEM_USER_UUID |
| **S1-S5** | Pydantic Schema | `XxxBase / XxxCreate / XxxUpdate / XxxPublic` (FastAPI 官方风格)，禁 `XxxIn/XxxOut/XxxRequest/XxxResponse` |

## 0.2 修订总账（PRISM-0420）

| 类型 | 当前 | 新规约 | 修订量 | 状态 |
|------|-----|-------|------|-----|
| ErrorCode enum value | 125 条 UPPER_SNAKE | 全改 lower_snake | 161 处 string 值修改（21 文件）| ✅ 2026-05-06 baseline-patch |
| ActionType（CRUD 通用）| 10 条单词原型 | 拆为每实体独立过去式 | 删 10 + 加 33（按各 TargetType 适用动词）| ✅ 2026-05-06 baseline-patch |
| ActionType（dot.notation）| 14 条 | 全改 snake 过去式 | 14 条修订 | ✅ 2026-05-06 baseline-patch |
| Queue task name | 6 个 Payload class（无函数名）| 加 task 函数名映射 | M01 实施时落地 | ⏳ 待 M01 |
| Pydantic schema | 0 条（无业务代码）| M01 实施按规范 | 无历史修订 | ⏳ 待 M01 |
| ADR-002 边界 | 未规约 cron user_id | 加 SYSTEM_USER_UUID 常量条款 | ADR-002 § 1 加段 | ✅ 2026-05-06 |

**baseline-patch 落地**：见 commit `baseline-patch ErrorCode value + ActionType CRUD split + dot→snake`。

---

## 1. ErrorCode 全局命名空间

### 1.1 命名规范

**业界标杆**：Stripe（`account_invalid` 实体前缀小写）/ GitHub REST API（`missing_field` 小写 snake）/ Google AIP-193（语义前缀 + domain 字段）/ RFC 9457 Problem Details / AWS SDK。Stripe 是最贴近"纯字符串 code"场景的标杆。

**N1（核心规则）**：实体前缀 + 全小写 snake_case，**enum value 全小写**

| 项 | 规则 |
|----|-----|
| Python enum 名（左侧）| UPPER_SNAKE_CASE（符合 PEP 8 常量风格）|
| **Enum value（右侧 / HTTP body code 字段）**| **全小写 snake_case 含实体前缀**（如 `user_not_found`）|
| 实体前缀 | 必须 — 直接作前端 next-intl i18n key，1:1 映射，无歧义 |
| 横向通用码 | 仍保留（INTERNAL_ERROR / VALIDATION_ERROR / CONFLICT 等）；模块特化优先用前缀化 |

**N2 配额超限**：`{entity}_{action}_quota_exceeded`（HTTP 429）。横向 RATE_LIMITED 仅指调用频率限制。

**N3 权限拒绝**：通用情况用横向 `permission_denied`；模块特殊语义（业务规则不允许）用 `{entity}_{action}_forbidden` 或 `{entity}_{constraint}_protected`。

**N4 认证错误**：全用横向通用码 `unauthenticated` / `access_token_expired` / `refresh_token_expired` / `account_locked`，模块不重定义。M01 design 内对应 enum 重新声明的视为 wrap，标注来源。

**N5 乐观锁冲突**：横向通用 `version_conflict`。**业务"版本"概念（如 M05 版本时间线）禁用 VERSION 前缀**——改用 `version_record_*`（与 TargetType 一致）。

**修订当前 125 条码**：enum 名保持 UPPER_SNAKE，**enum value 全部从 UPPER_SNAKE 改成 lower_snake**（HTTP body 改造）。业务代码 0 行 / 前端未消费 → 直接 baseline-patch。

**来源**：
- [Stripe Error Codes](https://docs.stripe.com/error-codes)
- [Google AIP-193 Errors](https://google.aip.dev/193)
- [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html)

### 1.2 通用码登记（横向 owner：api/errors/codes.py）

| code | http | 用途 | 复用规则 |
|------|------|------|---------|
| INTERNAL_ERROR | 500 | unhandled fallback | 模块禁直接 raise；middleware 兜底用 |
| NOT_FOUND | 404 | 通用资源未找到 | 待 N1 规则定稿（前缀化 vs 复用）|
| PERMISSION_DENIED | 403 | 通用权限拒绝 | 待 N3 规则定稿 |
| VALIDATION_ERROR | 422 | 输入校验失败 | 模块直接复用 |
| CONFLICT | 409 | 通用冲突 | 模块直接复用 |
| RATE_LIMITED | 429 | 调用频率限制 | 仅频率；配额用 N2 |
| UNAUTHENTICATED | 401 | 未认证 | 复用 N4 |
| ACCESS_TOKEN_EXPIRED | 401 | access token 过期 | 复用 N4 |
| REFRESH_TOKEN_EXPIRED | 401 | refresh token 过期 | 复用 N4 |
| ACCOUNT_LOCKED | 423 | 账号锁定 | 复用 N4 |

**总计**：10 个（含 INTERNAL_ERROR）

### 1.3 模块特化码登记（125 条）

> 自动提取自 design/02-modules/M*/00-design.md。每条 owner = 模块 ID。命名规范遵守度待 N1-N5 定稿后批量审计。

**M01**:

| code | http/note |
|------|-----------|
| UNAUTHENTICATED | 401 |
| INVALID_CREDENTIALS | 401 登录邮箱/密码错误（不暴露具体原因） |
| ACCOUNT_DISABLED | 403 |
| ACCOUNT_LOCKED | 423 |
| ACCOUNT_PENDING | 403（Q1 预留） |
| INVALID_REFRESH_TOKEN | 401 |
| REFRESH_TOKEN_EXPIRED | 401 |
| OLD_PASSWORD_MISMATCH | 400 改密码时旧密码错 |
| PASSWORD_TOO_WEAK | 422 |
| EMAIL_ALREADY_EXISTS | 409 |
| USER_NOT_FOUND | 404 |
| PERMISSION_DENIED | 403（require_admin 失败） |
| SELF_DOWNGRADE_FORBIDDEN | 400 admin 改自己 role |
| LAST_ADMIN_PROTECTED | 400 禁用最后一个 admin |
| INVALID_STATUS_TRANSITION | 400 |
| VERSION_CONFLICT | 409 Concern 1：乐观锁失败 |
| REGISTRATION_DISABLED | 403 Q1 预留（本期开放注册未启用时的稳定错误码） |

> ⚠️ M01 重声明了横向 UNAUTHENTICATED / ACCOUNT_LOCKED / REFRESH_TOKEN_EXPIRED / PERMISSION_DENIED / VERSION_CONFLICT —— 待 N3/N4/N5 规则定稿后决定是否清理（横向已有 → 模块不再登记）

**其他 19 模块特化码（共 108 条）**：

按模块分组的完整登记自动生成至 [`namespace-data/errorcodes-full.md`](./namespace-data/errorcodes-full.md)（待生成）。本节仅展示 M01 作为示例。

---

## 2. ActionType / TargetType 全局命名空间（owner：M15）

### 2.1 命名规范

**业界标杆**：Greg Young / Vaughn Vernon 事件溯源经典文献 + Apache Kafka 社区实践收敛到 **snake_case 过去时**。CloudEvents 反向 DNS（`com.example.*`）适合跨组织事件总线，对单系统 DB enum 过重。AWS EventBridge Title Case 是控制台 label，不适合机器存储。

**A1（核心规则）**：`{entity}_{past_verb}` snake_case 过去时——**所有 ActionType 统一**，CRUD 与模块特定动作不分两套

| 类型 | 当前现状 | 新规约 |
|------|---------|-------|
| 通用 CRUD | `create / update / delete`（10 条单词原型，靠 target_type 区分实体）| **拆开为每实体独立**：`user_created / project_created / node_created / dimension_record_created / ...`（按 14 个 TargetType 各一）|
| 模块特定（dot 风格）| `cold_start.create / snapshot.create / import.create`（14 条 ⚠️）| `cold_start_completed / snapshot_created / import_completed`（snake 过去式）|
| 模块特定（snake 过去式）| `team_created / team_renamed / ...`（10 条 ✅ 已合规）| 保留 |
| _triggered 后缀 | `embedding_model_upgrade_triggered`（2 条）| 保留——`_triggered` 用于"已触发但未完成"语义，是过去式合法变体 |

**A2 命名约束**：
- 全小写，下划线分隔
- 过去时动词结尾（`_created` / `_completed` / `_failed` / `_changed` 等）
- 实体在前
- **禁止命令式**（如 `create_user`）——activity log 记录已发生事实，命令式语义错误
- **禁止 dot.notation**——单系统 DB enum 用 snake 即可

**A3 字段查询便利**：所有 ActionType 使用同一格式后，DB 单字段 `WHERE action_type LIKE 'user_%'` 可查所有 user 操作；不需要 `(action_type, target_type)` 双字段拼。

**修订工作量**：M15 enum 41 条 → 改造后约 50-60 条（拆 CRUD 10 条 → 14 条 × N entity）。修订时机：等 contracts-draft 契约 1+3 落地后做 baseline-patch。

**来源**：
- [CloudEvents Spec](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)
- [AWS EventBridge event structure](https://docs.aws.amazon.com/eventbridge/latest/userguide/event-reference.html)
- [How to name events in EDA](https://richygreat.medium.com/how-to-name-events-in-event-driven-architecture-cc962d93ed60)

### 2.2 ActionType 登记（baseline-patch 2026-05-06 → 56 条统一 snake 过去式）

> 提取自 design/02-modules/M15-activity-stream/00-design.md `class ActionType`。
> 全表统一 `{entity}_{past_verb}` 风格——无通用 CRUD、无 dot.notation。

| 模块 | enum 名 / value（一致）| 备注 |
|-----|------------------------|------|
| M01 | user_created / user_updated / user_deleted | |
| M02 | project_created / project_updated / project_archived / project_deleted | |
| M02 | project_member_invited / project_member_role_updated / project_member_removed | 替原 invite_member / update_member_role / remove_member |
| M02 | project_dimension_config_updated / project_ai_provider_updated | |
| M03 | node_created / node_updated / node_deleted / node_reordered / node_moved | 替原通用 reorder / move |
| M04 | dimension_record_created / dimension_record_updated / dimension_record_deleted | |
| M05 | version_record_created / version_record_updated / version_record_deleted | |
| M06 | competitor_created / competitor_updated / competitor_deleted | |
| M06 | competitor_ref_created / competitor_ref_deleted | |
| M07 | issue_created / issue_updated / issue_deleted | |
| M07 | issue_status_changed / issue_orphaned | 替原通用 status_change / orphan |
| M08 | module_relation_created / module_relation_deleted | |
| M11 | cold_start_created / cold_start_completed / cold_start_failed | dot.notation 改 snake |
| M12 | comparison_snapshot_created / comparison_snapshot_renamed / comparison_snapshot_deleted | dot.notation `snapshot.*` → 实体前缀 + snake |
| M17 | import_created / import_status_changed / import_ai_step_completed / import_review_confirmed | dot.notation 改 snake |
| M17 | import_batch_inserted / import_canceled / import_failed / import_partial_failed | |
| M18 | embedding_model_upgrade_triggered / embedding_backfill_triggered | _triggered 是过去式合法变体（已触发但未完成）|
| M20 | team_created / team_renamed / team_description_changed / team_deleted | |
| M20 | team_member_added / team_member_removed | |
| M20 | team_member_promoted_admin / team_member_demoted_member | 字面命名，半年回看（README 2026-10-26）评估合并为 role_changed |
| M20 | project_joined_team / project_left_team | |

**baseline-patch 2026-05-06 变更摘要**：
- 删除 10 条通用 CRUD（create / update / delete / import_ / analyze / archive / reorder / move / status_change / orphan）
- 删除 5 条 M02 命令式 snake 原型（invite_member 等）→ 改为实体前缀 + 过去式
- 14 条 dot.notation（cold_start.* / snapshot.* / import.*）→ 全改 snake 过去式
- 总数：41 → 56；风格：4 种 → 1 种统一

### 2.3 TargetType 登记（14 条）

| target_type | owner |
|-------------|-------|
| node | M03 |
| dimension_record | M04 |
| version_record | M05 |
| competitor | M06 |
| competitor_ref | M06 |
| issue | M07 |
| project | M02 |
| project_member | M02 |
| project_dimension_config | M02 |
| module_relation | M08 |
| cold_start_task | M11 |
| comparison_snapshot | M12 |
| import_task | M17 |
| team | M20 |

**风格**：全 snake_case 单词或 snake_case 复合词，统一 ✓ 无违规。

---

## 3. Queue / Task 命名空间

### 3.1 命名规范

**业界标杆**：Celery 文档（`module.task_name` 点分）/ arq（函数名字符串，惯例 snake）/ Kafka 社区（点分或 snake 二选一不混用）。arq 的 task name 就是 Python 函数名字符串——函数名不能含 `.`，因此 PRISM 用 arq → 应统一 snake_case，不用点分。

**Q1 TaskPayload class**：`{Entity}{Action}Payload`（PascalCase + Payload 后缀），如 `ImportExtractPayload` / `EmbedSinglePayload` ✅ 已合规。

**Q2 arq task 函数名 = Queue 内部 task 标识符**：`{module}_{action}` snake_case，与 Python 函数名 1:1。例：

| Payload class（PascalCase）| arq task 函数 / Queue 标识（snake）|
|---|---|
| ImportExtractPayload | `import_extract` |
| ImportAIStepPayload | `import_ai_step` |
| ImportBatchInsertPayload | `import_batch_insert` |
| EmbedSinglePayload | `embed_single` |

**Q3 cron 触发任务的 user_id 边界规约**（解 contracts-draft S-C2）：

cron / 系统触发的任务（M16 zombie cleanup / M18 embedding backfill）payload 中 `user_id` 字段：

- 用常量 `SYSTEM_USER_UUID = UUID("00000000-0000-0000-0000-000000000000")`（保留 UUID，永不分配给真实用户）
- 在 `api/queue/base.py` 定义为公共常量
- payload 校验时若 `user_id == SYSTEM_USER_UUID` 则跳过权限校验链中的 user-scoped 检查
- Activity log 写入时 user_id 字段直接写常量，前端展示为"系统"

**回写 ADR-002**：在 ADR-002 § 1 加边界条款 "cron 触发任务 user_id 必须用 SYSTEM_USER_UUID 常量"。

**来源**：
- [Celery Tasks documentation](https://docs.celeryq.dev/en/stable/userguide/tasks.html)
- [arq documentation](https://arq-docs.helpmanual.io/)
- [Confluent — Kafka Topic Naming](https://www.confluent.io/learn/kafka-topic-naming-convention/)

### 3.2 TaskPayload class 登记（6 条）

| class | owner | 触发 | user_id 来源 |
|-------|-------|------|------------|
| TaskPayload | api/queue/base.py（**待建** — 闸门 2.6）| 基类 | — |
| ImportExtractPayload | M17 | 用户上传 | 用户 |
| ImportAIStepPayload | M17 | M17 内部链 | 用户 |
| ImportBatchInsertPayload | M17 | M17 内部链 | 用户 |
| EmbedSinglePayload | M18 | cron 触发 | ⚠️ 系统 — 待 Q3 边界规约 |

**注**：M16 fire-and-forget 走 §12B 不走 Queue，本表不登记。

---

## 4. Pydantic Schema 命名空间

### 4.1 命名规范

**业界标杆**：FastAPI 官方 SQL 教程（tiangolo 维护）/ SQLModel 官方教程 / fastapi-best-practices OSS / JD Solanki 社区指南。FastAPI / SQLModel 官方均用 `XxxCreate` / `XxxPublic` 风格，**不使用** `XxxIn`/`XxxOut` 或 `XxxRequest`/`XxxResponse`。

**S1-S4 命名规约**：

| 后缀 | 用途 |
|------|------|
| `XxxBase` | 共享字段基类 |
| `XxxCreate` | POST body（含内部字段如 secret_name）|
| `XxxUpdate` | PATCH body（全字段 Optional）|
| `XxxPublic` | 对外响应（排除敏感字段）|
| `XxxPublicDetail` | 详情页扩展响应（含关联数据）|

**禁用后缀**：
- ❌ `XxxIn` / `XxxOut`：In 是 create 还是 update 不明
- ❌ `XxxRequest` / `XxxResponse`：绑定 HTTP 语义，跨 endpoint 复用时失准

**S5 文件位置**：`api/schemas/{module}_schema.py`（单文件 per module）。模块内 schema 数量超过 10 个时拆分为 `api/schemas/{module}/{topic}.py`。

**修订工作量**：业务代码 0 行 → M01 实施时直接按本规范写，无历史包袱。

**来源**：
- [FastAPI SQL Databases Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [SQLModel FastAPI Tutorial](https://sqlmodel.tiangolo.com/tutorial/fastapi/simple-hero-api/)
- [fastapi-best-practices (zhanymkanov)](https://github.com/zhanymkanov/fastapi-best-practices)

### 4.2 现状

业务代码 0 行，本节待 M01 实施后逐步登记。

---

## 5. 检测自动化（契约 4 一部分）

待跑 `scripts/structural-audit.sh`：
- P2 namespace collision 自动扫
- 命名规范 lint（N/A/Q/S 系列）

---

## 6. 关联

- 触发：[`design/audit/full-reconcile-pass.md`](../audit/full-reconcile-pass.md) S-A1/A2/A3
- 契约形态：[`design/audit/contracts-draft.md`](../audit/contracts-draft.md) § 3
- 业界标准：agent `aa84a97` 输出后整合到本文 § 1.1 / 2.1 / 3.1 / 4.1
- 闸门：[`design/00-phase-gate.md`](../00-phase-gate.md) 闸门 2.5 / 2.6
