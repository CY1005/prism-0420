# 模块详细设计（C 档）

按 16 字段模板逐模块设计——pilot 验证模板可复用性，再批量填其他模块。

---

## 模块清单

| 顺序 | 模块 | 状态 | 路径 |
|------|------|------|------|
| **Pilot 1** | M04 功能项档案页（覆盖并发） | draft（pilot 模板） | [`M04-feature-archive/`](./M04-feature-archive/) |
| 第一批 | M05 版本时间线 | draft（待 fix + CY 裁决） | [`M05-version-timeline/`](./M05-version-timeline/) |
| 第一批 | M06 竞品参考 | draft（待 fix + CY 裁决） | [`M06-competitor/`](./M06-competitor/) |
| 第一批 | M07 问题沉淀 | draft（待 fix + CY 裁决） | [`M07-issue/`](./M07-issue/) |
| 第一批 | M14 行业动态 | draft（待 fix + CY 裁决） | [`M14-industry-news/`](./M14-industry-news/) |
| 第一批 | M19 导入/导出 | draft（待 fix + CY 裁决） | [`M19-import-export/`](./M19-import-export/) |
| **Pilot 2** | M17 AI 智能导入（覆盖 Queue 异步） | 待开 | `M17-ai-import/` |
| 第二批 | M01 / M02 / M03 基础链 | 待 CY 出业务 | — |
| 第二批 | M11 / M12 中复杂 | 待开 | — |
| 第三批 | M13 / M16 / M18 复杂 AI | 待 CY 出业务 | — |
| 第四批 | M08 / M09 / M10 / M15 / M20 | 待开 | — |

第一批 reviewer audit 报告：[`audit-report-batch1.md`](./audit-report-batch1.md)

完整能力定位见 [`../00-architecture/07-capability-matrix.md`](../00-architecture/07-capability-matrix.md)。

---

## 16 字段模板（每个模块产出）

每个模块目录最少包含 `00-design.md`（节 0-13 + 15）+ `tests.md`（节 14）。

| # | 节 | 性质 | 强制项 |
|---|----|------|--------|
| 0 | frontmatter | 强制（规约 11.3）| 12 字段标准（见下） |
| 1 | 业务说明 + 职责边界（in / out scope） | 业务 | **必须引 PRD/US 编号** |
| 2 | 依赖模块图（M? → M?） | 半机械 | mermaid flowchart |
| 3 | 数据模型（SQLAlchemy + Alembic） | 业务核心 | **必含 SQLAlchemy class 代码块**（不只 ER 图） |
| 4 | 状态机（无状态显式声明） | 业务 | 无状态实体也要显式说明 |
| 5 | 多人架构 4 维必答 | 半机械（按 catalog） | 5 项清单逐项标 + **有状态机时增"状态转换竞态分析"行** |
| 6 | 分层职责表 | 机械（按 04-layer） | 每层文件路径具体 |
| 7 | API 契约（Pydantic + OpenAPI） | 半机械 | endpoints 表 + Pydantic schema 草案 |
| 8 | 权限三层防御点 | 机械（按 04-layer Q4） | 含异步路径声明 |
| 9 | DAO tenant 过滤策略 | 机械（按清单 5） | 豁免清单显式（无则写"无"） |
| 10 | activity_log 事件清单 | 业务 | action_type / target_type / metadata 三列表格 |
| 11 | idempotency_key 适用清单 | 业务 | 不需要也要显式声明 |
| 12 | Queue payload schema（异步专用） | 半机械（异步模块） | 同步模块写"N/A 显式声明" |
| 13 | ErrorCode 新增清单 | 半机械 | + AppError 子类草案 |
| 14 | 测试场景（独立 tests.md） | 业务 | 6 类：Golden/边界/并发/Tenant/权限/错误 |
| 15 | 完成度判定 checklist | 机械 | **含三轮 reviewer audit 强制勾选** |

---

## frontmatter 12 字段标准（CI 可静态扫描）

```yaml
---
title: M{NN} 模块名 - 详细设计       # 必填
status: draft                           # 必填：draft / accepted / superseded / deprecated
owner: CY                               # 必填
created: YYYY-MM-DD                     # 必填
accepted: null                          # 必填：null 或 YYYY-MM-DD
supersedes: []                          # 必填：[] 或 [ADR-NNN]
superseded_by: null                     # 必填：null 或 ADR-NNN
last_reviewed_at: null                  # 必填：null 或 YYYY-MM-DD（最近 reviewer audit 时间）
module_id: M{NN}                        # 必填：M01-M20
prism_ref: F{N}                         # 必填：对应 Prism F1-F20
pilot: false                            # 必填 boolean：是否 pilot 模板
complexity: low                         # 必填：low / medium / high（来自 catalog 颜色）
---
```

---

## 模板硬规则（reviewer 第一批 audit 输出）

1. **tests.md 禁止 ⚠️ 渗漏**：测试文档写完时所有决策必须已定，⚠️ 标记只能在 design.md 里
2. **节 3 必含 SQLAlchemy class 代码**：ER 图 + class 代码二者皆有，单独 ER 图不通过
3. **节 15 三轮 reviewer 强制勾选**：每模块都要勾完三轮 audit + CY 复审才能转 accepted
4. **节 5 状态转换竞态分析**：节 4 有 status 字段时，节 5 必须答"状态转换是否存在竞态：是/否+理由"
5. **frontmatter 12 字段固定**：缺字段或多字段 = 模板不合规

---

## 设计流程（每模块）

```
CY 出业务理解（节 1 + 节 3 数据语义 + 节 4 状态语义）
       ↓
AI 出 16 字段初稿（机械节定稿，业务节给候选）
       ↓
CY 逐节裁决「待 CY 裁决」项 + 复审
       ↓
独立 reviewer Agent 三轮 audit（Sonnet）：
  ① 完整性    ② 边界场景    ③ 演进 / 模板可复用性
       ↓
CY 标 status: accepted（节 15 全勾过 + last_reviewed_at 填日期）
       ↓
对照 Prism 现状 → 99-comparison/ 报告
```

**Agent 协作纪律**：
- pilot 模板用对话内推进，不起子 Agent
- 批量生成用 implementer Agent + 对抗式 reviewer Agent
- Agent 不得 commit / push（Agent 只产 patch / report，主对话 commit）

---

## 完成度判定（C 档整体）

- [x] Pilot M04 完成 + 模板首版定稿
- [x] 第一批 5 模块批量生成 + reviewer audit（不能转 accepted，需 fix + CY 裁决）
- [ ] 第一批 fix（机械问题 + CY 业务裁决）→ 转 accepted
- [ ] Pilot M17 完成 + audit 通过 → 异步字段补完
- [ ] 20 模块全部 status=accepted
- [ ] 99-comparison/ 对照报告：每模块一份
