---
title: M10 sprint 实证 + R1/R2 命中比例 + L1 第八数据点
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M10 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀。

  - **纯读聚合范式首次实证**（无 model/migration / ADR-003 规则 2 豁免 / 4 子片代替 5 子片简化范式）
  - 闸门 2.5 三栏：A 5 / B 0 / C 7（**第五次 B 栏 0 项**）
  - R1=1 合并 Opus subagent + R2=1 合并 Opus subagent（M10 简化范式：R1 三 subagent 合并为 1）
  - L1+L2+L3 节奏第八次实证（八数据点稳定 → M11+ 默认范式可作模板）
  - 元教训新增 2 条：(1) 纯读模块无写端点强契约通道 → schema-service contract drift 风险；
    (2) R1 P1 立修后被 reviewer 误连 false positive 一起撤销 → R1→R2 reconcile 缺失
last_reviewed_at: 2026-05-08
---

# M10 sprint 实证 + Review 命中比例

## 闸门 2.5 reconcile 三栏（M10 sprint 启动当天 / 第五次 B 栏 0 项实证）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 5 | A1 §14.5 默认范式段补 / A2 conftest 复用 / A3 ADR-003 规则 2 豁免（design 已立）/ A4 folder 均值迭代后序遍历（design D-1 已锁）/ A5 元教训防御 actionable：cross-tenant 404 + 401 + viewer 读 200（M10 无写端点 viewer 写不适用）|
| **B 待 CY 决策** | **0** | （第五次 B 栏 0 项 / M05+M06+M07+M08+M10 五连稳定）|
| **C 已自我消解** | 7 | C1 ADR-003 方案 A 已决 / C2 完善度阈值前端 / C3 folder 均值算法 / C4 单 project / C5 R-X2 N/A（纯读）/ C6 状态机/idempotency/Queue/activity_log 全 N/A / C7 batch_create 推迟 |

---

## R1 review 命中（1 合并 Opus subagent / 子片 1+2 合并审 / **M10 简化范式：3 subagent → 1 合并**）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | folder.filled_count 子树聚合（design §7 NodeOverview "file 自身 / folder 子树汇总" 字面 drift）| **重立修**（R2 抓后真做）：sum_filled 三元组 + folder 节点 r["filled_count"] = sum_filled |
| P1-02 | OverviewProjectNotFoundError 生产路径不可达（router check_project_access 已拦）| 立修：code 注释（M02 R-X5 范式 R13-1 parity 保留 pattern 同款） |
| P1-03 | _build_tree 递归未豁免 D-1（rate 算法严守迭代但 tree 排序仍递归）| 立修：design §3 D-1 disambiguation 注释（rate 算法 vs tree 排序作用域不同；CY 场景 depth<20 可接受）|
| P1-04（false positive 撤销）| asyncio.gather 并行 _check_project_exists + count_enabled_dimensions | **撤销**：SA AsyncSession 同 session 不允许 concurrent IO；保持串行 await。**元教训**：reviewer 建议优化跨 await 时必须 grep `concurrent_to`/`Lock` 等 SA 文档限制 |
| P2 #1 | _make_dim_record 跨 dao+service test 重复 → 迁 conftest（M03 R1-B C1 规则）| 立修 make_dim_record fixture（M04+M05+M06+M07+M08+M10 六连规则延续）|
| P2 多 | count(*) 优化范式偏离 / N+1 风险 / archived project / NodeCompletionResponse 死代码 | punt 子片 4 audit 或后续 sprint |

**M10 R1 简化范式**：因 M10 是纯读聚合无 model/migration（DAO 层 LEFT JOIN 即一切），R1 把 spec+quality+reuse+efficiency 4 维合并为 1 Opus subagent — 实证简化 OK，命中范围与 M02-M08 三 subagent 拆分相当（七数据点对照可作 M11+ "纯读模块" 简化模板）。

---

## R2 review 命中（1 合并 Opus subagent / 子片 3 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | folder.filled_count subtree rollup R1 立修被 CY 误撤（与 asyncio.gather false positive 一起撤销）| **重立修**（commit 8166703 后追加）：sum_filled 三元组 + test 加 folder.filled_count 断言 |
| P1-02 | R1→R2 reconcile 缺失（启动包陈述 asyncio.gather 已立修但代码已撤销）| audit 注明撤销 / handoff 口径修正 |
| P2 #1 | design §7 endpoint 数量字面 drift（design 列 3 / 实装 2 + M04 复用 1）| 子片 4 design §7 disambiguation 已落 |
| P2 #2 | NodeCompletionResponse 死 schema 无契约方持有 | 留 + design §7 disambiguation 注明"未来 M04 委托可用"|
| P2 #3 | viewer 读 200 测试只覆盖 /overview 未覆盖 /overview/stats | punt M11 sprint 启动前补 |
| P2 #4 | fully_complete_nodes >= 1.0 vs empty_nodes == 0.0 不对称（潜在浮点）| SKIP（current rate 整数除法 + 1.0 cap 等价）|

**R2 命中**：2 P1（folder.filled_count 重立修 + R1→R2 reconcile 缺失元教训）+ 4 P2 — 与 M02-M08 R2 P1 命中 0-1 区间**M10 上限 2**（含元教训新发现），第八数据点稳定。

---

## 元教训（M10 sprint 新增）

### 新增 1 — **纯读模块 schema-service contract drift 风险**（首次实证）

**触发**：M10 是纯读聚合首次实证。无写端点 = **无强契约校验通道**（viewer 写 403 / activity_log / migration / IntegrityError 等 M02-M08 强契约都不适用）。schema 字段语义只能靠 docstring + 测试断言守。

**关键决策点**：folder.filled_count 字段 design §7 docstring 字面 "file 自身 / folder 子树汇总"，但 R1 立修期 sum_filled 三元组被误连 asyncio.gather false positive 一起撤销，service mutate 只改 completion_rate 不改 filled_count → API JSON 自相矛盾（folder.completion_rate=0.75 / folder.filled_count=0）。

**根因**：M02-M08 业务模块靠"写端点 contract + activity_log + IntegrityError"三层强契约通道兜底，绿测 ≠ 范式正确尚有兜底。M10 三层都不存在，绿测漏断 folder.filled_count 直接漂移到 production JSON。

**沉淀**：feedback_problem_layered_analysis 失效信号新增（子片 4 commit 同步）：
> ❌ 纯读聚合模块（无写端点 / 无 activity_log / 无 IntegrityError）docstring 字段语义必须配套 **每个字段 1 个 unit test 断言守护**；M10 R2 P1-01 实证缺断言导致 schema-service drift 漏过 R1 直到 R2 才被抓。**修法**：M11+ 纯读模块（M09 superseded / M10 / 未来）启动 reconcile 时主动列"docstring 字段断言"清单，对应 schema 每字段配 ≥1 unit test 断言。

### 新增 2 — **R1→R2 reconcile 缺失**（启动包陈述与代码状态对账漂移）

**触发**：R1 P1 立修期 CY 撤销 asyncio.gather（false positive：SA AsyncSession 不允许 concurrent IO 同 session）+ 误连撤销 sum_filled 三元组。但 R2 启动包仍把 asyncio.gather 列为"已立修项"，sum_filled 状态没核对 → R2 reviewer 看到代码 vs 启动包不一致暴露给 reviewer。

**关键决策点**：R1→R2 之间无 reconcile 步骤检查"R1 立修是否真做"。

**沉淀**：M11+ sprint 应在 R2 dispatch 前加 **R1.5 reconcile checkpoint**（grep R1 立修关键词在代码中真实存在）。本 audit 作 actionable 模板示例。

### 复用 1 — feedback_problem_layered_analysis B 栏 0 项

第五次 B 栏 0 项 — 5 步分层 step 1-2 grep 既有规则 + 自审"我倾向的恰好是范式机械应用？" 5 项原候选全 grep 命中 L1/L3 锁规归 A 栏。

### 复用 2 — feedback_design_scaffold_reconcile

design §7 endpoint 数量 disambiguation（设计字面 3 / 实装 2 + M04 复用 1）+ §3 D-1 disambiguation（rate 算法迭代 vs tree 排序递归作用域）— 本 sprint 双处实证 disambiguation 注释规约。

---

## L1+L2+L3 节奏第八次实证（M02-M10 — 八数据点稳定）

| 节奏层 | M10 sprint 表现 | 与 M02-M08 差异 |
|---|---|---|
| L1 总则 | ✅ R1+R2 共 2 次 review | 与 M02-M08 一致 |
| L2 sprint 计划（design §14.5）| ✅ M10 简化范式（4 子片 / R1 1 合并 Opus）| 首次"纯读模块简化范式"实证 |
| L3 实证回写（本文件）| ✅ accepted | 与 M02-M08 同款 |

**八数据点稳定结论**：M11+ 普通业务模块按 M02-M08 默认范式（5 子片 / R1=3 / R2=1）；纯读模块按 M10 简化范式（4 子片 / R1 合并 / R2=1）。

---

## PT1-PT3 复用判断（已回填到 m01-pilot-template-validation.md）

- **PT1**：❌ 不复用 — M10 无自有 model；本身就是纯读聚合无 schema 预留语义
- **PT2**：✅ 复用 — Router check_project_access 走 ADR-004
- **PT3**：❌ 不复用 — M10 无 model

---

## Punt 池总表（M10 sprint 末 6 项）

| 来源 | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|
| R1 P2 | count(*) 优化范式偏离 | P3 | M11 sprint 启动前一并清 |
| R1 P2 | get_node_completion N+1（M04 切节点反复扫整树）| P2 | M16 pilot 压测时升级 fast path |
| R1 P2 | _check_project_exists 不过滤 archived | P3 | design §1 in scope 未约束，可观察 |
| R2 P2 #2 | NodeCompletionResponse 死 schema | P3 | M04 委托或子片 4 删 |
| R2 P2 #3 | viewer 读 200 测试覆盖 /overview/stats 缺 | P2 | M11 sprint 启动前补 |
| R2 P2 #4 | fully_complete >= 1.0 vs empty == 0.0 浮点不对称 | P3 | 未来引入小数权重时复审 |

---

## 维护规则

- 本文件 status=accepted（M10 sprint 关闸）
- M11 sprint 启动闸门 2.5 reconcile 时复用本文件 R1/R2 命中 + 元教训防御 actionable 清单
- M10 简化范式（4 子片 / R1 合并）仅适用纯读聚合模块；M11+ 业务模块仍走 M02-M08 默认范式
- M16 pilot 压测时复审 R1 P2 N+1 / R1 P2 archived 过滤 / R2 P2 浮点不对称
