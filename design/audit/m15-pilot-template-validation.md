---
title: M15 sprint 实证 + R1/R2 命中比例 + L1 第十三数据点（**纯读 R10-2 owner 模块** / R1=1 合并 Opus M10 范式复用 / 横切 enum owner 责任首发）
status: accepted
owner: CY
created: 2026-05-08
purpose: |
  M15 sprint 闸门 2.5 reconcile + R1/R2 review 沉淀（**纯读 R10-2 owner 模块 /
  R1=1 合并 Opus M10 纯读范式复用 / 横切 activity_log 表 owner 责任首发**）。

  - 闸门 2.5 三栏：A 6 / B 0 / C 10（**第十次 B 栏 0 项**；M05+M06+M07+M08+M10+M11+
    M12+M13+M14+M15 十连稳定）
  - R1 = 1 合并 Opus subagent 子片 1+2+3 合并审（M10 纯读范式复用 / 1 P1 立修 + 3 P2
    punt）
  - R2 = 1 合并 Opus subagent endpoint 单审（M02-M14 默认 / 2 P1 立修 + 2 P2 punt）
  - L1+L2+L3 节奏第十三次实证 / M02-M15 默认范式作 M16+ 模板
  - 纯读 R10-2 owner 模块新教训 4 条 sink
last_reviewed_at: 2026-05-08
---

# M15 sprint 实证 + Review 命中比例

## 模块特性（与 M02-M14 对比）

| 维度 | M02-M08 业务 | M10 纯读 | M11 R-X1 | M12 R-X3 只读 | M13 LLM+SSE | M14 全局豁免 | **M15 纯读 owner** |
|---|---|---|---|---|---|---|---|
| 写自表 | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **横切 owner** | N/A | N/A | N/A | N/A | N/A | N/A | **✅ activity_log（首发 R10-2）** |
| 自调 write_event | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | **❌（design §10 字面 N/A）** |
| 跨模块 enum 维护责任 | N/A | N/A | N/A | N/A | N/A | N/A | **✅（65 ActionType + 16 TargetType）** |
| project_id NULLABLE | N/A | N/A | N/A | N/A | N/A | N/A（无 project_id 字段） | **✅（M14 baseline-patch 实装）** |
| ImmutableMixin | N/A | N/A | N/A | N/A | N/A | N/A | **✅ append-only / 无 updated_at** |
| double-layer 权限防御 | ✅ | ✅ | ✅ | ✅ | ✅ | owner-vs-admin | **✅ Router PermissionDenied + Service Forbidden 双语义** |
| 首发"读权限 403"测试 | N/A | N/A | N/A | N/A | N/A | N/A | **✅（M02-M14 写 403 思想横切到读）** |

---

## 闸门 2.5 reconcile 三栏（**第十次 B 栏 0 项**）

| 栏 | 项数 | 关键项 |
|---|---|---|
| **A 机械可做** | 6 | A1 §14.5 sprint review 拆分计划段 / A2 元教训防御 actionable 14 条 / A3 model project_id NULLABLE / A4+A5 ActionType+TargetType enum +5+2 / A6 M14 baseline-patch 反向回写（α 路线 5 处 service.py + 7 处 e2e + design §10）|
| **B 待 CY 决策** | **0** | **第十次 B 栏 0 项**（M05-M15 十连稳定 / B1 命名规约冲突按 feedback_problem_layered_analysis L1 锁裁决型 AI 自决 α）|
| **C 已自我消解** | 10 | C1 ImmutableMixin 已存在 base.py:37 / C2 conftest 既有 fixtures 充足 / C3 R-X1 N/A / C4 文件上传 N/A / C5 LLM hot path N/A / C6 R-X3 横切表豁免（DAO 直 JOIN）/ C7 cross-project node N/A / C8 viewer 写 403 N/A → 替换为读 403 / C9 check_project_access rank 系统等价 design §8 list / C10 IntegrityError N/A 纯读 |

---

## R1 review 命中（1 合并 Opus / 子片 1+2+3 合并审 / 共 1 P1 立修 + 3 P2 punt）

> R1 范式：**M10 实证 1 合并 Opus 复用**（纯读模块特化 / 区别于 M02-M09/M11/M12/M14
> 业务模块默认 R1=3 subagent 并行）。子片 0 prep §14.5 self-correct 回写"纯读模块
> R1 = 1 合并 Opus / 业务模块 R1 = 3 subagent 并行"。

### R1-A 命中（合并 Opus）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | ActivityStreamInvalidFilterError 注册但 schema model_validator 抛裸 ValueError（design §13 own ErrorCode 无 raise caller / dead exception）| **立修** commit d527632：schema 层 raise ActivityStreamInvalidFilterError 替 ValueError + 测试断言 err.code = ACTIVITY_STREAM_INVALID_FILTER + http_status=422 + details 含 from_dt/to_dt |

### R1 P2 punt 池

| 命中 | 项 | 处理 |
|---|---|---|
| P2-1 | design §3 model code block 字面（line 317-322）`Mapped[ActionType]` / `metadata` 与实装 `Mapped[str]` + `event_metadata` 漂移 design 端未回写 | 子片 5 关闸 commit 9ca130e+ 子片 5 commit：design §3 加 Disambiguation 段统一回写 |
| P2-2 | design §3 line 396 list_for_team 签名含 user_id 参数 vs 实装无 | 同 P2-1 在 Disambiguation 段说明 |
| P2-3 | ci-lint 加 L13 守 M15 self not-write_event（design §10 N/A 字面 / 0 成本）| **立修** 子片 5 关闸：scripts/ci-lint.sh L13 grep `write_event` 在 activity_stream_service.py 中应不命中 |

---

## R2 review 命中（1 合并 Opus / 子片 4 endpoint 单审 / 共 2 P1 立修 + 2 P2 punt）

| 命中 | 项 | 处理 |
|---|---|---|
| P1-1 | metadata 字段 e2e 字面缺测（M13 NEW 元教训直击 + M15 字段名重映射比 M13 更脆弱）| **立修** commit 9ca130e：test_get_stream_metadata_field_literal_in_response 断言 "metadata" key 存在 + "event_metadata" 不在 + 值映射完整 |
| P1-2 | Pydantic Filter 422 边界 e2e 缺测（M15 是首个纯读 + 6 维 query filter 模块 / Pydantic Depends 暴露面最大）| **立修** commit 9ca130e：page_size=201 → 422 + action_type=invalid → 422 双 e2e |
| P2-1 | ActivityStreamForbiddenError e2e 不可达 disambiguation 注释（与 R1 P1-1 InvalidFilterError "schema 注册无 raise"不同结论：本项是 router 抢先 + service 防御未来 / 双层防御非 dead code）| **立修** 子片 5：service _check docstring 加段说明 |
| P2-2 | cross-tenant member-of-both e2e 缺测（DAO unit 已字面验过 / e2e 显式补"用户既是 A 又是 B 的成员，访问 A 不混入 B 事件"）| **立修** 子片 5：test_get_stream_member_of_both_only_sees_self_project |

**M15 R1+R2 命中数据**：R1=1 P1 + 3 P2 / R2=2 P1 + 2 P2；M02-M15 R2 P1 命中 0-4 区间，M15 落在下沿（2 P1）—— 纯读模块 + 首个 R10-2 owner 形态特殊但契约纪律未免除（M14 NEW 元教训应用）。

---

## L1+L2+L3 节奏第十三次实证（**十三数据点稳定 → M16+ 默认范式作模板**）

| 层 | 内容 |
|---|---|
| L1 总则 | sprint ≥1 次 review + ≥50 行 OR ≥2 文件触发；触发例外条款全合规；**纯读模块 R1 = 1 合并 Opus / 业务模块 R1 = 3 subagent 并行**（self-correct 回写 §14.5）|
| L2 sprint 计划 | design §14.5 sprint review 拆分计划段（commit 29b0aaa 子片 0 prep 落地）|
| L3 实证回写 | 本文件 |

---

## 元教训防御 actionable 应用情况（**14 项元教训 / 主动复制不等抓**）

| # | 元教训 | M15 应用结果 |
|---|---|---|
| 1 | viewer 写 403 全覆盖（M07 立 / M08-M14 应用）| **N/A 显式声明 + 首发"读权限 403"测试**（C-5 候选 β 字面 / e2e T3 viewer 读 → 403 PermissionDenied / unit test_check_access_viewer_raises_forbidden 同思想）|
| 2 | write_event 异常传播（M04+ 范式）| **N/A 显式声明**（design §10 字面 + L13 守护 + service 不导入 write_event）|
| 3 | cross-tenant 404（M02 范式）| **✅ 主动复制**（DAO 强 project_id 过滤 + e2e T4/T6/member-of-both 三场景）|
| 4 | cross-project node 404 | **N/A 显式声明**（M15 不消费 node 实体）|
| 5 | IntegrityError 区分约束名（M05 P1-01）| **N/A 显式声明**（纯读无 INSERT）|
| 6 | M12 元自审 — L1 锁裁决型 P1 自决不让 CY 拍 | **✅ 已应用**（B1 命名规约冲突子片 0 prep 自决 α / R1+R2 各 P1 全自决处理）|
| 7 | R1.5 reconcile checkpoint（M10 NEW）| **✅** R2 dispatch 前 grep 验 R1 立修无冲突 |
| 8 | M11 NEW R-X1 失败补偿 commit boundary | **N/A**（无 orchestrator）|
| 9 | M11 NEW 文件上传 file.size + sanitize | **N/A**（无上传）|
| 10 | M13 NEW "3 端点全覆盖"形态特殊不免除 | **✅ 应用**（list_for_team 形态特殊 disambiguation 落 design §3 + §7 + §14.5 字面 / Router 不暴露 endpoint 子片 5 audit 字面声明 M20 sprint own）|
| 11 | M13 NEW design metadata 字段集每条 e2e 字面验 | **R1 ❌ 未抓 → R2 P1-1 立修 ✅** 补 e2e 字面 metadata 映射验证 + 字段名重映射防漂移 |
| 12 | M14 NEW write_event project_id Optional | **✅ 实装**（ActivityLog.project_id NULLABLE column + scaffold 4 字段注释 + UI 时间线"全局事件"分组语义留 / e2e T13 全局事件不召回验证）|
| 13 | M14 NEW N/A 元教训显式声明范式 | **✅ 应用**（本表逐条 N/A 声明 + 测试文件 docstring 双重 / §14.5 字面）|
| 14 | M14 NEW endpoint 形态特殊不免除契约纪律 | **✅ 应用**（list_for_team 双形态 disambiguation / metadata 字段名重映射 e2e 验 / Pydantic Depends 422 边界 e2e 验 / R2 直接命中说明形态特殊不免除）|

---

## 纯读 R10-2 owner 模块新教训 4 条 sink（M16+ 复制 / sink memory 候选）

### 新教训 1：横切表 owner 模块的 enum 字面同步责任

**Why**：M15 是 activity_log 横切表 owner（R10-2），ActionType 65 + TargetType 16 字面
分散在 model `_ACTION_TYPES` / `_TARGET_TYPES` tuple + schema StrEnum 65/16 值 +
CHECK constraint IN 列表 + Alembic 迁移文件 import — 4 处必须严格同步。M14 baseline-patch
反向回写（α 路线 news_*）在 4 处都加了；test_action_type_enum_matches_model_action_types
unit 测断言全集相等防漂移。

**How to apply**：未来新模块若加 ActionType/TargetType（如 M16 ai_snapshot / M17 import
扩 8 个 import_*）必同步 4 处；M15 schema enum vs model 字面 set 比较 unit 测是首道
防御。

### 新教训 2：纯读模块 R1 = 1 合并 Opus（M10 范式复用 / 区别业务模块 3 subagent 并行）

**Why**：M10 audit 已锁"纯读聚合范式 4 子片简化 / R1 三 subagent 合并为 1 Opus"。M15
是 M10 同款纯读模块（ADR-003 规则 3 横切表豁免 / 1 endpoint 查询 / 无写自表 / 无跨模块
写依赖）→ R1 走 M10 实证不走业务模块默认。子片 0 prep §14.5 我误抄业务模块"3 subagent
并行"，子片 3→R1 切换时 self-correct 回写。

**How to apply**：未来新模块判定 R1 范式时先看是否纯读：纯读模块（R3-5 +/- ADR-003
规则 3）默认 R1=1 合并 Opus；业务模块（R3-1 + 写自表）默认 R1=3 subagent 并行。design
§14.5 sprint review 拆分计划段必须显式声明 R1 范式。

### 新教训 3：双层权限防御 service unit 不可达 e2e 是合理设计而非 dead code

**Why**：M15 service `_check_activity_audit_access` 抛 ActivityStreamForbiddenError 但
e2e 永远不可达（router check_project_access role="editor" 抢先抛 PermissionDenied）。
与 R1 P1-1 立修的 InvalidFilterError "schema 注册无 raise" 表面相似但**结论相反**：
前者是真 dead exception（schema 路径无 raise）；后者是 router 抢先 + service 防御未来
caller（如 background task / admin 后台 / future GraphQL resolver 跳过 router 直调
service）。

**How to apply**：未来 R1/R2 reviewer 抓"ErrorCode 注册无 raise / e2e 不可达"时必区分
两种结论 — 看 service unit 测是否可达：可达 = 防御未来非 dead；不可达 = 真 dead 必修。
docstring 注释字面声明"双层防御非 dead code"防 R1 反复抓。

### 新教训 4："读权限 403"是首发测试范式（M02-M14 写 403 思想横切到读）

**Why**：M02-M14 11 模块"viewer 写 403 全覆盖"元教训仅适用业务模块写端点。M15 是首个
纯读模块需测"viewer 读 403"——同思想但形态对称翻转。e2e T3 / service unit
test_check_access_viewer_raises_forbidden 双重覆盖。

**How to apply**：未来纯读模块（M16 ai_snapshot 读 / M18 semantic_search 读 / M19
导入导出 status 读）若有 role-based 权限差异都需走"读权限 403"测试范式；design §14.5
元教训防御 actionable 清单加新条目"纯读模块读权限 403 全覆盖（M15 立 / 首发）"。

---

## 元自审教训（无主流程错误）

M15 sprint **无主流程错误**——R1+R2 命中均按 M02-M14 范式处理：
- 闸门 2.5 三栏第十次 B 0 项稳定
- L1 范式既锁的 B1 命名规约冲突 AI 自决 α（M12 元自审教训应用合规 / 不报 CY）
- R1=1 合并 Opus self-correct 回写 §14.5（M10 纯读范式复用 / 子片 3→R1 切换时识别）
- M14 NEW 元教训 14 项主动复制清单 100% 落 §14.5 字面 + 实装核对
- R1.5 reconcile checkpoint M10 元教训应用合规（R1 P1-1 立修 + R2 dispatch 前 grep 验证 / R1+R2 立修无冲突）

---

## design 回写（关闸 commit 同 commit）

- §3 Disambiguation 段新增（R1 P2-1 + P2-2 / Mapped[str] 三重防护 + event_metadata
  列名重映射 + list_for_team user_id 参数 disambiguation）
- §10 字面"M15 无 activity_log 事件"已通过 ci-lint L13 守护
- §13 ErrorCode 全集（M15 own 3 + M20 baseline-patch 8 / R13-1 90→101 守护）
- §14.5 sprint review 拆分计划段（子片 0 prep 落地 / 含 M14 NEW 14 项元教训防御
  actionable 清单 + R1=1 合并 Opus 纯读范式 self-correct 字面）

---

## Punt 池总表（M15 sprint 完成期 / 后续 sprint 顺手清）

| # | 项 | 来源 | 推荐时机 |
|---|----|------|---------|
| B1 | write_event stub 替换为真 INSERT（design §3 R10-2 + B7 字面）| design 字面 | 后续独立 sprint（同时回扫 M03/M04/M05/M06/M07/M08 service action_type 字面是否过去式 / 命名规约 baseline-patch 二次反向回写 / 工作量约 2-4h）|
| B2 | M03-M08 service 中是否仍有裸 CRUD action_type=`"create"/"update"/"delete"`（M14 sprint 已修 5 处 / 其他模块**未验证**）| R2 元自审 | 与 B1 同 sprint 处理 / 同时进行命名规约统一 |
| B3 | OpenAPI schema 一致性自动校验（response_model 字段 / 类型导出）| R2 §8 | 后续 simplify 体检统一加 |

---

## sprint 总览数据

- **commits**：7 主提交
  - 29b0aaa 子片 0 prep（§14.5 + M14 baseline-patch 反向回写 α 路线 + 元教训 14 条清单）
  - 8889ec5 子片 1（ActivityLog model + alembic + 9 model tests）
  - af9120c 子片 2（ActivityStreamDAO + 16 unit tests + conftest make_activity_log fixture）
  - 0fa19ad 子片 3（Schema + 11 ErrorCode 3 own + 8 M20 baseline-patch + Service + 21 tests）
  - d527632 R1 立修（schema InvalidFilterError raise + design §14.5 R1 self-correct）
  - 4e9fd54 子片 4（Router 1 endpoint + 13 e2e）
  - 9ca130e R2 立修（metadata e2e 字面 + Pydantic 422 边界）
  - 子片 5 关闸 commit（本 audit + roadmap + handoff + design §3 Disambiguation + ci-lint L13 + service docstring + cross-tenant member-of-both e2e）
- **测试**：63 PASS（model 9 + DAO 16 + schema 8 + service 13 + e2e 17 含 R2 立修+P2-2 补）/ R13-1 90→101（+11）/ L12+L13 守护通过
- **新增 ErrorCode**：11（3 M15 own + 8 M20 baseline-patch）
- **新增 endpoint**：1（GET /api/projects/{project_id}/activity-stream）
- **新增模型**：1（ActivityLog）
- **新增表**：1（activity_logs / 横切共享 / R10-2 owner = M15）
- **新增 ci-lint 守护**：L13（M15 self not-write_event）
- **新增 conftest fixture**：make_activity_log（跨文件 helper 规则十一连）
- **跨模块接通**：M01 User 只读 JOIN（DAO list_stream user_name）/ M02 Project + ProjectMember 只读（service _check_activity_audit_access）
- **复用率**：~95%（service 100% / conftest fixtures 全调用 / DAO 直 JOIN 不嵌 service）
- **首发新教训**：4 条（横切 owner enum 同步责任 / 纯读 R1=1 合并 Opus 范式 / 双层防御非 dead code 区分 / 读权限 403 测试范式）

---

## 关联

- design 真相源：design/02-modules/M15-activity-stream/00-design.md
- 上游决策：ADR-003 规则 3 横切表豁免 + ADR-004 P1 require_user + 06-design-principles
  清单 5 全局豁免 + R10-2 横切表 owner
- 跨 sprint 元教训沉淀候选：feedback_problem_layered_analysis（R1=1 合并 Opus 纯读
  范式 self-correct + 双层防御非 dead code 区分）/ feedback_design_scaffold_reconcile
  （Disambiguation 段统一回写范式 / 防 design 字面与实装漂移）
