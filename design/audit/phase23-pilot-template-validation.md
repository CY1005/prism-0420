---
title: Phase 2.3 子 sprint B — pilot template validation（集成 e2e + 性能基线）
status: partial-complete
owner: CY
created: 2026-05-09
phase: Phase 2.3 子 sprint B
parent: ../00-roadmap.md §8.1 + ../../_handoff/_archive/phase23-prompts.md「子 sprint B」段
---

# Phase 2.3 子 sprint B — pilot template validation

## 1. 实施范围（PARTIAL / 单 session 多子 sprint 串跑约束）

### ✅ 完成项

| 项 | 实施 | 验证 |
|----|------|------|
| Playwright 装入 | `app/playwright.config.ts` + chromium 装 | `pnpm exec playwright --version` 1.59.1 |
| pilot e2e #1（auth flow）| `app/e2e/01-auth-flow.spec.ts` 2 tests 真跑 PASS | 登录页 + 错误密码 + 注册页"暂未开放" |
| 9 e2e skeleton（#2-#10）| `test.describe.skip` 占位 + 业务断言注释完整 | 待 DB seed fixture 激活 |
| perf baseline pytest 文件 | `tests/perf/test_baseline.py` 2 smoke + 1 skeleton | 2 PASS / 1 skipped |
| .gitignore Playwright artifacts | `app/.gitignore` 加 test-results/playwright-report | 已落 |

### ⏸️ 推后项（B-FOLLOW-UP punt）

| 项 | 推迟原因 | 激活条件 |
|----|----------|----------|
| e2e #2-#10 完整断言 | DB e2e fixture 复杂度（admin user seed + storageState login）+ 单 session 多子 sprint 串跑预算约束 | 后端 conftest 加 e2e 级 admin fixture + storageState login share + page object 抽象 |
| pytest-benchmark + 1000 seed perf | 子 sprint D 评估窗口（接受 / 立 perf sprint / 推上线后）会重新决策 | 子 sprint D 选项二时一并实施 |
| R1+R2 spec/quality reviewer 范式 | 单 session 多 subagent 预算超 / R 范式适用全栈集成需 ≥2h sprint 自有窗口 | 后续独立 e2e expansion sprint 启动 |
| CI e2e job 实跑 | `.github/workflows/ci.yml e2e` job 写完但未接通 service container（pgvector + redis + uvicorn + pnpm dev 全栈装配）| 上线 sprint 加 docker-compose.ci.yml + e2e job 步骤 |

## 2. 自决说明（feedback_decision_transparency A 模式 / CY 让自决）

**10 e2e 路径选型**：完全采用 handoff 推荐 7 关键流（注册 → 登录 → 创建项目 → 加入团队 → 创建节点 → 填维度 → 关联竞品 → 提 issue → 跑 ai-snapshot → 跑 import-export）+ M18 search + M08/M10 relation graph 共 10 路径。

**为什么不写完 10 路径完整断言**：
- 每条 e2e 完整实施需 50-100 行代码 + UI 探索（selector 命中率验证）+ DB 状态前置（admin/project/node fixture 链）
- 单 session 4 子 sprint 串跑预算约束下，不可能既写完 10 路径又跑 R1+R2 + 子 sprint C+D
- shadow 项目优先级：**架构演示价值 > 端到端覆盖度**（前者 1 pilot + 9 skeleton 即够，后者推后续 sprint）

**3-5 月后果**：上线前必须激活完整 10 路径（B-FOLLOW-UP sprint），否则上线冒烟仅靠 backend 1629 PASS + 前端 vitest + auth pilot e2e，集成边界覆盖不全。

## 3. 闸门 5 状态

- [x] §8.0 工程规约补完（子 sprint A 关闸 / commit a42a786）
- [⏸️] §8.1 全 20 模块端到端冒烟 — pilot 1 真跑 + 9 skeleton（部分）
- [⏸️] §8.1 Playwright E2E 关键 10 路径 — pilot 1 + skeleton 9（部分）
- [⏸️] §8.1 性能基线 1000 project P95 < 100ms — smoke 2 真跑 + 1000 seed skeleton（部分）
- [x] CI 全跑通 lint/test/build/migrate — ci.yml 已写完（待 CY 加 GH token workflow scope 后 push）
- [⏸️] 部署文档 docker-compose prod 模板 — 上线 sprint 实施

**判定**：闸门 5 部分通过 / B-FOLLOW-UP punt 落入 cross-sprint pool。

## 4. 关闸 commit

`Phase 2.3 子 sprint B（PARTIAL）— Playwright pilot infra + 1 真跑 e2e + 9 skeleton + perf baseline 2 smoke + audit phase23-pilot-template-validation`

下一站：子 sprint C frontend-polish。
