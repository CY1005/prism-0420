---
title: Phase 2.3 集成验证清债 sprint 冷启动 prompt 集合（10 子片）
status: ready
owner: CY
created: 2026-05-12（Sprint 3.1+3.2 完整收尾后 / Phase 3 v0.2 已落地）
purpose: |
  Sprint 3.1+3.2 暴露的真漏（#25 tsc 88 错 + #26 M01 admin .local TLD）的清债 sprint。
  目标 = 让 prism-0420 到达"测试通过 / 可上线"等价水位，才能跑 Phase 3 数据完整对照
  （v0.3+ 维度 + 最终报告 v0.1 草稿）。
parent:
  - _handoff/cross-sprint-punt-pool.md 真漏 #25 + #26
  - _handoff/phase23-prompts.md（原 4 子 sprint A/B/C/D 总体 plan / 本文件是其延伸 / 聚焦清债）
  - design/99-comparison/phase3-data-baseline.md（v0.2 数据 / 每子片完成后重跑看数据演化）
related:
  - scripts/phase3_data_collector.py（v0.2 数据采集脚本 / 可重跑）
  - design/00-phase-gate.md "关闸盲区立规" 段（2026-05-12 Sprint 3.2 落地）
  - design/00-roadmap.md §9 Phase 3 数据采集 + Prism 对照（4 待办项）
---

# Phase 2.3 集成验证清债 sprint 冷启动 prompt 集合

> **使用方法**：CY 开新 Claude session → 复制本文件对应子片代码块全文粘贴。
> 子片自包含（不依赖前一会话 context），cold-start friendly。

> **跨 session 顺序硬约束**：S1 → S2 → S3 → S4 → S5-S7 (任序) → S8 → S9 → S10
> S9 集成 e2e Playwright 是独立大 sprint（可跳到 Phase 3 报告后做）
> S10 Phase 3 报告 v0.1 草稿依赖 S8 数据重跑完成

---

## 计划总览

| 子片 | 范围 | 估 cost | 估时 | 依赖 | 风险 |
|---|---|---|---|---|---|
| **S1** | M01 admin .local TLD seed 修（5 min 小胜）| $0.5 | 5 min | — | 极低 |
| **S2** | backend-test 全绿（跑全 1649 测试 / `-x` 后续可能还有 fail）| $1-2 | 30-60 min | S1 | 中（可能暴露更多 fail）|
| **S3** | `permission.service.ts` 整文件删/迁（drizzle 死依赖 ≥5 错）| $1-2 | 30-60 min | S2 | 低 |
| **S4** | `project-role-context.tsx` 类型修 + 高密度死代码区清扫 | $2 | 1 h | S3 | 中 |
| **S5** | tsc 错按 module #1（M01-M07 前端调用层 / ≈25 错）| $2-3 | 1-2 h | S4 | 中 |
| **S6** | tsc 错按 module #2（M08-M14 前端调用层 / ≈25 错）| $2-3 | 1-2 h | S5（可与 S5 并行）| 中 |
| **S7** | tsc 错按 module #3（M15-M20 + 边角 / ≈15 错）| $2-3 | 1-2 h | S6（可与 S5/S6 并行）| 中 |
| **S8** | build job 100% 绿验证 + Phase 3 v0.2 数据重跑 | $1 | 30 min | S7 | 极低 |
| **S9** | 集成 e2e Playwright 启动（独立大 sprint / 可跳 / Phase 2.3 子 sprint B）| $5-10 | 1-2 天 | S8（OR 跳到 S10 后再做）| 高 |
| **S10** | Phase 3 报告 v0.1 草稿 ≥1 段 + v0.3 加重工/可追溯/关闸盲区 3 维度 | $3-5 | 1 天 | S8 | 中 |

**清债主链（S1-S8）累计估**：$11-17 / 5-9 h / 拆 4-6 个 session 跑（单 session 上限 $10）
**总累计估**：S1-S10 ≈ $19-32 / 9-13 天日历时间（看 CY 节奏）

---

## 跨 session 共用纪律（每个 prompt 内嵌引用）

每子片 cold-start 必读（顺序硬约束）:
1. **本文件「计划总览」+ 对应子片段**（看本子片范围 / 完成判定 / 失败 escalation）
2. **`_handoff/cross-sprint-punt-pool.md`**「真漏洞」段 #25 #26（看清债项当前状态）
3. **`design/00-roadmap.md`**（current_phase / 闸门 5 / Phase 3 §9 待办）
4. **`design/99-comparison/phase3-data-baseline.md`**（v0.2 baseline 数据 / 子片完成后对比）

每子片完成后状态回填（**漏一项 = 子片未完成**）:
- a. **commit msg**：`Phase 2.3 cleanup S<N> — <简短目标>`（commit 必含子片号便于 git log 追踪）
- b. **更新** `_handoff/cross-sprint-punt-pool.md`：真漏 #25 段标 PARTIAL（减 N 错）/ #26 段标 DONE
- c. **跑** `uv run python scripts/phase3_data_collector.py` 看数据演化（每次跑都是 STAR 素材：`scripts 自动 重跑 看数据变化 = 数据驱动闭环`）
- d. **更新** `_handoff/cross-sprint-punt-pool.md` 顶部 `last_updated`（含子片号）

失败 / 雪崩 escalation:
- 子片范围预估 ≤ 1 h，实际跑超 2 h → 停下来报告 CY 是否切其他子片
- 出现新真漏（非 #25/#26 范围）→ 入 cross-sprint-punt-pool.md 真漏表新行 + 不顺手修
- 单 session cost > $5 → 主动 commit 当前进度 + 让 CY 拍是否继续

数据演化期望:
- S1 → backend-test fix commit +1（pytest 至少多过 1 个测试）
- S2 → backend-test 全绿 / 1649 PASS / fix commit +N（看具体多少个 -x 后续 fail）
- S3-S7 → tsc 88 → 0 / fix commit +1（按子片标 "Phase 2.3 cleanup" 不算 fix）
- S8 → build job ✅ / v0.2 输出 prism-0420 到达"测试通过"水位

---

## 子片 S1 — M01 admin list users .local TLD seed 修

> **estimated cost**: $0.5 / **estimated time**: 5 min / **依赖**: 无（最便宜小胜）

**范围**：改 seed 系统用户 email 从 `system@internal.prism0420.local` 改成合法 TLD（如 `.example`）。
**根因**：pydantic EmailStr 用 email-validator 库严验 → 拒 `.local`（RFC 6762 mDNS 保留）。
**完成判定**：`uv run pytest tests/test_m01_admin.py::test_admin_list_users_returns_all -v` PASS。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S1：M01 admin list users .local TLD seed 修。

状态快照：
- Sprint 3.1+3.2 完整收尾 / GitHub Actions 4/6 jobs 稳定绿 / backend-test + build 仍红
- backend-test 红根因：tests/test_m01_admin.py::test_admin_list_users_returns_all → 500 (pydantic EmailStr 拒 .local TLD)
- seed 系统用户 email = "system@internal.prism0420.local"（email-validator 严验拒 RFC 6762 mDNS 保留 TLD）

冷启动按序读（共用纪律段已内化此清单）：
1. _handoff/phase23-integration-cleanup-prompts.md 「计划总览」+「子片 S1」+「共用纪律」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #26 段（M01 admin .local TLD）

本次范围：
- 找 seed 系统用户 email 的实际 hardcode 位置（grep "system@internal.prism0420.local"）
- 改成合法 TLD：推荐 system@internal.prism0420.example（.example 是 IANA 保留示例域名 / email-validator 接受）
- 不改 schema（UserListItem.email 保留 EmailStr 严验 / bug 在数据不在设计）

完成判定：
- uv run pytest tests/test_m01_admin.py::test_admin_list_users_returns_all -v → PASS
- 顺手跑 uv run pytest -x（看 -x 后续是否还有 fail / S2 范围）

完成后状态回填（共用纪律 a-d 全做）：
- commit msg: "Phase 2.3 cleanup S1 — M01 admin seed email .example TLD（撞 EmailStr 修复）"
- 更新 cross-sprint-punt-pool.md 真漏 #26 段：状态改 ✅ DONE 2026-05-XX
- 跑 scripts/phase3_data_collector.py 看数据（fix commits +1 期望）
- 更新 cross-sprint-punt-pool.md 顶部 last_updated（含 S1）

接下来子片：S2 backend-test 全绿（用 S1 的 fresh verification 触发）。
```

---

## 子片 S2 — backend-test 全绿（1649 测试无 -x fail）

> **estimated cost**: $1-2 / **estimated time**: 30-60 min / **依赖**: S1 / **风险**: 中

**范围**：S1 修了 M01，`-x` 跳过后续 fail；本子片去掉 `-x` 跑全套，列出剩余 fail 一次性修。
**完成判定**：`uv run pytest` 全 PASS（1649+ 测试）/ backend-test CI job 转绿。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S2：backend-test 全绿。

状态快照：
- S1 ✅ M01 admin .local TLD seed 修 完成（commit "Phase 2.3 cleanup S1 — ..."）
- CI ci.yml 的 backend-test 用 `pytest -x --cov=api` / -x 命中首个 fail 即停
- S1 后剩余 fail 数未知（M01 修了之后可能暴露更多 / 也可能就此全绿）

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S2」+「共用纪律」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #26（看 S1 是否标 DONE）
3. .github/workflows/ci.yml 看 backend-test job pytest 命令

本次范围：
- 跑 `uv run pytest`（不带 -x / 让所有 fail 都暴露 / collect-only 不算 / 真跑）
- 列出 N 个 fail（按 test file 分组）
- 逐个判断：
  - 配置/seed 类（同 S1 性质 / 5 min 改）→ 当场修
  - 真业务 bug（schema 漂移 / service 逻辑漏）→ 入 cross-sprint-punt-pool.md 真漏表新行 / 不顺手修
  - 测试本身 flaky / time-dependent → 标 xfail / 入 punt
- 估算总修 cost：> $3 或 > 1.5 h → 拆 S2a / S2b 两子 session

完成判定：
- 单 session `uv run pytest` exit 0 / 0 failed
- CI 上 backend-test job 转绿（push 后看 GitHub Actions）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S2 — backend-test 全绿（修 N 处 / 入 punt M 处）"
- 更新 cross-sprint-punt-pool.md：真漏入新行 / last_updated 含 S2
- 跑 scripts/phase3_data_collector.py 看数据演化（fix commits +N 期望）

接下来子片：S3 permission.service.ts 整文件删/迁（drizzle 死依赖）。
```

---

## 子片 S3 — permission.service.ts 整文件删/迁（drizzle 死依赖）

> **estimated cost**: $1-2 / **estimated time**: 30-60 min / **依赖**: S2

**范围**：`app/src/services/permission.service.ts` 仍 import `@/db` + `@/db/schema` + `drizzle-orm`——这是 Phase 2.2 子片 0 prep 删 drizzle 时漏的文件。预估≥5 个 tsc 错来自这一个文件。
**完成判定**：`pnpm exec tsc --noEmit` 不再出现 `@/db` / `drizzle-orm` 相关错。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S3：permission.service.ts 死代码处理。

状态快照：
- S1+S2 ✅ backend-test 全绿
- tsc 88 错中，permission.service.ts 单文件预估贡献 5-10 错（drizzle/@/db 死依赖）
- 子片 0 prep 删 drizzle 时漏了这个文件

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S3」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #25（看当前 tsc 错数）
3. app/src/services/permission.service.ts 全文件
4. grep "permission.service" app/src/ -r（看调用方）

本次范围（按"读真实代码再判断" / feedback_code_first）：
1. 读 permission.service.ts 看做了啥（应该是前端权限检查 helper）
2. grep 调用方：
   - 0 调用 → 直接删整文件
   - 有调用 → 看是否能用 useProjectRole context / useAuth 替代 → 改调用方 + 删此文件
   - 调用复杂 → 入 cross-sprint-punt-pool.md 真漏表 / 此子片跳过
3. 删文件后跑 pnpm exec tsc --noEmit 看错数减少

完成判定：
- pnpm exec tsc --noEmit 不再有 "Cannot find module '@/db'" / "drizzle-orm" 错
- tsc 总错数从 88 减到 ~78（预估 -10）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S3 — 删 permission.service.ts（drizzle 死依赖 / Phase 2.2 子片 0 prep 漏文件）"
- 更新 cross-sprint-punt-pool.md 真漏 #25 段：标 PARTIAL（tsc 88→78）+ 子片 S3 完成时间
- 跑 scripts/phase3_data_collector.py（fix commits 不变 / 此 commit 标 "cleanup" 不算 fix）

接下来子片：S4 project-role-context.tsx 类型修 + 高密度死代码区。
```

---

## 子片 S4 — project-role-context.tsx 类型修 + 高密度死代码区清扫

> **estimated cost**: $2 / **estimated time**: 1 h / **依赖**: S3

**范围**：`project-role-context.tsx` 状态机收窄漂移（`"owner" | "editor" | "viewer" | null` vs `SetStateAction<ProjectRole>`）+ 顺手扫"高密度死代码"区（≥3 个 tsc 错的文件）。
**完成判定**：tsc 错从 ~78 减到 ~50。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S4：project-role-context.tsx + 高密度死代码区。

状态快照：
- S3 ✅ permission.service.ts 已处理 / tsc 减约 10 错
- 当前 tsc 约 78 错（需 pnpm exec tsc --noEmit 重数确认）

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S4」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #25（看 S3 后状态）

本次范围：
1. 跑 pnpm exec tsc --noEmit 2>&1 | grep "error TS" | awk -F'(' '{print $1}' | sort | uniq -c | sort -rn | head -15
   → 出"高密度死代码"文件 top-15（按错数排序）
2. 取 top-3（每个 ≥3 错）逐个看：
   - app/src/contexts/project-role-context.tsx（状态机漂移）
   - 其他 top-2 由数据决定
3. 每个文件判断：
   - 类型漂移（最常见）→ 改类型定义
   - 死代码（Prism 拷过来 unused）→ 删
   - 真业务（含 logic）→ 入 punt
4. 完成后再跑 tsc 看错数

完成判定：
- tsc 错从 ~78 减到 ~50
- 不引入新 vitest fail（cd app && pnpm test 不破）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S4 — project-role-context + N 处死代码清扫（tsc 78→50）"
- 更新 cross-sprint-punt-pool.md 真漏 #25 段：标 PARTIAL（tsc 数 + S4 完成）
- 跑 scripts/phase3_data_collector.py

接下来子片：S5/S6/S7 tsc 错按 module 维度分批清（剩 ~50 错）。
```

---

## 子片 S5 — tsc 错按 module #1（M01-M07 前端调用层 / ≈25 错）

> **estimated cost**: $2-3 / **estimated time**: 1-2 h / **依赖**: S4 / **可与 S6/S7 并行**

**范围**：剩余 tsc 错按对应 M01-M07 模块的前端调用文件分批清。
**完成判定**：M01-M07 触及的前端文件 tsc 错全消。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S5：tsc 错按 module #1（M01-M07）。

状态快照：
- S1-S4 ✅ tsc 88 → ~50（具体看 cross-sprint-punt-pool.md 真漏 #25 最新数）
- 剩余错按文件分布看 pnpm exec tsc --noEmit | grep "error TS" | awk -F'(' '{print $1}' | sort -u

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S5」段 + 「共用纪律」
2. _handoff/cross-sprint-punt-pool.md 真漏 #25 当前状态
3. design/02-modules/M01-user-account/README.md 看 M01 前端调用边界
4. design/02-modules/M02-project/README.md ... M07-issue/README.md 类似

本次范围：
- pnpm exec tsc --noEmit | grep "error TS" 全列表
- 过滤 src/app/{auth,profile,users,projects/[projectId]/(overview|settings|members|dimensions|hierarchy),features,issues} 对应 M01-M07
- 按文件维度分批改：
  - 类型漂移 → 改类型
  - 死 import → 删
  - 真业务漏（schema 变了前端没跟）→ 改契约
- 注意"删 export 前必 grep 调用方"（phase-gate.md 关闸盲区立规）

完成判定：
- M01-M07 触及文件 tsc 错 = 0
- tsc 错从 ~50 减到 ~30

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S5 — tsc M01-M07 前端调用清扫（tsc 50→30）"
- 更新 cross-sprint-punt-pool.md 真漏 #25
- 跑 scripts/phase3_data_collector.py

接下来子片：S6 tsc M08-M14。
```

---

## 子片 S6 — tsc 错按 module #2（M08-M14 / ≈25 错）

> **estimated cost**: $2-3 / **estimated time**: 1-2 h / **依赖**: S4（可与 S5 并行）

**范围**：M08 module_relation / M10 overview / M11 cold-start / M12 comparison / M13 requirement / M14 industry_news 前端调用文件。
**完成判定**：M08-M14 触及文件 tsc 错全消 / tsc 从 ~30 减到 ~15。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S6：tsc 错按 module #2（M08-M14）。

状态快照：
- S1-S4 ✅ / S5 处理 M01-M07（如已做）
- 当前 tsc 错数看 cross-sprint-punt-pool.md 真漏 #25

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S6」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #25
3. design/02-modules/M08-module-relation/README.md / M10-overview / M11-cold-start / M12-comparison / M13-requirement-analysis / M14-industry-news 各 README

本次范围：
- pnpm exec tsc --noEmit | grep "error TS" 过滤这 6 模块对应的前端文件
- 按文件分批改（同 S5 套路：类型漂移 / 死 import / 真业务漏）
- 涉及 M11 cold-start 异步 zip 导入 / M12 对比矩阵 / M13 AI 需求分析 / M14 RSS feed 等业务

完成判定：
- M08-M14 触及文件 tsc 错 = 0
- tsc 错从 ~30 减到 ~15

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S6 — tsc M08-M14 前端调用清扫（tsc 30→15）"
- 更新 cross-sprint-punt-pool.md 真漏 #25
- 跑 scripts/phase3_data_collector.py

接下来子片：S7 tsc M15-M20 + 边角。
```

---

## 子片 S7 — tsc 错按 module #3（M15-M20 + 边角 / ≈15 错）

> **estimated cost**: $2-3 / **estimated time**: 1-2 h / **依赖**: S4（可与 S5/S6 并行）

**范围**：M15 activity-stream / M16 ai-snapshot / M17 ai-import / M18 semantic-search / M19 import-export / M20 team + 不属于任何模块的边角文件（lib / utils 等）。
**完成判定**：tsc --noEmit 全绿（0 错）。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S7：tsc 错按 module #3（M15-M20 + 边角）。

状态快照：
- S1-S4 ✅ / S5+S6 处理 M01-M14（如已做）
- 当前 tsc 错数 ~15（看 cross-sprint-punt-pool.md 真漏 #25）

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S7」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #25
3. design/02-modules/M15-activity-stream / M16-ai-snapshot / M17-ai-import / M18-semantic-search / M19-import-export / M20-team

本次范围：
- pnpm exec tsc --noEmit 全列表 / 过滤 M15-M20 + 边角（src/lib / src/utils / src/components 共享）
- 注意 M20 是新模块（不是 Prism 拷过来），错少；M15-M19 是 Prism 拷改，错可能多

完成判定：
- pnpm exec tsc --noEmit 全绿（0 errors）
- cd app && pnpm test 不破

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S7 — tsc M15-M20 + 边角清扫（tsc 全绿 / 88→0）"
- 更新 cross-sprint-punt-pool.md 真漏 #25：标 ✅ DONE
- 跑 scripts/phase3_data_collector.py

接下来子片：S8 build job 100% 绿验证 + Phase 3 v0.2 数据重跑。
```

---

## 子片 S8 — build job 100% 绿 + Phase 3 v0.2 数据重跑

> **estimated cost**: $1 / **estimated time**: 30 min / **依赖**: S7

**范围**：push 后看 CI build job 转绿 + 把 prism-0420 当前 commit 加进 MILESTONES["prism-0420"] 作为"测试通过 / 可上线"等价水位，重跑 v0.2 看完整对照。
**完成判定**：build job ✅ / Phase 3 baseline 新增"测试通过"水位数据 / commit + push 后到达 STAR 关键节点。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S8：build 全绿 + Phase 3 数据重跑。

状态快照：
- S1-S7 ✅ tsc 全绿 / backend-test 全绿
- CI 6 jobs 预期全绿（含 build）
- prism-0420 到达"测试通过 / 可上线"等价水位 → 可与 prism v1 完整对照

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S8」段
2. _handoff/cross-sprint-punt-pool.md 真漏 #25 #26（应全 ✅ DONE）
3. scripts/phase3_data_collector.py MILESTONES 配置段

本次范围：
1. push 最新 commit 触发 CI → gh run watch 看 build 转绿
2. 修改 scripts/phase3_data_collector.py MILESTONES["prism-0420"] 加新里程碑：
   ("测试通过 / 可上线", "<S8 最终 commit hash>"),
3. uv run python scripts/phase3_data_collector.py → 看完整等价对照表（4 vs 4 milestones）
4. 看最终关键数据：
   - prism-0420 到达"测试通过 / 可上线"水位的累计天数（预估 30-35 天）
   - vs prism v1 13 天
   - fix commits 终值 vs prism v1 23
   - 这是 STAR 论断的最终数据

完成判定：
- CI build job ✅
- phase3-data-baseline.md 含完整 4 vs 4 milestones 对照
- 关键数据点输出（commit + push）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S8 — CI 全绿 / Phase 3 v0.2 完整对照（prism-0420 到达 production-ready 水位）"
- 更新 cross-sprint-punt-pool.md：真漏 #25 #26 全 ✅ DONE / 顶部 last_updated
- 更新 design/00-roadmap.md current_phase："Phase 2.3 集成验证清债完成 / 下一步 S9 e2e 或 S10 报告"

接下来子片：S9 集成 e2e Playwright（独立大 sprint / 可跳）OR S10 Phase 3 报告 v0.1 草稿（推荐先做 S10）。
```

---

## 子片 S9 — 集成 e2e Playwright（Phase 2.3 子 sprint B / 独立大 sprint）

> **estimated cost**: $5-10 / **estimated time**: 1-2 天 / **依赖**: S8 / **可跳到 S10 后做** / **风险**: 高

**范围**：Playwright 跨 backend+frontend 真接通 / 10 关键路径 e2e。这是闸门 5 上线 gate 之一。
**完成判定**：app/playwright 真 e2e 10 路径 PASS（不是 mock）。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S9：集成 e2e Playwright（独立大 sprint）。

⚠️ 警告：本子片 cost $5-10 / 估 1-2 天 / 雪崩风险高（真 e2e 跨栈调试痛）。
推荐：先做 S10 Phase 3 报告 v0.1 草稿（核心 STAR 产出），S9 留到报告写完后做。
如果你现在就要做，继续读。

状态快照：
- S1-S8 ✅ CI 6 jobs 全绿 / Phase 3 数据完整对照
- 闸门 5 §8.1：集成 e2e（Playwright 跨 backend+frontend 真接通）⏳ 未做
- 当前 app/playwright 有 19 e2e（Sprint 2 关闸 / 但是 mock / 非跨栈）

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S9」段
2. _handoff/phase23-prompts.md 「子 sprint B」段（原始 e2e 规划）
3. design/00-phase-gate.md 闸门 5 §8.1
4. app/playwright/* 现有 e2e

本次范围（参考 _handoff/phase23-prompts.md 子 sprint B 详细 plan）：
- 10 关键路径 e2e 设计：login → 创建项目 → 加成员 → 加节点 → ... → 导出
- backend docker-compose up + frontend pnpm dev 真接通
- Playwright config 跨栈

完成判定：见 phase23-prompts.md 子 sprint B（10 路径 PASS）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S9 — 集成 e2e 10 路径 PASS"
- 更新 cross-sprint-punt-pool.md / design/00-phase-gate.md 闸门 5 §8.1 打钩

接下来子片：S10 Phase 3 报告 v0.1 草稿（如未做）。
```

---

## 子片 S10 — Phase 3 报告 v0.1 草稿 + 数据 v0.3 维度扩展

> **estimated cost**: $3-5 / **estimated time**: 1 天 / **依赖**: S8

**范围**：基于 S8 完整数据写 Phase 3 报告 v0.1 草稿（≥1 段）+ 给 phase3_data_collector.py 加 v0.3 维度（重工 / 可追溯 / 关闸盲区）。
**完成判定**：`design/99-comparison/phase3-report-v0.1.md`（新文件 / 报告草稿）+ 脚本 v0.3 + baseline 重跑。

```
继续 prism-0420 Phase 2.3 集成验证清债 sprint 子片 S10：Phase 3 报告 v0.1 草稿 + 数据 v0.3。

状态快照：
- S1-S8 ✅ CI 全绿 / Phase 3 数据完整对照（4 vs 4 milestones）
- 当前 baseline 含 v0.1 (开发速度+bug数) + v0.2 (等价完成度对齐) 3 维度
- v0.3 候选：重工次数 / 可追溯性 / 关闸盲区 3 维度

冷启动按序读：
1. _handoff/phase23-integration-cleanup-prompts.md 「子片 S10」段
2. design/99-comparison/phase3-data-baseline.md（v0.2 完整数据）
3. design/00-roadmap.md §9 Phase 3 数据采集 4 待办（产出对照报告 + 沉淀方法论）
4. /root/prism/docs/testing/bugs/INDEX.md「prism-0420 数据延伸」段（已落地的 4 bug 子模式 #1.b）

本次范围：

第一部分（v0.3 数据扩展）：
1. 给 scripts/phase3_data_collector.py 加 3 维度（按现有 PATTERNS + MILESTONES 风格扩展）：
   - 维度 4 重工: git log --follow + --stat 同文件 ≥2 次 ≥10 行 改动数
   - 维度 5 可追溯性: prism-0420 design/02-modules/M01-M20/audit-* commit hash → impl commit 链
   - 维度 6 关闸盲区: prism-0420 = phase-gate.md "关闸盲区立规" 段记录数；prism v1 = bug-log.md 后期修补数

第二部分（Phase 3 报告 v0.1 草稿）：
1. 新建 design/99-comparison/phase3-report-v0.1.md
2. 结构（参考 SCQA / STAR 双线）：
   - 摘要：3 句话浓缩（design-first 是【时间换质量】不是【更快】）
   - 数据：链 baseline.md 完整对照表
   - 论断：design-first 在 implementation+集成验证全周期下 fix commits = N vs v1 23 (ratio X)
   - 方法论收获：phase-gate 关闸盲区立规 / 契约漂移子模式 #1.b（已落地 Prism v1 INDEX.md）
   - 限制 / 反例：xxx
   - STAR 候选段：3-5 个面试可用素材

完成判定：
- 脚本 v0.3 跑通 / baseline.md 新增 3 维度
- phase3-report-v0.1.md 草稿 ≥1 段（核心论断段）

完成后状态回填：
- commit msg: "Phase 2.3 cleanup S10 — Phase 3 报告 v0.1 草稿 + 数据 v0.3 三维度（重工 / 可追溯 / 关闸盲区）"
- 更新 cross-sprint-punt-pool.md 顶部 last_updated（含 S10）
- 更新 design/00-roadmap.md §9 Phase 3 数据采集 [x] 产出对照报告（v0.1 草稿完成）
- 跑 scripts/phase3_data_collector.py 看最终数据

🎯 至此 prism-0420 → Phase 3 数据对照报告 v0.1 完成 / 北极星核心 STAR 母体落地。
后续 v0.2 报告（含图表 + 详细论证）留到下一 sprint / 月底前。
```

---

## 维护

- 每子片完成 → CY 复制对应代码块 + 跑 → 完成后状态回填四件套 → 通知 Claude
- 子片之间状态自动通过 cross-sprint-punt-pool.md 真漏 #25 #26 / commit msg "Phase 2.3 cleanup S<N>" 同步
- 若某子片实际范围 > 估时 2x → 拆 SNa / SNb 两子 session（feedback_session_focus / 不爆 sprint）
- Sprint 完成（S1-S10 全 ✅）后归档本文件到 `_handoff/_archive/`，下一阶段开新 sprint prompts

---

## STAR 素材产出预期（每子片完成都是一颗 STAR 候选）

| 子片 | STAR 候选 | 量化 |
|---|---|---|
| S1 | "AI 实施暴露 seed 数据契约漂移 / 5 min 修复" | 1 bug / 1 commit |
| S2 | "去 `-x` 跑全套测试 → 暴露 N 个隐藏 fail" | N bug / N commits |
| S3 | "Phase 2.2 拷代码漏文件 / 整文件级死代码处理" | tsc -10 / 1 文件删 |
| S4-S7 | "tsc 88 错按 module 维度系统清扫" | tsc 88 → 0 / N 个 PR |
| S8 | "CI 全绿 + 数据驱动验证 design-first 真值" | 6/6 jobs / 完整对照 |
| S9 | "跨栈 e2e Playwright 真接通" | 10 路径 PASS |
| S10 | **"Phase 3 报告 v0.1 落地 / 北极星 STAR 母体完成"** | 完整数据 + 报告 |

每子片完成后跑 `scripts/phase3_data_collector.py` 看数据演化——**脚本本身就是 STAR**（"我设计可重跑数据采集脚本 / 每修一批就重跑看数据 / 数据驱动闭环"）。
