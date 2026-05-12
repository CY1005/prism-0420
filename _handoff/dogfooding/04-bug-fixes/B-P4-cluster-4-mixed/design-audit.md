---
title: P4 cluster-4 mixed bug fix — design audit
status: A 路径全 / 0 design G 决策违反
owner: P4 cluster-4 subagent
created: 2026-05-13
---

# Plan §3 D 风险分级

| Bug | 路径 | 决策违反 G 决策 | 影响半径 |
|-----|------|---------------|---------|
| 1 cc-A lockout drift | A 路径 — testpoint + spec 注释 sync only | 0 | testpoint doc 1 行 + spec comment 3 处 |
| 2 cc-B analyze leak | A 路径 — router 加 11 行前置 check | 0（参 M04 同范式 / design §8 R8-1 已规约） | analyze_router 1 endpoint / 单文件 |
| 3 M13 save-btn | A 路径 — page.tsx 1 行加守护 | 0 | 单文件 / 行为更安全 / spec 转 PASS |
| 4 M17 WS close | A 路径 — import_router accept 顺序调整 + design line 547 sync | 0（RFC 6455 + Starlette 实证 / design 文字 vs client 可观测性平衡） | import_router 1 endpoint / design doc 1 行 sync |

→ A 路径全 / 不需要 G 决策门 / 不动 product 业务逻辑

---

# Bug 1 design 真相反验

## M01 §7 line 98（design 真相）
```
| **失败锁** | 连续 5 次失败密码 → 锁 15min | AC10（安全） |
```

## ADR-004 §4 + line 343（design 真相）
```
**短路保护**：若 refresh 也 401，前端清 refresh token + 跳登录页。禁止"无限重试 refresh"
（P3 端点本身用 IP-based rate limit，本期不实装但在 ADR 声明）。
```

## design line 770/1042（design 真相）
```
⚠️ **rate limit 本期未实装**（M5/M6 审计决策）：应用层无保护 ... 部署前必须前置：
Nginx `limit_req zone=login burst=10 nodelay;` 或 app 层 slowapi（5 req/min per IP）。
```

## 反验结论

**M01 design 一致**：5-strike lockout + IP rate limit 部署前 Nginx/slowapi = 完整范式。

drift 在 testpoint + cc-A spec 注释（误称"无 rate limit / 不锁账号"= 误读 "app 层 IP rate limit 部署前兜底" 为 "无 rate limit"）。

修法 = sync **testpoint + spec 注释**（不动 M01 design / 不删 lockout code）。

---

# Bug 2 design 真相反验

## design §8 R8-1（design 真相，已横切规约）

design `02-modules/M04/00-design.md` + `02-modules/M13-ai-analyze/00-design.md` §8 + cross-cutting §5 R-X3 字面：聚合 Service 调上游 Service 必带 project_id，service 层做 cross-project node 防御 / 不暴露存在性。

实装 audit：
- M04 dimension_service `_check_node_belongs_to_project` (line 80) ✅
- M07 issue_router 引用 `_check_node_belongs_to_project` ✅
- **M13 analyze_router 漏前置 check** — 漏洞

## 反验结论

修法 = router 前置 check（与 M04 read paths 同范式 / line 80 helper 已存在）。design 不需改 / 实装补齐。

---

# Bug 3 design 真相反验

design 没显式规约 "error state UI 行为"，但 M13 §8 UI testpoint 隐含：分析失败 = 不允许保存（避免存空 dimension_record）。

实装 audit：
- error 路径 callback (line 354-357) 字面将 isComplete=true 设给所有 layer → 共享 layer-level state（让"分析失败"卡片可渲染）
- save button 用 `allLayersDone` 间接代理"完成"判定 / 这里耦合泄漏

修法 = save button 加 `!error` 显式守护（不破坏 layer state 语义）。design 不需改。

---

# Bug 4 design 真相反验

## design line 547（原文，已 sync）

旧：`WebSocket 握手 accept() 前；不通过则 close(1008)`

新：`WebSocket 握手 accept() 后立即 close(1008)（B-P3-M17 fix：accept 前 close → Starlette 转 HTTP 403 / client closeCode=1006 不可观测；先 accept 后 close 才能让 RFC 6455 close frame 携带 1008 code 对 client 可见；task_id 已在 URL path 暴露，多一次升级握手不构成实质泄漏）`

## RFC 6455 + Starlette 真相

- close() before accept() → handshake denial / HTTP 403 / client closeCode=-1 或 1006
- accept() + close(1008) → WebSocket close frame / client closeCode=1008

design 原文字 vs client 可观测性矛盾。fix 选 client 可观测性优先（M17 dogfooding spec 已固化 1008 断言 / WebSocket-PILOT 范式后续 M17/任意 WS endpoint 通用）。

## 反验结论

design line 547 字面同步实装真相（accept-then-close + 理由段）。

---

# 完成检查

- ✅ Step 0 fact-finding 完整 / 4 bug 全部 design 反验通过
- ✅ A 路径全 / 0 G 决策门违反
- ✅ tsc + pytest + 4 spec + regression 全 PASS
- ✅ backend kill+restart 验证（pid 55895 / 新 code loaded / playwright 真跑通过）
- ✅ 三件套齐 (fix.patch / rca.md / design-audit.md)
- ✅ Bug 5 punt cluster-5 已 03-bug-queue.md 标记
