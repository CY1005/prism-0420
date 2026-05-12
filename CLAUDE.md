# CLAUDE.md — prism-0420 协作指南

## 项目定位

prism-0420 是 Prism 的 Shadow 项目——**同样的需求、不同的开发策略、最终都实现完整功能**。

- **需求**：完全复用 Prism F1-F20（对应 M1-M20）
- **策略**：设计前置 → AI 实现（vs Prism 边做边想）
- **目标**：数据化验证"设计前置方法论"的价值（对照 Prism 做 bug 数 / 速度 / 可追溯性对比）

GitHub：https://github.com/CY1005/prism-0420

## 当前阶段

**Phase 3 数据对照 v0.3 落地 + dogfooding 全功能测试 sprint 进行中**（截至 2026-05-12）

**真实进度**（权威来源 `design/00-roadmap.md`，每次进度变化必须同步更新；以下仅快照，不替代 roadmap）：
- ✅ Phase 0 准备 100%
- ✅ Phase 1 设计前置 100%（2026-04-26 完成）
  - 档位 A 架构骨架 7 份 / 档位 B 工程规约 5 份 / 档位 C 模块详设 M01–M20 全交付 / 5 个 ADR
- ✅ Phase 2.0 工程基线 100%（2026-05-05）
- ✅ Phase 2.1 业务模块 100%（M01-M08+M10-M20 全交付 / M09 superseded by M18）
- ✅ Phase 2.2 前端继承 100%（7/7 子片，2026-05-09 完 / 揭露关闸盲区 #2 已立规）
- ✅ Phase 2.3 集成验证 100%（2026-05-12 cleanup S1+S3+S4+B+A+C+D 全完 / tsc 88→0 / next build PASS / pytest 1643 PASS / CI 6/6 绿）
- 🟢 **Phase 3 数据对照 v0.3** ← 当前位置
  - 同水位 STAR 数据已落地：prism-0420 23 天 / 14 fix vs prism v1 13 天 / 23 fix → 设计前置 + 三 Agent reviewer 减少 39% bug 硬实证；时间代价 1.77x
  - 下一步：6/8 + 6/15 工作笔记导入 → Phase 3 完整报告 v1
- 🟡 **dogfooding sprint 并行进行**（2026-05-12 起 / 当前活跃 sprint）
  - 接力点权威：`_handoff/dogfooding/progress.md`（每 session 起点必读）
  - 总 plan：`_handoff/dogfooding/00-plan.md`（5-phase / 8 agent / A 路径全跑）
  - P0 preflight ✅ / P1 testpoint 🟡 进行中（M01 pilot + 批 1+2 完，剩批 3-5 + cross-cutting）
  - P2-P5 待启（待 P1 完）

**下一件事**：见 `_handoff/dogfooding/progress.md` 起手段 + `design/00-roadmap.md` §1 仪表盘。历史 sprint prompt 在 `_handoff/_archive/`（详见 `_handoff/_archive/README.md`）。

## 协作规则（严格遵守）

**主文档**：`/root/workspace/projects/ai-quality-engineering/02-技术/架构设计/设计前置执行方法论-人机协作与对抗式Reviewer.md`

核心三原则：

1. **CY 出骨架，AI 做质疑者**
   - CY：业务、产品、数据、状态、价值判断
   - AI：提候选、质疑、细节填充、格式化
   - 不要替 CY 原创设计内容

2. **决策透明度**（见 memory `feedback_decision_transparency.md`）
   - 每个技术建议必须给：业务场景 + 实现例子 + 完整优缺点
   - 禁止简短推荐 / 引导性选择 / 隐瞒风险
   - 明确说"我倾向 X，但 Y 情况你可以选 Z"

3. **对抗式 Reviewer**
   - 每个档位完成后启动独立 Agent 做批判性 review
   - Reviewer 不附和，独立读文件判断
   - 三轮递进：完整性 → 边界 → 演进

## 阶段闸门（防跳过工程地基写业务代码）

🔴 **AI 准备生成「实现提示词」/「Phase N 启动包」/ 业务模块代码 / PR 计划 前必须**：
1. 读 [`design/00-roadmap.md`](./design/00-roadmap.md) 看真实进度（不凭印象）
2. 读 [`design/00-phase-gate.md`](./design/00-phase-gate.md) 看下一闸门 checkbox
3. 任一 checkbox 未 ✅ → 不出业务提示词，告诉 CY「你在阶段 X，下一步是 Y」

每次进度变化（决策落定 / PR merge / 闸门项打钩）→ AI 必须更新 `00-roadmap.md` 的进度仪表盘 + 对应行 + last_updated 字段。

## 一次一件事节奏

- 一次对话聚焦一个可交付小任务
- 完成后 commit + push + TaskUpdate completed
- 告诉 CY "完成了 X，下一件是 Y，继续吗？"
- 等 CY 明确"继续"才启动下一件

## 核心决策（已 accepted）

读 `design/adr/ADR-001-shadow-prism.md` 看完整决策。关键点：

- **架构**：单 ORM（SQLAlchemy）+ OpenAPI 契约 + FastAPI + Next.js
- **Queue**：arq（异步 Redis Queue）
- **并发**：乐观锁（version 字段）
- **Tenant 隔离**：Queue payload 带 user_id + project_id
- **事务边界**：Service 层
- **权限防御**：三层（Server Action session / Router 粗粒度 / Service 细粒度）
- **空间**：不引入"空间"概念，预留 space_id 扩展口

## 设计原则（5 条核心 + 5 条约束清单）

读 `design/00-architecture/06-design-principles.md`。核心原则：

1. SQLAlchemy 是 schema 唯一真相源
2. 分层严格，禁止跨层调用
3. 接口 Contract First（OpenAPI）
4. 状态机必须显式定义
5. 多人架构 4 维必答（Tenant / 事务 / 异步 / 并发）

**多人架构约束清单**（必须参考）：
- activity_log / 乐观锁 version / Queue payload tenant / idempotency_key / DAO 层 tenant 过滤

## 禁止模式（已踩过的坑）

- ❌ 简短推荐（"推荐 A"没有理由）
- ❌ 凭印象估时（必须 git-first 验证）
- ❌ 假完成声明（PRD accepted 但其他文件空模板）
- ❌ 原则稀释（>5 条等于没有）
- ❌ 异步模式混用同一 ✅（流式 / 后台 / Queue 要区分）

## Phase 2 代码落地时的合并前体检

进入 Phase 2 写代码后，每次完成一个模块、三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）通过 **之后**，commit **之前**，跑 simplify 体检。

**清单**：`/root/workspace/projects/ai-quality-engineering/02-技术/AI工具与工作流/Prism-simplify-checklist.md`

**三维并行**：派 3 个 subagent 分别扫
- 横向（Reuse）：跟仓库已有代码的关系
- 纵向（Quality）：通用 + Prism 特有坑（契约漂移 / 版本兼容 / 空状态 / 租户隔离 / 静默吞错 / Migration）
- 动态（Efficiency）：重复 I/O、N+1、useMemo 缺失等

**门槛**：改 ≥ 50 行或跨 ≥ 2 文件才跑。小改动主 AI 自扫。

**findings 处理**：false positive 记 `SKIP: ... — 理由：...`，不辩论。修完一句话总结。

**踩新坑就回流**：同一根因踩 ≥ 2 次 → 必须加清单新条目。

## 快速上手（新 session 读这个顺序）

1. 本文件（协作规则）
2. **`_handoff/INDEX.md`**（_handoff 全图索引）→ 当前活跃 sprint = dogfooding，接力点 `_handoff/dogfooding/progress.md`（旧 `next-session.md` 已归档到 `_handoff/_archive/`）
3. **`_handoff/cross-sprint-punt-pool.md`**（🔴 跨 sprint Punt 池总表 / 防"约定 M? sprint 处理但被遗忘"漂移 / 启动 reconcile 必查本 sprint 命中项 + 真漏洞 Top 10 + 高耦合触发点联动）
4. `design/00-roadmap.md`（**真实进度仪表盘——权威**）
5. `design/00-phase-gate.md`（下一闸门 checkbox）
6. TaskList pending 任务（下一件事）
7. `design/adr/ADR-001-shadow-prism.md`（核心决策）
8. 开始工作前：告诉 CY "我看到进度是 X，handoff 推荐 prompt 是 Y，要按这个跑还是切别的？"

## 关键路径

- 设计文档：`/root/workspace/projects/prism-0420/design/`
- 方法论：`/root/workspace/projects/ai-quality-engineering/02-技术/架构设计/`（三篇）
- Pain-log：`/root/workspace/projects/ai-quality-engineering/00-GTD/日志/pain-log.md`
- TODO：`/root/workspace/projects/ai-quality-engineering/00-GTD/待办/TODO-index.md`
- Prism 代码参考：`/root/prism/`（注意路径：不在 workspace/projects/ 下）
  - **后端**：做对照用，**不直接抄**（M01-M20 全设计前置独立写 / shadow 对照实验完整度仅后端）
  - **前端**：UI 可拷改（CY 喜欢现有 UI 设计 / 工作量妥协 / Phase 2.2 拷 `/root/prism/web/` 改 API 接 prism-0420 后端 + M20 团队页新写）
  - 详见 ADR-001 §6 前端继承策略
