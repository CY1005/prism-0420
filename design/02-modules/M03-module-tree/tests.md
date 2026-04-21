---
title: M03 功能模块树 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M03
---

# M03 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **CY 2026-04-21 已 ack 8 组决策（G2/G5/G7），本文件依据决策更新：硬删除/last-write-wins/无状态/跨父移动/R-X2。**

---

## 1. Golden Path（9 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建根节点 | editor → POST `/api/projects/{pid}/nodes` body `{name="功能A", type="folder", parent_id=null}` | 201 + depth=0 + path="/`{new_id}`/" + sort_order=0 + activity_log `create` 一条 |
| G2 | 创建子节点 | editor → POST `/api/projects/{pid}/nodes` body `{name="子功能A1", parent_id=rootId}` | 201 + depth=1 + path="/rootId/`{new_id}`/" + sort_order=0 |
| G3 | 读取完整树 | viewer → GET `/api/projects/{pid}/nodes` | 200 + 嵌套树结构（children 递归），按 sort_order 排序 |
| G4 | 更新节点名称 | editor → PUT `/api/projects/{pid}/nodes/{nid}` body `{name="新名称"}` | 200 + name 更新 + activity_log `update` 一条（含 old_name/new_name） |
| G5 | 拖拽重排同级节点 | editor → POST `/api/projects/{pid}/nodes/reorder` body `{parent_id=rootId, items=[{node_id, sort_order},...]}` | 200 + 所有节点 sort_order 更新 + activity_log `reorder` 一条 |
| G6 | 删除叶子节点 | editor → DELETE `/api/projects/{pid}/nodes/{nid}` （无子节点）| 204 + activity_log `delete` 一条（had_children=false） |
| G7 | 面包屑查询 | GET `/api/projects/{pid}/nodes/{nid}/breadcrumb` | 200 + items 从根到当前节点顺序（id/name/depth） |
| G8 | 跨父移动节点（G5）| editor → POST `/api/projects/{pid}/nodes/{nid}/move` body `{new_parent_id=targetId}` | 200 + path 更新为新父节点路径前缀 + depth 更新 + 子树所有节点 path 同步更新 + activity_log `move` 一条 |
| G9 | 删除有子节点的节点（R-X2）| editor → DELETE `/api/projects/{pid}/nodes/{nid}` （含子节点和 M04/M06/M07 数据）| 204 + nodes 子树全部删除 + M04 dimension_records 删除 + M04 activity_log `delete` 记录 + M06/M07 同理 |

---

## 2. 边界场景（9 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 节点名为空 | `name=""` | 422 `VALIDATION_ERROR`（Pydantic min_length=1 拦截） |
| E2 | 节点名超长 | `name` 超 200 字符 | 422 `VALIDATION_ERROR` |
| E3 | parent_id 不存在 | POST 含不存在的 parent_id | 404 `NODE_PARENT_NOT_FOUND` |
| E4 | 删除有子节点的节点 | DELETE 含子节点的 folder | 204 + 子节点全部级联删除（验证 DB 中子节点已不存在）|
| E5 | 尝试更改节点类型 | PUT 含 `type="file"` (原为 folder) | 422 `NODE_TYPE_IMMUTABLE` |
| E6 | 重排含跨父节点 items | NodeReorder.items 含不同 parent_id 的节点 | 422 `NODE_REORDER_INVALID` |
| E7 | 单节点树面包屑（根节点） | GET breadcrumb for root node（depth=0） | 200 + items=[{id, name, depth=0}]（只有自己） |
| E8 | move 节点到其子孙节点（G5 循环引用检测）| POST `/move` body `{new_parent_id=childId}` where childId 是 nodeId 的子孙 | 422 `NODE_MOVE_CYCLE_DETECTED`（Service 层路径前缀检查：`target.path NOT LIKE source.path || '%'`） |
| E9 | move 节点到当前同一父节点（NOOP）| POST `/move` body `{new_parent_id=sameParentId}` | 200 + path 不变 + depth 不变（幂等操作，不报错） |

---

## 3. 并发场景（3 条）

> M03 catalog 标注：并发 ❌；采用 last-write-wins 策略（G2/G5 决策）。

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 两个 editor 同时在同父节点下创建子节点 | `asyncio.gather()` 并发 POST 两个节点 | 两者均 201，sort_order 不同（DB 插入顺序决定），不报冲突，数据完整（无丢失） |
| C2 | 并发拖拽重排后 path 字段一致性（G7-M03-R2-04）| 并发两次 POST `/reorder`（items 覆盖相同节点）| 最后一次 sort_order 生效（last-write-wins），无 500；**path 字段验证**：sort_order 更新不影响 path（path 包含 `/{id}/`，不含 sort_order），验证并发后所有节点 path 格式正确（`/parentId/nodeId/`），无空字符串或乱码 |
| C3 | 并发 move_subtree（G5）| 两个 editor 同时 POST move 同一节点到不同目标父节点 | 最后到达的 move 生效（last-write-wins），子树 path 一致更新，无 500，无孤儿 path |

**实现要点**：
- 使用真实 PG 不 mock DB
- C1 验证 last-write-wins 不导致数据丢失（两条节点都存在）
- C2 说明：path 不包含 sort_order，path 不因重排改变（只有 move 才改 path）；验证重排后 path 格式合法
- C3 验证子树 path 一致性（无中间状态残留）

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 非项目成员读取树 | userB 无 project_members 记录，GET `/nodes` of projectA | 403 `PERMISSION_DENIED`（Router `check_project_access` 拦） |
| T2 | 跨项目越权写节点 | userB 是 projectB 成员，PUT projectA 的 node_id | 403（Router 拦：userB 非 projectA 成员） |
| T3 | DAO 过滤测试 | 单元测试 `NodeDAO.list_by_project(projectA_id)` | 返回列表不含 projectB 的节点（tenant 过滤生效）|
| T4 | path 不跨项目泄露 | 两个项目各有根节点，查 projectA 树 | 返回结果不含 projectB 任何 path 片段 |
| T5 | 子树查询 tenant 验证 | `NodeDAO.list_subtree(node_id_from_projectA, project_id=projectB)` | 返回空列表（project_id 过滤防跨租户）|

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | viewer 创建节点 | 403 `PERMISSION_DENIED`（Router 层：写接口需 editor）|
| P3 | viewer 删除节点 | 403 `PERMISSION_DENIED` |
| P4 | editor 读取树 | 200（读接口允许 viewer 及以上，editor OK）|

---

## 6. 错误处理（6 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | 删除不存在的节点 | `{"error": {"code": "NODE_NOT_FOUND", "message": "..."}}` 404 |
| ER2 | 面包屑查询不存在节点 | `{"error": {"code": "NODE_NOT_FOUND", "message": "..."}}` 404 |
| ER3 | 创建节点时 parent_id 属于其他项目 | `{"error": {"code": "NODE_PARENT_NOT_FOUND", "message": "..."}}` 404（不暴露跨租户信息）|
| ER4 | 重排包含 node_id 不存在 | `{"error": {"code": "NODE_NOT_FOUND", "message": "..."}}` 404 |
| ER5 | 删除节点后下游 activity_log 验证（R-X2）| DELETE 含 M04 数据的节点 | 204 + M04 dimension_records 已删除 + M04 activity_log 有 `delete` 记录（验证 Service 层调下游而非仅靠 CASCADE） |
| ER6 | move 时循环引用（G5）| POST move node 到其子孙 | `{"error": {"code": "NODE_MOVE_CYCLE_DETECTED", "message": "..."}}` 422 |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤 / path LIKE 子树查询每条分支 |
| Service | ≥ 90% | 含 path 计算逻辑 / 拖拽重排事务路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 树渲染 / 右键菜单 / 拖拽 UI |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- Prism 对照参考：`/root/cy/prism/web/src/db/schema.ts`（nodes 表）
- 下游模块：M04 通过 `(project_id, node_id)` 引用 nodes 表；M11/M17 通过 `NodeService.batch_create_in_transaction` 批量创建节点
