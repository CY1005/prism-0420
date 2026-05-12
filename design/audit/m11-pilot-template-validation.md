---
title: M11 sprint 实证 + R1/R2 命中比例 + L1 第九数据点（首个 R-X1 orchestrator）
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M11 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀（**首个 R-X1 orchestrator 模块**）。

  - 闸门 2.5 三栏：A 8 / B 0 / C 3（**第六次 B 栏 0 项**）
  - R1=3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
  - R2=1 合并 Opus subagent endpoint 单审
  - L1+L2+L3 节奏第九次实证（九数据点稳定 / M02-M11 默认范式可作 M12+ 模板）
  - 元教训新增 3 条 + R-X1 首发新教训 2 条
last_reviewed_at: 2026-05-08
---

# M11 sprint 实证 + Review 命中比例（**首个 R-X1 orchestrator**）

## 模块特性（与 M02-M10 业务/纯读模块对比）

| 维度 | M02-M08 业务 | M10 纯读 | **M11 R-X1 orchestrator** |
|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅（cold_start_tasks）|
| 写跨模块表 | ❌ | ❌ | **❌（强制；R-X1 契约）** |
| 调跨模块 service | 偶尔（R-X2 child）| ❌ | **✅ 4 个 batch_create_in_transaction** |
| 多表事务 | 单表 / 自表+activity_log | N/A | **必须（4 service 共享 db.begin/commit）** |
| 失败补偿（task=failed metadata 持久化）| N/A | N/A | **首发挑战**（R2 P1-01 punt）|
| 文件上传 | ❌ | ❌ | **首发**（multipart/form-data）|

---

## 闸门 2.5 reconcile 三栏（M11 sprint 启动 / **第六次 B 栏 0 项**）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 8 | A1 §14.5 sprint review 计划段补 / A2 4 跨模块 batch_create_in_transaction 接通（M04 R1-A A6 + M06/M07 scaffold "M11 期实装" 全到期）/ A3 conftest fixture 复用 / A4 R-X1 不直 INSERT 跨模块表 / A5 caller 拓扑排序契约（design §6 G5 已决）/ A6 同步 HTTP 路径（design §12 N/A）/ A7 元教训防御 actionable 5 条 / A8 ISSUE_CATEGORIES 跨模块单一真相源 |
| **B 待 CY 决策** | **0** | （第六次 B 栏 0 项 / M05+M06+M07+M08+M10+M11 六连稳定）|
| **C 已自我消解** | 3 | C1 queue N/A（design §1+§12 同步已决）/ C2 R-X1 不是 R-X2（无 child service 注入）/ C3 caller 拓扑责任 design §6 G5 已决（line 238）|

---

## R1 review 命中（3 subagent 并行 / 子片 0+1+2+3 合并审）

### R1-A spec+quality Opus 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | design §5 多表事务格 `with db.begin():` 字面 vs service 不开 begin 实装范式分歧（兼容测试 fixture 妥协）| **立修**：design §5 回写 disambiguation 注释（service 不主动 begin/commit；router 管事务；测试 fixture savepoint 模式下不调 begin_nested）|
| P1-02 | frontmatter `produces_action_types` 用下划线（cold_start_created）vs §10 + 实装点号（cold_start.create）| **立修**：5 秒纠正（M15 订阅靠机械字符串匹配，不一致会订阅失败）|
| P1-03 | dimensions 静默跳过 + activity_log metadata 缺 dimensions_created → R-X1 完整性破坏| **立修**：service.process_csv 在 parse 后检测 dimensions_pending 非空 → 显式 raise ColdStartCsvInvalidError + _mark_failed 落 error_report；metadata 加 dimensions_created=0 字段 |
| P1-04 | _mark_failed 内 dao.update 在外层 IntegrityError 路径会触发 PendingRollbackError 把原异常吞掉| **部分立修**（write_event 包 try/except + 测试覆盖 RuntimeError 路径）；IntegrityError 真路径作 R-X1 punt（feedback_monkeypatch_not_verification 第二次实证）|
| P2 5 项 | tasks.md 缺 R-X1 反例测试 / Mapped[str] vs design 字面 / savepoint 妥协 audit 登记 / update rowcount=0 race 判定 / dao 排序 id desc 二级 | punt 池（部分 audit 登记）|

### R1-B reuse Sonnet 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | _make_task 内联 helper 未进 conftest（M04+M05+M06+M07+M08+M10 七连规则延续）| **立修**：迁 tests/conftest.py make_cold_start_task fixture |
| P1-02 | issue_category 硬编码 `("bug","tech_debt","design_flaw","performance")` 与 issue.py CheckConstraint 重复 | **立修**：api/models/issue.py 导出 ISSUE_CATEGORIES + ISSUE_STATUSES frozenset；M11 csv_parser import 单一真相源 |
| P2 2 项 | _mark_failed dao.update + write_event 双步抽 helper / 大小重复检查 process_csv vs parse_csv | punt（M17 时再评估抽 helper）|
| OK | conftest fixture 全复用 / 4 batch_create_in_transaction 签名匹配 / DAO 模板无重复 / write_event + ck_clause 复用 | ✅ 复用率 ~90% |

### R1-C quality+efficiency Sonnet 命中

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | _mark_failed 内 write_event 抛异常会吞调用方原始异常 | **立修**：write_event 包 try/except + log warning + 测试 test_svc_mark_failed_tolerates_write_event_failure |
| P1-02 | parse_csv 大小检查与 process_csv 前置检查重复 | punt（保留兜底；DRY 改进 M17 sprint 时一并清）|
| P1-03 | issue_category continue 时 node + competitor 已加入 errors 行已被部分入队 | punt（全量回滚语义下逻辑无害；可注释）|
| P2 5 项 | MAX_ROWS 检查时机 / 大小写路径歧义 / dimensions_pending 静默丢失 / BOM/CRLF/空 header 测试盲区 / `parts="/"` 边界 | dimensions 静默丢失已被 R1-A P1-03 立修；其他 punt 池 |

**R1 P1 立修汇总（合并 6 个去重）**：commit `2ccd579`
- 1 frontmatter 5 秒纠正（R1-A P1-02）
- 1 design §5 回写注释（R1-A P1-01）
- 1 dimensions 显式抛错 + activity_log metadata 补齐（R1-A P1-03 + R1-C P1-03）
- 1 _mark_failed write_event 兜底（R1-A P1-04 + R1-C P1-01）
- 1 _make_task 进 conftest（R1-B P1-01）
- 1 ISSUE_CATEGORIES 跨模块导出（R1-B P1-02）
- 附带：M10 残留 ruff F811 重复 fixture / 2 处 unused import 顺手清

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 endpoint 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | commit-then-rollback 把 task=failed 元数据 + 部分业务 INSERT 一起 commit → 违 R-X1 全量回滚契约 | **punt**（R-X1 首发新教训）：彻底修复需独立 connection 或显式 SAVEPOINT，与测试 fixture 不兼容；推迟 M17 sprint orchestrator helper 抽出时一并立 |
| P1-02 | file.read() 整文件读完才 check 413 → attacker 可发 11MB body 全部 buffer | **立修**：file.size 预检（multipart 协议已知大小）→ 不行才 read 兜底 |
| P1-03 | filename `or "upload.csv"` 无 sanitize → path traversal / CRLF 注入 | **立修**：_sanitize_filename(raw) basename + 控制字符 strip + 长度截断 |
| P2 4 项 | model_validate(..., from_attributes=True) 三处冗余 / GET /template 路径含 project_id 是设计意图 / list endpoint 硬编码 user_id 过滤是 design §9 字面 / error_report list[dict]→Pydantic round-trip 测试缺 | punt 池 |

**R2 P1 立修汇总**：commit `2c39980`
- file.size 预检（P1-02）+ filename sanitize（P1-03）+ 2 测试覆盖
- P1-01 punt（首发 R-X1 新教训）

**M11 R2 命中超平均**（M02-M10 R2 平均 0-1 P1，M11 R2 抓 3 P1）→ R-X1 orchestrator endpoint 范式独有命中（commit-then-rollback / 文件上传攻击面 / filename 注入），属"首发"非"漂移"，9 数据点范式稳定。

---

## L1+L2+L3 节奏第九次实证（**九数据点稳定 → M12+ 默认范式可作模板**）

| 层 | 内容 |
|---|---|
| L1 总则 | sprint ≥1 次 review + ≥50 行 OR ≥2 文件触发；触发例外条款全合规 |
| L2 sprint 计划 | design §14.5 sprint review 拆分计划段（commit 8ef59b3 子片 0 prep 落地）|
| L3 实证回写 | 本文件 |

**M11 默认范式**：
- R1 = 3 subagent 并行（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）
- R2 = 1 合并 Opus subagent endpoint 单审
- 子片 5 不单跑（≥80% SKIP 例外）
- M11 自身无 schema 子片（子片 1 = own model + alembic）

---

## R-X1 orchestrator 首发新教训（M11 是首个，沉淀供 M17 参照）

### 教训 1：R-X1 失败补偿事务边界（R2 P1-01 punt 来源）

**现象**：M11 router commit-then-rollback 把"task=failed 元数据"和"部分业务 INSERT"绑同一 commit boundary。
若 batch_create 中第 3 个 service 抛异常 → 前 2 个 service 已 INSERT 的数据 + service 内 dao.update task=failed 一起 commit → 用户看 task=failed 但 DB 有孤儿数据。

**根因**：design §1 G6 + §4 全量回滚契约要求"批量入库失败 → DB 干净"；但 task 元数据持久化要求至少一次 INSERT。两个目标在单 session 单 commit 模型下无法兼容。

**正解**（M17 sprint 立独立 helper 时一并实装）：
- 选项 A：独立 connection（异步 worker 自然有；M11 同步 HTTP 路径需手动开新 session）
- 选项 B：显式 `async with conn.begin_nested()` SAVEPOINT 包业务 → except 内 SAVEPOINT 已 rollback → 主 txn 仍存活 → INSERT failed task → commit
  - **M11 验证**：选项 B 与测试 fixture `join_transaction_mode='create_savepoint'` 冲突（after_transaction_end listener 与手动 begin_nested 互踩）
- 选项 C：抛异常前先 dao.flush task → service 不动外层 commit；router 在 except 块用新 SQL 直 INSERT failed_task 行（绕过 ORM session）

**立规候选**（沉淀到 feedback_problem_layered_analysis 失效信号）：
> R-X1 orchestrator 失败补偿写入路径必须用独立 connection 或显式 SAVEPOINT；
> 禁止与业务事务共享 commit boundary。M11 sprint 范式 punt 至 M17 设独立 helper。

### 教训 2：multipart/form-data 攻击面（M11 是首次 endpoint，M17 异步导入 zip 复用）

**现象**：file.read() 一次读全才 size check → attacker 发 chunked encoding 11MB body 已落盘后才 413。
filename 不 sanitize → path traversal / CRLF 头注入。

**正解**（M11 R2 P1-02 + P1-03 立修）：
- file.size 预检（multipart 协议已知大小不依赖读取）
- _sanitize_filename：basename + 控制字符 strip + 长度截断 255

**立规候选**：
> 文件上传 endpoint 必须 file.size 预检 + filename sanitize；
> 禁止裸 file.read() + raw filename 直入 DB / response header / activity_log metadata。

---

## M02-M10 元教训防御 actionable 应用情况（**M11 R1+R2 主动复制不等抓**）

| # | 元教训 | 应用结果 |
|---|---|---|
| 1 | viewer 写**所有**写端点 403 全覆盖（M07 立 / M08 应用 / M10 N/A 纯读）| ✅ M11 写端点只 1 个（POST /upload）→ test_viewer_write_upload_returns_403 主动覆盖 |
| 2 | write_event 异常传播测试（M04+ 范式）| ✅ test_svc_write_event_exception_propagates |
| 3 | cross-tenant 404（M02 范式）| ✅ test_cross_tenant_returns_404（404 + project_not_found）|
| 4 | cross-project node 422（M06+M07+M08 范式）| N/A M11 不引用其他模块 entity（orchestrator 创建新 entity）|
| 5 | IntegrityError 区分约束名（M05 P1-01）| N/A M11 dao.create 不依赖 unique 约束（G2/G6 无 idempotency）|
| 6 | 纯读模块 docstring 每字段 ≥1 unit test 断言（M10 NEW）| N/A M11 业务模块不适用（"绿测 ≠ 范式正确"通用元教训仍参考）|
| 7 | R1.5 reconcile checkpoint（M10 NEW）| ✅ M11 R1 立修后没有再被 R2 误撤；R2 反向命中 R1 未抓的范式新教训 |

---

## Punt 池总表（M11 sprint 完成期 / 后续 sprint 顺手清）

| # | 项 | 来源 | 推荐时机 |
|---|----|------|---------|
| B1 | R-X1 orchestrator 失败补偿 commit boundary 重构（独立 connection / SAVEPOINT helper）| R2 P1-01 | M17 sprint 异步导入 zip 时立独立 helper |
| B2 | tasks.md 加 R-X1 反例测试（mock dao.execute 直 INSERT nodes 应被 lint 抓）| R1-A P2-01 | M11 sprint 后续追加 / M17 时一并 |
| B3 | design §3 status `Mapped[str]` 注释 follow codebase 范式（vs design 字面 `Mapped[ColdStartStatus]`）| R1-A P2-02 | sprint 5 design 回写时 |
| B4 | savepoint 兼容测试 fixture 妥协登记到 audit/scaffold-design-reconcile.md | R1-A P2-03 | M11 audit 后即时 |
| B5 | dao.update rowcount=0 race / not_found 判定补 | R1-A P2-04 | 后续 sprint 顺手 |
| B6 | dao.list_by_project order_by id desc 二级排序 design §9 回写 | R1-A P2-05 | sprint 5 design 回写时 |
| B7 | _mark_failed dao.update + write_event 双步抽 helper | R1-B P2-01 | M17 sprint reuse 时 |
| B8 | parse_csv vs process_csv 大小检查重复（保留兜底）| R1-B P2-02 / R1-C P1-02 | M17 时一并清 |
| B9 | issue_category continue 时 node/competitor 已入队（全量回滚下无害）| R1-C P1-03 | sprint 内加注释 |
| B10 | MAX_ROWS 早 exit 改 itertools.islice / 大小写路径歧义 / `parts="/"` 边界 / BOM/CRLF/纯 header 测试盲区 | R1-C P2-01/02/05 / R1-C P2-04 | M11 sprint 后续 / M17 |
| B11 | model_validate(..., from_attributes=True) 三处冗余抽 helper | R2 P2-01 | M17 同类时一并清 |
| B12 | error_report list[dict]→Pydantic CsvRowError round-trip 测试 | R2 P2-04 | M11 sprint 后续可加 |

---

## sprint 总览数据

- **commits**：8 主提交（commit hash 见 _handoff/_archive/next-session.md M11 段）
  - 8ef59b3 子片 0 prep（§14.5 + 3 跨模块 batch_create 接通）
  - 4ed8dbe 子片 1（model + alembic + 14 model tests）
  - 090621a 子片 2（DAO + 12 unit tests）
  - e93057c 子片 3（OrchestratorService + 7 ErrorCode + 17 service tests）
  - 2ccd579 R1 立修（6 P1）
  - aba873a 子片 4（router + 4 endpoints + 11 e2e tests）
  - 2c39980 R2 立修（2 P1 + 1 punt）
  - 子片 5 关闸 commit（本 audit + roadmap + handoff）
- **测试**：674 PASS / 0 fail / ruff 净 / R13-1 74=74 / L12 守护通过
- **新增 ErrorCode**：7（cold_start.* 系列）→ R13-1 67→74
- **新增 endpoints**：4（POST upload / GET list / GET detail / GET template）
- **新增依赖**：python-multipart>=0.0.27（FastAPI multipart/form-data）
- **跨模块接通**：3 batch_create_in_transaction（dimension/competitor/issue 与 M11 sprint 启动子片 0 prep 同期接通）+ M03 既有
- **复用率**：~90%（service 层 100%；测试层 1 个 helper 经 R1-B 立修后 100%）

---

## 关联

- design 真相源：design/02-modules/M11-cold-start/00-design.md
- 上游决策：ADR-001（shadow-prism 单 ORM）+ ADR-002（orchestrator + SYSTEM_USER_UUID 但 M11 同步路径不触发）+ ADR-003（跨模块只读策略）
- 跨 sprint 元教训沉淀候选：feedback_problem_layered_analysis 失效信号（R-X1 失败补偿事务边界 / 文件上传攻击面）
