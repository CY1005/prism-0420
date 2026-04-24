---
title: M13 pilot fix 独立复审
status: draft
owner: verify-agent
created: 2026-04-25
batch: pilot-4
modules: [M13, M04]
verifies_commit: ba97381
---

# M13 pilot fix 独立复审

> **立场**：独立验证主对话对 reviewer audit 发现的修复质量。对驳回保持更高怀疑。只读设计文件，不动 commit。

## 总体结论

修复整体**方向正确、质量偏高**——5 Blocker 中 4 个完整修复（B1 部分修复），10 条 non-blocker 中多数落地；M04 baseline-patch 真实存在且签名对齐；主对话对 reviewer M15 部分的驳回**合理成立**（M15 §5/§10 明文纯读，M13 复用 M04 `create` 事件 + target_type=`dimension_record` 确实可以避开 M15 CHECK 枚举扩增与 Alembic 迁移）。

但仍有 **1 个 🟡 Partial（B1 §5/§9 遗留旧方法名）** 和 **1 个 ❌ Unfixed（R3-03 B5 前置条件缺 M03 基线补丁声明）**——建议精修一版再进 CY 复审，工作量 <10 分钟。

---

## 逐条复审（按 audit-report 原编号）

### Blockers

**B1 / R1-01 上游 Service 契约对齐** — **🟡 Partial**

- ✅ §2 "依赖契约"段 L116-131 已按上游真实接口重写：M02 `get_by_id_for_user`、M03 `get_by_id` + `list_subtree(depth=2)`、M04 `list_by_node / create_dimension_record（新增）/ get_latest（新增）`、M07 `list_by_project(node_id 过滤)`——全部对得上各模块 §6 对外契约。
- ✅ §3 上游依赖表 L159-165 同步改成新签名。
- ❌ **§5 多人架构表 Tenant 行 L267** 仍写 `self.node.get_node_with_path(project_id, node_id, user_id)`——旧方法名漏改，与 §2/§3 矛盾。
- ❌ **§9 DAO tenant 过滤 L468-471** 仍通篇引用旧方法名（`get_project_ai_config` / `get_node_with_path` / `list_dimension_records_for_node` / `list_issues_by_node`）——4 处全部未随 §2/§3 更新。
- ❌ **tests.md T2 L159** 也漏改 `node_service.get_node_with_path(P1, N2)` / R4 L369 漏改 `get_latest_dimension_record`。

**影响**：Phase 2 实装按 §5/§9/tests 去找接口仍会找不到；这正是 reviewer 原 Blocker 的痛点再现。**需再精修一轮**。

---

**B2 / R2-01 §8 P2 路径声明** — **✅ Fixed**

- §8 权限表 L421 "Server Action（save / affected-nodes）" 行明确：`fetch(FastAPI_URL, { headers: { 'X-Internal-Token', 'X-User-Id', 'X-Internal-Timestamp', 'X-Internal-Signature': HMAC-SHA256(...) } })`；显式引 **ADR-004 §3.2 签名材料 + §核心 5 项第 2 点**，凭据路径标 **P2 Internal HMAC**。
- L422 流式行显式 P1 Bearer JWT + 绕过 Server Action 理由。
- L423 Router 行 `require_user` 自动 P1+P2 合并 + `check_project_access`。
- 与 ADR-004 L38-39 / L99-104 的 P1/P2 定义完全一致，无漂移。

---

**B3 / R2-03 §5 R-X3 依赖声明** — **✅ Fixed（驳回 M15 部分合理，见末节）**

- §5 多表事务列 L268 已补：`with self.db.begin():` 包 `M04.create_dimension_record(db, ...)`；显式声明依赖 M04 Service 接受外部 session，并括注 "M04 pilot 基线补丁已满足 `create_dimension_record(db, ...)` 签名"。
- §15 accept 前置条件 L721 勾了 M04 baseline-patch（已完成）。
- M15 部分（reviewer 原要求改 M15 ActivityService 签名）被主对话驳回——**驳回合理**（见末节独立复审）。

---

**B4 / R3-01 §12A 子模板适用范围** — **✅ Fixed**

- §12 开篇 L542 新增 "**§12A 适用范围（决策 2 ack A，2026-04-25）**"段：明确 "**仅服务 🌊 流式 SSE 场景**；字段语义与 §12C Queue payload schema **粒度对等（都 7 字段）** 但**字段语义不通用**"；显式点名 M16 / M18 另起 §12B/§12C 不复用 §12A。
- §12A 与 §12B/§12C 对比表 L602 保留——**验证合理**：此对比表仍有价值（展示 3 形态维度对照），未造成"M16/M18 照抄 §12A"误导，且主对话已在 §12 开篇声明粒度对等而非字段通用。
- grep M13 全文无 "§12A 子模板供 M16/M18 照抄" 类混淆表述。

---

**B5 / R3-03 §15 accept 前置条件列表** — **🟡 Partial**

- ✅ §15 拆分 "accept 前置条件 / accepted 同期补丁" 两组（L719-729）——结构到位。
- ✅ M04 baseline-patch 列出（已勾完成）。
- ✅ M07 baseline-patch（list_by_project 加 node_id 参数）列出——对齐 M07 §6 实况（M07 §6 L270 的 `orphan_by_node_id` 已有；`list_by_project` DAO 已支持 node_id 参数——参 M07 §9 L368-384，故 **M07 这项其实已无需 baseline-patch**，§6 对外契约签名若已暴露 node_id，此前置条件可以删掉或降级为"仅 §6 对外契约表追加一行签名声明"）。
- ❌ **M03 baseline-patch 缺失**：reviewer R3-03 原明确要求 "M03 需明确 `get_by_id` 返回 Node 带 `.path` + 另外新增 `list_subtree_names(depth=2)` 或直接复用 `list_subtree` + 在 M13 层做 projection"——M13 §2 L122 现采用后者（复用 `list_subtree` + M13 层 projection），这**本身免了 M03 基线补丁**，但 §15 前置条件清单应显式声明"M03 无需 baseline-patch（采取 §2 项目化策略）"——现 §15 L719-724 完全不提 M03，读者会困惑"reviewer 说要 M03 补丁，现在没了？是漏了还是驳回了？"。
- ❌ **ADR-002 L116 替换**在 §15 前置条件（L724）被列为 accept 前置——但 §8 末段 L440-444 已把替换后原文写出。"前置"与"同期"归类不准：ADR-002 替换既可前置也可同期，既然原文已备妥，建议降级到"同期"或合并声明一句"文本已备妥（§8 末段），accepted 当日提交即可"。

**影响**：不挡主干；但 CY 复审时可能纠结 "M03 到底改不改"。

---

### Major

**R1-02 §3 M02 访问方式命名** — **✅ Fixed**

- §3 依赖表 L161 已改为 "Service `get_by_id_for_user`（读 ai_provider / ai_api_key_enc / ai_model）"，对齐 M02 §6 实况；ADR-003 规则 1 引用保留。

**R1-05 `AnalysisProviderError` 分裂** — **✅ Fixed**

- §13 L622-623 新增 `ANALYSIS_PROVIDER_NOT_CONFIGURED`（422）与 `ANALYSIS_PROVIDER_ERROR`（503）分列；L636-644 对应两个 AppError 子类；R13-2 L671-672 wrap 规则分别声明。
- tests.md E7 L277-282 断言 `error_code="ANALYSIS_PROVIDER_NOT_CONFIGURED"` 并**显式对比 E1**（`ANALYSIS_PROVIDER_ERROR`）说明前端差异化 UX——比 reviewer 要求还多一步。

**R2-02 流式 DB session 占用** — **✅ Fixed**

- §5 并发列 L270 末段新增 "**流式 DB session 释放策略**"：① 在 `async for chunk` 开始前完成所有上游 Service 调用并释放 db session；② 流式循环内不持 DB 连接；③ save 由前端新起请求另开 session——与 reviewer R2-02 修复方向逐条吻合，显式点名 "Postgres pool 10-20，5 并发流式即可打满的风险"。

**R2-04 前端防抖兜底** — **✅ Fixed**

- §6 Component 层 L293 描述新增 "保存按钮防抖（点击后立即 disabled；同一 full_result 的 SHA256 hash 在本抽屉生命周期内不允许二次 save）"。
- tests.md 新增 C3b `[E2E]` 场景 L130-136，网络面板只 1 次 `/analyze/save` 请求 + SHA256 重放拒绝断言——覆盖面完整。

**R3-02 Phase 2 迁移成本** — **✅ Fixed**

- §2 L133-145 新增 "Phase 2 Prism → prism-0420 迁移成本" 表格，5 差异点 + 每项预计改动行数（总 ~100-150 行）。
- `RequirementAnalysisRequest` schema §7 L335-337 已删 `project_id / node_id` 字段（只留 requirement_text + analysis_level）——与 Prism 对照 reviewer 要求一致。
- **独立核对**：Prism `/root/prism/api/routers/analyze.py` 实际 496 行，M13 估算 "3 文件 / ~30-50 行" 是局部改动（不是整文件重写），估算**合理**。

---

### Minor

**R1-03 §3 R3-4 适用范围措辞** — **✅ Fixed**
- §3 L220 首句已改为 "M13 §3 采用 R3-5 纯读聚合规范（ADR-003 规则 1），无 ⚠️ 待决；R3-4 不强适用，下方成本块为 CY Q2 ack 决策的可逆性留痕"——精确对齐 reviewer 建议文字。

**R1-04 `SaveAnalysisResponse` + `analysis_saved_at`** — **✅ Fixed**
- §7 L348-351 `SaveAnalysisResponse` 增 `analysis_saved_at: str` （ISO 8601 + 注释便于前端立即更新 affected-nodes）；tests.md G1 L37 断言 `analysis_saved_at` + L40 断言 "response 的同一时间戳"——闭环。

**R1-06 §10 R10-2 Alembic 迁移** — **🔵 Rebutted-Valid（见末节）**

**R2-05 JWT 自然过期 vs 主动作废** — **✅ Fixed**
- §8 "流式期间的连接级 auth 一致性" L449-452 显式分 (a) JWT 自然过期（与 ADR-004 一致，不是脱节）/ (b) token 主动作废（ADR-004 §5 `token_invalidated_at`）两种；(b) M13 明确接受 ≤5min 暴露窗口为已知决策。
- tests.md P8（自然过期，明确标记"不是脱节"）/ P9（P9a 流前作废拒建 + P9b 流中作废接受脱节）分拆覆盖——比 reviewer 要求更细。

**R3-04 ADR-002 替换而非加脚注** — **✅ Fixed**
- §8 末段 L440-444 明确 "**替换** ADR-002 L116 原文"；给出替换后原文建议 "M13 pilot 已结论——流式鉴权走 ADR-004 P1……本 ADR 不覆盖"；并加括号说明 "不加脚注，直接替换正文——ADR 演进由事实结论收口"——对齐 reviewer 建议。

**R3-05 AsyncIterator aclose 协议声明** — **✅ Fixed**
- §12A 字段 ⑥ L590 补 "依赖 AI Provider SDK 的 AsyncIterator 实现 aclose，anthropic ≥0.x / openai ≥1.x 满足；MockProvider 必须实现 aclose_called 标志"；§15 accept 前置 L723 勾 "ADR-001 §4.1 补一句……MockProvider 必须实现 aclose_called 断言标志"。
- tests.md S4 L310 + E3 L255 都断言 `provider.aclose()` 被调用——闭环。

---

### 主对话驳回的复审（独立判定）

**M15 相关驳回（R1-06 + R2-03 B3 M15 部分 + R3-03 B5 M15 部分）** — **🔵 Rebutted-Valid**

**独立读 M15 原文**：
- M15 §5 多表事务列（/root/workspace/projects/prism-0420/design/02-modules/M15-activity-stream/00-design.md:312）："M15 纯读，无写操作，无事务需求……写入 activity_log 的动作归属各业务模块（M02/M03/M04 等）的 Service 层事务，M15 仅消费已写入的数据"——主对话引用准确。
- M15 §10 事件清单（L505-519）：开头就是 "**M15 无 activity_log 事件**"；显式列出 "M04 Service：写 `create_dimension_record` / `update_dimension_record` 等事件"——**主对话引用准确**。

**独立读 M04 原文**：
- M04 §6 对外契约 L265：`create_dimension_record(...)` "写一条 `create` activity_log 事件（target_type=`dimension_record`, target_id=<新建 id>, metadata 含 `{node_id, type_id, content_size, dimension_type_key}` + 调用方传入的 `extra_activity_metadata` 合并）；**M13 的"1 条 save 日志"就由此方法代写，M13 自身不直写 activity_log**"——M04 baseline-patch 真的把代写职责写明了，语义完整。
- M04 §10 L411-415 `create` / target_type=`dimension_record` 事件本就存在——M13 完全复用 M04 既有 action_type + target_type。
- M15 §3 CHECK constraint L179-194 `action_type IN ('create'...)` + `target_type IN ('dimension_record'...)` 均已含 M13 需要的枚举值——**无需 Alembic 迁移**，驳回 R1-06 正确。

**M04 一次调用是否真的只写 1 条 activity_log？**
- M04 §10 L411-415 只列 `create/update/delete` on `dimension_record`——没有任何 `create` on `dimension_type` 事件；虽 M04 `create_dimension_record` spec（§6 L265）说 "按 dimension_type_key 在 dimension_types 表 upsert 对应 id"，但 M04 §10 事件清单未给 `dimension_types` 相关事件——说明 upsert 是配置字典的幂等登记，**不产生业务审计事件**。M13 Q6 ack "只 save 写 1 条"成立。✅

**M13 §10 metadata 过滤语义是否对 M15 UI 足够？**
- M15 DAO `ActivityStreamDAO.list_stream`（L238-283）接受的过滤参数：`user_id / action_type / target_type / from_dt / to_dt`——**不支持按 `metadata.dimension_type_key` JSONB 子字段过滤**。
- 这意味着 M15 列表页目前**拿不到"只看 M13 需求分析行为"的精准过滤能力**——最多能按 `target_type="dimension_record"` 过滤到全部维度记录事件，再按 summary 字符串/metadata 展开才能人工区分。
- **但这不构成驳回的 blocker**：M13 §10 L520 原文 "M15 UI 侧需要理解 metadata.dimension_type_key 字段以在时间线展示需求分析图标 / 标签（M15 UI 层增强，不涉及 schema）"——M13 明确把 "按需求分析精准过滤"归为 M15 UI 未来增强（上 JSONB GIN 索引 + DAO 加过滤参数）而非 M13 pilot 期需交付。M15 §3 model 的 metadata 字段是 JSONB（L213），未来加 DAO 过滤参数改动范围是 M15 内部，不回灌 M13。
- **反驳触发条件不成立**：若 CY 业务场景确实需要"M15 列表里一眼挑出 M13 分析行为"，可以在 M13 accepted 同期补丁里把 "M15 DAO 增 dimension_type_key 过滤参数 + JSONB GIN 索引" 登记为 M15 小 patch——但这不该作为 M13 的 accept 前置条件。

**结论**：M15 部分驳回在架构契约层面**完全合理**——M13 没把任何写操作压到 M15 头上，也没依赖 M15 改 schema。若驳回错了会发生什么？会：① M15 被要求增一个 `ActivityService.log()` 写接口（违背 M15 §5/§10 纯读决策）；② Alembic 迁移扩 action_type/target_type CHECK 枚举（但 M13 真实用的 `create` + `dimension_record` 都已在枚举里，改是白改）。故 **reviewer 这几条基于"M13 会写新 action_type"的前提已被主对话通过"复用 M04 既有事件"消解**。

---

## 副作用扫描（audit 外发现）

独立扫描主对话 ba97381 fix 可能引入的新问题：

1. **§5/§9 旧方法名遗留**（见 B1 Partial）——已列为阻塞项。

2. **tests.md 旧方法名遗留**（T2 L159 `get_node_with_path` / R4 L369 `get_latest_dimension_record`）——同 B1 Partial 批次，建议一并扫改。

3. **§10 "只 1 条" 精神核对**：§10 L487 "仅 save 写 1 条（由 M04 Service 代写）"——已确认 M04 `create_dimension_record` 的 `dimension_types` upsert 不产生 `create`/target_type=`dimension_type` 事件（M04 §10 未登记）。✅ 不引入第 2 条 activity_log。

4. **§15 前置条件顺序无循环依赖**：L720-724 四项（M04/M07 基线补丁 + ADR-001 §4.1 补一句 + ADR-002 L116 替换）互不依赖——可任意顺序提交。✅

5. **M03 baseline-patch 从"reviewer 要求"到"无需"的静默变化**未在 §15 声明（见 B5 Partial）——建议 §15 加一行 "M03 无需 baseline-patch（§2 采取 `list_subtree` + M13 层 projection 策略，绕开 `list_subtree_names`）"。

6. **M07 baseline-patch 可能已冗余**：M07 §6 `list_by_project` DAO L368-384 已暴露 `node_id` 参数。若 M07 §6 对外契约（而不仅是 DAO）也已含 node_id，本 baseline-patch 可以删除；若仅 DAO 有、对外 Service 签名未显式暴露，则保留为"签名声明性补丁"（不改实装）。建议精修时核对 M07 §6 Service 层契约行再定。

---

## 阻塞项

**必须再修才能进 CY 最终复审**：

1. **🟡 B1 残余**：M13 §5 L267 / §9 L468-471 的 4 处旧方法名；tests.md T2 L159 / R4 L369 的 2 处旧方法名——共 6 处一次性扫改。

2. **🟡 B5 残余**：§15 前置条件清单补一行 "M03 无需 baseline-patch"；建议把 ADR-002 L116 替换从"前置"降到"同期"（原文已备妥，accepted 当日提交即可）。

**非阻塞但建议**：

3. 核对 M07 §6 对外契约签名是否已含 node_id 参数，若已含则 §15 前置条件里的 M07 那项可删。
