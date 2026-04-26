---
title: CI/CD 规划（最小集占位决策）
status: accepted-minimal
owner: CY
created: 2026-04-20
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
