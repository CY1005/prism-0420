---
title: M20 Batch 1 修复独立验证报告 (audit-verify-v1)
status: draft
owner: verify-reviewer (independent)
created: 2026-04-26
module_id: M20
parent_audit: ./audit-report.md
batch: 1 (12 findings)
verdict: NEEDS_FIX
---

# M20 团队 - Batch 1 修复 verify (独立验证)

> 独立 reviewer 逐文件读 + 比对原始 audit finding，不附和。
> 验证范围：00-design.md / tests.md / ADR-005-team-extension.md 三文件 12 项 finding。

---

## 综合判定矩阵

| Finding | 级别 | 验证结论 | 关键证据 |
|---------|------|---------|---------|
| F1.1 | P0 Auth P1+P2 合并入口 | **PASS** | 00-design.md:497-499 §8.5 / 行 855 Q11 表 / ADR-005:48 Q11 行 |
| F1.2 + F3.9 | P0 R-X3 Service 签名 | **PASS** | 00-design.md:382-388 §6 / 545-594 §8.7（章节顺序 §8.5→§8.6→§8.7 正确）|
| F2.1 | P1 transfer 给自己锁定 | **PASS** | tests.md:40 B4 / 113 E6b / 00-design.md:742 detail 含 4 reason / ADR-005:133 同步 |
| F2.6 | P1 creator_id detail | **PASS** | 00-design.md:740 detail 含 creator_id / tests.md:42 B5b 已新增 |
| F2.7 | P1 PATCH 拆 endpoint | **PARTIAL** | 00-design.md:407 endpoint 表已新增 move-team / 409 拆分说明 / 445-447 ProjectMoveTeam target_team_id ✅；**但 tests.md G6/G7（行 25-26）+ E10（行 117）+ 00-design.md §12 行 718 仍用旧 PATCH /api/projects/{pid} { team_id: ... } 语义，未同步** |
| F1.3 | P0 R10-1 合规子节 | **PASS** | 00-design.md:672-690 §10.3 全部 5 维约束 + 禁止做法 3 条 + 实施落点指 §8.7 |
| F2.10 + F3.1 | P1 supersede 范围 | **PASS** | ADR-005:6 frontmatter supersedes "ADR-001 §预设 3 整段" 三件 / 263 Consequences §中性段同步精确化 |
| F1.4 | P0 R3-4 反悔表 4 行 | **PASS** | 00-design.md:294-303 §3.5 表共 7 行（Q0/Q4/Q8/Q13 + 新增 Q1/Q2/Q3/Q5），四列填实 |
| F1.5 | P0 §4.1 真禁止转换 | **PASS** | 00-design.md:318-319：`[*] → active：team_recreated` 拒 404 + 前置校验明确挪 §10/§13 |
| F1.6 | P1 §4.2 加禁止 | **PASS** | 00-design.md:340-341 owner→admin（非 transfer）+ owner→member 直降两条已新增 |
| F1.7 | P1 §12 引 README | **PASS** | 00-design.md:720 引 README §12 4 子模板表 / 729 catalog 4 维「同步」标注 |
| F1.8 | P0 §5.2 决策来源 | **PASS** | 00-design.md:362 「Q13.2=A」+ 决策来源；行 856 决策表 Q13.2 行；ADR-005:54 Q13.2 行 |

**综合判定**：**NEEDS_FIX** —— 11/12 PASS，1 项 PARTIAL（F2.7 端点拆分声明已加但 tests.md + §12 描述未同步）。

---

## 逐项证据明细

### F1.1 Auth P1+P2 合并入口 — PASS

**目标**：把"全 P1 不涉及 P2"改成 P1+P2 合并入口，引 ADR-004 §79；同步 ADR-005 + Q 表。

- 00-design.md §8.5 标题 (line 497)：`### 8.5 Q11=A 决策注解（修订：P1+P2 合并入口，对齐 ADR-004 §79）` ✅
- 行 499：「ADR-004 §79『绝大多数业务端点 P1+P2 合并入口』对齐，不是『全 P1 不涉及 P2』」 ✅
- 00-design.md Q 决策表行 855：`| Q11 | Auth 路径 | A 全 P1+P2（require_user 合并入口）| 2026-04-26 |` ✅
- ADR-005 line 48：`Q11 ... A 全部 P1+P2（require_user 合并入口，对齐 ADR-004 §79）` ✅

四处全部同步。

---

### F1.2 + F3.9 R-X3 跨事务 Service 签名 — PASS

**目标**：§6 Service 行注「接受外部 db: Session（R-X3）」；新增 §8.7 跨事务 Service 签名草案；章节顺序 §8.5→§8.6→§8.7。

- 00-design.md §6 line 384：Service 行注 `**跨事务方法（delete_team / transfer_ownership）接受外部 db: Session（R-X3 共享事务），由调用方持有 commit/rollback 权**` ✅
- §8.7 line 545-594：完整草案（标题 + 业务说明 + delete_team 5 步签名注释 + transfer_ownership 6 步签名注释，含「assert new_owner_id != actor_id（否则 422 reason="target_is_self"）」）✅
- 行 594：`**共享同一 db session**（R-X3）` ✅
- 章节顺序：§8.5 (line 497) → §8.6 (line 507) → §8.7 (line 545)，无错位 ✅

---

### F2.1 transfer 给自己锁定 422 — PASS

**目标**：tests.md B4 锁定 422 + 新增 E6b；00-design TEAM_OWNER_REQUIRED detail.reason 扩 4 个含 target_is_self；ADR-005 同步。

- tests.md B4 line 40：`**422 TEAM_OWNER_REQUIRED detail.reason="target_is_self"**（Phase 1 锁定：拒绝 + 新增第 4 个 reason 枚举值，与 transfer_target_not_member 区分）` ✅（不再"Phase 2 决"）
- tests.md E6b line 113：`E6b | transfer 给自己（B4 错误码归位） | TEAM_OWNER_REQUIRED (reason="target_is_self") | 422` ✅ 新增
- 00-design.md §13.1 line 742：`{reason: "last_owner_demote" | "last_owner_remove" | "transfer_target_not_member" | "target_is_self"}` ✅ 4 枚举
- ADR-005 line 133：`detail: reason ∈ {last_owner_demote, last_owner_remove, transfer_target_not_member, target_is_self}` ✅ 同步

---

### F2.6 creator_id detail + B5b — PASS

- 00-design.md §13.1 TEAM_NAME_DUPLICATE line 740：`| TEAM_NAME_DUPLICATE | 409 | 同 creator 下 team name 重复 | {name, creator_id} |` ✅ 含 creator_id
- tests.md B5b line 42：完整新增 transfer 后 creator 想再用同名拒，含前端文案区分 ✅

---

### F2.7 PATCH 拆 endpoint — PARTIAL

**已落地**：
- 00-design.md §7.1 endpoint 表 line 407：新增独立行 `POST /api/projects/{pid}/move-team` ✅
- 00-design.md line 409：拆分说明 `**端点拆分说明（F2.7 决策）**` 含 3 条理由 ✅
- 00-design.md line 445-447：`class ProjectMoveTeam` 字段已改名 `target_team_id: UUID | None` ✅
- 表中 Path 列原 `PATCH /api/projects/{pid}`（带 team_id 字段）已删除（line 407 替换为 move-team 端点）✅

**未落地（PARTIAL 扣分点）**：
1. **tests.md G6 (line 25)**：`U1 PATCH /api/projects/{pid} { team_id: tid }` —— 仍写 PATCH 旧路径，应改 `POST /api/projects/{pid}/move-team { target_team_id: tid }`
2. **tests.md G7 (line 26)**：同上，应改 `{ target_team_id: null }`
3. **tests.md E10 (line 117)**：`PATCH /projects/{pid} 从 team A 直接到 team B` —— 应改 move-team 端点
4. **00-design.md §12 line 718**：`AC2「一键迁移」由前端循环调 PATCH /api/projects/{pid} N 次` —— 应改 `POST /api/projects/{pid}/move-team`

**说明**：这 4 处旧端点残留与 §7.1 + §7.2 的拆分声明矛盾，会让 Phase 2 实施时混乱（实现到底跟谁？）。建议补一个小修复 patch。

---

### F1.3 R10-1 合规子节 — PASS

- 00-design.md §10.3 line 672-690：完整新增子节 `### 10.3 R10-1 删 team N+1 条事件合规说明（防汇总漂移）` ✅
- 5 字段约束表：写入顺序 / target_type / target_id / actor / metadata.user_id / metadata.reason 全部锁死 ✅
- 禁止做法 3 条（line 685-688）：无 metadata.user_id ❌ / target_id 写 user_id ❌ / 汇总成 1 条 metadata.member_user_ids 数组 ❌ ✅
- line 690：`实施落点：见 §8.7 delete_team 第 3 步签名注释` ✅ 闭环引用

---

### F2.10 + F3.1 supersede 范围 — PASS

- ADR-005 frontmatter line 6：`**supersedes**：[ADR-001 §预设 3 整段] —— 涵盖三件实质变更：① 命名 space_id → team_id；② 类型 INT NULL → UUID NULL（对齐 PRD F20 + Prism 实跑）；③ 启用 FK（原"无 FK 预留口"放弃，正式 ondelete=RESTRICT）。supersede 范围**不仅"命名"**，决策对照表与 Consequences §中性段同步精确化。` ✅
- ADR-005 §Consequences §中性段 line 263：精确改写为「**整段**被 supersede —— 三件实质变更：① 命名... ② 类型... ③ 启用 FK」 ✅ 与 frontmatter 一致

---

### F1.4 R3-4 反悔表 4 行 — PASS

- 00-design.md §3.5 line 294-303：表 7 行：原 4 行 (Q0/Q4/Q8/Q13) + 新增 4 行 (Q1/Q2/Q3/Q5) = 实际 7 行 ≥ audit 要求 ≥4 行 ✅
- 4 列：决策 / 反悔到 / Alembic 步数 / 受影响模块 / 不可逆性 全部填实 ✅
- 新增 Q1 不可逆性「高（已落 ProjectMember 数据语义被吞）」/ Q2「中」/ Q3「中」/ Q5「高」均给具体业务后果

---

### F1.5 §4.1 真禁止转换 — PASS

- 00-design.md §4.1 line 318：`[*] → active：team_recreated —— team 物理删除后**不可复活**（拒 404 TEAM_NOT_FOUND）` ✅ 真状态机风格
- line 318 后半：完整说明语义偏漏洞「即使同 creator 用同 name 再创建，也是新 team（id 不同），已发出的 activity_log target_id 永久指向旧 team_id」✅
- line 319：`active → [*]：team_deleted —— 不是禁止转换，是**前置校验**...前置校验失败逻辑挪 §10（活动日志）/ §13（ErrorCode），非状态机职责。` ✅ 明确挪走

---

### F1.6 §4.2 加禁止 — PASS

- 00-design.md line 340：`owner → admin（非 transfer 场景）` 拒 422 TEAM_OWNER_REQUIRED detail.reason="last_owner_demote"`，注明仅允许在 transfer-ownership 流程内同事务发生 ✅
- 00-design.md line 341：`owner → member（直降）` 任何路径直接降至 member 拒 422 TEAM_PERMISSION_DENIED ✅
- 行 337 注：`R4-2 终态数 1 + 1 = 2，至少 2 条；M20 实际登记 4 条` ✅ 合规

---

### F1.7 §12 引 README + catalog — PASS

- 00-design.md line 720：`参照 [../README.md §12 4 子模板表](../README.md#12-异步形态-4-子模板) 显式排除` + 4 行子模板对照表 (line 722-727) ✅
- line 729：`catalog 4 维异步标注 = **同步**（与 README 模块清单 M20 行一致）` ✅

---

### F1.8 §5.2 决策来源 — PASS

- 00-design.md §5.2 事务边界行 line 362：`Service 层；删 team 5 步事务 + transfer 6 步事务，**Service 方法接受外部 db: Session**（R-X3 共享）...| **Q13.2=A**（决策来源：Q13.2 brainstorming 2026-04-26 子点登记）` ✅
- 00-design.md Q 决策表 line 856：`| Q13.2 | Service 跨事务签名... | A 接受外部 db: Session（R-X3 共享事务）| 2026-04-26 |` ✅
- ADR-005 §Decision Q0-Q15 表 line 54：`| **Q13.2** | Service 跨事务签名... | **A 接受外部 db: Session（R-X3）** | M20 §8.7 给签名草案... |` ✅ 三处同步

---

## 额外审计

### 1. 章节编号一致性 — PASS

§8.5 (line 497) → §8.6 (line 507) → §8.7 (line 545)：顺序连续，无错位。§8.6 「权限并集解析伪代码」逻辑上属于权限解析侧，§8.7 「跨事务 Service 签名」属于事务边界侧，命名分类合理。

### 2. 硬规则交叉合规 — PASS

- **R3-1 SQLAlchemy class**：§3.2 完整 ✅
- **R5-1 多人架构 4 维**：§5.2 表已补 Q13.2 决策来源 ✅
- **R7-2 Pydantic Literal**：§7.2 ProjectMoveTeam target_team_id 改名 ✅
- **R8-1 三层防御**：§8.1-§8.4 完整 ✅
- **R10-2 主规则**：§10.2 显式声明不申请例外 ✅
- **R-X3 跨事务共享 session**：§6 + §8.7 完整闭环 ✅

未引入新违规。

### 3. tests.md 覆盖度计数 — NEEDS_FIX（minor）

- 末尾覆盖陈述 line 142 仍写「6 类共 51 个测试用例」
- 实际计数：G=10 + B=12 (含 B5b/B11) + C=6 + T=6 + P=15 (P1-P15) + E=15 (含 E6b) = **64 个**
- F2.1 加 E6b、F2.6 加 B5b 后总数 51 → 64，未同步。
- 此外注意 P 类「权限并集 P1-P10 矩阵」+「权限拒绝 P11-P15」共 15 个；audit 时若按 51 起算，加 13 个新 case，应为 64。

**建议**：行 142 改为「6 类共 64 个测试用例」。

### 4. ADR-005 §7 完成度判定 — PASS

ADR-005 §7 完成度 checklist 6 行（line 303-310）已包含 `Decision 16 决策点 + Q10.1 / Q13.1 子点全收敛`。Q13.2 是子点已落入 Decision 表 Line 54，不需 §7 单独加行。✅ 不需同步。

---

## 综合判定 — NEEDS_FIX

**11/12 PASS**，**1 项 PARTIAL（F2.7）**，**1 项 minor（tests.md 覆盖陈述计数）**。

### 待修清单（优先级排序）

| 优先级 | 待修项 | 建议改动 |
|--------|--------|---------|
| P0 | tests.md G6 line 25 端点未同步 | `PATCH /api/projects/{pid} { team_id: tid }` → `POST /api/projects/{pid}/move-team { target_team_id: tid }` |
| P0 | tests.md G7 line 26 端点未同步 | `PATCH /api/projects/{pid} { team_id: null }` → `POST /api/projects/{pid}/move-team { target_team_id: null }` |
| P0 | tests.md E10 line 117 端点未同步 | `PATCH /projects/{pid} 从 team A 直接到 team B` → `POST /projects/{pid}/move-team { target_team_id: team_B_id }`（前提当前 team_id=team_A_id） |
| P1 | 00-design.md §12 line 718 端点未同步 | `前端循环调 PATCH /api/projects/{pid} N 次` → `前端循环调 POST /api/projects/{pid}/move-team N 次` |
| P2 | tests.md line 142 计数未同步 | `6 类共 51 个测试用例` → `6 类共 64 个测试用例`（G10 + B12 + C6 + T6 + P15 + E15）|

### 不需修复

- 章节编号 §8.5→§8.6→§8.7 顺序正确
- ADR-005 §7 完成度 checklist 不需为 Q13.2 加行（已在 Decision 表）
- 硬规则交叉无新违规

修完上述 5 项 → ALL_PASS，可进入 Batch 2。
