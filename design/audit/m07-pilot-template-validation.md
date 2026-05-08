---
title: M07 sprint 实证 + R1/R2 命中比例 + L1 第六数据点
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M07 sprint 闸门 2.5 reconcile 三栏 + R1/R2 review 沉淀。

  - 闸门 2.5 三栏：A 8 / B 0 / C 6（**第三次 B 栏 0 项**：M05 立 / M06 复用 / M07 复用）
  - R1=3 subagent + R2=1 合并 Opus subagent 命中（与 M02-M06 五数据点对照）
  - L1+L2+L3 节奏第六次实证（六数据点稳定 → M08-M20 默认范式可作模板）
  - **R-X2 第三真注入实证（不同语义 orphan，与 M04/M06 delete 行为契约对照）**
  - PT1-PT3 模板复用判定（不复用 PT1+PT3，复用 PT2，已回填 m01 audit）
  - **关键元教训**：M06 立的 P1 范式（viewer 写全端点）在 M07 复发——单条 P1 立修
    不自动横切，需升级到 design 公共段或 testpoint 模板
last_reviewed_at: 2026-05-08
---

# M07 sprint 实证 + Review 命中比例

## 闸门 2.5 reconcile 三栏（M07 sprint 启动当天 / 第三次 B 栏 0 项实证）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 8 | A1 Node back_populates **passive_deletes=True**（与 M04/M06 cascade 不同）/ A2 conftest fixture 复用 / A3 §14.5 默认范式复用 / A4 ck_clause 别名规范化 / A5 R-X2 第三真注入 orphan 语义 / A6 get_for_embedding A 路径（title + description）/ A7 §5 多表事务字面**预防性消歧**（避免 R1-A 再抓 M04/M05/M06 同款漂移）/ A8 batch_create_in_transaction 推迟 |
| **B 待 CY 决策** | **0** | （第三次 B 栏 0 项 / M05 立 / M06+M07 防御未来）|
| **C 已自我消解** | 6 | C1 状态机 + SELECT FOR UPDATE 行锁（design §4 §5 已决）/ C2 idempotency / Queue / 并发 N/A / C3 多表事务 docstring 范式（M02-M06 已立 / A7 顺修）/ C4 reattach 游离 issue（IssueUpdate 已含 node_id）/ C5 cross-project node 校验（design §13）/ C6 tags JSONB tag 查询（DAO 层 contains）|

**A7 预防性消歧创新**：M06 R1-A A1 立修 §5 多表事务字面 "with db.begin():" 漂移
是 sprint 期 R1 抓到的；M07 sprint 启动 reconcile 时主动顺修同款，不让 R1-A 再抓
重复 punt — 这是 M07 sprint 元教训"防御未来非修复存量"机制的进一步实证（除了
B 栏 0 项之外）。

---

## R1 review 命中（3 并行 subagent / 子片 1+2+3 合并审）

### R1-A spec+quality Opus

| 命中 | 项 | 处理 |
|---|---|---|
| P1 | （0 项）— A7 预防性消歧已避免 design §5 漂移 | — |
| P2 #1 | ErrorCode 基类 ValidationError vs design §13 字面 AppError | 子片 5 design 回写注释（M02-M06 同款实装范式）|
| P2 #2 | update 不支持 detach（None→NULL）— Pydantic 默认行为限制 | design §3/§7 reconcile 注释 disambiguation |
| P2 #3 | transition activity_log metadata.assigned_to 仅变更值 vs 当前态 | design §10 注释明确"变更值"语义 |
| P2 #4 | IssueCategoryInvalidError 注释缺失（与 M03 NODE_NAME_EMPTY 同款）| codes.py 加 R13-1 parity 注释 |

### R1-B reuse Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1 | （0 项）| — |
| P2 #1 | _make_issue 单文件内聚（dao test 33 次调用 / service+models 不用）| 预登记 M08+ 跨文件触发时迁 conftest |
| SKIP | 12 项全 SKIP | 横切层 / 范式 / fixture 复用率 ~95% |

**M07 复用率 ~95%**，与 M06 持平或微优。

### R1-C quality+efficiency Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | get_for_embedding 空字符串 falsy 漏判 → text 漏 description | commit 6a1072f 立修：直接 f"{title}\\n{description}" + 补 description="" 测试 |
| P1-02（自评 P2）| transition UPDATE 缺 WHERE status=old_status 谓词（防御未来重构）| punt（自评"P2 若过于前瞻"；事务边界正确时 SELECT FOR UPDATE 行锁串行已防）|
| P2-01 | orphan list↔UPDATE race（M04 R1-C C1.2 同款）| punt M15 升级真 INSERT 时复审 |
| P2-03 | tag JSONB GIN 索引（M13/M16 大量 tag 查询时压力出现）| punt 观察期 |

### R1 命中合计

- **P1 共 1 项**：commit 6a1072f get_for_embedding 空字符串立修
- **P2 共 8 项**进 punt 池
- 与 M02-M06 R1 P1 命中区间（0-4）对照：M07=1，五数据点稳定区间内

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | viewer 写 4 端点未全覆盖（**M06 R2 P1-02 元教训复发**）| commit 8246984 立修：cases 列表遍历 POST/PUT/POST transition/DELETE 4 端点全 403 |
| P2 #1 | IssueResponse 漏 design §7 join 字段（node_name / created_by_name / assigned_to_name）| punt M13/M15 集成期补 + design 回写 disambiguation |
| P2 #2 | IssueListResponse 漏 design §7 page_size 分页（M02-M06 默认 limit-only 范式）| 横切 disambiguation 注释（M07 design §7 表脚或 design/00-architecture 列表分页规约）|

**R2 命中**：1 P1（M06 元教训复发立修）+ 2 P2 + 多 SKIP — 与 M02-M06 R2 P1 命中
0-1 区间稳定。

---

## R-X2 第三真注入实证（M04 第一 / M06 第二 / M07 第三 — 三数据点 + 不同语义对照）

### 关键差异：orphan vs delete

| 方面 | M04 DimensionService | M06 CompetitorService | M07 IssueService |
|---|---|---|---|
| 接口名 | delete_by_node_id | delete_by_node_id | **orphan_by_node_id** |
| 行为 | DELETE FROM dimension_records | DELETE FROM competitor_refs | **UPDATE issues SET node_id = NULL** |
| FK | ondelete=CASCADE | ondelete=CASCADE | **ondelete=SET NULL** |
| Node ⇄ children relationship | cascade='all,delete-orphan' | cascade='all,delete-orphan' | **passive_deletes=True**（无 cascade）|
| activity_log action_type | "delete" | "delete" | **"orphan"** + metadata 含 cascade_source |
| Protocol 4 参签名 | `(db, node_id, project_id, actor_user_id)` | 同款 | 同款（**接口共享 / 行为分化**）|

**5 步分层分析法实证**：M04 sprint 升级 Protocol 4 参时把 actor_user_id 作为
跨模块契约层（L1）共享字段；M06 第二真注入复用零摩擦；M07 第三真注入**接口共享
但行为契约不同**——证明 L1 契约设计的关键是"参数签名 + 异常契约"统一，而**业务
语义（DELETE vs UPDATE SET NULL）属于 L2 模块决策**，不需要拉到 L1 强制一致。

### orphan 语义代码层 anchor（防误读）

design / model / migration / DAO / service / Protocol / lifespan 共 **7 处**显式
标注 orphan 语义（与 M04/M06 cascade delete 对照）：

1. design §3 Alembic 要点："node_id 外键：ON DELETE SET NULL（节点删除后 issue 变游离）"
2. api/models/issue.py 头部 docstring + Issue.node 注释
3. api/models/node.py Node.issues relationship 注释（passive_deletes=True 解释）
4. api/dao/issue_dao.py 头部 docstring + orphan_by_node_id 方法 docstring
5. api/services/issue_service.py 头部 docstring "**orphan 语义**"
6. api/services/node_service.py NodeChildrenServiceProtocol docstring target_type 分发表（已有 / M04 sprint 立）
7. api/main.py lifespan 注释 "**第三真注入（orphan 语义）**"

**多 anchor 防御**：M04/M06 reviewer 不会误以为 M07 也是 cascade delete；下一
模块 reviewer 不会误以为 R-X2 是统一 delete 语义。

---

## Punt 池总表（M07 sprint 末 8 项）

| 来源 | # | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|---|
| R1-A P2-1 | 1 | ErrorCode 基类 ValidationError vs design §13 字面 | P3 | 子片 5 design 回写注释 |
| R1-A P2-2 | 2 | update 不支持 detach（None→NULL）| P2 | design §3/§7 reconcile 注释 + 产品决策 |
| R1-A P2-3 | 3 | transition activity_log metadata.assigned_to 范围 | P3 | design §10 注释明确"变更值" |
| R1-A P2-4 | 4 | IssueCategoryInvalidError R13-1 parity 注释 | P3 | M08 sprint 启动前一并清 |
| R1-B P2-1 | 5 | _make_issue 跨文件触发时迁 conftest | P3 | M08+ sprint 启动前评估 |
| R1-C P1-02 | 6 | transition UPDATE 加 WHERE status=old_status 谓词（防御未来）| P2 | 未来重构事务边界时复审 |
| R1-C P2-01 | 7 | orphan list↔UPDATE race（M04 同款）| P2 | M15 升级 write_event 真 INSERT 时复审 |
| R1-C P2-03 | 8 | tag JSONB GIN 索引 | P3 | M13/M16 上线前评估 |
| R2 P2-1 | 9 | IssueResponse 漏 join 字段 | P2 | M13/M15 集成期补 + design 回写 |
| R2 P2-2 | 10 | IssueListResponse 漏分页（M02-M06 默认）| P3 | 横切 disambiguation 注释 |

---

## L1+L2+L3 节奏第六次实证（M02-M07 — 六数据点稳定）

| 节奏层 | M07 sprint 表现 | 与 M02-M06 差异 |
|---|---|---|
| L1 总则 | ✅ 全合规：R1+R2 共 2 次 review | 与 M02-M06 一致 |
| L2 sprint 计划（design §14.5）| ✅ 默认范式复用简写（M06 立 / M07 第二次复用）| 与 M06 一致 |
| L3 实证回写（本文件）| ✅ accepted | 与 M02-M06 同款 |

**六数据点稳定结论**：M08+ sprint 默认范式可不再重复说明，§14.5 段可仅引用
本 audit "默认范式复用"。

---

## PT1-PT3 复用判断（已回填到 m01-pilot-template-validation.md）

- **PT1**：❌ 不复用 — M07 是问题沉淀主表，所有字段必须可用；M18 baseline-patch 已实装
- **PT2**：✅ 复用 — Router check_project_access 走 ADR-004
- **PT3**：❌ 不复用 — M07 无预留 model

---

## 元教训（M07 sprint 新增）

### 新增 1 — R-X2 接口共享但行为契约分化的 L1/L2 边界

**触发**：M07 是 R-X2 第三真注入方，行为契约（orphan UPDATE SET NULL）与 M04/M06
（delete CASCADE）不同。M04 sprint 升级 Protocol 4 参时把 actor_user_id 作为
L1 跨模块契约层共享，但行为语义留给 L2 模块自决。

**关键决策点**：L1（Protocol 签名 + 异常契约）vs L2（业务行为语义）的边界。

**实证**：M07 接 4 参 Protocol 零摩擦，但内部 orphan 语义需 7 处代码层 anchor
显式标注（防误读）。L1 契约统一 ≠ L2 行为统一；多 anchor 防御是 L2 分化场景的
配套机制。

**沉淀**：本 audit R-X2 三数据点对照表 + 7 处 anchor 清单作未来 R-X2 第四+ 真注入
方设计参考。

### 新增 2 — **R2 P1-01 元教训仪式化提示但未真实施**（M06 范式复发）

**触发**：M06 R2 立的 P1-02 范式 "viewer 写**所有**写端点 403 测试" 在 M07 复发：
- M07 sprint R2 prompt 在"特别关注"段提示了"M07 是否需要补 PUT/DELETE/transition
  viewer 测试"
- 但 sprint 实施 子片 4 时仍只测 POST 一个端点
- R2 reviewer 抓到 → 立修（commit 8246984）

**关键决策点**：单条 P1 立修不自动横切到下一模块。

**根因**：
- prompt 提示是 reviewer 的注意力引导，不是实施时的 enforce
- 立的范式纯靠"下一 sprint reviewer 比对 M_{N-1} audit punt 池"被动传递
- 仪式化提示（"特别关注"段提了）≠ 实施时真做（写测试时仍漏）

**沉淀**：
- feedback_problem_layered_analysis 失效信号新增"元教训仪式化提示但未真做实施"
  + 修法："跨模块测试契约升到 design 公共段（如 design/00-architecture/06-design-principles.md
  或测试模板），让模块 design 必须含 X testpoint"
- M08+ sprint 启动 reconcile 时 grep design §8 三层权限段是否含"viewer 写**所有**
  写端点 403"模板要求 — 本 sprint 不做（design 公共段升级是横切修复，不属 M07 范围）；
  punt 到 M08 sprint 启动前由 CY 决定是否升级到 design 公共段

**复用价值**：M07 是该元教训的第一次"复发 + 应用立修"实证 — 验证了"P1 立修不
自动横切"是真问题，需要横切机制（design 公共段 / lint / testpoint 模板）解决。

### 复用 1 — feedback_problem_layered_analysis 闸门 2.5 自审

第三次 B 栏 0 项实证：5 步分层 step 1-2 grep 既有规则 + 自审"我倾向的恰好是
范式机械应用" — 8 项原候选全 grep 命中 L1/L3 锁规归 A 栏。

### 复用 2 — feedback_design_scaffold_reconcile

A7 §5 多表事务字面预防性消歧 — M06 R1-A A1 sprint 期立修，M07 sprint 启动
reconcile 时主动顺修同款，不让 R1-A 再抓重复 punt（防御未来非修复存量）。

---

## 维护规则

- 本文件 status=accepted（M07 sprint 关闸时）
- M08 sprint 启动闸门 2.5 reconcile pass 时复用本文件 R1/R2 命中比例 + punt 池
- M11/M17 sprint 启动时 batch_create_in_transaction 接通（与 M04/M06/M07 同款 punt）
- M13 sprint 启动时 IssueService.list_by_project 跨模块调用契约直接消费（已 pass-through，无代码改动）
- M15 sprint 升级真 INSERT 时复审 R1-C P2-01 orphan list↔UPDATE race
- M16 sprint 上线前评估 R1-C P2-03 tag JSONB GIN 索引
- **元教训复发防御**：M08 sprint 启动 reconcile 时主动比对 M02-M07 R1/R2 punt 池中
  立的"跨模块测试契约"项（如 viewer 写全端点 / write_event 异常传播 / 等），
  sprint 实施时主动复制（不等 R2 抓）— 这是 M07 R2 P1-01 元教训的 actionable 防御
