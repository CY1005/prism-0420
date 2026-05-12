---
fix: B-cold-start-validation-deadlock
bug_class: P0 / M11 cold-start 校验失败路径完全不可用（任何含行级校验错的 CSV 让 backend worker 挂起）
root_cause: cold_start_service.py L342 `dao.update(VALIDATING)` 后未 commit / AsyncSession 自动开启的隐式 txn 持有 cold_start_tasks 行锁 / 后续 _mark_failed 走 compensation_session() 新 connection UPDATE 同行 → PostgreSQL 行级锁互斥 → comp_db 等业务 db 释放锁，业务 db 等 _mark_failed 完成才 raise → 双向永久阻塞 / HTTP 请求 30s timeout
fixed_by: api/services/cold_start_service.py 在 L342 dao.update(VALIDATING) + L407 dao.update(IMPORTING) 两处状态扭转后立即 `await db.commit()`（与 L339 任务创建立即 commit 范式对齐）/ 释放行锁让 compensation_session 独立 connection 不阻塞
created: 2026-05-12
status: 已修 / M11 "[P0] 校验失败响应体" 转 PASS / tests/test_m11_* 58 PASS / next build PASS
---

# RCA — B-cold-start-validation-deadlock

## §1 现象（P2 spike subagent 真复现）

来源：`_handoff/dogfooding/03-bug-queue.md` `B-P2-M11-validation-hang` + M11 spec L544 "[P0] 校验失败响应体 — COLD_START_ROW_VALIDATION_FAILED 格式"。

- 入口：editor 已登录 → POST `/api/projects/{pid}/cold-start/upload` multipart CSV 含至少一行行级校验失败（如 `node_path` 不以 `/` 开头：`InvalidPathWithoutSlash`）
- 现象：HTTP 请求挂起 / 不返回任何 status / curl timeout / playwright test 30s timeout
- 复现 100%（spike subagent 独立验证 + 本次 fix 期 e2e timeout 复现）

## §2 根因深定位

### §2.1 SQLAlchemy AsyncSession 隐式 txn + 行锁机制

PostgreSQL `UPDATE` 默认行为：

```
1. session.execute(update(...).where(id=task.id).values(status="validating"))
2. PostgreSQL 在该 connection 的 txn 中对 task 行加 ROW EXCLUSIVE 锁
3. 锁释放时机：txn COMMIT 或 ROLLBACK
4. SQLAlchemy AsyncSession 在 commit() 后 next statement 自动 begin（隐式 txn / 不需要显式 db.begin()）
```

### §2.2 deadlock 触发链（修前）

```python
# api/services/cold_start_service.py（修前）
# L320: dao.create(db, task)
#   → INSERT INTO cold_start_tasks; flush（task 行加锁 / 内存 ORM 状态）
# L339: await db.commit()
#   → COMMIT；task 行可见 + 锁释放（OK）

# L342: dao.update(db, task.id, ..., {"status": "validating"})
#   → SQLAlchemy 自动 begin 隐式 txn
#   → UPDATE cold_start_tasks SET status='validating' WHERE id=task.id
#   → task 行 ROW EXCLUSIVE 锁加上 / 锁在 txn 范围内持有
#   → 🔴 不 commit！txn 持续打开

# L391-401: parsed.errors 非空 → await self._mark_failed(...)
#   → L535: async with compensation_session() as comp_db:
#     → 自起 SessionLocal → 新 connection（独立 connection / R-X1 commit boundary 隔离设计）
#   → L536: await self.dao.update(comp_db, task.id, ..., {"status": "failed", ...})
#     → 新 connection 上 UPDATE cold_start_tasks WHERE id=task.id
#     → 🔴 等业务 db 释放 task 行锁 → 永远不会等到（业务 db 在 await _mark_failed）

# Result: comp_db.execute() 阻塞等行锁；业务 db 阻塞等 _mark_failed 完成
# → 双向 deadlock / HTTP 请求 30s timeout
```

### §2.3 为什么 L339 任务创建立即 commit 范式没扩展到状态扭转

`cold_start_service.py` docstring L9-25 写得很清楚：

> 任务创建后立即 commit（service 内 await db.commit()）—— 把 task 行从批量入库事务里解耦出去，让失败补偿能从独立 connection 看到任务。

**M17 sprint 子片 0 prep（2026-05-09）重构 R2 P1-01 punt 关闭时**，只在 L339（task 创建后）加了 commit，没考虑到 L342 / L407 同样会持有 task 行锁。docstring 字面"task 行从批量入库事务里解耦"理解为"task 创建只走一次"——但实际状态扭转（VALIDATING / IMPORTING）也是 UPDATE 同表同行，同样持锁。

**重构盲区**：作者认为 status 转换由 router 持有的 outer txn 在最终 commit / rollback 时统一收尾，忽略了"失败路径走 compensation_session 新 connection 需要看到/写到 task 行 / 必须先释放锁"这个延迟约束。

### §2.4 验证细节

修前手动 curl 复现：

```bash
TOKEN=...
PROJ=...
echo "node_path
InvalidPathWithoutSlash
/ValidNode" > /tmp/bad.csv

time curl -X POST "http://localhost:8000/api/projects/$PROJ/cold-start/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/bad.csv;type=text/csv" \
  --max-time 15

→ timeout（修前 100% 复现）
→ 修后：HTTP 422 + body {"code":"cold_start_row_validation_failed","message":"...","details":{...}}
```

## §3 类似问题 grep 清单

### §3.1 同模式 grep：service 层 UPDATE + 后续 compensation_session 路径

```bash
cd /root/workspace/projects/prism-0420/api
grep -rln "compensation_session" services/
```

结果：

| # | 文件 | 模式 | 风险 | 状态 |
|---|------|------|------|------|
| 1 | services/cold_start_service.py | dao.update + compensation_session | 🔴 高（本 bug） | **修** |
| 2 | services/import_service.py | M17 AI 导入 / arq Queue worker / compensation_session | 🟡 中（同模式但运行环境不同 / Queue worker session 不与 router 共享） | 已检 / Queue worker 自起 session 完整 commit-or-rollback / 无同 bug |
| 3 | services/orchestrator_helpers.py | 仅 helper 定义 / 不持锁 | 🟢 无 | N/A |

### §3.2 import_service.py audit

<details><summary>展开</summary>

`api/services/import_service.py` 是 M17 AI 导入 / arq Queue worker 用：

- 整体跑在自起 SessionLocal（`api/services/ai_snapshot_runner.py` 范式 / R-X1 第二实例）
- 失败补偿也走 compensation_session 但发生在 **同一 process / 不同 connection**
- session lifecycle 由 Queue worker context 管理 / 不与 HTTP 请求 db 共享 txn
- 实测：M17 sprint 启动期已有 deadlock 测试覆盖（test_m17_*.py 含 race 路径）/ tsc + pytest 全 PASS

**结论**：import_service.py **无同模式 bug** / 其 session lifecycle 自洽 / 不需修。

</details>

### §3.3 punt 清单

无 punt — 本 fix 范围内同模式仅 1 处命中 + 已修；M17 不需改。

## §4 design vs 实装漂移定位

### §4.1 design 哪步漏了？

`design/02-modules/M11-cold-start/00-design.md` §5 多人架构 4 维必答 L289：

> **多表事务** ✅ 必须（批量入库阶段）| **Sprint 实装范式**：service 不主动 begin/commit/rollback；caller（router）管事务...M11 R1-A P1-01 立修注释（2026-05-08）

**漂移点**：design L289 说 "service 不主动 begin/commit/rollback" / 但 M17 sprint 子片 0 prep 重构时已经字面豁免 L339 立即 commit（cold_start_service.py docstring L14 "task 创建立即 commit"）/ design L289 没同步更新 / 形成 **三态不一致**：
1. design L289 字面：service 不 commit
2. cold_start_service.py docstring L14：task 创建立即 commit
3. 实装代码 L339：实际 commit / 但状态扭转 L342 不 commit

本 fix 把实装从 "部分 commit" 升级到 "状态扭转都 commit"，让 docstring 字面"commit boundary 隔离"覆盖全状态机 / **比 design L289 更严格 / 但与 docstring + design §1 G6 全量回滚契约 + design/00-architecture/06-design-principles.md 清单 6（commit boundary 隔离）一致**。

### §4.2 design 字面豁免依据（本 fix 合规化路径）

- `feedback_rx1_orchestrator_design` L1（memory）字面：失败补偿 commit boundary **必独立 connection / 禁与业务事务共享 commit**
- `design/00-architecture/06-design-principles.md` 清单 6（2026-05-09 立）字面：commit boundary 隔离
- `api/services/orchestrator_helpers.py` docstring 第 5-10 行：M11 ColdStart（第一实例）+ M17 AI 导入（第二实例）的"失败补偿 commit boundary"对照表

→ **本 fix 是 design 字面授权范围内的实装收敛**（design L289 那一行需要更新文字、但行为上本 fix 与 commit boundary 隔离原则一致）

### §4.3 应该如何避免

1. **dogfooding sprint phase2-case.md §禁止模式 候选新增**：
   - "service 层 DAO UPDATE 后必须显式 commit 或保证后续 compensation 不跨 connection / 否则行锁 + 新 connection UPDATE = deadlock"

2. **CI 守护候选（cross-sprint pool）**：
   - `R-LOCK-1`：grep service 层 `dao.update(.*$` 后续 N 行没有 `await db.commit()` 且函数体内含 `compensation_session()` → 告警

3. **design/02-modules/M11-cold-start/00-design.md §5 字面修正**：
   - 把 L289 "service 不主动 begin/commit/rollback" 改成 "service 不主动 begin / 但状态扭转 + task 创建可立即 commit 释放行锁，业务批量 INSERT 仍由 router 统一 commit/rollback"
   - 加引用 `_handoff/dogfooding/04-bug-fixes/B-cold-start-validation-deadlock/rca.md`

4. **R-X1 第二实例对照表更新**：
   - `api/services/orchestrator_helpers.py` 类型表加 "状态扭转 commit 时机" 行 / 同步 M11 和 M17

## §5 fix 改动

| 文件 | 行 | 改动 | 类型 |
|------|----|------|------|
| api/services/cold_start_service.py | L342-L351 | dao.update(VALIDATING) 后立即 `await db.commit()` + 注释 | 核心 |
| api/services/cold_start_service.py | L407-L420 | dao.update(IMPORTING) 后立即 `await db.commit()` + 注释 | 核心 |

**未动**：
- `api/services/orchestrator_helpers.py`（helper 字面正确 / docstring 已字面说明 commit boundary 隔离）
- `api/dao/cold_start_dao.py`（DAO 层不 commit / 行为正确）
- `api/routers/cold_start_router.py`（router 末尾 commit 业务事务 / 失败 rollback / 字面正确）
- `tests/conftest.py`（compensation_session monkeypatch 在测试期间共享 session / 我加的 db.commit() 在 savepoint 模式下 = release savepoint / 测试不受影响 / 58/58 PASS 实证）
- `design/02-modules/M11-cold-start/00-design.md`（design 字面同步建议见 §4.3 / 由主 agent 拍板时统一改）

### dogfooding 6 项自评

| # | 维度 | 评级 | 备注 |
|---|------|------|------|
| 1 | 改动范围 | **中** | 单文件 2 处 + ≈15 行 / 比 plan 预估 "中 1-2 文件" 准 |
| 2 | 代码位置 | **高** | service 层 + transaction 边界 |
| 3 | 可逆性 | 中 | 不动 schema / 不破坏 ORM 状态 / 但改 transaction 边界语义（多 commit 点） |
| 4 | 业务断言 | 中 | 改 transaction 边界 / 状态机 VALIDATING + IMPORTING 路径分别 commit / 失败路径不再 deadlock |
| 5 | 测试覆盖 | 中 | M11 spec "[P0] 校验失败响应体" 转 PASS / tests/test_m11_service 等 58 PASS（含 row_validation + batch_fail + completed_chain 等）|
| 6 | bug 类型 | **高** | race / deadlock |

**3 项高 / 中 → B 路径必启 audit**。见 `design-audit.md`。

## §6 验证证据

### §6.1 tsc + next build

```
pnpm exec tsc --noEmit → exit=0
pnpm exec next build → ✓ Compiled successfully in 8.2s
```

### §6.2 backend pytest M11 套件

```bash
uv run pytest tests/test_m11_service.py tests/test_m11_routers.py tests/test_m11_dao.py tests/test_m11_models.py
→ 58 passed in 3.98s

含覆盖路径：
- test_svc_process_csv_row_validation_fail_marks_failed（行级校验失败 → mark_failed → failed 终态）
- test_svc_process_csv_batch_fail_rolls_back_keeps_task（batch insert 失败 → mark_failed → failed 终态 + task 仍存活）
- test_svc_process_csv_pending_to_completed_status_chain（happy path 状态链 pending → completed）
- test_svc_mark_failed_tolerates_write_event_failure（_mark_failed 内 write_event 抛异常不遮盖 task 状态落盘）
```

### §6.3 backend pytest 邻近模块（regression）

```
tests/test_m03_service.py + test_m03_dao.py + test_m04_service.py + test_m04_dao.py
+ test_m14_service.py + test_m14_routers.py（M11 batch_create_in_transaction 依赖 M03/M04 / M14 不相关 regression）
→ 217 passed
```

### §6.4 E2E Playwright

```
M11 "[P0] 校验失败响应体 — COLD_START_ROW_VALIDATION_FAILED 格式": ✅ PASS (640ms)
  修前：HTTP timeout / 修后：HTTP 422 + body 含 "row" + "field" + "message" + "COLD_START"
M11 其他 9 spec 仍 PASS（无 regression）
M01 + M02 + M20 regression 36/36 PASS
```

### §6.5 真实复现 curl

```bash
# 修后验：
$ TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -d '{"email":"e2e@example.com","password":"Password123!"}' -H "Content-Type: application/json" | jq -r .access_token)
$ PROJ=$(curl -s -X POST http://localhost:8000/api/projects -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name":"x","description":"","template_type":"custom"}' | jq -r .id)
$ printf 'node_path\nNotSlash\n' > /tmp/bad.csv
$ time curl -X POST "http://localhost:8000/api/projects/$PROJ/cold-start/upload" -H "Authorization: Bearer $TOKEN" -F "file=@/tmp/bad.csv;type=text/csv" --max-time 15
< HTTP/1.1 422
< Content-Type: application/json
{"code":"cold_start_row_validation_failed","message":"...","details":{...}}
real    0m0.142s   # 修前 timeout / 修后 142ms
```

## §7 后续闭环

- 主 agent 拍板 design L289 字面更新（见 §4.3 #3）
- B-P2-M11-validation-hang 从 OPEN 池移到 FIX_DONE 池
- import_service.py（M17）无同模式 bug 实证 / 不需 follow-up
- 反向应用规则候选（cross-sprint pool）：R-LOCK-1 CI 守护
