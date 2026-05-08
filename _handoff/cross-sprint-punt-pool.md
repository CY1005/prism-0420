---
title: prism-0420 跨 sprint Punt 池总表
status: living-doc
owner: CY
created: 2026-05-08（M15 sprint 收官后建立）
last_updated: 2026-05-09 (M17 sprint 子片 0 prep)
purpose: |
  把分散在 9 个 audit 文件 + handoff 的 punt 项聚合 + 代码验证状态，作为下一 sprint
  cold-start 必读项（防"约定 M? sprint 处理但被遗忘"漂移）。

  M15 sprint 收官时 CY 反馈"之前的任务里 会有类似的问题吗 有没有被记录"—— 触发本表
  建立。Opus subagent 全量审计 94 项发现 30 项 STILL_PUNT，其中至少 8 项约定时机已过。

policy:
  - **每 sprint 关闸 commit 必更新本表**（标 DONE / 新增本 sprint punt / 重新评估 STILL_PUNT 时机）
  - **每 sprint 启动 cold-start 必读本表**（Prompt 0 reconcile checklist 字面引用）
  - **同触发点 ≥3 项 punt 自动升 P1**（防"高耦合触发点"延迟联动失修，本表元发现 #1）
  - **代码 punt vs 文档 punt 区分**（代码 punt 必给 grep 锚点 / 文档 punt 短期可关闸不入本表）
---

# 跨 sprint Punt 池总表

> ⚠️ M15 sprint 收官审计后**首次**建立。基于 design/audit/m05-pilot..m15-pilot.md 9 个
> 文件 + _handoff/next-session.md M01/M02 后置债 = 共 94 条 punt 全量代码验证。
> Opus subagent 跑完整 grep 验证。

---

## 状态分布快照（2026-05-08 baseline / 含 M02/M03/M04 补审）

> 2026-05-08 二次审计：CY 抓出 subagent 一审漏 M02/M03/M04 audit 文件 punt 池（仅查 m05~m15）。
> 二审 spawn 补充 41 项 punt 验证；去 M02 audit 与 _handoff §0a 的 6 项 DUPE 后净增约 35 项。

| 状态 | 项数 | 占比 | 说明 |
|---|---|---|---|
| **STILL_PUNT** | **49** | 38% | 代码完全没动，问题还在（一审 30 + 二审 19）|
| **DONE** | **22** | 17% | 代码已落实（部分被主线"默默吸收"无人关闸 / 一审 15 + 二审 7）|
| **PARTIAL** | 2 | 2% | 部分子项做了 |
| **UNVERIFIABLE** | **59** | 46% | 设计意图 / 性能压测 / 未来 sprint 才触发 / docstring 注释类（一审 46 + 二审 13）|
| **OBSOLETE** | 3 | 2% | punt 已不适用 |
| **总计** | **129** | 100% | （一审 94 + 二审 41 - 6 DUPE）|

---

## 🔴 真漏洞（约定时机已过 + STILL_PUNT / 按严重度排序）

| # | punt | 来源 | 约定 | 影响 | 推荐处理 |
|---|---|---|---|---|---|
| 1 | ~~**write_event stub 仍未替换为真 INSERT**~~ ✅ **DONE 2026-05-09 commit 959e0b4** | M15-B1 | 后续独立 sprint | ~~critical~~ | **M16 sprint 子片 0.5 L1+L3 batch 关闭** |
| 2 | ~~**M03-M08 service ~14 处裸 CRUD `action_type="create/update/delete"`**~~ ✅ **DONE 2026-05-09 commit 5c592d5**（实际 7 模块 41 处 含 M02 + M11 cold_start 命名漂移 + M07 issue_unassigned + M08 module_relation_updated + M05 version_record_set_current + M06 competitor_ref_updated 4 NEW enum）| M15-B2 | 与 B1 同 sprint | ~~high~~ | **M16 sprint 子片 0.5 batch 关闭 + ci-lint R14 grep 守护立规防御未来** |
| 3 | **IssueResponse 漏 join 字段（node_name/created_by_name/assigned_to_name）** | M07 R2 P2-1 | M13/M15 集成期补 | **high** — design §7 字面承诺；前端 N+1 拼接；列表卡顿 | M16 启动 reconcile 时拍 |
| 4 | ~~**SSE generator 占 AsyncSession 300s**~~ ✅ **RE-EVALUATE 2026-05-09 / M16 sprint 已用 BackgroundTasks + 自起 SessionLocal 替代长持 SSE 范式** | M13-B13 | M16/M17 立异步 SSE 策略 | ~~high~~ | **M16 §12B 后台 fire-and-forget 子模板 + 自起 SessionLocal 隔离请求级 Depends(get_db) 已沉淀**（commit 2273f90 + 043e3e2 / audit/m16 元贡献 #5）；M13 `analyze_service.py` SSE generator 仍存量未迁但**新模块（M16/M17）已不触发同款** → 标 STATUS_CHANGE：从"M17 必查"降为"M13 后续重构 sprint 顺手迁"low |
| 5 | ~~**M02 Project.ai_model 字段未实装**~~ ✅ **DONE 2026-05-09 / 子片 3 验证字段已存在不需 alembic add**（M02 model 字面已含 ai_model 列；M13-B16 punt 误判） | M13-B16 | M14+ baseline-patch | ~~medium~~ | **M16 sprint 子片 3 验证关闭** |
| 6 | **M07 update 不支持 detach (None→NULL)** | M07 R1-A P2-2 | design §3/§7 reconcile + 产品决策 | medium — issue 节点关联无法解除；M14 link/unlink 已支持但 M07 主表残缺 | M16 启动让 CY 拍是否补 |
| 7 | ~~**M11-B1 R-X1 失败补偿 commit boundary**~~ ✅ **DONE 2026-05-09 / M17 子片 0 prep**：cold_start_service._mark_failed 改用 compensation_session 独立 commit boundary（task 创建立即 commit / 失败补偿 comp_db 独立写 task=FAILED+activity_log）；router 失败分支只剩 db.rollback() / R2 P1-01 punt 关闭；conftest autouse fixture monkeypatch compensation_session yield db_session 兼容 savepoint；1079 PASS 不破 | M11 R2 P1-01 punt | M17 异步 zip 导入时 | ~~critical~~ | M17 子片 1+2+3 直接复用 helper（首个非 M11 caller） |
| 8 | **M14-B12 update/delete/unlink write_event 异常传播 e2e** | M14 R2 punt | M14 baseline-patch | medium — M02+ 元教训纪律 3 写路径无 e2e 覆盖 | 与 #1+#2 同 sprint 做 |
| 9 | **M05-2/14 + M06-1 + M07-7 + M08-1 多模块 `if rows == 0: continue` race window** | 多 sprint | M15 升级 INSERT 时复审 | medium — B1 落地后必须一并复审；不复审会 silently 改变行为 | 与 #1 同 sprint 联动复审 |
| 10 | **M10-5 viewer /overview/stats 测试缺** | M10 R2 P2 #3 | M11 启动前补 | low — endpoint 行为正确，仅测试覆盖度 | M16 启动顺手补 |
| **11** | **IntegrityError → 500 跨模块 3 处（M02 project create ✅ DONE / M04-4 dimension B3 / M04-17 C7.1）** ⏳ **PARTIAL 2026-05-09 / M17 启动期**：通用规则已立（`design/00-architecture/06-design-principles.md` 清单 6 + ci-lint R15 grep 守护立规防御未来 + 3 类豁免显式声明）；M02 project create 已实装（project_service.py:102/302）；**M04 dimension 修存量推迟到独立 cleanup sprint** | M04 R1-A B3 + R1-C C7.1 | M05 sprint 顺修（已过） / M17 启动期立规 | ~~high~~ → medium（立规已落 / 存量保留 / 后续 sprint 自然推动） | M04 dimension_service.create + create_dimension_record 加 IntegrityError handler；ci-lint R15 实装由后续 sprint 落 |
| **12** | **M04-9 target_type 5 处 hard-code（service:327/378/436/482/516）** ⏳ 2026-05-09 M17 子片 0 prep 验证仍 STILL_PUNT；服务 M17 不触动 dimension_service 范围，本期不顺手清 | M04 R1-B B6 | M15 启动前 const 化（已过）| medium — 与 #1+#2 同根因（命名规约一致性）；若 #1 先升 schema 不 const 化会冲突 | M16 启动 reconcile A 栏首条 / 与 #2 同 batch |
| **13** | **M04-1 dimension_records (updated_by, updated_at) 联合索引未建** ⏳ 2026-05-09 M17 子片 0 prep 验证：现仅有 (project_id, updated_at) 索引（model:52），(updated_by, updated_at) 仍缺 / STILL_PUNT | M04 R1-A A2 | M15/M19 | medium — dimension_records 是 M13/M14 写大量行的源表，缺联合索引会让 activity_stream 时间线查询慢 | 与 #1 同 sprint 评估是否提前建 |
| **14** | **M04-8 db.get(DimensionType) 三处未走 DAO** ⏳ 2026-05-09 M17 子片 0 prep 验证仍 STILL_PUNT（service:349/428/474）；M17 不触 dimension_service，本期不清 | M04 R1-B B2.4 | M15 启动前（已过）| low — 风格统一性；service:349/428/474 三处 | M16 启动顺手清 |
| **15** | **M04-R2 A1 DimensionResponse 缺 dimension_type_key/updated_by_name join 字段** | M04 R2 A1 | 前端真用时补 join | medium — 与 #3 IssueResponse 同款契约缺口；前端真用时必补 selectinload | 与 #3 一并 M16 启动拍 |

---

## 🌟 元发现（机制本身的洞察）

### #1 高耦合触发点 — M15-B1 锁住下游 8 项历史 punt

**M05-2 / M05-14 / M06-1 / M07-7 / M08-1 + M13-B16 + M14-B12 + M15-B2** 共 **8 项**全
约定"M15 升级真 INSERT 时复审"—— B1 单点延迟使下游 8 项联动失修。立 punt 时**未识别
共享触发点**，导致状态从"分散小修"变成"一个 sprint 必须 batch 8 项"，工作量爆炸。

**立规**：未来 punt 立项时若发现 ≥3 项指向同一未来动作（如"M? sprint 升级 X 时"），
**自动升 P1 提前规划**到目标 sprint 计划段，不许做"分散登记"。

### #2 "性能 sprint" 是 punt 黑洞

M02-M14 累计 **~12 项** punt 写"性能 sprint"，但项目从无独立性能 sprint 计划。M16
audit 必看是否吸收 / 否则将永久驻留 punt 池。

### #3 UNVERIFIABLE 占 49% — 大量 punt 是"文档/决议"类

大量 punt 是 "design 注释回写 / docstring 注释 / 决议未来"——非代码可验证状态。

**立规**：未来 punt 立项时区分"代码 punt"vs"文档 punt"。
- 代码 punt：必给 grep 锚点（关键字 / 文件:行号 / 函数签名）→ 入本表
- 文档 punt：sprint 关闸前必修完 / 短期内不入本表（防噪音）

### #4 被默默吸收 / 跟踪噪声

**M06-4 / M11-B3 / M11-B6 / M02-7（_ck_clause helpers）/ M03-3 breadcrumb / M03-4 child_services /
M03-13 ck_clause helpers / M04-3 batch_get_by_nodes / M04-7 make_dim_type / M04-11 / M04-12** 等
**22 项** punt 在后续 sprint 主线工作中**顺带 done** 而无人关闸标记。

**立规**：每 sprint 关闸 commit 必跑"DONE 检查"——audit 文件 punt 池总表标 DONE 的项
同步标到本表。本次 baseline 已识别 22 项 DONE。

### #5 二审发现：3 个新触发点（元发现 #1 立规应用）

二审 spawn 的 subagent 找出 **3 个新高耦合触发点**：

#### 触发点 A — M16 sprint 启动 reconcile pass 必查 4 项

**M04-1（联合索引）+ M04-8（db.get → DAO 风格）+ M04-9（target_type const）+ M04-10
（delete cascade activity_log 真 INSERT 复审）** 共 4 项指向同一 sprint。M16 闸门 2.5
reconcile pass A 栏首条预录这 4 项，避免漂移。

#### 触发点 B — IntegrityError 转换缺口跨模块 3 处

**M02 project create / M04 dimension create（B3）/ M04 C7.1** 三处都缺 IntegrityError
→ 业务异常转换 layer。立通用规则（feedback 或 design §13 R13 段）：service 层 INSERT
凡有 UNIQUE constraint 必 catch IntegrityError 转 *DuplicateError，docstring 必标。

#### 触发点 C — design §3 字面 vs 实装漂移在 M03/M04 各 1+ 处

**M03 P-A-08（description 加 design §3）+ M03 P2-05（path 公式）+ M04 R1-A A1
（dimension_type relationship 实装未建）** 印证 memory `feedback_design_scaffold_reconcile`
红线，建议 M05+ 每次 sprint R1 spec subagent 显式扫"design §3 SQLAlchemy block 是否
同步实装字段"作为标准 review 检查项。

---

## 完整 punt 池（按原 sprint 分组）

> 详细 grep 证据已在 subagent 审计跑出。本表只列简要状态；要看具体 grep 命令请回查
> 本文件 git 历史 commit message 或对应 audit 文件原 punt 表。

### M01 sprint 后置债（_handoff §2.1，4 项）

| # | 项 | 状态 |
|---|---|---|
| D1 | M03/M04 模块开工时验证 PT1-PT3 | DONE |
| D2 | tests.md A22 strikethrough | UNVERIFIABLE |
| D3 | bcrypt 5.x deprecation warning | DONE/OBSOLETE |
| D4 | feedback_three_agent_pipeline 替代 | DONE |

### M02 sprint 后置债（11 项 / 跨 §0a 两组）

| # | 项 | 状态 |
|---|---|---|
| 1 | check_project_access vs require_owner 重复 JOIN | STILL_PUNT |
| 2 | batch_update N 条 UPSERT → ON CONFLICT | STILL_PUNT |
| 3 | ProjectMember.joined_at vs created_at 冗余 | UNVERIFIABLE |
| 4 | update_project exclude_none + setattr 白名单 | UNVERIFIABLE |
| 5 | R-X2 stub: M04 第一真注入 | DONE |
| 6 | NodeChildrenServiceProtocol batch | DONE/OBSOLETE |
| 7 | NodeService.update_node 测试 | UNVERIFIABLE |
| 8 | refresh attribute_names + path | DONE |
| 9 | batch_create max_sort_order O(N) | UNVERIFIABLE |
| 10 | update_paths_in_subtree REPLACE 安全性 | UNVERIFIABLE |
| 11 | migrations _ck_clause helpers.py 提取 | DONE |

### M02 sprint audit punt 池（7 项 / 二审补 / 6 项 DUPE 已在 _handoff §0a）

| # | 项 | 状态 |
|---|---|---|
| M02-A1 | update_project exclude_none 让 null 无法清字段 | STILL_PUNT (DUPE _handoff §0a #4) |
| M02-A2 | update_project hasattr setattr 无白名单 | STILL_PUNT (DUPE) |
| M02-A3 | AiProviderUpdate 不强制 min_length | STILL_PUNT |
| M02-A4 | in-method/in-loop import (style) | UNVERIFIABLE |
| M02-A5 | check_project_access vs require_owner 重复 JOIN | STILL_PUNT (DUPE) |
| M02-A6 | batch_update N 条 UPSERT → ON CONFLICT | STILL_PUNT (DUPE) |
| M02-A7 | _project_response/_member_response 单行 helper | OBSOLETE (R2 修后已含 join) |

### M03 sprint audit punt 池（13 项 / 二审补）

主要 STILL_PUNT 2 项：
- M03-1 P-A-03 batch_create 拓扑责任（约定 M11/M17 / 服务仍简化版）
- M03-12 P2-07 alembic downgrade 无 drop_constraint（migrations/m03 仅 drop_index/table）

DONE 4 项：M03-3（breadcrumb 已 list_by_ids 一次 IN）/ M03-4（child_services M04 实证）/
M03-11（move metadata 已 design 回写）/ M03-13（_ck_clause migrations/helpers.py 已抽 / commit 4c3c413）

UNVERIFIABLE 7 项（多为 design 注释 / docstring / 测试覆盖类）

### M04 sprint audit punt 池（22 项 / 二审补 / 17 主表 + 5 R2 punt）

主要 STILL_PUNT 12 项：
- **M04-1 (updated_by, updated_at) 联合索引未建** → 真漏洞 #13
- **M04-4 create 竞态 IntegrityError → 500** → 真漏洞 #11（与 M04-17 同根因）
- M04-6 completion(enabled_count=...) caller 推（docstring 已标）
- **M04-8 db.get(DimensionType) 3 处未走 DAO** → 真漏洞 #14
- **M04-9 target_type 4 处 hard-code** → 真漏洞 #12
- M04-10 delete_by_node_id 并发 continue 跳 activity_log（→ M15-B1 联动）
- M04-13 R1-C C6.1 delete_by_node_id N+1（M06/M07 启动评估已过）
- M04-15 create 二次查询 TOCTOU（DB UNIQUE 兜底已显式）
- M04-16 monkeypatch ≠ 生产路径（M15 真 INSERT 端到端复审 / 已过）
- **M04-17 R1-C C1.1/C2.4/C7.1/C9.4 聚合 4 项**（C7.1 与 M04-4 同根因）
- **M04-R2 A1 DimensionResponse 缺 join 字段** → 真漏洞 #15
- M04-R2 A2 list_by_node 未调 _check_node（docstring 豁免）
- M04-R2 B5 _record_response 单行冗余 helper
- M04-R2 A4 jsonschema 二次校验 design §7 字面要求未实装
- M04-R2 B7 真并发乐观锁测试

DONE 4 项：M04-3（batch_get_by_nodes service.py:154）/ M04-7（make_dim_type
conftest:450）/ M04-11（design §6 reconcile）/ M04-12（router 子片 4 R2 已审）

UNVERIFIABLE 6 项（design §3 字面 / docstring / 测试覆盖类）

### M05 sprint punt 池（19 项 / 一审）

主要 STILL_PUNT 6 项：
- #2 set_current 已 current 快路径（约定 M15 升级时 / 待 #1 触发）
- #3 update_metadata 未 catch IntegrityError
- #8 action_type 裸字符串 const 化（→ 与 M15-B2 联动）
- #11 update_metadata rows=0 区分 docstring
- #14 set_current 6→5 query / #15 update_metadata 4→3 query
- #18 router 5 处 VersionService() 内联实例化
- #19 list endpoint 双查 items+total

DONE 4 项：#1/#4/#5/#6
UNVERIFIABLE/OBSOLETE 9 项

### M06 sprint punt 池（8 项）

主要 STILL_PUNT 2 项：
- #1 delete_by_node_id continue 跳过 activity_log（→ M15-B1 联动）
- #3 design §10 batch competitor_ref event punt 注释

DONE 2 项：#4 _make_competitor 已迁 conftest / #6 display_name 已实装
UNVERIFIABLE 4 项

### M07 sprint punt 池（10 项）

主要 STILL_PUNT 3 项：
- #2 update 不支持 detach（→ 真漏洞 #6）
- #7 orphan list↔UPDATE race（→ M15-B1 联动）
- #9 IssueResponse 漏 join 字段（→ 真漏洞 #4）

DONE 1 项：#6 transition WHERE status 谓词
UNVERIFIABLE 6 项

### M08 sprint punt 池（5 项）

主要 STILL_PUNT 1 项：#1 delete_by_node_id race window（→ M15-B1 联动）
UNVERIFIABLE 4 项

### M10 sprint punt 池（6 项）

主要 STILL_PUNT 2 项：
- #4 NodeCompletionResponse 死 schema
- #5 viewer /overview/stats 测试缺（→ 真漏洞 #10）

UNVERIFIABLE 4 项

### M11 sprint punt 池（12 项）

主要 STILL_PUNT 5 项：
- B1 R-X1 失败补偿 commit boundary（→ 真漏洞 #7 / 等 M17）
- B2 tasks.md R-X1 反例测试
- B8 parse_csv vs process_csv 大小检查重复
- B11 model_validate 三处冗余（cold_start_router）
- B12 error_report Pydantic round-trip 测试

DONE 2 项：B3/B6/B4
UNVERIFIABLE 5 项

### M12 sprint punt 池（13 项）

主要 STILL_PUNT 3 项：
- B3 create_snapshot 0 items 边界 e2e
- B5 DAO 7 处 project_id where 抽 _tenant_filter
- B7 list_snapshots 双查询合一（COUNT OVER）

UNVERIFIABLE 10 项

### M13 sprint punt 池（16 项）

主要 STILL_PUNT 5 项：
- B8 SSEErrorEvent.error_code Enum
- B13 SSE generator 占 AsyncSession 300s（→ 真漏洞 #4）
- B14 兜底 except 路径无测试
- B16 M02 Project ai_model 字段未实装（→ 真漏洞 #5）

DONE/PARTIAL 1 项：B12 prompt injection 局部防御
UNVERIFIABLE 11 项

### M14 sprint punt 池（12 项）

主要 STILL_PUNT 4 项：
- B1 link_node IntegrityError race FK NOT_FOUND
- B2 _check_node_exists 用基类 NotFoundError
- B11 NewsCreate extra='forbid' 立规
- B12 write_event 异常传播 update/delete/unlink 三路径 e2e（→ 真漏洞 #8）

UNVERIFIABLE 8 项

### M15 sprint punt 池（3 项）

| # | 项 | 状态 |
|---|---|---|
| B1 | write_event stub 替换为真 INSERT | STILL_PUNT — **真漏洞 #1 / 高耦合触发点** |
| B2 | M03-M08 service 裸 CRUD action_type | STILL_PUNT — **真漏洞 #2 / B1 联动** |
| B3 | OpenAPI schema 一致性自动校验 | UNVERIFIABLE |

---

## 维护规约

### 每 sprint 关闸 commit（5-10 min）

1. 本 sprint audit 新 punt → 追加到对应"M? sprint punt 池"段（含 grep 锚点）
2. 主线工作中"默默吸收"的历史 punt → 标 DONE + 引 commit hash
3. 重新评估 STILL_PUNT 项约定时机是否应延后/取消（不再适用）

### 每 sprint 启动 cold-start（必读）

Prompt 0 字面引用本表。冷启动按序读 + 闸门 2.5 reconcile 必查：
1. 本 sprint **应处理**的 punt 项（约定时机命中）
2. **触发点联动**——本 sprint 是否触发某项历史 punt 的"约定 M? 处理"批量复审
3. 真漏洞 Top 10 是否本 sprint 能顺修

### 高耦合触发点防御（元发现 #1 立规）

未来 punt 立项时若发现 ≥3 项指向同一未来动作 → **自动升 P1 提前规划**到目标 sprint
计划段，不许"分散登记"。

---

## 关联

- 9 个 audit 文件：design/audit/m{05,06,07,08,10,11,12,13,14,15}-pilot-template-validation.md
- handoff §2.1 M01 后置债 + §0a 历史快照 M02 后置债
- 立规来源：feedback_kb_design_principles（过期触发 + 增量 vs 周期）+ feedback_inbox_7day_rule（>7 天必处置不许"再想想"驻留）
