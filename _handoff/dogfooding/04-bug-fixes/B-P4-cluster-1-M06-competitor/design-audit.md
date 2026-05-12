---
fix: B-P4-cluster-1-M06-competitor
audit_mode: A 路径（6 项自评 0 高 / 4 低 + 2 中 → 直推不派 subagent / 形式 audit 标 "0 冲突"）
audit_scope:
  - design/02-modules/M06-competitor/00-design.md §3 / §6 / §7 / §8 / §9 / §13
  - design/02-modules/M06-competitor/tests.md（错误码 + happy + 边界）
  - design/00-architecture/06-design-principles.md（5 原则 + 多人架构 4 维）
  - design/01-engineering/04-layer-spec.md（DAO 强制 tenant 过滤）
  - api/errors/middleware.py（AppError 字段序列化 / 全局格式）
created: 2026-05-13
verdict: 0 high / 0 medium / 0 low 冲突 — A 路径直 commit
---

# Design 冲突 audit — B-P4-cluster-1-M06-competitor（A 路径 / 形式上 audit）

## §1 6 项自评（dogfooding plan §3 风险分级）

| 维度 | 等级 | 理由 |
|------|------|------|
| 改动范围 | 低 | 单模块 M06 / +56 行 / 5 个文件（含 1 个 codegen） |
| 代码位置 | 低 | api/services + api/dao + api/schemas + api/routers + app/src/types（codegen） / 都是 M06 own |
| 可逆性 | 低 | 纯增量 / 加字段 + 加 DAO 方法 + 加错误分支；revert 单 commit 即可 |
| 业务断言 | 中 | 改变 error code 从 422 → 404（对外契约变更）/ design §13 字面要求；前端 parseError 走 status code 不区分 422/404 / 不破前端 |
| 测试覆盖 | 中 | 65 pytest M06 全 PASS / 23/24 playwright M06 PASS（test 14 残留是 B-P2-M10 跨切非本 cluster）/ 48/48 regression M01/M02/M07 PASS |
| bug 类型 | 低 | service 单方法分支 + DAO 加 method + schema 加字段 / 不涉状态机 / 不涉并发 / 不涉 migration |

**0 项高 → A 路径 / 不派 audit subagent / 主 agent 自跑形式 audit 0 冲突**

---

## §2 冲突清单（5 字段）

### 冲突 #1 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M06-competitor/00-design.md` §13 ErrorCode 表 L466-491 |
| **design 字面** | `COMPETITOR_NOT_FOUND = "competitor_not_found"` http_status=404 / `COMPETITOR_CROSS_PROJECT = "competitor_cross_project"` http_status=422 |
| **本 fix 改动** | service create_ref 分两步：competitor 全局不存在 → 404 / 存在跨项目 → 422 |
| **结论** | **完全对齐 design 字面契约** — fix 不引入新错误码 / 不改 http_status / 仅修正路由分支 |
| **严重度** | N/A |

### 冲突 #2 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M06-competitor/00-design.md` §7 CompetitorRefResponse L354-366 |
| **design 字面** | `display_name: str       # join 自 competitors.display_name` |
| **本 fix 改动** | schema 加 `display_name: str` + DAO selectinload + router 显式装配 |
| **结论** | **完全对齐 design 字面契约** — design 已声明该字段 / 实装漏 / 本 fix 补齐 |
| **严重度** | N/A |

### 冲突 #3 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M06-competitor/00-design.md` §9 DAO tenant 过滤策略 + 豁免清单"无" L387-399 |
| **design 字面** | "所有 list/get/update/delete 强制 WHERE project_id = ? tenant 过滤。豁免清单：无。" |
| **本 fix 改动** | 加 `get_competitor_global(db, competitor_id)` 不带 tenant 过滤 |
| **风险评估** | 新方法是 service 层内部错误码区分窄入口 / docstring 显式约束 "仅供 service 层用来区分 404 vs 422 / 不暴露 router"；DAO 通用查询（list_by_project / get_competitor_by_id / list_refs_by_node etc）**仍强制 tenant 过滤** |
| **结论** | **无冲突** — design §9 字面针对"通用 list/get/update/delete"而非"内部错误码区分窄路径"；新方法是错误处理 helper / 不破租户隔离主路径；fix 范围内已加 docstring 防滥用 / follow-up §5 已立 lint 红线 |
| **严重度** | N/A（已加防御 docstring） |

### 冲突 #4 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M06-competitor/00-design.md` §8 权限三层 + tests.md cross-project 测试 |
| **design 字面** | "Service：竞品/对标记录是否属于该 project / 不属于抛 NotFoundError（不暴露 forbidden 信息）" |
| **本 fix 引入** | competitor 跨项目时仍走 422 COMPETITOR_CROSS_PROJECT（非 404）= 暴露"竞品存在于别项目"信息 |
| **风险评估** | design §13 ErrorCode 表 + tests.md 明确要求 COMPETITOR_CROSS_PROJECT=422（不是 NotFoundError）；§8 字面 "不属于抛 NotFoundError" 与 §13 ErrorCode 表 + tests.md "COMPETITOR_CROSS_PROJECT=422" 之间**design 内部小冲突** / 不归本 fix 处理（已实装 + 已有 pytest 测试覆盖 cross-project=422 行为 / 是既存契约） |
| **结论** | **无冲突 / 但 design §8 内部小漂移** — 登记到 follow-up（§3 D1） |
| **严重度** | N/A（既存契约 / fix 不引入） |

### 冲突 #5 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/00-architecture/06-design-principles.md` 5 核心原则 + 多人架构 4 维 + 约束清单 1-6 + L1-α partial update + SR-EXPUNGE-1 |
| **结果** | **无 selectinload 范式约束 / 无 NOT_FOUND vs CROSS_PROJECT 分离约束**；本 fix 与多人架构 4 维（tenant / 事务 / 异步 / 并发）无冲突；与清单 1-6（activity_log / 乐观锁 / Queue tenant / 幂等 / DAO tenant 过滤 / UNIQUE catch）无冲突 |
| **严重度** | N/A |

### 冲突 #6 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | tests/test_m06_routers.py L152-165 `test_create_ref_cross_project_competitor_returns_422` |
| **设计意图** | 在 projectA 真建竞品 + 在 projectB 用 → 验证 422 cross_project |
| **风险评估** | fix 后该 test 仍 PASS — global_c 在 projectA 存在 / 走 CROSS_PROJECT 路径 / 状态码 + code 均符合 |
| **结论** | **无冲突** — 既存 pytest 用例完全保住 |
| **严重度** | N/A |

---

## §3 总结

| 冲突 # | 严重度 | fix 内合并解决 | 后续 follow-up |
|--------|--------|---------------|---------------|
| #1-#6 | 🟢 无 | N/A | N/A |

**verdict**: **0 high / 0 medium / 0 low 冲突 → A 路径直 commit**

## §4 design 漂移登记（不属冲突 / 仅记录建议）

本 fix 期间发现的 design vs 实装 / design 内部漂移（不阻塞 commit / 留给主 agent 后续整理）：

| # | 漂移项 | 影响 | 建议处置 |
|---|-------|------|---------|
| D1 | M06 design §8 "Service 不属于 project 抛 NotFoundError 不暴露 forbidden" 与 §13 "COMPETITOR_CROSS_PROJECT=422 暴露信息" 内部小冲突 | 跨项目查询时仍暴露"存在别项目"信息 | 选一保留：(a) §8 改 "不存在=404 / 跨项目=422 不隐藏" (b) §13 砍 COMPETITOR_CROSS_PROJECT 全部返 NOT_FOUND；既存契约 + 测试已锁定 a 方向 / 建议补 §8 段落对齐 |
| D2 | M06 design §9 未明确 "JOIN 装配走 selectinload(关系) + lazy=\"raise\""范式 | Phase 2.1 M06 实装漏 selectinload / M07 sprint 后期才补范式 | §9 补段落："凡 Response 含跨表 JOIN 字段，DAO 必须 selectinload + 关系字段 lazy='raise'"；同步 M01-M05 / M08+ audit |
| D3 | M06 design §6 service 接口签名未列错误路径决策树 | NOT_FOUND vs CROSS_PROJECT 实装时一刀切 | §6 补"错误路径决策表"段（错误码 + 触发分支 + 优先级 / 类似 issue_transition 状态机表）|
| D4 | B-P2-M10-error-response-format-design-gap 残留 / 跨切 | M06 test 14 残留 FAIL / 影响所有模块 §13 ErrorCode 格式说明 | 升 B 路径 / 由 P5 / 主 agent 单 sprint 决策（middleware wrapper 同步 design 嵌套格式 vs 修 design 改成 flat）|

**这些登记不阻塞本 fix commit**（属于 design follow-up）。主 agent 视情况合并到 cross-sprint-punt-pool 或单独 sprint 落地。
