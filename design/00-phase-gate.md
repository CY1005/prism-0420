---
title: prism-0420 阶段闸门规则
status: accepted
owner: CY
created: 2026-04-26
---

# Phase Gate 阶段闸门

> 防"跳过工程地基直接写业务代码"的硬规则。配合 [`00-roadmap.md`](./00-roadmap.md) 当前位置查询使用。

---

## 闸门 1：Phase 1 → Phase 2.0

**进入 Phase 2.0 工程基线无前置（Phase 1 已完成 = 进入许可证）**。

---

## 闸门 2：Phase 2.0 → Phase 2.1（关键闸门）

写**任何业务模块代码**之前必须**全部 ✅**：

### 2.1 决策类（A 阶段）

- [ ] `02-quality-spec.md` accepted（测试框架 + Lint + Formatter 全决）
- [ ] `engineering-spec.md` §13 accepted（Code review 流程）

### 2.2 代码类（B 阶段）

本地命令必须能跑通：
- [ ] `make dev`（启动 FastAPI + Next.js + PG + Redis）
- [ ] `make test`（pytest + vitest 跑空 test 通过，fixtures 工作）
- [ ] `make migrate`（Alembic upgrade head 不报错）

横切 helper 必须有可调用 + 单元测试：
- [ ] `api/errors/`（AppError + ErrorCode + middleware）
- [ ] `api/auth/`（require_user + JWT + P2 internal token）
- [ ] `api/services/activity_log_service.py`（write_event 单方法）
- [ ] `api/auth/tenant_filter.py`（user_accessible_project_ids_subquery）

---

## 闸门 2.5：Phase 2.0 后置 / Phase 2.1 前置 — Scaffold ↔ Design Reconcile

每个业务模块 sprint 启动前（M01 起每模块都跑一次），必须 ✅：

- [ ] 模块 design 引用的所有 horizontal helper（`api/errors/`、`api/auth/`、
      `api/models/base.py`、`api/queue/` 等）已对照模块 design 检查命名/接口/形态对齐
- [ ] 发现的 seam 已分类（机械可做 / 待 CY 决策 / 已自我消解）并在
      `design/audit/scaffold-design-reconcile.md` 登记
- [ ] 机械可做项已在本模块 sprint 第一个 commit 内修掉（不留尾巴）
- [ ] 待 CY 决策项已显式列出，CY 拍板后再启动业务实施

**防御机制 — 任何 scaffold 后续改动 commit 前 3 问**（来自 memory
`feedback_design_scaffold_reconcile.md`）：

1. 我的实装是否和上游 design（ADR / engineering-spec / 引用模块 design）完全对齐？
2. 如果不对齐，我已经在 **scaffold 注释** OR **对应 design 文档** 里写明
   "这是简化决策，X 模块实施时扩齐到 Y 形态"？
3. 如有未建的 horizontal helper 影响**非当前模块**实施，已在 phase-gate
   登记 reconcile checkbox？

任一 No → 不许 commit。

---

### S2 注释强制模板（2026-05-07 时间维度盲区沉淀）

scaffold-design-reconcile.md S2（TenantContextProtocol）是"做对了"的范例——
注释清楚指明 M02/M20 各自补什么形态。但 S1/S4/S6 没做对，导致 6/7 漏写。

**强制规则**：任何 scaffold 简化决策的注释**必须含 4 字段**（缺任一 → 不许 commit）：

```python
# Scaffold 简化决策（YYYY-MM-DD）
# ① 决策内容：本期落地形态（含简化范围）
# ② 简化理由：为什么不直接做完整形态
# ③ 由哪个模块在何时扩齐到何形态（M? sprint）
# ④ 触发回写的具体动作：add 列 / 注入 concrete impl / data migration / 等
```

**正例**（`api/auth/tenant_filter.py` S2 模板）：

```python
"""...
本期（B2.4 scaffold）：表 project_members / projects / team_members 由 M02/M20
owns，尚未落地。helper 定义 Protocol + set_tenant_context 注入点；
M02 上线时注入"仅 project_members"实现，
M20 上线时注入 UNION 实现。
"""
# ① 决策内容：定 Protocol + 注入点，不实装具体过滤
# ② 简化理由：依赖表由 M02/M20 owns 尚未落地
# ③ 由 M02 sprint（注入 only project_members）/ M20 sprint（升级 UNION）扩齐
# ④ 触发回写动作：set_tenant_context(concrete_impl) 在 lifespan startup 注入
```

**反例**（M01 sprint 前 `api/auth/dependencies.py` AuthServiceProtocol 1 法 vs ADR-004 4 法）：注释只写"本期 B2 仅冻结接口"，缺 ②③④——M01 sprint 启动时只能猜。

---

### Reconcile pass 三栏强制分类（2026-05-07 时间维度盲区沉淀）

> **背景**：M02 sprint 启动首次 reconcile pass 时把"机械可做"+"待 CY 决策"+"已自我消解" 9 处混入一张表，9 处看似都像问题，5 处实是凑数。CY 元反思暴露分类失误。

**强制规则**：每模块 sprint 启动 reconcile pass 输出**必须分 3 栏**呈现，禁止混入一张表：

#### A 栏：机械可做

直接做、不让 CY 拍、commit 内修复完。例如：M01 sprint 的 S3（ErrorCode 重命名）/ S4（补 AppError 子类）/ S6（建 Mixin）/ S7（注释修正）。

#### B 栏：待 CY 决策

按 [`feedback_decision_transparency`](memory) A 模式呈现：候选 + 优缺点 + 3-5 月后果。例如：M01 sprint 的 S1 D1 决策（AuthServiceProtocol 三选一）/ M02 sprint 的 baseline-patch 退化路径（A/B/C）。

#### C 栏：已自我消解

scaffold 注释清楚 / 上一模块已处理 / 不阻塞本模块——只引用即可。例如：M01 sprint 的 S2（TenantContextProtocol scaffold 注释已指明 M02/M20 各自补什么）/ M02 sprint 的 S5（queue/ 不阻塞 M02）。

#### 禁混入信号

下列任一现象 = 反例：
- A/B/C 三类问题列在同一张表里
- 含"机械可做"的项里夹"需 CY 决策"
- 把"已自我消解"列为待办（导致虚胖问题清单）
- reconcile pass 输出无明确栏目分隔，CY 看不出哪些他要拍 / 哪些 AI 直接做

**违反 → reconcile pass 重做**。

---

## 闸门 2.6：M17 前置 — Queue Scaffold Mini-Sprint

M17 对话历程模块依赖 `api/queue/base.py:TaskPayload`（强制 user_id +
project_id 字段），但 Phase 2.0 B1-B10 未单列 queue scaffold（reconcile
S5）。M17 启动前必须 ✅：

- [ ] `api/queue/__init__.py` + `api/queue/base.py:TaskPayload` 基类落地
- [ ] 至少 1 个 dummy 子类化 + pytest 验证 user_id/project_id 强制
- [ ] ADR-002 § 1 形态与实装一致

可单独 commit 一次 mini-sprint，或 M02 sprint 顺手补（CY 拍）。

---

## 闸门 3：Phase 2.1 启动 → M02-M20

写**第二个业务模块**前必须 ✅：
- [ ] M01 用户系统 PR merge（探针验证整套流程跑得通）
- [ ] M01 tests.md critical path 100% PASS
- [ ] simplify-checklist 三 Agent 流水线在 M01 PR 上实际跑过一次

---

### 闸门 3.4 — Review 触发粒度规则（L1 总则，2026-05-07 立）

> **背景**：bypass log #1 配套承诺「M02 sprint 必须真跑三 Agent + simplify」是 **sprint 级**
> 承诺；simplify-checklist「≥50 行 OR ≥2 文件」是 **文件规模** 触发器；CY M02 启动 prompt
> 红线「每完成一类 endpoint 跑一次」是 **endpoint 级** 触发——三套口径粒度不同，
> M02 子片 1（纯 schema/无业务逻辑）首次撞上此缺口。
>
> 按 [`audit/time-dimension-blindspot-2026-05-07.md`](./audit/time-dimension-blindspot-2026-05-07.md)
> §9 教训 4 L1/L2/L3 节奏 + §10 元教训 1（类 1 实证驱动）补 L1 总则缺位。

**L1 总则**：

1. **sprint 必跑 ≥1 次**：每个业务模块 sprint 内必须至少跑 1 次完整 spec-reviewer +
   code-quality-reviewer + simplify-checklist 三维（满足 bypass log #1 配套承诺，
   不允许任一模块 sprint 0 次跑）
2. **触发器**：≥50 行 OR ≥2 文件改动触发（来自
   [`simplify-checklist.md`](../../ai-quality-engineering/10-项目/Prism/01-实现/simplify-checklist.md) 「何时跑」）
3. **触发例外（可合并到下游子片 / 可降级 self-审）**：

   a) **≥80% SKIP**：当本子片 ≥80% checklist 条目天然 SKIP（如纯 schema/migration
      子片对 simplify Prism 特有 22 条中 frontend/Server Action / 契约漂移类
      几乎全不命中），可合并到下游业务子片（service/router）一次性跑——
      合并必须在 L2 sprint review 计划段提前声明，sprint 中临时合并 = bypass log

   b) **Context budget pressure**（2026-05-09 M16 sprint bypass log #2 触发线达标
      后立规 / 累计绕 = 2 次后 review 触发本条修订）：当本会话同时满足
      以下两条件时，main agent self-审 + 子片 4 e2e 主动复制元教训 actionable
      可替代外部 reviewer：

      - usage 24h 信号 🔴 long-context（>150k context）+ subagent-heavy
        （>60% subagent 占比）同时存在
      - 本 sprint 前序子片已积累 ≥17 条 actionable 元教训主动写入子片 4 e2e
        （viewer 写 403 / cross-tenant 404 / cross-project node 404 / metadata
        字面 / write_event 异常传播 / 双层防御 / path mismatch / ErrorCode raise
        全覆盖等）

      **强制配套承诺**（缺一即违反 / 必须同 commit 写入 bypass log）：

      1. 下一 sprint 必须真跑 R1+R2 spawn subagent，不再 self-审
      2. 下一 sprint 启动子片 0 prep 必查"上一 sprint bypass 配套承诺是否兑现"
      3. 累计 self-审 sprint ≥2 个连续 → 触发对本 b 条目本身的 review

   c) **临时合并未提前声明** = bypass log（与 a 同处置）

**L2 sprint 级声明**：每业务模块 design 必有「Sprint Review 拆分计划」段
（位置：§14.5 或末尾），声明本 sprint「拆 N 次 review，每次覆盖哪些子片，
合并子片的 SKIP 比例理由」。**闸门 2.5 reconcile pass 必须验证该段存在**
（缺失 → reconcile pass 不通过）。

**L3 子选项（R-X5 风格留空待实证）**：
- "schema/migration 子片是否单独跑" — sprint 实证后回写
  `audit/m{XX}-pilot-template-validation.md` 加新章节
- "合并粒度边界（最多合并几个子片）"
- "已稳定基线扩展型 sprint 是否触发例外（如纯 baseline-patch 回扫）"

**违反**：跳过 L2 声明 / sprint 0 次跑 / 临时合并未提前声明 → 写
`design/99-comparison/phase-gate-bypass-log.md` 第 2 行 → 触发对闸门规则本身的 review。

---

## 闸门 4：后端 → 前端继承 ✅ 2026-05-09 全 ✅

启动 **Phase 2.2 前端继承 Prism** 之前：
- [x] M01-M05 + M20 后端代码 merge（OpenAPI 契约稳定）
- [x] `npm run codegen` 能从后端 OpenAPI 生成 TS 类型
- [x] 前端 api-client 至少 1 个真实 endpoint 调通（不是 mock）

---

## 闸门 5：上线前

启动 **Phase 2.3 集成验证 → 上线** 之前：
- [x] 后端 20 模块全 PR merge（M01-M20 全交付 / M09 superseded by M18）
- [x] 前端继承 Prism + M20 新增页面 PR merge（Phase 2.2 子片 0-5 全完成 2026-05-09）
- [ ] CI 全跑通（lint + test + build + migrate）— Phase 2.3 §8.0 工程规约 minimal 补完时落
- [ ] 工程规约 minimal 补完（03-cicd / 04-observability / 05-security）
- [ ] cross-sprint pool C 类 12 项 perf sprint 评估（接受 / 立专门 sprint / 推上线后）
- [ ] 集成 e2e（Playwright 跨 backend+frontend 真接通）
- [ ] 真业务 path 启用（pgvector + cross-sprint A 类 #21-#24 占位期残留解锁）

---

## AI 行为约束（防再跳）

**AI 准备做以下任一动作前**，**必须读 `00-roadmap.md` 当前 phase + 检查对应闸门**：
1. 生成「实现提示词」/「Phase N 启动包」
2. 写业务模块代码（M01-M20 任一）
3. 写 PR 计划 / 拆批策略
4. 给 CY 推荐"下一步做什么"

**自检 3 问**（任一 No → 不许出业务内容）：
1. 上一阶段所有 checkbox 都 ✅ 了吗？
2. 闸门所列文件/命令是否都存在/能跑？（用 ls / grep / Bash 验，不凭印象）
3. roadmap.md `last_updated` 是否反映真实进度？

任一 No → 告诉 CY「你在阶段 X，下一步是 Y（具体闸门项），先补完才能 Z」。

---

## CY 自我约束

CY 自己也可绕（这是你的项目你说了算）。但每次想绕时建议：
1. 写一句"为什么这次必须绕闸门 X" 到 `design/99-comparison/phase-gate-bypass-log.md`
2. 累计绕 ≥ 2 次 → 触发对闸门规则本身的 review（是不是闸门定错了）

---

## 关闸盲区立规（2026-05-12 Sprint 3.2 事后补）

### 闸门 4 Phase 2.2 关闸 ✅ 后发现的盲区

**现象**：Phase 2.2 子片 5 关闸 audit 时只验 `tsc --noEmit` + vitest + e2e PASS，未跑 `next build`。Sprint 3.1 CI 首次接通后 build job 暴露：
1. 3 处死引用 `@/actions/auth`（子片 2 删 auth flow 时未 grep 上游调用方：`use-page-context.ts` / `settings/page.tsx` / `overview/page.tsx`）
2. 88 个 tsc 错（含 drizzle-orm / @/db 死依赖，Prism 拷过来未清）

**根因**：`tsc --noEmit` 比 `next build` 宽松。next build 做完整 module resolution + 全页面遍历，能扫到 tsc `--noEmit` 漏的：
- 死 import（被 import 的 module 不存在）
- 跨页面间接引用错
- Turbopack 编译产物级 typecheck（next 自带的 type-check 比独立 tsc 严）

### 立规

🔴 **以下闸门 audit 必跑 `next build` 而非仅 tsc**：
- 任何前端关闸（Phase 2.2 / Phase 2.3 集成验证 / Phase 3+ / 上线前）
- 闸门 5 line 229 "CI 全跑通（lint + test + build + migrate）" — `build` 显式含 `next build` 不是 `tsc --noEmit`
- 未来子片关闸 audit 模板必含 step："`cd app && pnpm build` 必 PASS"

🔴 **删 export / 删 module 前必跑**：`grep -rn "@/actions/<deleted>" app/src/` — 验证 0 调用方再删

### STAR 素材标签
- **模式归类**：契约漂移 28% 模式的一个新子类——"AI 删上游 export 后未扫调用方"
- **量化**：1 次 audit 盲区 → 3 处死引用 + 88 tsc 错 + 1 个 sprint（3.2）单开补救
- **教训**：审计 ≠ 编译。审计跑 tsc 是 type 层验证，编译 next build 才扫到 module resolution + 全页面遍历盲区

---

## 维护

- 闸门规则不变 → 不更新本文件
- 闸门项需调整（如新增工程地基要求）→ AI 修订并标注变更原因
- 与 `00-roadmap.md` 不一致时 → 以本文件为准（闸门是真相，roadmap 是状态镜像）
