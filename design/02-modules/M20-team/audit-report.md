---
title: M20 Team — 三轮独立 reviewer audit 合并报告
status: pending-cy-decision
owner: CY
created: 2026-04-26
rounds: [完整性 R1 / 边界 R2 / 演进 R3]
auditors: 3 independent general-purpose Agents（互不知情，并行执行）
total_findings: 39（Blocker 6 / High 16 / Medium 12 / Low 5）
---

# M20 三轮 audit 合并报告

> 三 Agent 独立 audit，互不知道对方的 finding，并行执行。本文按 Round 1 / 2 / 3 分章节集结。每轮原始报告分别保留在 [`audit-report-round1.md`](./audit-report-round1.md) / [`audit-report-round2.md`](./audit-report-round2.md) / [`audit-report-round3.md`](./audit-report-round3.md)，本文做合并 + Finding 矩阵 + 重复识别 + CY 决策入口。

---

## 0. Finding 矩阵（按严重度 × 主题分布）

| ID | 严重度 | 主题 | 重叠/独立 | 一句话 |
|----|--------|------|----------|--------|
| **F1.1** | Blocker | Auth 路径 | 独立 | §8.5 Q11=A "全 P1" 与 ADR-004 §253 "绝大多数 P1+P2"+§6 Server Action(P2) 冲突 |
| **F1.2** | Blocker | R-X3 跨模事务 | 与 F3.9 重叠 | 删 team 5 步 + transfer owner 无 Service 接口签名草案，未声明接受外部 db: Session |
| **F1.3** | Blocker | R10-1 + target_id | 独立 | 删 team N+1 条 activity_log 写入顺序 / target_id 字段约束未锁，易漂移成汇总 |
| **F2.1** | Blocker | 契约延后 | 独立 | tests.md B4 "transfer 给自己" 行为留 Phase 2 决，违反设计前置；ErrorCode reason 枚举不一致 |
| **F3.1** | Blocker | ADR supersede | 与 F2.10 重叠 | ADR-005 supersede 仅"命名"，实际改了 命名 + 类型 INT→UUID + 启用 FK 三件 |
| **F3.2** | Blocker | 17 模块拆批 | 独立 | L3 注入升级 17 模块拆批策略 unchecked + 测试模板形态未明，违反可逆性二分 |
| F1.4 | High | R3-4 反悔成本 | 独立 | 反悔表只覆盖 Q0/Q4/Q8/Q13，缺 Q1/Q2/Q3/Q5 行为级反悔成本 |
| F1.5 | High | R4-2 teams 状态机 | 独立 | teams 唯一一条"禁止转换"实为前置校验，自承认违反 R4-2 |
| F1.6 | High | R4-2 role 状态机 | 独立 | team_members.role 禁止转换 2 条不够，admin↔owner 反向（非 transfer 场景）未列 |
| F1.7 | High | §12 N/A 引用 | 独立 | §12 N/A 声明未引 README §12 4 子模板表 |
| F1.8 | High | §5.2 决策来源 | 独立 | "事务边界=A（默认）" 无 Q 编号，决策来源不可追溯 |
| F2.2 | High | AC2 规模假设 | 独立 | 一键迁移规模未声明，§12 同步 + 前端循环隐式假设 100 量级，未量化 |
| F2.3 | High | archived×team 互锁 | 独立 | M02 archived 不可逆 vs M20 删 team RESTRICT 互锁，跨模决策盲点 |
| F2.4 | High | 软切断 audit | 独立 | Q3 软切断仅 HTTP 响应通知，活动日志无 residual 字段，脚本路径绕过 |
| F2.5 | High | M15 read 入口 | 独立 | team_* 事件 8/10 无 project_id，但 baseline 仅升级 list_for_project，无 list_for_team |
| F2.6 | High | creator 唯一冲突 | 独立 | UniqueConstraint(creator_id, name)+永不变 → transfer 后 U1 想再用同名被拒 |
| F2.7 | High | PATCH 多字段顺序 | 独立 | PATCH /projects/{pid} 同时改 team_id+其他字段时校验顺序 / partial update 语义未定 |
| F2.10 | High | supersede 范围 | 与 F3.1 重叠 | ADR-005 supersedes 字段只"命名部分"，但实质 3 项变更 |
| F3.3 | High | org 层迁移 | 独立 | 加 organization 层路径仅一句"再走一次 baseline-patch"，4 决策点零锚点 |
| F3.4 | High | Alembic 合并顺序 | 独立 | M16/M18/M20 三批 ActionType 扩 CHECK 合并 Alembic 顺序未画 |
| F3.5 | High | 性能阈值锚点 | 独立 | "P95>100ms 引 Redis" 未挂 ADR T1 / README 回看；缓存失效路径 0 行 |
| F3.6 | High | 对称性演进 | 与 F2.11 重叠 | Q3 软 / Q8 严 非对称在加 org 层时如何延续未画 |
| F1.9 | Medium | helper ADR-003 引 | 独立 | §9 横切 helper 未声明 ADR-003 / R-X3 / R-X4 合规 |
| F1.10 | Medium | endpoint 嵌套 max | 独立 | PATCH /projects/{pid} 权限语义与 §8.6 嵌套 max 未自洽 |
| F1.11 | Medium | §15 边界 | 独立 | M02/M15 文档同步是 Phase 1 还是 Phase 2 在 §15 vs baseline 冲突 |
| F2.8 | Medium | out-of-scope 反测 | 独立 | 15 项 out-of-scope 多项缺反向测试覆盖陈述 |
| F2.9 | Medium | correlation_id | 独立 | transfer 拆 2 条 / 删 team N+1 条事件 audit 关联仅靠 timestamp，无硬关联字段 |
| F2.11 | Medium | Q3/Q8 不对称 | 与 F3.6 重叠 | Q3 软 vs Q8 严 防误哲学不一致，未在 ADR §Trade-offs 显式登记 |
| F2.12 | Medium | M15 read 范围 | 独立 | M15 read 仅升级 list_for_project，list_for_user / get_by_id 未明示 |
| F2.13 | Medium | M02 双重过滤 | 独立 | M02 ProjectDAO 既 own 又横切引用，去重逻辑未明（叠加冗余 vs 替换） |
| F3.7 | Medium | 命名空间膨胀 | 独立 | M20 ActionType 命名 promoted_admin 实际承载 owner，命名空间缺失早期信号 |
| F3.8 | Medium | 半年回看缺 | 独立 | README 设计回看清单未挂 M20 性能/枚举/org 层触发器 |
| F3.9 | Medium | R-X3 显式 | 与 F1.2 重叠 | 删 team 5 步流程未显式声明 R-X3 共享外部 session |
| F3.10 | Medium | CASCADE×CASCADE | 独立 | team_members.user_id CASCADE + R-X2 要求 Service 显式 / "无 owner team" 风险 |
| F3.13 | Medium | creator RESTRICT | 独立 | teams.creator_id RESTRICT vs user_id CASCADE 内部冲突，删 user 路径卡 |
| F1.12 | Low | README 状态 | 独立 | README §模块清单 M20 行"待开" vs 实际 draft，格式不一致 |
| F2.14 | Low | M09 死代码 | 独立 | baseline-patch §M03-M19 表仍列 M09，应去掉（superseded by M18） |
| F3.11 | Low | role endpoint 对称 | 独立 | TeamMemberRoleUpdate 限 admin/member，transfer 独立端点对称性未声明 |
| F3.12 | Low | AC2 锚点重复 | 独立 | out-of-scope 第 13 + §12 N/A 实质重复，未来引入批量 API 易漂移 |

**重叠合并建议**：
- F1.2 + F3.9 → 合并为「R-X3 删 team 5 步 / transfer / M15 调用全链路 Service 签名 + 共享 session」
- F2.10 + F3.1 → 合并为「ADR-005 supersede 范围精确化（命名 + 类型 + FK 三件）」
- F2.11 + F3.6 → 合并为「Q3/Q8 防误对称性 + 演进延伸原则（ADR-005 §4 T7）」

合并后 unique findings：39 - 3 = 36 项需独立处置。

---

## 1. CY 决策入口（Blocker / High 必决，Medium / Low 可批量"接受+登记"）

> 6 个 Blocker + 16 个 High（其中 3 对重叠合并为 19 - 3 = 13 项独立 High）= **19 项必决**
> 12 个 Medium + 5 个 Low = **17 项可批量**

按修复路径分组，给 CY 拍板。每组给推荐选项（基于 reviewer 一致建议），CY 可全接受 / 单独反驳。

### 组 A（Auth + 跨模事务，Blocker 集中）

| Finding | 推荐 |
|---------|------|
| F1.1 | A：Q11 改"P1+P2 合并入口"，§8.5 文案对齐 ADR-004 §79 |
| F1.2 + F3.9 | A：§6 + §8.7（新增）补 Service 签名草案 `def delete_team(self, db, ...)` / `def transfer_ownership(self, db, ...)`，明示接受外部 db + R-X3 合规 |

### 组 B（契约必须 Phase 1 收敛）

| Finding | 推荐 |
|---------|------|
| F2.1 | A：B4 拒 422，detail.reason="target_is_self"（新增第 4 值），§13.1 ErrorCode + ADR-005 同步登记 |
| F2.6 | B：保留 schema，§13.1 TEAM_NAME_DUPLICATE detail 加 creator_id 字段 + 前端文案区分；tests.md 加 B5b 用例 |
| F2.7 | B：拆 POST /projects/{pid}/move-team 独立端点（与 transfer-ownership 风格一致），M02 PATCH 不再承担 team_id 字段 |

### 组 C（数据 / 事件可追溯性）

| Finding | 推荐 |
|---------|------|
| F1.3 | A：§10 末加"删 team R10-1 合规说明"，锁死 N+1 写顺序 + target_id=team_id + metadata.user_id |
| F2.4 | A：team_member_removed.detail 加 residual_project_count + residual_project_ids[:10] |
| F2.5 | A：M15 baseline-patch 加 ActivityLogDAO.list_for_team(team_id, user_id) |
| F2.9 | C：metadata.detail 加 correlation_id（jsonb，0 schema 改），M20 transfer + 删 team 流程统一生成 |

### 组 D（ADR / supersede 元数据精确化）

| Finding | 推荐 |
|---------|------|
| F2.10 + F3.1 | A：ADR-005 supersedes 改为「ADR-001 §预设 3 整段（命名 + 类型 + FK）」+ Consequences §中性段改写 |
| F1.4 | A：§3.5 R3-4 表加 Q1/Q2/Q3/Q5 四行行为级反悔代价 |

### 组 E（状态机 + N/A 声明合规）

| Finding | 推荐 |
|---------|------|
| F1.5 | A：§4.1 改写为"[*]→active：team_recreated 拒 404"风格的真禁止转换；前置校验挪 §10/§13 |
| F1.6 | A：§4.2 加 owner→admin（非 transfer）拒 422 + owner→member 直降拒 422 两条 |
| F1.7 | A：§12 N/A 段引 README §12 4 子模板表 + catalog 4 维异步标注"同步" |
| F1.8 | B：补 brainstorming Q13.2 事务边界 + ADR-005 决策表加行（决策来源严格 1:1） |

### 组 F（边界场景：archived / 规模 / 软切断哲学）

| Finding | 推荐 |
|---------|------|
| F2.2 | A：§1 in scope 加规模假设"AC2 ≤100 个 project，>100 列 Phase 2 批量 API 触发器" + tests.md 加 B12 |
| F2.3 | A+C 组合：禁止 archived project 加入 team（C，源头）+ 删 team 时 archived 自动迁出（A，历史兜底） |
| F2.11 + F3.6 | A：ADR-005 §4 加 T7"Q3 软切断 vs Q8 强制前置"哲学陈述「越靠近资源越严格」+ 给未来 org 层延伸原则 |

### 组 G（演进锚点 + 半年回看）

| Finding | 推荐 |
|---------|------|
| F3.2 | A：baseline-patch §3 现在拍板拆批策略（批 1=M02+M03+M04 / 批 2=M05-M08 / 批 3=M10-M14 / 批 4=M15-M19）+ 测试模板用 pytest parametrize over DAO |
| F3.3 | A：ADR-005 加 §8"未来 organization 层路径（占位）"，列 4 决策点（唯一约束 / 二维空白态 / helper 形态 / 对称延伸） |
| F3.4 | A：baseline-patch §3 加"M15 三批合并 Alembic 顺序"（单 revision + 字母序 M16→M18→M20）+ 硬触发器"M20 accept 当天回写 M15" |
| F3.5 | A：tests.md C 类加 C7 性能压测前置硬节点 + ADR-005 §4 T1 加失效路径预演（U 加入 / 移出 / 删 team / project 加 / project 移） |
| F3.8 | A：README 设计回看清单加 M20 三行（2026-10-26 性能 + 2026-10-26 枚举 + 2027-04-26 org 层） |

### 组 H（CASCADE / RESTRICT 内部冲突）

| Finding | 推荐 |
|---------|------|
| F3.10 | A：§5.3 加第 6 场景"删 user vs team owner 操作"+ M01 baseline 提议 USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER 校验链 |
| F3.13 | A：§3.5 R3-4 表加 creator_id RESTRICT vs CASCADE 反悔成本 + M01 baseline 提议（与 F3.10 同一改动批次） |

### 组 I（Medium / Low 批量"接受+登记"）

11 项推荐统一接受 reviewer 推荐方案：
- F1.9 / F1.10 / F1.11 / F2.8 / F2.12 / F2.13 / F3.7 / F3.11 / F3.12（Medium / Low）
- F1.12 / F2.14（Low，README/baseline 文档清理）

---

## 2. Round 1 — 完整性 Audit（12 finding：B3 / H5 / M3 / L1）

> 完整原文：[`audit-report-round1.md`](./audit-report-round1.md)
>
> 主结论：M20 设计骨架完整、Q0-Q15 决策落地清晰、R3-1/R3-2/R5-1/R10-2 等核心硬规则通过；3 处 Blocker（P1+P2 漂移 / R-X3 缺签名 / R10-1 顺序未锁）+ 5 处 High。20 项检查中 11 项无 finding。

详见 `audit-report-round1.md`。

---

## 3. Round 2 — 边界 Audit（14 finding：B1 / H6 / M5 / L2）

> 完整原文：[`audit-report-round2.md`](./audit-report-round2.md)
>
> 主结论：主体决策与 PRD F20 字面对齐良好；边界场景 5 类未收敛——AC2 规模 / archived×team / 软切断 audit / creator 唯一性 / R10-2 与 list_for_team。
>
> Phase 1 收官前必修 8 项：F2.1 + F2.2 + F2.3 + F2.4 + F2.5 + F2.6 + F2.7 + F2.10。

详见 `audit-report-round2.md`。

---

## 4. Round 3 — 演进 Audit（13 finding：B2 / H5 / M4 / L2）

> 完整原文：[`audit-report-round3.md`](./audit-report-round3.md)
>
> 主结论：演进基础健康；2 Blocker（supersede 真相漂移 + 17 模块拆批延后）+ 5 High（org 层路径 / Alembic 合并 / 性能阈值 / Q3-Q8 演进对称 / M15 baseline 同步）。
>
> 关键风险：M20"最小实现，未来按需扩展"预设遇到"未来如何扩展几乎零锚点"现实——Q3/Q8/Q10/Q12 非对称、L3 helper 演进、Alembic 三批合并都是 Phase 2 启动后立刻触发的决策点。

详见 `audit-report-round3.md`。

---

## 5. 修复 → verify 闭环建议

CY 决策每项后，按以下顺序执行：

1. **第一批（fix v1）**：组 A + B + D + E（Auth / 契约 / supersede / 状态机），约 12 项 finding，集中改 00-design.md + ADR-005 + tests.md
2. **第二批（fix v2）**：组 C + F + H（事件可追溯 / 边界场景 / CASCADE 冲突），约 12 项 finding，需协同 M01 / M02 / M15 baseline 变更
3. **第三批（fix v3）**：组 G（演进锚点），约 5 项 finding，集中改 baseline-patch-m20.md + ADR-005 §4 + README 设计回看清单
4. **批量批（接受 + 登记）**：组 I，11 项 Medium/Low

每批完成后启动 **独立 verify Agent**（subagent_type=general-purpose），独立读修复后文件验证 fix 没撒谎、没引入新违规，产 `audit-verify-vN.md`。

---

## 6. 决策文档落地清单

最终 accept 时 M20 关联文档同步更新：

- [ ] `M20-team/00-design.md` —— 主设计修复（按 CY 决策落每项）
- [ ] `M20-team/tests.md` —— 测试用例补 B5b / B12 / C7 等
- [ ] `adr/ADR-005-team-extension.md` —— supersedes 字段精确化 + §4 加 T7 + §8 加未来 org 层路径占位
- [ ] `02-modules/baseline-patch-m20.md` —— 拆批策略 + Alembic 合并顺序 + M02/M15 双重过滤去重 + M15 list_for_team
- [ ] `02-modules/README.md` —— §模块清单 M20 状态 / §设计回看清单 +3 行
- [ ] `02-modules/M02-project/00-design.md` —— space_id → team_id 同步（决策 F1.11 后定 Phase 1 还是 2）
- [ ] `02-modules/M15-activity-stream/00-design.md` —— ActionType +10 / TargetType +1 / ErrorCode +8 / list_for_team 接口
- [ ] `02-modules/M01-user-account/00-design.md` —— 提议 baseline-patch（USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER）
- [ ] `adr/ADR-001-shadow-prism.md` —— §预设 3 末尾加反向交叉引用（如 F3.1 选 B 候选）
