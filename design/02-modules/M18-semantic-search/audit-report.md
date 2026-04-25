---
title: M18 三轮 Audit 合并报告
status: draft
owner: CY (待裁决)
created: 2026-04-25
module_id: M18
related_design: ./00-design.md
related_tests: ./tests.md
related_baseline_patch: ../baseline-patch-m18.md
audit_rounds:
  - round: 1
    focus: 完整性
    reviewer: Sonnet (independent)
    findings: 0B / 2M / 3m
  - round: 2
    focus: 边界 / 矛盾 / corner case
    reviewer: Opus (independent)
    findings: 3B / 6M / 4m / 3 CY 决策
  - round: 3
    focus: 演进（半年-3年）
    reviewer: Opus (independent)
    findings: 12 演进风险 / 7 退路建议 / 半衰期 9-12 月
---

# M18 三轮 Audit 合并报告

> 3 个独立 reviewer 并行 audit，本报告主对话合并去重 + 跨轮交叉验证。**Reviewer 不附和原则**：3 轮独立读文件判断，3 处发现互证（如删除一致性 B1、模型升级回填、failure 阈值）有更高 confidence。

## 0. 执行摘要

| 严重度 | 数量 | 来源 |
|--------|------|------|
| **Blocker（accepted 前必修）** | **5** | R2: 3 / R3: 2（升级） |
| **Major（accepted 前应修）** | **13** | R1: 2 / R2: 6 / R3: 5 |
| **Minor（可推迟到 Phase 2）** | **7** | R1: 3 / R2: 4 |
| **CY 关键决策** | **3** | R2: C1-C3 |
| **演进退路（Phase 2 之前/之中实施）** | **7** | R3: R1-R7 |

**最大风险一句话**：embeddings 表缺 `modality / dim / provider` 三个字段是**结构性死局**——Phase 2 写代码前不加，未来引入图片/音频/双 provider 时要回填全表 + 重建向量索引（R3-E9）。

**审计走法建议**：先关 5 个 Blocker → CY 拍 3 个决策 → 修 13 Major → 进入 status=accepted；7 个 Minor + 7 演进退路在 Phase 2 同步实施。

---

## 1. Blocker（5 项 - 必修）

### B1 [§9 + baseline-patch 决策 5] 删除一致性事务模型自相矛盾 ★ R2

**问题**：决策 5 说 `delete_by_target` 失败"不阻塞"业务删除；§9 删除策略说"业务模块 Service 内显式调，共享外部 db session（R-X3）"——同一事务内的清理失败按 R-X3 应该 rollback 整个 begin() 块。

**矛盾**：try/except 包住 + commit 业务删除 = 破坏 R-X3 原子性；走外部 enqueue 异步清理 = 不能共享 session。

**期望（二选一明示）**：
- 选项 A：`commit 后再调 enqueue 异步清理` —— 与决策 5 一致，不再共享 session（baseline-patch M03 改动 2 的 `with db.begin()` 内调用要改）
- 选项 B：严守 R-X3 共享事务 —— delete 失败必须 rollback（推翻决策 5）

**reviewer 倾向**：A（异步清理 + zombie cron 兜底，与"派生数据失败容忍"哲学一致）

**关联文件**：00-design.md L536-543 / baseline-patch-m18.md M03 改动 2 + 决策 5

---

### B2 [§3 + Q2=B] 维度切换路径完全缺位 ★ R2

**问题**：`Vector(1536)` 写死 SQLAlchemy class。Alembic 不能在线 ALTER pgvector 列维度（需 drop+rebuild ivfflat 索引 + 全量重写）。决策 2=B "3 provider 抽象（OpenAI 1536 / bge 512 / mock）"在物理层做不到无缝切换。

**期望**：§3 显式补一段「provider 切换迁移路径」，三选一明文：
- A：停服迁移（admin 触发，全表 drop 重建）
- B：双表并行（embeddings_provider_a + embeddings_provider_b，过渡期双写）
- C：不支持运行时切换（部署期固定，承认 Q2=B 抽象仅是接口预留非运维能力）

**reviewer 倾向**：C（最 KISS，明确切 provider = 重大运维事件）

**关联文件**：00-design.md §3 L177 + §6 EmbeddingProvider 抽象段

---

### B3 [§9 + ADR-003] 规则 4 时序矛盾 ★ R2

**问题**：M18 §9 大量引用"规则 4"，但 ADR-003 尚未扩条（baseline-patch 实施顺序第 1 步才扩）。M18 status=draft 时 reviewer 无法 audit "规则 4 是否被正确应用"——规则 4 权威定义在 baseline-patch 草稿里。

**期望（二选一）**：
- 选项 A：先把 ADR-003 规则 4 扩条 accepted，再 audit M18（顺序倒过来）
- 选项 B：M18 §9 把规则 4 全文嵌入（不引用），accepted 时与 ADR-003 修订**同步**

**reviewer 倾向**：B（ADR 修订流程比 M18 audit 慢，避免阻塞）

**关联文件**：00-design.md §9 + baseline-patch-m18.md ADR-003 段

---

### B4 [§3] 缺 modality / dim / provider 字段 = 结构性死局 ★ R3

**问题**：embeddings 表 `target_type` 是业务实体类型（node/dimension_record/...），不是 modality。未来引入 image/audio embedding 时，要么扩 `target_type='node_image'` 字符串膨胀（CHECK 约束失控），要么按 modality 分表（search 路由跨表 UNION，RRF 融合层重写）。

**严重性升级理由**：
- 现在加成本 = 改 1 个 SQLAlchemy class（5 分钟）
- 半年后加成本 = 回填 50 万行 + 重建 ivfflat 索引（数小时停服）
- 这是 schema PK 锁定的**不可逆债务**，不是配置参数

**期望**：Phase 2 写代码**之前**强制 §3 加：
```python
modality: Mapped[str] = mapped_column(VARCHAR(16), default='text', nullable=False)  # 'text' | 'image' | 'audio'
dim: Mapped[int] = mapped_column(nullable=False)        # 1536 / 512 / 384 / ...
provider: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)   # 拆 model_version
# model_version 改为业务版本号（如 v1 / v2）

# 字符串约定：provider/model/version → openai/text-embedding-3-small/v1
__table_args__ = (
    CheckConstraint("modality IN ('text', 'image', 'audio')", ...),
    ...
)
```

**关联文件**：00-design.md §3 + R3 演进退路 R1+R7

---

### B5 [§6] 无 M18 整体回退路径（kill switch 缺失） ★ R3

**问题**：M09 已 superseded 路由迁 M18。运行半年后若发现混合搜索质量不如纯关键词（PRD F18 没"质量评估"机制——见 M11/E11），**没有 env flag 一键回退**。一旦 M09 代码物理删除（Phase 2 实施），回退要重写。

**期望**：Phase 2 实施前 §6 SearchService 加 env kill switch：
```python
SEARCH_MODE = os.getenv("SEARCH_MODE", "hybrid")  # 'hybrid' | 'keyword_only' | 'semantic_only'
# 入口判断 → keyword_only 模式跳过向量路径，与 PgvectorUnavailableError 同链
```

**关联文件**：00-design.md §6 SearchService + R3 演进退路 R2

---

## 2. Major（13 项 - 应修）

### M1 [§10 表格 vs 末段枚举] action_type 大小写不一致 - R1

§10 主表格写 `embedding_model_upgrade_triggered`（小写），末段 ActionType 枚举写 `EMBEDDING_MODEL_UPGRADE_TRIGGERED`（大写）。Phase 2 实现易混淆。

**修法**：主表格改为枚举成员名 `ActionType.EMBEDDING_MODEL_UPGRADE_TRIGGERED`。

---

### M2 [§13 R13-2] search 上游错误 wrap 是未决 TBD - R1

R13-2 要求"跨模块错误 wrap 为自己的 ErrorCode"。设计文档写"search 直接透传（待 audit 决定）"——属未决而非显式豁免。

**修法**：明确 ack「search 上游 ErrorCode 透传」+ 写明理由（搜索是聚合操作，上游模块 ErrorCode 用户感知更直接），或加 `SearchUpstreamError` 子类。

---

### M3 [§9 + baseline-patch] 增量路径未覆盖 batch 写入场景 - R2

M11 冷启动 1000 节点 / M17 import 5000 行，若 `batch_create_in_transaction` 内循环调 `create_node` → 1000 次 enqueue + 1000 次 Redis SET 操作连发，Redis 反成瓶颈，且 enqueued_by 边界混乱。

**修法**：baseline-patch 加第 4 enqueued_by 枚举值 `batch_import`，batch 写入路径走"事务后一次性扫差异 enqueue"模式（与 backfill 同框架），不走单条 enqueue。

---

### M4 [§11] advisory_xact_lock 缺 namespace 防御 - R2

当前 `pg_advisory_xact_lock(hashtext(target_id::text))` 单 key。未来图片/音频 embedding 加入若复用同模式 → 跨 namespace 互锁。

**修法**：现在改双 key（成本零）：`pg_advisory_xact_lock(hashtext('m18_text_embedding'), hashtext(target_id::text))`。

---

### M5 [§12D 字段⑤] 2s query embedding 超时 = P99 边界 - R2

OpenAI P99 ≈ 1.5-2s + RRF + DB ≈ 1s = 接近 3s SLA 边界。约 50% 概率破 SLA。

**修法**：query embedding 超时降到 1s + 显式声明"超时即 fallback keyword_only 不计入 SLA"。

---

### M6 [§3 + tc_error_07] current_model 启动后全 miss 场景 - R2

env 改成"未来计划但暂未上线的 model"（合法字符串）→ embeddings 表 `WHERE model_version=current` 全空 → search 仅命中关键词。tc_error_07 的"启动失败"逻辑无法捕获此场景。

**修法**：§7 search 路由加保护：`current_model` 不在 embeddings 表 model_version distinct 集合中 → 启动 warn + 自动 fallback 最近 model_version；§3 加该约束说明。

---

### M7 [§10 R10-2 文字修订连锁伤 M01] - R2

修订后条件 3 = "事件为系统级（用户无主动操作语义）"。但 M01 auth `login_attempt` 显然有用户主动操作 → M01 反而**失去**例外资格。

**修法**：文字再精修——"事件主体是**系统行为**（auth 校验 / embedding 计算）而非**业务行为**（创建编辑删除）"。把"主动操作"换成"业务行为"，能容纳 auth 与 embedding 两个 case。baseline-patch §README 修订段一并改。

---

### M8 [tests.md] 4 缺漏 case - R2

补充：
- backfill 中断恢复（admin 触发跑到 50% 服务重启 → 续跑能力）
- RRF 参数 update 时正在 search 的 race（read-after-write 一致性）
- embedding 写入 commit 后 worker 未跑的 read-after-write 显式契约（明示"5s 内能语义召回刚写内容"是**不保证**的）
- mock provider 切换后已有 OpenAI embedding 全 filter 掉的退化测试

---

### M9 [§3 SQLAlchemy] ivfflat lists=100 演进锚点缺失 - R3

50 万行规模需 lists≈500，否则召回 latency 退化 3-10×。lists 写死在 ORM `Index` 里，半年后改要 Alembic + REINDEX 锁表。

**修法**：lists 移到 env 配置；§15 加"embeddings 行数 > 50万 时触发 lists reindex 评估"演进锚点。

---

### M10 [§12D 字段⑥] failure 阈值 5%/h 与规模耦合 - R3

CY 单人时 5% = 1 条；50 用户时 5% = 100+ 条/h，告警风暴。阈值是"百分比+小时"二维死参数。

**修法**：cron 同时算"绝对值 / 百分比 / 单 project 占比"三维度，任一超过阈值告警。env 三个独立阈值。

---

### M11 [§12D 字段⑦] zombie cron 5min 全表扫演进瓶颈 - R3

50 万行规模 + 终态行 30 天才清 → 5min cron 每跑都扫几万行。

**修法**：§12D 字段⑦ 加"按时间 partition 或终态行立即归档表"演进路径；§15 加"行数 > 50万 触发分区评估"锚点。

---

### M12 [§7] search 路由 2s 超时无分级 - R3

大 project（向量索引大）天然慢，2s 阈值让大项目**经常拿不到语义结果而不自知**。

**修法**：超时事件单独计数指标埋点（即使本期不分级超时，至少有数据未来调）。

---

### M13 [§14] 搜索质量无离线评估积累 - R3

PRD F18 无质量评估机制。M18 输出 matched_by 但不记录"keyword-only / semantic-only / hybrid 三种模式同 query 对比结果"。半年后想答"RRF k=60 是不是真的比 k=80 好"——没数据。

**修法**：search 路由按 1% 采样写 `search_evaluation_log` 表（query / 三模式 top5 / user_clicked_id），半年后离线分析。这是 PRD 明显的盲点。

---

## 3. Minor（7 项 - 可推迟）

### m1 [§3] embedding_tasks.status 裸 str 注解 - R1

R3-2 第 1 重防护要求 `Mapped[StatusEnum]`。修：补 `EmbeddingTaskStatus` 枚举改注解。

### m2 [README] M18 行描述未更新 - R1

README 模块清单 M18 行仍写"brainstorming Q0-Q11 完成"，未体现 00-design.md 已完成。修：改"00-design.md draft 完成，待 audit"。

### m3 [tests.md §7] 12 ErrorCode 测试矩阵未逐一核实 - R1

`PGVECTOR_UNAVAILABLE`/`EMBEDDING_TASK_TERMINAL_VIOLATION`/`EMBEDDING_TASK_INVALID_TRANSITION` 在 tests.md 无对应明确触发 case。修：补 case 或矩阵注明"框架级不测"。

### m4 [§12D] "用户"边界未明示 - R2

字段⑥说"用户无感"+"告警 CY"，但"用户"边界没明示。修：加 1 行"用户=终端用户(viewer/editor/admin)；CY=单人运维=系统侧"。

### m5 [§3 R3-4] 候选 B 改回成本块只列了 1 个 - R2

只列了"移除 project_id 列"成本，没列"PK 含 model_version"改回成本（如果 reviewer 后续推翻 Q3=A）。修：加第二个改回成本块。

### m6 [§13] EmbeddingDeleteFailedError 反模式 - R2

声明"不抛 HTTP"但仍是 AppError 子类，其他模块 try/except AppError 可能误判。修：改为非 AppError 内部 enum 或专门 SilentFailure 基类。

### m7 [tests.md tc_concurrent_05] cache 击穿监控阈值 - R2

接受 race 但应加监控阈值"cache 击穿率 > 30% 引入 singleflight"。修：补到 tests §8 实施约束。

---

## 4. CY 关键决策（3 项）

### C1 [§12D 字段⑦ 适用边界] - R2

字段⑦"模型升级回填"是否 M18-only？图片 embedding 不一定有"模型升级"概念（CLIP-v1 升 v2 频率远低于文本 model）。

**reviewer 倾向**：现在不拆，但 §12D 字段⑦ 加"适用性条件 = 文本类高频迭代 model"。给后续图片模块明文 escape hatch；不要等 2026-10-25 半年回看才发现已经有图片模块抄歪。

**CY 选**：A 现在拆为 M18 自有节 / **B 保留 §12D 字段⑦ + 加适用性条件（reviewer 倾向）** / C 维持原样

---

### C2 [B1 删除一致性二选一] - R2

实质同 B1。**CY 选**：A commit 后异步 enqueue（reviewer 倾向）/ B 严守 R-X3 共享事务（推翻决策 5）

---

### C3 [B2 维度切换路径明文化] - R2

实质同 B2。**CY 选**：A 停服迁移 / B 双表并行 / **C 部署期固定不支持运行时切换（reviewer 倾向）**

---

## 5. 演进退路建议（7 项 - Phase 2 实施时落地）

> 已升级为 Blocker B4/B5 的 R1/R2 不重复列出。

### R3 ivfflat lists 配置化 + reindex 演进锚点 → 升 M9

### R4 failure 阈值 3 维化 → 升 M10

### R5 §12D 复用度复盘自动化（OpenClaw cron）

CY 已有 OpenClaw cron 推 bulletin 机制。建议挂 2026-10-25 自动提醒，不依赖 README 触发器手动扫。

### R6 搜索质量评估机制最小可行版 → 升 M13

### R7 model_version → provider/model/version 三段式 → 已并入 B4

---

## 6. 跨轮交叉验证（reviewer 互证 = 高 confidence）

| 议题 | Round 来源 | 互证结论 |
|------|-----------|---------|
| **删除一致性事务矛盾** | R2 B1 + R3 隐含（kill switch） | 独立发现，确实是架构问题 |
| **embeddings 表 schema 演进** | R2 B2（维度）+ R3 B4（modality/dim/provider）| 同一根源不同视角，必修 |
| **R10-2 文字修订伤 M01** | R2 M6 单点发现 | 反例必须验证（CY 自检不严） |
| **failure 阈值演进** | R2（未提）+ R3 M10 | 仅 R3 发现，是规模演进盲点 |
| **§12D 子模板复用度** | R2 C1 + R3 E8 + R3 R5 | 三处呼应，强建议自动化 |

**reviewer 不附和验证**：3 轮独立 reviewer 都未对 M18 整体设计给"全 OK"评价——证明 audit 流程有效，没有附和倾向。

---

## 7. 推进路径

### Phase 1.5（accepted 前 = 本轮 audit 闭环）

1. **CY 拍 C1 / C2 / C3** 三决策 → ✅ **2026-04-25 ack** C1=B / C2=A / C3=C
2. 主对话改 5 Blocker（B1-B5）+ 13 Major（M1-M13）→ ✅ **2026-04-25 fix v1 完成**
3. 改完 verify Agent 独立审 fix 是否撒谎（参 M16 流程）→ ✅ **2026-04-25 verify 完成**：抓出 1.5 假修 + 3 regression + 4 漏洞 + 4 新问题
4. **fix v2 主对话修 verify 发现** → ✅ **2026-04-25 fix v2 完成**（CY 决策 1=B 异维列拆分 / 2=同意 §15 修 / 3=B SilentFailure 保留+约束）
5. 主对话精修剩余 → status=draft → accepted → ⏳
5. 同步落 baseline-patch（M02/M09/M03/M04/M06/M07/M15/ADR-003/README）→ ✅ **2026-04-25 baseline-patch-m18 v2 完成**（含 batch_import 路径 + B1 删除路径修订）
6. R5 OpenClaw cron 挂上（2026-10-25 §12D 复用度复盘提醒）→ ⏳ accepted 后挂

### audit fix v1 落地清单（2026-04-25）

**5 Blocker** 全部修：
- B1 删除一致性 → C2=A commit 后异步 enqueue（§9 删除策略表 + baseline-patch M03 改动 2 + 决策 5 都改齐）
- B2 维度切换 → C3=C 部署期固定 + §3 加 Provider 切换路径表
- B3 规则 4 时序 → §9 全文嵌入规则 4，accepted 时与 ADR-003 同步生效
- B4 schema 缺字段 → §3 embeddings 表加 modality / dim / provider，PK 6 字段
- B5 无 kill switch → §6 加 SEARCH_MODE env + env 配置表

**13 Major** 全部修：
- M1 §10 表格改用 ActionType.* 枚举成员名
- M2 §13 search 上游 wrap 明示豁免 + source 标记替代防御
- M3 baseline-patch §3.5 加 batch_import enqueued_by 第 4 枚举值 + M11/M17 走 backfill
- M4 §11 advisory_xact_lock 改双 namespace key
- M5 §12D 字段⑤ query embedding 超时 1s + SLA 声明
- M6 §9 加 current_model startup sanity check + fallback latest
- M7 R10-2 文字最终版"系统行为 vs 业务行为"（M01 兼容验证）
- M8 tests.md 补 4 case（中断恢复 / RRF race / RAW 一致性契约 / mock 切换）
- M9 ivfflat lists 移到 env + §15 演进锚点
- M10 failure 阈值 3 维化（绝对 + 百分比 + 单 project）
- M11 §12D 字段⑦ partition 演进路径 + §15 锚点
- M12 §6 + env 表加超时事件埋点
- M13 §3 加 search_evaluation_log 表 + 1% 采样

**3 Minor** 落地：
- m1 EmbeddingTaskStatus 枚举 + Mapped[StatusEnum] 注解
- m2 README M18 行描述更新
- m4-m6 全修（用户边界 / 改回成本块 #2 / SilentFailure 基类）

**未落地 Minor**（推到 Phase 2 实施）：
- m3 测试矩阵 ErrorCode 逐一核实（框架级不测的明示）
- m7 cache 击穿监控阈值（在 tests.md §8 已加约束）

---

## fix v2 落地清单（2026-04-25 - verify 闭环修复）

**3 CY 决策 ack**：1=B（真做异维列）/ 2=同意修 §15 / 3=B（SilentFailure 保留 + 写约束）

**1.5 假修 → 真修**：
- B4 异维列拆分：embeddings 表加 embedding_512 + embedding_1536 + embedding_3072 三 nullable 列 + dim 决定 INSERT 哪列 + CHECK 约束保证恰好一列非 NULL + 三独立 ivfflat 索引
- B2 Provider 切换路径表对齐：异维切换从"不支持数据丢失"改为"支持但需回填，新行写新列"

**3 regression 修**：
- §15 §3 三表 → 四表（含 search_evaluation_log）
- §15 11 ErrorCode → 12 + 12 子类
- CY 决策记录 Q4 超时 2s → 1s

**4 漏洞修**：
- L1 SilentFailure 加完整使用约束 docstring（继承 BaseException 是 by-design + 正确/错误用法示例）
- L2 cron 职责矩阵 7 cron 区分（zombie / monitor / task cleanup / failure cleanup / orphan cleanup / model_version cleanup / search_eval cleanup / backfill recovery）
- L3 advisory lock key 加 project_id：`(hashtext('m18_text_embedding'), hashtext(project_id||'/'||target_id))`
- L4 backfill 中断恢复机制定义：`detect_and_resume_pending_backfill()` + 启动时 + 每小时 cron

**4 新问题修**：
- N1 dim CHECK 上限 1536 → 4096（覆盖 OpenAI 3-large + Cohere 4096）
- N2 §10 加 search_evaluation_log 不写 activity_log 行
- N3 ABS 阈值 100 → 500（与 PER_PROJECT=100 拉开数量级，恢复独立性）
- N4 SilentFailure 使用约束写入 docstring + baseline-patch 同步

---

## 7.5 fix v3 落地清单（verify v2 → CY 决策 D/A/B → fix v3）

**3 关键决策**：
- 决策 1=D（dim 区段死局换形式）：`ck_embeddings_dim_range` 从 `dim > 0 AND dim <= 4096` **收紧** 到 `dim IN (512, 1536, 3072)`，与 `ck_embeddings_dim_column_consistency` 完全对齐；消除"中间维度物理 INSERT 不进表"的隐性陷阱；同步删除 §3/§3 关键设计点中关于 384/768/1024/4096 的虚假"覆盖"承诺；新维度走 ADR + Alembic 加列 + 同步两个 CHECK 的 breaking 迁移声明（§3 Alembic 要点新增）
- 决策 2=A（L4 真做 re-enqueue）：`detect_and_resume_pending_backfill` 改为真调 `await arq_pool.enqueue_job("embed_text", ..., _job_id=f"backfill_recovery:{task.id}")`；arq 自带 1h job_id 去重防风暴；保留 logger.info 但语义改为"detected=N, re-enqueued=M"
- 决策 3=B（advisory lock 双参形式接受现状）：§12D 增加显式说明——`pg_advisory_xact_lock(int4, int4)` 是 PG 官方支持的双参重载，hashtext 返回 int4 直接喂入合法，namespace + project/target 复合 key 满足并发隔离；不为完美主义重写 lock helper

**漏洞 + 新问题修**：
- N3 §10 monitor cron 段 ABS=100 → 500（与 §11 env 表对齐；fix v4 verify R3 修正章节定位——原 commit 误指为"§12D 字段⑥"，§12D 字段⑥实际是失败/重试/死信类型行不带数字，真正改的是 §10 monitor 阈值段）
- N5 §6 Service 行加 dim 路由说明（query embed 的 dim 决定查 embedding_512/1536/3072 哪一列 + WHERE dim 列 IS NOT NULL + provider filter，不跨列 union）
- N8 §3 Alembic 要点加 breaking 迁移声明（新增 dim 必须停服窗口或 expand-then-contract）
- N9 §3 改写 "Cohere embed-v3" 误导性正向 vouching → 显式排除注释（fix v4 verify R2：commit message 原写"删除"实为"改为否定性引用"，文字漂移修正）
- L2 orphan cleanup cron 文字精修（按 target_type 分组左外联到 nodes/dimension_records/competitors/issues，business.id IS NULL 即孤儿；30 天宽限避免误删未 commit 业务事务窗口的 enqueue）
- L4 cron 矩阵行同步改为"真调 arq_pool.enqueue_job + _job_id 幂等"

**未修（已显式 ack）**：
- N6 PrimaryKeyConstraint 显式声明：SQLAlchemy `primary_key=True` 已生成等价 PK；显式 `PrimaryKeyConstraint()` 无 schema 差异，纯风格偏好，不改
- N7 ivfflat lists=100 在 dim_3072 不均衡：Phase 2 实施期按真实数据量调；§15 已有"50 万行调 sqrt(N)"锚点

---

## 7.6 fix v4 落地清单（verify v3 → CY 决策 R1=A → fix v4）

**verify v3 抓出 1 致命假修 + 2 必修 regression**：

- **R1（致命假修）修**：`detect_and_resume_pending_backfill` 改 `async def` + 加 `arq_pool: ArqRedis` 形参；caller（FastAPI lifespan startup 钩子 + arq cron）天然 async context 无缝调用；与 M18 其他 7 cron（zombie/monitor/task cleanup/failure cleanup/orphan/model_version/search_eval）同 arq worker 进程托管，不引入额外调度路径
  - 决策理由：B（sync def + asyncio.run 包 / 自拼 arq payload）在用户层零增益（搜索结果同 5 分钟内恢复），但维护层显著增加复杂度（arq 升级易破 / 与现有 cron 矩阵割裂 / 3-5 月后看不懂为何特殊）
- **R4 §7 切换矩阵 384 死引用修**：`OpenAI 1536 → bge 384` 改为 `OpenAI 1536 → bge-small-zh 512`，与新 CHECK `dim IN (512,1536,3072)` 对齐
- **R5 tests.md 4 处同步**：
  - advisory lock 单参 `pg_advisory_xact_lock(hashtext(target_id))` → 双参 `(hashtext('m18_text_embedding'), hashtext(project_id::text || '/' || target_id::text))`（line 32 + replace_all 全文）
  - trace 矩阵 "4 字段 PK" → "6 字段 PK + fix v2 异维列 embedding_512/1536/3072 拆分" 说明
  - golden_05 env 名 `DEFAULT_EMBEDDING_MODEL=text-embedding-4` → `EMBEDDING_PROVIDER=openai` + `EMBEDDING_MODEL_VERSION=text-embedding-3-large` + dim=3072 写 embedding_3072 列；error_07 同步改 env 名
  - boundary_07 重写：从 "embeddings.embedding 1536 维写入 512 失败" 改为 "dim=768 不在 {512,1536,3072} 支持档位 → CHECK 拒绝 → EMBEDDING_DIM_NOT_SUPPORTED → CY 触发 §3 Alembic breaking 加 embedding_768 列"

**轻度修**：
- R2 N9 audit-report 文字"删除 Cohere"→"改为显式排除注释"
- R3 N3 audit-report 章节定位"§12D 字段⑥"→"§10 monitor cron 段"
- R6 L4 docstring 双层去重分工说明（入队层 _job_id 1h vs 处理层 idempotency_key + ON CONFLICT；串联保险，不冗余）

**status 推进**：fix v4 完成后建议 CY 派 verify v4 闭环 → 通过则 status=draft → accepted

---

## 7.7 fix v4.1 落地清单（verify v4 → CY 决策 R5'=B 拆分 → fix v4.1）

verify v4 抓出 fix v4 仍是"半修"——env 名统一只在 tests.md 改了，源头 00-design.md §11 / §4 / §3 schema 全未同步。本次 fix v4.1 处理：

**R5'=B 拆分（核心，CY 决策）**：拆 model_name（provider-level 模型名）与 model_version（product-level 业务版本号）两层语义，三段式独立——
- §3 schema PK 6 字段 → 7 字段：加 `model_name: Mapped[str] = mapped_column(Text, primary_key=True)`
- §3 ix_embeddings_project_provider_model 索引 + 4 字段
- §3 R3-4 候选 B 改回成本块 #2：Alembic 迁移步数 4 → 5（多一步移除 model_name PK）
- §4 状态机隐式状态：单 model_version → (model_name, model_version) 二元组判定
- §4 回滚说明：env 名 DEFAULT_EMBEDDING_MODEL → EMBEDDING_MODEL_NAME（如需要也可同步改 EMBEDDING_MODEL_VERSION）
- §5 idempotency_key worker 阶段加 model_name
- §5 R5-2 worker 跑到一半 (model_name, model_version) 二元组锁定
- §6 EmbedSinglePayload 加 provider + model_name 字段（payload 调度时锁定三段）
- §9 vector_search DAO 形参 + WHERE 三段过滤
- §9 EmbeddingBackfillDAO.list_pending_node_ids 形参 + JOIN 三段
- §11 env 表：DEFAULT_EMBEDDING_MODEL 改名 EMBEDDING_MODEL_NAME（provider-level）；EMBEDDING_MODEL_VERSION 语义澄清为 product-level
- §11 _validate_current_model_on_startup：current 二元组 → 三元组 (provider, model_name, model_version)
- tests.md：trace 矩阵 6 字段 → 7 字段；golden_05 / provider_switch_01 同步加 model_name

**应修 3 项（reviewer 建议，已 ack）**：
- §6 分层职责表加 `api/cron/embedding_backfill_recovery.py` cron 入口 + `api/main.py` lifespan startup 注册位置 + `from arq.connections import ArqRedis` import 声明
- §15 cron 矩阵 backfill recovery 行：触发栏从"启动时 + 每小时一次"改为"arq cron 每小时一次 + FastAPI startup 钩子调一次"，命名澄清（行项名从 "backfill recovery cron" 改为 "backfill recovery"，避免 cron + lifespan 混称 cron 引误解）

**status 推进路径**：fix v4.1 → 派 verify v4.1（独立 reviewer 审 R5'=B 拆分是否真做完 + 应修 3 项是否落地 + 没引入新 regression）→ 通过则 status=draft → accepted

### Phase 2（实施代码时）

7. 7 Minor（m1-m7）一次性扫
8. 演进退路 R3/R4/R6 实施落地
9. simplify 体检（按 prism-0420 CLAUDE.md「Phase 2 合并前体检」）

### 半衰期评估

reviewer 给 M18 设计**半衰期 9-12 个月**（比 M16/M17 短，因 AI 增强模块受外部 model/provider 生态推着跑）。建议 2026-10-25 半年回看时同步评估"是否需要重构 §3 schema"。

---

## 8. 关联

- 主设计：[`./00-design.md`](./00-design.md)
- 测试：[`./tests.md`](./tests.md)
- 基线补丁：[`../baseline-patch-m18.md`](../baseline-patch-m18.md)
- ADR-003 待扩规则 4：[`../../adr/ADR-003-cross-module-read-strategy.md`](../../adr/ADR-003-cross-module-read-strategy.md)
- §12D 子模板：[`../README.md`](../README.md) §12 表
- 半年回看触发器：[`../README.md`](../README.md) 末尾「设计回看触发器」
