---
title: M13 pilot 三轮对抗 audit
status: draft
owner: reviewer-agent
created: 2026-04-25
batch: pilot-4
modules: [M13]
---

# M13 pilot 三轮对抗 audit

> **审稿立场**：独立、不附和、每条问题必须有文件路径 + 节号。
> **参照基线**：README 16 字段模板 + R0-R15/R-X1~X4 + ADR-001~004 + M04/M17/M01 pilot 范本 + Prism F13 实装。
> **不挑战 CY brainstorming 8 Q 决策本身，只审落地**。

## 总体评价

初稿结构完整，16 节到齐，§12A 7 字段子模板首稿成形，tests.md 覆盖面亦扎实，属高完成度 pilot 初稿。但**落地时存在 5 处 Blocker**——主要集中在：① 上游 Service 契约与 M02/M03/M04/M07 已 accepted 设计里的实际签名**全部对不上**（Phase 2 实装时会全盘找不到接口），② §8 P2 路径声明缺失（save/affected-nodes 走 Server Action 必走 P2，而 §8 表格里 P2 行只存在于"流式"讨论的反面），③ §5 R-X3 共享 session 规范未显式声明 M04/M15 Service 接受外部 session 的契约，④ §10 `target_type="node"` + M15 Check 枚举未扩 `requirement_analysis.save` 的回写路径只勾在 checklist 但未写回流程详细度，⑤ §12A 子模板 7 字段对 M16（🪷）不可直接复用——缺"无用户盯盘"场景所需进度/状态字段。

另有 Major/Minor 若干。建议主对话按 Blocker 逐条精修后再启动 CY 全文复审。

---

## 第一轮：完整性

**R1-01 上游 Service 契约与 M02/M03/M04/M07 已 accepted 的真实签名全部不匹配** — 级别：**Blocker**

`00-design.md §2` 末段 "依赖契约（M13 假设上游提供）" 与 `§3` 上游依赖表 + `§6` 分层职责表一致引用以下上游接口：

- M02：`get_project_ai_config(project_id)` / `check_project_access(project_id, user_id, role=...)`
- M03：`get_node_with_path(project_id, node_id) -> Node` / `get_subtree_names(project_id, node_id, depth=2)`
- M04：`list_dimension_records_for_node(...)` / `create_dimension_record(...)` / `get_latest_dimension_record(...)`
- M07：`list_issues_by_node(project_id, node_id, limit=20)`

对照 `design/02-modules/M02-project/00-design.md:528-564`、`M03-module-tree/00-design.md:416-449`、`M04-feature-archive/00-design.md:349-374`、`M07-issue/00-design.md:368-386`，上游 Service 的真实方法名是：

- M02：`list_by_user` / `get_by_id_for_user` / `list_by_project`（ProjectMember）/ `get_member`——**无 `get_project_ai_config` 也无 `check_project_access`**（注：check_project_access 是 Router Depends，见 M02 §8 L504，不是 Service 方法）
- M03：`get_by_id(node_id, project_id)` / `list_subtree` / `list_children`——**无 `get_node_with_path` 与 `get_subtree_names`**，且物化 `path` 是表字段（M03 L173）而非单独方法
- M04：`list_by_node` / `get_one` / `update_with_version`——**无 `list_dimension_records_for_node` / `create_dimension_record` / `get_latest_dimension_record`**
- M07：`list_by_project` / `get_one`——**无 `list_issues_by_node`**

违反 `ADR-003 §Decision §规则 1`（"上游模块需要为聚合读场景显式暴露接口"）+ `README R-X4`（聚合读模块必须引 ADR-003 且依赖必须在上游已登记）。Phase 2 实现时 M13 将找不到任何一个声明的 Service 接口。

**修复方向**：两选一——(a) M13 §2 "前置依赖"追加一行"accept 前置条件：M02/M03/M04/M07 四模块需通过 baseline-patch 追加上述接口"，并各给出最小签名；或 (b) 改用上游已有接口（如 M03 `get_by_id` + 读 `.path` 字段自行解析），并在 §3/§6 做等价改写。本 pilot 若采 (a)，需立即触发基线补丁流程，不得 accept M13 于前置未落地时。

---

**R1-02 §3 上游依赖表的 M02 `projects` 行访问方式标注错误** — 级别：**Major**

`00-design.md §3 上游依赖表清单` 将 M02 `projects` 表访问方式标为 "Service 接口调用 `get_project_ai_config`"，对应 ADR-003 规则 1。但 M02 Service 并未在设计里登记该方法（见 R1-01）；且 M02 本身是自有实体表归属模块，M13 读 `projects.ai_provider` 属于"同一聚合事务链路中取子对象"而非"搜索类聚合"——即使 M02 补接口，命名与规则 1 的 `search_by_keyword / list_by_xxx / get_by_id` 规范（ADR-003 §规则 1）也不契合。

**修复方向**：选 `get_by_id_for_user(project_id, user_id)` 返回 Project 对象，M13 读 `.ai_provider` + `.ai_api_key_enc` + `.ai_model`（对齐 M02 §3 L214+ 的 Prism 已有列）。同时在 §3 依赖表里把 M02 `projects` 的"访问方式"列改成 "Service `get_by_id_for_user` 读取 ai_provider/ai_api_key_enc/ai_model"。

---

**R1-03 §3 核心设计决策候选 B 改回成本（R3-4）适用范围声明错误** — 级别：Minor

`00-design.md §3 核心设计决策候选 B 改回成本（R3-4）` 首句："M13 无'⚠️ 核心设计决策'（分析结果存 M04 已在 brainstorming Q2 确定，非 pilot 期待决策点）"。

对照 `README §3 R3-4` 原文："核心设计决策必须有'候选 B 改回成本'块——对于有 ⚠️ 核心决策的模块"。R3-4 适用条件是"有 ⚠️"——M13 无 ⚠️ 时 R3-4 本身不强制适用，初稿仍提供改回成本是 over-compliance（无害），但"Q2 已确定"措辞会被误读成"R3-4 不适用所以也不需 ADR-003 规则引用"。

**修复方向**：本节首句改为 "M13 §3 采用 R3-5 纯读聚合规范（ADR-003 规则 1），无 ⚠️ 待决；R3-4 不强适用，下方成本块为 CY Q2 ack 决策的可逆性留痕"。

---

**R1-04 §7 `SaveAnalysisResponse` 缺失回写节点高亮所需的时间戳字段回传** — 级别：Minor

`00-design.md §7` `SaveAnalysisResponse` 仅返 `dimension_record_id + message`。但 `AffectedNodesResponse` 需要 `analysis_saved_at` 字段（同节 L334），`tests.md G1` 断言 `analysis_record_id=<上一步返回的 id>`——save 返回后前端直接 GET `affected-nodes` 才能拿到时间戳；若并发多 save，前端拿不到确定的 `created_at` 校对。

**修复方向**：`SaveAnalysisResponse` 增 `analysis_saved_at: str`（ISO-8601），tests.md G1 补断言。

---

**R1-05 §13 `AnalysisProviderError` 同码承载两种语义——被 R13-2 wrap 后无法区分** — 级别：Major

`00-design.md §13 R13-2 跨模块错误 wrap`：
- Provider 调用失败 → `AnalysisProviderError`（http 503）
- M02 找不到 AI config → 同样 wrap 为 `AnalysisProviderError`，message 改成"先配置 AI provider"

两者 http_status、用户引导差异很大（503 是"服务器/第三方临时问题，请重试"；未配置是 422/400"你需要去配置页面设置"）。tests.md E7 的断言会无法区分此两类 error_code。

**修复方向**：新增 `ANALYSIS_PROVIDER_NOT_CONFIGURED`（http 400 或 422，code 独立）与 `ANALYSIS_PROVIDER_ERROR`（503）分开。对应 §13 R13-1 +1 个 AppError 子类；tests.md E7 断言改 `error_code="ANALYSIS_PROVIDER_NOT_CONFIGURED"`。

---

**R1-06 §10 R10-2 回写 M15 的 CHECK 枚举扩增路径未显式声明 Alembic 迁移项** — 级别：Minor

`00-design.md §10 R10-2`：声明 accept 后回写 M15 `ActionType` 枚举 + "若启用 CHECK constraint，需新 Alembic 迁移"。

对照 `M15-activity-stream/00-design.md:179-187`，CHECK constraint **已启用**（有 `ck_activity_log_action_type` 枚举值显式列出），且 `requirement_analysis.save` **不在**现有枚举里。故 "若启用"是既成事实，Alembic 迁移是**必须**不是"若"。

**修复方向**：§10 R10-2 段改为"必须在 M13 accepted 同期提交 Alembic 迁移，追加 `requirement_analysis.save` 到 M15 `ck_activity_log_action_type` 枚举列表"，并在 §15 最后一勾（"accepted 后的横切补丁"）把这条从"ActionType 枚举加"细化为"ActionType 枚举 + Alembic 迁移扩 CHECK 枚举"。

---

## 第二轮：边界

**R2-01 §8 P2 Internal Token 路径在非流式端点（save / affected-nodes）被 Server Action 转发时完全缺席** — 级别：**Blocker**

`00-design.md §6` 分层职责表明确：save / affected-nodes **走** Next.js Server Action。按 `ADR-004 §Decision §核心 5 项第 2 点`，Server Action → FastAPI 服务间调用必须走 P2（Internal HMAC + X-User-Id + 签名），而非 P1。

但 M13 `§8 权限三层防御点` 表格里 "Router" 行凭据路径列写的是 "**P1 Bearer JWT（优先）+ P2 Internal HMAC（兜底）**"——虽然把两条写了，但全文**无任何一处**说明 Server Action 侧如何发起 P2（例如 `fetch(..., headers: { 'X-Internal-Token': ..., 'X-Internal-Signature': ..., 'X-User-Id': ..., 'X-Internal-Timestamp': ... })`），也没有说明流式端点是否接受 P2（ADR-004 §3.2 签名材料含 `body_hash`，流式响应的 request body 非空，是可以走 P2 的，但本期决策 Q1 ack "流式只走 P1"）。

违反 `README R8-1`（所有模块 3 层 + 异步路径声明）+ `ADR-004 §横切影响`（所有业务模块 §8 必须引本 ADR 声明"本模块用 P1/P2"）。

**修复方向**：§8 权限表格增一行"Server Action（save/affected-nodes）→ FastAPI 的凭据转发走 ADR-004 P2"；§8 "流式端点 auth 特殊说明" 段增补一句"save/affected-nodes 两个非流式端点走 Server Action，凭据从 P1（浏览器端 Auth.js session）在 Server Action 侧转为 P2（X-Internal-Token + X-User-Id + HMAC 签名）发到 FastAPI，Router 层 `Depends(require_user)` 自动接 P2 兜底（ADR-004 §核心 5 项第 2 点）"。

---

**R2-02 §5 流式期间 `self.db` session 占用 5 分钟的 DB 连接池风险未审计** — 级别：Major

`00-design.md §6 Service` 层：AnalyzeService `__init__(self, db: Session, ...)`；§5 多表事务列："save 阶段 Service 层 `with self.db.begin():`"。对照 FastAPI 默认 `Depends(get_db)` 生命周期 = 一个 request scope——流式 request 持续 5 分钟，意味着**这 5 分钟 Session 不归还连接池**。典型 Postgres 默认连接池 ~10-20，5 个并发流式请求即可打满（CY Q4 ack 允许并发）。

违反 `README §5 约束清单` 精神（并发列虽标"✅ 无 lock"，但未分析 DB 连接池压力）。

**修复方向**：§5 并发列或 §12A 字段 ⑤（超时策略）补一段"流式期间 DB 连接占用分析"：① 声明在 `async for` 开始前完成所有上游 Service 调用（拉 context 完成）并 `db.close()`/释放 session；② 流式循环内只保留 AI provider stream，不持 DB session；③ save 阶段由前端新起请求（G1 流程即如此），另开一个 request scope 的 session。tests.md 可选加 1 条"连接池监控"非功能性断言。

---

**R2-03 §5 多表事务列声明 "with self.db.begin():" 但未显式验证 M04 / M15 Service 接受外部 session** — 级别：**Blocker**

`00-design.md §5` 多表事务列声明："save 阶段 Service 层 `with self.db.begin():` 包两次写（dimension_record + activity_log），单表事务语义"。

`README R-X3`：跨模块调用的下游 Service 方法必须接受外部 `db: Session` 参数，不自开事务。M13 save 时调 `M04.DimensionService.create_dimension_record` + `M15.ActivityService.log` 必须满足此约束。

但 M04 `00-design.md:349-374` 的 `list_by_node / get_one / update_with_version` **均不接受外部 db 参数**（与 R-X3 冲突，已在 README §基线补丁清单标"M04 高概率需改"）；M15 的 `ActivityService.log` 签名在 M15 §6 中也需核对。M13 §5 没引用 R-X3，没声明"依赖 M04/M15 Service 接受外部 session 的前提"。

违反 `README R-X3`。若 M04/M15 未先完成 baseline-patch，M13 `with self.db.begin():` 包两次写就会变成"两次独立事务"——activity_log 写入失败时 dimension_record 无法回滚。

**修复方向**：§5 多表事务列补一段："依赖 M04 `DimensionService.create_dimension_record(db, ...)` 与 M15 `ActivityService.log(db, ...)` 均接受外部 session（R-X3）。两 Service 当前设计签名不满足本契约，accept 前置条件 = 基线补丁完成 M04/M15 相关方法改签名。" §15 accepted 后横切补丁清单里补一项。

---

**R2-04 §11 断线后用户"再分析"产生多份 dimension_record 的"前端 UX 兜底"完全缺失** — 级别：Major

`00-design.md §11` 声明三端点均无幂等，"save 多次 = 多条历史记录是合法产物"。Q3 ack 断线不续传——断线 → 用户再分析 → 生成新 full_result → 用户再 save → 又写一条。3-5 分钟内可能写 N 条 duplicate-ish 记录。

`tests.md C3` 断言"快速点保存 3 次 → 写 3 条"——仅验证"不拦"，未验证"前端/UI/Service 是否给出防抖提醒"。§7 SSE 客户端消费策略末尾 "用户点取消按钮" 之外无防抖约定；§10 的"activity_log 以 node 为 target_type"+"按 node 折叠 UI"是"刷屏由 M15 UI 解决"的设计——但"重复 save"的源头是 M13 的前端组件（`analyze-drawer.tsx`），应在 Component 层防抖（disable 按钮 / loading 态 / 同结果 SHA256 去重提示）。

违反 `README §设计原则` 的"用户体验兜底"精神（虽无硬 R 规则，属 Major）。

**修复方向**：§6 Component 层职责描述增 "点击保存后按钮立即 disabled 直至 save response 回来；同一 full_result hash 在本抽屉生命周期内不允许二次 save"；tests.md 新增 1 条前端行为断言 `[E2E] 连点保存第 2 次无响应`。

---

**R2-05 §8 JWT 中途过期与 ADR-004 §5 `token_invalidated_at` 的衝突点表述不精确** — 级别：Minor

`00-design.md §8 流式期间的连接级 auth 一致性` 写："JWT 即使中途过期不影响已建立的 HTTP/1.1 长连接……接受此脱节（最大 5 分钟暴露窗口）"。

对照 `ADR-004 §核心 5 项第 5 点`：`token_invalidated_at` 的 4 个触发事件（管理员禁用 / 改密 / 强制登出 / 刷新令牌被盗）——**这些不是"JWT 自然过期"**，是"服务端主动作废"。M13 §8 把两种情况合并成"JWT 过期"叙述，技术上不精确：自然过期用户无感（JWT `exp` 字段），主动作废是"本应立即失效但 M13 选择不中断流"（ADR-004 §5 用"iat vs token_invalidated_at"比较，要求 Access token 校验时拒绝——M13 流式里不做逐 chunk 校验，这才是真正的"脱节"）。

**修复方向**：§8 "流式期间的连接级 auth 一致性" 段区分两种情况：(a) JWT 自然过期（exp）——流继续，与 ADR-004 一致（ADR-004 未要求 HTTP 长连接内重校）；(b) 管理员主动作废（`token_invalidated_at`）——M13 明确选择**不中断**已建流，接受 ≤5min 暴露窗口，与 ADR-004 §5 精神形式上有脱节但明确声明为已知决策（非 bug）。该脱节由 §8 显式接受并写入 tests.md P9。

---

## 第三轮：演进 / 可复用性

**R3-01 §12A 7 字段子模板对 M16（🪷 后台 fire-and-forget）不可直接复用——缺"用户不盯盘"场景字段** — 级别：**Blocker**

`00-design.md §12A` 7 字段：①端点路径 ②event 类型枚举 ③data payload schema ④鉴权路径 ⑤超时策略 ⑥取消机制 ⑦断线重连策略。对 🌊 流式 SSE 完备。

Walk-through：假设明天起 M16（🪷）用 §12A 填空——M16 是"用户不盯着、服务器跑完入库"的后台任务，对"断线重连"字段定义不适用（用户本就不在），对"取消机制"字段也需重新定义（是"任务状态改 cancel"不是"fetch AbortController"），最关键是 **§12A 没有字段表达"任务状态查询端点"**（M16 依赖的 `GET /tasks/{id}` 轮询或 WebSocket push）、**没有字段表达"任务结果在哪里拿"**（M16 不流式，结果写 DB 供后续 GET）、**没有字段表达"失败重试策略"**（🪷 可能也需要 1-2 次重试）。

违反 `README §12 异步形态分支表` 精神（§12A/B/C 应形成可互相对照的 7 字段基线）。M16 若照抄 §12A 将发现 60% 字段不适用。

**修复方向**：§12A 本节保持 M13 的 7 字段填充，但**额外增"子模板扩展指南"段**，声明：
- §12A 7 字段对 🌊 流式适用；对 🪷 后台/🗂️ Queue 需"字段映射"——列一张映射表（本 pilot 不填 M16/M18 具体值，但给出"🪷 场景下字段 ②/⑥/⑦ 的重定义方向"）。
- 或者：明确声明"§12A 仅服务 🌊 场景；M16/M18 另起 §12B/§12C 子模板，不复用 §12A 字段表"，并在 §12 本节开头写清楚"7 字段是 🌊 场景专属，不是统一跨 3 形态的基线"。
- CY brainstorming Q7 的"§12A 7 字段对齐 §12C Queue schema 详细度" —— 对齐的是**详细度粒度**，不是**字段语义**。原稿文字（§12 开篇）有混淆风险。

---

**R3-02 Prism F13 实装与 M13 设计的 URL 路径差异未做"前端迁移成本"评估** — 级别：Major

Prism 实装（`/root/prism/api/routers/analyze.py:254`）：`POST /analyze/requirement`（扁平、`project_id/node_id` 在 request body）。M13 设计（`00-design.md §7`）：`POST /api/projects/{project_id}/nodes/{node_id}/analyze/requirement`（嵌套、路径参数）。

对 Phase 2 实装而言：前端 `analyze-sse-client.ts` 要改 URL 拼装；Server Action `analyze.ts` 的转发 URL 要改；Prism 测试 `/root/prism/api/tests/test_analyze.py`（若有）的 fixture URL 要改。此外 `project_id` 从 body 挪到 URL 之后，`RequirementAnalysisRequest` schema 要删 `project_id` / `node_id` 字段（M13 §7 schema 未显式删，对照 Prism schema `RequirementAnalysisRequest` 含 `project_id: str`）。

违反 `CLAUDE.md §项目定位` 精神（shadow 项目要"数据化验证设计前置方法论价值"——迁移成本必须被计入对照指标）。

**修复方向**：§2 "Prism 对照" 段或 §15 末段追加一条"Phase 2 迁移成本评估"：具体列需改的文件 + 预计改动行数（M13 设计侧做一次估时即可，Phase 2 实装时再验证）。同时 §7 `RequirementAnalysisRequest` schema 显式确认不含 `project_id / node_id` 字段（改为 Router 层路径参数 + Service 层入参）。

---

**R3-03 §15 accepted 后的横切补丁清单遗漏 M02/M03/M04/M07 基线补丁 + 补丁与 M13 accept 的依赖关系未声明** — 级别：**Blocker**

`00-design.md §15` accepted 后横切补丁清单仅 3 项：M04 登记 dimension_type / M15 ActionType / ADR-002 脚注。

对照 R1-01 / R2-03 发现：
- M02 需新增 `get_by_id_for_user` 返回值补齐 ai_provider/ai_api_key_enc/ai_model（若 Prism 已有列，M02 Service 层接口化缺失）
- M03 需明确 `get_by_id` 返回 Node 带 `.path` + 另外新增 `list_subtree_names(depth=2)` 或直接复用 `list_subtree` + 在 M13 层做 projection
- M04 需改 `create_dimension_record(db, ...)` / `get_latest(db, node_id, dimension_type_key)` / `list_by_node` 签名接受外部 session（R-X3）
- M07 需改/新增 `list_by_node(db, node_id, project_id, limit=20)`

**全部缺失**。且"accepted 后"的措辞表明这些补丁在 M13 accept 之后做——但 R-X3 violation 是**accept 前置条件**（tests.md E5 断言 "事务回滚：dimension_records 无残留 + activity_log 无残留（R-X3 共享 session）"——补丁不落地，E5 断言无法通过）。

**修复方向**：§15 末段分"accept 前置条件（必须先于 M13 accept）"与"accepted 后同期补丁"两组：
- **前置**：M02/M03/M04/M07 baseline-patch 完成 Service 接口新增/改签名；Alembic 迁移扩 M15 CHECK 枚举
- **同期**：M04 dimension_type 首次写入幂等 / ADR-002 脚注

---

**R3-04 ADR-002 §横切影响脚注的物理位置未指明——"M13 pilot 结论"写到 ADR-002 哪里** — 级别：Minor

`00-design.md §8` 末段："ADR-002 §横切影响遗留……M13 结论为'不扩不起，ADR-002 脚注一句话说明……' 该脚注在 M13 accepted 后由主对话补充到 ADR-002。"

对照 `ADR-002 §横切影响` 原文（L116）："M13（流式 SSE）：虽然不用 Queue，但需要'流式响应中的 chunk 鉴权'——本 ADR 不覆盖，M13 设计时另起 ADR 或扩展本 ADR"。M13 结论是"不扩不起"，但此脚注应该**替换**L116 这段原文（把"M13 设计时另起 ADR"改成"M13 pilot 已结论：流式 SSE 鉴权走 ADR-004 P1，本 ADR 不覆盖"），不是"在 ADR-002 加新脚注"。

**修复方向**：§8 末段 + §15 横切补丁清单把"脚注"改为"替换 ADR-002 L116 行"，并给出替换后原文建议。

---

**R3-05 §12A 字段 ⑥"取消机制"的 `provider.aclose()` 在 tests.md S4 断言但未在 §13 / §15 里沉淀"MockProvider 必须实现 aclose 协议"的测试契约** — 级别：Minor

`00-design.md §12A 字段 ⑥` + `tests.md S4`：断言 `provider.aclose()` 被调用 1 次。tests.md 底部 `MockProvider` 实现有 `aclose_called`——但 `ADR-001 §4 AI Provider stream() 接口` 对真实 provider（Claude/Kimi/Codex）是否**都**实现 aclose 未声明。Prism 现状 `/root/prism/api/services/ai_provider.py` 是 `AsyncIterator[str]`——AsyncIterator 协议本身有 `aclose`（PEP 533），但三方 SDK（anthropic/openai）的实际实现行为差异需要在 M13 或 ADR-001 里明确。

**修复方向**：§12A 字段 ⑥ 末尾加一行"依赖 AI Provider SDK 的 AsyncIterator 实现 `aclose()` 释放底层连接；anthropic SDK ≥0.x / openai SDK ≥1.x 均满足，M13 accept 前由主对话在 ADR-001 §4 补充 aclose 协议声明"。

---

## Blocker 总结表

| 编号 | 轮 | 标题 | 位置 | 建议修复方向 |
|------|----|------|------|-------------|
| B1 | 1 | 上游 Service 签名全部对不上 | §2 / §3 / §6 | M02/M03/M04/M07 accept 前置补丁 + M13 §2 改用已有接口 |
| B2 | 2 | §8 Server Action → FastAPI 的 P2 路径声明缺失 | §8 | 补"save/affected-nodes 走 ADR-004 P2"段 |
| B3 | 2 | §5 未声明 M04/M15 Service 接受外部 session（R-X3） | §5 多表事务列 | 补 R-X3 依赖声明 + 前置条件 |
| B4 | 3 | §12A 7 字段对 M16（🪷）不可直接复用 | §12A | 加"子模板扩展指南" + 明确 §12A 仅服务 🌊 场景 |
| B5 | 3 | §15 横切补丁清单缺 M02/M03/M04/M07 前置补丁 | §15 | 分"前置 / 同期"两组 |

## Non-blocker 统计

- **Major**：5 条（R1-02 / R1-05 / R2-02 / R2-04 / R3-02）
- **Minor**：5 条（R1-03 / R1-04 / R1-06 / R2-05 / R3-04 / R3-05——实 6 条；其中 R3-04 R3-05 均 Minor）
- **Nit**：0 条

> 复核说明：Minor 实际 6 条（R1-03、R1-04、R1-06、R2-05、R3-04、R3-05），以上 5/6 为数数误差；以本段文字为准。
