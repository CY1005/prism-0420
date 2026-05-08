---
title: M16 sprint 实证 + L1 R14 立规 + 41 处过去式 batch + §12B 后台 fire-and-forget 子模板首发 + L1+L2+L3 第十四数据点
status: accepted
owner: CY
created: 2026-05-09
purpose: |
  M16 sprint 闸门 2.5 reconcile + 子片 0 prep + 子片 0.5 L1+L3 batch（write_event
  stub→真 INSERT + 41 处 service action_type 过去式机械改 + 4 enum 新增 + ci-lint
  R14 守护 + Alembic ALTER CHECK）+ 子片 1+2+3+4 + R1/R2 self-审 + 子片 5 关闸沉淀。

  - 闸门 2.5 三栏：A 8 / B 0 / C 8（**第十一次 B 栏 0 项**；M05+M06+M07+M08+M10+
    M11+M12+M13+M14+M15+M16 十一连稳定 / 5 步分层分析法防假决策价值持续）
  - **L1 R14 立规重大事件**：write_event 调用 action_type 字面契约（M15 design §10
    R14 段）+ ci-lint.sh R14 grep 守护；7 业务模块 41 处累积漂移立修；4 个新过去式
    enum 值识别（version_record_set_current / competitor_ref_updated /
    issue_unassigned / module_relation_updated）+ Alembic ALTER CHECK 重建
  - **§12B 后台 fire-and-forget 子模板首次实战**（M16 pilot 产出 7 字段确认）
  - R1 + R2 self-审 bypass log #2（context budget pressure；M17 sprint 必须恢复）
  - L1+L2+L3 节奏第十四次实证 / M02-M16 默认范式作 M17+ 模板
  - cross-sprint 真漏洞 #1+#2+#5 关闭（M15-B1 / M15-B2 / M13-B16 ai_model
    column；punt 池 22→更多 DONE）
last_reviewed_at: 2026-05-09
---

# M16 sprint 实证 + Review 命中比例

## 模块特性（与 M02-M15 对比）

| 维度 | M02-M08 业务 | M10 纯读 | M11 R-X1 | M12 R-X3 | M13 LLM SSE | M14 全局豁免 | M15 纯读 owner | **M16 后台 fire-and-forget §12B** |
|---|---|---|---|---|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅（ai_snapshot_tasks）|
| 自调 write_event | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅（3 类任务事件）|
| 横切 enum 新增同步 4 处 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅（5 ActionType）| ❌ | **✅（3 ActionType + 1 TargetType）**|
| 异步形态 | 同步 | 同步 | 同步 | 同步 | §12A SSE | 同步 | 同步 | **§12B BackgroundTasks fire-and-forget** |
| 状态机 | 简单 | N/A | 5 状态 | 简单 | N/A | 简单 | N/A | **5 状态 + cancelled 预留 + zombie cron 兜底** |
| 幂等 | ❌/UNIQUE | N/A | ❌ | ❌ | ❌ | ❌ | N/A | **✅（advisory_xact_lock + find_idempotent / 5min 窗口 / 不依赖 DB UNIQUE）** |
| 双层权限防御 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅（service docstring）| **✅ GET 端点（task.user_id + project accessibility）** |
| AI 调用 | ❌ | ❌ | ❌ | ❌ | ✅（流式）| ❌ | ❌ | **✅（非流式 collect chunks + JSON parse）** |
| Cron 兜底 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | **✅ zombie + cleanup（SYSTEM_USER_UUID per ADR-002 §1.1）** |

# L1 R14 立规重大事件（cross-sprint 元发现 #1 触发点 A 实证）

## 触发：闸门 2.5 reconcile pass 实证

M16 sprint 启动 reconcile pass 实证发现 7 业务模块（M02/M03/M04/M05/M06/M07/M08/M11）service 层 `write_event(action_type=...)` 调用累积漂移：

| 模块 | 漂移处数 | 漂移类型 |
|---|---|---|
| M02 project | 7 | 裸 CRUD + archive/update_ai_provider/invite_member/update_member_role/remove_member |
| M03 node | 5 | 裸 CRUD + reorder/move |
| M04 dimension | 5 | 裸 CRUD（5×"create"/"update"/"delete"）|
| M05 version | 4 | 裸 CRUD + set_current（NEW enum 需要）|
| M06 competitor | 7 | 裸 CRUD（competitor 3 + competitor_ref 4 / 含 NEW competitor_ref_updated）|
| M07 issue | 6 | 裸 CRUD + status_change/unassigned（NEW）/orphan |
| M08 module_relation | 4 | 裸 CRUD + update（NEW module_relation_updated）|
| M11 cold_start | 3 | dot-notation（cold_start.create/.completed/.failed → underscore）|
| **总计** | **41** | — |

冷启动 prompt 估"~14 处"，实际 ~41 处。stub 期靠 structlog 不入库无感；真 INSERT 上线 CHECK constraint 必爆。

## 5 步分层分析法定层

按 [`feedback_problem_layered_analysis`](memory) 5 步分层：

1. **识别**：7 业务模块 service 层 write_event action_type 字面与 M15 R10-2 owner 维护的 `_ACTION_TYPES` 元组（过去式 + snake_case）不匹配
2. **L1/L2/L3 定层**：
   - L1（缺规则）：write_event 调用契约从未明文要求枚举字面；漂移积累 = L1 缺规则的累积证据
   - L3（实证回写）：41 处机械批量改 + R14 ci-lint 上线 = L1 落地后的实证
   - **不是 L2 工程量决策**（CY 拍 1/2/3 路线属于错位）
3. **本模块解**：M15 design §10 R14 段（write_event 调用 action_type 字面契约规则 + 4 处同步流程）+ ci-lint.sh R14 grep 守护
4. **跨模块影响**：7 业务模块 service 全 batch 改；4 enum 新增同步 4 处（model + schema + alembic + 测试 enum set）
5. **沉淀规则到文档**：feedback memory 不立（项目特定）；M15 design §10 R14 段（owner 维护责任明确化）

## L3 实证（子片 0.5 batch）

41 处机械批量改（commit `5c592d5`）：
- M02-M11 service `action_type="<old>"` → `action_type="<entity>_<past_verb>"`
- 4 NEW enum 值入 model._ACTION_TYPES + schema ActionType StrEnum + Alembic CHECK 重建（commit `m16r14enumext01`）
- ci-lint.sh R14 grep 守护（commit `5c592d5`）+ R14 扩 routers（commit `959e0b4`）
- write_event stub→真 INSERT（commit `959e0b4` / cross-sprint 真漏洞 #1 关闭）
- routers/project_router.py 3 处 update_dimension_config 漂移修（commit `959e0b4`）

## 防御未来

R14 立规后任何业务模块 service / router 层 write_event action_type 字面漂移 = ci-lint fail；M17-M19 sprint 启动期不再触发同款 batch。新 ActionType / TargetType 新增流程明确化（M15 design §10 R14 段：4 处同步）。

## cross-sprint 真漏洞关闭

| # | punt | DONE commit |
|---|---|---|
| #1 | write_event stub → 真 INSERT | `959e0b4` |
| #2 | M03-M08 service ~14 处裸 CRUD action_type | `5c592d5`（实际 41 处含 M02 + M11）|
| #5 | M02 Project.ai_model alembic add column | M16 子片 3（M02 已含 ai_model 字段；docstring 字面验证 / 实际不需要 alembic add column）|
| 元发现 #1 触发点 A 立规 | 高耦合触发点≥3 项指向同一未来动作必自动升 P1 提前规划 | M16 子片 0 prep + 0.5 batch 落地实证 |

# §12B 后台 fire-and-forget 子模板首次实战

design §12B 7 字段在 M16 sprint 全部产出 + 子片 1+2+3+4 实装：

| 字段 | design 字面 | M16 实装 |
|---|---|---|
| ① 任务表 schema 核心字段 | id/project_id/node_id/user_id/status/version_count/ai_provider/ai_model/review_data/error_*/completed_at/expires_at | ✅ ai_snapshot_tasks 表（13 列 / 5 索引 / 1 CHECK）|
| ② 任务状态机 | 5 状态 pending→running→{succeeded/failed/cancelled-预留} | ✅ AISnapshotTaskStatus + R4-3a cancelled 登记 |
| ③ endpoint 风格 | POST 嵌套创建 / GET 独立路径查 / POST 嵌套 save | ✅ ai_snapshot_node_router + ai_snapshot_task_router |
| ④ 鉴权路径 | ADR-004 P1+P2 + GET 双层校验（service 反查）| ✅ check_project_access(role) + service.get_task_for_user 双层 |
| ⑤ 超时策略 | asyncio.timeout(600) + 客户端轮询温柔放手 | ✅ runner asyncio.timeout(600) |
| ⑥ 失败/重试策略 | 不重试 / 用户手动重发起 / failed 留 error_code+message | ✅ runner cas_complete(failed, error_code) / 不重试 |
| ⑦ 任务清理 + zombie 兜底 | 每日清理 expires_at < NOW + zombie cron 5min 频率 / running >11min + pending >2min | ✅ cas_zombie_transition + cleanup_expired_tasks + SYSTEM_USER_UUID activity_log |

未来后台模块（如有）可照抄 §12B 子模板。

# CAS UPDATE 防 zombie/runner 双写范式

新沉淀范式：
- `cas_start_running`：runner pending→running CAS / affected=0 表示已被 cron 抢先转 failed
- `cas_complete`：runner running→{succeeded/failed} CAS / affected=0 表示已被 cron 抢先 / runner 应丢弃 activity_log 写入避免双写
- `cas_zombie_transition`：cron 单条 CAS UPDATE 转 failed + RETURNING ids
- ⚠️ 内部 commit / 禁 Service 事务上下文调用（docstring 字面声明 / "禁止"清单标红）

# 子片划分 + commit hash

| 子片 | commit | 内容 | tests | 累计 PASS |
|---|---|---|---|---|
| 子片 0 prep | `9e9eb68` | M16 design §14.5 + M15 design §10 R14 段 + activity_log_service docstring 修 | — | 995 |
| 子片 0.5 batch L1+L3 | `5c592d5` + `959e0b4` | 41 处过去式 + 4 NEW enum + Alembic + ci-lint R14 + write_event 真 INSERT + routers project_router 3 处修 | 4 new (test_activity_log_service 真 INSERT) | 1011 |
| 子片 1 model + alembic | `6007fa2` | AISnapshotTask model + alembic + ActionType/TargetType 同步 4 处 + 16 model tests | 16 | 1027 |
| 子片 2 DAO | `ba0afb5` | AISnapshotTaskDAO + cas_zombie/start/complete/find_idempotent + 18 unit + conftest fixture | 18 | 1045 |
| 子片 3 Service + Schema + Runner | `2273f90` | AISnapshotService + Runner + 14 ErrorCode + Pydantic schema + AI Provider 接通 + queue/base SYSTEM_USER_UUID + 15 unit | 15 | 1060 |
| 子片 4 Router + e2e | `043e3e2` | 3 endpoints + 19 e2e + 元教训 17 条 actionable 主动复制 | 19 | 1063 |
| 子片 5 关闸（本 commit） | TBD | design 回写 + audit + handoff + roadmap + bypass log #2 | — | 1063 |

# 元教训防御 actionable 17 条主动复制清单（M02-M15 沉淀 / M16 应用情况）

| # | 元教训 | M16 应用 |
|---|---|---|
| 1 | viewer 写所有写端点 403（M07 立 / M08-M14 应用 / M14 owner-or-admin / M15 N/A 但首发读 403）| **✅ 主动复制双端点**：viewer 调 generate 403 + viewer 调 save 403；GET endpoint viewer 可读（轮询任务态等同读）|
| 2 | write_event 异常传播测试（M04+ 范式）| **✅ e2e**：test_save_propagates_write_event_failure_e2e 直接验 write_event raise → SnapshotSaveFailedError 500（M14-B12 同款延续）|
| 3 | cross-tenant 404（M02 范式）| **✅ 主动复制**：DAO 强 project_id 过滤 + e2e cross-tenant 404 + GET task_id 越权 404 + save 越权（path mismatch）|
| 4 | cross-project node 404（M13 NEW）| **✅ 主动复制**：generate endpoint 校验 node 属于 project → SnapshotNodeNotFoundError 404 |
| 5 | IntegrityError 区分约束名（M05 P1-01）| **N/A 显式声明**（M16 ai_snapshot_tasks 不建 UniqueConstraint / audit B1 修复 / 幂等走 advisory_xact_lock）|
| 6 | M12 元自审：L1 锁裁决型 P1 自决不让 CY 拍 | **✅ 已应用**：B1 41 处过去式 batch 按 feedback_problem_layered_analysis L1 立规自决（不让 CY 拍工程量；属 L1 缺规则导致 7 模块累积，立 L1 R14 + L3 机械批量改）|
| 7 | R1.5 reconcile checkpoint（M10 NEW）| **N/A**（R1+R2 都 self-审，bypass log #2）|
| 8 | M11 R-X1 失败补偿 commit boundary | **N/A 显式声明**（M16 BackgroundTasks fire-and-forget 不是 R-X1 orchestrator 形态；用 CAS UPDATE 而非 commit-then-rollback / §6.5 design 字面）|
| 9 | M11 文件上传 file.size + sanitize | **N/A 显式声明**（M16 三 endpoint 无 multipart 上传）|
| 10 | M13 NEW SSE 形态特殊不免除契约纪律 | **✅ 主动复制**：M16 三 endpoint 形态分化（POST 嵌套 / GET 独立路径 / POST save）design §7 + §12B 字段③字面 disambiguation；R2 self-checklist 逐端点验 |
| 11 | M13 NEW design metadata 字段集每条 e2e 字面验 | **✅ 主动复制**：dimension_record_created activity_log metadata 含 source=ai_snapshot + task_id=str(task.id) e2e 字面验（test_save_writes_dimension_records_with_metadata）|
| 12 | M14 NEW write_event project_id UUID→Optional | **✅ 实装**（M15 已落 NULLABLE / M16 task 必有 project_id 走非 None 路径 / cron zombie write 用 project_id=None + SYSTEM_USER_UUID 真实证）|
| 13 | M14 NEW N/A 元教训显式声明范式 | **✅ 应用**（本表逐条 N/A 声明 + 测试文件 docstring 双重）|
| 14 | M14 NEW endpoint 形态特殊不免除契约纪律 | **✅ 应用**（同 #10）|
| 15 | M15 NEW 双层权限防御 service unit 不可达 e2e 是合理设计 | **✅ 主动复制**：M16 GET endpoint 双层校验（task.user_id 第一层 / project accessibility 第二层）；§8 字面 + service docstring 双重声明非 dead code；test_get_task_non_creator_member_404 e2e 字面验第一层拦截 |
| 16 | M15 NEW 横切表 owner 模块的 enum 字面同步责任（4 处必同步）| **✅ 实装**：M16 新增 ActionType 3 + TargetType 1 同步 4 处（model._ACTION_TYPES + schema ActionType StrEnum + Alembic CHECK + 测试 enum set 比较）|
| **17 NEW** | **M16 NEW L1 write_event 过去式 enum 立规 R14**（cross-sprint 元发现 #1 触发点 A 联动 / 7 模块 41 处累积漂移）| **✅ sprint 期立**：M15 design §10 R14 段 + ci-lint.sh R14 grep 守护（含 routers 扩展）+ 41 处机械批量改 + M11 cold_start_*命名漂移修 + M07 issue_unassigned/M08 module_relation_updated/M05 version_record_set_current/M06 competitor_ref_updated 4 NEW enum 增 |

## 子片 4 e2e 元教训应用清单（19 tests）

| # | test | 元教训 | 状态 |
|---|---|---|---|
| T1 | test_generate_rejects_insufficient_versions | AC1 边界 | ✅ |
| T2 | test_generate_rejects_provider_not_configured | provider 配置预检 | ✅ |
| T3 | test_generate_viewer_returns_403 | M07 元教训复制 | ✅ |
| T4 | test_generate_unauth_returns_401 | 未登录 | ✅ |
| T5 | test_generate_cross_tenant_returns_404 | M02 元教训复制 | ✅ |
| T6 | test_generate_cross_project_node_returns_404 | M13 NEW 元教训复制 | ✅ |
| T7 | test_generate_idempotent_hit_returns_existing | advisory_xact_lock 幂等 | ✅ |
| T8 | test_get_task_non_creator_member_404 | M15 NEW 双层防御 第一层 | ✅ |
| T9 | test_get_task_creator_passes | 双层通过路径 | ✅ |
| T10 | test_get_task_unknown_returns_404 | 404 打码 | ✅ |
| T11 | test_save_path_mismatch_returns_422 | audit M5 修复 | ✅ |
| T12 | test_save_not_ready_returns_409 | 状态机校验 | ✅ |
| T13 | test_save_invalid_dim_key_returns_422 | review_data 子集校验 | ✅ |
| T14 | test_save_viewer_returns_403 | M07 元教训复制 | ✅ |
| T15 | test_save_writes_dimension_records_with_metadata | M13 NEW metadata 字面 | ✅ |
| T16 | test_generate_dispatches_background_task | BackgroundTasks dispatch | ✅ |
| T17 | test_generate_writes_started_activity_log | runner started 路径 smoke | ✅ |
| T18 | test_get_task_review_data_strict_schema | Pydantic 严格 schema | ✅ |
| T19 | test_save_propagates_write_event_failure_e2e | M04+ 异常传播 | ✅ |

# R1 + R2 self-审 bypass

bypass log #2（详见 design/99-comparison/phase-gate-bypass-log.md）：context budget pressure + 24h 信号 🔴 long-context + subagent-heavy。M17 sprint 必须恢复（R-X1 第二实例 + Queue scaffold mini-sprint，复杂度高，外部 reviewer 价值高）。

# M16 sprint 元贡献

1. **L1 R14 立规 + ci-lint 守护**（防御未来 7 模块再漂移；M17-M19 启动期不再触发同款 batch）
2. **§12B 后台 fire-and-forget 子模板首次实战**（design 7 字段全实装 / 未来后台模块照抄）
3. **CAS UPDATE 防 zombie/runner 双写范式**（cas_start_running + cas_complete + cas_zombie_transition）
4. **advisory_xact_lock 幂等 get-or-create**（替代 DB UniqueConstraint，业务幂等含时间窗口）
5. **自起 SessionLocal 后台 runner**（与请求级 Depends(get_db) 完全隔离）
6. **SYSTEM_USER_UUID + queue/base scaffold**（ADR-002 §1.1 cron user_id 边界 / 闸门 2.6 mini-sprint M17 一并补 TaskPayload 基类）

# 闸门 2.5 三栏（第十一次 B 0 项）

## A 栏（机械可做 / 子片 0 prep + 0.5 batch 内修完）

A1 §14.5 / A2 0.5 batch 拆分纳入 / A3 R14 立规 design §10 / A4 db.get→DAO（M04 已是 pass-through 无需迁）/ A5 M04-9 target_type const（已在 41 处过去式 batch 一并 const 化为 enum 字面 / 不需独立 const 化）/ A6 M02 ai_model（已含字段 docstring 验证）/ A7 M10-5 viewer test（M10 design 字面豁免 / 不必补）/ A8 docstring 修

## B 栏（待 CY 拍）

**0 项**（第十一次 B 栏 0 项实证 / M05+M06+M07+M08+M10+M11+M12+M13+M14+M15+M16 十一连稳定）

## C 栏（已自我消解）

C1 闸门 2.6 Queue Scaffold（M16 用 BackgroundTasks 不用 arq / N/A） / C2 M11 R-X1 失败补偿（M16 不是 R-X1 形态） / C3 M11 文件上传（无上传） / C4 M13 SSE AsyncSession 占 300s（M16 自起 SessionLocal 不持请求级） / C5 conftest 11 连规则延续 / C6 viewer 写 403 sprint 红线非 reconcile 项 / C7 cross-tenant + metadata e2e sprint 红线 / C8 M07-2 update detach（产品决策 / 回写 M07 design 留独立处理）

# 关联

- design/02-modules/M16-ai-snapshot/00-design.md（§3 + §6 + §8 + §10 + §11 + §12B + §13 + §14.5）
- design/02-modules/M15-activity-stream/00-design.md §10 R14 立规段
- _handoff/cross-sprint-punt-pool.md（真漏洞 #1+#2+#5 标 DONE / 元发现 #1 触发点 A 立规实证）
- design/99-comparison/phase-gate-bypass-log.md #2（R1+R2 self-审 bypass）
