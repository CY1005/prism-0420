---
title: M16 三轮 audit 报告
reviewer: opus-reviewer-agent
created: 2026-04-25
target: M16-ai-snapshot/00-design.md (draft)
---

# M16 AI 快照 pilot 三轮对抗 audit

> **审稿立场**：独立、不附和、每条问题必须有文件路径 + 行号。
> **参照基线**：M13 audit 同款风格 + ADR-001/003/004 + M02/M04/M05 已 accepted 的 Service 真实签名 + M17 §12C 7 字段对照。
> **不挑战 CY brainstorming 10 个 Q 的决策本身，只审落地**。

## 总体评价

整体完成度高于 M13 初稿：16 节齐全、§12B 7 字段成形、tests.md 35 用例覆盖面扎实、CY 决策记录完整、Phase 2 迁移成本量化。但**存在 4 处真正的 Blocker 必须先修才能启动 CY 复审**，集中在：

1. **§3 表的 `UniqueConstraint(user, project, node, version_count)` 与 §1/§9 "5 分钟窗口复用 + failed 不复用"语义直接矛盾** —— DB 约束永久强制，"5 分钟" + "排除 failed" 是 ORM 层逻辑，二者实际跑会互相打架，failed 后用户立刻重发会被 DB 拒绝。
2. **§7 `DimensionSnapshotItem.content: str` 与 M04 已登记的 `create_dimension_record(content: dict, ...)` 类型签名不兼容** —— save 阶段无法直接传字符串。
3. **§5 状态转换竞态分析声称 BackgroundTasks worker `SELECT FOR UPDATE`，但 `BackgroundTasks` 跑在 FastAPI 同进程同请求上下文里，已在 response 之后；`with self.db.begin()` 与 `Depends(get_db)` 的 session 生命周期已结束**——claim 与 FastAPI 行为不符。
4. **§10 R10-1 "save 阶段 N 条 dimension_record 串行写 N 条 activity_log" 的事务声明，依赖 M04 `create_dimension_record` 接受外部 db session 的 R-X3 契约，但 §15 accept 前置条件**没有显式列**M04 R-X3 验收**——M13 pilot accept 时已补丁 `create_dimension_record(db, ...)` 签名，但 M16 没有引用此前置历史，留下盲区（一旦 M04 之后回退就崩）。

另有 Major 6 条 / Minor 5 条。tests.md 数学有错（G1 断言）+ 关键场景缺失（save 端点幂等窗口外的 DB 约束行为、不同 status 之间的复用迁移）。

**判定**：**不能直接 accept，需先修 4 个 Blocker + 至少 3 个 Major。** 修后可走 CY 复审。

---

## 第一轮：完整性

### B1（Blocker, 第一轮）：DB UniqueConstraint 与"5min 窗口 + failed 不复用"语义直接矛盾

**位置**：`00-design.md:213-216`（UniqueConstraint 定义）+ `00-design.md:539-554`（find_idempotent 5min 窗口 + status 过滤）+ `00-design.md:96-97`（"5min 复用"声明）+ `00-design.md:619`（端点表"key=(user,project,node,version_count)，5min 窗口"）+ `tests.md:96-98 I5`（失败任务不复用断言）

**问题**：
- §3 SQLAlchemy 模型行 213-216：
  ```python
  UniqueConstraint("user_id","project_id","node_id","version_count", name="uq_ai_snapshot_idem")
  ```
  这是**无条件、永久**的 DB 唯一约束。
- §9 `find_idempotent`（行 536-554）：只查"5 分钟内 + status in (pending,running,succeeded)"，明确排除 `failed/cancelled`。
- 真实运行流：
  1. 用户点生成 → task_A 写入 (u, p, n, vc=5) → AI 报错 → task_A 转 failed
  2. 用户点"重新生成"（Q5 ack A 强调"用户手动重发"）→ Service 调 `find_idempotent` → 因 failed 排除，返回 None → Service 调 `dao.create(...)` → DB 抛 IntegrityError（UniqueConstraint 命中 task_A 那一行）
  3. 用户卡死，必须等 30 天 task_A 清理或者 vc 涨到 6 才能重发
- `tests.md I5` 断言"返回新 task_B"——这条测试**实际会失败**（IntegrityError）。
- `tests.md I4` 同样"5 min 过期后"返回新 task_B 也会失败（约束没时间字段）。

**修复方向**（择一）：
1. 把 UniqueConstraint 改为**部分索引**（partial unique index），仅约束活跃任务行：
   ```python
   Index(
     "uq_ai_snapshot_idem_active",
     "user_id", "project_id", "node_id", "version_count",
     unique=True,
     postgresql_where=text("status IN ('pending','running','succeeded') AND created_at > NOW() - INTERVAL '5 minutes'")
   )
   ```
   注：PG partial index 支持但 `NOW()` 不能进 predicate（不可变要求）。需把"5min 窗口"用 `expires_idem_at` 字段+独立索引另写 —— 这是独立设计任务，不是一行改动。
2. **取消 DB UniqueConstraint，幂等只靠 ORM 层 `find_idempotent` + 同事务 SELECT FOR UPDATE 防并发** —— 简单但放弃 DB 强制保险，性能上接受连点最多多跑 1-2 次（get-or-create 竞态）。
3. UniqueConstraint 加 `idem_token` 列（每个 task 有 token，复用命中时拷贝旧 token），约束改为 (user, project, node, version_count, idem_token) —— 复杂度大幅上升。

**关联**：违反 README §设计原则"DB 约束必须与业务规则一致"；CY Q6 ack Y 决策本身没问题，落地实现路径错。

---

### B2（Blocker, 第一轮）：§7 `DimensionSnapshotItem.content: str` 与 M04 真实签名 `content: dict` 不兼容

**位置**：`00-design.md:449-453`（DimensionSnapshotItem 定义 content: str）+ `00-design.md:455-459`（SnapshotReviewData.dimensions: list[DimensionSnapshotItem]）+ `M04-feature-archive/00-design.md:265`（`create_dimension_record(... content: dict, ...)`）

**问题**：
- M04 §6 对外契约（M13 pilot 已补丁 accepted 2026-04-25）：
  ```
  create_dimension_record(db, *, project_id, node_id, dimension_type_key, content: dict, user_id, extra_activity_metadata) -> DimensionRecord
  ```
  `content` 类型是 `dict`（dimension_records 表 `content` 列是 JSONB，存结构化字段如 `{"text": "...", "fields": {...}}`）。
- M16 §7 `DimensionSnapshotItem.content: str`（自由文本）。save 阶段（行 488-490 的篡改防御代码描述）"Service 层从 task.review_data 读取实际 content"，传给 M04 的 content 是 str。
- 直接传 str 给期望 dict 的 M04，要么 Pydantic 校验失败（dict 类型），要么 M04 自身 JSONB 写入逻辑炸（json.dumps(str) ≠ {"text": str}，前端按字段读会跨型）。
- `tests.md G1` 断言"dimension_records 新增 N+1 条"完全没有验证 content 形态——这条测试在 mock 层会"绿"，Phase 2 实装会爆。

**修复方向**：
1. `DimensionSnapshotItem.content` 改为 `dict[str, Any]`，AI prompt 模板（§6 Prompt Template 层 `ai_snapshot_prompts.py`）必须约束 AI 输出 `content` 为 `{"text": "...", ...}` 形态 dict，§13 增 `SNAPSHOT_PARSE_FAILED` 时识别 content 不是 dict。
2. 或：M04 `create_dimension_record` 加 `content_text: str | None = None` 重载入参，由 M04 自己包成 dict 落 JSONB —— 改 M04 契约更重，需走 baseline-patch 流程。
3. tests.md G1 / G2 / G3 全部加 "dimension_records.content == {...} 结构化校验"。

**关联**：违反 ADR-003 规则 1（上游 Service 接口契约必须严格遵守）；违反 R-X3（跨模块调用不得擅自变换 Service 入参类型）。

---

### B3（Blocker, 第一轮）：§5 状态机竞态分析的 `SELECT FOR UPDATE` 与 BackgroundTasks 实际生命周期矛盾

**位置**：`00-design.md:362-363`（BackgroundTasks worker 先 SELECT FOR UPDATE → 校验 status='pending' → UPDATE）+ `00-design.md:382`（Background Task 层 `run_snapshot_task(task_id, project_id, user_id)`）+ `00-design.md:653-654`（service.create_task 内 `self.background_tasks.add_task(run_snapshot_task, task_id=task.id)`）

**问题**：
- FastAPI `BackgroundTasks` 行为：在 response **发回客户端之后**、同 worker 进程的 asyncio 事件循环里串行执行。请求级 `Depends(get_db)` session 在 response 之前就 `db.close()` 了——background task 启动时**没有可用 session**，必须在 `run_snapshot_task` 内自己 `with SessionLocal() as db:` 起新 session。
- §5 行 362 声称 "BackgroundTasks worker 先 `SELECT FOR UPDATE` task → 校验 status==pending → UPDATE status=running"——但全文（§6 + §11 代码片段）没有体现 background runner 内的 session 创建逻辑、事务控制、SELECT FOR UPDATE 的 SQLAlchemy 写法。这一句是**承诺没落地**。
- 更严重：BackgroundTasks 跑在**接收请求的同一 worker 进程**，跨进程并发不存在——对 cancel 端点的"另一并发请求转 cancelled"场景，无须 `SELECT FOR UPDATE`（同一进程 asyncio 单线程串行）。但 §5 把它写得像跨进程竞态防御，给读者错误心智模型。
- 真正的竞态在 **zombie cron** vs **正常 BackgroundTasks 完成**：cron 在另一进程跑 `list_zombie + UPDATE status=failed` 时，正在跑的 background task 可能同时 `UPDATE status=succeeded` —— 这才是需要 SELECT FOR UPDATE 的地方，但 §9 `list_zombie` 实现（行 556-568）用 `.all()` 列读不锁。

**修复方向**：
1. §5 行 362 改为："BackgroundTasks 跑在同 worker 进程，无跨请求竞态。**真正竞态是 zombie cron（另一进程）vs background runner**——runner 完成时 `UPDATE ... WHERE id=? AND status='running'` 加 status 条件，cron 同样 `UPDATE ... WHERE id=? AND status='running' AND created_at < NOW-15min`，CAS 风格更新自然防双写。"
2. §6 Background Task 层补一段示例代码（含 `with SessionLocal() as db: with db.begin(): ...`）。
3. §9 `list_zombie` 改成 cron 用单条 `UPDATE ... RETURNING id` 直接 CAS 转换，避免读-改-写两步竞态。
4. tests.md 新增一条 P5"zombie cron 与正常完成 race"——并发跑 cron + runner，断言不出现"任务先 succeeded 又被改 failed"或反之。

**关联**：违反 R-X3（跨模块/跨进程 session 共享语义未声明）；CY Q5 ack A "不重试"决策依赖 zombie 兜底正确性，竞态没防住等于 zombie 可能误杀正常完成的任务。

---

### M1（Major, 第一轮）：§15 accept 前置条件没有列 M04 `create_dimension_record(db, content)` 的 R-X3 契约校验

**位置**：`00-design.md:927-937`（accept 前置条件）+ `00-design.md:46`（声明"复用 M13 pilot 已补丁的 create_dimension_record"）+ `M13 audit-report B3 / B5`（M04/M15 R-X3 + 前置补丁先决）

**问题**：
- §15 行 927-937 列了 3 项前置：M05 count_by_node / M15 CHECK 枚举 / README §12 表更新。
- 行 933-936 声称"M02 / M03 / M04 无需 baseline-patch"，理由是"M04 复用 M13 pilot 已补丁的 create_dimension_record + get_latest"。
- 但 M13 pilot accept 时新加的 M04 方法签名（dict content）正是 B2 撞到的坑——M16 复用前没显式校验该签名能满足 M16 需求。
- "M13 已补丁"是**历史快照**，不是契约保证；M04 owner 后续可能再改。M16 §15 应该明确锁定"依赖 M04 `create_dimension_record(db: Session, *, project_id, node_id, dimension_type_key, content: dict, user_id, extra_activity_metadata) -> DimensionRecord` 签名不变；如该签名调整，M16 同期联动更新"。

**修复方向**：§15 accept 前置条件第 4 条增："M04 `create_dimension_record` + `get_latest` 当前签名作为 M16 依赖契约锁定（M13 pilot 2026-04-25 accepted 后状态）；M16 setup tests 含 contract test 校验签名稳定。"

---

### M2（Major, 第一轮）：§13 R13-1 自洽性—— `SNAPSHOT_ZOMBIE` 没 AppError 子类的理由站不住

**位置**：`00-design.md:872`（R13-1 合规说明 "SNAPSHOT_ZOMBIE 不需独立 Exception——是 cron 写入 task.error_code 的纯标记值"）+ `00-design.md:798`（ErrorCode 列表含 SNAPSHOT_ZOMBIE）

**问题**：
- 用户从前端调 `GET /snapshot-tasks/{id}` 拿到 `status=failed + error_code=SNAPSHOT_ZOMBIE`，前端要根据 error_code 决定 UI 文案（"任务异常退出，请重试"vs"AI 服务故障"vs"配额超限"）。
- ErrorCode 是面向**用户感知**的契约，不是仅 HTTP 抛出路径。R13-1 的"每个 ErrorCode 必须有 AppError 子类映射"是为了 wrap 一致性——SNAPSHOT_ZOMBIE 虽然不在 HTTP 抛出链，但若未来某个 endpoint 需要判定"这个 task 是 zombie 死的"，没有 Exception 类型只能字符串比较，反模式。
- 13 个 ErrorCode 里只有这一个例外，破坏 R13-1 字面合规。

**修复方向**：补 `SnapshotZombieError(AppError)` 子类（http_status=504 或 500，message="任务执行异常退出"），cron 既写 `error_code` 又持有该 Exception class（即使不实际 raise）。或：在 §13 R13-1 段把"例外条款"明确写入并解释取舍。

---

### m1（Minor, 第一轮）：§4 状态机表 "pending → failed 不合理只有 running 才会失败"与 §11 异常路径有边界争议

**位置**：`00-design.md:331`（"pending → failed：任务还没起跑就失败=业务上不合理"）+ `00-design.md:632-640`（create_task 校验 < 3 抛 SnapshotInsufficientVersionsError）

**问题**：行 331 禁止 pending → failed。但 §11 行 632-640 的 create_task 流：先 `node_service.get_by_id` → `count_by_node` → `< 3 raise`，**任务还没创建**就抛错（OK）。然而如果 BackgroundTasks 启动失败（FastAPI 进程内 `add_task` 异常 / OOM）—— task 已写 pending 但 runner 没拉起，会卡 pending 等 zombie 兜底。这种情况"业务上"算 failed，但状态机禁止——结果是用户看到 zombie 转 failed 慢 15min。

**修复方向**：要么允许"pending → failed（zombie 兜底也覆盖 pending 长时间未起跑）"，把 zombie cron 阈值改成 `(status='running' AND created_at < NOW-15min) OR (status='pending' AND created_at < NOW-2min)`；要么显式接受这种 ≤15min 延迟并写到 §5 trade-off 列表。

---

### m2（Minor, 第一轮）：§3 `expires_at` 索引存在但 `created_at` 字段未单独索引——清理 cron 扫表性能

**位置**：`00-design.md:223`（`Index("ix_ai_snapshot_expires", "expires_at")`）+ `00-design.md:564-568`（list_zombie 用 `created_at < NOW-15min` 查询）

**问题**：list_zombie 用 `created_at` 而非 `expires_at`（pending/running 任务 expires_at=NULL，行 756 明说不设）。索引 `ix_ai_snapshot_expires` 在 zombie cron 用不上；`created_at` 来自 TimestampMixin 通常无独立索引。zombie cron 全表扫，task 表大时性能炸。

**修复方向**：补一条复合索引 `Index("ix_ai_snapshot_status_created","status","created_at")`，覆盖 zombie cron 与 §9 line 561-565 查询。

---

## 第二轮：边界 + 后台 fire-and-forget 特化

### B4（Blocker, 第二轮）：独立 GET endpoint `/snapshot-tasks/{task_id}` 的访问控制反查在用户被踢出 project 后存在打码不一致

**位置**：`00-design.md:507-510`（独立 GET 反查 → "project 查不到 → 404 而非 403"）+ `00-design.md:144`（M02 `get_by_id_for_user` 真实签名）+ `M02-project/00-design.md:540`

**问题**：
- 反查链路：拿 task → task.project_id → `project_service.get_by_id_for_user(project_id, user_id)` 检查用户 ≥viewer。
- 场景：user_X 创建 task_X 跑成 succeeded → user_X 被 project owner 移除 member → user_X 拉自己浏览器历史的 poll URL 调 GET。
- 按 §8 描述，project 查不到（user_X 不再是 member）→ 返回 404"任务不存在或无权限"。OK，单层防御正确。
- **但**：user_X 的同事 user_Z（仍是 project member）拿到 task_X 的 task_id（截屏 / 链接复制粉到群里）调 GET：
  - user_Z 在 project 里 ≥viewer，`get_by_id_for_user` 返回 Project，**不抛**。
  - §8 行 509 提到"task.user_id 校验：默认仅 task creator 能轮询"——但 §9 DAO `get_by_id` 对 GET 端点不传 user_id（行 528-534），Service 层做反查；**Service 层反查的代码示例（行 500）只校验 project accessibility，没校验 task.user_id == current_user.id**。
- 结果：user_Z 能正常拿到 task_X.review_data —— 含 user_X 私下生成的 AI 输出（可能含未公开的 dimension 内容草稿、AI provider 元信息等）。
- §8 行 509 说"如果未来需求允许同 project editor 互看，把 user_id 校验放宽"——意思**当前默认**应该是"仅 creator"，但代码示例和 DAO 实现里**没有**这层校验。文字承诺与代码契约脱节。

**修复方向**：
1. §8 Service 反查代码补一行 `if task.user_id != current_user.id: raise SnapshotTaskNotFoundError()`（默认仅 creator 可见）。或显式选另一种语义"同 project ≥viewer 都可见"并文字明说。
2. tests.md T2 现在测的是"跨 project user_Y"——补 T2.5"同 project user_Z 拿别人 task_id"应该 404。
3. §10 activity_log 加 `ai_snapshot.read`（敏感读审计）—— 可选，但对"AI 输出含未发布草稿"的场景值得。

**关联**：违反 ADR-004 §核心 5 项第 3 点（细粒度授权放 Service 层）；与 M13 audit B2 的 P2 路径声明类似的"§8 文字与代码契约脱节"反模式。

---

### M3（Major, 第二轮）：BackgroundTasks vs arq 反悔触发器只给"zombie 率 > 1%"和"单次成本 > $0.5"两个阈值——监测手段没说

**位置**：`00-design.md:411`（反悔触发器定义）

**问题**：
- 反悔触发器要可操作，必须配套：① 怎么测 zombie 率（cron 每天打日志 + Grafana dashboard 还是手工统计）② 单次 AI 成本谁结算（M02 还是 M16 自记 metadata.cost）③ 触发后谁负责拉评估会。
- 行 411 只一句"如果 Phase 2 实测发现 zombie task 发生率 > 1%，或 AI provider 单次调用成本上升到 $0.5+，则迁移到 arq"。指标无 owner 无监测路径，等于没有触发器。
- M16 §10 activity_log metadata 也没含 cost 字段（行 585 metadata 只有 generation_time_ms）。

**修复方向**：
- §10 activity_log `ai_snapshot.complete` metadata 增 `estimated_cost_usd: float`（由 AI provider 调用层填，参 ADR-001 §4.1）。
- §6 `BackgroundTasks vs arq` 段补"反悔触发器的监测路径"：① zombie 率 = `count(error_code=SNAPSHOT_ZOMBIE)` / `count(任务总数)` ≥1%（每周 cron 算一次进 metrics 表）；② 单次成本 = `avg(metadata.estimated_cost_usd)` ≥ $0.5。两指标超阈触发主对话评估。

---

### M4（Major, 第二轮）：zombie 阈值 15min vs 服务器硬超时 10min 的 buffer 论证不充分

**位置**：`00-design.md:368`（cron 每小时扫 `created_at < NOW - 15min`）+ `00-design.md:761`（"zombie 阈值 = 服务器硬超时 + buffer，防 runner 已正常返回但 commit 慢"）

**问题**：
- 服务器硬超时 600s = 10min（ADR-001 §5.3 / `00-design.md:67`）。
- zombie 阈值 15min = 10min + 5min buffer。
- "5min buffer 防 commit 慢"——没具体场景。FastAPI BackgroundTasks 单 task commit 通常 < 1s（写 status='succeeded' + activity_log）；5 min commit 要 DB 极度堵塞。
- **真正风险点**：cron **每小时**扫一次（行 368）。当一个 task 在 14:00 启动 → 14:10 timeout → BackgroundTasks runner 在 timeout handler 内更新 status=failed 时崩溃 → task 卡 running。下一次 cron 14:30 跑：14:30 - 14:00 = 30min ≥ 15min → 转 failed，OK。
- 但若 task 在 14:55 启动 → 14:59 cron 跑（task 才 4min，跳过）→ 15:05 timeout → handler 崩溃 → 下次 cron 15:59 才跑。从 task 异常到用户拿到 failed 状态 ≈ **1 小时**——前端"温柔放手"30 次轮询（5s × 30 = 2.5min）早就放手了，用户回来调 GET 还是 running，体验糟。
- §12 行 760 "未来后台模块照抄要点：必须有 zombie 兜底"——但没说兜底频率怎么选。

**修复方向**：
1. cron 频率从每小时改为每 5min 一次（zombie 检测延迟从 ≤1h 降到 ≤5min）。
2. 或保留 1h 频率但 zombie 阈值降到 11min（10min + 1min buffer），让 cron 即使 1h 跑一次，只要 task 崩了 11min+ 就会被下一次 cron 抓到。
3. §12 字段 ⑦ 子模板加一句"zombie cron 跑频率 ≤ 阈值 / 2，否则用户感知失败延迟过长"。

---

### M5（Major, 第二轮）：save 篡改防御只防"前端改 content 文本"，没防"前端用别人的 task_id"

**位置**：`00-design.md:476-478`（SnapshotSaveRequest 含 task_id + selected_dimension_keys）+ `00-design.md:487-490`（篡改防御段）+ `00-design.md:502`（save Service 校验 task 属于当前 user）

**问题**：
- 行 487-490 防御逻辑：前端不传 content；Service 从 task.review_data 读 content。OK 防"改文本"。
- 但 SnapshotSaveRequest.task_id 完全由前端传——save endpoint 路径是 `POST /api/projects/{pid}/nodes/{nid}/snapshot/save`（含 pid/nid）+ body 含 task_id，**path pid/nid 与 body task_id 是否一致 没校验**。
- 攻击场景：user_X 在 project_A 的 node_A 上有 task_X (vc=5)；user_X 也在 project_A 的 node_B 上点 save，body 故意填 task_X.id，path 填 node_B → Service 取 task_X 的 review_data → 走 M04 `create_dimension_record(node_id=node_B, content=...)` 把 task_X 的内容**写到 node_B 上**。
- 行 502 校验 task.user_id == current_user → OK，user_X 自己的 task 自己写得到。但 task 与 path node_id/project_id 的一致性没校验。

**修复方向**：
- §7 SnapshotSaveRequest 完全删除 task_id（用 path 拿 node_id 找最新 succeeded task），或：
- §8 / §11 Service.save 入口加 `assert task.project_id == path_project_id and task.node_id == path_node_id`，否则 422 SNAPSHOT_TASK_PATH_MISMATCH（新错误码）。
- tests.md "save 防篡改" 段新增 1 条："body 的 task_id 是别 node 的 task → 422"。

---

### M6（Major, 第二轮）：AC1 兜底（version_count<3）放在 Service 创建任务前 OK，但幂等命中复用一个 vc=旧值的 task 后语义有歧义

**位置**：`00-design.md:631-643`（create_task：先校验 vc>=3，再 find_idempotent，再 create）

**问题**：
- 步骤是"校验 → 幂等查询 → 新建"。如果 5min 内已有 task_A (vc=5, status=running)，用户再点：
  1. 校验 vc=5（M05 现在 count_by_node 还是 5）→ pass
  2. find_idempotent → 命中 task_A → 返回 task_A
  - OK，幂等好用。
- 但若 5min 内已有 task_A (vc=5, succeeded)，用户在 M05 timeline 又添了 1 条 → vc=6 → 用户点 generate：
  1. 校验 vc=6 → pass
  2. find_idempotent (vc=6) → miss
  3. 新建 task_B (vc=6)
  - OK。
- **问题场景**：若 vc=5 时连续提交，第 1 个请求已经走到 dao.create 但还没 commit，第 2 个请求走 find_idempotent **看不到未提交的 task_A** → 也走 create → DB UniqueConstraint 拒绝（如果 B1 修后还有 unique）→ 第 2 个请求抛 IntegrityError 给用户 500。
- §11 没声明用 `SELECT FOR UPDATE` 或 advisory lock 解决并发 get-or-create。tests.md I1（5min 内连点 3 次）实际是串行的，捕捉不到这个并发坑。

**修复方向**：
- create_task 用 PG `INSERT ... ON CONFLICT DO NOTHING RETURNING ...`（取决于 B1 怎么改）+ 失败后 SELECT 已存在的 task 返回。
- 或：Service 入口对 `(user, project, node)` 加 advisory lock（pg_advisory_xact_lock）。
- tests.md I1 升级"3 个并发协程同时调 generate" → 断言只跑 1 task。

---

### m3（Minor, 第二轮）：tests.md G1 数学错误—— activity_log 行数与 N+1 dimension_records 不匹配

**位置**：`tests.md:33`（断言"activity_log 新增 4 条：1 ai_snapshot.start + 1 ai_snapshot.complete + (N+1) create"）

**问题**：1 + 1 + (N+1) = N+3，不等于 4。如果 N+1=2（只 save 1 个维度），那是 1+1+2=4 这条断言才对——但这是特例数。G1 步骤 6"全部 keys"（行 28），如果当前 node 有 N 个维度，save 全 + summary = N+1 dim_records → activity_log = 2 + (N+1) = N+3 条。

**修复方向**：行 33 改为"activity_log 新增 (N+3) 条：1 start + 1 complete + (N+1) create"或写明 N 的具体值。

---

### m4（Minor, 第二轮）：tests.md 缺关键 race 场景

**位置**：`tests.md` P 段（行 127-149）

**问题**：覆盖了"BackgroundTasks 起跑后断开"和"进程崩溃 zombie 模拟"，但缺：
- zombie cron 与正常 BackgroundTasks 完成的 race（B3 提到的）
- save 端点在 task 状态从 succeeded 转回（不可能但状态机预防）的反测
- find_idempotent 的"5min 边界值前后 1 秒"测试（freezegun 精确控制）—— I4 只测 6min 后

**修复方向**：增 P5 / P6；I4 加 5min 边界精确测试（4:59 / 5:01）。

---

## 第三轮：§12B 子模板可复用性 + 跨模块对照

### M7（Major, 第三轮）：§12B 7 字段与 §12C 7 字段在"任务表 schema"字段名不对等——未来照抄者会困惑

**位置**：`00-design.md:670-688`（§12B 字段 ① 任务表 schema）+ `M17-ai-import/00-design.md:599-642`（§12C TaskPayload 基类 + ImportExtractPayload 等）

**问题**：
- §12B 字段 ① "任务表 schema"——M16 选了"任务表 schema"作为字段语义。
- §12C 字段 ① "TaskPayload schema"——M17 选了"Queue payload schema"。
- 同样是"持久化的任务描述",一个是 SQLAlchemy 模型，一个是 Pydantic Queue payload。**两者本质不同**：M16 任务表是用户可查的状态载体；M17 TaskPayload 是 Queue 消费者的入参。
- 行 664 自认"§12A/B/C 字段语义不通用，粒度对等"。这个"粒度对等"的说法很弱——粒度对等意味着字段数都是 7，但概念结构完全不同。**未来某个新场景**（比如 cron 触发的非用户驱动后台任务）想找子模板照抄，看到"§12B 字段 ① 任务表 schema"会以为是"持久化任务，照抄 7 字段"，结果发现字段 ⑥"失败/重试"M16 选了"不重试"，M17 §12C 选了"3 次指数退避"——同字段位次不同语义。

**修复方向**：
1. §12 开篇加一张明确**字段位次到字段名 mapping** 三列表：
   ```
   位次 | §12A 流式 | §12B 后台 | §12C Queue
   ①   | 端点路径 | 任务表 schema | TaskPayload schema
   ②   | event 类型 | 状态机 | Queue 任务清单
   ...
   ```
2. 或：明确放弃"位次对等"，把 §12B / §12C 各自独立编号（B-1...B-7 / C-1...C-7），消除"位次错觉"。

---

### M8（Major, 第三轮）：M16 选 BackgroundTasks 而非 arq 的决策没在 ADR-001 / ADR-002 留痕

**位置**：`00-design.md:973`（§关联参考 列 ADR-002 "M16 不覆盖"）+ `ADR-002-queue-consumer-tenant-permission.md`（无 M16 提及）

**问题**：
- 行 973 自认"ADR-002 §横切影响：M16 不覆盖——M16 不走 Queue，本 ADR 不适用；本期不扩 ADR-002"。
- 但 ADR-002 §横切影响是**所有异步模块的范式索引**——M16 作为第 4 个 pilot，特意选了"不走 Queue"路径，这本身是值得记录的决策（其他后台任务想抄 M16 时需要知道"M16 评估过后选 BackgroundTasks 不选 arq"的理由 + 反悔触发器）。
- M13 audit B5 类似处理过"ADR-002 L116 由 M13 结论替换"。M16 应同样在 ADR-001（§5.3 TASK_TIMEOUTS 已含 ai_snapshot=600s）或 ADR-002 留一条**M16 的横切决策脚注**：M16 = 后台 fire-and-forget 不持久化，不归 ADR-002 覆盖；选择理由 + 反悔触发器见 M16 §6。

**修复方向**：
- §15 accept 前置条件第 4 条："ADR-002 §横切影响新增脚注：'M16（AI 快照）：BackgroundTasks fire-and-forget，**不**走 Queue。决策依据 + 反悔触发器见 M16 §6 BackgroundTasks vs arq 边界。'"
- 或：ADR-001 §5.3 `TASK_TIMEOUTS` 表附近加注"ai_snapshot 走 BackgroundTasks 非 arq"。

---

### M9（Major, 第三轮）：§15 M05 baseline-patch 描述只一句"追加 count_by_node"——M05 owner 无法直接补

**位置**：`00-design.md:929`（M05 baseline-patch 行）+ `00-design.md:138-140`（M05 依赖契约：count_by_node 新签名）

**问题**：
- 行 929："**M05 baseline-patch**：§6 对外契约追加 `count_by_node(db, node_id, project_id) -> int` 方法（M16 pilot 基线补丁）"——只 1 句。
- 对照 M13 pilot 在 M04 加 `create_dimension_record` / `get_latest` 时给了完整签名 + activity_log 行为 + 双 tenant 过滤约束（M04 §6 行 265-266）。
- M05 owner 收到这条补丁需要知道：
  - 是否写 activity_log？（不写——纯读）
  - 是否双 tenant 过滤？（必须，project_id + node_id）
  - 是否接受外部 db session？（必须，R-X3）
  - 性能：是否对超大 version_records 表加索引（M05 现有 (node_id, created_at) 索引应该够，但 M16 应确认）

**修复方向**：行 929 展开为：
```
M05.VersionService.count_by_node(db: Session, node_id: UUID, project_id: UUID) -> int
- 双 tenant 过滤（WHERE project_id = ? AND node_id = ?）
- 接受外部 db session（R-X3）；不开事务；不写 activity_log
- 复用现有 ix_version_records_node_created 索引（M05 §3 表索引）；count(*) 性能验收 < 5ms p95（typical node ≤100 versions）
- 实现位置 M05 §6 对外契约段，accept 前置必须落地
```

---

### m5（Minor, 第三轮）：§15 M15 CHECK 枚举扩 3+1 描述未指定 Alembic 迁移文件命名

**位置**：`00-design.md:930`（M15 Alembic 迁移行）+ `M13 audit R1-06`（M13 也踩同样坑）

**问题**：
- 行 930："**M15 Alembic 迁移**：activity_log CHECK 枚举扩 `ai_snapshot.start` / `ai_snapshot.complete` / `ai_snapshot.failed` 3 个 action_type + `ai_snapshot_task` 1 个 target_type"。
- 没有 migration 文件命名规范（如 `alembic/versions/2026_04_25_M16_extend_activity_log_check.py`）+ revision 编号 + downgrade 内容。
- M13 audit R1-06 已经提过类似问题。M16 重蹈覆辙。

**修复方向**：行 930 后补一行 "Alembic 文件命名 `<rev>_M16_extend_activity_log_action_target.py`，含 upgrade（ALTER TABLE activity_log DROP CONSTRAINT ck_... + ADD CONSTRAINT ... 包含新枚举）+ downgrade（回滚到旧枚举）；revision 与 M16 实装 PR 同期合并"。

---

### m6（Minor, 第三轮）：§12 §12B 字段 ⑦ "expires_at 设值时机"对 pending 状态 zombie 兜底有时间窗口风险

**位置**：`00-design.md:756`（"pending/running 任务不设 expires_at"）+ `00-design.md:368`（zombie cron 阈值 15min）

**问题**：
- pending 任务 expires_at = NULL → 永远不被清理 cron 扫到。
- 如果 BackgroundTasks 因为 FastAPI 进程内 add_task 失败（罕见但 OOM 时会发生）—— task 永远 pending，永远不进 zombie cron（zombie cron 只扫 status='running'，行 564）。
- 结果：表里堆积"卡 pending"的孤儿，永远不清理。

**修复方向**：
- zombie cron 改成扫 `(status='running' AND created_at < NOW-15min) OR (status='pending' AND created_at < NOW-2min)`（同 m1）。
- 或：清理 cron 加一条"`status='pending' AND created_at < NOW-1h` 直接物理删（兜底）"。
- §12B 字段 ⑦ 文字补"pending 也要有 zombie 兜底，不能只看 running"。

---

## 总结表

| 编号 | 轮 | 级别 | 标题 | 位置 |
|------|----|------|------|------|
| B1 | 1 | Blocker | DB UniqueConstraint 与 5min/failed 复用语义矛盾 | §3 行 213 / §9 行 539 |
| B2 | 1 | Blocker | DimensionSnapshotItem.content: str 与 M04 dict 签名不兼容 | §7 行 449 |
| B3 | 1 | Blocker | §5 BackgroundTasks SELECT FOR UPDATE 与 FastAPI 行为不符 | §5 行 362 / §6 行 382 |
| B4 | 2 | Blocker | 独立 GET endpoint 同 project 越权（同事 Z 拿 task_id 能读）| §8 行 500-510 |
| M1 | 1 | Major | §15 没显式锁定 M04 create_dimension_record 签名契约 | §15 行 933 |
| M2 | 1 | Major | SNAPSHOT_ZOMBIE 没 AppError 子类破坏 R13-1 字面合规 | §13 行 798 / 872 |
| M3 | 2 | Major | BackgroundTasks vs arq 反悔触发器无监测路径 | §6 行 411 |
| M4 | 2 | Major | zombie 阈值 15min + cron 1h 频率组合下用户感知延迟 ≤1h | §5 行 368 / §12 行 761 |
| M5 | 2 | Major | save 篡改防御未校验 task vs path 一致性（跨 node 攻击）| §7 行 476 / §11 行 502 |
| M6 | 2 | Major | create_task 并发 get-or-create 没 advisory lock | §11 行 631 |
| M7 | 3 | Major | §12B 与 §12C 7 字段位次语义不对等，未来照抄者会困惑 | §12 行 664 |
| M8 | 3 | Major | M16 选 BackgroundTasks 决策没在 ADR-001/002 留痕 | §15 行 927 / §关联参考 |
| M9 | 3 | Major | M05 count_by_node baseline-patch 描述太简略 | §15 行 929 |
| m1 | 1 | Minor | 状态机禁止 pending → failed 与 add_task 失败场景冲突 | §4 行 331 |
| m2 | 1 | Minor | 缺 (status, created_at) 复合索引 | §3 行 220-223 |
| m3 | 2 | Minor | tests.md G1 activity_log 数学错误（4 ≠ N+3）| tests.md 行 33 |
| m4 | 2 | Minor | 缺 zombie/save race 测试 + I4 边界精确测试 | tests.md P/I 段 |
| m5 | 3 | Minor | M15 Alembic 迁移文件命名 / downgrade 未声明 | §15 行 930 |
| m6 | 3 | Minor | pending 任务无 zombie 兜底 + expires_at NULL | §12 行 756 |

**统计**：Blocker 4 / Major 9 / Minor 6

## 总判断

**不能 accept。** 4 个 Blocker（B1/B2/B3/B4）任意 1 个落到 Phase 2 都是炸——B1 让幂等 + 失败重发互锁、B2 让 save 直接报错、B3 让竞态防御只是字面承诺、B4 让 review_data 跨同 project 用户泄漏。**主对话必须先修 4 个 Blocker + 至少 M1/M5/M7（与契约稳定性 + 安全性 + 子模板可复用性强相关）后再启动 CY 复审**。

修后剩余 Major / Minor 可作为 verify agent 二轮的检查项，不阻 accept。
