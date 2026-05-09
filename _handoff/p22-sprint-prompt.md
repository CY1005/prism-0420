---
title: Phase 2.2 前端继承 Prism — sprint 启动提示词
status: ready
owner: CY
created: 2026-05-09 (M-CLEANUP sprint 关闸 + ADR-001 §6 sanction 后预录)
phase: Phase 2.2 / 拷贝继承 + 改 API + codegen / 估 1-1.5 周
purpose: CY 开新 Claude session → 直接复制下方代码块全文粘贴执行。
---

# Phase 2.2 sprint 启动提示词

> **使用方法**：CY 开新 Claude session → 直接复制下方代码块全文粘贴执行。

```
继续 prism-0420 Phase 2.2 前端继承 Prism（拷贝 /root/prism/web → 改 API 接 prism-0420
后端 + M20 团队页新写 / ADR-001 §6 已 sanction）。

状态快照（已 commit + push 到 origin/main）：
- Phase 2.0 工程基线 ✅ 100%
- Phase 2.1 业务模块 ✅ 100%（M01-M08+M10-M20 全交付 / M09 superseded by M18）
- M-CLEANUP sprint ✅ 完成（49 → 34 STILL_PUNT / B 类真漏洞清完 / 9 commits）
- ADR-001 §6 前端继承策略 sanction（CLAUDE.md L135 路径修正 + 拆后端/前端两条）
- baseline: 1619 PASS / R13-1 139 / L12+L13+R14 全过 / ruff 净
- 闸门 4 启动条件全 ✅（M01-M05+M20 后端 merge / OpenAPI 契约稳定 / B 类真漏洞 0 项）

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md（L135 已修 / 后端不抄 / 前端可拷改）
2. design/adr/ADR-001-shadow-prism.md §6 前端继承策略（v3 修订 / 6.1 决策 6.2 理由
   6.3 影响 6.4 与 §预设 3 关系 6.5 修订动作）
3. design/00-roadmap.md §7 Phase 2.2 前端继承 Prism + 改造（§7.1 继承范围决策 / §7.2
   继承 + 改造 / §7.3 M20 团队页新写）
4. design/00-phase-gate.md 闸门 4（启动条件已全 ✅）+ 闸门 5（上线前 / 暂不触发）
5. _handoff/cross-sprint-punt-pool.md 状态分布快照段（M-CLEANUP 49→34 / 5 类 A/B/C/D/E
   归类 / D 类 #3+#15 IssueResponse/DimensionResponse join 字段已 schema 预留 default=None）
6. design/audit/m-cleanup-sprint.md（cleanup 元贡献 + Phase 2.2 启动条件复评 + SR-CLEANUP-3
   立规候选：标 ✅ DONE 必须 e2e 字面断言新行为防假覆盖）
7. /root/prism/web/（继承基底 / Next.js 16 + React 19 + Tailwind 4 + shadcn / 18 actions +
   19+ components + 7 services / 含 teams.ts + app/teams/[teamId]/page.tsx）
8. memory：feedback_subagent_sprint / feedback_design_first / feedback_self_decide_no_ask /
   feedback_decision_transparency / feedback_completion_audit / feedback_usage_budget v3 /
   feedback_code_first（前端代码改前必读真实代码不凭印象）

启动期：
- 闸门 2.5 reconcile pass（A/B/C 三栏 / B 栏穷举锁规 / B 栏=0 时禁列）
- bypass log #2 配套继续 ✅（M16 bypass + M17/M18/M19/M20 + M-CLEANUP 真跑 / 不复位累计
  触发线 / 第 3 次触发闸门 3.4 L1 review）
- 评估 Phase 2.2 形态特殊性（前端继承 + 改造 / 不是新模块 design 前置 / R1+R2 范式是否
  适用前端模块需重新评估）
- ADR-001 §6.1 字面 inventory：可继承（components/ + app/ 路由 + lib/ + contexts/ + UI 库）
  + 必改（services/* HTTP client → fetch prism-0420 FastAPI / actions/* Server Actions
  → call prism-0420 API / db/* drizzle 删）+ 新写（M20 团队页 shadcn pattern）

Phase 2.2 子片拆分预期（5+ 子片 / 估 1-1.5 周 / complexity=high）：
- 子片 0 prep：拷贝 /root/prism/web → app/ 选定子集 + 改 package.json deps（删 drizzle /
  next-auth / postgres / bcryptjs；保 next 16 / react 19 / shadcn / tailwind 4）+ 加
  codegen 工具（推荐 openapi-typescript / 或 orval 含 react-query hooks）
- 子片 1：codegen 接通（FastAPI OpenAPI export → app/src/types/ 自动生成 TS types）+
  http-client 改 API_BASE_URL 指向 prism-0420 FastAPI + auth header 走 Bearer JWT（不再
  next-auth session）
- 子片 2：auth flow 改造（M01 user login / register / refresh 走 prism-0420 /api/auth
  endpoints / 删 next-auth / 加 JWT cookie storage 或 localStorage）+ 1 个 e2e 验证 login
- 子片 3：核心页面改造批量（projects 列表 / 项目详情 / 维度档案 / 模块树 / 竞品 / 问题）
  改 Server Actions 调 prism-0420 API + 错误处理改 prism-0420 ErrorCode 范式
- 子片 4：M20 团队页新写（Prism 无 / app/teams/[teamId]/page.tsx + components 新建 /
  shadcn pattern / R-X3 owner+admin+member UI）
- 子片 5：D 类 #3+#15 真装配（IssueResponse + DimensionResponse join 字段 / 后端 DAO
  selectinload + ORM relationships + router 装配填充 / e2e 字面断言 join 字段在响应内）+
  关闸（design 回写 + audit/p22-pilot-template-validation.md + handoff §0 + roadmap
  Phase 2.2 100% 收官 + 闸门 5 启动条件评估）

R1+R2 范式（前端模块重新评估）：
- 前端形态与后端不同 / R1=3 subagent 并行（spec+quality + reuse + quality+efficiency）+
  R2=1 合并 endpoint 单审范式可能不直接适用 / 评估子片 0 prep 时拍是否调整为：
  - R1 = 1 reuse subagent（验证 Prism web 拷贝是否覆盖既有 UI / DRY / 命名规约）
  - R2 = 1 spec subagent（验证 prism-0420 FastAPI OpenAPI vs 前端调用契约一致 / 类型同步）
- 或保持 R1=3+R2=1 范式（与后端对照实验完整度对齐）/ 但内容维度调整

红线（M-CLEANUP 沉淀 + Phase 2.2 形态特殊）：
- ADR-001 §6 字面：后端不抄 Prism 源码 / 前端 UI 可拷改 / 拷贝时必须改 API client +
  删 drizzle ORM + auth flow 重写
- SR-CLEANUP-3：标 ✅ DONE 必须 e2e 字面断言新行为（防假覆盖 / monkeypatch 反 false-positive
  范式应用到前端 e2e）
- 元教训 #19：tests ↔ design ↔ exceptions.py 三方 status code 字面同步（前端类型同步
  时 codegen 自动生成 TS types 等价对账）
- viewer 写所有写端点 403：前端等价范式 = 路由守卫 + UI disabled 状态字面验
- 闸门 4 启动条件复读：M01-M05+M20 后端 merge ✅ / OpenAPI 契约稳定 ✅ / npm run codegen
  准备（子片 0 prep 接通）/ 前端 api-client 至少 1 个真实 endpoint 调通（子片 1）

Phase 2.2 形态特殊性（vs Phase 2.1 后端 own sprint）：
- 前端是"继承 + 改造" / 不是 design-first 全新写
- design/02-modules/ 不需要新建前端模块详设（ADR-001 §6.3 明示）
- shadow 对照实验仅后端有效 / 前端无对照数据点 / Phase 3 报告范围已缩
- baseline 1619 PASS 是后端 / 前端 vitest 测试是另一套（app/package.json npm test）

启动注意：
1. usage_budget v3 单会话 $10 上限 / >$15 强制开新会话；Phase 2.2 估 1-1.5 周需多 session
2. 每子片间 commit；前端改完每页面手测过一遍（CLAUDE.md 字面"关键交互冒烟测试"）
3. 1619 PASS 后端 baseline 不变 / 前端 vitest 独立基线 / 不串
4. 子片 0 prep 必决策：codegen 工具选型（openapi-typescript vs orval / B 栏决策 /
   feedback_decision_transparency A 模式呈现）
5. ADR-001 §6.5 字面：未来 Phase 2.2 启动时引用 §6 / 闸门 4 启动条件评估时复读 §6 确认范围

任务起点：进入启动期 reconcile pass + bypass log #2 配套继续 + Phase 2.2 形态特殊性评估 +
codegen 工具选型 B 栏 → 子片 0 prep（拷贝 + 删 drizzle + 加 codegen）→ 子片 1 → ...
```

---

## 子片拆分备忘（Phase 2.2 完整路线）

| 子片 | 范围 | 估时 | 依赖 |
|------|------|------|------|
| 0 prep | 拷 /root/prism/web → app/ + 改 package.json deps + 加 codegen 工具 + 删 drizzle/next-auth | 0.5 天 | ADR-001 §6 / 闸门 4 |
| 1 codegen + http | OpenAPI → TS types 接通 + http-client API_BASE 改 + Bearer JWT auth header | 1 天 | 子片 0 |
| 2 auth flow | M01 login/register/refresh 走 prism-0420 /api/auth + JWT 存储 + 1 e2e | 0.5 天 | 子片 1 |
| 3 核心页面 | projects/dimension/node/competitor/issue 5+ 页面改 API + actions 重写 | 3-4 天 | 子片 2 |
| 4 M20 团队页 | shadcn 新写 / 团队列表 + 详情 + 成员 + 转让 + 删除 + 项目归属 | 1-1.5 天 | 子片 3 |
| 5 D 类 join + 关闸 | IssueResponse + DimensionResponse 真装配 + handoff 同步 | 0.5 天 | 子片 4 |

**总估**：6.5-8 天（1-1.5 周）/ 多 session 完成 / 单 session 约 2 个子片。

---

## CY 决策点（B 栏 / 启动期必拍）

| # | 决策点 | 候选 | 推荐 |
|---|--------|------|------|
| 1 | codegen 工具 | A openapi-typescript（仅 types）/ B orval（types + react-query hooks）/ C openapi-generator-cli（多语言通用）| **A**（最轻量 / 不强制 react-query 范式 / Prism 已有自己 fetch 范式 / 与 ADR-001 §6 "改 API client" 路径一致）|
| 2 | auth 存储 | A localStorage（简单 / XSS 风险）/ B httpOnly cookie（安全 / 跨域配置复杂）/ C 内存 + refresh token | **B**（生产级 / 与 prism-0420 后端 P3 refresh token 范式对齐）|
| 3 | drizzle 删除范围 | A 完全删（前端不要 ORM）/ B 保留作 type 推断工具 | **A**（前端走 codegen TS types / drizzle 是后端 ORM 不该在前端）|
| 4 | R1+R2 范式 | A 保持 R1=3+R2=1 / B 调整为 R1=1 reuse + R2=1 spec | 启动期评估前端形态后拍（建议 B / 前端继承非 design-first） |

last_updated: 2026-05-09
