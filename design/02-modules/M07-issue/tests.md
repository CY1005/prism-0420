---
title: M07 问题沉淀 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
last_reviewed_at: null
module_id: M07
prism_ref: F7
pilot: false
complexity: medium
---

# M07 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（8 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建 bug 类型 issue（挂节点）| 编辑者 → POST `/issues` 含 node_id, category="bug", title="登录超时无提示", description="..." | 201 + status="open" + activity_log 一条 `create` |
| G2 | 创建游离 issue（无节点）| POST `/issues` 不含 node_id | 201 + node_id=null + project 级问题 |
| G3 | 读取项目全部 issue | GET `/issues` | 200 + items 含节点 issue + 游离 issue |
| G4 | 读取功能项 issue 列表 | GET `/nodes/{node_id}/issues` | 200 + 只含该节点的 issue |
| G5 | 按 status 筛选 | GET `/issues?status=open` | 200 + 只含 open 状态 |
| G6 | 状态流转 open→in_progress | POST `/issues/{id}/transition` 含 target_status="in_progress" | 200 + status 变更 + activity_log `status_change` |
| G7 | 状态流转 in_progress→resolved | POST transition 含 target_status="resolved" | 200 + resolved_at 写入 + activity_log |
| G8 | 删除 issue | DELETE `/issues/{id}` | 204 + activity_log `delete`（含 final_status） |

---

## 2. 边界场景（9 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | title 为空 | `title=""` | 422（Pydantic min_length） |
| E2 | title 超长 | > 256 字符 | 422 Pydantic 校验 |
| E3 | category 非法枚举 | `category="unknown"` | 422 `ISSUE_CATEGORY_INVALID` |
| E4 | node_id 跨项目 | node_id 属于 projectB，但在 projectA 下创建 | 422 `ISSUE_NODE_CROSS_PROJECT` |
| E5 | 非法状态转换 closed→open | POST transition target_status="open" on closed issue | 422 `ISSUE_TRANSITION_INVALID` |
| E6 | 非法状态转换 open→resolved | 跳过 in_progress 直接 resolved | 422 `ISSUE_TRANSITION_INVALID` |
| E7 | 同状态重复 transition | in_progress → in_progress | 待 CY 裁决决策点：见 [00-design.md](./00-design.md) 节 11 |
| E8 | 删除不存在 issue | DELETE 不存在 id | 404 `ISSUE_NOT_FOUND` |
| E9 | tags 非字符串数组 | `tags=["valid", 123]` | 422 Pydantic 类型校验 |

---

## 3. 并发场景

**无并发场景**——05-module-catalog 标注 M07 并发=❌。

理由：issue 是单一责任人顺序操作（open→in_progress→resolved），不存在多人同时编辑同一 issue 的业务场景；状态转换由 Service 层串行校验，不引入乐观锁。

---

## 4. Tenant 隔离（4 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读 issue 列表 | userA 用 projectA token 访问 projectB issue 列表 | 403 `PERMISSION_DENIED`（Router 层拦） |
| T2 | 越权读单 issue | A 用 projectA 路径访问 projectB 的 issue_id | 404 `ISSUE_NOT_FOUND`（DAO tenant 过滤生效） |
| T3 | DAO 单元测试 tenant 过滤 | `issue_dao.list_by_project(other_project_id)` | 返回空 list |
| T4 | 越权触发状态流转 | A 用 projectA 路径 transition projectB 的 issue | 404（Service 层 tenant check） |

---

## 5. 权限场景（5 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录读 issue 列表 | 401 `UNAUTHENTICATED` |
| P2 | viewer 创建 issue | 403 `PERMISSION_DENIED`（POST 要求 editor） |
| P3 | viewer 读取 issue 列表 | 200（只读允许 viewer） |
| P4 | viewer 触发状态流转 | 403 `PERMISSION_DENIED`（transition 要求 editor） |
| P5 | editor 删除 closed issue | 204（editor 有权删任意状态 issue） |

---

## 6. 错误处理（5 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | issue 不存在 | `{"error": {"code": "ISSUE_NOT_FOUND", "message": "..."}}` |
| ER2 | 非法状态转换 | `{"error": {"code": "ISSUE_TRANSITION_INVALID", "message": "...", "details": {"current": "closed", "target": "open"}}}` |
| ER3 | 非法 category | `{"error": {"code": "ISSUE_CATEGORY_INVALID", "message": "..."}}` |
| ER4 | node 跨项目 | `{"error": {"code": "ISSUE_NODE_CROSS_PROJECT", "message": "..."}}` |
| ER5 | DB 约束违反（status CHECK）| `{"error": {"code": "VALIDATION_ERROR", ...}}` ← 兜底，不暴露 SQL |

---

## 7. 状态机专项测试（4 条）

> 状态机是 M07 与 M05/M06 的核心差异，需专项覆盖。

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| SM1 | 完整生命周期 | open → in_progress → resolved → closed | 每步 200 + resolved_at 在 resolved 步写入 |
| SM2 | resolved → open（问题复现）| 已 resolved 的 issue 重新打开 | 200 + resolved_at 清空 + status=open |
| SM3 | open → closed（直接关闭）| 不修复直接关闭 | 200 + resolved_at=null + status=closed |
| SM4 | closed 后所有 transition 拦截 | closed issue 任意 transition | 422 `ISSUE_TRANSITION_INVALID` |

---

## 8. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤 + 多参数筛选组合 |
| Service | ≥ 90% | 含状态机转换所有合法/非法路径 |
| Router | ≥ 80% | 含 transition 端点 |
| Component | ≥ 70% | 状态标签 + 列表渲染 |

---

## 9. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码：`design/01-engineering/01-engineering-spec.md` 规约 7
- Prism 对照：`/root/cy/prism/web/src/db/schema.ts`（issues 原始表）
