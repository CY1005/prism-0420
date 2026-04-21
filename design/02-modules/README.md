# 模块详细设计（C 档）

按 16 字段模板逐模块设计——pilot 验证模板可复用性，再批量填其他模块。

---

## 模块清单（按 pilot 顺序）

| 顺序 | 模块 | 状态 | 路径 |
|------|------|------|------|
| **Pilot 1** | M04 功能项档案页（覆盖并发） | draft | [`M04-feature-archive/`](./M04-feature-archive/) |
| **Pilot 2** | M17 AI 智能导入（覆盖 Queue 异步） | 待开 | `M17-ai-import/` |
| 之后 | M01 / M02 / M03 基础链 | 待开 | — |
| 之后 | M13 / M16 / M18 复杂 AI | 待开 | — |
| 之后 | M5-M12 中复杂度 8 个 | 待开 | — |
| 之后 | M14 / M15 / M19 / M20 简单 4 个 | 待开 | — |

完整能力定位见 [`../00-architecture/07-capability-matrix.md`](../00-architecture/07-capability-matrix.md)。

---

## 16 字段模板（每个模块产出）

每个模块目录最少包含 `00-design.md`（节 0-13 + 15）+ `tests.md`（节 14）。

| # | 节 | 性质 |
|---|----|------|
| 0 | frontmatter | 强制（规约 11.3） |
| 1 | 职责边界（in / out scope） | 业务 |
| 2 | 依赖模块图（M? → M?） | 半机械 |
| 3 | 数据模型（SQLAlchemy + Alembic） | 业务核心 |
| 4 | 状态机（无状态显式声明） | 业务 |
| 5 | 多人架构 4 维必答 | 半机械（按 catalog） |
| 6 | 分层职责表 | 机械（按 04-layer） |
| 7 | API 契约（Pydantic + OpenAPI） | 半机械 |
| 8 | 权限三层防御点 | 机械（按 04-layer Q4） |
| 9 | DAO tenant 过滤策略 | 机械（按清单 5） |
| 10 | activity_log 事件清单 | 业务 |
| 11 | idempotency_key 适用清单 | 业务 |
| 12 | Queue payload schema（异步专用） | 半机械（异步模块） |
| 13 | ErrorCode 新增清单 | 半机械 |
| 14 | 测试场景（独立 tests.md） | 业务 |
| 15 | 完成度判定 checklist | 机械 |

---

## 设计流程（每模块）

```
CY 出业务理解（节 1 + 节 3 数据语义 + 节 4 状态语义）
       ↓
AI 出 16 字段初稿（机械节定稿，业务节给候选）
       ↓
CY 逐节裁决「待 CY 裁决」项 + 复审
       ↓
CY 标 status: accepted
       ↓
独立 reviewer Agent 三轮 audit（Sonnet）：
  ① 完整性    ② 边界场景    ③ 演进 / 模板可复用性
       ↓
修复 + 收尾
       ↓
对照 Prism 现状 → 99-comparison/ 报告
```

**Agent 协作纪律**：
- pilot 模板用对话内推进，不起子 Agent
- audit 用独立 Sonnet Agent
- Agent 不得 commit / push（Agent 只产 patch / report，CY 或主对话 commit）

---

## 完成度判定（C 档整体）

- [ ] Pilot M04 完成 + audit 通过 → 模板字段定稿
- [ ] Pilot M17 完成 + audit 通过 → 异步字段补完
- [ ] 20 模块全部 status=accepted
- [ ] 99-comparison/ 对照报告：每模块一份

对照报告见 [`../99-comparison/`](../99-comparison/) 目录（待建）。
