---
title: M14 行业动态 - 测试场景
status: accepted
owner: CY
created: 2026-04-21
accepted: 2026-04-21
last_reviewed_at: 2026-04-21
module_id: M14
prism_ref: F14
pilot: false
complexity: low
---

# M14 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **特殊说明**：M14 全局共享数据，Tenant 测试类聚焦"豁免验证"（确认全局可读），非越权拦截。

---

## 1. Golden Path（6 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建行业动态 | 已登录用户 → POST `/api/news` 含 title="AI 监管新规" + tags=["AI","监管"] | 201 + id + source_type="manual" + activity_log 一条 `create` |
| G2 | 读取动态列表 | GET `/api/news` 无过滤 | 200 + items 按 created_at DESC + total 正确 |
| G3 | 读取动态详情 | GET `/api/news/{news_id}` | 200 + linked_nodes 列表（即使为空也返回 []） |
| G4 | 更新动态 | PUT `/api/news/{news_id}` 改 title + summary | 200 + 字段更新 + activity_log 一条 `update` |
| G5 | 关联功能项 | POST `/api/news/{news_id}/links` 含 node_id | 201 + NewsNodeLinkResponse + activity_log 一条 `link` |
| G6 | 删除动态 | DELETE `/api/news/{news_id}`（本人） | 204 + activity_log 一条 `delete` |

---

## 2. 边界场景（6 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 标题超长 | `title` 超过 200 字 | 422 `VALIDATION_ERROR`（Pydantic 校验） |
| E2 | 空标题 | `title=""` | 422 `VALIDATION_ERROR` |
| E3 | 关联不存在的 node | `node_id` 为随机 UUID | 404 `NOT_FOUND`（Service 校验 node 存在） |
| E4 | 分页边界 | `page=9999&page_size=20`（超出总数） | 200 + `items=[]` + `total` 不变（不报错） |
| E5 | 无关联 node 的动态 | 创建动态后直接 GET | 200 + `linked_nodes=[]`（空数组，非 null） |
| E6 | source_url 格式无效 | `source_url="not-a-url"` | 422 `VALIDATION_ERROR`（URL 格式校验） |

---

## 3. 并发场景（2 条）

> M14 无乐观锁（05-catalog 并发 ❌），并发测试聚焦"同时操作无死锁"。

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 两人同时删除同一条动态 | asyncio.gather 两次 DELETE 同 news_id | 一个 204；一个 404 `NEWS_NOT_FOUND`（不报 500） |
| C2 | 两人同时关联同一 node | asyncio.gather 两次 POST `/links` 含相同 node_id | 一个 201；一个 409 `NEWS_LINK_DUPLICATE`（DB 唯一约束兜底） |

---

## 4. Tenant 隔离（全局豁免验证，4 条）

> M14 无 tenant——本类测试验证"全局可读"行为符合预期，非"越权拦截"。

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目用户读取全局列表 | userA 所在 projectA，userB 所在 projectB，各自 GET `/api/news` | 两者返回**相同完整列表**（无项目过滤） |
| T2 | 无项目归属用户可读 | 新注册用户（未加入任何项目）GET `/api/news` | 200 + 全局列表（全局数据无需项目归属） |
| T3 | DAO 无 tenant 过滤确认 | 单元测试 `IndustryNewsDAO.list_all()` 不传 project_id | 返回所有动态（无 tenant 过滤代码路径执行） |
| T4 | 关联 node 跨项目 | userA 关联 projectB 的 node_id（userA 无 projectB 权限）| 404 `NOT_FOUND`（Service 层校验 node 存在；node_id 归属不校验 project，M14 全局数据——但 node 若不存在则 404；node 存在则允许关联，全局动态可关联任意 node） |

---

## 5. 权限场景（5 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录读取列表 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | 未登录创建动态 | 401 `UNAUTHENTICATED` |
| P3 | 非本人删除动态 | 403 `NEWS_FORBIDDEN`（Service 层 `_check_news_owner_or_admin` 拦） |
| P4 | 平台管理员删除他人动态 | 204（管理员豁免本人校验） |
| P5 | 非本人编辑动态 | 403 `NEWS_FORBIDDEN` |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | news_id 不存在 | `{"error": {"code": "NEWS_NOT_FOUND", "message": "Industry news not found"}}` |
| ER2 | 重复关联同一 node | `{"error": {"code": "NEWS_LINK_DUPLICATE", "message": "This node is already linked to the news"}}` |
| ER3 | 删除不存在的关联 | `{"error": {"code": "NEWS_LINK_NOT_FOUND", ...}}` |
| ER4 | DB IntegrityError 未识别 | `{"error": {"code": "INTERNAL_ERROR", ...}}` ← 兜底，不暴露 SQL |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 90% | 含全局豁免路径确认（无 tenant 过滤分支） |
| Service | ≥ 90% | 含权限检查 / node 存在校验路径 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 动态卡片渲染 + 关联 picker |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 全局豁免依据：`design/00-architecture/06-design-principles.md` 清单 5 豁免条件
