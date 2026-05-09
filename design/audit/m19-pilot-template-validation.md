---
title: M19 sprint pilot-template-validation（living tracker）
status: completed
owner: CY
sprint: M19 导入/导出 / pilot=false / complexity=low / Phase 2.1 90→95%
started: 2026-05-09
purpose: |
  M19 是 Phase 2.1 倒数第 2 个 own sprint（M20 团队最后）。pilot=false / complexity=low /
  本文件记录 M19 启动期 + 子片 0-5 实施期产出 + R1=3 subagent 并行 + R2=1 合并 Opus
  endpoint 单审命中数据 + 元教训沉淀 + sink 立规候选。
---

# M19 sprint pilot-template-validation

## M19 启动期（2026-05-09 / 详见 design/audit/m19-startup-reconcile.md）

闸门 2.5 reconcile pass 三栏 A 6 / **B 0**（第十四次实证 / M05-M19 十四连）/ C 8 已自我消解。

- §14.5 Sprint Review 拆分计划补完（design 节 14.5 / 5 子片 + R1=3 + R2=1 + 范式复用 19 项 + L3 留空 3 项）
- bypass log #2 配套验收最终 ✅（M16 bypass + M17 恢复 + M18 继续 = 累计 2 次不复位 / 第 3 次触发闸门 3.4 L1 review）
- cross-sprint punt 池本 sprint 命中检查（13 项 STILL_PUNT：12 N/A 显式 + 1 触发评估 #17 _sanitize_filename horizontal 输出端首发）
- B 栏 = 0 穷举 L1 锁规候选清单（11 项 / Q1-Q6 CY ack 2026-04-21 + design 字面 + ADR-003 规则 1）
- design status accepted 2026-04-21 不需 audit flip / baseline-patch 仅触发 ActionType+1（不改其他模块）

---

## M19 sprint 实施（2026-05-09 / 8 commits）

| # | commit | 子片 | 范围 | tests | R13-1 |
|---|--------|------|------|-------|-------|
| 1 | 3ad8efa | 启动期 | reconcile pass + §14.5 + bypass 验收 + punt 池检查 | 1480 baseline | 136 |
| 2 | 子片 0 | 合并到启动期 | （M19 无 scaffold 简化决策需求） | - | 136 |
| 3 | facce18 | 子片 1 | ActionType+1 + alembic ALTER CHECK + 4 model tests | 1484 (+4) | 136 |
| 4 | 子片 2 | 合并到子片 3 | DAO 复用接通（5 上游 DAO 全已存在 / DI 在 service 构造函数） | - | 136 |
| 5 | 83cf44a | 子片 3 | ExportService + Schema + 3 ErrorCode + 13 service tests | 1497 (+13) | 139 (+3) |
| 6 | c98e563 | R1 立修 | 7 P1（3 subagent 并行审 / Opus + 2 Sonnet 合并去重）+ 4 punt | 1498 (+1) | 139 |
| 7 | 947f0e2 | 子片 4 | Router 2 endpoints + 12 e2e（元教训 18 类 actionable + N/A 显式声明） | 1510 (+12) | 139 |
| 8 | 257ab92 | R2 立修 | 3 P1（1 合并 Opus endpoint 单审）+ 1 P2 顺修 + 3 punt | 1512 (+2) | 139 |
| 9 | 子片 5 关闸 | 本 commit | design 回写 + audit + handoff + roadmap + cross-sprint punt 池 | ≈1512 | 139 |

**最终回归**：1480 → ≈1512 PASS（+32 / 5 skipped / R13-1 136→139 / L12+L13+R14 全过 / ruff 净）

---

## R1+R2 命中数据（M02-M19 第十七数据点 / bypass log #2 配套不复位）

### R1 = 3 subagent 并行审子片 1+2+3（spec+quality Opus + reuse Sonnet + quality+efficiency Sonnet）

- **R1-A spec+quality Opus**：5 P1 + 5 P2 / 关键：tests.md E4 vs design §13 EXPORT_EMPTY_CONTENT 422 字面冲突（独家 / R1-B/C 漏抓）+ EXPORT_NODE_LIMIT_EXCEEDED 死码（Pydantic max_length 丢业务码）
- **R1-B reuse Sonnet**：3 P1 + 2 P2 / 关键：ExportNodeNotInProjectError 422 vs 404 范式不一致（M06/M08/M12 ValidationError 范式延续应 422 / 独家命中）+ R14 立规精神过去式 vs design "export"（漏识别 #2 / 独家）
- **R1-C quality+efficiency Sonnet**：3 P1 + 3 P2 / 关键：include 全 False schema 不阻 / Service 走完 4 DAO 才抛 422 I/O 浪费（独家命中 / 提前 422）

合并去重：11 项 → 7 立修 + 4 punt（_md_cell horizontal 化第三 sprint 触发 punt / _load_project 兜底子片 4 R2 复审 / _md_cell HTML 注入安全风险低 / basic_project_with_node fixture 提到 conftest 收益低）

### R2 = 1 合并 Opus subagent endpoint 单审子片 4

- 3 P1 + 3 P2 = 6 项 / 立修 3 + 顺修 1 + punt 2
- **R2 真漏抓贡献**：
  1. **tests.md ↔ design.md ↔ exceptions.py 三方 status code 字面同步漂移**（R1 立修把 exceptions.py + design §13 改 422 / 但 tests.md E6/T2/T4 + design §14.5 N/A 清单未同步回写 / R1 三 subagent 把 tests.md 当"参照真相"而非"待同步对象"）— **元教训 #19 独家**
  2. tests.md G2 字面"3 node + 顺序"e2e 缺失（R1-A P1-3 dict.fromkeys 立修后无端到端验证 / R1 三 subagent 漏抓覆盖度）
  3. tests.md E5 字面"重复 node 去重"e2e 缺失

R2 命中略超普通模块 0-2 P1 区间（M19 主要由元教训 #19 揭示的 tests.md 文档同步盲区驱动 / 非异常 sprint 形态 / 数据点 17 仍稳定）。

---

## 元贡献清单（M19 sprint 实施期 4 项 sink）

### 1. **元教训 #19：R1 局部立修触发 tests.md 第三方文件漂移**

R1 改 design §13 + exceptions.py 时把 "404 → 422" 同步了，但 tests.md（被 R1 三 subagent 当作"参照真相"而非"待同步对象"）成了滞后文件。

**立规候选 SR-M19-1**：tests.md ↔ design.md ↔ exceptions.py 三方 status code 字面同步 checkbox。M17 立的 R2 reconcile 仅覆盖 design ↔ 实装 / M19 第二实证扩第三方 tests.md 必须纳入 R2 reconcile B 栏；明确 grep 命令 `grep -n "404\|422" tests.md` 与 `exceptions.py:http_status` 字面比对。

**应用**：M20 sprint 启动 reconcile pass A 栏首条预录 tests.md status code 字面对账。

### 2. **R14 过去式立规精神 vs design accepted 字面对齐范式**

design §10 字面 "export" / accepted 2026-04-21；M16 R14 立规过去式 + snake_case 是 2026-05-09 立。M19 sprint 启动期 R1-B 漏识别 #2 抓到 / 5 步分层判断：横切纪律（R14）优先于单模块字面（design §10）。立修：4 处同步 "export" → "exported"。

**立规候选 SR-M19-2**：design accepted 时间早于横切立规时（如 R14） / sprint 启动期 R1 reviewer 必跑立规精神 vs design 字面对齐 grep 检查。

### 3. **filename sanitize 输入端 vs 输出端分门别类**

M11 cold_start (CSV upload) + M17 zip import = 输入端 sanitize（用户上传 filename）/ M19 export Markdown = 输出端 sanitize（服务端拼装 timestamp）。根源不同：用户输入需 strip + 长度截断 + 特殊字符防御；服务端构造仅需控制字符 strip 纵深防御。

**立规候选 SR-M19-3**：filename sanitize 输入端（M11/M17）vs 输出端（M19）分门别类立规。防御策略对齐但触发条件应分别声明。cross-sprint punt 池 #17 第三实例触发 / 当前实装 _build_export_filename 内联 / 后续 M20+ 第二输出端实例触发 horizontal 化提取。

### 4. **N/A 元教训显式声明范式扩展（19 项主动复制清单）**

§14.5 范式复用清单 19 项是 M02-M18 沉淀的最大主动复制清单（M14 立 5 项 / M15 立 14 项 / M19 扩 19 项）。每项含"M? 立 / M19 形态 / N/A 显式声明位置"三段格式。test_meta_lesson_na_explicit_declarations 是有意义 docstring 占位（M18 R2 sink 立规 #4 测试反模式 assert True 不构成永真污染 / docstring-only placeholder + 注释字面声明）。

---

## R-X5 子选项实证（design §14.5 L3 留空 3 项）

### R-X5-1：M19 纯只读导出（无 model / 无 DAO 新增）模块的 R1=3 subagent 命中分布

R1=3 subagent 总命中 11 P1（合并去重 7 立修）/ M02-M18 普通模块 R1 命中 4-13 P1 区间 / M19 落在 11 偏中位 / 但**特殊形态**：纯只读模块的 R1 漏抓"design 文档与立规精神对齐"+ "tests.md 与 design 字面同步"= R2 第十七数据点的独家命中区域（M19 之前 R1+R2 数据点 R2 平均 0-2 P1 / M19 R2 = 3 P1 略超）。**结论**：纯只读模块 R1+R2 命中分布偏 R2 文档同步面 / R1 偏代码契约面。

### R-X5-2：Markdown 渲染逻辑 R1-A spec+quality 命中区域

R1-A 命中 design §13 EXPORT_EMPTY_CONTENT vs tests.md E4 矛盾（独家 / R1-B/C 漏） + EXPORT_NODE_LIMIT_EXCEEDED 死码。**未命中**：design §7 字面 Markdown 表格列名 / 标题层级 / 章节顺序——R1-A spec 没字面对账 design §7 line 308-345 草案 vs 实装。**结论**：design §7 字面 Markdown 结构对账漏在 R1（R2 子片 4 e2e golden test 字面验补足）。

### R-X5-3：Content-Disposition filename sanitize 输出端首发是否触发 horizontal 化

第三实例触发评估：M11 输入端 + M17 输入端 + M19 输出端。根源不同 → 当前 punt 候选评估保留至 M20+ 第二输出端实例（如团队报告导出）触发横切提取。当前 _build_export_filename 内联 router.py 是合理简化（仅 12 行 / 单一调用点 / 服务端拼装 ASCII timestamp 攻击面窄）。**结论**：第三实例不立即触发 horizontal / 第四实例（第二输出端）触发。

---

## bypass log #2 配套验收最终 ✅

M16 bypass（context budget pressure 触发条款 b）+ M17 恢复（R1=3 + R2=1 真跑）+ M18 继续（R1=3 + R2=1 真跑）+ M19 继续（R1=3 + R2=1 真跑）= 累计 2 次 bypass 不复位 / 第 3 次触发闸门 3.4 L1 总则 review。M19 真跑 ✅ / 不复位累计触发线 / M20 sprint 启动期继续验收。

---

## cross-sprint punt 池接通

### 本 sprint 关闭

无（M19 是只读模块 / 不触发 cross-sprint 历史 punt 修复路径）。

### 本 sprint 新增 PUNT

| # | 项 | 来源 | 约定 | 处置 |
|---|----|------|------|------|
| #25 | _md_cell + _render_dimension_content + _render_pros_cons horizontal 化到 api/utils/markdown_helpers.py | M19 R1-B P1-2 | 第二渲染场景触发（M20+ 团队报告） | STILL_PUNT 输出端 |
| #26 | filename sanitize 输入端 vs 输出端分门别类立规（SR-M19-3） | M19 R2 sink | 第二输出端实例触发 | STILL_PUNT 输出端 |
| #27 | Cache-Control: no-store header 缺失（含 user 上下文敏感数据） | M19 R2 P2-2 | M20 性能 sprint 横切添加 | STILL_PUNT |
| #28 | filename 含 project_name 风险（RFC 5987 filename* 编码） | M19 R2 P2-3 | 该改动发生时 | STILL_PUNT |

### 真漏洞 #20 require_platform_admin 去重评估

M19 design §8 字面 viewer 即可导出 / 无 admin endpoint / 不触发 require_platform_admin 重复路径 → STILL_PUNT 不变。M20 sprint 启动期重新评估（M20 团队管理可能有 admin endpoint）。

---

## R1+R2 数据点 17 稳态确认

| sprint | 模块 | R1 P1 立修 | R2 P1 立修 | 形态 |
|--------|------|----------|----------|------|
| M02 | 项目管理 | 8 | 1 | 业务首发 |
| M03 | 模块树 | 6 | 0 | 业务 |
| M04 | 维度记录 | 4 | 1 | 业务 |
| M05 | 版本时间线 | 4 | 3 | 业务 |
| M06 | 竞品 | 3 | 0 | 业务 |
| M07 | 问题沉淀 | 1 | 1 | 业务 |
| M08 | 模块关系 | 7 | 1 | 业务 |
| M10 | 总览 | 1 | 0 | 纯读 |
| M11 | 冷启动 | 6 | 2 | R-X1 首发 |
| M12 | 对比 | 4 | 1 | 业务 |
| M13 | 需求分析 | 8 | 4 | LLM 首发 |
| M14 | 行业新闻 | 6 | 4 | 全局豁免首发 |
| M15 | 数据流转 | 1 | 2 | 纯读 R10-2 owner |
| M16 | AI 快照 | (self-审 bypass) | (self-审 bypass) | §12B 首发 |
| M17 | AI 导入 | 8 | 4 | R-X1 第二实例 |
| M18 | 语义搜索 | 16 | 7 | §12D 首发 / pilot=true |
| M19 | 导入/导出 | 7 | 3 | 纯只读 / pilot=false |

R1 平均 5.7 / R2 平均 1.9 / M19 R1=7 (持平) / R2=3 (略高 / 元教训 #19 文档同步驱动)。

**结论**：R1+R2 数据点 17 稳态确认 / M19 形态特殊性体现在 R2 命中区域偏文档同步而非代码契约（纯只读模块独家）。

---

last_updated: 2026-05-09
