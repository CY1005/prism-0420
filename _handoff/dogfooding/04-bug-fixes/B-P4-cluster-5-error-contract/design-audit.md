---
title: B-P4-cluster-5 design audit
sprint: dogfooding P4
date: 2026-05-13
fix_ids:
  - B-P2-M10-error-response-format-design-gap
  - B-P2-cc-A-empty-body-pydantic-422
risk: B 路径 / 全局 handler / 影响所有 Pydantic 422
audit_scope: design ↔ 实装 ↔ frontend ↔ tests 四方契约同步
status: 0 反向冲突 / 实装即真相
---

# 跨 sprint design audit 清单

## 0. 审计范围

按 cluster-5 prompt 指引：B 路径必走 audit / 检查是否有"反向规约"（design / ADR / 跨模块）字面要求 raw Pydantic 422 暴露 或 嵌套 error wrapper / 跟新 flat 契约冲突。

## 1. 冲突清单 (decision / source / impact / action)

### 1.1 engineering-spec §7.4 Router exception handler 范例（已 fix）

| 字段 | 内容 |
|------|------|
| decision | 错误响应 body 格式 |
| source (BEFORE) | `design/01-engineering/01-engineering-spec.md` line ~866 `content={"error":{"code":...,"message":...,"details":...}}` 嵌套 |
| reality | `api/errors/middleware.py::_payload` 自始至终 flat `{"code","message","details"}` |
| impact | spec reviewer / 新模块设计者 可能误信 design 写嵌套契约 spec / 实际跑就 fail (M06 line 555 实证) |
| action | ✅ 已 fix：design §7.4 范例 sync flat + 加锚点 `api/errors/middleware.py::_payload` + 历史段（"旧 design 草案曾写嵌套 / 实装从未走嵌套"）+ 加新增 `RequestValidationError` handler 范例 |

### 1.2 engineering-spec §7.6 兼容表（已 fix）

| 字段 | 内容 |
|------|------|
| decision | 错误响应格式约束 |
| source (BEFORE) | line ~960 "错误响应格式 \| 统一 `{"error": {"code", "message", "details"}}`" |
| reality | 同 1.1 |
| impact | 同 1.1 / 兼容表是新人 review 入口 |
| action | ✅ 已 fix：表行改 "**flat**：`{"code", "message", "details"?}`（顶层 / 无 `"error"` wrapper / 实装锚 api/errors/middleware.py::_payload）" + 加 422 raw Pydantic 行（"必须走全局 `RequestValidationError` handler 包成 flat / 禁直接暴露 raw `detail[]`"）|

### 1.3 模块 §13 ErrorCode 新增清单（**不需要改 / 0 冲突**）

| 字段 | 内容 |
|------|------|
| decision | M01-M20 模块各自 §13 |
| source 实证 | grep 全 20 模块 `## 13` 段：都是 "ErrorCode 新增清单"（只列 code 名 + http_status）/ 不定义 body 格式 / 0 处嵌套契约假设 |
| 唯一例外 | M08 line 659 引用 `@app.exception_handler(RequestValidationError)` 作 RelationSelfLoop ValueError 转换占位（实装走 service 层 raise / 不走 RequestValidationError 路径 / 不冲突）|
| action | ✅ 不改 / 文档跟实装已一致 |

### 1.4 ADR-001 ~ ADR-005 反向规约审计（**0 冲突**）

| ADR | 内容相关性 |
|------|------|
| ADR-001 Shadow Prism | 架构方向 / 不涉及错误 body 格式 / 0 冲突 |
| ADR-002 ~ ADR-005 | 单 ORM / OpenAPI 契约 / arq Queue / 三层权限 / 都不涉及错误 body 嵌套 vs flat / 0 冲突 |

### 1.5 frontend parseError（**实装早已 sync / 0 冲突**）

| 字段 | 内容 |
|------|------|
| reality | `app/src/lib/server-http-client.ts` L37-41 + `app/src/services/http-client.ts` L52-56 已 fallback 读 `body.code`（B-P2-M14-workspace-dimension-error fix 时 Phase 2.3 cleanup 期适配）|
| 注释锚 | L22-25 "middleware.py L18 实际序列化字段名是 `code` 而非 `error_code`" |
| action | ✅ 不动 / 实装锚是真相源 |

### 1.6 pytest assertion（**早已 sync / 0 冲突**）

| 字段 | 内容 |
|------|------|
| reality | grep `tests/` 所有错误码断言：`r.json()["code"]` 22+ 处 flat / 0 处 `body["error"]["code"]` 嵌套 |
| action | ✅ 不动 / pytest 是 backend 行为真相源 |

### 1.7 e2e playwright spec（**部分 fix + 容忍式 fallback 跑过**）

| 字段 | 内容 |
|------|------|
| reality | 19 处 `body?.error?.code ?? body?.code` 容忍式 fallback / 实际取 `body.code` PASS / 1 处 M06 line 555 硬断言 `body.error.code` FAIL |
| action | ✅ M06 line 549-557 已 fix 改 flat 硬断言 + `expect(body).not.toHaveProperty("error")` 防回滚 / 其他容忍式 fallback 不动（取 `body.code` 自动 PASS）|
| 未来改进 punt | 容忍式断言 = 契约不清 / 应在 dogfooding sprint Phase 2 spec 重构 / 推 punt 池 |

### 1.8 RequestValidationError 全局 handler 反向影响审计（**0 反向破坏**）

| 范围 | 反向影响检查 |
|------|----------|
| M18 search query length | router 内 try/except raise InvalidQueryLengthError / service 层 raise / 不走 RequestValidationError 路径 / 新 handler 不拦它 / ✅ test_m18 PASS |
| M08 RelationSelfLoop | service 层 raise `RelationSelfLoopError(ValidationError)` / 不走 RequestValidationError / 新 handler 不拦它 / ✅ test_m08 48/48 PASS |
| M02 ProjectCreate name min_length=1 / M03 NodeCreate name min_length=1 / M04 DimensionCreate / 等 | 之前走 raw Pydantic 422 → 现在走新 handler 包 flat / 输出从 raw `{"detail":[...]}` 变成 flat `{"code":"invalid_request_body",...}` / **行为变化** / 但 frontend parseError fallback 读 `body.code` 自动识别 / ✅ M02+M03+M04 e2e PASS |

### 1.9 ci-lint.sh R13-1 守护（**已 sync**）

| 字段 | 内容 |
|------|------|
| 守护规则 | 业务 ErrorCode 数 = AppError 子类数 |
| BEFORE | 139 = 139 |
| AFTER | 140 = 140（新增 `INVALID_REQUEST_BODY` + `InvalidRequestBodyError(ValidationError)`）|
| action | ✅ parity 保持 / ci-lint 绿 |

## 2. SUPERSEDED 段（旧 design 草案 SUPERSEDED 记录）

```
design/01-engineering/01-engineering-spec.md §7.4 + §7.6
BEFORE (2026-04-26 Phase 1 草案 / SUPERSEDED 2026-05-13 P4 cluster-5):
  错误 body = {"error":{"code":"...","message":"...","details":{}}}（嵌套）

AFTER (2026-05-13 / cluster-5 fix):
  错误 body = {"code":"...","message":"...","details":{}}（flat / 顶层 / 无 error wrapper）
  锚点 = api/errors/middleware.py::_payload
  历史 = 旧 design 草案 SUPERSEDED / 实装从未走嵌套 / frontend parseError 已适配 flat
```

## 3. 跨 sprint punt 池触发记录

- B-P4-cluster-5 fix 期发现：dogfooding sprint Phase 2 spec 期"容忍式 fallback 断言"是契约不清的标志 → 推荐未来 sprint 重构 spec 用唯一硬断言
- M14 known bug spec（`B-P2-M14-workspace-dimension-error`）不在本 fix 范围 / 已记入 03-bug-queue.md
- engineering-spec §7.4 加历史段 + 锚指向真相源 = 防设计前置方法论"草案错了不回头 sync"的元教训防御

## 4. 总结

- **0 反向冲突**：无任何 ADR / engineering-spec 其他段 / 模块 design / 实装代码 字面要求嵌套契约或 raw Pydantic 422 暴露 / 跟新 flat 契约对立
- **设计前置 vs 实装的真相源**：实装从未走嵌套 / pytest+frontend parseError 早已 sync / 仅 design §7.4+§7.6 + 1 个 e2e spec assertion 是迟同步
- **新加 handler 反向影响**：M02/M03/M04 等业务 endpoint 的 raw Pydantic 422 行为从 raw `detail[]` 变成 flat `{code:invalid_request_body}` / **是设计意图改进** / frontend 已无缝识别 / e2e PASS / 0 破坏
