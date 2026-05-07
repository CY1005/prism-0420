---
title: M02 sprint 实证子选项 + R-X5 子选项清单回写
status: tracking
owner: CY
created: 2026-05-07
purpose: |
  M02 sprint 启动期 design §3.X 标了 4 处 R-X5 🟡 子选项待 sprint 实证 (case-by-case
  决策 + 登记)。本文件按 5 步分层分析法 (memory feedback_problem_layered_analysis)
  逐项实证 + 沉淀 → 推动 R-X5 子选项清单升级 (元原则 1 类 1 实证驱动)。

  另含: M02 R1+R2 review 命中比例数据 (L3 数据驱动 M03/M04 sprint review 计划)
  + L1 总则触发粒度规则 (闸门 3.4) 实证。
last_reviewed_at: 2026-05-07
---

# M02 sprint 实证子选项

## R-X5 子选项 1 — C 路径 team_id 中间态写入策略 (design §3.X A1)

### 原标 🟡 候选
(a) API 不暴露 team_id (Schema 不含)
(b) Schema 暴露但 service 拒绝 (raise 422)
(c) DAO 完全允许 (最低限制)

### 5 步分层分析

| Step | 内容 |
|---|---|
| 1 是什么 | M02 期 team_id 列存在 (UUID nullable 无 FK), teams 表 M20 才建; 谁拒绝越界写入 |
| 2 分层 | L3 实证后归纳 (R-X5 子选项已留空) |
| 3 本模块 | 选 (c) DAO 完全允许 |
| 4 跨模块 | M03-M19 不写 projects.team_id (只读), 无影响; M20 ALTER ADD CONSTRAINT 前 data migration reset 不合法 team_id (design §3.X A1 ① 已声明) |
| 5 沉淀 | 本文件 (sprint 内一次性登记, 不每次决策都创建文件) |

### 决策落地 (sprint 内实证)
- **子片 2** `api/dao/project_dao.py:13` docstring: "本期 ProjectDAO.create 不校验 team_id 合法性"
- **子片 3** `api/services/project_service.py:14` docstring: "service 不校验 team_id 合法性 — DAO 完全允许 (R-X5 子选项实证决: schema 已允许任意 UUID, service 拒会引入双源真相)"
- **子片 3** test `tests/test_m02_service.py::test_c_path_team_id_service_does_not_reject_arbitrary_uuid` 实证

### 回写 design §3.X A1 子选项清单
- 🟢 实证决: **C 路径 (DAO 完全允许)** — 不引入双源真相
- 后续 M20 sprint 启动时按 design §3.X A1 M20 回写 checklist ① 做 data migration reset

---

## R-X5 子选项 2 — A 路径 SearchConfig 类型 owner (design §3.X A2)

### 原标 🟡 候选
(a) M02 own raw types (api/schemas/project_schema.py)
(b) 共享 horizontal (api/schemas/shared.py)

### 5 步分层分析

| Step | 内容 |
|---|---|
| 1 是什么 | get_search_config 返回类型 SearchConfig 定义放哪 |
| 2 分层 | L3 实证后归纳 |
| 3 本模块 | 选 (a) M02 own |
| 4 跨模块 | M18 sprint 期 import api.schemas.project_schema.SearchConfig (M18→M02 分层依赖) |
| 5 沉淀 | 本文件 + design 回写 |

### 决策落地
- **子片 3** `api/schemas/project_schema.py:127-132` SearchConfig dataclass(frozen=True)
- **子片 3** `api/services/project_service.py:212` get_search_config 返回 SearchConfig
- **子片 3** test `tests/test_m02_service.py::test_get_search_config_returns_defaults` 实证 default 路径

### 回写 design §3.X A2 子选项清单
- 🟢 实证决: **A 路径 (M02 own)** — 建 horizontal shared.py 仅为 1 类型 = YAGNI; M19/M20 也用 SearchConfig 时再上抽

---

## R-X5 子选项 3 — B 路径 move-team OpenAPI 处理 (design §3.X A3.2)

### 原标 🟡 候选
(a) 不实装 router → OpenAPI 不含
(b) 占位 router 返回 501 stub → OpenAPI 含

### 5 步分层分析

| Step | 内容 |
|---|---|
| 1 是什么 | move-team endpoint 本期不实装, OpenAPI schema 是否含 |
| 2 分层 | L3 实证后归纳 |
| 3 本模块 | 选 (a) 不实装 → OpenAPI 不含 |
| 4 跨模块 | 前端 codegen 不会误生成 stub client; M20 sprint 启用时一并实装 + codegen 自然同步 |
| 5 沉淀 | 本文件 + design 回写 |

### 决策落地
- **子片 4** `api/routers/project_router.py:16-23` scaffold TODO 注释 4 字段 (S2 模板)
- **子片 4** test `tests/test_m02_routers.py::test_b_path_move_team_endpoint_not_registered` 实证 FastAPI 返 404

### 回写 design §3.X A3.2 子选项清单
- 🟢 实证决: **不实装 router** — 占位 501 易误导前端 codegen 认为 endpoint 已就绪

---

## R-X5 子选项 4 — R13-1 未实装期 ErrorCode 标记位置 (design §3.X A3.1)

### 原标 🟡 候选
(a) code 注释 (在 codes.py / exceptions.py docstring)
(b) design §13 表加列
(c) ci-lint.sh 加附加规则 (类似 R13-2: 强制 raise caller 才允许 ErrorCode 存在)

### 5 步分层分析

| Step | 内容 |
|---|---|
| 1 是什么 | ProjectArchivedError 子片 4 不 raise (move-team 不实装), 如何标记"未实装期 ErrorCode" |
| 2 分层 | L3 实证后归纳 |
| 3 本模块 | 选 (a) code 注释 — 最低成本 |
| 4 跨模块 | M03+ 同款 (pre-implant ErrorCode 等待 caller) 适用同款 |
| 5 沉淀 | 本文件 + 不入 ci-lint.sh 附加规则 (避免规则膨胀) |

### 决策落地
- **子片 3** `api/errors/exceptions.py` `class ProjectArchivedError` docstring:
  > "M02 sprint 期 ErrorCode + AppError 子类配齐 (R13-1 parity); raise caller 在 M20 sprint move-team router 实装时建. 标记位置 (R13-1 子选项实证): code 注释 (本段) — 不入 ci-lint.sh 附加规则."
- **子片 3** `api/errors/codes.py:54` 上方注释: "F2.3 M20 baseline-patch (move-team scaffold caller 子片 4 推迟 / R-X5 子选项实证标记位置=code 注释)"

### 回写 design §3.X A3.1 子选项清单
- 🟢 实证决: **(a) code 注释** — 最低成本, ci-lint.sh 不加附加规则避免膨胀

---

# M02 R1+R2 review 命中比例 (L3 数据驱动 M03/M04 计划)

## R1 命中比例 (子片 1+2+3 合并审, 3 subagent)

| Subagent | 命中 | SKIP | 命中率 |
|---|---|---|---|
| A Spec+Quality (Opus) | 12 (1 P0→R2 / 2 P1 / 8 P2 / 1 无) | — | 高 (合并审有信号) |
| B Reuse (Sonnet) | 1 真命中 (`_make_user` 重复) | 5 SKIP (合理) | 17% (1/6) |
| C Quality+Efficiency (Sonnet) | 7 命中 (3 与 A 重叠) | 11 SKIP | 39% (7/18) |

**实证结论**:
- ✅ schema 子片 (子片 1) 单跑预期 ≥80% SKIP 假设**部分成立** — Quality+Efficiency 在 schema 层确实多 SKIP, 但 Spec 在合并 service 后才能审业务
- ✅ 子片 1+2+3 合并审 R1 是对的: 3 subagent 共出 8 项立修, 5 项 punt 子片 5 design 回写
- ❓ 下次 M03 schema 子片是否能进一步合并?
  - 倾向: M03 仍按 R1 合并 schema+DAO+service 一起跑 (避免 schema 单跑信号弱)

## R2 命中比例 (子片 4 endpoint 单跑, 1 合并 subagent)

| Subagent | 命中 | SKIP | 命中率 | 总判 |
|---|---|---|---|---|
| Spec+Quality+Simplify 合并 (Opus) | 6 P1 立修 + 5 P2 punt | — | 高 (endpoint 是高命中区印证) | ❌ 不通过 → 修后 ✅ |

**6 P1 立修 (commit 待补)**:
1. MemberResponse 漏 user_name/user_email/created_at join 字段 → schema + DAO outerjoin + service 装配
2. DimensionConfigResponse 漏 dimension_type_key/name join → schema + DAO outerjoin + router
3. router 直调 db.execute(delete) 违反 §6 分层禁令 → ProjectDimensionConfigDAO.delete_one
4. batch_update dim_type 校验 N+1 → DimensionTypeDAO.list_by_ids 一次 IN
5. invite_member 不校验 invited_user_id 存在 (FK IntegrityError 吞成 MEMBER_ALREADY_EXISTS) → 预校 raise UserNotFoundError
6. check_project_access role typo 静默退化 viewer → 未知 role raise ValueError

**P2 punt (子片 5 follow-up 或 design 回写)**:
- update_project exclude_none 让 null 无法清字段 (语义讨论)
- update_project hasattr setattr 无白名单 (style)
- AiProviderUpdate 不强制 min_length (微问题)
- in-method/in-loop import (style)
- check_project_access vs require_owner 重复 JOIN (P1 但属性能优化, punt 子片 5)
- batch_update N 条 UPSERT 应用 ON CONFLICT (P1 但属性能优化, punt)
- _project_response/_member_response 单行 helper (R2 表认为可去, 但 R2 修后 _member_response 含 join 装配, 已不是单行)

**实证结论 (R2)**:
- ✅ endpoint 子片单跑信号强 — 6 P1 全部命中契约漂移/静默吞错/分层违例 (R2 review 设计的高命中区), 验证 L2 计划"endpoint 单跑保留独立性" 决策对
- ✅ Simplify P1 多与 Quality P1 重叠 (重复 JOIN / N+1) — 合并维度 subagent 在 endpoint 层证明可行
- ❓ 下次 M03/M04 endpoint 子片是否照搬 R2 单跑? — 倾向**是** (endpoint 阶段必须 spec+quality 合并跑)

**下游 M03/M04 sprint review 计划修订建议** (L3 数据驱动):
- R1 (schema+DAO+service 合并审): 保留, 3 subagent (spec+quality / reuse / quality+efficiency)
- R2 (endpoint 单审): 简化为 1 合并 subagent (spec+quality+simplify) — M02 实证 1 个 Opus 合并 subagent 出 6 P1 + 5 P2 已足够

---

# L1 总则 (闸门 3.4) 实证

| 总则 | 是否触发例外 | M02 实证 |
|---|---|---|
| sprint ≥1 次必跑 | — | ✅ R1+R2 共 2 次, 满足 |
| ≥50 行 OR ≥2 文件触发 | — | ✅ 每子片均触发 |
| 触发例外 (≥80% SKIP 合并下游) | 子片 1 ⏳, 子片 5 ✅ | 子片 5 (tests + audit + 文档回写) 不单跑 — 例外条款适用 |

**L1 改进提议** (M02 实证后归纳):
- 触发例外条款的"≥80% SKIP" 阈值在 schema 子片实测约 50-80% (Quality 维度), Spec 维度合并后才能审 — 建议后续模块 sprint 也用合并审, 不强求 schema 单跑

---

# M01 PT1-PT3 复用情况 (M02 sprint 内回写)

| PT | M02 是否复用 M01 范式 | 备注 |
|---|---|---|
| PT1 「本期实现最简 + schema 都支持」 | ❌ 部分 | M02 dimension_types 表是全部实装 (无预留模式); SearchConfig 是"现在建未来用" 部分对应模式; M02 design §3 列 4 表全部实装 |
| PT2 ADR-004 凭据路径表 | ✅ 复用 | M02 router 用 require_user (M01 P1 路径); 没新建凭据类型 |
| PT3 预留 schema + CI 禁引用 | ❌ 不适用 | M02 4 表全部本期实装, 无"建表禁 import"模式 |

**校准回写** (M01 m01-pilot-template-validation.md PT1 表):
- M02 row: ❌ 不复用 (4 表全实装) — 与 M01 7 表 (3 实装 + 4 预留) 模式不同, 因 M02 是 tenant 锚点, 所有字段 M02 sprint 必须可用

---

# 维护

- M02 sprint 关闸时本文件 status 改 accepted
- R-X5 子选项清单按本次 4 个实证回写到 `design/02-modules/README.md` 对应段
- 后续 M03/M04 sprint 启动 reconcile pass 时引用本文件作为先例
