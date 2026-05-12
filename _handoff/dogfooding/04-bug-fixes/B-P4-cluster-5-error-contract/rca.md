---
title: B-P4-cluster-5 全局 error contract 同步 / RCA
bug_ids:
  - B-P2-M10-error-response-format-design-gap
  - B-P2-cc-A-empty-body-pydantic-422
status: FIX_DONE
risk: medium (B 路径 / 全局 handler / 影响所有 Pydantic 422)
fix_path: b (design sync + 加全局 handler / 不动 product middleware _payload 序列化)
date: 2026-05-13
sprint: dogfooding P4
agent: Opus subagent cluster-5 fix
---

# Bug 1: B-P2-M10-error-response-format-design-gap

## 1. 现象 (What)

- design/01-engineering/01-engineering-spec.md §7.4 Router exception handler 范例代码声称错误 body 嵌套格式 `{"error":{"code":"...","message":"..."}}`
- 第 960 行 §7.6 表"统一 `{"error":{"code","message","details"}}`"
- backend 实装 `api/errors/middleware.py::_payload()` 自始至终是 **flat** `{"code","message","details"}`（顶层 / 无 error wrapper）
- frontend `parseError` (server-http-client.ts L37-41 + http-client.ts L52-56) 已适配 flat（fallback 读 `body.code`）
- pytest 全套 22+ 处断言 (`r.json()["code"]`) 均按 flat 写
- M06 dogfooding spec line 549-557 误信 design 写硬断言 `body.error.code` → FAIL（cluster-5 fix 期发现）

## 2. 根因 (Why)

设计文档草案期写嵌套契约 (engineering-spec §7.4 / §7.6) / 后续实装从未走嵌套 / design 没同步成 flat / Phase 2.3 cleanup 期 frontend parseError 适配 flat 时记入注释（`code` 字段读取 fallback / 详 server-http-client.ts L24-25 注释）但 design 文档没回头 sync / 多模块 `## 13` 是 "ErrorCode 新增清单"（只列 code 名）不定义 body 格式 / 实际 nested vs flat 契约定义点**只有** engineering-spec §7.4 一处。

## 3. 修法 (How)

**b 路径 / design sync 跟实装一致**（不动 product middleware）：

| 文件 | 改动 |
|---|---|
| `design/01-engineering/01-engineering-spec.md` §7.4 (line ~866) | exception_handler 范例 JSON 改 flat `{code, message, details}` / 加注释锚指向 `api/errors/middleware.py::_payload` + 历史说明 |
| `design/01-engineering/01-engineering-spec.md` §7.6 兼容表 (line ~960) | 改 "**flat**：`{code, message, details?}`（顶层 / 无 `error` wrapper）" + 加 422 raw Pydantic 行 |
| `app/e2e/dogfooding/M06-competitor.spec.ts` line 549-557 | spec assertion 同步 flat（不再 assert `body.error.code` 嵌套契约 / 改 assert 顶层 `body.code` + `expect(body).not.toHaveProperty("error")` 防回滚） |

**未改**（不需要 / 跟实装一致已 ok）：
- 20 个模块 `design/02-modules/M*/00-design.md` §13 = "ErrorCode 新增清单"（只列 code 名 / 不定义 body 格式 / 0 处嵌套契约假设）
- `api/errors/middleware.py::_payload` 实装（已 flat / 不动）
- frontend parseError（已 flat / 不动）
- 其他 19 个 e2e spec（都是 fallback `body?.error?.code ?? body?.code` 形式 / 容忍 flat / 无硬嵌套断言）

## 4. 影响 (Impact)

- design ↔ 实装 ↔ frontend ↔ test 四方契约同步成 flat / 防未来再次漂移
- engineering-spec §7.4 加注释锚 `api/errors/middleware.py::_payload` + 历史段 / 防再次草案误改回嵌套
- 0 product 代码变更（仅 design 文档 + 1 spec assertion）/ 0 regression

---

# Bug 2: B-P2-cc-A-empty-body-pydantic-422

## 1. 现象 (What)

- POST `/auth/logout` + `/auth/refresh` body 完全缺失（curl 不带 `-d` / playwright `request.post(url, {})` 不带 `data`）
- 返 raw FastAPI Pydantic 422：`{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}`
- 跟 design §13 flat error format 不一致
- 内部字段名 `type/loc/msg/input` 泄漏到客户端
- 直接调用方（前端 http-client.apiPost 自动加 Content-Type+空 JSON）不会触发 / 但 curl / SDK / 集成工具暴露非契约错误

## 2. 根因 (Why)

FastAPI 默认对 Pydantic `RequestValidationError` 没走 `api/errors/middleware.py::_payload()` wrapper / 直接返 raw `HTTPValidationError`。`register_exception_handlers()` 只注册了 `AppError` + `Exception` 两个 handler / 没拦 `RequestValidationError`（FastAPI 自带 default handler 拦它返 raw）。

之前 M18 sprint 单点解决（router 层 try/except + raise InvalidQueryLengthError）/ 但没做横切 / 详 cluster-2/M18-M03/rca.md "未来若 design 要求统一 flat 400 包装则需横切引入 RequestValidationError handler" 即此次 cluster-5 fix 承接。

## 3. 修法 (How)

**b 路径 / 全局 RequestValidationError handler 包装 flat**：

| 文件 | 改动 |
|---|---|
| `api/errors/codes.py` | 新增 `INVALID_REQUEST_BODY = "invalid_request_body"` ErrorCode + 注释锚 + 触发场景说明 |
| `api/errors/exceptions.py` | 新增 `InvalidRequestBodyError(ValidationError)` 子类（http_status=422 / R13-1 parity 守护要求每个 ErrorCode 必配 AppError 子类）|
| `api/errors/__init__.py` | export 新增 `InvalidRequestBodyError` |
| `api/errors/middleware.py` | 新增 `_handle_request_validation()` handler / 包成 flat `{code:invalid_request_body, message, details.errors[]}` / details.errors[] 简化版只含 `loc + msg`（去掉 Pydantic 内部 `type/input` 字段）/ `register_exception_handlers()` 注册 |
| `tests/test_errors.py` | 3 个新测试：empty body / missing field / invalid type 全验 flat 契约 + 不暴露 raw Pydantic 内部字段 |

**关键设计决策**：
- 不改 router 层每个 endpoint 加 `Body(default={})` （a 路径）/ 因 N 个 endpoint 都要改 / 范围大 / 仍无法解决"raw Pydantic 422 泄漏内部字段"主问题
- 不改 product middleware `_payload()` 序列化格式 / 因前端 parseError 已适配 flat / 多 spec assertion 跟 flat
- 加全局 handler 是最小侵入 + 最大覆盖（所有 Pydantic 422 都被包）

## 4. 影响 (Impact)

- 所有 Pydantic 422 输出统一 flat 契约 / 跟 design §13 + middleware._payload + frontend parseError + pytest assertion 全方位一致
- 内部字段名 `type/input` 不再泄漏到客户端
- M18 sprint 单点解决（query length validate）仍 work（service 层 raise / 走 AppError handler / 不受新 handler 影响）
- M08 RelationSelfLoop（service 层 raise / 不走 RequestValidationError 路径）不受影响
- frontend `parseError` 读取 `body.code` fallback 自动识别新 code `invalid_request_body` / 无需改前端

## 5. 验证 (Evidence)

```bash
# 实装验证
$ curl -s -X POST http://127.0.0.1:8000/auth/logout
{"code":"invalid_request_body","message":"Request body validation failed","details":{"errors":[{"loc":["body"],"msg":"Field required"}]}}

$ curl -s -X POST http://127.0.0.1:8000/auth/refresh
{"code":"invalid_request_body","message":"Request body validation failed","details":{"errors":[{"loc":["body"],"msg":"Field required"}]}}

$ curl -s -X POST -H "Content-Type: application/json" -d '{}' http://127.0.0.1:8000/auth/logout
{"status":"ok"}  # 正常 happy 路径不受影响

# 测试矩阵
- pytest tests/ : 1648 → 1651 PASS（+3 新测试 / 0 regression）
- pytest tests/test_errors.py : 5 → 8 PASS（+3 新测试）
- pytest tests/test_m01_refresh.py + test_m01_logout.py + test_m01_cookie_channel.py : 20/20 PASS
- ci-lint R13-1 : 140 ErrorCode = 140 AppError 子类（parity 守护 ✅）
- tsc --noEmit : 0 errors
- playwright cc-A spec : 19/19 PASS
- playwright M10 + M06 : 45/45 PASS（M06 line 555 spec assertion 同步 flat / 转 PASS）
- playwright M02+M03+M04+M07+M08 : 124/125（1 fail = B-P2-M14 已知不可修 spec / 与本 fix 无关）
```

## 6. 跨 sprint follow-up

- 推 punt 池：M14 issue 跟踪 known-bug spec 是否值得 fix（B-P2-M14-workspace-dimension-error）
- design-audit.md 记录：engineering-spec §7.4 加 "锚 api/errors/middleware.py::_payload + 历史段" → 防未来 spec reviewer 看老草案再写嵌套契约

## 7. 元教训

| # | 教训 | 防御 |
|---|------|------|
| 1 | design 草案错（嵌套）/ 实装对（flat）/ 前端 parseError 同步实装 / 但 design 没回头 sync → 文档 ↔ 代码漂移 | 设计前置方法论补充：实装阶段发现 design 错 → 立即同步 design 不留漂移 / 加锚点指向真相源 + 历史段 |
| 2 | FastAPI default RequestValidationError handler 默默返 raw / 不走自定义 _payload / 是隐式默认行为 | 启动期审计：所有 FastAPI 内置 handler 必须显式审 / 默认行为不能默认接受 |
| 3 | spec 跟着错误 design 写硬断言（M06 line 555 `body.error.code`）/ spec 第一次跑就 fail 但被 cluster fix 期才发现 | dogfooding sprint P2 spike 期必跑 / 不能延迟到 P4 fix 期才发现 spec 跟 design 漂移 |
| 4 | 多 spec 用 fallback `body?.error?.code ?? body?.code` "容忍式" assertion 掩盖真实契约 | 容忍式断言 = 契约不清的标志 / 应在 P2 spec 期统一选定唯一契约写硬断言 |
