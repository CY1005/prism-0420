---
title: M09 全局搜索 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M09
prism_ref: F9
---

# M09 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> CY 2026-04-21 已 ack A-4/A-5/A-6/C-1/C-2/C-3（均候选 A），本测试基于：仅成员 project IN 过滤 + ILIKE + created_at DESC 排序 + M14 默认聚合。

---

## 1. Golden Path（8 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 关键词命中节点名称 | 编辑者 → GET `/search?q=支付` | 200 + items 含 result_type=node 且 title 包含"支付" + snippet 高亮 |
| G2 | 关键词命中维度内容 | 搜索含某个维度记录内容的关键词 | 200 + items 含 result_type=dimension_record + snippet 截取上下文 |
| G3 | 关键词命中竞品备注 | 搜索某竞品 notes 中的关键词 | 200 + items 含 result_type=competitor |
| G4 | 关键词命中问题描述 | 搜索某 issue title/description 中的关键词 | 200 + items 含 result_type=issue |
| G5 | 关键词命中关联备注 | 搜索某 module_relation notes 中的关键词 | 200 + items 含 result_type=module_relation |
| G6 | 混合结果（跨多类型） | 关键词在多种类型中都命中 | 200 + items 包含多种 result_type + 分页信息正确 |
| G7 | 分页正确性 | GET `/search?q=x&page=2&page_size=5` | 200 + items 长度 ≤ 5 + total 正确 + 结果不重复首页 |
| G8 | 指定 project 搜索 | GET `/projects/{pid}/search?q=x` | 200 + items 全部属于该 project |

---

## 2. 边界场景（8 条）

| ID | 场景 | 输入 | 期望 |
|----|------|------|------|
| E1 | 空关键词 | `q=` 或 `q=  ` | 422 `SEARCH_QUERY_TOO_SHORT`（Pydantic 校验） |
| E2 | 超长关键词 | `q=` 超 200 字符 | 422 `SEARCH_QUERY_TOO_LONG` |
| E3 | 无匹配结果 | 搜索不存在的词 | 200 + `{"items": [], "total": 0}` （不报错） |
| E4 | page 越界 | `page=9999` | 200 + items=[]（最后一页后返回空，不报 404） |
| E5 | page_size 超上限 | `page_size=101` | 422（Pydantic Field max 校验） |
| E6 | SQL 注入字符 | `q='; DROP TABLE nodes; --` | 200 + 安全（Pydantic + ORM 参数化，不拼 SQL） |
| E7 | 包含通配符 | `q=%payment%` | 200（ILIKE 中 `%` 被转义，不作为通配符处理） |
| E8 | 搜索全局 industry_news | 关键词匹配 industry_news.title | 200 + items 含 result_type=industry_news + project_id=null |
| E9 | JSONB key 名假阳性（CY ack 接受边界，A-6）| 关键词 = dimension_records JSONB key 的名字（如"value"）；内容中无实际业务匹配 | 200 + items 可能出现 result_type=dimension_record 假阳性命中；测试确认不报错、不崩溃；此边界已 CY ack 接受 |

---

## 3. 并发场景

> **M09 纯读聚合，无状态写操作，无并发场景。**

显式声明（按 README §14 要求）：M09 所有操作为只读 GET，不涉及资源竞争、乐观锁、幂等键，并发 100 次相同查询仅影响性能（不在本阶段验证），不存在数据一致性并发问题。

性能基准（可选，非强制）：
- 单 project / 1000 节点 / ILIKE 查询响应时间 < 500ms
- 10 个 project / 并发 10 个搜索请求 → P95 < 1s

---

## 4. Tenant 隔离（6 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 越权读取（全局搜索） | userA 无成员身份的 projectB 有匹配节点 | 200 + items 中不出现 projectB 的内容（IN 过滤生效） |
| T2 | IN 过滤覆盖测试 | 单元测试 `SearchService.search(query="x", user_id=userA)`（mock 上游各模块 search_by_keyword 只接受 project_ids=[projectA_id]），DB 有 projectB 的匹配节点 | 返回结果不含 projectB 数据（ADR-003 规则 1：各上游 Service 自身 tenant 过滤）|
| T3 | 多 project 成员合并搜索 | userA 是 projectA + projectB 成员，关键词在两个 project 都命中 | 200 + items 同时包含两个 project 的结果 + project_name 区分 |
| T4 | 指定 project 越权 | userA 无成员身份，GET `/projects/{projectB_id}/search?q=x` | 403 `SEARCH_PROJECT_ACCESS_DENIED` |
| T5 | 用户 role 降级后搜索 | userA 被移出 projectB 后搜索 | 200 + 结果不再包含 projectB 内容（实时查 project_members，无缓存延迟） |
| T6 | industry_news 不过滤 | 搜索命中 industry_news 内容 | 200 + items 含 industry_news 条目（project_id=null，无 tenant 限制） |

---

## 5. 权限场景（4 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦） |
| P2 | viewer 可搜索（全局） | 200（GET /search 只需登录，不需要 project 角色） |
| P3 | viewer 可搜索（指定 project） | 200（viewer 有 project 访问权限） |
| P4 | session 过期 | 401 `TOKEN_EXPIRED` |

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式 |
|----|------|------------|
| ER1 | 空关键词 | `{"error": {"code": "SEARCH_QUERY_TOO_SHORT", "message": ...}}` |
| ER2 | 超长关键词 | `{"error": {"code": "SEARCH_QUERY_TOO_LONG", "message": ...}}` |
| ER3 | 指定 project 无权限 | `{"error": {"code": "SEARCH_PROJECT_ACCESS_DENIED", "message": ...}}` |
| ER4 | DB 查询异常（超时/断连） | `{"error": {"code": "INTERNAL_ERROR", "message": "Search temporarily unavailable"}}` ← 不暴露 SQL |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| **M09 无 DAO 层**（ADR-003 规则 1：通过上游 Service 读取）| N/A | 上游 Service `search_by_keyword` 的 tenant 过滤由各自模块（M03/M04/M06/M07/M08/M14）各自的测试覆盖 |
| Service | ≥ 90% | 含 accessible_project_ids 获取 + 6 个上游 Service 聚合（含 M14 无 project_id 例外分支）+ 分页 + snippet 生成 + ILIKE 通配符转义 |
| Router | ≥ 80% | 主要走 e2e（依赖真实上游 Service）|
| Component | ≥ 70% | 搜索栏 debounce + 结果渲染 + 高亮标记 |

---

## 8. 跨模块 Read 聚合方案说明（ADR-003 已定）

CY 2026-04-21 ack 采纳 ADR-003 规则 1（各模块 Service 提供 `search_by_keyword()` 接口，M09 聚合）。

本测试文件基于此方案：DAO 层测试改为对各模块 Service mock 测试；Service 层测试验证聚合逻辑。G1-G9 Golden Path / Edge 测试行为不受影响。

---

## 9. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 跨模块搜索接口：待 ADR-003 决策后各模块补充 `search_by_keyword()` 接口定义
- 对照：Prism F9 现状（`/root/cy/prism/api/routers/`，参考不直接抄）
