---
title: M06 竞品参考 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M06
---

# M06 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（8 条）

### 竞品全局实体

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建竞品全局条目 | 编辑者 → POST `/competitors` 含 display_name="飞书", website_url="https://feishu.cn" | 201 + activity_log 一条 `create competitor` |
| G2 | 获取项目竞品列表 | GET `/competitors` | 200 + items 含新建竞品 + total 正确 |
| G3 | 更新竞品描述 | PUT `/competitors/{competitor_id}` 改 description | 200 + updated_at 更新 + activity_log `update` |
| G4 | 删除竞品（无对标记录）| DELETE `/competitors/{competitor_id}` | 204 + activity_log `delete` |

### 功能项对标记录

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G5 | 创建对标记录 | 编辑者 → POST `/competitor-refs` 含 competitor_id + feature_coverage + pros_and_cons | 201 + activity_log 一条 `create competitor_ref` |
| G6 | 读取功能项对标列表 | GET `/competitor-refs` | 200 + display_name join 展示 |
| G7 | 更新对标内容 | PUT `/competitor-refs/{ref_id}` 改 tech_approach | 200 + activity_log `update competitor_ref` |
| G8 | 删除对标记录 | DELETE `/competitor-refs/{ref_id}` | 204 + activity_log `delete competitor_ref` |

---

## 2. 边界场景（8 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 竞品名为空 | `display_name=""` | 422（Pydantic min_length） |
| E2 | 竞品名超长 | display_name > 128 字符 | 422 Pydantic 校验 |
| E3 | website_url 超长 | > 512 字符 | 422 Pydantic 校验 |
| E4 | 引用不存在竞品创建对标 | `competitor_id` 不存在 | 404 `COMPETITOR_NOT_FOUND` |
| E5 | 引用跨项目竞品 | `competitor_id` 属于 projectB，但在 projectA 下建对标 | 422 `COMPETITOR_CROSS_PROJECT` |
| E6 | 重复关联同一竞品 | 同一 (node_id, competitor_id) 二次 POST | 409 `COMPETITOR_REF_DUPLICATE` |
| E7 | 删除有对标记录的竞品 | DELETE 有 ref 的竞品 | ⚠️ 待 CY 裁决：A. 级联删（204）/ B. 422 阻止；设计选 A（Prism onDelete cascade），需确认 |
| E8 | pros_and_cons 格式非法 | `pros_and_cons={"pros": "not-a-list"}` | 422 Pydantic 类型校验 |

---

## 3. 并发场景

**无并发场景**——05-module-catalog 标注 M06 并发=❌。

理由：竞品录入属于低频手动操作，没有多人同时编辑同一对标记录的典型业务场景；系统不引入乐观锁。

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读竞品列表 | userA 用 projectA token 访问 projectB 竞品列表 | 403 `PERMISSION_DENIED`（Router 层拦） |
| T2 | 越权读对标记录 | A 用 projectA 路径访问 projectB node 的对标列表 | 403 `PERMISSION_DENIED` |
| T3 | DAO 单元测试 tenant 过滤 | `competitor_dao.list_by_project(other_project_id)` | 返回空 list |
| T4 | DAO refs 单元测试 tenant 过滤 | `competitor_dao.list_refs_by_node(node_id, other_project_id)` | 返回空 list |
| T5 | 跨项目竞品引用（Service 层）| Service 创建对标时 competitor_id 属于 projectB | 422 `COMPETITOR_CROSS_PROJECT`（Service 层 _check_competitor_belongs_to_project） |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录读竞品列表 | 401 `UNAUTHENTICATED` |
| P2 | viewer 创建竞品 | 403 `PERMISSION_DENIED`（POST 要求 editor） |
| P3 | viewer 读取对标列表 | 200（只读允许 viewer） |
| P4 | editor 删除竞品（有对标记录）| 204 + 级联删对标记录（若选候选 A） |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | 竞品不存在 | `{"error": {"code": "COMPETITOR_NOT_FOUND", "message": "..."}}` |
| ER2 | 对标记录重复 | `{"error": {"code": "COMPETITOR_REF_DUPLICATE", "message": "..."}}` |
| ER3 | 跨项目竞品引用 | `{"error": {"code": "COMPETITOR_CROSS_PROJECT", "message": "..."}}` |
| ER4 | pros_and_cons 格式错误 | `{"error": {"code": "VALIDATION_ERROR", "details": {...}}}` ← Pydantic 标准响应 |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤（两个 DAO 方法） |
| Service | ≥ 90% | 含跨项目竞品检查 + 级联删逻辑 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 竞品列表 + 对标卡片渲染 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码：`design/01-engineering/01-engineering-spec.md` 规约 7
- Prism 对照：`/root/cy/prism/web/src/db/schema.ts`（competitors + competitorReferences）
