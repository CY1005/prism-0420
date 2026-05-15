---
title: prism-0420 跨 sprint Punt 池总表
status: living-doc
owner: CY
created: 2026-05-08（M15 sprint 收官后建立）
last_updated: 2026-05-15 (**Phase 2.x M-frontend cluster-M17 + cluster-M14 闭环** — 元发现 #11 新立：Phase 2.2 拷贝层 vs design §6 范式漂移群 / feed.ts 长期 stub 归宿待决)
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
> 文件 + _handoff/_archive/next-session.md M01/M02 后置债 = 共 94 条 punt 全量代码验证。
> Opus subagent 跑完整 grep 验证。

---

## 状态分布快照（2026-05-08 baseline / 含 M02/M03/M04 补审）

> 2026-05-08 二次审计：CY 抓出 subagent 一审漏 M02/M03/M04 audit 文件 punt 池（仅查 m05~m15）。
> 二审 spawn 补充 41 项 punt 验证；去 M02 audit 与 _handoff §0a 的 6 项 DUPE 后净增约 35 项。

| 状态 | 项数 | 占比 | 说明 |
|---|---|---|---|
| **STILL_PUNT** | **31** | 24% | 代码完全没动，问题还在（Sprint 1 关闭 P22-3c-1~8 共 8 项 / 39→31）|
| **DONE** | **40** | 31% | 代码已落实（Sprint 1 +8：P22-3c-1~8 全清 / Phase 2.2 子片 5 +2 / M-CLEANUP +8 / pre +22）|
| **PARTIAL** | 2 | 2% | 部分子项做了 |
| **UNVERIFIABLE** | **53** | 41% | 设计意图 / 性能压测 / 未来 sprint 才触发 / docstring 注释类（M-CLEANUP 子片 5 清扫 6 项）|
| **OBSOLETE** | 3 | 2% | punt 已不适用 |
| **总计** | **129** | 100% | （一审 94 + 二审 41 - 6 DUPE）|

### 2026-05-12 Sprint 3.1 + 3.2 CI 接通完整收尾（5 commits / e2141d2→d9fa3f4）

**触发**：CY 5/12 拍 PAT workflow scope 解锁 → Claude push ci.yml 启动 Sprint 3.1

**5 commits 时间线**：
- `e2141d2` push ci.yml（253 行 / design/01-engineering/03-cicd-plan.md §8 实施）→ 首次 CI run 4 红
- `81d7067` fix#1: pytest-cov 加 dev group + pnpm-workspace.yaml 加 packages 字段（方案 A）→ 5/6 jobs 转绿
- `abff5c6` fix#2: CY 选 B 切方案——删 pnpm-workspace.yaml + 移 ignoredBuiltDependencies 到 app/package.json 的 pnpm 字段（语义干净 / app/ 是单包不是 monorepo）
- `f07fa3c` Sprint 3.2: 3 处 @/actions/auth migration 到 useAuth（use-page-context.ts + settings/page.tsx + overview/page.tsx）+ phase-gate.md 关闸盲区立规
- `d9fa3f4` fix#3: test_config CI-friendly（monkeypatch.delenv APP_ENV/DATABASE_URL/REDIS_URL 验代码 default）

**累计成果**：
- ci.yml 进 main + GitHub Actions 跑通
- 6 触发 jobs 里 **4 个稳定绿**（backend-typecheck / backend-lint / frontend-test / frontend-lint）
- 2 个红收窄到 Phase 2.3 真实工作量（入新真漏 #25 + #26）
- 闸门 5 §8.0 部分 ✅（CI 配置 + 5 个 job 接通 / build 项 ⏳ 待 Phase 2.3 完成 88 tsc 错清理）

**学习沉淀**（候选入 docs/testing/bugs/INDEX.md）：
- 暴露 4 个"spec → impl 文本抄但本地 dry-run 缺失"系列 bug（pytest-cov 不在 deps / pnpm-workspace 缺 packages / 3 处 auth 死引用 / test_config env 假设）
- 统一根因 = 契约漂移 28% 模式的子分类"配置文本契约 vs 运行时 deps/env 漂移"
- phase-gate.md 立规：未来前端关闸必跑 `next build`（不只 tsc）+ 删 export 前必 grep 调用方

**未做（入 punt pool 真漏 #25+#26 等 Phase 2.3 集成验证 sprint）**：
- #25 tsc 88 错（permission.service.ts drizzle 死依赖 / project-role-context 类型漂移 / 等 86 处）
- #26 M01 admin list users 撞 .local TLD（seed 系统用户 email vs EmailStr 严格验证）

---

### 2026-05-10 Sprint 2 NEAR-DONE — Task 2.3 全 9 spec API smoke + Task 2.4 完整版（19 e2e + 1643 pytest PASS）

**CY 出门期间无人值守串跑完成**：
- Task 2.3 spec 07-10（之前 punt）→ 全改 API smoke：
  - 07 M16 AI snapshot（trigger 422 业务码 / ai_provider 未配 + version<3 路径）
  - 08 M19 export（multi-node + single-node markdown + include all-false 422）
  - 09 M18 search（query 200 keyword_only + >200char 400 + empty 422）
  - 10 M08 module_relation（create + self_loop 422 + overview 可达 + delete）
- Task 2.4 完整版（升级路径 1+3）：1000 project + bulk_insert + module-aware function scope

**真 mock 全栈 happy path 推下次专 sprint**（mock provider / pgvector / WS 各自独立基础设施）：
- M16 happy path：mock AI provider + 3+ versions seed + 后台 runner + poll → succeeded
- M17 happy path：mock AI provider + 3 步流程（propose / review / confirm） + WS 进度
- M17 import zip：multipart/form-data + WS 客户端 + worker 真跑
- M18 hybrid search：pgvector 真接通 + embedding worker + cosine 排序
- M16/M17/M18 WS golden e2e（cross-sprint pool §16）

**阻塞 Sprint 3**：CY 加 PAT workflow scope（GH Settings → Developer settings → PAT → Edit → 勾 workflow）—— 2026-05-10 CY 反馈"暂时加不了 / 让做别的"。无人值守期间无法替操作。

### 2026-05-10 Sprint 2 Task 2.3 part-1 + 4C.3 expunge fix（10 e2e PASS / 1638 pytest PASS）

**完成**：
- Task 2.1+2.2 基础设施（seed_e2e_admin.py + seed.ts + global-setup.ts + playwright config）
- Task 2.3 spec 03+04+05+06 完整断言（API 路径 / 含 D 类 #3 join 实证 + L1-α detach 双 case）
- 4C.3 issue_service.update 加 expunge fix（Sprint 2 e2e 暴露 raw SQL + selectinload identity map cache 副作用）

**SR-EXPUNGE-1 ✅ 已正式立规**（design `00-architecture/06-design-principles.md` 附录 L1-α "配套规约 SR-EXPUNGE-1" 段 / 2026-05-10 commit 后续）：
- 触发：service.update 同时满足 (1) raw SQL UPDATE (2) Response 含 selectinload join 字段 (3) 业务支持 detach
- 范式：`db.refresh + db.expunge(existing) + dao.get_by_id` → 真重 SELECT 触发 _JOINS
- 替代（优先）：service 用 ORM mutate（M02/M03/M14 范式 / setattr + db.flush + 末尾 self._get_or_raise）
- 当前实证：M07 issue（已修 commit 22b3484）；M05/M06 同 raw 但 Response 无 selectinload 字段所以无暴露 / 长期建议迁 ORM mutate
- ci-lint R18 候选（已写到 design 06 字面）

**Sprint 2 剩余（punt 下次会话）**：
- spec 07-10（AI snapshot / import-export / search / relation graph）—— 各自依赖 mock provider / WS / multipart / XYFlow 交互
- Task 2.4 pytest-benchmark + 1000 seed
- Task 2.5 R1+R2 第 7 数据点（等 spec 07-10 + Task 2.4 完成 R 才齐）

### 2026-05-10 Sprint 4C.3 SR-DETACH-1 跨模块立规（5 模块同步立修 / 1629→1638 PASS）

**关闭项 2 + 立规 1**：
- #6 ✅ M07 update detach（node_id 游离 + assigned_to 取消责任人 2 字段）
- M02-A1 ✅ update_project exclude_none → exclude_unset only（移除显式禁 detach）

**SR-DETACH-1 立规**（design `00-architecture/06-design-principles.md` 附录 L1-α）：
- 范式：router `model_dump(exclude_unset=True)` + service `fields: dict[str, Any]` 接收
- 跨模块同步立修：M02 / M03 / M05 / M06 (×2) / M07 共 5 模块
- M14 industry_news 已对范式（2026-05-08 R1-A 立修）—— 反向回扫确认 L1-α 一致
- ci-lint R16+R17 grep 候选（待立规）：router 双排除 / service `if X is not None` 老模式 → 告警

**层级分析过程**（CY 教方法）：
- 矛盾根源：A 选项 vs B 选项原则未分上下层
- A 背后：L1-α 用户合理业务动作必须有 API 入口（领域驱动）
- B 背后：L1-β 业务态变化走 transition / 数据态变化走 update（状态机单一入口）
- 推导：L1-β 在本职范围（状态合法转换）有效；超出范围（正交字段变化）应让位 L1-α
- 跨模块循环验证：M02 / M03 / M05 / M06 / M07 全同根因 → 全应用 L1-α 都得当 → 原则成立
- CY 选 A2 一并修（vs A1 仅 M07 / A3 立规先行）

### 2026-05-09 Phase 2.2 子片 5 关闸（D 类 #3+#15 装配 / 1623→1629 PASS）

**关闭项 2**：
- #3 ✅ IssueResponse join 字段（node_name/created_by_name/assigned_to_name）— 子片 5 / Issue model relationship + IssueDAO `_JOINS` selectinload + service 三处 refetch + router `_resp` 装配 + 3 e2e
- #15 ✅ DimensionResponse join 字段（dimension_type_key/updated_by_name）— 子片 5 / DimensionRecord model relationship + DimensionDAO `_JOINS` selectinload + service 两处 refetch + router `_record_response` 装配 + 3 e2e

### 2026-05-09 M-CLEANUP sprint 关闸（4 commits / 1613→1619 PASS / 8 punt 关闭）

**commits**：33b5759 子片 1（mechanical 4 项）+ aabde04 子片 2（M04 IntegrityError）+ 5c7783d 子片 3（M14 write_event e2e + M05-M08 race 复审）+ 本 commit 子片 5 关闸

**关闭项 8**：
- #8 ✅ M14-B12 update/delete/unlink write_event 异常传播 e2e（子片 3 / 3 e2e 立修）
- #9 ✅ M05/M06/M07/M08 race window 复审（子片 3 / DONE_BY_INSPECTION / M15-B1 升级后行为等价）
- #10 ✅ M10-5 viewer /overview/stats 测试缺（子片 1 / 2 e2e 立修）
- #11 ✅ M04 IntegrityError → 500（子片 2 / create + create_dimension_record 双入口立修）
- #12 ✅ M04-9 target_type 5 处 hard-code（子片 1 / TARGET_DIMENSION_RECORD 常量化）
- #13 ✅ M04-1 (updated_by, updated_at) 联合索引（子片 1 / alembic m_cleanup_01_dim_compound_index）
- #14 ✅ M04-8 db.get(DimensionType) 3 处走 DAO（子片 1 / DimensionDAO.get_type_by_id）
- #3 + #15 ⏸️ IssueResponse + DimensionResponse join 字段 → 推迟到 D 类条件触发型（前端 Phase 2.2 真用时一并补 / 不补 join 不影响后端独立测试）

**剩余 41 项 STILL_PUNT 重新归类**：
- **A 类 占位期残留 5 项**（#21-#24 + 部分 M11-B1 已关）：M18 embedding worker source_text + noop 转 succeeded + cron PCT 维度 + batch_backfill INSERT FROM unnest — 待 pgvector 真接通 + 真业务 path 启用时解锁
- **B 类 真漏洞 0 项**（M-CLEANUP 已清完）
- **C 类 性能黑洞 ~12 项**（元发现 #2 / M02 batch_update UPSERT / M04 batch_get_by_nodes / M05 query 优化 / M11 size 检查 / M12 _tenant_filter 等）— **2026-05-09 Phase 2.3 子 sprint D 决策升级 STILL_PUNT → DEFER_TO_POST_LAUNCH**（选项 C 上线优先+数据驱动 / 详见 `design/audit/phase23-perf-evaluation.md`）；触发条件 = 真负载 P95 > 500ms 告警 / 多租户场景启用 / Phase 3 数据回流后立 post-launch perf sprint
- **D 类 条件触发型 ~10 项**（#3+#15 join / #16 WS golden / #17 _sanitize_filename / #25-#28 M19 punts / #18-#19 M17 重构等）— 触发条件未到 / 不动
- **E 类 文档/UNVERIFIABLE ~14 项** — 子片 5 grep 验证 / 多数已被默默吸收 / 显式不立项

---

## 🔴 真漏洞（约定时机已过 + STILL_PUNT / 按严重度排序）

| # | punt | 来源 | 约定 | 影响 | 推荐处理 |
|---|---|---|---|---|---|
| 1 | ~~**write_event stub 仍未替换为真 INSERT**~~ ✅ **DONE 2026-05-09 commit 959e0b4** | M15-B1 | 后续独立 sprint | ~~critical~~ | **M16 sprint 子片 0.5 L1+L3 batch 关闭** |
| 20 | ~~**require_platform_admin Protocol 版 vs current_user 版去重**~~ ⏸️ **STILL_PUNT 2026-05-09 / M20 sprint 重新评估不触发**：M20 全走 require_user + assert_team_role / 无 platform_admin endpoint / 保留至下一含 platform_admin 模块（如未来 platform-admin 独立模块） | M18 R2 #2 | 子片 5+ 或后续 sprint | ~~medium~~ | M20 评估不触发 / 推迟到下一 platform_admin 模块 |
| 2 | ~~**M03-M08 service ~14 处裸 CRUD `action_type="create/update/delete"`**~~ ✅ **DONE 2026-05-09 commit 5c592d5**（实际 7 模块 41 处 含 M02 + M11 cold_start 命名漂移 + M07 issue_unassigned + M08 module_relation_updated + M05 version_record_set_current + M06 competitor_ref_updated 4 NEW enum）| M15-B2 | 与 B1 同 sprint | ~~high~~ | **M16 sprint 子片 0.5 batch 关闭 + ci-lint R14 grep 守护立规防御未来** |
| 3 | ~~**IssueResponse 漏 join 字段（node_name/created_by_name/assigned_to_name）**~~ ✅ **DONE 2026-05-09 / Phase 2.2 子片 5 关闸**：Issue 模型加 created_by_user/assigned_to_user relationship（lazy="raise"）+ IssueDAO `_JOINS` selectinload 应用到 list_by_project + get_by_id + IssueService create/update/transition 三处 refetch + router `_resp` 显式装配 + 3 backend e2e（test_list_issues_join_fields_populated / test_get_issue_join_fields_populated / test_floating_issue_node_name_is_none） | M07 R2 P2-1 | ~~M13/M15 集成期补~~ → **Phase 2.2 关闸**| ~~high~~ | DONE / 与 #15 一并 |
| 4 | ~~**SSE generator 占 AsyncSession 300s**~~ ✅ **RE-EVALUATE 2026-05-09 / M16 sprint 已用 BackgroundTasks + 自起 SessionLocal 替代长持 SSE 范式** | M13-B13 | M16/M17 立异步 SSE 策略 | ~~high~~ | **M16 §12B 后台 fire-and-forget 子模板 + 自起 SessionLocal 隔离请求级 Depends(get_db) 已沉淀**（commit 2273f90 + 043e3e2 / audit/m16 元贡献 #5）；M13 `analyze_service.py` SSE generator 仍存量未迁但**新模块（M16/M17）已不触发同款** → 标 STATUS_CHANGE：从"M17 必查"降为"M13 后续重构 sprint 顺手迁"low |
| 5 | ~~**M02 Project.ai_model 字段未实装**~~ ✅ **DONE 2026-05-09 / 子片 3 验证字段已存在不需 alembic add**（M02 model 字面已含 ai_model 列；M13-B16 punt 误判） | M13-B16 | M14+ baseline-patch | ~~medium~~ | **M16 sprint 子片 3 验证关闭** |
| 6 | ~~**M07 update 不支持 detach (None→NULL)**~~ ✅ **DONE 2026-05-10 / Post-Phase-2.3 Cleanup Sprint 4C.3 / SR-DETACH-1 立规 + 跨模块 5 模块同步立修**：CY 选 A2 一并修；L1-α 用户路径完整性原则压制 L1-β 状态机单一入口；M07 IssueService.update 改 fields dict 范式（router model_dump(exclude_unset=True)）；node_id 游离 + assigned_to 取消责任人 2 字段 detach 真支持；M02 update_project 移 exclude_none + update_ai_provider 走 fields dict（关闭 M02-A1）；M03 node description detach；M05 version details detach；M06 competitor + ref 6 字段 detach；M14 industry_news 已对范式（反向回扫确认）；6 detach unit tests 加 / pytest 1629→1638 PASS / 0 failed；design `06-design-principles.md` 附录立 L1-α 原则 + R16/R17 ci-lint grep 候选立规 | M07 R1-A P2-2 | ~~design §3/§7 reconcile + 产品决策~~ → **CY 拍 A2 / 跨模块一并修**| ~~medium~~ | DONE |
| 7 | ~~**M11-B1 R-X1 失败补偿 commit boundary**~~ ✅ **DONE 2026-05-09 / M17 子片 0 prep**：cold_start_service._mark_failed 改用 compensation_session 独立 commit boundary（task 创建立即 commit / 失败补偿 comp_db 独立写 task=FAILED+activity_log）；router 失败分支只剩 db.rollback() / R2 P1-01 punt 关闭；conftest autouse fixture monkeypatch compensation_session yield db_session 兼容 savepoint；1079 PASS 不破 | M11 R2 P1-01 punt | M17 异步 zip 导入时 | ~~critical~~ | M17 子片 1+2+3 直接复用 helper（首个非 M11 caller） |
| 8 | **M14-B12 update/delete/unlink write_event 异常传播 e2e** | M14 R2 punt | M14 baseline-patch | medium — M02+ 元教训纪律 3 写路径无 e2e 覆盖 | 与 #1+#2 同 sprint 做 |
| 9 | **M05-2/14 + M06-1 + M07-7 + M08-1 多模块 `if rows == 0: continue` race window** | 多 sprint | M15 升级 INSERT 时复审 | medium — B1 落地后必须一并复审；不复审会 silently 改变行为 | 与 #1 同 sprint 联动复审 |
| 10 | **M10-5 viewer /overview/stats 测试缺** | M10 R2 P2 #3 | M11 启动前补 | low — endpoint 行为正确，仅测试覆盖度 | M16 启动顺手补 |
| **11** | **IntegrityError → 500 跨模块 3 处（M02 project create ✅ DONE / M04-4 dimension B3 / M04-17 C7.1）** ⏳ **PARTIAL 2026-05-09 / M17 启动期**：通用规则已立（`design/00-architecture/06-design-principles.md` 清单 6 + ci-lint R15 grep 守护立规防御未来 + 3 类豁免显式声明）；M02 project create 已实装（project_service.py:102/302）；**M04 dimension 修存量推迟到独立 cleanup sprint** | M04 R1-A B3 + R1-C C7.1 | M05 sprint 顺修（已过） / M17 启动期立规 | ~~high~~ → medium（立规已落 / 存量保留 / 后续 sprint 自然推动） | M04 dimension_service.create + create_dimension_record 加 IntegrityError handler；ci-lint R15 实装由后续 sprint 落 |
| **12** | **M04-9 target_type 5 处 hard-code（service:327/378/436/482/516）** ⏳ 2026-05-09 M17 子片 0 prep 验证仍 STILL_PUNT；服务 M17 不触动 dimension_service 范围，本期不顺手清 | M04 R1-B B6 | M15 启动前 const 化（已过）| medium — 与 #1+#2 同根因（命名规约一致性）；若 #1 先升 schema 不 const 化会冲突 | M16 启动 reconcile A 栏首条 / 与 #2 同 batch |
| **13** | **M04-1 dimension_records (updated_by, updated_at) 联合索引未建** ⏳ 2026-05-09 M17 子片 0 prep 验证：现仅有 (project_id, updated_at) 索引（model:52），(updated_by, updated_at) 仍缺 / STILL_PUNT | M04 R1-A A2 | M15/M19 | medium — dimension_records 是 M13/M14 写大量行的源表，缺联合索引会让 activity_stream 时间线查询慢 | 与 #1 同 sprint 评估是否提前建 |
| **14** | **M04-8 db.get(DimensionType) 三处未走 DAO** ⏳ 2026-05-09 M17 子片 0 prep 验证仍 STILL_PUNT（service:349/428/474）；M17 不触 dimension_service，本期不清 | M04 R1-B B2.4 | M15 启动前（已过）| low — 风格统一性；service:349/428/474 三处 | M16 启动顺手清 |
| **15** | ~~**M04-R2 A1 DimensionResponse 缺 dimension_type_key/updated_by_name join 字段**~~ ✅ **DONE 2026-05-09 / Phase 2.2 子片 5 关闸**：DimensionRecord 模型加 dimension_type/updated_by_user relationship（lazy="raise"）+ DimensionDAO `_JOINS` 应用到 list_by_node + get_by_id + get_one + DimensionService create/update_with_lock 两处 refetch + router `_record_response` 显式装配 + 3 backend e2e（test_list_dimensions_join_fields_populated / test_get_dimension_join_fields_populated / test_update_dimension_join_fields_after_refetch）| M04 R2 A1 | ~~前端真用时补 join~~ → **Phase 2.2 关闸**| ~~medium~~ | DONE / 与 #3 一并 |
| **16** | **WS golden e2e（accept 后 service push + client receive）** | M17 R2 P1-01 punt | M18 集成 sprint 或专门 WS integration sprint | medium — sync TestClient + async fixture 桥接复杂；当前 4 鉴权拒绝矩阵已覆盖安全边界，golden 留 integration | M18+ 启动评估是否落 integration helper |
| **17** | **_sanitize_filename horizontal 化** | M17 R2 sink #1 | 第三实例（M18+ multipart 上传）触发 | medium — M11 cold_start + M17 import 重复实装；第三实例触发立规迁 api/utils/upload_helpers.py | 第三 multipart sprint 启动时迁 |
| **18** | **M17 confirm_review 绕过 _transition 缺 import_status_changed event** | M17 R1-A P2-3 | M18+ 顺手补 | low — design §10 期望每次状态扭转都有 status_changed event；当前缺 awaiting_review→ai_step3 一条 | M18+ 启动顺手补 |
| **19** | **M17 import_tasks.py 6 处 lazy import 抽 helper** | M17 R1-A P3-3 | 后续重构 sprint | low — 风格统一性；6 处重复 from api.core.db import SessionLocal + from api.services.import_service import ImportService | 后续重构 sprint 顺手抽 |
| **20** | **require_platform_admin Protocol 版 vs current_user 版去重**（R2 #2 PUNT）| M18 R2 #2 | 子片 5+ 或后续 sprint | medium — api/auth/dependencies.py:91 Protocol 版（depends require_user / set_auth_service stub）vs embedding_admin_router.py:58 内联版（depends current_user 真实 DB）；直接合并会让所有 admin 测试 401（注入 fixture 缺）| 需 conftest set_auth_service fixture 配套；M19 admin endpoint 触发再做 |
| **21** | **M18 worker source_text 真接上游 Service.get_for_embedding**（R1-A P1-3）| M18 R1-A | 子片 4+ / 接通 pgvector + 真业务 path 时 | high — 当前 source_text=f"{target_type}:{target_id}" 占位字符串 / content_hash 永远只 hash UUID / 所有 embedding 是 garbage；mock provider 测试不触发；生产 path 不可启用 | NodeService/DimensionService/CompetitorService/IssueService 加 get_for_embedding(target_id, project_id) → str 接口；M11 baseline-patch 已锁规但实施留 M18 后续 sprint |
| **22** | **EmbeddingTargetNotFoundError noop 转 succeeded 语义**（R1-A P1-11）| M18 R1-A | design 加字面或 task DAO 加 result_label="noop" | low — 当前 worker noop 路径转 task=succeeded 但 embeddings 表无对应行；admin /stats total_embeddings vs succeeded_tasks 有 gap | design 加一句"noop 转 succeeded + error_code=embedding_target_not_found"；或 cas_complete 加新参数 result_label="noop" |
| **23** | **M18 cron_failure_monitor PCT 维度真实施**（R1-C P2-3 / R2 #7）| M18 R1-C / R2 | 子片 4+ / 接 task_dao.count_completed_in_window | medium — 当前缺 PCT 维度只剩 ABS+PER_PROJECT 两维 / design line 1043 三维设计避免单维死参数；占位期已加 TODO 注释 | 实施 task_dao.count_completed_in_window 后接 PCT 计算分子分母 |
| **24** | **M18 batch_backfill 真 batch INSERT INTO embedding_tasks SELECT FROM unnest**（R1-C P1-4）| M18 R1-C | 子片 4+ / 5 万条规模 | medium — 当前 for-loop 逐条 enqueue() N+1 INSERT pattern / 5 万条回填 = 5 万次 DB 往返；占位期仅适用 mock provider 测试 | EmbeddingTaskDAO 增 batch_create(ids: list[UUID]) 用 INSERT ... SELECT FROM unnest(:ids) 单 SQL 批量 |
| ~~**25**~~ | ~~**CI build job tsc 88 错（Phase 2.3 残留死代码）**~~ ✅ **DONE 2026-05-12 Phase 2.3 cleanup S1+S3+S4+B+A+C+D**（tsc 88 → 0 / next build ✓ / pytest 1643 PASS） | Sprint 3.1 CI 接通暴露 2026-05-12 | Phase 2.3 集成验证 sprint | ✅ 全清 — 6 sub-sprint 累计 88 → 0：S1 (.local TLD seed -1) / S3 (permission.service.ts -3) / S4 (project-role-context + Project adapter -10) / B (dimension_types dev seed + workspace 字段访问) / **A (workspace 33 → 0 / actions D-aware adapter)** / **C (search 改 project-scoped M18 接通 / 删 services/search.ts + 旧 /search / 新 /projects/[pid]/search/page.tsx)** / **D (consumer 层 27 错 / overview ProjectStats+ActivityLog 字段对齐 + settings ProjectData/MemberData 删 local + relation-graph FeatureNode 类型双定义合并)**。**总用时**：~3.5h（pre-fact-finding 估 5-7.5h 偏高 2 倍）| 见 commits f15a5ed→<本 commit> + actions/projects/competitors/nodes/competitor-references 单点 adapter 收敛 |
| ~~**26**~~ | ~~**M01 admin list users 撞 .local TLD（EmailStr 严格验证）**~~ ✅ **DONE 2026-05-12 Phase 2.3 cleanup S1** | Sprint 3.1 CI 接通暴露 2026-05-12 | Phase 2.3 集成验证 sprint | ✅ 已修复 — `migrations/versions/m16_ai_snapshot.py:44` `'system@internal.prism0420.local'` → `'system@internal.prism0420.example'`（.example 是 IANA 保留示例域名 / email-validator 接受）+ dev DB row 同步 UPDATE / 1643 PASS 6 skipped 0 fail（顺手 `-x` 验 S2 等价完成）| 采方案 (a)：bug 在 seed 数据不在 schema 设计；schema EmailStr 严验保留 |
| **27** | **dimension_types + project_dimension_configs admin endpoint + create_project hook（R3-6-C 真路径）** | Phase 2.3 cleanup B sprint 揭露 2026-05-12 | D-2 sprint / 7 月碎片或 prism 真上线前 | high — design §3.Y R3-6-C 明文：业务字典清单走运行期 admin endpoint POST /api/admin/dimension-types 创建（待 admin UI 实装）。当前 prism-0420 后端只在 migration 种 1 行 'default'，create_project 不初始化 ProjectDimensionConfig → 新建项目后 workspace 看到 0 维度。**B sprint 临时方案** `scripts/seed_dimension_types.py`（dev DB 一次性 INSERT 8 行 dim_types + 对所有现有 projects INSERT 8 行 dim_configs / 不进 migration / 不进 production）已解锁 dogfooding。**长期需做**：(1) POST /api/admin/dimension-types CRUD（platform_admin only）+ POST /api/admin/dimension-types/{id}/projects 启用某项目 / (2) create_project 时按 template_type 调用 dimension_configs 初始化 hook（hardcoded 或 template_dimension_packs 表查表）/ (3) 删 scripts/seed_dimension_types.py 改用 admin endpoint 真路径 | D-2 sprint 工作量 4-8h |

---

## 🌟 元发现（机制本身的洞察）

### #1 高耦合触发点 — M15-B1 锁住下游 8 项历史 punt

**M05-2 / M05-14 / M06-1 / M07-7 / M08-1 + M13-B16 + M14-B12 + M15-B2** 共 **8 项**全
约定"M15 升级真 INSERT 时复审"—— B1 单点延迟使下游 8 项联动失修。立 punt 时**未识别
共享触发点**，导致状态从"分散小修"变成"一个 sprint 必须 batch 8 项"，工作量爆炸。

**立规**：未来 punt 立项时若发现 ≥3 项指向同一未来动作（如"M? sprint 升级 X 时"），
**自动升 P1 提前规划**到目标 sprint 计划段，不许做"分散登记"。

### #2 "性能 sprint" 是 punt 黑洞 — **关闭于 2026-05-09 / Phase 2.3 子 sprint D**

M02-M14 累计 **~12 项** punt 写"性能 sprint"，但项目从无独立性能 sprint 计划。M16
audit 必看是否吸收 / 否则将永久驻留 punt 池。

**2026-05-09 关闭**：12 项 status 升级 STILL_PUNT → DEFER_TO_POST_LAUNCH（详见 `design/audit/phase23-perf-evaluation.md`）。决策选项 C：上线优先 + 数据驱动 + Phase 3 数据回流后立 post-launch perf sprint。pool 状态明确归宿 / 黑洞**关闭**。

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

### #6 双栈迁移半完成 / 编译绿但运行 broken（2026-05-12 Phase 2.3 cleanup S3+S4 揭露）

**现象**：Phase 2.2 前端继承 9 子片全 ✅ 标 100% 完成，但 Phase 2.3 cleanup 跑真 tsc + 读 consumer 真实代码后发现 70+ 处数据形态漂移：

- workspace.tsx 33 错 / NodeData camelCase 期望 vs API snake_case
- consumer 层 32 错（overview/settings/page/issues/features/import/modules）/ 同 prism shape gap
- legacy search 7 错 / services/search.ts 指向不存在的 analyzer:8001
- 后端契约缺口：DimensionTypeRef 缺 description+field_schema / DimensionConfigResponse 扁平 vs 前端期望嵌套

**根因**：Phase 2.2 子片 audit 只验"导入 prism web 代码 + 替换 auth + 改 actions 调用 API"，未验**数据形态迁移完整性**。Drizzle（camelCase 字段约定）→ SQLAlchemy+Pydantic（snake_case 默认）字段名重映射全在编译期"宽松通过"——TS 不报错（用 `any` / `unknown` / loose typing），运行期返 `undefined`。CI 当时未接通 tsc 检查也是次因。

**与 #4 区别**：#4 是"分散小修被默默吸收 / 跟踪噪声"——已修但没记录；#6 是"未修 / 标 ✅ 但实际未完成"——更严重，破坏 phase 完成度信号本身。

**立规已落**：
1. `design/00-phase-gate.md` 关闸盲区 #2 段（2026-05-12 落地）— 未来"前端继承 / 后端栈切换"类 phase 必跑 (a) 旧栈字段名 grep / (b) consumer 抽样字段对照 codegen / (c) 后端 schema 与前端期望对齐 grep / (d) tsc 0 错
2. **"继承 ≠ 运行" 红线**：拷贝后必跑 happy path 真操作流程（至少 1 个核心 page UI 点击到 API 收响应），不能只看 `next build` 编译通过
3. **adapter 单点 vs consumer 全量**：consumer 端访问 ≥5 文件 → actions 层加 `toX` mapper / <5 → 直接 rename consumer

**STAR 标签**：
- 模式归类：契约漂移 28% 模式 / 子类"双栈迁移半完成 / 编译绿但运行 broken"
- 严重度：比关闸盲区 #1（删 export 未扫调用方 / 编译 broken）更高一档——前者 CI 红会暴露，后者编译过 = 永远不会被 audit 自动发现，需要人工 + 真跑才能识别
- 量化：Phase 2.2 子片关闸模板覆盖率 ≈ 80%（缺数据形态迁移完整性扫这一项），漏检 70+ 错

### #8 本地 dev 跑通 ≠ 远程访问跑通 / dogfooding 远程接入暴露 4 类系统性 bug（2026-05-12 cloudflare tunnel 上线）

**现象**：Phase 2.3 cleanup 完成（tsc 0 / pytest 1643 / next build / CI 全绿）后，准备 dogfooding 通过 cloudflare tunnel 暴露 `https://prism-0420.19911005.xyz` 给 CY Windows 浏览器访问。本地 dev 全跑通的同代码，**远程访问立即撞 4 类系统性 bug**：

#### 1. docker-compose 默认绑 0.0.0.0 公网暴露
- `prism0420-pg / prism0420-redis` ports `5432:5432` / `6379:6379`
- 实际公网 `162.43.44.163:5432 / :6379` 直接可达（`nc -zv` 验证 succeeded）
- ufw 防火墙完全失效（docker iptables 绕过 ufw 是已知现象）
- **修法**：ports 显式绑 `127.0.0.1:5432:5432` / `127.0.0.1:6379:6379`

#### 2. 浏览器端 fetch BASE_URL "http://localhost:8000" 远程访问撞客户机本地
- `services/http-client.ts: BASE_URL = NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"`
- 浏览器执行 JS 时 `fetch("http://localhost:8000/auth/logout")` → localhost = 客户机自己 / 不是服务器
- 症状：logout 无反应 / 隐身模式直接登录态（refresh failed silent）
- **修法**：BASE_URL 默认 `""`（同源相对路径）+ Next.js rewrites 转 backend
- **教训**：server-side fetch 和 client-side fetch 用不同 URL 策略 / 不能共享 BASE_URL 常量

#### 3. cookie `secure=settings.app_env != "local"` 把 CI/test/staging 都当 production
- `api/routers/auth.py:52` 设 cookie secure flag
- CI 是 APP_ENV=ci → secure=True / ASGITransport base_url=http://test 非 HTTPS → cookie 不发 → refresh test 401
- 症状：CI `test_refresh_with_cookie_only_no_body_token` 失败 / 本地 PASS
- **修法**：`secure=settings.app_env == "production"`（production-only 白名单）
- **教训**：黑名单 production 排除法（`!= "local"`）会把任何未列举环境当 production / 白名单才安全

#### 4. Next.js 默认无 rewrites / 前端单独跑无法代理 backend
- prism-0420 默认 `next.config.ts` 空 / 前端 3000 / backend 8000 各自独立
- 客户端 fetch 必须显式打 backend URL（撞 bug #2）
- **修法**：`next.config.ts rewrites /auth/* + /api/* → http://localhost:8000`
- **教训**：前后端分离架构的"前端 dev server 必须能代理 backend API"是基础设施前置 / 不该等远程接入暴露

#### Bonus: SYSTEM_USER 例外漏在 2 处业务逻辑（CI 暴露）
- migration m16 种 system user (role=platform_admin) / `count_active_admins` + `bootstrap_admin_if_empty` 都没排除 → CI 跑测试时 last-admin 保护逻辑失效 + bootstrap 永不创建首个 admin
- **修法**：两处 SQL 加 `WHERE id != SYSTEM_USER_UUID`
- **教训**：migration 种 seed 数据 + 业务断言（"empty"/"last"/"first"）冲突 / 所有 WHERE 都要显式排除 SYSTEM seed

**根因总结**：这 5 个 bug **共同点**——**本地 dev 同机器 + 同 localhost + APP_ENV=local 永远撞不到**。dogfooding 远程访问是第一个真实环境暴露（CI 已捕获 #3 + bonus，但 #1 #2 #4 必须真有浏览器跨主机才暴露）。

**立规已落**：
1. memory 候选 `feedback_remote_access_audit.md`：前后端分离项目 phase 关闸前必跑"远程访问 audit checklist"
   - 浏览器端 fetch BASE_URL 是相对路径还是 absolute localhost
   - Next.js rewrites 配 /auth/* /api/* 转 backend
   - docker-compose ports 绑 127.0.0.1 不绑 0.0.0.0
   - cookie secure 白名单 production / 不黑名单排除 local
   - migration 种 seed 数据后所有"empty/last/first"业务断言要排除 seed
2. phase-gate 关闸盲区 #3（候选 / 跟 #2 数据形态迁移半完成同档）—— 关闸 audit 模板必跑"远程访问 happy path"（不只本地 happy path）

**STAR 标签**：
- 模式归类：契约漂移 28% 模式 / 子类"本地环境假设漂移到远程"
- 严重度：跟关闸盲区 #2（数据形态迁移半完成 / 编译绿但运行 broken）平行 / 都是"本地 audit 永远撞不到的远程 bug"
- 量化：dogfooding 第 1 次远程接入 = 4 类 bug + 1 个 bonus / 全部本地 audit 完全无法发现
- **教训**：dogfooding 不只是"用产品"——是 phase 关闸最后一道远程环境验证 / 提前到 Phase 2.3 集成验证里可以拦下 80% 这些 bug

---

### #7 决策类推荐跳过 design + 真实代码 fact-finding（2026-05-12 C sprint 推荐翻车 + workspace 估时差 10 倍）

**现象**：Phase 2.3 cleanup 进行中两个决策暴露同根因失败：

1. **C sprint 推荐 C-1 全删**（CY 一问"看真实代码和设计"暴露 5 处反向证据）：
   - M18 design §1 明文"搜索框不变 / 升级 F9 / 保留 F9 全部能力" → 跟"删全局搜索"反向
   - M18 backend 99 行 search_router 真实装含 hybrid + RRF + pgvector 降级 / production-grade
   - GlobalSearchBar 是 7 页面 header `flex justify-between` 中间填充元素，删后视觉塌陷
   - SearchResultItem 在 `src/types/api.ts` codegen 是 M18 真类型，不是 dead
   - GlobalSearchBar hooks 是 production-grade，重做 1-2h 不是 30min

2. **workspace.tsx "1-2 天" 估时**（fact-finding 后实测 1-2h）：
   - 14 个 TS2554 全是同一种错（`getNodeWithDimensions(id)` 缺 projectId arg）→ 5-10 min find+replace 批量改
   - 8 个 TS2352 / 11 个 TS2345 总计 60-120 min
   - 之前 1-2 天估时基于"33 错 / 1549 行 / 大问题"笼统印象，没数具体修复路径

3. **DimensionTypeRef 扩字段 "30 min" 估时**（fact-finding 后 10 min）：
   - schema 加 2 字段 + router list comprehension 加 2 行 + codegen 自动重生 = 10 min
   - 而且 fact-finding 顺便揭露**更深业务漏**：dimension_types 表只种 1 行 'default'（migrations/versions/m02_project.py:163），workspace 期望的 8 维度（description/user_scenario/tech_impl/design_decision/engineering_exp/test_analysis/requirement_analysis/competitive_ref）从未真种过

**根因**：决策类推荐时跳过 fact-finding：
- 跳 design 文档（M18 design §1 业务背景没读，直接套"M18 = project-scoped"一句话归纳）
- 跳真实代码 grep（GlobalSearchBar 在 header 中的角色没看 / SearchResultItem codegen 类型没查 / TS2554 14 错没数具体修复路径）
- 用 abstraction + 推理代替 ground truth 验证

**与 #6 区别**：#6 是关闸 audit 模板不完整 / 漏验数据形态；#7 是**决策环节本身就跳过 fact-finding**。两者递进——#6 是机制漏洞，#7 是行为漏洞。讽刺连锁：同日刚立 #6 + 关闸盲区 #2 讲"决策跳 fact-finding"，几小时后 AI 又犯，被 CY 抓现行。

**立规已落**：
1. memory `feedback_decision_codefirst_validation.md`（2026-05-12 创建）— 决策类推荐前必 fact-finding 3 步：读 design 文档 + grep 真实代码 + hypothesis 反验；不适用于纯机械修复
2. 触发条件：A 模式选项 / 工作量估计 / "推 X 不推 Y" / sprint 范围划分 — 任一缺 fact-finding → 不许给推荐
3. 错误快路径识别：从"项目 X = Y"一句话归纳推具体决策 / "似乎应该删干净"心态 / 笼统估时

**STAR 标签**：
- 元方法论失败模式——AI 给推荐不读 design + 代码 → 决策类输出全不可信
- 量化：机械修复 fact-finding 程度高 → 9/9 不暴露；产品决策跳 design → 100% 暴露反向证据或工作量偏差 5-10 倍
- 比 #6 严重一档：#6 是 phase 关闸模板覆盖率不足（机制层），#7 是决策行为本身跳 fact-finding（行为层）；机制可补但行为漏洞需要立"规则 + 触发条件"双层防御
- **教训**：prism-0420 项目方法论是"设计前置 → AI 实现"。AI 给推荐时绕过 design 文档 = 方法论自我背叛

---

### #9 dogfooding sprint P1 cross-cutting 视角发现 baseline-patch 时序契约累计 6 处（2026-05-12 P1 闸门）

**现象**：dogfooding P1 全闸门（21/21 模块 / 2327 testpoint）/ 批 5 cross-cutting subagent 跨 19 模块综合元发现暴露 **baseline-patch 时序契约 punt 累计 6 处堆积**：

| # | 来源 | 描述 |
|---|------|------|
| 1 | M02 反向引用 | M20 / M18 反向引用未实装 baseline-patch |
| 2 | M03 enqueue B | enqueue B 路径推迟 baseline-patch |
| 3 | M04 enqueue B | enqueue B 路径推迟 baseline-patch（与 #2 同模式） |
| 4 | M07 audit A7 | issue A7 退化路径未补 baseline-patch |
| 5 | M13 audit B1 | M02/M03/M04/M07 baseline-patch 前置 / SSE 流式集成时同步堆积 |
| 6 | M15 NULLABLE | activity_stream baseline-patch project_id NULLABLE / 全局事件跨模块 patch 风险 |

**触发元发现 #1 自动升 P1 规则**：≥3 项 punt 同触发点 → 高耦合触发点。本批 6 项 **远超 ≥3 阈值**，**baseline-patch 时序契约**正式立为高耦合触发点。

**根因**：baseline-patch 模式 = 上游模块（如 M02）需要下游模块（M18/M20）实装后才能反向打补丁。设计前置阶段 6 处显式 punt 到下游 sprint，但**实施期下游 sprint 关闸时未做反向 reconcile**，6 处累积在 P1 cross-cutting 才一次性 surface。

**与 #1（M15-B1 锁住下游 8 项）区别**：#1 是单个高耦合 punt 阻塞下游；本条是**反向 patch 时序设计本身的堆积模式** / 每条 punt 单独看都"以后做"是合理决策，集中起来才是漂移。

**立规**：
1. **每模块 sprint 关闸 commit 必跑 baseline-patch reconcile pass**（查本模块是否有上游模块 punt 等本模块实装后回填 / 命中即立做或转入此触发点列表）
2. **dogfooding sprint cross-cutting 视角必含 baseline-patch 时序契约专项**（已在 `_handoff/dogfooding/01-testpoints/_cross-cutting.md` 视角 10 落实 10 条 testpoint）
3. **P2-P5 sprint 启动 reconcile pass 必查本条**（按本文件 policy "cold-start 必读" / 命中即纳入本 sprint 范围或显式 punt 升级 STILL_PUNT）

**STAR 标签**：
- 模式归类：设计前置阶段显式 punt 但实施期未追踪 → 跨 sprint 时序漂移
- 严重度：medium（每条单独不阻塞 / 累计起来是设计前置方法论的"长期债"实证 / Phase 3 v0.4 STAR 数据点）
- 量化：6 处 baseline-patch / 涉及 6 个不同模块 / 平均每模块 1 处 punt 反向 patch / cross-cutting 视角才一次性 surface
- **教训**：设计前置不等于设计完成 / **反向 patch 时序需要专门的跨 sprint 追踪机制**（本元发现就是新机制）
- **跟元发现 #1 联动**：#1 防"高耦合下游阻塞"，本条防"上游 punt 等下游反向回填漂移"，两个互补

---

### #10 auto-gen marker 字面自指 bug — 文档内 hint 嵌入 marker 字符串导致 non-greedy 正则误匹配（2026-05-12 Phase 3 v0.3→narrative 落地揭露）

**触发**：`phase3_data_collector.py` 重跑 7 次，`phase3-data-baseline.md` 累积 7 段重复（1 BEGIN + 7 END + 7 段 ## 维度 1）。表面看像"append 而非 replace bug"。

**真 root cause**（非表面）：脚本 line 333 hint 文本 `f"> 手工 narrative 段写在 {END_MARK} 之后，不会被脚本覆盖。"` 把 `END_MARK` 字面值嵌入了 BEGIN block 内部。每个 auto_block 因此含 **2 个 END_MARK 字符串**——一个在 hint 行（行中），一个在结尾（行起手）。Line 342 正则 `BEGIN.*?END` non-greedy 匹配 BEGIN→第一个 END_MARK（hint 行那个），真数据 + 真 END 被孤立保留。每次重跑残留一次 → N 次跑 = N 段重复。

**修复**（方案 1+2 一起）：
1. hint 文本不嵌入字面 marker 字符串（改成"自动生成区块之后"）
2. 正则加 `\n` anchor `BEGIN.*?\nEND` 强制 marker 行起手

**教训**：
- **marker 字符串必须唯一且只出现在结构位置**——不允许出现在 hint / 注释 / 文档说明里
- non-greedy 正则在文档替换场景**不能裸用**，必须配 anchor（`\n` 或 line-start）
- 发现 N 段重复时不要假设"append bug"——可能是 marker 匹配错位
- 跟元发现 #7 同源：决策跳 fact-finding。本次幸亏 systematic-debugging Phase 1 没跳"读真实代码 + 数 marker 数量"两步，否则会照着"append bug"方向乱改

**联动**：
- 与 #7（决策跳 fact-finding）：本元发现也是 phase 1 强制读源代码 + 数 marker 才避开了假修复
- 与 #4（被默默吸收）：7 段重复其实污染了 5/12 内 6 次脚本重跑后的 baseline.md，但没人 grep 看 marker 数量 → 默默累积

---

### #11 Phase 2.2 拷贝层 vs design §6 范式漂移群 — 每 frontend cluster 启动必先 reconcile（2026-05-15 cluster-M17 + cluster-M14 双 RCA 沉淀）

**触发**：Phase 2.x M-frontend follow-up sprint 内 5 个 cluster 共享同根因：
- **M11**（已闭 / sprint 内）/ **M17**（cluster commit cb27ac8 / RCA §5.2 首推）/ **M14**（cluster commit 79f6204 / RCA §5.3 再推 / 触发立元规则）
- 待做：**M12** / **M16** / **M13**（PUNT-REPORT.md 清单 / 全同根因群）

**根因模式**（双 cluster 实证 / 不只是单 sprint 巧合）：
1. **子片 3b 拷贝降级期**：把老 prism 业务 actions 整体 stub 为 `NOT_IMPLEMENTED` / `puntResult` / file header 注释承诺"子片 3c/5 接入"
2. **子片 3c/5 未执行**：cleanup S1+S3+S4+B+A+C+D 全完 reconcile 时未把 punt 列表完整入 cross-sprint-pool（已立 punt-frontend-gap-phase2x/PUNT-REPORT.md 5/13）
3. **design §6 字面 vs 实装路径段漂移**（不破契约 / 与 peer 业务组件范式不一致）：
   - M17 F1（business/ 子目录 vs flat）+ F5（独立组件 vs 合并到 wizard）
   - M14 F1（business/ 子目录 vs flat）+ F2（`web/` 前缀 vs 项目 app/）
4. **异步范式漂移**（M13 SSE + M16 轮询 + M17 WebSocket / M14 同步 CRUD 不触发）：老 prism 同步 setTimeout 假进度 / await mapping_rows vs prism-0420 design fire-and-forget + WS/polling
5. **拷贝层 stub 长期 punt 风险**（M14 实证 §3.3）：`actions/feed.ts` 8 NOT_IMPLEMENTED 签名 + 3 caller（workspace/overview/settings）残留 prism v1 UI / prism-0420 design 无对应概念 / 双域并存到 RSS sprint 或显式删除

**元规则**（cluster 启动前 reconcile checklist）：
- **A 栏首查**：每 frontend cluster cold-start 必 `cat _handoff/dogfooding/04-bug-fixes/punt-frontend-gap-phase2x/PUNT-REPORT.md §<当前模块>` + 本元规则
- **B 栏 design vs 实装 grep**：subagent fact-finding 阶段必 grep design §6 file list vs 实际 `app/src/...` 路径 / 标低风险漂移点（业务组件统一 flat / `web/` 前缀已固化）
- **C 栏 stub 旁路检查**：必 grep `actions/<related-domain>.ts` `NOT_IMPLEMENTED` / `puntResult` 残留 / 决策 leave/delete/redirect（cluster boundary 守恒优先 / 跨模块影响升 escalation §5）
- **D 栏 异步范式 audit**：design §6+§7+§12 异步范式 vs 老 prism 同步范式漂移点必单独成 finding（cluster-M17 F3 PARTIAL 范式参考）

**真漏洞触发关联**：
- 真漏洞表 #28 候选 — **feed 域 stub 长期归宿决策**（M14 RCA §5.1 / A: 删 feed UI 树 + actions/feed.ts / B: feed UI 改 listNewsByNode 适配器 / C: 保留到 RSS sprint）。当前 STILL_PUNT / 待 next cluster (M12) 或独立 cleanup cluster 评估。

**联动**：
- 与 cluster-M17 RCA §5.2 / cluster-M14 RCA §5.3（直接来源）
- 与 punt-frontend-gap-phase2x/PUNT-REPORT.md 共同根因段（5 cluster 同根因）
- 与 #1（高耦合触发点）—— Phase 2.2 子片 3b 是 ≥5 cluster 同根因的高耦合点，本元规则正是 #1 的应用

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
| M02-A1 | ~~update_project exclude_none 让 null 无法清字段~~ ✅ **DONE 2026-05-10 / Sprint 4C.3 SR-DETACH-1 跨模块同步立修**（与 #6 同根因 / L1-α 立规） | DONE |
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

### M18 sprint punt 池（5 项 / 详 design/audit/m18-pilot-template-validation.md）

| # | 项 | 状态 |
|---|---|---|
| #20 | require_platform_admin 去重 | STILL_PUNT — **真漏洞 #20** |
| #21 | worker source_text 真接上游 Service.get_for_embedding | STILL_PUNT — **真漏洞 #21** |
| #22 | noop 转 succeeded 语义 | STILL_PUNT — **真漏洞 #22 / low** |
| #23 | cron_failure_monitor PCT 维度真实施 | STILL_PUNT — **真漏洞 #23** |
| #24 | batch_backfill 真 batch INSERT FROM unnest | STILL_PUNT — **真漏洞 #24** |

### M19 sprint punt 池（4 项 / 详 design/audit/m19-pilot-template-validation.md）

| # | 项 | 状态 |
|---|---|---|
| #25 | _md_cell + _render_dimension_content + _render_pros_cons horizontal 化到 api/utils/markdown_helpers.py | STILL_PUNT — 第二渲染场景触发（M20+ 团队报告）/ 输出端 horizontal |
| #26 | filename sanitize 输入端（M11/M17）vs 输出端（M19）分门别类立规（SR-M19-3 sink 候选） | STILL_PUNT — 第二输出端实例触发 |
| #27 | Cache-Control: no-store header 缺失（含 user 上下文敏感数据） | STILL_PUNT — M20 性能 sprint 横切添加 |
| #28 | filename 含 project_name 风险（RFC 5987 filename* 编码） | STILL_PUNT — 该改动发生时 |

### 触发点 D — M19 元教训 #19：R1 局部立修触发 tests.md 第三方文件漂移

**M17 立的 R2 reconcile** 仅覆盖 design ↔ 实装 / **M19 第二实证扩**第三方 tests.md 必须纳入 R2 reconcile B 栏。

**SR-M19-1 立规建议**：每 sprint R2 reconcile 必跑 `grep -n "404\|422\|500" tests.md` 与 `exceptions.py:http_status` + `design.md:§13` 字面比对。M20 sprint 启动期 reconcile pass A 栏首条预录。

### M15 sprint punt 池（3 项）

| # | 项 | 状态 |
|---|---|---|
| B1 | write_event stub 替换为真 INSERT | STILL_PUNT — **真漏洞 #1 / 高耦合触发点** |
| B2 | M03-M08 service 裸 CRUD action_type | STILL_PUNT — **真漏洞 #2 / B1 联动** |
| B3 | OpenAPI schema 一致性自动校验 | UNVERIFIABLE |

### Phase 2.2 子片 3c punt 池（8 项 / 全部 ✅ DONE 2026-05-10 Sprint 1 / 详 design/audit/p22-pilot-template-validation.md §3c）

| # | 项 | 状态 / 触发时机 |
|---|---|---|
| P22-3c-1 | ~~search.ts / project-stats-proxy.ts 内联 redirect / 不复用 withAuthRedirect~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.5 commit 5afc6d1 + Task 1.2 project-stats-proxy 一并并入 withAuthRedirect** |
| P22-3c-2 | ~~StatsResult&lt;T&gt; vs ActionResult&lt;T&gt; 双 result 类型并行~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.2 commit 2b890dd**：删 services/project-stats.ts 死代码 + proxy 全 ActionResult / overview/page.tsx caller r.ok→r.success |
| P22-3c-3 | ~~issues.ts 命名前缀混用 list/get~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.4 commit ad1d040**：getIssuesByNode/Category → listIssuesByNode/Category |
| P22-3c-4 | ~~competitor-references 命名缺资源前缀~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.4 commit ad1d040**：updateReference→updateCompetitorReference + 全套资源前缀 |
| P22-3c-5 | ~~findInTree 三处重复~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.3 commit 0507ffa**：抽 lib/tree-utils.ts 泛型 + 5 unit tests + 3 caller 收敛 |
| P22-3c-6 | ~~export.ts ExportPayload = unknown / OpenAPI 真不约束~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.1 commit dae2760 / 真因重定**：原 punt 描述误导成 "后端 schema 缺失"；实际后端走标准 HTTP attachment / 真问题 = 前端 client wrapper 不支持 text/binary。新增 serverApiPostDownload 从 Content-Disposition 提 filename + body.text() / ExportPayload→DownloadResponse / 5 unit tests / 修 caller 存量 unknown 错 |
| P22-3c-7 | ~~activity-log.logActivity / logActivityAuto no-op 兼容层~~ ✅ **DONE 2026-05-09 / Phase 2.3 子 sprint C commit af6f78e**：no-op 函数已删 / 残留 caller analysis/page.tsx 已清 / Sprint 1 Task 1.6 验证零残留 |
| P22-3c-8 | ~~project-stats-proxy 注释提兼容层但缺 file-level eslint-disable cleanup anchor~~ ✅ **DONE 2026-05-10 / Sprint 1 Task 1.7 自然消除**：Task 1.2 重写 proxy 后 0 eslint issue / file-level disable 锚点不再需要 |

**3c trend update**：
- P22-3b-1 helper 重复从 5 文件扩散到 10 文件（superset）/ 抽 lib/server-action-helpers.ts 时机已成熟
- P22-3b-2 findInTree 重复持续 3 处 / 与 P22-3c-5 同源
- **3c 立修 root-cause**：`errors.ts.actionError` 加 isUnauthenticatedError → redirect 一改通修 mutation 路径 401 静默吞错（影响 3a/3b 全栈，但 3c 关闸时立修 / 无残留 punt）

### Phase 2.2 子片 4 punt 池（详 design/audit/p22-pilot-template-validation.md §3d）

| # | 项 | 状态 / 触发时机 |
|---|---|---|
| P22-4-1 | TeamMemberRemoveResponse.residual_project_members 仅展示 count / 详情未消费 | Phase 2.3 GET members endpoint 上线后统一展示残留成员详情 |
| P22-4-2 | isTeamOwner action 死代码 / page 直接 creator_id 推断未调用 | ~~子片 5 决定~~ → defer Phase 2.3 frontend-polish 子 sprint（与 P22-3c-1~8 同批）|
| P22-4-backend-gap | M20 后端 4 项 endpoint 缺口 — 子片 4 启动期 ls 穷举发现：(a) GET /api/teams/{tid}/members 列成员名单 + role + user_name；(b) GET 候选用户检索 endpoint（add member + transfer 下拉数据源 / 当前只能 by user_id 输入）；(c) GET /api/teams/{tid}/me-role admin/member RBAC 真守卫数据源；(d) ❌ soft-delete + restore = M20 design §3 Q8=B 字面已决 hard delete + RESTRICT FK / **不立项 / prompt 字面错记纠正** | Phase 2.3 集成期评估补 (a)+(b)+(c) / (d) 撤销 |

**4 trend update**：
- P22-3b-1 helper 重复从 10 文件扩散到 11 文件（superset / teams.ts +1）/ 抽 lib/server-action-helpers.ts 时机持续 / Phase 2.3 启动前必抽
- **4 立修 root-cause**：`errors.ts isNextRedirectError` 加 export + 3 处 client `.catch` rethrow（teams/page + teams/[teamId] + projects/page 同根因连带修）/ R 范式第 5 数据点 R2 真漏抓 client-side 同根因新场景变体 / SR-P22-4 实证扩展

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

## 产品级 punt (Prism KB 知识 lifecycle / 2026-05-12 unsunk-scan F-8.10)

> **背景**：2026-05-11 文章 "Harness 不是目的，知识才是护城河" 分析提出的 G-OPT-001 已部分实现（memory 层 maturity+decay 字段），但应用到 Prism **产品层** 的 F-OPT-001~003 未落地。

| ID | 内容 | 当前状态 | 触发时机 |
|----|------|---------|---------|
| **F-OPT-001** | 需求知识 maturity 字段（草稿→稳定→归档），防止过期需求干扰 AI | 仅提出，未实现 | dogfooding sprint 后 / Phase 4 需求审计 / 用户反馈知识陈旧时 |
| **F-OPT-002** | 知识衰减触发器（超过 N 天未引用自动降级），与 memory 层 G-OPT-001 同构 | 仅提出，未实现 | F-OPT-001 实现后 / dogfooding 验证需求归档机制可行 |
| **F-OPT-003** | MOC（Map of Content）视图替代纯文件列表，类似 memory 的 MEMORY.md 但用户侧 | 仅提出，未实现 | F-OPT-001+002 实现后 / 用户开始有 ≥20 文档时 |

**与 prism-0420 当前 scope 关系**：产品功能扩展，**不在当前 sprint scope**（Phase 3 / dogfooding 已锁）。dogfooding 完成后评估是否进 Phase 4。

**触发联动**：dogfooding sprint 完成后 Phase 4 规划时必查本段，决定是否升级为 P0 sprint。

---

## 关联

- 9 个 audit 文件：design/audit/m{05,06,07,08,10,11,12,13,14,15}-pilot-template-validation.md
- handoff §2.1 M01 后置债 + §0a 历史快照 M02 后置债
- 立规来源：feedback_kb_design_principles（过期触发 + 增量 vs 周期）+ feedback_inbox_7day_rule（>7 天必处置不许"再想想"驻留）
- 2026-05-12 unsunk-scan F-8.10 (`_handoff/unsunk-scan-2026-05-12/chunk_8.md`)
