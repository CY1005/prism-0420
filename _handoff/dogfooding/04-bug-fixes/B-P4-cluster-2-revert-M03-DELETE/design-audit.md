---
title: B-P4-cluster-2-revert design audit — A 路径 0 冲突
sprint: dogfooding
cluster: P4-cluster-2-revert
date: 2026-05-13
status: ZERO_CONFLICT (A 路径 / 修法跟 design 真相一致)
parent_audit: _handoff/dogfooding/04-bug-fixes/B-P4-cluster-2-M18-M03/design-audit.md (superseded for M03 DELETE 段)
---

# A 路径 design audit — M03 project DELETE 改 422 PROJECT_DELETE_NOT_SUPPORTED

## audit 范围

- M02 §1 / §4 / §13 design（项目模块字面规约）
- ErrorCode `PROJECT_DELETE_NOT_SUPPORTED` 留位（`api/errors/codes.py:44`）
- Exception `ProjectDeleteNotSupportedError(http_status=422)` 留位（`api/errors/exceptions.py:180-181`）

## audit 结果总览

**A 路径** = 修法与 design 真相一致 / 不动 design / 不动 ErrorCode / 不动 schema。

| # | 源 | 修法 vs design | 状态 |
|---|----|---------------|------|
| 1 | M02 §1 L117 「不物理删除——归档为不可逆终态（G2 决策）」 | service raise ProjectDeleteNotSupportedError 422 / endpoint 不物理删除 | ✅ 一致 |
| 2 | M02 §4 L503 禁止转换表「任何状态 → 物理删除 \| 抛 PROJECT_DELETE_NOT_SUPPORTED（422）」 | router 返 422 + body.code = "project_delete_not_supported" | ✅ 一致 |
| 3 | M02 §4 L479 状态机「archived --> [*] : 归档为不可逆终态」 | DB 数据保留 / 状态不变 | ✅ 一致 |
| 4 | M02 §13 ErrorCode + Exception 已留位（30+ commit 无 caller） | service 增 caller raise ProjectDeleteNotSupportedError / router endpoint 显式 422 OpenAPI 契约 | ✅ 一致（实装留位）|
| 5 | M03 §7 nodes.project_id ON DELETE CASCADE schema 约束 | schema 仍有效 / 由 DB 兜底（不通过 API 触发）/ 不删除 FK 配置 | ✅ 不影响 |

**冲突数：0**

## 与 cluster-2 design-audit 关系

cluster-2 (`B-P4-cluster-2-M18-M03/design-audit.md`) 识别了 4 HIGH + 1 MEDIUM 冲突但选错路径（保留物理删除代码 / 上报 CY 决策）。本 fix 取反向 = sync code 跟 design G2 一致 / 4 HIGH 冲突全部消除。

cluster-2 design-audit 的 M03 DELETE 段标 **SUPERSEDED**（M18 search 422→400 段不受影响 / 仍 valid）。

## 修法对 design 文档触发

- design M02 §1 / §4 / §13：✅ 无需改（修法已对齐）
- design M03 §7：✅ 无需改（CASCADE schema 不变）
- ADR-001 / ADR-005：✅ 无需改

## 修法对 ErrorCode/Exception 触发

- `PROJECT_DELETE_NOT_SUPPORTED`：✅ 已存在 / 现增 caller（service `delete_project`）/ ErrorCode 不再 0 引用
- `ProjectDeleteNotSupportedError`：✅ 已存在 / 现 service raise / `(http_status=422)` 不变

## 修法对横切原则触发

- 设计原则 #1（schema 唯一真相源）：✅ 不变
- 设计原则 #2（分层严格）：✅ 修法在 dao/service/router 各自层 / 无跨层
- 设计原则 #3（Contract First）：✅ OpenAPI endpoint 保留（显式 422 契约 / 不静默移除）
- 设计原则 #4（状态机显式）：✅ active/archived 两态 + 物理删除转换 = 422 拒绝 / 状态机不变
- 设计原则 #5（多人架构 4 维必答）：✅ tenant/事务/异步/并发 维度无变化

## 结论

A 路径修法 / 0 design 冲突 / 不需要 CY 决策 / 直接 commit。
