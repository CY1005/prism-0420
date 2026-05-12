---
fix: B-cold-start-validation-deadlock
audit_mode: B 路径必启 audit（6 项自评 2 高 / 4 中 / 主 agent 自跑详查 design + ADR + 06-design-principles + M11 design + R-X1 orchestrator memory）
audit_scope:
  - design/02-modules/M11-cold-start/00-design.md（§5 多人架构 4 维 / §4 状态机 / §6 分层职责 / §1 G6 全量回滚 / docstring）
  - design/00-architecture/06-design-principles.md（5 原则 + 约束清单 1-6 + 多人架构 4 维必答）
  - design/adr/ADR-001-shadow-prism.md + ADR-002 batch_create_in_transaction
  - api/services/orchestrator_helpers.py（compensation_session helper docstring）
  - api/services/cold_start_service.py docstring L9-25（R-X1 orchestrator commit boundary）
  - memory feedback_rx1_orchestrator_design（commit boundary 隔离原则）
  - tests/conftest.py（join_transaction_mode='create_savepoint' fixture 兼容性）
created: 2026-05-12
verdict: 1 medium 冲突（design L289 字面 vs 实装 commit 时机偏离 / 但本 fix 与 docstring + 清单 6 commit boundary 隔离精神一致 / design 字面同步更新由 CY 拍板）+ 1 low 漂移记录（M17 R-X1 第二实例对照表更新建议）
---

# Design 冲突 audit — B-cold-start-validation-deadlock（B 路径 / 详查）

## §1 冲突清单（4 字段）

### 冲突 #1（核心 / 已存在的漂移 / 本 fix 加深差距 / 与 docstring 一致）

| 字段 | 内容 |
|------|------|
| **design 出处** | `design/02-modules/M11-cold-start/00-design.md` §5 多人架构 4 维必答 L289 "多表事务"行 |
| **design 字面** | "Sprint 实装范式：service 不主动 begin/commit/rollback；caller（router）管事务（成功 commit / 失败 commit task 失败状态 + rollback batch 数据）..." |
| **本 fix 改动** | service 层 cold_start_service.py L342 + L407 状态扭转后立即 `await db.commit()`（2 处新增 commit 点） |
| **冲突类型** | 字面偏离 — design L289 字面"service 不主动 commit"被 M17 sprint 子片 0 prep（2026-05-09）+ 本 fix 共同字面突破；但 docstring + design §1 G6 全量回滚 + 清单 6 commit boundary 隔离原则字面一致允许 |
| **严重度** | 🟡 **medium** — design L289 字面被实装颠覆 / 但 design 同文档 docstring（cold_start_service.py L9-25）已字面豁免 task 创建立即 commit；本 fix 把豁免范围扩展到状态扭转 / 字面同步更新由 CY 拍板时统一改（非阻塞本 commit） |
| **处置建议** | CY 批准 fix 后同步更新 M11 design §5 L289 字面："service 不主动 begin；task 创建 + 状态扭转可立即 commit（释放行锁 / 让 compensation_session 独立 connection 不阻塞）；业务批量 INSERT 仍由 router 统一 commit/rollback。引用：_handoff/dogfooding/04-bug-fixes/B-cold-start-validation-deadlock/rca.md" |

### 冲突 #2（次要 / 设计原则字面一致 / 仅命名补强）

| 字段 | 内容 |
|------|------|
| **design 出处** | `design/00-architecture/06-design-principles.md` 多人架构 4 维必答 + 约束清单 1-6 |
| **design 字面** | 多人架构 4 维 = Tenant / 事务 / 异步 / 并发；清单 6 service 层 INSERT 凡 UNIQUE 必 catch IntegrityError；未约束 UPDATE + 后续 compensation_session 模式的 commit 时机 |
| **本 fix 改动** | service 层 UPDATE 后立即 commit（与既有清单不直接冲突 / 但属于"约束盲区"） |
| **冲突类型** | 引入新模式但属合理收敛（commit boundary 隔离精神延伸）|
| **严重度** | 🟢 **low** — 不破坏既有原则 / 属于补强 |
| **处置建议** | cross-sprint pool 候选 R-LOCK-1：CI 守护 service 层 `dao.update(.*)` 后续 N 行没有 `await db.commit()` 且函数体内含 `compensation_session()` → 告警（待立 / 不阻塞本 commit） |

### 冲突 #3 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M11-cold-start/00-design.md` §4 状态机（L242-281）+ §1 G6 全量回滚 |
| **结果** | **无冲突** — 状态机只声明合法转换路径（pending → validating → importing → completed/failed），未约束 commit 时机；G6 全量回滚是业务 INSERT 路径（本 fix 不动业务事务边界 / router 仍 commit 业务 / 失败仍 rollback） |
| **严重度** | N/A |

### 冲突 #4 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M11-cold-start/00-design.md` §6 分层职责表 L305-323 + 禁止清单（L320-323）|
| **结果** | **无冲突** — 禁止清单约束 service 不直 INSERT 跨模块表 + 不直查 DB（DAO 隔离）/ 本 fix 没破坏分层 / 仅在 service 调 dao.update 后加 commit |
| **严重度** | N/A |

### 冲突 #5 候选（已检 / 无冲突 / R-X1 一致）

| 字段 | 内容 |
|------|------|
| **检查范围** | `api/services/orchestrator_helpers.py` docstring L9-75（R-X1 第二实例对照表 + commit boundary 隔离原则）+ memory `feedback_rx1_orchestrator_design` L1 字面 |
| **结果** | **本 fix 与 R-X1 原则完全一致** — orchestrator_helpers docstring L31-44 字面：业务事务 commit / 失败补偿独立 connection commit；本 fix 把状态扭转 commit 释放行锁 = 完整执行 commit boundary 隔离精神 / 让 compensation_session 真正独立 |
| **严重度** | N/A / 反方向 = audit 加分 |

### 冲突 #6 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | tests/conftest.py L89-114 + L132-165（db_session + _patch_compensation_session_for_tests fixture）|
| **结果** | **无冲突** — 测试期间 compensation_session 被 monkeypatch 成共享 db_session / `db.commit()` 在 savepoint 模式下 = release savepoint（非真 commit）/ 测试期间不会真的 commit 到 prism_test 库 / fixture 设计字面兼容；实证：tests/test_m11_* 58/58 PASS 含 row_validation + batch_fail + completed_chain |
| **严重度** | N/A |

### 冲突 #7 候选（已检 / 无冲突 / Queue worker M17 范式对照）

| 字段 | 内容 |
|------|------|
| **检查范围** | M17 import_service.py（R-X1 第二实例）+ ai_snapshot_runner.py |
| **结果** | M17 整体跑在 Queue worker 自起 SessionLocal / session lifecycle 自洽 / 不与 HTTP 请求共享 txn / 实测 M17 sprint 启动期已有 race 路径测试覆盖 + 全 PASS / 本 bug 是 M11 同步路径独有 / **M17 无同 bug 不需 follow-up** |
| **严重度** | N/A |

### 冲突 #8 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | ADR-001 单 ORM SQLAlchemy + ADR-002 batch_create_in_transaction（M11 → M03/M04/M06/M07 调用契约）|
| **结果** | ADR-001 字面"事务边界=Service 层" / 本 fix 把 service 层事务边界更精细化（task 创建 commit + 状态扭转 commit + 业务 INSERT router commit）/ ADR-002 batch_create_in_transaction 接口不变 / 不破任何 ADR |
| **严重度** | N/A |

## §2 总结

| 冲突 # | 严重度 | fix 内合并解决 | 后续 follow-up |
|--------|--------|---------------|---------------|
| #1 | 🟡 medium | ❌（fix 范围红线"不动 design 字面"）| CY 拍板后单独改 design/02-modules/M11-cold-start/00-design.md §5 L289 |
| #2 | 🟢 low | ❌ | cross-sprint pool 候选 R-LOCK-1 CI 守护（不阻塞 commit） |
| #3-#8 | 🟢 无 | N/A | N/A |

**verdict**: **0 high / 1 medium / 1 low 冲突**

按 dogfooding plan §3 6 项自评：
- 改动范围 中 / 代码位置 高 / 可逆性 中 / 业务断言 中 / 测试覆盖 中 / bug 类型 高
- 2 项高 / 4 项中 → **B 路径必启 audit**（已跑 / 形式 audit 完）

**B 路径合并 commit 条件检查**：
- design 0 high 冲突 ✅
- 1 medium 冲突属于字面同步漂移（已有 docstring 字面豁免 / design §1 + 清单 6 精神一致）/ 不阻塞 commit
- 1 low 是改进建议 / 不阻塞

→ **B 路径 commit 通过 / medium 冲突的字面同步交主 agent 后续整理（与前 trigger-bug fix 06-frontend-spec.md L96 字面同步等量齐观）**

## §3 安全 / 正确性 reasoning（CY 拍板辅助材料）

### §3.1 业务事务边界变化是否破坏 G6 全量回滚

**design §1 G6**：批量入库阶段全量回滚（任一行失败回滚全部业务写入）

**本 fix 不破坏 G6**：
- task 创建 + 状态扭转 commit 的是 `cold_start_tasks` 这一张表的元数据 / **不属于"业务批量入库"范畴**
- 业务批量入库（M03 NodeService.batch_create / M06 Competitor / M07 Issue）仍由 router 持有 outer txn 统一 commit/rollback
- 失败时：comp_db 写 task=failed + activity_log_failed（commit）/ 业务 db rollback 业务 INSERT（保持 G6 全量回滚）

### §3.2 race conditions / 并发用户

- 同一用户重传同一 CSV：design G2/G6 显式声明无 idempotency / 每次创建新 task / 不冲突
- 不同用户同时上传：不同 task.id / 行锁互不影响
- 同一 task 不被多 process 同时操作（task 创建 + service.process_csv 是请求级单线程）

### §3.3 可观测性 / 失败模式

- 修后状态扭转独立 commit → activity_log + task 元数据落盘节奏更清晰
- 失败路径 _mark_failed 仍走 compensation_session 独立 commit / 即使 router rollback 业务事务，failed 状态可见
- 用户拿到 422 + 详细 error_report（row + field + message）/ 体验改善

### §3.4 测试范式兼容

- tests/conftest.py monkeypatch compensation_session = db_session（savepoint 模式 / commit = release savepoint）
- 本 fix 新增的 await db.commit() 在测试期间 = 释放 savepoint / 不会真的 commit 到 prism_test 库
- 58/58 PASS 实证兼容

**结论**：B 路径 audit 通过 / medium 冲突仅是 design 字面同步偏差 / 实装与 design 精神 + docstring 一致 / 不阻塞 commit。

## §4 design 漂移登记（不属冲突 / 仅记录建议）

| # | 漂移项 | 影响 | 建议处置 |
|---|-------|------|---------|
| D1 | design/02-modules/M11-cold-start/00-design.md §5 L289 字面 vs cold_start_service.py 实装 commit 时机三态不一致 | 维护者读 design 字面以为不 commit / 实装已 commit 2 处（本 fix 后） | 主 agent 拍板后更新 L289 |
| D2 | R-X1 第二实例对照表（orchestrator_helpers.py docstring L68-74）应加 "状态扭转 commit 时机" 行 | M17 ImportService 维护者读对照表时缺少 "为何 M11 commit 状态扭转" 上下文 | 主 agent 拍板后扩 docstring 表 |
| D3 | 06-design-principles.md 清单 6 可扩展到 "service 层 UPDATE + 后续 compensation_session 必先 commit 释放行锁" | 防 race / deadlock 通用规则 | cross-sprint pool 候选 R-LOCK-1 CI 守护 |

**这些登记不阻塞本 fix commit**（属于 design follow-up）。
