---
title: CI/CD 规划（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
v2_revision: 2026-05-07  # §6 加 early adopter 触发条款引用（横切判断前置 + §7.1/§7.2 分支），详见 ../audit/time-dimension-blindspot-2026-05-07.md
accepted: 2026-04-26
phase: Phase 2.0 启动决策（A4.1）+ Phase 2.3 上线前补完
parent: ../00-roadmap.md
---

# 03 - CI/CD 规划

> Phase 2.0 阶段只决最小集（CI 平台 + 流水线节点框架），不阻塞 Phase 2.1。详细 yml 推到 Phase 2.3 上线前。

---

## 1. CI 平台

| 候选 | 优 | 缺 |
|------|----|----|
| **A GitHub Actions** | 仓库已在 GitHub / 免费额度足 / 生态最全 | 私有 runner 需自管（暂不需要）|
| B GitLab CI | 一体化 | 仓库不在 GitLab |
| C Jenkins | 灵活 | 需自管 |

**决定**：✅ **A GitHub Actions**

**理由**：仓库 `CY1005/prism-0420` 在 GitHub，零迁移成本

**替代触发**：未来仓库迁出 GitHub → 评估切

---

## 2. 流水线阶段（最小集）

```
on: [pull_request, push to main]
  ↓
1. Lint
   - ruff check api/
   - ruff format --check api/
   - eslint app/
   - prettier --check app/
  ↓
2. Type check
   - mypy api/（Phase 2.0 末期加）
   - tsc --noEmit app/
  ↓
3. Test
   - pytest api/ --cov=api（critical path 100%）
   - vitest run app/
   - 上传 coverage report（仅展示，不强制门槛 / 02-quality-spec §5）
  ↓
4. Build
   - docker build api/
   - npm run build app/
  ↓
5. Migrate dry-run（仅 PR）
   - alembic upgrade head --sql > /tmp/migration.sql（不实际执行）
```

> 注：Phase 2.3 上线前补「6. Deploy」节点。

---

## 3. CI 触发条件

- **PR**：跑 1+2+3+4+5（拒合并硬条件见 engineering-spec §13.3）
- **Push to main**：跑 1+2+3（合并后 sanity check）
- **Schedule（每日）**：跑全套（兜底防 flaky 漏判）

---

## 4. 工作流文件占位

`.github/workflows/ci.yml`（Phase 2.0 B 阶段 B1 仓库脚手架时建占位，内容 Phase 2.3 上线前补完）

---

## 5. 完成度判定（Phase 2.0 范围）

- [x] CI 平台决策（A GitHub Actions）
- [x] 流水线阶段框架（5 节点 + Phase 2.3 加 Deploy）
- [x] 触发条件（PR + push + schedule）
- [ ] **Phase 2.3 上线前补**：完整 ci.yml + secrets 管理 + matrix（多 Python 版本）+ Deploy 节点

---

## 6. accepted-minimal 状态的 early adopter 触发条款（2026-05-07 时间维度盲区沉淀）

本文档为 accepted-minimal 状态——Phase 2.0/2.1/2.2 业务开发够用，详细补完推到 Phase 2.3 §8.0。

若 M02-M19 任一模块在 §8.0 补完之前需要本文件 minimal 范围**之外**的 CI 能力（如某模块 sprint 需提前用 GitHub Actions secrets 注入 / matrix 多版本 / 跨 repo workflow），sprint 启动 reconcile pass 期间必须按 [`05-security-baseline.md §7`](./05-security-baseline.md#7-accepted-minimal-状态的-early-adopter-触发条款2026-05-07-时间维度盲区沉淀2026-05-07-后续-d4-推演修订) 流程：

1. **判断前置**：能力是横切（CI 工作流 / secrets 注入机制 / runner pool 等多模块复用）还是模块特定？CI 能力**绝大多数都是横切**——默认走横切分支
2. **三选一**：横切走 §7.1（A 完整提前 / B' 部分提前 + 横切实装 / C 推迟）；模块特定走 §7.2

**禁止**：把 CI 能力（如 secrets 注入流程 / GitHub Actions workflow 文件 / 缓存策略）挂在某业务模块名下——这是横切关注，必须建在横切层（`.github/workflows/` 由本文档 own）。

> 触发条款完整定义、判断前置、横切 vs 模块特定分支、决策登记格式、清单维护在 05-security-baseline.md §7 主表，本文件仅引用。
