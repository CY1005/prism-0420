---
phase: P3 executor (init regression / 非 P5a after-fix)
runner: P3 executor subagent / Sonnet 4.6
created: 2026-05-13
total_specs: 22
total_tests: 505
---

# P3 Executor 全量回归结果

## 总览

- Total: 22 spec / 505 tests
- **PASS: 488 (96.6%)**
- **FAIL: 17 (3.4%)**
  - 已知真 bug FAIL: 6
  - Spec-design-fix（pre-existing / 已知）: 8
  - 新 FAIL: 3

## 环境说明

- Backend: localhost:8000 (health OK)
- Frontend: localhost:3000 (307 redirect OK)
- unlock 脚本: `.venv/bin/python3 scripts/_unlock_e2e_admin.py` (sqlalchemy in venv)
- 关键发现: cross-cutting 套件（cc-A/B/C）必须独立跑 / 不能与其他 spec 合批 — cc-A 末尾刻意触发 5-strike lockout，若合批会锁住后续套件全部失败

## Per-batch 结果

| Batch | Spec | Tests | PASS | FAIL | 备注 |
|-------|------|-------|------|------|------|
| 1 | M01+M02 | 10 | 10 | 0 | 全 PASS |
| 2 | M11+M14+M19+M20 | 92 | 86 | 6 | M11×4 + M19×2 pre-existing spec-design |
| 3 | M03+M04+M05+M06 | 100 | 95 | 5 | M04×1+M05×1 pre-existing + M06×3 已知 OPEN bug |
| 4 | M07+M10+M12+M15 | 113 | 113 | 0 | 全 PASS |
| 5 | M16+M18+M08+M13 | 94 | 89 | 5 | M18×3 OPEN bug + M13×1 新 FAIL + M18×1 transient |
| 6a | M17 | 19 | 18 | 1 | WS close code 新 FAIL |
| 6b | cc-A | 19 | 19 | 0 | 全 PASS（含刻意 5-strike lockout 测 PASS）|
| 6c | cc-B | 32 | 32 | 0 | 全 PASS |
| 6d | cc-C | 26 | 26 | 0 | 全 PASS |
| **总** | **22** | **505** | **488** | **17** | **96.6% pass rate** |

## FAIL test 分类

### 已知真 bug FAIL（已在 03-bug-queue.md OPEN 池）

| Test Title | Spec | Bug ID | 状态 |
|------------|------|--------|------|
| [P0] API 旁路: competitor_id 不存在创建 ref 返 404 COMPETITOR_NOT_FOUND | M06 | B-P2-M06-competitor-not-found-returns-422 | OPEN / verified FAIL |
| [P0] API 旁路: 错误响应格式符合规约 error.code + error.message（同 M06 test setup 失败）| M06 | B-P2-M06-competitor-not-found-returns-422 | OPEN / 联动 FAIL |
| [P1] API 旁路: GET /competitor-refs 返回含 display_name join 的 CompetitorRefResponse | M06 | B-P2-M06-competitor-ref-response-no-display-name | OPEN / verified FAIL |
| [P0] API 旁路: SearchRequest query='' 返 400 INVALID_QUERY_LENGTH | M18 | B-P2-M18-search-query-validation-returns-422 | OPEN / verified FAIL |
| [P1] API 旁路: SearchRequest limit=0 返 400 ge=1 拦截 | M18 | B-P2-M18-search-query-validation-returns-422 | OPEN / verified FAIL |
| [P1] API 旁路: SearchRequest limit=101 返 400 le=100 拦截 | M18 | B-P2-M18-search-query-validation-returns-422 | OPEN / verified FAIL |

**已知真 bug FAIL 小计: 6**（3 条 M06 / 3 条 M18）

### Spec-design-fix（pre-existing FAIL / 已在 progress.md P2-close 段确认）

| Test Title | Spec | 根因 | 备注 |
|------------|------|------|------|
| [P1] empty-project welcome card — 新建空项目进工作区展示冷启动引导卡片 | M11 L37 | strict mode violation: `getByRole('link', /导入文档/)` 命中 2 元素 | P2-close 已确认 |
| [P1] empty-project click 导入文档 — 跳转 /import 页 | M11 L75 | strict mode violation: 同上 2 elements | P2-close 已确认 |
| [P1] happy path — CSV upload DOM via import-csv-modal + 结果展示 | M11 L102 | backend 返 400（M11 CSV upload API 路径问题）| P2-close 已确认 |
| [P1] CSV 仅列头 0 数据行 — 返 422 COLD_START_CSV_INVALID | M11 L659 | backend 返 201（接受仅列头 CSV）vs 期望 422 | P2-close 已确认为 pre-existing |
| [P0] export node happy path — DOM 主路径 workspace 页面正常渲染 | M19 L57 | `导出 Markdown` 按钮不在 folder 视图（仅 file 视图渲染）| P2-close 已确认 |
| [P1] export button DOM — 导出模块按钮存在于 folder 视图 | M19 L117 | folder 视图 folderChildren 异步加载 2s timeout 不够 | P2-close 已确认 |
| [P0] workspace smoke — feature 详情页进入撞 error boundary | M04 | B-P2-M14 FIX_DONE 后 workspace 渲染了"第三种状态"（既非 error boundary 也非维度卡片）→ spec `isError || isNormal` 双重断言失败 | P2-close 已确认为 spec-design bug |
| [P0] workspace.tsx 进入项目详情页 — DOM smoke | M05 | 默认 folder 视图不渲染 `版本演进` section | P2-close 已确认 |

**Spec-design-fix 小计: 8**（M11×4 + M19×2 + M04×1 + M05×1）

### 新 FAIL（P2 subagent 边写边跑未抓 / 本 P3 新发现）

| Test Title | Spec | 现象 | 优先级建议 | 新 Bug ID |
|------------|------|------|-----------|-----------|
| [P0-DOM] save 按钮 stub puntResult 验证（finding-2 真 bug 复现）| M13 | 测试期望 `保存到需求分析维度` 按钮 count=0（SSE 失败则无结果），但实测 count=1 — 说明在 SSE 失败+error 渲染后 save 按钮仍出现，条件 `hasResults && allLayersDone` 为 true。spec 假设 finding-1 SSE 失败→layers 永远不填充已不成立，或 page state 有残留 | P1（逻辑 bug / save 按钮应在 error 状态下不可见）| B-P3-M13-save-btn-shows-on-error |
| [P0-WS-PILOT] WebSocket 握手鉴权: 无效 JWT token 必 close(1008) policy violation | M17 | WebSocket 握手用 invalid JWT → 期望 server 发 close(1008)，实测 closeCode=-1（8s 超时，server 未发 close frame）— FastAPI WS endpoint 可能在 JWT 校验失败时挂起或用了 1006 abnormal closure | P1（安全相关 / 无效 JWT 应立即 close）| B-P3-M17-ws-invalid-jwt-close-code |
| [P0] API 旁路: admin backfill + stats 返回体结构 — platform_admin token（如有）| M18 | ECONNRESET — HTTP 连接被服务端重置。可能是 backfill 触发 Redis 任务后服务重启/OOM/后端短暂不可达。其余 M18 API 旁路测试全 PASS，此单条为孤立失败 | P2（疑似 transient / 需重跑验证）| 暂不立 entry / 重跑确认后决定 |

**新 FAIL 小计: 3**（2 确认新 bug + 1 疑似 transient）

## 新 bug 入队

### B-P3-M13-save-btn-shows-on-error（新）

- **现象**: analysis/page.tsx 在 SSE 分析失败（error state）后，`保存到需求分析维度` 按钮仍渲染（count=1 而非 0）
- **来源**: P3 executor / M13 spec `[P0-DOM] save 按钮 stub puntResult 验证` / 2026-05-13
- **status**: OPEN
- **根因（疑）**: `hasResults && allLayersDone` 条件在某些 SSE 失败场景下为 true — 可能是 layers state 未在 error 时清空，或 allLayersDone 逻辑对空 layers 数组返回 true（`layers.every()` 对空数组返 true）
- **fix 路径**: `app/src/app/projects/[projectId]/analysis/page.tsx`: `allLayersDone` 逻辑加 `layers.length > 0` 前置 guard（已有但需确认）+ error 状态时清空 layers state / 或 save button 加 `!error` 条件

### B-P3-M17-ws-invalid-jwt-close-code（新）

- **现象**: WebSocket 握手用无效 JWT token 时 server 未在 8s 内发送 close frame / 连接挂起 → closeCode=-1（超时）而非期望的 1008 policy violation
- **来源**: P3 executor / M17 spec `[P0-WS-PILOT] WebSocket 握手鉴权` / 2026-05-13
- **status**: OPEN
- **根因（疑）**: `api/routers/import_router.py` WS endpoint JWT 校验失败时的错误处理 — FastAPI `WebSocket.close(code=1008)` 可能是 async 但未被 await，或在 accept 前 close 的协议层问题（RFC 6455：close 前必须先 accept）
- **fix 路径**: `api/routers/import_router.py` WS 入口：先 `await websocket.accept()` 再 `await websocket.close(1008)` — 或在 decode_jwt 异常处理中确保 close frame 被真实发送

## P4 优先级建议

### P0 立即修（跨模块/安全影响）

- B-P3-M17-ws-invalid-jwt-close-code：WS 无效 JWT 未正确 close → 安全 + 协议层 fix（小改）
- B-P2-M06-competitor-not-found-returns-422：competitor_id 不存在返错误状态码（API 契约违反）
- B-P2-M18-search-query-validation-returns-422：search 边界校验返 422 非 400（API 契约不一致）

### P1 Sprint 内修

- B-P3-M13-save-btn-shows-on-error：save 按钮在 error 状态下不应出现（UX + logic bug / 分析 `layers.every([])` 是否是根因）
- B-P2-M06-competitor-ref-response-no-display-name：CompetitorRefResponse 缺 display_name join（API 契约）

### P2 Punt 下 Sprint

- M18 admin backfill ECONNRESET：疑似 transient / 重跑确认后决定
- Spec-design-fix 8 条：M11/M19/M04/M05 pre-existing / 需 spec 级修复或接受

## 关键运行发现

1. **cc-A 必须独立跑**: `_cross-cutting-A` 末尾刻意触发 5-strike lockout（真 bug 验证），若与其他套件合批运行，后续套件全部登录失败。今后 P5 回归时 cc-A 必须单独一批 + unlock 脚本放在它之后。
2. **unlock 脚本必须用 venv**: 系统 python3 无 sqlalchemy → `ModuleNotFoundError`。正确调用: `.venv/bin/python3 scripts/_unlock_e2e_admin.py`
3. **M04 workspace smoke 状态变化**: B-P2-M14 FIX_DONE 后 workspace 渲染结果改变——既非 error boundary 也非维度卡片，导致 spec `isError || isNormal` 双重断言均失败。这是 FIX_DONE 后遗留的 spec 需要更新（断言应对应新的正常渲染状态）。

## 数据（供 P5b STAR 报告 D1）

- testpoint 总数: 2327（P1 阶段产出）
- spec 总数: 22
- test 总数（P3 init regression）: 505
- init pass rate: **96.6%** (488/505)
- init fail rate: **3.4%** (17/505)
  - 真 bug FAIL: 6 / 1.2%
  - Spec-design FAIL: 8 / 1.6%
  - 新 FAIL: 3 / 0.6%
- 已知 OPEN bug 验证: 6 条 OPEN bug verified 仍 FAIL（M06×3 + M18×3）
- 新入队: 2 条新 bug（B-P3-M13 + B-P3-M17）+ 1 条疑似 transient 待确认

---

_created by P3 executor subagent / Sonnet 4.6 / 2026-05-13_
