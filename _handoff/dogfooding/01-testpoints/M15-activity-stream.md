---
module: M15
name: activity-stream
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M15-activity-stream/00-design.md
  - design/02-modules/M15-activity-stream/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: US-A2.2 + PRD Q3 + PRD Q4（activity_log 多人协作审计）
---

# M15 数据流转可视化 测试点

## 业务流程（H1 / 1 行概述）

M15 是纯读聚合模块（消费横切 activity_logs 表 + JOIN M01 users 取 name + 强 project_id tenant 过滤），自身无写入；GET /api/projects/{pid}/activity-stream 按时间倒序分页返 ActivityStreamResponse（owner+editor 可审计 C-5、viewer 不可），支持 user_id/action_type/target_type/from_dt/to_dt 五维过滤；M15 是 activity_logs 横切表 owner（R10-2，负责 ActionType/TargetType enum + CheckConstraint + Alembic 迁移），ImmutableMixin 仅 created_at 不可变；M15 自身无 activity_log 事件、无状态机、无 Queue、无 idempotency_key、无并发写冲突场景。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] owner GET /api/projects/{pid}/activity-stream?page=1&page_size=20 返 200 + items 按 created_at 倒序 + 每条含 user_name JOIN（design §7 + tests.md G1）
- [P0] editor GET /api/projects/{pid}/activity-stream 返 200 + 完整列表（design §8 C-5 owner+editor 可审计 + tests.md P3）
- [P0] ActivityStreamResponse 首页 page=1 返精确 total 整数 / page=2+ 返 total=null 仅靠 has_more 翻页（design §7 D-2 CY ack + §3 DAO list_stream offset>0 total=None）
- [P0] ?user_id={uid} 过滤返 items 全部来自该 user（design §7 ActivityStreamFilter + tests.md G2）
- [P0] ?action_type=node_updated 过滤返 items 全部为该 action_type（design §7 + tests.md G3）
- [P0] ?from_dt=2026-01-01T00:00:00&to_dt=2026-04-01T00:00:00 过滤返 items 全部在范围内含边界（design §7 + tests.md G4）
- [P1] ?user_id={uid}&action_type=node_created&target_type=node 组合过滤返满足全部三条件 items（design §7 + tests.md G5）
- [P1] ?target_type=team 过滤返 items 全部为 target_type=team（design §7 TargetType + M20 baseline-patch）
- [P1] items[].user_name 来自 JOIN users.name 而非 user_id 字面（design §3 DAO list_stream + §9 users JOIN 豁免）
- [P1] items[].summary 显示写入方冻结的可读摘要不做跨表 JOIN 取 target name（design §1 A-11 CY ack 仅 summary + tests.md 边界灰区）
- [P1] items[].metadata 字段 nullable / 写入方可省（design §3 JSONB nullable=True + §7 ActivityLogItem Optional）
- [P1] ?page_size 默认 50 / page 默认 1（design §7 Field default + tests.md G1 隐含）
- [P2] items 按 created_at desc 排序在同毫秒内 fallback 顺序不抖动（design §3 DAO order_by desc(created_at) 单列稳定性）

### 2. 边界 / 状态机

- [P0] M15 无状态机显式声明 / activity_logs 表无 status 字段 / 日志 append-only 不可修改（design §4 R4-1 + ImmutableMixin 仅 created_at）
- [P0] 空日志新建项目立即 GET 返 200 + items=[] + total=0 + has_more=false（tests.md E1）
- [P0] page=999 page_size=50 超出范围返 200 + items=[] + has_more=false（tests.md E2）
- [P1] page_size=200 上限返 200 + items.len ≤200（design §7 Field le=200 + tests.md E7）
- [P1] page_size=201 返 422 Pydantic le=200 校验（design §7 + tests.md E6）
- [P1] page=0 返 422 Pydantic ge=1 校验（design §7 page: int = Field(default=1, ge=1)）
- [P1] page_size=0 返 422 Pydantic ge=1 校验（design §7 page_size Field ge=1）
- [P1] from_dt=to_dt 同值返 200（design §7 model_validator from_dt > to_dt 拦截 / 等值放行）
- [P2] 单项目 500 条日志 page_size=200 GET 返 200 + items.len=200 + has_more=true + 响应 <2s（tests.md E7）

### 3. 异常 / 错误

- [P0] ?from_dt=2026-04-30&to_dt=2026-01-01 返 422 ACTIVITY_STREAM_INVALID_FILTER（design §7 model_validator + §13 + tests.md E3 + ER3）
- [P0] ?action_type=invalid_action 返 422 Pydantic ActionType StrEnum 校验失败（design §7 + tests.md E5）
- [P0] ?target_type=invalid_target 返 422 Pydantic TargetType StrEnum 校验失败（design §7 TargetType Enum）
- [P0] project 不存在返 404 ACTIVITY_STREAM_PROJECT_NOT_FOUND + 错误响应 `{"error":{"code":"activity_stream_project_not_found","message":"Project not found or access denied"}}`（design §13 + tests.md ER1）
- [P0] viewer 访问返 403 ACTIVITY_STREAM_FORBIDDEN + 错误响应含 code/message（design §13 ActivityStreamForbiddenError + tests.md ER2）
- [P1] ?user_id={不存在 UUID} 返 200 + items=[] + total=0 不报 404（tests.md E4 显式）
- [P1] ?user_id={非 UUID 字符串} 返 422 Pydantic UUID 校验失败（design §7 ActivityStreamFilter user_id: Optional[UUID]）
- [P1] DB 查询超时大量日志返 502/504 + 不暴露 SQL stacktrace（tests.md ER4）
- [P1] target_type=node 但目标 node 已被删 / 仍展示该日志记录 / target_id 无 FK 约束日志不丢失（design §1 边界灰区 僵尸 target_id 展示策略）
- [P1] from_dt 缺省 to_dt 给值返 200 / 单边时间过滤生效（design §3 DAO list_stream if from_dt / if to_dt 独立分支）
- [P1] action_type 跨大小写如 "NODE_CREATED" 返 422（design §7 StrEnum 严格小写匹配）

### 4. 权限 / Auth

- [P0] 未登录访问返 401 UNAUTHENTICATED（design §8 Server Action getServerSession + tests.md P1）
- [P0] viewer 角色访问返 403 ACTIVITY_STREAM_FORBIDDEN（design §8 C-5 候选 β + tests.md P2）
- [P0] editor 角色访问返 200（design §8 C-5 owner+editor 可审计 + tests.md P3）
- [P0] owner 角色访问返 200（design §8 + tests.md P4）
- [P1] check_project_access(roles=["owner","editor"]) Router 层粗粒度拦截 / Service 层 _check_activity_audit_access 二次校验（design §8 三层权限防御）
- [P1] 非项目成员（无任何角色记录）访问返 403/404（design §8 + tests.md T2）
- [P1] session 过期 token 失效访问返 401 TOKEN_EXPIRED（design §8 Server Action session 校验范式）
- [P2] M02 角色枚举无 "admin" / Router check_project_access 不接受 role="admin" 字面（design §15 C-M15-1 候选 β ack）

### 5. Tenant 隔离

- [P0] owner-A 持 projectA token GET /api/projects/{projectB_id}/activity-stream 返 403 PERMISSION_DENIED（design §8 Router check_project_access + tests.md T1）
- [P0] userC 非 projectA 成员 GET projectA activity-stream 返 403/404（design §8 Service _check_activity_audit_access + tests.md T2）
- [P0] ActivityStreamDAO.list_stream(db, other_project_id) 单元测试返空 list / 不泄露其他 project 日志（design §9 强 project_id 过滤 + tests.md T3）
- [P0] DAO list_stream 第一过滤条件强制 activity_logs.project_id=:project_id 不得省略（design §9 防绕过纪律）
- [P0] URL path 含 projectA 时 query 无法指定其他 project_id / 锁定在路径中（design §9 + tests.md T4）
- [P1] projectA 与 projectB 各有日志 owner-A 查 projectA 返 items 全部来自 projectA（tests.md T5）
- [P1] activity_logs.project_id NULLABLE 全局事件（M14 news_*）IS NULL 时不被 project_id 过滤召回（design §3 M14 baseline-patch + 14.5 元教训 12）

### 6. 并发 / 乐观锁

- [P0] M15 纯读模块无并发写冲突场景显式声明（design §5 并发控制 N/A + tests.md §3）
- [P1] 业务模块 M04 写 dimension_record 的同时 M15 GET activity-stream / PG READ COMMITTED 返查询时刻快照不需锁（tests.md §3 读-写并发）
- [P1] M04 update_dimension_record 写 activity_log 后立即 M15 GET activity-stream / 新日志出现在 items 第一条无缓存延迟（tests.md C1 读一致性）
- [P2] 多 owner/editor 同时 GET activity-stream / 各自独立返结果一致无干扰（tests.md §3 显式）

### 7. 数据完整性

- [P0] activity_logs 表 ImmutableMixin 仅 created_at 无 updated_at / 日志 append-only 不可修改（design §3 ImmutableMixin + M15-F3 修复）
- [P0] activity_logs.action_type CheckConstraint 仅枚举值字面通过 / 写入非枚举值 INSERT 失败（design §3 三重防护 R3-2 + 元教训 R14）
- [P0] activity_logs.target_type CheckConstraint 仅枚举值字面通过 / 写入非枚举值 INSERT 失败（design §3 ck_activity_log_target_type）
- [P0] M15 是 R10-2 owner / ActionType + TargetType 枚举 + CheckConstraint + Alembic 迁移在 M15 模块内统一维护（design §3 + §10 R10-2）
- [P1] activity_logs 索引 ix_activity_log_project_created (project_id, created_at) 存在 / M15 主查询路径走索引（design §3 __table_args__）
- [P1] activity_logs 索引 ix_activity_log_user_project (user_id, project_id) 存在 / 按用户过滤走索引（design §3）
- [P1] activity_logs 索引 ix_activity_log_target (target_type, target_id) 存在 / 按目标关联走索引（design §3）
- [P1] activity_logs.target_id 是 Text 字段无 FK 约束 / 日志不因 target 被删而丢失（design §1 边界灰区 + §3 Text nullable=False）
- [P1] activity_logs.metadata JSONB 列 Python 属性名 event_metadata 重映射 schema 字段 metadata（design §3 Disambiguation 2 + _to_item 重映射）
- [P1] activity_logs.project_id ForeignKey projects.id ondelete=CASCADE / 删 project 级联清日志（design §3 ForeignKey 配置）
- [P1] ActivityLog model Mapped[str] + String(50) 实装 vs design 字面 Mapped[ActionType] disambiguation（design §3 Disambiguation 1）
- [P2] activity_logs.user_id ForeignKey users.id 无 ondelete 显式 / 删 user 行为待 M01 owner 定义（design §3 user_id ForeignKey 仅 nullable=False）

### 8. UI / UX

- [P0] 未知 action_type fallback UI 展示 action_type 字符串作标题 + metadata 折叠展开 / 不隐藏不 raw JSON（design §15 C-6 候选 C ack + §7 前端渲染契约 D-3）
- [P0] target 已删除时前端展示 summary 字段内容（写入方已冻结 target 名）/ 点击跳转禁用（design §1 边界灰区 僵尸 target_id 展示策略）
- [P1] 前端时间轴按日期分组渲染 / 后端只返结构化数据不做分组（design §1 in scope + §6 Component 层）
- [P1] 过滤器 UI 含 user / action_type / target_type / 时间范围四维（design §6 activity-filter-bar.tsx + §7 ActivityStreamFilter）
- [P1] page=1 首页展示 total 计数 / page=2+ 仅"加载更多"按钮依靠 has_more 翻页（design §7 D-2 D-2 CY ack）
- [P2] activity_logs.project_id=NULL 全局事件（M14 news_*）UI 时间线分组为"全局事件" / structlog stub 序列化字面 "global"（design §3 M14 baseline-patch + 14.5 元教训 12）

### 9. 性能

- [P0] page=1 调用 q.count() 全量精确 total / page>1 跳过 count 仅 has_more / 防百万级日志全表 count 退化（design §3 DAO list_stream D-2 分支）
- [P1] activity_logs 大量日志（500 条）GET page_size=200 响应 <2s（tests.md E7）
- [P1] 主查询 (project_id, created_at) 复合索引命中 / EXPLAIN ANALYZE 不走全表扫描（design §3 ix_activity_log_project_created）
- [P2] M15 全 GET 同步路径无 Queue 无后台任务（design §5 异步处理 N/A + §12 N/A）

### 10. 集成 / 跨模块

- [P0] M01 users 表 JOIN 取 name / users 是全局表豁免 project_id 过滤（design §9 豁免清单）
- [P0] M02 projects 表只读校验 project 存在 + 用户是 owner/editor / 不写 projects 表（design §1 cross_module_reads M02）
- [P1] M04 写 activity_log action_type=dimension_record_updated → M15 list 召回（design §10 + tests.md C1）
- [P1] M03 写 activity_log action_type=node_created / node_deleted / node_moved 等 → M15 list 召回（design §7 ActionType M03 节点）
- [P1] M11 写 activity_log action_type=cold_start_created / cold_start_completed / cold_start_failed → M15 list 召回（design §7 ActionType M11）
- [P1] M14 baseline-patch 反向回写 news_created / news_updated / news_deleted / news_linked / news_unlinked target_type=industry_news 字面通过 CheckConstraint（design §3 M14 baseline-patch + §7 ActionType M14）
- [P1] M18 baseline-patch embedding_model_upgrade_triggered / embedding_backfill_triggered 字面通过 CheckConstraint（design §3 + §7 ActionType M18 + §3.X A8）
- [P1] M20 baseline-patch team_created / team_renamed / team_deleted / team_member_added / team_member_removed / project_joined_team / project_left_team 8 类 target_type=team 字面通过 CheckConstraint（design §3 + §7 ActionType M20 + §3.X A9）
- [P1] M20 ErrorCode 8 类（TEAM_NOT_FOUND / TEAM_NAME_DUPLICATE / TEAM_HAS_PROJECTS / TEAM_OWNER_REQUIRED / TEAM_MEMBER_NOT_FOUND / TEAM_MEMBER_DUPLICATE / TEAM_PERMISSION_DENIED / CROSS_TEAM_MOVE_FORBIDDEN）注册 codes.py + AppError 子类 R13-1 配齐（design §13 + §3.X A9）
- [P2] R14 守护 / api/services/*.py 调 write_event 时 action_type 必为 _ACTION_TYPES 字面 / "create" / "update" 等裸字符串 ci-lint 拦截（design §10 R14 规则）
- [P2] ci-lint.sh R13-1 守护 ErrorCode ↔ AppError 子类 parity 通过（design §13 + 14.5 元教训 R13-1）

### 11. 演进 / 兼容

- [P0] 新增 action_type 流程 / 业务模块 §10 设计字面 → accepted 后回写 4 处（M15 model _ACTION_TYPES + schema StrEnum + Alembic CHECK + 测试 enum set）（design §10 R10-2 + R14 同步流程）
- [P1] 新增 target_type 同流程 / 4 处同步 / R10-2 owner 维护责任在 M15（design §10 R10-2）
- [P1] M15 方案 A 独立 DAO 直查（ADR-003 规则 3 豁免）→ 未来若升 ADR-003 Read Model 方案 B 仅 §3/§6/§7/§9 改回 0 Alembic 步数（design §3 ADR-003 + 改回成本 R3-4）
- [P2] M20 team_member_promoted_admin / team_member_demoted_member 命名半年回看（README 2026-10-26）评估合并 role_changed（design §7 ActionType M20 注释）

### 12. 安全

- [P0] DAO list_stream 强 project_id 过滤防 SQL 注入跨 tenant 读 / Pydantic UUID 校验拦截字符串注入（design §9 防绕过 + §7 Filter UUID）
- [P1] activity_logs.summary Text 写入方提供 / M15 仅展示 / XSS 防护由前端渲染层负责（design §1 in scope summary 字段 + §6 Component 层）
- [P1] activity_logs.metadata JSONB 由前端折叠展开 / 不直接 eval / 不 dangerouslySetInnerHTML（design §15 C-6 fallback UI）
- [P2] DB 查询超时不暴露内部 SQL / 错误响应不带 stacktrace（tests.md ER4）

### 13. 横切关注

- [P0] M15 自身不写 activity_log 事件（纯读浏览不产生审计事件 / 事务 ❌ 与 catalog 一致）（design §5 多人架构 4 维 + §10 produces_action_types=[]）
- [P0] M15 无 idempotency_key 适用操作 / 全 GET 天然幂等（design §11 + §5 清单 4）
- [P0] M15 无 Queue 任务投递 / 全同步 GET 无 Queue payload（design §12 N/A + §5 清单 3）
- [P1] M15 是 activity_logs 横切表 owner（R10-2）/ M15 负责 Alembic 迁移文件 + CheckConstraint 维护（design §3 + §10 R10-2）
- [P1] activity_logs 表本身不归属任何单一业务模块 / 横切共享表 ADR-003 规则 3 豁免（design §3 ADR-003 + §10）

### 14. 国际化 / 文案

- [P1] action_type 字符串使用过去式 snake_case 字面（如 node_created 而非 create / node.create）（design §10 R14 + §7 A1 命名规范）
- [P2] PRD 未给具体 i18n 要求 / summary 字段写入方语言由各模块决定（design 边界灰区 + tests.md ER 表）

### 15. 可观测 / 日志

- [P1] M15 list_stream 不在 activity_logs 写入"view_activity_stream"事件 / 当前不记录"谁查看了日志"审计（design §10 显式说明 + 观察项留存）
- [P2] structlog 日志记录 query params + project_id + user_id 用于慢查询排查（design §6 Service 层 + 通用日志范式）
