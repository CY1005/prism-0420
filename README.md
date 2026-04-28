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

## 项目要解决什么问题

CY 的产品分析、技术研究、竞品调研、测试经验散落在 Notion、Obsidian、本地文档、聊天记录里——做产品分析 / 竞品对比 / 测试设计时找不齐、关联不上、版本变化无法追踪。

prism-0420（与 Prism 相同的产品定位）要做一个**围绕"功能模块"组织、AI 自动结构化、能持续沉淀产品理解的平台**——核心是通过记录去推动产品的理解和开发。区别于 Notion / Obsidian 的自由文档：

- **AI 按工作流自动拆解整理**——zip / git URL / .git 包导入，自动结构化
- **围绕"功能模块"组织**——不是文档目录，而是模块为中心的整合视角（左侧 280px 模块树 + 右侧档案页）
- **内置"产品评价"能力**——评价新需求：是否伪需求、有没有更好的实现方式、AI 自动分析涉及哪些已有模块
- **内置"测试沉淀"能力**——结构化沉淀测试文档：数据结构、测试 SQL、使用方法等

完整 PRD 见 [`design/00-architecture/01-PRD.md`](design/00-architecture/01-PRD.md)。

---

## 开发流程（设计前置 → AI 实现）

整个项目按 4 个 Phase 推进，每个 Phase 有明确的"完成定义"和闸门 checkbox（[`design/00-phase-gate.md`](design/00-phase-gate.md)）。

### Phase 0｜准备 ✅
仓库初始化、引入设计前置方法论、约定 AI 协作规则。

### Phase 1｜设计前置 ✅（2026-04-20 → 04-26，6 天完成）
**只产出文档，不写一行业务代码**。分 3 档（A → B → C）顺序推进，每档完成后启动独立 Reviewer Agent 做 3 轮批判式 audit（完整性 → 边界 → 演进）：

- **档位 A：架构骨架**（7 份）—— PRD / Context Diagram / Tech Stack / 分层架构 / 模块清单 / 设计原则 / 能力矩阵
- **档位 B：工程规约**（5 份）—— Engineering Spec / Quality / CI-CD / Observability / Security Baseline
- **档位 C：模块详设**（M01–M20 共 20 个）—— 每个模块含数据模型 / 状态机 / API 契约 / 测试设计

每个模块按"4 维必答"标注：Tenant 隔离 / 事务边界 / 异步模式（流式 SSE / 后台异步 / Queue）/ 并发控制（乐观锁）。

### Phase 2｜代码实现 ⏳（当前位置）
基于 Phase 1 设计文档用 AI 完整实现 20 个模块。分 4 个子阶段：

- **Phase 2.0 工程基线** ⏳ 25% ← 当前位置
  - A 决策（quality-spec / engineering-spec §13）已 accepted
  - B 代码（脚手架 / make dev / make test / make migrate / api/errors / api/auth / activity_log_service / tenant_filter）未起
- **Phase 2.1 业务模块** —— 后端 20 模块按依赖顺序实现，M01 用户系统作为探针模块跑通整套流程
- **Phase 2.2 前端继承 Prism** —— 大部分继承 Prism 现有前端，只改对接 API + 类型同步
- **Phase 2.3 集成验证** —— E2E 测试 + 上线准备

每个模块代码完成后跑**三 Agent 流水线**（Implementer + Spec Reviewer + Code Quality Reviewer）+ simplify 体检（Reuse / Quality / Efficiency 三维并行扫）。

### Phase 3｜数据对照 ⏳
对照 Prism 实跑数据，输出"bug 数 / 速度 / 可追溯性"对比报告，验证设计前置方法论的工程价值。

---

## 当前进度仪表盘（2026-04-29）

```
Phase 0 准备           ✅ ████████████████ 100%
Phase 1 设计前置       ✅ ████████████████ 100%   ← 2026-04-26 完成
Phase 2.0 工程基线     ⏳ ████░░░░░░░░░░░░  25%   ← 当前位置
Phase 2.1 业务模块     ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 2.2 前端继承     ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 2.3 集成验证     ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 3 数据对照报告   ⏳ ░░░░░░░░░░░░░░░░   0%
```

权威实时进度：[`design/00-roadmap.md`](design/00-roadmap.md)。

**Phase 1 总产出**：~5200 行设计文档，3 轮对抗式 Reviewer audit 全通过。

---

## 仓库结构（每个目录在做什么）

```
prism-0420/
├── README.md                            # 本文件
├── CLAUDE.md                            # AI 协作规则（人机协作三原则 + 阶段闸门 + 禁止模式）
├── HANDOFF-TO-CLAUDE.md                 # 跨 session 交接备忘
├── status-reconciliation-checklist.md   # 进度自洽校验清单（防 roadmap 与各文档状态打架）
└── design/                              # 所有设计产物（Phase 1 主体）
    ├── README.md                        # 设计文档总索引
    ├── 00-roadmap.md                    # 全项目进度仪表盘（权威 single source of truth）
    ├── 00-phase-gate.md                 # 阶段闸门规则（防跳过工程地基直接写业务代码）
    │
    ├── 00-architecture/                 # 档位 A：架构骨架（7 份）
    │   ├── 01-PRD.md                    #   极简 PRD（项目要解决什么、用户是谁、价值主张）
    │   ├── 02-context-diagram.md        #   系统上下文图（外部依赖 / 边界）
    │   ├── 03-tech-stack.md             #   技术选型（FastAPI + Next.js + PostgreSQL + Redis + arq）
    │   ├── 04-layer-architecture.md     #   分层架构（含三层鉴权防御）
    │   ├── 05-module-catalog.md         #   20 模块清单（按 Tenant / 事务 / 异步 / 并发 4 维分级）
    │   ├── 06-design-principles.md      #   5 条核心设计原则 + 多人架构 5 条约束清单
    │   └── 07-capability-matrix.md      #   横切能力 × 模块矩阵（哪个模块用 activity_log / 乐观锁 / idempotency_key）
    │
    ├── 01-engineering/                  # 档位 B：工程规约（5 份）
    │   ├── 01-engineering-spec.md       #   工程规约主文档（2300+ 行：目录结构 / 错误码 / 配置 / 日志 / Code Review 流程等）
    │   ├── 02-quality-spec.md           #   质量规范（pytest + vitest + Lint + Formatter）
    │   ├── 03-cicd-plan.md              #   CI/CD 计划
    │   ├── 04-observability-plan.md     #   可观测性计划（日志 / Metrics / Trace）
    │   └── 05-security-baseline.md      #   安全基线
    │
    ├── 02-modules/                      # 档位 C：20 模块详设（M01–M20）
    │   ├── README.md                    #   模块索引 + 阅读顺序建议
    │   ├── M01-user-account/            #   用户系统（注册/登录/鉴权）
    │   │   ├── 00-design.md             #     数据模型 + 状态机 + API + 流程
    │   │   ├── tests.md                 #     测试设计（critical path + 边界）
    │   │   ├── audit-report.md          #     Reviewer 3 轮 audit 记录
    │   │   └── audit-report-verify.md   #     Audit 修复后验证
    │   ├── M02-project/                 #   项目管理（项目+模板+维度+成员+AI 配置）
    │   ├── M03-module-tree/             #   功能模块树（左侧导航）
    │   ├── M04-feature-archive/         #   功能项档案页（核心业务页面，多人编辑+乐观锁）
    │   ├── M05-version-timeline/        #   版本演进时间线
    │   ├── M06-competitor/              #   竞品参考
    │   ├── M07-issue/                   #   问题沉淀
    │   ├── M08-module-relation/         #   模块关系图（React Flow）
    │   ├── M09-search/                  #   全局搜索
    │   ├── M10-overview/                #   项目全景图
    │   ├── M11-cold-start/              #   冷启动支持（CSV 导入 + 空状态引导）
    │   ├── M12-comparison/              #   功能对比矩阵
    │   ├── M13-requirement-analysis/    #   需求分析（AI，流式 SSE）
    │   ├── M14-industry-news/           #   行业动态（全局共享）
    │   ├── M15-activity-stream/         #   数据流转可视化（操作日志展示）
    │   ├── M16-ai-snapshot/             #   AI 生成快照（后台异步）
    │   ├── M17-ai-import/               #   AI 智能导入（Queue 异步 + 多表批量写）
    │   ├── M18-semantic-search/         #   语义搜索（pgvector + RRF 混合）
    │   ├── M19-import-export/           #   导入/导出（Markdown 报告）
    │   ├── M20-team/                    #   团队/空间（数据模型预留 space_id，本期不实现 UI）
    │   └── audit-report-batch*.md       #   分批 audit 总报告 + baseline patch
    │
    ├── 99-comparison/                   # Phase 3 输出：与 Prism 现状对照报告（当前空，等代码完成）
    │
    └── adr/                             # 架构决策记录（MADR 格式，5 个）
        ├── ADR-001-shadow-prism.md      #   Shadow 项目定位（完整 fork vs 简化版）
        ├── ADR-002-queue-consumer-tenant-permission.md   #   Queue Consumer 租户隔离方案
        ├── ADR-003-cross-module-read-strategy.md          #   跨模块读取策略（Service 直调 vs 事件总线）
        ├── ADR-004-auth-cross-cutting.md                  #   鉴权横切三层防御
        └── ADR-005-team-extension.md                      #   团队/空间扩展口（预留 space_id）
```

---

## 关键技术决策速览

来自 5 个 ADR 和 `06-design-principles.md`：

- **架构**：单 ORM（SQLAlchemy）+ OpenAPI 契约 + FastAPI + Next.js
- **Queue**：arq（异步 Redis Queue）
- **并发**：乐观锁（version 字段）
- **Tenant 隔离**：Queue payload 带 user_id + project_id，Worker 端二次校验
- **事务边界**：统一在 Service 层
- **权限防御三层**：Server Action session / Router 粗粒度 / Service 细粒度
- **空间**：本期不引入"空间"概念，预留 `space_id` 扩展口

5 条核心设计原则：

1. SQLAlchemy 是 schema 唯一真相源
2. 分层严格，禁止跨层调用
3. 接口 Contract First（OpenAPI）
4. 状态机必须显式定义
5. 多人架构 4 维必答（Tenant / 事务 / 异步 / 并发）

---

## 人机协作方式

整个 Phase 1 由 CY 与 AI 配合完成，遵守 3 条核心原则（详见 [`CLAUDE.md`](CLAUDE.md)）：

1. **CY 出骨架，AI 做质疑者**：业务/产品/数据/状态由 CY 决策，AI 提候选 + 质疑 + 填细节
2. **决策透明度**：每个技术建议必须给业务场景 + 完整优缺点 + 3-5 月后果，禁止简短推荐
3. **对抗式 Reviewer**：每个档位完成后启动独立 Agent 做 3 轮批判式 review（完整性 → 边界 → 演进），Reviewer 不附和、独立读文件判断

---

**仓库**：https://github.com/CY1005/prism-0420
**对照原项目**：https://github.com/CY1005/prism
