# P1 cross-cutting subagent prompt（批 5 范式 / 单 subagent / 按视角组织）

> **跟单模块版（phase1-testpoint.md / phase1-testpoint-invocation-template.md）的区别**：
> - 单模块：1 design → 1 testpoint 文件 / 视角内化在单模块边界 / 多并发
> - cross-cutting：**横切 19+ 模块** / 按**视角维度**组织 / **单 subagent** / 不重复任何模块内已写的 testpoint
>
> **触发时机**：单模块 P1 全跑完后 / 21 个模块测试点齐 / 批 1-N 已沉淀元发现 / 进入批末。
>
> **2026-05-12 批 5 实证**：238 testpoint / 18 视角 / cost ~$1.8 / 22 元发现 100% 转化 / 远低于 $3 cap + ≥80 / ≥12 视角下限。

---

## Role
P1-testpoint cross-cutting / Opus / 单 subagent / 横切 19+ 模块

## Cost cap
$3（超即 commit 当前进度 + 退出）

## Input contract（≥12 项 / 必读 / 按顺序）

1. `_handoff/dogfooding/00-plan.md`（§1 5-phase / §2 P1 行）
2. `_handoff/dogfooding/prompts/phase1-testpoint.md`（§"Cross-cutting 视角"段 / Self-check / Forbidden）
3. **`_handoff/dogfooding/progress.md` 批 1-N 累计元发现章节**（找"批 N 汇总 → 新增跨模块元发现"段 / **这是核心素材** / 不要重新推导）
4. **抽样 ≥4 个已完成 testpoint 文件**（推荐覆盖：状态机 / 异步 / 跨模读 / 跨事务 / Auth）/ 提取 H3 视角清单 + 每条 testpoint 引 design §N 风格
5. `design/00-architecture/06-design-principles.md`（5 核心 + 5 约束）
6. **全部 ADR**（`design/adr/ADR-*.md`）— cross-cutting 视角的设计前提
7. `feedback_testpoint_style.md`（**风格红线 2 条**）
8. `requirements-to-testpoints` skill 15 角度框架

## 视角组织（H2 = "测试点" / H3 = 视角 / 叶子 = 单行 testpoint）

**必含两层视角**：

### 通用 cross-cutting（来自 phase1-testpoint.md §"Cross-cutting 视角"）
auth flow / 跨 tab cookie sync / 网络断连+API 超时 / 权限三层防御 / 跨 module navigation / mobile / i18n+时区 / 性能（首屏+长列表+翻页）

### 元发现专项（progress.md 批 1-N 沉淀 / **必须覆盖否则白做**）
- R-X 横切纪律（R-X1 orchestrator / R-X2 上调下 / R-X3 跨事务签名 / DAO 必须分文件）
- 异步路径范式（SSE / BackgroundTasks / cron CAS race / arq Queue / WebSocket / Redis SET debounce / advisory_xact_lock）
- 幂等三层（idempotency_key 三元组 / advisory_xact_lock 替代 UniqueConstraint / Redis SET + content_hash PK）
- 状态机非法转换（跨多模块统一返码）
- AI Provider 集成边界（多 env 同步漂移）
- baseline-patch 时序契约（punt pool 累计触发 ≥3 处升 P1 高耦合触发点 / 元发现 #1）
- DB 部分唯一索引 race + 多表事务回滚
- cross-tenant 攻击三层防御 / tenant 豁免 N 类 / ADR 只读豁免
- activity_log 失败传播 + SYSTEM_USER_UUID
- action_type 同步漂移（Alembic N 处同步）
- filename sanitize 输出端 / 跨项目实体 422 非 403 / viewer 写端点 403 全覆盖
- schema 性死债务 / disambiguation 模式（Pydantic vs SQLAlchemy 字段映射）

## Output contract

写入：`_handoff/dogfooding/01-testpoints/_cross-cutting.md`

frontmatter 含 `scope: cross-cutting` + `references:` 列全部依赖。H1 = 模块横切名 + "业务前提（1 段）" + "测试点（H2 = 视角）"。

## Self-check（缺任一 → 重做）

1. **testpoint 总数 ≥80** / 视角 ≥12（cross-cutting 是系统级风险密集区 / 不许凑数）
2. 每 testpoint **单行**：`- [P<0/1/2>] <内容>`（不许换行 / 不许子项 / 不许"步骤"/"断言"/"业务影响"）
3. 每条**显式引来源**：design §N / ADR-XXX / progress.md 批 N 元发现 / 单模块 testpoint 文件（≥3 类混合）
4. P0 ≥30
5. **不重复单模块文件内已写的 testpoint** — 关注**多模块同时出现的模式** / 不是搬运

## Forbidden

- ❌ 子项 / 步骤 / 断言 / 业务影响（[[feedback_testpoint_style]] 红线）
- ❌ 凭印象写（必须基于 design + progress 元发现 + 单模块 testpoint 抽样）
- ❌ 重复单模块 testpoint（cross-cutting 必须真横切）
- ❌ 只写通用视角不覆盖元发现专项（**元发现是 cross-cutting 核心价值** / 不覆盖 = 白做）
- ❌ 占位 placeholder（"待补" / "如适用"）/ 真不适用就跳过 H3

## 启动 prompt 骨架（拷给 subagent）

```markdown
你是 prism-0420 dogfooding sprint 的 P1-testpoint cross-cutting subagent。
任务：为整个 M01-M20 全系统按视角而非模块生成跨模块测试点（_cross-cutting.md）。

cost cap $3。

按本文件 §"Input contract" 12 项读 → 设计视角骨架 →
按本文件 §"Output contract" + §"Self-check" + §"Forbidden" 写 →
返简短报告（≤500 字 / 含 testpoint 数 + 视角清单 + 元发现转化对照 + 风险点 top 5 + cost + escalation）。

不许并发 / 不许 commit / 不许凭印象。
```

## 元发现转化对照模板（subagent 完成时返主 agent）

完成报告必含 "**批 N 元发现转化对照**" 段 / 对照 progress.md 列的元发现条目 ✓ / 缺失项明示原因。这是 cross-cutting 价值的实证维度。

---

## 与单模块 prompt 的核心差异速查

| 维度 | 单模块（phase1-testpoint.md）| cross-cutting（本文件）|
|------|---------------------------|----------------------|
| subagent 数 | 4-5 并发 × 批 | 单 1 |
| 输入 design | 单模块 00-design.md | 全 ADR + design-principles + 19 testpoint 抽样 |
| 视角组织 | 15 角度框架（模块内） | 通用 8 视角 + 元发现专项 ≥10 |
| testpoint 下限 | ≥10 | **≥80 / 视角 ≥12** |
| 来源引用 | design §N + tests.md 编号 | design §N / ADR / progress 元发现 / 单模块文件（≥3 类） |
| 核心价值 | 模块内深度 | **多模块共性模式 + 元发现转化** |
| 实证 cost | ~$0.6-1.5 单模块 | ~$1.8 单 subagent |
