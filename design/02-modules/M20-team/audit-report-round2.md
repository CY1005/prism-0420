---
round: 2
focus: 边界
auditor: independent reviewer (general-purpose Agent)
created: 2026-04-26
---

# M20 Round 2 — 边界 Audit Report

## 总览

读 7 份核心文件 + PRD §5.5 F20 原文 + M02 §3 schema + M01 §10 R10-2 例外 + M18 backfill 路径定义。

按 12 个 audit 检查项独立判断，产出 **Findings 共 14 条**：
- Blocker：1（B4 transfer 给自己语义未定义即测试用例）
- High：6
- Medium：5
- Low：2

整体结论：M20 主体决策与 PRD F20 字面对齐良好，但**边界场景存在多处未收敛**，主要集中在：
1. AC2 大批量场景未做规模假设与防护
2. archived project 在删 team 流程中行为未定（与 M02 status 字段交互盲点）
3. 软切断 Q3 的"语义违反"风险登记不足
4. Q13.1 ① UniqueConstraint 与 transfer 后语义偏的真实用户路径未演练
5. R10-2 例外与 R10-2 主规则的引用文本互斥（§10.2 与依赖声明冲突）

**Phase 1 收官前必须解决的项**：F2.1（Blocker）+ F2.2 / F2.4 / F2.6 / F2.10（High，影响外部契约或不变量）。

---

## Findings

### F2.1 [Blocker]：B4 测试用例对"transfer 给自己"行为留 Phase 2 决定 —— 设计阶段 contract 未定就发版

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:40` (B4)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:432` (Pydantic schema TeamTransferOwnership)

**问题**：
B4 测试用例描述：
> 422 TEAM_OWNER_REQUIRED (detail.reason="transfer_target_not_member" 或专门处理"target_is_self") —— 或 Service 层接受成 noop（**设计阶段倾向拒绝，归 Phase 2 实施时定**）

设计前置方法论的核心是**接口契约在 Phase 1 收敛**。B4 把行为决策延后到 Phase 2，意味着：
- 不同实现者会做出不同选择（拒 vs noop vs 200 success）
- 自动化测试无法编写（assertion 不确定）
- API 文档无法发布给前端
- ErrorCode TEAM_OWNER_REQUIRED 的 detail.reason 枚举未收敛（设计文档 §13.1 列了 3 个 reason，但 B4 又允许第 4 个 "target_is_self"）

这与 M01-M19 的"决策收敛后才 accepted"标准矛盾。M20 是 Phase 1 收官，留 Phase 2 决定 = 把不确定性带进实施。

**证据**：
> tests.md:40：`422 TEAM_OWNER_REQUIRED (detail.reason="transfer_target_not_member" 或专门处理"target_is_self") —— 或 Service 层接受成 noop（设计阶段倾向拒绝，归 Phase 2 实施时定）`
>
> 00-design.md:648 ErrorCode 表：`TEAM_OWNER_REQUIRED 422 不变量守护 {reason: "last_owner_demote" \| "last_owner_remove" \| "transfer_target_not_member"}`（reason 仅 3 值，未含 "target_is_self"）

**修复建议**：

| 候选 | 行为 | 优 | 缺 |
|------|------|----|-----|
| A | 拒 422，detail.reason="target_is_self"（新增 reason 第 4 值） | 严格语义；前端可定向提示"不能转给自己" | ErrorCode detail 枚举扩到 4 个 |
| B | 拒 422，复用 detail.reason="transfer_target_not_member"（语义松绑：self 不算自己的"target"） | 不扩 reason | 语义偏（self 显然是 member），前端无法区分两种错误 |
| C | Service 层 noop，返回 200（idempotent） | 与 §11.1 "重复加拒 409 / transfer 第二次自然失败"幂等风格一致 | 改 PRD 字面"transfer ownership"语义；审计写 0 条事件还是 1 条？需额外定 |

**推荐 A**：明确加 detail.reason="target_is_self" 第 4 值，§13.1 ErrorCode 表 + ADR-005 §Decision 同步登记。Phase 1 必须收敛。

---

### F2.2 [High]：AC2 一键迁移规模未假设 + §12 决策仅基于"个人 1-N project"小规模隐式假设

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:69` (out-of-scope 第 13 项)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:633` (§12 显式声明)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md` 全文

**问题**：
1. PRD F20 AC2 原文「现有个人项目可一键迁移到团队」，未声明规模上限。M20 §12 决策"前端循环单 API"+ Q6=A 同步，**隐式假设个人 project 数 < 100 量级**，但设计文档没显式登记此假设。
2. tests.md 完全没有大批量场景（B 类边界仅到 N=100，且是 ProjectMember 残留，不是 AC2 迁移）。
3. 真实场景：CY 自己用 0.x 一年沉淀 500-1000 个 project 后迁团队 = 前端循环 1000 次 PATCH，每次都走 L2+L3 三层防御 + activity_log 单条事务 commit。即使每 PATCH 50ms，1000 个 = 50s，期间任一 commit 失败前端怎么处理？部分迁移如何回滚？

§12 显式声明只说「进度条与失败重试由前端维护，后端不做事务原子回滚」—— 这是把分布式事务问题甩给前端，**没登记最大可承受规模**。

**证据**：
> 00-design.md:633:`AC2「一键迁移」由前端循环调 PATCH /api/projects/{pid} N 次，进度条与失败重试由前端维护，后端不做事务原子回滚。`
>
> tests.md 全文：B 类最大 N=100（B10 residual ProjectMember），无 AC2 迁移规模测试

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | 设计文档 §1 In scope 加显式规模假设："AC2 假设个人 project 数 ≤ 100；超过 100 列入 Phase 2 性能监控触发批量 API" + tests.md 加 B12「N=100 顺序迁移正确性 + N=1001 拒 422 PROJECT_BATCH_LIMIT」 | 显式契约；规模限制可执行 | 引入新 ErrorCode 需 §13 同步 |
| B | 升级 §12C Queue 持久化：AC2 走批量 task | 真正解耦前端 | 与 Q6=A 同步决策矛盾，需 reopen Q6 |
| C | 不限制 + 加性能监控告警 | 灵活 | 仍是甩锅前端 |

**推荐 A**：§1 显式登记规模假设 + 加 B12 测试。如果 CY 自己未来超 100 个 project，Phase 2 再补批量 API（§Decision T2 的"未来视痛点"承诺要可执行）。

---

### F2.3 [High]：archived project 与删 team 交互完全未定（与 M02 status 字段隐式冲突）

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:312-315` (§4.1 状态机)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:43-44` (B7/B8)；`/root/workspace/projects/prism-0420/design/02-modules/M02-project/00-design.md:303` (project status 不可逆 archived)

**问题**：
M02 §4 定义 `projects.status: active | archived`，archived 是不可逆终态。M20 §4.1 删 team 前置条件：`COUNT(projects WHERE team_id=X)=0` —— 但**没区分 active vs archived**。

边界场景：
- U1 在 team T 下有 project P1 (active) + project P2 (archived 永久态)
- U1 想删 team T
- M02 「archived 不可逆」 = U1 不能把 P2 unarchive 后改 team_id
- M20 RESTRICT FK = P2 阻止删 team T
- U1 唯一出路：把 P2 直接 PATCH team_id=NULL（如果允许 archived project PATCH team_id）

设计文档**完全没说** archived project 是否允许 PATCH team_id。M02 §1 out of scope / §7 API 都没明确。两个模块的"不变量"在 archived project 这个边界**互锁了**。

更严重的边界：如果某用户的所有 project 都是 archived，他想删 team 只能逐个 PATCH archived project 的 team_id，但 archived project 的写操作权限本身可能受限（M02 业务语义"archived = 不应再改"）。

**证据**：
> M02 00-design.md:317-318：`active --> archived : 管理员归档 / archived --> [*] : 归档为不可逆终态（本期不支持恢复和物理删除）`
>
> M20 00-design.md:314：`active → [*]：team_deleted 必须先满足 COUNT(projects WHERE team_id=X)=0`（不区分 status）

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | archived project 在删 team 前置校验中**豁免**（COUNT 仅算 active 的）+ 删 team 时 archived project 自动 team_id=NULL（系统迁出） | 删 team UX 不被 archived 卡死 | 引入"archived 可被系统改 team_id"的语义例外，需 M02 §4 同步登记；删 team 写额外 N 条 project_left_team 事件 |
| B | archived project 也算占用 team，必须先逐个 PATCH team_id=NULL（明确 PATCH 对 archived 例外允许） | 不变量统一 | UX 重；CY 自己用一年后必踩 |
| C | 禁止把 archived project 加入 team（M02 PATCH /projects/{pid} 校验 team_id 变更必须 status=active） | 从源头消除问题 | 已有数据迁移期不能保证；不解决"加入团队后归档"的情况 |

**推荐 A + C 组合**：源头禁止 archived project 加入 team（C），同时对历史数据兜底，删 team 时 archived 自动迁出（A 的弱化版，避免历史数据卡死）。Phase 1 必须在 §1 / §4 / B 类测试登记。

---

### F2.4 [High]：Q3 软切断决策的"管理意图被违反"风险登记不足 —— 无 audit trail 证据残留 ProjectMember 是被通知的

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:80` (Q3 边界灰区)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:455-457` (Pydantic TeamMemberRemoveResponse)

**问题**：
Q3 软切断决策核心：U 被踢出 team 后，仍以 ProjectMember 身份保留对相关 project 的访问。设计依赖 API 响应附 `residual_project_members` 列表给**前端做提醒**。

**真实风险场景**：
- 安全场景：U 因违规被 admin 踢出 team。如果 admin 用脚本/curl 调 API（不走前端），residual_project_members 列表只在 HTTP response 一次性返回，**没写入 activity_log**。admin 可能错过、忽略，导致 U 仍有访问权但管理者以为切断了。
- audit 反查：3 月后审计"U 还能访问哪些 project"，从 activity_log 查不到当初 admin 被告知有 N 个残留，无法判断是"明知保留"还是"漏处理"。

设计文档第 80 行只说"前端做提醒"，**没说后端是否写 activity_log 标注此次切断的残留状态**。activity_log §10.1 的 `team_member_removed` event detail 只有 `{user_id, reason}`，**没有 residual_project_members 字段**。

**证据**：
> 00-design.md:80:`移 team_member 不级联清 ProjectMember：U 仍以 ProjectMember 身份保留对相关 project 的访问权，前端做提醒（Q3 软切断）`
>
> 00-design.md:591:`team_member_removed | team | actor | team_id | {user_id, reason: "manual" \| "team_deleted"}`（detail 无 residual 字段）

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | activity_log team_member_removed 的 detail 加 `residual_project_count` 与 `residual_project_ids[:10]` 字段（与 TEAM_HAS_PROJECTS detail 风格一致） | audit 可反查；脚本调用者无法跳过通知 | event detail schema 微扩 |
| B | 前端必须二次确认对话框（HTTP 响应 + 前端阻断） | UX 防误操作 | 不解决脚本/API 直调路径 |
| C | 强制级联（违反 Q3 决策） | 简单 | reopen Q3 |

**推荐 A**：detail 加 residual 字段。零成本，audit 可查。Phase 1 必须更新 §10.1 + Pydantic response schema 同步。

---

### F2.5 [High]：§10.2 R10-2 主规则确认与 §0/§14 frontmatter 依赖声明 + M01 R10-2 例外参考存在引用冲突

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:603-605` (§10.2)；`/root/workspace/projects/prism-0420/design/02-modules/M01-user-account/00-design.md:925-929` (R10-2 例外定义)

**问题**：
M01 §10 沉淀了 R10-2 例外条件：「① 该表仅服务单一模块的审计职责 ② 事件高频（100+/用户/天级别）进 M15 会淹没业务时间线 ③ 事件无 project_id 归属（系统级）」。

M20 §10.2 写：`M20 不申请 R10-2 例外（不是横切专用审计表 own，复用 M15 activity_log）`。这看起来对，但**审视 R10-2 例外条件 vs M20 实际**：
- M20 team 事件实际有 project_id 归属（project_joined_team / project_left_team 两条），但 team_* 系列事件**没 project_id**（target_id = team_id，不是 project_id）
- §10.1 表的 team_created / team_renamed / team_deleted / team_member_* 共 8 个事件 = 系统级事件，不归任何 project
- M15 ActivityLogDAO.list_for_project 在加 L3 注入并集后（baseline-patch-m20.md:222），**team_* 8 个事件如何按 project_id 过滤检索？这些事件没 project_id**

冲突：M15 own 路径只支持 list_for_project（按 project_id 过滤），但 team_* 事件无 project_id —— 它们去哪里查？

**证据**：
> 00-design.md:584-595 §10.1 事件表：8/10 个事件 target_type="team"（无 project_id），仅 project_joined_team / project_left_team 是 project_id
>
> baseline-patch-m20.md:222：`M15 | ActivityLogDAO.list_for_project | list 加并集`（仅 list_for_project，没有 list_for_team / list_for_user）

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | M15 baseline-patch 加 `ActivityLogDAO.list_for_team(team_id, user_id)` 方法（走 L1 require_team_access 校验） | 复用 R10-2 主规则；UI 团队详情页活动 feed 可用 | M15 baseline 改动加大 |
| B | team_* 事件分流到 M01-style 独立审计表 `team_audit_log`（走 R10-2 例外条件 ①③） | 边界清晰 | reopen Q10 + 与 baseline-patch ActionType +10 决策矛盾 |
| C | 不查 team_* 事件，只写不读（仅作 forensic audit） | 改动最小 | UX 无团队活动 feed 页 |

**推荐 A**：M15 baseline-patch 增 list_for_team。M20 §9 + baseline-patch §M03-M19 横切表都要补 list_for_team 入口。Phase 1 必须在 baseline-patch-m20.md §M15 加。

---

### F2.6 [High]：Q13.1 ① 「同 creator 唯一」+ Q13 creator_id 永不变 → transfer 后用户感知混乱场景未演练

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:181-182` (UniqueConstraint)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:78` (T4 缓解 UI 显示 creator 名)；`/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:237` (T4 trade-off)

**问题**：
真实用户路径（设计文档**完全没演练**）：
1. U1 创建 team "Eng"（creator_id=U1）
2. U1 transfer ownership 给 U2
3. U1 想再创建一个新 team 也叫 "Eng"（团队解散重建场景）
4. **当前 schema**：UniqueConstraint(creator_id, name) → U1 仍是 "Eng" 的 creator → U1 无法再创建 "Eng" 名的 team

第 3 步在用户视角是"我把 Eng 给了别人，现在自己想重新建一个" —— 完全合理。但当前约束**禁止**。

更糟的对称场景：
5. U2 在 transfer 接手后想创建另一个叫 "Eng" 的 team —— UniqueConstraint(U2, "Eng") 检查 U2 是否已是某 "Eng" 的 creator → U2 不是 creator（U1 才是），U2 创建成功
6. **结果**：系统中存在两个 "Eng"，一个 owned by U2 (creator=U1)，另一个 owned by U2 (creator=U2)。U2 视角看到自己有两个完全同名的 team。

T4 trade-off 用 "UI 显示 creator 名" 缓解，但**这是给观察者看的**，不解决 owner 自己想再创建同名 team 的场景。

**证据**：
> 00-design.md:181-182：`UniqueConstraint("creator_id", "name", name="uq_teams_creator_name"),  # Q13.1 ① 同 creator 下唯一（不同 creator 可同名）`
>
> ADR-005:237：`T4 | Q13.1 ① team name 同 creator 唯一 → transfer 后语义偏 | 接受语义偏，PRD「私域分组」优先 | UI 显示 team name 附 creator 名缓解`

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | UniqueConstraint 改 (current_owner_id, name) —— 但 owner 在 team_members 不在 teams 表 | 语义最准 | 跨表 UniqueConstraint 不可行；改"应用层校验"丢 DB 守护 |
| B | 维持现 schema，§7 文档显式登记此用户路径 + 提示文案"你曾创建过同名团队（已转让），如需再用此名请先归档原团队" | 兼容当前决策 | 需新增 409 detail.reason="creator_legacy_name" 区分 |
| C | UniqueConstraint 取消，靠应用层校验（Prism 实跑 schema 是无 UniqueConstraint 的） | 灵活 | reopen Q13.1 ①；丢 DB 守护 |

**推荐 B**：保留 schema，但在 §7.1 / 13.1 ErrorCode TEAM_NAME_DUPLICATE 的 detail 加 `creator_id` 字段标注是"我自己创的"还是"别人创的"，前端区分文案。Phase 1 必须更新 §13.1 detail schema 并在 tests.md B5/B6 加 B5b「U1 创建 X → transfer 给 U2 → U1 再创建 X 拒 409」。

---

### F2.7 [High]：跨 team 直跳禁止（Q7=A）但 PATCH /projects/{pid} 同时改 team_id 与其他字段时校验顺序未定

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:399` (M02 PATCH 扩展)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:115` (E10)

**问题**：
§7.1 Endpoint 表写：
> PATCH /api/projects/{pid} (M02 own，M20 扩) | 改 team_id（null ↔ team_id，禁 team A → team B） | L2 assert_project_role(owner) + assert_team_role(target, admin) | CROSS_TEAM_MOVE_FORBIDDEN

未明确：
1. 一次 PATCH 同时改 `name="新名"` + `team_id=null`（从 team A 移回个人）+ 其他字段，校验顺序？
2. 一次 PATCH 同时改 `team_id` from team A to team B（跨 team 直跳）+ name —— 如果先校验 name 通过，再校验 team_id 拒 422，整个事务回滚还是部分提交？
3. 如果 team_id 字段在 PATCH body 中**未传**（partial update 语义），是 noop 还是隐式保留 —— Pydantic ProjectMoveTeam schema 写 `team_id: UUID | None`，但 None 在 partial update 含义混淆（是"清空"还是"未传"）。

§5.3 竞态分析有"跨 team 移动 project 与删 team A 并发"，但**没有"PATCH 单次改多字段"的边界**。

**证据**：
> 00-design.md:435-438：
> ```python
> class ProjectMoveTeam(BaseModel):
>     """M02 PATCH /api/projects/{pid} 的 team_id 字段"""
>     team_id: UUID | None  # null = 移回个人；非 null = 加入 team（前提当前 team_id IS NULL）
> ```
> （None 在 PATCH 未传 vs 显式 null 的语义未区分）

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | Pydantic schema 用 `team_id: UUID \| None \| Literal[Unset] = Unset` 显式区分 partial update + 文档 §7.1 加校验顺序「字段级 Pydantic → team_id 跨域 422 → 业务字段 → 单事务 commit」 | 边界清晰 | Pydantic FastAPI Unset 模式需 v2 用法 |
| B | 拆 endpoint：PATCH /projects/{pid}（业务字段）+ POST /projects/{pid}/move-team（专门改 team_id） | 关注点分离；与 transfer-ownership 独立 endpoint 风格一致 | M02 现有 PATCH 端点拆改面大 |
| C | 文档登记"PATCH 同时改 team_id + 其他字段时整事务回滚 / 跨 team 422 优先校验" | 改动最小 | 不解决 partial update 语义 |

**推荐 B**：拆专门的 move-team endpoint，与 §7.1 已有的 POST /transfer-ownership 风格一致。Phase 1 必须在 §7.1 端点表登记。

---

### F2.8 [Medium]：§14 测试矩阵覆盖陈述与决策 Q15「out-of-scope 15 项」之间漏覆盖项

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:124-141` (覆盖度陈述)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:46-73` (out-of-scope 15 项)

**问题**：
out-of-scope 15 项中**有些应该写"防御性测试"**（即测试该行为被拒），但 tests.md 覆盖陈述未声明：
- 第 1 项「跨 team 直接迁移」→ E10 已覆盖 ✓
- 第 2 项「删 team 级联删 project」→ B8/E3 已覆盖 ✓
- 第 4 项「邀请审批流」→ G2 直接 added 隐式覆盖 ✓
- 第 9 项「角色自定义」→ P13 拒 422 覆盖 ✓
- 第 10 项「嵌套 team」→ **无测试**（API 是否拒"team 下嵌套子 team"未测，因 API 本身就没此 endpoint，但应有 schema 级声明）
- 第 11 项「跨实例/多组织」→ 不测（不存在 API）
- 第 13 项「批量后端 API」→ **无测试**确认不存在 POST /api/teams/{tid}/projects:batch
- 第 15 项「P4 token 保护」→ §8.5 写"不引入"，但**无负向测试**确认 DELETE /teams/{tid} 不要求额外 token

**证据**：
> tests.md:130 覆盖陈述：列了 Q0-Q13/Q13.1，**未列 Q15 的 15 项 out-of-scope 各项是否有"反向测试"**

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | 覆盖陈述加 Q14/Q15 行：声明哪些 out-of-scope 走"反向测试"哪些走"无 API 即覆盖" | 完整 | tests.md 增 ~10 行 |
| B | 不改 | — | 边界审计提问点保留 |

**推荐 A**：tests.md 末尾覆盖度陈述加 Q14/Q15 行，明确 15 项中哪些有反向测试、哪些靠"API 不存在"覆盖。

---

### F2.9 [Medium]：transfer owner 拆 2 条事件（Q10.1 ① B）的"同事务"承诺无 SQL 层验证字段

**位置**：`/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:239` (T6 trade-off)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:599` (§10.1 说明)

**问题**：
T6 trade-off：
> 转让 owner 拆 2 条事件（demote + promote） → 审计需关联推断 | 与 Q10 细粒度风格一致 | **同事务 + 同 actor + timestamp 邻近三条件可推断**

但 activity_log schema（M15 own）**无 transaction_id 字段**。所谓"同事务"完全靠"timestamp 邻近 + 同 actor"间接推断：
- 如果两次 transfer 在 1 秒内串行（极端但可能：admin 用脚本批量改），timestamp 邻近**会误关联**：U1 → U2 的 demote 事件 + U3 → U4 的 promote 事件可能 timestamp 差 < 100ms，被误判为同次 transfer。
- 设计文档说"timestamp 邻近三条件可推断"是经验法则，不是硬不变量。

更严重：删 team 写 N+1 条事件（Q10.1 ③ B），同事务原子写。审计反查"哪 N 个 team_member_removed 是同一次删 team 触发的"**完全无法在 SQL 层 group**，只能靠 timestamp 邻近 + actor —— 同样的问题。

**证据**：
> M15 schema (M15 00-design.md grep)：activity_log 无 `transaction_id` / `correlation_id` / `request_id` 字段

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | M15 baseline-patch 加 `correlation_id UUID NULL` 字段（同事务/同请求相同 UUID），M20 transfer + 删 team 流程 Service 层生成并写入 | audit 可硬关联；通用机制（M17 batch_create 也能用） | M15 baseline 改动加 +schema 字段；既有事件需 backfill NULL |
| B | 维持现状，§10.1 文档登记"审计关联依赖 timestamp + actor 邻近，1 秒内同 actor 多次 transfer 不可区分" | 改动小 | 真实 forensic audit 时无解 |
| C | 用 metadata.correlation_id（jsonb 内字段，无需 schema 改） | 改动极小 | 无索引、查询慢 |

**推荐 C**：metadata.detail 加 `correlation_id` 字段（jsonb 内），M20 transfer / 删 team 流程统一生成 UUID4 写入 N+1 条事件 detail。零 schema 改。Phase 1 必须更新 §10.1 detail schema。

---

### F2.10 [High]：M02 baseline-patch supersede 仅命名（space_id → team_id）但实际类型也漂移（INT → UUID）+ 启用 FK = 实质决策变更

**位置**：`/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:14` (Context ADR-001 §预设 3 原文)；`/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:5` (supersedes 字段)

**问题**：
ADR-005 supersedes 字段：
> supersedes：[ADR-001 §预设 3 命名部分（space_id → team_id）]

ADR-001 §预设 3 原文（ADR-005 §Context 引用）：
> 所有 project 相关表预留 `space_id INT NULL` 字段，本期不建 spaces 表，不加 FK

ADR-005 实际改动（baseline-patch-m20.md:55-65）：
1. **命名**：space_id → team_id ✓ supersede 已登记
2. **类型**：INT → UUID（M02 实际用 `Mapped[PyUUID | None]`）✗ supersede **未登记类型变更**
3. **FK**：从"无 FK"到"FK + RESTRICT"✗ supersede 仅说"命名部分"

ADR-005 §Consequences 中性条目说：
> ADR-001 §预设 3 命名部分被 supersede（space_id → team_id），但「预留口」「无 FK 升级路径」精神保留

但实际"无 FK"被打破了 —— 启用 FK 是实质变更，不是"精神保留"。

**证据**：
> ADR-005:14（Context 引用 ADR-001 原文）：`所有 project 相关表预留 space_id INT NULL 字段，本期不建 spaces 表，不加 FK`
>
> ADR-005:5（supersedes 字段）：`[ADR-001 §预设 3 命名部分（space_id → team_id）]` —— 只覆盖命名

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | ADR-005 supersedes 改为 `[ADR-001 §预设 3（命名 space_id → team_id + 类型 INT → UUID + 启用 FK RESTRICT）]` 三项显式登记 | 决策可追溯；半年后 reviewer 知道改了什么 | ADR-005 frontmatter + Context 4 行更新 |
| B | 不改 ADR-005，但 baseline-patch-m20.md §M02 改动末尾加"supersede ADR-001 §预设 3 整段（非仅命名）"标注 | 改动小 | supersede 字段仍误导 |
| C | 维持现状，靠 baseline-patch 文档承担细节 | 改动最小 | ADR 索引层信息缺失，未来工具化追溯断链 |

**推荐 A**：ADR-005 supersedes 字段精确化。这是**ADR-005 自身的元数据准确性问题**，半年后回看 ADR-001 → ADR-005 的链路依赖此字段。Phase 1 必须修正。

---

### F2.11 [Medium]：决策对称性 — Q3 软切断（移成员宽松）vs Q8 强制前置迁出（删 team 严格）的"防误"哲学不一致

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:80` (Q3)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:51` (Q8 out-of-scope)；`/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:37, 42`

**问题**：
两个决策方向不对称：
- **Q3**：移成员 = 软切断（残留 ProjectMember，不级联清，前端提醒但不强制处理）= **宽松**
- **Q8**：删 team = 必须前置迁出 project（422 拒）= **严格**

直觉上应当对称：要么都"宽松：警告 + 允许"，要么都"严格：前置必须处理"。当前的不对称隐含价值判断：
- 删 team 是不可逆 / 重操作 → 严格
- 移成员是可逆（再加回来）/ 轻操作 → 宽松

但**移成员的副作用（U 仍能访问 project）也是不可逆的**：U 可能在残留期间通过 ProjectMember 访问 / 修改 / 导出敏感数据。从安全视角，移成员**比删 team 更需要严格防护**（删 team 至少不会造成数据访问，而残留 ProjectMember 会）。

ADR-005 §Trade-offs 没显式登记此对称性张力。设计文档没解释为什么"删 team 严 / 移成员松" —— 这违反 R 类硬规则的"决策一致性"。

**证据**：
> 00-design.md:80：Q3 软切断
> 00-design.md:51：「删 team 时级联删 project（Q8）—— 必须前置迁出（拒 422）」
> ADR-005 §Trade-offs 6 项无对称性条目

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | ADR-005 §Trade-offs 加 T7 行登记此不对称性 + 业务理由（"移成员是日常操作可逆 / 删 team 是最终操作不可逆"），并强调 F2.4 的 audit_log residual 字段是"宽松路径的 audit 兜底" | 显式承认 + 文档化 | 不解决张力本身 |
| B | Q3 改强制级联（破坏当前决策） | 对称 | reopen Q3 |
| C | Q8 改宽松（删 team 自动迁出 project 到个人） | 对称 | reopen Q8；与 RESTRICT FK 方向矛盾 |

**推荐 A**：登记 trade-off 对称性 + 解释。Phase 1 必须在 ADR-005 §4 加。

---

### F2.12 [Medium]：M15 write 路径豁免「单向豁免」无 read 路径升级显式登记

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:574` (§9.3 豁免清单)；`/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:222` (M15 横切表)

**问题**：
§9.3 豁免清单：
> M15 activity_log 自身写入：write 路径不走 tenant 过滤（M15 own 表，写入由各模块 Service 层主动调用，非用户查询入口）

baseline-patch §M03-M19 表第 14 行：
> M15 | ActivityLogDAO.list_for_project | list 加并集 | write 路径不走（豁免）

read 路径升级了 list_for_project，但 M15 的 read 入口**还有**：
- list_for_user（查"U 自己触发的所有事件"）—— 与 F2.5 的 list_for_team 同样问题
- get_by_id（查单条 audit 记录）—— 是否需要 L3 注入？取决于 detail 是否含 cross-team project_id

baseline-patch / 设计文档**仅升级了 list_for_project**，list_for_user / get_by_id 是否升级未明示。如果 list_for_user 不升级，恶意用户可构造 query 看其他用户的事件流（虽 L1 require_user 过滤了 actor=self，但 target_id=其他 user 的 team 事件呢？）。

**证据**：
> baseline-patch-m20.md:222：仅 list_for_project，未列 list_for_user / get_by_id

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | baseline-patch §M15 改动表加 list_for_user / get_by_id 行，说明是否升级 + 升级方式 | 完整 | 改动小 |
| B | 默认全 read 路径都走 user_accessible 子查询 + 文档登记 | 安全优先 | M15 own 复杂度增加 |
| C | 不改 + 在 §9.3 豁免清单加注"read 路径仅 list_for_project 升级，list_for_user / get_by_id 留 Phase 2 决定" | 改动最小 | 风险后置 |

**推荐 A**：baseline-patch 显式列全 M15 read 入口。Phase 1 必须更新。

---

### F2.13 [Medium]：M02 自身既是 own 又是横切引用方 —— 双重处理的去重未明

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:209` (M02 行)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:539-541` (§9.1 M20 自身 DAO)

**问题**：
baseline-patch §M03-M19 表第 1 行：
> M02 | ProjectDAO.list_for_user / get_by_id | 自身入口（owner_id 校验保留 + 加 accessible 子查询并集）

ProjectDAO 是 M02 own 的核心 DAO。M02 §9 的现有过滤已经走 `owner_id = user_id OR id IN (SELECT project_id FROM project_members WHERE user_id = X)`。M20 baseline-patch 加的 `user_accessible_project_ids_subquery` 内部其实就**包含** project_members 子查询 + team-derived 子查询。

**所以 M02 ProjectDAO.list_for_user 现在会变成**：
- WHERE (owner_id = user OR id IN project_members) AND id IN (project_members ∪ team_members-derived)
- 第二个条件**包含**第一个条件的 project_members 路径 → SQL 冗余

baseline-patch / 设计文档**没说明 M02 怎么去重**：是改 ProjectDAO 完全用新 helper（删原 owner_id / project_members 过滤）？还是叠加（性能损失）？

**证据**：
> baseline-patch-m20.md:209：`owner_id 校验保留 + 加 accessible 子查询并集` —— 暗示叠加，未说去重

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | baseline-patch §M02 行说明：M02 ProjectDAO 改造时**用 helper 替换原过滤**（owner_id 校验保留作 L2 业务校验，L3 SQL 仅 helper 一次） | 性能不退化；语义清晰 | M02 §9 文档需小改 |
| B | 叠加双重过滤 | 安全冗余 | 性能损失（两个 IN 子查询） |
| C | 文档登记此是 trade-off，Phase 2 实施时 benchmark 决定 | 改动小 | 不确定性带进 Phase 2 |

**推荐 A**：baseline-patch 显式说明 M02 改造方式。Phase 1 必须更新。

---

### F2.14 [Low]：M09 superseded by M18 但 baseline-patch §M03-M19 表仍把 M09 列为豁免行 —— 死代码登记

**位置**：`/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:216` (M09 行)；`/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md` §3.2

**问题**：
baseline-patch §M03-M19 表第 8 行：
> M09 | superseded by M18 | — | 仅 M18 SearchDAO 升级

M09 既然 superseded，本不该出现在 baseline-patch 改动表中。把它列出来等于"这一行声明 M09 不改" —— **登记的是不改的事实**，但 baseline-patch 主体目的是"列改的内容"。这种"列不改"的行让阅读者多一道理解：是要我改 M09 吗（看一眼又说不改）。

ADR-005 §3.2 表第 8 行也有同样问题：
> M09 | superseded by M18 — 仅 M18 SearchDAO 升级

不算严重，但是设计文档"信息密度"问题。

**修复建议**：

| 候选 | 优 | 缺 |
|------|----|-----|
| A | baseline-patch / ADR-005 §3.2 表去掉 M09 行，"受影响 17 模块" 改为 "16 模块（M09 已 superseded by M18，不计）" | 信息更准 | 改动小 |
| B | 维持 + 加注释 | 阅读连贯 | 信息冗余 |

**推荐 A**：去掉 M09 行 + 改"受影响模块数"。

---

## 总结表

| Finding | 严重度 | 类型 | Phase 1 必修 |
|---------|--------|------|-------------|
| F2.1 transfer 给自己契约未定 | Blocker | 决策内部一致性 | ✅ |
| F2.2 AC2 规模假设缺失 | High | in/out scope vs PRD | ✅ |
| F2.3 archived project 删 team 交互 | High | 跨决策互动（M02×M20）| ✅ |
| F2.4 软切断无 audit residual | High | 安全 | ✅ |
| F2.5 R10-2 与 list_for_team 缺失 | High | 跨决策（M15×M20）| ✅ |
| F2.6 transfer 后 creator 重复同名 | High | 决策内部一致性 | ✅ |
| F2.7 PATCH 多字段校验顺序 | High | 决策内部一致性 | ✅ |
| F2.8 out-of-scope 反向测试缺失 | Medium | 测试覆盖 | 推荐 |
| F2.9 同事务无 correlation_id | Medium | 决策内部一致性 | 推荐 |
| F2.10 ADR supersede 范围不准 | High | 跨 ADR 决策溯源 | ✅ |
| F2.11 Q3/Q8 防误哲学不对称 | Medium | 决策对称性 | 推荐 |
| F2.12 M15 read 路径升级范围 | Medium | 跨决策（M15×M20）| 推荐 |
| F2.13 M02 ProjectDAO 双重处理 | Medium | 跨决策（M02×M20）| 推荐 |
| F2.14 M09 死代码登记 | Low | 文档信息密度 | 否 |

**Phase 1 收官前必修 8 项**（Blocker 1 + High 6 + 涉及外部契约的）：F2.1 / F2.2 / F2.3 / F2.4 / F2.5 / F2.6 / F2.7 / F2.10。

**风险评估**：当前 M20 不应直接 accepted。建议至少处理 Blocker（F2.1）+ 4 项 High（F2.3 archived 边界 / F2.4 安全 audit / F2.5 R10-2 list_for_team / F2.10 supersede 元数据）后再走 Round 3 演进 audit。其余 High（F2.2 / F2.6 / F2.7）可以接受"显式登记 + 不修代码"的方式收尾。

---

## 不在范围内但建议 Round 3 关注

- L3 SQL 注入子查询性能（17 模块 × 每 query 多 1 次 IN 子查询）—— 是演进/性能项不是边界项
- 未来加 organization 层时此 helper 如何扩展为 user_accessible_project_ids 的多级链路 —— 演进项
- M03-M19 的 17 模块改造拆批次 —— 演进项
