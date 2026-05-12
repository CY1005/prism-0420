# Prism-0420

> [Prism](https://github.com/CY1005/prism.git) 的 Shadow 项目——**同样的需求、不同的开发策略、最终都要实现完整功能**。
> 用来数据化验证「设计前置 → AI 实现」相对于「VibeCoding 边做边想」的工程价值。

---

## 一句话定位

| | Prism（原项目） | prism-0420（Shadow） |
|---|---|---|
| **需求范围** | F1–F20（20 个功能） | M1–M20（完全对应，不缩水）|
| **开发策略** | VibeCoding，边做边想 | 设计前置（架构 + 20 模块详设）→ AI 实现 |
| **已知结果** | 13 天到"测试通过/可上线"水位；23 fix commits | 23 天到同水位；**14 fix commits（减 39% bug）** |
| **Phase 3 STAR** | 对照基线 | v0.3 数据已落地（详见下方"关键数据"段）|

详细决策见 [`design/adr/ADR-001-shadow-prism.md`](design/adr/ADR-001-shadow-prism.md)。

---

## 当前状态（2026-05-12）

```
Phase 0 准备           ✅ ████████████████ 100%
Phase 1 设计前置       ✅ ████████████████ 100%   2026-04-26 完成
Phase 2.0 工程基线     ✅ ████████████████ 100%   2026-05-05 一日完成
Phase 2.1 业务模块     ✅ ████████████████ 100%   M01-M08+M10-M20 全交付（M09 superseded by M18）
Phase 2.2 前端继承     ✅ ████████████████ 100%   7 子片 / Prism 前端继承 + M20 团队页新写
Phase 2.3 集成验证     ✅ ████████████████ 100%   tsc 88→0 / next build PASS / pytest 1643 PASS
Phase 3 数据对照报告   🟢 ██████░░░░░░░░░░ v0.3   同水位 STAR 数据已落地
```

**真实进度权威源**：[`design/00-roadmap.md`](design/00-roadmap.md)（每次变化必更新）。

**当前活跃 sprint**：dogfooding 全功能测试 sprint（5-phase / 8-agent 流水线 / 详见 [`_handoff/dogfooding/progress.md`](_handoff/dogfooding/progress.md)）。M01 P1 pilot 已 ✅（127 testpoints）；剩 20 模块 + cross-cutting 在跑。

---

## Phase 3 关键数据（v0.3）

同到达"测试通过 / 可上线"水位的对照：

| 维度 | prism-0420（设计前置）| prism v1（VibeCoding）|
|---|---|---|
| **时间** | 23 天 | 13 天 |
| **Fix commits** | 14 | 23 |
| **bug 数减少** | **-39%** | 基线 |
| **时间代价** | **1.77x** | 1.0x |

> 🎯 **核心结论**：设计前置 + 三 Agent reviewer（Spec + Code Quality + Simplify）以 1.77x 的时间代价，换来 39% 的 fix commits 下降——bug 表面修复成本前移到设计期。完整方法论与逐模块数据见 [`design/99-comparison/`](design/99-comparison/)。

---

## 项目要解决什么问题

CY 的产品分析、技术研究、竞品调研、测试经验散落在 Notion、Obsidian、本地文档、聊天记录里——做产品分析 / 竞品对比 / 测试设计时找不齐、关联不上、版本变化无法追踪。

prism-0420（与 Prism 相同的产品定位）要做一个**围绕"功能模块"组织、AI 自动结构化、能持续沉淀产品理解的平台**：

- **AI 按工作流自动拆解整理**——zip / git URL / .git 包导入，自动结构化
- **围绕"功能模块"组织**——不是文档目录，而是模块为中心的整合视角（左侧 280px 模块树 + 右侧档案页）
- **内置"产品评价"能力**——评价新需求是否伪需求、有更好实现方式吗、AI 自动分析涉及哪些已有模块
- **内置"测试沉淀"能力**——结构化沉淀测试文档：数据结构、测试 SQL、使用方法等
- **语义搜索 + AI 智能导入**（M18 pgvector / M17 arq Queue 异步）

完整 PRD 见 [`design/00-architecture/01-PRD.md`](design/00-architecture/01-PRD.md)。

---

## 快速上手

依赖：Python 3.12 + Node 22 + pnpm + uv + Docker。

```bash
# 1. 启动本地依赖（PG 16 + pgvector + Redis 7，绑 127.0.0.1）
make up

# 2. 后端依赖 + 数据库迁移
make install
make migrate

# 3. 启动后端（FastAPI :8000）
make dev

# 4. 启动前端（另一终端，Next.js :3000）
make web

# 测试 / lint
make test       # pytest（1500+ tests）
make web-test   # vitest + playwright
make check      # ruff lint + pytest
make hooks      # 安装 pre-commit
```

`.env.example` 是模板（默认值与 docker-compose 一致），复制为 `.env` 后即可跑。

---

## 开发流程（设计前置 → AI 实现）

整个项目按 4 个 Phase 推进（[`design/00-phase-gate.md`](design/00-phase-gate.md)）：

### Phase 0 准备 ✅
仓库初始化、引入设计前置方法论、约定 AI 协作规则。

### Phase 1 设计前置 ✅（2026-04-20 → 04-26，6 天完成）
**只产出文档，不写一行业务代码**。分 3 档（A → B → C）顺序推进，每档完成后启动独立 Reviewer Agent 做 3 轮批判式 audit：

- **档位 A 架构骨架**（7 份）—— PRD / Context Diagram / Tech Stack / 分层架构 / 模块清单 / 设计原则 / 能力矩阵
- **档位 B 工程规约**（5 份）—— Engineering Spec / Quality / CI-CD / Observability / Security Baseline
- **档位 C 模块详设**（M01–M20 共 20 个）—— 每个模块含数据模型 / 状态机 / API 契约 / 测试设计

总产出 ~5200 行设计文档，3 轮对抗式 Reviewer audit 全通过。

### Phase 2 代码实现 ✅（2026-05-05 → 05-12）
基于 Phase 1 设计用 AI 完整实现 20 个模块 + 前端继承 + 集成清债：

- **Phase 2.0 工程基线** ✅ B1-B10 全跑通（FastAPI / docker-compose / Alembic / structlog / Next.js / AppError / Auth JWT / activity_log / tenant_filter / 测试 fixtures）
- **Phase 2.1 业务模块** ✅ M01-M08 + M10-M20（M09 superseded by M18 语义搜索）
- **Phase 2.2 前端继承** ✅ 7 子片 / 拷 Prism `app/` 基底 + shadcn + openapi-typescript codegen + M20 团队页新写
- **Phase 2.3 集成验证** ✅ cleanup S1+S3+S4+B+A+C+D 全完 / tsc 88→0 / next build PASS / pytest 1643 PASS / CI 6/6 绿

每个模块走**三 Agent 流水线**（Implementer → R1 Spec Reviewer → R2 Code Quality Reviewer）+ Simplify 体检（Reuse / Quality / Efficiency）。

### Phase 3 数据对照 🟢 v0.3
对照 Prism 实跑数据，输出"bug 数 / 速度 / 可追溯性"对比报告。v0.3 同水位 STAR 已落地；v1 完整报告等 dogfooding sprint 收尾后产出。

---

## 仓库结构

```
prism-0420/
├── README.md                            # 本文件
├── CLAUDE.md                            # AI 协作规则（人机协作三原则 + 阶段闸门 + 禁止模式）
├── Makefile                             # make up / install / migrate / dev / test / web / web-test / hooks
├── docker-compose.yml                   # PG 16 + pgvector + Redis 7（绑 127.0.0.1）
├── pyproject.toml                       # uv 包管理 + ruff + pytest 配置
├── uv.lock                              # 依赖锁
├── alembic.ini                          # 数据库迁移配置
├── .env.example                         # 环境变量模板
├── .pre-commit-config.yaml              # ruff + prettier + eslint + ci-lint hooks
│
├── api/                                 # 后端（FastAPI + SQLAlchemy + asyncpg）
│   ├── main.py / cli.py                 #   入口
│   ├── auth/                            #   JWT + require_user + tenant_filter + check_project_access
│   ├── core/                            #   配置 / DB session / structlog / SYSTEM_USER
│   ├── errors/                          #   AppError + ErrorCode（139 codes）+ middleware
│   ├── models/                          #   SQLAlchemy 模型（唯一 schema 真相源）
│   ├── dao/ services/ routers/ schemas/ #   分层（严禁跨层调用）
│   ├── queue/                           #   arq Worker + Tenant 二次校验
│   ├── cron/                            #   embedding backfill + dead-letter 清理
│   └── ws/                              #   M17 WebSocket endpoint（AI 导入进度）
│
├── app/                                 # 前端（Next.js 16 + React 19 + TS + Tailwind 4 + shadcn）
│   ├── src/                             #   pages / components / actions / lib（含 openapi-typescript codegen）
│   ├── e2e/                             #   Playwright（含 dogfooding 子目录占位）
│   └── openapi.json                     #   codegen 输入（gitignored / scripts/export_openapi.py 产）
│
├── migrations/                          # Alembic（async + initial baseline + 20 模块 migrations）
│
├── tests/                               # 后端 pytest（1500+ tests / async db_session + NESTED savepoint per-test）
│   ├── integration/                     #   集成测试
│   └── perf/                            #   性能基线（C7：1000 project / P95）
│
├── scripts/                             # 工具脚本
│   ├── ci-lint.sh                       #   R13-1 ErrorCode↔AppError parity + R14 过去式守护 + L12/L13
│   ├── export_openapi.py                #   导出 openapi.json 给前端 codegen
│   ├── phase3_data_collector.py         #   Phase 3 STAR 数据收集
│   ├── seed_dimension_types.py          #   8 维度 dev seed（解锁 dogfooding）
│   └── seed_e2e_admin.py
│
├── _handoff/                            # 跨 session 接力（详见 _handoff/INDEX.md）
│   ├── INDEX.md                         #   全 handoff 文件索引 + 状态枚举
│   ├── cross-sprint-punt-pool.md        #   跨 sprint Punt 池 + 真漏洞表 + 元发现集
│   ├── dogfooding/                      #   ★ 当前活跃 sprint（progress.md + plan + prompts/）
│   ├── phase23-integration-cleanup-prompts.md  # Phase 2.3 cleanup S1-S10 prompts（2026-05-12 跑完）
│   └── _archive/                        #   📦 已完成 sprint 历史 prompt（详见 _archive/README.md）
│
└── design/                              # 所有设计产物
    ├── README.md                        # 设计文档总索引
    ├── 00-roadmap.md                    # ★ 全项目权威进度仪表盘
    ├── 00-phase-gate.md                 # 阶段闸门规则
    ├── 00-architecture/                 # 档位 A：架构骨架 7 份
    ├── 01-engineering/                  # 档位 B：工程规约 5 份
    ├── 02-modules/                      # 档位 C：M01–M20 详设 + 批 audit + baseline-patch
    ├── adr/                             # 5 个 ADR（Shadow 定位 / Queue 租户 / 跨模块读 / Auth 横切 / 团队扩展）
    ├── audit/                           # 反向 audit 报告（time-dimension / p22-pilot 等）
    ├── 99-comparison/                   # ★ Phase 3 数据对照报告（v0.3 同水位 STAR）
    └── _archive/                        # 历史快照（已过时的早期文档）
```

---

## 关键技术决策速览

来自 5 个 ADR 和 `06-design-principles.md`：

- **架构**：单 ORM（SQLAlchemy）+ OpenAPI Contract First + FastAPI + Next.js
- **Queue**：arq（异步 Redis Queue）
- **并发**：乐观锁（version 字段）
- **Tenant 隔离**：Queue payload 带 user_id + project_id，Worker 端二次校验
- **事务边界**：统一在 Service 层
- **权限防御三层**：Server Action session / Router 粗粒度 / Service 细粒度
- **空间**：本期不引入"空间"概念，预留 `space_id` 扩展口（M20 团队落地时 rename → `team_id`）

5 条核心设计原则：

1. SQLAlchemy 是 schema 唯一真相源
2. 分层严格，禁止跨层调用
3. 接口 Contract First（OpenAPI）
4. 状态机必须显式定义
5. 多人架构 4 维必答（Tenant / 事务 / 异步 / 并发）

---

## 人机协作方式

整个项目由 CY 与 AI 配合完成，遵守 3 条核心原则（详见 [`CLAUDE.md`](CLAUDE.md)）：

1. **CY 出骨架，AI 做质疑者**：业务/产品/数据/状态由 CY 决策，AI 提候选 + 质疑 + 填细节
2. **决策透明度**：每个技术建议必须给业务场景 + 完整优缺点 + 3-5 月后果，禁止简短推荐
3. **对抗式 Reviewer**：每个档位完成后启动独立 Agent 做 3 轮批判式 review（完整性 → 边界 → 演进），Reviewer 不附和、独立读文件判断

进入 Phase 2 后追加**三 Agent 流水线** + **Simplify 体检**（Reuse / Quality / Efficiency 三维并行扫）。

---

**仓库**：https://github.com/CY1005/prism-0420
**对照原项目**：https://github.com/CY1005/prism
**真实进度权威源**：[`design/00-roadmap.md`](design/00-roadmap.md)
**新 session 接力**：[`_handoff/INDEX.md`](_handoff/INDEX.md)
