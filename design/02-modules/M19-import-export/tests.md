---
title: M19 导入/导出 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M19
---

# M19 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **特殊说明**：M19 本期只实现导出（Markdown 报告），无导入逻辑（M11=CSV 导入，M17=AI 导入）。

---

## 1. Golden Path（5 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 单 node 导出 | viewer → POST `/api/projects/{pid}/export` 含 `node_ids=[node_a]` | 200 + Content-Type: text/markdown + Content-Disposition: attachment + 文件含 `## {node_name}` 章节 |
| G2 | 多 node 导出（3 个） | POST 含 `node_ids=[a, b, c]` | 200 + Markdown 含 3 个 node 章节 + 目录 |
| G3 | 含全部章节导出 | `include_sections.dimensions=true, version_timeline=true, competitors=true, issues=true` | Markdown 含维度/版本/竞品/问题 4 节 |
| G4 | 部分章节导出 | `include_sections.version_timeline=false, competitors=false` | Markdown 仅含维度 + 问题章节（无版本/竞品） |
| G5 | 导出触发 activity_log | POST 导出成功后 | activity_log 写入一条 `export` 事件，metadata 含 node_count + node_ids |

---

## 2. 边界场景（6 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | node_ids 超上限 | `node_ids` 含 21 个 UUID | 422 `EXPORT_NODE_LIMIT_EXCEEDED` |
| E2 | node_ids 为空 | `node_ids=[]` | 422 `VALIDATION_ERROR`（Pydantic min_length=1） |
| E3 | node 无维度内容 | 导出一个未填任何维度的 node | 200 + Markdown 含该章节但维度区块显示"（暂无内容）"（不报错） |
| E4 | 全部 node 无任何内容 | 所有 node 均无维度/版本/竞品/问题 | ⚠️ **待 CY 裁决**：A: 200 + 空报告 / B: 422 `EXPORT_EMPTY_CONTENT`；我倾向 A（空报告也是合法输出） |
| E5 | node_ids 含重复 UUID | `node_ids=[a, a, b]` | 去重后导出（200 + 2 章节，不报错） |
| E6 | 所选 node 含已删除 node | node_a 已软删除 | 404 `EXPORT_NODE_NOT_IN_PROJECT`（或 NOT_FOUND） |

---

## 3. 并发场景（2 条）

> M19 只读操作，并发测试聚焦"无死锁/无数据竞争"。

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 同一用户并发发起两次导出 | asyncio.gather 两次相同 POST | 两次都 200（读操作无冲突，各自独立返回 Markdown） |
| C2 | 导出与 M04 编辑并发 | userA 导出同时 userB 编辑同一 node 维度 | 导出读到编辑前或编辑后的快照（均 200，不报错，不死锁） |

---

## 4. Tenant 隔离（5 条 — 安全核心）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权导出 | userA 有 projectA 权限，POST 含 projectB 的 node_ids 到 `/projects/projectB/export` | 403 `PERMISSION_DENIED`（Router check_project_access 拦） |
| T2 | URL project_id 与 node 实际 project 不符 | URL 是 projectA，node_id 实际属于 projectB | 404 `EXPORT_NODE_NOT_IN_PROJECT`（Service 层校验拦） |
| T3 | DAO tenant 过滤覆盖测试 | 单元测试：`export_dao.get_dimensions_for_export(node_ids, projectA_id)` 调用，node 实际属 projectB | 返回空 dict（tenant 过滤生效，不返回 projectB 数据） |
| T4 | 混合 node 列表（部分越权） | `node_ids=[projectA_node, projectB_node]`（无 projectB 权限） | 404 `EXPORT_NODE_NOT_IN_PROJECT`（任一不符即报错） |
| T5 | viewer 角色导出 | 查看者用 GET 查看了内容后 POST 导出 | 200（viewer 有导出权限） |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录导出 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | viewer 导出 | 200（viewer 可导出，见设计节 8） |
| P3 | 非项目成员导出 | 403 `PERMISSION_DENIED`（Router check_project_access 拦） |
| P4 | session 过期后导出 | 401 `TOKEN_EXPIRED` |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | node_ids 超限 | `{"error": {"code": "EXPORT_NODE_LIMIT_EXCEEDED", "message": "Too many nodes selected for export (max 20)"}}` |
| ER2 | node 不属于 project | `{"error": {"code": "EXPORT_NODE_NOT_IN_PROJECT", "message": "One or more nodes do not belong to this project"}}` |
| ER3 | 上游 DAO 查询失败 | `{"error": {"code": "INTERNAL_ERROR", ...}}` ← 兜底，不暴露 SQL |
| ER4 | project_id 不存在 | `{"error": {"code": "NOT_FOUND", "message": "Project not found"}}` |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO（读路径） | ≥ 90% | 含 tenant 过滤每个表的覆盖 |
| Service（聚合 + Markdown 生成） | ≥ 90% | 含 include_sections 各组合路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component（导出按钮 + node 选择器） | ≥ 70% | 按钮交互 + 选择状态 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 模块边界：M11 CSV 导入 / M17 AI 智能导入（不在本测试范围）
- Tenant 过滤依据：`design/00-architecture/06-design-principles.md` 清单 5
