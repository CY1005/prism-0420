---
title: M06 sprint 实证 + R1/R2 命中比例 + L1 第五数据点
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M06 sprint 闸门 2.5 reconcile 三栏 + R1/R2 review 沉淀。

  - 闸门 2.5 三栏：A 8 / B 0 / C 5（**第二次 B 栏 0 项** / M05 首次 / M06 复用）
  - R1=3 subagent + R2=1 合并 Opus subagent 命中（与 M02-M05 四数据点对照）
  - L1+L2+L3 节奏第五次实证（五数据点稳定 → 默认范式可作 M07-M20 模板）
  - R-X2 第二真注入实证（M04 第一已立 / Protocol 4 参签名复用零摩擦）
  - PT1-PT3 模板复用判定（不复用 PT1+PT3，复用 PT2，已回填 m01 audit）
last_reviewed_at: 2026-05-08
---

# M06 sprint 实证 + Review 命中比例

## 闸门 2.5 reconcile 三栏（M06 sprint 启动当天 / 第二次 B 栏 0 项实证）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 8 | A1 Node back_populates / A2 conftest fixture 复用 / A3 §14.5 段补（默认范式复用）/ A4 ck_clause 别名规范化（M05 punt 接通）/ A5 R-X2 第二真注入 / A6 get_for_embedding A 路径 / A7 IntegrityError 转换 / A8 batch_create_in_transaction 推迟 |
| **B 待 CY 决策** | **0** | （第二次 B 栏 0 项 / M05 首次实证后默认范式延续）|
| **C 已自我消解** | 5 | C1 多表事务策略已决 / C2 cross-project 已决 / C3 R-X1 N/A / C4 N+1 batch 升级 punt 不触发 / C5 batch_get_by_nodes M12 才触发 |

**M06 sprint 元教训：B 栏 0 项第二次实证**——5 步分层分析法 step 1-2 grep 既有规则 + 自审 "我倾向的恰好是范式机械应用" 的双重防御，连续两个 sprint 命中归 A/C 栏，证明 M05 立的 reconcile 自审范式可复用。

---

## R1 review 命中（3 并行 subagent / 子片 1+2+3 合并审）

### R1-A spec+quality Opus

| 命中 | 项 | 处理 |
|---|---|---|
| P1 #1 | M06 design §5/§14.5 多表事务字面 `with db.begin():` 漂移（M04 §5 reconcile 范式漏跟进）| commit `c792263` 立修 §5 + Q4 决策记录消歧 |
| P2 #1 | delete_by_node_id 并发 `rows == 0` continue 跳过 activity_log（M04 R1-C C1.2 同款）| punt 到 M15 升级真 INSERT 时复审 |
| P2 #2 | update_ref 缺 IntegrityError 转换（design 不允许改 competitor_id 不必本期补）| punt 未来扩展时补 |
| P2 #3 | design §10 字面 vs 实装 batch competitor_ref 事件冲突 | punt 子片 5 audit 注释（与 M04 R1-C C1.2 同款）|
| P2 #4 | service docstring "with db.begin()" 跨模块字面漂移（M05 R1-A P3-1 同款）| punt M06+ 集中改 |
| SKIP | 多 | 模型/迁移/DAO/测试/错误码/lifespan/init 全对齐 |

### R1-B reuse Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1 | （0 项）| — |
| P2 #1 | _make_competitor / _make_ref 仅 dao test 单文件内聚（**符合"单文件不强制迁 conftest"规则**） | 预登记 M07+ 跨文件需求触发时迁 conftest |
| SKIP | 多 | 横切层 100% 命中 / shape 与 M04/M05 完全对齐 / ck_clause 别名规范化（M06 无枚举 CHECK 不适用）|

**M06 复用率 ~90%+**（横切层 / 范式 / fixture）— 优于 M02-M05 ~14-18% 内联重复率基线。

### R1-C quality+efficiency Sonnet

| 命中 | 项 | 处理 |
|---|---|---|
| P1-01 | create_ref IntegrityError 未区分约束名（M05 P1-01 立规回退；UNIQUE vs FK 语义混淆） | commit `c792263` 立修：err_text 检查 → CompetitorRefDuplicateError / CompetitorCrossProjectError |
| P1-02 | delete_by_node_id 缺 write_event 异常传播测试（M04 范式未复制）| commit `c792263` 立修：monkeypatch 测试 |
| P2 #1 | list_refs_by_node_for_delete 全列 SELECT（含 JSONB pros_and_cons）| punt M16 pilot 压测时升级 selective columns |
| P2 #2 | delete_competitor TOCTOU window count → delete | punt（与 M04 同款，已知可接受偏差）|
| SKIP | 多 | N+1 punt 已立 / count(*) 已用 / docstring 范式正确 / 三层防御完整 |

### R1 命中合计

- **P1 共 3 项**：CY 5e0e239 (M05) commit 已 set 范式 / commit `c792263` 含 3 项立修（design §5 + IntegrityError 区分 + write_event 测试）
- **P2 共 6 项**进 punt 池（M07-M16 各 sprint 接通）
- **SKIP 多项**：C 栏决议 + 已立范式 + 横切层范式

---

## R2 review 命中（1 合并 Opus subagent / 子片 4 单跑）

| 命中 | 项 | 处理 |
|---|---|---|
| P1 | （0 项）| — |
| P2 #1 | CompetitorRefResponse.display_name join 字段未实装（design §7 字面承诺）| punt M07/M12 sprint 接通时补 selectinload + schema 字段，或子片 5 子项回写 design 注释"由 caller 另查" |
| P2 #2 | pros_and_cons 响应类型 dict[str, Any] vs design ProsAndCons 类型退化 | punt 同款（前端类型契约弱化非运行错误）|
| P2 #3 | router 测试 ref update/delete 缺 404 e2e 闭环（service 层有但 router 层缺）| punt M07 sprint 启动前补 2 个 e2e test |
| SKIP | 5 | total=len(items) 范式延续 / pros_and_cons 空 case 序列化正确 / 双 router 设计 / 4 条范式延续 / R1 已立修不重提 |

**R2 命中**：0 P1 + 3 P2 + 5 SKIP — **M02-M05 R2 P1 命中 0-1 区间，M06=0 稳定，第五次实证 1 合并 Opus subagent 默认范式有效**。

---

## R-X5 子选项实证（M06 sprint 新 + M02-M05 复用）

### 子选项 1 — A5 R-X2 第二真注入（M04 第一已立 / Protocol 4 参签名复用）

**5 步分层分析**：M04 sprint 已立 L1 跨模块契约（NodeChildrenServiceProtocol 4 参 +
异常契约不 catch-all），M06 sprint 直接复用 — 5 步分层第 1 步 "是什么" 即识别为
"既有契约 plug-in"，无新决策。

**决策落地**：
- commit `86195cc` CompetitorService.delete_by_node_id (4 参) + lifespan
  register_child_service("competitor", ...) 真注入
- 异常契约 R1-C P1-01 立规：内层循环 `if rows == 0: continue` + write_event 异常
  向上传播（commit `c792263` test 闭环）

**元教训**：Protocol 4 参 M04 升级"零摩擦"复用 — 验证 M04 sprint 末元教训"5 步分层
分析法识别 L1 跨模块契约层"的复用价值。M06 是 R-X2 第二真注入方实证，与 M07 第三真
注入方（IssueService.orphan_by_node_id 不同语义）一起构成 R-X2 范式三数据点。

### 子选项 2 — A6 get_for_embedding A 路径（M04/M05 范式延续）

**5 步分层分析**：与 M04 同款（design §6.X 主标准已覆盖，不重复推导）。

**决策落地**：commit `86195cc` `competitor_service.py:get_for_embedding` 拼接
`name + description`（CY 决策 4：**url 不参与**）；test_svc_get_for_embedding_concat_name_description
+ test_svc_get_for_embedding_no_description + test_svc_get_for_embedding_not_found_returns_none
3 项 unit test 覆盖 + 显式断言 url 不出现。

### 子选项 3 — A9 IntegrityError 区分约束名（M05 P1-01 立规深化复用）

**5 步分层分析**：M05 P1-01 立规已识别 IntegrityError 不区分约束 = 错误码语义误导
caller，M06 R1-C 抓到回退实证 + 立修。

**决策落地**：commit `c792263` create_ref err_text 检查
`uq_competitor_ref_node_competitor` → CompetitorRefDuplicateError；其他（FK 违约）
→ CompetitorCrossProjectError(reason=competitor_concurrently_modified)。

---

## Punt 池总表（M06 sprint 末 6 项）

| 来源 | # | 项 | 优先级 | M? sprint 处理 |
|---|---|---|---|---|
| R1-A P2-1 | 1 | delete_by_node_id 并发 continue 跳过 activity_log | P2 | M15 升级 write_event 真 INSERT 时复审 |
| R1-A P2-2 | 2 | update_ref 缺 IntegrityError 转换（design 不允许改 competitor_id）| P3 | 未来扩展时补 |
| R1-A P2-3 | 3 | design §10 字面 vs 实装 batch competitor_ref 事件 punt 注释 | P3 | M15 sprint 顺手回写 design |
| R1-B P2-1 | 4 | _make_competitor / _make_ref 跨文件需求触发时迁 conftest | P3 | M07+ sprint 启动前评估 |
| R1-C P2-1 | 5 | list_refs_by_node_for_delete 全列 SELECT（含 JSONB）| P2 | M16 pilot 压测时升级 selective columns |
| R2 P2-1 | 6 | CompetitorRefResponse.display_name join 字段未实装 | P2 | M07/M12 接通时补 selectinload + schema 字段 |
| R2 P2-2 | 7 | pros_and_cons 响应类型 dict[str, Any] 退化（前端类型契约弱化）| P3 | 同 P2-1 一并修 |
| R2 P2-3 | 8 | router 测试 ref update/delete 404 e2e 缺失 | P2 | M07 sprint 启动前补 |

**M05 punt 池接通进度**（M06 sprint 期）：
- M05 R1-B P2-2（ck_clause 别名规范化）：✅ M06 子片 0 commit `c84f6f2` 顺修
  m05_version_timeline.py 改为 `as _ck_clause`（5 处 m01-m05 一致）
- M05 R1-A P2-2（list_by_node id DESC tie-break 不在索引）：punt 继续到 M16
- M05 R1-A P2-3（VersionNotFoundError reason 字段）：punt 继续到 M01 auth 统一审计

**M04 punt 池接通进度**（M06 sprint 期）：
- M04 R1-C C6.1（delete_by_node_id N+1）：M06 单 node refs ≤ 10-20 不触发，punt 继续
- M04 R1-A B3（IntegrityError race → 500）：M06 同款 race（UNIQUE node, competitor）
  ✅ A9 + R1-C P1-01 立修干净起步
- M04 R1-A A6（batch_get_by_nodes service 缺包装）：M12 才触发，M06 不触发

---

## L1+L2+L3 节奏第五次实证（M02-M06 — 五数据点稳定）

| 节奏层 | M06 sprint 表现 | 与 M02-M05 差异 |
|---|---|---|
| L1 总则（sprint ≥1 次 + ≥50 行 OR ≥2 文件 + 触发例外）| ✅ 全合规：R1 (3 sub) + R2 (1 sub) 共 2 次 review，子片 5 不单跑（≥80% SKIP 例外）| 与 M02-M05 一致 |
| L2 sprint 计划（design §14.5 必有）| ✅ commit `c84f6f2` 含 §14.5（默认范式复用 + 不重复说明）| 与 M03-M05 一致；M06 启用"默认范式复用"简写 |
| L3 实证回写（本文件）| ✅ accepted | 与 M02-M05 同款 |

**五数据点稳定结论（M07+ sprint 复用）**：
- R1=3 subagent (spec+quality Opus / reuse Sonnet / quality+efficiency Sonnet)
- R2=1 合并 Opus subagent (spec + quality + simplify)
- 子片 5 不单跑 + schema 子片禁单跑（≥80% SKIP 例外）
- §14.5 段可简写引用本 audit "默认范式复用"

---

## PT1-PT3 复用判断（已回填到 m01-pilot-template-validation.md）

- **PT1**（最简 + schema 都支持）：❌ 不复用 — M06 是档案页竞品参考主表，所有字段必须可用；M18 baseline-patch get_for_embedding A 路径已实装非"预留"
- **PT2**（ADR-004 凭据路径）：✅ 复用 — Router check_project_access 走 ADR-004；M06 design 凭据路径未改 ADR-004 = 抽象成功
- **PT3**（预留 schema + CI 禁引用）：❌ 不复用 — M06 无预留 model

---

## 元教训（M06 sprint 新增）

### 新增 1 — Protocol 4 参签名"零摩擦"复用实证

**触发**：M06 是 R-X2 第二真注入方。M04 sprint 升级 Protocol 4 参时对所有
M03/M04/M06/M07 design 真相源回写 5 处，M06 sprint 启动直接 plug-in
CompetitorService.delete_by_node_id (4 参 含 actor_user_id) 完全无摩擦。

**关键决策点**：M04 sprint "5 步分层分析法识别 L1 跨模块契约层 + 升级 Protocol 而
非本模块绕"的元教训，在第二真注入方实证为零修改成本。如果 M04 sprint 当时本模块绕
（contextvar 注入 / 跳过 cascade activity_log / 共享变量），M06 sprint 启动会
撞同款问题需重新决策；M04 升级 Protocol 让 M06+ 后续 sprint 直接复用。

**沉淀**：feedback_problem_layered_analysis 已含此实证（M04 sprint 末
"5 步法实战示例 2"段）；M06 sprint 是该规则首次"复用价值"实证（非新拦截）。

### 新增 2 — 闸门 2.5 三栏 B 栏 0 项第二次实证（M05 立 / M06 复用）

**触发**：M05 sprint 元教训立"自审一问必先 grep 既有规则"，M06 sprint 启动初版直接
按规则跑（5 步分层 step 1-2 grep / 自审"我倾向的恰好是范式机械应用"）— 8 项原候选
全部 grep 命中 L1/L3 锁规归 A 栏。

**关键决策点**：M05 立的 feedback_problem_layered_analysis 失效信号
（"闸门 2.5 reconcile 自审仪式化失效 = 没做"）在 M06 sprint 是第一次"防御未来"
而非"修复存量"实证。

---

## 维护规则

- 本文件 status=accepted（M06 sprint 关闸时）
- M07 sprint 启动闸门 2.5 reconcile pass 时复用本文件 R1/R2 命中比例数据点 +
  punt 池本期到期项（B1 _make_competitor/_make_ref 跨文件需求 / B6
  CompetitorRefResponse.display_name 接通 / B8 ref 404 e2e test）
- M07 是 R-X2 第三真注入方（IssueService.orphan_by_node_id 不同语义：SET NULL）
- M11/M17 sprint 启动时 batch_create_in_transaction 接通（M06 同款 punt）
- M16 sprint 落 R-X3 真消费时审 list_refs_by_node_for_delete 列裁剪
