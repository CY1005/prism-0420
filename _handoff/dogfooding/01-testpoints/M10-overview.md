---
module: M10
name: overview
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M10-overview/00-design.md
  - design/02-modules/M10-overview/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F10 项目全景图（US-C1.1 / PRD Q3 / Q3.1）
---

# M10 项目全景图 测试点

## 业务流程（H1 / 1 行概述）

M10 是纯读聚合模块（ADR-003 规则 2 豁免 / 无自有表 / 方案 A 实时 JOIN），OverviewDAO 只读 import M02 ProjectDimensionConfig + M03 Node + M04 DimensionRecord 三个上游 model，2 个 HTTP endpoint（GET /overview / GET /overview/stats，第三个 /completion 由 M04 dimension_router 唯一注册），三层权限防御（Server Action session / Router check_project_access viewer / Service _check_project_access），folder 节点完善度走"迭代后序遍历"算子树均值（design §3 D-1），count_enabled_dimensions=0 早返回 OverviewNoDimensionsError(422)（design M10-B3）。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] GET /api/projects/{pid}/overview viewer happy path 返 200 + tree 嵌套结构 + 每 file 节点含 completion_rate（design §7 + tests.md G1）
- [P0] GET /api/projects/{pid}/overview file 节点 completion_rate = filled_count / enabled_count（启用 3 维 / 填 2 维 → 0.667）（design §1 完善度公式 + tests.md G2）
- [P0] GET /api/projects/{pid}/overview folder 节点 completion_rate = 子树 file 节点均值（子 file 1.0 + 0.5 → folder 0.75）（design §1 边界灰区 CY ack A-9 + tests.md G3）
- [P0] GET /api/projects/{pid}/overview/stats 返 OverviewStats 全字段 total_nodes/file_nodes/fully_complete_nodes/empty_nodes/avg_completion_rate/enabled_dimension_count（design §7 OverviewStats + tests.md G5）
- [P1] GET /overview 返回 NodeOverview.children 嵌套树结构由 Service 层从 DAO flat list 内存组装（design §7 说明）
- [P1] GET /overview/stats avg_completion_rate 仅按 file 节点均值不含 folder（design §7 OverviewStats + tests.md G5）
- [P1] GET /overview/stats fully_complete_nodes 计数 completion_rate=1.0 的 file 节点数（design §7 OverviewStats）
- [P1] GET /overview/stats empty_nodes 计数 completion_rate=0.0 的 file 节点数（design §7 OverviewStats）
- [P1] GET /overview 节点排序按 depth + sort_order ASC（design §3 DAO order_by line 225）
- [P1] GET /overview 节点 path 字段透传 M03 nodes.path 原值（design §3 list_nodes_with_fill_count line 213）

### 2. 边界 / 状态机

- [P0] 空项目（无节点）GET /overview 返 200 + tree=[] + stats.total_nodes=0 + avg_completion_rate=0.0（tests.md E1）
- [P0] 项目启用维度 0 个 GET /overview 返 422 OVERVIEW_NO_DIMENSIONS 不进入节点聚合查询（design M10-B3 早返回 + tests.md E2）
- [P0] file 节点未填任何维度 completion_rate=0.0 正常返回不报错（tests.md G6）
- [P0] N file 节点全填满 stats.fully_complete_nodes=N + avg_completion_rate=1.0（tests.md E4）
- [P1] 树全是 folder 无 file 时 stats.file_nodes=0 + avg_completion_rate=0.0 + folder.completion_rate=0.0（tests.md E3）
- [P1] M10 显式声明无状态实体 / 完善度数值不持久化为状态由查询实时计算（design §4 R4-1）
- [P1] depth > 5 深层嵌套树 GET /overview 返 200 + tree 嵌套正确 + 性能 < 2s（tests.md E7）
- [P1] folder 均值"迭代后序遍历"算法 depth=20 不栈溢出（design §3 D-1 迭代非递归 + Python 默认递归栈 1000）
- [P2] 节点数极大（>1000）NodeOverview.children 嵌套组装无性能退化（design §7 说明潜在优化点）

### 3. 异常 / 错误

- [P0] GET /api/projects/{不存在 pid}/overview 返 404 OVERVIEW_PROJECT_NOT_FOUND（design §13 + tests.md E6 + tests.md ER1）
- [P0] GET /api/projects/{pid}/overview project_dimension_configs 全 enabled=false 返 422 OVERVIEW_NO_DIMENSIONS（design §13 + tests.md E2 + ER3）
- [P0] 错误响应体格式 {"error":{"code":"overview_no_dimensions","message":"Project has no enabled dimensions configured"}}（design §13 + tests.md ER3）
- [P0] 错误响应体格式 {"error":{"code":"overview_project_not_found","message":"Project not found or access denied"}}（design §13 + tests.md ER1）
- [P1] project_id 路径非 UUID 格式返 422（FastAPI path param 自动校验）
- [P1] DB 超时（大项目节点数）返 502/504 不暴露内部 SQL（tests.md ER4）
- [P1] OverviewDAO 执行任何 INSERT/UPDATE/DELETE 触发 ADR-003 规则 2 豁免边界违反 / CI 守护拦截（design §3 OverviewDAO 豁免注释 + §6 禁止条款）

### 4. 权限 / Auth

- [P0] 未登录调 GET /overview 返 401 UNAUTHENTICATED Server Action 层拦（design §8 + tests.md P1）
- [P0] viewer 角色调 GET /overview 返 200 全景图 viewer 权限即可（design §8 Router check_project_access role="viewer" + tests.md P2）
- [P0] 非项目成员（无角色）调 GET /overview 返 403 PERMISSION_DENIED Router 拦（design §8 + tests.md T2）
- [P1] session 过期调 GET /overview 返 401 TOKEN_EXPIRED Server Action 层拦（tests.md P3）
- [P1] Service 层 _check_project_access 二次校验 project_id 真实存在且用户真实有成员资格（design §8 Service 层）
- [P1] 异步路径声明 M10 无异步无 Queue 消费者侧权限 / 三层即足够（design §8）

### 5. Tenant 隔离

- [P0] userA 持 projectA token 调 GET /api/projects/{projectB_id}/overview 返 403 PERMISSION_DENIED（Router check_project_access 拦 + tests.md T1）
- [P0] userC 不在 projectA 成员表调 GET projectA overview 返 403/404 不暴露存在性（Service _check_project_access 拦 + tests.md T2）
- [P0] OverviewDAO.list_nodes_with_fill_count(db, other_project_id) 返空 list / nodes.project_id 过滤生效（design §9 + tests.md T3）
- [P0] OverviewDAO dimension_records LEFT JOIN 含 project_id 过滤 / 不混入其他 project 的 dimension_records（design §3 line 220 + tests.md T4）
- [P0] OverviewDAO.count_enabled_dimensions 仅计目标 project 的 project_dimension_configs / 不混入其他 project（design §9 + tests.md T5）
- [P1] OverviewDAO 所有方法签名强制 project_id 入参 / DAO 内部不从外部推断 project_id（design §9 防绕过纪律）
- [P1] M10 所有上游表 SELECT 强制 WHERE project_id 过滤 / 豁免清单空（design §9 三表过滤规则）

### 6. 并发 / 乐观锁

- [P1] M10 显式声明无并发写冲突场景 / 纯读多用户同时 GET overview 结果一致（design §5 4 维必答 + tests.md §3）
- [P1] 读-写并发（M04 更新 dimension_records 同时 M10 读）M10 返查询时刻快照不需锁 / PG READ COMMITTED 正常工作（tests.md §3 读-写并发）
- [P2] M04 更新某 file 节点新增第 N 维度后立即 GET overview / filled_count 已含新更新（方案 A 实时 JOIN 无缓存延迟 + tests.md C1 读一致性）
- [P2] count_enabled_dimensions 与 list_nodes_with_fill_count 两次查询在同一 DB session 内执行 / 接受短窗口（几毫秒级）不一致（design §3 line 202-204 docstring）

### 7. 数据完整性

- [P0] OverviewDAO 只读 import M02/M03/M04 上游 model 禁止 INSERT/UPDATE/DELETE（ADR-003 规则 2 豁免边界 + design §3 注释 + §6 禁止条款）
- [P0] M10 无 Alembic 迁移 / 不新增表（design §3 Alembic 要点 + R3-5 纯读聚合规范）
- [P0] dimension_records LEFT JOIN ON 条件 (node_id = Node.id AND project_id=:pid) 双 tenant 过滤（design §3 list_nodes_with_fill_count line 217-220）
- [P0] count_enabled_dimensions 仅计 enabled=True 的 ProjectDimensionConfig（design §3 line 189-192）
- [P1] M10 无 activity_log 事件 / 纯读豁免清单 1（design §10）
- [P1] M10 无 idempotency_key / 全 GET 天然幂等（design §11）
- [P1] M10 无 Queue 任务 / 显式 N/A（design §12）
- [P1] 节点 filled_count 来自 LEFT JOIN COUNT(DimensionRecord.id) / 无 dimension_record 节点返 0 而非 null（design §3 outerjoin + tests.md G6）

### 8. UI / UX

- [P0] 完善度色块阈值 completion_rate < 0.3 红色（CY ack C-4 候选 A + design §7 COMPLETION_THRESHOLDS）
- [P0] 完善度色块阈值 0.3 ≤ completion_rate ≤ 0.7 黄色（CY ack C-4 + design §7）
- [P0] 完善度色块阈值 completion_rate > 0.7 绿色（CY ack C-4 + design §7）
- [P1] 全景图 SSR 渲染 /project/:id 路径（design §6 Page 层 + PRD Q3.1）
- [P1] folder 节点 UI 可展开/折叠（design §6 Component 层 overview-tree.tsx）
- [P1] file 节点显示自身 completion_rate / folder 节点显示子树均值（design §1 边界灰区 + §7 NodeOverview.completion_rate 语义）
- [P2] 色块颜色映射逻辑覆盖单元测（red/yellow/green 三档边界 0.3 / 0.7 临界）（design §6 覆盖率目标 70% Component 层）
- [P2] 空树（无节点项目）UI 渲染空状态文案 / 不报错（tests.md E1 + design §6 Component 70% 覆盖）

### 9. 性能

- [P1] OverviewDAO.list_nodes_with_fill_count 单条 SQL（nodes LEFT JOIN dimension_records GROUP BY node_id）/ 无 N+1（design §3 docstring line 200-201）
- [P1] folder 均值迭代后序遍历用 collections.deque 从叶节点向根逐级 / 或按 node.path 前缀排序（design §3 D-1）
- [P2] 项目 > 100 节点 GET /overview p95 < 2s（tests.md E7 + 规约性能验收）
- [P2] OverviewStatsResponse 轻量接口比 OverviewResponse 响应更快（design §7 stats endpoint 设计意图）

### 10. 跨模块契约（M10 是消费者）

- [P0] OverviewDAO 只读 import M02 ProjectDimensionConfig / M03 Node / M04 DimensionRecord 三个 model（design §3 ADR-003 规则 2 豁免 + frontmatter cross_module_reads）
- [P0] /api/projects/{pid}/nodes/{nid}/completion endpoint 由 M04 dimension_router 唯一注册 / M10 router 不实装（design §7 sprint 关闸 disambiguation 2026-05-08）
- [P1] M10 router 仅实装 2 endpoints（/overview + /overview/stats）/ NodeCompletionResponse schema 保留作未来 M04 委托可用（design §7 disambiguation）
- [P1] M10 service.get_node_completion 是 folder 均值算法的内部接口 / 不暴露 HTTP（design §7 disambiguation）
- [P1] M10 produces_action_types=[] / 不产生任何 activity_log 事件（design frontmatter）
- [P1] M10 consumes_action_types=[] / 非 M15 不订阅 action_type（design frontmatter）

### 11. ErrorCode / 错误响应规范

- [P0] OVERVIEW_PROJECT_NOT_FOUND 错误 http_status=404 / 响应体 code=overview_project_not_found（design §13 OverviewProjectNotFoundError + tests.md ER1）
- [P0] OVERVIEW_NODE_NOT_FOUND 错误 http_status=404 / 响应体 code=overview_node_not_found（design §13 OverviewNodeNotFoundError + tests.md ER2）
- [P0] OVERVIEW_NO_DIMENSIONS 错误 http_status=422 / 响应体 code=overview_no_dimensions（design §13 OverviewNoDimensionsError + tests.md ER3）
- [P1] ErrorCode 枚举 3 条 == AppError 子类定义 3 个（design §13 R13-1 + frontmatter codes_added）
- [P1] PERMISSION_DENIED / UNAUTHENTICATED 复用 errors v3 helper（design frontmatter codes_used）

### 12. 设计漂移 / CI 守护

- [P1] OverviewDAO 全部查询带 tenant 过滤 / CI 扫描无裸 SELECT 缺 project_id（design §9 + design-principles 清单 5）
- [P1] OverviewDAO 文件顶部含 ADR-003 规则 2 豁免注释 / 禁止 INSERT/UPDATE/DELETE 范式（design §3 line 165）
- [P1] Pydantic NodeOverview.model_rebuild() 自引用模型必须调用 / 否则运行时 PydanticUserError（design §7 line 359）
- [P1] M10 无自有 SQLAlchemy model 文件 / R3-5 纯读聚合规范（design frontmatter mixins=no_dependency + §15 checklist）
- [P2] folder 均值算法（rate 算法）严守迭代非递归 / _build_tree 树排序 _sort 函数仍用递归（CY ack 2026-05-08 disambiguation 作用域不同）（design §3 line 245-249）
