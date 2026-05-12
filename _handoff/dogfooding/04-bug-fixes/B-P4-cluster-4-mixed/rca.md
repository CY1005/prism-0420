---
title: P4 cluster-4 mixed bug fix — RCA
status: FIX_DONE
owner: P4 cluster-4 subagent
created: 2026-05-13
covers:
  - B-P2-cc-A-account-lockout-design-drift (testpoint doc sync only)
  - B-P2-cc-B-analyze-rx3-cross-tenant-leak (router 前置 check)
  - B-P3-M13-save-btn-shows-on-error (frontend !error 守护)
  - B-P3-M17-ws-invalid-jwt-close-code (WS accept-then-close)
  - punt: B-P2-cc-A-empty-body-pydantic-422 → cluster-5 跟 M10 error format 同 fix
---

# Step 0 fact-finding 反验结论

| 反验对象 | 结果 | 影响 |
|---|---|---|
| design/02-modules/M01-user-account/00-design.md §7 line 98 | 字面 "连续 5 次失败密码 → 锁 15min" / 实装一致 | **prompt 描述错** — design 已写 lockout / 不需要 sync M01 design / 真 drift 在 testpoint + cc-A spec 注释 |
| design/01-engineering/05-security-baseline.md | rate limit 部署前 Nginx/slowapi 兜底（design line 770/1042 一致） | app 层未实装是 design 决策 / 不矛盾 |
| design/02-modules/M17-ai-import/00-design.md line 547 | 字面 "WS 握手 `accept()` 前；不通过则 close(1008)" | design 文字 vs RFC 6455 client 可观测性矛盾 / sync design 注释为 "accept-then-close" + 解释 |
| api/errors/codes.py | ANALYSIS_NODE_NOT_FOUND / ACCOUNT_LOCKED / RATE_LIMITED 全部已留位 | ✅ Bug 2 直接用 AnalysisNodeNotFoundError 不需新增 ErrorCode |
| api/services/analyze_service.py line 134 | nodes.get_node 已在 SSE generator 内 try/except wrap NodeNotFound → AnalysisNodeNotFoundError | 漏洞：generator 已在 HTTP 200 流内抛错 → 表现为 SSE event:error 而非 4xx HTTP / 修法 = router 早期前置 check |

---

# Bug 1: B-P2-cc-A-account-lockout-design-drift (design sync only)

## 根因

**Drift 来源不在 M01 design**，在：
1. `_handoff/dogfooding/01-testpoints/_cross-cutting.md` line 70 字面 "重试不锁账号（无 rate limit / M01 §7）" — 跟 M01 §7 line 98 "5 次失败锁 15min" 矛盾
2. `app/e2e/dogfooding/_cross-cutting-A-auth-network.spec.ts` line 459-462 + 668-672 + 689-690 注释字面 "testpoint 声称无 rate limit / 真 bug 入 queue / 设计漂移"

实际：M01 §7 + ADR-004 + config 默认值 5-strike lockout 是设计一致的决策 / app 层 IP rate limit 才是 design 显式 punt 到部署前 Nginx/slowapi（design line 770/1042/1261）。

## 修法

- testpoint line 70：句式重写为 "5-strike lockout 15min（M01 §7 line 98 + auth_service.py L100-106）/ app 层 IP rate limit 部署前兜底"
- cc-A spec line 459-462：注释清晰 5-strike 是 design 范式 / lockout 测试单独覆盖
- cc-A spec line 669-672 + test name + 690-694：从"设计漂移真 bug" 改为"M01 §7 设计实证 / 5-strike lockout 真实行为存在"
- **不动 M01 design**（design 本来就对）/ **不删 lockout code**（design 范式）

## 验证

- cc-A spec [P1/§3] 5-strike test 19/19 PASS（含本 test）

---

# Bug 2: B-P2-cc-B-analyze-rx3-cross-tenant-leak

## 根因

`api/routers/analyze_router.py:stream_requirement_analysis` 直接进入 SSE generator，**HTTP 200 + StreamingResponse 已经发出 headers**。然后 generator 内调 `svc.analyze_stream` → `nodes.get_node` → 抛 `NodeNotFoundError` → wrap 为 `AnalysisNodeNotFoundError`，但已经在 generator 内：被 router 的 except 兜底转为 `SSE event:error`（content-type=text/event-stream / status=200）。

跨 project node_id 探测者看到：
- HTTP 200 (不是 404) → 探测信号"接受了请求"
- SSE event:error code=analysis_node_not_found 或 analysis_provider_not_configured (实测后者) → 模糊化 cross-tenant 探测

design §8 R8-1 三层防御第三层：service 层必须前置校验 node 归属（M04 dimension_router 已正确执行 / M13 analyze 漏写）。

## 修法

`api/routers/analyze_router.py` `stream_requirement_analysis`：在创建 `svc` 后、return `StreamingResponse` 前，前置：
```python
target_node = await svc.nodes.dao.get_by_id(db, node_id, access.project.id)
if target_node is None:
    raise AnalysisNodeNotFoundError(node_id=str(node_id))
```

这样跨 project node_id 在 HTTP layer 即返 404 不进入 SSE 流。

## 验证

- pytest `test_stream_requirement_cross_project_node_returns_404` PASS（旧 test 同步 design 真相 / 断言 status_code == 404）
- cc-B spec `[P0-API] §5 R-X3 间接观察` PASS（走 else 分支 4xx 路径）

---

# Bug 3: B-P3-M13-save-btn-shows-on-error

## 根因

`app/src/app/projects/[projectId]/analysis/page.tsx` save button 显示条件 line 836:
```ts
{hasResults && allLayersDone && !testPointsResult && (
```

其中：
- `hasResults = layers.length > 0` (line 199)
- `allLayersDone = layers.length > 0 && layers.every(l => l.isComplete)` (line 201)

SSE error 路径（line 354-357 error callback）：
```ts
setLayers((prev) =>
  prev.map((l) => (l.level === level ? { ...l, isStreaming: false, isComplete: true } : l)),
);
```

→ error 场景下 `isComplete=true` 仍被设 / `allLayersDone=true` 即使分析失败 / save button 显示。spec [P0-DOM] save 按钮 stub puntResult 验证（finding-2 真 bug 复现）断言 `saveBtn.toHaveCount(0)` FAIL。

## 修法

save button 显示条件加 `&& !error` 守护：
```ts
{hasResults && allLayersDone && !error && !testPointsResult && (
```

不动 error callback 的 `isComplete=true` 逻辑（保持 layer-level 完成状态 / 让 UI 可以渲染 "分析失败" 卡片）。

## 验证

- M13 spec `[P0-DOM] save 按钮 stub puntResult 验证（finding-2 真 bug 复现）` PASS
- tsc --noEmit 0 错

---

# Bug 4: B-P3-M17-ws-invalid-jwt-close-code

## 根因

`api/routers/import_router.py:import_progress_ws` 在 JWT 校验失败时调 `await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)` — 但是**在 `await websocket.accept()` 之前**。

RFC 6455 + Starlette 范式：
- close() 在 accept() 之前 → Starlette 自动回 **HTTP 403** (handshake denial response) — 没有 WS close frame
- client（playwright `new WebSocket(...)`）收到 connection failed / ws.onerror / closeCode=-1 或 1006 abnormal closure / **拿不到 1008 close code**

M17 spec `[P0-WS-PILOT] WebSocket 握手鉴权: 无效 JWT token 必 close(1008)` 断言 `closeCode === 1008` → 8 秒 timeout FAIL（closeCode=-1）。

design line 547 字面 "WS 握手 accept() 前；不通过则 close(1008)" — 描述与 client 可观测性矛盾。

## 修法

`api/routers/import_router.py:import_progress_ws`：将 `await websocket.accept()` 提前到 JWT 校验**之前**（func 入口），让后续 close(1008) 走 WS close frame 路径 / client 收到 1008 code。

design/02-modules/M17-ai-import/00-design.md line 547 同步：accept-then-close + 解释（attacker 多看到一次 handshake / 但 task_id 已在 URL path 暴露 / 不构成实质泄漏）。

## 验证

- pytest `test_ws_invalid_token_closes_1008` + `test_ws_refresh_token_type_closes_1008` + `test_ws_task_not_owned_closes_1008` 3 个 / 用 TestClient ws.receive_text() 触发 disconnect / 全 PASS
- M17 spec `[P0-WS-PILOT] WebSocket 握手鉴权` PASS（closeCode=1008）
- M17 spec `[P0-WS-PILOT] WebSocket 握手成功` PASS（valid JWT 不 early close）

---

# Bug 5: B-P2-cc-A-empty-body-pydantic-422 — PUNT

属 global error contract / 跟 cluster-5 M10 error format design vs flat backend impl 同 fix。本 cluster 不处理 / queue 标记。

---

# 验证摘要

| 检查 | 结果 |
|---|---|
| tsc --noEmit | ✅ 0 错 |
| pytest tests/ 全跑 | ✅ 1648 passed / 6 skipped / 0 failed |
| M13 spec 33 个 | ✅ 33 passed |
| M17 spec 含 WS 2 个 | ✅ included in 33 / WS close 1008 PASS |
| cc-A spec 19 个 | ✅ 19 passed（含 5-strike test 改名 + lockout 单测 PASS）|
| cc-B spec 32 个 | ✅ 32 passed |
| Regression 01-auth + 02-create-project + 04-node | ✅ 5 passed |
| Backend kill+restart | ✅ pid 42185 → 55895 / health OK |
