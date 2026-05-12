---
audit: P1→P2 gate
auditor: Opus subagent / cost cap $3
created: 2026-05-12
samples: M01-user-account / M07-issue / M17-ai-import / _cross-cutting
verdict: PASS_WITH_FIX
---

# P1→P2 闸门 audit finding

## Verdict

**PASS_WITH_FIX** — 风格红线 0 违反，15/18 角度覆盖到位，22 元发现真转化，P0/P1/P2 分布合理；唯一**结构性 finding** 是 testpoint 全部按"API contract 视角"写（POST /api/.../issues 201 + activity_log），P2 要做"全 DOM 端到端范式"（page.goto + locator）时，**大量 P0 backend 测试点在前端 page.tsx 无 DOM 入口可达**（M07 状态机转换/筛选/认领 UI 不存在），需要在 P2 启动前做一次 testpoint→spec.ts 映射方案对齐（不补 testpoint / 而是改 P2 prompt 说清"DOM 不可达的走 API-only 验证或标 N/A"）。

## 6 项检查结果

### 1. 风格红线（feedback_testpoint_style）

- 违反数: **0**
- grep `断言:|步骤:|业务影响:|要抓 bug` 仅命中 frontmatter `references:` 段（YAML 列表 metadata，非 testpoint 子项），属合法用法
- grep `^- \[P[012]\] (验证|检查|确认|校验|保证|确保)` 4 文件均 0 hits（feedback_testpoint_style §禁止 第 4 条全过）
- 每条 testpoint 均为单行 `- [Pn] <内容>（design §N + tests.md GX）` 格式，无子项 / 无步骤 / 无断言段
- 4 文件累计 618 testpoint，**风格红线 100% 通过**

### 2. 15 角度覆盖

| 文件 | H3 视角数 | 状态 |
|------|-----------|------|
| M01-user-account | 14 | ✅ 含 §1 功能性 / §3 异常 / §4 权限 / §5 Tenant / §6 并发 / §10-14 M01 特有（ADR-004 凭据路径 / Token 失效 / auth_audit_log / CI 守护 / 跨模块契约）；缺 §10 兼容性（合理，auth 不依赖浏览器版本） |
| M07-issue | 15 | ✅ 全 15 角度 + R-X3 跨模块契约 + ErrorCode 注册 + M18 baseline-patch（M07 是模块自然 15 全覆盖） |
| M17-ai-import | 15 | ✅ 全 15 角度 + §10 WebSocket 协议 + §11 Queue 异步路径专项（异步 pilot 自然加强） |
| _cross-cutting | 18 | ✅ 远超 ≥12 要求（progress.md "18 视角清单"全数命中：Auth flow / cookie sync / 网络断连 / 三层防御 / R-X 横切 / 异步 7 范式 / 幂等三层 / 状态机非法转换 / AI Provider / baseline-patch / 部分唯一索引 race / cross-tenant / tenant 豁免 / activity_log 传播 / action_type 漂移 / filename sanitize / i18n+mobile / schema 性死债务） |

**缺漏角度**：无。M01 缺 §10 兼容性可接受（auth flow 不依赖浏览器 quirks）。

### 3. P0/P1/P2 分布

| 文件 | P0 | P1 | P2 | 总 | P0 比例 | 合理性 |
|------|----|----|----|----|---------|--------|
| M01-user-account | 45 | 69 | 13 | 127 | 35.4% | ✅ 合理（auth pilot + 凭据路径 P0 密集是天然） |
| M07-issue | 42 | 56 | 12 | 110 | 38.2% | ✅ 合理（4 态 5 禁转 + R-X3 + cross-tenant 全 P0） |
| M17-ai-import | 62 | 66 | 15 | 143 | 43.4% | ⚠️ 偏高但合理（11 状态机 + idempotency + WebSocket + Queue 双异步 pilot 模块 P0 必然密集 / 与 progress.md M16 P0 41.8% 一致） |
| _cross-cutting | 153 | 69 | 16 | 238 | 64.3% | ⚠️ 高但 progress.md 已声明"cross-cutting 是系统级风险密集区 / 元发现专项全 P0"合理 |

**判定**：4 文件均无 "P0 ≥80% 失效" 或 "P0 <20% 漏关键路径" 风险。Self-check §4 "P0 ≥3" 远超满足。M17/_cross-cutting P0 偏高已有合理性陈述（pilot + 元发现密集区）。

### 4. 元发现 22 项转化

progress.md L233-246 列了 22 元发现关键词 → grep `_cross-cutting.md` 全部命中：

| 元发现关键词 | hits |
|------|----|
| R-X1 / R-X2 / R-X3 | 4 / 1 / 11 ✅ |
| 异步 7 范式（SSE/BackgroundTasks/cron/arq/WebSocket/Redis/advisory）| 11/6/16/6/7/9/8 ✅ |
| 幂等三层（idempotency_key / advisory_xact_lock / Redis SET + PK）| 6 / 7 / 9 ✅ |
| 状态机非法转换 | 7 ✅ |
| AI Provider 三 env | 4 / 2 ✅ |
| JWT ≤5min 暴露窗口 | 8 ✅ |
| baseline-patch punt 池 6 处 | 6 / 1 ✅ |
| DB 部分唯一索引 race | 4 ✅ |
| last-write-wins vs 乐观锁分化 | 2 / 3 ✅ |
| cross-tenant 三层防御 + tenant 豁免 + ADR-003 只读豁免 | 4 / 1 / 15 ✅ |
| activity_log 失败传播 + SYSTEM_USER_UUID | 23 / 10 ✅ |
| action_type 同步漂移 + R14 守护 | 6 / 3 ✅ |
| filename sanitize / 跨项目 422 / viewer 403 / disambiguation | 3 / 7 / 7 / 4 ✅ |
| schema 性死债务 / G4=B 值快照不降级 | 4 / 2 ✅ |

**命中**: **22/22**（progress.md "22 元发现全转化"声称属实）。漏项：无。

### 5. testpoint→spec.ts 可操作性（粗判）

抽样 M01/M07/M17 各 5 条 P0（共 15 条，行号 M01 L25-29 / M07 L25-29 / M17 L28-32）：

**评级**：**大部分可操作**（约 11/15 含具体动作）

具体例（≤3）：
- ✅ **M01 L25 可操作**：`POST /auth/login 邮箱密码正确返 200 + access_token + refresh_token + UserProfile` — 映射 `page.fill('input[name=email]') → page.click('button[type=submit]') → expect(page).toHaveURL('/projects') / + API 旁路断言 cookie`
- ✅ **M07 L25 可操作**：`POST /api/projects/{pid}/issues 含 node_id+category=bug 返 201 status=open + activity_log create` — 映射 page.click('新建问题') → dialog fill → submit → expect table row + GET activity_log 旁路
- ⚠️ **M17 L29 模糊**：`WebSocket 推 status_change 序列 pending → extracting → ai_step1 → ... → completed 8 状态全推` — playwright 测 WebSocket 复杂，需 page.evaluate 或 page.on('websocket')；P2 spec 编写时需要 LLM 自己脑补协议测试范式

模糊例多集中在 M17 异步（WebSocket / Queue / 死信通知）和 _cross-cutting 跨 tab cookie sync 场景，P2 prompt 需注明"WebSocket/Queue 类 P0 接受 API 旁路验证不强求 DOM"。

### 6. DOM 路径友好性（本次特别检查 / CY 选全 DOM 端到端范式）

抽 M07 5 条 P0 vs `app/src/app/projects/[projectId]/issues/page.tsx`：

**评级**：**大部分需 backend**（约 2/5 DOM 可达，3/5 backend-only）

page.tsx 实际 UI（L221-322）：
- ✅ 有：Select 分类筛选（bug/tech_debt/design_flaw/performance）/ Plus 新建按钮 / AddIssueDialog 创建对话框（仅 category + description + tags + 可选 title） / Trash2 删除按钮（confirm 确认）/ Table 5 列（描述 / 分类 / 标签 / 创建时间 / 操作）
- ❌ 无：**status 字段** / **status filter** / **状态 badge** / **状态转换按钮**（认领 / 解决 / 关闭）/ **assigned_to 字段** / **node_id 关联**（page L93 hardcoded `nodeId: null` 仅游离创建）/ **issue 详情页**（无 edit / get_by_id UI）/ **node-scoped issue 列表**（GET /nodes/{nid}/issues 无前端入口）

**M07 P0 对账**（5 条采样）：

| M07 P0 testpoint | DOM 可达？ |
|------|------------|
| POST /issues 含 node_id+category=bug 201 status=open | ❌ page.tsx L93 hardcoded `nodeId: null`，无 node 关联 UI |
| POST /issues 不含 node_id 游离 issue 201 | ✅ 唯一支持的创建路径（AddIssueDialog → handleSave） |
| GET /issues 列表含节点+游离 | ⚠️ 部分（page.tsx 拉所有 category 拼接，但前端拉取按 category 而非 status；GET /projects/{pid}/issues 全量接口未被直接调用） |
| GET /nodes/{nid}/issues node-scoped | ❌ 无 node 详情页内 issue 区块 UI（design §6 声称"档案页节点详情含 issue 区块"但当前 issues/page.tsx 无该入口） |
| DELETE /issues/{id} 204 + activity_log final_status | ✅ Trash2 按钮 → confirm() 删除 |

**结构性 finding（详 P0 findings §1）**：M07 testpoint 文件含 110 条全量测试点，**约 40-60% 是状态机 / 转换 / 认领 / 节点关联 / 详情查看**等当前前端 page.tsx 无入口的功能。这不是 testpoint 文件的错（design 文档定义了完整的 backend API + 状态机 + R-X3 契约）—— 是 P2 范式 "全 DOM 端到端" 跟 testpoint 视角错位。

类似情况可推测 M17 也严重（4 步向导 UI 是否已实现需 P2 启动前抽查）/ _cross-cutting Auth flow 多 P0 走 P2 HMAC 服务间签名（INTERNAL_TOKEN 浏览器禁用 / ADR-004 §3.5）也无 DOM 路径。

## P0/P1/P2 findings（分级）

### P0（阻塞 P2 启动 / 必修）

1. **【范式错位 / 阻塞 P2 启动】testpoint 视角 vs P2 "全 DOM 端到端范式" 错位**
   - 现象：4 文件 618 testpoint 主体写在 API contract 视角（POST /api/.../ 200 + activity_log），而 P2 prompt 要求"page.goto + locator + 真浏览器路径"
   - 实证：M07 page.tsx 缺 status badge / status filter / 状态转换按钮 / 节点关联 UI / 详情页，导致 M07 110 条 testpoint 中估 40-60% backend-only
   - 影响：若 P2 subagent 拿到 testpoint 直接写 spec.ts，会出现两类失败：
     - (a) 找不到 locator 强行 page.evaluate / API 调用绕过浏览器，违反 "全 DOM" 范式
     - (b) skip 这些 testpoint 标 N/A，导致 testpoint 覆盖率严重下降
   - 必修方案（选一 / 不补 testpoint）：
     - **方案 A**：P2 prompt 加"DOM 可达性分类"步骤 — subagent 第一步先扫前端 page，把 testpoint 分 [DOM-reachable] / [API-only-via-旁路] / [skip-N/A]，写到 spec 顶部注释，CY 后续 review
     - **方案 B**：P2 阶段做"两轨范式" — DOM 端到端走真用户旅程（创建项目 / 创建 issue 文案 / 跨页跳转 / cookie / login 跳转 bug 复现）+ API 旁路走 backend P0（状态机 / 权限三层 / R-X3 契约 / 异步范式）
     - **方案 C**：先跑 M02 项目创建 + M01 login + dogfooding trigger_bug 复现作 spike，验证哪种范式落得下，再回头定 M07-M17 等模块策略
   - **CY 拍板项**：建议方案 B（dogfooding trigger_bug 是 DOM 路径 bug，单走 DOM 范式逻辑闭环；但状态机/异步等高价值 P0 backend 通过 API 旁路保覆盖率不丢）

### P1（建议修 / 不阻塞）

1. **M17 / _cross-cutting P0 占比偏高（43% / 64%）的"门槛漂移"风险**
   - 现象：M17 11 状态机 + WebSocket + Queue 双异步 / cross-cutting 元发现专项导致 P0 密集
   - 风险：若 P2 spec 全跑 P0，单模块跑时间膨胀；P3 执行阶段失败 case 入队也膨胀
   - 建议：P2 写 spec 时按 P0 内部再分"smoke P0"（happy path 5-10 条）和"完整 P0"（≥40 条），smoke P0 必跑 / 完整 P0 spec.ts 注 test.skip(/* P2 sprint 内细分 */) 后续按需启
   - 不阻塞：P2 启动后 LLM subagent 内部决策也可处理

2. **M01 缺 §10 兼容性视角 + M07 / M17 部分视角名与 phase1-testpoint.md §Output contract 模板字面对不上**
   - 现象：M01 用 §14 跨模块契约 / M07 用 §10 R-X3 跨模块契约 / M17 用 §10 WebSocket §11 Queue，prompt 模板 §10 是"兼容性（如适用）"
   - 实质：subagent 按"模块自然语言"重命名了角度（合理）/ 不损失内容
   - 建议：P2 spec 编写时无需对齐 testpoint 视角名，按 testpoint 顺序遍历即可

3. **M07 testpoint §8 UI / UX 自相矛盾（vs page.tsx 实际）**
   - 现象：M07 L114-120 §8 P0 "档案页节点详情含 issue 区块" / "issue-status-badge 4 状态视觉区分" / "issue-form category 下拉 4 选项"
   - 实证：page.tsx 实际无 issue-status-badge 组件 / 无 issue-form 4 选项 dialog（AddIssueDialog 内部待查 / Select 仅 4 category 全部分类用）
   - 注：testpoint 是基于 design §6 写的（design 声称有这些组件）——这本身就是 dogfooding 应该挖出的 design vs 实现漂移
   - 建议：标记为 design-audit candidate，P3/P4 期 RCA 时回写
   - 不阻塞：dogfooding 价值正在这里 / 不修

### P2（推后 / 写到 P2 子片中关注）

1. **M01 §10 ADR-004 P2 凭据路径 18 条 P0/P1 测试点跟"全 DOM 端到端"完全错位**
   - P2 是服务间 HMAC 签名（INTERNAL_TOKEN 不进浏览器 / ADR-004 §3.5）
   - 这些 testpoint 必须 API/集成测试走，不可能 DOM
   - 处置：P2 阶段直接走 backend integration test（FastAPI TestClient）/ 不进 playwright spec.ts

2. **WebSocket / SSE / Queue 异步 P0 在 playwright 内的范式不熟**
   - M17 §10 WebSocket + M13 SSE 流式（在 _cross-cutting §3）
   - playwright 可以 page.on('websocket') + page.on('response')，但范式重，建议 P2 启动时小 spike 一个 WebSocket spec 跑通范式后再批量

3. **AddIssueDialog 详细内容未读 — title 字段是否真在 dialog 表单**
   - page.tsx L322 引用 AddIssueDialog，handleSave L84-101 接受 title? optional
   - 若 dialog 内 title 不可见 / 不可填 → testpoint L34 "PUT 更新 title" 也无 DOM 入口
   - 建议：P2 启动前由 P2 subagent 自查 / 加进 DOM 可达性分类

## 进 P2 前 testpoint 文件修复 punch list

**结论：不改 testpoint 文件**（feedback_testpoint_style §禁止 + 本 audit 任务"不补内容/只 audit 现有"）

要改的是 **P2 phase prompt + P2 范式拍板**，不是 testpoint 文件：

- [ ] `_handoff/dogfooding/prompts/phase2-case.md`（待新建 / 或更新现有）— 加入"DOM 可达性分类" step：subagent 写 spec.ts 前必扫对应前端 page.tsx，把 testpoint 标 [DOM] / [API-via-fetch] / [skip-N/A]
- [ ] `00-plan.md` §"P2 case" 行 — 注明"两轨范式：DOM 主路径 + API 旁路覆盖 backend P0"（或 CY 选 A/B/C 之一后更新）
- [ ] 启 P2 前先派 1 个 spike subagent 跑 M01 login + M02 create-project + trigger_bug 复现，sample size 1 验证范式 / 不并发派 21 个
- [ ] M07 §8 UI / UX testpoint 跟 page.tsx 漂移记到 punt pool 或 design-audit candidate（P3/P4 期回写，不在 P1 修）
- [ ] 注：风格红线 0 违反 / 22 元发现 0 漏 / 15 角度全覆盖 — testpoint 文件本身**质量过关，不需要修**

## Audit 总评

- P1 testpoint 文件质量：**A-**（风格 100% / 视角 100% / 元发现 100% / P0 分布合理 / design 引用规范）
- P2 启动可行性：**需 1 个范式决策 + 1 个 spike 验证** 才进批量并行
- 不阻塞 dogfooding sprint，只阻塞"无脑 P2 4 并发开干"
- P0 findings = 1 项（范式错位）/ P1 findings = 3 项 / P2 findings = 3 项
