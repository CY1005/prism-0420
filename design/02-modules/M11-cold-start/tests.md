---
title: M11 冷启动支持 - 测试场景
status: draft
owner: CY
created: 2026-04-21
accepted: null
module_id: M11
---

# M11 测试场景

> 主设计文档：[`00-design.md`](./00-design.md)
> 测试用例命名遵循规约 6（中文允许）+ pytest 标准。
> **R14-1**：所有用例基于 CY 2026-04-21 ack 决策编写（G2/G6：全量回滚/无 idempotency）。

---

## 1. Golden Path（5 条）

| ID | 场景 | 步骤 | 期望 |
|----|------|------|------|
| G1 | 上传合法 CSV 完整流程 | 编辑者 → POST `/cold-start/upload` 含合法 CSV（含节点路径 / 维度内容 / 竞品 / 问题）| 200 + status=completed + success_rows=N + activity_log `cold_start.completed` |
| G2 | 仅节点路径（无维度/竞品/问题列）| 上传只含节点路径列的最小 CSV | 200 + completed + nodes 创建成功 + dimensions/competitors/issues 为 0 |
| G3 | 查询任务详情 | 导入完成后 GET `/cold-start/{task_id}` | 200 + task_id + status=completed + success_rows + completed_at 非 null |
| G4 | 下载 CSV 模板 | 编辑者 GET `/cold-start/template` | 200 + Content-Type text/csv + 包含标准列头 |
| G5 | 查询项目任务列表 | 导入 2 次后 GET `/cold-start` | 200 + items 含 2 条 + 按 created_at 倒序 |

---

## 2. 边界场景（8 条）

| ID | 场景 | 输入 | 期望错误 |
|----|------|------|---------|
| E1 | 空 CSV（0 行数据）| 仅含列头行的 CSV | 422 `COLD_START_CSV_INVALID`（无数据行） |
| E2 | CSV 缺必填列（节点路径缺失）| 无 `node_path` 列 | 422 `COLD_START_CSV_INVALID`（缺必填列头） |
| E3 | 单行节点路径为空 | 第 2 行 `node_path` 列为空字符串 | 422 `COLD_START_ROW_VALIDATION_FAILED`（row=2, field=node_path） |
| E4 | 节点路径格式错误（非 `/` 分隔）| `node_path=产品线>模块>功能项` | 422 `COLD_START_ROW_VALIDATION_FAILED`（row=N, field=node_path, message=invalid format） |
| E5 | 超过文件大小限制 | 上传 > 10MB 的 CSV | 413 `COLD_START_FILE_TOO_LARGE` |
| E6 | 字段含特殊字符（SQL 注入尝试）| `node_path="'; DROP TABLE nodes;--"` | 422 行校验失败或正常入库（Pydantic/ORM 防注入，不执行 SQL） |
| E7 | 超长字段值 | `summary` > 5000 字符 | 422 `COLD_START_ROW_VALIDATION_FAILED`（field=summary, too long） |
| E8 | 竞品列引用不存在的节点路径 | `competitor.node_path` 指向 CSV 内不存在的路径 | 422 `COLD_START_ROW_VALIDATION_FAILED`（节点路径引用失效） |

---

## 3. 并发场景（4 条）

| ID | 场景 | 模拟方式 | 期望 |
|----|------|---------|------|
| C1 | 同用户同项目重传同 CSV（G2/G6：无 idempotency）| 上传 csv-A → completed；再次上传同 csv-A 到同 project | 第二次创建新任务并执行（无 idempotency 复用）；nodes 表会产生重复节点——已知行为，用户自行管理 |
| C2 | 同用户不同项目传同 CSV | 上传 csv-A 到 project-A → completed；再次上传同 csv-A 到 project-B | project-B 新建独立任务，各自独立入库（无 idempotency，各 project 隔离） |
| C3 | 不同用户同项目并发上传不同 CSV | userA 上传 csv-A，userB 同时上传 csv-B 到同项目 | 两个任务各自成功，互不影响 |
| C4 | 不同用户同项目并发上传包含相同节点路径的 CSV（G7-M11-R2-08）| userA 上传含 `/产品线/功能A`，userB 同时上传也含 `/产品线/功能A` | 两个任务各自成功；M03 nodes 表产生同名重复节点（无 UNIQUE(project_id, path) 约束）；**已知行为：用户自行解决重名**（业务决策，不技术约束） |

---

## 4. Tenant 隔离（5 条）

| ID | 场景 | 模拟 | 期望 |
|----|------|------|------|
| T1 | 跨项目越权上传 | userA 持有 projectA token，POST 到 projectB 的上传接口 | 403 `PERMISSION_DENIED`（Router `check_project_access` 拦） |
| T2 | 越权查询任务 | userA 查询 userB 在 projectB 的 task_id | 404 `NOT_FOUND`（DAO project_id 过滤，不暴露 forbidden） |
| T3 | DAO tenant 过滤单元测试 | `ColdStartDAO.list_by_project(other_project_id)` | 返回空 list（tenant 过滤生效） |
| T4 | URL 路径篡改 | path 是 projectA，body 含 projectB 的节点路径引用 | Service 拒绝（节点 project_id 校验） |
| T5 | viewer 角色上传 | viewer 调 POST upload | 403 `PERMISSION_DENIED`（Router 要求 ≥editor） |

---

## 5. 权限场景（3 条）

| ID | 场景 | 期望 |
|----|------|------|
| P1 | 未登录上传 | 401 `UNAUTHENTICATED`（Server Action session 校验） |
| P2 | session 过期后上传 | 401 `TOKEN_EXPIRED` |
| P3 | role 降级中上传 | editor → 降为 viewer → 再次上传 | 403 `PERMISSION_DENIED` |

---

## 6. 错误处理（7 条）

| ID | 场景 | 期望响应格式（规约 7） |
|----|------|----------------------|
| ER1 | 校验失败（全量回滚模式）| `{"error": {"code": "COLD_START_ROW_VALIDATION_FAILED", "message": "...", "details": [{row, field, message}]}}` |
| ER2 | 批量入库事务异常（DB 错误）| `{"error": {"code": "COLD_START_BATCH_INSERT_FAILED", "message": "Batch insert failed; transaction rolled back"}}` + nodes/dimensions 无残留 |
| ER3 | NodeService 失败（跨模块 Service 异常）| M11 wrap 为 `COLD_START_BATCH_INSERT_FAILED`（R13-2 跨模块 wrap） + 全量回滚 |
| ER4 | M06 失败而 M03/M04 已执行（G7-M11-R2-07 四步回滚专项）| 顺序：M03 成功 → M04 成功 → M06 抛异常 → 全量回滚 | 422/500 `COLD_START_BATCH_INSERT_FAILED` + `db.begin()` 事务回滚 → M03 nodes 无残留 + M04 dimension_records 无残留 + M06/M07 无残留（事务内所有操作原子回滚，4 步全撤销） |
| ER5 | M07 失败而 M03/M04/M06 已执行（四步最后一步失败）| 顺序：M03→M04→M06 成功 → M07 抛异常 | 全量回滚，M03/M04/M06/M07 均无残留（同一 `db.begin()` 事务） |
| ER6 | 终态任务重触发 | 对 completed 任务重 POST upload | 409 `COLD_START_TASK_FINALIZED` |
| ER7 | 非法文件类型 | 上传 .xlsx 而非 .csv | 422 `COLD_START_CSV_INVALID`（非 text/csv MIME 类型） |

---

## 7. 测试覆盖率目标

| 层 | 覆盖率目标 | 备注 |
|----|----------|------|
| DAO | ≥ 95% | 含 tenant 过滤每条分支 |
| Service | ≥ 90% | 含事务回滚路径 + 状态机转换 + orchestrator 调用链 |
| Router | ≥ 80% | 主要走 e2e |
| Component | ≥ 70% | CSV 上传 UI + 错误行展示 |

---

## 8. 测试要点

- pytest + asyncio（同 M04 模式）
- **DB 用真实 PG 不 mock**（integration 测试不 mock DB，CY feedback 统一原则）
- CSV 解析用 `io.StringIO` 构造测试用 CSV 流，不依赖真实文件
- 并发测试 C3 用 `asyncio.gather()` 模拟同时上传
- 重传测试 C1/C2 用相同 SHA256(file_bytes) 构造 CSV（G2/G6 无 idempotency，每次新建任务）

---

## 9. 关联

- 设计：[`00-design.md`](./00-design.md)
- 错误码定义：`design/01-engineering/01-engineering-spec.md` 规约 7
- M04 tests 范本：`design/02-modules/M04-feature-archive/tests.md`
