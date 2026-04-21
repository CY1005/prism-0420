---
title: M10 项目全景图 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M10
prism_ref: F10
---

# M10 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> M10 纯读聚合模块，无并发写冲突场景——并发场景节显式说明。
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。

---

## 1. Golden Path（6 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 查询项目全景图（含树 + 统计）| viewer → GET `/api/projects/{pid}/overview` | 200；tree 嵌套结构正确（父子关系）；每个 file 节点含 completion_rate；stats.total_nodes 正确 |
| G2 | file 节点完善度计算正确 | 项目启用 3 个维度；某 file 节点填了 2 条 dimension_records → GET overview | 该节点 filled_count=2，enabled_count=3，completion_rate≈0.667 |
| G3 | folder 节点显示子树均值 | folder 下 2 个 file 节点 completion_rate 分别 1.0 和 0.5 → GET overview | folder 节点 completion_rate=0.75（均值）；CY ack A-9 均值方案 |
| G4 | 单节点完善度查询 | editor → GET `/api/projects/{pid}/nodes/{nid}/completion` | 200；filled_count/enabled_count/completion_rate 准确 |
| G5 | 查询项目整体统计 | GET `/api/projects/{pid}/overview/stats` | 200；avg_completion_rate = 所有 file 节点均值；fully_complete_nodes 准确 |
| G6 | 完善度 0% 节点（空节点）| file 节点未填任何维度 → GET overview | filled_count=0，completion_rate=0.0；正常返回不报错 |

---

## 2. 边界场景（7 条）

| ID | 场景 | 输入 | 期望 |
|----|------|------|------|
| E1 | 空项目（无节点）| 新建项目，GET overview | 200；tree=[]；stats.total_nodes=0；avg_completion_rate=0.0 |
| E2 | 项目无启用维度 | 项目 project_dimension_configs 全部 enabled=false → GET overview | 422 `OVERVIEW_NO_DIMENSIONS`（分母=0，无法计算完善度）|
| E3 | 只有 folder 无 file | 树全是 folder 节点 | 200；stats.file_nodes=0；avg_completion_rate=0.0；folder 节点 completion_rate=0.0（无子 file 时均值为 0）|
| E4 | 所有节点完善度 100% | N 个 file 节点全部填满所有启用维度 | stats.fully_complete_nodes=N；avg_completion_rate=1.0 |
| E5 | 单节点查询 node 不存在 | GET `/api/projects/{pid}/nodes/{不存在 nid}/completion` | 404 `OVERVIEW_NODE_NOT_FOUND` |
| E6 | project 不存在 | GET `/api/projects/{不存在 pid}/overview` | 404 `OVERVIEW_PROJECT_NOT_FOUND` |
| E7 | 深层嵌套树（depth > 5）| 6 层深度 nodes → GET overview | 200；tree 嵌套正确；深度字段准确；性能不超时（< 2s，参考规约）|

---

## 3. 并发场景（M10 纯读，无并发写冲突场景）

**M10 是纯读模块，无状态写入，无并发冲突场景。**

显式说明：
- M10 不存在"两个用户同时写同一资源"的场景
- 多用户同时读全景图：各自独立 GET，结果一致（方案 A 实时 JOIN，无缓存失效问题）
- **读-写并发**（M04 更新 dimension_records 的同时 M10 读）：M10 读到的是查询时刻的快照，不需要锁；PG READ COMMITTED 隔离级别下正常工作

补充一条**读一致性验证**（非并发锁，而是业务逻辑验证）：

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| C1 | 编辑后全景图实时反映 | M04 更新某 file 节点填了第 N 个维度 → 立即 GET M10 overview | M10 返回的 filled_count 已包含新更新（方案 A 实时 JOIN，无缓存延迟）|

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权读 | userA 持 projectA token，GET `/api/projects/{projectB_id}/overview` | 403 `PERMISSION_DENIED`（Router check_project_access 拦）|
| T2 | 非成员读 | userC 不在 projectA 成员表，GET projectA overview | 403 / 404（Service 层 _check_project_access 拦；不暴露存在性）|
| T3 | DAO tenant 过滤覆盖——nodes | 单元测试 `overview_dao.list_nodes_with_fill_count(db, other_project_id)` | 返回空 list（nodes.project_id 过滤生效）|
| T4 | DAO tenant 过滤覆盖——dimension_records | 两个项目的 dimension_records 混在 DB；查 projectA | 只统计 projectA 的 dimension_records（dimension_records.project_id 过滤生效）|
| T5 | DAO tenant 过滤覆盖——project_dimension_configs | 两个项目启用不同数量维度 | 分母只计算目标 project 的启用维度数，不混入其他 project |

---

## 5. 权限场景（3 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录访问 | 401 `UNAUTHENTICATED`（Server Action 层拦）|
| P2 | viewer 角色正常读 | 200（全景图 viewer 权限即可，Router check_project_access(role="viewer") 通过）|
| P3 | session 过期 | 401 `TOKEN_EXPIRED`（Server Action 层拦）|

---

## 6. 错误处理（4 条）

| ID | 场景 | 期望响应格式（规约 7）|
|----|------|----------------------|
| ER1 | project 不存在 | `{"error": {"code": "OVERVIEW_PROJECT_NOT_FOUND", "message": "Project not found or access denied"}}` |
| ER2 | node 不存在（单节点接口）| `{"error": {"code": "OVERVIEW_NODE_NOT_FOUND", "message": "..."}}` |
| ER3 | 无启用维度 | `{"error": {"code": "OVERVIEW_NO_DIMENSIONS", "message": "Project has no enabled dimensions configured"}}` |
| ER4 | DB 超时（节点数量大）| 502 / 504；不暴露内部 SQL；观察项：若添加超时保护，ErrorCode 待后续精修阶段定 |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | tenant 过滤三张表每条分支（nodes / dimension_records / project_dimension_configs）|
| Service | ≥ 90% | 完善度计算逻辑 + folder 节点汇总均值 + 树形组装（flat → nested）|
| Router | ≥ 80% | 主走 e2e；含 viewer 权限正常返回 + 越权 403 |
| Component | ≥ 70% | 色块颜色映射逻辑 + 空树渲染 |

---

## 8. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- 上游 tenant 过滤参考：`M04-feature-archive/tests.md`（T1-T5 模式复用）
