---
title: prism-0420 跨 sprint Punt 池总表
status: living-doc
owner: CY
created: 2026-05-08（M15 sprint 收官后建立）
last_updated: 2026-05-08
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

## 状态分布快照（2026-05-08 baseline）

| 状态 | 项数 | 占比 | 说明 |
|---|---|---|---|
| **STILL_PUNT** | 30 | 32% | 代码完全没动，问题还在 |
| **DONE** | 15 | 16% | 代码已落实（部分被 sprint 主线"默默吸收"无人关闸）|
| **PARTIAL** | 1 | 1% | 部分子项做了 |
| **UNVERIFIABLE** | 46 | 49% | 设计意图 / 性能压测 / 未来 sprint 才触发 / docstring 注释类（非代码状态可验证）|
| **OBSOLETE** | 2 | 2% | punt 已不适用 |

---

## 🔴 真漏洞（约定时机已过 + STILL_PUNT / 按严重度排序）

| # | punt | 来源 | 约定 | 影响 | 推荐处理 |
|---|---|---|---|---|---|
| 1 | **write_event stub 仍未替换为真 INSERT** | M15-B1 | 后续独立 sprint | **critical** — M02-M14 全部 activity_log 事件未持久化；M15 owner 表零写入；前端 timeline / 审计追溯空数据 | M16 启动子片 0 prep 内吸收（β 路线） |
| 2 | **M03-M08 service ~14 处裸 CRUD `action_type="create/update/delete"`** | M15-B2 | 与 B1 同 sprint | **high** — 一旦 B1 落地，CHECK constraint 必爆（M14 baseline-patch α 路线已锁过去式命名规约）；R10-2 enum 守护失效 | 与 #1 同时做（issue/version/dimension/competitor/node） |
| 3 | **IssueResponse 漏 join 字段（node_name/created_by_name/assigned_to_name）** | M07 R2 P2-1 | M13/M15 集成期补 | **high** — design §7 字面承诺；前端 N+1 拼接；列表卡顿 | M16 启动 reconcile 时拍 |
| 4 | **SSE generator 占 AsyncSession 300s** | M13-B13 | M16/M17 立异步 SSE 策略 | **high** — 10 并发即吃光默认 10 PG 连接池；生产可能拒服务 | M16 启动必查（M16 是 Queue 后台 / 同款 long-lived session 风险） |
| 5 | **M02 Project.ai_model 字段未实装** | M13-B16 | M14+ baseline-patch | medium — M13 LLM 集成走 fallback；M14 已过未补 | M16 启动子片 0 prep 顺修（alembic add column 1 步） |
| 6 | **M07 update 不支持 detach (None→NULL)** | M07 R1-A P2-2 | design §3/§7 reconcile + 产品决策 | medium — issue 节点关联无法解除；M14 link/unlink 已支持但 M07 主表残缺 | M16 启动让 CY 拍是否补 |
| 7 | **M11-B1 R-X1 失败补偿 commit boundary** | M11 R2 P1-01 punt | M17 异步 zip 导入时 | critical 但**未到约定** | 等 M17 sprint（按计划） |
| 8 | **M14-B12 update/delete/unlink write_event 异常传播 e2e** | M14 R2 punt | M14 baseline-patch | medium — M02+ 元教训纪律 3 写路径无 e2e 覆盖 | 与 #1+#2 同 sprint 做 |
| 9 | **M05-2/14 + M06-1 + M07-7 + M08-1 多模块 `if rows == 0: continue` race window** | 多 sprint | M15 升级 INSERT 时复审 | medium — B1 落地后必须一并复审；不复审会 silently 改变行为 | 与 #1 同 sprint 联动复审 |
| 10 | **M10-5 viewer /overview/stats 测试缺** | M10 R2 P2 #3 | M11 启动前补 | low — endpoint 行为正确，仅测试覆盖度 | M16 启动顺手补 |

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

**M06-4 / M11-B3 / M11-B6 / M02-7（_ck_clause helpers）** 等 punt 在后续 sprint 主线
工作中**顺带 done** 而无人关闸标记。没有自动审计机制就会假装 STILL_PUNT，跟踪噪声。

**立规**：每 sprint 关闸 commit 必跑"DONE 检查"——audit 文件 punt 池总表标 DONE 的项
同步标到本表。本次 baseline 已识别 15 项 DONE。

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

### M05 sprint punt 池（19 项）

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
