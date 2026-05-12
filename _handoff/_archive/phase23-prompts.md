---
title: Phase 2.3 集成验证 + 上线准备 冷启动 prompt 集合
status: ready
owner: CY
created: 2026-05-09（Phase 2.2 100% 关闸 / 子片 5 commit 597b885 后预录）
purpose: |
  Phase 2.3 4 子 sprint 各一份独立冷启动 prompt / CY 开新 session 直接复制粘贴对应代码块。
  4 子 sprint 顺序硬约束：A → B → C → D（A 工程规约不补不能上 prod / B 集成 e2e 是上线 gate /
  C frontend-polish 可与 A/B 并行 / D perf 可推上线后）。
parent: design/00-roadmap.md §8 + design/00-phase-gate.md 闸门 5
related:
  - design/01-engineering/03-cicd-plan.md（accepted-minimal / §8.0 补完目标）
  - design/01-engineering/04-observability-plan.md（同）
  - design/01-engineering/05-security-baseline.md（同）
  - _handoff/cross-sprint-punt-pool.md（C 类 ~12 项 perf / Phase 2.2 子片 4 长尾 P22-3b-1+P22-3c-1~8+P22-4-2）
  - design/audit/p22-pilot-template-validation.md §3f §6（子片 5 关闸 scope 自决）
---

# Phase 2.3 集成验证 + 上线准备 冷启动 prompt 集合

> **使用方法**：CY 每个子 sprint 开新 Claude session → 复制对应章节代码块全文粘贴执行。
>
> **跨 session 顺序硬约束**：A → B → D（上线主链路）；C 可与 A/B 并行（独立 frontend 子 sprint）。

---

## 计划总览

| 子 sprint | 范围 | 估 cost | 估时 | 依赖 | 风险 |
|-----------|------|---------|------|------|------|
| A 工程规约 minimal 补完 | §8.0 / 03-cicd + 04-observability + 05-security 三 spec 补完 + GH Actions workflow 文件 + 选型决策 | $4-6 | 1.5-2 天 | Phase 2.2 100% ✅ | 中（决策密集 / CY 拍多次）|
| B 集成 e2e | §8.1 / Playwright 跨 backend+frontend 真接通 + 10 核心页面 golden + 性能基线 | $5-8 | 1.5-2 天 | A 完成 + 后端 alive + 前端 build 通 | 高（首次跨栈集成 / 真业务 path 启用）|
| C frontend-polish | 子片 4 长尾 10 items（P22-3b-1 抽 helper + P22-3c-1~8 命名/dead code/兼容层 + P22-4-2）| $2-3 | 0.5 天 | Phase 2.2 100% ✅ | 低（独立 frontend / 无契约影响）|
| D perf sprint 评估 | cross-sprint pool C 类 ~12 项 / 接受 / 立专门 sprint / 推上线后 | $1（评估）or $5-10（实施）| 0.5 天评估 + 1-2 天实施 | A+B 完成（先验证基线） | 中（依赖真负载数据）|

**总估**：$12-27 / 4-6.5 天 / 4 sessions（C 可与 A/B 并行多开 1 session）。

---

## 跨 session 共用纪律（每个 prompt 内嵌引用）

1. **冷启动按序读**（每 session 前 5 分钟）：
   - CLAUDE.md
   - design/00-roadmap.md §8（Phase 2.3 总纲 / current_phase 字段）
   - design/00-phase-gate.md 闸门 5
   - _handoff/next-session.md §0 状态快照
   - _handoff/cross-sprint-punt-pool.md（C 类 ~12 项 + Phase 2.2 子片 4 长尾 punt）
   - 上一子 sprint commit message（`git log -1 --format=%B HEAD`）

2. **commit 关闸**：每子 sprint 完成 → commit + push origin/main → 更新 `_handoff/next-session.md` 推荐下一子 sprint → ack CY 等"继续"

3. **usage 自检**：每子 sprint 启动时跑 `/usage` / 若周用量 >60% 主动报 / >80% 强制开新会话延后

4. **memory 必读**：feedback_subagent_sprint / feedback_design_first / feedback_decision_layering / feedback_completion_audit / feedback_code_first / feedback_usage_budget / feedback_decision_transparency

5. **R 范式适用性**：A/D 是文档/方法论决策密集 → 不走 R1+R2 / 走 feedback_decision_transparency A 模式直接 CY 拍；B/C 是工程实施 → 走 R 范式（B 全栈 e2e R1+R2 / C frontend 继承形态 R1=1+R2=1 per SR-P22-2 sink）

6. **handoff prompt grep 守护**（SR-P22-5 sink）：写本文件 prompt 块前已 grep schema/router/spec 字面 / 防 prompt 凭印象漂移

---

## 子 sprint A — 工程规约 minimal 补完（§8.0 / 上线前硬前置）

> **estimated cost**: $4-6 / **estimated time**: 1.5-2 天 / **依赖**: Phase 2.2 100% ✅

```
继续 prism-0420 Phase 2.3 子 sprint A：工程规约 minimal 补完（§8.0）。

状态快照：
- Phase 2.2 100% ✅ 597b885（D 类 #3+#15 join 装配 + 关闸 audit / 1629 PASS）
- 03-cicd / 04-observability / 05-security 三 spec 当前 accepted-minimal（仅决策占位 / 上线前必补）

冷启动按序读：
1. _handoff/phase23-prompts.md「跨 session 共用纪律」+「子 sprint A」段
2. design/00-roadmap.md §8.0（必补清单 / 三 spec 各 4 项）
3. design/00-phase-gate.md 闸门 5（Phase 2.3 → 上线 gate）
4. design/01-engineering/03-cicd-plan.md（当前 minimal 状态）
5. design/01-engineering/04-observability-plan.md（同）
6. design/01-engineering/05-security-baseline.md（同）
7. design/adr/ADR-001-shadow-prism.md §6（部署形态 / shadow 与 Prism 共存）

实施清单（feedback_decision_transparency A 模式 / CY 拍每个选型 / 三 spec 各起一段三轮决策）：

A. 03-cicd-plan 补完（4 项决策 + 工作流文件）：
- [ ] A1. .github/workflows/ci.yml 完整步骤
  - 业务场景：每次 push / PR 跑 lint + typecheck + test + build + migrate dry-run
  - 实现例子（含完整 yaml）：matrix [3.12] / steps: ruff check + ruff format --check + mypy api/ + pnpm test + pnpm build + uv run alembic upgrade head --sql
  - 完整优缺点：单一 workflow vs 拆 lint/test/build 三 workflow / 串行 vs 并行 / 触发条件
  - 3-5 月后果：单一 workflow 简单但慢 / 拆并行复杂但快；prism-0420 单人 + 低频 push → 单一 workflow 推荐
- [ ] A2. 缓存策略（pip / pnpm / docker layer）
  - actions/setup-python + cache pip / actions/setup-node + cache pnpm / docker buildx cache-from
  - 完整优缺点：cache hit 提速 vs 偶发 stale cache 调试难
- [ ] A3. secrets 注入（GH Actions secrets → env）
  - 必备 secrets 清单：DATABASE_URL / REDIS_URL / JWT_SECRET / OPENAI_API_KEY / SENTRY_DSN
  - 注入方式：env: 字段 / GH 仓库 secrets / environment-scoped secrets
- [ ] A4. 部署触发条件（main push / tag / 手动）
  - 推荐：tag 触发 prod / main push 触发 staging / 手动 workflow_dispatch backup
  - 与 03-cicd-plan §X 当前决策对照 / 不破

B. 04-observability-plan 补完（4 项决策）：
- [ ] B1. 指标采集方案选型（Prometheus / OTel / 云厂商）+ 关键指标清单
  - 业务场景：M16 ai-snapshot SSE / M17 ai-import WS / M18 embedding worker 三大异步链路必有指标
  - 实现例子：FastAPI prometheus-fastapi-instrumentator middleware + arq custom counter + Grafana dashboard
  - 完整优缺点：Prometheus 生态广 vs OTel 标准前瞻 vs 云厂商 vendor-lock
  - 关键指标：QPS / P95 / 错误率 / Queue 堆积（arq pending+running）/ embedding success rate / SSE/WS active connections
- [ ] B2. 告警阈值 + 通道（TG / 邮件）
  - 阈值：P95 > 500ms 持续 5min / 错误率 > 1% 持续 5min / Queue 堆积 > 1000 持续 10min / embedding 失败率 > 5%
  - 通道：CY TG（reuse OpenClaw push 通道）/ alertmanager / GH issue auto-create
- [ ] B3. traceId 贯穿（FastAPI middleware → arq job → 日志字段）
  - 实现例子：FastAPI middleware 注入 X-Trace-Id / structlog bind / arq job kwargs 透传
  - 与 ADR-002 Queue 消费者租户权限对照（trace_id 与 tenant_id 同 payload 字段）
- [ ] B4. 错误聚合（Sentry / 自建）选型
  - Sentry SaaS 简单 vs 自建 GlitchTip 私有但运维成本高
  - 推荐：Sentry SaaS（单人项目运维成本最低）

C. 05-security-baseline 补完（4 项决策）：
- [ ] C1. prod 密钥管理选型（Vault / Doppler / 云 KMS / GH secrets-only）
  - shadow 项目 + 单人部署 → GH secrets-only 起步 / 多人或 prod 切换时升 Doppler/Vault
- [ ] C2. 密钥轮转流程（JWT / DB / 第三方 API key）
  - JWT_SECRET 轮转：双 key 重叠期 + KID claim / DB 密码：人工切换 + downtime 接受 / 第三方 key：手动
- [ ] C3. HTTPS / CSRF / CORS / Rate limit 上线前 checklist
  - HTTPS：Caddy auto-cert / CSRF：FastAPI 不需（API token-based）/ CORS：spec 06 §2 已补 prod guard punt #1+#2 一并修 / Rate limit：slowapi middleware
- [ ] C4. 备份 + 灾恢方案（PG dump 频率 / 异地）
  - PG dump 每日 + 7 天保留 / 异地 S3 / 灾恢演习一次

D. cross-sprint pool punt 顺修（与 A/B/C 配套）：
- 子片 2 R2 punt #1+#2：CORS prod guard + cookie secure prod guard（A1+A4 配套）
- 子片 2 R2 punt #3+#5：spec 06 §2 路径前缀备注 + logout body 备注（A4 配套）
- 子片 2 R2 punt #4：OpenAPI codegen drift CI guard（A1+A2 配套 / GH Actions 加 export → codegen → diff check 步骤）

E. 关闸：
- 三 spec 全 accepted（不再 minimal）/ §8.0 4×3=12 checkbox 全 ✅
- 闸门 5 第 3+4 项 ✅（CI 全跑通 + 工程规约补完）
- commit "Phase 2.3 子 sprint A — 工程规约 minimal 补完（03-cicd + 04-observability + 05-security 三 spec accepted / GH Actions workflow / 上线前必补 12 项全 ✅）"
- 更新 _handoff/next-session.md 推荐子 sprint B

下一步子 sprint B：集成 e2e + 性能基线（§8.1）。
```

---

## 子 sprint B — 集成 e2e + 性能基线（§8.1）

> **estimated cost**: $5-8 / **estimated time**: 1.5-2 天 / **依赖**: A 完成 + 后端 alive + 前端 build 通

```
继续 prism-0420 Phase 2.3 子 sprint B：集成 e2e + 性能基线（§8.1）。

状态快照：
- 子 sprint A ✅ <commit-hash>（工程规约 minimal 补完 / CI workflow accepted）
- 后端 1629 PASS / 前端 vitest 通 / 拷贝层 eslint ignore 残留（C frontend-polish 子 sprint 清）

冷启动按序读：
1. _handoff/phase23-prompts.md「跨 session 共用纪律」+「子 sprint B」段
2. design/00-roadmap.md §8.1（5 项 checklist）
3. design/00-phase-gate.md 闸门 5
4. design/01-engineering/02-quality-spec.md §6（E2E 推 Phase 2.3 字面已锁）
5. design/00-architecture/07-capability-matrix.md（关键路径清单 / 推 10 路径选型基础）

前置确认：
- CY 跑 uvicorn 后端 alive（cd /root/workspace/projects/prism-0420 && uv run uvicorn api.main:app --reload）
- CY 跑 pnpm dev 前端 alive（cd app && pnpm dev）
- pgvector + arq + Redis docker compose up

实施清单：

A. Playwright 环境装入（前端层）：
- [ ] cd app && pnpm add -D @playwright/test
- [ ] pnpm exec playwright install chromium（其他 browser 上线后再加）
- [ ] app/playwright.config.ts：baseURL / projects: [chromium] / webServer: pnpm dev

B. 10 核心 E2E 路径选型（CY 拍 / feedback_decision_transparency A 模式）：
- 推荐 10 路径（按 capability-matrix 7 关键流：注册 → 登录 → 创建项目 → 加入团队 → 创建节点 → 填维度 → 关联竞品 → 提 issue → 跑 ai-snapshot → 跑 import-export）
- 每条 e2e 字面断言：API 200/201 + DOM 渲染含核心字段 + activity_log 追加事件 + 跨 backend+frontend 真接通

C. 关键 E2E 实装（10 文件）：
- app/e2e/01-register-login.spec.ts
- app/e2e/02-create-project.spec.ts
- app/e2e/03-create-team-and-join.spec.ts
- app/e2e/04-create-node-and-fill-dimension.spec.ts（D 类 #15 join 字段真用 / DOM 含 dimension_type_key + updated_by_name）
- app/e2e/05-link-competitor.spec.ts
- app/e2e/06-create-issue.spec.ts（D 类 #3 join 字段真用 / DOM 含 node_name + assigned_to_name）
- app/e2e/07-ai-snapshot-flow.spec.ts（M16 SSE）
- app/e2e/08-import-export.spec.ts（M19）
- app/e2e/09-search.spec.ts（M09 / M18 semantic search）
- app/e2e/10-relation-graph.spec.ts（M08 / XYFlow）

D. 性能基线（C7 测试 / capability-matrix 性能维度）：
- 1000 project seed → P95 < 100ms（GET /api/projects + GET /api/projects/{pid}/overview）
- pytest tests/perf/test_baseline.py + pytest-benchmark 跑

E. CI 全跑通（A1 workflow 含此步骤 / 验证）：
- lint + typecheck + test + build + migrate + e2e（headless）+ perf baseline 全过

F. R1+R2 范式（业务模块全栈集成 / R1=3 + R2=1 同 M02-M20 范式）：
- R1 spec+quality (Opus) + R1 reuse (Sonnet) + R1 efficiency (Sonnet) + R2 endpoint single (Opus)
- finding P1 立修 / P2 punt 进 audit/phase23-pilot-template-validation.md

G. 关闸：
- §8.1 5 checkbox 全 ✅
- 闸门 5 全 ✅（5 项）
- audit/phase23-pilot-template-validation.md 写完
- commit "Phase 2.3 子 sprint B — 集成 e2e（10 路径）+ 性能基线 + R1+R2 全栈数据点 + 闸门 5 全 ✅"
- 更新 _handoff/next-session.md 推荐子 sprint D（perf 评估）or 上线

下一步子 sprint D：perf sprint 评估 / 或直接上线。
```

---

## 子 sprint C — frontend-polish（子片 4 长尾 10 items / 与 A/B 可并行）

> **estimated cost**: $2-3 / **estimated time**: 0.5 天 / **依赖**: Phase 2.2 100% ✅

```
继续 prism-0420 Phase 2.3 子 sprint C：frontend-polish（子片 4 长尾 cleanup）。

状态快照：
- Phase 2.2 100% ✅ 597b885（子片 5 关闸 / 长尾 10 items 整批 defer 至本子 sprint）
- 10 items：P22-3b-1（withAuthRedirect 抽 helper）+ P22-3c-1~8（命名/dead code/兼容层）+ P22-4-2（isTeamOwner 死代码）

冷启动按序读：
1. _handoff/phase23-prompts.md「跨 session 共用纪律」+「子 sprint C」段
2. _handoff/cross-sprint-punt-pool.md（Phase 2.2 子片 3b/3c/4 punt 池段 / P22-3b-1+P22-3c-1~8+P22-4-2）
3. design/audit/p22-pilot-template-validation.md §3f（子片 5 关闸 scope 自决归档）
4. app/src/actions/{search,project-stats-proxy,projects,nodes,relations,panorama,analyze}.ts（withAuthRedirect 11 处分布）
5. app/eslint.config.mjs globalIgnores（拷贝层残留 / 本子 sprint 持续还债）

实施清单：

A. P22-3b-1 抽 lib/server-action-helpers.ts（11 处 withAuthRedirect）：
- 新建 app/src/lib/server-action-helpers.ts：export function withAuthRedirect<T>(fn: ServerAction<T>): ServerAction<T>
- 11 处 inline withAuthRedirect 替换为 import + wrap
- 11 处文件单测保留 / vitest 不破

B. P22-3c-1+P22-3c-2 result 类型统一（StatsResult vs ActionResult）：
- panorama / search / project-stats-proxy 双 result 类型并行 → 选 ActionResult&lt;T&gt; 统一
- 消费方 panorama 渲染层迁

C. P22-3c-3+P22-3c-4 命名规约统一：
- issues.ts: list/get/create/update/delete 前缀（listIssuesByNode / getIssueById / createIssue 等）
- competitor-references.ts: 加资源前缀（createCompetitorRef / updateCompetitorRef 等）

D. P22-3c-5 抽 lib/tree-utils.ts（findInTree 三处重复）：
- nodes.ts:282 + relations.ts inline + panorama.ts inline 三处合并
- export function findInTree<T>(tree: T[], predicate): T | null

E. P22-3c-6 export.ts ExportPayload schema（CY 拍）：
- 选项 (a) 补 ExportResponse Pydantic schema + OpenAPI 生效 / 前端 type 自动同步
- 选项 (b) 删 consumer UI 解析旧字段（更激进但简单）
- A 模式呈现完整优缺点 + 3-5 月后果 / CY 拍

F. P22-3c-7 删 logActivity / logActivityAuto no-op 兼容层：
- grep caller 全删 + 删函数 + 删 actions/activity-log.ts no-op 兼容层

G. P22-3c-8 + P22-4-2 cleanup：
- project-stats-proxy 文件级 eslint-disable cleanup anchor 删（删本文件时一并）
- isTeamOwner action 死代码删（page 直接 creator_id 推断 / 不再调）

H. eslint ignore 渐进还债：
- 每改一文件 → 移除 ignore → eslint ✓ 才 commit
- 累计移除目标：10+ 项

I. R1+R2 范式（前端继承形态 / R1=1 Sonnet + R2=1 Opus per SR-P22-2 sink）：
- R1 reuse (Sonnet) — 验剩余拷贝层 broken imports / dead code
- R2 spec (Opus) — 验本子 sprint 改动是否引入跨子片同根因漂移
- finding 处置同前

J. 关闸：
- 10 items 全标 ✅ DONE 进 cross-sprint pool（P22-3b-1 + P22-3c-1~8 + P22-4-2）
- audit/phase23-frontend-polish.md 写完（R 范式 6 数据点 / 前端继承形态收官）
- commit "Phase 2.3 子 sprint C — frontend-polish 10 items 关闭 / R 范式第 6 数据点 / 前端继承形态收官"
- 更新 _handoff/next-session.md

下一步：与 A/B 进度合并 / 等 A+B 完成后 D。
```

---

## 子 sprint D — perf sprint 评估（cross-sprint pool C 类 ~12 项）

> **estimated cost**: $1（评估）or $5-10（实施）/ **estimated time**: 0.5 天评估 + 1-2 天实施 / **依赖**: A+B 完成（先验证基线）

```
继续 prism-0420 Phase 2.3 子 sprint D：perf sprint 评估（cross-sprint pool C 类 ~12 项）。

状态快照：
- 子 sprint A ✅ + B ✅（CI + 集成 e2e + 性能基线已建）
- cross-sprint pool C 类 ~12 项性能 punt 待统一处理（元发现 #2 性能 sprint 黑洞）

冷启动按序读：
1. _handoff/phase23-prompts.md「跨 session 共用纪律」+「子 sprint D」段
2. _handoff/cross-sprint-punt-pool.md 元发现 #2（M02-M14 累计 ~12 项写"性能 sprint"）
3. _handoff/cross-sprint-punt-pool.md C 类列表（M02 batch_update UPSERT / M04 batch_get_by_nodes / M05 query 优化 / M11 size 检查 / M12 _tenant_filter 等）
4. 子 sprint B 性能基线数据（pytest tests/perf/test_baseline.py 跑出的 P95 / QPS）

实施清单（feedback_decision_transparency A 模式 / CY 拍三选项）：

A. 选项一：接受现状（不立 perf sprint）
- 业务场景：单人 prism-0420 shadow 无生产负载 / 当前基线达标 P95 < 100ms
- 完整优缺点：节省 1-2 天 / 但 12 项 punt 永久驻留
- 3-5 月后果：上线后真负载触发再做（可能需紧急 hotfix）

B. 选项二：立专门 perf sprint（实施 12 项）
- 业务场景：上线前一次性清完 / 防元发现 #2 黑洞永久化
- 实施清单（按 cross-sprint pool C 类逐项）：
  - M02 batch_update UPSERT（projects.batch_update / N+1 → 单 SQL upsert）
  - M04 batch_get_by_nodes（dimension records 批量 / 替 N+1）
  - M05 query 优化（versions.list 预 selectinload）
  - M11 cold-start size 检查（CSV 文件大小预校验）
  - M12 _tenant_filter（comparison snapshot 跨 tenant 过滤前移）
  - 其他 7 项（按 punt pool 详情逐一）
- 完整优缺点：1-2 天彻底清 / 但需先在 B 性能基线之上跑出 before/after 数据
- 3-5 月后果：上线后无 perf surprise

C. 选项三：拆分（推上线后处理）
- 业务场景：上线优先 / perf 在生产真负载验证后再决
- 完整优缺点：上线最快 / 但生产 perf 风险敞口
- 3-5 月后果：punt pool 再增"上线后 perf"项（噪音）

D. 评估输出（不论选项几）：
- audit/phase23-perf-evaluation.md 写完三选项决策 + CY 拍的选项 + 12 项 punt 的最终归宿（DONE / 接受 / 推上线后）
- 更新 cross-sprint pool C 类 ~12 项 status：DONE / ACCEPTED / DEFER_TO_POST_LAUNCH 三态分明

E. 关闸：
- 评估场景：commit "Phase 2.3 子 sprint D — perf sprint 评估（C 类 ~12 项 CY 拍 [选项 X]）"
- 实施场景（选项二）：commit "Phase 2.3 子 sprint D — perf sprint 实施（C 类 12 项全 ✅）+ before/after 数据"
- 更新 _handoff/next-session.md 推荐上线

下一步：上线（部署到 prod / Phase 3 数据采集开始）。
```

---

## 维护

- 每子 sprint 关闸 commit 后 → 本文件对应章节 status: completed + commit-hash 填回
- 4 子 sprint 全 ✅ → 闸门 5 全 ✅ → Phase 2.3 完成 → 上线 → Phase 3 数据采集

---

last_updated: 2026-05-09（Phase 2.2 100% 后预录 / 4 子 sprint prompt 全集）
