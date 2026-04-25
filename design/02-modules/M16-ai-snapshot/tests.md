---
title: M16 AI 快照 - 测试场景
module_id: M16
prism_ref: F16
created: 2026-04-25
last_reviewed_at: null
---

# M16 测试场景

> **配套设计**：[`00-design.md`](./00-design.md)
>
> **形态覆盖**：🪷 后台 fire-and-forget（§12B 子模板）。重点测试：BackgroundTasks 生命周期、轮询体验、zombie 兜底、不重试语义、幂等防连点。

---

## G. Golden Path（核心闭环）

### G1: 标准生成 + 全量 save

- **前置**：editor 用户；project + node 已建；该 node 有 5 条 version_records；project 已配 mock AI provider
- **步骤**：
  1. POST `/api/projects/{pid}/nodes/{nid}/snapshot/generate`
  2. 立即拿 202 + `task_id` + `status=pending` + `is_idempotent_hit=false` + `poll_url`
  3. 轮询 GET `/api/snapshot-tasks/{task_id}` 每 1s 一次（测试加速；线上 3-5s）
  4. 拿到 `status=running` → 继续轮询
  5. 拿到 `status=succeeded` + `review_data.summary` 非空 + `review_data.dimensions` 长度 = 当前维度数
  6. POST `/snapshot/save`：`save_summary=true` + `selected_dimension_keys=<全部 keys>`
- **断言**：
  - generate 响应耗时 < 200ms（fire-and-forget 不阻塞）
  - succeeded task.completed_at 非空，expires_at = completed_at + 30d
  - save 后 dimension_records 表新增 N+1 条（含 1 条 snapshot_summary）；旧 dimension_records **保留不更新**（追加+最新赢）
  - **dimension_records.content 形态校验**（audit B2 修复）：snapshot_summary 那一条 `content == {"summary": "..."}`；其他 N 条各自 `content` 为 dict 至少含 `text` 或对应维度的结构化字段
  - activity_log 新增 (N+3) 条：1 ai_snapshot.start + 1 ai_snapshot.complete + (N+1) create dimension_record（audit m3 修复——原"4 条"数学错）
  - ai_snapshot.complete metadata 含 `estimated_cost_usd: float`（audit M3 修复）
- **覆盖 AC**：F16 AC1 / AC2 / AC3

### G2: 仅 save 一句话概要

- 步骤同 G1，但 step 6 改 `save_summary=true` + `selected_dimension_keys=[]`
- **断言**：dimension_records 仅新增 1 条 snapshot_summary；返回 `summary_saved=true` + `saved_count=1`

### G3: 选择性 save（部分维度）

- 步骤同 G1，step 6：`save_summary=false` + `selected_dimension_keys=["feature_description", "tech_implementation"]`
- **断言**：仅 2 条 dimension_records 新建，summary 没保存

---

## B. 边界（AC1 版本数 + content size）

### B1: 版本数 < 3 拒绝

| 版本数 | generate 响应 |
|--------|--------------|
| 0 | 422 SNAPSHOT_INSUFFICIENT_VERSIONS（actual=0, required=3）|
| 1 | 422（actual=1）|
| 2 | 422（actual=2）|
| 3 | 202 通过（边界放行）|
| 4 | 202 通过 |

### B2: AI 输出 content 极端长度

- **B2a**：mock provider 返回 `summary=""`（空字符串）→ task succeeded（不在服务端拒绝），save 时 dimension_records.content 写入空 summary（业务上可接受，由 UI 提示用户重新生成）
- **B2b**：mock provider 返回 `summary` 长度 200KB → task succeeded，review_data JSONB TOAST 压缩；save 时正常落库（dimension_records.content 也是 JSONB）
- **B2c**：mock provider 返回**非 JSON** 文本 → task **failed** + `error_code=SNAPSHOT_PARSE_FAILED`

### B3: dimensions 列表为空 / 异常

- **B3a**：node 当前没有任何 dimension_records → AI prompt context 中 dim_keys=[] → review_data.dimensions=[] → save 时 `selected_dimension_keys` 必须为空，否则 422
- **B3b**：AI 输出 dimensions 含 review_data 没有的 key → save 时 selected 含此 key → 422 SNAPSHOT_INVALID_DIMENSION_KEY

### B4: save path / task 一致性（audit M5 修复）

- user_X 在 node_A 上有 task_X (succeeded)；user_X 也 own 同 project 的 node_B
- 调 `POST /api/projects/{p}/nodes/{node_B}/snapshot/save` body 填 `task_id=task_X.id`
- **断言**：422 SNAPSHOT_TASK_PATH_MISMATCH；node_B 没有任何新 dimension_records（Service 入口断言失败前不进事务）

### B5: dimension content dict 形态（audit B2 修复）

- mock provider 返回 review_data 中某 dimension 的 content 是 string 而非 dict（"feature_description content..."）
- **断言**：task 状态 = failed + `error_code=SNAPSHOT_PARSE_FAILED`（Service parse review_data 时 Pydantic DimensionSnapshotItem.content: dict 校验失败）；task 不进入 succeeded 状态
- **变种 B5b**：mock 返回 content={"text": "正确字符串"}（合规 dict）→ task succeeded，save 后 dimension_records.content == {"text": "正确字符串"} 落库

---

## I. 幂等

### I1: 5 分钟内连点同一按钮（含并发）

- 同 user / 同 project / 同 node / version_count 不变；POST /generate × 3 串行
- **断言**：3 次返回**同一** task_id；第 2、3 次响应 `is_idempotent_hit=true`；ai_snapshot_tasks 表只有 1 行

### I1b: 并发 get-or-create（audit M6 修复 + verify 补强）

- 同 user/proj/node/vc，3 个**独立 httpx.AsyncClient**（不共享 session/connection pool，模拟真并发请求；不要用同 client 串行）同时调 POST /generate（`asyncio.gather`）
- **断言**：返回 3 个 response 的 task_id 完全相同；ai_snapshot_tasks 表只 1 行；BackgroundTasks 仅排 1 次（pg_advisory_xact_lock 串行化）；3 个请求服务端日志可见 `pg_advisory_xact_lock` 等待时长 > 0

### I2: 中间新增 version 后再点

- POST /generate（拿 task_A，version_count=5）→ M05 加一条 version → POST /generate（version_count=6）
- **断言**：返回**新** task_B；表里有 2 行

### I3: 不同 user 同 node 并发

- user_X 调 generate；user_Y 同时调同 node 的 generate
- **断言**：返回 2 个不同 task_id（幂等 key 含 user_id）；两个任务独立跑，互不影响 dimension_records 写入

### I4: 5 分钟过期边界精确（audit m4 修复）

- POST /generate（拿 task_A）→ freezegun 推进到 4:59 → POST /generate → 返回 task_A（仍命中复用）
- 推进到 5:01 → POST /generate → 返回新 task_B（窗口外不复用）
- 推进到 6:00 → 同上仍新建

### I5: 失败任务不复用

- POST /generate → mock provider 抛错 → task_A failed → 立即 POST /generate（同 user/proj/node/vc，仍在 5min 窗口内）
- **断言**：返回新 task_B（failed 不在复用列表里——见 §9 find_idempotent 的 status 过滤）

---

## S. 状态机

### S1: 完整成功路径

- pending → running（BackgroundTasks 拉起）→ succeeded（mock provider 返回 + parse OK）

### S2: 完整失败路径

- **S2a 超时**：mock provider sleep 700s → asyncio.timeout(600) 触发 → task failed + SNAPSHOT_TIMEOUT
- **S2b provider error**：mock 抛 ProviderError → task failed + SNAPSHOT_PROVIDER_ERROR
- **S2c quota**：mock 抛 quota → SNAPSHOT_QUOTA_EXCEEDED
- **S2d parse**：mock 返回非 JSON → SNAPSHOT_PARSE_FAILED

### S3: 终态不可变

- task succeeded → 测试 hook 强行调 `service._transition(task, "running")` → 抛 SnapshotTaskFinalizedError
- failed → 同上
- cancelled → 同上（即使本期不实装 cancel 端点，单元测试覆盖状态机）

### S4: succeeded 后再点 generate（version_count 没变）

- 拿到 succeeded task_A → POST /generate（同参数）→ 返回 task_A（幂等命中复用）+ `is_idempotent_hit=true`；前端立刻拿到 review_data

---

## P. Polling / 后台 fire-and-forget 特化

### P1: BackgroundTasks 起跑后断开请求

- 测试 client：POST /generate 拿到 task_id 后**立即关闭 HTTP 连接**
- **断言**：BackgroundTasks 仍跑完 → task succeeded（FastAPI BackgroundTasks 文档保证 response 后才执行）

### P2: 进程崩溃模拟（zombie）

- 手工把 task `status` 改 `running` + `created_at` 改为 30 分钟前
- 跑 zombie cron `python -m api.cron.zombie_snapshot_tasks`
- **断言**：task 状态变 failed + `error_code=SNAPSHOT_ZOMBIE` + `error_message='任务执行异常退出'` + `expires_at = NOW + 30d`

### P3: expires_at 清理

- 手工把 task `expires_at` 改为 1 小时前
- 跑 cleanup cron
- **断言**：task 物理删除（DB 行不存在）

### P4: 前端"温柔放手"

- 模拟前端轮 30 次（5s 间隔）后停止 → 后台 task 仍在 running → 用户 5 分钟后回来调 GET → 拿到 succeeded 结果
- **断言**：服务端不感知前端是否在轮；任务进度独立

### P5: zombie cron 与正常 runner race（audit B3+m4 修复）

- 手工把 task A `created_at` 改到 11min 前（status 仍 running） → 同时启动：
  - 协程 1：跑 zombie cron `cas_zombie_transition()` → 试图转 failed
  - 协程 2：runner 拿到 AI 结果，调 `cas_complete(task_id, status='succeeded')` → 试图转 succeeded
- **断言**：两次 UPDATE 中只 1 个 affected_rows=1，另一个 affected_rows=0 → 任务终态唯一（要么 succeeded 要么 failed/SNAPSHOT_ZOMBIE，不双写）；activity_log 仅 1 条终态事件

### P6: pending zombie 兜底（audit m1+m6 修复）

- 手工创建 task `status='pending'` + `created_at` 改到 3min 前（模拟 add_task 失败 / OOM）
- 跑 zombie cron `cas_zombie_transition(pending_threshold_min=2)`
- **断言**：task 转 failed + `error_code=SNAPSHOT_ZOMBIE` + `expires_at=NOW+30d`

---

## T. Tenant 隔离

### T1: 跨 project generate

- user 是 project_A 的 editor，不是 project_B 的 member；POST /api/projects/{B}/nodes/{nid_in_B}/snapshot/generate
- **断言**：404（check_project_access 拒绝）

### T2: GET 跨 project 越权

- user_X（project_A 成员）创建 task_X；user_Y（不在 project_A）拿 task_X 的 task_id 调 GET /api/snapshot-tasks/{task_X.id}
- **断言**：404（Service 反查 user_Y 不在 task_X.project_id 的 member 列表）

### T2.5: GET 同 project 越权（audit B4 修复——核心 Blocker）

- user_X 和 user_Z 都是 project_A 的 editor；user_X 创建 task_X；user_Z 拿到 task_X.id（截屏 / 链接）调 GET /api/snapshot-tasks/{task_X.id}
- **断言**：404（Service 反查 task.user_id != user_Z → SnapshotTaskNotFoundError，错误信息打码不暴露 task 存在）；review_data 不泄漏给 user_Z

### T3: save 越权

- user_X 创建 task_X 跑成 succeeded；user_Y（同 project editor）拿 task_X.id 调 POST /save
- **断言**：404（DAO `get_by_id(task_id, user_id=current_user.id)` filter 卡 user_id；返回 None）

### T4: GET 不存在 task_id

- 随机 UUID 调 GET /api/snapshot-tasks/<random>
- **断言**：404 + 错误信息打码（不区分"不存在 / 越权"）

---

## A. 鉴权

### A1: 未登录

- POST /generate 不带 Authorization header → 401

### A2: viewer 无写权

- viewer 调 POST /generate → 403（check_project_access role="editor"）
- viewer 调 POST /save → 403
- viewer 调 GET /snapshot-tasks/{id}（自己的 task）→ 200（轮询查任务状态等同读，viewer 即可）—— 但 viewer 没有 generate 权限不会有自己创建的 task；这条主要测"editor 创建 + 同 project viewer 来读"在 Service 反查时是否放行

### A3: P2 内部凭据签名

- Server Action → FastAPI 调用必须带 `X-Internal-Token` + `X-User-Id` + `X-Internal-Timestamp` + `X-Internal-Signature`（参 ADR-004 §3.2）
- 缺签名 → 401；签名 5 分钟外 → 401；signature 不匹配 → 401

---

## E. 错误处理

### E1: M04 save 失败

- mock M04 `create_dimension_record` 抛 DBError → save 端点 wrap 为 `SnapshotSaveFailedError`（500）；事务回滚（dimension_records 一条都不写）；activity_log 也回滚

### E2: AI provider 未配置

- project 没配 ai_provider（值为 None）→ POST /generate → 422 SNAPSHOT_PROVIDER_NOT_CONFIGURED

### E3: 失败 task 重发起

- task_A failed → 用户点重新生成 → 调 POST /generate → 拿 task_B（不复用 task_A，因为 failed 不在复用列表）→ task_B 跑成 succeeded → 前端可正常 save

---

## D. R10 / R11 / R13 合规自检

- **R10-1 批量**：save 阶段 N 条 dimension_records 必须每条单独写 activity_log（断言 activity_log 行数 = N+1，包括 ai_snapshot.complete 那一条 + N 条 create）
- **R10-2 CHECK 枚举**：尝试 `INSERT INTO activity_log (action_type) VALUES ('ai_snapshot.unknown')` → DB CHECK 拒绝（迁移后枚举只含 3 个 ai_snapshot.* 值）
- **R11-2 project_id 在 idempotency key**（audit B1 修复后调整——不再依赖 DB UniqueConstraint）：通过 Service 层 `find_idempotent` 验证 key 包含 project_id：
  - 已有 task_A `(user, projA, node, vc=5, succeeded)` 5min 内 → 同 user 同 node 不同 project (projB) 调 generate → 返回新 task_B（projA 的 task 不命中 projB 查询）→ 断言两个 task 共存
  - 同 user 同 projA 同 node 同 vc 5min 内再调 generate → 返回 task_A（命中复用），不新建
- **R13-1**：14 个 ErrorCode 各有 raise 路径覆盖（每个 case 至少 1 个测试，含 SnapshotZombieError / SnapshotTaskPathMismatchError）

---

## 测试矩阵小结

| 类别 | 用例数 | 关键覆盖 |
|------|-------|---------|
| Golden | 3 | 完整闭环 + save 3 种粒度 |
| 边界 | 5 | AC1 + content 极端 + 维度异常 |
| 幂等 | 5 | 连点 / version 变化 / user 隔离 / 过期 / 失败不复用 |
| 状态机 | 4 | 成功 / 失败 / 终态 / 复用 |
| 后台特化 | 4 | 断开 / zombie / 清理 / 轮询放手 |
| Tenant | 4 | 跨 project / GET 越权 / save 越权 / 打码 |
| 鉴权 | 3 | 401 / 403 / P2 签名 |
| 错误处理 | 3 | save 回滚 / provider 未配 / 失败重发 |
| R-合规 | 4 | R10-1 / R10-2 / R11-2 / R13-1 |
| **合计** | **42** | — |

> 用例增量（vs 初稿 35）：I1b 并发幂等 / B4 path mismatch / B5 content 形态 / P5 race / P6 pending zombie / T2.5 同 project 越权 + I4 边界精确（覆盖 audit 关键 Blocker / Major）
