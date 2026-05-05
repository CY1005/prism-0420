---
title: 4 条对账契约草案 — 从结构性 audit 到设计阶段强制限制
status: draft
owner: CY
created: 2026-05-06
trigger: full-reconcile-pass.md 11 seam 根因诊断（5 条限制位空着）
---

# 4 条对账契约草案

## 0. 上下文

[`full-reconcile-pass.md`](./full-reconcile-pass.md) 找到 11 个结构性 seam，根因诊断：5 条限制位空着 + audit agenda 只看纵向。

本草案给 4 条对账契约的**具体形态**，作为下一步回填 PRISM-0420 + 喂方法论文章的素材。每条契约写"做什么 / 形态 / 回填动作 / 应用范围 / 解决哪些 seam"。

---

## 1. 契约 1 — 模块 design 顶部强制 `references` 清单

### 做什么

每个模块 design 的 frontmatter 强制声明本模块引用了哪些横向项。**design 写完时填，三轮 audit 第一轮就检查**。

### 形态（扩展 frontmatter 12 字段 → 13 字段）

```yaml
---
title: M01 用户账号 - 详细设计
status: accepted
owner: CY
created: 2026-04-24
accepted: 2026-04-24
module_id: M01
prism_ref: F1
pilot: true
complexity: high
# ↓↓↓ 新增 references 字段（强制）↓↓↓
references:
  adrs:                                  # 必填，本模块依赖的 ADR
    - { id: ADR-001, adopts: [§4 db session] }
    - { id: ADR-002, adopts: [P3 refresh token Queue] }
    - { id: ADR-003, adopts: [规则 1 上游 Service 调用] }
    - { id: ADR-004, adopts: [P1, P2, P3] }
  rules:                                 # 必填，本模块声明遵守的横向规约
    - R3-2  # 状态字段三重防护
    - R8-1  # 三层权限
    - R10-2-exception  # auth_audit_log 例外
    - R11-2  # idempotency 含 project_id
    - R13-1  # ErrorCode ↔ AppError 对账
  helpers:                               # 必填，本模块用了哪些横向 helper
    errors:
      version: v3
      codes_used:                        # 用了哪些通用码
        - UNAUTHENTICATED
        - PERMISSION_DENIED
      codes_added:                       # 本模块新增的码（17 个，见 §13）
        - USER_NOT_FOUND
        - ACCOUNT_LOCKED
        # ... 其余 15 个
    auth:
      protocols: [AuthServiceProtocol@v2]
    models:
      mixins: [TimestampMixin]
  cross_module_reads:                    # 必填，跨模块 model 直读（ADR-003 规则 2 豁免）
    - module: 无                         # M01 不直读其他模块
  consumes_action_types: []              # 本模块订阅 M15 哪些 action_type
  produces_action_types:                 # 本模块写哪些 action_type 进 M15
    - login.success
    - login.failed
    - password.changed
    # ...
---
```

### 强制点

- `references.adrs` / `references.rules` / `references.helpers` 三项**不能为空数组**（确实无依赖也要填 `[no_dependency]` + 注释说明）
- 新模块开工前先填 references → 才能写正文
- 三轮 audit 第一轮先核 references 完整性（横向 Lint 优先于纵向内容审）

### 回填动作（PRISM-0420 已 accepted 20 模块）

- 所有模块 frontmatter 新增 `references` 段（一次批量回填）
- 工时：每模块 10-15 分钟 × 20 = 4-5 小时
- 验证：跑脚本扫"references.adrs 中声明的 ADR 是否真实存在 / rules 中声明的规约是否真实存在 / helpers 声明的 codes 是否在命名空间登记表"

### 解决的 seam

- S-B1（ADR Interaction Blind Spot）：5 模块同时落 4 ADR 显形 → audit 自然问"4 ADR 同时适用边界怎么办"
- S-B2（M11/M14/M17/M19 0 引用 ADR）：必填字段强制暴露
- S-A1（NOT_FOUND 命名漂移）：codes_added 字段强制 → 模块设计师写时必须查命名空间登记表

---

## 2. 契约 2 — 横向草案末尾强制 `referenced_by` 反向链

### 做什么

每个 ADR / engineering-spec § / R-X 规约文档**末尾加段反向登记**：哪些模块引用了我、各自适用范围、已发现的边界盲区。

### 形态（每个 ADR / 规约文档末尾段）

```yaml
## referenced_by

# 横向文档维护这段，与契约 1 的 module-side 引用清单形成双向链
referenced_by:
  - module: M01
    accepted_at: 2026-04-24
    adopts: [P1, P2, P3]                    # 引用本 ADR 的哪些条款
    partial: false                          # 是否部分适用
    note: ""
  - module: M13
    accepted_at: 2026-04-25
    adopts: [P1]
    partial: true
    note: "仅 P1 用，P2 流式无内部签名场景；ADR-002 §横切影响段落已记录"
  - module: M16
    accepted_at: 2026-04-25
    adopts: []
    partial: true
    note: "fire-and-forget 不走 Queue，仅参考 TaskPayload 契约形态；详见 M16 §12B"

# 已发现但未规约的边界盲区
unspecified_boundaries:
  - id: 2026-05-06-cron-task-no-user
    description: "cron 触发任务的 user_id 字段未规约（M16 zombie / M18 backfill）"
    discovered_at: 2026-05-06
    discovered_by: full-reconcile-pass.md S-C2
    status: pending_adr_patch              # pending_adr_patch / accepted_with_workaround / wontfix
    proposal: "ADR-002 § 1 加边界条款 - cron 任务 user_id = system_uuid"
```

### 强制点

- 横向文档变更（ADR 修订 / 规约新增）→ 必须同步更新 `referenced_by`
- `unspecified_boundaries` 段是**横向规约的覆盖盲区登记** —— 每发现一个 seam 在这里登记，闭环到 `pending_adr_patch` → `accepted_with_workaround` 或 `accepted_into_main_rule`
- CI 守护：模块 references.adrs 中声明 `ADR-002.adopts: [P3]` → ADR-002 文件 referenced_by 必须有这个模块（双向校验）

### 回填动作（PRISM-0420）

- 5 个 ADR 各加 referenced_by 段
- engineering-spec 主要节（§ 7 ErrorCode / § 8 权限 / § 12 Queue）各加 referenced_by 段
- 02-modules/README.md 中 R-X 规约（约 25 条）各加 referenced_by 段（可缩为简表）
- 工时：5 ADR × 30min + 5 spec 节 × 30min + 25 R-X × 5min = 6-7 小时

### 解决的 seam

- 横向变更通知机制（S6 / S7 / S3 那种"横向改了名模块没跟"全自动）
- S-C1（5 模块有 §12 但 ADR-002 弱引用）：reverse link 立刻显形
- S-A4（RATE_LIMITED vs QUOTA 未区分）：通过 unspecified_boundaries 闭环

---

## 3. 契约 3 — 全局命名空间登记表

### 做什么

新建一份**全项目共享标识符**的集中登记表，作为单一真相源。

### 形态（新文件 `design/00-architecture/08-namespaces.md`）

文件分 4 张登记表 + 命名规范段：

```markdown
# 全局命名空间登记

> 单一真相源。所有模块新增标识符前先查本表，新增后必须登记一行。

## 1. ErrorCode 全局命名空间

### 1.1 命名规范

- **N1（实体未找到）**：用模块前缀 + `_NOT_FOUND` 后缀，不复用横向 NOT_FOUND
  - ✅ `USER_NOT_FOUND` / `PROJECT_NOT_FOUND` / `NODE_NOT_FOUND`
  - ❌ M01 用横向 NOT_FOUND + details.entity_type='user'
- **N2（配额超限）**：用 `XXX_QUOTA_EXCEEDED`（用户级额度）；横向 RATE_LIMITED 仅指调用频率限制
- **N3（权限拒绝）**：优先用横向 PERMISSION_DENIED；模块特殊语义（如 SELF_DOWNGRADE_FORBIDDEN）可加 `_FORBIDDEN`
- **N4（认证）**：用横向 UNAUTHENTICATED / ACCESS_TOKEN_EXPIRED / REFRESH_TOKEN_EXPIRED / ACCOUNT_LOCKED；模块不重定义
- **N5（乐观锁）**：用横向 VERSION_CONFLICT；模块业务"版本"概念不能用 VERSION 前缀

### 1.2 通用码登记（横向 owner）

| code | http | owner | 用途 | 命名规范 |
|------|------|-------|------|---------|
| INTERNAL_ERROR | 500 | api/errors | unhandled fallback | — |
| NOT_FOUND | 404 | api/errors | 通用资源未找到（实测不直接用，模块用 N1）| — |
| PERMISSION_DENIED | 403 | api/errors | 通用权限拒绝 | N3 |
| VALIDATION_ERROR | 422 | api/errors | 输入校验失败 | — |
| CONFLICT | 409 | api/errors | 通用冲突 | — |
| RATE_LIMITED | 429 | api/errors | 调用频率限制 | N2 |
| UNAUTHENTICATED | 401 | api/errors | 未认证 | N4 |
| ACCESS_TOKEN_EXPIRED | 401 | api/errors | access token 过期 | N4 |
| REFRESH_TOKEN_EXPIRED | 401 | api/errors | refresh token 过期 | N4 |
| ACCOUNT_LOCKED | 423 | api/errors | 账号锁定 | N4 |

### 1.3 模块特化码登记（125 条）

| code | http | owner | wraps_from | 命名规范 | 引入 |
|------|------|-------|-----------|---------|------|
| USER_NOT_FOUND | 404 | M01 | — | N1 | M01 §13 |
| INVALID_CREDENTIALS | 401 | M01 | UNAUTHENTICATED | N4 wrap | M01 §13 |
| ACCOUNT_DISABLED | 403 | M01 | — | — | M01 §13 |
| ... | | | | | |

（可写脚本批量提取 + 检测命名规范违规）

---

## 2. ActionType / TargetType 全局命名空间（M15 owns）

### 2.1 命名规范

- **A1**：用 snake_case 单词（不允许 dot.notation 或前缀风格）
  - ✅ `create / update / delete / archive / move`
  - ❌ `cold_start.create`（应改 `cold_start_create`）
- **A2**：模块特化动作用 `{module_prefix}_{verb}` 形式
  - ✅ `cold_start_create / snapshot_create / import_create`
  - ❌ `team_member_promoted_admin`（过长，建议 `member_promoted` + detail.to_role=admin）
- **A3**：用 `_triggered` 后缀仅限"触发但未完成"的事件
  - ✅ `embedding_model_upgrade_triggered`

### 2.2 ActionType 登记（XX 条）

| action_type | producer 模块 | target_type | metadata 必填字段 | 命名规范 |
|-----|-----|-----|-----|-----|
| create | 通用 | * | — | A1 |
| update | 通用 | * | — | A1 |
| delete | 通用 | * | — | A1 |
| login_success | M01 | user | ip, user_agent | A2 |
| ... | | | | |

### 2.3 TargetType 登记

| target_type | owner 模块 | 备注 |
|-----|-----|-----|
| user | M01 | |
| project | M02 | |
| node | M03 | |
| ... | | |

---

## 3. Queue Topic 全局命名空间

### 3.1 命名规范

- **Q1**：topic 名 = `{module}_{task_type}`，全 snake
- **Q2**：所有 payload 必继承 `api/queue/base.py:TaskPayload`
- **Q3**：cron 触发的任务 user_id 字段填 `system_uuid` 常量（边界规约）

### 3.2 Topic 登记

| topic | producer | consumer | payload class | 重试策略 | 死信通知 |
|-----|-----|-----|-----|-----|-----|
| ai_import_task | M17 router | M17 worker | ImportTaskPayload | 3次指数退避 | 用户通知 |
| ai_snapshot_task | M16 router | M16 worker | SnapshotTaskPayload | 不重试 | 手动重发 |
| embedding_text_task | M18 cron | M18 worker | EmbedSinglePayload | 失败容忍 | 不通知 |
| ... | | | | | |

---

## 4. Pydantic Schema 命名规范

- **S1**：输入 schema 用 `XxxIn` 后缀（不用 XxxRequest / XxxCreate）
- **S2**：输出 schema 用 `XxxOut` 后缀
- **S3**：内部传递用 `XxxData`
- **S4**：Pydantic schema 文件位置 `api/schemas/{module}_schema.py`

```

### 强制点

- 模块 design 写新码 / 新 action_type / 新 topic → CI 跑 grep 必在登记表添加一行
- 命名规范 N1-N5 / A1-A3 / Q1-Q3 / S1-S4 由 CI 强制（pre-commit hook + grep）

### 回填动作（PRISM-0420）

- 提取 125 个 ErrorCode + M15 ActionType enum + 所有 §12 topic → 一次性建表
- 工时：4-6 小时

### 解决的 seam

- S-A1 / S-A2 / S-A3：所有命名空间冲突
- S-C2：Queue topic 表中 cron 任务的 user_id 边界明确

---

## 4. 契约 4 — 14 类 seam 自动化检测 + audit agenda 加横向项

### 做什么

把今天 audit 的 5 个 procedure 中可自动化部分**写成 CI 脚本** + 在三轮 audit agenda 中**追加"横向对账三轮"**。

### 4.1 CI 脚本（部分自动化）

新建 `scripts/structural-audit.sh`：

| Procedure | 自动化程度 | 实现 |
|-----------|----------|-----|
| P1 Rule × Module 矩阵 | 80% | grep 提取每模块引用的 R-X，对比 README 全集；输出"未引用任何规约的模块"清单 |
| P2 Namespace collision | 100% | grep 提取所有 ErrorCode / ActionType / topic，跑 sort | uniq -d 找重；查命名规范违规 |
| P3 ADR × Module 矩阵 | 100% | 同上，找 ≥3 ADR overlap 模块 |
| P4 Queue contract | 60% | grep §12 形态 vs ADR-002 引用，找弱引用 |
| P5 State machine reachability | 20% | 难自动化（需理解语义），仅辅助：grep 模块对其他模块 service 调用，给人工 review |

### 4.2 audit agenda 加横向项

02-modules/README.md "三轮 audit" 流程加新一节："**横向对账三轮**"，独立于纵向（模块 self-completeness）三轮：

```
横向对账三轮（每模块 accepted 前必须）：
  R1（references 完整性）：跑 P2 + P3 自动 + 人工核 references YAML
  R2（覆盖盲区）：跑 P1 自动 + 人工核 unspecified_boundaries
  R3（命名空间）：跑 namespace 登记表对账
```

### 强制点

- 模块 design accepted 前 → 横向对账三轮全 ✅
- 横向 ADR / 规约修改 → 跑全量 P2 + P3 自动扫
- 命名空间登记表新增条目 → 命名规范 lint 自动跑

### 回填动作（PRISM-0420）

- 写 `scripts/structural-audit.sh`（新建）
- pre-commit hook 加 structural-audit
- 02-modules/README.md 加横向对账三轮段
- 工时：3-4 小时

### 解决的 seam

- 系统性兜底：未来新模块 / 横向修订自动跑 14 类 seam 检测，不依赖人记得跑

---

## 5. 实施顺序建议

| Phase | 契约 | ROI | 工时 | 推荐时机 |
|-------|------|-----|------|---------|
| 1（高 ROI 低成本）| 契约 1 + 契约 3 骨架 | 立即解决 5 个 seam | 8-10h | M01 实施前必做 |
| 2（中成本）| 契约 2（5 ADR 反向链）| 解决 4 个 seam + 长期防御 | 6-7h | Phase 2.1 完成前 |
| 3（基础设施）| 契约 4（CI + audit agenda）| 长期兜底 | 3-4h | Phase 2.1 中 |

**建议本次 sprint 先做 Phase 1 的契约 1 + 契约 3 骨架（不必填全 125 条 ErrorCode），其余 Phase 2/3 排到后续 sprint**。

---

## 6. 关联

- 触发：[`full-reconcile-pass.md`](./full-reconcile-pass.md) § 7 根因诊断
- 喂方法论文章：
  - `ai-quality-engineering/50-工具与方法论/设计与决策/怎么找出软件设计中的结构性问题.md`
  - `ai-quality-engineering/50-工具与方法论/设计与决策/设计阶段如何避免结构性漂移.md`
- 闸门：闸门 2.5（事后救火）将逐步被本契约（设计前置）取代
