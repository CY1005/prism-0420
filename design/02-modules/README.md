# 模块详细设计（C 档）

> **状态**：accepted（Phase 1 设计前置 2026-04-26 收官）
> **v2 修订**（2026-05-07，M02 sprint 启动 reconcile pass 暴露的体系缺口）：
> - 新增 R3-6 启动数据声明（细化 3 子项：启动期硬性 / 测试兜底 / 业务字典运行期）
> - 新增 R-X5 baseline-patch 时序契约（主标准 Q1+Q2 + 结构性约束 + 子选项清单待实证）
> - 新增 R-X6 横切 helper 必横切层 + 注释 4 字段
> - 新增 frontmatter `references.helpers:` 字段约束（仅允许引用横切层路径）
> - 详见 [`../audit/time-dimension-blindspot-2026-05-07.md`](../audit/time-dimension-blindspot-2026-05-07.md)

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
| 第三批 A1 | M09 全局搜索 | **superseded by M18（2026-04-26 M18 baseline-patch）** | [`M09-search/`](./M09-search/) |
| 第三批 A1 | M10 项目全景图 | **accepted（2026-04-21）** | [`M10-overview/`](./M10-overview/) |
| 第三批 A1 | M15 数据流转可视化 | **accepted（2026-04-21）** | [`M15-activity-stream/`](./M15-activity-stream/) |
| **Pilot 3** | M01 用户账号（**auth pilot**）| **accepted（2026-04-24）** | [`M01-user-account/`](./M01-user-account/) |
| **Pilot 4** | M13 需求分析（**流式 SSE pilot**）| **accepted（2026-04-25）** | [`M13-requirement-analysis/`](./M13-requirement-analysis/) |
| **Pilot 5** | M16 AI 快照（**后台 fire-and-forget pilot**）| **accepted（2026-04-25）** | [`M16-ai-snapshot/`](./M16-ai-snapshot/) |
| **Pilot 6** | M18 语义搜索（🗂️ §12D embedding 持久化 pilot） | **accepted（2026-04-26，三轮 audit + fix v1/v2/v3/v4/v4.1/v4.2/v4.3 + verify v1-v4.2 共 6 轮独立审）** | [`M18-semantic-search/`](./M18-semantic-search/) |
| 扩展 | M20 团队/空间（多 space 扩展）| **accepted（2026-04-26，三轮 audit + Batch 1-4 + Phase 1 sync 共 6 轮独立审）** | [`M20-team/`](./M20-team/) |

**Pilot 范本**（新模块设计前必读）：
- 同步模块 → `M04-feature-archive/00-design.md`
- 异步 Queue 模块 → `M17-ai-import/00-design.md`
- **流式 SSE 模块** → `M13-requirement-analysis/00-design.md`（§12A 流式子模板定稿；**仅服务 🌊 场景**，不跨形态复用）
- **Auth 横切源头模块** → `M01-user-account/00-design.md` + [`ADR-004`](../adr/ADR-004-auth-cross-cutting.md)（"实现最简 + schema 都支持"模式 / 独立审计表 R10-2 例外）
- **后台 fire-and-forget 模块** → `M16-ai-snapshot/00-design.md`（§12B 子模板定稿）
- **embedding/索引持久化模块** → `M18-semantic-search/00-design.md`（§12D 子模板 **accepted 2026-04-26**；双触发链 + 失败容忍 + 模型版本回填 + 跨模读双路豁免）

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

## frontmatter `references.helpers:` 字段约束（2026-05-07 时间维度盲区沉淀，对齐原则 6 + R-X6）

模块 design frontmatter 的 `references.helpers:` 子字段（见 M02 design 范例）**仅允许引用横切层路径**，禁止填业务模块路径。

**合法值**：

```yaml
references:
  helpers:
    errors:
      version: v3
      codes_used: [...]
      codes_added: [...]
    models:
      mixins: [TimestampMixin]
    auth:
      ref: api/auth/dependencies.py
    activity_log:
      ref: api/services/activity_log_service.py  # M15 own，但位置在横切 api/services/
    tenant_filter:
      ref: api/auth/tenant_filter.py             # M02/M20 注入，位置在横切 api/auth/
    crypto:
      ref: api/auth/crypto.py                    # 横切，owner = 05-security-baseline
```

**反模式（reviewer 阻塞 accept）**：

```yaml
references:
  helpers:
    crypto:
      ref: api/services/m02/crypto.py            # ❌ 横切关注挂业务模块名下
    audit_log:
      ref: api/dao/m02/audit_log_dao.py          # ❌ activity_log 横切归 M15，不能挂 M02
```

**判定**：横切层路径定义见 [`../00-architecture/04-layer-architecture.md` Q7 横切层定义](../00-architecture/04-layer-architecture.md#q7横切层定义2026-05-07-加对齐原则-6) 文件位置清单。

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
| **embedding/索引持久化**（派生数据 + 双触发链）| 🗂️ (embedding 子类) | §12D **embedding 持久化 schema**（M18 范式）| **accepted（M18 2026-04-26）** | 7 字段：①双触发链（增量+backfill）+ Payload schema ②embeddings 表 7 字段 PK (project_id, modality, target_type, target_id, provider, model_name, model_version) + 异维列 (embedding_512/1536/3072) + content_hash ③跨模读双路豁免（规则 1 + 规则 4）④鉴权路径（无用户端 endpoint，admin only）⑤超时（单 task 60s + batch 15min + query 1s）⑥失败容忍 + monitor cron（**不通知用户**——核心区别于 §12C 死信通知）⑦模型升级三段回填路径 + zombie + 8 cron 矩阵 + 90 天清理。**字段位次与 §12C 不语义对等**——核心区别：双触发链 / 失败容忍 / 必有 (provider, model_name, model_version) 三段回填 / 跨模读双路 / dim 锁定 {512,1536,3072} / mock provider 必 mock-* 前缀。详见 [M18-semantic-search/00-design.md §12](./M18-semantic-search/00-design.md) |

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
- **R3-6**（新增，2026-05-07 时间维度盲区沉淀；2026-05-07 后续 D3 推演细化）：**字典 / 全局表必须含"启动数据"段，分 3 类显式声明**

  > **细化盲点**（2026-05-07 后续 D3 推演）：原 R3-6 一刀切要求"必种数据清单 / 责任 sprint / 触发时机"，**没区分**启动数据的 3 类性质（启动期硬性 / 测试兜底 / 业务字典）。M02 `dimension_types` 撞到——业务类型清单（feature / competitor 等）属产品决策（运行期 admin 创建），不该被强塞进 design 期"启动数据"决策。

  含字典表 / 枚举注册表 / 全局参数表的模块（如 M02 `dimension_types` / M15 `ActionType` / 未来字典）§3 必须显式包含"启动数据"子段，**对每条数据先分类 3 子项 + 各自 3 字段**：

  **3 子项分类**：

  | 子项 | 性质 | design 期决策 vs 运行期 |
  |----|----|------|
  | **R3-6-A 启动期硬性 seed** | 系统启动必须存在（基础设施一部分，如 M01 admin user / 系统配置默认值） | design 期决（必种 + 由谁 + 何时种） |
  | **R3-6-B 测试兜底 placeholder** | 工程必需的最小集（无此数据下游模块测试跑不起来；如 M02 `dimension_types` 至少 1 条 `default` 类型） | design 期决（必种 + 由谁 + 何时种） |
  | **R3-6-C 业务字典清单** | 产品决策（具体类型清单 / 角色名 / 业务规则字典） | **运行期 admin 通过 CRUD endpoint 创建——不属 R3-6 范畴**，§3 启动数据段标"非 R3-6，运行期 admin 通过 [endpoint] 创建" |

  **R3-6-A / R3-6-B 子项必填 3 字段**：
  1. **必种数据清单**：列出启动时必须存在的具体数据行（key / name / 默认值等）
  2. **责任 sprint**：哪个模块 sprint 期内 seed（**仅 own 模块 sprint 自己 seed** —— 不允许推迟到下游模块 sprint，否则下游测试跑不起来；除非 R3-6-C）
  3. **触发时机**：alembic data migration / 启动 hook / CLI 命令 / 模块 sprint 内手工 seed 四选一

  **R3-6-C 子项必填**：
  - **运行期入口声明**：哪个 endpoint / Server Action / admin UI 用于创建（如"M02 POST /api/admin/dimension-types"）
  - **权限层级**：admin only / project owner only / etc

  **缺则 reviewer 阻塞 accept**——审计教训 1：M02 dimension_types 设计期空白，M03/M04/M07 实施前没兜底数据；审计教训 2（D3 推演）：原 R3-6 一刀切让"业务字典清单"误塞进 design 期决策。

  与 R3-1 / R3-5 关系：R3-6 不区分有无主表，只要含"字典/全局/启动期必需数据"特征都适用。

  适用模块：
  - M01（已合规：§6 + Q7 决策 env seed + CLI = R3-6-A）
  - M02 dimension_types（R3-6-B 必种 1 条 `default` placeholder + R3-6-C 业务类型清单运行期创建）
  - M15 ActionType / TargetType / ErrorCode（CHECK 约束初始版本——R3-6-A 启动期硬性，alembic data migration 内含枚举值）
  - 未来含字典表的模块（M07 issue type / M20 team role 等）参照本规则分类

### §4 状态机
- **R4-1**：无状态实体也要显式声明
- **R4-2**：禁止转换至少列 N 条（N = 终态数 + 1）+ **每条格式必须是 "状态A → 状态B：原因 + 对应 ErrorCode"**（batch2 audit 沉淀）
  - **禁止合并写法**：`X / Y → 任意`（两个终态合并算 1 条，不满足 N 数量要求）
  - 每个终态单独一条：`completed → 任意 状态`、`failed → 任意 状态`、`cancelled → 任意 状态` 必须分开写
  - 禁止把"并发控制 version 冲突"、"删后 404"等非状态转换混入（应放在节 5 竞态分析或节 13 ErrorCode）
- **R4-3**：mermaid stateDiagram-v2 必须画
- **R4-3a**：非常规态 / 非常规边登记规约（M01 pending 矛盾沉淀；K8s Pod phase 实践参照）

  状态机若含以下任一类型，**禁止在 mermaid 中画出**，必须在 mermaid 之外**单独"非常规态登记表"**呈现（防"同一边一处允许一处禁止"）：

  | 类型 | 判别 |
  |------|------|
  | 预留态（reserved）| schema CheckConstraint 含但本期 service 不可达，依赖未来功能启用 |
  | 半终态（pseudo-terminal）| 可循环回早期态的"看似终态" |
  | 短暂态（transient）| cron / 系统流程会强制转出，正常存活窗口 < 5min |
  | 降级态（degraded）| 系统过载/异常时进入的应急态 |
  | 迁移过渡态（migration）| 版本/schema 迁移期间存在，迁移完毕即消失 |

  若含**条件可达边**（仅在特定流程同事务内可达，不在常规 user-driven service 路径），独立"非常规边登记表"，mermaid **可以画**但必须用 `note` 标注同事务条件。

  与 R4-2 衔接：R4-2 的 N（终态数+1）公式**只覆盖 mermaid 中出现的态**——非常规态不参与 N 计算，其禁止/允许语义在本登记表"本期 service 行为"列内表达。

  **非常规态登记表模板**（6 字段必填）：

  | 态名 | 类型 | 启用条件 | 本期 service 行为 | 字段来源 | since |
  |------|------|---------|------------------|---------|-------|
  | pending | reserved | Q1 开放注册启用 | 拒登录返回 ACCOUNT_PENDING；任何写入抛 InvalidTransitionError | `users.status` | reserved since v1（M01 初版）|

  字段定义：
  - **字段来源**：填持久化字段名（`users.status`）；display-only 态填 `display-only`，**不允许空**
  - **since**：填 `reserved since v<X>` / `transient since v<X>` / `pseudo-terminal since v<X>`，**不允许填"未来"或空**

  **非常规边登记表模板**（3 字段必填）：

  | from → to | 触发流程 | 本期可达 |
  |----------|---------|---------|
  | owner → admin | transfer ownership 同事务（with db.begin()） | 是（仅 transfer 路径） |

  **反例对照**（M01 4-25 冲刺产出，已 patch）：

  M01 mermaid 含 `[*] → pending` / `pending → disabled (预留)` 同时禁止表又列 `pending → disabled` 禁止——同一边一处允许一处禁止，实装不知按哪条走。R4-3a 强制把 pending 拆出登记表后 mermaid 只剩本期可达态，矛盾消失。

  **根因**：mermaid 用"未来全图"思维画，禁止表用"本期硬约束"思维写，两个时间视角混进同一份文档。R4-3a 用"主表只画本期可达"+"非常规态独立登记"切开两个时间视角。

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
    3. 事件主体是 **系统行为**（auth 校验 / embedding 计算 / cron 维护等），而非 **业务行为**（CRUD 业务实体）。是否带 project_id 仅为索引/分析需要，不影响判定。（M18 baseline-patch 修订 2026-04-26：原文"事件无 project_id 归属"被 M18 audit M7 反例驳回——M01 login_attempt 显然有用户主动操作语义但应保留例外资格——改为"系统 vs 业务"二分法）
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
  - **Service 接口签名规范**（**M04 sprint R-X5 升级 / 2026-05-07**：4 参含 `actor_user_id` 满足 R10-1 batch3 per-record activity_log 写入需要）：
    ```python
    # ✅ 接受外部 session + actor_user_id
    async def delete_by_node_id(
        self, db: AsyncSession, node_id: UUID, project_id: UUID, actor_user_id: UUID
    ) -> None:
        # 不调 self.db.begin()，直接用入参 db；
        # actor_user_id 用于每条受影响记录的 activity_log write_event
        ...

    # ❌ 反例 1：自开事务
    async def delete_by_node_id(self, node_id: UUID, project_id: UUID) -> int:
        async with self.db.begin():    # 违反 R-X3
            ...

    # ❌ 反例 2：缺 actor_user_id（M04 sprint 前的旧 3 参签名）
    async def delete_by_node_id(self, db, node_id, project_id):
        # 无法写 R10-1 batch3 per-record activity_log（write_event 强制 actor_user_id）
        ...
    ```
  - 适用：所有"可能被跨模块调用"的 Service 方法（M03/M04/M06/M07/M08/M11/M17 的 batch/delete_by/orphan_by 方法等）
- **R-X4**（新增，batch3 audit 沉淀）：**聚合读模块必须引 ADR-003**——新增聚合读模块（无自有表 / 跨多模块读）的 §3 必须显式声明适用 [`ADR-003`](../adr/ADR-003-cross-module-read-strategy.md) 的哪条规则（规则 1 上游 Service 接口 / 规则 2 只读 import 豁免 / 规则 3 横切表豁免），禁止默认走"DAO 直 JOIN 业务表"（候选 C 已否决）
- **R-X6**（新增，2026-05-07 时间维度盲区沉淀；归纳 scaffold S2/S5 先例为通用规则）：**横切关注 helper 必建在横切层 + 注释含 4 字段强制模板**

  > **前置原则**：[`../00-architecture/06-design-principles.md` 原则 6 横切关注 vs 业务关注必须显式判定](../00-architecture/06-design-principles.md#原则-6横切关注-vs-业务关注必须显式判定2026-05-07-时间维度盲区沉淀) + [`../00-architecture/04-layer-architecture.md` Q7 横切层定义](../00-architecture/04-layer-architecture.md#q7横切层定义2026-05-07-加对齐原则-6)

  **规则**：
  1. 横切关注 helper（多模块复用 / 横切 ADR 范畴 / 工程基础设施）**必须建在横切层目录**之一（见 04-layer §Q7 清单），禁止挂在业务模块名下（如 `api/services/m02/crypto.py` 反模式）
  2. 横切 helper 文件**必须含 4 字段注释模板**（同 [`../00-phase-gate.md` S2 注释强制模板](../00-phase-gate.md#s2-注释强制模板2026-05-07-时间维度盲区沉淀)）：① 决策内容 ② 简化理由 ③ 由哪个模块在何时扩齐到何形态 ④ 触发回写动作
  3. 横切 helper 可有 owner 模块（M? own），owner 负责实装 + 测试 + 演进决策；其他模块只读消费——但**文件位置仍在横切层**

  **正例（已落地）**：

  - `api/services/activity_log_service.py` —— owner = M15（R10-2 例外允许独立审计表 own，但本 helper 是 horizontal）
  - `api/auth/tenant_filter.py` —— owner = M02 / M20（注入 concrete 实现），位置在 `api/auth/`
  - `api/errors/codes.py` + `api/errors/exceptions.py` + `api/errors/middleware.py` —— owner = engineering-spec 横切

  **反例（曾差点落 M02 own）**：

  - 2026-05-07 D4 推演：M02 sprint 期 AES-256-GCM 加解密 helper 原打算 own M02（路径 B），但 helper 是横切关注（M02 写 / M13 读 / 未来 M16/M17 cron secret），按原则 6 + R-X6 必须建在 `api/auth/crypto.py` 横切层，owner = 05-security-baseline

  **违反 → reviewer 阻塞 accept**；frontmatter `helpers:` 字段静态扫描可识别违反（仅允许引用横切层路径，见下方"frontmatter helpers 字段约束"）
- **R-X5**（新增，2026-05-07 时间维度盲区沉淀）：**baseline-patch 时序契约——被回写模块必须显式选退化路径**

  > **背景**：baseline-patch 机制是"模块 X 设计期不知道，但模块 Y 设计后回写到 X design 的字段/方法/调用"。例如 M20 baseline-patch 把 `team_id FK` 写到 M02 design §3，M18 baseline-patch 把 `get_for_embedding + enqueue` 写到 M03/M04/M06/M07 design §6。design 层面信息完整，但实施时序是 M02→...→M18→M20（baseline-patch 引用的依赖晚于被回写模块实施），导致被回写模块**实施期撞墙**——依赖表/方法/服务还不存在。
  >
  > **根因**：baseline-patch 让 design 始终是"目标态真相"，但**没规定实装期遇到"依赖未到位"如何退化**。

  **判断逻辑（主标准）**：

  对每条 baseline-patch 引用，问 2 个问题决定退化路径：

  **Q1：本模块 sprint 期能否独立完成该改动？**
  （独立 = 编译通过 + 单元测试通过 + 不依赖未实现的外部资源如表/service/endpoint）
  - 是 → **A 现在建**
  - 否 → 进 Q2

  **Q2：本模块在该 baseline-patch 中是 caller 还是 callee？**
  - **Caller**（本模块主动调用依赖 service / 主动写依赖表）→ **B 推迟** + scaffold 留 TODO 注释（理由：依赖未落地时调用必失败，硬建后 ImportError / NameError / FK 写入异常）
  - **Callee**（本模块定方法签名给依赖调用 / 字段是被动 schema 形态）→ **C 留中间态**（理由：方法签名 / 字段在，依赖到位时填实现 / ADD CONSTRAINT；本模块 sprint 期无人调用 / 无 FK 写入压力）
  - **混合**（一条 baseline-patch 含多个改动，如 ErrorCode + endpoint）→ **拆开**逐项套 Q1 + Q2

  **退化路径定义**：

  - **A 提前建占位**：本模块 sprint 期建依赖的最小占位（schema / stub service），自己 seed 数据 / mock 实现；优：alembic 一次成形 / 测试 fixture 直接用；缺：抢做依赖模块 owner 的 schema 边界 / 占位 schema 万一依赖模块 sprint 改动需 ALTER
  - **B 推迟到依赖落地**：本模块 sprint 期不写该字段/方法，scaffold 留 TODO 注释 + 显式标"M? sprint 实施"；优：模块边界严格 / schema 最小；缺：design ↔ 实装暂偏离需 disambiguation 注释 / alembic 演进多次
  - **C 留中间态**：本模块 sprint 期写字段（无 FK 约束）/ 方法签名（空实现）/ enum 定义（无引用），依赖模块 sprint 时只 ADD CONSTRAINT / 填实现；优：design 形态保留 / 切分清晰；缺：中间态有"列在但 FK 防御缺位"的窗口期

  **格式要求**（缺任一 → reviewer 阻塞 accept）：
  ```markdown
  ### 实施期处理（X baseline-patch 引用 Y）
  - **退化路径**：A / B / C 之一
  - **理由**：本期是否有调用 / 是否需 fixture / 是否需 FK 防御
  - **alembic 步骤数**：N 步（含 ALTER 详情）
  - **触发回写**：依赖模块（M?）sprint 启动时本模块 design 此段更新为"已落地"+ commit hash
  ```

  **结构性约束**（X- 折中，2026-05-07 推演沉淀；不依赖工程具体机制，可前置立规）：

  - **A 路径必声明**：unit test 仅覆盖 default 路径 / 死代码期窗口（M? → 依赖模块 sprint）；生产路径回归测试推迟到依赖模块 sprint 期补，回写 design 标"生产路径已验证 + commit hash"
  - **B 路径必动作**：scaffold 留 TODO 注释**必含 S2 4 字段强制模板**（决策内容 / 简化理由 / 由 M? sprint 扩齐到何形态 / 触发回写动作）；引 [`00-phase-gate.md`](../00-phase-gate.md#s2-注释强制模板2026-05-07-时间维度盲区沉淀)
  - **C 路径必登记**：
    1. **测试覆盖盲区清单**：本模块 sprint 期下游模块测不了哪些路径（如 M02 sprint 期下游测不了团队 project 路径）
    2. **依赖模块回写 checklist**：依赖模块 sprint 启动时本模块需做的回写动作（data migration 清理 / ADD CONSTRAINT FK / 回归测试 / 回写 design 标"已落地" + commit hash）
    3. 二者写入本模块 design "实施期处理" 段下，依赖模块 sprint 启动 reconcile pass 时校验

  **子选项清单**（_等 M02/M03 sprint 实证后归纳填入_）：

  > **🔴 立规红线**：A/C 路径下的具体子选项（如 C 路径"中间态写入策略"分 API/Service/DAO 三层 / B 路径 OpenAPI 契约层处理 / A 路径"被动接口类型 owner"受分层依赖方向约束）**禁止凭印象立规**，必须基于至少 1 次模块 sprint 真实写代码 + 跑测试的实证后归纳。
  >
  > **沉淀依据**：2026-05-07 路径 X+ 推演时凭印象立"C1 禁写 / C2 允许"二选一 + OpenAPI"三选一" + 类型 owner"三选一"，撞 4 个新盲区（C 子选项分层错 / FastAPI OpenAPI 是 router 生成不是 design 生成 / 分层依赖方向约束 / R13-1 标记位置颗粒不够），违反 [`feedback_external_behavior_lookup`](memory)。
  >
  > **执行约束**：M02 sprint 启动 reconcile pass 期间，sprint 内若撞结构性子选项，先 case-by-case 决策 + 登记到 design/audit/m02-pilot-template-validation.md（M01 PT tracker 同款机制），M03 sprint 启动时再积累 1 次实证；2 次实证后归纳到本段子选项清单，从而完成立规闭环。

  **类型倾向参考表**（辅助，**不替代主标准 Q1+Q2**——以下倾向是大多数情况的统计常态，仍须按主标准判断）：

  | baseline-patch 类型 | 多数情况倾向 | 主标准对照 | 示例 |
  |-----------------|---------|---------|----|
  | 含外部依赖的 schema（FK 引用未存在的表 / 跨表 check）| C 留中间态 | Q1 否 + Q2 callee（schema 形态保留）| M02-M20 team_id FK |
  | 无外部依赖的 schema（自表 column + default + 自表 check）| A 现在建 | Q1 是（独立完成）| M02-M18 rrf_k / similarity_threshold |
  | 主动方法调用（commit 后尾调依赖 service / 调用未存在的 endpoint）| B 推迟 + TODO 注释 | Q1 否 + Q2 caller | M03/M04/M06/M07-M18 enqueue |
  | 被动方法签名（本模块定接口给依赖调用 / 依赖 sprint 期才有 caller）| A / C（无人调影响小）| Q1 是 OR Q2 callee | M04-M13 create_dimension_record / M02-M18 get_search_config |
  | enum 扩展（ActionType / ErrorCode 添值，不立刻引用）| A 直接写入 | Q1 是（死定义无副作用）| M15-M18 ActionType / M15-M20 ErrorCode / M02-M20 PROJECT_ARCHIVED |
  | 主动业务 endpoint（POST 写依赖表 / 依赖业务流）| B 推迟 | Q1 否 + Q2 caller | M02-M20 move-team endpoint |

  **扫描清单**（基于 2026-05-07 全 M01-M20 design 扫描）：M02（A1+A2+A3）/ M03+M04+M06+M07（A4-A7 同款）/ M15（A8+A9 enum 扩展）共 5 模块 11 处。回扫工作单独 commit（见 design/audit/time-dimension-blindspot-2026-05-07.md）。

  **关联**：
  - 体系级新原则："design 是目标态真相，实装期遇到'依赖未到位'必须显式选退化路径，不允许悄悄绕"
  - 闸门：每模块 sprint 启动 reconcile pass（00-phase-gate.md 闸门 2.5）必扫本模块 design 所有 baseline-patch 引用是否含"实施期处理"段
  - 沉淀文档：[`../audit/time-dimension-blindspot-2026-05-07.md`](../audit/time-dimension-blindspot-2026-05-07.md) / KB `02-技术/架构设计/设计前置方法论-补丁01-时间维度.md`

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
- [x] **Pilot 6 M18 语义搜索（🗂️ §12D embedding 持久化）accepted（2026-05-09 startup flip / 设计完成 2026-04-26）**：brainstorming Q0-Q11 + 00-design.md + §12D 子模板首次实战 + tests.md + baseline-patch-m18.md + 三轮 audit + fix v1/v2/v3/v4/v4.1/v4.2/v4.3 + verify v1-v4.2 共 6 轮独立审 + 2026-05-09 startup grep verify v4.3 关键词全清 → status flip
- [x] **扩展 M20 团队 accepted（2026-04-26）**：ADR-005 + 16 节 00-design.md + tests.md（68 用例）+ baseline-patch-m20.md（M01+M02+M15+M03-M19 横切 16 模块）+ 3 轮 audit + 4 批修复 + Phase 1 sync 共 6 轮独立审；F1.11 硬触发器 M02/M15/ADR-001 已同步
- [x] **20 模块全部 status=accepted**（M01-M20 全收齐，M09 superseded by M18）—— Phase 1 设计前置收官
- [ ] 99-comparison/ 对照报告：每模块一份

---

## 设计回看触发器（手动审查清单）

> 集中记录"未来某时点要回头评估的设计决策"。**不挂自动 cron**——CY 在每月/每季度复盘时手动扫这里。

| 触发日期 | 触发对象 | 评估什么 | 决策路径 |
|---------|---------|---------|---------|
| **2026-10-25** | §12D embedding 持久化子模板 | 半年内是否仅 M18 一个实例使用？字段⑥/⑦ 是否与 §12C 高度重合？ | 是 → 降级为 §12C 扩展段落 + 删 §12D 行（防模板膨胀）<br>否 → 保留 §12D，记录新增使用模块 |
| **2026-10-25** | M18 §3 schema 7 字段 PK + 异维列拆分 | embeddings 行数是否 > 50万？ivfflat lists=100 在 dim_3072 列召回质量是否退化？mock provider mock-* 前缀约束在 Phase 2 是否引发开发阻力？ | 行数超 → §15 演进锚点 R3 E3 触发（按月 partition / lists 调 sqrt(N)~700）<br>mock 阻力 → 评估改 sanity check warning 而非 ConfigError |
| **2027-04-26** | M18 search_evaluation_log | 1 年累计采样数据是否够做离线分析？RRF k=60 是否需要按真实数据调？query embedding cache 命中率是否符合预期？ | 数据够 → 触发离线 metric 分析 + RRF 参数调优<br>数据不足 → 评估提高采样率或废弃 search_eval 表 |
| **2026-10-26** | M20 跨 team 子查询性能（ADR-005 §4 T1）| `user_accessible_project_ids_subquery` 在真实负载下 P95 是否 > 100ms？用户 team 数 P95 是否 > 20？单次 AC2 一键迁移是否 > 100 个 project？ | P95 > 100ms → 引入 Redis 缓存 + 5 处失效路径（参 ADR-005 §4 T1 预演）<br>team 数 > 20 → 同上<br>单次迁移 > 100 → 触发 Phase 2 批量后端 API 决策 |
| **2026-10-26** | M20 ActionType / ErrorCode 枚举膨胀 | M20 新增 10 个 team_* ActionType + 8 个 ErrorCode，半年使用率是否 < 30%（即 ≥ 70% 枚举值零事件）？ | 是 → 评估合并冗余 ActionType（如 promoted_admin / demoted_member 是否合并为 role_changed + detail）<br>否 → 保留 |
| **2027-04-26** | M20 organization 层引入触发器 | 单实例是否 ≥ 2 个独立组织 / 跨组织隔离 / 计费按组织独立结算 任一发生？ | 是 → 走 ADR-005 §8 org 层 4 决策点 + 启动 baseline-patch-org<br>否 → 不引入，下一年再回看 |
| _（未来 trigger 加在这里）_ | | | |
