---
title: M17 sprint pilot-template-validation（living tracker）
status: in-progress
owner: CY
sprint: M17
started: 2026-05-09
purpose: |
  M17 AI 导入 sprint（R-X1 第二实例 / 异步 Queue / 闸门 2.6 mini-sprint 合并）实证记录。
  本文件只记 M17 启动期工作（4 大必做项）+ sprint 实施期产出。
---

# M17 sprint pilot-template-validation

## M17 启动期（2026-05-09）

### 闸门 2.5 reconcile pass

**三栏强制分类输出**（M02 元教训 + 闸门 2.5 字面 / 第十四数据点）：

#### A 栏（机械可做 / 直接落 / 8 项）

| # | 项 | 状态 |
|---|---|---|
| A1 | 闸门 3.4 L1 总则修订 — 加 "context budget pressure" 触发例外段（双前置条件 + 3 配套承诺）+ bypass log #2 标 ✅ review 完成 | DONE 2026-05-09 |
| A2 | 闸门 2.6 Queue Scaffold 补完 — `api/queue/base.py` 加 `TaskPayload` 基类 + dummy 子类 + 12 pytest（user_id/project_id 强制 / extra='forbid' / round-trip）| DONE 2026-05-09 |
| A3 | cross-sprint punt #4 SSE 重新评估 — M16 BackgroundTasks + 自起 SessionLocal 已替代长持 SSE / 标 RE-EVALUATE 降级 high → low | DONE 2026-05-09 |
| A4 | M17 design §14.5 sprint review 拆分计划段补完 — 5+ 子片表 + R1=3 subagent + R2=1 合并 Opus + L3 实证子选项 | DONE 2026-05-09 |
| A5 | conftest fixture 预查 — 已有 `make_cold_start_task`（M11）+ 9 个 fixture / M17 不重复立 helper / 十二连规则延续 | DONE 2026-05-09 |
| A6 | R-X1 失败补偿 helper 抽出 — `api/services/orchestrator_helpers.py:compensation_session` async context manager + 4 pytest（yield 行为 / aclose 协议 / 独立 session 实例）；M11 ColdStart 后续迁移留到 M17 sprint 子片 0 prep | DONE 2026-05-09 |
| A7 | cross-sprint punt #11 立规防御未来 — `06-design-principles.md` 加清单 6（service 层 INSERT 凡 UNIQUE 必 catch IntegrityError 转业务异常 + ci-lint R15 grep 守护立规）；M02 project 已实装 / M04 dimension 修存量推迟 | DONE 2026-05-09 |
| A8 | 本会话范围限定 — 启动期 + commit + push + 新会话进 M17 子片 0；遵守 usage_budget v3 单会话 $10 + bypass log #2 配套（spawn subagent 必新 context） | DONE 2026-05-09 |

#### B 栏（CY 拍板）

**0 项**（5 步分层走完后所有候选都归 A 或 C 栏）

#### C 栏（已自我消解）

- **C1**: SYSTEM_USER_UUID 常量 — M16 commit 2273f90 已落 `api/queue/base.py:22`，M17 直接 import
- **C2**: M17 design §3-§13 — P5 audit 4 finding M16 之前已收口 + R4-3a 非常规态登记规约落地
- **C3**: cross-sprint punt #1+#2+#5 — M16 sprint 已关闭
- **C4**: 闸门 2.5 reconcile pass 输出本身 — 即此三栏

### 启动期元教训新教训 1 条 sink memory

#### 新失效信号：reconcile pass 列 B 栏前未穷举 L1 锁规

**首发** 2026-05-09 M17 sprint 启动期 reconcile pass。AI 输出 B 栏 3 项给 CY，CY 反问
「先分析，到底是哪些规则打架，重新归纳是哪一级，是不是分层没分对」一击命中。

**根因**：分层判断时**先列候选再查规则**（先入为主把"看起来要拍"的项归 B 栏，再补
查规则发现 L1 已锁），应**先穷举 L1/L2 锁规再列候选**（规则先于候选）。

**走完 5 步 step 1-2 后实证**：3 项 B 栏候选全部归 A 或 C 栏：

| 原 B 项 | 真实命中规则 | 归类 |
|---|---|---|
| B1 R-X1 真修方案 a/b/c | feedback_rx1_orchestrator_design L1 字面已锁「失败补偿 commit boundary 必独立 connection 或显式 SAVEPOINT」+ M12 元自审"既锁范式裁决型 P1 不让 CY 拍" | A6（自决 a 独立 SessionLocal）|
| B2 cross-sprint 处理范围 a/b/c | cross-sprint-punt-pool 维护规约 L1 字面「约定时机命中即做」+ M17 触发新立规即首个 caller | A7（机械推出本期处理 #7+#11）|
| B3 本会话范围 a/b/c | feedback_usage_budget v3 实施期单会话 $10 + 「不要同一会话连续跑多个 sprint」+ bypass log #2 配套承诺：M17 必恢复 spawn subagent | A8（机械推出 a 启动期 + 新会话进 M17）|

**修法 sink** memory `feedback_problem_layered_analysis.md` 失效信号段：
reconcile pass 输出 B 栏前必跑 grep checklist（feedback memory / ADR design 公共段 /
cross-sprint punt 池 / bypass log），命中任一 → A 或 C 栏。**B 栏 = 0 时禁列 B 栏**
（不为给 CY 拍而拍 / "凑选项"是失效信号）。

### 启动期产出物清单

- `design/00-phase-gate.md`：闸门 3.4 L1 总则触发例外段从 1 类扩到 3 类（a ≥80% SKIP /
  b context budget pressure 双前置 + 3 配套 / c 临时合并 = bypass log）
- `design/99-comparison/phase-gate-bypass-log.md`：触发线 review 标 ✅ 完成 + 修订内容
  指针；触发线不复位继续累计
- `design/00-architecture/06-design-principles.md`：清单 6（service 层 INSERT
  IntegrityError 转换通用规则 + ci-lint R15 待立 + 3 类豁免显式声明）
- `design/02-modules/M17-ai-import/00-design.md`：§14.5 sprint review 拆分计划段
  （5+ 子片 + R1+R2 安排 + L3 实证子选项 + 合规性自审）
- `_handoff/cross-sprint-punt-pool.md`：punt #4 SSE 标 RE-EVALUATE 降级
- `api/queue/base.py`：TaskPayload 基类 + extra='forbid' + UUID coerce
- `api/queue/__init__.py`：导出 TaskPayload
- `api/services/orchestrator_helpers.py`：compensation_session async context manager
  + scaffold 简化决策 4 字段注释 + R-X1 第二实例对照表
- `tests/test_queue_base.py`：12 pytest（强制字段 / extra forbid / coerce / round-trip /
  dummy 子类继承）
- `tests/test_orchestrator_helpers.py`：4 pytest（yield AsyncSession / aclose 协议正常
  退出 + 异常退出 / 独立 session 实例）
- memory `feedback_problem_layered_analysis.md`：新失效信号段（reconcile pass B 栏 0 时禁列）

### 启动期回归数据

- 1063 + 16 = **1079 PASS** / 4 skipped / 0 fail / ruff 净
- ci-lint: R13-1 116 + L12 + L13 + R14 全过
- 文件变更：4 新（queue/base 升级 / orchestrator_helpers + 2 tests）+ 5 改（phase-gate /
  bypass-log / cross-sprint punt 池 / M17 design §14.5 / design-principles 清单 6）

### M17 sprint 子片 0 prep 待续

- M11 ColdStartOrchestratorService._mark_failed + cold_start_router 期望套路迁移到
  compensation_session helper（A6 scaffold 简化决策 ③ ④ 字段触发）
- 测试 fixture 改造：tests/conftest.py 加 M17 sprint 子片 0 prep 的 SessionLocal
  monkeypatch 范式（join_transaction_mode='create_savepoint' 兼容）
- M17 子片 1 model + alembic（import_tasks + import_task_items + ActionType+N + TargetType+N）

---

## M17 sprint 实施期

### 子片 0 prep（2026-05-09）

**A 栏机械落项**：

| # | 项 | 状态 |
|---|---|---|
| P1 | M11 ColdStartOrchestratorService._mark_failed 迁移到 compensation_session：drop `db` 形参 / 内部 `async with compensation_session() as comp_db:` 写 task=FAILED + cold_start_failed 事件 + comp_db.commit()；service `process_csv` 在 dao.create + write_event(cold_start_created) 后立即 `await db.commit()` 让 task 行脱离批量入库事务（独立 connection 可见前提） | DONE |
| P2 | cold_start_router upload_cold_start_csv 失败分支精简为 `await db.rollback()` + raise（移除原"双 commit 试探 + rollback fallback"），R2 P1-01 punt 注释替换为新事务边界声明（cross-sprint punt #7 标 DONE）| DONE |
| P3 | tests/conftest.py autouse fixture `_patch_compensation_session_for_tests` 把 orchestrator_helpers + cold_start_service 两模块的 `compensation_session` 名字 monkeypatch 成 yield 同一 db_session 的实现（生产路径独立 connection 留生产/集成 e2e 验；测试期间靠 savepoint 模拟立即可见 + outer rollback 隔离）| DONE |
| P4 | cross-sprint punt 池触发点 A 4 项预查：M04-1（联合索引仍缺仅 project_id+updated_at 在用）/ M04-8（db.get(DimensionType) 3 处仍直调）/ M04-9（target_type='dimension_record' 5 处 hard-code）/ M04-10（delete_by_node_id race continue 仍跳 activity_log）—— 全 STILL_PUNT；M17 不触 dimension_service 范围，本子片不顺手清，punt 池注解打"M17 子片 0 prep 验证"戳 | DONE |
| P5 | cross-sprint punt 池 #7（R-X1 失败补偿 commit boundary）从 PARTIAL 升 ✅ DONE，引证 commit hash | DONE |

**回归数据**：1079 PASS / 4 skipped / 0 fail / ruff 净 / ci-lint R13-1 116 + L12 + L13 + R14 全过

**R-X1 第二实例对照表**（首个非 M11 caller 的 helper 实证）：

| 维度 | M11 ColdStart（第一实例 / 子片 0 prep 完成迁移）| M17 AI 导入（第二实例 / 子片 1-4 落地）|
|---|---|---|
| 形态 | 同步 HTTP（router → service / 单请求生命周期）| 异步 arq Queue（worker → service / 跨 Queue 任务生命周期）|
| 业务 session | `Depends(get_db)` 请求级 | Queue worker 自起 SessionLocal |
| 失败补偿 session | `compensation_session()` 独立 connection | 同 |
| 任务行 commit 时机 | service 内 dao.create 后立即 `await db.commit()` | 同范式（待子片 3 落地）|
| 失败响应路径 | router 异常分支 db.rollback() + raise / typed JSON 中间件转换 | Queue retry + 死信；compensation_session 写 task=failed/partial_failed |
| 测试 fixture | conftest autouse monkeypatch `compensation_session` ← yield db_session | 同 fixture 复用 |

**启动期元教训新教训沉淀**：

- 在 SQLAlchemy create_savepoint 测试 fixture 下叠加第二个 AsyncSession 在同一 db_connection 上会触发 greenlet 桥接冲突（asyncpg 一连接一活跃操作 / SAVEPOINT 嵌套被两个 session 各自管理）。妥协做法：测试 fixture 把 `compensation_session` 函数本身 monkeypatch 成 yield 同一 db_session（共享 session）。生产路径独立 commit boundary 的真实隔离留生产或专门集成 e2e 验证。
- 同一 service 函数内不要在 `await db.commit()` 失败补偿前再插一次 `await db.rollback()`：listener `_restart_savepoint` 触发的 `sync_session.begin_nested()` 会跑出 greenlet 上下文，下一次 dao.update 抛 MissingGreenlet。范式：service 触发失败补偿时不主动 rollback 业务 session，业务 session rollback 由 router/Queue worker 异常分支兜底。

### 子片 1-5 实施期（2026-05-09 完成）

**子片 1+2+3 commits**：
- `b806931` 子片 1（model + alembic + ActionType+8 + TargetType+1 + 36 model tests）
- `f41ad25` 子片 2（DAO + tenant filter + idempotency 7d + dead_letter 30d + 28 unit）
- `9229759` 子片 3（Service + Schema + 8 ErrorCode + Queue + WS + AI Orchestration / 1003 行 service / 40 新测试）
- `d558b5f` R1 立修（3 subagent 并行审 / 8 P1 合并去重立修）
- `[hash]` 子片 4（Router 7 REST + 1 WS endpoint + 24 e2e）
- `dcf7024` R2 立修（1 合并 Opus 单审 / 4 P1 立修）
- 子片 5 关闸（本 commit）

**回归数据**：1213 PASS / 4 skipped / 0 fail / R13-1 124（M17 +8）/ L12+L13+R14 全过 / ruff 净

**R1 命中数据**（3 subagent 并行 / 元教训防御）：
- R1-A spec+quality Opus：2 P1（partial_failed unreachable IMPL-NOTE / IntegrityError 区分约束名）+ 4 P2 + 6 P3
- R1-B reuse Sonnet：1 P1（make_import_task 迁 conftest / 十二连规则延续）+ 3 重复实现 D1-D3 标记观察
- R1-C quality+efficiency Sonnet：6 P1（N+1 _upsert_dimension_type / publish_progress 3 处 suppress / IntegrityError 同款 / consolidate_step3 set 重建 / awaiting_review→cancelled 缺测 / dimension upsert 调用次数缺测）
- 合并去重：8 P1 立修（commit d558b5f）
- M02-M17 R1 第十五数据点：3 subagent 并行范式稳定（Sprint 复杂度 high 时 R1=3 subagent 范式有效）

**R2 命中数据**（1 合并 Opus 单审 endpoint）：
- 4 P1 立修（commit dcf7024）：WS endpoint 0 e2e（4 鉴权拒绝矩阵 / golden punt integration）+ 413 vs 422 design 字面漂移裁决 + filename sanitize 字面验输出 + IntegrityError race 路径 docstring 注释
- 3 P2 punt（list endpoint viewer 200 矩阵 / get_review viewer 200 / confirm/cancel/retry 失败路径 db.rollback 隐式）
- 4 P3 nit（lazy import / docstring 字面 vs 实装漂移 / NULL byte 测试 / Response import 提到顶部）
- M02-M17 R2 第十四数据点：1 合并 Opus 单审 endpoint 形态稳定

**闸门 2.5 三栏第十二次 B 栏 0 项实证**（M05+M06+M07+M08+M10+M11+M12+M13+M14+M15+M16+M17 十二连稳定 / B 栏 = 0 时禁列 B 栏元规则继续守护）

### §14.5 L3 实证子选项回写

- **R-X1 第二实例对照（最终）**：见上方对照表 + R-X1 helper（compensation_session）零摩擦实证 — M11 第一实例迁移在子片 0 prep / M17 直接复用，无重新实装成本；R-X1 helper 横切设计验证有效
- **闸门 2.6 mini-sprint 是否单独 commit**：合并到子片 0 prep（commit ad069c0 启动期 + 7a6327f 子片 0 prep）单 commit 落地，TaskPayload + SYSTEM_USER_UUID + queue/base scaffold + orchestrator_helpers 同 sprint 同 commit 链
- **arq @task + Redis worker 部署**：arq 实际部署 docker-compose 段落 punt 后续运维 sprint（M17 sprint 范围仅 @task 函数定义 + Queue worker 自起 SessionLocal 范式实证；实际 enqueue 由 router 转 Queue 真接通在生产部署 sprint）

### M17 sprint 实施期元贡献清单

1. **R-X1 第二实例零摩擦验证** — compensation_session helper 横切设计成本控制有效（M11 第一实例 / M17 第二实例 / 后续 R-X1 caller 直接复用）
2. **WebSocket endpoint 首发 + Query Bearer 鉴权范式** — design §8 audit B6 每命令 task_id 重校实装 + 4 鉴权拒绝矩阵 e2e + golden integration sprint 推迟
3. **idempotency_key 含 project_id（B1 修复）实装实证** — UNIQUE(user_id, project_id, source_hash) + service.find_idempotent 7d 复用窗口 + IntegrityError 端到端 catch（清单 6 落地）
4. **N+1 防护批量 cache 范式** — _upsert_dimension_type 循环改批量 unique key 预查 cache（5 dim / 2 unique key → 2 次 upsert 而非 5）/ 后续 sprint dimension_type_key 路径复用
5. **filename sanitize 字面验输出范式** — M11 R2 P1-03 立 / M17 R2 P1-03 强化（不仅 not-crash 必字面验 source_uri 输出）
6. **partial_failed IMPL-NOTE 范式** — design §10 字面 vs 实装 §4 single-tx all-or-nothing 决策的实装 gap 显式登记（防未来误判 / 入边 enum 字面保留备 ai_step2 chunk 化）
7. **R-X1 第二实例 sprint 元发现：design §7 字面 status code 漂移**（413 vs 422）— 立规 sink 候选：每 sprint 关闸 R2 必跑 reconcile checkbox（design 字面异常契约 vs router 抛的 AppError.http_status）

### M17 sprint 元教训新教训 sink memory 候选

1. **WS endpoint 测试矩阵立规**（feedback_ws_endpoint_test_matrix.md 候选）：WS endpoint sprint 必须包含 5-test 矩阵（invalid token / wrong type claim / cross-tenant / cross-owner / golden accept）；不能用 broker 单测代替 endpoint e2e。R-X1 第二实例首发漏洞实证。
2. **filename sanitize horizontal 化触发条件**：第三实例（M18+ multipart 上传）触发横切到 api/utils/upload_helpers.py；同时 sanitize 测试必须字面验输出（M17 R2 P1-03 立规 / 不仅 not-crash）
3. **multipart 上限分级表**（engineering-spec §X 立）：小文件 10MB（M11 cold_start CSV）/ 大归档包 100MB（M17 zip / git_bundle）/ 超大场景明示

### bypass log #2 配套验收

- **spawn subagent 已恢复**：M17 R1 = 3 subagent 并行（A/B/C 不同模型 spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）+ R2 = 1 合并 Opus subagent；累计 bypass = 2 次（M16 sprint）/ M17 已恢复，触发线计数不复位 → 下次 bypass = 3 次 → 触发对闸门 3.4 L1 总则的 review
- **spawn prompt 含 ls/find 穷举要求**：✅ R1 三 subagent + R2 prompt 全含 cross-sprint 元发现 #5 立规字面要求（"穷举要求 / 不能凭'看了主要文件'判断完整性"）

### cross-sprint Punt 池接通

子片 5 同 commit 内：
- punt #7（R-X1 失败补偿 commit boundary）✅ DONE 已在子片 0 prep commit 标记
- 新 punt 入池：
  - WS golden e2e（R2 P1-01 punt integration sprint）
  - _sanitize_filename horizontal 化（M11+M17 重复 / 第三实例触发立规）
  - confirm_review 绕过 _transition 缺 import_status_changed event（R1-A P2-3）
  - 6 处 lazy import from api.core.db / from api.queue.import_tasks 抽 helper（R1-A P3-3）
