---
title: M15 数据流转可视化 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M15
---

# M15 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> M15 纯读聚合模块，无并发写冲突场景——并发场景节显式说明。
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（5 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 查询项目操作日志列表 | admin → GET `/api/projects/{pid}/activity-stream?page=1&page_size=20` | 200；items 按 created_at 降序；每条含 user_name（JOIN users）；has_more 正确 |
| G2 | 按 user_id 过滤 | `?user_id={uid}` 过滤 | 200；返回的 items 全部来自该 user；total 反映过滤后数量 |
| G3 | 按 action_type 过滤 | `?action_type=update` | 200；items 全部为 action_type="update" 的记录 |
| G4 | 按时间范围过滤 | `?from_dt=2026-01-01T00:00:00&to_dt=2026-04-01T00:00:00` | 200；items 全部在时间范围内；边界日期记录包含 |
| G5 | 组合过滤 | `?user_id={uid}&action_type=create&target_type=node` | 200；items 满足全部三个过滤条件 |

---

## 2. 边界场景（7 条）

| ID | 场景 | 输入 | 期望 |
|----|------|------|------|
| E1 | 空日志（项目无操作历史）| 新建项目后立即 GET activity-stream | 200；items=[]；total=0；has_more=false |
| E2 | 分页超出范围 | `?page=999&page_size=50`（总记录数 < 999*50）| 200；items=[]；total=实际总数；has_more=false |
| E3 | 时间范围 from > to | `?from_dt=2026-04-30&to_dt=2026-01-01` | 422 `ACTIVITY_STREAM_INVALID_FILTER`（from_dt 必须 < to_dt）|
| E4 | user_id 过滤不存在的用户 | `?user_id={不存在 UUID}` | 200；items=[]；total=0（过滤无匹配，不报 404）|
| E5 | action_type 过滤无效枚举值 | `?action_type=invalid_action` | 422（Pydantic ActionType 枚举校验失败）|
| E6 | page_size 超上限 | `?page_size=201` | 422（page_size <= 200 约束）|
| E7 | 单次返回大量记录（page_size=200）| 项目有 500 条日志，`?page_size=200` | 200；items.len=200；total=500；has_more=true；响应时间 < 2s |

---

## 3. 并发场景（M15 纯读，无并发写冲突场景）

**M15 是纯读模块，无状态写入，无并发冲突场景。**

显式说明：
- M15 不存在"两个用户同时写同一资源"的场景
- 多 admin 同时读 activity-stream：各自独立 GET，结果一致
- **读-写并发**（M04 写 dimension_record 的同时 M15 读）：M15 读到的是查询时刻的快照，PG READ COMMITTED 下正常工作，不需要锁

补充一条**读一致性验证**：

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| C1 | 业务操作后日志立即可查 | M04 更新维度 → activity_log 写入 → 立即 GET M15 activity-stream | 新日志出现在 items 第一条（M15 直查 activity_logs，无缓存延迟）|

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读 | admin-A 持 projectA token，GET `/api/projects/{projectB_id}/activity-stream` | 403 `PERMISSION_DENIED`（Router check_project_access 拦）|
| T2 | 非成员 admin 读 | userC 不在 projectA 成员表，GET projectA activity-stream | 403/404（Service 层 _check_project_admin 拦）|
| T3 | DAO tenant 过滤覆盖 | 单元测试 `activity_stream_dao.list_stream(db, other_project_id)` | 返回空 list（activity_logs.project_id 过滤生效，不泄露其他 project 日志）|
| T4 | URL 路径篡改 | URL path 是 projectA，query 无法指定其他 project_id | activity_logs 过滤锁定在路径中的 project_id，无法跨 project 读取 |
| T5 | 两个 project 日志隔离 | projectA 和 projectB 各有操作日志；admin-A 查 projectA | items 全部来自 projectA，不含 projectB 数据 |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦）|
| P2 | viewer 角色访问 | 403 `ACTIVITY_STREAM_FORBIDDEN`（Router check_project_access(role="admin") 拦）|
| P3 | editor 角色访问 | 403 `ACTIVITY_STREAM_FORBIDDEN`（同上，仅 admin 可访问）|
| P4 | admin 正常读 | 200；完整日志列表返回 |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7）|
|----|------|----------------------|
| ER1 | project 不存在 | `{"error": {"code": "ACTIVITY_STREAM_PROJECT_NOT_FOUND", "message": "Project not found or access denied"}}` |
| ER2 | 非 admin 访问 | `{"error": {"code": "ACTIVITY_STREAM_FORBIDDEN", "message": "Only project admin can view activity stream"}}` |
| ER3 | 过滤参数不合法（from > to）| `{"error": {"code": "ACTIVITY_STREAM_INVALID_FILTER", "message": "Invalid filter parameters: from_dt must be before to_dt"}}` |
| ER4 | DB 查询超时（大量日志）| 502/504；不暴露内部 SQL；⚠️ AI 推断——若添加超时保护，ErrorCode 待 CY 定 |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | tenant 过滤（project_id）/ 分页 / 各过滤条件分支（user_id / action_type / target_type / 时间范围）|
| Service | ≥ 90% | admin 权限校验 + 列表组装 |
| Router | ≥ 80% | 主走 e2e；含 admin 正常返回 + viewer/editor 403 |
| Component | ≥ 70% | 时间轴按日期分组渲染 + 过滤器 UI |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- tenant 过滤参考：`M04-feature-archive/tests.md`（T1-T5 模式复用）
- activity_log 写入来源：`M04-feature-archive/00-design.md` §10（M15 消费的事件来源之一）
