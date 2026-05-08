---
title: M18 sprint 启动期 reconcile pass — 三栏分类 + 配套验收
status: accepted
owner: CY
created: 2026-05-09
sprint: M18 语义搜索 / pgvector / §12D 子模板首战
trigger: M17 sprint 完成（commit 14517f9 / 1213 PASS）后启动 M18
related:
  - design/02-modules/M18-semantic-search/00-design.md
  - design/02-modules/baseline-patch-m18.md
  - design/00-phase-gate.md（闸门 2.5 reconcile pass + 闸门 3.4 L1 总则）
  - _handoff/cross-sprint-punt-pool.md
  - design/99-comparison/phase-gate-bypass-log.md（#2 配套承诺验收）
---

# M18 sprint 启动期 reconcile pass

> 闸门 2.5 三栏强制分类（A 机械可做 / B 待 CY 决策 / C 已自我消解）。
> B 栏前先穷举 L1 锁规候选（feedback_problem_layered_analysis 失效信号 /
> M17 启动期 R1-A P1-1 立规：B 栏 = 0 时禁列 B 栏）。

## 0. 执行摘要

| 栏目 | 项数 | 状态 |
|------|------|------|
| **A 机械可做** | **8** | 全 ✅（本 commit 内修完 / 部分前置已 baseline-patch 历史落地） |
| **B 待 CY 决策** | **0** | M18 audit 4 轮 fix + verify 已锁全部决策（C1=B / C2=A / C3=C / 决策 1=B 异维列 / 2 同意 / 3=B SilentFailure / R1=A async re-enqueue / R5'=B 三段拆分 / R2=A mock 前缀） |
| **C 已自我消解** | **6** | 横切 helper / scaffold 注释清楚 / 复用 M16-M17 范式 |

**B 栏 = 0 第十三次实证**（M05-M17 十二连 + M18 第十三）— 闸门 2.5 默认范式可作模板。

---

## 1. A 栏：机械可做（8 项 / 本 commit 内全 ✅）

### A1 [DONE 历史] M02 ProjectSettings.rrf_k + similarity_threshold baseline-patch

**位置**：`api/models/project.py:103-104` + ck_constraints lines 74-77

**实装**：
```python
rrf_k: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
similarity_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
# CheckConstraint("rrf_k > 0 AND rrf_k <= 200", name="ck_project_rrf_k_range")
# CheckConstraint("similarity_threshold >= 0.0 AND similarity_threshold <= 1.0", name="ck_project_similarity_threshold_range")
```

**Verify**：grep 命中 / 默认值 / CHECK 约束齐 → DONE 历史（baseline-patch-m18.md M02 段 commit 已落）

### A2 [DONE 历史] pgvector image 已配 / 等待 alembic CREATE EXTENSION（子片 1 责任）

**位置**：`docker-compose.yml:3` `image: pgvector/pgvector:pg16`

**Verify**：image 已配 ✅ / 但 `migrations/` 全文无 `CREATE EXTENSION vector` —— 留子片 1 alembic m18_semantic_search.py upgrade 第一行 `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` 显式落

**N/A**：本启动期不在 alembic 内做（与子片 1 schema migration 同 commit 落地更内聚）

### A3 [DONE 历史] ActionType+2 baseline-patch（M18）

**位置**：`api/schemas/activity_stream_schema.py:104-106`

```python
# M18 语义搜索 (baseline-patch 2026-04-26)
embedding_model_upgrade_triggered = "embedding_model_upgrade_triggered"
embedding_backfill_triggered = "embedding_backfill_triggered"
```

**Verify**：grep 命中 ✅ / Alembic CHECK constraint 同步 / R14 ci-lint 守护通过 → DONE 历史

### A4 [本启动期] M18 design status: draft → accepted

**触发**：fix v4.3 grep verify 关键词全清（2026-05-09 startup）：
- F1 `(provider, model_name, model_version)` 三元组 — line 338/527/529-530/563/734/795/810/899
- F2 7 字段 PK content_hash 兜底 — line 28/104/254/337/545/554/561/580/873/879
- F3 §12C/D 三段回填路径 — line 899
- F4 tests.md `EMBEDDING_MODEL_NAME=text-embedding-foo` — line 548
- V2 backfill recovery `embed_single`（不再 `embed_text`）— line 580/753/778/932/941/1145
- V3 backfill recovery 已删 `EmbeddingTask.idempotency_key` 误引 — line 1130 显式记录

**实装**：00-design.md frontmatter `status: draft` → `accepted`，`accepted: null` → `2026-05-09`，`last_reviewed_at: 2026-05-07` → `2026-05-09`

### A5 [本启动期] §14.5 Sprint Review 拆分计划补完

闸门 3.4 L1 总则强制段：5+ 子片 + R1=3 subagent 并行 + R2=1 合并 Opus + SKIP 例外（a/b/c）+ 范式复用清单（M02-M17 沉淀 17 项 actionable）+ L3 子选项留空。

### A6 [本启动期] §15 verify Agent + main objection check + README 行 status 同步

§15 完成度判定 checklist 7 个 verify 段（v1→fix v2→v3→fix v4→v4.1→v4.2→v4.3 + grep 复检）+ 主对话精修 → status=accepted ✅；README §A 列 line 542 M18 行 draft → accepted。

### A7 [本启动期] M17 sprint 配套承诺验收（bypass log #2）

- 累计 bypass = 2（M11+M15+M16 长 context + 2 次 bypass）→ M17 已恢复 R1=3 subagent 并行 + R2=1 合并 Opus（commit d558b5f + dcf7024 实证）
- 闸门 3.4 L1 总则 a/b/c 三类例外段 ad069c0 已修订
- design-principles 清单 6 + ci-lint R15 已立规（IntegrityError 转换守护）
- M18 必继续 R1=3 + R2=1 spawn subagent，**不复位 / 不再降级**（子片 1+2+3 R1 / 子片 4 R2 时跑）

### A8 [本启动期] cross-sprint punt 池本 sprint 命中检查

- punt #16 WS golden e2e（M17 R2 P1-01）— **N/A**：M18 search 路由非 WS
- punt #17 _sanitize_filename horizontal — **N/A**：M18 search 无 multipart 上传（第三 multipart sprint 触发）
- punt #18 M17 confirm_review event 缺失 — **N/A**：非 M18 范围
- punt #19 M17 6 处 lazy import helper — **N/A**：非 M18 范围
- 触发点 A 4 项（M04-1 联合索引 / M04-8 db.get / M04-9 target_type / M04-10 race window）— **STILL_PUNT**：M18 不触 dimension_service，本期不顺手清；M04 修存量推迟独立 cleanup sprint
- 真漏洞 #11 IntegrityError 立规 — **复用**：M18 4 表全新建，所有 INSERT 路径凡 UNIQUE 必 catch IntegrityError 转业务异常（清单 6 + ci-lint R15）
- punt #7 R-X1 失败补偿 — **N/A**：M18 无 R-X1 形态（search 无补偿 / delete 异步 enqueue）

---

## 2. B 栏：待 CY 决策（0 项 / B 栏 = 0 第十三次实证）

> 先穷举 L1 锁规候选（feedback_problem_layered_analysis 失效信号防御）：
> 列出 M18 design 全部架构决策 → 全部已 4 轮 fix + verify 锁规 → B 栏 0 项。

### L1 锁规候选清单（穷举 / 全部已锁）

1. **增量 vs backfill 双路** — ADR-003 规则 1（增量 Service.get_for_embedding）+ 规则 4（backfill DAO 只读 import）已 accepted（baseline-patch-m18.md / ADR-003 line 140-199）
2. **delete 一致性事务模型** — audit C2=A commit 后异步 enqueue（design §9 删除策略 / baseline-patch M03 改动 2 + 决策 5）
3. **维度切换路径** — audit C3=C 部署期固定 + fix v2 决策 1=B 异维列拆分（embedding_512/1536/3072）
4. **modality / dim / provider / model_name / model_version 7 字段 PK** — audit B4 + fix v4.1 R5'=B 三段拆分锁规
5. **query embedding 超时** — audit M5 锁 1s（QUERY_EMBEDDING_TIMEOUT_MS=1000）+ fallback keyword_only 不计入 SLA
6. **failure 阈值 3 维** — audit M10 锁绝对 ABS=500 + 百分比 PCT=5 + 单 project PER_PROJECT=100
7. **ivfflat lists env 配置** — audit M9 锁 IVFFLAT_LISTS=100 + 演进锚点（>50万行调 sqrt(N)）
8. **search_evaluation_log 1% 采样** — audit M13 锁 SEARCH_EVAL_SAMPLE_RATE=0.01
9. **kill switch SEARCH_MODE** — audit B5 锁 hybrid / keyword_only / semantic_only 三档
10. **mock provider mock-\* 前缀** — fix v4.2 R2=A startup sanity check 强制
11. **advisory lock 双 namespace + project/target 复合** — audit M4 + fix v2 verify L3 锁定
12. **backfill 中断恢复** — fix v2 verify L4 + fix v4.1 R5'=B + fix v4 R1=A async re-enqueue
13. **embed_single Queue task 命名** — fix v4.3 V2 锁定（不再 embed_text）
14. **§12D 子模板 7 字段** — pilot=true / fix v4.1+v4.2+v4.3 全链对齐

→ **B 栏 0 项**（M18 audit 4 轮 fix + 6 轮 verify 已锁全部决策 / 任何 sprint 实施期发现的新决策点应是 R1/R2 reviewer 命中而非启动期前置）

---

## 3. C 栏：已自我消解（6 项 / 引用即可不重列）

### C1 EmbeddingProvider 抽象（仿 ADR-001 §4.1）

**消解**：`api/services/ai/registry.py`（M13 落地 / Mock + Claude）已稳定；M18 子片 3 仿写 EmbeddingProvider 抽象基类（仿 ADR-001 §4.1）+ OpenAI/bge-small/Mock 三实现，复用 registry 形态。**横切归属**：horizontal helper（embedding 提供者抽象），owner = M18，文件路径 `api/services/embedding_provider.py`（与 ai/registry 同层）。

### C2 SYSTEM_USER_UUID + queue/base TaskPayload scaffold

**消解**：M16 闸门 2.6 mini-sprint 已落 `api/queue/base.py:TaskPayload` + `SYSTEM_USER_UUID` seed user 行（Alembic INSERT ... ON CONFLICT DO NOTHING）；M18 子片 3 EmbedSinglePayload(TaskPayload) 直接继承（design §6 line 588 + §7 line 648-656）。

### C3 BackgroundTasks / Queue runner 自起 SessionLocal 范式

**消解**：M16 §12B 后台 fire-and-forget 范式已沉淀（commit 2273f90 + 043e3e2 / audit/m16 元贡献 #5）；M18 cron + arq worker 复用（design §6 line 581-584 cron 入口 + §15 cron 矩阵）。

### C4 R-X1 失败补偿 helper（compensation_session）

**消解**：M11 第一实例 + M17 第二实例零摩擦验证（commit 7a6327f + ad069c0）；**M18 不触 R-X1 形态** — search 无补偿（失败容忍走 embedding_failures + monitor cron 阈值告警）/ delete 走异步 enqueue 不共享 session（audit B1 + C2=A）。N/A 显式声明，sprint review subagent 不应抓"M18 缺 R-X1 失败补偿"为 P1。

### C5 design §3 SQLAlchemy 真相源 reconcile

**消解**：fix v4 verify R3 + R5 + fix v4.1+v4.2+v4.3 链已对齐（4 表 SQLAlchemy + 7 字段 PK + 异维列拆分 + 3 字段 CHECK）；R1-A spec subagent 标准检查项「design §3 SQLAlchemy block 是否同步实装字段」M18 子片 1 实装时验证（cross-sprint 元发现 #5 触发点 C 立规延续）。

### C6 IntegrityError 转换（清单 6 + ci-lint R15）

**消解**：M17 启动期 ad069c0 已立 design-principles 清单 6 + ci-lint R15 grep 守护；M18 子片 1+2+3 service 层 INSERT 凡 UNIQUE 必 catch IntegrityError 转业务异常（embeddings 7 字段 PK ON CONFLICT / embedding_tasks idempotency_key UNIQUE / search_evaluation_log 无 UNIQUE → 不触发）。

---

## 4. 启动期完成判定 checklist

- [x] M02 ProjectSettings.rrf_k + similarity_threshold baseline-patch 已落地（DONE 历史）
- [x] pgvector image 已配（docker-compose.yml）/ CREATE EXTENSION 留子片 1 alembic
- [x] ActionType+2 已落地（embedding_model_upgrade_triggered + embedding_backfill_triggered）
- [x] ADR-003 规则 4 已 accepted（M18 baseline-patch 2026-04-26）
- [x] M09 status superseded_by=M18（baseline-patch 历史）
- [x] M18 design fix v4.3 grep verify 关键词全清（F1-F4 + V2 + V3）
- [x] M18 design status: draft → accepted（frontmatter flip + last_reviewed_at 2026-05-09）
- [x] M18 design §14.5 Sprint Review 拆分计划补完（闸门 3.4 L1 总则强制段）
- [x] §15 7 个 verify 段 + 主对话精修 → accepted ✅ + README 行 draft → accepted
- [x] 闸门 2.5 reconcile pass 三栏分类 A 8 / B 0 / C 6（B 栏 = 0 第十三次实证）
- [x] cross-sprint punt 池本 sprint 命中检查（4 项 N/A + 触发点 A 4 项 STILL_PUNT + 真漏洞 #11 复用）
- [x] M17 配套承诺验收（bypass log #2 已 ✅ / M18 R1=3 + R2=1 必跑不复位）

---

## 5. 子片拆分预期（design §14.5 字面 / 启动期范畴）

> 子片 0 prep 在下一会话开新 context 进入（usage_budget v3 单会话 $10 上限 + bypass log #2 配套：spawn subagent 必新 context）。

| 子片 | 范围 | 预期 commit |
|------|------|----------|
| 0 prep | scaffold 简化 4 字段注释 + EmbeddingProvider 抽象基类 + Mock 实现 + 4 pytest（闸门 2.6 类似 mini-sprint） | 1 |
| 1 | 4 表 model + alembic（含 CREATE EXTENSION vector + 7 字段 PK + 异维列 + ivfflat 三索引 + advisory_xact_lock 双 namespace）+ TargetType+1 + model tests | 1 |
| 2 | 4 DAO（含 EmbeddingBackfillDAO 规则 4 豁免）+ unit tests | 1 |
| 3 | EmbeddingService + EmbeddingProvider 抽象 + OpenAI/bge/Mock 三实现 + Schema + 12 ErrorCode + Queue tasks + Cron + Redis 短缓存 + AI Client 接通 + service/schema tests | 1 |
| R1 立修 | 3 subagent 并行审 子片 1+2+3 合并去重 P1 立修 | 1 |
| 4 | Router（search + embedding_admin）+ e2e（17+ 元教训 actionable 主动复制 + N/A 显式声明） | 1 |
| R2 立修 | 1 合并 Opus subagent endpoint 单审 P1 立修 | 1 |
| 5 关闸 | design 回写 + audit/m18-pilot-template-validation.md + handoff §0 + roadmap + cross-sprint punt 池接通 | 1 |

**预期总 commits = 8-10**（与 M17 11 commits 同量级）/ **预期 PASS = 1213 → 1300+**（视 M18 4 表 model+DAO+service+e2e 总测试数）/ **预期 R13-1 = 124 → 136**（+12 ErrorCode）

---

## 6. 元教训沉淀（启动期独立产出）

### #1 audit 4 轮 fix + 6 轮 verify 后的 startup grep verify 是 status flip 的最终闸门

M18 audit-report 末尾"fix v4.3 完成后 grep 复检关键词全清 → status=accepted ✅"在 4/26 写下，但 design frontmatter 一直 draft 等 sprint 启动期才 flip。立规：**audit 多轮闭环后未 flip status 的设计文档，sprint 启动期必跑 grep 复检关键词全清作为最终闸门，不允许靠 audit-report frontmatter 单方面声称 accepted。**

### #2 baseline-patch 落地 vs sprint 自有 schema 落地的责任划分

M02 ProjectSettings.rrf_k + ActionType+2（embedding_model_upgrade_triggered + embedding_backfill_triggered）属 M18 触发的 baseline-patch，**早 baseline-patch sprint 已落地**；而 M18 自有 4 表 + TargetType+1 + 12 ErrorCode 留 sprint 子片 1+2+3 落地。启动期只 verify baseline-patch 落地状态，不混淆为 sprint 范围。

### #3 B 栏 0 项第十三次实证（M05-M18 十三连）

audit 闭环锁规足够时启动期 B 栏 = 0 项是健康信号；穷举 L1 锁规清单（本文档 §2）防"反正都锁了"的认知漂移 / "没看见决策点 = 没锁规"的盲区。

