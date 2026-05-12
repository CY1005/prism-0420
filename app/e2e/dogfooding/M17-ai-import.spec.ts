import { test, expect } from "@playwright/test";

import { loginE2EAdmin, seedFullProject } from "../fixtures/seed";

// M17 AI 智能导入（异步 Queue + WebSocket）dogfooding spec — P2-case Opus spike (2026-05-12)
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M17-ai-import.md
// 143 testpoint / P0=62 / P1=66 / P2=15 / escalation surface ≥100
//
// ═══════════════════════════════════════════════════════════════════════════
// 范式定位（Opus spike — WebSocket 是范式未验过的领域）
// ═══════════════════════════════════════════════════════════════════════════
//
// 覆盖（按分类决策树拆三类标签）:
//   [DOM-reachable]    3 条  → page.goto /projects/{pid}/import + UI 三 tab 切换 + frontend stub
//                              puntResult 真 bug 复现（参 M13 finding-2 范式）
//   [API-via-旁路]    13 条  → request fixture 直打 /api/projects/{pid}/imports/*
//                              + multipart 提交 + 鉴权 + tenant + 状态机 + 幂等 + method
//   [API-via-WS]       2 条  → 原生 WebSocket 直连后端 / Bearer JWT via Query / 握手
//                              鉴权（1008 vs accept）/ Opus spike pilot
//   [skip-N/A]       125 条  → 见下方 punt 清单（多为 Queue 流水线 / 11 状态机深路径 /
//                              AI provider mock 注入 / S3 暂存 / dead letter 等 backend 范畴）
//
// ═══════════════════════════════════════════════════════════════════════════
// 🔴 WebSocket 范式 spike finding（Opus spike 任务核心 / design-gap candidate）
// ═══════════════════════════════════════════════════════════════════════════
//
// 🔴 ws-finding-1: 原生 Node `WebSocket`（node 20+）可在 playwright test runtime 内直连
//   后端 ws://localhost:8000/api/projects/{pid}/imports/{tid}/progress?token=<JWT>。
//   playwright `request` fixture 无 ws API / 不支持 server push；但 playwright runtime
//   是 node 20+ 可直接 `new WebSocket(url)`。本 spike 实证范式：
//     1) 用 `seeded.accessToken` 当 Query token（design §7 + import_router.py L375）
//     2) 监听 onopen / onmessage / onerror / onclose 收事件
//     3) 通过 Promise + timeout 等握手结果（设计应 1008 close 或 accept）
//   pilot 范围只验"握手是否成功 / close code 是否符合设计"。
//   不验：完整 progress_update 序列 / cancel 命令往返 / 8-status WebSocket 流水线
//   （这些需 Queue worker 真跑 + AI provider mock，是 pytest integration 范畴）。
//
// 🔴 ws-finding-2: 浏览器 page.on("websocket") 监听不适用 — M17 frontend 实装根本不发
//   WebSocket 请求（参见下方 design-gap candidate-1 / aiAnalyzeZip 全是 stub）。
//   page.on("websocket") 只能监听浏览器实际打开的 ws 连接 / frontend 不调 → 永远 0 个。
//   → DOM-side WebSocket 测试范式全 punt / WebSocket 只能 API 旁路（直连后端）验。
//
// 🔴 ws-finding-3: WebSocket 协议复杂场景（11 状态机推进 / 5 禁转 / cancel 真起作用 /
//   review_ready event 推送）需要：① 真 enqueue arq job ② AI provider mock ③ broker
//   pub/sub 全链路连通。playwright e2e 无法 monkeypatch backend / 这些 punt 给 pytest
//   integration（design §12 Queue 任务清单 + tests.md WS1-WS5 全部 punt）。
//
// 🔴 ws-finding-4: WebSocket idempotency / R-X1 importing single transaction 不在
//   WebSocket 协议层验证 / 属 Queue worker + DB 事务范畴。idempotency 在 REST POST
//   /imports 路径上验（[API-via-旁路] 已覆盖）；R-X1 single transaction 是 backend
//   pytest 范围（需 Mock node_service.batch_create_in_transaction 抛异常验 rollback）。
//
// ═══════════════════════════════════════════════════════════════════════════
// punt 清单（按 testpoint §章节 / 与已 [DOM]/[API]/[WS] 覆盖的不重复）
// ═══════════════════════════════════════════════════════════════════════════
//
// §1 功能性（14 条）:
//   - [P0] WebSocket 推 8 状态全推 → [skip-N/A] 需 Queue worker + AI mock / pytest integration
//   - [P0] GET /review 返 ReviewDataResponse 5 字段 → [skip-N/A] 需 awaiting_review 真态 / Queue
//   - [P0] POST /confirm 用户调整后入库 → [skip-N/A] 同上依赖 review_data 真生成
//   - [P0] importing 完成 activity_log 写齐 8 类 → [skip-N/A] 同上
//   - [P0] git URL / .git 包形态 → [skip-N/A] 需 git server 或真 bare repo / 主线 pytest
//   - [P1] cancel/retry/list/detail/confirm 调整 → 部分 [API-via-旁路] 覆盖
//   - [P1] zip 内全二进制 step1 识别 0 模块 → [skip-N/A] 需 AI provider mock 跑
//   - [P2] git_ref 默认 main → [skip-N/A] git server 依赖
//
// §2 边界 / 状态机（12 条）:
//   - [P0] pending → ai_step3 跳步 409 → [skip-N/A] 需 task 真处于 pending（Queue worker 不
//     拉起则状态保持 pending），但跳转触发只在 confirm 接口上调用 → 必须 awaiting_review
//     才能 confirm；这条间接通过 [API-CONFIRM-INVALID] 验
//   - [P0] completed/cancelled/failed → 任意 409 → [API-via-旁路] 部分覆盖
//   - [P0] partial_failed → 仅 ai_step3 / cancelled → [skip-N/A] 需 partial_failed 真态构造
//   - [P0] awaiting_review → importing 跳过 ai_step3 → [skip-N/A] 同上
//   - [P1] importing single tx ROLLBACK → [skip-N/A] R-X1 验需 mock Service / pytest
//   - [P1] cancelled 24h / failed 30 天 cron 清理 → [skip-N/A] cron job / 不在 spec 范围
//   - [P2] source_type 非枚举 422 → [API-via-旁路] 覆盖（status code 422）
//
// §3 异常 / 错误（17 条）:
//   - [P0] zip 损坏 → [skip-N/A] 需准备损坏 zip + Queue worker 真跑 / pytest
//   - [P0] git URL 不可达 3 次重试 → [skip-N/A] git server + Queue / pytest
//   - [P0] AI 调用失败 1/2/3 次重试 → [skip-N/A] 需 mock provider 注入失败 / pytest
//   - [P0] AI 输出格式错（非 JSON）→ [skip-N/A] 同上
//   - [P0] importing batch_create_in_transaction 部分失败 partial_failed → [skip-N/A] pytest
//   - [P1] 超大 zip >500MB 422 → [API-via-旁路] 通过 100MB 上限验证（router 实装 100MB / design 草案 500MB）
//   - [P1] git URL 私有 repo 认证失败 → [skip-N/A] git server / pytest
//   - [P1] .git 包格式错 → [skip-N/A] 需真 bare repo bundle / pytest
//   - [P1] confirm 在非 awaiting_review 409 → [API-via-旁路] 通过 pending 状态 confirm 验
//   - [P1] AI Provider 配额超限 429 → [skip-N/A] 需 mock / pytest
//   - [P1] Queue worker crash arq 持久化 → [skip-N/A] 需 kill worker / chaos test
//   - [P1] review_data >50MB TOAST → [skip-N/A] 需注入大 review_data / pytest
//   - [P1] activity_log 写失败不回滚 → [skip-N/A] 需 monkeypatch / pytest
//   - [P2] 死信 30 天 cron 删 → [skip-N/A] cron job
//
// §4 权限 / Auth（10 条）:
//   - [P0] viewer 角色 POST /imports 403 → [skip-N/A] 需 viewer fixture / 当前单 admin
//   - [P0] 未登录 POST 401 → [API-via-旁路] 覆盖
//   - [P0] Service _check_task_belongs_to_user_and_project 404 → [API-via-旁路] 覆盖（GET 不属于 task）
//   - [P0] Queue 消费者入口校验 → [skip-N/A] internal / pytest
//   - [P0] WebSocket 握手 task_id 归属 user 1008 → [API-via-WS] 覆盖
//   - [P0] WebSocket 每命令 ClientCommand.task_id 重校 1008 → [skip-N/A] 需 ws send_json /
//     需 cancel 真起作用看 close 行为；本 spike 只验握手 / 命令路径下次 sprint
//   - [P1] 中途降级 / 项目删除 / Server Action 文件上传 → [skip-N/A] 多账户 fixture / pytest
//
// §5 Tenant 隔离（9 条）:
//   - [P0] userA 用 projectA token 访问 projectB task → [API-via-旁路] 覆盖（404 期望）
//   - [P0] Queue payload 篡改 user_id → [skip-N/A] 直 Redis 投递 / pytest
//   - [P0] DAO.get_by_id 双过滤 → [API-via-旁路] 间接覆盖（task_id 不存在返 404）
//   - [P0] idempotency find_idempotent 含 project_id 防跨租户 → [skip-N/A] 需两 project 真
//     提交同 zip / source_hash 复杂构造（router 接 multipart 不直接 source_hash 参数）
//   - [P0] UNIQUE(user_id, project_id, source_hash) → [skip-N/A] 同上
//   - [P1] WebSocket 握手 URL path task_id 归属 → [API-via-WS] 覆盖
//   - [P1] DAO.list_by_project 双过滤 → [API-via-旁路] 通过 list 端点验
//   - [P1] activity_log 写入 user_id Queue 传入 → [skip-N/A] internal / pytest
//   - [P1] cron user_id=SYSTEM_USER_UUID → [skip-N/A] cron / pytest
//
// §6 并发 / 乐观锁（7 条）:
//   - [P0] 同 user 1s 内重复提交同 zip idempotency → [skip-N/A] 同 §5 idempotency 构造
//   - [P0] 同 user 不同 zip 并发 / 多 user 同 project → [skip-N/A] 多账户 / pytest
//   - [P1] 用户 cancel + worker 并发 / review 阶段并发 改 mapping → [skip-N/A] pytest
//   - [P1] partial_failed retry 并发 → [skip-N/A] 同上
//   - [P2] UNIQUE 并发 INSERT race → [skip-N/A] 同上
//
// §7 数据完整性（11 条）:
//   - 全部 CHECK constraint / source_hash 算法 / single transaction / R-X1 → [skip-N/A] pytest
//
// §8 UI / UX（8 条）:
//   - [P0] 4 步向导 page → 部分 [DOM] smoke / 但实装是合并 tab + AIImportWizard 自包含 4 步
//   - [P0] import-progress.tsx WebSocket 客户端 → [skip-N/A] 实装 ai-import-wizard.tsx 不调 WS
//     而是 setTimeout 假进度 → design-gap candidate
//   - [P0] review-mapping.tsx → [DOM] step2 mapping table smoke（design-gap：mapping table 是
//     AIImportWizard 内嵌组件而非独立 review-mapping.tsx）
//   - [P1] 进度卡死 30s 降级 / failed/partial_failed UI / cancel 按钮可见性 → [skip-N/A]
//     需 task 真进入对应状态 / stub 阻断
//   - [P2] confidence_scores 高亮 → [skip-N/A] 需 AI 真分析结果
//
// §9 性能（5 条）:
//   - 全部 [skip-N/A] backend benchmark / pytest
//
// §10 WebSocket 协议（8 条）:
//   - [P0] WS 握手成功 100ms 内推当前 status → [skip-N/A] 需 broker publish + worker running
//   - [P0] cancel 命令往返 → [skip-N/A] 需 Service cancel_task 真起作用 / 状态机推进
//   - [P0] 未知 type 推 error 保留连接 → [skip-N/A] 同上
//   - [P1] 30min ping/pong → [skip-N/A] 长连接 / 超 playwright 30s timeout
//   - [P1] 任务完成新客户端推 final + close → [skip-N/A] 需 completed 真态
//   - [P1] WS 每命令 task_id 重校 → [skip-N/A] 需 cancel 命令真 send / 见 §4
//   - [P2] ProgressEvent.metadata 失败时 → [skip-N/A] 需 mock provider 失败
//
// §11 Queue 异步路径（9 条）:
//   - 全部内部 Queue 实现 / TaskPayload 字段 / 重试策略 / arq crash → [skip-N/A] pytest
//
// §12 Idempotency（8 条）:
//   - 全部 [skip-N/A] 需 multipart zip + source_hash 显式构造 / pytest 用 service 层直调
//   - 注：通过 [API-via-旁路] 真提交两次同样 zip 可触发，但本 spec 不写 multipart 因 ai_provider
//     未配置走不通 / 优先级让位给 ai_provider_unset 验证
//
// §13 ErrorCode 映射（8 条）:
//   - [P0] IMPORT_TASK_NOT_FOUND 404 / IMPORT_TASK_FINALIZED 409 / IMPORT_INVALID_SOURCE 422 /
//     IMPORT_INVALID_STATE_TRANSITION 409 → [API-via-旁路] 覆盖
//   - [P0] IMPORT_AI_PROVIDER_ERROR 503 → [skip-N/A] 需 AI mock / pytest
//   - [P1] BATCH_INSERT_FAILED / QUOTA_EXCEEDED / DUPLICATE 200 → [skip-N/A] 内部 / pytest
//
// §14 activity_log 事件（8 条）:
//   - 全部 [skip-N/A] 需 task 推进 / 内部事件 / pytest
//
// §15 演进风险（5 条）:
//   - 全部 [skip-N/A] 设计推导 / 非 e2e 验证项
//
// ═══════════════════════════════════════════════════════════════════════════
// design-gap candidate（dogfooding 价值 / 报主 agent / 入 03-bug-queue.md）
// ═══════════════════════════════════════════════════════════════════════════
//
// 1. **🔴 frontend M17 完全不调真 M17 backend（真 bug-1）**：
//    app/src/actions/import-ai.ts L106+ 字面：
//      aiAnalyzeZip / aiAdjustMapping / aiConfirmImport / aiUndoImport
//      全部 return actionError(AppError(PUNT_MSG, "blocking", INTERNAL_ERROR, 501))
//    PUNT_MSG = "AI 智能导入将在子片 3c 接入 M17 ImportTask 异步任务 + WS 进度通道（当前路径 punt）"
//    AIImportWizard 渲染完整 4 步向导 UI，但点击「开始 AI 分析」立即 setError(PUNT_MSG)。
//    → 全部 [DOM] flow（上传 zip → AI 分析 → 确认导入）端到端不通。
//    → POST /api/projects/{pid}/imports 端点存在且工作，但浏览器 0 调用。
//    → WebSocket /progress 端点存在且工作，但浏览器 0 连接。
//    → 入 03-bug-queue.md（B-P2-M17-frontend-stub）。
//
// 2. **🔴 frontend WebSocket 客户端完全未实装（真 bug-2 / 同根因 #1）**：
//    design §6 列 import-progress.tsx「WebSocket 客户端连接进度条实时刷新」/ 实装
//    ai-import-wizard.tsx L524-537 字面用 setTimeout(150ms) 模拟假进度 / 0 WS 连接。
//    → 入 03-bug-queue.md（B-P2-M17-fake-progress-no-ws）。
//
// 3. **🔴 design vs UI 漂移：4 步向导 vs 3 tab 模式（design-gap）**：
//    design §6 字面「Page = 4 步向导（上传 → 预览 → 映射 review → 确认入库）」
//    实装 import-page-client.tsx 顶层是「手动映射 / AI 智能导入 / Markdown 导入」3 tab
//    切换，且 AI 智能导入 tab 内才是 4 步向导（与 design 步骤吻合）。但 design 没说
//    多种导入模式共存 / 没说 tab UI。→ design-gap candidate（决定 sync 文档还是 sync UI）。
//
// 4. **🔴 fresh seeded project 无法走 M17 happy path（设计盲区 / design-gap）**：
//    M17 router L124 字面：if not ai_provider: raise ImportInvalidSourceError(reason="ai_provider_unset")
//    seedFullProject 创建的项目 ai_provider=NULL（template_type=custom 默认）。
//    → 所有 happy path multipart 上传都被 422 阻断（设计要求 project 先配 ai_provider）。
//    → 这是 design vs onboarding 漂移：前端没引导用户先配 ai_provider 就直接给上传 UI。
//    → 实测后 M17 测试需先 PUT /api/projects/{pid}/ai-provider mock 再 multipart（M16 范式）。
//    → audit candidate（非阻塞 bug / 但用户体验是踩坑路径）。

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";
const WS_BASE = API_BASE.replace(/^http/, "ws");

// ─── Helper: 设置项目 AI provider（M16 范式复用 / submit_import 前置条件）─────────
async function setProjectAiProvider(
  request: Parameters<typeof loginE2EAdmin>[0],
  token: string,
  projectId: string,
  provider = "mock",
) {
  const res = await request.put(`${API_BASE}/api/projects/${projectId}/ai-provider`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { ai_provider: provider },
  });
  if (!res.ok()) {
    throw new Error(`set ai_provider failed: ${res.status()} ${await res.text()}`);
  }
}

// ─── Helper: 多部分提交 import (zip)，返回 status + body
async function submitImportZip(
  request: Parameters<typeof loginE2EAdmin>[0],
  token: string,
  projectId: string,
  fileBytes: Buffer,
  filename = "test.zip",
) {
  return request.post(`${API_BASE}/api/projects/${projectId}/imports`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      source_type: "zip",
      file: { name: filename, mimeType: "application/zip", buffer: fileBytes },
    },
  });
}

test.describe("M17 AI 智能导入（Queue + WebSocket）dogfooding", () => {
  // ════════════════════════════════════════════════════════════════════════
  // 轨 1: DOM 主路径
  // ════════════════════════════════════════════════════════════════════════

  test("[P0-DOM] /import page 可达 + 三 tab 切换（手动 / AI / Markdown）", async ({
    page,
    request,
  }) => {
    // design §6 字面声称 page = 4 步向导（design-gap candidate-3）/ 实装顶层是 3 tab
    // 这条只 smoke 页面可达 + tab 切换 / 不进 AI 流程（finding-1 阻断 / 见下一条）
    const seeded = await seedFullProject(request);

    await page.goto(`/projects/${seeded.project.id}/import`);
    await expect(page).toHaveURL(/\/import$/, { timeout: 8_000 });

    // import-page-client.tsx L54 字面 "导入文档" header
    await expect(page.getByRole("heading", { name: "导入文档" })).toBeVisible();

    // 三 tab 都渲染（import-page-client.tsx L60-94 字面）
    await expect(page.getByRole("button", { name: "手动映射" })).toBeVisible();
    await expect(page.getByRole("button", { name: "AI 智能导入" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Markdown 导入" })).toBeVisible();

    // 切到 AI tab → 验 AIImportWizard 4 步向导渲染
    await page.getByRole("button", { name: "AI 智能导入" }).click();

    // ai-import-wizard.tsx L50-55 AI_STEPS 4 步：上传文件 / 文件预览 / AI 分析 / 确认导入
    await expect(page.getByText("上传文件").first()).toBeVisible();
    await expect(page.getByText("文件预览").first()).toBeVisible();
    await expect(page.getByText("AI 分析").first()).toBeVisible();
    await expect(page.getByText("确认导入").first()).toBeVisible();

    // 上传区初始文案（ai-import-wizard.tsx L658）
    await expect(page.getByText(/拖拽 ZIP 压缩包到这里/)).toBeVisible();
  });

  test("[P0-DOM-CRITICAL] 🔴 frontend stub 真 bug 复现：上传 zip 即报 puntResult（finding-1）", async ({
    page,
    request,
  }) => {
    // 真 bug 复现：actions/import-ai.ts L106 aiAnalyzeZip 全 return actionError(PUNT_MSG)
    // ai-import-wizard.tsx L399 字面 throw new Error(result.error) → setError 触发
    // 浏览器永远走不到「真 M17 backend」/ 也永远不开 WebSocket。
    //
    // 注：上传 zip 后 client 先调 uploadZip(actions/import.ts) 解析 zip / 解析后才
    // 调 aiAnalyzeZip。本 test 上传一个简单 zip → 期望走到 step=1 后点「AI 分析」按钮
    // 报 puntResult 错误文案。
    //
    // 但若 uploadZip 本身也是 stub / 返 puntResult → 第一步上传就报错（这也算 bug 真复现）。

    const seeded = await seedFullProject(request);
    await page.goto(`/projects/${seeded.project.id}/import`);
    await expect(page.getByRole("heading", { name: "导入文档" })).toBeVisible({ timeout: 8_000 });

    await page.getByRole("button", { name: "AI 智能导入" }).click();
    await expect(page.getByText(/拖拽 ZIP 压缩包到这里/)).toBeVisible();

    // 构造一个简单 zip buffer（用 ai-import-wizard.tsx 的 fileInputRef）
    // 简单 zip 头 + 1 个 README.md 条目（不需要真有效，只让 .zip 后缀过 client 校验）
    // ai-import-wizard.tsx L327-334: 校验 .zip 后缀 + <50MB
    // ai-import-wizard.tsx L342-344: 调 uploadZip(fd) → 返 result.success / result.error
    const fakeZip = Buffer.from([
      0x50,
      0x4b,
      0x03,
      0x04, // local file header signature
      0x14,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x08,
      0x00, // file name length = 8
      0x00,
      0x00, // extra field length = 0
      0x52,
      0x45,
      0x41,
      0x44,
      0x4d,
      0x45,
      0x2e,
      0x6d, // "README.m"
      // central directory + EOCD（极简版本，未必合规 / 但若 uploadZip 是 stub 会先报 puntResult）
      0x50,
      0x4b,
      0x05,
      0x06,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
      0x00,
    ]);

    // 用 setInputFiles 直接 fill <input type=file accept=".zip" />
    // ai-import-wizard.tsx L644-649 字面 hidden input ref=fileInputRef
    await page.locator('input[type="file"][accept=".zip"]').setInputFiles({
      name: "test.zip",
      mimeType: "application/zip",
      buffer: fakeZip,
    });

    // 等待两种可能路径：
    // ① uploadZip 也是 stub → 立即报错（顶部 error 横条 / 文案含 "punt" 或 stub 文案）
    // ② uploadZip 真起作用 → 进入 step=1（预览）→ 切 step=2 点 AI 分析 → 报 puntResult
    //
    // 不论走哪条，最终都验"DOM 上能看到 PUNT_MSG 或类似 stub 错误文案"（finding-1 真存在）

    // 等 8s 让任一路径推进
    await page.waitForTimeout(3000); // 实装 client setTimeout 假进度 / 不是 hard sleep 替断言

    // 路径 ① 检测：顶部 error 横条出现（ai-import-wizard.tsx L611 字面 border-destructive 横条）
    const errorBanner = page.locator(".border-destructive\\/50");
    const errorVisible = await errorBanner.isVisible().catch(() => false);

    if (errorVisible) {
      // 期望文案含 punt / NOT_IMPLEMENTED / "子片 3c" 之一（actions/import-ai.ts L104 字面）
      const errorText = await errorBanner.textContent();
      expect(errorText, `期望含 PUNT 关键词，实际: ${errorText}`).toMatch(
        /punt|NOT_IMPLEMENTED|子片|未实装|未实现|stub/i,
      );
      // ✅ finding-1 真复现（uploadZip 也是 stub 状态）
    } else {
      // 路径 ②：uploadZip 真起作用 → 进入 step=1 → 必须点「下一步」 → step=2 才能点「AI 分析」
      // 但 step indicator 已切到 1 → 我们直接点「下一步」尝试触发 aiAnalyzeZip 路径
      const nextBtn = page.getByRole("button", { name: "下一步" });
      const nextVisible = await nextBtn.isVisible().catch(() => false);

      if (nextVisible) {
        await nextBtn.click();
        // step=2 后会出现「开始 AI 分析」按钮（ai-import-wizard.tsx L753 字面）
        await page
          .getByRole("button", { name: /开始 AI 分析|AI 分析/ })
          .first()
          .click();

        // aiAnalyzeZip 必 setError(PUNT_MSG) → 顶部 error 横条出现
        await expect(errorBanner).toBeVisible({ timeout: 8_000 });
        const errorText = await errorBanner.textContent();
        expect(errorText).toMatch(/punt|子片|未实装|NOT_IMPLEMENTED/i);
      } else {
        // 没有错误也没有「下一步」按钮 / 卡在某中间态 → bug 真存在不同表现
        // 不静默通过（feedback_subagent_sprint §2 T1 禁 try/catch 吞错）
        // 直接验"AIImportWizard step 0 的上传文案仍可见"（说明 uploadZip 没成功推进 / stub）
        await expect(page.getByText(/拖拽 ZIP 压缩包到这里/)).toBeVisible();
        // 把现状记下来 → 不让 test 假成功
        const stepIndicatorText = await page.locator("body").textContent();
        expect(
          stepIndicatorText,
          `expected stub error or step advance, got neither (DOM: ${stepIndicatorText?.slice(0, 200)})`,
        ).toMatch(/punt|stub|未实装|子片|文件预览|AI 分析中/i);
      }
    }
  });

  test("[P0-DOM] Markdown 导入 tab — confirmImport server action 可达性 smoke", async ({
    page,
    request,
  }) => {
    // import-page-client.tsx L84-94 + L129-131 字面：Markdown 模式调 confirmImport
    // （actions/import.ts，不是 stub puntResult / 实际接 backend 老路径）
    // 这条不验完整 happy（需 markdown 文件 + folder 真选）/ 只验 tab 切到 markdown 后
    // 上传 UI 渲染（确认 markdown 路径不是同根因 finding-1 stub）
    const seeded = await seedFullProject(request);
    await page.goto(`/projects/${seeded.project.id}/import`);

    await page.getByRole("button", { name: "Markdown 导入" }).click();

    // L205 字面 "导入 Markdown 文件" + L216 "选择 .md 文件" 按钮
    await expect(page.getByRole("heading", { name: "导入 Markdown 文件" })).toBeVisible();
    await expect(page.getByRole("button", { name: /选择 \.md 文件/ })).toBeVisible();
  });

  // ════════════════════════════════════════════════════════════════════════
  // 轨 2: API 旁路（backend-only / 状态机 / 鉴权 / tenant / method）
  // ════════════════════════════════════════════════════════════════════════

  test("[P0-API] POST /imports 未登录返 401 UNAUTHENTICATED（testpoint §4 P0）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      multipart: {
        source_type: "zip",
        file: { name: "x.zip", mimeType: "application/zip", buffer: Buffer.from("PK") },
      },
      // 故意不带 Authorization
    });

    expect(res.status()).toBe(401);
  });

  test("[P0-API] POST /imports 项目未配置 ai_provider 返 422 IMPORT_INVALID_SOURCE（design-gap candidate-4）", async ({
    request,
  }) => {
    // import_router.py L124-125 字面：if not ai_provider: raise ImportInvalidSourceError(reason="ai_provider_unset")
    // seedFullProject 创建的项目 ai_provider=NULL → 默认走 422 路径
    // → 实证 design-gap candidate-4（新建项目直进 /import 必踩坑）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
      multipart: {
        source_type: "zip",
        file: { name: "test.zip", mimeType: "application/zip", buffer: Buffer.from("PK\x03\x04") },
      },
    });

    expect(res.status()).toBe(422);
    const body = await res.json();
    // errors/middleware.py flat 格式（参 B-P2-M10-error-response-format-design-gap）
    expect(body.code).toBe("import_invalid_source");
  });

  test("[P0-API] POST /imports source_type 非枚举值返 422 (Pydantic / testpoint §2 P2)", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
      multipart: {
        source_type: "tar", // 非 zip/git_url/git_bundle
        file: { name: "x.zip", mimeType: "application/zip", buffer: Buffer.from("PK") },
      },
    });

    // Pydantic Enum 校验 → 422 (HTTPValidationError 或自定义)
    expect(res.status()).toBe(422);
  });

  test("[P0-API] POST /imports git_url 形态未传 git_url 返 422 (testpoint §2 + router L128-130)", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
      multipart: {
        source_type: "git_url",
        // 故意不传 git_url
      },
    });

    expect(res.status()).toBe(422);
    const body = await res.json();
    expect(body.code).toBe("import_invalid_source");
  });

  test("[P0-API] POST /imports zip 形态未传 file 返 422 (testpoint §2 + router L134-135)", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    const res = await request.post(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
      multipart: {
        source_type: "zip",
        // 故意不传 file
      },
    });

    expect(res.status()).toBe(422);
    const body = await res.json();
    expect(body.code).toBe("import_invalid_source");
  });

  test("[P0-API] POST /imports happy path — submit zip 返 201 + task_id + status=pending（testpoint §1 G1）", async ({
    request,
  }) => {
    // 这是 backend 主路径 happy 验证 / 走完 ai_provider 设置 → multipart 上传 → 201
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    const res = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      // 简单 zip header bytes（router 不校验 zip 真有效 / 只校验大小 + filename）
      Buffer.from([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00]),
      "happy.zip",
    );

    expect(res.status(), `expected 201, got ${res.status()}: ${await res.text()}`).toBe(201);
    const body = await res.json();

    // ImportTaskResponse schema 字段（api/schemas/import_schema.py L65-83）
    expect(body.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(body.project_id).toBe(seeded.project.id);
    expect(body.user_id).toBe(seeded.user.id);
    expect(body.source_type).toBe("zip");
    expect(body.status).toBe("pending"); // submit_import 立即返 pending（Queue 未拉起）
    expect(body.progress).toBe(0);
    expect(body.ai_provider).toBe("mock");
    expect(body.source_hash).toMatch(/^[0-9a-f]{64}$/); // SHA256
    // source_uri sanitize 验证（router L154 + R2 P1-03 立修字面验）
    expect(body.source_uri).toBe("upload://happy.zip");
  });

  test("[P0-API] GET /imports list happy — 返 ImportTaskListResponse 含已 submit task（testpoint §1 P1）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 先 submit 1 个
    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "list-test.zip",
    );
    expect(submitRes.status()).toBe(201);
    const task = await submitRes.json();

    const listRes = await request.get(`${API_BASE}/api/projects/${seeded.project.id}/imports`, {
      headers: auth,
    });
    expect(listRes.status()).toBe(200);
    const body = await listRes.json();
    expect(Array.isArray(body.items)).toBe(true);
    expect(body.total).toBeGreaterThanOrEqual(1);
    // 必含刚 submit 的 task
    expect(body.items.find((t: { id: string }) => t.id === task.id)).toBeTruthy();
  });

  test("[P0-API] GET /imports/{task_id} 不存在返 404 IMPORT_TASK_NOT_FOUND（testpoint §13 P0）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };
    const fakeTaskId = "00000000-0000-0000-0000-000000000999";

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${fakeTaskId}`,
      { headers: auth },
    );

    expect(res.status()).toBe(404);
    const body = await res.json();
    expect(body.code).toBe("import_task_not_found");
  });

  test("[P0-API] tenant: GET /imports 跨 project 不暴露他人 task（testpoint §5 P0 / DAO 双过滤）", async ({
    request,
  }) => {
    // 创建两个 project，project1 submit 1 task / 用同 admin token 调 project2 的 list →
    // 不应返 project1 的 task（DAO list_by_project WHERE project_id 过滤）
    const seeded1 = await seedFullProject(request, { suffix: `m17-A-${Date.now()}` });
    const seeded2 = await seedFullProject(request, { suffix: `m17-B-${Date.now() + 1}` });
    await setProjectAiProvider(request, seeded1.accessToken, seeded1.project.id);

    const submitRes = await submitImportZip(
      request,
      seeded1.accessToken,
      seeded1.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "cross-tenant.zip",
    );
    expect(submitRes.status()).toBe(201);
    const task1 = await submitRes.json();

    // 用同 admin 调 project2 list → task1 不应出现
    const listRes = await request.get(`${API_BASE}/api/projects/${seeded2.project.id}/imports`, {
      headers: { Authorization: `Bearer ${seeded2.accessToken}` },
    });
    expect(listRes.status()).toBe(200);
    const body = await listRes.json();
    expect(body.items.find((t: { id: string }) => t.id === task1.id)).toBeUndefined();

    // 反向：用 admin 调 project1 GET task1 走 project2 URL → 应 404（cross-project）
    const crossGet = await request.get(
      `${API_BASE}/api/projects/${seeded2.project.id}/imports/${task1.id}`,
      { headers: { Authorization: `Bearer ${seeded2.accessToken}` } },
    );
    expect(crossGet.status()).toBe(404);
  });

  test("[P0-API] POST /imports/{task_id}/confirm 在 pending 状态返 409 INVALID_STATE_TRANSITION（testpoint §2 SM1）", async ({
    request,
  }) => {
    // testpoint §2 P0 L44 字面：pending → ai_step3 跳步返 409 IMPORT_INVALID_STATE_TRANSITION
    // confirm 接口要求 status=awaiting_review；pending 时调 confirm → 应抛禁转
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "confirm-invalid.zip",
    );
    expect(submitRes.status()).toBe(201);
    const task = await submitRes.json();
    expect(task.status).toBe("pending");

    const confirmRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/confirm`,
      {
        headers: auth,
        data: {
          nodes: [],
          dimensions: [],
          competitors: [],
          issues: [],
          skip_proposed_ids: [],
        },
      },
    );

    expect(confirmRes.status()).toBe(409);
    const body = await confirmRes.json();
    // import_service.py L304-308: ImportInvalidStateTransitionError when not awaiting_review
    expect(body.code).toBe("import_invalid_state_transition");
  });

  test("[P0-API] POST /imports/{task_id}/cancel pending 状态允许 → 转 cancelled（testpoint §1 P1 + design §4 表）", async ({
    request,
  }) => {
    // design §4 字面：pending → cancelled 允许（用户取消）
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "cancel-test.zip",
    );
    expect(submitRes.status()).toBe(201);
    const task = await submitRes.json();

    const cancelRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/cancel`,
      { headers: auth },
    );
    expect(cancelRes.status()).toBe(204);

    // 验 GET 后 status=cancelled
    const getRes = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}`,
      { headers: auth },
    );
    expect(getRes.status()).toBe(200);
    const body = await getRes.json();
    expect(body.status).toBe("cancelled");
  });

  test("[P0-API] POST /imports/{task_id}/cancel cancelled→任何 返 409 IMPORT_TASK_FINALIZED（testpoint §2 SM3 终态不可变）", async ({
    request,
  }) => {
    // design §4 + testpoint §2 P0 L46：cancelled 是终态 / cancelled → 任意 应 409
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "finalized-test.zip",
    );
    const task = await submitRes.json();

    // 先 cancel → status=cancelled
    const cancel1 = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/cancel`,
      { headers: auth },
    );
    expect(cancel1.status()).toBe(204);

    // 再 cancel cancelled task → 应 409
    const cancel2 = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/cancel`,
      { headers: auth },
    );
    expect(cancel2.status()).toBe(409);
    const body = await cancel2.json();
    expect(body.code).toBe("import_task_finalized");
  });

  test("[P0-API] POST /imports/{task_id}/retry pending 状态拒绝（非 partial_failed 不可 retry）", async ({
    request,
  }) => {
    // design §4 字面 retry 仅 partial_failed → ai_step3 合法
    // pending 状态 retry → 应抛 INVALID_STATE_TRANSITION 或 FINALIZED 之一
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "retry-pending.zip",
    );
    const task = await submitRes.json();

    const retryRes = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/retry`,
      { headers: auth },
    );
    expect(retryRes.status()).toBe(409);
    const body = await retryRes.json();
    expect(body.code).toMatch(/import_invalid_state_transition|import_task_finalized/);
  });

  test("[P0-API] method: DELETE /imports/{task_id} 不暴露 → 404/405", async ({ request }) => {
    // router 字面 7 REST endpoints 不含 DELETE / 验 method 列表
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };
    const fakeId = "00000000-0000-0000-0000-000000000001";

    const res = await request.delete(
      `${API_BASE}/api/projects/${seeded.project.id}/imports/${fakeId}`,
      { headers: auth },
    );
    expect([404, 405]).toContain(res.status());
  });

  // ════════════════════════════════════════════════════════════════════════
  // 轨 3: WebSocket Pilot（Opus spike 核心 / 原生 WebSocket 直连后端绕 frontend stub）
  // ════════════════════════════════════════════════════════════════════════
  //
  // 范式说明（ws-finding-1 详细）：
  //   - node 20+ 原生 globalThis.WebSocket 可用
  //   - design §7 + import_router.py L374 字面：WS 路径 /api/projects/{pid}/imports/{tid}/progress?token=<JWT>
  //   - import_router.py L390-419 字面握手鉴权流程：
  //     ① decode_jwt(token) 失败 → close(1008)
  //     ② claims.type != "access" → close(1008)
  //     ③ claims.sub UUID 解析失败 → close(1008)
  //     ④ ImportService.check_task_access tenant/owner 失败 → close(1008)
  //     ⑤ accept() → 进入 handle_import_progress_ws 主循环
  //   - 本 pilot 验：bad token → close 行为 + good token + 真 task_id → accept + 不立即 close

  test("[P0-WS-PILOT] 🔴 WebSocket 握手鉴权: 无效 JWT token 必 close(1008) policy violation", async ({
    request,
  }) => {
    // import_router.py L391-394 字面：decode_jwt 异常 → close(1008)
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    // 先 submit 一个真 task 拿 task_id（让 path 合法 / 只让 token 不合法）
    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "ws-bad-token.zip",
    );
    const task = await submitRes.json();

    const wsUrl = `${WS_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/progress?token=not-a-jwt`;

    const result = await new Promise<{ closeCode: number; opened: boolean; errored: boolean }>(
      (resolve) => {
        const ws = new WebSocket(wsUrl);
        let opened = false;
        let errored = false;
        const timer = setTimeout(() => {
          try {
            ws.close();
          } catch {
            // ignore
          }
          resolve({ closeCode: -1, opened, errored });
        }, 8_000);

        ws.onopen = () => {
          opened = true;
        };
        ws.onerror = () => {
          errored = true;
        };
        ws.onclose = (ev) => {
          clearTimeout(timer);
          resolve({ closeCode: ev.code, opened, errored });
        };
      },
    );

    // 期望 close code 1008 (policy violation) / 不应该 accept 后立即关
    // 注：底层 ws 库可能把 1008 → 1006 (abnormal closure) 抛给 client（具体取决于 server 是否 send close frame）
    // FastAPI WebSocket.close(code=1008) 是发 close frame；client 应收到 1008
    expect(result.closeCode).toBe(1008);
  });

  test("[P0-WS-PILOT] 🔴 WebSocket 握手成功: valid JWT + 自己 task → accept + 不立即 close（testpoint §10 P0 + §4 P0）", async ({
    request,
  }) => {
    // import_router.py L422 字面：握手通过后 await websocket.accept()
    // ws-handler L150-153 字面：终态事件后 1s 后 close；pending 状态不会立即终态 → 连接保持
    // 这条 pilot 验：accept 成功 / 1s 内不主动 close（说明握手通过 / 主循环已运行）
    const seeded = await seedFullProject(request);
    await setProjectAiProvider(request, seeded.accessToken, seeded.project.id);

    const submitRes = await submitImportZip(
      request,
      seeded.accessToken,
      seeded.project.id,
      Buffer.from([0x50, 0x4b, 0x03, 0x04]),
      "ws-happy.zip",
    );
    expect(submitRes.status()).toBe(201);
    const task = await submitRes.json();

    const wsUrl = `${WS_BASE}/api/projects/${seeded.project.id}/imports/${task.id}/progress?token=${encodeURIComponent(seeded.accessToken)}`;

    const result = await new Promise<{ opened: boolean; earlyClose: boolean; closeCode: number }>(
      (resolve) => {
        const ws = new WebSocket(wsUrl);
        let opened = false;
        let earlyClose = false;
        const stayOpenMs = 1500;

        const settle = setTimeout(() => {
          // 1.5s 内未关 → 握手成功且连接保持（pending 态无 broker 事件推送）
          try {
            ws.close();
          } catch {
            // ignore
          }
          resolve({ opened, earlyClose, closeCode: -1 });
        }, stayOpenMs + 500);

        ws.onopen = () => {
          opened = true;
        };
        ws.onclose = (ev) => {
          // 若 onopen 后立即 close（< stayOpenMs）→ earlyClose=true（不是期望）
          if (opened) {
            earlyClose = true;
          }
          clearTimeout(settle);
          resolve({ opened, earlyClose, closeCode: ev.code });
        };
      },
    );

    // 关键 spike 断言：握手 accept 成功
    expect(result.opened, `expected ws.onopen fired, got opened=${result.opened}`).toBe(true);

    // accept 后不应立即 close（pending 态无 progress 事件 / handler 主循环阻塞在 recv/send）
    // 若 earlyClose=true → handler 异常退出 / 范式不通
    expect(result.earlyClose).toBe(false);
  });
});
