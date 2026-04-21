---
title: M08 模块关系图 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M08
prism_ref: F8
---

# M08 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> CY 2026-04-21 已 ack Q1/Q2/Q3（候选 A），本测试基于有向关系 + UNIQUE(source,target,type) + 3 种枚举。

---

## 1. Golden Path（6 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建 depends_on 关联 | 编辑者 → POST `/relations` `{source: A, target: B, type: depends_on}` | 201 + relation_id + activity_log 一条 `create` |
| G2 | 创建 related_to 关联 | 编辑者 → POST `{source: A, target: C, type: related_to, notes: "同一业务域"}` | 201 + notes 存储正确 |
| G3 | 读取 project 全部关联 | 任意角色 → GET `/relations` | 200 + items 包含所有关联 + source/target name join 正确 |
| G4 | 读取单节点关联（US-C1.2） | 查看者 → GET `/nodes/{A_id}/relations` | 200 + 仅返回 A 为 source 或 target 的关联 |
| G5 | 更新备注 | 编辑者 → PATCH `/relations/{id}` `{notes: "更新后备注"}` | 200 + notes 更新 + activity_log `update` |
| G6 | 删除关联 | 编辑者 → DELETE `/relations/{id}` | 204 + activity_log `delete` |

---

## 2. 边界场景（8 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 自环防护（source == target） | `source_node_id == target_node_id` | 422 `RELATION_SELF_LOOP` |
| E2 | 重复关联（同三元组） | 同 (source, target, type) 二次 POST | 409 `RELATION_DUPLICATE` |
| E3 | source 节点不属于 project | source_node_id 属于另一 project | 404 `RELATION_NODE_NOT_IN_PROJECT` |
| E4 | target 节点不属于 project | target_node_id 属于另一 project | 404 `RELATION_NODE_NOT_IN_PROJECT` |
| E5 | 非法 relation_type | `type: "blocks"` | 422（Pydantic 枚举校验先拦） |
| E6 | notes 超长 | notes 长度 > 5000 字符 | 422（Service 层字段长度校验）|
| E7 | 关联不存在（PATCH/DELETE） | relation_id 不存在 | 404 `RELATION_NOT_FOUND` |
| E8 | 节点已被 M03 删除后创建关联 | source_node_id 已删除 | 404（Service 节点归属校验失败） |

---

## 3. 并发场景（3 条）

> M08 无乐观锁——并发场景主要关注 DB 唯一约束兜底和幂等删除。

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 并发创建同三元组 | 两个请求并发 POST 同 (source, target, type) | 第一个 201；第二个 409 `RELATION_DUPLICATE`（DB 唯一约束兜底） |
| C2 | 并发删除同一关联 | 两个请求并发 DELETE `/relations/{id}` | 第一个 204；第二个 404 `RELATION_NOT_FOUND`（幂等，不报 500） |
| C3 | M03 删除节点 + M08 并发读取该节点关联 | M03 删除节点的同时 M08 拉取该节点关联 | 读取返回空 list 或 404（DB 级 FK CASCADE 清理，不报错） |

**实现要点**：
- pytest 用 `pytest-asyncio` + `asyncio.gather()` 模拟并发
- 数据库用真实 PG（不 mock DB）
- 断言 DB 唯一约束实际触发 IntegrityError → 转换为 `RELATION_DUPLICATE`

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨 project 越权读全部关联 | userA 持有 projectA token，访问 projectB 的 `/relations` | 403 `PERMISSION_DENIED`（Router 层 check_project_access 拦） |
| T2 | 越权创建关联（source 属于 projectB） | URL 是 projectA，body 传 projectB.node_id | 404 `RELATION_NODE_NOT_IN_PROJECT`（Service 层拦） |
| T3 | DAO 直查过滤测试 | 单元测试 `ModuleRelationDAO.list_by_project(other_project_id)` | 返回空 list（tenant 过滤生效） |
| T4 | 冗余 project_id 一致性 | 创建关联后直查 DB 确认 module_relations.project_id == source_node.project_id | 一致（Service 层强制赋值） |
| T5 | 跨 project 节点混搭 | source 属于 projectA，target 属于 projectB，URL 是 projectA | 404 `RELATION_NODE_NOT_IN_PROJECT`（target 不在 projectA） |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | viewer 创建关联 | 403 `PERMISSION_DENIED`（Router 层 editor 角色要求） |
| P3 | viewer 读取关联 | 200（读操作允许 viewer） |
| P4 | session 过期后写操作 | 401 `TOKEN_EXPIRED` |

---

## 6. 错误处理（5 条）

| ID | 场景 | 期望响应格式 |
|----|------|------------|
| ER1 | DB 唯一冲突（IntegrityError） | `{"error": {"code": "RELATION_DUPLICATE", "message": ...}}` |
| ER2 | 自环（Pydantic 校验） | `{"error": {"code": "RELATION_SELF_LOOP", "message": ...}}` |
| ER3 | 节点不在 project | `{"error": {"code": "RELATION_NODE_NOT_IN_PROJECT", "message": ...}}` |
| ER4 | 关联不存在 | `{"error": {"code": "RELATION_NOT_FOUND", "message": ...}}` |
| ER5 | 未识别 IntegrityError | `{"error": {"code": "CONFLICT", ...}}` ← 兜底，不暴露 SQL |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤每条分支 + delete_by_node |
| Service | ≥ 90% | 含节点归属校验 + 事务回滚路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 关系图渲染 + 表单提交 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 依赖模块：`design/02-modules/M03-module-tree/00-design.md`（R-X2 级联删除场景）
