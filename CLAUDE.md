# CLAUDE.md — prism-0420 协作指南

## 项目定位

prism-0420 是 Prism 的 Shadow 项目——**同样的需求、不同的开发策略、最终都实现完整功能**。

- **需求**：完全复用 Prism F1-F20（对应 M1-M20）
- **策略**：设计前置 → AI 实现（vs Prism 边做边想）
- **目标**：数据化验证"设计前置方法论"的价值（对照 Prism 做 bug 数 / 速度 / 可追溯性对比）

GitHub：https://github.com/CY1005/prism-0420

## 当前阶段

**Phase 1：设计前置**（2026-04-20 起）—— 只做设计文档，不写代码。

**档位进度**（读 `design/README.md` 看最新）：
- ✅ 档位 A：架构骨架（8 工件完成）
- ⏳ 档位 B：工程规约决策（5 项，下一步）
- ⏳ 档位 C：模块详细设计（最小模块待选）

**Phase 2（未来）**：基于完整设计用 AI 实现 20 个模块。

## 协作规则（严格遵守）

**主文档**：`/root/cy/ai-quality-engineering/02-技术/架构设计/设计前置执行方法论-人机协作与对抗式Reviewer.md`

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
2. `design/README.md`（当前进度）
3. TaskList pending 任务（下一件事）
4. `design/adr/ADR-001-shadow-prism.md`（核心决策）
5. 开始工作前：告诉 CY "我看到进度是 X，下一件是 Y，可以开始吗？"

## 关键路径

- 设计文档：`/root/cy/prism-0420/design/`
- 方法论：`/root/cy/ai-quality-engineering/02-技术/架构设计/`（三篇）
- Pain-log：`/root/cy/ai-quality-engineering/00-GTD/日志/pain-log.md`
- TODO：`/root/cy/ai-quality-engineering/00-GTD/待办/TODO-index.md`
- Prism 代码参考：`/root/cy/prism/`（做对照用，不直接抄）
