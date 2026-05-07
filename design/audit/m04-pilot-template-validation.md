---
title: M04 sprint 实证子选项 + R1/R2 命中比例 + L1 第三数据点
status: accepted
owner: CY
created: 2026-05-07
purpose: |
  M04 sprint 启动期 design §6.X 标了 1 处 R-X5 🟡 子选项待 sprint 实证 (A5
  enqueue B 推迟 + get_for_embedding A 现在建)，sprint 期实证出**新 1 项**
  L1 跨模块契约层缺口（NodeChildrenServiceProtocol 4 参升级）。

  本文件按 5 步分层分析法 (memory feedback_problem_layered_analysis) 沉淀:
  - R1 + R2 review 命中比例 (L3 数据驱动 M05+ sprint review 计划)
  - R-X5 子选项实证 (M02+M03 复用 + M04 新决 1 项 Protocol 升级)
  - L1+L2+L3 节奏第三次实证 (M02 首 / M03 第二 / M04 第三 — 三数据点稳定)
  - PT1-PT3 模板复用性 (M01 立 / M02-M04 已回写)
last_reviewed_at: 2026-05-07
---

# M04 sprint 实证子选项 + Review 命中比例

## R-X5 子选项实证（M04 新 + M02/M03 复用）

### 子选项 1 — A5 enqueue 推迟 / get_for_embedding 现在建（design §6.X）

**原标 🟡 候选**：A 现在建 / B 推迟 / C 中间态。

**主标准推导**（design 已决，与 M03 同款）：
- get_for_embedding：Q1 是 (M04 sprint 期可独立实装 + 单元测试覆盖) + Q2 callee (M04 own 被动接口) → **A 现在建** ✅
- enqueue / enqueue_delete：Q1 否 (embedding_service M04 期不存在) + Q2 caller (M04 调 M18) → **B 推迟** ✅

**5 步分层分析**：与 M03 同款（design §6.X 主标准已覆盖，不重复推导）。

**决策落地**：
- 子片 3 `api/services/dimension_service.py:101-115` get_for_embedding A 路径实装（拼接 JSONB content 所有 string 字段，运行期 isinstance 过滤）
- 子片 1+3 docstring 4 字段 scaffold 注释（A5 enqueue B 推迟 + M11/M17/M13 跨模块接口推迟）
- 子片 3 `tests/test_m04_service.py` 3 项 get_for_embedding 测试

**回写 design §6.X A5**：
- 🟢 实证决：get_for_embedding **A 现在建** ✅ + enqueue **B 推迟** ✅（M18 sprint 接通）

---

### 子选项 2 — NodeChildrenServiceProtocol 签名升级（M04 sprint 新决 / 非 design §6.X 预标）

**触发场景**：M04 是 M03 R-X2 第一真注入方。子片 3 实装 `delete_by_node_id` 时发现：
- design §10 R10-1 batch3 要求 child service 写 per-record `delete` activity_log
- `write_event` 强制 `actor_user_id` 字段
- 原 Protocol 签名 `(db, node_id, project_id)` 缺 `actor_user_id`

**5 步分层分析**：

| Step | 内容 |
|---|---|
| 1 是什么 | 跨模块契约缺口：Protocol 签名 vs design §10 写 activity_log 要求不匹配 |
| 2 分层 | **L1 跨模块契约层**（NodeChildrenServiceProtocol — M03/M04/M06/M07 共用） |
| 3 本模块解 | 全部本模块解（contextvar / 跳 activity_log / 共享变量等）都违反 design §10 或引入全局状态——不可行 |
| 4 跨模块影响 | M06/M07 sprint 启动时撞同款；不升级 → M06/M07 注入时再发现，更晚成本更高 |
| 5 沉淀规则 | 必须升级 Protocol 签名为 4 参 `(db, node_id, project_id, actor_user_id)` |

**实证决**：升级 Protocol 4 参（含 `actor_user_id`），M03 delete_node 调用点同步改 4 参（M03 已有 actor_user_id 可顺手传），M04 注入点 lifespan 用同款 4 参签名。

**决策落地**：
- 子片 3 `api/services/node_service.py:75-81` Protocol 签名升级 + docstring 文字描述（升级触发的 5 步分析）
- 子片 3 `api/services/node_service.py:307` delete_node 调用点改 4 参
- 子片 3 `api/services/dimension_service.py:264-298` delete_by_node_id 接受 actor_user_id 写 activity_log
- R1 立修 `0ca7e5b` 5 处 design 真相源回写：
  - `M03/00-design.md` §6 service 行 + §8 R-X2 流程 3 行
  - `M06/00-design.md` §6 delete_by_node_id 4 参
  - `M07/00-design.md` §6 orphan_by_node_id 4 参
  - `02-modules/README.md` R-X3 Service 接口签名规范段（含正反例代码）

**M06/M07 sprint 启动 reconcile 时验证锚点**：grep design 字面是否含 4 参签名 + actor_user_id 配套；若 sprint 启动时 design 未含 → 闸门 2.5 reconcile pass 不通过。

---

### 子选项 3 — pdc-existence-strict（R1-C C3.2 立修触发新决）

**触发场景**：R1-C 发现 `DimensionTypeDisabledError` 完全未 raise；立修时遇语义灰区——`project_dimension_configs` 行不存在时（pdc is None）的语义。

**候选**：
- A 严格：pdc is None OR pdc.enabled=False → DimensionTypeDisabledError
- B 宽松：pdc is None → 允许（视为未配置 = 默认启用）
- C 区分：pdc is None → DimensionTypeNotFoundError / pdc.enabled=False → DimensionTypeDisabledError

**实证决**：**A 严格 (pdc-existence-strict)**

**5 步分层分析**：

| Step | 内容 |
|---|---|
| 1 是什么 | service _check_dimension_type_enabled 对 pdc 不存在的语义决策 |
| 2 分层 | L2 模块设计（M04 own 业务规则） |
| 3 本模块解 | 三选一直接落 |
| 4 跨模块影响 | 无（M04 own 业务规则） |
| 5 沉淀规则 | docstring 标注语义决策；audit 留备选项以便 CY review 时调整 |

**理由**：design §1 in scope 明示 "维度内容编辑：保存 / 更新 / 删除维度记录"，design §6 cross_module_reads 标 `project_dimension_configs` 是 M04 渲染前必读——隐含语义即"项目必须显式启用某 dimension type 才能在档案页填记录"。pdc 不存在 = 项目未启用 = 应拒绝。

**决策落地**：
- 立修 commit `0ca7e5b` `api/services/dimension_service.py:83-106` `_check_dimension_type_enabled` 实装
- 测试 `tests/test_m04_service.py:test_svc_create_rejects_unconfigured_type` (pdc is None) + `test_svc_create_rejects_disabled_type` (pdc.enabled=False)
- Router 端到端 `tests/test_m04_routers.py:test_create_dimension_unconfigured_type_returns_422`

**保留备选**：B/C 选项保留在 docstring `_check_dimension_type_enabled` 注释里——若 CY 后期 review 发现 A 太严格（如希望项目自动启用所有 dimension_types），可调整 service 实装 + 改测试。

---

### 子选项 4 — `_ck_clause` 提取时机（B1 / 闸门 2.5 B 栏）

**CY 拍 A**：M04 sprint 子片 1 内提取到 `migrations/helpers.py`，m01/m02/m03 三个 revision 同 commit 回写 import。

**实证落地**：commit `4c3c413` `migrations/helpers.py` + 3 处历史 revision import（M03 R1-B C2 punt 闭环）。
- M03 R1-B Sonnet ✅ 验证：四个 migration import 形式完全统一（全用 `as _ck_clause`）

---

### 子选项 5 — `make_node` fixture 位置（B2 闸门 2.5 自我修正为 A 栏）

**自我修正过程**：闸门 2.5 reconcile pass 初版误把 `make_node` 提 conftest 列为 B 栏，CY 反问"按之前流程定不下来吗"。AI 反思：M03 R1-B C1 已立"跨模块 test helper 重复禁忌"规则，本项是机械应用既有规则——属 A 栏。

**实证落地**：commit `4c3c413` `tests/conftest.py` 加 `make_node` fixture，`tests/test_m03_dao.py` 内联 `_make_node` 迁移到 fixture（24 PASS 不回归）。
- 元教训：`feedback_process_transparency` 触发——把"机械应用既有规则"误列 B 栏 = 给 CY 制造无对比假决策。M05+ sprint 闸门 2.5 reconcile 时再审："这真有候选吗 / 还是延续既有规则？"

---

## R1 + R2 命中比例（L3 数据驱动）

### R1 (3 subagent 并行 / 子片 1+2+3 合并审)

| Subagent | 模型 | P1 | P2 | P3 | 工时 | 主命中类目 |
|---|---|---|---|---|---|---|
| R1-A spec+quality | Opus | 1 | 4 | 2 | 208s | A13 design 5 处 Protocol 4 参回写 |
| R1-B reuse | Sonnet | 0 | 1 | 2 | 137s | B1.1 `_seed_dim_type` 三文件重复 → conftest |
| R1-C quality+efficiency | Sonnet | 3 | 5 | 3 | 263s | C3.1 node 归属校验 / C3.2 DimensionTypeDisabledError 未 raise / C9 配套测试 |
| **合计** | — | **4 (合并)** | **10** | **7** | — | — |

**P1 全立修**（commit `0ca7e5b`）：
1. A13: design 5 处 Protocol 4 参回写
2. C3.1: `_check_node_belongs_to_project` 实装 + 3 写方法调用 + 3 cross-tenant 测试
3. C3.2: `_check_dimension_type_enabled` 实装 + pdc-existence-strict 子选项决 + 2 测试
4. C9.1+C9.2: 5 配套测试（merge 进 立修同 commit）

**M02 首 (6 P1) → M03 第二 (4 P1) → M04 第三 (4 P1)**：稳定在 4-6 P1 区间；R1 命中率正常。

### R2 (1 合并 Opus subagent / 子片 4 endpoint 单审)

| Subagent | 模型 | P1 | P2 | P3 | 工时 |
|---|---|---|---|---|---|
| R2 合并 | Opus | 1 | 3 | 3 | 146s |

**P1 立修**（commit `5a97824`）：B6.x `enabled_dimension_types` 字段名/SQL 不一致（含 disabled pdc）

**M02 (6 P1) → M03 (4 P1) → M04 (1 P1)**：M04 R2 命中下降，但 **B6.x 是 R1 三 subagent 没抓到的新角度**（"命名 vs SQL vs design 文字"三处一致性需 Opus 端到端读才能拼出）。M02+M03+M04 三数据点稳定后，R2=1 合并 Opus 范式仍有效。

### Punt 项总池（M04 sprint 末 17 项）

| 来源 | # | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|---|
| R1-A A2 | 1 | design §3 alembic `(updated_by, updated_at)` 索引未建 | P2 | M15 / M19 sprint 评估 |
| R1-A A4 | 2 | §5 vs §6 R-X3 事务边界字面冲突 | P2 | M05 sprint 启动 reconcile 时消歧 |
| R1-A A6 | 3 | `batch_get_by_nodes` 仅 DAO，service 缺包装 | P2 | M12 sprint 启动时补 |
| R1-A B3 | 4 | create 竞态 IntegrityError → 500（非 DimensionDuplicateError） | P2 | M05 sprint 顺修 |
| R1-A A1 | 5 | SQLAlchemy block 字面 `dimension_type` relationship 实装未建 | P3 | 顺手清 |
| R1-A B4 | 6 | `completion(enabled_count=...)` 推 caller vs design §6 字面 | P3 | docstring 加 punt 注释 |
| R1-B B1.1 | 7 | `_seed_dim_type` 三文件重复 → conftest `make_dim_type` | P2 | M05 sprint 启动前 |
| R1-B B2.4 | 8 | `db.get(DimensionType)` 未走 `DimensionTypeDAO`（与 M02 风格不一致） | P3 | M15 sprint 启动前 |
| R1-B B6 | 9 | `target_type` 字符串未 const 提取 | P3 | M15 sprint 启动前（一次性 const 化所有） |
| R1-C C1.2 | 10 | `delete_by_node_id` 并发 continue 跳过 activity_log 写（R10-1 弱化） | P2 | docstring 显式说明 / M15 升级真 INSERT 时复审 |
| R1-C C2.2 | 11 | design §6 字面 `delete_by_node_id` 仍 3 参（已合并到 A13 立修） | — | 已闭环 |
| R1-C C5.1 | 12 | router 子片 4 commit 闭环验证 | — | R2 已审，子片 4 无问题 |
| R1-C C6.1 | 13 | `delete_by_node_id` N+1 已知（Protocol R2-3 punt batch 升级） | P2 | M06/M07 sprint 启动时评估 |
| R1-C C6.2 | 14 | `update_with_lock` 二次查询竞态语义误差 | P2 | docstring 明确 / 不区分删除竞态 |
| R1-C C6.3 | 15 | create 二次查询 TOCTOU 风险 | P2 | DB UNIQUE 兜底 |
| R1-C C9.3 | 16 | monkeypatch ≠ 生产路径已知（feedback_monkeypatch_not_verification） | P2 | M15 sprint 升级 write_event 真 INSERT 时端到端复审 |
| R1-C C1.1/C2.4/C7.1/C9.4 | 17 | readyz log / `**fields` 白名单 / IntegrityError 转换 / 真并发测试 | P3 | M05+ sprint 顺手清 |
| R2 A1 | — | DimensionResponse 缺 `dimension_type_key` / `updated_by_name` | P2 | 前端真用时补 join |
| R2 A2 | — | list_by_node / get_one_record service 层未调 `_check_node` | P2 | docstring 加豁免说明 |
| R2 B5 | — | `_record_response` 与 `from_attributes=True` 冗余 | P3 | 顺手清 |
| R2 A4 | — | jsonschema 二次校验 design §7 字面要求未实装 | P3 | M13 真前端跑通时补 |
| R2 B7 | — | 真并发乐观锁 / DELETE+POST cross-tenant 测试 | P3 | M05+ sprint 启动前 |

---

## L1+L2+L3 节奏第三次实证（M02 首 / M03 第二 / M04 第三 — 三数据点稳定）

| 节奏层 | M04 sprint 表现 | 与 M02+M03 差异 |
|---|---|---|
| L1 总则（sprint ≥1 次 + ≥50 行 OR ≥2 文件 + 触发例外） | ✅ 全合规：R1 (3 sub) + R2 (1 sub) 共 2 次 review，子片 5 不单跑（≥80% SKIP 例外） | 与 M02+M03 一致 |
| L2 sprint 计划（design §14.5 必有） | ✅ commit `4c3c413` 含 §14.5（schema 子片禁单跑、R2=1 合并 Opus subagent） | 与 M03 一致；M02 R2 是 3 subagent；M03 已切到 1 合并 Opus + M04 复用证明范式稳定 |
| L3 实证回写（本文件） | ✅ accepted | 与 M02+M03 同款 |

**三数据点稳定结论**：M05+ sprint review 计划默认采用 R1=3 subagent（spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet）+ R2=1 合并 Opus subagent；schema 子片禁单跑（合并到 service 子片）；子片 5 不单跑（≥80% SKIP 例外）。

---

## PT1-PT3 复用判断（回填到 m01-pilot-template-validation.md）

- **PT1**（最简 + schema 都支持）：❌ 不复用 — M04 是档案页主表，所有字段必须可用；M18 baseline-patch get_for_embedding A 路径已实装非"预留 schema"
- **PT2**（ADR-004 凭据路径）：✅ 复用 — M04 read endpoint require_user 走 ADR-004 §2 P1 行；M04 design 凭据路径声明段未改 ADR-004 = 抽象成功
- **PT3**（预留 schema + CI 禁引用）：❌ 不复用 — M04 无预留 model

回填到 `audit/m01-pilot-template-validation.md` PT1 表 M04 行（commit `de239c2` 后立修 commit 内回填）。

---

## 元教训（M04 sprint 新增 + M02/M03 复用）

### 新增 1 — Protocol 签名升级触发的"L1 跨模块契约层"识别

**触发**：子片 3 实装 R-X2 第一真注入时撞 actor_user_id 缺口。

**关键决策点**：能否本模块绕？
- contextvar 注入 actor_user_id：引入全局状态，违反 service 层无状态原则
- 跳过 cascade activity_log 写入：违反 design §10 R10-1 batch3
- 升级 Protocol 4 参：跨模块契约改动，需回写 5 处 design 真相源

5 步分层分析法立刻定位为 L1 而非 L2，避免本模块绕的低质方案。`feedback_problem_layered_analysis` 在 M04 sprint 第一次产出实质性"防本模块绕"的拦截价值。

### 新增 2 — 闸门 2.5 reconcile 自我修正信号

**触发**：闸门 2.5 初版误把 `make_node` 提 conftest 列为 B 栏让 CY 拍。CY 反问"按之前流程定不下来吗"——AI 立即识别 R1-B C1 已立规则、本项是机械应用既有规则、属 A 栏。

**沉淀**：闸门 2.5 reconcile pass 自审追加一问："这真有候选吗 / 还是延续既有规则？"——不允许把"延续既有规则的机械应用"当 B 栏给 CY 制造假决策。
- 候选规则化：写入 `feedback_process_transparency` 红线触发列（已有；此次实证补强）

### 复用 1 — feedback_design_scaffold_reconcile 红线

A13 P1 阻塞性问题（升级实装但漏回写 5 处 design）正是该 memory 已立规则的违反——sprint 期"实装侧自洽 / design 侧滞后"是常见漂移；强制 R1 spec subagent 扫"实装是否同步 design 真相源"。

### 复用 2 — feedback_monkeypatch_not_verification

R1-C C9.3 已明示 monkeypatch ≠ 生产路径验证；service 测试 docstring 已显式标注；端到端验证靠 router integration 测试（子片 4 已补）。

---

## 维护规则

- 本文件 status=accepted（M04 sprint 关闸时）
- M05 sprint 启动闸门 2.5 reconcile pass 时复用本文件 R1/R2 命中比例数据点
- M06/M07 sprint 启动时验证 NodeChildrenServiceProtocol 4 参签名（grep design 字面）
