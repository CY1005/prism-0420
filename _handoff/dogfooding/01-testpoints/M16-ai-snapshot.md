---
module: M16
name: ai-snapshot
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M16-ai-snapshot/00-design.md
  - design/02-modules/M16-ai-snapshot/tests.md
  - design/02-modules/M16-ai-snapshot/audit-report.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F16 AI 快照（AC1-AC3 / 版本演进 ≥3 触发 / 一句话概要 + 维度结构化输出 / 选择性 save）
---

# M16 AI 快照 测试点

## 业务流程（H1 / 1 行概述）

M16 = 🪷 后台 fire-and-forget pilot：editor 在 M04 档案页点 "AI 生成快照" → POST /generate 创建 ai_snapshot_tasks 任务 202 立返 → FastAPI BackgroundTasks 自起 SessionLocal 跑 AI provider（10min 硬超时 / 不重试 / asyncio.timeout 600s）→ CAS UPDATE 转 succeeded/failed → 前端轮询 GET /snapshot-tasks/{id} 拿 review_data → save 经 M04 DimensionService 追加 N+1 条 dimension_records / activity_log；zombie cron 每 5min 兜底转 failed/SNAPSHOT_ZOMBIE。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] POST /api/projects/{pid}/nodes/{nid}/snapshot/generate happy path 返 202 + task_id + status=pending + is_idempotent_hit=false + poll_url（design §7 SnapshotTaskCreatedResponse + tests.md G1）
- [P0] POST /generate 响应耗时 <200ms 不阻塞 fire-and-forget（design §1 + tests.md G1）
- [P0] GET /api/snapshot-tasks/{task_id} 拿到 succeeded + review_data.summary 非空 + dimensions 长度 = 当前 node 维度数（design §7 SnapshotTaskDetailResponse + tests.md G1）
- [P0] POST /snapshot/save save_summary=true + selected_dimension_keys=全部 → dimension_records 新增 N+1 条（含 1 条 snapshot_summary）（design §11 + tests.md G1）
- [P0] save 写入 dimension_records.content 形态校验 snapshot_summary 那条 content == {"summary": "..."} 其他 N 条为 dict 至少含 text（design §7 audit B2 修复 + tests.md G1）
- [P0] PRD F16 AC1：版本数 ≥3 才允许生成快照（design §8 Service + tests.md B1）
- [P0] PRD F16 AC2：AI 输出两部分一句话概要 + 按维度结构化（design §1 + tests.md G1）
- [P0] PRD F16 AC3：用户 review 后 summary 保存为功能项摘要 + 结构化部分可按维度选择性覆盖/更新（design §1 Q2.1+Q2.2+Q2.3 + tests.md G3）
- [P1] save save_summary=true + selected_dimension_keys=[] 仅新增 1 条 snapshot_summary（design §11 + tests.md G2）
- [P1] save save_summary=false + selected_dimension_keys=部分维度 → 仅勾选维度新建 dimension_records summary 不保存（design §11 + tests.md G3）
- [P1] 保存语义 = 追加+最新赢 旧 dimension_records 保留不更新（design §1 Q2.2 + tests.md G1 断言）
- [P1] save 响应含 saved_dimension_record_ids + saved_count + summary_saved + message（design §7 SnapshotSaveResponse）
- [P1] generate 响应 estimated_duration_seconds 默认 60（design §7 SnapshotTaskCreatedResponse）
- [P1] node 当前无任何 dimension_records → review_data.dimensions=[]，save 时 selected_dimension_keys 必须空（design §1 + tests.md B3a）
- [P2] succeeded 但用户不 save 的任务 task 表保留 30 天后清理快照未沉淀（design §1 + §12 字段⑦）

### 2. 边界 / 状态机

- [P0] 版本数=0/1/2 generate 返 422 SNAPSHOT_INSUFFICIENT_VERSIONS 含 actual + required=3（design §13 + tests.md B1）
- [P0] 版本数=3 generate 返 202 边界放行（design §1 + tests.md B1）
- [P0] 状态机 pending → running → succeeded 完整成功路径（design §4 + tests.md S1）
- [P0] 状态机 pending → running → failed（provider 报错路径）（design §4 + tests.md S2）
- [P0] 终态不可变：succeeded → 任意/failed → 任意 抛 SnapshotTaskFinalizedError（design §4 R4-2 + tests.md S3）
- [P0] pending → succeeded 跳过 running 抛 SnapshotInvalidStateTransitionError（design §4 禁止转换 + tests.md S3）
- [P1] running → pending / 任意 → pending 抛 SnapshotInvalidStateTransitionError（design §4 禁止转换）
- [P1] cancelled 预留态本期不暴露 endpoint 任何 service 路径写入抛 SnapshotInvalidStateTransitionError（design §4 R4-3a 登记表）
- [P1] succeeded 后再点 generate（version_count 没变）幂等命中复用 task_A is_idempotent_hit=true（design §11 + tests.md S4）
- [P1] mock provider 返 summary="" task succeeded save 时 dimension_records.content 写空 summary 业务接受（design §1 + tests.md B2a）
- [P1] mock provider 返 summary 长度 200KB task succeeded JSONB TOAST 压缩正常落库（design §3 + tests.md B2b）
- [P1] save path/task 一致性校验 task.project_id != path_project_id 或 task.node_id != path_node_id 抛 SnapshotTaskPathMismatchError 422（design §7 audit M5 修复 + tests.md B4）
- [P1] save selected_dimension_keys 含 review_data.dimensions 没有的 key 抛 SnapshotInvalidDimensionKeyError 422 含 invalid 列表（design §11 + tests.md B3b）
- [P2] expires_at 仅在终态转换时设 NOW+30d pending/running 不设（design §12 字段⑦）

### 3. 异常 / 错误

- [P0] AI provider 抛 ProviderError task 转 failed + error_code=SNAPSHOT_PROVIDER_ERROR + error_message（design §13 + tests.md S2b）
- [P0] AI provider 调用超过 600s asyncio.timeout 触发 task failed + SNAPSHOT_TIMEOUT 504（design §6 runner + §13 + tests.md S2a）
- [P0] AI 输出非 JSON / parse 失败 task failed + SNAPSHOT_PARSE_FAILED 502（design §13 + tests.md B2c / S2d）
- [P0] AI provider quota 耗尽 task failed + SNAPSHOT_QUOTA_EXCEEDED 429（design §13 + tests.md S2c）
- [P0] M04 create_dimension_record 抛 DBError save 端点 wrap SnapshotSaveFailedError 500 + 事务回滚 dimension_records 一条都不写（design §13 R13-2 + tests.md E1）
- [P0] AI 返回 dimension content 是 string 非 dict task failed + SNAPSHOT_PARSE_FAILED 不进 succeeded 状态（design §7 audit B2 + tests.md B5）
- [P1] project.ai_provider=None 调 generate 返 SNAPSHOT_PROVIDER_NOT_CONFIGURED 422（design §13 + tests.md E2）
- [P1] task failed 后立即重发起 generate 拿到新 task_B（failed 不在复用列表）+ task_B 跑成可正常 save（design §11 + tests.md I5 / E3）
- [P1] runner 失败分支统一走 cas_complete(status='failed') 不直 UPDATE 否则与 zombie cron 双写（design §6 关键纪律 + 禁止清单）
- [P1] AI provider 失败 task 不自动转 pending 重发（违背显式重发语义）（design §12 字段⑥ 未来后台模块照抄要点）
- [P1] save 失败 activity_log 也回滚（design §10 + tests.md E1）
- [P1] DimensionSnapshotItem.content Pydantic 校验失败时识别为 SNAPSHOT_PARSE_FAILED 而非 SNAPSHOT_PROVIDER_ERROR（design §13 + audit B2 修复）
- [P2] error_message 截断 ≤500 字符避免日志爆炸（design §6 runner 代码 e.message_short）

### 4. 权限 / Auth

- [P0] 未登录调 POST /generate 返 UNAUTHENTICATED 401（design §8 + tests.md A1）
- [P0] viewer 调 POST /generate 返 PERMISSION_DENIED 403（check_project_access role=editor / design §8 + tests.md A2）
- [P0] viewer 调 POST /save 返 PERMISSION_DENIED 403（design §8 + tests.md A2）
- [P0] viewer 调 GET /snapshot-tasks/{id} 自己 task 返 200（轮询查任务状态等同读 viewer 可读）（design §8 + tests.md A2）
- [P0] GET endpoint 第一层校验 task.user_id != current_user_id 抛 SnapshotTaskNotFoundError 404 错误打码不暴露 task 存在（design §8 audit B4 修复 + tests.md T2.5）
- [P0] GET endpoint 第二层校验 task.project_id 不可访问（user 被踢出 project）抛 SnapshotTaskNotFoundError 404（design §8 audit B4 + tests.md T2）
- [P0] save Service 校验 task.user_id != current_user_id 返 404（DAO get_by_id 带 user_id filter / design §8 + tests.md T3）
- [P0] save Service 校验 task.status != succeeded 抛 SnapshotNotReadyError 409（design §8 + design §13）
- [P1] generate Service 校验 node 属于 path project（NodeService.get_by_id 反查 → SnapshotNodeNotFoundError 404）（design §8 + 元教训 #4）
- [P1] Server Action P2 内部凭据签名缺 X-Internal-Token / X-User-Id / 时间戳 / 签名 401（design §8 + ADR-004 §3.2 + tests.md A3）
- [P1] P2 签名时间戳 >5min 外 401（design §8 + tests.md A3）
- [P1] editor 调 POST /generate 通过 + POST /save 通过（design §8 角色矩阵 + tests.md A2）
- [P1] GET 端点 errors 全部统一 SnapshotTaskNotFoundError 不分别说"不存在/不是 creator/project 没了"打码一致（design §8 错误信息打码）
- [P2] task_id UUIDv4 空间 2^122 不需额外 rate limit（design §8 brute force 风险）

### 5. Tenant 隔离

- [P0] 跨 project 调 generate user 是 project_A editor 不是 project_B member POST /api/projects/{B}/nodes/{nid}/snapshot/generate 返 404（design §8 + tests.md T1）
- [P0] GET 跨 project 越权 user_Y 不在 project_A 拿 task_X.id 调 GET 返 404 Service 反查打码（design §8 第二层 + tests.md T2）
- [P0] GET 同 project 越权 user_Z 同 project editor 拿 task_X.id（非 creator）返 404 review_data 不泄漏（design §8 第一层 audit B4 + tests.md T2.5）
- [P0] save 跨 user 越权 user_Y 拿 user_X 的 task_id 返 404（DAO get_by_id 带 user_id filter / design §8 + tests.md T3）
- [P0] ai_snapshot_tasks 表 project_id 冗余字段 DAO 查询 WHERE project_id=? 强过滤（design §5 + §9）
- [P0] R11-2 idempotency key 含 project_id：同 user 同 node 不同 project 不命中复用返 2 个独立 task（design §11 + tests.md R11-2）
- [P1] GET /snapshot-tasks/{random_uuid} 返 404 错误打码不区分不存在/越权（design §8 + tests.md T4）
- [P1] DAO get_by_id(task_id, user_id) 双签名形态：传 user_id 强制过滤（save 用）/ 不传由 Service 反查（GET 用）（design §9 + 元教训 #15）
- [P1] BackgroundTasks payload 无序列化跨进程边界 user_id/project_id 通过函数参数传（design §5 约束清单第 3 项 N/A）
- [P2] 未来同 project editor 互看任务列表放宽时第一层校验改为 OR ≥editor 且 §10 新增 ai_snapshot.read 敏感读事件（design §8 未来放宽路径）

### 6. 并发 / 乐观锁

- [P0] 5min 内连点同 user/proj/node/version_count generate × 3 串行返同一 task_id 表里只 1 行 第 2/3 次 is_idempotent_hit=true（design §11 + tests.md I1）
- [P0] 并发 get-or-create 3 个独立 httpx.AsyncClient asyncio.gather 同时 generate 返 3 个相同 task_id 表里 1 行 BackgroundTasks 排 1 次（design §11 advisory_xact_lock + tests.md I1b）
- [P0] zombie cron vs runner race CAS UPDATE 只 1 个 affected_rows=1 任务终态唯一 activity_log 仅 1 条终态事件（design §5 audit B3 + tests.md P5）
- [P1] 同 user/proj/node 中间新增 version generate 拿新 task_B（version_count 变化破坏幂等 key）（design §11 + tests.md I2）
- [P1] 不同 user 同 node 并发 generate 返 2 个独立 task_id 互不影响 dimension_records 写入（design §5 + tests.md I3）
- [P1] freezegun 推进 4:59 generate 仍命中 task_A 推进 5:01 generate 拿新 task_B 窗口外不复用（design §11 + tests.md I4）
- [P1] save 端点无幂等 用户重复点 save = 多条 dimension_records 历史（Q2.3 M04 多条历史语义合法 / design §5 + §11）
- [P1] failed task 不复用 立即 generate 同参数（5min 内）返新 task_B（design §9 find_idempotent status 过滤 + tests.md I5）
- [P1] 不使用乐观锁 version（save 是 INSERT 非 UPDATE 任务状态变迁单 user 单 task 串行）（design §5 约束清单第 2 项）
- [P1] cas_start_running 仅当 status='pending' 才转 running affected=0 表示已被 cron 抢先转 failed runner 退出（design §6 + §9）
- [P1] cas_complete affected=0 时不写 ai_snapshot.failed log 避免与 zombie cron 重复写（design §6 关键纪律）
- [P2] pg_advisory_xact_lock 事务级 commit 后自动释放无泄漏风险（design §11 advisory_xact_lock 理由）

### 7. 数据完整性

- [P0] ai_snapshot_tasks 表不建 DB UniqueConstraint 幂等走 ORM find_idempotent + advisory_xact_lock（design §3 audit B1 + §12 字段①）
- [P0] zombie cron CAS UPDATE pending 阈值 2min + running 阈值 11min 单条 RETURNING ids 不读-改-写两步（design §9 cas_zombie_transition + tests.md P6）
- [P0] zombie cron user_id 写 activity_log 必须落 SYSTEM_USER_UUID 禁止用 task creator user_id 或 NULL（design §9 + §10 ADR-002 §1.1）
- [P0] ai_snapshot.complete metadata 必含 estimated_cost_usd / generation_time_ms / dimensions_count / ai_provider / ai_model 5 字段每条 e2e 字面验（design §10 + 元教训 #11）
- [P0] save 阶段 N 条 dimension_record 在同事务内 N+? 次 create_dimension_record 任一失败回滚（design §5 多表事务 + §11 save_snapshot 代码）
- [P1] activity_log 4 类事件齐全 ai_snapshot.start + ai_snapshot.complete + ai_snapshot.failed 由 M16 自写 + create dimension_record N+1 条由 M04 代写（design §10 + tests.md G1 / R10-1）
- [P1] ai_snapshot.start metadata 含 node_id / version_count / ai_provider / ai_model（design §10）
- [P1] ai_snapshot.failed metadata 含 node_id / version_count / ai_provider / error_code / error_message_short（design §10）
- [P1] dimension_record activity_log metadata 含 source="ai_snapshot" + task_id 用于 M15 时间线展示（design §10 + §11 extra_activity_metadata）
- [P1] M15 activity_log CHECK 枚举扩 3 个 action_type + 1 个 target_type Alembic 迁移（design §10 R10-2 + §15 accept 前置）
- [P1] R10-2 尝试 INSERT activity_log action_type='ai_snapshot.unknown' DB CHECK 拒绝（design §10 + tests.md R10-2）
- [P1] expires_at 字段仅终态转换时设 NOW+30d zombie cron 路径也设 expires_at 进入 30d 清理流程（design §12 字段⑦）
- [P1] R13-1 14 个 ErrorCode 各有 AppError 子类对应（含 SnapshotZombieError audit M2 修复后不再例外）（design §13 + tests.md R13-1）
- [P1] R13-2 跨模块错误 wrap M02→ProviderNotConfigured / M04→SaveFailed / M05→InsufficientVersions / M03→NodeNotFound / AI SDK→ProviderError（design §13）
- [P2] review_data JSONB 大字段（5-30KB 典型 / >100KB 少数）PG TOAST 自动压缩（design §3 Alembic 要点）

### 8. UI / UX

- [P0] 前端轮询 GET /snapshot-tasks/{id} 每 3-5s 一次拿 status 切到 succeeded 弹 toast + 档案页徽标从生成中变红点（design §1 用户场景）
- [P1] 前端轮 30 次（5s × 30 = 2.5min）后未 succeeded 弹"温柔放手"toast 停轮用户回来调 GET 即可拿结果（design §12 字段⑤）
- [P1] 前端拿到 failed status 弹 toast "{error_message}，点这里重新生成"用户点重新生成 = 新 task（design §12 字段⑥）
- [P1] 前端按 created_at DESC 取最新 dimension_record 作为"当前值"snapshot 后档案页该 node 维度卡片立即更新（design §1 + Q2.2）
- [P1] snapshot-poller useEffect cleanup 防内存泄漏不许 setInterval 不带 cleanup（design §6 禁止清单）
- [P2] generate 响应 estimated_duration_seconds=60 给前端 UX 提示用（实际 30s-3min）（design §7）
- [P2] review-drawer UI 允许用户勾选要保存的维度按 selected_dimension_keys 提交（design §1 用户场景 + §7 SnapshotSaveRequest）

### 9. 性能（如适用）

- [P0] BackgroundTasks 起跑后断开 HTTP 连接 task 仍跑完 succeeded（FastAPI 文档保证）（design §6 + tests.md P1）
- [P0] zombie cron 跑频率 5min ≤ 阈值 11min/2 用户感知失败延迟最坏 ≤16min（design §5 + §12 字段⑦ audit M4 修复）
- [P1] zombie cron 单条 CAS UPDATE 含 ix_ai_snapshot_status_created 复合索引扫表（design §3 索引 + §9 audit m2 修复）
- [P1] ix_ai_snapshot_idem_lookup 复合索引 find_idempotent 5min 窗口查询用（design §3 索引）
- [P1] node_id+status 索引 + user_id+created_at 索引 查询路径覆盖（design §3 5 索引）
- [P1] M05 count_by_node typical node ≤100 versions p95 <5ms（design §15 baseline-patch M05 §6）
- [P2] BackgroundTasks 同 worker 进程 asyncio 单线程串行无跨请求竞态（design §5 心智模型）
- [P2] AI provider 单次调用成本通过 metadata.estimated_cost_usd 跟踪反悔触发器（design §6 监测路径）

### 10. 兼容性（如适用）

- [P1] 多 AI provider 支持 claude / kimi / codex / mock 非流式接口 generate(prompt) -> str（design §2 + ADR-001 §4.1）
- [P1] M04 create_dimension_record 签名锁定 R-X3 契约 接受外部 db session 不开事务（design §15 accept 前置）
- [P2] 未来 SQLAlchemy 2.x autobegin 升级 Service 层 with db.begin() 降级为 begin_nested() 风险列入 Phase 2 contract 校验（design §6.5 verify 风险防御）

### 11. 后台 fire-and-forget 特化（§12B 子模板验证）

- [P0] BackgroundTasks 自起 SessionLocal 不复用请求级 Depends(get_db) session（design §6 runner 代码 + audit B3 修复）
- [P0] 进程崩溃模拟 task `status='running' + created_at` 改 30min 前 cron 转 failed/SNAPSHOT_ZOMBIE + 'task abnormally exited' + expires_at=NOW+30d（design §12 字段⑦ + tests.md P2）
- [P0] pending zombie 兜底 task `status='pending' + created_at` 改 3min 前 cron 转 failed/SNAPSHOT_ZOMBIE（add_task 失败/OOM 孤儿 pending 也被抓 / design §9 + tests.md P6）
- [P1] expires_at 清理 cron 扫 expires_at < NOW 物理删除（不软删 task 表无审计价值）（design §12 字段⑦ + tests.md P3）
- [P1] 服务器硬超时 600s 必须比"用户耐心轮询窗口"宽 1-3 倍（design §12 字段⑤ 未来后台模块照抄要点）
- [P1] zombie 阈值 = 服务器硬超时 + commit buffer（M16 = 10min + 1min = 11min）（design §12 字段⑦）
- [P1] cron 入口在拿到 cas_zombie_transition RETURNING ids 后批量补写 activity_log user_id 落 SYSTEM_USER_UUID（design §9 docstring + §10 cron user_id 边界）
- [P1] Service 事务内禁止调 DAO cas_* / cas_zombie_transition（内部 commit 破坏外层事务 / 仅供 runner / cron 顶层调用）（design §6 禁止清单）

### 12. 数据流转 / 跨模块契约

- [P0] M04 create_dimension_record 接受外部 db session 同事务写 dimension_record + activity_log（design §15 M04 契约锁定 + 元教训 #2）
- [P0] M05 count_by_node 新增方法签名 双 tenant 过滤 + 不开事务 + 不写 activity_log（design §15 M05 baseline-patch）
- [P0] M02 ProjectService.get_by_id_for_user 用于权限反查（design §2 依赖契约）
- [P0] M03 NodeService.get_by_id 校验 node 属于 project（design §2 + 元教训 #4）
- [P0] M16 不直 JOIN dimension_records / version_records / nodes 必经 Service 接口（design §3 禁止）
- [P0] M16 不直 INSERT dimension_records 必经 M04 Service（design §3 禁止 + §6 禁止）
- [P1] M15 UI 侧理解 metadata.task_id 字段 在时间线展示 "AI 快照"图标/标签（design §10 + §15 同期补丁）
- [P1] save 阶段 N 条 dimension_record 共享同一事务任一失败回滚一键 review 全保存 = 原子（design §5 多表事务）
- [P1] AI prompt 模板必须通过 context 注入 node 名称 / current_dimensions / versions（不许硬编码业务数据）（design §6 禁止清单）

### 13. dimension_type / 维度内容契约

- [P0] save 阶段首次创建 snapshot_summary 维度时 M04 DimensionService 在 dimension_types 表 upsert key（design §1 边界灰区 + §15 同期补丁）
- [P0] save 通过 selected_dimension_keys 必须是 review_data.dimensions 子集否则 422（design §7 audit M5 + §11 + tests.md B3b）
- [P0] save 端点篡改防御：前端只传 task_id + selected_dimension_keys 不传 content Service 从 task.review_data 读权威 content（design §7 audit B2 + M5 + §11 save_snapshot 代码）
- [P1] DimensionSnapshotItem.content: dict 形态契约（M04 dimension_records.content JSONB 列契约对齐）（design §7 audit B2 修复）
- [P1] snapshot_summary 维度 content = {"summary": "..."}其他维度 content 至少含 text 或对应维度结构化字段（design §7 + tests.md G1）
- [P2] 未来"用户编辑后再 save"加 content_overrides: dict[str, dict]字段本期不做（符合 PRD AC3 选择性覆盖语义 / design §7）

### 14. 反悔触发器 / 可观测性（audit M3 修复）

- [P1] zombie 率指标 count(error_code='SNAPSHOT_ZOMBIE') / count(status IN ('succeeded','failed')) ≥1% 每周 cron 算一次写入 metrics 表（design §6 监测路径）
- [P1] 单次成本指标 avg(metadata.estimated_cost_usd) ≥ $0.5 / 次 同上每周 cron 算一次（design §6 监测路径）
- [P2] 任一阈值超标主对话评估迁移到 arq Queue 迁移成本约 50 行 + 部署 Redis worker（design §6 反悔触发器）

### 15. 数学 / 计数 / 审计

- [P0] G1 完整闭环 activity_log 新增 N+3 条（1 ai_snapshot.start + 1 ai_snapshot.complete + N+1 create dimension_record）（design §10 + tests.md G1 audit m3 修复"原 4 条数学错"）
- [P0] R10-1 save 阶段断言 activity_log 行数 = N+1（含 1 条 ai_snapshot.complete + N 条 create）+ 1 条 dimension_record summary（design §10 + tests.md R10-1）
- [P1] 任务成功路径 expires_at = completed_at + 30d（design §4 + tests.md G1 断言）
- [P1] cas_complete affected=1 才写 ai_snapshot.complete log 保证与 zombie cron 不双写（design §6 关键纪律）
