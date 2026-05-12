---
title: Lessons Learned — 2026-05-12 batch（M05 / M14-M16 reconcile 教训 3 条）
status: lessons
owner: CY
created: 2026-05-12
source_scan: _handoff/unsunk-scan-2026-05-12/chunk_6.md
findings: F-6.1, F-6.10, F-6.11
---

# Lessons Learned — 2026-05-12 batch

> 由 prism-0420 未沉淀扫描批量沉淀的 reconcile / sprint 工序教训。三条独立，与主 `lessons-learned.md`（M01 D1）正交。

---

## 教训 A — 闸门 2.5 三栏分类自审仪式化失效

**来源**: `_handoff/unsunk-scan-2026-05-12/chunk_6.md F-6.1`（session `152bff88`，2026-05-09 M05 sprint reconcile）

**现象**：M05 sprint reconcile pass 中，Claude 把 5 个已有规则的机械应用项（covering 索引范式、quality-spec 关键路径、M04 punt 到期工序等）错误列为 B 栏让 CY 拍板。被 CY 一句"按照步骤分析做决定，做不出决定就是分析不对"点出后，重走流程后 B 栏归零。

**根因**：reconcile 自审流程中"真有候选吗"这一关虽然形式上问了，但没有先 grep design/audit/memory 既有规则，直接判断为"真权衡 ✅"——自审走的是仪式而非实质。根本公式错误："我有倾向 + 看似取舍 = B 栏"——但这个公式漏了第 0 步：倾向的那个候选是否恰好就是既有规则机械应用的结果？是的话 = A 栏，不是 B 栏。

**修法**：三栏自审前必须先完成 5 步分层第 1-2 步（识别+定层+找既有锁定项）。具体操作：grep design/audit/memory 既有规则 → 命中 → A 栏（机械执行）或 C 栏（用户已自决无需二次拍板）；grep miss 才进入 L2 候选枚举流程，这时才有资格出现真 B 栏。

**适用范围**：所有 reconcile pass 的三栏分类，包括 sprint 启动闸门 2.5 场景。

---

## 教训 B — 跨 sprint baseline-patch 反向修复工序

**来源**: `_handoff/unsunk-scan-2026-05-12/chunk_6.md F-6.10`（session `fb1ffdc9`，2026-05-08 M15 sprint reconcile）

**现象**：M14 sprint 实装 `action_type` 时使用 `"create"/"update"/"delete"/"link"/"unlink"` 裸 CRUD，违反了 M02-M13 十一个数据点稳定的 `{entity}_{past_verb}` 命名规约（该规约由 2026-05-06 baseline-patch 建立，CY 明确 ack）。M15 reconcile pass 时 Claude 首先将此问题误报为 B 栏，CY 指出"原则性问题，有现有规则解决不了吗"——这是第二次自审失效的典型信号，与教训 A 同根因。

**根因**：M14 sprint 实装时没有在实装前 grep 既有命名规约，导致命名漂移；M15 reconcile 首次自审时又未走 5 步分层第 1 步 grep，直接误归 B 栏。命名规约 baseline-patch 是 CY 自己 2026-05-06 ack 立的，M01-M13 11 模块严格遵守——M14 是漂移源不是规约新基线。

**修法（已验收的 α 路线工序）**：

1. grep 确认漂移范围（M14 service.py 5 处 + tests 7 处 + design §10）
2. 5 步分层定层 → L1 锁规（既有规约，无歧义）
3. AI 自决（不出 B 栏让 CY 拍）
4. 机械批量改：M14 service.py → tests → design §10 → M15 design §3 同步新值

**推广**：任何发现"某 sprint 实装漂移已确立的命名/结构规约"时，此工序可复用。识别信号：某模块 action_type / ErrorCode / 命名范式与其他 N 个已有模块不一致，且不一致来源是遗漏而非新决策。

---

## 教训 C — reconcile 工作量估算必须 grep 真实代码

**来源**: `_handoff/unsunk-scan-2026-05-12/chunk_6.md F-6.11`（session `69105db2`，2026-05-08 M16 sprint reconcile）

**现象**：M16 冷启动 prompt 估算"M03-M08 service 约 14 处裸 CRUD action_type 需反向回写"，实际 reconcile grep 后发现约 31 处（含 M02 project_service 2 处、M11 cold_start 3 处 dot→underscore 命名漂移未计入初始估算）。工作量从估计 4-6h 实际落到 8-12h，再加 write_event stub + race window 复审升至 12-16h——偏差 2-3×。

**根因**：工作量估算依赖 design 文字描述 + 历史印象，而非真实代码 grep 结果。Design 文档记录的是设计意图，不反映代码实际分布；历史印象则系统性低估了"同一错误在不同模块中扩散"的程度。这是 `feedback_decision_codefirst_validation` 在 PRISM 内部的具体实证（2026-05-12 已独立立规）。

**修法**：reconcile pass 启动前，凡涉及批量枚举修复类任务，必先 grep 真实代码统计命中数，再报工作量区间。具体步骤：

1. `grep -rn "action_type.*create\|action_type.*delete" api/` 等模式，得到真实命中行数
2. 以命中行数 × 单次改动成本估工时
3. 若 grep 结果与设计文字描述偏差 >50%，先向 CY 同步真实数字再确认 sprint 范围

**注意**：此教训不只适用于 action_type 修复，任何"预期影响 N 处"的批量修复任务都适用。设计文字描述的 N 往往是"已知模块清单"，grep 结果会揭露"顺带命中的遗漏模块"。

---

## 关联

- `design/audit/lessons-learned.md` §7 关联（主索引，本文件交叉引用）
- `feedback_problem_layered_analysis.md` — 5 步分层（教训 A/B 修法的核心方法）
- `feedback_decision_codefirst_validation.md` — code-first 验证（教训 C 的元规则）
- `_handoff/unsunk-scan-2026-05-12/chunk_6.md` — 完整 raw findings
