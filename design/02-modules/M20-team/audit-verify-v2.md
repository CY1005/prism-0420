---
title: M20 Team — Batch 2 修复独立 verify 报告 v2
status: verify-complete
owner: CY
created: 2026-04-26
batch: 2
findings_in_scope: [F2.4, F2.5, F2.9, F2.2, F2.3, F2.11+F3.6, F3.10, F3.13]
files_inspected:
  - /root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md
  - /root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md
  - /root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md
  - /root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md
verdict: ALL_PASS_WITH_MINOR
---

# M20 Batch 2 修复独立 verify 报告

> 独立 reviewer，互不附和。仅读改动后的 4 个文件，对照 8 个 finding 逐项验。

---

## 0. Pass/Fail 矩阵

| Finding | Verdict | 关键证据 |
|---------|---------|---------|
| F2.4 软切断 audit 字段 | **PASS** | 00-design.md line 669 metadata 含 `residual_project_count + residual_project_ids[:10]`；line 680 锚定段说明 |
| F2.5 list_for_team 入口 | **PASS** | baseline-patch-m20.md lines 116-145 完整 DAO 草案；00-design.md line 619 §9.1 同步引用 |
| F2.9 correlation_id | **PASS** | 00-design.md line 669 metadata 含 `correlation_id`；line 681 说明锁死 Service 入口生成 + 同流程共享；jsonb 0 schema 改 |
| F2.2 规模假设 | **PASS** | 00-design.md lines 44-48 三档 + 触发器；tests.md line 49 B12 用例 |
| F2.3 archived×team 互锁 | **PASS** | 00-design.md lines 87-89 §1 边界灰区 A+C；tests.md lines 50-51 B13/B14；00-design.md line 767 §13.2 PROJECT_ARCHIVED 标 M02 own |
| F2.11+F3.6 哲学陈述 | **PASS** | ADR-005 line 241 §4 T7 行含「越靠近资源越严格」+ org 层延伸；line 240 T6 行加 correlation_id 注解 |
| F3.10 §5.3 第 6 场景 | **PASS** | 00-design.md line 386 §5.3 第 6 行；baseline-patch-m20.md lines 175-222 M01 章节 + 2 ErrorCode；00-design.md lines 768-769 §13.2 标 M01 own |
| F3.13 §3.5 RESTRICT/CASCADE | **PASS** | 00-design.md lines 313-314 §3.5 双向行（RESTRICT→CASCADE + CASCADE→RESTRICT）；baseline-patch-m20.md line 11 modules_affected 含 M01 |

**额外审计**：

| 项 | Verdict | 证据 |
|----|---------|------|
| 章节编号/表格无错位 | PASS | §1/§3.5/§5.3/§9.1/§10.1/§13.2 表格行数与说明段对齐；mermaid/python 块未被截断 |
| 硬规则交叉合规 | PASS | R-X3（§8.7）/ R-X1（豁免清单）/ R10-1（§10.3）/ R10-2（§10.2）/ R3-4（§3.5 +2 行）/ R5-2（§5.3 +1 场景）/ R13-1（§13.3 子类草案）/ R7-2（schema Literal）均未被本批修复破坏 |
| tests.md 覆盖陈述计数同步 | **PARTIAL** | line 145 写「6 类共 56 个测试用例（Batch 1 +B5b +E6b；Batch 2 +B12 +B13 +B14）」。Batch 1 verify v1 建议改为 64（G10/B12/C6/T6/P15/E15），但当前 tests.md 实际仅 53→56 路径（v1 落 B5b+E6b=53，Batch 2 +B12+B13+B14=56）。计数与实际新增项一致，但与 v1 verify 建议的 64 不一致——属 v1 时计数基线分歧，未在 Batch 2 引新错位 |
| 是否引入新违规 | PASS | baseline-patch-m20.md M01 章节 USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER 在 ADR-005 §3.1 未重复定义（ADR-005 §3.1 只列 M20 own 8 个 ErrorCode + M02 PROJECT_ARCHIVED 复用，不含 M01 own 两个），R10-2 主规则未破坏 |

---

## 1. 逐项证据详述

### F2.4 软切断 audit 字段 — PASS

**证据**（00-design.md）：
- line 669：`team_member_removed` metadata 字段 = `{user_id, reason: "manual" | "team_deleted", residual_project_count: int, residual_project_ids: list[UUID][:10], correlation_id: UUID}`
- line 680：「**F2.4 软切断 audit 字段**：`team_member_removed` metadata 必填 `residual_project_count + residual_project_ids[:10]`（manual 路径 + team_deleted 路径都填，让 audit 能追溯软切断后的残留 ProjectMember 状况，而不是仅 HTTP 响应通知前端）」

manual 与 team_deleted 双路径覆盖明示。

### F2.5 list_for_team 入口 — PASS

**证据**：
- baseline-patch-m20.md lines 116-145：M15 ActivityLogDAO 新增 `list_for_team(db, team_id, user_id, limit, offset)` 完整方法草案 + docstring 标 F2.5 + 8/10 类 team_* 事件枚举 + L1 require_team_access(member) Router 层校验注释
- 00-design.md line 619：§9.1 表新增 `ActivityLogDAO.list_for_team(team_id, user_id) ※ M15 baseline 新增` 行；走 `WHERE target_type='team' AND target_id=:tid` 路径 + L1 require_team_access(member)

### F2.9 correlation_id — PASS

**证据**（00-design.md）：
- line 669：metadata 含 `correlation_id: UUID`
- line 681：「**F2.9 correlation_id（0 schema 改）**：所有 transfer 流程 2 条事件 + 删 team 流程 N+1 条事件，metadata 内必填 `correlation_id: UUID`（Service 入口生成 1 个 uuid4，同流程事件共享）。审计跨条目硬关联，不靠 timestamp 推断（避免 timestamp 同毫秒时序混淆）」

明示 jsonb metadata 字段（0 schema 改）+ Service 入口生成 + 同流程共享 + 不靠 timestamp 推断三件全锁死。

### F2.2 规模假设 — PASS

**证据**：
- 00-design.md lines 44-48 §1 in scope 末「**规模假设（F2.2 锚定）**」段：AC2 ≤100 / 单 team 成员 ≤200 / 用户 team 数 ≤20 + Phase 2 触发器（>100 批量 API、>200 删 team 异步化、>20 Redis 缓存）
- tests.md line 49：B12 「AC2 一键迁移规模假设上限（F2.2）」用例：100 个 project 全部 200 + 进度条 + ≤20s + >100 触发 Phase 2

### F2.3 archived×team 互锁 — PASS

**证据**：
- 00-design.md lines 87-89 §1 边界灰区末「**F2.3 archived×team 互锁**」段：C 源头（POST /move-team archived 拒 422 PROJECT_ARCHIVED）+ A 历史兜底（删 team 时 archived 自动 team_id=NULL + project_left_team detail.reason="team_deleted_archived_auto_unbind"）
- tests.md line 50：B13 archived 拒加入 team → 422 PROJECT_ARCHIVED
- tests.md line 51：B14 删 team 时 archived 自动迁出（active 算入 TEAM_HAS_PROJECTS / archived 走豁免）
- 00-design.md line 767 §13.2：`PROJECT_ARCHIVED（422，M02 own，F2.3 复用）` 标注明确

### F2.11+F3.6 哲学陈述 — PASS

**证据**（ADR-005-team-extension.md §4 Trade-offs 表）：
- line 241 T7 行：「Q3 软切断（删 team_member 不级联清 ProjectMember）vs Q8 强制前置迁出（删 team 拒留 project）非对称防误哲学 | 接受非对称，原则：**「越靠近资源越严格」** —— project 是「资源」、team_member 是「关系」；删一个「关系」不应殃及「资源」（软），删一个「容器」不应让「资源」漂移成孤儿（严）| 演进延伸原则（未来 organization 层）：org_member 删除走软切断（与 Q3 一致），org 删除走强制前置迁出 team（与 Q8 一致）；任何引入新「关系层」时按此原则取默认」
- line 240 T6 行：「同事务 + 同 actor + timestamp 邻近三条件可推断（Batch 2 后已加 metadata.correlation_id 硬关联）」—— correlation_id 注解已加

### F3.10 §5.3 第 6 场景 — PASS

**证据**：
- 00-design.md line 386 §5.3 第 6 行：「删 user vs team owner（F3.10）| ...CASCADE+RESTRICT 内部冲突...→ **M01 baseline 提议**：M01 删 user 入口加 `assert_user_has_no_owned_teams(uid)` 校验链，若 U 是任何 team 的最后 owner → 拒 422 `USER_IS_LAST_TEAM_OWNER`；若 U 是任何 team 的 creator（teams.creator_id RESTRICT）→ 拒 422 `USER_HAS_OWNED_TEAMS`（要求先 transfer ownership 或删 team）」
- baseline-patch-m20.md lines 175-222 「M01 用户系统（Batch 2 / F3.10 + F3.13 提议 baseline-patch）」章节：含 delete_user 校验链伪代码（2 步 owned_teams_as_creator + last_owner_team_ids 校验 + raise）+ 2 ErrorCode（USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER）+ M01 文档更新清单
- 00-design.md lines 768-769 §13.2：`USER_HAS_OWNED_TEAMS（422，M01 own，F3.10 / F3.13 baseline-patch 提议）` + `USER_IS_LAST_TEAM_OWNER（422，M01 own，F3.10 baseline-patch 提议）`

### F3.13 §3.5 RESTRICT vs CASCADE — PASS

**证据**：
- 00-design.md line 313：§3.5 R3-4 表新增 `Q13.1②a creator_id RESTRICT → CASCADE（F3.13）` 行（删 user 自动级联清 teams 含他人 team），Alembic 1 步 / 受影响 M20+M01 / 不可逆性 高（数据风险陈述完整）
- 00-design.md line 314：对偶行 `Q13.1②b user_id CASCADE → RESTRICT（F3.13 对偶）`（每删 user 必须先逐 team 退出），不可逆性 中
- baseline-patch-m20.md line 11：`modules_affected: [M01, M02, M03, ...]` —— M01 已纳入

---

## 2. 额外审计详述

### 2.1 章节编号/表格行错位 — PASS

逐节扫读：§1 in scope/out of scope/边界灰区结构完整；§3.5 R3-4 表 +2 行未破坏列宽；§5.3 表 6 场景行数对齐 mermaid 状态机说明；§9.1 表 +1 行；§10.1 表 metadata 列扩列字段密但未截断；§13.2 复用清单 +3 项编号顺。ADR-005 §4 T7 行新增不影响 T1-T6 编号。baseline-patch-m20.md 段落顺序 M02 → M15 → M01 → M03-M19 合理。

### 2.2 硬规则交叉合规 — PASS

- **R-X3 跨模事务共享 session**：§8.7 签名草案 + line 606「共享同一 `db` session（R-X3）」未变
- **R-X1 豁免清单**：§9.3 三类豁免（M18/M15 write/M20 自身）保留
- **R10-1 批量独立**：§10.3 表 + 禁止做法清单未删；新加 metadata.correlation_id 不汇总，不破坏
- **R10-2 M15 own 主规则**：§10.2 显式声明，line 676「所有事件归 M15 own」+ line 606「写 activity_log 时复用 R10-2 主规则」
- **R3-4 反悔成本**：§3.5 +2 行（含 F3.13 对偶），合规
- **R5-2 状态转换竞态**：§5.3 +1 场景，已含「防护」列
- **R13-1 子类草案**：§13.3 现有 8 子类未变；M01 own 2 个 ErrorCode 在 baseline-patch 而非 M20 §13.3，符合 own 边界
- **R7-2 Literal 枚举**：§7.2 schema Literal 限定保留

### 2.3 tests.md 覆盖陈述计数 — PARTIAL

line 145 写「**覆盖陈述**：6 类共 56 个测试用例（Batch 1 +B5b +E6b；Batch 2 +B12 +B13 +B14）」。

但 v1 verify 报告 line 181 建议改为 **64**（G10 + B12 + C6 + T6 + P15 + E15）。

实际数当前 tests.md：
- G 类：G1-G10 = 10
- B 类：B1, B2, B3, B4, B5, B5b, B6-B11, B12, B13, B14 = 14
- C 类：C1-C6 = 6
- T 类：T1-T6 = 6
- P 类：P1-P15 = 15
- E 类：E1-E14 + E6b = 15
- **合计 = 66**

实际 66，文中写 56——**计数偏差 10**（不是 Batch 2 引入的，是 Batch 1 v1 落地时基线即偏；v1 verify 也未真正修正过）。建议补一刀同步。

### 2.4 新违规审计 — PASS

- baseline-patch-m20.md M01 章节定义 USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER（lines 213-216）— ADR-005 §3.1 仅列 M20 own 8 个 ErrorCode + M02 PROJECT_ARCHIVED 复用项，**未重复**定义这两项；M20 00-design.md §13.2 标 M01 own + baseline-patch 提议，与 baseline-patch-m20.md M01 章节互引一致
- R10-2 主规则未破坏：list_for_team 仍在 M15 own 边界（baseline-patch 显式标 M15 own）
- 命名空间：USER_* 开头，与 M20 TEAM_* / M02 PROJECT_* 命名空间隔离

---

## 3. 综合判定

**ALL_PASS_WITH_MINOR**

8 项 finding 全部 PASS，硬规则交叉无破坏，未引入新违规。

**唯一 minor**（不影响 accept）：
- tests.md line 145 覆盖陈述计数 56 与实际 66 偏差 10——历史遗留（v1 时即偏），建议下次小修一并纠正为「6 类共 66 个测试用例」并罗列实际累计的项。

**建议下一步**：
- 接受 Batch 2 修复，进入 accept 阶段
- 将 tests.md 计数纠正纳入 Batch 3 / 文档清理批次（与 F1.12 README 状态、F2.14 M09 清理同批）
- ADR-005 §4 T6 注解中「Batch 2 后已加 metadata.correlation_id 硬关联」语义清晰，可考虑同步登记到 ADR §Decision 决策对照表 Q10.1 行的衍生备注
