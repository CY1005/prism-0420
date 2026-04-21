---
title: M04 功能项档案页 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M04
---

# M04 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（5 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建首条维度 | 编辑者 → POST `/dimensions` 含 type_id=1, content={...} | 201 + version=1 + activity_log 一条 `create` |
| G2 | 读取节点所有维度 | 编辑者 → GET `/dimensions` | 200 + items 含已填 + enabled_dimension_types 含未填 |
| G3 | 更新维度（乐观锁正常） | 拉取 → 改 content → PUT 带 expected_version=1 | 200 + version=2 + activity_log 一条 `update` 含 old/new version |
| G4 | 删除维度 | DELETE `/dimensions/{type_id}` | 204 + activity_log 一条 `delete` |
| G5 | 完善度计算 | GET `/completion` | enabled_count=N, filled_count=K, completion_rate=K/N |

---

## 2. 边界场景（6 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 内容空 | `content={}` | 422 `DIMENSION_CONTENT_INVALID`（field_schema 校验失败） |
| E2 | 内容超长 | `content` JSON 序列化 > 1MB | 413 / 422（按规约 12.4 边界校验） |
| E3 | 维度类型禁用 | 项目 disable type=5 后 POST type=5 | 422 `DIMENSION_TYPE_DISABLED` |
| E4 | 维度类型不存在 | type_id=999 | 404 `DIMENSION_TYPE_NOT_FOUND` |
| E5 | 重复创建 | 同 (node_id, type_id) 二次 POST | 409 `DIMENSION_DUPLICATE` |
| E6 | 节点已删 | 删 node 后 POST | 404 `NOT_FOUND`（node） |

---

## 3. 并发场景（4 条 — pilot 核心）

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 同 user 双 tab 并发更新同维度 | 两次 PUT 都带 expected_version=1 | 第一个 200 v=2；第二个 409 `CONFLICT`；activity_log 仅 1 条 |
| C2 | 不同 user 并发更新同维度 | userA 拉 v=1 → userB 拉 v=1 → A 先 PUT → B PUT | A 成功；B 收到 409；提示"updated_by={A_name}, 请刷新" |
| C3 | 并发更新不同维度 | userA 改 type=1，userB 改 type=2，并发 PUT | 都成功（不同 dimension_records 行） |
| C4 | 并发删除 + 更新 | userA DELETE，userB PUT 带 expected_version | A 成功 204；B 收到 404 `DIMENSION_NOT_FOUND`（不是 CONFLICT） |

**实现要点**：
- pytest 用 `pytest-asyncio` + `asyncio.gather()` 模拟并发
- 数据库用真实 PG 不 mock（CY feedback：integration 测试不 mock DB）
- 断言乐观锁 SQL 实际跑出 rows=0

---

## 4. Tenant 隔离（5 条 — 安全核心）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读 | userA 持有 projectA token，访问 projectB 的 node | 403 `PERMISSION_DENIED`（Router 层 check_project_access 拦） |
| T2 | 越权写 | A 用 projectA 路径，传 projectB 的 node_id | 404 `NOT_FOUND`（Service 层 _check_node_belongs_to_project 拦；不暴露 forbidden 信息） |
| T3 | DAO 直查覆盖测试 | 单元测试 DimensionDAO.list_by_node(other_project_id) | 返回空 list（tenant 过滤生效） |
| T4 | URL 路径篡改 | path 是 projectA，body 写 projectB.node_id | Service 拒绝（节 8 check） |
| T5 | viewer 角色写 | viewer 调 PUT | 403 `PERMISSION_DENIED` |

---

## 5. 权限场景（3 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | role 降级中读取 | A 有 editor，中途降为 viewer，二次写 | 第二次 403 |
| P3 | session 过期 | token 过期后任意操作 | 401 `TOKEN_EXPIRED` |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | DB 唯一冲突 | `{"error": {"code": "DIMENSION_DUPLICATE", "message": ...}}` |
| ER2 | 乐观锁冲突 | `{"error": {"code": "CONFLICT", "message": "Concurrent modification detected"}}` |
| ER3 | field_schema 不符 | `{"error": {"code": "DIMENSION_CONTENT_INVALID", "details": {...}}}` |
| ER4 | 未识别 IntegrityError | `{"error": {"code": "CONFLICT", ...}}` ← 兜底，不暴露 SQL |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤每条分支 |
| Service | ≥ 90% | 含事务回滚路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | UI 渲染 + 事件 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 类型校验：规约 12
