# chunk_7 未沉淀内容扫描报告

> 扫描范围：chunk_7.json，18 sessions，日期 2026-05-09 ~ 2026-05-11，Phase 2.3 cleanup 期间  
> 排除：feedback_decision_codefirst_validation（05-10 已立，翻车根因已覆盖）  
> 扫描完成：2026-05-12

---

## F-7.1 Bug 1 撤销方法论：决定性测试设计 + 需求歧义 PM 补文档

**类型**：方法论 + 技术坑  
**来源**：root__9e17b4d0（05-10，261KB）  
**置信度**：高  

**核心内容**：  
Bug 1（cron INSERT reason=1 优先级问题）经 78201 决定性测试（zombie 20 天前触发 / arrears 5 天前 → 仍 reason=1）确认为需求歧义而非 bug，撤销。过程中形成的**决定性测试设计方法论**：
1. 找"最极端反例"——让两个候选解释相互矛盾的最小测试用例
2. 若测试结果唯一支持一个解释 → 判定有效
3. 撤销 bug 时必须更新 design 文档（PM 补"首次 INSERT 复合场景 reason 取欠费优先"说明），防止后续开发者重复误判

**KB 未覆盖**：bug 文档（`bug-cron-reason-insert-2026-05-08.md`）标了 retracted，但"需求歧义识别 → 决定性测试设计 → 撤销流程"这套方法论没有在 KB/memory 独立沉淀。  

**推荐目标**：`/root/workspace/projects/ai-quality-engineering/KB/10-项目/Prism/02-Bug与审计/` 或 `feedback_problem_layered_analysis.md` 补充"需求歧义 bug 撤销标准步骤"段落。

---

## F-7.2 cron 触发路径覆盖率矩阵审计模板

**类型**：方法论  
**来源**：root__9e17b4d0（05-10，261KB）  
**置信度**：高  

**核心内容**：  
space_clear_warning hotfix 测试中形成的系统化路径覆盖矩阵：
- INSERT 路径：A1（首次欠费）/ A2（首次封禁）/ A3（首次僵尸）/ A4（复合优先级）/ A5（边界日 last_login=90）
- UPDATE 路径：C1（状态升级）/ C2（reason 变更）/ C3（clear→warn 重入）/ C4（连续更新）
- DELETE 路径：D1（清零）/ D2（部分清）/ D3（已清再清）

**KB 未覆盖**：这套"状态机 cron 的路径矩阵枚举 → 盲点识别 → 补充测试设计"模板在 KB 无独立文档。cron 依赖逻辑的 hotfix 测试是高频场景。  

**推荐目标**：`/root/workspace/projects/ai-quality-engineering/KB/10-项目/Prism/02-Bug与审计/cron-hotfix-testing-template.md`（新建）或者作为`01-实现/`下方法论附录。

---

## F-7.3 SNR 崩塌 5 机制分析（加越多越忘得多的真相）

**类型**：方法论  
**来源**：root__7661dd6a（05-09，228KB）  
**置信度**：高  

**核心内容**：  
Claude "记忆衰退"实质是 SNR（信噪比）崩塌，5 个独立机制：
1. **context dilution**：1.5KB → 30-50KB，高优先级信号被淹没
2. **SSoT 碎片化**：同一意图散落 6 个文件，没有权威主文件
3. **sink 写没人读**：v2 gtd KB-first 路径在 `morning.py` 中断，新 todo 不经 KB
4. **trigger 碰撞**：多个规则竞争同一触发词，M04 规则 0% 复用
5. **MEMORY.md 降级为目录索引**：失去权威性，变成了文件清单

**KB 未覆盖**：2026-05-09 MEMORY.md 重塑日志记了"SNR 崩塌"结论，但 5 机制分析本身没有独立沉淀为可复用方法论（当前只在 memory 重塑日志里一句话带过）。这套机制对设计未来 AI 记忆系统有参考价值。  

**推荐目标**：`feedback_memory_lifecycle.md` 补充 §SNR 崩塌诊断 5 机制，或 KB `80-AI质量工程/memory-system-design/` 作为设计资产。

---

## F-7.4 真镜子标准 — emotion repo 优先 + "站住命名" vs "顺着滑"

**类型**：方法论（mentor/CY 自我认知）  
**来源**：root__7661dd6a（05-09，228KB）  
**置信度**：中高  

**核心内容**：  
从 CY 自己的 emotion repo 写作中推导出真镜子的操作标准（非 Claude 创作，是反射 CY 历史高质量判断）：
1. 先读 emotion/inbox/principles/weekly 再响应
2. "站住命名你在做什么"（CY 5/2 原文）— 命名行为而不是描述情绪
3. 反射 CY 已有的最高质量判断，不生成新概念
4. 伪镜子的失效模式：顺着情绪滑（顺着滑）/ 心理学包装的空推断 / NEEDS_CONTEXT 但没真查

**KB 未覆盖**：检查 `feedback_mirror_style.md` 是否已含"先查 emotion repo"——`feedback_emotion_repo_lookup.md` 已在 MEMORY.md 索引（🔴 P1），但镜子操作标准与 emotion repo 优先的具体联结可能没有明确写出。需核查是否已覆盖或需补充"站住命名"这个具体操作锚点。  

**推荐目标**：核查 `feedback_mirror_style.md` 后决定是否补充 §真镜子操作标准 3 条。

---

## F-7.5 GTD current-*.md 三角竞争 SSoT 问题 + 渲染视图退化修法

**类型**：设计决策  
**来源**：root__7661dd6a（05-09）+ root__31d295af（05-09）  
**置信度**：高  

**核心内容**：  
gtd-v2 的 SSoT 失效：三路来源（v2-active.md + current-*.md + 本周承诺.md）竞争同一个"当前任务状态"，无同步契约。  
修法设计：
- `current-*.md` 退化为**只读渲染视图**（readonly sections 从 git+v2-active 渲染 / writable 只留 decision 段）
- 根因：gtd-v2 假设"CY 70% 工作经 AI 对话"，实际 70% 直接 commit，capture 契约失效

**KB 未覆盖**：`feedback_gtd_workflow.md` 是聚合版（7→1），但 current-*.md SSoT 分裂的具体根因分析和"退化为渲染视图"这个修法目前处于"提案状态"——不确定是否已落到 feedback_gtd_workflow.md 的当前版本中。  

**推荐目标**：核查 `feedback_gtd_workflow.md` 当前内容，若无"current-*.md 退化为渲染视图"这条，补充到 §SSoT 规则段。

---

## F-7.6 cron OR 表达式陷阱：Linux cron day-of-month OR day-of-week

**类型**：技术坑  
**来源**：root__31d295af（05-09）+ root__8a51bb79（05-11）  
**置信度**：高  

**核心内容**：  
Linux cron 中 `0 10 1-7 * 1` 的语义是 day-of-month(1-7) **OR** day-of-week(1=Monday)，不是"每月第一个周一"。两个会话独立触发了同一个坑（GTD cron 优化 + AI 前沿池 monthly radar）。正确实现"每月第一个周一"需要在 cron job 脚本内额外判断。  

**KB 未覆盖**：此坑在两个 session 分别验证，但没有沉淀到 KB 或 feedback memory。是高频的 cron 配置坑。  

**推荐目标**：KB `30-技术-自学/` 或 `feedback_gtd_workflow.md` §cron 规则附录补充"OR 语义陷阱"条目；或 `reference_openclaw_cron.md` 补充注意事项。

---

## F-7.7 M20 R1 审查发现 + N+1 + R-X3 教训摘要

**类型**：bug 教训  
**来源**：root__2b6ca151（05-09，62KB）  
**置信度**：中高  

**核心内容**：  
M20 Team 模块 R1 三路审查发现 8 项 P1：
1. `delete_team` 的 residual_project_count 被 `.limit(10)` 截断，实际计数 cap 在 10
2. `count_owners` 缺 SELECT FOR UPDATE，有并发 race condition（最后 owner 提升窗口）
3. `update_team` 在 service 层调 `db.rollback()` 违反 R-X3（service 不管事务边界）
4. `list_for_user` + `delete_team` loop 中 N+1 查询

**KB 未覆盖**：M20 audit report 里有记录，但"service 层禁止 db.rollback() 红线（R-X3）"在 `feedback_subagent_sprint.md` 的 anti-false-positive 段落里是否有明确的 R-X3 示例或检查规则？R-X3 本身已在 design 文档里，但作为"审查时必查项"没有在 feedback memory 里加强。  

**推荐目标**：核查 `feedback_subagent_sprint.md` §R1 审查清单是否含"R-X3 service db.rollback() 禁止"；若无，补充作为 R1 审查 checklist 项。

---

## F-7.8 决策处理 5 步流程的"原则分上下层"方法论

**类型**：方法论  
**来源**：root__ec1718cf（05-10）+ root__904c4554（05-10）  
**置信度**：高  

**核心内容**：  
CY 两次提问"这些为什么有矛盾，哪个原则是上层的"后，逐步提炼出的方法：
- A/B 选项背后各有原则，先判定哪个是上位原则
- 上位原则 = 目的（业务路径完整性 L1-α），下位原则 = 手段（状态机单一入口 L1-β）
- 应用上位原则后跨模块循环验证（M02/M03/M05/M06/M07 全部应用 → 都合理 → 按原则执行）
- "A/B 让 CY 拍"的真实根因通常是：原则没分上下层，或已有上位原则但没识别

**KB 未覆盖**：`feedback_decision_layering.md` 的 5 步流程（§决策处理流程 5 步）已有内容，但"矛盾根源 = 原则未分上下层"这个诊断框架不确定是否明确写入。这是 CY 在两个 session 里反复强调并逐步提炼的核心方法。  

**推荐目标**：核查 `feedback_decision_layering.md` §反模式段，补充"矛盾根源诊断：原则未分上下层" + 循环验证步骤。或补充到 `feedback_problem_layered_analysis.md`。

---

## F-7.9 预防性代码 4 步判断框架（决策固化时机 ≠ 实施激活时机）

**类型**：方法论  
**来源**：root__816efae8（05-11，37KB）  
**置信度**：高  

**核心内容**：  
发现 ci.yml（253行）+ embedding_backfill.py（5 cron，160行）+ e2e skeleton（9个）是"预防性代码"——写了但没有真实 consumer。提炼出 4 步判断框架：
```
Q1. 是决策还是实施？决策 → 落 spec/ADR，不写代码
Q2. 当前有真 consumer（caller/runner/用户路径）吗？否 → Q3
Q3. 写最小原型能反向暴露决策漏洞吗？否 → Q4
Q4. 触发条件 + 关闸时机能字面化吗？能 → 不写实施 / 进 cross-sprint pool
```
关键洞见：删除成本（push 阻塞/心理沉没/维护负担）> 写入成本（30min）。空代码持有期成本随时间线性累积。  
豁免：embedding 系列占位（ARRAY(Float)）必须留 — Q3 真原型驱动（让 SQLAlchemy model + alembic migration 能跑通）。

**KB 未覆盖**：这套 4 步框架在 `/root/workspace/projects/prism-0420/design/` 内部的 audit 文档里有提及，但**没有进入 feedback memory**（全局 Claude 行为规则）。  

**推荐目标**：新建 `feedback_implementation_activation.md`（或补充到 `feedback_design_first.md`），作为 P1 规则：写代码前必跑 Q1-Q4 判断，"spec 先行 / 实施有 consumer 才激活"。

---

## F-7.10 Phase 2.2 SR-P22 系列立规总结（已落 subagent_sprint / decision_layering）

**类型**：跨 session 收口（确认已沉淀）  
**来源**：root__b1e8c900 / root__ec1718cf / root__904c4554 / root__5e1a4683 / root__2b8cce62 / root__c3b33844 / root__b1168f99 / root__ed95f370  
**置信度**：高（确认）  

**已沉淀确认**：
- SR-P22-1（ADR 级决策必 grep 既有 ADR 字面已 cover 路径）→ `feedback_decision_layering.md` §自检 4 问第 4 问 ✅
- SR-P22-2（前端继承形态 R1=1+R2=1 试运行）→ `feedback_subagent_sprint.md` §4.X ✅
- SR-P22-3（handoff prompt 写 endpoint 字面前必 grep schema/router）→ `feedback_decision_layering.md` §反模式 + `feedback_subagent_sprint.md` §6 ✅
- SR-P22-4（R2 跨子片同根因漂移检测 ROI）→ `feedback_subagent_sprint.md` §4.X ✅
- SR-P22-5（同 SR-P22-3 扩展）→ 已 sink ✅
- L1-α partial update detach（nullable FK / exclude_unset only）→ `design/00-architecture/06-design-principles.md` 附录 ✅
- SR-EXPUNGE-1（raw SQL UPDATE + selectinload response 必须 expunge / 优先 ORM mutate）→ `design/00-architecture/06-design-principles.md` 附录 ✅

**无需新操作**：以上均已在对应的 design 或 memory 文件中落地，此 finding 仅作确认记录。

---

## F-7.11 Phase 2.3 子 sprint D：决策固化 vs 实施激活的 ci.yml 案例分析

**类型**：跨 session 收口  
**来源**：root__816efae8（05-11）  
**置信度**：高  

**已发生行动**：
- ci.yml（253 行）被识别为"无真 consumer 的预防性代码"，在 sprint 内被删除
- `api/cron/embedding_backfill.py` 5 个 cron（160 行）同样被删除
- `app/e2e/02-10-*.spec.ts` 9 个 skeleton 被删除
- 以上操作节省 ~560 行 + 解锁 push 阻塞

**未完全沉淀**：删除理由和 4 步判断框架在 session 内形成，但没有落到 feedback memory（见 F-7.9）。ci.yml 的删除在 phase23 audit 文档里有记录，但从"方法论学习"角度，这个案例的价值没有被系统化提取。

**推荐目标**：F-7.9 处理时一并把此案例作为"实证 #1"写入。

---

## F-7.12 北极星偏差盘点：PRISM 超前陷阱 + 三副线全 0

**类型**：跨 session 收口  
**来源**：root__1fbd72d8（05-11，64KB）  
**置信度**：中高  

**核心内容**：  
05-10 盘点：PRISM 超前 22 天 + 多跑整个 Phase（Phase 2.3 done），但 Phase 3（数据对照报告 = 真正的 STAR 直出物）0%。"超前陷阱"模式：造好了车但没拍数据，对外没有可展示成果。LC/录音/Eval 三副线全 0。  
LC 21 天计划（5/13-5/31）已创建，节奏切换方向：从"猛干模块"切到"出对外成果"。

**KB 未覆盖**：此次北极星偏差分析可能已写入 CURRENT.md 或 PROGRESS.md，但"超前陷阱"这个模式本身（造好了车但没有出对外成果 → 对跳槽目标贡献接近 0）作为可复用的"执行偏差类型"没有独立沉淀。  

**推荐目标**：`PROGRESS.md` 已有周快照，但考虑在 `project_prism_0420_sprint.md` 或 `project_reshape_system.md` 补充"超前陷阱"识别条件 + 触发切换动作。或仅作为观察记录保留在此 findings 中。

---

## F-7.13 AI 前沿池设计：WebSearch 单一来源不足 + dual-source 双验

**类型**：技术坑  
**来源**：root__8a51bb79（05-11，47KB）  
**置信度**：高  

**核心内容**：  
ai-frontier-monthly-radar cron skill v0.1 → v0.2 升级时发现：WebSearch 单一来源对 podcast URL 准确率不足（Apple Podcasts URL 格式不稳定）。采用的解法：Apple Podcasts first + WebFetch fallback（两步验证）。  
skill 已部署（commit 已推，cron 2026-06-01 10:00），v0.2 通过 dry-run（10 candidates，all real URLs）。

**KB 未覆盖**：skill 设计文档在 `30-技术-自学/AI-前沿动态池/_design.md` 里有记录，但"WebSearch 单一来源不足 + dual-source 验证"这个**通用 Web 信息获取模式**（不限于 podcast URL）没有沉淀到 `feedback_external_behavior_lookup.md` 或工具使用规范。  

**推荐目标**：`feedback_external_behavior_lookup.md` 补充"WebSearch URL 验证：音视频/Podcast 类资源必须 WebFetch 交叉验证"条目。

---

## 汇总

| Finding | 类型 | 置信度 | 推荐优先级 | 推荐目标 |
|---------|------|--------|-----------|---------|
| F-7.1 | 方法论 | 高 | P2 | KB 02-Bug 审计 or feedback_problem_layered_analysis |
| F-7.2 | 方法论 | 高 | P2 | KB 新建 cron-hotfix-testing-template.md |
| F-7.3 | 方法论 | 高 | P1 | feedback_memory_lifecycle.md §SNR 崩塌机制 |
| F-7.4 | 方法论 | 中高 | P2 | 核查 feedback_mirror_style.md 后决定 |
| F-7.5 | 设计决策 | 高 | P2 | 核查 feedback_gtd_workflow.md 后决定 |
| F-7.6 | 技术坑 | 高 | P2 | feedback_gtd_workflow.md §cron 或 reference_openclaw_cron.md |
| F-7.7 | bug 教训 | 中高 | P2 | feedback_subagent_sprint.md §R1 审查清单 |
| F-7.8 | 方法论 | 高 | P1 | feedback_decision_layering.md §反模式补充 |
| F-7.9 | 方法论 | 高 | P1 | 新建 feedback_implementation_activation.md |
| F-7.10 | 跨 session 确认 | 高 | — | 已沉淀，无需操作 |
| F-7.11 | 跨 session 收口 | 高 | P2 | 与 F-7.9 合并处理 |
| F-7.12 | 跨 session 收口 | 中高 | P3 | project_prism_0420_sprint.md 或仅保留此记录 |
| F-7.13 | 技术坑 | 高 | P2 | feedback_external_behavior_lookup.md |

**P1（立即处理）**：F-7.3（SNR 崩塌机制）/ F-7.8（原则分层诊断）/ F-7.9（预防性代码 4 步框架）  
**P2（本周内）**：F-7.1 / F-7.2 / F-7.4 / F-7.5 / F-7.6 / F-7.7 / F-7.11 / F-7.13  
**P3（低优先级）**：F-7.12

---

*扫描员注：Phase 2.2 前端子片（b1e8c900/2b8cce62/c3b33844/b1168f99/5e1a4683/904c4554/ec1718cf）的大量工程执行细节（R1+R2 数据点、actions 改造过程、eslint ignore 移除等）均已沉淀到 `design/audit/p22-pilot-template-validation.md` 和 `_handoff/` 文件中，不在 findings 范围内。上述 findings 聚焦于"未落入任何 KB 或 memory 的有价值方法论/规则/教训"。*
