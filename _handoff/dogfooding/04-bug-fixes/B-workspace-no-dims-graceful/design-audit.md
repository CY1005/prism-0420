---
fix: B-workspace-no-dims-graceful
audit_mode: A 路径（6 项自评 0 高 / 3 中 → 直推不派 subagent / 但按 prompt 要求写一份 audit 标 "0 冲突"）
audit_scope:
  - design/02-modules/M10-overview/00-design.md（OverviewNoDimensionsError 契约 / 分母=0 早返回）
  - design/01-engineering/06-frontend-spec.md（server action + RSC 通道）
  - design/00-architecture/06-design-principles.md（5 原则 + 多人架构 4 维）
  - api/errors/middleware.py（AppError 字段序列化命名）
created: 2026-05-12
verdict: 0 high / 0 medium / 0 low 冲突 — A 路径直 commit
---

# Design 冲突 audit — B-workspace-no-dims-graceful（A 路径 / 形式上 audit）

## §1 冲突清单（4 字段）

### 冲突 #1 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/02-modules/M10-overview/00-design.md` §3 分母=0 处理时机说明（M10-B3）L251-258 |
| **design 字面** | "若返回值 == 0，立即 raise `OverviewNoDimensionsError(422)`，不进入节点聚合查询" |
| **本 fix 改动** | 前端 catch 422 + fallback /nodes endpoint / 后端 422 路径不动 |
| **结论** | **无冲突** — design 字面约束 backend service 行为 / 不约束前端如何降级；前端的合理 fallback 反而符合 design "避免半成品" 的精神（前端 fallback 给空 completion 而不是 error boundary） |
| **严重度** | N/A |

### 冲突 #2 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/01-engineering/06-frontend-spec.md` §2 + §3（SSR auth / server action / RSC 通道）|
| **结果** | 仅描述凭据透传 + 路由分层 / **无前端 error 降级 / business 422 处理约束** |
| **严重度** | N/A |

### 冲突 #3 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | `design/00-architecture/06-design-principles.md` 5 核心原则 + 多人架构 4 维 + 约束清单 1-6 + L1-α partial update + SR-EXPUNGE-1 |
| **结果** | **无前端 fallback / error code 字段命名约束**；本 fix 修 parseError `error_code` → `code` 兼容 — 与多人架构 4 维（tenant / 事务 / 异步 / 并发）无冲突；与清单 1-6（activity_log / 乐观锁 / Queue tenant / 幂等 / DAO tenant 过滤 / UNIQUE catch）无冲突 |
| **严重度** | N/A |

### 冲突 #4 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | ADR-001 单 ORM + ADR-003 + ADR-004 auth + `api/errors/middleware.py` L18 序列化字段 `code` |
| **结果** | backend 已用 `code` / 前端历史用 `error_code` 是 prism v1 拷改残留 / **本 fix 修对齐** / 不破任何 ADR 约束 |
| **严重度** | N/A |

### 冲突 #5 候选（已检 / 无冲突）

| 字段 | 内容 |
|------|------|
| **检查范围** | tests/test_m10_overview*.py + tests/test_m11_*.py + frontend src/lib/server-http-client.test.ts |
| **结果** | 后端 M10 422 单测保持 / 前端 18 单测全 PASS（含 error_code mock）/ 本 fix 不引入测试逻辑变化 |
| **严重度** | N/A |

## §2 总结

| 冲突 # | 严重度 | fix 内合并解决 | 后续 follow-up |
|--------|--------|---------------|---------------|
| #1-#5 | 🟢 无 | N/A | N/A |

**verdict**: **0 high / 0 medium / 0 low 冲突 → A 路径直 commit**

按 dogfooding plan §3 6 项自评：
- 改动范围 中 / 代码位置 低 / 可逆性 低 / 业务断言 中 / 测试覆盖 中 / bug 类型 中
- 0 项高 → A 路径 / **不派 audit subagent / 主 agent 自跑形式 audit 0 冲突**

## §3 design 漂移登记（不属冲突 / 仅记录建议）

本 fix 期间发现的 design vs 实装漂移（不阻塞 commit / 留给主 agent 后续整理）：

| # | 漂移项 | 影响 | 建议处置 |
|---|-------|------|---------|
| D1 | `design/01-engineering/06-frontend-spec.md` 未约束 server action / RSC 遇 business 422 如何降级 | 多个 module DOM 主路径撞 error boundary | 补段 "遇业务 422 必须 catch 不抛" |
| D2 | `design/02-modules/M10-overview/00-design.md` §3 未指引前端 fallback 策略 | 间接同 D1 | 补段 "前端 catch + fallback /nodes 范式" |
| D3 | frontend `parseError` 读 `error_code` vs backend 序列化 `code` 字段名漂移 | 所有 errorCode UX 分发路径都失效（拿到 null） | cross-sprint pool F-CONTRACT-1（端到端 contract test）|
| D4 | `seed_full_project` fixture 不创建 file-type node + 不启用 dimensions | 多个 DOM-SMOKE spec 假设 file-view 路径 / 撞 spec 设计偏差 | seed 改造 punt 下次 sprint |

**这些登记不阻塞本 fix commit**（属于 design follow-up）。主 agent 视情况合并到 cross-sprint-punt-pool 或单独 sprint 落地。
