---
title: M02 项目管理 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M02
---

# M02 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **CY 2026-04-21 已 ack 8 组决策，本文件依据 G2/G3/G7 更新。**

---

## 1. Golden Path（7 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 创建项目（多表事务） | owner → POST `/api/projects` 含 name + template_type="custom" | 201 + projects 行 + project_members 行（role=owner）+ project_dimension_configs 初始行 + activity_log `create` 一条 |
| G2 | 列出当前用户项目 | GET `/api/projects` | 200 + items 只含当前用户是成员的项目 |
| G3 | 邀请成员（多表事务） | owner → POST `/api/projects/{pid}/members` body `{user_id, role="editor"}` | 201 + project_members 新行 + activity_log `invite_member` 一条 |
| G4 | 变更成员角色 | owner → PUT `/api/projects/{pid}/members/{uid}` body `{role="viewer"}` | 200 + role 更新 + activity_log `update_member_role` 一条（含 old_role/new_role） |
| G5 | 归档项目 | owner → POST `/api/projects/{pid}/archive` | 200 + status=archived + activity_log `archive` 一条 |
| G6 | 更新维度配置 | owner → PUT `/api/projects/{pid}/dimension-configs` 含批量配置 | 200 + configs 更新 + activity_log `update_dimension_config` 一条 |
| G7 | 移除成员 | owner → DELETE `/api/projects/{pid}/members/{uid}` | 204 + project_members 行删除 + activity_log `remove_member` 一条 |

---

## 2. 边界场景（10 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 项目名为空 | `name=""` | 422 `VALIDATION_ERROR`（Pydantic min_length=1 拦截） |
| E2 | 项目名超长 | `name` 超 200 字符 | 422 `VALIDATION_ERROR` |
| E3 | hierarchy_labels 格式错误 | `hierarchy_labels=["a", 1, null]` | 422 `VALIDATION_ERROR`（list[str] 类型校验失败） |
| E4 | AI Key 传入（加密路径） | PUT `/api/projects/{pid}` 含 `ai_api_key="sk-xxx"` | 200 + ai_api_key_enc 字段加密存储，响应体不含明文 key |
| E5 | 邀请不存在的用户 | `user_id` = 不存在 UUID | 404 `NOT_FOUND`（UserNotFoundError wrap 为本模块） |
| E6 | 重复归档已归档项目 | archive 已 archived 项目 | 409 `PROJECT_ALREADY_ARCHIVED` |
| E7 | 批量维度配置含不存在的 dimension_type_id | configs 含无效 type_id | 422 `DIMENSION_CONFIG_INVALID` |
| E8 | 同 owner 同名 active 项目冲突（G3-a）| 同 owner 创建同名第二个项目（两者均 active） | 409 `PROJECT_NAME_DUPLICATE`（部分唯一索引命中） |
| E9 | 同 owner 同名但原项目已归档（G3-b）| owner 归档项目 A，再创建同名项目 A | 201 成功（归档后释放名字，部分唯一索引仅对 active 生效） |
| E10 | 不同 owner 同名项目（G3-c）| userA 和 userB 各创建同名项目 | 两者均 201 成功（不同 owner，无约束冲突） |

---

## 3. 并发场景（4 条）

> M02 catalog 标注：并发 ❌，但归档状态转换需验证幂等安全性；邀请操作需验证 DB UNIQUE 竞态。

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 两个管理员同时归档同一项目 | `asyncio.gather()` 并发两次 POST `/archive` | 第一个 200 status=archived；第二个 409 `PROJECT_ALREADY_ARCHIVED`（不报 500，不丢数据） |
| C2 | 两个管理员同时移除不同成员 | 并发 DELETE 两个不同 user_id | 两者均 204（不同行，无冲突） |
| C3 | 并发邀请同一用户（G7-M02-R2-01）| owner 两个 tab 同时 POST 邀请同一 user_id | 第一个 201 + activity_log；第二个 409 `MEMBER_ALREADY_EXISTS`（DB UNIQUE(project_id, user_id) 竞态，不报 500） |
| C4 | 并发更新 AI Key（G7-M02-R2-03）| owner 两个 tab 同时 PUT AI Key（无乐观锁）| last-write-wins：最后到达的请求的 Key 生效；两次都返回 200；说明：无乐观锁，AI Key 更新是 last-write-wins 语义，用户需自行确认最终值 |

**实现要点**：
- 使用真实 PG 事务测试，不 mock DB
- C1 验证归档为幂等操作（先成功后幂等返回 409 业务错误，不 500）
- C3 验证 DB UNIQUE 约束竞态安全（两次并发同一 user_id 邀请只有一条记录）
- C4 说明 last-write-wins 语义，无乐观锁保护

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 非成员读取项目详情 | userB 无任何 project_members 记录，访问 projectA | 403 `PERMISSION_DENIED`（Router `check_project_access` 拦） |
| T2 | 非成员邀请成员 | userB 不是成员，POST `/members` | 403 `PERMISSION_DENIED` |
| T3 | DAO 过滤测试 | 单元测试 `ProjectDAO.list_by_user(userB_id)`，userB 只有 projectB 成员资格 | 返回列表中不含 projectA（tenant 过滤生效） |
| T4 | editor 尝试邀请成员 | role=editor 的 userB 调 POST `/members` | 403 `PERMISSION_DENIED`（节 8 Service 层细粒度检查：邀请需 owner） |
| T5 | 跨项目成员查询 | userA 查 projectB 的 `/members` | 403（Router 层拦，userA 非 projectB 成员） |

---

## 5. 权限场景（5 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | editor 修改维度配置 | 403 `PERMISSION_DENIED`（节 8：维度配置修改需 owner） |
| P3 | viewer 更新项目信息 | 403 `PERMISSION_DENIED` |
| P4 | owner 移除自己 | 422 `MEMBER_CANNOT_REMOVE_OWNER`（Service 层拦） |
| P5 | 角色降级后操作 | userA 从 editor 降为 viewer，再次调 PUT 接口 → 403 |

---

## 6. 错误处理（5 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | 邀请已有成员（DB UNIQUE 冲突） | `{"error": {"code": "MEMBER_ALREADY_EXISTS", "message": "..."}}` 409 |
| ER2a | 创建项目时 project_members(owner) 写入失败（事务回滚）| 500 + projects 行无残留 + project_members 无残留行（4 步事务全量回滚：INSERT projects → INSERT members → INSERT dimension_configs → log activity，任一步失败全回滚） |
| ER2b | 创建项目时 project_dimension_configs 写入失败（G7-M02-R2-02）| 模拟 dimension_configs INSERT 时抛 DB 异常 | 500 + projects / project_members / project_dimension_configs 均无残留行（同一事务，回滚覆盖已写入的 projects + members） |
| ER3 | 项目不存在 | `{"error": {"code": "PROJECT_NOT_FOUND", "message": "..."}}` 404 |
| ER4 | AI Key 加密失败 | `{"error": {"code": "AI_KEY_ENCRYPT_FAILED", "message": "..."}}` 500 |
| ER5 | 未识别 IntegrityError | `{"error": {"code": "CONFLICT", ...}}` ← 兜底，不暴露 SQL 细节 |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤每条分支 |
| Service | ≥ 90% | 含事务回滚路径（创建事务 + 邀请事务） |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | 项目卡片 + 成员列表 + 权限按钮可见性 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- Prism 对照参考：`/root/cy/prism/web/src/db/schema.ts`（projects / projectMembers）
