---
title: M16 audit fix 复审
verifier: opus-verify-agent
created: 2026-04-25
target: M16-ai-snapshot/00-design.md (post-fix)
audit_source: M16-ai-snapshot/audit-report.md
---

# M16 audit fix 独立复审

> 复审协议参 M13 audit-verify.md 范式。每条引用 fix 后文件具体行号。

## 逐项判定

### B1 DB UniqueConstraint vs 5min/failed 复用语义矛盾 — 🟡 Partial

- 修复主路径：`00-design.md:210-218` 显式注释取消 UniqueConstraint，改用 ORM `find_idempotent` + `pg_advisory_xact_lock`；`__table_args__` 中确实已删除 UniqueConstraint；`00-design.md:222-223` 增 `(status, created_at)` + `(user, project, node, version_count, created_at)` 复合索引支撑查询。`00-design.md:268` "不建 UniqueConstraint" 明确。
- 残留 1（**严重**）：`00-design.md:843` §12B 字段 ① 任务表 schema 子模板里**仍写** `UniqueConstraint(user, project, node, version_count)  # 幂等 DB 强制`。这是后台子模板的"未来照抄要点"，与 §3 决策直接冲突，未来后台模块照抄会重新踩 B1 同款坑。必须删或改写为 "幂等用 ORM + advisory lock，不要 DB UniqueConstraint"。
- 残留 2（**严重**）：`tests.md:254` D 段 R11-2 测试断言"相同 project 二次插入 → DB UniqueConstraint 拒绝"——B1 取消 UniqueConstraint 后此断言永远失败，测试用例已不可执行。需改为"通过 advisory lock 串行化后只产生 1 行；并发 3 协程拿同一 task_id（与 I1b 等价）"。
- 协同正确性核查：`00-design.md:711-734` create_task 流：`begin()` → `pg_advisory_xact_lock` → `find_idempotent` → `dao.create` → 出 with 块 commit + 释放锁。后到的 B 协程进入 begin → 阻塞拿锁 → A 已 commit 释放 → B find_idempotent 能看到 A 行（同事务隔离 read committed 默认；新事务可见已 commit 行）→ 命中复用。OK。

### B2 DimensionSnapshotItem.content: dict — 🟢 Resolved

- `00-design.md:469-473` `content: dict[str, Any]` ✓
- `00-design.md:773-792` save 代码示例传 `content={"summary": review.summary}` 与 `content=dim.content` 均为 dict ✓
- `00-design.md:38-46` 用户场景画面文字描述未涉及类型，无 str 残留
- `tests.md:33` 断言 `content == {"summary": "..."}` + B5/B5b 形态测试到位 ✓

### B3 BackgroundTasks 心智 / SELECT FOR UPDATE → CAS — 🟡 Partial

- 修复主路径：`00-design.md:359-379` 重写竞态分析；废 SELECT FOR UPDATE 心智模型，改 CAS UPDATE；`00-design.md:618-634` `cas_complete` DAO 实现；`00-design.md:393` 分层职责表说 runner "自起新 session（with SessionLocal()…）"。
- 残留 1：`00-design.md:393` 仅文字说"自起新 session"，**没有代码示例**展示 `with SessionLocal() as db:` + 失败路径调 `cas_complete(status='failed', error_code=…, error_message=…)`。原 audit M3 修复要求 "§6 Background Task 层补一段示例代码（含 with SessionLocal: with db.begin())" — 未落地。
- 残留 2：`cas_complete` 默认 status='succeeded'（行 619）。runner 的失败分支（asyncio.TimeoutError / ProviderError / parse fail）必须显式调 `cas_complete(status='failed', error_code=..., error_message=...)`，否则会回退为旧 UPDATE 不带 CAS guard，与 zombie cron 双写。设计文档没明确这一点。建议 §6 加一段伪码并强调"runner 所有终态写入必须经 cas_complete"。
- 残留 3（minor）：`tests.md:171-176` P5 测的是 cas_complete(succeeded) vs cas_zombie 的 race，没测 runner 内部 fail 分支 vs cas_zombie 的 race（两条 failed CAS 同时跑）—— 影响有限，可接受。

### B4 GET endpoint 同 project 越权 — 🟢 Resolved

- `00-design.md:530-543` Service 反查代码两层校验：先 `task.user_id != current_user_id → SnapshotTaskNotFoundError` 打码，再 project accessibility。打码统一 ✓
- `tests.md:198-201` T2.5 覆盖"同 project user_Z 拿别人 task_id → 404 + review_data 不泄漏" ✓
- `00-design.md:550` 错误信息打码声明 ✓

### M1 §15 M04 契约锁定 — 🟢 Resolved

- `00-design.md:1111` accept 前置条件第 3 条完整列出 `create_dimension_record` + `get_latest` 签名 + "M13 pilot 2026-04-25 accepted 后状态" + "签名调整必须 M16 同期联动更新" + "M16 setup tests 含 contract test 校验签名稳定" ✓

### M2 SNAPSHOT_ZOMBIE AppError 子类 — 🟢 Resolved

- `00-design.md:1039-1043` `SnapshotZombieError(AppError)` 已补 + http_status=504 + message + `00-design.md:1046` "14 个 ErrorCode 各有对应 AppError 子类（含 SnapshotZombieError——audit M2 修复后不再例外）" ✓

### M3 反悔触发器监测路径 — 🟢 Resolved

- `00-design.md:422-431` 表格列 zombie 率 / 单次成本计算式 + 阈值 + 监测方式（每周 cron + Prometheus counter）+ 指标 owner（M16 owner CY）✓
- `00-design.md:651` activity_log `ai_snapshot.complete` metadata 含 `estimated_cost_usd` ✓
- `00-design.md:660-662` estimated_cost_usd 字段说明（计算来源 + 用途）✓

### M4 zombie 阈值与 cron 频率 — 🟢 Resolved

- `00-design.md:376-379` cron 频率改 5min；阈值改 11min（10min + 1min commit buffer）；用户感知失败延迟 ≤ 16min ✓
- `00-design.md:911-921` §12B 字段 ⑦ "zombie cron 跑频率 ≤ 阈值 / 2"原则归纳进子模板 ✓

### M5 save path mismatch — 🟢 Resolved

- `00-design.md:510` 文字声明 ✓
- `00-design.md:756-759` Service.save 入口 step 2 path 校验在 `with self.db.begin()` **之前**（line 771 才进事务），不会半截事务 ✓
- `00-design.md:1033-1037` SnapshotTaskPathMismatchError + ErrorCode ✓
- `tests.md:73-77` B4 用例覆盖 ✓

### M6 advisory lock 防并发 get-or-create — 🟡 Partial

- `00-design.md:710-734` create_task 内 `pg_advisory_xact_lock` ✓；`_advisory_key` 用 blake2b 8 字节 + signed=True 转 PG bigint ✓
- `tests.md:94-97` I1b "3 个协程同时调"用例存在 ✓
- 残留：I1b 在 SQLAlchemy `session-per-request` 下要真触发并发，必须用**独立 client + 独立 event loop**（asyncio.gather 仅 await，不开新 session）—— `tests.md:96` 仅写 "asyncio.gather"，没明说"3 个 httpx.AsyncClient 并发请求" 或"3 个独立 SessionLocal"。如果 3 个协程共享同一 db session 串行执行，则 advisory lock 用不上，幂等命中也会"假绿"。建议在 I1b 步骤明确 "用 3 个独立 httpx.AsyncClient 实例并发 POST"。
- lock_key blake2b 8 字节 signed=True：64-bit 空间下 hash 碰撞概率 ~2^-32 量级，对 user×project×node 总数 < 1M 场景碰撞期望 < 10^-7，OK；signed 转换符号位无影响（PG bigint 接受负值）。

### M7 §12B vs §12C 字段位次 mapping — 🟡 Partial

- `00-design.md:806-820` mapping 表 7 行齐全，emoji 区分 + "强制纪律" 警告 ✓
- 残留：表中 ⑥ "失败 / 重试策略" §12A 写 "取消机制"——位次错位（§12A ⑥ 和 §12B/C ⑥ 名字不同就是 audit M7 警告的"位次错觉"）。但 fix 已通过强制纪律文字警示读者"不得按位次混抄"，可视为有意保留差异 + 文字补救。可接受为 Partial（不是错，只是表的形式仍可能误读，文字警告依赖读者纪律）。

### M8 ADR-001/002 留痕 — 🟢 Resolved

- `00-design.md:1112` accept 前置条件第 4 条 "ADR-002 §横切影响新增脚注：'M16（AI 快照）：BackgroundTasks fire-and-forget，不走 Queue。决策依据 + 反悔触发器（zombie 率 ≥1% / 单次成本 ≥$0.5）见 M16 §6 BackgroundTasks vs arq 边界'" ✓

### M9 M05 count_by_node baseline-patch — 🟢 Resolved

- `00-design.md:1103-1109` 完整签名 + 双 tenant 过滤 + 接受外部 db session 不开事务 + 不写 activity_log + 索引复用 + 性能验收 < 5ms p95 ✓

### m1 pending → failed 状态机冲突 — 🟢 Resolved

- `00-design.md:322` 已在允许转换表新增 `pending → failed (zombie cron 兜底 pending > 2min)` + 副作用列 写 activity_log + error_code=SNAPSHOT_ZOMBIE ✓
- `00-design.md:378` zombie cron 阈值含 `pending AND created_at < NOW-2min` ✓

### m2 (status, created_at) 复合索引 — 🟢 Resolved

- `00-design.md:222` `Index("ix_ai_snapshot_status_created", "status", "created_at")` 已补，注释 "zombie cron 用（audit m2 修复）" ✓

### m3 G1 activity_log 数学错误 — 🟢 Resolved

- `tests.md:34` 改为 "(N+3) 条：1 start + 1 complete + (N+1) create" 数学正确 ✓

### m4 缺 race / I4 边界精确 — 🟢 Resolved

- `tests.md:109-113` I4 加 freezegun 4:59 / 5:01 / 6:00 边界 ✓
- `tests.md:171-176` P5 zombie cron vs runner race 用例 ✓
- `tests.md:178-182` P6 pending zombie 兜底 ✓

### m5 M15 Alembic 文件命名 — 🟢 Resolved

- `00-design.md:1110` "Alembic 文件 `<rev>_M16_extend_activity_log_action_target.py`，含 upgrade（ALTER TABLE … DROP CONSTRAINT … + ADD CONSTRAINT … 含新枚举）+ downgrade（回旧枚举）；revision 与 M16 实装 PR 同期合并" ✓

### m6 pending 任务 zombie 兜底 — 🟢 Resolved

- `00-design.md:322` 状态机表 + `00-design.md:378` cron 阈值 + `00-design.md:919` §12B 子模板字段 ⑦ 强调 "pending **也**要被 zombie 兜底" ✓

---

## 残留风险清单（仅 🟡 / 🔴）

| 编号 | 严重度 | 残留点 | 建议 |
|------|--------|-------|------|
| B1-r1 | **High** | `00-design.md:843` §12B 字段 ① 子模板仍写 `UniqueConstraint(user,project,node,version_count) # 幂等 DB 强制` —— 与 §3 决策矛盾，未来照抄者会重踩 | 删除该行或改为 "幂等：ORM find + pg_advisory_xact_lock；**不**用 DB UniqueConstraint（partial index 无法用 NOW() 谓词）" |
| B1-r2 | **High** | `tests.md:254` R11-2 测试断言 "DB UniqueConstraint 拒绝" 在 fix 后不可执行 | 改为 "并发 3 协程同 (user, projA, node, vc) → 1 行；不同 project 共存正常" |
| B3-r1 | Medium | `00-design.md:393` Background Task 层缺 `with SessionLocal() as db:` 代码示例；runner 失败分支没明确"必须调 cas_complete(status='failed')" | §6 补一段 runner 伪码示例（含 try/except 三种失败分支均经 cas_complete） |
| B3-r2 | Low | tests.md P5 仅测 succeed vs zombie 的 race，缺 runner-fail vs zombie 双 fail-CAS race | 可后补，不阻 accept |
| M6-r | Medium | `tests.md:96` I1b "3 个协程同时调" 没明确"用 3 个独立 httpx.AsyncClient + 独立 session"，实际可能假绿 | 步骤明确 "3 个独立 client 并发 POST" |
| M7-r | Low | §12 三形态字段位次表 ⑥ §12A "取消机制" vs §12B/C "失败重试" 仍存位次错觉，但已有文字警告 | 可接受现状或拆为 §12A/B/C 各自独立编号 |

---

## 新引入风险

1. **`with self.db.begin()` 与 FastAPI `Depends(get_db)` session 嵌套**（`00-design.md:712`）：FastAPI 默认 `get_db` yield 的 Session 在请求结束才 close，但通常没有外层 `begin`。`Session.begin()` 在已存在事务时会返回 SavepointBegin（SQLAlchemy 2.x），不会冲突，OK。但若项目 `get_db` 实现已在外层 `begin`，则 advisory_lock 释放语义可能延后到外层 commit —— 建议 §11 补一句 "依赖 `get_db` 不开外层事务（与 prism-0420 默认 session 配置一致）"。
2. **DAO 内 `db.commit()`（`00-design.md:615, 633`）**：`cas_zombie_transition` 由 cron job 调用、`cas_complete` 由 runner 调用，两者都自起 SessionLocal，DAO commit OK 不破外层事务。但若 Service 误用（在 with self.db.begin() 内调 cas_complete）会破事务边界。建议 DAO docstring 明确"仅供 runner / cron 使用，禁止 Service 事务内调用"。
3. **BackgroundTasks add_task 在 `with self.db.begin()` 之外**（`00-design.md:732-733`）：commit 后才 add_task，如果 add_task 抛异常（OOM 等），task 行已落库但 runner 没拉起 → 孤儿 pending → 由 zombie cron 在 2min 后兜底。已有 m1+m6 修复覆盖此场景，OK，但建议在 §11 注释加一行"add_task 失败由 pending zombie cron 兜底"显式留痕。
4. **CAS UPDATE 不写 activity_log**：`cas_zombie_transition` / `cas_complete` 在 DAO 内只写 task 表，不写 activity_log。但 §10 表声明 `ai_snapshot.complete / failed` 由 "M16 Service" 写入。Runner 调 cas_complete 后还要单独调 ActivityService.log()，但代码未声明在哪一步、是否在同 session 同事务。建议 §6 runner 伪码同时展示 cas_complete + activity_log 写入顺序（活动日志应**在 cas_complete affected=1 后**写，否则 zombie 抢先时会双写日志）。

---

## 总判断

**需再修 2 项后 accept**：

- **必修（阻塞）**：B1-r1（§12B 子模板矛盾）+ B1-r2（tests.md R11-2 测试已失效）—— 两条都涉及 fix 后留下的"自相矛盾"残留，不是新设计而是清理工作。
- **建议修但不阻**：B3-r1（runner 伪码补）、M6-r（I1b 并发实现说明）、新引入风险 4（cas_complete + activity_log 顺序）。

整体修复质量良好：4 个 Blocker 中 B2/B4 完整修复，B1/B3 主路径修复但留残留；9 个 Major 中 7 项 🟢 / 2 项 🟡；6 个 Minor 全部 🟢。修完上面 2 项必修残留可走 CY 复审。
