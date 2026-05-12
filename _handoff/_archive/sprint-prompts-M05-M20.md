---
title: prism-0420 M05-M20 sprint 启动 prompts（按 M04 sprint 范式生成）
status: living
owner: CY
created: 2026-05-07
last_updated: 2026-05-07（M04 sprint 完成后批量生成）
purpose: |
  M02-M04 sprint 三数据点稳定后（详见 audit/m04-pilot-template-validation.md），
  默认范式：闸门 2.5 reconcile 三栏 + §14.5 sprint review 计划 +
  R1=3 subagent (spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet) +
  R2=1 合并 Opus subagent + 5 子片 + 跨项目沉淀 4 类清单。

  本文件保存 M05-M20 共 16 个 sprint 启动 prompt。每个 prompt 含：
  (1) 通用启动序 (与 M04 prompt 0 同款) +
  (2) 模块特定触发点 (R-X1 orchestrator / R-X2 child service / M04 punt 接通 / 等) +
  (3) 模块特定红线 (基于 M04 sprint 实证后强化的规则)。

  使用方法：sprint 启动当天复制对应模块 prompt 段落，主 agent 按顺序执行。
---

# M05-M20 Sprint 启动 Prompts

## 通用启动序（所有模块共享，复制时含此段）

```
冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（协作规则 + "快速上手"序）
2. /root/workspace/projects/prism-0420/_handoff/next-session.md（§0 状态快照 + 当前推荐 Prompt 0）
3. /root/workspace/projects/prism-0420/design/00-roadmap.md（真实 Phase 2.1 进度）
4. /root/workspace/projects/prism-0420/design/00-phase-gate.md（闸门 2.5 三栏 + 闸门 3.4 L1 review 触发粒度）
5. /root/workspace/projects/prism-0420/design/02-modules/M{XX}-{name}/00-design.md（本模块 design）
6. /root/workspace/projects/prism-0420/design/audit/m04-pilot-template-validation.md（M04 三数据点稳定 + punt 池 17 项 + 元教训 2 条）
7. /root/workspace/projects/prism-0420/design/audit/m01-pilot-template-validation.md（PT1-PT3 tracker — 本 sprint 闸门 2.5 时回填本模块行）
8. memory feedback_problem_layered_analysis（5 步分层分析法 — M04 实证首次实质性"防本模块绕"拦截）
9. memory feedback_three_agent_pipeline（v2: M02+M03+M04 三数据点稳定 / R1=3 subagent + R2=1 合并 Opus subagent）
10. memory feedback_process_transparency（A/B/C/D 决策清单分级；闸门 2.5 自审"这真有候选吗 / 还是延续既有规则？"）
11. memory feedback_sprint_test_helper_reuse_check（conftest fixture 预查清单）
12. memory feedback_decision_transparency + feedback_code_first + feedback_completion_audit + feedback_subagent_completion_check + feedback_subagent_interface_contract + feedback_git_push_kb（标准红线集）

启动顺序（严格按 M02+M03+M04 范式）：

1. **闸门 2.5 reconcile pass**（sprint 启动当天必跑）：
   - 预查 conftest.py 已有 fixture（make_user / make_project / make_node / 等；M04 R1-B 实证规则延续）
   - grep 本模块引用的 horizontal helper（含 NodeChildrenServiceProtocol 4 参签名 / api/auth/check_project_access / api/services/activity_log_service.write_event / api/errors/ / api/models/base / etc.）
   - 三栏分类输出（A 机械可做 / B 待 CY 决策 / C 已自我消解）
   - 自审一问："这真有候选吗 / 还是延续既有规则？"——不允许把"延续既有规则的机械应用"列为 B 栏给 CY 制造假决策（feedback_process_transparency 实战 2）

2. **闸门 3.4 L1 总则**：本模块 design 必须含 §14.5 sprint review 拆分计划段（参 M02/M03/M04）：
   - R1: 子片 1+2+3 合并审 / 3 subagent (spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet)
   - R2: 子片 4 endpoint 单审 / 1 合并 Opus subagent (spec+quality+simplify)
   - 子片 5 不单跑（≥80% SKIP 例外）
   - schema 子片禁单跑（M02+M03+M04 三数据点稳定结论）

3. **写代码 5 子片**（标准范式）：
   - 子片 1：models + alembic migration（含 helpers.py 复用 ck_clause）
   - 子片 2：DAO（design §9 主查询模式 + 强制 tenant 过滤 + 乐观锁/批量接口按需）
   - 子片 3：Service + 跨模块注入点（详见模块特定要素）
   - 子片 4：Router + endpoints + check_project_access Depends
   - 子片 5：tests 收尾 + ci-lint + design 回写 + audit 落盘

4. **R1+R2 review 按 §14.5 计划跑**：
   - R1 (子片 3 完成) → 3 subagent 并行 background mode；>5min 无通知主动 ping
   - R1 finding P1 立修同 commit；P2 punt 进 audit/m{XX}-pilot-template-validation.md
   - R2 (子片 4 完成) → 1 合并 Opus subagent；P1 同 commit 立修

5. **simplify-checklist 自动判断**：≥50 行 OR ≥2 文件触发；schema/migration 子片若 ≥80% checklist 条目天然 SKIP 可合并到下游

红线（M04 sprint 实证后强化）：
- 5 步分层分析法走（机制冲突/设计缺口） — M04 R-X5 实证此规则首次实质性"防本模块绕"
- NodeChildrenServiceProtocol 现是 4 参签名（含 actor_user_id） — 注入时 follow
- M04 sprint punt 池 17 项 — 启动 reconcile 时核对哪些可顺修（详见 audit/m04-pilot-template-validation.md）
- monkeypatch ≠ 生产路径（feedback_monkeypatch_not_verification）
- commit 不主动 push（feedback_git_push_kb）

完成判定（sprint 关闸 checklist）：
- 5 子片 commits 落地 + R1+R2 review 闭环（P1 全立修）
- 全量 pytest PASS（含历史模块不回归）
- ruff clean / ci-lint 全过（R13-1 parity / L12 / L?? 模块守护按需加）
- design A?/A?/A? 等实施期处理段 status="已落地 + commit hash"
- audit/m{XX}-pilot-template-validation.md 含 R-X5 子选项实证 + R1/R2 命中比例 + L1 第 N 数据点 + M01 PT1 表回写本模块行

跨项目沉淀（sprint 关闸前 + 关闸后两轮，详见 M04 sprint 范式）：
1-4 项目内 (design 回写 / audit 新建 / handoff 更新 / roadmap 更新)
5. memory 沉淀（sprint 实证有跨项目复用价值的）
6. KB 沉淀（30-架构设计/补丁02 加数据点 / 10-Prism/simplify-checklist 加新条 / 50-工具与方法论新建按需）
7. CY 决策同步（A 已落地 / B memory 候选 / C KB 候选 / D 不需要写）
```

---

## M05 — 版本时间线（version-timeline）

**模块特定**：
- 主表 `version_records`（节点版本快照；与 M04 dimension_records 解耦——M04 编辑维度时不自动建 version，version 是 M05 用户主动操作）
- M04 design §1 边界灰区已明文：M04 不写 version_records；M05 sprint 才实装

**特殊触发点**：
- M04 punt 池接通：无（M04 不依赖 M05）
- M05 是新主表，不是 R-X2 child service / 不是 R-X1 orchestrator

**特定红线**：
- ⚠️ 与 dimension_records 关系：M05 创建 version 时是否拍快照（snapshot 全量 dimension_records 字段值）vs 仅记元数据（time + actor + 引用）？— 这是 R-X5 子选项候选，5 步分层分析后定（很可能 L2 模块决策）
- M04 audit P2 项："R-X5 batch_create_in_transaction service 包装缺位 (R1-A A6)" — M05 不直接触发，但 M11/M17 启动时回头看
- 时间线 query 性能：(node_id, created_at DESC) 索引 + LIMIT 分页

**起手 prompt**（复制以下完整段落，替换 `{XX}={name}` 自己跑）：

```
继续 prism-0420 M05 sprint 实施代码（M05 版本时间线；M04 sprint 已完成 commits 4c3c413→4aab909 / 347 PASS / Phase 2.1 25%）。

[通用启动序，详见本文件 §"通用启动序"]

任务：M05 sprint TDD 实施。

模块特定要素：
- M05 是 version_records 主表所有者；与 M04 dimension_records 解耦（design §1 边界灰区）
- 不是 R-X2 child service / 不是 R-X1 orchestrator
- R-X5 候选子选项：version_records 是否含 dimension content snapshot（全量 vs 仅引用）— 5 步分层分析法定层 + sprint 期决
- 时间线 query 性能：(node_id, created_at DESC) 索引 + LIMIT 分页

模块特定红线：
- M05 不级联 M04 dimension_records（不动 R-X2 范式）
- 历史 version 的 reset_to / rollback 是否纳入本期？— design 应已含决策；sprint 启动闸门 2.5 复审
- M04 sprint punt 池中"R1-A A4 §5 vs §6 R-X3 事务边界字面冲突"— M05 sprint 启动 reconcile 时建议消歧（M04 punt 转给 M05 接续）
```

---

## M06 — 竞品参考（competitor）

**模块特定**：
- 主表 `competitor_refs`（节点级竞品引用列表）
- design §6 含 `delete_by_node_id` 4 参签名（M04 sprint R-X5 升级 / 已回写）

**特殊触发点**：
- **R-X2 第二真注入方**（M04 是第一）— `register_child_service("competitor", CompetitorService.delete_by_node_id)` 在 lifespan 注入
- M04 sprint Protocol 升级到 4 参 → M06 follow 同款（含 actor_user_id 写 per-record cascade `delete` event）
- M18 baseline-patch get_for_embedding 同款（A 现在建 / B 推迟 enqueue）

**特定红线**：
- ⚠️ N+1 风险：R2-3 punt batch 形态升级 — 子树节点 >50 时压力出现，但 M06 sprint 期不必修（与 M04 一致 punt 进 audit）
- delete_by_node_id 异常契约严守（不 catch-all 静默吞错；R1-C P1-01）
- competitor.url 字段不参与 embedding（design CY 决策 4：仅 name + description）

**起手 prompt**：

```
继续 prism-0420 M06 sprint 实施代码（M06 竞品参考；M{N-1} sprint 已完成 commits ... / N PASS / Phase 2.1 X%）。

[通用启动序]

任务：M06 sprint TDD 实施。

模块特定要素：
- M06 是 R-X2 第二真注入方（M04 第一已实证 / Protocol 4 参签名稳定）
- 子片 3 实装 CompetitorService.delete_by_node_id (4 参 含 actor_user_id) + lifespan 注入
- design §6 已回写 4 参签名（M04 sprint R-X5 升级期同步落地）
- M18 baseline-patch get_for_embedding A 现在建 (拼接 name + description，CY 决策 4：url 不参与)

模块特定红线：
- 异常契约严守：delete_by_node_id 不 catch-all 静默吞错（R1-C P1-01；M04 已立）
- N+1 punt 接续：R2-3 batch 形态升级仍 punt 到子树 >50 压力出现（与 M04 一致）
- M04 audit punt 池 R1-C C6.1（delete_by_node_id N+1）— M06 sprint 启动核对是否升级触发
- M04 audit punt 池 R1-A B3（IntegrityError race → 500）— M06 同款 race 风险评估
```

---

## M07 — 问题沉淀（issue）

**模块特定**：
- 主表 `issues`（项目级 bug / 技术债 / 改进点；可关联 node 也可游离）
- design §6 含 `orphan_by_node_id` 4 参签名（M04 sprint R-X5 升级 / 已回写）— **不是 delete，是 SET node_id=NULL**

**特殊触发点**：
- **R-X2 第三真注入方**（语义不同：orphan 而非 delete；issue 不被删除只变游离）
- batch3 基线补丁决策 4：命名为 `orphan_by_node_id` 区分 M04/M06 的 `delete_by_node_id`，避免调用方误以为 issue 被真删
- M03 design §8 R-X2 流程注入点：`register_child_service("issue", IssueService.orphan_by_node_id)`

**特定红线**：
- ⚠️ orphan 语义而非 delete：node_id 设 NULL + activity_log action_type=`orphan`（不是 `delete`）+ metadata 含 `{old_node_id, reason: "cascade_from_node_delete"}`
- IssueService.list_by_project（M13 跨模块调用契约 / 已登记 / 无代码改动 / pass-through 即可）
- M07 R-X5 候选子选项：游离 issue 后能否再 attach 到新 node？— design 应已含决策

**起手 prompt**：

```
继续 prism-0420 M07 sprint 实施代码（M07 问题沉淀；M{N-1} 完成）。

[通用启动序]

任务：M07 sprint TDD 实施。

模块特定要素：
- M07 是 R-X2 第三真注入方，但语义不同：orphan_by_node_id（SET node_id=NULL）而非 delete
- design §6 已回写 4 参签名（M04 sprint 同步升级期落地）
- batch3 基线补丁决策 4：命名 orphan 区分 M04/M06 的 delete（避免误以为真删）
- M13 pilot 登记 list_by_project 跨模块契约（无代码改动；pass-through DAO node_id 过滤）
- activity_log: action_type="orphan" + metadata 含 cascade_source

模块特定红线：
- orphan 语义严守：不真删；node_id 设 NULL；FK ON DELETE SET NULL 配合
- 异常契约：concrete impl 不 catch-all（R1-C P1-01）
- 游离 issue 后能否 reattach？— design 应含；闸门 2.5 复审
- M03 R-X2 流程注入点 lifespan 加 register_child_service("issue", IssueService.orphan_by_node_id)
```

---

## M08 — 模块关系图（module-relation）

**模块特定**：
- 主表 `module_relations`（节点之间的关系：依赖 / 引用 / 衍生 / 等）
- 不是 R-X2 child service（关系图是节点附属关系，节点删除时关系自动 ON DELETE CASCADE 清掉就够）
- 但 design 应明示是否走 R-X2 显式调用（防 CASCADE 绕过 activity_log）— sprint 启动闸门 2.5 reconcile 时确认

**特殊触发点**：
- 图查询性能：N+1 / 递归查询限制
- 双向关系：是否每条关系存两次（A→B 和 B→A）vs 单向 + 查询时 OR

**特定红线**：
- ⚠️ R-X2 适用性闸门 2.5 复审：若 design §10 R10-1 batch3 要求节点删除时清关系图 + 写 per-record activity_log → 必须走 R-X2 注入；否则可走 DB CASCADE（design 应已决）
- 图查询防 N+1：邻接表 vs 物化视图 vs 递归 CTE — design 应已选

**起手 prompt**：

```
继续 prism-0420 M08 sprint 实施代码（M08 模块关系图；M{N-1} 完成）。

[通用启动序]

任务：M08 sprint TDD 实施。

模块特定要素：
- 主表 module_relations（节点间依赖/引用/衍生关系）
- R-X2 适用性需 sprint 启动闸门 2.5 复审：design §10 是否要求 per-record activity_log；如是 → 注入 child service；否则 DB CASCADE 兜底
- 图查询性能：design 应已选邻接表 / 物化视图 / 递归 CTE

模块特定红线：
- 双向关系 vs 单向 + OR 查询：design 应已决；闸门 2.5 不复议
- 防 N+1：批量加载关系时按 (project_id, source_node_id IN (...)) 一次查
- M04 audit punt R1-C C6.1 batch 形态升级触发条件：图深度 >50 时同款风险
```

---

## M09 — 搜索（search）

**模块特定**：
- 跨模块只读聚合（节点 / 维度 / 竞品 / 问题 / 等）
- ADR-003 规则 2 纯读聚合豁免 vs 规则 1 上游 Service 调用——M09 应走规则 2 豁免直查多表

**特殊触发点**：
- **第一次跨模块只读聚合**（与 M12 比较类似但 M12 后做）
- `batch_get_by_nodes` 跨模块接口：M04 punt R1-A A6 "service 缺包装" — M09 启动 reconcile 时若需要走 service 接口 → 触发补
- 全文搜索 vs 字段搜索（M18 才是语义/向量；M09 是字面）

**特定红线**：
- ⚠️ 多表 join 性能：search 是 hot path；design 应已选索引策略
- ADR-003 规则 2 豁免严守：纯读聚合不写 activity_log
- M04 punt R1-A A6 (`batch_get_by_nodes` service 缺包装) — M09 是首个真使用 batch_get_by_nodes 的 caller？若是 → 触发 M04 service 层补包装

**起手 prompt**：

```
继续 prism-0420 M09 sprint 实施代码（M09 搜索；M{N-1} 完成）。

[通用启动序]

任务：M09 sprint TDD 实施。

模块特定要素：
- 第一个跨模块只读聚合模块（ADR-003 规则 2 纯读豁免直查多表）
- M04 punt R1-A A6 触发评估：M09 是否首个真用 batch_get_by_nodes 的 caller？是 → 推 M04 service 层补包装
- 字面搜索（M18 才是语义/向量）

模块特定红线：
- 纯读聚合不写 activity_log（ADR-003 规则 2 豁免）
- 跨模块多表 join 索引策略：design 应已选；闸门 2.5 复审
- M09 hot path 性能：design 估算 query latency target
```

---

## M10 — 全景图（overview）

**模块特定**：
- 项目首页全景视图：节点树 + 维度填充率 + 最近活动 + 等聚合
- 跨模块只读聚合（同 M09 范式）
- G7 删 US-C1.1 → out of scope（与 M03 关系：M10 不实装"添加节点"功能）

**特殊触发点**：
- 与 M09 类似的跨模块聚合范式
- 与 M15 activity_stream 集成（最近活动；M15 此期可能仍是 B2.3 stub log，M10 显示历史活动需要 M15 真实装后）

**特定红线**：
- ⚠️ M15 集成：M10 sprint 期 M15 是否已升级真 DB INSERT？若没有 → M10 全景图"最近活动"段使用 placeholder 或推迟到 M15 后
- 全景图 query 性能：dashboard hot path
- 跨多模块聚合（≥3 个）的 ADR-003 豁免边界确认

**起手 prompt**：

```
继续 prism-0420 M10 sprint 实施代码（M10 全景图；M{N-1} 完成）。

[通用启动序]

任务：M10 sprint TDD 实施。

模块特定要素：
- 跨模块只读聚合范式（同 M09）
- 与 M15 activity_stream 集成：sprint 启动核对 M15 是否已升级真 DB INSERT
- G7 删 US-C1.1 后：M10 不实装"添加节点"

模块特定红线：
- M15 stub 期 M10 全景图"最近活动"段策略：placeholder vs 推迟实装段（design 应已决）
- 全景图 hot path 性能 + ADR-003 规则 2 豁免严守
- 跨 ≥3 模块聚合时确认豁免边界（design §6 cross_module_reads 完备性）
```

---

## M11 — 冷启动 / 项目模板（cold-start）

**模块特定**：
- **第一个 R-X1 orchestrator**（不直 INSERT 跨模块表，必须通过其他模块 Service.batch_create_in_transaction 调用）
- 调用 M03 NodeService.batch_create_in_transaction + M04 DimensionService.batch_create_in_transaction（M04 punt：M11 sprint 期才实装）+ M07 IssueService.batch_create_in_transaction
- 闸门 2.6（M17 前置 queue scaffold mini-sprint）— M11 是否需要 queue？通常冷启动同步即可（不投递 Queue）

**特殊触发点**：
- **M04 punt 接通**：M11 是 M04 `batch_create_in_transaction` 的第一 caller — M04 sprint 把它推给 M11；M11 sprint 期实装 M04 service 层 batch_create_in_transaction（design §6 cross-module 接口）
- 同款触发 M03 / M07 service 层 batch_create_in_transaction
- R-X1 严守：不直 INSERT，全走 service.batch_*

**特定红线**：
- ⚠️ R-X1 严守：M11 不直查/直写 nodes/dimension_records/competitor_refs/issues；通过 service.batch_*
- M04 sprint punt R1-A A5 "batch_create 拓扑责任" — M11 sprint 期决（M04 punt B 半路径推迟，"caller 已排序"简化版；M11 决定是否升级 service 加最小拓扑 vs caller 必排序契约）
- 事务原子性：M11 全流程包在一个 `async with db.begin():` 内（R-X3 + ADR-001）
- 测试覆盖：冷启动整链端到端（>10 节点 + 多维度 + 多 issue）

**起手 prompt**：

```
继续 prism-0420 M11 sprint 实施代码（M11 冷启动；M{N-1} 完成）。

[通用启动序]

任务：M11 sprint TDD 实施。

模块特定要素：
- 第一个 R-X1 orchestrator（不直 INSERT，全走 service.batch_*）
- M04 punt 接通：M11 是 M04.DimensionService.batch_create_in_transaction 的第一 caller
  → M04 service 层 batch_create_in_transaction 此 sprint 期才实装
- 同款触发 M03.NodeService.batch_create_in_transaction 实装 + M07.IssueService 同款
- M03 sprint punt A5 "batch_create 拓扑责任"：M11 sprint 期定（service 加最小拓扑 vs caller 必排序契约）
- 闸门 2.6 queue scaffold：M11 通常同步无需 queue（design 应已决）

模块特定红线：
- R-X1 严守：M11 不直查/直写下游表
- 事务原子性：全流程一个 async with db.begin()（R-X3 + ADR-001）
- 测试覆盖：冷启动整链端到端（>10 节点 + 多维度 + 多 issue），失败回滚验证
- M04 punt R1-A A5 / R1-C C6.1 / R1-A A6（batch 接口相关 punt）— M11 启动复审
```

---

## M12 — 对比矩阵（comparison）

**模块特定**：
- 跨模块只读聚合（多 node × 多 dimension_type 拉 dimension_records）
- M04 design §6 对外契约 `batch_get_by_nodes` 为 M12 而设
- M04 sprint punt R1-A A6 "service 缺包装" — M12 启动 reconcile 时触发 M04 service 包装补建

**特殊触发点**：
- **M04 punt 接通**：M12 是 batch_get_by_nodes 的第一 caller — M12 启动时 M04 service 层补 batch_get_by_nodes 包装（DAO 已实装）
- 同款触发 M06 batch_get_by_nodes / M07 list_by_project（M07 已 pass-through 登记）
- 对比矩阵 query 性能：(project_id, node_id IN, dimension_type_id IN) 索引覆盖

**特定红线**：
- ⚠️ M04 punt R1-A A6 触发：M12 sprint 期补 M04 DimensionService.batch_get_by_nodes（已 DAO 层实装；service 层 pass-through）
- 跨多个 R-X3 接口聚合：design §6 对外契约严守
- 矩阵 cell-by-cell 查询防 N+1：一次性 batch_get_by_nodes 拉全量

**起手 prompt**：

```
继续 prism-0420 M12 sprint 实施代码（M12 对比矩阵；M{N-1} 完成）。

[通用启动序]

任务：M12 sprint TDD 实施。

模块特定要素：
- 跨模块只读聚合：M04.DimensionService.batch_get_by_nodes + M06 同款 + M07 list_by_project
- M04 punt R1-A A6 接通：M12 启动时 M04 service 层补 batch_get_by_nodes 包装（DAO 已实装）
- (project_id, node_id IN, dimension_type_id IN) 索引覆盖；M04 已建 ix_dim_node_type / ix_dim_project_updated

模块特定红线：
- 走 service 接口（ADR-003 规则 1 上游调用）；不直查 DAO 跨模块表
- 矩阵防 N+1：一次性 batch 拉全量
- 纯读聚合不写 activity_log（ADR-003 规则 2 豁免）
```

---

## M13 — AI 需求分析（requirement-analysis）

**模块特定**：
- AI 推理模块（调 LLM）—— 第一个真接 LLM 模块？或仅 prompt 层
- M04 design §6 对外契约 `create_dimension_record` + `get_latest` 为 M13 而设（pilot 基线补丁追加）

**特殊触发点**：
- **M04 punt 接通**：M13 是 M04 create_dimension_record / get_latest 的第一 caller — M13 sprint 期 M04 service 层实装这两个接口
- LLM 集成：cost / latency / 安全性（feedback_llm_hotpath_math）
- M07 IssueService.list_by_project 跨模块调用（已 pilot 登记）

**特定红线**：
- ⚠️ feedback_llm_hotpath_math：LLM 接进 hot path 前必报频率×延迟×cost 4 数字 + 3 红线
- M13 是否实装为同步 endpoint vs 异步 queue？design 应已决；若同步 → 接口 SLA 估算
- M04 punt 接通：M04 service 层 create_dimension_record（含 extra_activity_metadata 合并）+ get_latest（按 dimension_type_key 拿最新一条）
- 安全：LLM 不接管 dimension content schema 校验（jsonschema 仍 service 层做）

**起手 prompt**：

```
继续 prism-0420 M13 sprint 实施代码（M13 AI 需求分析；M{N-1} 完成）。

[通用启动序]

任务：M13 sprint TDD 实施。

模块特定要素：
- 第一个真 LLM 集成模块（feedback_llm_hotpath_math 触发）
- M04 punt 接通：M13 是 M04.DimensionService.create_dimension_record + get_latest 的第一 caller
  → M04 service 层此 sprint 期实装两接口（含 extra_activity_metadata 合并机制）
- M07 list_by_project 跨模块调用（已 pilot 登记，pass-through 即可）
- LLM 同步 vs 异步 queue：design 应已决

模块特定红线：
- feedback_llm_hotpath_math: 必报频率×延迟×cost 4 数字 + 3 红线（单跑<周期/2 + flock + cost ceiling）
- feedback_monkeypatch_not_verification: LLM monkeypatch ≠ 生产路径；端到端需真 LLM smoke
- jsonschema 校验仍 service 层做（不让 LLM 接管）
- M04 punt R2 A4 "jsonschema 二次校验"接通：M13 真前端跑通时补
```

---

## M14 — 行业资讯（industry-news）

**模块特定**：
- 主表 `industry_news`（项目级新闻订阅 + 抓取记录）
- 涉及 cron / queue（M14 design 应已决）— 与 M16/M17/M18 cron 模块同款约束（ADR-002 §1.1 SYSTEM_USER_UUID）

**特殊触发点**：
- 闸门 2.6 (M17 前置 queue scaffold) — M14 sprint 启动核对 queue scaffold 是否已落地（B1-B10 期未单列 queue scaffold；reconcile S5）
- ADR-002 §1.1 cron 模块 SYSTEM_USER_UUID 约束（M14 §12 cron 段加 1 行明确指引；M01 sprint 后置债 P5 F-4 收口已完成）

**特定红线**：
- ⚠️ Queue scaffold 前置：M14 sprint 前必须 queue/__init__.py + base.py:TaskPayload 落地（闸门 2.6）
- ADR-002 §1.1 SYSTEM_USER_UUID 严守：cron payload.user_id 走该常量
- 抓取节流：rate limit / dedup（防爬虫被 ban）

**起手 prompt**：

```
继续 prism-0420 M14 sprint 实施代码（M14 行业资讯；M{N-1} 完成）。

[通用启动序]

任务：M14 sprint TDD 实施。

模块特定要素：
- 主表 industry_news（项目级新闻订阅 + 抓取记录）
- cron + queue 模块（与 M16/M17/M18 同款约束）
- 闸门 2.6 前置：queue scaffold (api/queue/__init__.py + base.py:TaskPayload) 必须已落地
- ADR-002 §1.1 SYSTEM_USER_UUID 约束：cron payload.user_id 走该常量

模块特定红线：
- Queue scaffold 闸门 2.6 严守：未落地 → 不开 M14
- 抓取节流 rate limit / dedup
- feedback_adversarial_dataflow_design：scanner/collector 必走 3 闸门（4 对抗问 + 喂回测试 + 24h dry-run）
- feedback_llm_hotpath_math 若用 LLM 摘要新闻
```

---

## M15 — 数据流转 / 活动流（activity-stream）

**模块特定**：
- **横切模块升级**：activity_log_service B2.3 stub → 真 DB INSERT
- M04 sprint 起所有模块用的 `write_event` 此期升级真实装
- M04 sprint punt 池中 ≥5 项与 M15 相关（"M15 sprint 升级真 INSERT 时端到端复审"）

**特殊触发点**：
- **M04 punt 全面接通**：write_event B2.3 stub 升级；M01-M14 所有 write_event 调用一次性走真路径
- M15 同时 own activity_logs 表 + activity_stream 推送 / 实时订阅（design 应已决）
- target_type / action_type 常量化（M04 sprint R1-B B6 P3 punt 接通）

**特定红线**：
- ⚠️ 不向后兼容风险：write_event 接口签名不能变（M01-M14 已稳定调用）；只升级实现
- M04 audit punt R1-C C9.3 monkeypatch ≠ 生产路径 — M15 sprint 期 router/integration 测试端到端验证 write_event 真 DB INSERT
- bulk insert 性能：批量 cascade delete 时一次 INSERT 多行
- M04 audit punt R1-C C1.2 "delete_by_node_id 并发 continue 漏写 activity_log" — M15 升级时复审是否需要补

**起手 prompt**：

```
继续 prism-0420 M15 sprint 实施代码（M15 数据流转 / 活动流；M{N-1} 完成）。

[通用启动序]

任务：M15 sprint TDD 实施。

模块特定要素：
- 横切模块升级：activity_log_service B2.3 stub → 真 DB INSERT
- M04 punt 全面接通：write_event 接口签名不变；只升级实现；M01-M14 调用方一次性走真路径
- M15 own activity_logs 表 + activity_stream 推送 / 实时订阅
- target_type / action_type 常量化（M04 sprint R1-B B6 P3 punt 接通）

模块特定红线：
- write_event 接口签名严禁变（向后兼容 M01-M14）
- M04 audit punt R1-C C9.3：M15 期 router/integration 测试必端到端验证 write_event 真 DB INSERT
- bulk insert 性能：cascade delete 一次 INSERT 多行
- M04 audit punt R1-C C1.2 "并发 continue 漏写 activity_log" — 升级时复审
- L12 守护扩展：原 auth_service 不引用 activity_log_service 守护此期取消（M15 后 auth_service 也可调）
```

---

## M16 — AI 快照（ai-snapshot）

**模块特定**：
- AI 推理 + cron 模块
- ADR-002 §1.1 SYSTEM_USER_UUID（M01 sprint 后置债 F-4 已收口）
- 与 M14/M17/M18 cron 模块同约束

**特殊触发点**：
- LLM 调用（feedback_llm_hotpath_math）
- cron 触发：feedback_adversarial_dataflow_design 3 闸门
- 与 M11 冷启动协作？或与 M13 区分？— design 应已界定

**特定红线**：
- ⚠️ feedback_llm_hotpath_math 强制：cron 单跑 < 周期/2 + flock + cost ceiling
- feedback_monkeypatch_not_verification：LLM/HTTP 不能仅 monkeypatch
- ADR-002 SYSTEM_USER_UUID 严守
- 快照内容长度 / 存储位置 / 过期清理

**起手 prompt**：

```
继续 prism-0420 M16 sprint 实施代码（M16 AI 快照；M{N-1} 完成）。

[通用启动序]

任务：M16 sprint TDD 实施。

模块特定要素：
- AI 推理 + cron 模块（与 M13/M14/M17/M18 同约束）
- ADR-002 §1.1 SYSTEM_USER_UUID
- LLM 调用（feedback_llm_hotpath_math 触发）

模块特定红线：
- feedback_llm_hotpath_math: cron 单跑 < 周期/2 + flock + cost ceiling
- feedback_adversarial_dataflow_design: scanner/collector 3 闸门（4 对抗问 + 喂回测试 + 24h dry-run）
- feedback_monkeypatch_not_verification: LLM/HTTP 不能仅 monkeypatch；端到端真路径
- 快照存储位置 + 过期清理策略
```

---

## M17 — 智能导入（ai-import）

**模块特定**：
- **第二个 R-X1 orchestrator**（M11 之后；不直 INSERT）
- LLM + cron + queue（最重的复合模块）
- 闸门 2.6 (queue scaffold) 严守

**特殊触发点**：
- M11 已立 R-X1 范式 → M17 follow
- M04 sprint punt 池：M17 是 batch_create_in_transaction 的第二 caller（M11 第一）— 范式已稳定
- queue scaffold (api/queue/base.py:TaskPayload) 严守 user_id + project_id 字段

**特定红线**：
- ⚠️ 闸门 2.6 queue scaffold 已落地（M14 sprint 前置）— M17 follow 不重做
- feedback_llm_hotpath_math + feedback_adversarial_dataflow_design 双重触发
- ADR-002 §1.1 SYSTEM_USER_UUID 严守
- batch_create_in_transaction 调用方失败回滚整链

**起手 prompt**：

```
继续 prism-0420 M17 sprint 实施代码（M17 智能导入；M{N-1} 完成）。

[通用启动序]

任务：M17 sprint TDD 实施。

模块特定要素：
- 第二个 R-X1 orchestrator（M11 后；不直 INSERT，全走 service.batch_*）
- LLM + cron + queue（最重的复合模块）
- 闸门 2.6 queue scaffold 严守（M14 sprint 前已落地）
- M04 batch_create_in_transaction 第二 caller（M11 第一已立范式）

模块特定红线:
- R-X1 严守 + ADR-002 SYSTEM_USER_UUID
- feedback_llm_hotpath_math: 频率×延迟×cost 4 数字
- feedback_adversarial_dataflow_design: scanner 3 闸门
- queue payload TaskPayload 强制 user_id + project_id (B2.4 scaffold)
- batch_create 失败回滚整链（事务原子性 + 异常向上传播）
```

---

## M18 — 语义搜索（semantic-search）

**模块特定**：
- **embedding_service own 模块**（M03/M04/M06/M07 baseline-patch B 推迟 caller 此期接通）
- M04 punt R-X5 子选项 1 接通：DimensionService 三处 commit 后尾调 embedding_service.enqueue + delete 后 enqueue_delete + SilentFailure + cleanup cron 兜底
- 同款触发 M03 NodeService / M06 CompetitorService / M07 IssueService 的 enqueue 接通

**特殊触发点**：
- **M04 punt 全面接通（A5 enqueue B 推迟）**：M03/M04/M06/M07 commit 后尾调 enqueue
- get_for_embedding A 路径已在各模块 sprint 期实装（M04 已 unit test 覆盖）— M18 此期补生产路径端到端测试
- SilentFailure 设计（非 AppError 子类，不被通用 try/except 捕获）+ embedding_failures 表 + cleanup cron

**特定红线**：
- ⚠️ M04 sprint A5 子选项接通 4 处（M03/M04/M06/M07）— grep design §6.X "M18 sprint 扩齐" 段一次性核对
- feedback_llm_hotpath_math: embedding API 频率×延迟×cost
- feedback_monkeypatch_not_verification: embedding monkeypatch ≠ 生产路径
- get_for_embedding 各模块 unit 已覆盖默认拼接路径；M18 sprint 补生产路径整链
- SilentFailure 异常体系：与 AppError 严格区分

**起手 prompt**：

```
继续 prism-0420 M18 sprint 实施代码（M18 语义搜索；M{N-1} 完成）。

[通用启动序]

任务：M18 sprint TDD 实施。

模块特定要素：
- embedding_service own 模块；M03/M04/M06/M07 baseline-patch B 推迟 caller 此期接通
- M04 sprint A5 子选项接通 4 处（M03/M04/M06/M07）— grep design §6.X "M18 sprint 扩齐"
- get_for_embedding A 路径已各模块 unit 覆盖；M18 期补生产路径整链
- SilentFailure 设计（非 AppError 子类）+ embedding_failures 表 + cleanup cron

模块特定红线:
- M04 punt A5 接通：M03/M04/M06/M07 commit 后尾调 enqueue + delete 后 enqueue_delete
- feedback_llm_hotpath_math: embedding API 频率×延迟×cost
- feedback_monkeypatch_not_verification: embedding monkeypatch ≠ 生产路径
- SilentFailure vs AppError 严格区分（不被通用 try/except 捕获）
- 向量索引性能 / 召回率 baseline
```

---

## M19 — 导入导出（import-export）

**模块特定**：
- 横切功能（CSV / JSON / 等格式）
- 不是 R-X1 orchestrator（与 M11/M17 区分：M11/M17 是 LLM+template 触发；M19 是用户上传文件）
- 也不是 R-X2 child service

**特殊触发点**：
- batch_create_in_transaction 第三 caller（M11/M17 后；范式稳定）
- 与 M04/M06/M07 export 路径：走 list 接口（pass-through）

**特定红线**：
- ⚠️ 文件大小 / 行数限制（防 OOM）
- 字符编码 / CSV 转义 / Excel 兼容性
- 异步处理 vs 同步：design 应已决（大 CSV 走 queue）

**起手 prompt**：

```
继续 prism-0420 M19 sprint 实施代码（M19 导入导出；M{N-1} 完成）。

[通用启动序]

任务：M19 sprint TDD 实施。

模块特定要素：
- 横切功能（CSV / JSON / 等）；不是 R-X1 orchestrator / 不是 R-X2 child service
- batch_create_in_transaction 第三 caller（M11/M17 范式稳定后）

模块特定红线:
- 文件大小 / 行数限制（防 OOM）
- 字符编码 + CSV 转义 + Excel 兼容性
- 异步 vs 同步：大文件走 queue（design 应已决）
- 导入失败回滚整链（事务原子性）
```

---

## M20 — 团队（team）

**模块特定**：
- **空间 / 团队**：design ADR-001 决策"不引入空间概念，预留 space_id 扩展口"——M20 是该决策的实装方
- M02 sprint 已建 tenant_filter B2.4 scaffold S2 注入点（M02TenantContext only project_members）；M20 sprint 升级 UNION（project_members ∪ team_members）

**特殊触发点**：
- **B2.4 scaffold S2 升级**：tenant_filter set_tenant_context 注入新的 M20TenantContext（UNION）
- M02 PROJECT_ARCHIVED ErrorCode F2.3 + 跨模块 baseline-patch：M02 design 期已含 M20 baseline-patch 段
- team_members 表 + role 体系（与 project_members 合流但独立表）

**特定红线**：
- ⚠️ tenant_filter 升级不能 break M01-M19 现有测试（向后兼容；project_members 仍工作）
- M02 baseline-patch move-team scaffold caller 子片 4 已推迟 → M20 sprint 期决策实装
- ADR-001 space_id 预留口：M20 启用后是否需要回填？（design 应已决）
- tenant_filter UNION 性能：索引覆盖

**起手 prompt**：

```
继续 prism-0420 M20 sprint 实施代码（M20 团队；M{N-1} 完成）。

[通用启动序]

任务：M20 sprint TDD 实施。

模块特定要素：
- 空间 / 团队：ADR-001 "不引入空间概念，预留 space_id" 的实装方
- B2.4 scaffold S2 升级：tenant_filter 注入 M20TenantContext (UNION project_members ∪ team_members)
- M02 baseline-patch move-team scaffold caller 子片 4 推迟项接通
- M02 PROJECT_ARCHIVED ErrorCode F2.3 集成

模块特定红线:
- tenant_filter 升级不 break M01-M19 测试（向后兼容；project_members 仍工作）
- B2.4 S2 4 字段注释回写 status="已落地 + commit hash"
- ADR-001 space_id 预留口决策接通
- tenant_filter UNION 性能 + 索引覆盖
- M02 audit punt 池"M20 sprint 期决"项一次性核对（grep audit/m02-pilot-template-validation.md）
```

---

## 维护规则

- 每个 M{XX} sprint 启动当天：复制对应 prompt 段落 → 替换 `M{N-1} commits ... / N PASS / Phase 2.1 X%` 为真实最新值
- sprint 完成后：本文件不改（M{XX} prompt 留作历史模板）；handoff next-session.md 的 Prompt 0 指向下一个模块
- M04 sprint punt 池消化进度跟踪：每 sprint 关闸后核对 audit/m04-pilot-template-validation.md 哪些 punt 项被本 sprint 接通

## 关联

- M04 sprint 完整闭环：commits 4c3c413 → 4aab909（GitHub CY1005/prism-0420）
- 三数据点稳定 audit：design/audit/m{02,03,04}-pilot-template-validation.md
- 跨项目方法论 v1.0 候选：ai-quality-engineering KB 30-技术-自学/架构设计/设计前置方法论-补丁02-跨项目应用SOP-v0.1.md
