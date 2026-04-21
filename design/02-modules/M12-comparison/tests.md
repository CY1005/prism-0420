---
title: M12 功能对比矩阵 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M12
---

# M12 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **R14-1**：所有用例基于 CY 2026-04-21 ack 决策编写（G2/G4：B 值快照/无状态字段）。

---

## 1. Golden Path（6 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 实时矩阵渲染 | 编辑者 → GET `/comparison/matrix?node_ids=...&dimension_type_ids=...`（2 个 node，3 个维度）| 200 + cells 6 条（含 null 的未填格）+ nodes 2 条 + dimension_types 3 条 |
| G2 | 保存快照（G4=B 值快照）| 编辑者 → POST `/comparison/snapshots` 含 name="竞品对比 Q2" + node_ids + dimension_type_ids | 201 + snapshot_id + nodes_ref/dimensions_ref（元数据）+ comparison_snapshot_items N×M 行 content 副本 + activity_log `snapshot.create`（含 items_count） |
| G3 | 查询快照列表 | GET `/comparison/snapshots` | 200 + items 含当前项目所有快照 + 按 created_at 倒序 |
| G4 | 查询快照详情（G4=B 读 items 表）| GET `/comparison/snapshots/{snapshot_id}` | 200 + snapshot info + items（N×M 副本数据） |
| G5 | 重命名快照 | PUT `/comparison/snapshots/{id}` 含 name="新名称" + expected_version=1 | 200 + version=2 + activity_log `snapshot.rename` |
| G6 | 删除快照 | DELETE `/comparison/snapshots/{id}` | 204 + activity_log `snapshot.delete` + 后续 GET 返回 404 |

---

## 2. 边界场景（7 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 空 node_ids | GET matrix 不传 node_ids | 422 `COMPARISON_EMPTY_SELECTION` |
| E2 | 空 dimension_type_ids | GET matrix 不传 dimension_type_ids | 422 `COMPARISON_EMPTY_SELECTION` |
| E3 | node_id 不属于该 project | GET matrix 传入其他 project 的 node_id | 404 `COMPARISON_NODE_NOT_FOUND`（DAO project_id 过滤，不暴露跨租户信息）|
| E4 | 快照 name 为空 | POST snapshots 含 name="" | 422 `COMPARISON_SNAPSHOT_NAME_EMPTY` |
| E5 | 快照 name 超长 | POST snapshots 含 name=130 字符 | 422（Pydantic max_length=128 校验）|
| E6 | 快照 rename 传错 expected_version（乐观锁）| PUT 含 expected_version=999（实际 version=1）| 409 `COMPARISON_SNAPSHOT_CONFLICT` |
| E7 | 保存后原数据改变，快照内容不变（G4=B 核心场景）| 保存快照（items 存 content 副本）→ 编辑 M04 dimension_record 改变内容 → GET snapshot detail | 200 + items 中 content 仍是**保存时的原值**（B 模式存值，不受后续编辑影响） |
| E8 | node 被删后快照仍展示原值（G4=B 不降级）| 保存快照后 DELETE M03 node，再 GET snapshot detail | 200 + items 仍有 content 数据（node_id 为 NULL 但 content 有效）；**不报 404；不降级为空矩阵** |

---

## 3. 并发场景（4 条）

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 多人同时 rename 同一快照（乐观锁冲突）| userA 和 userB 同时 PUT rename，都携带 expected_version=1 | 第一个 200 version=2；第二个 409 `COMPARISON_SNAPSHOT_CONFLICT`；activity_log 仅 1 条 |
| C2 | 多人同时创建快照（互不干扰）| userA 和 userB 同时 POST 创建快照 | 两个各自 201，各自 snapshot_id，互不影响 |
| C3 | 并发 delete + rename | userA DELETE 快照，userB 同时 PUT rename 同一快照 | A 成功 204；B 收到 404 `COMPARISON_SNAPSHOT_NOT_FOUND` |
| C4 | 并发读矩阵时有人在编辑维度 | userA GET matrix，userB 同时 PUT dimension_record | A 返回当前最新数据（实时读）；两操作互不阻塞 |

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读快照列表 | userA 持 projectA token，GET projectB 的 snapshots | 403 `PERMISSION_DENIED`（Router check_project_access 拦）|
| T2 | 越权读单快照 | userA 拿 projectB 的 snapshot_id，GET 时 path 含 projectA | 404 `COMPARISON_SNAPSHOT_NOT_FOUND`（DAO project_id 过滤，不暴露 forbidden）|
| T3 | 越权渲染矩阵（传入他项目的 node_id）| GET matrix 传 projectB 的 node_id，path 含 projectA | 404 `COMPARISON_NODE_NOT_FOUND`（DAO project_id 双重过滤）|
| T4 | DAO tenant 过滤单元测试 | `ComparisonDAO.list_snapshots(other_project_id)` | 返回空 list |
| T5 | viewer 角色删除快照 | viewer 调 DELETE | 403 `PERMISSION_DENIED`（Router 要求 ≥editor 才能删）|

---

## 5. 权限场景（3 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问矩阵 | 401 `UNAUTHENTICATED`（Server Action session 校验）|
| P2 | viewer 读矩阵（只读接口）| 200（GET matrix + GET snapshots 允许 viewer）|
| P3 | viewer 保存快照 | 403 `PERMISSION_DENIED`（POST snapshots 要求 ≥editor）|

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7）|
|----|------|----------------------|
| ER1 | 乐观锁冲突（rename）| `{"error": {"code": "COMPARISON_SNAPSHOT_CONFLICT", "message": "Snapshot was modified by someone else; please refresh and retry"}}` |
| ER2 | 快照不存在（GET / DELETE）| `{"error": {"code": "COMPARISON_SNAPSHOT_NOT_FOUND", "message": "Comparison snapshot not found"}}` |
| ER3 | 节点不属于项目 | `{"error": {"code": "COMPARISON_NODE_NOT_FOUND", "message": "..."}}` |
| ER4 | 创建快照 DB 事务失败 | `{"error": {"code": "CONFLICT", "message": "..."}}` 兜底，不暴露 SQL |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤每条分支 + 乐观锁 SQL |
| Service | ≥ 90% | 含矩阵聚合逻辑 + 事务回滚 + 状态校验 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 矩阵渲染 + 快照保存弹窗 |

---

## 8. 测试要点

- pytest + asyncio（同 M04 模式）
- **DB 用真实 PG 不 mock**（CY feedback 统一原则）
- 乐观锁测试 C1 用 `asyncio.gather()` 模拟同时 PUT
- 矩阵渲染测试先用 M03/M04 service 创建测试节点和维度记录，再调 M12 GET matrix
- node 删除后渲染快照（E7）：需先有快照，再调 M03 NodeService 删除 node，再 GET snapshot detail

---

## 9. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- M04 tests 范本（乐观锁测试参考）：`design/02-modules/M04-feature-archive/tests.md`
