# Prism-0420

> [Prism](https://github.com/CY1005/prism.git) 的 Shadow 项目——**同样的需求、不同的开发策略、最终都要实现完整功能**。
> 用来数据化验证「设计前置 → AI 实现」相对于「VibeCoding 边做边想」的工程价值。

---

## 一句话定位

| | Prism（原项目） | prism-0420（Shadow） |
|---|---|---|
| **需求范围** | F1–F20（20 个功能） | M1–M20（完全对应，不缩水） |
| **开发策略** | VibeCoding，边做边想 | 设计前置（架构 + 20 模块详设） → AI 实现 |
| **已知结果** | 11 天做完功能；之后持续治理代码债 | 设计耗时 6 天（已完成）；实现期望显著低返工 |
| **最终对照** | — | Phase 3 输出"bug 数 / 速度 / 可追溯性"数据对比 |

详细决策见 [`design/adr/ADR-001-shadow-prism.md`](design/adr/ADR-001-shadow-prism.md)。

---

## 当前状态（2026-04-29）

```
Phase 0 准备           ✅ 100%
Phase 1 设计前置       ✅ 100%   ← 已完成
Phase 2.0 工程基线     ⏳  25%   ← 当前位置（A 决策完成，B 脚手架未起）
Phase 2.1 业务模块     ⏳   0%
Phase 2.2 前端继承     ⏳   0%
Phase 2.3 集成验证     ⏳   0%
Phase 3 数据对照报告   ⏳   0%
```

**Phase 1 产出（送审主体）**：

- 7 份架构骨架文档（PRD / Context Diagram / Tech Stack / 分层架构 / 模块清单 / 设计原则 / 能力矩阵）
- 5 份工程规约（Engineering Spec / Quality / CI-CD / Observability / Security Baseline）
- **20 个业务模块**完整详设（M01–M20，每个模块含数据模型 + 状态机 + API + 测试设计）
- 5 个 ADR（架构决策记录，MADR 格式）
- 共 ~5200 行设计文档，3 轮对抗式 Reviewer audit 全通过

实时进度仪表盘：[`design/00-roadmap.md`](design/00-roadmap.md)

---

## 评审入口（推荐阅读顺序）

如果时间有限，按下面 3 个层次任选其一：

### 🟢 30 分钟版（评审"思路"）
1. 本 README
2. [`design/00-architecture/01-PRD.md`](design/00-architecture/01-PRD.md) —— 项目要解决什么问题
3. [`design/00-architecture/06-design-principles.md`](design/00-architecture/06-design-principles.md) —— 5 条核心设计原则
4. [`design/adr/`](design/adr/) —— 5 个 ADR，每个 5 分钟看完

### 🟡 2 小时版（评审"架构"）
追加：

5. [`design/00-architecture/04-layer-architecture.md`](design/00-architecture/04-layer-architecture.md) —— 分层 + 鉴权中间件
6. [`design/00-architecture/05-module-catalog.md`](design/00-architecture/05-module-catalog.md) —— 20 模块按复杂度分级（4 维标注：Tenant / 事务 / 异步 / 并发）
7. [`design/00-architecture/07-capability-matrix.md`](design/00-architecture/07-capability-matrix.md) —— 横切能力 × 模块矩阵
8. [`design/01-engineering/01-engineering-spec.md`](design/01-engineering/01-engineering-spec.md) —— 工程规约（2300+ 行，目录式阅读）

### 🔴 半天版（评审"模块详设"）
追加：在 [`design/02-modules/`](design/02-modules/) 任选 2-3 个模块对照看：
- **M04 功能项档案页**：核心业务页面，多人编辑 + 乐观锁
- **M17 AI 智能导入**：Queue 异步 + 多表批量写
- **M13 需求分析（AI）**：流式 SSE + AI Provider 抽象

---

## 关键设计决策（5 个 ADR，建议重点看）

| ADR | 主题 | 核心权衡 |
|---|---|---|
| [ADR-001](design/adr/ADR-001-shadow-prism.md) | Shadow 项目定位 | 完整 fork vs 简化版 → 选完整 fork（按多人架构设计，即使本期 1 用户） |
| [ADR-002](design/adr/ADR-002-queue-consumer-tenant-permission.md) | Queue Consumer 租户隔离 | Queue payload 带 user_id+project_id，Worker 端二次校验 |
| [ADR-003](design/adr/ADR-003-cross-module-read-strategy.md) | 跨模块读取策略 | Service 间直接调用 vs 事件总线 → 选 Service 直调（YAGNI） |
| [ADR-004](design/adr/ADR-004-auth-cross-cutting.md) | 鉴权横切 | 三层防御：Server Action session / Router 粗粒度 / Service 细粒度 |
| [ADR-005](design/adr/ADR-005-team-extension.md) | 团队/空间扩展口 | 不引入"空间"概念，预留 `space_id` 字段为未来留口 |

---

## 想请你重点评审的几个问题

> 我（CY）希望听到的不是"看起来不错"，而是"这里你想错了 / 这里有坑"。

1. **"设计前置 → AI 实现"这套打法本身**：在你看过的项目里，类似策略有什么常见死法？我现在最大的盲区是什么？
2. **20 模块的拆分粒度**（[模块清单](design/00-architecture/05-module-catalog.md)）：是切得太细、太粗、还是分类维度有问题？
3. **多人架构 4 维（Tenant / 事务 / 异步 / 并发）的强制标注**：这种"必答清单"式的约束，会不会在实际写代码时反而成为枷锁？
4. **Phase 2.0 工程基线（A 决策已 accepted，B 代码未起）**：现在的 [`engineering-spec.md`](design/01-engineering/01-engineering-spec.md) 2300+ 行——是必要的"工程地基"，还是过度设计的债务？
5. **横切能力做到第几层是合适的**（[capability-matrix](design/00-architecture/07-capability-matrix.md)）：activity_log、乐观锁、idempotency_key、tenant 过滤都做了——对一个 1 人项目（即使本期按多人架构设计）是不是太重？

任何"我直觉觉得这里有问题但说不上来"的反馈，都欢迎抛过来。

---

## 仓库结构

```
prism-0420/
├── README.md                          # 本文件
├── CLAUDE.md                          # AI 协作规则（评审无需看）
├── design/
│   ├── 00-roadmap.md                  # 全项目进度仪表盘
│   ├── 00-phase-gate.md               # 阶段闸门规则
│   ├── 00-architecture/               # 架构骨架（7 份）
│   ├── 01-engineering/                # 工程规约（5 份）
│   ├── 02-modules/                    # 20 模块详设（M01–M20）
│   ├── 99-comparison/                 # 与 Prism 现状对照报告（Phase 3 输出）
│   └── adr/                           # 架构决策记录（5 个）
└── status-reconciliation-checklist.md # 进度自洽校验清单
```

---

## 方法论背景（可选阅读）

本项目是「设计前置方法论」的实践载体。方法论本身的核心三原则：

1. **CY 出骨架，AI 做质疑者**：业务/产品/数据/状态由人决策，AI 提候选 + 质疑 + 填细节
2. **决策透明度**：每个技术建议必须给业务场景 + 完整优缺点 + 3-5 月后果，禁止简短推荐
3. **对抗式 Reviewer**：每个档位完成后启动独立 Agent 做 3 轮批判式 review（完整性 → 边界 → 演进）

如果你对这套人机协作方法论本身有兴趣，我可以单独发方法论文档过去。

---

**仓库**：https://github.com/CY1005/prism-0420
**对照原项目**：https://github.com/CY1005/prism
