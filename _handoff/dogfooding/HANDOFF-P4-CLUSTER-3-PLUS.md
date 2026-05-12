---
title: dogfooding sprint P4-cluster-3+ / P5 完成 handoff
status: living-doc
owner: CY
created: 2026-05-13
purpose: 当 Claude 用量撞 weekly cap 时，新 session 从这里接手把 dogfooding sprint 跑完
trigger: "继续 dogfooding sprint" 或 CY 直接复制本文件 Prompt 0 到新 session
---

# Dogfooding Sprint — P4-cluster-3+ / P5 接手 Handoff

## Prompt 0（CY 复制到新 session）

```
继续 prism-0420 dogfooding sprint。

第一步必读：
1. /root/workspace/projects/prism-0420/_handoff/dogfooding/HANDOFF-P4-CLUSTER-3-PLUS.md（本文件 / 全图）
2. /root/workspace/projects/prism-0420/_handoff/dogfooding/progress.md（权威进度）
3. /root/workspace/projects/prism-0420/_handoff/dogfooding/03-bug-queue.md（OPEN bug 池）
4. /root/workspace/projects/prism-0420/_handoff/dogfooding/00-plan.md（5 phase plan + D 风险分级 + 3 路径 commit 决策）
5. /root/workspace/projects/prism-0420/_handoff/dogfooding/prompts/phase2-case.md（spec 写法范式 / 含 Next.js 4 坑 + SSE + WS + XYFlow 范式发现）

按 HANDOFF-P4-CLUSTER-3-PLUS.md 的 cluster 顺序串行跑。每 cluster 完后 commit + push + CI watch / 然后启下一个。最后跑 P5a + P5b。
```

---

## 1. 项目背景

**prism-0420** = Prism Shadow 项目 / 设计前置 → AI 实现 / GitHub: https://github.com/CY1005/prism-0420

**Dogfooding sprint** = 2026-05-12 启动 / 全功能测试 / 把"测试通过"水位推到"真用得起来"水位。trigger_bug: 创建项目后跳 login（已 FIX_DONE）。

### Sprint 完成度（2026-05-13）

| Phase | 状态 | 数据 |
|-------|------|------|
| P0 preflight | ✅ | 00-plan + 3 prompts + dir 结构 |
| P1 testpoint | ✅ | 21 文件 / 2327 testpoint / commit 期 P1 |
| P2 case | ✅ | **22 spec / 505 tests** / commits cf25cb9 + 57c0116 + 42f02c1 + fb496e2 |
| P2-close | ✅ | seed fixture opt-in 改造 / commit fb496e2 |
| P3 executor | ✅ | **488/505 PASS (96.6%) / 17 FAIL** / commit 52f4530 |
| P4 闭环 | 🟡 | 4 prelim FIX_DONE + cluster-1 M06 双 fix（commit 033ea64 + e8b041f）/ cluster-2 跑中 / 剩 cluster 3-6 |
| P5 final | ⏸ | P5a regression + P5b STAR v0.4 报告 |

### Commit 链路（全 sprint）

| Commit | 内容 | CI |
|--------|------|----|
| (P1) | 21 testpoint 文件 | ✅ |
| `cf25cb9` | trigger_bug fix（cookie Path=/） + list-projects search loader（dead re-export 删）+ phase2 prompt + audit 报告 + spec.ts batch1 部分 | 6/6 GREEN |
| `57c0116` | workspace-no-dims（OverviewNoDimensionsError 兜底）+ M11 validation-hang（cold_start_service commit 时序） | 9/9 GREEN |
| `42f02c1` | P2 batch 2-5 spec（12 spec + 3 cross-cutting / 495 tests） | GREEN |
| `fb496e2` | seed_full_project fixture opt-in（withEnabledDim + withFileNode） | GREEN |
| `52f4530` | P3 executor 全套真路径 / 05-regression-results.md | GREEN |
| `033ea64` | P4-cluster-1 M06 双 fix（competitor 404 + display_name JOIN） | GREEN |
| `e8b041f` | bug-queue sha backfill | GREEN |
| `<cluster-2 待>` | M18 422→400 + M03 type-immutable + M03 DELETE-projects | TBD |

---

## 2. 当前 in-flight

### Cluster-2（已 spawn / 待通知）

**模块**：M18 search + M03 module-tree
**Bug 数**：3（B-P2-M18 422→400 + B-P2-M03 type-immutable + B-P2-M03 DELETE-projects-missing）
**路径**：A + A + B（M03 DELETE 触发 B 路径 / audit 自跑）
**Cost cap**：$4
**Status**：等通知

新 session 进入时第一步：`git log --oneline -5` 看 cluster-2 是否已 commit / push 完。如已完 → 进 cluster-3。如未完 → 等通知或检查 03-bug-queue.md 看 2 bug 是否已移 FIX_DONE。

---

## 3. 剩余 cluster 详细（接手清单）

### Cluster-3：M04 + M07 命名/契约漂移（A 路径独立 fix）

**3 bug**：
1. **B-P2-M04-cross-node-tenant-read-gap**
   - 现象：GET `/dimensions` 用 projectA URL + projectB nodeId 返 200 空 items 而非 design §8 声称的 404
   - 根因：`api/routers/dimension_router.py` list_by_node 跳过 `_check_node_belongs_to_project`（注释"只读 P3 跳过"）
   - 修法：list_by_node 加 _check_node_belongs_to_project → 跨 project 返 404 NODE_NOT_IN_PROJECT

2. **B-P2-M04-activity-log-action-type-naming-gap**
   - 现象：activity_log `action_type` 实际复合命名（"dimension_record_created"）/ design §10 声称单词（"create"）
   - 修法（二选一 / 评估 design / 实装一致性）：
     - (a) **改实装**：activity_log 写入用 "create" / "update" / "delete" / 影响多模块同步漂移（高风险 / B 路径）
     - (b) **改 design**：design §10 改成复合命名 / target_type+action 一体（低风险 / 跟 cc-C subagent 实证一致 / R14 命名规约符合）
   - 推荐 (b) — design 跟实装一致性优先 / 不破 dogfooding 价值（dogfooding 抓的是 design vs 实装漂移 / 改 design 是合理 sync）

3. **B-P2-M07-error-details-field-naming**
   - 现象：POST transition 422 details 字段 `from_status/to_status` / design §13 + tests.md ER2 要求 `current/target`
   - 根因：`api/services/issue_service.py` raise ValidationError details 用 from_status/to_status
   - 修法：改 details key 为 current/target（design 字面优先 / spec test 用 current/target 断言）

**fix 范围**：
- M04: `api/routers/dimension_router.py` 加 _check_node_belongs_to_project + 改 action_type（按 b 方案改 design 而非实装 / spec 已用宽松 assertion）
- M07: `api/services/issue_service.py` raise 改 key

**Test 验证**：
```bash
cd app/ && pnpm exec playwright test e2e/dogfooding/M04-feature-archive.spec.ts e2e/dogfooding/M07-issue.spec.ts
# M04 期望 25/25 PASS（之前 25/25 / 不变 / 仅修 cross-node 残留 FAIL）
# M07 期望 38/38 PASS（之前 38/38 / 仅修 transition 残留）
```

**Cost cap**：$4

**Commit 模板**：
```
dogfooding fix P4-cluster-3 — M04 cross-node 404 + activity_log naming sync + M07 transition details

Risk: low(A 路径全 / 3 项独立改动)
Test: M04 25/25 / M07 38/38 / regression M01/M02 PASS
Action_type naming 选 design sync 方案（与 cc-C cross-cutting 实证一致 / R14 命名符合）
RCA: _handoff/dogfooding/04-bug-fixes/B-P4-cluster-3-M04-M07/rca.md
```

---

### Cluster-4：cc-A + cc-B + P3 新发现（A+B 混合）

**4 bug**：
1. **B-P2-cc-A-account-lockout-design-drift**
   - 现象：design + M01 §7 声称无 rate limit / backend 实装 5-strike + 15min lockout
   - 修法：sync M01 design §7 + 06-frontend-spec / 加 lockout 段（不删 backend 实装 / 5-strike 是安全增强）

2. **B-P2-cc-A-empty-body-pydantic-422**
   - 现象：POST `/auth/logout` + `/auth/refresh` body 缺失返 raw Pydantic 422 / 内部字段名泄漏
   - 修法：Pydantic schema 加默认值（empty body 合法）或 router 层包装 error 用 flat wrapper
   - 注：这跟 cluster-5 M10 error 格式同根源 / 可合到 cluster-5 一起做

3. **B-P2-cc-B-analyze-rx3-cross-tenant-leak**
   - 现象：POST `/analyze/{pid}/{nid}` 跨 project nodeId 返 HTTP 200 + SSE error 而非 404/422
   - 根因：`api/routers/analyze_router.py` 或 AnalyzeService 进 SSE 前未 _check_node_belongs_to_project
   - 修法：路由层前置 check → 跨 project 返 404 NODE_NOT_IN_PROJECT

4. **B-P3-M13-save-btn-shows-on-error**
   - 现象：M13 spec test 'save 按钮在 error 状态仍出现' FAIL
   - 根因：`app/src/app/projects/[projectId]/analysis/page.tsx` save button render 条件不含 error state check
   - 修法：button visible 条件 `&& !isError`

5. **B-P3-M17-ws-invalid-jwt-close-code**
   - 现象：M17 WS invalid JWT 没收到 1008 close frame
   - 根因：`api/routers/import_router.py` WS endpoint reject JWT 前 close code 不对
   - 修法：accept 前先验 JWT → 失败 close(1008) 字面对齐 RFC + design §7

**fix 范围**：
- cc-A drift: 改 design 文档（不动 product）
- cc-A empty-body: 改 schema 默认值 / 推 cluster-5 合并
- cc-B leak: 改 analyze_router 加 check
- M13 save-btn: frontend 改 condition
- M17 WS: backend ws endpoint 改 close code

**Cost cap**：$5

---

### Cluster-5：M10 error 格式 + cc-A empty-body（B 路径 / 影响所有模块）

**核心 bug**：B-P2-M10-error-response-format-design-gap

- 现象：backend `api/errors/middleware.py _payload()` 返 flat `{"code":...,"message":...,"details":{}}` / design §13 声称嵌套 `{"error":{"code":...}}`
- 影响：所有模块的 error response 格式漂移 / cluster-1 M06 test 14 + 多 cross-cutting spec 同根因
- 修法二选一：
  - (a) **改实装包嵌套**：middleware.py `_payload` 改返 `{"error":{"code":...,"message":...}}` / frontend parseError 需同步改回读 error.code（之前 cookie fix 已改成读 code 字段 / 这里要回滚 + 加 error wrapper）
  - (b) **改 design 文档**：design §13 改成 flat（实装为准）/ 不破前端兼容
- 推荐 **(b)** — 前端 parseError 已适配 flat / 改 design 文档不破产品 / 跟之前 06-frontend-spec L96 cookie path sync 同模式

**Bonus 合修**：
- B-P2-cc-A-empty-body-pydantic-422 → 同时改 router 层 422 包装（Pydantic raw 422 → flat error 格式）

**路径**：A（如选 b 改 design）/ B（如选 a 改 middleware / 影响 100+ spec assertion + frontend）

**推荐 a 还是 b**：
- (b) 改 design：cost $2-3 / 1 commit / 0 regression 风险
- (a) 改实装：cost $5-6 / 多 commit / 需全 spec regression 验

按 dogfooding 哲学："改 design 跟实装一致 = 合理 sync" / 选 (b)

**Cost cap**：$3（选 b）/ $6（选 a）

---

### Cluster-6：design-gap candidate sync + spec-design-fix + Frontend gap punt（A 路径合并报告）

**包含**：
1. **design-gap sync**（不改 product / 仅同步 design 文档）
   - M03 面包屑 link（design §1）
   - M05 version-ops UI（design §6 4 endpoint 未接通）
   - M07 §8 UI 漂移 6 处（status badge / filter / 转换按钮 / 详情页 / node-scoped 列表 / 档案页区块）
   - M11 cold-start-page-gap（design §6 专用 page 缺）
   - M15 filter-bar / date-grouping / metadata-collapse UI 缺
   - M18 rrf-k UI gap
   - M19 export-button + node-selector design vs 实装
   - M20 member-list UI gap

2. **spec-design-fix**（改 spec 断言 / 非 prod bug）
   - M04 L138 workspace smoke（dim card defaultExpanded=hasContent 折叠态 isVisible false）
   - M11 L37/L75/L102/L659（welcome card strict mode + manual content-type）
   - M19 L57/L117（folder vs file 视图按钮期望）
   - M05 L81（folder vs file 视图）
   - 修法：改 spec 断言用 force expand / use isAttached / target file node

3. **Frontend gap punt 报告**（5 模块大 sprint 推下 Phase 2.x）
   - M12 comparison page frontend 接错
   - M13 actions stub puntResult + sse-proxy-url-broken + save-request-fields-gap + drawer-vs-fullpage
   - M14 industry-news UI 全量缺
   - M16 frontend URL gap + no polling
   - M17 actions stub + fake progress + tab-vs-wizard + fresh-project
   - 输出：`_handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md`

**Cost cap**：$3

---

### P5a regression + P5b STAR report v0.4

**P5a**：Sonnet × 1 跑全 22 spec 重跑 / cap $2

期望：
- 之前 PASS 全保 PASS
- cluster 1-6 fix 后的 FAIL 转 PASS
- Frontend gap punt 池的 spec 仍按 known FAIL（spec 顶部注释关联）

**P5b**：**Opus × 1**（CY 明确不降级 Sonnet）/ cap $6 / 写完整 STAR 报告

输出：
- `_handoff/dogfooding/05-final-report.md`
- 更新 `ai-quality-engineering/05-数据对比/phase3-data-baseline.md` 加 v0.4 dogfooding 4 维度

4 维度（plan §6）：
- **D1 testpoint 总数 / pass rate**：2327 testpoint / 505 e2e tests / init 96.6% / after-fix 接近 100%
- **D2 bug 类别分布**：契约漂移 / cookie 透传 / SWC / state machine / cross-tenant / frontend gap 等
- **D3 类似 bug 关联率**：每 bug 平均挖出 N 个同根因（如 workspace fix 覆盖 6 模块同根因）
- **D4 design-audit 命中率**：N fix 触发 audit / M 找出真冲突

---

## 4. 范式 / 红线（每 cluster 必读）

### plan §3 D 风险分级 + 3 路径

- **A 路径**：6/6 自评全低 + 改 <3 文件 + 不动 design → 直推 main
- **B 路径**：6 项任一高 OR ≥3 文件 OR 改 design/ADR/migration → 启 audit subagent（本 sprint 实证：audit 自跑省 cost）
- **C 路径**：audit 出 ≥1 high/medium 冲突 → escalate CY 拍

### Commit 范式（跟 cf25cb9 / 57c0116 / 033ea64 一致）

```
dogfooding fix P4-cluster-N — <模块> <bug 简述>

Risk: low/medium（路径 + 自评）
Test: <模块> spec PASS / regression PASS
RCA: _handoff/dogfooding/04-bug-fixes/B-P4-cluster-N-<模块>/rca.md
Audit (B 路径): _handoff/dogfooding/04-bug-fixes/B-P4-cluster-N-<模块>/design-audit.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### 三件套必产

每 cluster 输出 `_handoff/dogfooding/04-bug-fixes/B-P4-cluster-N-<模块>/`:
1. `fix.patch`（git diff）
2. `rca.md`（4 段：现象 / 根因 / 类似 grep / design 哪步漏）
3. `design-audit.md`（A 路径标 0 冲突 / B 路径完整冲突清单）

### Forbidden（违反 → 重做 / [[feedback_subagent_sprint]] §2）

- ❌ try/catch 静默吞错
- ❌ 跳过 playwright + pytest 真跑验证
- ❌ commit 前没 push / CI 红没看
- ❌ 凭印象改代码（必须先 read + grep）
- ❌ 改 Next.js 自定义版本身
- ❌ 拆多 commit（cluster 合并 commit 范式）

### 真跑 rate limit 应对

- `cd /root/workspace/projects/prism-0420 && .venv/bin/python3 scripts/_unlock_e2e_admin.py`
- 分批跑 spec / 间 30-60s
- cc-A spec **必独立跑**（末尾刻意触发 5-strike）/ 不与其它合批

### Backend / Frontend dev 环境

- 都是 CY 长跑的 pnpm dev / uvicorn / **不要 kill 或重启**
- 检查：`curl -sS -m 3 http://localhost:8000/health` + `curl -sS -m 3 http://localhost:3000`
- 如挂 → 上报 CY / 不强重启

---

## 5. OPEN bug 池速查（截至 cluster-2 spawned）

详细见 `03-bug-queue.md`。

| Cluster | Bug 数 | 模块 | 路径 | cost |
|---------|--------|------|------|------|
| 3 | 3 | M04 (2) + M07 (1) | A | $4 |
| 4 | 5 | cc-A (2) + cc-B (1) + B-P3-M13 + B-P3-M17 | A+B 混合 | $5 |
| 5 | 2 | M10 error format + cc-A empty-body | B (选 b 降到 A) | $3 |
| 6 | ~15 design-gap + 6 spec-design + 5 frontend gap punt | 全模块 | A 合并报告 | $3 |
| **总** | **~31** | — | — | **$15** |

加 P5a $2 + P5b $6 = **$23 全闭环**

---

## 6. Cost 状态（2026-05-13 16:00 left）

- **已花累计**：~$56（基于 73% weekly / 周限假设 $50-100）
- **剩工作**：$23
- **总估**：~$79

按 `feedback_usage_budget` <48h 到 reset 特殊规则 / 当前 73% → 看撞顶速率不触发档位 / 但接近边界 / 节约模式严行：
- subagent 合并 cluster
- B 路径 audit 自跑
- 单 cluster ≤$5 cap
- 不并发 spawn / 串行

如真撞 cap：剩 cluster 5+6+P5 推 reset 后跑（May 15 周二晚 6pm Tokyo 后）。

---

## 7. 关键文件路径全清单

### Sprint 文档
- `_handoff/dogfooding/00-plan.md`（5 phase plan / D 风险 / 3 路径 commit）
- `_handoff/dogfooding/progress.md`（权威进度）
- `_handoff/dogfooding/03-bug-queue.md`（OPEN bug 池）
- `_handoff/dogfooding/05-regression-results.md`（P3 init regression / 待 P5a after-fix 重跑）
- `_handoff/dogfooding/prompts/phase2-case.md`（spec 写法范式 / Next.js 4 坑 + SSE + WS + XYFlow）
- `_handoff/dogfooding/audit/`（P1→P2 闸门 audit + P2 spike 报告）
- `_handoff/dogfooding/04-bug-fixes/`（每 cluster 三件套）

### Test spec（22 文件 / 505 tests）
- `app/e2e/dogfooding/M01-user-account.spec.ts`
- `app/e2e/dogfooding/M02-project.spec.ts`
- `app/e2e/dogfooding/M03-module-tree.spec.ts`
- `app/e2e/dogfooding/M04-feature-archive.spec.ts`
- `app/e2e/dogfooding/M05-version-timeline.spec.ts`
- `app/e2e/dogfooding/M06-competitor.spec.ts`
- `app/e2e/dogfooding/M07-issue.spec.ts`
- `app/e2e/dogfooding/M08-module-relation.spec.ts`
- `app/e2e/dogfooding/M10-overview.spec.ts`
- `app/e2e/dogfooding/M11-cold-start.spec.ts`
- `app/e2e/dogfooding/M12-comparison.spec.ts`
- `app/e2e/dogfooding/M13-requirement-analysis.spec.ts`
- `app/e2e/dogfooding/M14-industry-news.spec.ts`
- `app/e2e/dogfooding/M15-activity-stream.spec.ts`
- `app/e2e/dogfooding/M16-ai-snapshot.spec.ts`
- `app/e2e/dogfooding/M17-ai-import.spec.ts`
- `app/e2e/dogfooding/M18-semantic-search.spec.ts`
- `app/e2e/dogfooding/M19-import-export.spec.ts`
- `app/e2e/dogfooding/M20-team.spec.ts`
- `app/e2e/dogfooding/_cross-cutting-A-auth-network.spec.ts`
- `app/e2e/dogfooding/_cross-cutting-B-permissions-state-async.spec.ts`
- `app/e2e/dogfooding/_cross-cutting-C-data-ai-ui.spec.ts`

### Backend / Frontend 关键路径
- Backend: `api/routers/*` + `api/services/*` + `api/dao/*` + `api/schemas/*` + `api/errors/middleware.py`
- Frontend: `app/src/app/projects/[projectId]/*` + `app/src/actions/*` + `app/src/components/*`
- Fixtures: `app/e2e/fixtures/seed.ts` + `app/e2e/global-setup.ts`

### 工具
- `scripts/_unlock_e2e_admin.py`（5-strike lockout 恢复 / 用 `.venv/bin/python3`）

### Memory 索引（接手 session 需读）
- `/root/.claude/projects/-root/memory/MEMORY.md`
- 重点 feedback：subagent_sprint / decision_codefirst_validation / usage_budget / design_first / fresh_verification / four_state_report / process_transparency

---

## 8. CY 偏好（critical）

CY 2026-05-13 明确："**不要牺牲质量**"——意味着：
- P5b STAR 报告**必须用 Opus**（不降级 Sonnet）
- B 路径 audit 必走（不跳过）
- 三件套必齐（不省 RCA）
- 真跑验证不省（不仅 tsc / --list / 必须 playwright + pytest 真跑）

如撞 cap → 推 reset 后做 / 不降级 / 不偷工。

---

## 9. 启动指令清单（接手 session）

```bash
# Step 1: cold-start
cat _handoff/dogfooding/HANDOFF-P4-CLUSTER-3-PLUS.md
cat _handoff/dogfooding/progress.md
cat _handoff/dogfooding/03-bug-queue.md | head -60

# Step 2: 状态检查
git log --oneline -10
git status --short
gh run list --limit 3 --json status,conclusion,headSha
curl -sS -m 3 http://localhost:8000/health
curl -sS -m 3 http://localhost:3000

# Step 3: 进 cluster-N（按 cluster-2 完成与否判断）
# 如 cluster-2 已完成 → 启 cluster-3（M04 + M07 命名漂移）
# 如未完 → 检查 03-bug-queue.md M18 + M03 移没移 FIX_DONE 池
```

每 cluster 完后：
```bash
git log -1 --oneline
gh run watch
git status --short
```

终结条件：
- 全 OPEN bug 处理（修 / sync design / punt 报告）
- P5a 重跑 100% PASS 或残留 punt 池真漏洞表
- P5b STAR 报告 v0.4 + phase3-data-baseline.md 加 4 维度
- 全 commit + push + CI 绿

---

**End of handoff. CY 复制 Prompt 0 到新 session 即可接手。**
