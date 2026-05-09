---
title: M20 sprint 启动提示词（新 session 直接复制粘贴）
status: ready
owner: CY
created: 2026-05-09 (M19 sprint 关闸时预录)
sprint: M20 团队 / pilot=false / complexity=medium / Phase 2.1 95→100% 收官
purpose: 新 session 冷启动 M20 sprint 时，CY 直接复制下方 prompt 块全文执行。
---

# M20 sprint 启动提示词

> **使用方法**：CY 开新 Claude session → 直接复制下方代码块全文粘贴执行。

```
继续 prism-0420 M20 sprint（团队 / complexity=medium / pilot=false / Phase 2.1 95%→100%
完结 / 最后一个 own sprint）。

状态快照（已 commit + push 到 origin/main）：
- M19 sprint ✅ 完成 / 8 commits / 1512 PASS / R13-1 136→139 / L12+L13+R14 全过 / ruff 净
- Phase 2.1 业务模块 ⏳ 95%（M01-M08+M10-M19 完成 / M09 superseded by M18 不实装 /
  下一站 M20 团队最后一个 own sprint）
- bypass log #2 配套验收最终 ✅（M16 bypass + M17 恢复 + M18 继续 + M19 继续 = 累计
  2 次 bypass / 第 3 次触发闸门 3.4 L1 总则 review）

冷启动按序读：
1. /root/workspace/projects/prism-0420/CLAUDE.md
2. _handoff/next-session.md §0 状态快照（M19 完成 + 元教训 #19 + sink 候选 3 + 新 punt
   #25-#28 + 真漏洞 #20 M19 evaluated 不触发）
3. _handoff/cross-sprint-punt-pool.md（M19 新增 #25-#28 + 触发点 D 元教训 #19）
4. design/00-roadmap.md（Phase 2.1 95% / M20 待启 / Phase 2.1 收官）
5. design/00-phase-gate.md（闸门 2.5 reconcile pass + 闸门 3.4 L1 总则 3 类例外）
6. design/02-modules/M20-team/00-design.md（status=accepted 2026-04-26 / pilot=false /
   complexity=medium / R0-1+R3-2+R3-4+R4-2/3+R5-1/2+R7-2/3+R8-1/2/3+R10-1/2+R11-1/2 ADR-005）
7. design/audit/m19-pilot-template-validation.md（M19 元贡献 4 + R1+R2 第十七数据点 +
   元教训 #19 R1 局部立修触发 tests.md 第三方文件漂移）
8. design/audit/m19-startup-reconcile.md（启动期三栏范式参考）
9. memory：feedback_subagent_sprint / feedback_problem_layered_analysis /
   feedback_self_decide_no_ask / feedback_design_first / feedback_usage_budget v3 /
   feedback_decision_transparency / feedback_completion_audit

启动期：
- 闸门 2.5 reconcile pass（A/B/C 三栏 / B 栏穷举 L1 锁规 / B 栏=0 时禁列）
- M19 配套承诺验收：M20 必继续 R1=3 + R2=1 不复位
- design status 已 accepted 2026-04-26 不需 audit
- baseline-patch 检查（M20 design references 含 ADR-005 跨模块改动：
  projects.space_id → team_id RENAME + ActionType+10 + TargetType+1 + Alembic 单 revision
  合并 + M02 baseline-patch + M15 baseline-patch / 已部分预录 _ACTION_TYPES 包含 10 个
  team_* / TargetType "team" / 子片 1 验证）
- §14.5 sprint review 拆分计划补完（参 M17/M18/M19 范本）
- **M19 元教训 #19 应用 SR-M19-1**：A 栏首条预录 grep 命令
  `grep -n "404\|422\|500" design/02-modules/M20-team/tests.md` 与
  `api/errors/exceptions.py:http_status` + `design.md:§13` 字面比对（防 R1 局部立修触发
  tests.md 第三方文件漂移 / M19 R2 独家命中 / M20 第二实证）
- **M18 真漏洞 #20 重新评估**：M20 团队管理可能含 admin endpoint（如 platform_admin 强制
  解散 team）→ require_platform_admin Protocol 版 vs current_user 版去重必修
- **R14 过去式立规**：M20 ActionType 10 个 team_*（design 字面已含 team_created /
  team_renamed / team_description_changed / team_deleted / team_member_added /
  team_member_removed / team_member_promoted_admin / team_member_demoted_member /
  project_joined_team / project_left_team — 全过去式 / R14 验证）

子片拆分预期（M20 complexity=medium / 估 5+ 子片）：
- 子片 0 prep：§14.5 + scaffold 简化决策 4 字段注释 + space_id → team_id
  baseline-patch RENAME 验证
- 子片 1: model+alembic（teams + team_members + projects.team_id RENAME + ActionType+10
  + TargetType+1 全已 baseline-patch / 子片 1 验证 + 落库）+ tests
- 子片 2: DAO（TeamDAO + TeamMemberDAO + ADR-005 L3 SQL 注入 user_accessible_team_ids
  subquery）+ tests
- 子片 3: TeamService + 8 ErrorCode + R-X3 跨模块只读（M02 projects + project_members）
  + 状态机 4 条禁止转换（owner 移除 / 跨级直升 / 非 transfer 降 owner / 直降 member）+
  tests
- 子片 4: Router + e2e（元教训 19 类 actionable + N/A 显式声明 + R10-1 批量独立事件 N+1
  e2e 字面验 + R-X3 N+1 防护）+ R1+R2
- 子片 5: 关闸（design 回写 + audit/m20-pilot-template-validation.md + handoff §0 +
  roadmap **Phase 2.1 100% 收官** + cross-sprint punt 池 + 评估 #20+#25+#26 是否触发 +
  Phase 2.2 前端继承 Prism 启动评估）

R1+R2 范式（不降级）：
- R1 = 3 subagent 并行（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）
  覆盖子片 1+2+3
- R2 = 1 合并 Opus subagent endpoint 单审子片 4
- spawn prompt 必含 ls/find 穷举要求；spawn 后 >5min 无通知必主动 ping
- M19 元教训 #19 应用：R1 立修 status code/error code 时，tests.md 必须列入立修文件清单
  （与 design / exceptions / schema 同级 / 防 R1 三 subagent 把 tests.md 当"参照真相"
  漏抓）

红线（M02-M19 实证 + R14 + R-X1 + R-X3 + 元教训 #19）：
- viewer 写所有写端点 403 全覆盖（M07 立 / M19 N/A 复习：M20 写端点 viewer 必 403）
- write_event 异常传播 e2e 字面验（M16 立 / M20 10 个 team_* 事件路径必测）
- cross-tenant 404 + cross-team move 422（design §13 CROSS_TEAM_MOVE_FORBIDDEN）
- IntegrityError 区分约束名（清单 6 + ci-lint R15 / M20 team_name UNIQUE +
  team_member (team_id, user_id) UNIQUE 必 catch）
- M19 NEW 元教训 #19：tests.md ↔ design ↔ exceptions 三方 status code 字面同步
  checkbox（启动期 A 栏首条预录 + R2 reconcile 必跑）
- M19 NEW 范式：filename sanitize 输入端 vs 输出端分门别类（M20 无文件操作 N/A 显式）
- M18 NEW EndpointRequest schema 不继承 TaskPayload（M20 无 Queue / N/A 显式）
- M18 NEW 占位 metadata _stub:True 标记（M20 全真实数据 / N/A 显式）
- M18 NEW 测试反模式禁用：assert True / assert in 永真元组（M20 N/A 元教训显式声明 /
  test_meta_lesson_na_explicit_declarations docstring 范式延续）

启动注意：
1. usage_budget v3 单会话 $10 上限 / >$15 强制开新会话；M20 complexity=medium 估
   单会话能完成（参 M14 行业新闻 medium 模块 7 commit + 930 PASS 单会话完成范式）
2. 每子片间 commit；R1/R2 跑完看 finding 决定是否 spawn 修
3. 1512 PASS 是 baseline / 任何子片完不能下降
4. **M20 完成 = Phase 2.1 100% 收官** / 下一阶段 Phase 2.2 前端继承 Prism / 子片 5
   关闸时同步评估闸门 4 启动条件（M01-M05+M20 后端代码 merge / OpenAPI 契约稳定 /
   `npm run codegen` 准备）

任务起点：进入启动期 reconcile pass + baseline-patch 检查（M02 + M15）+ §14.5 补齐 +
M19 元教训 #19 应用（tests.md 三方对账） → 子片 0 prep → 子片 1 → ...
```
