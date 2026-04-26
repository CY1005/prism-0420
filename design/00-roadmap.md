---
title: prism-0420 全项目 Roadmap + 进度 Checklist
status: living-doc
owner: CY
last_updated: 2026-04-26
current_phase: Phase 1 完结 / Phase 2.0 未启动
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
Phase 2.0 工程基线  ⏳ ░░░░░░░░░░░░░░░░   0%   ← 你在这里
Phase 2.1 业务模块  ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 2.2 前端继承  ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 2.3 集成验证  ⏳ ░░░░░░░░░░░░░░░░   0%
Phase 3 数据对照   ⏳ ░░░░░░░░░░░░░░░░   0%
```

**上次更新**：2026-04-26（M20 accepted + Phase 1 收官）

**下一步动作**：A1 测试策略决策（02-quality-spec §3-4）

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
- [ ] **02-quality-spec.md**（CY 决策栏全空 → Phase 2.0 A1+A2）
- [ ] **03-cicd-plan.md**（CY 决策栏全空 → Phase 2.0 A4）
- [ ] **04-observability-plan.md**（CY 决策栏全空 → Phase 2.0 A4）
- [ ] **05-security-baseline.md**（CY 决策栏全空 → Phase 2.0 A4）

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

### 5.1 A 阶段：4 项决策（半天）

- [ ] **A1 测试策略**（02-quality-spec §3-4）
  - 后端测试框架 / 前端测试框架 / DB 隔离 / 覆盖率门槛
- [ ] **A2 Lint + Formatter + pre-commit**（02-quality-spec §1-2）
  - Python lint + format / TS lint + format / pre-commit hook 工具链
- [ ] **A3 Code review 流程**（engineering-spec §13）
  - PR reviewer 数 / 三 Agent 流水线触发时机 / simplify-checklist 门槛 / 拒合并硬条件
- [ ] **A4 CICD/可观测/安全占位决策**（03/04/05-spec 关键决策栏）
  - CI 平台 / 日志方案 / 密钥管理 三项最小集

### 5.2 B 阶段：10 项工程基线代码（2-3 天）

- [ ] **B1 仓库脚手架**（api/ + app/ + .env.example + Makefile + README Quick Start）
- [ ] **B2 Docker Compose**（PG 16 + pgvector + Redis + init-db / make up）
- [ ] **B3 SQLAlchemy base + Alembic init**（base.py + Mixin + session.py + alembic.ini + 跑通 base revision）
- [ ] **B4 FastAPI 启动框架**（main.py + config.py + 中间件 + /health + uvicorn 跑起来）
- [ ] **B5 AppError + 错误中间件**（base + codes + handler + raise → HTTP 转换测试）
- [ ] **B6 Auth 基础**（JWT + require_user Depends + P2 internal token + Auth.js v5 Redis adapter 配置）
- [ ] **B7 activity_log 写入封装**（M15 own helper：write_event 接受外部 db）
- [ ] **B8 tenant_filter helper**（M20 引入：user_accessible_project_ids_subquery 实现 + 测试）
- [ ] **B9 测试 fixtures**（pytest conftest + DB rollback + factory + 跑空 test 验证）
- [ ] **B10 Next.js 脚手架**（create-next-app + shadcn/ui + Tailwind + api-client + openapi-typescript codegen）

### 5.3 残留文档清理（与 B 并行可做）

- [ ] **engineering-spec §13/§14/§15** 填实（C 档：code review 清单 / 版本号规则 / 注释规范）
- [ ] **07-capability-matrix.md** draft → accepted

### 5.4 Phase 2.0 完成判定

闸门同时满足才进 2.1：
- A1-A4 决策全 accepted
- B1-B10 代码全跑通：`make dev` / `make test` / `make migrate` 三命令本地通过
- AppError + Auth + activity_log + tenant_filter 四 helper 单元测试通过

---

## 6. Phase 2.1：后端 20 模块 ⏳

> **闸门**：M01 PR merge（探针）才能开 M02-M20 顺序。

### 6.1 M01 探针（基线验证，1-2 天）

- [ ] M01 用户系统 own：users 表 + login/register
- [ ] M01 baseline-patch（F3.10/F3.13）：delete_user 校验链 + USER_HAS_OWNED_TEAMS / USER_IS_LAST_TEAM_OWNER
- [ ] M01 tests.md 全 PASS（critical path 100%）
- [ ] simplify-checklist 三维扫
- [ ] spec-reviewer + code-quality-reviewer 两 Agent 审
- [ ] M01 PR merge

### 6.2 M02-M19 业务模块顺序（约 2-3 周）

按依赖顺序：
- [ ] M02 项目管理（含 PROJECT_ARCHIVED ErrorCode F2.3）
- [ ] M03 模块树
- [ ] M04 维度记录
- [ ] M05 版本时间线
- [ ] M06 竞品对标
- [ ] M07 问题沉淀
- [ ] M08 模块关系
- [ ] M10 项目总览（聚合）
- [ ] M11 冷启动
- [ ] M12 对比矩阵
- [ ] M13 需求分析（流式 SSE §12A）
- [ ] M14 行业新闻
- [ ] M15 数据流转 own（含 list_for_team F2.5 + ActionType +10 + ErrorCode +8）
- [ ] M16 AI 快照（后台 §12B）
- [ ] M17 AI 导入（Queue §12C）
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
| _（未来变更追加在这里）_ | | |
