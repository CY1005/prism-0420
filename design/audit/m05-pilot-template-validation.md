---
title: M05 sprint 实证子选项 + R1/R2 命中比例 + L1 第四数据点
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M05 sprint 启动期闸门 2.5 reconcile pass 三栏（A 9 项 / B 0 项 / C 5 项）
  首次 B 栏 0 项实证（L1/L3 范式应用 5 项被 5 步分层分析法识别后全收 A 栏，
  避免给 CY 制造假决策）。

  本文件按 5 步分层分析法 (memory feedback_problem_layered_analysis) 沉淀:
  - R1 + R2 review 命中比例 (L3 数据驱动 M06+ sprint review 计划)
  - 闸门 2.5 三栏 A/B/C 实证 (B 栏 0 项 + 失效信号沉淀回 memory)
  - L1+L2+L3 节奏第四次实证 (M02 首 / M03 第二 / M04 第三 / M05 第四 — 四数据点)
  - PT1-PT3 模板复用性 (M05 行已回写 m01-pilot-template-validation.md)
  - M04 sprint punt 池 (17 项) 中本期到期项消化情况
last_reviewed_at: 2026-05-08
---

# M05 sprint 实证子选项 + Review 命中比例

## 闸门 2.5 reconcile pass 三栏实证（首次 B 栏 0 项）

### A 栏（机械可做 / sprint 第一 commit 内修）— 9 项全落地

| # | 项 | 落地 commit | 状态 |
|---|----|-----------|------|
| A1 | §3 imports 加 `from sqlalchemy import text` | `de53192` | ✅ |
| A2 | M03 Node model 加 `version_records` back_populates + cascade | `de53192` | ✅ |
| A3 | conftest 复用 make_user/make_project/make_node | （免修） | ✅ |
| A4 | M04 punt R1-B B1.1: `make_dim_type` 进 conftest + 4 文件回写 | `811d6bc` | ✅ |
| A5 | M05 design §14.5 sprint review 拆分计划段补 | `811d6bc` | ✅ |
| A6 | §3 主索引升级 `(node_id, project_id, created_at DESC)` ordered scan | `de53192` | ✅ |
| A7 | tests 加 set_current 不变量验证（B2 候选 A 路径，service 串行） | `063cbd4` | ✅ |
| A8 | M04 §5 vs §6 R-X3 事务边界字面冲突文字消歧 | `811d6bc` | ✅ |
| A9 | M05 实装 IntegrityError → VersionLabelDuplicateError 转换 | `063cbd4` | ✅ |

### B 栏（待 CY 决策）— **0 项**（首次 B 栏空）

CY 反馈"做不出决定就是分析不对，没分清层次"后用 5 步分层分析法重做：5 项原列 B
栏（B1 索引 / B2 并发测试 / B3 schema 校验 / B4 punt 顺修 / B5 race 转换）全
被 step 1-2 识别为 L1 已锁 / L3 范式应用 / punt 池工序到期，全收敛到 A 栏。

**首次 B 栏 0 项 = 5 步分层分析法首次实质性"防假决策"价值**。失效信号已沉淀
到 memory `feedback_problem_layered_analysis`：闸门 2.5 自审"真有候选吗"必先
grep 既有规则后再答，否则仪式化 = 没做。

### C 栏（已自我消解）— 5 项

| # | 项 | 已决依据 |
|---|----|--------|
| C1 | snapshot_data 全量 vs 元数据 + jsonschema 校验深度 | design §1 Out of scope（M05 不做 AI 解析）+ §7 schema optional 由调用方填 |
| C2 | R-X2 child service 注入 | M05 own 主表，nodes ON DELETE CASCADE 兜底 |
| C3 | R-X1 orchestrator 范式 | N/A，M05 不调下游 batch_* |
| C4 | reset_to / rollback | design §1 边界灰区归 M04 |
| C5 | NodeChildrenServiceProtocol 4 参 | M05 不实装 child service |

---

## R1 + R2 命中比例（M02-M05 四数据点）

### R1 (3 subagent / 子片 1+2+3 合并审)

| Subagent | 模型 | P1 | P2 | P3 | 主命中类目 |
|---|---|---|---|---|---|
| R1-A spec+quality | Opus | 2 | 3 | 3 | design §6 R-X3 ASC vs §9 DESC + 三处索引名不一致（design 真相源回写） |
| R1-B reuse | Sonnet | 2 | 3 | 4 | _make_version 应进 conftest（M04 R1-B C1 同款规则）+ T7 service 测试裸 select |
| R1-C quality+efficiency | Sonnet | 2 | 5 | 3 | create IntegrityError 不区分约束名 + count_by_node 缺 _check_node |
| **合计** | — | **6** (去重 4) | **11** | **8** (含 R1-B P1-02 降 P3) | — |

**P1 处理**（commit `5e0e239`）：
- Code-level 立修：R1-C P1-01（IntegrityError 区分约束）+ R1-B P1-01（_make_version 进 conftest）
- Design-level：R1-A P1-1（§6 ASC→DESC）+ R1-A P1-2（三处索引名统一）→ 子片 5 design 回写
- 降级：R1-B P1-02（T7 裸 select）→ P3（验唯一性需 count，dao.get_current 单条不够）；R1-C P1-02（rows=0 区分）→ P2（reviewer 自承防御深度非真危险）

**M02 (6) → M03 (4) → M04 (4) → M05 (4 去重)**：稳定 4-6 P1，R1 命中正常。

### R2 (1 合并 Opus / 子片 4 endpoint 单审)

| Subagent | 模型 | P1 | P2 | P3 | 工时 |
|---|---|---|---|---|---|
| R2 合并 | Opus | 3 | 4 | 3 | 89s |

**P1 处理**（commit `56da878`）：
- Code-level 立修：R2 P1-01（403 + viewer 路径零覆盖 → 加 test_create_version_viewer_role_returns_403）
- Design-level：R2 P1-03（VersionUpdate.summary min_length=1 vs design 草案）→ 子片 5 design §7 回写
- 降级：R2 P1-02（VersionResponse 缺 created_by_name）→ P3：M04 范式无此字段无实装 → M04 范式延续，子片 5 design §7 删此行

**M02 (6) → M03 (4) → M04 (1) → M05 (3 → 立修 1 + design 回写 1 + 降级 1)**：M05 R2
命中回升至 3，主因 P1-01 是 quality-spec 关键路径覆盖缺口（与 M02-M04 同类）+ P1-02
是 M04 范式延续点的 design 字面遗漏（本期发现，子片 5 删 design 字段对齐范式）。

---

## Punt 项总池（M05 sprint 末，共 19 项）

| 来源 | # | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|---|
| R1-A P2-1 | 1 | create(is_current=True) IntegrityError 兜底（**已合 R1-C P1-01 立修**） | — | 已闭环 |
| R1-A P2-2 | 2 | set_current 已 current 时快路径优化 | P3 | M15 升级 write_event 真 INSERT 时一并优化 |
| R1-A P2-3 | 3 | update_metadata 未 catch IntegrityError | P3 | schema 扩展允许改 label 时补 |
| R1-A P3-1 | 4 | service docstring "with db.begin()" 跨模块漂移 | P3 | M06+ 集中改表述 |
| R1-A P3-2 | 5 | list_by_node id DESC tie-break design §9 未写 | — | **本子片 5 已回写 design** |
| R1-A P3-3 | 6 | VERSION_SNAPSHOT_INVALID R13-1 parity 备用注释 | — | **本子片 5 audit 已注** |
| R1-B P2-1 | 7 | model `__table_args__` 索引风格 vs M04（M05 更清晰） | P3 | M06 sprint 范式对齐时确认 |
| R1-B P2-2 | 8 | action_type/target_type 裸字符串（M04 punt 同款） | P3 | M15 一次性 const 化（M04 punt 池继承） |
| R1-B P2-3 | 9 | DAO 写方法命名差异 vs M04（功能不同合理） | P3 | M06 命名规范讨论 |
| R1-B P1-02 | 10 | T7 service 测试裸 select VersionRecord（**降级 P3**） | P3 | 验唯一性需 count，dao.get_current 单条不够，false positive |
| R1-C P1-02 | 11 | update_metadata rows=0 区分（**降级 P2**） | P2 | 防御深度非真危险，docstring 加 |
| R1-C P2-01 | 12 | covering 索引 tie-break id 未在索引尾列 | P2 | M16 pilot 压测时触发 |
| R1-C P2-02 | 13 | get_current 部分唯一索引无 project_id 列 | P2 | M16 pilot 压测时触发 |
| R1-C P2-03 | 14 | set_current 6 query 可降 5（RETURNING 优化） | P3 | M15 升级 write_event 时顺手优化 |
| R1-C P2-04 | 15 | update_metadata 4 query 可降 3（RETURNING 优化） | P3 | 同 14 |
| R1-C P2-05 | 16 | service 并发测试仅串行路径，DB 层并发未验证 | P2 | M16 pilot 压测 / pgbouncer 时验证 |
| R1-C P3-01/02/03 | 17 | docstring 注释建议 3 项 | P3 | docstring 集中改时 |
| R2 P2-01 | 18 | router 反复 `VersionService()` 实例化（M04 同款） | P3 | 注入 DAO 单例时统一改 Depends |
| R2 P2-02 | 19 | list endpoint 双查 items+total + 重复 _check_node | P2 | 加 service.list_with_total 合并 |
| R2 P2-03 | — | snapshot_data PUT 静默忽略 vs 显式 422 | P3 | 子片 5 已注 design §7（M05 设计期 extra='ignore' 默认） |
| R2 P2-04 | — | list endpoint created_at 同 ms tie-break 不稳定（router 测试已不验排序） | P3 | DAO 测试已 cover；前端展示如需稳定再加 sort key |

---

## L1+L2+L3 节奏第四次实证（四数据点稳定）

| 节奏层 | M05 sprint 表现 | 与 M02+M03+M04 差异 |
|---|---|---|
| L1 总则 | ✅ R1 (3 sub) + R2 (1 sub) 共 2 次 review，子片 5 不单跑 | 与 M02+M03+M04 一致 |
| L2 sprint 计划（design §14.5） | ✅ 子片 0 commit `811d6bc` 含 §14.5 | 与 M03+M04 一致；schema 子片禁单跑沿用 |
| L3 实证回写 | ✅ 本文件 | 第四数据点（首次 B 栏 0 项实证 = 5 步分层分析法防假决策价值） |

**结论**：M02-M05 四数据点稳定后，**R1=3 subagent + R2=1 合并 Opus + schema 禁单跑**默认范式可作为 M06-M20 sprint 启动模板。

---

## M04 punt 池消化情况（M05 sprint 接通）

| M04 punt | 本期处理 | 状态 |
|---|---|---|
| R1-A A4 §5 vs §6 R-X3 事务边界字面冲突 | 子片 0 `811d6bc` 修 M04 design §5 显式区分入口形态 | ✅ 已闭环 |
| R1-A B3 create 竞态 IntegrityError → 500 | M05 实装 IntegrityError → VersionLabelDuplicateError + ConflictError 分支 | ✅ M05 干净起步（M04 自身后置） |
| R1-B B1.1 `_seed_dim_type` 三文件重复 | 子片 0 `811d6bc` 抽 conftest make_dim_type + 4 文件回写 | ✅ 已闭环 |
| R1-C C1.1/C2.4/C7.1/C9.4 P3 顺手清 | M05 sprint 内**未**主动清（与本 sprint 主线无关），保持 punt | ⏳ M06 / M15 sprint 顺手清 |
| R2 B7 真并发测试 | M05 service 层串行路径覆盖（B2 测试），DB 层并发 punt | ⏳ M16 pilot 压测时验 |

---

## 元教训沉淀

1. **闸门 2.5 自审仪式化失效首次实证**：5 项 L1/L3 范式应用被错误升 L2 假决策；CY "做不出决定就是分析不对"一击命中。已沉淀失效信号到 memory `feedback_problem_layered_analysis`：自审"真有候选吗"必先 grep 既有规则后答。
2. **B 栏 0 项不是异常**：当模块本期工作全是范式应用 + design 真相源已锁时，B 栏空是正常状态；列 B 栏 ≥1 项必先证"真有候选 + 既有规则未锁"。
3. **R1 三 subagent + R2 一合并 Opus 范式确认稳定**：M05 是第四数据点，R2 P1-02 命中"M04 范式延续中的 design 字面遗漏"是 R2 单 Opus 端到端读才能拼出的价值，与 M04 R2 B6.x 同款角色。
