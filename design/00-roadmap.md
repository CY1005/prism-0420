---
title: prism-0420 全项目 Roadmap + 进度 Checklist
status: living-doc
owner: CY
last_updated: 2026-05-09（M17 sprint 完成: 7 commit + R-X1 第二实例 + Queue 异步 pilot + WebSocket endpoint 首发 + L1+L2+L3 第十五次实证 / 闸门 2.5 三栏第十二次 B 栏 0 项实证 / R1=3 subagent 并行 + R2=1 合并 Opus（bypass log #2 配套已恢复）/ R-X1 helper compensation_session 第二 caller 零摩擦 / 元贡献 7 项 + sink 立规候选 3 项 + punt 池新增 4 项）
current_phase: Phase 2.1 进行中（M01-M08+M10+M11+M12+M13+M14+M15+M16+M17 完成；下一站 M18 语义搜索 / M09 superseded by M18）
---

# prism-0420 全项目 Roadmap

> **这是 single source of truth**。每次进度变化，AI 必须更新本文件。CY 想知道"我做到哪了"直接看这一份。

---

## 0. 项目定位重申

- **目标**：复用 Prism F1-F20 全部需求，用「设计前置 → AI 实现」策略**重新开发完整代码**
- **对照**：与 Prism 实跑做 bug 数 / 速度 / 可追溯性数据对比
- **前端策略**：**大部分继承 Prism 现有前端**（仅改对接 API + 类型同步），不重写
- **后端策略**：从 0 重写（设计已完整）

---

## 1. 当前位置仪表盘

```
Phase 0 准备     ✅ ████████████████ 100%
Phase 1 设计前置 ✅ ████████████████ 100%   ← 2026-04-26 完成
Phase 2.0 工程基线  ✅ ████████████████  100%  ← 闸门 2 全 ✅
Phase 2.1 业务模块  ⏳ █████████████████  85%  ← M01-M08+M10+M11+M12+M13+M14+M15+M16+M17 完成；下一步 M18 语义搜索（M09 superseded by M18）
Phase 2.2 前端继承  ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 2.3 集成验证  ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 3 数据对照   ⏳ ░░░░░░░░░░░░░░░░   0%
```

**上次更新**：2026-05-07（M01 探针完成 + 闸门 3 通过 / 第 3 项 bypass 已登记）

**下一步动作**：M02 项目管理 sprint（含 PROJECT_ARCHIVED ErrorCode F2.3）— 闸门 2.5 reconcile pass 启动

---

## 2. 全项目阶段总览

| Phase | 名称 | 估时（周）| 状态 |
|-------|------|---------|------|
| 0 | 准备（仓库+方法论引入）| 0.5 | ✅ |
| 1 | 设计前置 | 1（实际 6 天，前置 3 周）| ✅ |
| **2.0** | **工程基线（决策 + 代码）** | **0.5-1** | ⏳ 0% |
| 2.1 | 后端 20 模块 + 横切 17 模块 | 3-4 | ⏳ 0% |
| 2.2 | 前端继承 Prism + 改造 | 1-1.5 | ⏳ 0% |
| 2.3 | 集成 + E2E + 上线准备 | 0.5-1 | ⏳ 0% |
| 3 | 数据采集 + Prism 对照报告 | 1 | ⏳ 0% |

**预估总时长**：8-10 周 / 2-2.5 月（Phase 1 已耗 1 周完成 → 剩 7-9 周）

> 估算依据：单人 + AI 协作 + 每日 4-6 小时投入。前端继承显著压缩 Phase 2.2 时长。

---

## 3. Phase 0：准备 ✅

- [x] prism-0420 仓库建立（GitHub `CY1005/prism-0420`）
- [x] CLAUDE.md 协作规则
- [x] design/ 目录结构
- [x] 方法论 KB 引入（superpowers + Prism-simplify-checklist + 设计前置三篇）

---

## 4. Phase 1：设计前置 ✅（2026-04-20 → 2026-04-26）

### 4.1 档位 A 架构骨架（00-architecture/）

- [x] 01-PRD.md
- [x] 02-context-diagram.md
- [x] 03-tech-stack.md（Q1 ORM 单选 / Q5 Queue=arq）
- [x] 04-layer-architecture.md
- [x] 05-module-catalog.md
- [x] 06-design-principles.md（5 原则 + 5 约束清单）
- [ ] **07-capability-matrix.md draft → accepted**（残留，可延后到 Phase 2.0 末）

### 4.2 档位 B 工程规约（01-engineering/）

- [⚠️] 01-engineering-spec.md（A 档已填 + B 档已填 + **C 档 §13/§14/§15 未填** —— 推到 Phase 2.0）
- [x] **02-quality-spec.md**（accepted）
- [⚠️ accepted-minimal] **03-cicd-plan.md**（GitHub Actions 选型定 / 工作流文件 Phase 2.3 §8.0 补完）
- [⚠️ accepted-minimal] **04-observability-plan.md**（日志 stdout JSON 定 / 指标+告警+追踪 Phase 2.3 §8.0 补完）
- [⚠️ accepted-minimal] **05-security-baseline.md**（.env+gitignore 单人模式定 / 多人 prod 密钥 Phase 2.3 §8.0 补完）

### 4.3 档位 C 模块详细设计（02-modules/）

- [x] M01-M19（19 模块）
- [x] M20 团队（三轮 audit + 4 批修复 + Phase 1 sync 6 轮独立审 = 39 finding 全收敛）
- [x] baseline-patch-m18.md
- [x] baseline-patch-m20.md

### 4.4 ADR 决策

- [x] ADR-001 Shadow 项目（§预设 3 partial superseded by ADR-005）
- [x] ADR-002 Queue 消费者租户权限
- [x] ADR-003 跨模块读策略
- [x] ADR-004 Auth 横切
- [x] ADR-005 团队扩展

---

## 5. Phase 2.0：工程基线 ⏳ ← 你在这里

> **闸门**：本 Phase 全 ✅ 才能开 Phase 2.1。详见 [`00-phase-gate.md`](./00-phase-gate.md)。

### 5.1 A 阶段：4 项决策（半天）✅ **2026-04-26 完成**

- [x] **A1 测试策略**（02-quality-spec §3-4-5）
  - 后端 pytest / 前端 vitest / E2E 暂不做（推 Phase 2.3）/ DB 每用例 transaction rollback / 不设硬覆盖率门槛 + critical path 100% 是真门槛
- [x] **A2 Lint + Formatter + pre-commit**（02-quality-spec §1-2-6）
  - Python ruff（lint+format 一体）/ TS ESLint v9 + Prettier / pre-commit Python 包 / commit message 项目内约定
- [x] **A3 Code review 流程**（engineering-spec §13）
  - CY + 2 Agent / 三 Agent ≥50 行或 ≥2 文件触发 / 拒合并 6 项硬条件全选
- [x] **A4 CICD/可观测/安全占位决策**（03/04/05-spec 关键决策栏）
  - GitHub Actions / stdout JSON + structlog / .env + .env.example + .gitignore + AES-256-GCM

### 5.2 B 阶段：10 项工程基线代码（2-3 天）

- [x] **B1 仓库脚手架**（api/ + app/ + .env.example + Makefile + README Quick Start）
  - [x] B1.1 最小 FastAPI（pyproject.toml + Makefile + api/main.py + tests/test_health.py，2026-05-05 commit `0bafb20`）
  - [x] B1.2 docker-compose（pg16+pgvector / redis7，标准 5432/6379；老 v1 已 stop）+ config（pydantic-settings）+ /readyz 双探针，2026-05-05 commit `a08311b` + 端口归位 `b823461`
  - [x] B1.3 Alembic（async 模板 + env.py 接 settings + initial baseline b1c62870faa5）+ structlog JSON（lifespan startup/shutdown 日志），2026-05-05 commit `c4c46e4`；日志统一含 uvicorn 全 JSON commit `1c7fd5f`
  - [x] B1.4 Next.js 16 + React 19 + TS + Tailwind 4 + ESLint 9 + vitest 4 + Testing Library + prettier + pre-commit 4 hooks（ruff/prettier/eslint），2026-05-05 commit `23b0385`
- [ ] **B2 Docker Compose**（PG 16 + pgvector + Redis + init-db / make up）—— 并入 B1.2
- [ ] **B3 SQLAlchemy base + Alembic init**（base.py + Mixin + session.py + alembic.ini + 跑通 base revision）—— 并入 B1.3
- [x] **B4 FastAPI 启动框架**（main.py + /health + uvicorn 跑起来）—— B1.1 已含；config + 中间件留 B1.2/B5
- [x] **B5 AppError + 错误中间件**（codes + 6 子类 + middleware + 8 tests，2026-05-05 commit `6f7949a`）
- [x] **B6 Auth 基础**（JWT encode/decode + HMAC P2 签名 + require_user Depends + AuthServiceProtocol 注入点 + 11 tests，2026-05-05 commit `49f6eac`；Auth.js v5 Redis adapter 留 Phase 2.2 前端做）
- [x] **B7 activity_log 写入封装**（write_event stub 走 structlog；M15 实装时换 INSERT，调用方接口稳定，2026-05-05 commit `e140306`）
- [x] **B8 tenant_filter helper**（user_accessible_project_ids_subquery + TenantContextProtocol 注入点；M02/M20 上线时注入 concrete 实现，2026-05-05 commit `8e0be2e`）
- [x] **B9 测试 fixtures**（async db_session + NESTED savepoint per-test + alembic 走生产路径 + 4 隔离自检 tests，2026-05-05 commit `15d0329`）
- [x] **B10 Next.js 脚手架**（已并入 B1.4 完成）

### 5.3 残留文档清理（与 B 并行可做）

- [x] **engineering-spec §13/§14/§15** 填实（实查 spec 行 2210-2327：§13 A3 accepted 2026-04-26 / §14 B 日期+短sha accepted / §15 4 子节填实 accepted；roadmap 之前误标，2026-05-05 修正）
- [x] **07-capability-matrix.md** draft → accepted（2026-05-05：对照 M01-M20 accepted 设计 verify 9 推断项 + 决策 4 补漏候选；状态机命中收敛 9→6，幂等命中收敛 7→2，新增"文件上传"列）

### 5.4 Phase 2.0 完成判定

闸门同时满足才进 2.1：
- A1-A4 决策全 accepted
- B1-B10 代码全跑通：`make dev` / `make test` / `make migrate` 三命令本地通过
- AppError + Auth + activity_log + tenant_filter 四 helper 单元测试通过

---

## 6. Phase 2.1：后端 20 模块 ⏳

> **闸门**：M01 PR merge（探针）才能开 M02-M20 顺序。

### 6.1 M01 探针（基线验证，1-2 天）✅ 2026-05-07 完成

- [x] M01 用户系统 own：users 表 + login/refresh/logout/me + admin endpoints
- [x] M01 baseline-patch（F3.10/F3.13）：delete_user 校验链已写在 design（实装等 M20 team 落地后联动）
- [x] M01 tests.md PASS（118 PASS / 0 xfail / 0 fail / lint 净 / ci-lint.sh R13-1 22=22 + L12 守护通过）
- [x] M01 commits 已 push origin/main（c1e3acc → 1c198cf 6 commits）
- [⚠️ bypassed] simplify-checklist 三维扫（M01 范式简单 + 已稳定，转移到 M02 首跑——见 99-comparison/phase-gate-bypass-log.md #1）
- [⚠️ bypassed] spec-reviewer + code-quality-reviewer 两 Agent 审（同上 bypass，M02 起恢复）
- [x] M01 "PR merge"（项目无 PR 流程，commits push 到 origin/main 等价）

### 6.2 M02-M19 业务模块顺序（约 2-3 周）

按依赖顺序：
- [x] M02 项目管理（含 PROJECT_ARCHIVED ErrorCode F2.3）✅ 2026-05-07 (5 子片 c6b97d6→c9b0618 + R1+R2 修 e5651bf+e7b1b7f + 收尾 bc1b6a7; 205 PASS)
- [x] M03 模块树 ✅ 2026-05-07 (§14.5 prep 800e632 + 5 子片 d174e90→4a1a615 + R1+R2 修 ce73570+656e05c; 285 PASS; L1+L2+L3 第二次实证)
- [ ] M04 维度记录
- [x] M05 版本时间线 ✅ 2026-05-08 (6 子片 811d6bc→{TBD} + R1+R2 闭环 / 412 PASS / R13-1 49=49 / L12 守护 / 闸门 2.5 B 栏 0 项首次实证)
- [x] M06 竞品对标 ✅ 2026-05-08 (子片 0 c84f6f2 + 1 d01c5ad + 2 f7211fb + 3 86195cc + R1 立修 c792263 + 子片 4 [hash] + R2 闭环 0 P1 + 子片 5 关闸; 473+ PASS / R13-1 53=53; R-X2 第二真注入零摩擦; L1 第五数据点)
- [x] M07 问题沉淀 ✅ 2026-05-08 (子片 0 b81c0d8 + 1 13152e1 + 2 a917235 + 3 e6e0873 + R1 立修 6a1072f + 子片 4 [hash] + R2 立修 8246984 + 子片 5 关闸; 538+ PASS / R13-1 59=59; R-X2 第三真注入 **orphan 语义** + 接口共享行为契约分化 7 处 anchor; L1 第六数据点 + 元教训"M06 P1 范式 M07 复发立修"首次实证)
- [x] M08 模块关系图 ✅ 2026-05-08 (子片 0 eed7749 + 1 fc142ad + 2 1fe57fe + 3 7b3d3eb + 子片 4 [hash] + R1 立修 + R2 P1 立修 self_loop code 映射 + 子片 5 关闸; 586+ PASS / R13-1 64=64; **R-X2 第四真注入 双向 OR + delete 语义** 与 M07 orphan 对照 / R-X2 接口共享行为契约分化第二次实证; L1 第七数据点稳定 + 闸门 2.5 B 0 第四次 + **元教训"M07 P1 防御 actionable 主动应用"首次实证**（viewer 写 3 端点全覆盖主动写不等 R2 抓 + R2 没抓出新点 = 元教训内化生效）)
- [x] M10 项目全景图 ✅ 2026-05-08 (子片 0+1+2 098a2ee + 子片 3+R1 立修 b018aad + 子片 4 关闸 [hash]; 613 PASS / R13-1 67=67; **纯读聚合范式首次实证**（无 model/migration / ADR-003 规则 2 豁免 / 4 子片简化 / R1 三 subagent 合并 1 Opus）; folder 均值"迭代后序遍历"D-1 算法 / 分母=0 早返回 M10-B3; L1 第八数据点稳定 + 闸门 2.5 B 0 第五次 + **元教训新增 2 条**：纯读模块 schema-service contract drift 风险 + R1→R2 reconcile 缺失（启动包陈述与代码状态漂移）)
- [ ] M07 问题沉淀
- [ ] M08 模块关系
- [x] M10 项目总览（聚合）✅ 2026-05-08（详见上方 M10 项目全景图行）
- [x] M11 冷启动 ✅ 2026-05-08（**首个 R-X1 orchestrator**；8 commit 8ef59b3 子片 0 prep + §14.5 + 3 跨模块 batch_create 接通 / 4ed8dbe 子片 1 model+alembic+14 model tests / 090621a 子片 2 DAO+12 unit / e93057c 子片 3 OrchestratorService+7 ErrorCode+17 service tests / 2ccd579 R1 6 P1 立修 / aba873a 子片 4 router+4 endpoints+11 e2e / 2c39980 R2 2 P1 立修+1 punt / 子片 5 关闸；674 PASS / R13-1 74=74 / L12 守护；闸门 2.5 三栏 A 8 / B 0 / C 3 第六次 B 栏 0 项；R1=3 subagent 并行 / R2=1 合并 Opus；R-X1 首发新教训 2 条：① 失败补偿 commit boundary punt M17 sprint 抽独立 helper ② multipart 攻击面 file.size+filename sanitize 立修）
- [x] M12 对比矩阵 ✅ 2026-05-08（**R-X3 跨模块只读 + 多表事务 + 乐观锁 rename**；7 commit 63f2f93 子片 0 prep + §14.5 + DimensionService.batch_get_by_nodes 接通 / 9a0f039 子片 1 model+alembic+9 model tests / 3aa7415 子片 2 DAO+16 unit / 99105b4 子片 3 ComparisonService+5 ErrorCode+21 service tests / 169e948 R1 4 P1 立修+4 coverage / 589407c 子片 4 router+6 endpoints+15 e2e / 子片 5 关闸；742 PASS / R13-1 79=79 / L12 守护；闸门 2.5 三栏 A 4 / B 0 / C 4 第七次 B 栏 0 项；R1=3 subagent 并行 / R2=1 合并 Opus；R2 P1 裁决型 ComparisonMatrixResponse cells-only + scaffold disambiguation；元自审：让 CY 拍裁决型 P1 是 5 步分层失效信号）
- [x] M13 需求分析（流式 SSE §12A）✅ 2026-05-08（**LLM 集成首发 + §12A SSE pilot + R-X3 写 M04 + AES 全链路接通**；8 commit 73c7175 子片 0 prep §14.5 + DimensionService.create_dimension_record+get_latest 接通 / 28a127e 子片 1 AI Provider 抽象+MockProvider+ClaudeProvider+Registry+19 unit+3 integration smoke / ecb1d9c 子片 2 AnalyzeService+7 ANALYSIS_*+AnalysisLevel+Prompt 模板+20 unit / 368f83c 子片 3 Pydantic schema 4+3+13 unit / eedecd1 R1 8 P1 立修（3 subagent 并行去重合并）/ 7082b90 子片 4 Router 3 endpoints+21 e2e / 79fb4cc R2 4 项立修+conftest 迁 make_project_with_member+set_project_ai / 子片 5 关闸；827 PASS / R13-1 79→86 / L12 守护；闸门 2.5 三栏 A 4 / B 0 / C 7 第八次 B 栏 0 项；R1=3 subagent 并行 12 P1→去重 8 立修 / R2=1 合并 Opus 4 项；LLM 集成首发新教训 4 条 sink：PEP 533 aclose 区分 / Anthropic delta.type 多种校验 / SSE generator 占 AsyncSession 300s / design metadata 字段集逐字段 e2e 验；元自审：cross-project node 404 元教训应用不全 SSE 端点漏测 → R2 抓出立修 → "3 端点全覆盖"原则 sink 到 feedback_problem_layered_analysis）
- [x] M14 行业新闻 ✅ 2026-05-08（**首个全局豁免业务模块**；7 commit 3afbbdb 子片 0 prep §14.5 / c2858f7 子片 1 model+alembic+9 model tests / 968b284 子片 2 DAO+18 unit / e184c8b 子片 3 Service+4 ErrorCode+Pydantic+35 unit / 6ab088d R1 6 P1 立修 / 9028875 子片 4 Router 8 endpoints+27 e2e / 059c7ea R2 4 P1 立修 / 子片 5 关闸；930 PASS / R13-1 90=90 / L12 守护；闸门 2.5 三栏 A 2 / B 0 / C 7 第九次 B 栏 0 项；R1=3 subagent 并行 7 P1→6 立修 / R2=1 合并 Opus 4 项；L1 第十二数据点稳定；新教训 3 条 sink：write_event project_id UUID→Optional / N/A 元教训显式声明范式 / endpoint 形态特殊不免除契约纪律 M13 NEW 复用强化；元教训应用 9 项中 4 N/A 显式 + 4 ✅ 主动复制 + 1 ❌→立修（write_event e2e + metadata e2e + list_by_node disambiguation + source_type 守 e2e））
- [x] M15 数据流转 ✅ 2026-05-08（**纯读 R10-2 owner 模块 / R1=1 合并 Opus M10 范式复用**；8 commit 29b0aaa 子片 0 prep §14.5 + M14 baseline-patch 反向回写 α 路线 / 8889ec5 子片 1 ActivityLog model + alembic + 9 model tests / af9120c 子片 2 DAO + 16 unit / 0fa19ad 子片 3 Schema + 11 ErrorCode（3 own + 8 M20 baseline-patch）+ Service + 21 tests / d527632 R1 1 P1 立修 + §14.5 self-correct / 4e9fd54 子片 4 Router 1 endpoint + 13 e2e / 9ca130e R2 2 P1 立修（metadata e2e 字面 + Pydantic 422 边界）/ 子片 5 关闸 commit；63 PASS / R13-1 90→101 / L12+L13 守护；闸门 2.5 三栏 A 6 / B 0 / C 10 第十次 B 栏 0 项；纯读 R10-2 owner 新教训 4 条 sink：横切 enum 同步责任 / 纯读 R1=1 合并 Opus / 双层防御非 dead code 区分 / 读权限 403 测试范式）
- [x] M16 AI 快照（后台 §12B）✅ 2026-05-09（**§12B 后台 fire-and-forget 子模板首次实战 + L1 R14 立规重大事件**；7 commit 9e9eb68 子片 0 prep + 5c592d5 子片 0.5 L1+L3 batch 41 处过去式 + 959e0b4 write_event 真 INSERT + 6007fa2 子片 1 model+alembic+ActionType+3+TargetType+1 + ba0afb5 子片 2 DAO+CAS+18 unit + 2273f90 子片 3 Service+Schema+Runner+14 ErrorCode+15 unit + 043e3e2 子片 4 Router+19 e2e；1063 PASS / R13-1 116=116 / R14 守护通过 / L12+L13 守护；R1+R2 self-审 bypass log #2 / 闸门 2.5 三栏 A 8 / B 0 / C 8 第十一次 B 栏 0 项；L1 第十四数据点稳定 → M17+ 默认范式作模板；元贡献 6 项：R14 立规+ci-lint / §12B 子模板首战 / CAS UPDATE 防双写 / advisory_xact_lock 幂等 / 自起 SessionLocal runner / SYSTEM_USER_UUID + queue/base scaffold；cross-sprint 真漏洞 #1+#2+#5 关闭）
- [x] M17 AI 导入（Queue §12C）✅ 2026-05-09（**首个 R-X1 第二实例 + 异步 Queue + WebSocket endpoint pilot**；ad069c0 启动期 + 7a6327f 子片 0 prep R-X1 第一实例迁移 + b806931 子片 1 model+alembic+ActionType+8+TargetType+1+36 model tests + f41ad25 子片 2 DAO+tenant filter+idempotency 7d+dead_letter 30d+28 unit + 9229759 子片 3 Service+AIOrchestrationService+8 ErrorCode+Queue+WS+40 新测试 + d558b5f R1 立修 8 P1（3 subagent 并行）+ [hash] 子片 4 Router 7 REST+1 WS+24 e2e + dcf7024 R2 立修 4 P1（1 合并 Opus）+ 子片 5 关闸；1213 PASS / R13-1 116→124 / L12+L13+R14 全过；闸门 2.5 第十二次 B 0；L1 第十五数据点稳定；bypass log #2 配套已恢复 spawn subagent；元贡献 7 项：R-X1 第二实例零摩擦验证 + WS endpoint Query Bearer 鉴权 + idempotency project_id B1 修复 + N+1 防护批量 cache + filename sanitize 字面验范式 + partial_failed IMPL-NOTE + design §7 字面漂移立规 sink；sink 立规候选 3 项：WS 5-test 矩阵 / sanitize horizontal 化 / multipart 上限分级；punt 池新增 4 项）
- [ ] M18 语义搜索（embedding §12D）
- [ ] M19 导入导出
- [ ] ~~M09~~（superseded by M18，不实现）

### 6.3 M20 团队（最后一个 own）

- [ ] M20 own：teams + team_members + 8.5 P1+P2 + 8.7 R-X3 + 10.3 R10-1 N+1
- [ ] M02 baseline-patch：space_id → team_id RENAME + FK
- [ ] M15 baseline-patch：ActionType +10 + TargetType +1 + Alembic 单 revision 合并

### 6.4 M03-M19 横切 L3 注入升级（4 批，1 周）

按 baseline-patch §17 模块拆批：
- [ ] **批 1**：M02 + M03 + M04（先建 helper 复用基线 + pytest parametrize 测试模板）
- [ ] **批 2**：M05 + M06 + M07 + M08
- [ ] **批 3**：M10 + M11 + M12 + M13 + M14
- [ ] **批 4**：M15 + M16 + M17 + M18 + M19

---

## 7. Phase 2.2：前端继承 Prism + 改造 ⏳

> **闸门**：后端 OpenAPI 契约稳定（至少 M01-M05 + M20）才能开。

### 7.1 继承范围决策（CY 出骨架）

- [ ] 列出 Prism 前端目录清单 → 标注「直接继承 / 改造继承 / 重写 / 不要」四档
- [ ] 类型同步策略（openapi-typescript 自动生成 vs 手动维护）

### 7.2 继承 + 改造（推估 1-1.5 周）

- [ ] 拷贝 Prism `app/` 选定子集到 prism-0420
- [ ] 路由调整（适配 prism-0420 Auth.js 配置）
- [ ] API client 全替换（指向 prism-0420 后端）
- [ ] 类型层全替换（prism-0420 OpenAPI codegen）
- [ ] 关键交互冒烟测试（10 个核心页面手测过一遍）

### 7.3 M20 团队页面（前端唯一新增）

- [ ] M20 不在 Prism 现有前端 → 必须从头写（参考 shadcn pattern）
- [ ] 团队列表 / 团队详情 / 成员管理 / 转让 / 删除等页面

---

## 8. Phase 2.3：集成 + E2E + 上线 ⏳

### 8.0 🔴 工程规约 minimal 补完（上线前硬前置）

> 03/04/05 三份 spec 是 Phase 2.0 的"最小决策占位"，足够 2.0/2.1/2.2 业务开发，但上线前必须补完，否则线上会缺 CI/可观测/密钥能力。

**03-cicd-plan 必补**：
- [ ] `.github/workflows/ci.yml` 完整步骤（lint / typecheck / test / build / migrate dry-run）
- [ ] 缓存策略（pip / pnpm / docker layer）
- [ ] secrets 注入（GH Actions secrets → env）
- [ ] 部署触发条件（main push / tag / 手动）

**04-observability-plan 必补**：
- [ ] 指标采集方案选型（Prometheus / OTel / 云厂商）+ 关键指标清单（QPS / P95 / 错误率 / Queue 堆积）
- [ ] 告警阈值 + 通道（TG / 邮件）
- [ ] traceId 贯穿（FastAPI middleware → arq job → 日志字段）
- [ ] 错误聚合（Sentry or 自建）选型

**05-security-baseline 必补**：
- [ ] prod 密钥管理选型（Vault / Doppler / 云 KMS / GH secrets-only）
- [ ] 密钥轮转流程（JWT / DB / 第三方 API key）
- [ ] HTTPS / CSRF / CORS / Rate limit 上线前 checklist
- [ ] 备份 + 灾恢方案（PG dump 频率 / 异地）

**判定**：8.0 全 ✅ 才能进 8.1 上线冒烟。

### 8.1 集成与上线

- [ ] 全 20 模块端到端冒烟（用户注册 → 创建项目 → 加入团队 → 跑全功能流）
- [ ] Playwright E2E（关键 10 路径）
- [ ] 性能基线（C7 测试：1000 project / P95 < 100ms）
- [ ] CI 全跑通（lint + test + build + migrate）
- [ ] 部署文档（docker-compose prod 模板）

---

## 9. Phase 3：数据采集 + Prism 对照 ⏳

> 这是 Shadow 项目的核心 KPI：用数据证明「设计前置 vs VibeCoding」差异。

- [ ] 收集 prism-0420 开发期 commit / 测试 / bug 数据
- [ ] 对比 Prism 同期数据（git log + PR + bug 库）
- [ ] 产出对照报告（`design/99-comparison/` 每模块一份）
- [ ] 沉淀方法论（KB `02-技术/架构设计/` 增量更新）

---

## 10. 维护规则（AI 必读）

1. **每次进度变化**（任一 checkpoint 完成 / 决策落定 / PR merge）→ AI 必须更新本文件 `last_updated` + 对应行打钩 + 仪表盘百分比
2. **CY 问"我在哪一步"** → 直接读本文件回答，不凭印象
3. **AI 准备生成"实现提示词" / "Phase X 启动包" / "PR 计划"前** → 必先读本文件确认上一阶段闸门已通过；任一未通过 → 拒出业务提示词，告诉 CY 真实位置
4. **本文件状态** = 真相源；与 README.md 模块清单不一致时以本文件为准

---

## 11. 进度变更日志

| 日期 | 变更 | 责任人 |
|------|------|-------|
| 2026-04-26 | Phase 1 完结（M20 accepted + 6 commit push）| CY + AI |
| 2026-04-26 | Phase 2.0 启动 / roadmap.md 建立 | CY |
| 2026-04-26 | A1-A4 4 项决策全 accepted（02/03/04/05-spec + engineering-spec §13/§14/§15 落地，含候选+优缺点+理由+替代触发完整记录）| CY + AI |
| 2026-05-05 | 修正 03/04/05 spec 真实状态为 accepted-minimal + §8.0 加上线前必补清单（防漏） | CY + AI |
| 2026-05-05 | B1.1 最小 FastAPI 脚手架落地（uv+py3.12+fastapi+ruff+pytest，/health 200，commit 0bafb20）| CY + AI |
| 2026-05-05 | B1.2 docker-compose（pg16+pgvector / redis7，先 55432/56379 避让 v1）+ pydantic-settings + /readyz 双探针绿，commit a08311b；端口归位 5432/6379 + v1 stack stop，commit b823461 | CY + AI |
| 2026-05-05 | B1.3 Alembic async 接 settings + initial baseline b1c62870faa5 + structlog JSON + lifespan 启动日志，commit c4c46e4 | CY + AI |
| 2026-05-05 | 日志统一：uvicorn 接 ProcessorFormatter，access/startup/error 全 JSON，commit 1c7fd5f | CY + AI |
| 2026-05-05 | B1.4 Next.js 16+React 19+TS+Tailwind 4+ESLint 9+vitest 4+TestLib+prettier+pre-commit 4 hooks 全跑通，commit 23b0385 | CY + AI |
| 2026-05-05 | B2.1 api/errors（AppError + ErrorCode + middleware）8 tests，commit 6f7949a | CY + AI |
| 2026-05-05 | B2.2 api/auth（JWT + HMAC P2 签名 + require_user + AuthServiceProtocol 注入点）11 tests，commit 49f6eac | CY + AI |
| 2026-05-05 | B2.3 api/services/activity_log_service（write_event stub）2 tests，commit e140306 | CY + AI |
| 2026-05-05 | B2.4 api/auth/tenant_filter（user_accessible_project_ids_subquery + TenantContextProtocol 注入点）2 tests，commit 8e0be2e | CY + AI |
| 2026-05-05 | B9 测试 fixtures（D1-D5 全 A）：async db_session + NESTED savepoint + alembic prod 路径 + 4 隔离自检 tests，commit 15d0329 | CY + AI |
| 2026-05-05 | §5.3 残留文档对账：§13/§14/§15 实查为已完成（roadmap 之前误标）+ 07-capability-matrix.md draft→accepted（verify 9 推断项 + 4 补漏决策 + 加文件上传列）；Phase 2.0 100% | CY + AI |
| 2026-05-07 | M01 探针实施完成（5 子片 c1e3acc → 2704d0f + design 回写 1c198cf；118 PASS / 0 xfail / lint 净 / ci-lint.sh R13-1 22=22 + L12 通过；ADR-004 §3 #5 + §3.5 + §3.6 + M01 §4 §10 回写） | CY + AI |
| 2026-05-07 | 闸门 3 通过：第 1+2 项 ✅；第 3 项（三 Agent 流水线）bypass 转 M02 首跑（首条 phase-gate-bypass-log.md 登记）；Phase 2.1 5%→10%；下一站 M02 | CY + AI |
| 2026-05-07 | M02 sprint 启动元反思 → 设计体系 v2 升级（5 体系盲区 + 8 条新规则 + 11 处 baseline-patch 回扫 + 修复 10 horizontal helper docstring 存量）；沉淀 design/audit/time-dimension-blindspot-2026-05-07.md + KB 补丁01；M02 design ready for sprint 实施 | CY + AI |
| 2026-05-07 | M03 sprint 完成（5 子片 + R1+R2 闭环；285 PASS / R13-1 41=41 / L12 守护；§14.5 prep + design §6.X A4/A5/A6 + §3 description + §10 metadata + audit/m03-pilot-template-validation.md）；Phase 2.1 15→20%；下一站 M04 | CY + AI |
| 2026-05-08 | M05 sprint 完成（6 子片 811d6bc 子片 0 prep / de53192 子片 1 model + alembic + Node back_populates / d3374fe 子片 2 DAO / 063cbd4 子片 3 Service+ErrorCode / 5e0e239 R1 P1 立修 / 56da878 R2 P1 立修 + 子片 5 design 回写；412 PASS / R13-1 49=49 / L12 守护；闸门 2.5 三栏首次 B 栏 0 项实证 = 5 步分层分析法防假决策价值首次产出）；Phase 2.1 25→30%；下一站 M06 | CY + AI |
| 2026-05-08 | M06 sprint 完成（c84f6f2 子片 0 prep + ck_clause 别名规范化 / d01c5ad 子片 1 双表 model+migration+Node back_populates / f7211fb 子片 2 DAO / 86195cc 子片 3 Service+R-X2 第二真注入+4 ErrorCode / c792263 R1 3 P1 立修 + 子片 4 Router 8 endpoints + R2 0 P1 + 子片 5 关闸；473+ PASS / R13-1 53=53 / L12 守护；**R-X2 第二真注入零摩擦实证**（M04 Protocol 4 参升级元教训复用价值首次产出）+ **闸门 2.5 三栏 B 0 项第二次实证**（M05 立 / M06 复用，防御未来非修复存量）+ L1 第五数据点稳定）；Phase 2.1 30→35%；下一站 M07 问题沉淀 | CY + AI |
| 2026-05-08 | M07 sprint 完成（b81c0d8 子片 0 prep + §14.5 默认范式复用 + §5 预防性消歧 / 13152e1 子片 1 Issue model+migration+Node back_populates **passive_deletes** orphan 语义 / a917235 子片 2 DAO+SELECT FOR UPDATE+orphan_by_node_id / e6e0873 子片 3 IssueService+R-X2 第三真注入(orphan)+6 ErrorCode+状态机 4 状态 / 6a1072f R1 1 P1 立修 get_for_embedding 空字符串 / 子片 4 Router 7 endpoints+15 e2e tests / 8246984 R2 1 P1 立修 viewer 写 4 端点全覆盖（**M06 元教训复发立修**）+ 子片 5 关闸；538+ PASS / R13-1 59=59 / L12 守护；**R-X2 第三真注入 orphan 语义实证**（接口共享 / 行为契约分化 / 7 处代码 anchor 防误读）+ **闸门 2.5 三栏 B 0 项第三次实证** + L1 第六数据点稳定 + **元教训"M06 P1 立修不自动横切到下一模块" 首次实证 + actionable 防御** sink 进 feedback_problem_layered_analysis 失效信号）；Phase 2.1 35→40%；下一站 M08 模块关系图 | CY + AI |
| 2026-05-08 | M12 sprint 完成（63f2f93 子片 0 prep §14.5 + DimensionService.batch_get_by_nodes 接通 / 9a0f039 子片 1 model+alembic / 3aa7415 子片 2 DAO+16 unit / 99105b4 子片 3 Service+5 ErrorCode+21 service / 169e948 R1 4 P1 立修+4 coverage 补 / 589407c 子片 4 router+6 endpoints+15 e2e / 子片 5 关闸；742 PASS / R13-1 79=79 / L12 守护；R-X3 跨模块只读 + 多表事务 + 乐观锁 rename + 元教训防御 actionable 5 主动复制；R2 P1 裁决型 cells-only + scaffold disambiguation；闸门 2.5 第七次 B 0；L1 第十数据点稳定 → M13+ 默认范式作模板；元自审：让 CY 拍 R-X3 范式既锁的裁决型 P1 是 5 步分层失效信号）；Phase 2.1 55→60%；下一站 M13 需求分析（流式 SSE）| CY + AI |
| 2026-05-08 | M15 sprint 完成（29b0aaa 子片 0 prep §14.5 + M14 baseline-patch 反向回写 α 路线 / 8889ec5 子片 1 ActivityLog model + alembic + 9 model tests / af9120c 子片 2 ActivityStreamDAO + 16 unit + conftest make_activity_log fixture / 0fa19ad 子片 3 Schema + 11 ErrorCode（3 M15 own + 8 M20 baseline-patch）+ Service + 21 tests / d527632 R1 1 P1 立修（schema InvalidFilterError 业务 code raise）+ §14.5 self-correct（纯读 R1=1 合并 Opus）/ 4e9fd54 子片 4 Router 1 endpoint + 13 e2e / 9ca130e R2 2 P1 立修（metadata e2e 字面 + Pydantic 422 边界）/ 子片 5 关闸 commit；63 PASS / R13-1 90→101 / L12+L13 守护通过；纯读 R10-2 owner 模块新教训 4 条 sink；闸门 2.5 第十次 B 0；L1 第十三数据点稳定 → M16+ 默认范式作模板）；Phase 2.1 70→75%；下一站 M16 AI 快照 | CY + AI |
| 2026-05-09 | M17 sprint 完成（**首个 R-X1 第二实例 + 异步 Queue + WebSocket endpoint pilot + bypass log #2 配套已恢复 spawn subagent**；7 commit ad069c0 启动期闸门 2.6+R-X1 helper+L1 总则修订 / 7a6327f 子片 0 prep M11 ColdStart R-X1 helper 迁移 / b806931 子片 1 model+ActionType+8+TargetType+1+36 model tests / f41ad25 子片 2 DAO+tenant filter+idempotency 7d+dead_letter 30d+28 unit / 9229759 子片 3 Service+AIOrchestrationService+8 ErrorCode+Queue+WS+40 新测试 / d558b5f R1 立修 8 P1（3 subagent 并行）/ [hash] 子片 4 Router 7 REST+1 WS+24 e2e / dcf7024 R2 立修 4 P1（1 合并 Opus）/ 子片 5 关闸；1213 PASS / R13-1 116→124 / L12+L13+R14 全过；闸门 2.5 第十二次 B 0；L1 第十五数据点稳定；元贡献 7 项：R-X1 第二实例零摩擦验证 + WS endpoint Query Bearer 鉴权 + idempotency project_id（B1 修复）+ N+1 防护批量 cache + filename sanitize 字面验范式 + partial_failed IMPL-NOTE + design §7 字面 status code 漂移立规 sink；sink 立规候选 3 项：WS 5-test 矩阵 + sanitize horizontal 化 + multipart 上限分级；punt 池 #7 关闭+新增 4 项；bypass log #2 配套验收 ✅）；Phase 2.1 80→85%；下一站 M18 语义搜索（首个 §12D embedding 持久化子模板 / pgvector + 增量+backfill 双路触发链 + 模型版本升级回填）| CY + AI |
| 2026-05-09 | M16 sprint 完成（**§12B 后台 fire-and-forget 子模板首战 + L1 R14 立规重大事件**；7 commit 9e9eb68 子片 0 prep §14.5 + M15 design §10 R14 段 + activity_log_service docstring 修 / 5c592d5 子片 0.5 L1+L3 batch 7 业务模块 41 处 service action_type 过去式机械批量改 + 4 NEW enum（version_record_set_current/competitor_ref_updated/issue_unassigned/module_relation_updated）+ Alembic ALTER CHECK + ci-lint R14 守护 / 959e0b4 write_event stub→真 INSERT + ci-lint R14 扩 routers + project_router 3 处修 / 6007fa2 子片 1 AISnapshotTask model + alembic + ActionType+3 + TargetType+1 同步 4 处 + 16 model tests / ba0afb5 子片 2 DAO+CAS UPDATE+find_idempotent+advisory 范式+18 unit / 2273f90 子片 3 Service+Schema+14 ErrorCode+Runner+AI Provider 接通+queue/base SYSTEM_USER_UUID scaffold+15 unit / 043e3e2 子片 4 Router 3 endpoints+19 e2e+元教训 17 条 actionable 主动复制；1063 PASS / R13-1 116=116 / R14 守护通过 / L12+L13；R1+R2 self-审 bypass log #2（context budget）/ 闸门 2.5 第十一次 B 0；L1 第十四数据点稳定；元贡献 6 项；cross-sprint 真漏洞 #1+#2+#5 关闭+元发现 #1 触发点 A 立规实证）；Phase 2.1 75→80%；下一站 M17 AI 导入（首个 arq Queue 消费者+R-X1 第二实例+闸门 2.6 mini-sprint 必须恢复 R1+R2 spawn subagent）| CY + AI |
| 2026-05-08 | M14 sprint 完成（3afbbdb 子片 0 prep §14.5 / c2858f7 子片 1 IndustryNews+NewsNodeLink models+alembic+9 model tests / 968b284 子片 2 DAO+18 unit（GLOBAL DATA NO TENANT FILTER 字面）/ e184c8b 子片 3 IndustryNewsService+4 ErrorCode+Pydantic schema+35 unit/schema tests（write_event project_id UUID→Optional 升级）/ 6ab088d R1 6 P1 立修（NewsNodeLink.node relationship + design §8 unlink disambiguation + ORM mutate + make_news conftest 十连 + page validation + tags max_length）/ 9028875 子片 4 Router 8 endpoints+27 e2e / 059c7ea R2 4 P1 立修（write_event e2e 2 + metadata e2e 2 + list_by_node disambiguation + source_type 守 e2e 2）/ 子片 5 关闸；930 PASS / R13-1 90=90 / L12 守护；**首个全局豁免业务模块**首发；闸门 2.5 第九次 B 0；L1 第十二数据点稳定 → M15+ 默认范式作模板；新教训 3 条 sink：write_event project_id Optional / N/A 元教训显式声明 / endpoint 形态特殊不免除契约纪律 M13 NEW 复用强化）；Phase 2.1 65→70%；下一站 M15 数据流转 | CY + AI |
| 2026-05-08 | M13 sprint 完成（73c7175 子片 0 prep §14.5 + DimensionService.create_dimension_record+get_latest 接通 / 28a127e 子片 1 AI Provider 抽象+MockProvider+ClaudeProvider+Registry+19 unit+3 integration smoke / ecb1d9c 子片 2 AnalyzeService+7 ANALYSIS_*+AnalysisLevel+Prompt 模板+20 unit / 368f83c 子片 3 Pydantic schema 4+3+13 unit / eedecd1 R1 8 P1 立修+conftest 迁 make_project_with_member+set_project_ai / 7082b90 子片 4 Router 3 endpoints+21 e2e / 79fb4cc R2 4 项立修 / 子片 5 关闸；827 PASS / R13-1 86=86 / L12 守护；**LLM 集成首发 + §12A SSE pilot + R-X3 写 M04 + AES 全链路接通**；闸门 2.5 第八次 B 0；R1=3 subagent 并行 12 P1→8 立修 / R2=1 合并 Opus 4 项；L1 第十一数据点稳定；新教训 4 条 sink：PEP 533 aclose 区分 / Anthropic delta.type 多种校验 / SSE generator 占 AsyncSession 300s punt M16/M17 / design metadata 字段集逐字段 e2e；元自审："3 端点全覆盖"原则 SSE 形态特殊不免除 → R2 抓 P1-2 SSE 端点 cross-project node 缺测立补 + sink feedback_problem_layered_analysis 失效信号）；Phase 2.1 60→65%；下一站 M14 行业新闻 | CY + AI |
| 2026-05-08 | M08 sprint 完成（eed7749 子片 0 prep + §14.5 默认范式复用 + §5 预防性消歧 / fc142ad 子片 1 ModuleRelation model+migration+UNIQUE 三元组+self-loop CHECK / 1fe57fe 子片 2 DAO+双向 OR / 7b3d3eb 子片 3 ModuleRelationService+R-X2 第四真注入(双向 delete)+5 ErrorCode+IntegrityError 区分约束名 / 子片 4 Router 5 endpoints+12 e2e tests + R1 立修 R3-2 R-X2 cross-project 422 / R2 P1 立修 self_loop code 映射 design §13 ValidationException Handler 字面 drift（移 schema 层 model_validator → service 层独家 raise 范式与 M02-M07 一致）+ 子片 5 关闸；586+ PASS / R13-1 64=64 / L12 守护；**R-X2 第四真注入 双向 OR + delete 语义**（与 M04/M06 同 delete / 与 M07 orphan 对照）+ R-X2 接口共享行为契约分化第二次实证 + L1 第七数据点稳定 + 闸门 2.5 B 0 第四次 + **元教训"M07 P1 防御 actionable 主动应用"首次实证**（viewer 写 3 端点全覆盖主动写不等 R2 抓 + R2 没抓出新点 = 元教训内化生效）；Phase 2.1 40→45%；下一站 M10 全景图（M09 superseded by M18） | CY + AI |
| _（未来变更追加在这里）_ | | |
