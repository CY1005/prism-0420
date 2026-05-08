---
title: M01 pilot 模板复用性验证（PT1-PT3 跟踪表）
status: tracking
owner: CY
created: 2026-05-07
purpose: |
  M01 design tests.md §12 列了 3 项"pilot 模板可复用性验证"——
  这是元设计校准，难以自动化。本文件作为 living tracker，在后续模块
  实施时回头核对：M01 沉淀的范式是否真的被复用，未复用的为什么。
last_reviewed_at: 2026-05-07
---

# M01 pilot 模板复用性验证

## PT1：「本期实现最简 + schema 都支持」模式可被复用

**M01 范式**：design §3 列了 7 张表（实装 3 + 预留 4），CI grep 守护 services/routers
不引用预留 model（design §9 + S5c 测试），未来扩展时只解禁 import 不动 schema。

**复用候选模块**：

| 模块 | 复用情形 | 实施时回写状态 |
|------|---------|--------------|
| M02 项目管理 | 4 表 (projects/members/dim_configs/dim_types) 全实装,无预留模式 | ❌ 不复用 (2026-05-07): M02 是 tenant 锚点,所有字段必须可用; SearchConfig+rrf_k+similarity_threshold 是"现在建未来用"部分模式但属横切扩展非"预留 schema" |
| M03 模块树 | nodes 1 表全部本期实装,无预留模式 | ❌ 不复用 (2026-05-07): M03 是 M04-M19 树结构锚点,当前所有字段必须可用; A2 reconcile 加 description 字段是 M18 baseline-patch 被动接口需求,属横切扩展非"预留 schema" |
| M04 维度记录 | dimension_records 1 表全部本期实装,无预留模式 | ❌ 不复用 (2026-05-07): M04 是档案页主表,所有字段（content JSONB / version / created_by / updated_by）必须可用; M18 baseline-patch get_for_embedding A 路径已实装非"预留 schema" |
| M05 版本时间线 | version_records 1 表全部本期实装,无预留模式 | ❌ 不复用 (2026-05-08): M05 是档案页版本快照主表,所有字段（version_label / summary / details / change_type / is_current / snapshot_data / release_mode）必须可用; M16 pilot 基线补丁 count_by_node 是 R-X3 对外契约**已实装**非"预留" |
| M06 竞品参考 | competitors + competitor_refs 2 表全部本期实装,无预留模式 | ❌ 不复用 (2026-05-08): M06 是档案页竞品参考主表（双表），所有字段（display_name/website_url/description + competitor_version/feature_coverage/tech_approach/pros_and_cons）必须可用; M18 baseline-patch get_for_embedding A 路径**已实装**非"预留" |
| M11 节点版本 | 是否预建 `node_versions` 表但本期只读？ | ⏳ M11 实施时核对 |
| M16/M17/M18 cron | 预留 cron config 表 vs 本期硬编码？ | ⏳ M16 实施时核对 |
| M07 dimension 配置 | 预留 dimension type 枚举扩展位 vs 本期固定？ | ⏳ M07 实施时核对 |

**校准动作**：每个候选模块 sprint 启动闸门时，新增 1 项 reconcile 检查
"是否复用 M01 PT1 模式"——若不复用，design §3 必须显式说明理由。

## PT2：ADR-004 凭据路径表可复用

**M01 范式**：ADR-004 §2 4 类凭据路径表 + §3 P2 信任链 + §3.6 P3 形态明示。
未来扩展凭据路径（P5 OAuth / P6 WebSocket）时只在 ADR-004 表加 1 行 + 1 个
`resolve_from_xxx` 方法签名，不改业务模块 design。

**触发场景（未来）**：

| 场景 | 触发动作 | 预期不发生的事 |
|------|---------|--------------|
| Q4 OAuth 启用（P5）| ADR-004 §2 表加 P5 行 + AuthService.resolve_from_oauth | M01 design §8 凭据路径表**不应**改动；其他模块 require_user 也不改 |
| Q5 Session 管理 + 强制登出 | ADR-004 §5 失效事件表加 1 行（"管理员强制登出"已预留）| M01 §10 audit 事件清单不变 |
| WebSocket 引入（P6）| ADR-004 §2 + ADR-002 第 4 项交叉引用扩展 | 业务模块 ws 路由各自走 require_user |

**校准动作**：上述任一场景实施时，先 grep `02-modules/*/00-design.md` 看
"凭据路径声明"段是否需修改——若有模块需改，说明 ADR-004 抽象失败，需回头补强。

## PT3：预留 schema + CI 禁引用 机制可复用

**M01 范式**：design §3 列预留 model（PasswordResetToken 等）+ §9 §10 CI grep
守护 + 实装侧 tests/test_m01_schema_guards.py S5c 自动化测试。

**复用判定**：每个有"本期不实装但 schema 预留"诉求的模块，必须三件齐全：

1. design §3 列预留 model + 标 "✅ 建表预留"
2. design §9 加 CI 守护伪代码（grep 模式）
3. scripts/ci-lint.sh 加对应 grep 规则 + tests/test_*_schema_guards.py 加自动化断言

**未来候选**：

| 模块 | 是否触发 | 三件检查 |
|------|---------|---------|
| M11 历史快照 | 预留 snapshot_diff 表？ | ⏳ |
| M14 metrics | 预留 metric_aggregation 表？ | ⏳ |

## 维护规则

- 每个候选模块 sprint 闸门 2.5 reconcile pass 时，把本表对应行从 ⏳ 转 ✅/❌
- 若 ❌（不复用），design 必须写明理由，本表 link 过去
- 全部 ⏳ 转完后本文件 status 改 accepted
