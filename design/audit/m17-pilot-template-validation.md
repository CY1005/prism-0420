---
title: M17 sprint pilot-template-validation（living tracker）
status: in-progress
owner: CY
sprint: M17
started: 2026-05-09
purpose: |
  M17 AI 导入 sprint（R-X1 第二实例 / 异步 Queue / 闸门 2.6 mini-sprint 合并）实证记录。
  本文件只记 M17 启动期工作（4 大必做项）+ sprint 实施期产出。
---

# M17 sprint pilot-template-validation

## M17 启动期（2026-05-09）

### 闸门 2.5 reconcile pass

**三栏强制分类输出**（M02 元教训 + 闸门 2.5 字面 / 第十四数据点）：

#### A 栏（机械可做 / 直接落 / 8 项）

| # | 项 | 状态 |
|---|---|---|
| A1 | 闸门 3.4 L1 总则修订 — 加 "context budget pressure" 触发例外段（双前置条件 + 3 配套承诺）+ bypass log #2 标 ✅ review 完成 | DONE 2026-05-09 |
| A2 | 闸门 2.6 Queue Scaffold 补完 — `api/queue/base.py` 加 `TaskPayload` 基类 + dummy 子类 + 12 pytest（user_id/project_id 强制 / extra='forbid' / round-trip）| DONE 2026-05-09 |
| A3 | cross-sprint punt #4 SSE 重新评估 — M16 BackgroundTasks + 自起 SessionLocal 已替代长持 SSE / 标 RE-EVALUATE 降级 high → low | DONE 2026-05-09 |
| A4 | M17 design §14.5 sprint review 拆分计划段补完 — 5+ 子片表 + R1=3 subagent + R2=1 合并 Opus + L3 实证子选项 | DONE 2026-05-09 |
| A5 | conftest fixture 预查 — 已有 `make_cold_start_task`（M11）+ 9 个 fixture / M17 不重复立 helper / 十二连规则延续 | DONE 2026-05-09 |
| A6 | R-X1 失败补偿 helper 抽出 — `api/services/orchestrator_helpers.py:compensation_session` async context manager + 4 pytest（yield 行为 / aclose 协议 / 独立 session 实例）；M11 ColdStart 后续迁移留到 M17 sprint 子片 0 prep | DONE 2026-05-09 |
| A7 | cross-sprint punt #11 立规防御未来 — `06-design-principles.md` 加清单 6（service 层 INSERT 凡 UNIQUE 必 catch IntegrityError 转业务异常 + ci-lint R15 grep 守护立规）；M02 project 已实装 / M04 dimension 修存量推迟 | DONE 2026-05-09 |
| A8 | 本会话范围限定 — 启动期 + commit + push + 新会话进 M17 子片 0；遵守 usage_budget v3 单会话 $10 + bypass log #2 配套（spawn subagent 必新 context） | DONE 2026-05-09 |

#### B 栏（CY 拍板）

**0 项**（5 步分层走完后所有候选都归 A 或 C 栏）

#### C 栏（已自我消解）

- **C1**: SYSTEM_USER_UUID 常量 — M16 commit 2273f90 已落 `api/queue/base.py:22`，M17 直接 import
- **C2**: M17 design §3-§13 — P5 audit 4 finding M16 之前已收口 + R4-3a 非常规态登记规约落地
- **C3**: cross-sprint punt #1+#2+#5 — M16 sprint 已关闭
- **C4**: 闸门 2.5 reconcile pass 输出本身 — 即此三栏

### 启动期元教训新教训 1 条 sink memory

#### 新失效信号：reconcile pass 列 B 栏前未穷举 L1 锁规

**首发** 2026-05-09 M17 sprint 启动期 reconcile pass。AI 输出 B 栏 3 项给 CY，CY 反问
「先分析，到底是哪些规则打架，重新归纳是哪一级，是不是分层没分对」一击命中。

**根因**：分层判断时**先列候选再查规则**（先入为主把"看起来要拍"的项归 B 栏，再补
查规则发现 L1 已锁），应**先穷举 L1/L2 锁规再列候选**（规则先于候选）。

**走完 5 步 step 1-2 后实证**：3 项 B 栏候选全部归 A 或 C 栏：

| 原 B 项 | 真实命中规则 | 归类 |
|---|---|---|
| B1 R-X1 真修方案 a/b/c | feedback_rx1_orchestrator_design L1 字面已锁「失败补偿 commit boundary 必独立 connection 或显式 SAVEPOINT」+ M12 元自审"既锁范式裁决型 P1 不让 CY 拍" | A6（自决 a 独立 SessionLocal）|
| B2 cross-sprint 处理范围 a/b/c | cross-sprint-punt-pool 维护规约 L1 字面「约定时机命中即做」+ M17 触发新立规即首个 caller | A7（机械推出本期处理 #7+#11）|
| B3 本会话范围 a/b/c | feedback_usage_budget v3 实施期单会话 $10 + 「不要同一会话连续跑多个 sprint」+ bypass log #2 配套承诺：M17 必恢复 spawn subagent | A8（机械推出 a 启动期 + 新会话进 M17）|

**修法 sink** memory `feedback_problem_layered_analysis.md` 失效信号段：
reconcile pass 输出 B 栏前必跑 grep checklist（feedback memory / ADR design 公共段 /
cross-sprint punt 池 / bypass log），命中任一 → A 或 C 栏。**B 栏 = 0 时禁列 B 栏**
（不为给 CY 拍而拍 / "凑选项"是失效信号）。

### 启动期产出物清单

- `design/00-phase-gate.md`：闸门 3.4 L1 总则触发例外段从 1 类扩到 3 类（a ≥80% SKIP /
  b context budget pressure 双前置 + 3 配套 / c 临时合并 = bypass log）
- `design/99-comparison/phase-gate-bypass-log.md`：触发线 review 标 ✅ 完成 + 修订内容
  指针；触发线不复位继续累计
- `design/00-architecture/06-design-principles.md`：清单 6（service 层 INSERT
  IntegrityError 转换通用规则 + ci-lint R15 待立 + 3 类豁免显式声明）
- `design/02-modules/M17-ai-import/00-design.md`：§14.5 sprint review 拆分计划段
  （5+ 子片 + R1+R2 安排 + L3 实证子选项 + 合规性自审）
- `_handoff/cross-sprint-punt-pool.md`：punt #4 SSE 标 RE-EVALUATE 降级
- `api/queue/base.py`：TaskPayload 基类 + extra='forbid' + UUID coerce
- `api/queue/__init__.py`：导出 TaskPayload
- `api/services/orchestrator_helpers.py`：compensation_session async context manager
  + scaffold 简化决策 4 字段注释 + R-X1 第二实例对照表
- `tests/test_queue_base.py`：12 pytest（强制字段 / extra forbid / coerce / round-trip /
  dummy 子类继承）
- `tests/test_orchestrator_helpers.py`：4 pytest（yield AsyncSession / aclose 协议正常
  退出 + 异常退出 / 独立 session 实例）
- memory `feedback_problem_layered_analysis.md`：新失效信号段（reconcile pass B 栏 0 时禁列）

### 启动期回归数据

- 1063 + 16 = **1079 PASS** / 4 skipped / 0 fail / ruff 净
- ci-lint: R13-1 116 + L12 + L13 + R14 全过
- 文件变更：4 新（queue/base 升级 / orchestrator_helpers + 2 tests）+ 5 改（phase-gate /
  bypass-log / cross-sprint punt 池 / M17 design §14.5 / design-principles 清单 6）

### M17 sprint 子片 0 prep 待续

- M11 ColdStartOrchestratorService._mark_failed + cold_start_router 期望套路迁移到
  compensation_session helper（A6 scaffold 简化决策 ③ ④ 字段触发）
- 测试 fixture 改造：tests/conftest.py 加 M17 sprint 子片 0 prep 的 SessionLocal
  monkeypatch 范式（join_transaction_mode='create_savepoint' 兼容）
- M17 子片 1 model + alembic（import_tasks + import_task_items + ActionType+N + TargetType+N）

---

## M17 sprint 实施期（待 sprint 内回写）

待 R1 + R2 spawn subagent 跑完后填充：

- R1 命中数据 / R2 命中数据
- R-X1 第二实例 vs 第一实例对照表实证（同步 vs 异步 / commit boundary helper 复用）
- 闸门 2.5 三栏第十二次 B 栏 0 项实证（M05-M17 十二连）
- §14.5 L3 实证子选项回写
