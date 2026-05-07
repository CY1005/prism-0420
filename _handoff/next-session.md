---
title: prism-0420 跨 session 交接
status: living
owner: CY
last_updated: 2026-05-07 (post-M01-merge)
purpose: 上一 session 留给下一 session 的"接着做什么 + 怎么做"——避免冷启动 Claude 凭印象拍板
---

# Next-session handoff

> **冷启动 Claude 读这份**：先读本文件 → 再读 `design/00-roadmap.md` 看真实进度 →
> 再读 `design/00-phase-gate.md` 看下一闸门 → 再决定从哪条 prompt 起手。

## 0. 状态快照（更新于 2026-05-07 post-M01）

- **Phase 2.0 工程基线**：✅ 100%（B1-B10 + 决策类全 accepted；commit b91c8d5）
- **Phase 2.1 业务模块**：⏳ 5%（**M01 已实施完毕 ready for闸门 3，下一站 M02**）
- **2026-05-07 M01 sprint 闭环**（commits c1e3acc → 2704d0f + design 回写 commit pending）：
  - 5 子片全 PASS：read-only auth / PATCH me / admin endpoints / ADR-004 P2 全 / CI 守护
  - 测试 113 PASS + C9 isolated 转 PASS（共 117+ PASS / 0 xfail）
  - design / ADR 回写（M01 实施反馈）：
    - ADR-004 §3 #5 同秒边界 + §3.5 P2 信任链 + §3.6 P3 形态
    - M01 §4 R4-2 加 active→pending 禁 + 同值豁免说明
    - M01 §10 多事件原子组顺序约定 + P2 入站不写 audit 策略
  - ci-lint.sh 加 L12 守护（M01 不调 M15 activity_log_service）
  - design/audit/m01-pilot-template-validation.md（PT1-PT3 living tracker）
- **2026-05-07 session 产出**（P5 4 🔴 + F-9 收口；commits 2e93de9 + b24f049）：
  - R4-3a 非常规态登记规约落地（02-modules/README.md）：5 类 + 严格档 + 6 字段态表 + 3 字段边表
  - M01/M16/M17/M18 四模块 mermaid 按 R4-3a 回扫（pending / cancelled / partial_failed / failed 拆出登记表）
  - ADR-002 §1.1 触发方清单从 3 → 10 条，区分 Queue 与直接 SQL 形态
  - M16/M17/M18 模块端反向引用 SYSTEM_USER_UUID（M16 §9+§10+§12B / M17 §12 / M18 §10+§12D）
  - P5 audit 5 finding 标 fixed（F-1/F-4/F-6/F-7/F-9）
- **2026-05-06 session 产出**（设计前置 audit 16h）：
  - `design/audit/lessons-learned.md`（8 元教训 + 6 校准）
  - `design/audit/scaffold-design-reconcile.md`（7 对错型 seam）
  - `design/audit/full-reconcile-pass.md`（11 结构性 seam）
  - `design/audit/contracts-draft.md`（4 条对账契约）
  - `design/audit/p5-state-machine-reachability.md`（10 findings：🔴4 / 🟡3 / 🟢3）
  - `design/00-architecture/08-namespaces.md`（命名空间登记 + 业界标准）
  - 4 个 baseline-patch commit（ErrorCode value lower / ActionType CRUD split + dot→snake / ADR-002 §1.1 SYSTEM_USER_UUID / 20 模块 references frontmatter 回填）

## 1. 推荐 prompt 顺序

### Prompt 0 — 闸门 3 检查 + M02 启动（**当前推荐**）

```
继续 prism-0420，过闸门 3（M01 PR merge ready 检查）+ 启动 M02 sprint。

任务：
1. 闸门 3 检查（design/00-phase-gate.md 闸门 3 checklist）：
   - M01 5 子片 commits 已 push（c1e3acc → 2704d0f + design 回写 commit）
   - 测试矩阵 117+ PASS / 0 xfail / lint 全过 / pre-commit hooks 全过
   - design 反馈已回写 ADR-004 + M01 §4 §10
   - PT1-PT3 tracker 在 design/audit/m01-pilot-template-validation.md
2. 若闸门 3 通过，按 prompt A（重写自 M01 模板）启动 M02。

红线：
- M02 sprint 内必须给 PT1-PT3 第 1 次回写（M02 是否复用 M01 范式）
- M02 涉及 user 跨 project 关系，凭据路径声明段必须引 ADR-004（PT2 校准）
```

### Prompt A' — M01 sprint 已完成（保留作为 M02 起手模板参考）

```
继续 prism-0420，启动 M01 用户系统探针实施 sprint。

任务：按 design-first 方法论 + TDD 跑完 M01（auth pilot 模块）。

必读（按序）：
1. _handoff/next-session.md（本文件，看上下文）
2. design/00-roadmap.md（确认当前真实位置 = Phase 2.1 第 1 模块）
3. design/00-phase-gate.md 闸门 2.5（M01 sprint 启动当天必跑 reconcile）
4. design/02-modules/M01-user-account/00-design.md（含 references frontmatter）
5. ADR-001 + ADR-002 + ADR-004（M01 引用的 3 个 ADR）
6. design/audit/scaffold-design-reconcile.md（已知 7 seam，机械可做项 M01 sprint 第一 commit 内修掉）
7. design/audit/p5-state-machine-reachability.md F-1（M01 mermaid 与禁止转换表自相矛盾——sprint 内必拍 + 修）

启动顺序：
1. 闸门 2.5 reconcile pass：grep 7 seam，分类（机械可做 / 待 CY 拍 / 已自我消解）
2. M01 实施前决策包：把 design 中所有 ⚠️ 占位 + P5 F-1 整理成 A 模式清单（候选 + 优缺点 + 3-5 月后果）让 CY 拍
3. CY 拍完 → 落 design 文档 status=accepted
4. TDD 实施：tests/test_m01_*.py 先写 → router/service/dao 后填
5. 三 Agent 流水线（Implementer + Spec Reviewer + Code Quality Reviewer）每完成一类 endpoint 跑一次
6. simplify checklist 在 ≥50 行或跨 ≥2 文件改动时跑
7. PR 准备：含 M01 tests.md critical path 100% PASS evidence

红线：
- 闸门 3 要求 M01 PR merge 后才能开 M02——本 sprint 必须 merge-ready
- ADR-002 §1.1 SYSTEM_USER_UUID：M01 自身不是 cron 模块但其 activity_log 写入需统一对齐 ADR
- design 任何字段与本次 audit 产出（references frontmatter / namespace 登记）冲突时——design 是真相，audit 是约束 lint
- 决策点 A 模式呈现，禁打包；禁引导

关联：design/00-phase-gate.md 闸门 2.5 / 闸门 3 / feedback_three_agent_pipeline.md
```

---

### Prompt B — P5 audit 🔴 4 finding 收口（建议 M01 sprint 内夹带做）

```
跑 design/audit/p5-state-machine-reachability.md 的 4 条 🔴 finding 收口。

任务：
- F-1（M01 mermaid 与禁止转换表 pending→disabled 自相矛盾）：
  现在就修 design 文档——CY 决策哪边对（mermaid 还是禁止表为真），改另一边一致。
  A 模式呈现两种解读 + 各自语义后果让 CY 拍。
- F-4 / F-6 / F-7（M16 / M17 / M18 cron 模块端 0 处引用 SYSTEM_USER_UUID）：
  现在不写业务代码——在每个模块 §12 cron 段加 1 行明确指引：
  "本 cron 触发的 payload.user_id 必须用 api.queue.base.SYSTEM_USER_UUID 常量
   （ADR-002 §1.1）"。
  把规约从 ADR 落到模块 design 引用层，避免实施时漏。

红线：
- F-1 决策走 A 模式呈现；不预设答案
- F-4/F-6/F-7 不写业务代码，只补模块 design 的引用注释

关联：design/audit/p5-state-machine-reachability.md / ADR-002 §1.1 / feedback_decision_transparency.md
```

---

### Prompt C — 契约 2 + 契约 4 + M14 baseline-patch tail（M01 PR merge 后）

```
完成 design/audit/contracts-draft.md 的 4 条契约（已落契约 1 + 3，剩 2 + 4）+
M14 baseline-patch tail。

任务：
1. 契约 2（referenced_by 反向链）：5 ADR + engineering-spec §7/§8/§12
   + 02-modules/README.md R-X 25 条 → 各自尾部加 `referenced_by` 段。
   双向链格式：见 design/audit/contracts-draft.md §2 形态示例。
2. 契约 4：
   - scripts/structural-audit.sh 写 P1 + P2 + P3 自动扫
     （namespace collision / ADR×Module 矩阵 / Rule×Module 矩阵）
   - pre-commit hook 加 structural-audit
   - 02-modules/README.md 加"横向对账三轮"段（独立于纵向三轮）
3. M14 baseline-patch tail：M14 §10 5 个 action_type
   （create/update/delete/link/unlink）→ 改为 entity 前缀 + 过去式后回写
   M15 ActionType enum：news_created / news_updated / news_deleted /
   news_linked / news_unlinked。同步 namespace 登记表。

红线：
- 契约 2 / 4 形态严格对齐 contracts-draft §2 / §4，不发明新形态
- 与契约 1（references frontmatter）形成双向校验闭环

工时估计：契约 2 ≈ 6-7h / 契约 4 ≈ 3-4h / M14 ≈ 0.5h

关联：design/audit/contracts-draft.md / design/audit/lessons-learned.md
```

---

## 2. 历史 prompt（已完成，仅供追溯）

- ❌ ~~Prompt: Phase 2.0 决策类（quality-spec + engineering-spec §13）~~ → ✅ 2026-05-05 commit b91c8d5
- ❌ ~~Prompt: Phase 2.0 代码地基（5 helper + Makefile + queue scaffold）~~ → ✅ 已落地，B1-B10 全 ✅
- ❌ ~~Prompt B: P5 audit 🔴 4 finding 收口~~ → ✅ 2026-05-07 commits 2e93de9 + b24f049（含 F-9 R4-3a 模板修订一并落地）
- ❌ ~~Prompt A: M01 探针实施 sprint~~ → ✅ 2026-05-07 commits c1e3acc → 2704d0f（5 子片）+ design 回写 commit
  - 117+ tests PASS / 0 xfail / 22=22 R13-1 / L12 守护通过
  - design / ADR 回写 6 处（同秒边界 / P2 信任链 / refresh 形态 / active→pending / 同值豁免 / 多事件顺序）
  - 17 ErrorCode 新增 + 7 表 schema 落地 + ADR-004 P1+P2+P3 全打通

## 2.1 M01 sprint 后置债（不阻断 M02 启动，M02 sprint 内或后续顺手清掉）

| # | 项 | 优先级 | 触发场景 |
|---|----|------|---------|
| D1 | M03/M04/... 模块开工时验证 PT1-PT3（design/audit/m01-pilot-template-validation.md）| 🟢 | 每模块 sprint 闸门 2.5 reconcile 时 |
| D2 | tests.md A22 注释"每次记录 1 行"已被 design §10 校正为本期不写——必要时补 strikethrough | 🟢 | M01 PR review 期或下次扫 tests.md 时 |
| D3 | bcrypt 5.x deprecation warning（passlib `__about__` 缺失）| 🟢 | 升级 passlib 或换 bcrypt 直调（已是直调，仅 warning 噪音）|
| D4 | feedback_three_agent_pipeline 在本 sprint 用 main agent self-audit 替代——M02 起恢复 | 🟡 | M02 sprint 启动时 |

## 3. 维护规则

- 每次 session 结束有遗留任务 → 来这里更新 / 加新 prompt
- prompt 跑完 → 移到 §2 历史，标 commit hash + 日期
- `last_updated` 字段反映最近一次写入

## 4. 关联

- 真实进度：`design/00-roadmap.md`（权威）
- 闸门规则：`design/00-phase-gate.md`
- 协作规约：`CLAUDE.md`
- 本周方法论沉淀：`design/audit/lessons-learned.md`
