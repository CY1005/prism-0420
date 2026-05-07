---
title: P5 state-machine reachability audit
status: draft
owner: CY
created: 2026-05-06
trigger: contracts-draft.md §4.1 P5（manual portion of structural audit procedure 5）
purpose: 横向 audit "状态机可达性 + 终态性 + 跨模块触发 + cron user_id 边界"——纵向模块 audit 漏审项
---

# P5 状态机可达性 audit

## 0. 范围 + 方法

### 范围（覆盖到的模块）

按 contracts-draft §4.1 P5 列举 + 全仓 grep 补全，确认有显式状态机的模块共 **8 个**：

| 模块 | 实体 | 状态枚举类 | mermaid stateDiagram 行 |
|------|------|-----------|------------------------|
| M01 | `User.status` | `UserStatus`（00-design.md:229）| 472 |
| M02 | `Project.status` | `ProjectStatus`（00-design.md:174）| 322 |
| M07 | `Issue.status` | `IssueStatus`（00-design.md:95）| 186 |
| M11 | `ColdStartTask.status` | `ColdStartStatus`（00-design.md:112）| 200 |
| M16 | `AISnapshotTask.status` | `AISnapshotTaskStatus`（00-design.md:200）| 303 |
| M17 | `ImportTask.status` | `ImportTaskStatus`（00-design.md:137）| 271 |
| M18 | `EmbeddingTask.status` | `EmbeddingTaskStatus`（00-design.md:253）| 441 |
| M20 | `Team`（隐式）+ `team_members.role` | 无 status enum，role enum | 323、337 |

### 显式声明无状态机（已在各模块 §4 显式 R4-1）

- M03 `nodes`（type 不可变枚举，无 status）—— 00-design.md:228-234
- M04 `dimension_records`（无 status 字段）—— 00-design.md:207-216
- M05 `version_records`（is_current 是布尔，不是状态机）—— 00-design.md:184-202
- M13 流式分析（无持久化状态；只有 streaming → [*] 形式占位）—— 00-design.md:250-259

### 本文不审什么

- 不审字段级 CHECK 约束完整性（已在 P3 模块 audit 覆盖）
- 不审 ErrorCode AppError 一致性（已在 R13-1 grep + 各模块 audit-report 覆盖）
- 不审 i18n key 完备性
- 不审具体 SQL（cas_* 等 DAO 实现已在 M16 §9 自审）

### 方法

1. 对每个状态机：列出状态、初始/终态、mermaid 中所有转换、允许/禁止表中的转换
2. Reachability：DFS 验证所有非初始状态可达；终态无出向边
3. cron 触发的转换 → 检查 ADR-002 §1.1 SYSTEM_USER_UUID 是否被引用
4. 跨模块 trigger（M03 → M07 / M17 batch_insert → M03/M04/M06/M07 / M18 enqueue → cross-module reads）：转换是否在两端都登记

---

## 1. 状态机清单

### 1.1 M01 User.status

**文件**：`design/02-modules/M01-user-account/00-design.md`

**状态**（L229-232）：`active` / `disabled` / `pending`（pending 本期预留未启用，但 schema CheckConstraint 含）

**初始**：`[*] → active`（admin 创建默认）；`[*] → pending`（开放注册预留，未启用）

**终态**：无显式终态；`active → [*]`（hard delete）已在 mermaid 标但说"不启用"

**转换图**（L472-480）：

```
[*] → active            : Admin 创建（默认）
[*] → pending           : 开放注册（预留，未启用）
active → disabled       : Admin PATCH status=disabled
disabled → active       : Admin PATCH status=active
pending → active        : Admin 审核通过（预留）
pending → disabled      : Admin 拒绝（预留）  ⚠️ 与禁止转换表 L492 矛盾
active → [*]            : hard delete（不启用）
```

**禁止转换**（L487-494）：`disabled→pending` / `pending→disabled` / `disabled→[*]` / `pending→[*]`

**Reachability finding**：
- ✅ active 可达（admin 创建路径）
- 🟡 **pending 不可达（本期）**：mermaid 画了 `[*] → pending` 但 §4 说明显式声明"开放注册预留未启用"+"创建默认 active"。pending 在本期是 schema 预留态，无 service 路径写入，仅靠未来"开放注册"启用。L485 也说"若出现 pending 用户，Service 层一律拒绝登录"——这是防御代码，不是写入路径。**已在文档中显式 ack 为预留态，不构成审计阻塞**。
- 🔴 **mermaid 与禁止转换表自相矛盾**：mermaid L478 `pending → disabled : Admin 拒绝（预留）` 与禁止转换表 L492 `pending → disabled` 都列在表里。一处说允许（预留启用后用），另一处说禁止（拒审等价于硬删除→应硬拒）。CY 实装时不知该按哪条走 → **Finding F-1**。
- ✅ disabled 非终态（disabled→active 双向）
- ⚠️ 终态：`active → [*]`（hard delete）在 mermaid 标了但 §4 强调"本期不启用"——前端/Service 都没有该端点。本期事实上没有终态出口；如果实装时不阻断状态机会从 active 永远没法离开。**接受**：本期 user 是软删除/disable 终生保留。

**跨模块触发**：
- M20 `team_members.user_id ondelete=CASCADE`（M20 §5.3 F3.10 声明）：删 user 会 CASCADE 清 team_member 行——若 U 是 last team owner，M01 baseline 提议加 `assert_user_has_no_owned_teams(uid)` 校验。**这是删 user 的前置校验，不影响 status 状态机**。
- M01 不被任何模块的 service 推动 status 转换（admin PATCH 是 M01 自身路由）。

**cron / SYSTEM_USER**：N/A，M01 无 cron 触发的状态转换。

---

### 1.2 M02 Project.status

**文件**：`design/02-modules/M02-project/00-design.md`

**状态**（L174-176）：`active` / `archived`

**初始**：`[*] → active`（创建项目）

**终态**：`archived`（不可逆，G2 决策）

**转换图**（L322-326）：

```
[*] → active           : 创建项目
active → archived      : 管理员归档（archive_project）
archived → [*]         : 归档为不可逆终态（本期不支持恢复和物理删除）
```

**禁止转换**（L334-335）：`archived → active`（PROJECT_ALREADY_ARCHIVED 409）；`archived → archived`（同 ErrorCode）

**Reachability finding**：
- ✅ active 可达
- ✅ archived 可达（owner/admin 调 `POST /projects/{pid}/archive`）
- ✅ archived 是真正的终态（无出向边）
- ✅ mermaid `archived → [*]` 实质是"任务终结"标记（保留行，不删除），不是状态转换

**跨模块触发**：
- M20 §5.3 决策 + baseline-patch-m20 引入 `PROJECT_ARCHIVED` ErrorCode（422，detail `{project_id, status}`）：archived project 拒入 team。**这是 M02 状态被 M20 service 读，不是写**——单向。
- M03 / M04 / M06 / M07 等所有 project_id 冗余 tenant 表都通过 `ON DELETE CASCADE` 与 projects 关联，但 M02 是软归档不物理删除 → **CASCADE 不会触发**。
- 🟡 **archive_project → 子模块状态联动未文档化**：M02 archive 时，子模块的 issue/version/dimension 等仍保持其原 status（open/in_progress 的 issue 仍 open）。本设计接受这一点（设计意图：归档=只读快照），但**M02 §4 没有显式声明"归档不级联子模块状态"**。下一模块开发者需读 §3 部分唯一索引才推断出来。**Finding F-2**。

**cron / SYSTEM_USER**：N/A，无 cron 转换。

---

### 1.3 M07 Issue.status

**文件**：`design/02-modules/M07-issue/00-design.md`

**状态**（L95-99）：`open` / `in_progress` / `resolved` / `closed`

**初始**：`[*] → open`

**终态**：`closed`

**转换图**（L186-193）：

```
[*] → open              : 创建 issue
open → in_progress      : 认领（assign + 开始）
open → resolved         : 直接解决
in_progress → resolved  : 标记解决
resolved → closed       : 最终关闭
closed → [*]            : 关闭归档
```

**禁止转换**（L207-209）：`open → closed`（必须经 in_progress 或 resolved）；`closed → 任意`（IssueClosedError）

**Reachability finding**：
- ✅ 全部 4 状态可达
- ✅ closed 是真正终态
- 🟡 **`in_progress → open`（取消认领）未在 mermaid / 允许 / 禁止 三表登记**：现实场景：编辑误点认领后想取消归还 issue 池——既不允许也未声明禁止。Service 层会落到 default else 分支抛 `InvalidTransitionError` 但 ErrorCode 表 §13 中 `ISSUE_TRANSITION_INVALID` 通用兜底 → **形式合规但语义模糊**。**Finding F-3**。
- ⚠️ `assigned_to` 字段是状态机的隐式约束（in_progress 时必填，L211-216），属"扩展状态"——已在文档显式声明，不计 finding。

**跨模块触发**：
- 🔴 **M03 节点删除 → M07 issue.node_id orphan**：M07 §6 L272 登记 `orphan_by_node_id(db, node_id, project_id) -> int`——M03 NodeService delete 时调用，每条 issue 写独立 `orphan` activity_log。这是**实际的跨模块 service 写**，但**这不是 issue.status 状态转换**（status 仍保留 open/in_progress 不变，只是 node_id 设 NULL）。状态机文档没漏；但跨模块行为登记应在 M03 §6 / §10 也对账。
  - 检查 M03 §6/§10 是否登记了"删除节点时调用 M07 orphan_by_node_id"——本审计不直接审 M03（无状态机），**留作 P1/P2 跨模块对账契约的下游**。
- M11 cold start `batch_create_in_transaction` → 写 issue（status=open 默认）
- M17 ai_import importing 阶段 → 写 issue（status=open 默认）
- M18 incremental enqueue → issue create/update 后 enqueue embedding（不影响 issue.status）

**cron / SYSTEM_USER**：N/A，issue 无 cron 触发的状态转换。

---

### 1.4 M11 ColdStartTask.status

**文件**：`design/02-modules/M11-cold-start/00-design.md`

**状态**（L112-118）：`pending` / `validating` / `importing` / `completed` / `failed`（G6 决策已删除 partial_failed）

**初始**：`[*] → pending`

**终态**：`completed` / `failed`

**转换图**（L200-210）：

```
[*] → pending             : 接收 CSV / 创建任务
pending → validating      : 开始行校验
validating → importing    : 全量校验通过
validating → failed       : 校验失败
importing → completed     : 全量入库成功
importing → failed        : 任一 Service 批量入库异常（全量回滚）
completed → [*]
failed → [*]              : 用户重传时新建任务
```

**禁止转换**（L224-229）：completed/failed 终态不可变（COLD_START_TASK_FINALIZED）；`importing → validating` 逆向；`pending → importing` 跳过 validating

**Reachability finding**：
- ✅ 全部 5 状态可达
- ✅ 终态 completed / failed 无出向边
- ✅ R4-2 禁止转换 ≥ N+1=3 条满足（实测 4 条）

**跨模块触发**：
- M11 是 orchestrator：在 importing 阶段调 M03/M04/M06/M07 的 `batch_create_in_transaction`，全量回滚由 `db.begin()` 包外层事务实现。**M11 不直 INSERT 跨模块表**（R-X1）—— M11 §6 已显式登记。
- 这些子模块 service 写不会触发它们自身的状态转换（只是 INSERT 新行，初始 status）。**无 cross-module 状态机交互**。

**cron / SYSTEM_USER**：N/A，无 cron 转换；M11 同步 HTTP 完成。

---

### 1.5 M16 AISnapshotTask.status

**文件**：`design/02-modules/M16-ai-snapshot/00-design.md`

**状态**（L200-205）：`pending` / `running` / `succeeded` / `failed` / `cancelled`（cancelled 预留，本期不实装端点）

**初始**：`[*] → pending`

**终态**：`succeeded` / `failed` / `cancelled`

**转换图**（L303-315）：

```
[*] → pending          : POST /snapshot/generate
pending → running      : BackgroundTasks 拉起 + 调 AI provider
running → succeeded    : AI 返回 + parse 成功
running → failed       : AI 异常 / 超时 / 配额超限 / parse 失败
pending → cancelled    : 预留，本期不实装
running → cancelled    : 预留，本期不实装
succeeded → [*]        : 30 天后清理
failed → [*]           : 30 天后清理
cancelled → [*]        : 30 天后清理（预留）
```

**附加 cron 转换**（L322 + L990 + L654 cas_zombie_transition）：

```
pending → failed       : zombie cron 兜底（pending > 2min 仍未 BackgroundTasks 拉起）；error_code=SNAPSHOT_ZOMBIE
running → failed       : zombie cron（running > 11min）；error_code=SNAPSHOT_ZOMBIE
```

**禁止转换**（L326-332）：终态不可变；跳步（pending→succeeded）；逆向到 pending

**Reachability finding**：
- ✅ pending / running / succeeded / failed 全部可达
- 🟡 **`cancelled` 在本期不可达（无端点 + 文档显式声明 L334-336）**：状态机里有 2 条入边（pending→cancelled / running→cancelled）但**本期都没有 service 路径触发**——即 cancelled 是预留死状态。**已显式 ack**，不计阻塞 finding，但要在审计表中标注。
- ✅ 终态 succeeded / failed / cancelled 无出向边（L326 终态守护）

**cron / SYSTEM_USER 边界（ADR-002 §1.1）**：

🔴 **关键 finding**：M16 zombie cron `cleanup_zombie_snapshots`（L990）通过 `cas_zombie_transition`（§9 L654）直接 UPDATE DB，**不走 arq Queue**（因为 M16 整体是 BackgroundTasks fire-and-forget，不走 Queue）。

ADR-002 §1.1 的 SYSTEM_USER_UUID 规约（L78、L93）**显式列出** "M16 cron `cleanup_zombie_snapshots`" 是触发方，要求：
- payload.user_id = SYSTEM_USER_UUID
- M15 ActivityLog 写入时 user_id = SYSTEM_USER_UUID

但 M16 §9 `cas_zombie_transition` docstring 只说"zombie 转换的 activity_log 写入由 cron 入口在拿到 RETURNING ids 后批量补写"——**没有显式说明 activity_log.user_id = SYSTEM_USER_UUID**。

仓库 grep 验证：
```
grep -rn "SYSTEM_USER_UUID\|00000000-0000-0000-0000-000000000000" design/02-modules/  →  零结果
```

**问题**：M16 实装时若按文档照抄，cron 直接 UPDATE 不带 user_id 字段（对 ai_snapshot_tasks 表 OK，因为表里 user_id 是 task creator 已存在），**但补写的 activity_log.user_id 字段填什么没规约**。两种可能错：
1. 用 task.user_id（误把"系统操作"归到原用户名下，违反 ADR-002 §1.1 i18n "系统"语义）
2. 用 NULL（违反 §1.1 "禁止用 is None 判断系统任务"）

**Finding F-4**：M16 §10 / §12B / §9 cas_zombie_transition 三处都没显式引用 ADR-002 §1.1 SYSTEM_USER_UUID，cron 补写 activity_log 的 user_id 字段无规约。

**跨模块触发**：
- M16 succeeded 阶段 user 调 `POST /snapshot/save` → 在 M16 事务内调 `M04.create_dimension_record(db, ...)` N 次（§5 L345）。这是 M16 user-driven 操作，不是状态机自身转换。
- save 完成不触发 M16 本身的状态转换（succeeded 终态保持）。

---

### 1.6 M17 ImportTask.status

**文件**：`design/02-modules/M17-ai-import/00-design.md`

**状态**（L137-148）：11 个 —— `pending` / `extracting` / `ai_step1` / `ai_step2` / `ai_step3` / `awaiting_review` / `importing` / `completed` / `partial_failed` / `failed` / `cancelled`

**初始**：`[*] → pending`

**终态**：`completed` / `failed` / `cancelled`；`partial_failed` 是**半终态**（可重试 → ai_step3）

**转换图**（L271-300，简化）：

```
[*] → pending → extracting → ai_step1 → ai_step2 → awaiting_review → ai_step3 → importing → completed
                                            ↓                                       ↘
                                       (failed paths)                            partial_failed → ai_step3 (用户重试)
任意非终态 → cancelled
```

**禁止转换**（L316-326）：cancelled/completed/failed 终态；跳步；任意→pending；partial_failed→completed 跳重试；partial_failed→除 ai_step3/cancelled 外

**Reachability finding**：
- ✅ 全部 11 状态可达（每条状态都有入边）
- 🟢 **`partial_failed` 实际是循环节点（→ai_step3）而不是终态**：mermaid L299 标"partial_failed → [*] : 30 天后清理"暗示它最终也会清理，但允许的转换里 `partial_failed → ai_step3 : 用户重试`（L286）使其语义=半终态。**文档已用"可恢复"语言显式声明**（L146），不计 finding，但 R4 终态计数表里要算它做"半终态"会让 N+1 公式产生分歧。
- ✅ 终态 completed / failed / cancelled 无出向边
- 🟡 **`importing → cancelled` 副作用文档化但实现细节模糊**（L294 + L314 "回滚已写入数据"）：importing 阶段已通过 `with db.begin():` 写入 M03/M04/M06/M07 行；cancelled 时如何 cleanup 已 commit 的数据？——若 importing 事务尚未 commit 则 ROLLBACK；若已 commit 则需级联 DELETE，文档没说明。**Finding F-5**。

**cron / SYSTEM_USER 边界**：

🔴 **关键 finding F-6**：M17 §12 L673 登记 cron 任务 `import_cleanup_dead_letter`（payload `TaskPayload`，cron daily），**这是真 Queue cron 任务**——但 ADR-002 §1.1 SYSTEM_USER_UUID 规约里**只列了 M16 zombie + M18 backfill 两个触发方**（L78 表 + L93 触发方清单），**M17 dead letter cleanup cron 没在 ADR-002 §1.1 登记**。

按 ADR-002 §1 "TaskPayload.user_id 非空" + §1.1 "cron 必须用 SYSTEM_USER_UUID"，M17 dead_letter cron **必须**用 SYSTEM_USER_UUID，但 ADR-002 §1.1 触发方清单未列 → M17 实装时容易漏看。

且 M17 dead_letter cron 不触发任何状态转换（已 failed 的 task expires_at 过期清理），属于 cleanup 操作，**严格说不算"状态机转换路径"**——但它仍是受 ADR-002 §1 约束的 Queue task。

**跨模块触发**：
- M17 importing 阶段：`with db.begin():` 包 M03/M04/M06/M07 batch_create_in_transaction（L335）。各被调模块 service 接受外部 db session 不开新事务。这些 INSERT 不触发被调模块的状态机（dimension_records 无状态机；issue 默认 open；node 无状态机；competitor 无状态机）。
- M17 增量 embedding：commit 后 enqueue M18 embedding tasks（M18 §6 baseline-patch）。这是 M17 → M18 单向触发，不影响 M17 状态机。
- M17 cancelled 状态副作用 = 回滚已写入数据：见 F-5。

---

### 1.7 M18 EmbeddingTask.status

**文件**：`design/02-modules/M18-semantic-search/00-design.md`

**状态**（L253-258）：`pending` / `running` / `succeeded` / `failed` / `dead_letter`

**初始**：`[*] → pending`

**终态**：`succeeded` / `failed`（→`dead_letter`）/ `dead_letter`

**转换图**（L441-450）：

```
[*] → pending         : enqueue (incremental / backfill / model_upgrade)
pending → running     : worker 拉起
running → succeeded   : embedding 写入成功
running → failed      : 重试耗尽（3 次）
running → pending     : 单次失败重试
failed → dead_letter  : cron 30s 后转死信
succeeded → [*]       : 30 天后 cron 物理删除
dead_letter → [*]     : 90 天后 cron 物理删除
```

**禁止转换**（L452-456）：succeeded / failed / dead_letter 终态；跳步 pending→succeeded

**Reachability finding**：
- ✅ pending / running / succeeded / failed / dead_letter 全部可达
- 🟡 **`failed` 不是真正终态——会被 cron 30s 后强制转 `dead_letter`**：禁止转换 #2 说"failed → succeeded：失败已落 embedding_failures 不可重新成功"——这条对，但 mermaid 表明 `failed → dead_letter` 是允许的，所以 failed 是**短暂态**（30s 窗口）。L455 称 dead_letter 为终态，但禁止转换表只列了 `dead_letter → 任意 状态` 一条（#3）——和现实 cron 不冲突。**文档自洽**，不计 finding。
- ✅ dead_letter 是真正终态
- ⚠️ `running → pending`（单次失败重试）是逆向转换 —— 与 M11 / M16 / M17 的"前向单调"规则不同。这是 M18 显式接受的设计（fix v4.x audit 修复），允许"3 次重试中"在 running→pending 间往返，第 3 次失败才转 failed。**已 ack 显式**。

**cron / SYSTEM_USER 边界（ADR-002 §1.1）**：

M18 多个 cron（§12D + L514-517）：
- `embedding_backfill` cron daily（ADR-002 §1.1 触发方清单显式列）
- `embedding_backfill_recovery` arq cron 每小时（fix v4.1 verify R5'）
- zombie cron 5min（同上）
- failures 监控 cron 1h
- cleanup cron / 死信 90 天清理 cron

🔴 **Finding F-7**：M18 §12 / §15 cron 定义中**未显式引用 ADR-002 §1.1 SYSTEM_USER_UUID**，与 M16 同病。仓库 grep 显示 M18 0 处出现 SYSTEM_USER_UUID。M18 §12D Queue payload 说"继承 TaskPayload 基类"（§5 L486），TaskPayload 强制 user_id 非空，但 cron 实装时该填什么——文档没说。ADR-002 §1.1 触发方清单虽列了 "M18 cron embedding_backfill"，但**反向链未在 M18 文档登记**（这正是 contracts-draft §2 反向链契约要解决的根因之一）。

**跨模块触发**：
- M18 cron `embedding_backfill_recovery`（L515）通过规则 4 豁免**只读 import** M03/M04/M06/M07 model 找差异 → enqueue 新 embedding task。**纯读不写**，不影响这些模块的任何状态。
- M03/M04/M06/M07 的 create/update/delete service → commit 后 enqueue M18 embedding task（incremental 路径）。这是**单向 fan-out**，不形成状态机闭环。

---

### 1.8 M20 teams + team_members.role

**文件**：`design/02-modules/M20-team/00-design.md`

#### 1.8.a teams（隐式存在态）

**状态**（L320-326）：无显式 status 字段；只有"存在/不存在"

**转换**：`[*] → active : team_created` / `active → [*] : team_deleted`

**禁止转换**（L328-330）：team 物理删除后不可复活；删除前置校验 `COUNT(projects WHERE team_id=X)=0`

**Reachability finding**：
- ✅ 简单存在/删除生命周期，可达 + 终态正确
- ⚠️ R4-2 禁止转换严格说只有 1 条（[*] → active：team_recreated）——文档显式承认这是隐式状态机的最小声明（L328），**已 ack**。

**跨模块触发**：
- `teams.creator_id ondelete=RESTRICT`（L386 F3.10 决策）：删 user 时若 user 是 team creator → 拒 422 USER_HAS_OWNED_TEAMS。**反向阻断 M01 的 user 删除路径**，已在 M20 §5.3 登记并要求 M01 baseline 加 assert（M01 §xx 待跟进）。

#### 1.8.b team_members.role

**状态**（L336-346）：`member` / `admin` / `owner`（这是 role 不是 status，但 M20 设为 R4 状态机审计）

**初始**：`[*] → member`（默认 role）

**终态**：`[*]`（被 team_member_removed）

**转换图**（L337-346）：

```
[*] → member             : team_member_added (default)
member → admin           : promoted (actor ≥ admin)
admin → member           : demoted (actor ≥ admin)
admin → owner            : transfer_target (transfer ownership 流程)
owner → admin            : transfer_source (transfer ownership 流程)
member → [*]             : team_member_removed
admin → [*]              : team_member_removed
owner → [*]              : 禁止（必须先 transfer）
```

**禁止转换**（L348-352，4 条）：
- `owner → [*]` 拒 TEAM_OWNER_REQUIRED
- `member → owner` 跨级直升禁止
- `owner → admin`（非 transfer 场景，单 owner team）拒 TEAM_OWNER_REQUIRED
- `owner → member` 直降禁止（schema Literal 已限）

**Reachability finding**：
- ✅ 三个 role 全部可达
- ✅ 终态出向（被 remove）受守护
- ⚠️ `owner → admin` 仅在 transfer 流程内同事务可达——这是**条件可达**，文档显式声明（L351）。
- ✅ R4-2 N+1=3 满足（实测 4 条）

**跨模块触发**：见 M20 §5.3 F3.10（与 M01 user 删除的 RESTRICT/CASCADE 内部冲突）。这是 RBAC 规则与外键级联的交互，已被识别为 "M01 baseline 提议"待跟进。

**cron / SYSTEM_USER**：N/A。

---

## 2. 横向发现（跨模块状态机交互）

### 2.1 cron 触发的 SYSTEM_USER_UUID 引用空缺（最大 finding 群）

ADR-002 §1.1 是**主动登记**的（来自 full-reconcile-pass S-C2 修复），但**反向链未在模块端登记**：

| 模块 | cron 任务 | ADR-002 §1.1 列入触发方？ | 模块文档显式引用 SYSTEM_USER_UUID？ |
|------|----------|-----------------------|--------------------------------|
| M16 | cleanup_zombie_snapshots（5min）| ✅ 列入（L78 + L93）| ❌ 0 处 |
| M16 | cron 写 metrics（每周）| ❌ 未列 | ❌ |
| M17 | import_cleanup_dead_letter（daily）| ❌ 未列 | ❌ |
| M18 | embedding_backfill（daily）| ✅ 列入 | ❌ 0 处 |
| M18 | embedding_backfill_recovery（hourly）| ❌ 未列 | ❌ |
| M18 | zombie cron（5min）| ❌ 未列 | ❌ |
| M18 | failures 监控 cron（hourly）| ❌ 未列 | ❌ |
| M18 | cleanup cron（weekly）| ❌ 未列 | ❌ |
| M18 | embedding_model_upgrade_triggered（手动）| ✅ 列入（L79 系统级回调）| ❌ |

**根因**：ADR-002 §1.1 列入的"触发方"是触发了 SYSTEM_USER_UUID **payload 写入** 的；周期 cron 不一定都是 Queue 任务（如 M16 zombie 直接 UPDATE）。但 §1.1 表上写的"M16 zombie / M18 backfill"措辞模糊，未区分"Queue payload"和"直接 SQL"两种 cron 形态——前者必须 SYSTEM_USER_UUID，后者也必须（写 activity_log 时）。

→ **F-4** + **F-7** + **F-8** 三个 finding。

### 2.2 跨模块状态触发不形成闭环（结构正确）

完整图：

```
M11 ColdStart importing → M03/M04/M06/M07 batch_create  (创建新行，初态)
M17 importing → M03/M04/M06/M07 batch_create_in_transaction  (创建新行，初态)
M03 NodeService.delete → M07 orphan_by_node_id  (改 issue.node_id 不改 status)
                       → M04/M06 delete_by_node_id  (DELETE，无状态)
M03/M04/M06/M07 create/update/delete commit → M18 embedding enqueue  (新建 M18 task pending)
M16 save → M04 create_dimension_record N 次  (创建新行)
M13 save → M04 create_dimension_record  (创建新行)
M02 archive → M20 PROJECT_ARCHIVED 拒绝 move-team  (M20 读 M02 状态)
M01 user delete → M20 RESTRICT/CASCADE 守护  (M20 守护 M01 流程)
```

**横向断言**：所有跨模块 trigger 都是"上游写入下游初态"或"上游读下游状态做防御"，**没有跨模块状态机闭环**（A.status → B.status → A.status 这种环）。结构干净。

### 2.3 半终态和"伪可达"状态登记

| 模块 | 状态 | 类型 | 风险 |
|------|------|-----|-----|
| M01 | pending | 本期不可达预留 | 实装时若漏看 §4 说明，会按 mermaid 写入路径，造成"幽灵 pending 用户" |
| M16 | cancelled | 本期不可达预留（端点未实装）| 同上，实装时若按 mermaid 暴露 cancel 端点，会产生未文档化的副作用 |
| M17 | partial_failed | 半终态（可循环回 ai_step3）| R4-2 终态计数语义不清（算 1 还是 0.5）|
| M18 | failed | 短暂态（30s 后 cron 转 dead_letter）| 实装时若漏 cron，failed 会卡住成真终态 |

→ **F-9**：建议每个状态机加"非常规态登记表"（半终态 / 预留态 / 短暂态），与正常态分开，让审计 + 实装一眼分辨。

### 2.4 状态转换的 activity_log 一致性

每条状态转换都应写一条 activity_log（R10-1）。本审计抽查：
- M01 disabled 转换：`user.admin_update_status` ✅
- M02 archive：`archive`（previous_status=active）✅
- M07 status_change：✅
- M11 全部转换：✅
- M16 转换：✅（cas_complete affected=1 才写，避免与 zombie cron 双写）
- M17 转换：✅（每条 task 状态变更写）
- M18：❌ embedding 转换不写 activity_log（CY ack: Q7=C，写 embedding_failures 自有表）

M18 例外已显式 ack，符合 R10-2 例外条款（高频系统级 + 自有审计表），**不计 finding**。

---

## 3. Findings 表

> **状态**：F-1 / F-4 / F-6 / F-7 / F-9 / F-10 已 fixed（2026-05-07，commits 2e93de9 + b24f049）；F-2 / F-3 / F-5 / F-8 留作后续单独处理。

| ID | 模块 | 等级 | 描述 | 修复建议 | 引用 |
|----|------|-----|------|---------|------|
| F-1 ✅ fixed (2e93de9) | M01 | 🔴 | mermaid `pending → disabled : Admin 拒绝（预留）`（L478）与禁止转换表 `pending → disabled : INVALID_STATUS_TRANSITION`（L492）自相矛盾 | 已 patch：方案 A 路径——通过 R4-3a 严格档将 pending 拆出 mermaid 进非常规态登记表，矛盾消失 | M01-user-account/00-design.md:478 vs :492 |
| F-2 | M02 | 🟡 | M02 archive 不级联子模块状态（issue 仍 open / version 仍 is_current 等）— 设计意图但未在 §4 显式声明 | §4 加一段"归档不级联子模块状态"显式声明 + 引用 §3 部分唯一索引 | M02-project/00-design.md:319-335 |
| F-3 | M07 | 🟡 | `in_progress → open`（取消认领）未在三表登记，现实场景常见但 fall-through 到通用 ISSUE_TRANSITION_INVALID | mermaid + 允许表 + 禁止表三选一明确 status；建议加入允许转换（编辑取消认领后释放给池）+ 副作用 = `assigned_to=NULL` | M07-issue/00-design.md:186-209 |
| F-4 ✅ fixed (b24f049) | M16 | 🔴 | M16 zombie cron + 周报 cron 写 activity_log 时 user_id 字段未规约——ADR-002 §1.1 显式列了 M16 cleanup_zombie 但 M16 文档 0 处引用 SYSTEM_USER_UUID | M16 §10 / §12B / §9 cas_zombie_transition docstring 三处补 references.adrs `ADR-002 §1.1` + activity_log.user_id = SYSTEM_USER_UUID 显式代码示例 | M16-ai-snapshot/00-design.md:990, 654; ADR-002:78,93 |
| F-5 | M17 | 🟡 | `importing → cancelled` 副作用"回滚已写入数据"未细化——若 importing 已 commit 部分批次如何级联 DELETE 没说明 | M17 §4 加一段说明"importing 阶段事务粒度 = 整任务 single tx" 还是"per-step tx；若 step N 已 commit 则 cancelled 走级联 DELETE 路径"；建议前者（单事务），与 R-X1 "M17 不直 INSERT" + 共享 db session 模式自洽 | M17-ai-import/00-design.md:294,314 |
| F-6 ✅ fixed (b24f049) | M17 | 🔴 | M17 `import_cleanup_dead_letter` cron daily 是真 Queue 任务，受 ADR-002 §1.1 约束，但 ADR-002 §1.1 触发方清单未列 → M17 实装时容易漏看 SYSTEM_USER_UUID | ① ADR-002 §1.1 触发方清单（L93）补 M17 dead_letter cleanup cron；② M17 §12 cron 段补 `payload.user_id = SYSTEM_USER_UUID` 示例 | M17-ai-import/00-design.md:673; ADR-002:93 |
| F-7 ✅ fixed (b24f049) | M18 | 🔴 | M18 5 个 cron（backfill / recovery / zombie / failures / cleanup）+ model_upgrade_triggered 全部 0 处引用 SYSTEM_USER_UUID；ADR-002 §1.1 仅列 backfill 和 model_upgrade，其他 3 个 cron 未规约 | ① ADR-002 §1.1 触发方清单补全 4 个 cron；② M18 §12D / §15 cron 矩阵段加 `payload.user_id = SYSTEM_USER_UUID` 显式列；③ M18 §10 R10-2 例外段补"自有 embedding_failures 表的 user_id 字段同样落 SYSTEM_USER_UUID" | M18-semantic-search/00-design.md:514-517,447; ADR-002:78,93 |
| F-8 | 横向 | 🔴 | ADR-002 §1.1 触发方清单是单向声明（ADR 列模块）但模块端无反向链——这正是 contracts-draft §2 反向链契约要解决的根因 | 等待 contracts-draft §2 落地为正式契约后批量回填；本期可先在 ADR-002 §1.1 末尾加 referenced_by 占位段（M16/M17/M18 各列 cron 任务名）+ 各模块 references.adrs 段加 `ADR-002 §1.1 [cron user_id=SYSTEM_USER_UUID]`（待 contracts-draft §1 落地） | contracts-draft.md §1 + §2; ADR-002:59-95 |
| F-9 ✅ fixed (2e93de9) | 横向 | 🟢 | 4 模块（M01/M16/M17/M18）含"非常规态"（预留态 / 半终态 / 短暂态）但与正常态混在 mermaid 里，审计 + 实装容易误读 | 已落地：02-modules/README.md R4-3a 严格档（5 类：预留/半终态/短暂/降级/迁移 + 条件可达边）+ M01/M16/M17/M18 mermaid 回扫拆出非常规态登记表（6 字段态表 + 3 字段边表） | 02-modules/README.md:156 R4-3a |
| F-10 ✅ fixed (2e93de9) | M01 | 🟢 | M01 mermaid 标 `active → [*] : (hard delete，不启用)` 但 §4 说明本期无 hard-delete——mermaid 边在但不可达不算错；建议清理一致性 | 已 patch：R4-3a 严格档将"本期不启用"的 hard delete 边一并从 mermaid 删除（M01 mermaid 现仅 active ↔ disabled 两态三边）；hard delete 端点本期不存在，未来启用时新增 mermaid 边 + 登记表条目 | M01-user-account/00-design.md:528-531 |

**统计**：
- 🔴 阻塞级：4（F-1, F-4, F-6, F-7）—— 全部围绕 cron user_id 边界 + 一处转换表自矛盾
- 🟡 注意级：3（F-2, F-3, F-5）—— 跨模块级联 / 状态登记不全 / 副作用细节
- 🟢 提醒级：3（F-8, F-9, F-10）—— 反向链结构性问题 + mermaid 一致性

---

## 4. 关联

- [`design/audit/contracts-draft.md`](./contracts-draft.md) §4.1 P5 —— 本审计的方法论触发
- [`design/audit/full-reconcile-pass.md`](./full-reconcile-pass.md) S-C2 —— cron user_id 未规约（ADR-002 §1.1 修复回流）
- [`design/adr/ADR-002-queue-consumer-tenant-permission.md`](../adr/ADR-002-queue-consumer-tenant-permission.md) §1.1 —— SYSTEM_USER_UUID 规约 + 触发方清单
- [`design/adr/ADR-003-cross-module-read-strategy.md`](../adr/ADR-003-cross-module-read-strategy.md) 规则 1/2/4 —— 跨模 trigger 行为合规依据
- 各模块 ErrorCode：
  - `INVALID_STATUS_TRANSITION`（M01 L997）
  - `COLD_START_INVALID_STATE_TRANSITION`（M11 L442）
  - `SNAPSHOT_INVALID_STATE_TRANSITION`（M16 L1037）
  - `IMPORT_INVALID_STATE_TRANSITION`（M17 L699）
  - `EMBEDDING_TASK_INVALID_TRANSITION` / `EMBEDDING_TASK_TERMINAL_VIOLATION`（M18 §4 L453-456）
- [`design/02-modules/README.md`](../02-modules/README.md):155 —— R4-3 mermaid 必须画规约（F-9 待回填）
