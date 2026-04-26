---
round: 3
focus: 演进
auditor: independent reviewer (general-purpose Agent)
created: 2026-04-26
---

# M20 Round 3 — 演进 Audit Report

## 总览

- finding 数：13（Blocker 2 / High 5 / Medium 4 / Low 2）
- 整体演进健康度判定：**演进基础健康，但 Phase 2 实施前有 2 个 Blocker 必须拆解**——M02 schema 与 ADR-001 §预设 3 历史记录之间的真相漂移、横切 17 模块 PR 拆批策略缺失。其余 5 个 High 集中在「未来加 organization 层时的演进退路未画」「跨 team 子查询性能阈值未硬挂节点」「M15 baseline 合并执行的 Alembic 顺序未画」三类，是 6 个月后会变成实战债务的典型盲点。

---

## Findings

### F3.1 [Blocker]：M02 schema 真实状态与 ADR-001 §预设 3 文字描述不一致，supersede 表述偏轻

**位置**：
- `/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:6` （supersedes 标"ADR-001 §预设 3 命名部分"）
- `/root/workspace/projects/prism-0420/design/adr/ADR-001-shadow-prism.md:136-150`
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:11` (`adrs_affected: [ADR-001(supersede §预设 3 命名)]`)

**问题**：
ADR-005 把 supersede 范围限定为「§预设 3 **命名部分**」，但实质改了 3 件事，命名只是其中之一：

1. **类型**：ADR-001 §预设 3 写 `space_id INT NULL`（line 138 + 150），M02 实际已是 `Mapped[PyUUID | None]`——这一漂移在 M02 accepted 时（2026-04-21）就已经发生，**不是 M20 引入的**，但 ADR-001 从未被修订。
2. **FK**：ADR-001 §预设 3 明确「不加 FK 约束」「批量为现有记录填 space_id … 加 FK 约束」是未来步骤；M20 现在直接加 `ondelete=RESTRICT` FK——**预设 3 的"无 FK 升级路径"**精神并未保留，被实质替换。
3. **命名**：space_id → team_id。

把这三件事压成"命名部分"被 supersede 会让 6 个月后看 ADR-001 的人困惑：到底 INT/UUID 是哪个 ADR 决定的？FK 启用是哪个决定的？

**证据**：
> ADR-001 line 138-150：「所有 project 相关表预留 `space_id INT NULL` 字段，本期不建 spaces 表，不加 FK 约束 … `space_id: Mapped[Optional[int]]  # 预留，无 FK`」
>
> ADR-005 line 6：「supersedes：[ADR-001 §预设 3 命名部分（space_id → team_id）]」
>
> ADR-005 line 261：「ADR-001 §预设 3 命名部分被 supersede（space_id → team_id），但「预留口」「无 FK 升级路径」精神保留」——但 M20 实际加了 FK，"无 FK 升级路径"精神并未保留

**修复建议**：
- A（推荐）：ADR-005 supersedes 字段改为「ADR-001 §预设 3 整段」+ Consequences §中性段把"精神保留"改为「ADR-001 §预设 3 整段被 supersede。INT→UUID 由 M02 accepted 时已实质执行（历史 drift，由 M02 baseline-patch 追认），FK 启用由 M20 引入 teams 表后启用」。优点：3-5 月后能从 ADR-001 链路追到完整真相。
- B：保留"命名部分被 supersede"措辞，但在 ADR-001 §预设 3 末尾加「**[2026-04-26 修订]** 本节 INT 类型已被 M02 accept (2026-04-21) 实质修订为 UUID；本节 FK 设计已被 ADR-005 (2026-04-26) supersede。完整迁移路径见 ADR-005 §3」反向交叉引用。优点：不动 ADR-005，缺点：ADR-001 不再是"预设"而是"已迁出的过渡决策"，文字不准。
- C：保持现状。**否决**——3-5 月后回看 ADR-001 §预设 3 仍写 INT 无 FK，会误导新人。

---

### F3.2 [Blocker]：横切 17 模块 L3 注入升级未给拆批策略，CY 决策项最后一行 unchecked 留给未来

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:228-238` （§实施策略 5 步）
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:269` （CY 决策项最后一行 unchecked）

**问题**：
17 模块 DAO 升级是 Phase 2 工作量最集中的一块。当前 baseline-patch §3 实施策略仅 5 步：写 helper / 写测试模板 / 逐模块改 / 回归测试 / 性能监控。**关键缺失**：
1. 拆批策略「每批 4-5 个模块」当前以 unchecked 留给"Phase 2 实施前再定"——但 Phase 2 启动条件就是 M20 通过 audit，把决策延迟到启动后等于现在不敢拍板。
2. 回归测试模板的具体形态（pytest fixture / 共享 conftest / 共享 test class / parametrize over 17 个 DAO）没说清。这直接影响测试模板能否被复用——否则每个模块写一份，17 模块 × 6 类（T1-T6）= 102 测试 case 工作量爆炸。
3. 17 模块改造期间是否阻塞其他 Phase 2 工作（如 M20 自身实现）没说。

对比 baseline-patch-m18 的实施顺序段（line 372-376）给了「audit 阻塞项 / Phase 2 集中迁移」分级——M20 baseline 实施段没有同等分级。

**证据**：
> baseline-patch-m20.md line 269：`- [ ] **待 CY 确认**：M03-M19 逐模块 DAO 升级 PR 是否拆批（建议每批 4-5 个模块）—— 留 Phase 2 实施前再定`
>
> baseline-patch-m20.md line 228-233：「实施策略（Phase 2 落地时）：1. 先实现 helper 2. 写测试模板 3. 逐模块改造 DAO 4. 回归测试 5. 性能监控」
>
> baseline-patch-m18.md line 372-376（对比）：实施顺序按「audit 阻塞项→Phase 2 集中迁移」分级，每步标注阻塞/非阻塞

**修复建议**：
- A（推荐）：baseline-patch §3 加一段「Phase 2 实施拆批默认策略」明确决策：批 1 = M02+M03+M04（核心 tenant 链路验证）/ 批 2 = M05+M06+M07+M08（同 tenant 风险接近）/ 批 3 = M10+M11+M12+M13+M14（业务边）/ 批 4 = M15+M16+M17+M18+M19（横切+派生）；每批一个 PR + 一次回归。CY 决策项第 5 条标 [x]。**理由**：拆批不是 Phase 2 才决定的事——决定是否拆批本身就是设计阶段的可逆性二分（一次性 PR 不可逆）。
- B：保持 unchecked 但显式声明「Phase 2 启动前 CY 必须拍板」+ 给一个判定锚点（例：M20 accept 后 1 周内）。优点：不强迫现在决定。缺点：违反 reversibility_binary 原则——这是可逆决策，可以现在给时间盒决定。
- C：加测试模板形态选型块：选 pytest parametrize over `[(M03, NodeDAO, "list_for_project"), ...]` 共享 conftest，理由是 17 模块 DAO 接口高度同构——而 M02 owner_id 校验保留属于例外，单独写一份。优点：把测试爆炸问题在设计阶段就压下去。

---

### F3.3 [High]：未来加 organization 层迁移路径完全未画，二维空白态冲突未预演

**位置**：
- `/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:262` （Consequences §中性「再走一次类似的 baseline-patch（team_id → org_id 链路扩展）」）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:64` （out-of-scope 第 11 条）

**问题**：
ADR-005 用 1 句话带过 organization 层，但实际加 org 层会触发**至少 4 个具体决策**当前没有锚点：

1. **唯一约束迁移**：`UniqueConstraint("creator_id", "name")` 在 org 引入后是否要改 `(org_id, creator_id, name)`？还是 `(org_id, name)`（org 内全局唯一）？这是产品决策——团队名在 org 内应不应该被另一 user 重复用？
2. **二维 nullable 链空白态**：`projects.team_id IS NULL` 当前 = 个人 project；引入 `projects.org_id` 后，`(team_id IS NULL, org_id IS NULL)` = 个人 / `(team_id IS NULL, org_id NOT NULL)` = org 内未归属任何 team / `(team_id NOT NULL, org_id IS NULL)` = 历史数据/数据漂移 / `(team_id NOT NULL, org_id NOT NULL)` = 完整路径。第三态合法吗？还是要 `org_id = team.org_id` invariant？这个决策不画现在做，将来 org 层会卡这里。
3. **L3 helper 的扩展形态**：`user_accessible_project_ids_subquery` 现在是 2 路并集，加 org 后会不会变 3 路（org_members）？还是保持 team-as-bridge（org → team → project）？
4. **对称决策延伸**：见 F3.7。

§中性段「再走一次类似的 baseline-patch」是一句承诺，没有等价于 ADR-001 §预设 3 那种"未来步骤"清单。

**证据**：
> ADR-005 line 262：「中性：M20 后续若引入 organization 层，再走一次类似的 baseline-patch（team_id → org_id 链路扩展）」
>
> M20 设计 line 64：「11. 跨实例 / 多组织（organization 概念）—— Q0 不引入」
>
> 对比 ADR-001 §预设 3 原文 line 140-143：「未来加空间层迁移步骤：1. 建 spaces 表 2. 批量为现有记录填 space_id 3. Alembic 迁移加 FK 约束」——给了 3 步路径，虽然现在看不够细但至少有锚点

**修复建议**：
- A（推荐）：ADR-005 加 §8「未来 organization 层引入路径（占位）」，列 4 个决策点（唯一约束 / 二维空白态 / helper 形态 / 对称决策延伸），每点给当前预判但不锁死。优点：6 个月后回看至少有思考起点。
- B：在 README §设计回看触发器加「未来加 org 层时启动 ADR-006，回看 ADR-005 §3 + §6」，不写具体路径。优点：不假装未来想清楚了，留白诚实。
- C：什么都不加。**否决**——M20 是 PRD 里"万一有人想看"的预留，加 org 层概率不低（如果 prism-0420 真上线给团队用），现在零锚点等于把演进债务全留给未来。

---

### F3.4 [High]：M15 baseline-patch 与 M16/M18 已积压枚举的 Alembic 合并顺序未画

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:128` （`Alembic 迁移（2 步，与 M16 / M18 已积压枚举合并执行）`）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:288` （§3.4 同样表述）
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m18.md:285` (`与 M16 已积压的 ActionType +3 + TargetType +1 … 合并执行`)

**问题**：
"合并执行"是个温柔的词，背后藏 3 个未决问题：

1. **顺序**：M16 +3 / M18 +2 / M20 +10（ActionType），TargetType M16 +1 / M20 +1。Alembic revision 链是有序的——这三个 baseline 哪个先 head？是按 accept 时间（M16 先 / M18 中 / M20 后）排，还是按"一份合并 migration"压成一个 revision？
2. **冲突点**：M16/M18 的 baseline-patch 文档当前都没 accept 后回写 M15 文档（M20 §15 第 4 行 unchecked、M18 同样未做），如果 M20 先回写 M15 文档，M16/M18 的 baseline 是否要被反向回填到 M15？
3. **CHECK constraint 升级模式**：PostgreSQL 改 CHECK constraint 不是 add value，必须 DROP CONSTRAINT + ADD CONSTRAINT，三批一起做和分批做的回滚语义不同（一起做 = 单 revision 整体回滚 / 分批 = 每批独立 revision）。

§15 完成度 checklist 第 4 行（"M15 §3 ActionType / TargetType 枚举表加行 + §13 ErrorCode 全局表加 8 行 —— Phase 2 实施前补"）unchecked，意味着 Phase 2 启动前 M15 文档不更新会**直接导致漂移**（M16/M18/M20 三家各自记自己加的枚举，M15 文档永远是空的）。

**证据**：
> baseline-patch-m20 line 128：「Alembic 迁移（2 步，与 M16 / M18 已积压枚举合并执行）」
>
> baseline-patch-m20 line 259：「f. ActionType / TargetType / ErrorCode CHECK constraint 迁移（与 M16 / M18 已积压枚举合并）」
>
> M20 design line 731-732：`[ ] M02 §3 schema 块更新（space_id → team_id）+ §1 out of scope 表第 5 行 —— Phase 2 实施前补 / [ ] M15 §3 ActionType / TargetType 枚举表加行 + §13 ErrorCode 全局表加 8 行 —— Phase 2 实施前补`

**修复建议**：
- A（推荐）：baseline-patch §3 实施顺序段加「§3.X M15 三批合并 Alembic 顺序」明确：单 revision，按字母排序（M16 → M18 → M20）合并，DROP + ADD CHECK 一次性升级；revision 文件名 `phase2_m15_actiontype_consolidated_<date>.py`。同时给三批模块 accept 状态触发器：「最晚 accept 的模块 +1 天后启动合并 Alembic」。
- B：每批独立 revision，M16 baseline、M18 baseline、M20 baseline 各自的 Alembic 单独跑。优点：回滚粒度细。缺点：CHECK constraint 升级 3 次 PG drop+add 抖动 3 次。
- C：M20 design §15 + baseline §4 加硬触发器「M20 accept 当天必须同步回写 M15 文档」，不留 Phase 2 才补。

---

### F3.5 [High]：跨 team 子查询性能阈值「P95 > 100ms」未挂硬节点+缓存失效路径未设计

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:233` （`若 P95 > 100ms，引入 Redis 缓存 user:{uid}:accessible_projects TTL 60s`）
- `/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:234` （T1 trade-off「上线后视监控引入 Redis 缓存」）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:146` （`实际 SQL 注入子查询性能测试 … 待 Phase 2 实施时补充`）

**问题**：
3 处提到性能监控，但合起来还是没回答 3 个演进问题：

1. **预压测时机缺失**：tests.md 把性能测试推到 "Phase 2 实施时补充"。但 1000 user × 100 team × 1000 project 是真实压测场景吗？还是 100/10/100 ？baseline-patch §3.2 没给假设量级，"上线后监控" = 没有上线前 baseline。**演进风险**：上线发现 P95=300ms 时再加 Redis 已经晚了。
2. **阈值挂在哪个文档**：「P95 > 100ms 引入缓存」只在 baseline-patch §3.2 line 233 提了一次，没进 ADR-005 §4 trade-off T1，没进 README 设计回看清单。半年后 CY 想找这个阈值得回 grep。
3. **缓存失效路径完全未设计**：U 加入 team / 移出 team / team 删除 / project 加入 team / project 移出 team —— 这 5 个事件都会让 `user:{uid}:accessible_projects` 缓存失效。当前文档零行说明。Redis 缓存上线时这是 P0 实现项，现在不画 = 上线时发现"缓存命中但权限错"。

`union subquery` 在 1000 team / 用户在 100 team 场景下确实可能 O(N²)——每次请求一次 SQL 算 union——CY 文档假设这是「安全优先可接受」的，但没量化"可接受到什么程度"。

**证据**：
> baseline-patch-m20 line 233：「若 P95 > 100ms，引入 Redis 缓存 `user:{uid}:accessible_projects` TTL 60s（不在本期）」
>
> ADR-005 line 234（T1）：「接受性能开销，安全优先 / 上线后视监控引入 Redis 缓存 user_accessible_project_ids」
>
> tests.md line 146：「实际 SQL 注入子查询性能测试（user_accessible_project_ids_subquery 在 N=1000 project 时的耗时）—— 待 Phase 2 实施时补充」

**修复建议**：
- A（推荐）：tests.md §C 加「C7 跨 team 子查询性能压测（Phase 2 实施前置硬节点）」：在 helper 实现完成 + 17 模块未升级前跑 baseline，再升级 5 模块跑 delta，再升级 17 模块跑 final；同时把 "P95 > 100ms 引入 Redis" 阈值挂到 ADR-005 §4 T1 + README 半年回看清单（2026-10-26）。
- B：在 ADR-005 §4 T1 加 「失效路径预演」子段，列 5 个事件 → invalidate `user:{uid}:accessible_projects`；不实现，但写明 Phase 2 实施 Redis 时这 5 个钩子是 P0。优点：Redis 引入时不漏失效。
- C：baseline-patch §3.2 加假设量级声明：「假设场景 = 1000 user / 100 team / 1000 project / 用户平均 5 team / 每 team 平均 50 project」。优点：未来性能压测有 baseline 对照。

---

### F3.6 [High]：决策对称性的演进盲点（Q3 软切断 vs Q8 强制前置）在加 org 层时如何延续未画

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:80` （Q3 软切断）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:51` （Q8 强制前置迁出）
- `/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:38` （Q3）+ `:42` （Q8）

**问题**：
Q3（移 user 出 team → 不级联清 ProjectMember，软切断）和 Q8（删 team → projects 必须先全部迁出，强制前置）是非对称决策——前者宽松、后者严格。CY 显然有自己的偏好，但没在 ADR 里说明对称性。

**演进风险**：加 org 层时这两个决策必须延续：

1. 删 organization 时 teams 处置：强制前置迁出（org 内所有 team 必须先解绑或销毁）vs 级联软切断（teams 保留但 org_id 设 null）vs CASCADE（一起删）？现在没有锚点，未来 org 层启动时这又是一轮 brainstorming。
2. 移 user 出 organization 时其 team_member 行处置：软切断（保留 team_member 但 org-level 失访）vs 级联清（自动从所有 team 移出 + 软切断 ProjectMember）？
3. 这两个决策当前是否有 invariant：「越靠近底层资源（project）的删除越严格，越靠近上层组织（user / org）的删除越宽松」？如果是，文档应该写出来作为演进时的指南；如果不是，每次都要重新 case-by-case。

**证据**：
> 00-design.md line 80：「移 team_member 不级联清 ProjectMember：U 仍以 ProjectMember 身份保留对相关 project 的访问权，前端做提醒（Q3 软切断）」
>
> 00-design.md line 51：「删 team 时级联删 project（Q8）—— 必须前置迁出（拒 422）」
>
> ADR-005 没有把 Q3 / Q8 的非对称性显式登记为决策风格

**修复建议**：
- A（推荐）：ADR-005 §4 trade-off 加 T7「Q3/Q8 非对称：成员管理动作宽松（软切断）vs 资源管理动作严格（前置迁出）」+ 一句话决策风格陈述「越靠近资源越严格」+ "未来扩展时延伸该原则"。优点：给未来 org 层一个判断起点。
- B：00-design.md §1 in/out scope 加「决策风格统一：成员动作软切断 / 资源动作强一致」声明。优点：模块文档自包含。
- C：什么不加。**否决**——CY 半年后未必记得这个非对称是有意还是巧合。

---

### F3.7 [Medium]：Q10 细粒度 10 + Q12 粗粒度 8 的非对称结构在加 org 层时枚举膨胀

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:88-104` （ActionType 扩 10）
- `/root/workspace/projects/prism-0420/design/02-modules/baseline-patch-m20.md:115-126` （ErrorCode 扩 8）
- `/root/workspace/projects/prism-0420/design/adr/ADR-005-team-extension.md:236` （T3 trade-off）

**问题**：
M15 ActionType 已经是扁平枚举（M16 +3 / M18 +2 / M20 +10 = +15）。加 org 层时按 Q10.1 同等粒度可能要再扩 10：org_created / org_renamed / org_member_added / org_member_removed / org_member_promoted / ... ；ErrorCode 同理 +8（ORG_NOT_FOUND / ORG_HAS_TEAMS / ORG_OWNER_REQUIRED / ...）。

**3 个演进问题**：
1. M15 ActionType CHECK constraint 单值列表会越来越长，PG CHECK 可读性下降。
2. 没有"事件命名空间"概念（`team.member.added` vs `org.member.added`），靠字符串前缀人为约束。
3. M20 内部已有命名漂移：`team_member_promoted_admin` 但 detail.to_role 含 "owner"（line 592 注释）——名字说 admin 实际可能 owner，这是非对称结构压力的早期信号。

T3 trade-off 只说"接受非对称"+"文档显式标注"，没说未来怎么演进。

**证据**：
> 00-design.md line 592：「team_member_promoted_admin … ※ to_role 含 "admin" 或 "owner"（含 transfer 中升 owner）」——命名说 admin，实际可承载 owner，是命名空间缺失的早期症状
>
> ADR-005 line 236（T3）：「Q10 细粒度事件 + Q12 粗粒度错误 → 非对称结构 / 接受非对称（事件审计需细 / 错误客户端处理不需细）/ 文档显式标注此 trade-off」

**修复建议**：
- A：ADR-005 §4 T3 加「演进退路」子句：「枚举数 > 50 时评估改为 (action_namespace, action_verb) 二元组」+ README 半年回看挂 2026-10-26 触发器。
- B：M20 ActionType 命名改为 dot notation（`team.member.promoted` 而非 `team_member_promoted_admin`），现在就分离命名空间。优点：未来加 org 不破坏命名一致性。缺点：M16 / M18 已积压枚举不一致，要么不动，要么一并改。
- C（推荐，Low cost）：M20 ActionType 现有命名保留，但把 `team_member_promoted_admin` / `team_member_demoted_member` 这种"包含 owner/admin 模糊"的事件改成更准确的 `team_member_role_changed`（detail.from_role + to_role 携带），减 2 个 ActionType（10 → 8）。理由：transfer owner 已经是 2 条（demoted + promoted），到 promoted_admin 还附带 owner case，命名实际承担多语义——拆得不彻底。

---

### F3.8 [Medium]：§15 完成度 checklist 缺 M20 的"半年回看"触发器，README 设计回看清单未挂

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:706-739` （§15）
- `/root/workspace/projects/prism-0420/design/02-modules/README.md:339-344` （设计回看触发器表）

**问题**：
README 末尾「设计回看触发器」表只有 §12D 半年回看（2026-10-25）+ M18 schema + M18 search_evaluation_log 三行。M20 完全没挂。当前文档的"演进"决策点（T1 性能阈值 / T3 枚举非对称 / Q3+Q8 对称性 / org 层扩展路径）都没有未来回看的硬触发。

CLAUDE.md 也强调「三轮递进：完整性 → 边界 → 演进」+ feedback_kb_design_principles 的"过期触发"原则——M20 通过 audit 后，半年回看触发是基础设施。

**证据**：
> README line 339-344 表：3 行 trigger 全部和 M18 相关，M20 行不存在
>
> M20 design §15 line 736-739 三轮 audit checklist 末尾：`Round 3：演进（横切 L3 注入升级路径 + 未来加 organization 层 + 性能监控 + Phase 2 实施顺序）`——只列了演进 audit 范围，没列未来回看触发
>
> 对比 README line 40：「§12D 半年回看触发器（2026-10-25）：M18 accept 后半年评估 … 记录方式：见本 README 末尾「设计回看触发器」清单（手动审查，不挂自动 cron）」——给了对照样板

**修复建议**：
- A（推荐）：README 设计回看清单加 3 行 M20 触发器（建议日期 2026-10-26 + 2027-04-26）：
  - 2026-10-26：M20 helper 性能 P95 是否 > 100ms（决策路径：超阈值引入 Redis + 5 失效钩子）
  - 2026-10-26：M15 ActionType 总枚举数是否 > 50（决策路径：超阈值评估改命名空间）
  - 2027-04-26：是否需要引入 organization 层（PRD F20 演进）+ Q3/Q8 对称性原则是否仍适用
- B：仅加 1 行性能阈值触发器（最关键的）。优点：不堆叠半年回看清单。
- C：M20 §15 加内联回看锚点（不进 README 表）。**不推荐**——README 表是统一入口，分散到模块内 CY 半年后扫不到。

---

### F3.9 [Medium]：R-X3 共享外部 db session 在删 team 5 步流程未显式声明

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:78-79` （删 team 时 team_members 处置）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/tests.md:27` （G8 删 team 5 步）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:218-219`（R-X3 在 README 描述）

**问题**：
README §横切 R-X3 (line 216-232) 明确要求"级联删除必须共享外部 db session"，且明确适用「所有可能被跨模块调用的 Service 方法」。M20 删 team 5 步：

1. 校验 projects 空（不调下游）
2. 查 N 个 team_members（不调下游）
3. 写 N+1 条 activity_log（**调 M15 Service**）
4. 删 N 条 team_members（不调下游）
5. 删 1 条 teams（不调下游）

第 3 步明显跨模块。R-X3 要求 `M15.write_activity_log(db: Session, ...)` 必须接受外部 session——但 M20 §8.6 / §3.4 / tests.md G8 都没显式声明「这 5 步在同一个 `with self.db.begin():` 内 + M15 调用接受外部 db」。

更隐蔽的：删除 team 时如果 project 还有 ProjectMember 关联（虽然 project 已迁出 team，但是 ProjectMember 行可能因为某些原因存在），团队 owner 转让流程在 §G4 描述「单事务原子：U1 → admin + U2 → owner + 同事务写 2 条 activity_log」——同事务写 activity_log 也是 R-X3 适用范围。

**证据**：
> README line 216-232（R-X3 全文）：「下游模块的 delete_by_xxx / batch_create_in_transaction 等被跨模块调用的 Service 方法必须接受外部 db: Session 参数 … 上游发起方用 with self.db.begin(): 包住整个流程」
>
> M20 design line 78-79：「删 team 时 team_members 处置：ondelete=RESTRICT，必须 Service 层显式 5 步删除（先迁出 project + 写 N+1 条 activity_log + 单事务删 team_members + teams）」——只说"单事务"，没说"M15 接受外部 session"
>
> M20 design §8.6 / §3.4 没找到 R-X3 显式引用
>
> M20 design §6 分层职责表 line 376：「Service 层 … 事务边界 + 写 activity_log」——事务边界提了，跨模块 session 没提

**修复建议**：
- A（推荐）：M20 §6 分层职责表 Service 行加 「跨模块调用规范：调 M15.log() 时传入外部 db session（R-X3）」+ §3.4 Alembic 段加注释「Phase 2 实施时所有跨模块 Service 方法签名包含 db: Session 入参」+ tests.md G8 期望段加「M15 写 N+1 条 activity_log 必须共享 M20 的事务（R-X3 验证：M15 INSERT 失败 → teams DELETE 整体回滚 = 已有 E14 case 等价）」。
- B：在 baseline-patch-m20 加「M15 Service 签名约束」段：M15 baseline-patch 时 `log(db: Session, action_type, ...)` 必须接受外部 db。优点：把 R-X3 落到 M15 baseline 行动中。
- C：什么都不加，靠 Phase 2 实施时 R-X3 自然触发。**不推荐**——M20 是 Phase 1 收官 +最后一个 R-X3 高密度场景，应该现在显式锚点。

---

### F3.10 [Medium]：team_members.user_id ondelete=CASCADE 与「移 user 出 team」业务路径冲突，并发场景未列入 §5.3

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:248-251` （`user_id ondelete=CASCADE`）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:359-366` （§5.3 状态转换竞态分析 5 场景）

**问题**：
team_members.user_id 是 ondelete=CASCADE（line 249），意思是删 user 时自动清其所有 team_members 行。但 README §横切 R-X2 (line 213-215) 明确要求「DB CASCADE 不触发下游 activity_log … 本模块删除时必须在 Service 层显式调用下游 Service.delete_by_xxx 以写入下游 activity_log，DB CASCADE 仅作兜底」。

**演进风险**：
1. 删 user 时（M01 路径）应该走 Service 层 `M01.delete_user()` → 显式调 `M20.remove_member_from_all_teams(user_id, db)`（写 N 条 team_member_removed activity_log + 含 R-X3 共享 session），而不是靠 DB CASCADE 静默删 team_members 不写 activity_log。当前 M01 文档没有这个调用链（没核对，但 M20 design 没声明这个跨模块协议）。
2. 删 user 时如果 user 是某 team 的最后一个 owner，team_member CASCADE 删除会把 team 留成"无 owner"状态——这是不变量违反。Q3 软切断 + Q9 乐观锁 + assert_team_has_owner 都不防 DB CASCADE 路径。
3. §5.3 竞态分析 5 场景没列「删 user vs team transfer」并发场景。

**证据**：
> 00-design.md line 246-252：`# 删用户时自动清其所有 team_members 行（与 M01 用户删除范式对齐） user_id: ... ondelete="CASCADE"`
>
> README line 213-215（R-X2）：「DB CASCADE 不触发下游 activity_log … 本模块删除时必须在 Service 层显式调用下游 Service.delete_by_xxx」
>
> §5.3 line 359-366：5 场景为 transfer 并发 / demote 最后 owner / 删 team 加 member / promote 同 user / 跨 team 移 project，**无**「删 user 与 team 操作」组合

**修复建议**：
- A（推荐）：§5.3 加第 6 场景「删 user vs team owner 操作并发」（写明 M01 删 user 必须先调 M20 remove_member_from_all_teams + 校验「该 user 是否任 team 唯一 owner」+ 报错 USER_IS_LAST_TEAM_OWNER 类似的 ErrorCode 或拒绝删 user）。同时加新 ErrorCode 或登记到 M01 baseline 提案。
- B：把 user_id 的 CASCADE 改 RESTRICT，强制 Service 层显式 5 步删——优点：和 team_id RESTRICT 风格一致，防"无 owner team"漂移。缺点：M01 删 user 路径会变重。
- C：在 §10 activity_log 表加注释「team_member_removed (reason="user_deleted") 由 M01 删 user 路径主动写入；DB CASCADE 仅兜底」+ 加 reason 第 3 个枚举值。

---

### F3.11 [Low]：Pydantic schema TeamMemberRoleUpdate 不允许 owner，导致 transfer 流程必须独立端点——但端点对称性未声明

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:427-428` （`TeamMemberRoleUpdate.role: Literal["admin", "member"]`）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:431-432` （`TeamTransferOwnership.new_owner_id`）

**问题**：
PATCH `/teams/{tid}/members/{uid}` 的 role 字段限 admin/member，导致升级到 owner 必须走单独的 `/transfer-ownership` 端点。这是合理设计（transfer 涉及双行更新），但**演进盲点**：
1. 未来如果加 "co-owner" 多 owner 角色（PRD 升级），这个端点二分（普通 PATCH vs transfer）能扛住吗？
2. owner 转让 = 一种 role 变更，但 API 设计里它独立成端点，违反 "改 role 走同一端点" 原则——这是有意还是巧合？没有锚点。

**证据**：
> 00-design.md line 427-428：`class TeamMemberRoleUpdate(BaseModel): role: Literal["admin", "member"]   # 不能直接改成 owner（必须走 transfer 流程）`

**修复建议**：
- A：§7.1 endpoint 表加注释「role 变更端点对称性：升降级 admin↔member 走 PATCH，owner 转让走独立 transfer-ownership（双行原子更新理由）。未来如允许多 owner，重新评估是否合并端点」。
- B：什么都不加。

---

### F3.12 [Low]：Out-of-scope 第 13 条「AC2 一键迁移批量 API」与 Q6 同步决策实质重复

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:69` （out-of-scope 第 13 条）
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:631-634` （§12 N/A 同步声明）

**问题**：
out-of-scope 第 13 条「AC2 一键迁移的批量后端 API —— 前端循环单 API（Q6）」和 §12 N/A 段「AC2「一键迁移」由前端循环调 PATCH /api/projects/{pid} N 次，进度条与失败重试由前端维护，后端不做事务原子回滚」实质相同——都把批量责任丢给前端。

**演进风险**：
- 如果将来 AC2 的 UX 痛点高（CY 自己提到 T2 trade-off），引入批量 API 时这两段都要更新——锚点重复带来漂移风险。
- 前端循环 N 次 = N 次 activity_log INSERT，加 team 时 100 个 project 移动 = 100 条 project_joined_team 事件——M15 数据流转视图会被这种"批量行为的细粒度展示"冲垮（M15 折叠分组能扛吗？）。

**证据**：
> 00-design.md line 69：「13. AC2 一键迁移的批量后端 API —— 前端循环单 API（Q6）」
> 00-design.md line 633：「AC2「一键迁移」由前端循环调 PATCH /api/projects/{pid} N 次，进度条与失败重试由前端维护，后端不做事务原子回滚」

**修复建议**：
- A：保持现状，但 ADR-005 §4 T2 trade-off 加一句「未来批量 API 引入时，记得同步更新 §12 N/A 段 + out-of-scope 第 13 条 + M15 数据流转折叠分组策略」。
- B：合并为单一锚点（out-of-scope 第 13 条引用 §12，§12 不重复声明）。

---

### F3.13 [Medium]：teams.creator_id ondelete=RESTRICT 与"删 user"路径冲突未声明

**位置**：
- `/root/workspace/projects/prism-0420/design/02-modules/M20-team/00-design.md:196-201` （creator_id 定义 RESTRICT）

**问题**：
`creator_id` ondelete=RESTRICT 意味着删 user 时如果该 user 是任何 team 的 creator，DB 会拒绝删除。Q13=C 决策 "creator_id 永不变" 让这个 RESTRICT 看起来合理，但**演进盲点**：

1. M01 删 user 路径未声明遇到 creator_id RESTRICT 怎么办——把 user 的 team 也删？转让 creator？保留 user 行只标 deleted？
2. 与 line 249 user_id ondelete=CASCADE 形成 schema 内部冲突：删 user 时 team_members 自动清，但 teams.creator_id RESTRICT 阻止删 user。结果是删 user 在第一步就 fail，CASCADE 永远不触发。
3. 这个矛盾在 §5.3 / §13 / 测试 case 都没出现。

**证据**：
> 00-design.md line 196-201：`creator_id: Mapped[PyUUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)`
> 00-design.md line 247-251：`user_id: ... ondelete="CASCADE"`——删 user 时清 team_members
> 删 user 流程未在任何地方声明优先级

**修复建议**：
- A（推荐）：§3.5 候选 B 改回成本表加新行「Q13 creator_id RESTRICT vs CASCADE/SET NULL：删 user 时 team 处置」+ M01 baseline-patch 提议（M20 accept 时通知 M01 加 user 删除路径校验：`SELECT teams WHERE creator_id=:uid` 非空 → 拒删 USER_HAS_OWNED_TEAMS 或前置迁移）。
- B：把 creator_id 改成 ondelete=SET NULL（user 删了 team 仍存在，creator_id NULL = "原创建者已删除"）—— 优点：删 user 路径不卡。缺点：creator_id NULL 的 team 唯一约束 (creator_id, name) 会让多个 NULL creator_id 的 team 无法约束 name。
- C：M20 §13 ErrorCode 加 USER_IS_TEAM_CREATOR 类似锚点，标注「删 user 时返回」，让 M01 baseline 知道这个跨模块 invariant。

---

## 总结意见

M20 整体设计扎实（Q0-Q15 决策密度 + R3-1/R3-2/R5-1/R10-2 硬规则全部满足 + tests.md 51 case 覆盖度好），Round 3 演进 audit 找到的 13 项 finding 中：

- **2 Blocker** 集中在「文档真相漂移」（F3.1 supersede 范围）和「拆批策略延迟决策」（F3.2）——这两项 Phase 2 启动前必须拆解。
- **5 High** 集中在演进盲点（org 层 F3.3 / Alembic 合并 F3.4 / 性能阈值 F3.5 / 决策对称性 F3.6）。
- **4 Medium + 2 Low** 是建议性改进（命名空间 F3.7 / 半年回看 F3.8 / R-X3 显式 F3.9 / CASCADE 冲突 F3.10+F3.13 / 端点对称性 F3.11 / 批量重复 F3.12）。

**关键演进风险一句话**：M20 的"M20 是 PRD 最小实现，未来按需扩展"的预设遇到了"未来如何扩展" 几乎完全没画的现实——Q3/Q8/Q10/Q12 的非对称风格、L3 helper 的演进形态、Alembic 三批合并的顺序，全都是 Phase 2 启动后会立刻触发的决策点。建议在 accept 前至少处理 F3.1 + F3.2 + F3.4 三项。
