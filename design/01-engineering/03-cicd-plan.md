---
title: CI/CD 规划
status: accepted
owner: CY
created: 2026-04-20
v2_revision: 2026-05-07  # §6 加 early adopter 触发条款引用（横切判断前置 + §7.1/§7.2 分支），详见 ../audit/time-dimension-blindspot-2026-05-07.md
v3_revision: 2026-05-09  # §8 Phase 2.3 §8.0 补完决策（A1-A4 + 部署触发 + secrets 清单 + codegen drift CI guard）
accepted: 2026-04-26
phase: Phase 2.0 启动决策（A4.1）+ Phase 2.3 §8.0 补完
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

## 5. 完成度判定

- [x] CI 平台决策（A GitHub Actions）
- [x] 流水线阶段框架（5 节点 + Phase 2.3 加 Deploy）
- [x] 触发条件（PR + push + schedule）
- [x] **Phase 2.3 §8.0 补完**（见 §8 / commit Phase 2.3 子 sprint A）：完整 ci.yml + 缓存 + secrets + 部署触发 + codegen drift guard

---

## 6. accepted-minimal 状态的 early adopter 触发条款（2026-05-07 时间维度盲区沉淀）

本文档为 accepted-minimal 状态——Phase 2.0/2.1/2.2 业务开发够用，详细补完推到 Phase 2.3 §8.0。

若 M02-M19 任一模块在 §8.0 补完之前需要本文件 minimal 范围**之外**的 CI 能力（如某模块 sprint 需提前用 GitHub Actions secrets 注入 / matrix 多版本 / 跨 repo workflow），sprint 启动 reconcile pass 期间必须按 [`05-security-baseline.md §7`](./05-security-baseline.md#7-accepted-minimal-状态的-early-adopter-触发条款2026-05-07-时间维度盲区沉淀2026-05-07-后续-d4-推演修订) 流程：

1. **判断前置**：能力是横切（CI 工作流 / secrets 注入机制 / runner pool 等多模块复用）还是模块特定？CI 能力**绝大多数都是横切**——默认走横切分支
2. **三选一**：横切走 §7.1（A 完整提前 / B' 部分提前 + 横切实装 / C 推迟）；模块特定走 §7.2

**禁止**：把 CI 能力（如 secrets 注入流程 / GitHub Actions workflow 文件 / 缓存策略）挂在某业务模块名下——这是横切关注，必须建在横切层（`.github/workflows/` 由本文档 own）。

> 触发条款完整定义、判断前置、横切 vs 模块特定分支、决策登记格式、清单维护在 05-security-baseline.md §7 主表，本文件仅引用。

---

## 8. Phase 2.3 §8.0 补完决策（2026-05-09 / 子 sprint A）

> **scope**：03-cicd minimal → accepted。**自决原则**：shadow 项目 + 单人 + 上线最简，trade-off 透明记录，复杂方案做触发条件保留。

### 8.1 ci.yml 完整步骤（A1）

**决定**：✅ **单 workflow（`.github/workflows/ci.yml`）+ 多 job 并行**

- 单 workflow 简化运维（vs 拆 lint/test/build 三 workflow）
- job 并行加速（lint/typecheck 与 test 并行 / build 与 migrate 并行）
- Python matrix：仅 3.12（与 dev/prod 统一；多版本 matrix 是开源库需要，单部署应用不需）
- Node 单 22.x（与 app/.nvmrc 一致）

**job 拓扑**：
- `lint`（ruff check + ruff format --check + eslint + prettier --check）
- `typecheck`（mypy api/ + tsc --noEmit app/）
- `test-backend`（pytest + coverage）
- `test-frontend`（vitest run）
- `build`（pnpm build + docker build api/）
- `migrate-dryrun`（alembic upgrade head --sql）
- `codegen-drift`（export OpenAPI → 跑 codegen → diff 检测漂移）— SR-P22-2 sink #4 立项
- `e2e`（Playwright headless / 子 sprint B 接入）
- `perf-baseline`（pytest tests/perf / 子 sprint B 接入）

**3-5 月演进**：模块数膨胀 → 拆 path-filter（仅改 api/ 不跑 frontend test）；多人协作 → 加 required reviewers + branch protection。

### 8.2 缓存策略（A2）

**决定**：✅ **actions/setup-python + uv cache + actions/setup-node + pnpm cache**（不引 docker buildx 缓存本期）

- uv cache 命中率高（pyproject.toml 稳定时几乎 0 安装时间）
- pnpm cache 命中率高（pnpm-lock.yaml hash key）
- docker layer cache（buildx + GHA cache backend）：上线频率低、本期仅 build 验证镜像可构建，不发布；保留 §8.3 上线 sprint 加

**风险**：stale cache 偶发；规避：cache key 含 lockfile hash + 兜底 `actions/cache@v4` 自动 GC。

### 8.3 secrets 注入（A3）

**决定**：✅ **GH 仓库级 secrets → env: 字段注入 / 关键 prod secrets 走 `environment: prod` 二次门控**

**必备 secrets 清单**：
```
DATABASE_URL                # PG 连接（CI 用 service container / prod 用 environment）
TEST_DATABASE_URL           # CI test
REDIS_URL                   # arq + cache
JWT_SECRET                  # ≥32 字符
INTERNAL_TOKEN              # P2 HMAC
ENCRYPTION_KEY              # AES-256-GCM (base64 32B)
OPENAI_API_KEY              # M13 LLM provider
ANTHROPIC_API_KEY           # M13 LLM provider 备选
EMBEDDING_PROVIDER          # M18 mock / openai
SENTRY_DSN                  # §8.7 错误聚合
GHCR_PAT                    # docker registry push（上线 sprint 加）
TG_BOT_TOKEN + TG_CHAT_ID   # 04-observability §8.6 告警通道
```

**注入方式**：
```yaml
env:
  DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
```

**prod environment 二次门控**：deploy job 加 `environment: prod` → GitHub 强制人工 approve。

**3-5 月演进**：多人协作 → 切 Doppler/Vault（见 05-security §8.5）。

### 8.4 部署触发条件（A4）

**决定**：✅ **三条触发链路**

| 触发 | 行为 | 环境 |
|------|------|------|
| `push` to `main` | 跑 lint/test/build/migrate-dryrun，**不部署** | — |
| `tag v*` 推送 | 跑全套 + 部署到 prod（`environment: prod` 人工 approve）| prod |
| `workflow_dispatch` | 手动触发任何分支跑全套 / 选 staging or prod | staging/prod |

**为什么不 main → staging 自动部署**：shadow 项目当前 staging 不存在；staging 上线 sprint 再起。不预置噪音。

**3-5 月演进**：staging 上线 → main push 自动 staging；prod 仍 tag-only。

### 8.5 OpenAPI codegen drift CI guard（punt #4 关闭）

**决定**：✅ **CI 加 `codegen-drift` job，PR 阶段必跑**

- 步骤：`uv run python -m api.scripts.export_openapi > /tmp/openapi.json` → `cd app && pnpm codegen` → `git diff --exit-code app/src/lib/api-types.ts`
- 失败信号：开发者改了 backend schema 没跑 codegen → CI red → PR 拒合并
- 立此 guard 防 sprint 子片漂移（SR-P22-2 sink #4 已记）

### 8.6 决策登记总览

| 决策 | 选 | 理由 |
|------|----|------|
| A1 ci.yml | 单 workflow + 多 job 并行 + Python 3.12 单 / Node 22 单 | shadow 简化运维 |
| A2 缓存 | uv cache + pnpm cache（无 docker layer）| 高命中 / 0 build push 频率 |
| A3 secrets | GH repo secrets → env: 注入 / prod environment 门控 | 单人足够 / 多人切 Doppler |
| A4 触发 | main push CI / tag 部署 prod / workflow_dispatch backup | 上线 sprint 时增 staging |
| 8.5 codegen guard | PR 阶段强制 diff exit-code | 防 schema 漂移 |
