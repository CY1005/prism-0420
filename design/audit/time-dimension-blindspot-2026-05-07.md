---
title: 时间维度盲区 — M02 sprint 启动元反思
status: living
owner: CY
created: 2026-05-07
purpose: |
  沉淀 prism-0420 设计前置体系在 M02 sprint 启动 reconcile pass 期间暴露的
  两个元维度盲区：①时间维度（baseline-patch 时序错位 / accepted-minimal early adopter / 启动数据 / scaffold 注释）
  ②横切 vs 业务关注边界。

  本文件记录全过程：触发→收敛→盲区根因→体系级新原则→落地规则→实证→元教训。
  作为 prism-0420 项目内日志（项目特定数据）；脱敏方法论部分见 KB
  `02-技术/架构设计/设计前置方法论-补丁01-时间维度.md`。
---

# 时间维度盲区 — M02 sprint 启动元反思

## 1. 触发场景

2026-05-07 M02 sprint 启动闸门 2.5 reconcile pass 期间，AI（Claude Code）扫 M02 design 发现 **9 处 seam**（疑似阻塞项），呈现给 CY 决策。CY 元层级追问"为什么 9 处都有问题？现有原则体系没卡住吗？"——多轮 reconcile 后收敛到**真问题 + 体系盲区**。

## 2. 9 收敛到 4 真 seam（reconcile pass 三栏混淆）

AI 初版扫描列了 9 处 seam，混入 3 类：

| 编号 | 内容 | 实际类别 |
|----|----|----|
| M02-S1 | M20 baseline-patch teams FK | **真 seam B 类（待 CY 决策）** |
| M02-S2 | M18 baseline-patch rrf_k+方法 | **真 seam B 类** |
| M02-S3 | TenantContextProtocol 注入 | C 已自我消解（scaffold S2 注释指明）|
| M02-S4 | dimension_types seed | **真 seam B 类（产品决策）** |
| M02-S5 | AES helper 不存在 | **真 seam B 类（横切 helper 缺失）** |
| M02-S6 | 12 ErrorCode + R13-1 | A 机械可做（design 已列子类）|
| M02-S7 | activity_log action_type 注册 | A 机械可做（write_event stub 走 structlog）|
| M02-S8 | check_project_access Depends 不存在 | A 机械可做（M02 own horizontal）|
| M02-S9 | 无 PR vs 闸门 3 §3.1 | C 已通过 bypass-log 处理 |

CY 戳出：**9 处看起来都像问题，但 5 处是凑数**（A 机械可做 / C 已自我消解 / 已处理）。混入一张表让 CY 难以分辨"哪些他要拍 / 哪些 AI 直接做"。

→ **真 seam = 4**（S1 / S2 / S4 / S5）

## 3. 5 个体系盲区（4 时间维度 + 1 横切维度）

逐项推导根因：

### 3.1 baseline-patch 反向时序（L1 总领级缺位）

M02 design §3 含 M20/M18 baseline-patch 反向回写（M20/M18 在 M02 之后实施），但**没规定实装期遇到"依赖未到位"如何退化**。

→ **缺：R-X5 baseline-patch 时序契约 + 主标准 Q1+Q2（独立完成性 + caller/callee）+ 退化路径 A/B/C 定义**

### 3.2 accepted-minimal early adopter 触发条款缺失（L1 总领级缺位）

03/04/05-spec 是 accepted-minimal 状态，§8.0 必补——但**没规定模块在 §8.0 之前需要某能力时怎么办**。M02 sprint 期就要用 AES helper，但 §8.0 还没补完。

→ **缺：05-security-baseline §7 early adopter 触发条款 + 后续 D4 推演修订加 §7.1/§7.2 横切判断前置**

### 3.3 启动数据声明缺失（L2 模块级模板缺位）

含字典/全局表的模块 design 没强制声明"启动数据是什么 / 谁种 / 何时种"。M02 dimension_types 是首例。

→ **缺：R3-6 启动数据声明（细化版分 3 子项：启动期硬性 / 测试兜底 / 业务字典运行期）**

### 3.4 scaffold S2 注释模板未规范化（L1 总领级缺位）

M01 sprint 7 seam 中 S2 (TenantContextProtocol) 是"做对了"的范例（注释指明 M02/M20 各自补什么），但**没归纳成强制规则**——S1/S4/S6 没做对。

→ **缺：闸门 2.5 S2 注释 4 字段强制模板 + reconcile pass 三栏强制分类**

### 3.5 横切 vs 业务关注边界缺失（L1 顶层元维度缺位）⭐ 最深盲区

prism-0420 体系覆盖纵向分层（5 原则 #2）/ tenant 隔离 / 事务边界 / 跨模块调用 / 时序错位等——**整体缺一条"横切 vs 业务关注"的元维度原则**。

CY 推 D4 决策时指出"AES helper 应所有模块共用，为什么挂在 M02 名下？"——这是横切 vs 业务边界判定问题，不是 sprint 边界问题。AI 推 "B M02 own helper" 时确实给齐了候选 + 优缺点，**但全从"M02 sprint 边界"维度看**，没从"helper 归属"维度看。

→ **缺：6 原则 #6 横切 vs 业务关注必须显式判定 + R-X6 横切 helper 必横切层 + 04-layer Q7 横切层定义 + frontmatter helpers 字段约束 + §7 判断前置**

## 4. 体系级新原则 2 条

### 原则 1（时间维度）
> **design 是目标态真相，实装期遇到"依赖未到位"必须显式选退化路径，不允许悄悄绕**

### 原则 2（横切维度）
> **横切关注 vs 业务关注必须显式判定——横切 helper 必建在横切层；不确定时默认横切（YAGNI 反向）**

## 5. 落地规则清单（8 条）

| # | 规则 | 落点 |
|---|---|---|
| 1 | **6 原则 #6 横切 vs 业务关注必须显式判定** | `00-architecture/06-design-principles.md` |
| 2 | **04-layer Q7 横切层定义**（横切层文件位置清单 + 业务模块层定义 + 判定流程 + Owner 归属） | `00-architecture/04-layer-architecture.md` |
| 3 | **R-X5 baseline-patch 时序契约**（主标准 Q1+Q2 + 退化路径 A/B/C 定义 + 结构性约束 + 子选项清单留空待实证 + 类型倾向参考表）| `02-modules/README.md` 横切区 |
| 4 | **R-X6 横切 helper 必横切层**（归纳 scaffold S2/S5 先例 + 4 字段注释模板）| `02-modules/README.md` 横切区 |
| 5 | **R3-6 启动数据声明（细化 3 子项）**（启动期硬性 / 测试兜底 / 业务字典运行期）| `02-modules/README.md` §3 |
| 6 | **frontmatter `references.helpers:` 字段约束**（仅允许引用横切层路径）| `02-modules/README.md` |
| 7 | **闸门 2.5 S2 注释 4 字段强制模板 + reconcile pass 三栏强制分类** | `00-phase-gate.md` |
| 8 | **accepted-minimal §7 early adopter（含 §7.1/§7.2 横切 vs 模块特定判断前置）** | `01-engineering/05-security-baseline.md` + 03/04 引用段 |

## 6. 11 处 baseline-patch 实证（5 模块）

按 R-X5 主标准推导 11 处 baseline-patch 退化路径：

| # | 模块 | baseline-patch | 主标准推导 | 退化路径 | 落点 |
|---|----|----|----|----|----|
| A1 | M02 | team_id FK to teams (M20)| Q1 否+Q2 callee | **C 留中间态** | M02 §3.X |
| A2 | M02 | rrf_k+similarity_threshold+get_search_config (M18)| Q1 是 | **A 现在建** | M02 §3.X |
| A3.1 | M02 | PROJECT_ARCHIVED ErrorCode (M20)| Q1 是（enum）| **A 现在建** | M02 §3.X |
| A3.2 | M02 | move-team endpoint (M20)| Q1 否+Q2 caller | **B 推迟** | M02 §3.X |
| A4 | M03 | get_for_embedding+enqueue (M18)| Q1 否+Q2 caller（enqueue 部分）/ Q1 是（被动接口部分）| **B + A 拆开** | M03 §6.X |
| A5 | M04 | 同 A4（dimension_record）| 同上 | 同上 | M04 §6.X |
| A6 | M06 | 同 A4（competitor，url 不参与 embedding）| 同上 | 同上 | M06 §6.X |
| A7 | M07 | 同 A4（issue）| 同上 | 同上 | M07 §6.X |
| A8 | M15 | M18 ActionType+TargetType enum | Q1 是（enum 死定义）| **A 现在建** | M15 §3.X |
| A9 | M15 | M20 TEAM_NOT_FOUND+8 ErrorCode | Q1 是（enum）| **A 现在建** | M15 §3.X |
| B1 | M02 | dimension_types 启动数据 | R3-6-B 测试兜底 placeholder + R3-6-C 业务清单运行期 | **B+C 分层** | M02 §3.Y |
| C1 | M02 | AES helper（C1） | §7.1 横切关注 | **B' 部分提前**（横切层 `api/auth/crypto.py`）| M02 §3.Z |

## 7. T11 排查结果（验证：立规防御未来，不是修复存量）

整体扫 M01-M20 design + scaffold + ADR + baseline-patch：

- ✅ frontmatter helpers ref 路径：0 违反
- ✅ design §6 分层职责表：5 处合法模式（业务 service 调横切 activity_log）
- ✅ 现有 8 horizontal helper 位置：全部在横切层
- ✅ 业务模块子目录（如 `api/services/m02/`）：0 处存在
- ✅ ADR 1-5 横切归属：全明确
- ✅ baseline-patch-batch3/m18/m20：0 错放

**0 处真正反模式存量**——CY 一直凭 sense 把横切 helper 放对位置（M01 sprint TenantContextProtocol scaffold S2 是范本）。立规价值是**防御未来 sprint 漂移**，不是修存量。

T12 修复存量：10 horizontal helper docstring 加 horizontal+owner 4 字段 + 3 design 灰区（ADR-001/M18/M17）显式标 horizontal owner。

## 8. 元层级反思 4 案例

### 案例 1 — reconcile pass 三栏混淆

AI 初版把"机械可做 + 待 CY 决策 + 已自我消解"9 处混入一张表 → CY 戳出 5 处凑数 → 立规：闸门 2.5 三栏强制分类。

### 案例 2 — 路径 X+ 立子选项规撞凭印象（X- 折中）

AI 推路径 X+（立 R-X5 子选项清单 A/B/C 各 3 子项）→ CY 推演 4 个新盲区（C 子选项分层错 / FastAPI OpenAPI 是 router 生成不是 design 生成 / 分层依赖方向约束 / R13-1 标记位置颗粒不够）→ AI 承认凭印象立规违反 `feedback_external_behavior_lookup` → 改路径 X- 折中（结构性约束可前置 + 子选项清单留空待实证）。

### 案例 3 — §7 "模块 own helper" 对横切关注反模式

§7 1.0 三选一含"B 模块 own helper" → AI 推 D4 选 B 让 M02 own AES helper → CY 戳"helper 不应该所有模块共用吗？"→ AI 承认 B 项对横切关注是反模式 → §7 修订加判断前置（横切 vs 模块特定）→ §7.1 横切三选一 + §7.2 模块特定三选一拆开。

### 案例 4 — 原则体系缺"横切 vs 业务"元维度

CY 追问"哪些原则有卡点"→ AI 系统盘 5 原则 + 5 约束清单 + R-X1~X5 → 发现整体缺一条"横切 vs 业务"元维度原则 → 加 6 原则 #6 + R-X6 + 04-layer Q7 + frontmatter helpers 约束。

## 9. 元教训 4 条

### 教训 1：立规分两层
> **结构性约束可前置 / 工程具体子选项必先实证**

凭印象立工程具体子选项（如 OpenAPI 处理选项 / C 路径写入策略）会撞 FastAPI/分层依赖等真实机制，违反 `feedback_external_behavior_lookup`。结构性约束（必声明 / 必登记 / 必有 TODO 注释）不依赖工程具体，可前置立规。

### 教训 2：立规时必判 horizontal vs module-specific 边界
> **横切关注禁挂业务模块名下；不确定时默认横切（YAGNI 反向）**

立规时漏一道判断前置（"helper 是横切还是模块特定？"）会导致规则本身把横切关注错塞进模块 own。

### 教训 3：立规防御未来 vs 修复存量
> **好体系让团队不靠 sense 也能走对**

prism-0420 现状 0 处反模式存量——CY 一直凭 sense 放对横切 helper。但立规的价值是**防御未来 sprint 漂移**——M02 AES helper 差点凭"sprint 边界"维度推错（B M02 own），是首次 sense 险些失灵。

### 教训 4：L1/L2/L3 时间维度切分
> **设计原则按"应定时机"分 3 层，立规时机错位是体系级问题**

| 层级 | 应定时机 | 内容 | prism-0420 是否前置 |
|---|----|----|---|
| **L1 总领级** | Phase 1 设计前置早期 | 设计原则 / 分层架构 / 横切边界 / R-X 横切规则 | ❌ 多数晚定 |
| **L2 模块级** | Phase 1 模块 design | 模块业务 / 状态机 / schema / API | ✅ 已前置 |
| **L3 实证后归纳** | Phase 2.1 sprint 实证后 | 工程具体子选项（如 OpenAPI 处理 / 类型 owner）| ✅ 合理推迟 |

## 10. L1/L2/L3 对比表 — 10 项晚定 + 5 矛盾

### 10 项晚定（L1 应早立但 2026-05-07 后期才补）

| 项 | 实际定的时机 | 应该定的时机 |
|---|---|---|
| 6 原则 #6 横切 vs 业务边界 | 2026-05-07 | 06-design-principles 1.0 |
| 04-layer Q7 横切层定义 | 2026-05-07 | 04-layer 1.0 |
| R-X5 baseline-patch 时序契约 | 2026-05-07 | 02-modules/README.md 1.0 |
| R-X6 横切 helper 必横切层 | 2026-05-07 | 02-modules/README.md 1.0 |
| R3-6 启动数据声明 | 2026-05-07 | 02-modules/README.md 1.0 |
| accepted-minimal §7 early adopter | 2026-05-07 + 修订 | 03/04/05 spec 1.0 |
| 闸门 2.5 S2 注释 + 三栏分类 | 2026-05-07 | 闸门 2.5 立时 |
| ADR-001 §预设 4 横切归属标 | 2026-05-07 | ADR-001 1.0 |
| frontmatter helpers 字段约束 | 2026-05-07 | frontmatter 标准立时 |
| 现有 horizontal helper docstring horizontal+owner | 2026-05-07 (T12) | Phase 2.0 scaffold 立 helper 时 |

### 5 矛盾

| # | 矛盾 | 解决 |
|---|---|---|
| 1 | R3-6 启动数据声明与"产品字典"混淆 | R3-6 细化 3 子项（启动期硬性 / 测试兜底 / 业务字典运行期）|
| 2 | L1 总领级规则全部晚定 | 沉淀 KB 补丁 01 推动方法论修订 |
| 3 | R-X5 三层立规时机错配（主标准+结构性应早 / 子选项可晚）| 立规时显式分三层结构 |
| 4 | §7 修订版 §7.1/§7.2 在 D4 推演后才补 | 横切判断前置加入主标准 |
| 5 | 设计前置流程"总领→详设→实证"实际反向 | 沉淀 KB 补丁，未来项目早期立 L1 |

## 11. 决策透明度边界

何时 AI 推荐 / 何时 CY 必判断（本次会话实证）：

| 类型 | AI 处理 | CY 必判断 |
|---|---|---|
| 机械执行（按既有规则）| ✅ 直接做 | — |
| 主标准推导（按 Q1+Q2 → A/B/C）| ✅ 直接推 | — |
| 工程具体子选项（凭印象有风险）| ⚠️ 不立规，留实证 | ✅ sprint 写代码时拍 |
| 业务决策（产品方向 / 字典内容）| ❌ 不替决 | ✅ 必拍 |
| 体系级方向（立新原则 / 加 R-X 规则）| 提议 | ✅ 必拍 |
| 多维度审视（如横切 vs 业务边界）| ❌ AI 容易漏维度 | ✅ 元层级追问触发 |

CY 在本次会话连戳 4 轮（9→4 真 seam / 路径 X+ 凭印象 / §7 模块 own / 原则缺横切元维度），每轮都暴露 AI 决策透明度边界——AI 给出的"完整优缺点"实际只覆盖一个维度。

## 12. 落地验证

### M02 闸门 2.5 reconcile pass（C 阶段）

| 检查项 | 状态 |
|---|---|
| A 栏机械可做 | ✅ T2+T5 已落 |
| B 栏待 CY 决策 | ✅ 全按主标准推导，无 B 栏未决 |
| C 栏已自我消解 | ✅ |
| R-X5 主标准 Q1+Q2 推导 3 处 baseline-patch | ✅ A1=C / A2=A / A3.1=A + A3.2=B |
| R-X6 横切层归属 | ✅ AES helper 横切层 |
| R3-6 启动数据 3 子项 | ✅ M02 §3.Y 已声明 |
| 6 原则 #6 横切 vs 业务 | ✅ |
| §7 horizontal vs module-specific 判断前置 | ✅ §7.1 横切三选一应用 |

**M02 闸门 2.5 reconcile pass: ✅ 通过**——无矛盾、无未拍决策、无新发现的盲区。

### 全 M01-M20 扩展验证（D 阶段）

- R3-6 启动数据：0 缺漏
- frontmatter helpers ref：0 违反
- 横切关注错放：0 实例
- ADR + spec + 模块 design v2 修订标：全补完
- E 递归：无新发现

### 回归测试（F 终止条件）

- pytest：118 PASS / 0 fail / 0 xfail
- ruff：净
- ci-lint.sh：R13-1 22=22 + L12 守护通过

## 13. 关联

- **KB 方法论补丁**：[`/root/workspace/projects/ai-quality-engineering/02-技术/架构设计/设计前置方法论-补丁01-时间维度.md`](file:///root/workspace/projects/ai-quality-engineering/02-技术/架构设计/设计前置方法论-补丁01-时间维度.md)
- **主方法论**：`/root/workspace/projects/ai-quality-engineering/02-技术/架构设计/设计前置执行方法论-人机协作与对抗式Reviewer.md`
- **本项目 lessons-learned**：[`./lessons-learned.md`](./lessons-learned.md)
- **R-X5 主规则**：[`../02-modules/README.md`](../02-modules/README.md)
- **6 原则 #6**：[`../00-architecture/06-design-principles.md`](../00-architecture/06-design-principles.md)
- **04-layer Q7**：[`../00-architecture/04-layer-architecture.md`](../00-architecture/04-layer-architecture.md)
- **§7 修订**：[`../01-engineering/05-security-baseline.md`](../01-engineering/05-security-baseline.md)
- **闸门 2.5**：[`../00-phase-gate.md`](../00-phase-gate.md)

## 14. 维护

- 本文件 status=living——M03 / M07 / M20 等后续模块 sprint 启动若再撞同款问题（如新字典模块 / 新 baseline-patch / 新 horizontal helper），追加到 §6 实证表 + §10 矛盾表
- 累积 ≥ 3 次新撞同款问题 → 触发对应 L1 规则升级（如 R-X5 子选项清单从"留空待实证"升级为含具体子选项）
- 本文件由 CY review 决定何时归档（推荐 Phase 3 数据对照报告完成后）
