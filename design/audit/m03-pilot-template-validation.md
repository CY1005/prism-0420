---
title: M03 sprint 实证子选项 + R1/R2 命中比例
status: accepted
owner: CY
created: 2026-05-07
purpose: |
  M03 sprint 启动期 design §6.X 标了 1 处 R-X5 🟡 子选项待 sprint 实证 (A4 enqueue 推迟 +
  get_for_embedding A 现在建，已在 design §6.X 主标准 Q1+Q2 推导决)。

  本文件按 5 步分层分析法 (memory feedback_problem_layered_analysis) 沉淀:
  - R1 + R2 review 命中比例 (L3 数据驱动 M04+ sprint review 计划)
  - R-X5 子选项实证 (M02 sprint 4 项已决, M03 sprint 复用 + 新 1 项 batch_create 拓扑责任)
  - L1+L2+L3 节奏第二次实证 (M02 首次 / M03 第二次 — 双数据点)
  - PT1-PT3 模板复用性 (M01 立 / M02 已回写 / M03 此次回写)
last_reviewed_at: 2026-05-07
---

# M03 sprint 实证子选项 + Review 命中比例

## R-X5 子选项实证 (M03 新 + M02 复用)

### 子选项 1 — A4 enqueue 推迟 / get_for_embedding 现在建 (design §6.X)

**原标 🟡 候选**: A 现在建 / B 推迟 / C 中间态。

**主标准推导** (design 已决):
- get_for_embedding: Q1 是 (M03 sprint 期可独立实装 + 单元测试覆盖) + Q2 callee (M03 own 被动接口) → **A 现在建** ✅
- enqueue / enqueue_delete: Q1 否 (embedding_service M03 期不存在) + Q2 caller (M03 调 M18) → **B 推迟** ✅

**5 步分层分析**:
| Step | 内容 |
|---|---|
| 1 是什么 | M03 与 M18 baseline-patch 接口拆分: 哪些 M03 own 现在建 / 哪些 M03 caller 推迟 |
| 2 分层 | L2 模块设计 (R-X5 主标准 Q1+Q2 已覆盖) |
| 3 本模块 | design §6.X 已决, sprint 期照执行即可 |
| 4 跨模块 | M18 sprint 期接通 enqueue 调用 + 回归测试 |
| 5 沉淀 | design §6.X 已含, scaffold S2 4 字段注释强制落地 (子片 2/3) |

**决策落地**:
- 子片 2 `api/services/node_service.py:80-117` get_for_embedding A 路径实装
- 子片 2/3 `api/services/node_service.py` 头部 scaffold S2 4 字段注释 (A4 enqueue B 推迟 + A3 child_services 注册表 noop)
- 子片 2 `tests/test_m03_dao.py:282-333` 4 项测试 (name+desc / name only / not_found / cross-tenant)

**回写 design §6.X A4 子选项清单**:
- 🟢 实证决: get_for_embedding **A 现在建** ✅ + enqueue **B 推迟** ✅ (M18 sprint 接通)

---

### 子选项 2 — batch_create 拓扑排序责任 (R1 P-A-03 punt)

**原 R1-A 发现**: design §3 G5 字面 "拓扑排序后单阶段处理"，但 service 实装注释 "简化版: caller 已按层级顺序排好" → 责任甩给 M11/M17 caller，design 无 punt 条款。

**主标准推导**: Q1 是 (M03 sprint 可实装最小拓扑 ~15 行) + Q2 callee (M03 own 接口) → **本应 A 现在建**。

**实证决** (sprint 末): **B 半路径推迟** + design §6.X 加 A5 4 字段 punt 段
- 理由: 子片 3 实装的"caller 已排序" 简化版功能正确（拓扑对正确输入幂等），M11/M17 sprint 期 csv 流程通常已是层序——此期不重复实装拓扑
- 风险: M11/M17 caller 未保证拓扑 → `parent_temp_id not in temp_to_real` raise NodeParentNotFoundError，行为可观测
- M11/M17 sprint 启动时按 design §6.X A5 决策"是否 service 加最小拓扑 vs caller 必排序契约"

**回写 design §6.X A5** (sprint 末执行):
```markdown
### A5 — batch_create_in_transaction 拓扑排序责任 (R1 review punt)
- 退化路径: B 半路径推迟
- 主标准推导: Q1 是 + Q2 callee → 本应 A 但 M03 sprint 实装"caller 已排序"简化版
- 理由: 功能正确 (拓扑对已排序输入幂等); M11/M17 csv 流通常已层序 — 此期不重复实装
- 触发回写: M11/M17 sprint 启动时拍"service 加最小拓扑 vs caller 必排序契约"
- B 路径必动作: api/services/node_service.py:420-457 头部 TODO 注释 (子片 5 补 4 字段)
```

---

### 复用 M02 sprint 4 项实证 (无需 M03 重新实证)

- C 路径 team_id (M02 A1): DAO 完全允许 — M03 不涉及 team_id, **复用即可**
- A 路径 SearchConfig (M02 A2): M02 own raw types — M03 不涉及, **不适用**
- B 路径 move-team (M02 A3.2): 不实装 router → OpenAPI 不含 — M03 不涉及, **不适用**
- R13-1 标记位置 (M02 A3.1): code 注释 — M03 7 个 NODE_* ErrorCode **复用即可** (api/errors/codes.py:55-66 顶部注释 + 个别 docstring 标 "保留备用 R13-1 parity")

---

## R1 命中比例 (子片 1+2+3 合并审 / 3 subagent)

### M03 数据 (commit ce73570 R1 修)

| Subagent | 命中 | SKIP | 命中率 |
|---|---|---|---|
| A spec+quality (Opus) | 9 (3 P1 立修 / 6 P2 punt) | 9 | 高 (合并审有信号) |
| B reuse (Sonnet) | 1 P1 + 1 P2 | 9 | 18% (2/11) |
| C quality+efficiency (Sonnet) | 1 P1 + 7 P2 | 28+ (Prism 22 + 通用扩) | ~25% |

**M03 立修 4 项 (R1 修 commit ce73570)**:
1. **P-A-01** (P1) update_node 无变化时仍 flush 写 updated_by ("幽灵写") → 早返回不动 updated_by + 不写 activity_log + 锁定回归 test_svc_update_no_change_does_not_touch_updated_by
2. **P-A-02** (P1) reorder_siblings 对未变 sort_order 节点也写事件 (契约漂移) → 跳过同值节点 + 锁定回归 test_svc_reorder_skips_unchanged_sort_order
3. **P1-01** (P1, R1-C) NodeChildrenServiceProtocol 无异常契约 → docstring 加异常传播契约 (禁 catch-all 静默吞错)
4. **C1** (P1, R1-B) test_m03_dao + test_m03_service `_make_user_and_project` 三处重复 → conftest.py 加 make_project fixture, 47 测试调用迁移

**M03 punt 12 项 (sprint 末或 design 回写)**:
- P-A-03: batch_create 拓扑责任 → design §6.X A5 punt (本文件子选项 2 已落)
- P-A-04: empty string 语义 → 子片 5 加 description="" 测试固化语义
- P-A-05/P2-01: breadcrumb N+1 → 子片 5 加 dao.list_by_ids + 重写 breadcrumb 一次 IN
- P-A-06: child_services 分发语义 → design §8 R-X2 回写: "每 target_type service 对全 subtree 节点调用; M04+ service 内部用 node_id 过滤本表数据, 多余调用是 noop"
- P-A-07/P2-04: root↔root + self-move 测试 → 子片 5 补
- P-A-08: design §3 SQLAlchemy block 加 description 字段 + reconcile 注释 (sprint 末必做, 已计划)
- P-A-09: refresh attribute_names 加 path → 子片 5 加 (防御性)
- P2-02: batch_create max_sort_order O(N) TODO 注释 → 子片 5 在 service 头加
- P2-03: REPLACE 安全性注释缺失 → 子片 5 加 docstring
- P2-05: design §3 path 公式 vs 实装公式歧义 → 子片 5 design 回写 "parent.path 已含末尾 /"
- P2-06: move 子节点 metadata old_path/old_depth None → 子片 5 design §10 显式声明本期为 None / M15 sprint 回填
- P2-07: alembic downgrade 无 drop_constraint → P2 punt 仅 PG 项目可 SKIP, 跨 DB 兼容时再加
- C2 (R1-B): migrations `_ck_clause` 重复 → P2 punt M04 migration 出现前提取 helpers.py

**实证结论 (M03 R1)**:
- ✅ R1 合并审 schema+DAO+service 仍是对的 — 3 subagent 共出 4 项立修 + 12 项 punt, 信号强
- ✅ M02 R1 命中比例数据复用: B reuse Sonnet ~17-18% (M02 17% / M03 18%) 稳定
- ✅ A spec+quality Opus 合并 schema+service 合并审才能审业务 — schema 单跑信号弱假设再印证
- ❓ C1 (test helper 重复) 是 M03 才出现 — M02 sprint 期 test_m02_*.py 各自内联 helper 未抽出 conftest, M03 sprint 是第一次跨模块 helper 重复浮出。**未来模块 sprint 启动前应预查 conftest.py 是否已有可用 fixture**

---

## R2 命中比例 (子片 4 endpoint 单审 / 1 合并 subagent)

### M03 R2 数据 (commit 656e05c R2 修)

| Subagent | 命中 | SKIP | 命中率 | 总判 |
|---|---|---|---|---|
| Spec+Quality+Simplify 合并 (Opus) | 4 P1 立修 + 5 P2 punt | 14+ | 高 (endpoint 是高命中区印证) | ❌ 不通过 → 修后 ✅ |

**4 P1 立修 (commit 656e05c)**:
1. **R2-1** reorder 契约漂移: `NodeTreeResponse → NodeListResponse` (design §7 字面)
   + 删 reorder 后多余 list_tree call (R2-2 N+1 同合并修)
2. **R2-3** NodeChildrenServiceProtocol 未来契约升级路径 docstring 注 (子树 N×K 风险埋点)
3. **R2-4** breadcrumb 真 N+1: 加 NodeDAO.list_by_ids 一次 IN 查 (兑现 design §1 "O(1) 面包屑")

P2 顺修 1 项:
- **R2-8** NodeResponse type: str → NodeTypeEnum (design §7 字面，前端 enum 类型保证)

**5 P2 punt 子片 5 / design 回写**:
- R2-5 move 子节点 metadata old_path/old_depth None → design §10 显式声明 ✅ (子片 5 已回写)
- R2-6 NodeListResponse 死代码 → R2-1 修后启用 ✅ 自然消解
- R2-7 _build_tree 双 Pydantic 验证 → M11/M17 batch_create 实证后再优化
- R2-9 update_node service 层 type 参数死防御 → 子片 5 加 service 层直调测试 (低优,有 raise 路径)
- R2-3 (P1 但 docstring punt) → M04 sprint 启动时实装 batch 形态

**实证结论 (M03 R2)**:
- ✅ **endpoint 单审 1 合并 Opus subagent 信号强**：4 P1 全命中契约漂移/N+1/未来债（Prism 特有 22 条 endpoint 高命中区印证）— **M02 R2 (6 P1) + M03 R2 (4 P1) 双数据点验证 1 合并 subagent 范式足够**
- ✅ R2 高命中区一致：契约漂移 (R2-1+R2-8) + N+1 (R2-4) + 未来债 (R2-3)
- ❓ **新增模式**：docstring 自承单方面改契约 (R2-1 router L177) → 应纳入 simplify checklist 维度 17 ("docstring 不能凌驾 design 表")
- 下游 M04+ 计划修订建议: **保留** R2 endpoint 单审 1 合并 Opus subagent 范式 (双数据点足够)

---

## L1 总则 (闸门 3.4) 第二次实证

| 总则 | M02 实证 | M03 实证 |
|---|---|---|
| sprint ≥1 次必跑 | ✅ R1+R2 共 2 次 | ✅ R1+R2 共 2 次 |
| ≥50 行 OR ≥2 文件触发 | ✅ 每子片均触发 | ✅ 每子片均触发 |
| 触发例外 (≥80% SKIP 合并下游) | 子片 5 ✅ | 子片 5 ✅ (tests + design 回写) |

**L1 改进提议** (M02 + M03 双数据点归纳):
- "≥80% SKIP" 阈值在 schema 子片实测 50-80% (Quality 维度命中 schema 弱, Spec 合并 service 后才出信号)
- 后续模块 sprint 也用合并审 (R1=schema+DAO+service / R2=endpoint 单审) — 不强求 schema 单跑
- L2 sprint review 计划段 §14.5 强制存在 (闸门 3.4 L2) — M03 sprint 启动前补段 (commit 800e632)

---

## PT1-PT3 复用情况 (M03 sprint 内回写 m01-pilot-template-validation.md)

| PT | M03 是否复用 M01 范式 | 备注 |
|---|---|---|
| PT1 「本期实现最简 + schema 都支持」 | ❌ 不适用 | M03 nodes 1 表全部本期实装, 无"建表禁 import"模式; 与 M02 同款 (M02 4 表全实装) |
| PT2 ADR-004 凭据路径表 | ✅ 复用 | M03 router 8 endpoints 全用 require_user (M01 P1 路径) + check_project_access; 无新建凭据类型 |
| PT3 预留 schema + CI 禁引用 | ❌ 不适用 | M03 nodes 表全本期实装, 无"建表禁 import"模式 |

**校准回写** (m01-pilot-template-validation.md PT1 表 M03 row):
- ❌ 不复用 (M03 nodes 全实装) — 与 M01 7 表 (3 实装 + 4 预留) 模式不同, 因 M03 是 M04-M19 树结构锚点, 当前所有字段必须可用; M02 同款不适用模式

---

## 维护

- M03 sprint 关闸时本文件 status 改 accepted
- R-X5 子选项 2 (batch_create 拓扑) 沉淀回 `design/02-modules/README.md` 对应段
- L1 总则双数据点归纳沉淀回 `design/00-phase-gate.md` 闸门 3.4 (子片 5 执行)
- 后续 M04/M05+ sprint 启动 reconcile pass 时引用本文件 + m02-pilot-template-validation.md 作为先例
