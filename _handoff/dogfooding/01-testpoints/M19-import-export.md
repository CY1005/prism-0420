---
module: M19
name: import-export
created: 2026-05-12
generator: P1-testpoint subagent
references:
  - design/02-modules/M19-import-export/00-design.md
  - design/02-modules/M19-import-export/tests.md
  - design/00-architecture/01-PRD.md
  - design/00-architecture/06-design-principles.md
prd_ref: F19 / US-C1.6（查看者导出模块分析报告 Markdown）
---

# M19 导入/导出 测试点

## 业务流程（H1 / 1 行概述）

M19 本期只做 Markdown 报告导出（无导入，导入归 M11/M17）：入口 A 多 node POST `/api/projects/{pid}/exports`（≤20）+ 入口 B 单 node POST `/api/projects/{pid}/nodes/{nid}/export` 共享 ExportService，只读聚合上游 M03-M07 DAO 拼 Markdown，viewer 即可导出，导出后写 activity_log action_type="exported" target_type=node。

## 测试点（H2 / 按 15 角度）

### 1. 功能性

- [P0] 入口 B 单 node POST `/projects/{pid}/nodes/{nid}/export` 返 200 + Content-Type=text/markdown + Content-Disposition: attachment; filename="prism-export-{timestamp}.md"（design §7 + tests.md G1）
- [P0] 入口 A 多 node POST `/projects/{pid}/exports` node_ids=[a,b,c] 返 200 + Markdown 含 3 个 `## {node_name}` 章节（design §7 + tests.md G2）
- [P0] include 全开 dimensions/versions/competitors/issues=true Markdown 同时含 4 节内容（design §7 ExportIncludeOptions + tests.md G3）
- [P0] 导出成功后 activity_log 写一条 action_type="exported" / target_type="node" / target_id=node_ids[0] / metadata 含 node_ids+node_count+sections+file_size_bytes 全字段（design §10 metadata 字段集字面验 + §14.5 范式 + tests.md G5）
- [P1] include 部分开 versions=false + competitors=false Markdown 仅含维度+问题章节不含版本/竞品（design §7 + tests.md G4）
- [P1] 入口 B 单 node 与入口 A node_ids=[同一 nid] 返相同 Markdown 内容（service generate_markdown 共享逻辑，design §7 接口 + tests.md G6）
- [P1] include 默认值 competitors=false 不在 Markdown 输出竞品章节（design §7 ExportIncludeOptions default + tests.md G4）
- [P1] Markdown 报告首行含 `# 分析报告 — {project_name}` + 元信息行 `> 生成时间：{datetime} 导出者：{user_name}`（design §7 Markdown 结构）
- [P1] 每个 node 章节含 `> 路径：{node_path}` 元行（design §7 Markdown 结构）
- [P1] 版本时间线渲染为 Markdown 表格（| 版本号 | 变更类型 | 描述 | 日期 |），design §7 Markdown 结构
- [P1] 竞品参考渲染为 Markdown 表格（| 竞品名称 | 版本 | 覆盖情况 | 优劣势 |），design §7 Markdown 结构
- [P1] 问题沉淀渲染为 Markdown 表格（| 类型 | 标题 | 状态 |），design §7 Markdown 结构
- [P2] 文件名 timestamp 段落非空且符合 ISO 时间格式 / 同一秒内两次导出可同名不影响下载（design §7 filename 模板）

### 2. 边界 / 数据

- [P0] 入口 A node_ids 含 21 个 UUID 返 422 EXPORT_NODE_LIMIT_EXCEEDED（design §7 max_length=20 + §13 + tests.md E1）
- [P0] 入口 A node_ids=[] 空数组返 422 VALIDATION_ERROR（Pydantic min_length=1，design §7 + tests.md E2）
- [P0] 全部 node 无维度/版本/竞品/问题任何内容返 422 EXPORT_EMPTY_CONTENT（design §13 + tests.md E4 R1-A P1-1 立修）
- [P1] node_ids 恰好 20 个边界值返 200 不触发 LIMIT_EXCEEDED（design §7 max_length=20 含端点）
- [P1] node_ids=[a,a,b] 含重复 UUID 去重后返 200 仅 2 个 node 章节不报错（tests.md E5）
- [P1] 单个 node 未填维度但 include.dimensions=true 返 200 维度区块显示"（暂无内容）"占位（design §7 + tests.md E3）
- [P1] node_id 入参非合法 UUID 返 422（Pydantic UUID 类型校验，design §7）
- [P1] include 字段未传走默认值 dimensions=true/versions=true/competitors=false/issues=true（design §7 ExportIncludeOptions default + tests.md G4）
- [P1] include 含 forbid 之外的额外字段（如 reports=true）按 Pydantic 默认 ignore 不报错（design §7 schema 未声明 extra=forbid，与 M01 严格 schema 区分）
- [P2] node_ids=[1 个] 入口 A 单元素合法返 200（min_length=1 端点）

### 3. 异常 / 错误

- [P0] node_ids 含已软删除 node 返 422 EXPORT_NODE_NOT_IN_PROJECT（design §13 + tests.md E6 R1-B P1-1 立修 / Service _validate_and_load_nodes 拦）
- [P0] project_id URL 不存在返 NOT_FOUND 404（design §13 + tests.md ER4）
- [P0] write_event 写 activity_log 抛异常时整体导出不阻塞用户拿到 Markdown（design §10 非事务 / §14.5 write_event 异常传播 e2e 字面验范式）
- [P1] DAO 上游 DimensionDAO.list_by_node 抛 DB 异常返 INTERNAL_ERROR 500 不暴露 SQL stacktrace（design §13 兜底 + tests.md ER3）
- [P1] 错误响应统一壳 `{"error": {"code": "EXPORT_NODE_LIMIT_EXCEEDED", "message": "..."}}`（design §13 + tests.md ER1）
- [P1] EXPORT_NODE_NOT_IN_PROJECT 错误响应 message="One or more nodes do not belong to this project"（design §13 + tests.md ER2）
- [P2] 大 node 数（20 个全填满）响应未超时即可（design §1 灰区 3 决策同步可控）

### 4. 权限 / Auth

- [P0] 未登录无 Authorization 调任一 endpoint 返 401 UNAUTHENTICATED（design §8 Server Action 层 + tests.md P1）
- [P0] viewer 角色调 POST exports 返 200（design §8 决策 viewer 即可导出 + tests.md P2/T5）
- [P0] 非项目成员（无 viewer/editor/owner 任一角色）返 403 PERMISSION_DENIED（design §8 Router check_project_access + tests.md P3）
- [P0] session 过期 access token 失效返 401 TOKEN_EXPIRED（design §8 + tests.md P4）
- [P1] viewer 通过 POST 写 activity_log 不触发 viewer 写权限拦截（design §14.5 范式：POST 但语义只读 + activity_log 副作用不算"业务写"）
- [P1] editor 角色调 POST exports 返 200（design §8 viewer 及以上均可）
- [P1] owner 角色调 POST exports 返 200（design §8 viewer 及以上均可）

### 5. Tenant 隔离

- [P0] userA 有 projectA 权限调 POST `/projects/projectB/exports` 越权返 403 PERMISSION_DENIED（design §8 Router check_project_access + tests.md T1）
- [P0] URL projectA + node_ids 实际属 projectB 返 422 EXPORT_NODE_NOT_IN_PROJECT（design §8 Service 第三层 + tests.md T2 R1-B 立修）
- [P0] 混合 node_ids=[projectA_node, projectB_node]（仅有 projectA 权限）返 422 EXPORT_NODE_NOT_IN_PROJECT 任一不符即拦（design §8 + tests.md T4）
- [P1] DimensionDAO.list_by_node(node_id=projectB_node, project_id=projectA_id) 返空 list（DAO 内置 WHERE project_id=? tenant 过滤，design §9 + tests.md T3）
- [P1] VersionDAO/CompetitorDAO/IssueDAO 同样 project_id 过滤跨项目返空 list（design §9 复用各模块 DAO + tests.md T3 扩展）
- [P1] 跨项目越权场景写 activity_log 的 target_id 与 metadata.node_ids 全部属于 URL 实际 project（design §10 metadata 一致性）

### 6. 并发 / 乐观锁

- [P1] 同一 user 并发两次 POST /export（asyncio.gather）两次都 200 各自独立 Markdown 不互相阻塞（design §5 只读无并发控制 + tests.md C1）
- [P1] 导出 node_a 时另一 user 同时 PATCH M04 dimension_record 导出读到编辑前或后快照均 200 不死锁（design §5 + tests.md C2）
- [P2] 同时 10 个 viewer 并发导出同一 node 全部 200 / activity_log 写入 10 条 exported 事件（design §5 只读 + §10）

### 7. 数据完整性 / 契约

- [P0] activity_log target_type 字段值字面等于 `"node"` 不是 `"project"`（design §10 决策让 M15 数据流转精确定位 + §14.5 字段集字面验）
- [P0] activity_log action_type 字段值字面等于 `"exported"` 过去式（design §10 R1 立修 + §14.5 R14 过去式立规对齐 / ActionType+1）
- [P0] activity_log metadata.node_count 等于实际导出 node 去重后数量（design §10 + tests.md E5 去重场景验证）
- [P0] activity_log metadata.sections 字段含 dimensions/versions/competitors/issues 四 bool 反映本次 include 选项（design §10 sections 字段定义 + §14.5 metadata 字段集字面验）
- [P0] activity_log metadata.file_size_bytes 等于响应 body bytes 长度（design §10 + §14.5）
- [P1] activity_log metadata.node_ids 数组 == 入参 node_ids（去重后）含原顺序（design §10）
- [P1] _ACTION_TYPES 枚举守护（ci-lint R14）含 "exported" 字面值 / service write_event(action_type="exported") 不漂移（design §14.5 R14 + R1 立修）
- [P1] ActionType+1 同步 4 处（model tuple + schema StrEnum + CHECK constraint + Alembic migration）（design §14.5 范式 4 处同步）
- [P1] Alembic CHECK 约束更新后 INSERT action_type="export"（旧形式无 d）失败 / "exported" 成功（design §14.5 + R1）
- [P2] 旧版本 activity_log 中 export action_type 无影响（M19 sprint 之前 activity_log 表为空，design §14.5 R1 立修阶段历史无数据）

### 8. UI / UX

- [P1] B 入口档案页右上角"导出"按钮可见且单击触发 Server Action `actions/export.ts`（design §6 分层 + Component export-button.tsx）
- [P1] A 入口模块树 / 全景图多选节点后"导出报告"按钮可点击（design §6 node-selector.tsx）
- [P1] 浏览器收到 Content-Disposition attachment 触发文件下载而非 inline 显示（design §7 attachment 字面 + §14.5 二进制响应契约纪律）
- [P1] 下载文件后缀 .md（filename 含 ".md"）非 .txt / .markdown（design §7 filename 模板 prism-export-{ts}.md）
- [P2] 多选 21 个 node 前端 disable "导出报告"按钮并提示"最多 20 个"（design §1 上限 20）

### 9. 性能 / 容量

- [P1] 20 个 node 含全部章节同步导出响应 P95 ≤ 5s（design §1 灰区 3 决策 + §11 控制 node 数量上限响应可控）
- [P2] 大量历史 version_records（>100）的 node 导出 Markdown 表格行数与实际记录数匹配（design §7 + 性能边界）

### 10. Content-Disposition / 文件名 sanitize（M19 输出端首发）

- [P0] filename 含 UTF-8 兼容字符（如中文 project_name）通过 RFC 5987 编码 filename*=UTF-8''... 而非裸 ASCII（design §14.5 filename sanitize 输出端首发 / M11+M17 输入端范式复用）
- [P0] filename 中控制字符 \r \n \0 被 strip 不进 Content-Disposition header（design §14.5 sanitize 字面验）
- [P1] filename 超长（>255 字符）截断不超 Content-Disposition 单 header 上限（design §14.5 长度截断）
- [P1] filename 含 `"` `;` `\` 等 Content-Disposition 保留字符被转义不破坏 header 解析（design §14.5 sanitize 字面验）
- [P2] filename 中 path 分隔符 `/` `\` 被替换防客户端误用（design §14.5 sanitize）

### 11. activity_log write 失败传播（M16 立 / M19 范式复用）

- [P0] monkeypatch ActivityDAO.log raise IOError 导出主路径不阻塞用户拿到 Markdown 文件（design §10 非事务 + §14.5 write_event 异常传播 e2e 字面验范式）
- [P1] write_event 失败日志写 stderr 含 exported 事件信息（design §10 失败也留痕）
- [P1] write_event 失败不阻塞响应但响应内 Markdown 内容完整（design §10 非事务边界）

### 12. CI 守护 / 设计漂移防御

- [P1] ci-lint R14 grep 守护：service 层 write_event(action_type=...) 入参 _ACTION_TYPES 枚举内（design §14.5 R14 ci-lint 守护 / 不漂移）
- [P1] ci-lint R15 grep 守护：export_service 无 INSERT 业务表（M19 全只读 / 仅 activity_log）/ activity_log dao 已 catch IntegrityError 豁免（design §14.5 + 06-design-principles 清单 6）
- [P1] export_service 复用 DimensionDAO/VersionDAO/CompetitorDAO/IssueDAO/NodeDAO 5 个 DAO 通过 DI 注入 / 不自建 SQL（design §6 R-N 分层 + §9 复用决策）
- [P2] M19 不新建 SQLAlchemy model 不新建 export_dao.py（design §3 + §6）

### 13. 跨模块契约（M19 是只读消费者）

- [P1] DimensionDAO.list_by_node 签名稳定 node_id+project_id 返 List[DimensionRecord]（design §2 依赖契约 + §9）
- [P1] VersionDAO.list_by_node 签名稳定（design §2 依赖契约）
- [P1] CompetitorDAO.list_refs_by_node 签名稳定（design §2 依赖契约）
- [P1] IssueDAO.list_by_project node_id 过滤参数稳定（design §2 依赖契约）
- [P1] NodeDAO 校验 node 归属 project 接口稳定（design §2 + §8 Service _check_nodes_belong_to_project）

### 14. N/A 显式声明（design §14.5 范式）

- [P2] M19 无 idempotency_key 需求只读天然幂等（design §11 显式 N/A）
- [P2] M19 无 Queue 任务无异步处理（design §12 显式 N/A）
- [P2] M19 无状态实体无状态机（design §4 显式 N/A）
- [P2] M19 无乐观锁 version 字段只读（design §5 + 清单 2 N/A）
- [P2] M19 无 SSE / WebSocket / Background fire-and-forget 同步路由（design §14.5 N/A 范式）
- [P2] M19 输入无 multipart 仅输出 Content-Disposition / file.size sanitize N/A（design §14.5 N/A 范式）
