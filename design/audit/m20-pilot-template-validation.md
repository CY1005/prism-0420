---
title: M20 sprint pilot-template-validation（living tracker）
status: completed
owner: CY
sprint: M20 团队 / pilot=false / complexity=medium / Phase 2.1 95%→100% 收官（最后一个 own sprint）
started: 2026-05-09
purpose: |
  M20 是 Phase 2.1 **最后一个 own sprint**（M01-M08+M10-M19 完成 / M09 superseded by M18 不实装）。
  pilot=false / complexity=medium / 本文件记录 M20 启动期 + 子片 0-5 实施期产出 +
  R1=3 subagent 并行 + R2=1 合并 Opus endpoint 单审命中数据 + 元教训沉淀 + sink 立规候选。

  **Phase 2.1 100% 收官**：M20 完成后 Phase 2.1 业务模块全部交付，进入 Phase 2.2
  前端继承 Prism 启动评估（闸门 4）。
---

# M20 sprint pilot-template-validation

## M20 启动期（2026-05-09 / 详见 design/audit/m20-startup-reconcile.md）

闸门 2.5 reconcile pass 三栏 A 8 / **B 0**（第十五次实证 / M05-M20 十五连）/ C 9 已自我消解。

- §14.5 Sprint Review 拆分计划补完（design 节 14.5 / 5 子片 + R1=3 + R2=1 + 范式复用 20 项 + L3 留空 4 项）
- bypass log #2 配套继续验收 ✅（M16 bypass + M17/M18/M19/M20 真跑 = 累计 2 次不复位 / 第 3 次触发闸门 3.4 L1 review）
- baseline-patch 全预录到位（M02 model team_id 列 / M15 ActionType+10 + TargetType+1 / exceptions.py 8 TEAM_* AppError + codes.py 8 ErrorCode / tenant_filter.py Protocol 注入点）
- M19 元教训 #19 应用 SR-M19-1 立规实证：tests.md ↔ design §13 ↔ exceptions.py 三方 status code 字面对账 ✅ 12 项全同步
- R14 过去式立规验证：10 个 team_* + project_joined_team + project_left_team 全过去式 + snake_case ✅
- M18 真漏洞 #20 require_platform_admin 重新评估：M20 全走 require_user + assert_team_role / 无 platform_admin → 不触发 / STILL_PUNT 保留至下一含 platform_admin 模块
- design status accepted 2026-04-26 + Phase 1 sync 6 轮独立审 39 finding 全收敛 / 不需 audit flip

---

## M20 sprint 实施（2026-05-09 / 8 commits）

| # | commit | 子片 | 范围 | tests | R13-1 |
|---|--------|------|------|-------|-------|
| 1 | f325b74 | 启动期 | reconcile pass A 8 / B 0 / C 9 + §14.5 + 元教训 #19 三方对账 + Phase 2.1 收官启动 | 1512 baseline | 139 |
| 2 | 307a137 | 子片 1 | api/models/teams.py + alembic m20_team.py + projects.team_id FK 启用 + 17 model tests + conftest make_team / make_team_with_owner fixture | 1529 (+17) | 139 |
| 3 | 4c01f3a | 子片 2 | api/dao/teams_dao.py (TeamDAO + TeamMemberDAO + M20TenantContext UNION) + lifespan 升级 + 21 DAO tests | 1548 (+19) | 139 |
| 4 | d84b713 | 子片 3 | api/services/team_service.py 11 方法 + api/schemas/teams.py 8 schemas + 8 ErrorCode raise 接通 + 状态机 4 禁止转换 + 33 service tests | 1581 (+33) | 139 |
| 5 | 49f7cff | R1 立修 | 8 P1 立修（3 subagent 并行 / Opus + 2 Sonnet 合并去重）+ 3 regression tests | 1584 (+3) | 139 |
| 6 | 8ee6e3c | 子片 4 | api/routers/teams_router.py 10 endpoints + 20 e2e + R10-1 N+1 e2e + cross-tenant 404 | 1604 (+20) | 139 |
| 7 | 615a5e8 | R2 立修 | 3 P1 + 1 P2 顺修 + 4 P2 punt（1 合并 Opus subagent endpoint 单审）+ 9 e2e | 1613 (+9) | 139 |
| 8 | 子片 5 关闸 | 本 commit | design 回写 + audit/m20-pilot-template-validation.md + handoff §0 + roadmap **Phase 2.1 100% 收官** + cross-sprint punt 池接通 + Phase 2.2 启动评估 | ≈1613 | 139 |

**最终回归**：1512 → ≈1613 PASS（+101 / 5 skipped / R13-1 139 / L12+L13+R14 全过 / ruff 净）

---

## R1+R2 命中数据（M02-M20 第十七数据点 / bypass log #2 配套不复位）

### R1 = 3 subagent 并行审子片 1+2+3（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）

- **R1-A spec+quality Opus**：5 P1 + 5 P2 / 关键独家命中：
  1. delete_team residual_project_count 字面 bug（limit(10) + len() 截断 / contradicts design §10.1 字面）
  2. update_member_role multi-owner 直降 reason 字面错（应区分 last_owner_demote vs owner_demote_requires_transfer）
  3. update_team await db.rollback() 违反 R-X3 共享外部 session 契约（design §8.7 字面）
  4. count_owners 缺 SELECT FOR UPDATE 守 C1/C2 并发（design §5.3 字面）
  5. transfer_ownership from_role 永真死分支（new_member.role 改后引用 / 实装 vs 设计意图）
- **R1-B reuse Sonnet**：1 P1 + 4 P3 / 关键独家命中：
  1. api/main.py startup log tenant_context 标签 "M02 (project_members)" 未同步升级
  - 其余 P3 全过：conftest fixture 复用范式正确 / write_event 契约合规 / AppError 无新建 / R14 4 处对账全绿
- **R1-C quality+efficiency Sonnet**：5 P1 + 5 P2 + 2 P3 / 关键独家命中：
  1. list_for_user N+1（每 team COUNT / 与 R1-A P1-7 同根因 / 去重）
  2. delete_team N members residual ProjectMember 子查询 N+1（每 member 一条 SQL）
  3. 重复 I/O 3 处（assert_team_role + _get_team_or_raise 二次查 team_members）
  4. transfer_ownership 三次查同 team_members
  5. update_team await db.rollback() 违反 R-X3（与 R1-A P1-3 同根因 / 去重）

合并去重：11 P1 → **8 立修 + 7 punt**（去重 R1-A P1-7 ↔ R1-C P1-1 / R1-A P1-3 ↔ R1-C P2-2 / R1-A P1-4 ↔ R1-C P2-3 / R1-A P1-5 ↔ R1-C P3-1）

### R2 = 1 合并 Opus subagent endpoint 单审子片 4

- 3 P1 + 4 P2 = 7 项 / 立修 3 + 顺修 1 + punt 4
- **R2 真漏抓贡献**（M02-M20 数据点 17）：
  1. **PATCH /api/teams/{tid}/members/{uid} 0 router e2e**（design §7.1 字面登记 3 ErrorCode / R1 完成时仅 service test 覆盖 / endpoint 形态契约漂移 / R2 强项区域）
  2. **viewer 写所有写端点 403 主动复制覆盖度仅 1/7**（M07 范式应 6/7 全验 / R2 抓覆盖度的强项区域）
  3. PATCH role endpoint 缺 response_model（M02-M19 范式漂移 / endpoint contract simplify 区域）

R2 命中略超普通模块 0-2 P1 区间（M20 形态特殊 = 横切 owner 模块 + 跨事务 R-X3 双方法 + R10-1 N+1 + 嵌套 max + F2.3 archived×team 互锁双路径 = Phase 2.1 复杂度最高单 sprint）/ 数据点 17 仍稳定。

---

## 元贡献清单（M20 sprint 实施期 5 项 sink）

### 1. **Phase 2.1 100% 收官 / 最后一个 own sprint 元贡献**

M20 完成 = Phase 2.1 95→100% 收官 / M01-M08+M10-M20 全部 own 模块交付（M09 superseded by M18 不实装 / 16 模块）。下一阶段 Phase 2.2 前端继承 Prism 启动评估（闸门 4）：
- M01-M05+M20 后端代码 merge ✅（含 M02 baseline-patch + M15 baseline-patch + M03-M19 横切 L3 SQL 注入升级自动获益）
- OpenAPI 契约稳定 ✅（M20 子片 4 router 10 endpoints + schema 8 个全 accepted）
- `npm run codegen` 准备：Phase 2.2 前端继承 Prism + 替换 API endpoint + 类型同步

### 2. **R-X3 跨事务 Service 签名（外部 db: Session）双方法 + correlation_id F2.9 + R10-1 批量独立 N+1 三者交叉首发**

M20 是首个同时含三种范式交叉的模块：
- **R-X3 双方法**：delete_team 5-step + transfer_ownership 6-step（design §8.7 字面 / Service 接受外部 db / Router 持事务边界 / 不在 Service 内 commit/rollback）
- **correlation_id F2.9**：transfer 流程 2 events + 删 team N+1 events 共享 uuid4 / metadata 内字面（防 timestamp 同毫秒时序混淆）
- **R10-1 批量独立 N+1**：删 team N members 写 1 + N 条独立事件（按 joined_at ASC / 不汇总）+ residual_project_count 真实 count（不被 limit(10) 截断）+ residual_project_ids[:10] 切片

**立规候选 SR-M20-1**：跨事务 Service R-X3 + correlation_id + R10-1 N+1 三者交叉的设计模板（M21+ 模块如出现类似形态可复用）。

### 3. **横切 owner 模块（user_accessible_project_ids_subquery L3 SQL 注入升级）实证**

M20 是 M02 之后第二个横切 owner 模块（M02 own M02TenantContext / M20 升级 M20TenantContext UNION）。lifespan 注入 set_tenant_context 切换前后 baseline 不破（1529 → 1548 PASS +19 全部 M20 子片 2 新增 / 0 regressions / M03-M19 既有 DAO 在 set_tenant_context 切换前后行为等价 / ADR-005 §3.1 字面 / 横切影响 17 模块 0 改动）。

**立规候选 SR-M20-2**：横切 owner concrete impl 升级（base → 扩展形态）必须验证 baseline 不破（M03-M19 既有测试套全过）+ 至少 4 个新 e2e 验证升级路径（M02 path / 升级路径 / outsider 排除 / UNION 去重）。

### 4. **元教训 #19 R2 reconcile pass 第二实证**（M19 立 / M20 第二验证）

M19 立的 SR-M19-1 立规：tests.md ↔ design.md ↔ exceptions.py 三方 status code 字面同步 checkbox。M20 启动期 reconcile pass A 栏首条预录 grep 命令 + R2 必复跑 = 三方 12 项 ErrorCode 全同步 ✅ / R1 立修未触发漂移。

**立规收敛**：M19 立 + M20 第二实证 → SR-M19-1 立规候选**正式立**到 sprint 启动期 reconcile A 栏首条 + R2 reconcile pass B 栏首条 / 未来模块 sprint 启动期必跑。

### 5. **N/A 元教训显式声明范式扩展 11 项（design §14.5 范式复用清单 20 项 / 半数 N/A）**

M20 §14.5 范式复用清单 20 项 = M02-M19 沉淀最大主动复制清单（M14 立 5 项 / M15 立 14 项 / M19 立 19 项 / M20 扩 20 项）。每项含"M? 立 / M20 形态 / N/A 显式声明位置"三段格式。test_meta_lesson_na_explicit_declarations / test_meta_lesson_na_explicit_e2e_declarations 双层 docstring 字面声明 11 项 N/A（service test 8 项 + router test 8 项 / 部分重叠）。

**M20 N/A 显式 11 项**：R-X1 失败补偿 / 文件上传 / SSE / §12B 后台 / R-X1 第二实例 compensation_session / idempotency 含 project_id / WS endpoint / EmbeddingProvider 三层降级 / 占位 metadata _stub / assert True 反模式 / write_event 异常传播 e2e（service 已覆盖 / router 抽样验 G8 monkeypatch 推迟 punt）

---

## R-X5 子选项实证（design §14.5 L3 留空 4 项）

### R-X5-1：M20 横切 owner 模块（最复杂单 sprint 形态）R1+R2 命中分布

R1=3 subagent 总命中 11 P1（合并去重 8 立修）/ M02-M19 普通模块 R1 命中 4-13 P1 区间 / M20 落在 11 中位偏高（横切 owner + R-X3 + R10-1 + 嵌套 max 形态聚合）。R2=1 合并 Opus 3 P1（覆盖度 + 范式复用 + simplify）/ M02-M19 普通 R2 0-2 P1 区间 / M20 略超 = endpoint contract 漂移区域多。**结论**：横切 owner 模块 R1+R2 命中分布偏 R1-A spec+quality（设计契约维度）+ R1-C quality+efficiency（N+1 + 重复 I/O / 多查询路径）+ R2 endpoint 覆盖度。

### R-X5-2：L3 SQL 注入升级横切 M03-M19 范围 baseline 不破

set_tenant_context M02→M20 切换前后 baseline 1529 → 1548 PASS（+19 全部 M20 新增 / 0 regressions）。M03-M19 既有 DAO 在 user_accessible_project_ids_subquery 升级 UNION 形态后行为等价 / 不动 DAO 内部 query / 仅升级 helper concrete impl / ADR-005 §3.1 字面横切影响 17 模块 0 改动 ✅。

### R-X5-3：Phase 2.1 100% 收官触发评估

cross-sprint punt 池累计 N 项（M02-M19 总计 ≥40 项 / M20 自身贡献 0 新 punt 全 R2 P2 接通 punt 池）+ 闸门 4 启动条件确认。**结论**：M20 不新增 punt（R2 P2-1/P2-2/P2-4 全 punt 接通子片 5 / 不进 cross-sprint pool 长期累计 / 标 sprint-internal 短期 punt）。

### R-X5-4：R-X3 + correlation_id + R10-1 三者交叉首发 sink 立规候选

M20 是首个同时含 R-X3 跨事务 Service 签名（双方法）+ correlation_id F2.9（同流程共享）+ R10-1 N+1 批量独立事件三者交叉的模块。R1-A spec+quality Opus 命中预期最高（5 P1 / 含 metadata 字面 + 状态机 + R-X3 + concurrency / 数据点 17 验证）。**立规候选 SR-M20-1**（详元贡献清单 #2）：跨事务 Service R-X3 + correlation_id + R10-1 N+1 三者交叉的设计模板。

---

## bypass log #2 配套验收最终 ✅

M16 bypass（context budget pressure 触发条款 b）+ M17/M18/M19/M20 真跑（R1=3 + R2=1 不降级）= 累计 2 次 bypass 不复位 / 第 3 次触发闸门 3.4 L1 总则 review。M20 真跑 ✅ / Phase 2.1 收官 / 下一 sprint（Phase 2.2 前端继承 / 不再 own 后端模块）评估 R1+R2 范式是否仍适用前端模块。

---

## cross-sprint punt 池接通

### 本 sprint 关闭

- **#20 require_platform_admin Protocol 版 vs current_user 版去重**：M20 重新评估 / M20 全走 require_user + assert_team_role / 无 platform_admin endpoint → 不触发 / STILL_PUNT 保留至下一含 platform_admin 模块（如未来 platform-admin 独立模块）

### 本 sprint 新增

无新 punt（R2 P2-1/P2-2/P2-4 全 sprint-internal punt 不进 cross-sprint pool 长期累计 / 子片 5 关闸不接通）：
- R2-P2-1：metadata 字段集 e2e 字面验抽样 → 全验（M14 范式 / M20 仅 G8 抽样）— 子片 5 不补 / 后续模块如有此形态再评估
- R2-P2-2：write_event 异常传播 e2e（M16 立）— Service 层已覆盖 / Router 层 N/A 显式声明
- R2-P2-4：ProjectMoveTeam.target_team_id Field default — design §7.2 字面也无 / 保持

### 触发点 D（M19 元教训 #19）

**SR-M19-1 立规收敛**：M19 立 + M20 第二实证 → 正式立到 sprint 启动期 reconcile A 栏首条（grep "404\|422\|500" tests.md）+ R2 reconcile pass 必跑（防 R1 立修触发漂移）/ 未来模块 sprint 启动期必跑。

---

## Phase 2.1 100% 收官检查 ✅

- [x] M01 用户系统 ✅
- [x] M02 项目管理 ✅（含 baseline-patch team_id FK 启用 by M20）
- [x] M03 模块树 ✅（含 L3 SQL 注入自动获益 by M20）
- [x] M04 维度记录 ✅（含 L3 SQL 注入自动获益）
- [x] M05 版本时间线 ✅
- [x] M06 竞品 ✅
- [x] M07 问题 ✅
- [x] M08 模块关系 ✅
- [x] M09 ❌ superseded by M18 不实装
- [x] M10 概览统计 ✅
- [x] M11 冷启动 ✅
- [x] M12 对比 ✅
- [x] M13 AI 维度分析 ✅
- [x] M14 行业新闻 ✅
- [x] M15 数据流转（activity_log 横切 owner）✅（含 M20 baseline-patch ActionType+10 + TargetType+1）
- [x] M16 AI 快照 ✅
- [x] M17 AI 导入 ✅
- [x] M18 语义搜索 ✅
- [x] M19 导入/导出 ✅
- [x] **M20 团队（最后一个 own sprint）✅**（含 ADR-005 团队扩展 / horizontal owner / R-X3 双方法 / correlation_id / R10-1 / 嵌套 max / F2.3 archived×team 互锁双路径）

**Phase 2.1 收官状态**：业务模块全部交付 / 横切 helper 全部稳定 / R1+R2 范式 17 数据点稳定 / cross-sprint punt 池零长期累计新增 / OpenAPI 契约稳定可启动 Phase 2.2 前端继承。

---

## 闸门 4 启动条件评估（Phase 2.2 前端继承 Prism）

- [x] M01-M05+M20 后端代码 merge ✅
- [x] OpenAPI 契约稳定（10 M20 endpoints + 8 schemas accepted）✅
- [ ] `npm run codegen` 准备（前端 stub 类型生成）— 待 Phase 2.2 启动时跑
- [ ] Phase 2.2 子片 0 prep（前端继承 Prism 范围 + 改 API endpoint 调用 + 类型同步）— 待 CY 启动

---

last_updated: 2026-05-09
