---
title: Phase 2.3 子 sprint D — perf sprint 评估
status: accepted
owner: CY
created: 2026-05-09
phase: Phase 2.3 子 sprint D
parent: ../00-roadmap.md §8 + ../../_handoff/_archive/phase23-prompts.md「子 sprint D」段
decision: 选项 C — DEFER_TO_POST_LAUNCH
---

# Phase 2.3 子 sprint D — perf sprint 评估

## 1. 背景：cross-sprint pool 元发现 #2

`_handoff/cross-sprint-punt-pool.md` 元发现 #2：M02-M14 累计 **~12 项** punt 写"性能 sprint"，但项目从无独立性能 sprint 计划。本子 sprint D 必须在 12 项漂移成永久驻留前作三选一决策。

### C 类 ~12 项清单（待决归宿）

| # | punt | 来源 | 影响 |
|---|------|------|------|
| 1 | M02 batch_update UPSERT（projects.batch_update / N+1 → 单 SQL upsert）| M02 | 多项目批量更新 N+1 |
| 2 | M04 batch_get_by_nodes（dimension records 批量 / 替 N+1）| M04 | dimension 批量查 N+1 |
| 3 | M05 query 优化（versions.list 预 selectinload）| M05 | versions list eager loading |
| 4 | M11 cold-start size 检查（CSV 文件大小预校验）| M11 | 5MB+ 文件 OOM 风险 |
| 5 | M12 _tenant_filter（comparison snapshot 跨 tenant 过滤前移）| M12 | 跨租户过滤 SQL 层下推 |
| 6 | M18 batch_backfill 真 batch INSERT FROM unnest（5 万条规模）| M18 | embedding 回填 N+1 |
| 7 | M18 cron_failure_monitor PCT 维度真实施 | M18 | 监控 3 维降为 2 维 |
| 8 | M18 worker source_text 真接 get_for_embedding | M18 | embedding garbage（占位期）|
| 9 | M18 EmbeddingTargetNotFoundError noop 转 succeeded 语义 | M18 | admin /stats gap |
| 10 | M14 list_by_node disambiguation 批量查 | M14 | news list 批量优化 |
| 11 | M16 ai-snapshot batch insert（多 step 一并落）| M16 | snapshot 落库 N+1 |
| 12 | M19 export multi-node 批量并行 | M19 | export 5 节点串行优化 |

> 实际 punt 池含部分 D 类条件触发型（#21-#24 占位期残留），与 perf 性能优化 punt 共生。
> 三选一决策按 12 项作 perf 性能优化基础对象。

## 2. 三选项 A 模式呈现

### 选项 A — 接受现状（不立 perf sprint）

- **业务场景**：单人 prism-0420 shadow 无生产负载 / 当前 1629 backend PASS / perf baseline smoke 2 PASS（DB roundtrip / ORM select 健康）
- **优**：节省 1-2 天开发时间 / 上线时间最早
- **缺**：12 项 punt 永久驻留 cross-sprint pool（元发现 #2 黑洞坐实）/ 上线后真负载触发再做（可能需紧急 hotfix）/ 上线后 punt 池继续膨胀
- **3-5 月后果**：上线后 N+1 问题在 5+ project 规模时出现 P95 漂移；用户无感（shadow 无并发）但数据对照报告 Phase 3 会失真（Prism 同期 perf 数据更难解读）

### 选项 B — 立专门 perf sprint（实施 12 项）

- **业务场景**：上线前一次性清完 / 防元发现 #2 黑洞永久化 / 在 1000 project seed perf baseline 之上跑 before/after 数据
- **实施清单**：上述 12 项逐一 + 性能 sprint 0 prep（pytest-benchmark 装 + 1000 seed fixture + perf-baseline CI job 接通）
- **优**：上线后无 perf surprise / Phase 3 数据对照报告能拿到 N+1 修复前后量化数据（**这是 shadow 项目核心 KPI**）/ 元发现 #2 黑洞关闭
- **缺**：1-2 天工作量 / **每项 punt 真做 before/after 验证需 30-60min**（12 项 × 45min ≈ 9h 实施 + R 范式 reviewer 还需 4-6h）/ 上线推迟
- **3-5 月后果**：上线无 perf 风险 / Phase 3 报告含 perf 维度

### 选项 C — DEFER_TO_POST_LAUNCH（推上线后处理）

- **业务场景**：上线优先 / perf 在生产真负载验证后再决 / shadow 项目上线本质是数据采集，先有数据再优化
- **优**：上线最快 / Phase 3 数据采集启动最快 / 真负载下能识别"哪些 punt 真触发哪些是过度担心"
- **缺**：punt pool 增"上线后 perf"专项 / 上线后若真触发需紧急 hotfix
- **3-5 月后果**：M+1 月 Phase 3 数据回流后启动 post-launch perf sprint / 12 项重新评估 keep/drop / 数据驱动决策

## 3. 自决决策：选项 C — DEFER_TO_POST_LAUNCH

### 决策依据

**自决原则**："shadow + 上线优先 + 数据驱动"。三选项中：
- A 是规避（黑洞坐实）→ 否
- B 是预防（投入 1-2 天 / 验证未发生的问题）→ 在无真负载数据时优先级低
- C 是延后（用真负载数据决定 perf 必要性）→ **shadow 项目数据采集为本 / 上线即数据**

**why C 不是 A 的伪装**：
- A 选项的核心问题是"punt 永久驻留"+"无关闸时间"
- C 选项强制设关闸时间（M+1 月 Phase 3 数据回流后启动）+ 真负载数据触发评估 → **pool 状态从 STILL_PUNT 升级为 DEFER_TO_POST_LAUNCH**（明确归宿）

**why C 不是 B 的妥协**：
- B 在"已发生 perf 问题"时是首选；当前 backend 1629 PASS 无 perf 报警 / SSE/WS pilot 在 mock 数据下健康
- shadow 项目的核心实验是"设计前置 vs VibeCoding"差异，**不是 perf 优化** — perf 数据恰好是 Phase 3 数据对照的子维度，不应抢在采集前优化

### 风险敞口（透明记录）

- **风险 R1**：上线后 5+ project 用户场景触发 #1+#2 N+1 → 紧急 hotfix
  - 缓解：04-observability §8 P95 阈值告警 > 500ms 触发 → 立即定位 → 12 项 punt 优先级排序拉对应项做
- **风险 R2**：embedding worker 真启用后 #6+#7+#8 触发 garbage 数据
  - 缓解：M18 子片 4+ 接通真业务 path 时同步触发（即 punt #21+#23+#24 关联触发链）
- **风险 R3**：Phase 3 数据对照报告 perf 维度数据不完整
  - 缓解：上线后真负载数据本身就是更好的 perf baseline（vs 1000 假 seed）

## 4. 12 项 punt 状态更新

| # | 原 status | 新 status | 触发条件 |
|---|-----------|-----------|----------|
| 1-3 | STILL_PUNT | **DEFER_TO_POST_LAUNCH** | 真负载 P95 > 500ms 告警 |
| 4 | STILL_PUNT | **DEFER_TO_POST_LAUNCH** | 真用户 5MB+ CSV 上传 |
| 5 | STILL_PUNT | **DEFER_TO_POST_LAUNCH** | 多租户场景启用 |
| 6-9 | STILL_PUNT | **关联触发链**（M18 真业务 path 启用时一并做）| 同 #21+#23+#24 |
| 10-12 | STILL_PUNT | **DEFER_TO_POST_LAUNCH** | 真业务规模触发 |

> cross-sprint-punt-pool.md 同步更新（C 类标 DEFER_TO_POST_LAUNCH / 关闸条件字面）。

## 5. 闸门 5 状态

- [x] §8.0 工程规约补完（子 sprint A）
- [⏸️] §8.1 全 20 模块端到端冒烟（B PARTIAL / pilot 1+skeleton 9）
- [⏸️] §8.1 Playwright E2E 关键 10 路径（B PARTIAL）
- [⏸️] §8.1 性能基线 1000 project P95 < 100ms（B smoke 2+skeleton / D 决策 DEFER）
- [⏸️] §8.1 CI 全跑通（A ci.yml 写完 / GH token workflow scope 缺待 CY 加 / B-FOLLOW-UP 接 e2e job）
- [⏸️] §8.1 部署文档 docker-compose prod 模板（推上线 sprint）

**判定**：闸门 5 部分通过 / 上线 sprint 立项条件 = 至少需补 e2e 完整 + ci.yml 接通 + docker-compose prod。本 sprint D 决策不阻塞上线 / 但上线后必须立 post-launch perf sprint。

## 6. 关闸 commit

`Phase 2.3 子 sprint D — perf 评估（C 类 12 项 → DEFER_TO_POST_LAUNCH / 选项 C / 上线优先 / 数据驱动）`

下一站：上线 sprint（B-FOLLOW-UP 实施 e2e 完整 + ci.yml workflow scope + docker-compose prod 模板 → 上线 → Phase 3 数据采集）。
