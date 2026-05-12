# Chunk 8 Findings（05-11 ~ 05-12 / 14 sessions）

扫描范围：14 sessions / 0.43MB / 主题：Phase 2.3 翻车日 + dogfooding P1 全闸 + CI接通 + 冷启动测试
基线对照：/tmp/prism-essences/kb-baseline.txt
输出时间：2026-05-12

---

## Summary

| 指标 | 数值 |
|------|------|
| 扫描 session | 14 |
| 识别 findings | 12 |
| 高置信度 | 8 |
| 中置信度 | 4 |
| 主要缺口类型 | bug教训(4) / 方法论(3) / 跨session收口(2) / 设计决策(2) / 未完结TODO(1) |

---

## F-8.1 `feedback_remote_access_audit` 6项远程访问检查单（高）

**来源 session**：77b3f34e（2026-05-12 主翻车日）
**类型**：方法论 + 技术坑
**状态**：已写入 `memory/feedback_remote_access_audit.md`，但 **未在 AIQE KB** 中沉淀

**内容**：
前后端分离项目部署到远程服务器时必跑 6 项关闸 checklist：
1. Docker 容器绑定 `127.0.0.1` 而非 `0.0.0.0`（安全）
2. 浏览器 fetch 走同源（`NEXT_PUBLIC_API_URL` 空 = 同源）
3. Next.js rewrites 把 `/auth/*` + `/api/*` 代理到后端端口
4. Cookie `secure=settings.app_env=="production"`（不是 `!= "local"`，CI env=ci 会误触 secure=True 导致 http 401）
5. dev seed 中 SYSTEM_USER 在 `count_active_admins` + `bootstrap_admin_if_empty` 中必须排除其 UUID
6. 远程浏览器访问 happy path（不只是 localhost curl）

**建议目标**：AIQE KB `/root/workspace/projects/ai-quality-engineering/10-项目/Prism/02-Bug与审计/` 新增「远程访问部署 checklist」条目

---

## F-8.2 前端继承 phase 关闸必须包含 `tsc --noEmit=0`（高）

**来源 session**：77b3f34e（2026-05-12 / 关闸盲区 #2）
**类型**：bug教训 + phase-gate 设计缺陷
**状态**：已在 session 中讨论，但 **未在 AIQE KB 中作为 phase-gate rule 沉淀**

**内容**：
Phase 2.2 被标记为"100%完成"时，Drizzle camelCase → FastAPI snake_case 迁移实际只做了一半（前端 types 用了 camelCase 但 API 实际返回 snake_case）。这个断裂直到 Phase 2.3 的 `tsc --noEmit` 扫描才发现（88 个 TS 错误）。

核心教训：**前端继承任何后端 schema 变更的 phase，关闸必须包含 `tsc --noEmit=0` 作为硬指标**，而不只是"人工确认迁移"。

**建议目标**：AIQE KB Prism/02-Bug与审计 + `_handoff/` 中的 phase-gate checklist

---

## F-8.3 `dimension_types` seed 问题 + `create_project` 未初始化 `ProjectDimensionConfig`（高）

**来源 session**：77b3f34e（2026-05-12 B-sprint 执行段）
**类型**：设计决策 + bug教训
**状态**：临时用 dev seed SQL 脚本修复，**设计决策未在 design/ 中正式沉淀**

**内容**：
- M02 §R3-6-C 规定：`dimension_types` 由管理员在运行时通过 admin 端点创建（不能写死在 migration 里）
- `create_project` API 不初始化 `ProjectDimensionConfig`（每个维度的 enabled/required 配置），导致新建项目后 dogfooding 无法选维度——成为 dogfooding blocker
- 临时解法：dev seed SQL 脚本插入 8 个 dimension_types + 初始化 ProjectDimensionConfig
- 正式解法（punt 到 D sprint）：实现 admin 端点 + 让 `create_project` 自动初始化 ProjectDimensionConfig

**建议目标**：
- `design/M02-dimension-model/sprint-notes.md`（或 ADR）记录"dev seed 不等于 migration"决策边界
- AIQE KB 记录"业务实体创建时必须初始化关联配置表"范式

---

## F-8.4 Phase 3 STAR 数据：设计前置 -39% bug（高）

**来源 session**：77b3f34e（2026-05-12 Phase 3 数据收集段）
**类型**：跨session收口 + 项目里程碑数据
**状态**：已在 `_handoff/phase3-data-baseline.md` 中记录，但 **未在 AIQE KB Prism 项目日志 / README 中展示**

**内容**：
Phase 3 v0.3 STAR 数据快照：
- 设计前置组（Prism）：14 个 fix commits / 13 天到"可 demo"基线
- 无设计前置组（历史对照）：23 个 fix commits / 23 天到等效基线
- 结论：**设计前置 -39% fix commits，-43% 历史时间**

这是 2026 年 10 月跳槽目标"PRISM 代表作"的核心量化数据点。

**建议目标**：AIQE KB `10-项目/Prism/` 顶层 README 或 leaderboard + `project_career_2026q4_jump.md` memory 的证据栏

---

## F-8.5 CI 4个"spec→impl文本抄，本地dry-run缺失"bug（高）

**来源 session**：5cf6f219（2026-05-12 CI sprint 3.1+3.2）
**类型**：bug教训 + 工程实践
**状态**：已在 prism v1 `bugs/INDEX.md` 记录为 P420-001~004，但 **未在 AIQE KB Prism/02-Bug与审计 中归档**

**内容**：
4 个 CI 配置 bug，共同根因="从 spec 文本复制配置，但未在本地跑一遍验证"：
- P420-001：`pytest-cov` 不在 pyproject.toml dev 依赖中（spec 引用了但没装）
- P420-002：`pnpm-workspace.yaml` 缺 `packages` 字段（本地 pnpm 10 容忍，CI pnpm 9 报错）
- P420-003：3 个死 `@/actions/auth` import（auth 迁移了但旧引用没清）
- P420-004：test_config 环境变量 `APP_ENV` 未设置为 `test`（导致 CI cookie secure 行为异常）

**建议目标**：AIQE KB `Prism/02-Bug与审计/` 增加「CI接通 - spec→impl drift 4连坑」条目

---

## F-8.6 cookie `secure` 模式的正确设计范式（中）

**来源 session**：5cf6f219（2026-05-12 CI cookie bug 修复段）+ 77b3f34e
**类型**：技术坑
**状态**：代码已修复，**未沉淀为可复用的 engineering pattern**

**内容**：
错误范式：`secure=settings.app_env != "local"` → CI（APP_ENV=ci）会使 secure=True，http 测试 transport 下 cookie 被丢弃 → 401
正确范式：`secure=settings.app_env == "production"` → 只在 production 设 secure，本地/CI/staging 全部走非 secure

推论：**任何基于 env 的布尔开关，应用"白名单正确值"而非"黑名单排除值"**，以防新 env 名称意外落入黑名单行为。

**建议目标**：AIQE KB `Prism/02-Bug与审计/` 或通用工程 KB

---

## F-8.7 dogfooding 5阶段 + 6智能体测试体系设计（高）

**来源 session**：77b3f34e（2026-05-12 dogfooding brainstorm 段）+ 1bbc6158 + aae35cb6 + e49c4963
**类型**：方法论 + 项目里程碑
**状态**：已在 `_handoff/dogfooding/` 目录下（phase1-testpoint.md / progress.md / cross-cutting prompt），但 **未在 AIQE KB 中归档为可复用的测试方法论**

**内容**：
Prism dogfooding 体系架构：
- **P1**：testpoint 生成（21/21 模块完成，2327 个 testpoint，~$23 cost）
- **P2**：Playwright spec 编写（未开始）
- **P3**：执行（未开始）
- **P4**：fix + RCA（未开始）
- **P5**：regression（未开始）

6 类智能体：P1-agent（testpoint）/ P2-agent（spec）/ P3-agent（execution）/ P4-agent（fix+RCA）/ P5-agent（regression）/ meta-agent（orchestration）

Agent 接口契约 T1-T6：T1=输入模块范围 / T2=输出格式要求 / T3=并发限制（≤4 Opus 并发）/ T4=cost 节流 / T5=自检规则 / T6=完成信号格式

**建议目标**：AIQE KB `10-项目/Prism/` 新建 `dogfooding-system.md` 或 `05-测试体系/`

---

## F-8.8 P1 testpoint 5大跨模块元发现（中）

**来源 session**：1bbc6158 + aae35cb6（dogfooding P1 批1~5）
**类型**：跨session收口 + 产品质量洞察
**状态**：已在 `_handoff/dogfooding/progress.md` 中记录，**未在 AIQE KB 或 PRISM 风险登记中可视化**

**内容**：
P1 testpoint 生成过程中发现的 5 个跨模块高频模式：
1. **R-X3 第三方实体真注入**（连续 4 模块命中：M06/M07/M08/M12）— cross-cutting 必有专项
2. **viewer 写端点 403 元教训**（M07 发现后 M08/M12 主动复制）— 教训跨模块自传播成功
3. **跨项目实体 422 非 403 范式**（3 模块连续命中）
4. **多表事务 `with db.begin()` 主纪律**（4 模块连续命中）
5. **escalation surface ≥100 testpoint**（M07 issue 模块 / 状态机 4 态 + 5 禁转）

**建议目标**：AIQE KB Prism 项目 / 风险登记或 Phase 3 data context

---

## F-8.9 pre-commit + `git mv` stash 联动 bug（中）

**来源 session**：6664f27d + 703f2360（2026-05-12 _handoff 清理）
**类型**：技术坑
**状态**：已在 `memory/feedback_git_safety.md` §6 中沉淀，**未在 AIQE KB 通用工程坑中记录**

**内容**：
当 staging area 同时有 `git mv`（rename）和普通修改时，pre-commit framework 在执行 hook 前会 stash，但 stash 会把 staged rename 变回 unstaged（两个独立文件 add + delete）。

规避方案：把 rename 和修改分两次 commit（先 commit rename，再 commit 修改），或用 `git commit -- <pathspec>` 精确限定提交文件范围。

**建议目标**：AIQE KB 通用工程坑 / git safety

---

## F-8.10 Knowledge lifecycle（maturity+decay）for Prism KB 未实现（中）

**来源 session**：9c2211a6（2026-05-11 文章分析 "Harness不是目的，知识才是护城河"）
**类型**：未完结TODO + 产品/系统设计
**状态**：G-OPT-001~004 已提出，G-OPT-001（memory lifecycle）已部分实现（4字段 frontmatter），但 **F-OPT-001~003（Prism产品知识生命周期）未落地**

**内容**：
文章核心洞察应用到 Prism 产品设计：
- F-OPT-001：需求知识 maturity 字段（草稿→稳定→归档），防止过期需求干扰
- F-OPT-002：知识衰减触发器（超过 N 天未引用自动降级）
- F-OPT-003：MOC（Map of Content）视图替代纯文件列表

当前状态：memory 层已有 maturity 字段，Prism 产品层（KB + design）尚未实现。

**建议目标**：`_handoff/` 新建 TODO 项目 或沉淀到 `design/` 的 product-roadmap 段

---

## F-8.11 "create project → redirect to login" dogfooding bug（高）

**来源 session**：77b3f34e（2026-05-12 cloudflare tunnel 验证段）
**类型**：bug教训 + 未完结TODO
**状态**：在 dogfooding 中被 CY 发现并报告，**未做 RCA / 未修 / 未在 bug tracker 中登记**

**内容**：
用户在 Prism 界面点击"创建项目"后，直接重定向到 login 页面（而非创建成功后的项目详情页）。

触发路径：点击"创建项目" → 后端 API 可能返回非 2xx（可能是 dimension_types 缺失 → 500 → 前端 auth guard 误判 → redirect login）

关联 F-8.3：`create_project` 未初始化 `ProjectDimensionConfig` 是候选根因之一。

**建议目标**：
- AIQE KB `Prism/02-Bug与审计/` 登记此 bug（待 RCA）
- `_handoff/dogfooding/` 新增 P4 任务项

---

## F-8.12 估算方法论缺陷：TS错误分析前不可给时间估算（中）

**来源 session**：77b3f34e（2026-05-12 workspace.tsx 估算段）
**类型**：CY方法论反思 / 智能体行为教训
**状态**：session 中有讨论和自我检讨，**未沉淀为可操作的估算 checklist**

**内容**：
两次10x估算失误：
1. workspace.tsx："1-2天" → 实际 TS2554 14个错误全同类型 → 5-10分钟 → 1-2小时
2. C-2 GlobalSearchBar改写："1-1.5h" → 未检查 M18 backend schema vs 前端字段映射 → 实际35分钟（D-aware adapter减少了工作量）

反模式：拿到"TS 88 errors"就估"1-2天"，**没有先 `tsc --noEmit 2>&1 | sort | uniq -c | sort -rn` 看错误分布**。

正确流程：估算 TS 修复工时前，必须先跑错误分类命令，按错误类型分组计数，才能判断实际工作量量级。

**建议目标**：`feedback_decision_codefirst_validation.md` 补充"TS错误估算必先分类"子规则

---

## 跨Chunk 累积缺口（需要与之前 chunk findings 合并关注）

以下是在本 chunk 发现、但实际根源更早的系统性缺口：

- **关闸盲区** 系列（#1=关闸时未验迁移完整性 / #2=前端继承无 tsc 硬指标）：应在 phase-gate.md 显式列出
- **元发现 #7 立规即犯** 现象：`feedback_decision_codefirst_validation` 规则在建立当天即被违反 3 次 → 说明规则本身需要"强制工具拦截"而非"意识提醒"
- **dogfooding baseline-patch punt pool** 在 4 个模块命中（M02/M03/M04/M07）：说明 baseline-patch 是系统性技术债，需要独立 sprint 而非分散 punt

---

*生成时间：2026-05-12 / 扫描员：Claude Sonnet 4.6*
