# 模块详细设计（C 档）

按 16 字段模板逐模块设计——pilot 验证模板可复用性，再批量填其他模块。

---

## 模块清单

| 顺序 | 模块 | 状态 | 路径 |
|------|------|------|------|
| **Pilot 1** | M04 功能项档案页（同步基线） | **accepted（2026-04-21）** | [`M04-feature-archive/`](./M04-feature-archive/) |
| 第一批 | M05 版本时间线 | **accepted（2026-04-21）** | [`M05-version-timeline/`](./M05-version-timeline/) |
| 第一批 | M06 竞品参考 | **accepted（2026-04-21）** | [`M06-competitor/`](./M06-competitor/) |
| 第一批 | M07 问题沉淀 | **accepted（2026-04-21）** | [`M07-issue/`](./M07-issue/) |
| 第一批 | M14 行业动态 | **accepted（2026-04-21）** | [`M14-industry-news/`](./M14-industry-news/) |
| 第一批 | M19 导入/导出 | **accepted（2026-04-21）** | [`M19-import-export/`](./M19-import-export/) |
| **Pilot 2** | M17 AI 智能导入（异步基线 / Queue + WebSocket） | **accepted（2026-04-21）** | [`M17-ai-import/`](./M17-ai-import/) |
| 第二批 | M02 项目管理 | **accepted（2026-04-21）** | [`M02-project/`](./M02-project/) |
| 第二批 | M03 功能模块树 | **accepted（2026-04-21）** | [`M03-module-tree/`](./M03-module-tree/) |
| 第二批 | M11 冷启动支持 | **accepted（2026-04-21）** | [`M11-cold-start/`](./M11-cold-start/) |
| 第二批 | M12 对比矩阵 | **accepted（2026-04-21）** | [`M12-comparison/`](./M12-comparison/) |
| 第三批 A1 | M08 模块关系图 | **accepted（2026-04-21）** | [`M08-module-relation/`](./M08-module-relation/) |
| 第三批 A1 | M09 全局搜索 | **accepted（2026-04-21）** | [`M09-search/`](./M09-search/) |
| 第三批 A1 | M10 项目全景图 | **accepted（2026-04-21）** | [`M10-overview/`](./M10-overview/) |
| 第三批 A1 | M15 数据流转可视化 | **accepted（2026-04-21）** | [`M15-activity-stream/`](./M15-activity-stream/) |
| **Pilot 3** | M01 用户账号（**auth pilot**）| **accepted（2026-04-24）** | [`M01-user-account/`](./M01-user-account/) |
| **Pilot 4** | M13 需求分析（**流式 SSE pilot**）| **accepted（2026-04-25）** | [`M13-requirement-analysis/`](./M13-requirement-analysis/) |
| **Pilot 5** | M16 AI 快照（**后台 fire-and-forget pilot**）| **accepted（2026-04-25）** | [`M16-ai-snapshot/`](./M16-ai-snapshot/) |
| **Pilot 6** | M18 语义搜索（🗂️ §12D embedding 持久化 pilot） | **draft（2026-04-25 brainstorming + 三轮 audit + fix v1 完成，待 verify）** | [`M18-semantic-search/`](./M18-semantic-search/) |
| 扩展 | M20 团队/空间（多 space 扩展）| 待开 | — |

**Pilot 范本**（新模块设计前必读）：
- 同步模块 → `M04-feature-archive/00-design.md`
- 异步 Queue 模块 → `M17-ai-import/00-design.md`
- **流式 SSE 模块** → `M13-requirement-analysis/00-design.md`（§12A 流式子模板定稿；**仅服务 🌊 场景**，不跨形态复用）
- **Auth 横切源头模块** → `M01-user-account/00-design.md` + [`ADR-004`](../adr/ADR-004-auth-cross-cutting.md)（"实现最简 + schema 都支持"模式 / 独立审计表 R10-2 例外）
- **后台 fire-and-forget 模块** → `M16-ai-snapshot/00-design.md`（§12B 子模板定稿）
- **embedding/索引持久化模块** → `M18-semantic-search/00-design.md`（§12D 子模板 draft；双触发链 + 失败容忍 + 模型版本回填 + 跨模读双路豁免）

**§12D 半年回看触发器**（2026-10-25）：M18 accept 后半年评估——若 §12D 仅 M18 一个实例使用、且字段⑥/⑦与 §12C 高度重合，**降级为 §12C 扩展段落 + 删 §12D 行**（防模板膨胀）。**记录方式**：见本 README 末尾「设计回看触发器」清单（手动审查，不挂自动 cron）。

**Audit 报告归档**：
- 第一批：[`audit-report-batch1.md`](./audit-report-batch1.md) + [`audit-report-batch1-verify.md`](./audit-report-batch1-verify.md)
- 第二批：[`audit-report-batch2.md`](./audit-report-batch2.md) + [`audit-report-batch2-verify.md`](./audit-report-batch2-verify.md)
- 第三批 A1：[`audit-report-batch3.md`](./audit-report-batch3.md) + [`audit-report-batch3-verify.md`](./audit-report-batch3-verify.md)
- M17 pilot：[`M17-ai-import/audit-report.md`](./M17-ai-import/audit-report.md)
- M13 pilot：[`M13-requirement-analysis/audit-report.md`](./M13-requirement-analysis/audit-report.md) + [`audit-verify.md`](./M13-requirement-analysis/audit-verify.md)

完整能力定位见 [`../00-architecture/07-capability-matrix.md`](../00-architecture/07-capability-matrix.md)。

---

## 16 字段模板（每个模块产出）

每个模块目录最少包含 `00-design.md`（节 0-13 + 15）+ `tests.md`（节 14）。

| # | 节 | 性质 | 强制项 |
|---|----|------|--------|
| 0 | frontmatter | 强制（规约 11.3）| 12 字段标准（见下） |
| 1 | 业务说明 + 职责边界（in / out scope） | 业务 | **必须引 PRD/US 编号** |
| 2 | 依赖模块图（M? → M?） | 半机械 | mermaid flowchart |
| 3 | 数据模型（SQLAlchemy + Alembic） | 业务核心 | **必含 SQLAlchemy class 代码块**（不只 ER 图）+ **状态字段必用 `Mapped[StatusEnum]`**（不能裸 `Mapped[str]`，audit 教训） |
| 4 | 状态机（无状态显式声明） | 业务 | 无状态实体也要显式说明 + **禁止转换至少列 N 条**（N = 终态数 + 1，audit 教训） |
| 5 | 多人架构 4 维必答 | 半机械（按 catalog） | 5 项清单逐项标 + **有状态机时增"状态转换竞态分析"行** |
| 6 | 分层职责表 | 机械（按 04-layer） | 每层文件路径具体 |
| 7 | API 契约（Pydantic + OpenAPI） | 半机械 | endpoints 表 + Pydantic schema 草案 + **Queue payload 用强类型**（不能裸 `dict`） |
| 8 | 权限三层防御点 | 机械（按 04-layer Q4） | 含异步路径声明 + **🗂️ Queue 模块强制增"Queue 消费者侧权限"行 + WebSocket 模块加"每命令重校"行**（audit 教训，引 [`adr/ADR-002`](../adr/ADR-002-queue-consumer-tenant-permission.md)） |
| 9 | DAO tenant 过滤策略 | 机械（按清单 5） | 豁免清单显式（无则写"无"） |
| 10 | activity_log 事件清单 | 业务 | action_type / target_type / metadata 三列表格 |
| 11 | idempotency_key 适用清单 | 业务 | 不需要也要显式声明 + **必答"project_id 是否参与 key 计算"**（audit 教训） |
| 12 | Queue payload schema | 按异步形态分支 | 见下方 §12 异步形态分支表 |
| 13 | ErrorCode 新增清单 | 半机械 | + AppError 子类草案（**每个 ErrorCode 必有对应子类**，audit 教训） |
| 14 | 测试场景（独立 tests.md） | 业务 | 6 类：Golden/边界/并发/Tenant/权限/错误 |
| 15 | 完成度判定 checklist | 机械 | **含三轮 reviewer audit 强制勾选** |

---

## frontmatter 12 字段标准（CI 可静态扫描）

```yaml
---
title: M{NN} 模块名 - 详细设计       # 必填
status: draft                           # 必填：draft / accepted / superseded / deprecated
owner: CY                               # 必填
created: YYYY-MM-DD                     # 必填
accepted: null                          # 必填：null 或 YYYY-MM-DD
supersedes: []                          # 必填：[] 或 [ADR-NNN]
superseded_by: null                     # 必填：null 或 ADR-NNN
last_reviewed_at: null                  # 必填：null 或 YYYY-MM-DD（最近 reviewer audit 时间）
module_id: M{NN}                        # 必填：M01-M20
prism_ref: F{N}                         # 必填：对应 Prism F1-F20
pilot: false                            # 必填 boolean：是否 pilot 模板
complexity: low                         # 必填：low / medium / high（来自 catalog 颜色）
---
```

---

## §12 Queue payload schema 异步形态分支（M17 pilot 沉淀）

按 catalog 4 维"异步"标注的 emoji 选对应子模板：

| 异步形态 | catalog emoji | §12 子模板 | 范本 | 关键产出 |
|---------|--------------|-----------|------|----------|
| **同步** | — | §12 显式 N/A | M04 | 写"本模块不投递 Queue 任务" |
| **流式（SSE）** | 🌊 | §12A 流式 schema | **定稿（M13 accepted 2026-04-25）** | 7 字段：①端点路径 ②SSE event 类型 ③data payload schema ④鉴权路径（ADR-004 P1）⑤超时策略 ⑥取消机制（AbortController + is_disconnected + aclose）⑦断线重连（不支持续传）**仅服务 🌊 场景，字段语义不跨 3 形态通用** |
| **后台异步**（fire-and-forget）| 🪷 | §12B 后台任务 schema | **定稿（M16 accepted 2026-04-25）** | 7 字段：①任务表 schema（核心字段）②任务状态机 ③创建+查询 endpoint 风格（创建嵌套+查询独立）④鉴权路径（ADR-004 P1+P2 + 独立 GET 反查）⑤超时策略（asyncio.timeout 600s）⑥失败/重试策略（不重试+手动重发）⑦清理+zombie 兜底（CAS UPDATE，cron 频率 ≤ 阈值/2）**字段位次与 §12A/§12C 不语义对等，照抄须按 emoji 选模板**。详见 [M16-ai-snapshot/00-design.md §12](./M16-ai-snapshot/00-design.md) |
| **Queue 异步**（持久化 + 重试）| 🗂️ | §12C **Queue payload schema**（M17 范式）| **M17** | TaskPayload 基类（强制 user_id + project_id）+ 任务清单 + 重试策略 + 死信处理 |
| **embedding/索引持久化**（派生数据 + 双触发链）| 🗂️ (embedding 子类) | §12D **embedding 持久化 schema**（M18 范式）| **draft（M18 brainstorming 2026-04-25）** | 7 字段：①双触发链（增量+backfill）+ Payload schema ②embeddings 表 + model_version + content_hash ③跨模读双路豁免（规则 1 + 规则 4）④鉴权路径（无用户端 endpoint，admin only）⑤超时（单 task 60s + batch 15min + query 2s）⑥失败容忍 + monitor cron（**不通知用户**——核心区别于 §12C 死信通知）⑦模型升级回填路径 + zombie + 90 天清理。**字段位次与 §12C 不语义对等**——核心区别：双触发链 / 失败容忍 / 必有 model_version 回填 / 跨模读双路。详见 [M18-semantic-search/00-design.md §12](./M18-semantic-search/00-design.md) |

**M17 §12C 范式核心**（所有 Queue 模块照抄）：
1. 定义模块 `TaskPayload` 基类继承 `api/queue/base.py:TaskPayload`（强制 user_id + project_id）
2. 每个 Queue task 一个 Pydantic Payload class（不能裸 dict）
3. Queue 消费者入口 3 步：① `payload = MyPayload.parse_obj(raw)` ② `service.check_access(payload.user_id, payload.project_id, payload.task_id)` ③ 业务逻辑
4. 重试策略：3 次指数退避（1s / 4s / 16s）
5. 死信：失败 3 次后标 `status=failed` + `error_metadata.dead_letter=true` + 通知用户 + 30 天保留

---

## 模板硬规则（按节编号组织）

> 由两轮 audit 实战提炼——违反任一项 = reviewer 阻塞 accept。

### §0 frontmatter
- **R0-1**：12 字段固定，缺字段或多字段不通过

### §3 数据模型
- **R3-1**：必含 SQLAlchemy class 代码块（ER 图 + class 二者皆有，单独 ER 图不通过）
- **R3-2**：状态字段**三重防护**合规（CY 2026-04-21 ack，batch2 audit 沉淀）：
  1. Python 类型注解：`Mapped[StatusEnum]`（不能裸 `Mapped[str]`）
  2. SA 列类型：`mapped_column(String(N) / Text, ...)` 或 `mapped_column(SAEnum(StatusEnum, name="..."), ...)` 二选一
  3. **`CheckConstraint` 枚举值显式列出**（无论选 String 还是 SAEnum，CHECK 都必须有）
  - 现状选型：4 模块 + M17 pilot 统一用 `String(N) + CheckConstraint`，**不**升级 SAEnum（避免 PG TYPE 迁移 + pilot 改动）；审计时满足三重即合规
- **R3-3**：tenant 字段（project_id）冗余在 SQLAlchemy class 上（统一规则，便于 DAO 过滤）
- **R3-4**（新增）：**核心设计决策必须有"候选 B 改回成本"块**——对于有 ⚠️ 核心决策（如 M12 快照存引用 vs 值、M11 持久化 vs 无持久化）的模块，§3 或专属决策块内必须量化给出：
  - Alembic 迁移步数（新增/删除表、改字段）
  - 新增/删除表数
  - 受影响模块数（需要联动改动的其他 M 模块）
  - 数据迁移不可逆性（是否丢历史数据）
- **R3-5**（新增，batch3 audit 沉淀）：**纯读聚合模块 §3 规范**——R3-1 原适用于"有主表"模块，纯读聚合模块（无自有实体表）豁免 SQLAlchemy class 要求，但 §3 必须显式包含：
  1. 首段声明"本模块无自有实体表，§3 适用纯读聚合规范（R3-5，引 [`adr/ADR-003`](../adr/ADR-003-cross-module-read-strategy.md)）"
  2. **上游依赖表清单**（表名 / 归属模块 / 访问方式：`Service 接口调用 / 只读 model import / 横切表直查`，三选一对应 ADR-003 规则 1/2/3）
  3. **DAO 草案代码块**（含 tenant 过滤模式 + 豁免规则引用注释）
  4. **Pydantic 聚合结构**显式标注"无 SQLAlchemy model（本模块是纯读聚合）"
  5. 若有核心决策（如 M10 folder 均值规则），候选 B 改回成本块仍适用（R3-4 照常）
  - §15 checklist 第 3 行改为"§3：无自有表声明 + 上游清单 + DAO 草案 + ADR-003 规则 X 引用"，**不得**误勾"SQLAlchemy class 满足 R3-1"
  - 适用模块：M09 / M10 / M15 / M18（待设计）/ 未来聚合读模块

### §4 状态机
- **R4-1**：无状态实体也要显式声明
- **R4-2**：禁止转换至少列 N 条（N = 终态数 + 1）+ **每条格式必须是 "状态A → 状态B：原因 + 对应 ErrorCode"**（batch2 audit 沉淀）
  - **禁止合并写法**：`X / Y → 任意`（两个终态合并算 1 条，不满足 N 数量要求）
  - 每个终态单独一条：`completed → 任意 状态`、`failed → 任意 状态`、`cancelled → 任意 状态` 必须分开写
  - 禁止把"并发控制 version 冲突"、"删后 404"等非状态转换混入（应放在节 5 竞态分析或节 13 ErrorCode）
- **R4-3**：mermaid stateDiagram-v2 必须画

### §5 多人架构 4 维必答
- **R5-1**：5 项清单逐项标（即使 N/A 也要显式说明）+ **4 维表格禁止 ⚠️ 占位**（batch2 audit 沉淀）
  - 4 维（Tenant / 事务 / 异步 / 并发）表格中必须给出 AI 默认值 + 候选说明
  - ⚠️ 只能出现在 §15 "待 CY 裁决项"汇总表中
  - 反例：M03 原稿 §5 多表事务列写 "⚠️ 待裁决"——违反本规则
- **R5-2**：有状态机时必答"状态转换竞态分析"行（防自圆其说）

### §7 API 契约
- **R7-1**：Pydantic schema 强类型（不能裸 `dict`，必须 `dict[str, Any]` 或具体 BaseModel）
- **R7-2**：枚举字段用 Enum class（不能裸 `str` / `int`）
- **R7-3**：Queue payload 必须 `Literal[...]` 限定取值（如 step 必须 `Literal[1, 2, 3]`）

### §8 权限三层
- **R8-1**：所有模块 3 层（Server Action / Router / Service）+ 异步路径声明
- **R8-2**：🗂️ Queue 模块强制增第 4 行"Queue 消费者侧权限"（参 [`adr/ADR-002`](../adr/ADR-002-queue-consumer-tenant-permission.md)）
- **R8-3**：含 WebSocket 模块强制增第 5 行"每命令重校 task_id 归属"（防同连接绕过）

### §10 activity_log 事件（batch3 audit 沉淀）
- **R10-1**：**批量操作写 N 条独立事件，禁止汇总**——涉及批量的操作（`delete_by_node_id` / `batch_create_in_transaction` / 批量导入批量 move 等），每个被影响实体写**一条独立 activity_log 事件**（target_id 独立），不得汇总为单条"批量操作 N 个实体"事件
  - 理由：M15 数据流转以"操作时间线"为核心价值，细粒度可审计（用户可按 target_id/target_type 精确搜到每条变更）；刷屏问题由 M15 UI 折叠分组解决，不牺牲可追溯性
  - 反例：M03 删节点时若 M08 级联删 20 条关联只写 1 条汇总日志 `"deleted 20 relations"`——违反本规则；正确做法是写 20 条独立 `delete` 事件（每条 target_id=relation_id）+ 1 条节点删除事件
  - 适用：所有批量写操作模块（M02/M03/M08/M11/M17 等）
- **R10-2**：**`activity_log` 横切表由 M15 own**——M15 是 activity_log model / schema / Alembic 迁移的 owner
  - 新 action_type / target_type 扩增流程：
    1. 业务模块在自身 §10 设计新 action_type/target_type 字符串
    2. 模块 accepted 后**回写 M15 的 `ActionType` / `TargetType` 枚举**（M15 schema 统一维护）
    3. 同步发起 Alembic 迁移（若 CHECK constraint 启用则需更新）
  - 新模块 tests.md 验证清单：确保自己写的 action_type 已在 M15 schema 中登记
  - 反例：M17 / M13 各自独立写 schema 扩枚举导致合并冲突或前端展示"未知操作"
- **R10-2 例外**（M01 auth pilot 沉淀 2026-04-24）：**横切专用审计表由归属模块自身 own**，不强制归 M15
  - 当前唯一适用例外：`auth_audit_log`（M01 own）
  - **适用条件**（全部满足）：
    1. 该表仅服务单一模块的审计职责（M01 auth 事件）
    2. 事件高频（100+/用户/天级别）进 M15 activity_log 会淹没业务时间线
    3. 事件无 `project_id` 归属（系统级 / 跨项目事件）
  - 采用此例外的模块 §10 必须**显式引用本例外条目**并说明三个适用条件各自满足情况
  - 不适用例外的模块仍走 R10-2 主规则（回写 M15 schema）
  - 跨表查询预案（若出现"查某用户全系统操作"场景）：模块 §10 给 PG view 或 UNION ALL 候选，参 [`M01-user-account/00-design.md`](./M01-user-account/00-design.md) §10 末段

### §11 idempotency_key
- **R11-1**：不需要也要显式声明
- **R11-2**：**必答"project_id 是否参与 key 计算"**——M17 教训：原稿用 `(user_id, source_hash)` 跨项目命中导致租户污染，audit 抓出后改为 `(user_id, project_id, source_hash)`
- **R11-3**：tenant 资源的 idempotency key **必含 project_id**（除非显式说明为何不参与）

### §13 ErrorCode
- **R13-1**：每个 ErrorCode 必有对应 AppError 子类（M17 教训：3 个 ErrorCode 缺子类）
- **R13-2**：跨模块调用产生的错误，本模块 wrap 为自己的 ErrorCode（不直接 raise 其他模块的 Error）

### §14 tests.md
- **R14-1**：tests.md 写完时所有决策已定，**禁止 ⚠️ 渗漏**

### §15 完成度
- **R15-1**：含三轮 reviewer audit 强制勾选（每模块都要勾完三轮 + CY 复审才能 accept）

### 横切
- **R-X1**：M17 的"M17 不直 INSERT 跨模块表"原则——orchestrator 模块通过其他模块 Service.batch_create_in_transaction 调用，不直查/直写其他模块的表（M17 教训：原稿直写 nodes/dimension_records 等违反分层）
- **R-X2**（新增，batch2 audit 沉淀）：**DB CASCADE 不触发下游 activity_log**
  - 若本模块被其他模块 FK 引用且设为 `ON DELETE CASCADE`（如 M03 nodes 被 M04/M06/M07 引用），**本模块删除时必须在 Service 层显式调用下游 Service.delete_by_xxx** 以写入下游 activity_log，DB CASCADE 仅作兜底
  - 反例：M03 若只靠 DB CASCADE 删除节点，M04 dimension_records 删除不写 activity_log——违反清单 1（所有变更操作必须写 activity_log）
- **R-X3**（新增，batch3 audit 沉淀）：**级联删除必须共享外部 db session**——R-X2 要求 Service 显式调下游 `delete_by_xxx`，R-X3 进一步约束跨模块事务原子性
  - 下游模块的 `delete_by_xxx` / `batch_create_in_transaction` 等被跨模块调用的 Service 方法**必须接受外部 `db: Session` 参数**，不得自己 `self.db.begin()` 另开事务
  - 上游发起方（如 M03 删节点）用 `with self.db.begin():` 包住整个流程，所有下游调用共享该 session
  - 反例：M03 删节点时 M08 `delete_by_node_id` 自己开新事务——若 M08 成功但 M03 失败回滚，M08 的删除和 activity_log 已提交，产生"关联没了但节点还在"的半删状态
  - **Service 接口签名规范**：
    ```python
    # ✅ 接受外部 session
    def delete_by_node_id(self, db: Session, node_id: UUID, project_id: UUID) -> int:
        # 不调 self.db.begin()，直接用入参 db
        ...

    # ❌ 反例：自开事务
    def delete_by_node_id(self, node_id: UUID, project_id: UUID) -> int:
        with self.db.begin():    # 违反 R-X3
            ...
    ```
  - 适用：所有"可能被跨模块调用"的 Service 方法（M03/M04/M06/M07/M08/M11/M17 的 batch/delete_by 方法等）
- **R-X4**（新增，batch3 audit 沉淀）：**聚合读模块必须引 ADR-003**——新增聚合读模块（无自有表 / 跨多模块读）的 §3 必须显式声明适用 [`ADR-003`](../adr/ADR-003-cross-module-read-strategy.md) 的哪条规则（规则 1 上游 Service 接口 / 规则 2 只读 import 豁免 / 规则 3 横切表豁免），禁止默认走"DAO 直 JOIN 业务表"（候选 C 已否决）

---

## ✅ 基线补丁（已 accepted 模块回扫，2026-04-24 完成）

> batch3 沉淀的 R3-5 / R10-1 / R-X3 / R-X4 新规则 + ADR-003 回扫已完成。报告：[`baseline-patch-batch3.md`](./baseline-patch-batch3.md)（15 发现 / 6 决策 / accepted 2026-04-24）。
> 改动范围：M02/M03/M04(pilot 破例)/M06/M07/M12/M15 schema。核心决策：M12 改走 M04 Service 接口（不扩 ADR-003 规则 2）；M07 改名 `orphan_by_node_id`（对齐 SET NULL 语义）；M15 ActionType +22 / TargetType +4，移除 `relation`。

### 扫描清单

| 已 accepted 模块 | 扫描项 | 触发规则 | 预判 |
|----------------|-------|---------|------|
| M02 项目 | 批量操作 activity_log 颗粒度（批量成员邀请 / 项目归档级联）| R10-1 | 可能已合规，需核对 |
| M03 模块树 | `move_subtree` / `batch_create` / `delete_node` 是否 N 条独立事件 + 是否接受外部 session | R10-1 / R-X3 | **高概率**需改：`delete_node` 连带删 M04/M06/M07 目前未明确外部 session |
| M04 档案页 | Service 方法是否接受外部 db session（M17 orchestrator 调用场景）| R-X3 | **高概率**需改 |
| M06 竞品 / M07 问题 | 被 M03 级联删除时是否共享 session + N 条独立事件 | R10-1 / R-X3 | **高概率**需改 |
| M11 冷启动 | CSV 批量导入 activity_log 颗粒度 | R10-1 | 需核对 |
| M12 对比矩阵 | `bulk_insert_items` 是否写 N 条独立事件 vs 1 条汇总 | R10-1 | 当前 audit 显示 "items_count" 汇总——需改为 N 条独立 |
| M17 AI 导入 | 批量入库各 Service 是否接受外部 session（已 pilot 确认） + 批量 activity_log 颗粒度 | R-X3 / R10-1 | M17 已对外 session；颗粒度需核对 |
| **所有已 accepted 模块** | action_type / target_type 枚举是否回写 M15 schema | R10-2 | M15 设计定稿后集中回写 |

### 执行时机

- **不纳入本轮（batch3 A1）**——避免污染第三批流水线节奏
- 候选时机 1：batch3 A1 全部 accepted 后、A2（M01 pilot）启动前执行（推荐）
- 候选时机 2：batch4 开始时前置扫描
- 产出：`design/02-modules/baseline-patch-batch3.md`（记录各模块改动点 + 改回确认）

### 关联

- ADR-003 引用方清单含"基线补丁 TODO"
- batch3 audit 报告 T4 / T5 提出本补丁需求

---

## 设计流程（每模块）

### 同步模块（M04 范本）：CY 在场对话推进
```
CY 出业务理解（节 1 + 节 3 数据语义 + 节 4 状态语义）
       ↓
AI 出 16 字段初稿（机械节定稿，业务节给候选）
       ↓
CY 逐节裁决「待 CY 裁决」项 + 复审
       ↓
独立 reviewer Agent 三轮 audit
       ↓
CY 标 status: accepted（节 15 全勾过 + last_reviewed_at 填日期）
       ↓
对照 Prism 现状 → 99-comparison/ 报告
```

### 异步模块（M17 范本）：CY brainstorming + Agent 流水线
```
CY brainstorming（5-7 个核心 Q，CY 一次答完）
       ↓
主对话出 16 节初稿（含 §12C Queue payload）
       ↓
独立 reviewer Agent 三轮 audit（重点：§8 异步权限、§11 跨租户、§12 Queue 设计）
       ↓
主对话精修 blocker
       ↓
CY ack → status=accepted
```

### 批量模块（第一批 5 模块范本）：powerskill 4 段流水线
```
Generate（implementer Agent 并行）→ Audit r1（reviewer Agent 三轮）
  → Fix v1（机械修复）→ CY ack 8 组决策（按"统一规则"压缩）
  → Fix v2（决策落地）→ Verify r3（独立审 fix 撒谎）
  → 主对话精修 blocker → status=accepted
```

详见方法论：[`/root/cy/ai-quality-engineering/02-技术/AI工具与工作流/Powerskill流水线-四段式实战与提示词模板.md`](file:///root/cy/ai-quality-engineering/02-技术/AI工具与工作流/Powerskill流水线-四段式实战与提示词模板.md)

**Agent 协作纪律**：
- pilot 模板（M04 / M17）不得改（基线神圣）
- 批量生成用 implementer Agent + 对抗式 reviewer Agent
- Agent 不得 commit / push（Agent 只产 patch / report，主对话 commit）
- verify Agent 必须独立，不附和 fix Agent 自报告

---

## 完成度判定（C 档整体）

- [x] Pilot M04 完成 + 模板首版定稿
- [x] 第一批 5 模块批量生成 + reviewer audit + fix v1/v2 + verify + accept（2026-04-21）
- [x] **Pilot M17 完成 + audit + 7 问题修复 + accept（2026-04-21）→ 异步字段补完**
- [x] **模板调整 5 条建议沉淀到 README（2026-04-21）+ ADR-002 起**
- [x] **第二批 4 模块批量生成 + audit + fix v2 + verify + 精修 accept（2026-04-21）**：M02/M03/M11/M12；模板追加 TA-01~05 + R3-4 + R-X2
- [x] **第三批 A1 4 模块（M08/M09/M10/M15）accepted（2026-04-21）**+ ADR-003 跨模块读策略 + R3-5/R-X3/R-X4
- [x] **第三批 A2 M01 auth pilot accepted（2026-04-24）**：ADR-004 auth 横切范式 + "实现最简+schema 都支持" 模式 + R10-2 例外（独立审计表）
- [x] **Pilot 4 M13 需求分析（流式 SSE）accepted（2026-04-25）**：§12A 流式子模板定稿 + ADR-001 §4.1 补 aclose 协议 + ADR-002 L116 替换 M13 结论 + M04 baseline-patch（`create_dimension_record` + `get_latest`）+ M07 §6 对外契约登记 `list_by_project(node_id=...)`；驳回 reviewer M15 部分（合理 🔵）
- [x] **Pilot 5 M16 AI 快照（后台 🪷 fire-and-forget）accepted（2026-04-25）**：§12B 后台子模板定稿（7 字段+位次不通用警告）+ ADR-002 §横切影响 M16 脚注（不走 Queue + 反悔触发器）+ M05 baseline-patch（`count_by_node`）+ M15 Alembic 迁移 3+1 枚举（Phase 2）+ M04 契约锁定（复用 M13 补丁的 `create_dimension_record`）；19 项 audit（4 Blocker / 9 Major / 6 Minor）全部 🟢/🔵 关闭
- [ ] **Pilot 6 M18 语义搜索（🗂️ §12D embedding 持久化）draft（2026-04-25）**：brainstorming Q0-Q11 完成 + 00-design.md draft + §12D 子模板首次实战；待 tests.md + baseline-patch + 三轮 audit
- [ ] 扩展 M20 团队 / 空间 —— 待开
- [ ] 20 模块全部 status=accepted（剩 2 个：M18 / M20）
- [ ] 99-comparison/ 对照报告：每模块一份

---

## 设计回看触发器（手动审查清单）

> 集中记录"未来某时点要回头评估的设计决策"。**不挂自动 cron**——CY 在每月/每季度复盘时手动扫这里。

| 触发日期 | 触发对象 | 评估什么 | 决策路径 |
|---------|---------|---------|---------|
| **2026-10-25** | §12D embedding 持久化子模板 | 半年内是否仅 M18 一个实例使用？字段⑥/⑦ 是否与 §12C 高度重合？ | 是 → 降级为 §12C 扩展段落 + 删 §12D 行（防模板膨胀）<br>否 → 保留 §12D，记录新增使用模块 |
| _（未来 trigger 加在这里）_ | | | |
