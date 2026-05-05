---
title: 横向规约 ↔ 模块设计 完整 reconcile pass
status: draft
owner: CY
created: 2026-05-06
trigger: M01 实施前 D1 决策暴露 7 seam 后，CY 要求"全面梳理详细设计中的结构性问题"
methodology:
  - ATAM (SEI) — sensitivity points / tradeoff points / risk themes
  - Rozanski & Woods — perspectives + perspective interactions
  - Garcia et al. — Architectural Bad Smells (4 类)
  - 14 类结构性 seam taxonomy（agent 调研整合）
references:
  - https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/
  - https://www.viewpoints-and-perspectives.info/
  - https://link.springer.com/chapter/10.1007/978-3-642-02351-4_10
---

# 横向规约 ↔ 模块设计 完整 reconcile pass

## 0. 本次 audit 的方法学基础

前一份 [`scaffold-design-reconcile.md`](./scaffold-design-reconcile.md) 找的是**对错型 seam**（命名漂移 / 路径错 / 接口不一致）。

本次 audit 找的是**结构性 seam** —— 横向规约单看 OK、模块单看 OK、**组合时才暴露**的问题。

### 14 类结构性 seam taxonomy

| # | 名称 | 一句话定义 |
|---|------|----------|
| 1 | Rule Coverage Gap（规约覆盖盲区）| 横向规约覆盖 80% 场景，剩下 20% 没显式说，模块各自发明 |
| 2 | Rule-Rule Tradeoff Point（规约对冲点）| 两条规约单独看都对，某模块同时触发两条时矛盾 |
| 3 | Namespace Collision（命名空间冲突）| 横向分类（ErrorCode / 事件类型 / topic）没全局命名空间机制，模块间静默撞名 |
| 4 | Ambiguous Interface（接口分发歧义）| 一个接口对外一份契约，内部按状态/输入分发，调用方不知道走了哪条 |
| 5 | Scattered Concern（关注点散落）| 一个责任分散在多模块，聚合行为没人定 |
| 6 | Missing State Machine Edge（状态机边缺失）| 模块状态机漏掉了"另一模块的 API 能触发的转换" |
| 7 | Idempotency Contract Mismatch（幂等契约错配）| 模块写库幂等但副作用（队列 / 日志 / 外调）非幂等 |
| 8 | Permission Model Underspecification（权限模型欠规约）| 模块只写 CRUD 权限，横向要求字段级 / 状态条件级权限没回答 |
| 9 | Queue Contract Incompleteness（队列契约不完整）| Queue payload 写了，consumer 行为/重复/乱序/错误语义没人定 |
| 10 | ADR Interaction Blind Spot（ADR 交叉盲区）| 两个 ADR 各自合理，某模块同时落两个 ADR 时边界没指定 |
| 11 | Broken Modularization（模块化破损）| 跨模块共享概念无人 own，或多人 own |
| 12 | Silent Inheritance of Horizontal Default（默认值静默继承）| 横向有默认值，模块不显式 override，默认值用错没人发现 |
| 13 | Cross-Module Error Propagation Gap（跨模块错误传播缺口）| 模块 A 抛的错码，模块 B 调它但没说怎么处理 |
| 14 | Observability Coverage Hole（可观测覆盖盲区）| 横向 observability 触发表覆盖不全，某些模块操作不在覆盖内 |

### 5 个检测流程

- **P1**：Rule × Module 矩阵 — 找规约覆盖盲区 / 默认值静默继承
- **P2**：Namespace collision grep — 找命名空间冲突
- **P3**：ADR × ADR 交叉矩阵 — 找 ADR 交叉盲区
- **P4**：Queue producer-consumer 完备性走查 — 找队列契约不完整
- **P5**：State machine reachability — 找跨模块 API 触发的状态机边缺失

---

## 1. P2 执行结果 — Namespace Collision Scan

### 1.1 ErrorCode 命名空间（125 个码 / 0 重名 / 但分布有问题）

**统计**：20 模块累计 **125 个业务 ErrorCode**，跨模块 0 重名。

**发现 S-A1（Rule Coverage Gap #1 + Namespace Collision #3）**：

24 个 `_NOT_FOUND` 后缀码各自前缀化：

```
M01 USER_NOT_FOUND
M02 PROJECT_NOT_FOUND / MEMBER_NOT_FOUND
M03 NODE_NOT_FOUND / NODE_PARENT_NOT_FOUND
M04 DIMENSION_NOT_FOUND / DIMENSION_TYPE_NOT_FOUND
M05 VERSION_NOT_FOUND
M06 COMPETITOR_NOT_FOUND / COMPETITOR_REF_NOT_FOUND
M07 ISSUE_NOT_FOUND
M08 RELATION_NOT_FOUND
M10 OVERVIEW_PROJECT_NOT_FOUND
M11 COLD_START_TASK_NOT_FOUND
M12 COMPARISON_NODE_NOT_FOUND / COMPARISON_SNAPSHOT_NOT_FOUND
M13 ANALYSIS_NODE_NOT_FOUND
M14 NEWS_NOT_FOUND / NEWS_LINK_NOT_FOUND
M15 ACTIVITY_STREAM_PROJECT_NOT_FOUND
M16 SNAPSHOT_NODE_NOT_FOUND / SNAPSHOT_TASK_NOT_FOUND
M17 IMPORT_TASK_NOT_FOUND
M18 EMBEDDING_TARGET_NOT_FOUND
```

vs 横向通用 `NOT_FOUND` 1 个。

**根因**：横向 engineering-spec § 7.2 + 02-modules/README.md R13-1/R13-2 **从未表态**："实体未找到"该用横向 NOT_FOUND + details.entity_type 还是模块各自前缀化。结果各模块都选了前缀化，但**这个选择无人登记、无人审计是否一致**。

**结构性问题**：错过了把 ErrorCode 命名空间策略写进规约的机会。

---

### 1.2 M15 ActionType enum 命名风格分裂

**发现 S-A2（Namespace Collision #3）**：

M15 是横向 ActionType taxonomy 的 owner（R10-2），但 enum 内部**三种命名风格混用**：

| 风格 | 例子 |
|------|------|
| snake_case 单词 | `create / update / delete / archive / move / orphan` |
| dot.notation | `cold_start.create / snapshot.create / import.create / import.failed` |
| prefix + snake | `team_created / team_renamed / project_joined_team` |
| 后缀 _triggered | `embedding_model_upgrade_triggered` |

**根因**：R10-2 规约说"模块 accepted 后回写 M15 schema"，**但没规约 ActionType 命名风格统一**。M11/M16/M17 用 dot.notation，M20 用 prefix+snake，通用动作用 single word。

**结构性问题**：横向 schema 没有"命名规范"这层规则。

---

### 1.3 跨语义重用同一个词

**发现 S-A3（Namespace Collision #3）**：

| 词 | 语义 1 | 语义 2 |
|----|-------|-------|
| `VERSION` | M01 user.version 乐观锁字段 / `VERSION_CONFLICT` 错误 | M05 版本时间线业务 `VERSION_NOT_FOUND` / `VERSION_LABEL_DUPLICATE` |
| `import_` | M15 enum 通用动作 `import_` | M17 特化系列 `import_create / import_failed / import_partial_failed / import_cancel` |
| `archive` | 通用动作 | M02 项目归档 / M03 节点归档 / M04 档案归档 三者共享 |

**根因**：横向无"动词语义全局命名空间"概念，模块各自起名时不查重。

---

### 1.4 模块用了 `_QUOTA_EXCEEDED` 而横向有 `RATE_LIMITED`

**发现 S-A4（Rule Coverage Gap #1）**：

```
M13 ANALYSIS_QUOTA_EXCEEDED
M16 SNAPSHOT_QUOTA_EXCEEDED
M17 IMPORT_QUOTA_EXCEEDED
M19 EXPORT_NODE_LIMIT_EXCEEDED
```

横向有 `RATE_LIMITED`（429），但语义是"调用频率限制"；4 模块用的是"额度上限"（用户级配额）。两个语义在横向规约里**没有区分定义**，每模块各自命名。

**结构性问题**：横向规约对"配额 vs 频率限制"的区分缺失。

---

## 2. P3 执行结果 — ADR × Module 交叉矩阵

```
Module                ADR-001 ADR-002 ADR-003 ADR-004 ADR-005
M01-user-account         1       7       1      24       .
M02-project              1       .       .       .       1
M03-module-tree          .       .       1       .       .
M04-feature-archive      .       .       2       .       .
M05-version-timeline     .       .       .       .       .
M06-competitor           .       .       1       .       .
M07-issue                .       .       1       .       .
M08-module-relation      .       .       1       .       .
M09-search               .       .      17       .       .
M10-overview             .       .      21       .       .
M11-cold-start           .       .       .       .       .
M12-comparison           .       .       2       .       .
M13-requirement-analysis 7       4       8      18       .
M14-industry-news        .       .       .       .       .
M15-activity-stream      .       .      11       .       .
M16-ai-snapshot          5       2       7       8       .
M17-ai-import            .       .       .       .       .
M18-semantic-search      7       5      15       4       .
M19-import-export        .       .       .       .       .
M20-team                 2       .       4       2       5
```

### 2.1 5 模块同时落 4 ADR（高风险 ADR Interaction Blind Spot）

**发现 S-B1（ADR Interaction Blind Spot #10）**：

| 模块 | 落的 4 ADR |
|------|----------|
| M01 user-account | 001 + 002 + 003 + 004 |
| M13 requirement-analysis | 001 + 002 + 003 + 004 |
| M16 ai-snapshot | 001 + 002 + 003 + 004 |
| M18 semantic-search | 001 + 002 + 003 + 004 |
| M20 team | 001 + 003 + 004 + 005 |

**结构性问题**：5 个模块同时受 4 个 ADR 约束，**没有任何文档登记"4 ADR 同时适用时的优先顺序 / 边界冲突解析"**。

**真实场景举例**：M16 fire-and-forget 任务（§12B）触发时：
- ADR-001 说 db session 在 service 层 → 但 fire-and-forget 跑出 service 层后 session 怎么管？
- ADR-002 说 Queue payload 带 user_id + project_id → 但 fire-and-forget **不走 Queue**（M16 design 注明），ADR-002 该不该套？没说
- ADR-004 说 auth 横切 4 法 → fire-and-forget 是系统行为不是用户调用，4 法走哪条？没说

→ M16 design 直接 `from api.db import SessionLocal` 自创 session 路径绕过 ADR-001 service 层规约。**这是 ADR 缝隙逼出的违规**。

---

### 2.2 M11 / M14 / M17 / M19 完全不引 ADR

**发现 S-B2（Rule Coverage Gap #1 + Documentation Hole）**：

| 模块 | 状态 | 应引 |
|------|-----|------|
| M11 cold-start | 0 ADR 引用 | 应引 ADR-002（Queue async）+ ADR-004（auth）|
| M14 industry-news | 0 ADR 引用 | 至少 ADR-001（单 ORM）|
| **M17 ai-import** | 0 ADR 引用 | 应引 ADR-002（Queue pilot 本身就是 M17 抽出的）+ ADR-001 |
| M19 import-export | 0 ADR 引用 | 应引 ADR-003（跨模块读 5 个 model）|

**M17 是 ADR-002 的范本但自己 0 引用**——这是元 seam（ADR 写于 M17 之后？还是模板未要求显式引用？）。

**结构性问题**：02-modules/README.md 没要求"每模块 design 头部声明引用了哪些 ADR"，导致引用稀疏度无法审计。

---

## 3. P4 执行结果 — Queue Contract 完备性

### 3.1 §12 形态分布 vs ADR-002 引用

```
                    §12A  §12B  §12C  ADR-002引用
M01-user-account     1     1     6      7
M11-cold-start       1     0     0      0   ⚠
M13-requirement-analysis 43 7    9      4
M15-activity-stream  3     0     0      0   ⚠
M16-ai-snapshot     13    30    15      2   ⚠
M17-ai-import        0     0    10      0   ⚠⚠ pilot 不引
M18-semantic-search  6     7    26      5
M20-team             3     2     2      0   ⚠
```

**发现 S-C1（Queue Contract Incompleteness #9）**：

5 模块有 §12 形态但 ADR-002 引用 ≤2，强信号"声明但未对齐契约"。

---

### 3.2 ADR-002 强制 user_id + project_id，但 cron-triggered backfill 任务没有真实 user_id

**发现 S-C2（ADR Interaction Blind Spot #10 + Queue Contract Incompleteness #9）**：

ADR-002 § 1 强制 TaskPayload 含 user_id + project_id（多租户隔离）。

**但 M16 zombie cron / M18 backfill cron 是系统触发，不是用户触发**：

- M18 design line 383：`user_id: Mapped[UUID]` 字段必填
- M18 backfill 任务由 cron（非用户）触发——user_id 该填什么？admin？system_uuid？空？
- ADR-002 没规约"系统任务的 user_id 边界"
- M18 design 也没显式说

**结构性问题**：ADR-002 的契约没区分"用户触发 vs 系统触发"。

---

### 3.3 Queue 默认重试策略 vs 模块 override

**发现 S-D1（Silent Inheritance of Horizontal Default #12）**：

ADR-002 / 02-modules/README.md § 12 写 M17 §12C 范式 5 条：默认 3 次指数退避（1s/4s/16s）+ 死信通知用户。

但：
- M16 §12B 后台任务：失败**不重试 + 手动重发**（与默认相反）
- M18 §12D embedding：**失败容忍 + 不通知用户**（与默认相反）

M16 / M18 都是"显式 override"——但**横向规约没有"override 必须放在 design § 几"的规则**，导致 override 散落在不同节，未来新模块审计时容易漏。

---

## 4. P1 执行结果 — Rule × Module 覆盖矩阵（采样）

### 4.1 R-X4（聚合读模块必须引 ADR-003）覆盖

**应引 ADR-003 的聚合读模块**：M09 / M10 / M15 / M18

实际引用次数（grep）：
- M09 = 17 ✓
- M10 = 21 ✓
- M15 = 11 ✓
- M18 = 15 ✓

**SKIP**：本规约执行良好。

但 **M19 import-export 直 import 5 个其他模块的 model，按 ADR-003 规则 2 应豁免登记，但 ADR-003 引用 = 0**。规约触发条件不清晰。

---

### 4.2 frontmatter R0-1（12 字段强制）

**发现 S-E1（Rule Coverage Gap #1）**：未抽样验证（成本高），交给 CI 静态扫。但已知现象：M01-M20 的 frontmatter 字段集合未与 02-modules/README.md 模板自动比对——**没有 CI/lint 守护这条 R0-1**。

---

### 4.3 M01 §10 表头与其他模块不一致

**发现 S-E2（Rule Coverage Gap #1）**：

```
M01: | action_type | user_id | metadata 字段 | 触发点 |       (4 列，无 target_type)
其他: | action_type | target_type | target_id | summary | metadata |   (5 列)
```

M01 享受 R10-2 例外（auth_audit_log 独立表），合理。**但 02-modules/README.md § 16 字段模板第 10 节** 仍按主规则模板写——**例外没回写模板**，未来新模块若也享受 R10-2 例外（如未来加 audit log），不知道用哪个表头。

---

## 5. P5 — State Machine Reachability（未执行 / 待补）

成本高（每模块 §4 + 跨模块 service 调用矩阵），本 pass 暂不展开。建议作为 **2 期 audit** 单独跑。

预期输出：每个模块 §4 状态机 vs 其他模块对它的 API 调用，找"另一模块 API 能触发但本状态机未声明"的边。

---

## 6. 总 seam 清单（按 14 类聚合）

| ID | 14 类 | 描述 | 严重度 |
|----|------|------|--------|
| S-A1 | #1 + #3 | NOT_FOUND 命名策略横向无规约（24 个前缀化各自发明）| 🔴 |
| S-A2 | #3 | M15 ActionType enum 三种命名风格混用 | 🟡 |
| S-A3 | #3 | VERSION / import / archive 跨语义重用 | 🟡 |
| S-A4 | #1 | RATE_LIMITED vs QUOTA 横向无区分 | 🟡 |
| S-B1 | #10 | 5 模块同时落 4 ADR，无优先级/边界登记 | 🔴 |
| S-B2 | #1 | M11/M14/M17/M19 不引 ADR；模板未要求显式引用 | 🔴 |
| S-C1 | #9 | 5 模块有 §12 形态但 ADR-002 弱引用 | 🔴 |
| S-C2 | #9 + #10 | ADR-002 user_id 必填 vs 系统 cron 任务边界 | 🔴 |
| S-D1 | #12 | Queue 默认重试策略 override 无统一登记位置 | 🟡 |
| S-E1 | #1 | frontmatter R0-1 无 CI/lint 守护 | 🟡 |
| S-E2 | #1 | M01 §10 表头例外未回写模板 | 🟢 |

**前一份 reconcile 7 seam 中的结构性部分**也归类进来：
| S6（前文）| #1 | TimestampMixin 规约定义缺失（横向漏写规则） | 🔴（已修） |
| S5（前文）| #1 | api/queue/base.py TaskPayload 横向漏建 | 🔴（待 M17 前补） |

**未跑 P5 状态机 reachability（2 期 audit）**：预估还能挖出 3-5 个 #6 类 seam。

---

## 7. 结构性根因（喂方法论文章）

### 7.1 共同根因

PRISM-0420 设计阶段实际执行的是"**横向草案 + 模块设计同步演化**"流程，但**没有强制对账机制**：

1. 横向草案没有"模块需求登记"——每条规约不知道有哪些模块在引用
2. 模块设计没有"显式引用清单"——design 顶部不声明引用了哪些 ADR / 哪些 R-X 规约 / 哪些横向 helper 接口
3. 横向草案没有"版本号"——任何变更不知道通知谁
4. 横向草案没有"全局命名空间登记表"——ErrorCode / ActionType / Queue topic 各模块独立起名

### 7.2 防御机制 = 设计阶段的对账契约（4 条）

**对账契约 1：模块 design 顶部强制"引用清单"**
```yaml
references:
  adrs: [ADR-001, ADR-002, ADR-004]   # 必填
  rules: [R3-2, R8-2, R10-2, R13-1, R-X3]  # 必填
  horizontal_helpers:
    - api/errors/codes.py: [USER_NOT_FOUND, ACCOUNT_LOCKED]  # 本模块用了哪些码
    - api/auth/dependencies.py: AuthServiceProtocol@v2
    - api/models/base.py: [TimestampMixin, SoftDeleteMixin]
```

**对账契约 2：横向草案末尾强制"被引用模块清单"**
```yaml
# ADR-002 末尾
referenced_by:
  - M01: P3 refresh token Queue
  - M13: §12A 流式（部分适用）
  - M16: §12B 仅参考契约不走 Queue
  - M17: §12C pilot
  - M18: §12D 派生数据 Queue
unspecified_boundaries:
  - cron-triggered tasks: user_id 字段未规约（待 ADR 补丁）
```

**对账契约 3：全局命名空间登记表**
- `design/00-architecture/08-namespaces.md`（新建）
- 内含：ErrorCode 全清单 / ActionType 全清单 / TargetType 全清单 / Queue topic 全清单
- 每条登记 owner 模块 + 命名风格规范
- CI grep 守护：模块 design 写新码 → 必须在登记表添加一行

**对账契约 4：14 类 seam 的检测自动化**
- 把本 audit 的 5 个 procedure 写成 CI 脚本
- 每模块 PR / 每 ADR 修改触发自动跑
- 至少 P2 namespace collision / P3 ADR matrix 可完全自动化

### 7.3 与今天闸门 2.5 的关系

今天 commit `4860d0d` 加的闸门 2.5 是**事后救火型**对账（每模块开工前跑一次）。

正确版本应在**设计阶段就有上面 4 条契约**，闸门只做"再次确认"而非"首次发现"。

---

## 8. 建议动作

**今晚停在这里——下一步等 CY 拍**：

| 选 | 行动 | 工时 | 决定的事 |
|---|------|------|--------|
| A | 跑 P5 state machine reachability（2 期 audit）| 2-3h | 找 #6 / #5 类 seam |
| B | 对当前 11 个 seam 拍机械 / 等决策 / 暂不修 | 30min | 落地优先级 |
| C | 起草 4 条对账契约的具体形态（写到方法论文章 + 回填到 PRISM-0420）| 3-4h | 把"事后救火"升级为"设计前置" |
| D | 写方法论文章首版（用本文档当素材）| 2h | 跳槽材料 |

预算估计：A + B + C + D ≈ 7-10h（约 1 工作日）。

---

## 9. 关联

- 触发事件：M01 实施前 D1 决策
- 关联前文：[`scaffold-design-reconcile.md`](./scaffold-design-reconcile.md)（7 seam，对错型）
- 方法论沉淀：待写 `ai-quality-engineering/02-技术/架构设计/设计前置-横向与模块的对账机制.md`
- 闸门：[`design/00-phase-gate.md`](../00-phase-gate.md) § 闸门 2.5（事后救火版本）
