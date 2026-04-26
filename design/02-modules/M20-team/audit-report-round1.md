---
round: 1
focus: 完整性
auditor: independent reviewer (general-purpose Agent)
created: 2026-04-26
---

# M20 Round 1 — 完整性 Audit Report

## 总览

- finding 总数：12（Blocker 3 / High 5 / Medium 3 / Low 1）
- 主结论：M20 设计骨架完整、Q0-Q15 决策落地清晰、R3-1/R3-2/R5-1/R10-2 等核心硬规则通过；但存在 **Auth 路径 P1+P2 漂移**、**R-X3 跨模块共享 session 缺失**、**R10-1 批量独立事件未在 N+1 流程中显式给到细粒度反例守护** 三处 Blocker，以及若干 N/A 声明缺乏对模板 §12 4 子模板表的显式引用。Phase 2 实施前必须修复 Blocker / High。

---

## Findings

### F1.1 [Blocker]：§8.5 Q11=A 决策与 ADR-004 横切影响声明（"绝大多数是 P1+P2"）矛盾，仅声明 P1

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:489 + ADR-004:253

**问题**：M20 §8.5 写「所有 M20 endpoint 走 ADR-004 P1 用户态（Bearer JWT + require_user 合并入口）」并把 Q11 决策对照表登记为「A 全 P1」（00-design.md:761）。但 ADR-004 §横切影响 L253 明文要求「**所有业务模块** §8 必须引本 ADR，声明"本模块用 P1 / P2"（绝大多数是 P1+P2）」，且 ADR-004 §79 把 `require_user` 定义为「P1+P2 的唯一合并入口」。M20 §6 分层职责表第 1 行写「Server Action: app/actions/teams.ts → 转 require_user」——这条路径本身就是 ADR-004 P2（Next.js Server Action → FastAPI 服务间调用），只声明 P1 与自己 §6 描述的链路冲突。

**证据**：
> 00-design.md:489：「所有 M20 endpoint 走 ADR-004 P1 用户态（Bearer JWT + require_user 合并入口）。」
>
> 00-design.md:374：「Server Action | app/actions/teams.ts | session 校验（Next.js 层）→ 转 require_user」
>
> ADR-004:253：「**所有业务模块** §8 必须引本 ADR，声明"本模块用 P1 / P2"（绝大多数是 P1+P2）」
>
> ADR-004:79：「require_user Depends 是 P1+P2 的唯一合并入口（P1 优先 + P2 带签名兜底）」

**修复建议**：

- **候选 A**：把 Q11 决策从「A 全 P1」改为「A 全 P1+P2（require_user 合并入口）」，§8.5 文案改为「所有 M20 endpoint 走 ADR-004 require_user 合并入口（P1 Bearer JWT 优先 + P2 internal token 兜底）」，并在 brainstorming 复盘把"全 P1"理解为"不涉及 P3/P4"而非"排除 P2"。
  - 优点：与 ADR-004 §79 + §253 一致；与 §6 分层职责表 Server Action 链路对齐；不需要重新决策。
  - 缺点：需回写 ADR-005 §Decision Q11 行 + 决策对照表 + brainstorming Q&A 文案。
- **候选 B**：保留「A 全 P1」字面，但在 §8.5 显式说明「M20 不暴露给 Next.js Server Action 直调（Web 端只走浏览器→FastAPI Bearer 路径）」，并删除 §6 Server Action 行。
  - 优点：字面保留 brainstorming 决策。
  - 缺点：与 Prism shadow 项目实际架构（Next.js + FastAPI 双 runtime）冲突，且其他模块都走 P1+P2，M20 单点豁免增加未来重构风险。

---

### F1.2 [Blocker]：R-X3 共享外部 db session 在 §8.6 / 删 team 5 步流程 / transfer owner 流程中未显式体现 Service 接口签名

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:79-80 + §5.3 + §6 + §8.6

**问题**：M20 删 team 是跨模块多步事务（"前置校验 projects 空 + 查 N 个 team_members + 写 N+1 条 activity_log + 删 N 条 team_members + 删 1 条 teams"，§1:79-80, §10:600-601），明确触发 README R-X3 「级联删除必须共享外部 db session」。R-X3 要求 Service 接口签名形如 `def delete_team(self, db: Session, ...)` 接受外部 db，且不得自开 `with self.db.begin()`。M20 §6 分层职责表 / §8.6 伪代码 / §5.3 竞态分析 / 删 team 5 步声明全部**没有**给出符合 R-X3 规范的 Service 接口签名草案，也没有显式声明"M20 Service 方法接受外部 db: Session"。同时调 M15 写 activity_log 应共享同一 db。

**证据**：
> README §R-X3 L216-232：「下游模块的 delete_by_xxx / batch_create_in_transaction 等被跨模块调用的 Service 方法**必须接受外部 db: Session 参数**，不得自己 self.db.begin() 另开事务」+ Service 接口签名规范代码示例。
>
> 00-design.md:79：「ondelete=RESTRICT，必须 Service 层显式 5 步删除（先迁出 project + 写 N+1 条 activity_log + 单事务删 team_members + teams）」——5 步声明里没有"接受外部 db"
>
> 00-design.md:494-528 §8.6 `resolve_project_role(user_id, project_id, db)` 接受 db 但这是只读且非删除路径。
>
> 删 team 流程未给完整 Service 签名草案（与 M03 batch3 audit 范例对照差距明显）。

**修复建议**：

- **候选 A**：在 §6 分层职责表 Service 行加注「所有跨事务方法接受外部 db: Session 参数（R-X3 合规）」，并在 §8.6 后追加 §8.7 "删 team Service 签名草案"，给出 `def delete_team(self, db: Session, team_id, actor_id) -> None` 含 5 步 + 写 activity_log 同 db；transfer_ownership 同样。
  - 优点：完整对齐 R-X3 + 与 M03/M04 batch3 baseline-patch 一致。
  - 缺点：需补 ~30 行伪代码。
- **候选 B**：仅在 §6 分层职责表加一行声明（不写伪代码），把 R-X3 合规留待 Phase 2。
  - 优点：改动最小。
  - 缺点：违反 README §R-X3 「Service 接口签名规范」要求设计阶段给签名；reviewer 可能在 Phase 2 拍回。

---

### F1.3 [Blocker]：R10-1 批量独立事件在删 team N+1 流程中虽提一笔，但与 R-X3 共享 session 的"先写 N 条 log 再 DELETE N 行 team_members"顺序无声明，存在汇总实现漂移

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:600-601, tests.md:G8

**问题**：§10 末段写「R10-1 批量独立事件：删 team 时 N 个成员各写一条独立事件，不汇总」，G8 测试用例也展开了 5 步。但 §1 边界灰区 L79-80 和 §10 都没显式约束："**先**写 N 条 team_member_removed activity_log + 1 条 team_deleted **再**物理 DELETE N+1 行"还是"DELETE 后再批量写汇总"。R10-1 反例（README L177）正是 M03 删节点写 1 条汇总——M20 删 team 涉及 N 个 team_members 是同形场景。当前设计未明文锁定每条 log 的 target_id 独立 + activity_log 写在 DELETE 之前/之后/同事务的具体顺序，Phase 2 实施时容易漂移成"DELETE 完后汇总写 1 条 deleted-team-with-N-members"。

**证据**：
> 00-design.md:601：「R10-1 批量独立事件：删 team 时 N 个成员各写一条独立事件，不汇总」——只一句，未给伪代码 / 顺序约束 / target_id 字段约束
>
> tests.md:G8：「① 校验 projects 空 ② 查 N 个 team_members ③ 写 N 条 team_member_removed (reason="team_deleted") + 1 条 team_deleted ④ 删 N 条 team_members ⑤ 删 1 条 teams」——顺序③在④之前 OK，但 metadata 中 user_id 字段在 DELETE 后是否仍能 SELECT 出来未明（先写 log 再 DELETE 是合理顺序）。
>
> README §R10-1 L175-178：「每个被影响实体写一条独立 activity_log 事件（target_id 独立），不得汇总为单条"批量操作 N 个实体"事件」+ 反例 M03 删节点 N 条独立 vs 1 条汇总。

**修复建议**：

- **候选 A**：在 §10 表格下补一段"删 team 流程 R10-1 合规说明"：每条 team_member_removed 的 target_id = team_id（按现表第 591 行）+ metadata.user_id 区分被删用户；删 team 写 1 条 team_deleted 单独事件；写顺序为先写 N+1 条 log 再 DELETE，否则 user_id 来源丢失。同步 §6 删 team Service 伪代码体现该顺序。
  - 优点：锁死 Phase 2 实施漂移，target_id 设计与 §10 表格 L591 行的 target_id=team_id 自洽。
  - 缺点：需补 5-8 行说明。
- **候选 B**：把 team_member_removed 的 target_type 从 team 改为 team_member（target_id=user_id 或 team_member.id），让 R10-1 「target_id 独立」字面合规。
  - 优点：每条事件 target_id 唯一，前端按 target_id 过滤更直接。
  - 缺点：需联动改 baseline-patch-m20.md 的 TargetType +1 改 +2，改 ADR-005 决策对照表 Q10.1③，超出本 audit 范围；且现表 L591 行 target_type=team 也是合理选择（团队层面事件）。

---

### F1.4 [High]：§3.5 R3-4 改回成本表覆盖 Q0/Q4/Q8/Q13 但缺 Q1/Q2/Q3 等"嵌套式 + 三角色映射 + 软切断" 反悔成本

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:294-299

**问题**：README §R3-4 要求「核心设计决策」给出量化反悔成本。Q0/Q4/Q8/Q13 已覆盖，但 Q1（嵌套式 vs 覆盖式）/ Q2（三角色映射 vs 双角色 vs 五角色） / Q3（软切断 vs 级联清 ProjectMember） 同等重要——尤其 Q1=B 嵌套式 max 直接决定 §8.6 权限解析伪代码、Q3=A 软切断决定移成员响应 schema。这些决策反悔的 Alembic 步数可能为 0（行为级），但「受影响模块数 / API 行为不可逆性」是真实代价。当前表只列 schema 改动，对"行为级反悔"未量化。

**证据**：
> 00-design.md:294-299 §3.5 表仅 4 行：Q0 / Q4 / Q8 / Q13。
>
> README §R3-4 L135-139：「核心设计决策必须有候选 B 改回成本块——对于有 ⚠️ 核心决策（如 M12 快照存引用 vs 值、M11 持久化 vs 无持久化）的模块，§3 或专属决策块内必须量化给出 Alembic 步数、新增/删除表数、受影响模块数、不可逆性」

**修复建议**：

- **候选 A**：补 Q1 / Q2 / Q3 / Q5 四行入 R3-4 表，反悔代价分别量化「Service 层 resolve_project_role 重写 + 测试套 P1-P10 全推翻 / 17 模块 L3 helper 升级回滚」。
  - 优点：完整对齐 README R3-4 精神，未来 reviewer/CY 反悔时有定量参照。
  - 缺点：表从 4 行扩到 8 行，可读性略降。
- **候选 B**：在 §3.5 顶部加注「本表仅列 schema 级反悔；行为级反悔（Q1/Q2/Q3）参见 ADR-005 §6 Alternatives Considered」。
  - 优点：避免重复登记。
  - 缺点：CY 复盘时需跨文件查 ADR-005，分散；且 ADR-005 §6 是"为什么否决候选"而非"反悔代价"，语义不完全对等。

---

### F1.5 [High]：§4.1 teams 状态机"禁止转换"只列 1 条且语义混入"前置校验"，违反 R4-2 "禁止转换 N+1 条" 的清晰边界

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:313-315

**问题**：R4-2 规定「禁止转换至少列 N 条（N = 终态数 + 1），每条格式必须是『状态A → 状态B：原因 + ErrorCode』」，并明确「禁止把"并发控制 version 冲突"、"删后 404"等非状态转换混入（应放在节 5 竞态分析或节 13 ErrorCode）」。M20 §4.1 唯一一条「active → [*]：team_deleted」是**允许的转换**，而非"禁止转换"——它说"必须先满足 projects 为空"是**前置校验**而非"禁止转换"，并在文末自注「不算状态转换失败，是前置校验失败」自我承认违反 R4-2 边界。teams 终态数 = 0（无终态，删除即销毁）+ 1 = 至少 1 条**禁止转换**，但当前给出的是允许转换的前置条件。

**证据**：
> 00-design.md:313-315：「active → [*]：team_deleted 必须先满足 COUNT(projects WHERE team_id=X)=0，否则 422 TEAM_HAS_PROJECTS（不算状态转换失败，是前置校验失败）」——自承认非状态转换。
>
> README §R4-2 L153-154：「禁止合并写法 / 禁止把"并发控制 version 冲突"、"删后 404"等非状态转换混入（应放在节 5 竞态分析或节 13 ErrorCode）」

**修复建议**：

- **候选 A**：把 §4.1 当前条目改写为真正的禁止转换：「[*] → active：team_recreated（语义不合法 —— team 物理删除后不可恢复，必须新建 + 新 UUID）→ ErrorCode: TEAM_NOT_FOUND（404）」，前置校验"projects 必须为空"挪到 §10 删 team 流程 / §13 ErrorCode TEAM_HAS_PROJECTS 描述里。
  - 优点：严格符合 R4-2 格式 + 精神；与 README L154 反例对齐。
  - 缺点：需把"projects 非空守护"在 §13 / §10 重复一次。
- **候选 B**：在 §4.1 显式声明「teams 实体无显式状态字段，本节按 README §R4-1 走"无状态实体声明"，不强制 R4-2 N+1 条」。
  - 优点：承认本质 —— teams 是无状态实体，硬凑禁止转换是形式主义。
  - 缺点：当前文档已给隐式 active 状态机 + mermaid，再声明无状态自相矛盾；且 R4-1 是"无状态实体也要显式声明"不是"豁免 R4-2"。

---

### F1.6 [High]：§4.2 team_members.role 状态机"禁止转换"列 2 条但合规计算应至少 4 条（终态数 1 + 3 个非终态状态出口审视）

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:330-333

**问题**：state diagram 含 4 个状态（[*] entry / member / admin / owner / [*] exit），其中 [*] 是终态（exit）。按 README §R4-2 「N = 终态数 + 1，至少 N 条」 + 「每个终态单独一条」，team_members 终态数 = 1（[*] exit），最少 2 条已满足；但 R4-2 实战标准（M02/M03 范例）通常每个反向/跨级转换都列：missing 的有：①`owner → [*]: team_member_removed`（已列）但同条还应单列「owner → admin： 非 transfer 流程下不允许」（4.2 mermaid 显示 admin → owner 仅在 transfer 流程，反向也仅在 transfer，但禁止表未独立列出"非 transfer 流程下 owner→admin"）。②跨级 admin → member 走 demote 是允许，不在禁止表 OK；③ `owner → member` 直降未列（应禁止直降，必须经 admin）。

**证据**：
> 00-design.md:319-329 mermaid：admin → owner / owner → admin 均标注「仅在 transfer owner 流程中」，意味着非 transfer 流程下这两个转换是禁止的，但禁止转换表只列了 member → owner 跨级 + owner→[*]。
>
> 00-design.md:331-333 禁止转换 2 条：
> > `owner → [*]：team_member_removed` —— 拒 422 TEAM_OWNER_REQUIRED
> > `member → owner` —— 禁止跨级直升

**修复建议**：

- **候选 A**：补两条禁止转换：①`owner → admin（非 transfer 流程）：拒 422 TEAM_OWNER_REQUIRED detail.reason="last_owner_demote"`；②`owner → member（直降）：拒 422 TEAM_PERMISSION_DENIED detail.required_role="owner via transfer"`。
  - 优点：完全锁死 mermaid 标注的"仅在 transfer"语义 + 明确每个非法路径的 ErrorCode。
  - 缺点：表从 2 行扩到 4 行；与 §13 ErrorCode 表的 TEAM_OWNER_REQUIRED.reason 枚举值需对齐（当前 reason 只列 last_owner_demote / last_owner_remove / transfer_target_not_member 三个）。
- **候选 B**：在 mermaid 加 admin/owner 双向虚线注释「非 transfer 流程下禁止」，并在文末加一段说明而非扩展禁止转换表。
  - 优点：mermaid 自描述完整。
  - 缺点：违反 R4-2「每条单独一行格式：状态A → 状态B：原因 + ErrorCode」要求。

---

### F1.7 [High]：§12 N/A 声明引 Q6=A 决策来源但**未引** README §12 4 子模板表（R5-1 失效信号 + 模板硬规则要求）

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:626-635

**问题**：M20 §12 写「不适用 §12A / §12B / §12C / §12D 任一子模板」，但没引 README §12 4 子模板分支表（README L99-109）作为决策来源依据。pilot M04 范本 / M16 后台模块 / M18 embedding pilot 在 N/A 声明时都需引到 4 子模板表说明"为何不选其中任一"。M20 当前文案仅"列举不适用"，没说明"按 catalog 4 维 emoji 选不到任何 emoji"，与 README L101 「按 catalog 4 维'异步'标注的 emoji 选对应子模板」首句要求脱节。

**证据**：
> 00-design.md:626-635：「§12 N/A（同步模块）...不适用 §12A / §12B / §12C / §12D 任一子模板」
>
> README §12 L101：「按 catalog 4 维"异步"标注的 emoji 选对应子模板」 + 表格"同步 | — | §12 显式 N/A | M04 | 写'本模块不投递 Queue 任务'"

**修复建议**：

- **候选 A**：M20 §12 首段加引：「按 README §12 异步形态分支表（L99-109），M20 catalog 4 维异步标注为"同步"（无 emoji），对应 §12 显式 N/A 行（范本 M04）；下方 4 子模板均不适用」，再加 catalog 引用。
  - 优点：完全合规 R5-1（异步形态维度明确决策来源）+ 与 M04 / M16 / M18 N/A 范式一致。
  - 缺点：需查 catalog 文件确认 M20 标注，多 1 步。
- **候选 B**：保留现状，在 §15 checklist 第 12 行打勾时补"已引 4 子模板表"做形式合规。
  - 优点：改动最小。
  - 缺点：实质未引，checklist 自勾不解决"决策来源缺失"问题。

---

### F1.8 [High]：§5.2 4 维表"事务边界"行决策为 "A（默认）" 而非引用 brainstorming Q 编号，决策来源不可追溯

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:354

**问题**：§5.2 4 维必答表 Tenant / 异步 / 并发 三行 CY 决策列均填 Q4/Q6/Q9 编号引用 brainstorming，唯独"事务边界"行写「A（默认）」无 Q 编号。R5-1 要求「4 维表必须给出 AI 默认值 + 候选 + CY 决策」并防"⚠️ 待裁决"渗漏；当前虽未用 ⚠️，但"A（默认）"语义模糊（默认意味着 CY 没决，AI 自填？还是 CY 同意默认？），不可追溯到 Q0-Q15 任一决策。

**证据**：
> 00-design.md:351-356 §5.2 表：
> > Tenant 隔离 → Q4=A
> > 事务边界 → A（默认）   ← 无 Q 编号
> > 异步形态 → Q6=A
> > 并发控制 → Q9=A

**修复建议**：

- **候选 A**：把"A（默认）"改为「Q13.1③=A（M02 范式照搬，事务边界 Service 层）」并在 brainstorming 复盘把 Q13.1③ 决策含义扩展到事务边界。
  - 优点：决策来源可追溯。
  - 缺点：Q13.1③ 原义是"通用字段照搬"，扩展事务边界含义需 ADR-005 同步注释。
- **候选 B**：新增一个 brainstorming Q（如 Q13.2 事务边界）补登记，CY 决策即 A。
  - 优点：决策点严格 1:1 对应。
  - 缺点：需补 brainstorming 记录 + ADR-005 决策表加行。

---

### F1.9 [Medium]：§9.3 豁免清单缺 R-X3/R-X4 显式声明 + 横切 helper 是否被 ADR-003 覆盖未说明

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:572-576

**问题**：M20 §9.2 引入横切 helper `user_accessible_project_ids_subquery` 供 M03-M19 引用（17 模块 L3 注入升级）。这是典型的"聚合读模块 + 跨模 DAO 调用"，README §R-X4 要求「聚合读模块必须引 ADR-003」声明走规则 1/2/3 哪条；但 M20 §9 / ADR-005 §3.2 都没明确这个 helper 是否走 ADR-003 规则 3（横切表豁免）。同样 R-X3 是否适用此 helper（helper 不开事务，纯子查询，应豁免）也未声明。

**证据**：
> 00-design.md:546-570：helper 实现（横切引用对象）
> 00-design.md:572-576 豁免清单仅 3 条，未涉及 ADR-003 规则引用 / R-X3 / R-X4 声明。
>
> README §R-X4 L233：「聚合读模块必须引 ADR-003」+ 规则 1/2/3 三选一

**修复建议**：

- **候选 A**：§9.2 helper 实现块上方加一段「ADR-003 / R-X3 / R-X4 合规声明：本 helper 是横切表只读子查询，按 ADR-003 规则 3（横切表豁免）+ 不开事务（纯 SELECT），不触发 R-X3 共享 session 要求；M03-M19 引用方按规则 3 豁免独立审计」。
  - 优点：完整覆盖 R-X4 + R-X3 + ADR-003 三规则。
  - 缺点：需 CY 确认 ADR-003 规则 3 是否覆盖"非 own 模块新增 helper 供横切引用"语义。
- **候选 B**：把声明放在 baseline-patch-m20.md 而非 M20 §9。
  - 优点：M20 主设计文档保持精简。
  - 缺点：reviewer 在 M20 §9 找不到 R-X4 引用会拍回。

---

### F1.10 [Medium]：§7 endpoint 表"项目归属变更" `PATCH /api/projects/{pid}` 行第 5 列权限"L2 assert_project_role(owner) + assert_team_role(target, admin)" 与 §1 Q1=B 嵌套 max 语义未自洽

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:399

**问题**：endpoint 表写「project owner + 目标 team admin」是双重要求；但按 §8.6 `resolve_project_role(user_id, project_id)` 逻辑，project_role = max(team_role_mapped, project_member_role)，意味着 user 可能只在 team A 是 admin（→ editor）而不是 ProjectMember 中 owner。当前要求"必须 project_role=owner"等于隐式排除"仅靠 team admin 衍生 editor 的用户" —— 但这是设计意图（project 归属变更是高危操作）还是漏洞？文档无显式说明，且与 Q1=B 嵌套式 max 精神略冲突（既然嵌套 max，应该承认 team-admin → editor 等价于 ProjectMember.editor，而 owner 必须是真 ProjectMember.owner）。这个语义需要明文锁定，否则 Phase 2 实施漂移到"team admin 也能挪 project"。

**证据**：
> 00-design.md:399：「PATCH /api/projects/{pid} (M02 own，M20 扩) | 改 team_id | L2 assert_project_role(owner) + assert_team_role(target, admin) | CROSS_TEAM_MOVE_FORBIDDEN」
>
> 00-design.md:497-528 §8.6 `resolve_project_role` 返回 `max(team_role_mapped, project_member_role)`

**修复建议**：

- **候选 A**：endpoint 表行后加注「assert_project_role(owner) 含义：resolve_project_role 返回 owner（即 user 在 team 是 owner 衍生 owner 或 ProjectMember 直接 owner，二者皆可）」，明确嵌套 max 适用此校验。
  - 优点：与 §8.6 一致，team-owner 用户可挪自己 team 的 project 不卡。
  - 缺点：team-owner 衍生 project owner 可能挪 project 出 team，权限语义微妙（需 PRD 确认）。
- **候选 B**：把"挪 project"权限收紧为「project_members.role=owner（不走 team 衍生）」，明文写入 §8.5。
  - 优点：高危操作严格守护。
  - 缺点：违反 Q1=B 嵌套 max 一致性；用户体验：刚转让 owner 给团队的人无法挪 project（必须先加 ProjectMember owner）。

---

### F1.11 [Medium]：§15 完成度 checklist「关联产出」3 行未完成项与 baseline-patch-m20.md §3 实施顺序冲突

**位置**：/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:730-733 + baseline-patch-m20.md §3:243-251

**问题**：M20 §15 关联产出 3 项未勾：「M02 §3 schema 块更新」/「M15 §3 ActionType / TargetType 枚举表」/「README §10 R10-2 等」。baseline-patch-m20.md §3 实施顺序步骤 4-6 列出"更新 M02 文档 / M15 文档 / README"是 Phase 1 内的步骤，但 §15 checklist 标的"Phase 2 实施前补"语义偏向 Phase 2。同一动作两份文档存在 Phase 1 vs Phase 2 边界争议。

**证据**：
> 00-design.md:731-733：
> > [ ] M02 §3 schema 块更新（space_id → team_id）+ §1 out of scope 表第 5 行 —— Phase 2 实施前补
> > [ ] M15 §3 ActionType / TargetType 枚举表加行 + §13 ErrorCode 全局表加 8 行 —— Phase 2 实施前补
>
> baseline-patch-m20.md §3 L249-251：「4. 更新 M02 文档：§3 schema 字段改名 + §1 out of scope 表 + §15 baseline-patch 标注 / 5. 更新 M15 文档...」 —— 列在 Phase 1 设计阶段步骤而非 Phase 2 实施。

**修复建议**：

- **候选 A**：把 §15 checklist 3 行 「Phase 2 实施前补」 改为 「baseline-patch-m20.md 实施步骤 4-6 完成时同步勾」，与 baseline-patch 文档一致归 Phase 1 收尾动作。
  - 优点：边界清晰，Phase 1 内闭环。
  - 缺点：M20 accept 前需先把 M02 / M15 文档改完。
- **候选 B**：保留"Phase 2 实施前补"，把 baseline-patch-m20.md §3 步骤 4-6 也改为 Phase 2 阶段。
  - 优点：Phase 1 仅产 M20 + ADR-005 + baseline-patch，最小化。
  - 缺点：M02/M15 已 accepted 文档与 M20 设计不一致期延长，Round 2 边界 audit 时容易找不到对照。

---

### F1.12 [Low]：README §模块清单 M20 行状态"待开"与 M20 frontmatter status=draft 名义一致但语义存在轻微落差

**位置**：/root/workspace/projects/prism-0420/design/02-modules/README.md:30 + 00-design.md:3

**问题**：README §模块清单 L30 写「扩展 / M20 团队/空间（多 space 扩展） / 待开 / —」，但 M20 已经有 00-design.md（draft 状态）+ tests.md + ADR-005 + baseline-patch。"待开"暗示尚未开工，与实际 draft 状态不一致；路径列写"—"也与已存在的 `M20-team/` 目录冲突。CY 复盘清单时需 1 秒识别"M20 已 draft"而非"待开"。

**证据**：
> README L30：「| 扩展 | M20 团队/空间（多 space 扩展）| 待开 | — |」
>
> 00-design.md:3：「status: draft」 + 已存在 00-design.md + tests.md + ADR-005

**修复建议**：

- **候选 A**：README L30 改为「扩展 | M20 团队/空间 | **draft（2026-04-26）** | [`M20-team/`](./M20-team/) |」，与 M01/M13/M16/M18 的状态记法一致。
  - 优点：一目了然，与其他模块统一格式。
  - 缺点：M20 audit 三轮通过后还需再改一次为 accepted。
- **候选 B**：保留"待开"等 Round 1+2+3 audit 通过后一次改 accepted。
  - 优点：减少改动。
  - 缺点：违反"frontmatter 与 README 模块清单一致性"的 audit 项 19 要求。

---

## 检查项逐项核对结论

| # | 检查项 | 结论 |
|---|--------|------|
| 1 | §0 frontmatter R0-1 | 12 字段齐全合规（draft / CY / 2026-04-26 / null / null / [] / null / null / M20 / F20 / false / medium）✅ |
| 2 | §3 R3-1 SQLAlchemy class + ER | 双双完整 ✅（L116-150 ER + L154-260 class） |
| 3 | §3 R3-2 三重防护 | team_members.role 三重满足：`Mapped[TeamRole]` + `String(20)` + `CheckConstraint("role IN ('owner','admin','member')")` ✅；teams 表无 status 字段 → R3-2 N/A 合规 |
| 4 | §3 R3-3 tenant 字段 | §15 checklist 显式声明"R3-3 N/A，M20 不属于 project tenant" ✅ |
| 5 | §3 R3-4 反悔成本表 | 4 行覆盖 Q0/Q4/Q8/Q13 ⚠️ → **F1.4 High** |
| 6 | §4 R4-2 禁止转换 | teams 1 条但语义不规范 ⚠️ → **F1.5 High**；team_members 2 条但应至少 4 条 ⚠️ → **F1.6 High** |
| 7 | §5 R5-1 4 维表 | 无 ⚠️ 占位但"事务边界=A（默认）"无 Q 编号 ⚠️ → **F1.8 High** |
| 8 | §5 R5-2 状态转换竞态 | 5 场景齐全 ✅ |
| 9 | §7 R7-1/2/3 | Pydantic 强类型 ✅ + Literal 枚举 ✅ + R7-3 N/A 显式 ✅ |
| 10 | §8 R8-1 三层防御 + 异步声明 | L1+L2+L3 + 同步声明 ✅；但 P1 vs P1+P2 漂移 ⚠️ → **F1.1 Blocker** |
| 11 | §8 R8-2 / R8-3 | Queue / WebSocket N/A 显式 ✅ |
| 12 | §10 R10-1 批量独立 | 提及但未给 N+1 顺序 + target_id 设计约束 ⚠️ → **F1.3 Blocker** |
| 13 | §10 R10-2 主规则 | 走 M15 own + 不申请例外声明合规 ✅（L603-605） |
| 14 | §11 R11-1 + R11-2 | 显式声明 N/A + project_id N/A 合规 ✅ |
| 15 | §13 R13-x AppError 子类 | 8 个 ErrorCode 各对应一个子类 ✅ |
| 16 | §15 checklist 准确性 | 大部分准确，但关联产出 Phase 1/2 边界冲突 ⚠️ → **F1.11 Medium** |
| 17 | 横切 R-X1/2/3/4 | R-X3 在删 team 5 步事务中未声明外部 db ⚠️ → **F1.2 Blocker**；R-X4 helper 未引 ADR-003 ⚠️ → **F1.9 Medium** |
| 18 | §12 异步形态 N/A 声明 | 缺引 README §12 4 子模板表 ⚠️ → **F1.7 High** |
| 19 | frontmatter 与 README 一致性 | 名义一致但语义不齐 ⚠️ → **F1.12 Low** |
| 20 | 决策对照表 Q0-Q15 一致性 | 00-design.md §CY 决策记录表 与 ADR-005 §Decision 决策对照表逐项核对 ✅（Q0-Q15 + Q10.1①②③ + Q13.1①②③ 全部字面一致） |
