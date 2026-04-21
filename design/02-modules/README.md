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
| 第二批 | M01 / M02 / M03 基础链 | 待开 | — |
| 第二批 | M11 / M12 中复杂 | 待开 | — |
| 第三批 | M13 / M16 / M18 复杂 AI | 待 CY 出业务 | — |
| 第四批 | M08 / M09 / M10 / M15 / M20 | 待开 | — |

**Pilot 范本**（新模块设计前必读）：
- 同步模块 → `M04-feature-archive/00-design.md`
- 异步 Queue 模块 → `M17-ai-import/00-design.md`

**Audit 报告归档**：
- 第一批：[`audit-report-batch1.md`](./audit-report-batch1.md) + [`audit-report-batch1-verify.md`](./audit-report-batch1-verify.md)
- M17 pilot：[`M17-ai-import/audit-report.md`](./M17-ai-import/audit-report.md)

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
| **流式（SSE）** | 🌊 | §12A 流式 schema | 待 M13 实战补完 | SSE endpoint + 流式 chunk 格式 + 客户端断线重连策略 |
| **后台异步**（fire-and-forget）| 🪷 | §12B 后台任务 schema | 待 M16 实战补完 | 任务状态轮询 endpoint + 状态字段定义（无持久化 Queue） |
| **Queue 异步**（持久化 + 重试）| 🗂️ | §12C **Queue payload schema**（M17 范式）| **M17** | TaskPayload 基类（强制 user_id + project_id）+ 任务清单 + 重试策略 + 死信处理 |

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
- **R3-2**：状态字段必用 `Mapped[StatusEnum]`（不能裸 `Mapped[str]`），配合 `CheckConstraint` 双重防护
- **R3-3**：tenant 字段（project_id）冗余在 SQLAlchemy class 上（统一规则，便于 DAO 过滤）

### §4 状态机
- **R4-1**：无状态实体也要显式声明
- **R4-2**：禁止转换至少列 N 条（N = 终态数 + 1，防仅列 2 条就勾过）—— M17 教训：原稿仅列 2 条，audit 抓出 4 条漏列
- **R4-3**：mermaid stateDiagram-v2 必须画

### §5 多人架构 4 维必答
- **R5-1**：5 项清单逐项标（即使 N/A 也要显式说明）
- **R5-2**：有状态机时必答"状态转换竞态分析"行（防自圆其说）

### §7 API 契约
- **R7-1**：Pydantic schema 强类型（不能裸 `dict`，必须 `dict[str, Any]` 或具体 BaseModel）
- **R7-2**：枚举字段用 Enum class（不能裸 `str` / `int`）
- **R7-3**：Queue payload 必须 `Literal[...]` 限定取值（如 step 必须 `Literal[1, 2, 3]`）

### §8 权限三层
- **R8-1**：所有模块 3 层（Server Action / Router / Service）+ 异步路径声明
- **R8-2**：🗂️ Queue 模块强制增第 4 行"Queue 消费者侧权限"（参 [`adr/ADR-002`](../adr/ADR-002-queue-consumer-tenant-permission.md)）
- **R8-3**：含 WebSocket 模块强制增第 5 行"每命令重校 task_id 归属"（防同连接绕过）

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
- [ ] 第二批批量（M02 / M03 / M11 / M12 等）
- [ ] 第三批 AI 类（M13 / M16 / M18）—— 异步流式 / 后台 子模板待补完
- [ ] 第四批（M08 / M09 / M10 / M15 / M20）
- [ ] 20 模块全部 status=accepted
- [ ] 99-comparison/ 对照报告：每模块一份
