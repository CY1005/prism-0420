---
title: M20 Team — Batch 4 Medium/Low 修复独立 verify 报告
status: verified
owner: CY
created: 2026-04-26
verifier: independent general-purpose Agent (v4)
batch: 4 (Medium/Low 接受 + 登记)
findings_in_batch: 11 (F1.9 / F1.10 / F1.11 / F1.12 / F2.8 / F2.12 / F2.13 / F2.14 / F3.7 / F3.11 / F3.12)
verdict: ALL_PASS
m20_overall_accept_recommendation: RECOMMEND_ACCEPT
---

# M20 Batch 4 Verify 报告（独立 reviewer）

> 角色：独立 verify reviewer，独立读 00-design.md / baseline-patch-m20.md / README.md，对照 audit-report.md 11 项 Batch 4 finding 逐条验真。不附和 fix 报告，仅以文件原文为证据。

---

## 0. Pass/Fail 矩阵

| Finding | 严重度 | 主题 | 判定 | 证据锚点 |
|---------|--------|------|------|---------|
| F1.9  | M | helper ADR-003/R-X3 引用 | **PASS** | 00-design.md:861, 875-881 |
| F1.10 | M | endpoint 嵌套 max 自洽 | **PASS** | 00-design.md:862, 419-421 |
| F1.11 | M | M02/M15 同步时机 | **PASS** | 00-design.md:863；baseline-patch-m20.md:394-396 |
| F1.12 | L | README 状态格式 | **PASS** | README.md:30；00-design.md:864 |
| F2.8  | M | out-of-scope 反测覆盖 | **PASS** | 00-design.md:865 |
| F2.12 | M | M15 read 范围 | **PASS** | 00-design.md:866, 619 |
| F2.13 | M | M02 双重过滤去重 | **PASS** | 00-design.md:867 |
| F2.14 | L | M09 死代码 | **PASS** | baseline-patch-m20.md:11, 26, 290 |
| F3.7  | M | 命名空间膨胀（promoted_admin）| **PASS** | 00-design.md:869；README.md:345 |
| F3.11 | L | role endpoint 对称（transfer 独立）| **PASS** | 00-design.md:870 |
| F3.12 | L | AC2 锚点重复 | **PASS** | 00-design.md:871 |

**综合判定**：**ALL_PASS（11/11）**

---

## 1. 逐项证据

### F1.9 — PASS
- 00-design.md:861 §16 登记表 F1.9 行明确写「§9.2 helper 已声明 ADR-003 规则 4（embedding 豁免）+ §8.7 跨事务 Service 已声明 R-X3；R-X4 不适用（M20 无并发跨模 write）」。
- 00-design.md:875-881 §16.1 给出 §9.3 豁免清单 4 项的合规来源标注：M18→ADR-003 规则 4；M15 write→R10-2；M20 自身→team_members 子查询语义；§8.7→R-X3 共享外部 session。
- 独立验证：§9.3（00-design.md:651-654）原文已含 ADR-003 规则 4 引用；§8.7（558）含 R-X3 字样。R-X4 显式声明"不适用"是合理的（M20 无并发跨模写）。

### F1.10 — PASS
- 00-design.md:862 §16 登记说明：F2.7 拆 POST /move-team 后双 role 校验「project owner（自身资源 owner）+ target team admin（目标容器写权限）」与 §8.6 嵌套 max 一致。
- 独立交叉：§7.1 endpoint 表（419 行）已是独立端点 `POST /api/projects/{pid}/move-team`，权限列写「L2 assert_project_role(owner) + assert_team_role(target, admin)」。F2.7 已在前批修完，F1.10 自洽叙述与现状对齐。

### F1.11 — PASS
- 00-design.md:863 §16 登记锁 Phase 1 同步 + 硬触发器「M20 accept 前 M02/M15 文档未同步则拒 accept」。
- baseline-patch-m20.md:394-396 §3 实施顺序步骤 4-5 列「更新 M02 文档」「更新 M15 文档」，处于"M20 accept 后 README 之前"位置。与登记表"Phase 1 收官同步"一致。
- 边界小注：00-design.md §15 checklist:843-844 仍写「Phase 2 实施前补」措辞，与 §16 锁 Phase 1 略有字面张力，但 §16 是后置覆盖且明确 "已在 baseline-patch-m20.md §3 实施顺序 4-5 步登记"，未构成新违规——属可接受的 known-trace（建议 accept 时 §15 同步改字面，但非阻塞）。

### F1.12 — PASS
- README.md:30 M20 行状态原文「**draft（2026-04-26 三轮 audit + Batch 1-4 修复 + verify v1-v3 通过；待 CY 最终 accept）**」+ 链接 `[`M20-team/`](./M20-team/)`。从 audit 之前的"待开"+`—`已迁。
- 注：链路注解写 v1-v3，本 v4 通过后 accept 时再改 v1-v4，但这是 v4 之前的快照，符合 fix 时点状态。

### F2.8 — PASS
- 00-design.md:865 §16 登记说明「8 项已有反测 + 7 项纯文档锁死无端点可测」并具体列举：#1 cross-team 直跳→E10 / #2 删 team 强制前置→B8/E3 / #4 邀请审批→Pydantic 入参拒；7 项纯不实现：#3 邮件、#5 评论、#7 头像、#10 嵌套 team、#11 多 org、#12 模板、#15 P4 token。
- 数量对：8 + 7 = 15，与 §1 out-of-scope 15 项总数一致。

### F2.12 — PASS
- 00-design.md:866 §16 登记：list_for_user 走并集（user_accessible_project_ids_subquery 同形）；get_by_id 走 L1 require_team_access；承诺 Phase 2 跑 T 类用例。
- 交叉 00-design.md:619 §9.1 已有 `ActivityLogDAO.list_for_team(team_id, user_id) ※ M15 baseline 新增`（F2.5 修复）—— read 入口三种形态（team / user / by_id）覆盖完整。

### F2.13 — PASS
- 00-design.md:867 §16 登记明确「叠加（AND）非替换」、「内层子查询保 tenant + 外层 OR owner_id 兜底」、「subquery 已 union ProjectMember + team_members」、owner_id 作 fallback 防 ProjectMember 数据漂移；承诺 Phase 2 T2/T4 验证。

### F2.14 — PASS
- baseline-patch-m20.md:11 frontmatter `modules_affected` 列表已无 M09。
- baseline-patch-m20.md:26 摘要表「受影响横切模块」= **16**（M02-M19 去除 M09 superseded）。
- baseline-patch-m20.md:290 §M03-M19 表注解「16 个，M09 已 superseded by M18 不计入；F2.14 修订」+ 表格中无 M09 行（M08 直接接 M10）。表语法完整未破坏。

### F3.7 — PASS
- 00-design.md:869 §16 登记「promoted_admin 实际承载 owner 是早期信号，已记入 README §设计回看触发器（2026-10-26 ActionType 枚举膨胀回看）」+ 半年触发器：使用率 < 30% → 评估合并。
- README.md:345 已有 2026-10-26 行：「M20 ActionType / ErrorCode 枚举膨胀 ... 评估合并冗余 ActionType（如 promoted_admin / demoted_member 是否合并为 role_changed + detail）」—— 与登记完全闭环。

### F3.11 — PASS
- 00-design.md:870 §16 登记说明「transfer 是单事务 2-step 原子操作（demote + promote），不能拆 PATCH」+ Schema 注释已锁定。属"有意非对称"。
- 交叉 00-design.md:449-454（TeamMemberRoleUpdate Literal["admin","member"] + TeamTransferOwnership 独立 schema）证实意图编码进 schema。

### F3.12 — PASS
- 00-design.md:871 §16 登记「§12 N/A = 形态层（Q6=A 同步）；out-of-scope #13 = 功能层（不做批量后端 API）。锚点不同非冗余」+ 触发器「Phase 2 引批量 API 时两处同步删」。

---

## 2. 额外审计

### 2.1 §16 登记表完整性
- §16 登记表 11 行（F1.9 / F1.10 / F1.11 / F1.12 / F2.8 / F2.12 / F2.13 / F2.14 / F3.7 / F3.11 / F3.12）—— 与 audit-report.md 「组 I 11 项」清单一一对应，**无漏登**。
- 严重度标注一致：F1.12 / F2.14 / F3.11 / F3.12 标 **L**（4 项），其余 7 项标 **M**——与合并报告 §0 矩阵 4L + 7M（Batch 4 范围）一致。
- 每行三列结构（接受方案 / 修复落点 / 监控触发器）齐全；7 项有显式触发器（其中 4 项 "无"/"一次性已修" + 3 项硬触发器或半年触发器）。

### 2.2 新违规检查
- §15 完成度 checklist → §16 Batch 4 → CY 决策记录表 顺序合理；§16 / §16.1 是新增 Batch 4 章节，未挤入 §15 之前导致结构错位。
- 未发现新增 emoji / 真名 / 隐私词；命名规范保持。
- §16.1（00-design.md:875-881）作为 §16 子节给 §9.3 合规来源补注，挂位合理。

### 2.3 baseline-patch-m20.md 删 M09 后表格 + 数字一致性
- frontmatter `modules_affected`（行 11）：18 个模块 [M01, M02, M03, M04, M05, M06, M07, M08, **M10**, M11, M12, M13, M14, M15, M16, M17, M18, M19] —— 已无 M09，M08 直接接 M10。
- 摘要表「受影响横切模块（L3 SQL 注入升级）」（行 26）= **16** ✅（M02-M19 = 18 个 minus M09 minus M01 = 16；与 modules_affected 18 中减 M01 / M09 一致——M01 走 Service 校验链非 L3 query 注入，被分到上一行单算）。
- §M03-M19 表（行 290 起）注解「16 个，M09 已 superseded by M18 不计入」+ 表实体行计数（M02 + M03 + M04 + M05 + M06 + M07 + M08 + M10 + M11 + M12 + M13 + M14 + M15 + M16 + M17 + M18 + M19 = 17 行，包含 M02 自身）。表语法 markdown pipe 完整未破坏。
- 数字 17→16 同步：摘要表（26 行）已写 16 ✅；§M03-M19 表注解（290 行）已写 16 ✅。文中无残留"17 模块"原始字样指代横切清单。
- **小观察**：§M03-M19 表实际行数 17（含 M02 自身横切引用），摘要数字"16"是去掉 M02 后的"M03-M19 严格范围"——这是合理的双视角（M02 既 own 又横切），不是数字漂移。

### 2.4 Batch 1/2/3 已通过项目未被破坏
- §15 完成度判定（00-design.md:818-851）16 节 checklist 全 [x]——结构未动。
- §10.3 R10-1 删 team N+1 条事件合规说明（00-design.md:687-705）字段约束表 + 禁止做法 + 实施落点引用 §8.7 完整保留。
- §8.7 跨事务 Service 签名草案（00-design.md:557-606）含 delete_team / transfer_ownership 双签名 + R-X3 共享 session 显式声明 + Service 内不 commit 注释——完整保留。
- §8.5 Q11=A 注解（509-511）"P1+P2 合并入口对齐 ADR-004 §79"措辞保留——F1.1 Blocker 修复未被 Batch 4 改回。
- §1 边界灰区 archived×team 互锁（87-89 行）A+C 组合修复保留——F2.3 修复未被 Batch 4 改回。
- §10.1 metadata 含 residual_project_count + residual_project_ids[:10]（669 行）+ correlation_id（681 行）保留——F2.4 / F2.9 修复未被 Batch 4 改回。
- §13.1 ErrorCode TEAM_OWNER_REQUIRED detail.reason 含 "target_is_self"（757 行）保留——F2.1 修复未被 Batch 4 改回。
- §3.5 R3-4 表已扩 7 行新决策（含 Q1/Q2/Q3/Q5/Q13.1）—— F1.4 修复保留。
- §4.2 状态机 4 条禁止转换（348-352 行）保留——F1.5/F1.6 修复保留。

未发现 Batch 1-3 任何关键节点被本批修改撞坏。

---

## 3. 综合判定

**ALL_PASS（11/11）**：Batch 4 全部 11 项 Medium/Low 修复真实落地、登记规范、与已有章节交叉一致、未引入新违规、未破坏 Batch 1-3 已通过项目。

**修复风格**：批量"接受 + 登记"策略合理——这 11 项均为低风险设计层澄清，集中在 §16 单一新增章节 + 散点小修（baseline-patch-m20.md 删 M09 / README.md 状态格式），评审成本可控。

无待修项。

---

## 4. M20 整体 accept 推荐

> 39 finding 全部修完（Batch 1 v1 ALL_PASS / Batch 2 v2 ALL_PASS / Batch 3 v3 ALL_PASS / Batch 4 v4 ALL_PASS）。

**推荐**：**RECOMMEND_ACCEPT** — CY 可拍板将 M20 frontmatter `status: draft` → `accepted` + `accepted: 2026-04-26`，并执行：

1. 同步把 README.md M20 行状态末尾"verify v1-v3"改"verify v1-v4 全 PASS"+ 状态最终改 `accepted`（F1.12 落点）；
2. 按 baseline-patch-m20.md §3 实施顺序硬触发器，accept 当天回写 M02 §3/§1/§15 + M15 §3/§13 文档（F1.11 落点）；
3. §15 checklist 末尾 3 行"Phase 2 实施前补"改为"已同步"（与 §16 F1.11 登记一致，消除字面张力）；
4. accept 当天勾掉 §15「三轮 reviewer audit」3 行的 [ ] → [x]。

**风险提示**（accept 后即时关注，非阻塞）：
- §15:843-844 字面与 §16 F1.11 锁 Phase 1 措辞张力（小，建议 accept 同批改）；
- F1.11 硬触发器"M20 accept 前 M02/M15 文档未同步则拒 accept"——执行 accept 时 verify Agent 应在 M20 accept 那一刻检查 M02/M15 文档已落（即 baseline-patch-m20.md §3 步骤 4-5 已执行）；
- 11 项登记的"Phase 2 监控触发器"挂在 README §设计回看触发器（已有 3 行 2026-10-26 + 2027-04-26），accept 不再阻塞。

---

## 5. 验证元数据

- 读取文件：00-design.md (912 行) / baseline-patch-m20.md (428 行) / README.md (M20 相关 6 行) / audit-report.md (210 行) / 三轮 round 报告 grep
- 未修改任何文件（仅读 + 写本报告）
- 验证策略：逐 finding 独立查文件原文 → 不依赖 fix 报告自陈
