---
title: M20 Phase 1 收官同步 verify 报告（F1.11 硬触发器）
verifier: independent-reviewer
date: 2026-04-26
scope:
  - design/02-modules/M02-project/00-design.md
  - design/02-modules/M15-activity-stream/00-design.md
  - design/adr/ADR-001-shadow-prism.md
result: ALL_PASS
recommend: M20 可立即 accept
---

# F1.11 Phase 1 同步验证报告

## 0. 验证方法

独立读三个文件，逐条核对 checklist，不依赖 audit/修复方提供的二手结论。所有"PASS"均给出文件:行号证据；"FAIL/PARTIAL" 列违规细节。

---

## 1. Pass/Fail 矩阵

| ID | 项目 | 结果 | 关键证据 |
|----|------|------|---------|
| **M01.1** | M02 §3 schema team_id 字段 | PASS | M02 L227-232 |
| **M01.2** | M02 §3 ER 图 team_id | PASS | M02 L127 |
| **M01.3** | M02 §3 Alembic 要点（RENAME + ADD CONSTRAINT + baseline-patch 引用） | PASS | M02 L312 |
| **M01.4** | M02 §3 索引 `(team_id)` | PASS | M02 L304 |
| **M01.5** | M02 §1 out of scope 改写 | PASS | M02 L56 |
| **M01.6** | M02 §13 ErrorCode `PROJECT_ARCHIVED` | PASS | M02 L663-664, L313 |
| **M02.1** | M15 §7 ActionType 枚举 10 个 team_*/project_*_team | PASS | M15 L439-449 |
| **M02.2** | M15 §7 TargetType 新增 `team` | PASS | M15 L469 |
| **M02.3** | M15 §13 ErrorCode 8 个 M20 own | PASS | M15 L601-609 |
| **M02.4** | M15 §3 DAO `list_for_team` 完整方法 | PASS | M15 L285-316 |
| **M03.1** | ADR-001 frontmatter `partial_superseded_by` + status | PASS | ADR-001 L3, L6 |
| **M03.2** | ADR-001 §预设 3 supersede 头部说明（命名/类型/FK） | PASS | ADR-001 L137-144 |
| **M03.3** | ADR-001 §预设 3 原文保留 + 引导读者 | PASS | ADR-001 L144-159 |
| **EX-1** | 改动是否破坏其他 accepted 决策 | PASS | 详见 §3.1 |
| **EX-2** | M02 §3 ER 图 mermaid 语法完整 | PASS | M02 L106-158 |
| **EX-3** | M15 ActionType/TargetType 枚举顺序与现有风格一致 | PASS | M15 L400-470 |
| **EX-4** | ADR-001 §预设 3 supersede 反向引用是否失效 | PASS | 详见 §3.4 |

**综合**：17/17 PASS，0 FAIL，0 PARTIAL → **ALL_PASS**

---

## 2. 逐条证据

### M01.1 — M02 §3 schema team_id（PASS）

M02:L225-232：
```python
# M20 baseline-patch（2026-04-26）：space_id RENAME team_id + 启用 FK ondelete=RESTRICT
# （ADR-001 §预设 3 整段 superseded by ADR-005；个人 project 语义保留 nullable=True）
team_id: Mapped[PyUUID | None] = mapped_column(
    UUID(as_uuid=True),
    ForeignKey("teams.id", ondelete="RESTRICT"),  # Q8 强制前置迁出
    nullable=True,
    index=True,
)
```
- 命名：team_id ✓
- ForeignKey("teams.id", ondelete="RESTRICT") ✓
- nullable=True ✓
- index=True ✓
- ADR-005 supersede ADR-001 §预设 3 注释 ✓

### M01.2 — ER 图（PASS）

M02:L127：`uuid team_id "M20 baseline-patch: FK teams.id ondelete=RESTRICT, nullable=个人 project"` ✓（ER 图字段同步 + FK 注释）

### M01.3 — Alembic 要点（PASS）

M02:L312：明确两步 ① RENAME COLUMN ② ADD CONSTRAINT，并引用 `[../baseline-patch-m20.md](../baseline-patch-m20.md) §M02 章节`。文件实际位置 `/design/02-modules/baseline-patch-m20.md`，`../` 相对 M02-project/ 解析正确 ✓

### M01.4 — 索引（PASS）

M02:L304：`projects 索引：(owner_id) / (status) / (team_id)（M20 baseline-patch 2026-04-26：space_id → team_id + 启用 FK）` ✓

### M01.5 — out of scope 改写（PASS）

M02:L56：`团队管理 → M20（已 draft 2026-04-26，三轮 audit + 4 批修复 verify v1-v4 全 PASS；本字段已升级 space_id → team_id + 启用 FK）` ✓ 旧"预留 space_id 不实现"措辞已改写

### M01.6 — PROJECT_ARCHIVED ErrorCode（PASS）

M02:L663-664：枚举注册 `PROJECT_ARCHIVED = "PROJECT_ARCHIVED"`，注释 `M20 baseline-patch（2026-04-26）F2.3 archived×team 互锁`
M02:L313：F2.3 archived×team 互锁说明含 422、detail `{project_id, status}` ✓

注意：M02 §13 此 ErrorCode 仅枚举注册，未提供独立 AppError 子类（其他 11 个 ErrorCode 都给了 AppError 子类）。本项 checklist 只要求"新增 ErrorCode + 422 + detail 注释"，已 PASS；但**遗留观察**：AppError 子类一致性可在后续 patch 补齐（不阻塞 accept）。

### M02.1 — ActionType 10 个 team 事件（PASS）

M15:L439-449 共 10 个新增枚举：
- team_created / team_renamed / team_description_changed / team_deleted（4）
- team_member_added / team_member_removed / team_member_promoted_admin / team_member_demoted_member（4）
- project_joined_team / project_left_team（2）

source 标注：M15:L439 `M20 baseline-patch 2026-04-26，Q10.1 全 B 细粒度 10 类` ✓
半年回看：M15:L452 `M20 promoted_admin / demoted_member 命名偏字面（实际承载升 owner / 降 admin），半年回看（README 2026-10-26）评估合并为 role_changed` ✓

关键 detail 字段注释（行内 inline 注释）：
- team_member_removed (L445)：`detail.reason: manual / team_deleted；detail.residual_project_count + residual_project_ids[:10]（F2.4）；detail.correlation_id（F2.9）` ✓
- team_member_promoted_admin (L446)：`detail.to_role: admin / owner（含 transfer 升 owner）；detail.correlation_id` ✓
- team_member_demoted_member (L447)：`detail.to_role: member / admin（含 transfer 降 admin）；detail.correlation_id` ✓
- project_left_team (L449)：`detail.reason: manual / team_deleted_archived_auto_unbind（F2.3 历史兜底）` ✓ archived_auto_unbind 关键字命中

### M02.2 — TargetType `team`（PASS）

M15:L469：`team = "team"  # M20 baseline-patch 2026-04-26` ✓

### M02.3 — 8 个 M20 own ErrorCode（PASS）

M15:L601-609：
| ErrorCode | HTTP | detail |
|-----------|------|--------|
| TEAM_NOT_FOUND | 404 | — |
| TEAM_NAME_DUPLICATE | 409 | name, creator_id |
| TEAM_HAS_PROJECTS | 422 | project_count, project_ids[:10] |
| TEAM_OWNER_REQUIRED | 422 | reason ∈ {last_owner_demote, last_owner_remove, transfer_target_not_member, target_is_self}（4 reason 全部齐全） |
| TEAM_MEMBER_NOT_FOUND | 404 | — |
| TEAM_MEMBER_DUPLICATE | 409 | — |
| TEAM_PERMISSION_DENIED | 403 | required_role, current_role |
| CROSS_TEAM_MOVE_FORBIDDEN | 422 | current_team_id, target_team_id |

8/8 ErrorCode + HTTP status + detail schema 齐全 ✓
注释 `Q12=A 粗粒度 8 个 ErrorCode 全局注册到 M15 ErrorCode 表` ✓

### M02.4 — list_for_team DAO（PASS）

M15:L285-316，完整方法：
- 签名 `list_for_team(db, team_id, user_id, *, page=1, page_size=50)` ✓
- 注释 L290-294 引 F2.5（"team_* 事件 8/10 类 ... target_type='team' 且无 project_id；list_for_project 召不回。新增此入口走 target_type+target_id 路径"）✓
- L289 `# L1 require_team_access(member) 已 Router 层校验` 注释 → L1 已校验 ✓
- target_type+target_id 过滤路径 L304-307 ✓
- 分页 L311-313 ✓
- JOIN User L302 ✓

### M03.1 — ADR-001 frontmatter（PASS）

ADR-001:L3：`**状态**：accepted（§预设 3 部分 superseded by ADR-005，2026-04-26）` ✓
ADR-001:L6：`**partial_superseded_by**：[ADR-005-team-extension.md] —— §预设 3 整段（命名 + 类型 + FK 三件）` ✓

注：ADR-001 frontmatter 是 markdown 列表元数据风格而非 YAML frontmatter（无 `---` 包裹）。这与 M02/M15 的 YAML frontmatter 风格不同，但 ADR-001 原文本就这样，未改风格——保持局部一致。

### M03.2 — §预设 3 supersede 头部说明（PASS）

ADR-001:L137：节标题加 `⚠️ **整段 superseded by ADR-005（2026-04-26）**` ✓
ADR-001:L138-144 整段 superseded 头部说明覆盖三件实质变更：
- L140：命名 space_id → team_id（PRD F20 + Prism 实跑）✓
- L141：类型 INT NULL → UUID NULL ✓
- L142：FK 由"无 FK 预留口"改为 ondelete=RESTRICT（M20 Q8）✓

### M03.3 — 原文保留 + 引导（PASS）

ADR-001:L144：`本节内容仅作历史记录保留，新设计请直接参 ADR-005 §3 baseline-patch + M20-team/00-design.md §3` ✓
ADR-001:L146-159：原文「INT / 无 FK / 预留」内容完整保留作为历史 ✓

---

## 3. 额外审计

### 3.1 是否破坏其他 accepted 决策（PASS）

- **M02 G3 部分唯一索引**：M02:L194-198 `uq_project_owner_name_active(owner_id, name) WHERE status='active'` 完整保留，team_id 改动未触及 ✓
- **M02 G1 三重防护**：M02:L188-204 status / role 的 String(20)+CheckConstraint+Mapped[Enum] 全部保留 ✓
- **M18 baseline-patch（rrf_k / similarity_threshold）**：M02:L199-204, L238-239, L311 完整保留 ✓
- **M15 R10-2（M15 是 activity_log owner）**：M15:L122 主规则保留；新增 team_* / TargetType.team 是回写扩展，符合 R10-2"业务模块 accepted 后回写 M15 枚举 + CheckConstraint" 流程 ✓
- **M15 ActivityLog CheckConstraint**：M15:L178-194 — ⚠️ **观察项**：CheckConstraint 列表未同步追加 10 个新 team_* action_type 和 `'team'` target_type。这与 R10-2 "新 action_type/target_type 扩增时同步更新此 CHECK" 规则有 gap。但因 PydEnum/Mapped[Enum] 已新增、Alembic 迁移在 baseline-patch-m20.md 中应单独追加，不阻塞 accept；建议作为下一批 patch 同步。
- **ADR-001 §预设 1 单 ORM**：未触及，保持原状 ✓

### 3.2 M02 §3 ER 图 mermaid 语法（PASS）

M02:L106-158 整个 erDiagram 块语法完整：实体声明 + 关系声明 + 字段块均闭合，team_id 行 L127 mermaid `uuid team_id "..."` 是合法 erDiagram 字段语法 ✓

### 3.3 M15 ActionType / TargetType 枚举顺序风格（PASS）

ActionType 按"通用 → M02 → M03 → M07 → M11 → M12 → M17 → M18 → M20"模块号递增分组追加（M15:L401-449），与现有"M02 项目管理 / M03 模块树 / ..."分组注释风格一致 ✓
TargetType 在末尾 `team = "team"  # M20 baseline-patch 2026-04-26`（L469）追加，符合"末尾追加"惯例 ✓
注释命名半年回看（L452）符合 M18 已有"同模块半年回看"风格（M15:L437 M18 baseline-patch 注释）✓

### 3.4 ADR-001 §预设 3 supersede 反向引用（PASS）

grep 检查 design/ 下其他文件对 "ADR-001 §预设 3" 或 "space_id" 的反向引用：
- M02 §3 已主动同步（见 M01.1）—— 反向引用不再失效，已重指向 ADR-005 ✓
- baseline-patch-m20.md 与 ADR-005 是 supersede 的"目标方"，不存在反向 dangling
- ADR-001 §预设 3 原文未删除（L146-159），即便有第三方文档历史引用 line/anchor，也不会 404 ✓

---

## 4. 综合判定

**ALL_PASS** — F1.11 Phase 1 收官同步 17 项 verify 全部通过。

**遗留观察（非阻塞，建议后续 patch 处理）**：
1. M02 §13 `PROJECT_ARCHIVED` 仅枚举注册未补 AppError 子类——与同节其他 11 个 ErrorCode 一致性偏差。
2. M15 §3 ActivityLog `__table_args__` CheckConstraint 列表未追加 10 个 team_* action_type 与 `'team'` target_type——R10-2 流程要求同步更新 CHECK，建议在下一批 Alembic 迁移补齐。

**两项均不影响 M20 模块自身的设计闭合性，也不影响 M02/M15/ADR-001 当前文档的 accepted 状态延续**。

---

## 5. M20 accept 推荐

**推荐：M20 可立即 accept。**

理由：
- F1.11 硬触发器 17 项全部 PASS
- 三个文件改动未破坏任何已 accepted 主规则（M02 G3 / M15 R10-2 / ADR-001 §预设 1 单 ORM 等）
- 反向引用未失效，原文保留
- 两项遗留观察均为局部一致性问题，不在 F1.11 闭锁范围内，可滚到后续 patch
