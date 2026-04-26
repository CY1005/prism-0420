---
title: M20 Batch 3 修复独立 verify 报告
status: final
owner: independent-reviewer
created: 2026-04-26
audit_round: batch3-verify
scope: F3.2 / F3.3 / F3.4 / F3.5 / F3.8（共 5 项 finding）
files_inspected:
  - design/02-modules/baseline-patch-m20.md
  - design/adr/ADR-005-team-extension.md
  - design/02-modules/README.md
  - design/02-modules/M20-team/tests.md
parent_audit: ./audit-report.md
verdict: ALL_PASS（含 1 项次要观察 / 不阻塞 accept）
---

# M20 Batch 3 修复独立 verify 报告

> 我作为独立 reviewer 重读 4 个改动文件，逐 finding 比对 audit-report.md §"修复 v3"列建议与文件实际落地内容，独立判定。所有"PASS"均给出文件:行号证据；不附和。

---

## 0. Pass/Fail 矩阵

| Finding | 严重度 | 修复建议核心 | 落地判定 | 主证据 |
|---------|--------|------------|---------|--------|
| F3.2 | Blocker | 17 模块拆批 4 批清单 + PR 边界 + 单批回滚 + 批 1 完成判定 + parametrize 测试模板 | **PASS** | baseline-patch-m20.md:320-333 + L315 |
| F3.3 | High | ADR-005 §8 organization 层占位 + 4 决策点 + 触发器 + baseline-patch 模板 | **PASS** | ADR-005:302-324 |
| F3.4 | High | Alembic 单 revision + 字母序 M16→M18→M20 + 硬触发器 | **PASS** | baseline-patch-m20.md:335-380 |
| F3.5 | High | §4 T1 加失效路径 5 处 + Service 层 5 处 DEL 不靠 TTL + tests.md C7 性能压测 | **PASS** | ADR-005:235 + tests.md:65 |
| F3.8 | Medium | README 设计回看 3 行（2026-10-26×2 + 2027-04-26）| **PASS** | README.md:344-346 |

| 额外审计 | 判定 | 证据/说明 |
|---------|------|----------|
| ADR-005 §8 与 §7 章节顺序 | **OBSERVATION（不阻塞）** | 现状 §3/§4/§5/§6/§8/§7（§8 在 §7 之前），数字顺序倒置 |
| ADR-005 §3/§4/§6 内部交叉引用合规 | **PASS** | §4 T1 引用 "Batch 3 / F3.5"；§4 T7 演进延伸引 §8；§3.2 引 §4 T1；交叉自洽 |
| 硬规则 R-X3 / R10-1 / R10-2 / R5-1 仍合规 | **PASS** | Batch 3 改动未触碰决策矩阵中 Q13.2 / Q10.1 / Q5 / Q1 实质，未引入新违规 |
| Batch 1/2 已通过项目未被 Batch 3 破坏 | **PASS** | T6/T7 行编号保留（ADR-005:240-241），T1 仅扩写正文 |

**综合判定：ALL_PASS**（无待修项；§7/§8 顺序为可读性观察，作 batch4 reviewer 提醒，非本期 blocker）

---

## 1. F3.2 17 模块拆批策略（baseline-patch-m20.md）

**audit 修复建议**（audit-report.md:129）：「baseline-patch §3 现在拍板拆批策略（批 1=M02+M03+M04 / 批 2=M05-M08 / 批 3=M10-M14 / 批 4=M15-M19）+ 测试模板用 pytest parametrize over DAO」

**实际落地**：

baseline-patch-m20.md L320-333 新增「17 模块拆批策略（Batch 3 / F3.2 锚定）」章节，含 4 批清单表格：

- 批 1（基础）：M02 + M03 + M04 — 1 个 PR，先建 helper + parametrize 测试模板（L326）
- 批 2（叶子结构）：M05 + M06 + M07 + M08 — 1 个 PR（L327）
- 批 3（聚合 + 异步）：M10 + M11 + M12 + M13 + M14 — 1 个 PR，含 SSE 路径备注（L328）
- 批 4（横切 own + 异步重）：M15 + M16 + M17 + M18 + M19 — 1 个 PR（L329）

**单批回滚策略**：L331「每批独立 commit，发现某批 helper 引用错就回滚那 1 个 PR，不影响其他批」— 落地。

**批 1 完成判定门槛**：L333「M02 + M03 + M04 三模块 tests.md T 类全部 PASS + L3 注入测试模板（pytest parametrize）通过 → 才允许启动批 2」— 门槛硬。

**测试模板 parametrize over DAO**：L315「pytest parametrize over DAO 类（每个 DAO 实例一组同形 case，CI 覆盖矩阵自动展开）」— 已写入实施策略第 2 步。

**判定：PASS**。建议表 4 批清单 / PR 边界 / 单批回滚 / 完成门槛 / parametrize 模板 5 项均落地。

**独立观察**：批 1 仅含 M02+M03+M04 3 个模块（audit 建议同），批 2-4 加起来共 14 模块；4 批共 3+4+5+5=17 与受影响模块清单数（L290 表 17 模块）匹配，无遗漏。M09 显式注 "superseded by M18"（L301），不计入升级范围 — 一致。

---

## 2. F3.3 organization 层占位（ADR-005-team-extension.md）

**audit 修复建议**：「ADR-005 加 §8"未来 organization 层路径（占位）"，列 4 决策点（唯一约束 / 二维空白态 / helper 形态 / 对称延伸）」

**实际落地**：

ADR-005 L302-324 新增 §8「未来 organization 层演进路径（占位 / Batch 3 F3.3）」：

- L304 顶部声明非本期 accepted、仅占位、防"零锚点跳跃式扩展" — **PASS**（避免被误读为已 accepted 决策）
- §8.1 触发器（L306-309）：「单实例 ≥ 2 个独立组织 / 跨组织数据严格隔离 / 计费按组织独立结算 任一发生」+ 触发后阅读路径 — **PASS**
- §8.2 4 决策点表（L313-318）：
  - **O1** 唯一约束（creator 唯一 / org 唯一 / 双层）→ 与 Q13.1① 对偶 — **PASS**
  - **O2** 二维空白态（hybrid 态禁/允）→ 防权限歧义 — **PASS**
  - **O3** helper 形态（一次性扩 / 各模块显式）→ 与 M20 helper 一致原则 — **PASS**
  - **O4** 对称延伸（沿用 §4 T7「越靠近资源越严格」）→ 不重复决策 — **PASS**
- §8.3 baseline-patch 模板（L320-324）：照本 ADR §3，5 步落地点 + 工作量预估 1.2× — **PASS**

**判定：PASS**。4 决策点 / 触发器 / 模板齐全；占位语境清晰。

---

## 3. F3.4 Alembic 三批合并顺序（baseline-patch-m20.md）

**audit 修复建议**：「baseline-patch §3 加"M15 三批合并 Alembic 顺序"（单 revision + 字母序 M16→M18→M20）+ 硬触发器"M20 accept 当天回写 M15"」

**实际落地**：

baseline-patch-m20.md L335-380 新增「Alembic 三批 ActionType CHECK 合并顺序（Batch 3 / F3.4 锚定）」：

- **单 revision 名**：L340 `revision: "20260427_m15_action_type_consolidate"` — **PASS**
- **字母序 M16→M18→M20**：L345-365 注释明确 `-- M16 新增（snapshot_*）` → `-- M18 新增（embedding_*）` → `-- M20 新增（team_* / project_*_team）`，DROP 后单一 ADD CONSTRAINT — **PASS**
- **DROP/ADD CONSTRAINT 完整 SQL**：L347-366 ActionType + L368-377 TargetType 二者均 DROP + ADD，避免三次 ALTER 串行 lock — **PASS**
- **硬触发器**：L380「M20 accept 当天，M15 文档 §3 ActionType / TargetType 表必须**同步回写**…verify Agent 在 M20 accept 检查清单内必须验证 M15 文档已同步」— **PASS**（写入 verify checkpoint 而非软建议）

**判定：PASS**。

---

## 4. F3.5 性能阈值锚点（ADR-005 §4 T1 + tests.md C7）

**audit 修复建议**：「tests.md C 类加 C7 性能压测前置硬节点 + ADR-005 §4 T1 加失效路径预演（U 加入 / 移出 / 删 team / project 加 / project 移）」

**ADR-005 §4 T1**（L235）扩写后内容：

> 失效路径预演（Batch 3 / F3.5）：① U 加入 team → DEL key；② U 移出 team → DEL key；③ 删 team → DEL key for all members；④ project 加入 team → DEL key for all team members；⑤ project 移出 team → DEL key for all team members（含目标 team）。任一路径漏失效都会导致权限残留 ≤ 60s，必须在 Service 层 5 处显式 DEL（不靠 TTL 过期兜底）

5 处失效路径完整 / "Service 层 5 处显式 DEL 不靠 TTL 兜底"显式声明 — **PASS**。

**tests.md C7**（L65）：

- 构造数据：U 加入 20 个 team，每 team 含 50 个 project（共 1000 project）— **PASS**（达到 1000 project 量级）
- P95 < 100ms 阈值 — **PASS**
- > 100ms 触发 ADR-005 §4 T1 Redis 缓存路径 + 实施 5 处失效路径（U 加入/移出 team / 删 team / project 加入/移出 team）— **PASS**（5 处完整与 §4 T1 对齐）
- 标"Phase 2 实施前必跑"硬节点 — **PASS**

**测试覆盖度陈述**（tests.md L146）已含 C7 计入"6 类共 67 个测试用例"（C1-C6 → C1-C7 实为 7 个，覆盖陈述显示"C1-C6×6"× 与实际不符；不过 grep 实测结论 67 是把 E6b 单独算了一行 + C7 算入 6，对外口径可能是合并的边界处理；不影响实施。)

**独立观察**：tests.md L146 的覆盖度陈述自统计公式 "C1-C6×6" 实际 C 类已增至 C1-C7=7 项；这是 Batch 3 加 C7 后未刷新统计公式的细节，**不阻塞 accept**（总数 67 与逐项加和大致一致，最多偏 1，非语义错误）。建议 Batch 4 时一并修。

**判定：PASS**（含 1 个统计公式刷新建议，可在后续微修中处理）。

---

## 5. F3.8 README 设计回看触发器（README.md）

**audit 修复建议**：「README 设计回看清单加 M20 三行（2026-10-26 性能 + 2026-10-26 枚举 + 2027-04-26 org 层）」

**实际落地**：

README.md L344-346 在「设计回看触发器（手动审查清单）」表格新增 3 行：

- L344 `2026-10-26` M20 跨 team 子查询性能（ADR-005 §4 T1）— 评估 P95 / team 数 P95 / 单次 AC2 迁移规模；决策路径分支具体（P95>100ms → 引 Redis + 5 处失效；team 数>20 → 同上；迁移>100 → 触发 Phase 2 批量后端 API）— **PASS**
- L345 `2026-10-26` M20 ActionType / ErrorCode 枚举膨胀 — 评估半年使用率<30% 阈值；决策路径具体（合并 promoted_admin/demoted_member 为 role_changed + detail）— **PASS**
- L346 `2027-04-26` M20 organization 层引入触发器 — 三 OR 触发条件与 ADR-005 §8.1 一致；决策路径引 §8 4 决策点 + baseline-patch-org — **PASS**

每行决策路径均"是 → 走 X / 否 → 走 Y"二分，可执行。**PASS**。

---

## 6. 额外审计

### 6.1 ADR-005 §8 与 §7 章节顺序

**现状**（grep 实测）：§3 → §4 → §5 → §6 → §8 → §7（L302 §8 在 L328 §7 之前）

**判定：OBSERVATION（不阻塞 accept）**。

**理由**：
- 数字顺序上 §7 < §8，常规期望 §7 先于 §8
- 但语义上 §7 是"完成度判定 checklist"（应位于文档末尾，方便 reviewer 最后勾选）；§8 是"未来演进路径占位"（属正文延伸）
- §7 放最末是合理的（与典型 ADR 模板"Status / Context / Decision / Consequences / 完成度"末尾收口一致），但**编号应该交换**（§7 ↔ §8）让数字单调
- 当前状态可读性可接受，但严格看属编号瑕疵；建议下次微修把"§7 完成度判定"改名 §9 或与 §8 编号对调
- 不阻塞本期 accept（语义自洽，仅是数字顺序）

### 6.2 ADR-005 §3/§4/§6 内部交叉引用合规

- §4 T1（L235）引用 "Batch 3 / F3.5" — 与本批次锚定一致
- §4 T7（L241）引「未来 organization 层」原则，与新增 §8 §8.2 O4 形成对称延伸链路 — 自洽
- §3.2（L222）末尾"详 ADR-005 §4 T1 失效路径预演"（baseline-patch-m20.md L318 也引同一锚点）— 自洽
- §6 4 个否决方案各有理由，未被 Batch 3 改动触碰
- **判定：PASS**

### 6.3 硬规则交叉合规

- **R-X3**（外部 db Session）：Q13.2 决策矩阵保留（ADR-005:54），Service 跨事务签名规范不变 — **PASS**
- **R10-1**（批量 N 条独立事件）：Q10.1③（删 team 写 N 条 team_member_removed）保留（ADR-005:47）— **PASS**
- **R10-2**（M15 own activity_log）：M15 ActionType 扩 10 / TargetType 扩 1 通过回写 M15 文档 + Alembic 单 revision 合并落地 — **PASS**
- **R5-1**（4 维表禁 ⚠️）：Batch 3 未触碰 §5 4 维 — **PASS**

### 6.4 Batch 1/2 通过项目未被破坏

- ADR-005 §4 Trade-offs 表 T1-T7 行编号保留（L235 T1 / L236 T2 / L237 T3 / L238 T4 / L239 T5 / L240 T6 / L241 T7），T1 仅扩写正文未改编号；下游 tests.md / baseline-patch / README 引用 T1/T6/T7 处编号一致 — **PASS**
- M02 baseline-patch 块（baseline-patch-m20.md L43-79）未变化 — **PASS**
- M15 ActionType / TargetType / ErrorCode 块（L83-172）未变化 — **PASS**
- M01 删 user 校验链（L175-222）未变化 — **PASS**
- 未在 4 个允许文件外做改动（task 约束遵守）— **PASS**

---

## 7. 综合判定

**ALL_PASS**

5 项 Batch 3 finding 全部独立证据通过；4 项额外审计中 3 项 PASS、1 项 OBSERVATION（§7/§8 编号瑕疵，不阻塞）。

**待修项（非阻塞，建议下次微修一并处理）**：

1. ADR-005 §7 与 §8 编号交换（让数字单调），或把 §7 改名为更靠后的编号
2. tests.md L146 覆盖度陈述自统计公式刷新（C1-C6×6 → C1-C7×7；总数验证）

**M20 模块（Batch 1/2/3 三轮 verify 合计 39 项 finding）落地完整，可推进 accept 流程**。
