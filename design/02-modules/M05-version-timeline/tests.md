---
title: M05 版本演进时间线 - 测试场景
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
last_reviewed_at: 2026-04-21
module_id: M05
prism_ref: F5
pilot: false
complexity: medium
---

# M05 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（6 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建第一个版本记录 | 编辑者 → POST `/versions` 含 version_label="v1.0.0", summary="初始版本", change_type="added" | 201 + is_current=false + activity_log 一条 `create` |
| G2 | 读取节点时间线 | GET `/versions` | 200 + items 按 created_at desc 排列 + total 正确 |
| G3 | 读取单版本详情 | GET `/versions/{version_id}` | 200 + 含 created_by_name（join 展示） |
| G4 | 更新版本元数据 | PUT `/versions/{version_id}` 改 summary | 200 + updated_at 更新 + activity_log 一条 `update` |
| G5 | 标记为当前版本 | POST `/versions/{version_id}/set-current` | 200 + is_current=true + 原 current 自动变 false + activity_log 一条 `set_current` |
| G6 | 删除版本记录 | DELETE `/versions/{version_id}` | 204 + activity_log 一条 `delete`（含 was_current 标记） |

---

## 2. 边界场景（7 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | summary 为空 | `summary=""` | 422 校验错误（Pydantic min_length） |
| E2 | version_label 超长 | label 超 64 字符 | 422 校验错误 |
| E3 | version_label 重复 | 同一 node 下两次 POST 相同 label | 409 `VERSION_LABEL_DUPLICATE` |
| E4 | change_type 非法枚举 | `change_type="unknown"` | 422 Pydantic 枚举校验失败 |
| E5 | snapshot_data 格式错误 | `snapshot_data="not-a-dict"` | 422 `VERSION_SNAPSHOT_INVALID` |
| E6 | 删除不存在的版本 | DELETE 不存在 version_id | 404 `VERSION_NOT_FOUND` |
| E7 | 节点已删（soft delete） | node 被 M03 软删后 POST 版本 | 404 `NOT_FOUND`（node） |

---

## 3. 并发场景

**无并发场景**——05-module-catalog 标注 M05 并发=❌。

理由：版本记录主要是追加写（每次新建版本），没有多人同时编辑同一版本记录的业务场景；`is_current` 切换由 Service 层在单事务内完成，不存在乐观锁需求。

---

## 4. Tenant 隔离（4 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读时间线 | userA 持 projectA token，访问 projectB node 的版本列表 | 403 `PERMISSION_DENIED`（Router 层拦） |
| T2 | 越权读单版本 | A 用 projectA 路径访问 projectB 的 version_id | 404 `VERSION_NOT_FOUND`（DAO tenant 过滤生效，不暴露 forbidden） |
| T3 | DAO 单元测试 tenant 过滤 | `version_dao.list_by_node(other_project_id)` | 返回空 list |
| T4 | 越权删除 | 用 projectA 路径删 projectB 的 version | 404（Service 层 tenant check） |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问时间线 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | viewer 创建版本 | 403 `PERMISSION_DENIED`（Router 层：POST 要求 editor） |
| P3 | viewer 读取时间线 | 200（只读允许 viewer，US-C1.4 场景） |
| P4 | editor 标记当前版本 | 200（editor 权限足够） |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | DB 唯一冲突（version_label 重复） | `{"error": {"code": "VERSION_LABEL_DUPLICATE", "message": "..."}}` |
| ER2 | 版本不存在 | `{"error": {"code": "VERSION_NOT_FOUND", "message": "..."}}` |
| ER3 | snapshot_data 格式非法 | `{"error": {"code": "VERSION_SNAPSHOT_INVALID", "details": {...}}}` |
| ER4 | set-current 时原 current 版本已被删（数据不一致）| 200（clear_current_flag 无记录时正常，不报错）；activity_log 记录 previous_current_id=null |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤 + clear_current_flag |
| Service | ≥ 90% | 含 is_current 互斥逻辑 + set-current 路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 时间线渲染 + 变更类型标签 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码：`design/01-engineering/01-engineering-spec.md` 规约 7
- Prism 对照：`/root/cy/prism/web/src/db/schema.ts`（versionRecords）
