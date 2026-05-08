---
title: M08 sprint 实证 + R1/R2 命中比例 + L1 第七数据点
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M08 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀。

  - 闸门 2.5 三栏：A 7 / B 0 / C 6（**第四次 B 栏 0 项**）
  - R1=3 subagent + R2=1 合并 Opus subagent（与 M02-M07 六数据点对照）
  - L1+L2+L3 节奏第七次实证（七数据点稳定 → M09+ 默认范式可作模板）
  - **R-X2 第四真注入实证（双向 OR + delete 语义）**：与 M04/M06 同 delete / 与 M07
    orphan 对照；接口共享行为契约分化第二次实证
  - **元教训"M07 P1 防御 actionable 主动应用"首次实证**：M07 立的"viewer 写所有
    写端点 403 全覆盖"P1 范式在 M08 sprint 实施时主动写不等 R2 抓 / R2 没抓出新点
    = 元教训内化生效
last_reviewed_at: 2026-05-08
---

# M08 sprint 实证 + Review 命中比例

## 闸门 2.5 reconcile 三栏（M08 sprint 启动当天 / 第四次 B 栏 0 项实证）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 7 | A1 §14.5 默认范式段补 / A2 §5 多表事务**预防性消歧**（M06+M07 立修延续）/ A3 ck_clause 别名 / A4 R-X2 第四真注入（双向 + delete 语义；与 M07 orphan 对照）+ lifespan / A5 IntegrityError 区分约束名（M05 立规延续）/ A6 search_by_keyword pass-through M09 / **A7 元教训防御 actionable 主动复制**：viewer 写**所有**写端点 403 / write_event 异常传播 / cross-tenant 404 / cross-project node 422 / IntegrityError 区分约束名 |
| **B 待 CY 决策** | **0** | （第四次 B 栏 0 项 / M05 立 / M06+M07+M08 复用稳定）|
| **C 已自我消解** | 6 | C1 双向关系策略（候选 A 三元组唯一已决）/ C2 relation_type 枚举（3 值已决）/ C3 self-loop 双重防护已决 / C4 Node back_populates（design 字面无要求；FK CASCADE + R-X2 显式注入兜底）/ C5 idempotency / Queue / 状态机 N/A / C6 batch_create_in_transaction 推迟 M11/M17 |

---

## R1 review 命中（3 并行 subagent）

### R1-A spec+quality Opus

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | RelationTypeInvalidError R13-1 parity 注释（与 M03 NODE_NAME_EMPTY 同款）| commit `868d290` 立修 |
| P1-02 | Service docstring R-X2 vs FK CASCADE 双重防御消歧 | commit `868d290` 立修 |
| P1-03 | NodeChildrenServiceProtocol docstring 加 module_relation 第 4 项 target_type 分发表 | commit `868d290` 立修 |
| P2 多 | search_by_keyword 签名 disambiguation / `RelationNodeNotInProjectError` 继承 ValidationError 等 | 部分 punt 部分立修 |
| SKIP | 多 | C 栏决议 + 已立范式 |

### R1-B reuse Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | _make_relation 进 conftest（M04+M05+M06+M07 五连规则延续 / make_module_relation fixture）| commit `868d290` 立修；test_m08_dao.py 13+ 调用迁 fixture |
| P1-02（CY 升 R1-B）| RelationNodeNotInProjectError 404 → 422（M06+M07 范式对齐：跨 project 引用校验 = 422 validation 而非 404 资源不存在）| commit `868d290` 立修 + test 改 422 |

**M08 复用率 ~95%**（横切层 / 范式 / fixture 全命中）。

### R1-C quality+efficiency Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | count_by_project 走 index-only scan（count(*) 优化；M07 P1 同款延续）| commit `868d290` 立修 |
| P1-02 | _check_nodes_belong_to_project asyncio.gather 并行（节省 1 RTT）| commit `868d290` 立修 |
| P2 #1+P2 #2 | delete_by_node_id race window（M04 R1-C C1.2 / M07 同款）| punt M15 升级 INSERT RETURNING 时复审 |
| P2 #3 | count_by_project 用 func.count() 不加列名（合规 M05 P2-03）| ✅ 合规 |
| P2 #4 | search_by_keyword ilike 无 GIN 索引（M07 P2-03 同款）| punt M13/M16 数据量上量评估 |

### R1 命中合计

- **P1 共 7 项**：commit `868d290` 全部立修（5 步分层全 L3 范式应用 — 都是延续既有立规 / 范式机械应用，非新决策）
- **P2 共多项**进 punt 池
- 与 M02-M07 R1 P1 命中（0-4）对照：M08 = 7（其中 5 项是 M02-M07 立的范式延续机械应用，2 项 R1-C 性能优化）— **第七数据点稳定区间内（含五连规则延续）**

---

## R2 review 命中（1 合并 Opus subagent）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | self_loop code 映射缺失（design §13 ValidationException Handler 字面 drift）| 立修：移除 schema 层 model_validator，service 层独家 raise RelationSelfLoopError → middleware 翻 code=relation_self_loop（M02-M07 service-only 范式延续）+ test 改断 422 + code |
| P2 #1 | design §7 列 6 endpoints 但实装 5（DELETE /nodes/{nid}/relations 走 R-X2 lifespan 不暴露 HTTP / 与 M07 同款）| punt 子片 5 design 回写 disambiguation 注释 |
| P2 #2 | §8 vs §13 自相矛盾（"不暴露 forbidden 信息" vs RelationNodeNotInProjectError message 暴露）| punt design 回写决议 |
| SKIP | 5 | 12 e2e tests viewer 写 3 端点全覆盖（**M07 元教训防御 actionable 主动写命中**——R2 没抓出新点，验证元教训内化生效）|

**R2 命中**：1 P1（self_loop code 映射）+ 2 P2 + 多 SKIP — 与 M02-M07 R2 P1 命中
0-1 区间稳定；**第七数据点稳定（M08 R2 = 1 P1）**。

---

## R-X2 实证对照（M04 第一 / M06 第二 / M07 第三 / M08 第四 — 四数据点 + 行为契约分化）

| 方面 | M04 dim | M06 competitor | M07 issue | M08 module_relation |
|---|---|---|---|---|
| 接口名 | delete_by_node_id | delete_by_node_id | **orphan_by_node_id** | delete_by_node_id |
| DB 行为 | DELETE | DELETE | **UPDATE SET NULL** | DELETE（双向 OR）|
| FK | ondelete=CASCADE | CASCADE | **SET NULL** | CASCADE |
| Node back_populates cascade | all,delete-orphan | all,delete-orphan | **passive_deletes=True** | （无；FK CASCADE 兜底）|
| activity_log action_type | delete | delete | **orphan** | delete |
| 双向 OR | 否 | 否 | 否 | **是**（source / target 两 FK）|
| Protocol 4 参签名 | 共享 | 共享 | 共享 | 共享 |

**关键实证**：Protocol（参数签名 + 异常契约）属 L1 跨模块共享层；行为契约（DELETE
vs UPDATE SET NULL vs 双向 OR）属 L2 模块决策层。**接口抽象稳定 + 业务语义分化**
是合理设计。

---

## Punt 池总表（M08 sprint 末 ≥6 项）

| 来源 | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|
| R1-C P2-01/02 | delete_by_node_id race window（M04/M07 同款）| P2 | M15 升级真 INSERT 时复审 |
| R1-C P2-04 | search_by_keyword ilike 无 GIN 索引（M07 同款）| P3 | M13/M16 数据量上量评估 |
| R2 P2-1 | design §7 6→5 endpoints 回写 disambiguation | P3 | 子片 5 落 design |
| R2 P2-2 | §8 vs §13 自相矛盾（tenant info leak design layer）| P3 | 子片 5 决议 |
| R1-A 多项 | search_by_keyword 签名 disambiguation 等 | P3 | 后续 sprint 顺手清 |

---

## L1+L2+L3 节奏第七次实证（M02-M08 — 七数据点稳定）

| 节奏层 | M08 sprint 表现 | 与 M02-M07 差异 |
|---|---|---|
| L1 总则 | ✅ R1+R2 共 2 次 review | 与 M02-M07 一致 |
| L2 sprint 计划（design §14.5）| ✅ 默认范式复用 | 与 M06+M07 一致 |
| L3 实证回写（本文件）| ✅ accepted | 与 M02-M07 同款 |

**七数据点稳定结论**：M09+ sprint 默认范式不再重复说明。

---

## PT1-PT3 复用判断（已回填到 m01-pilot-template-validation.md）

- **PT1**：❌ 不复用 — M08 主表全字段必须可用；search_by_keyword R-X3 已实装非"预留"
- **PT2**：✅ 复用 — Router check_project_access 走 ADR-004
- **PT3**：❌ 不复用 — M08 无预留 model

---

## 元教训（M08 sprint 新增）

### 新增 1 — R-X2 接口共享 + 行为契约分化第二次实证（含双向语义）

**触发**：M08 是 R-X2 第四真注入方，行为契约（双向 OR + delete）与 M04/M06（单向
delete）+ M07（orphan）都不同，但 Protocol 4 参签名共享。

**关键决策点**：L1（Protocol）vs L2（行为契约）边界第二次验证。

**实证**：
- M04→M06：delete 语义复用零摩擦（M06 第二真注入零摩擦元教训首次产出）
- M06→M07：orphan 语义需 7 处代码 anchor 防误读（M07 元教训首次产出）
- M07→M08：双向 OR + delete 既不是 M04/M06 单向 delete 也不是 M07 orphan，**第三种行为契约**实证 — 接口仍稳定，仅业务语义层 doc 标注

**沉淀**：feedback_problem_layered_analysis 实证 R-X2 是"L1 接口锁 + L2 行为分化"
合理抽象的样板范式（4 数据点 = 单向 delete x2 / orphan x1 / 双向 delete x1）。

### 新增 2 — **元教训"M07 P1 防御 actionable 主动应用"首次实证**

**触发**：M07 R2 P1-01 立修后，元教训沉淀到 feedback_problem_layered_analysis
失效信号（"立的元教训不会自动横切"）。M08 sprint 启动闸门 2.5 reconcile 主动列
A7 项"M02-M07 punt 池跨模块测试契约**主动复制不等 R2 抓**"（viewer 写所有
写端点 403 / write_event 异常传播 / cross-tenant 404 / cross-project node 422 /
IntegrityError 区分约束名 5 项）。

**实施验证**：
- 子片 4 router test 写时主动包 viewer 写**所有** 3 端点（POST/PATCH/DELETE）
  cases 列表全覆盖
- 子片 3 service test 写时主动包 write_event 异常传播 monkeypatch
- R2 reviewer 没抓出 viewer 写覆盖问题（与 M07 R2 P1-01 复发对照）

**关键决策点**：单条 P1 立修不自动横切的修复机制——**sprint 启动 reconcile 主动列**
"M02-M_{N-1} 跨模块测试契约清单"——这是 audit 层 actionable 防御。

**沉淀**：本 audit 元教训章作 M09+ sprint 启动 reconcile 时**直接复制清单**的范本。

### 复用 1 — feedback_problem_layered_analysis B 栏 0 项

第四次 B 栏 0 项 — 5 步分层 step 1-2 grep 既有规则 + 自审"我倾向的恰好是范式
机械应用？" 7 项原候选全 grep 命中 L1/L3 锁规归 A 栏。

### 复用 2 — feedback_design_scaffold_reconcile A2 §5 预防性消歧

M06 + M07 + M08 三次连续主动顺修 §5 多表事务字面 with db.begin() 漂移，避免 R1-A
反复抓重复 punt。

---

## 维护规则

- 本文件 status=accepted（M08 sprint 关闸）
- M09 sprint 启动闸门 2.5 reconcile 时复用本文件 R1/R2 命中比例 + punt 池 +
  **元教训防御 actionable 清单**（A7 5 项主动复制范式）
- M09 superseded by M18（不实装）；下一站 M10
- M11/M17 sprint 启动时 batch_create_in_transaction 接通（M04/M06/M07/M08 同款 punt）
- M13 sprint 启动时 IssueService.list_by_project + ModuleRelationService.search_by_keyword
  跨模块调用契约直接消费（已 pass-through，无代码改动）
- M15 sprint 升级真 INSERT 时复审 R1-C P2-01 race window
- M13/M16 数据量上量评估 search_by_keyword GIN 索引
