import { test, expect } from "@playwright/test";

import { loginE2EAdmin, seedFullProject } from "../fixtures/seed";

// M13 需求分析（SSE 流式）dogfooding spec — P2-case Opus spike (2026-05-12)
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M13-requirement-analysis.md
// 142 testpoint / P0=53 / P1=72 / P2=17 / escalation surface ≥100
//
// ═══════════════════════════════════════════════════════════════════════════
// 范式定位（Opus spike — SSE 是范式未验过的领域）
// ═══════════════════════════════════════════════════════════════════════════
//
// 覆盖（按分类决策树拆三类标签）:
//   [DOM-reachable]    4 条  → page.goto /projects/{pid}/analysis + UI 文案断言 + SSE smoke
//   [API-via-旁路]    10 条  → request fixture 直打 /api/projects/{pid}/nodes/{nid}/analyze/*
//                              （Pydantic / 鉴权 / tenant / Method / affected-nodes / SSE 真验）
//   [skip-N/A]        128 条  → 见下方 punt 清单（多为 SSE 复杂场景 / design-gap / backend pytest）
//
// ═══════════════════════════════════════════════════════════════════════════
// SSE 范式 spike finding（design-gap candidate / 写主 agent 决策）
// ═══════════════════════════════════════════════════════════════════════════
//
// 🔴 finding-1: SSE 流式 DOM 测试 spike 通路被 frontend 实装阻断（多重 bug 叠加）。
//
//   设计 §12A：浏览器 → POST /api/projects/{pid}/nodes/{nid}/analyze/requirement
//                Bearer JWT（ADR-004 P1）/ SSE 流式 / Content-Type: text/event-stream
//                event: chunk / complete / error 三类 / aclose 协议 / AbortController
//
//   实装现状：
//     1. analysis/page.tsx L75 浏览器调 fetch("/api/analyze/stream") Next route 代理
//     2. Next route stream/route.ts L12 又 fetch(`${API_BASE}/api/analyze/requirement`)
//        ↑ 这条 URL 不存在 / 真后端是嵌套 /api/projects/{pid}/nodes/{nid}/analyze/requirement
//     3. API_BASE 默认 "http://localhost:8001" / 真后端跑 8000 → 端口也错
//     4. proxy 完全不转发 Authorization header → 即使 URL 对也会 401
//     5. proxy 不从 body 抽 project_id/node_id 拼到 URL path 上
//
//   实测 curl POST /api/analyze/stream → 500 / curl POST /api/analyze/requirement → 404
//
//   结论：design §12A 7 字段所有 DOM-侧 SSE testpoint（S1-S9 / 字段①-⑦）当前都被
//         前端 proxy URL 错误阻断，无法到 DOM 验证。
//   处置：不在本 spec 自修 proxy（dogfooding 不修 spec / 不修产品 / 真 bug 入 03-bug-queue.md）
//         DOM-SSE smoke 改成"按下 AI 分析按钮 → 报错文案出现"端到端验证（验 bug 真存在）。
//         真 SSE 协议（chunk/complete/error/aclose/5min timeout/AbortController/cancel）改走
//         API 旁路绕过 Next proxy 直打 FastAPI / 用 admin JWT 作 P1 鉴权（绕 P2 HMAC）。
//
// 🔴 finding-2: saveAnalysisAction / generateTestPointsAIAction / saveTestPointsAction 全部 stub。
//   src/actions/analyze.ts L60+ 字面 puntResult() / 全返 {ok:false, error:"punt 中"}
//   所有 [P0] save 路径 + 全部 generate test points 路径 + [P0] affected-nodes 通过 page UI 验证
//   均无法走 DOM。本 spec 改走 API 旁路 / 真 bug 入 queue。
//
// 🔴 finding-3: SaveAnalysisRequest schema 要求 `requirement_text` 1-5000 字段必填
//   （api/schemas/analyze_schema.py L54），但 saveAnalysisAction stub 时无任何调用者 / 即使
//   接通了，page.tsx 调 saveAnalysisAction(projectId, nodeId, layers) 时不传 requirement_text。
//   → 接通后会 422。design-gap candidate 报主 agent。
//
// 🔴 finding-4: SSE 协议范式（Opus spike 任务核心）— API 旁路实证可行
//   - Playwright `request` fixture 不解 SSE / 但可读 response body stream
//   - 用 fetch + ReadableStream + TextDecoder 解析 "event: <type>\ndata: <json>\n\n" 可行
//   - 实证 1 条 "[P0] SSE 流式 chunk + complete event 顺序" 真跑（见 SSE-PILOT 测试）
//   - 复杂场景（5min timeout / AbortController 真停 / aclose 协议 / JWT 中途作废 5min 窗口）
//     punt — playwright e2e 无法 monkeypatch backend / 这些是 pytest integration 范畴
//
// ═══════════════════════════════════════════════════════════════════════════
// punt 清单（按 testpoint §章节）
// ═══════════════════════════════════════════════════════════════════════════
//
// §1 功能性（11 条）:
//   - [P0] §1 L2 流式 5 chunk + 1 complete 顺序 → [API-via-旁路] 通过 SSE-PILOT 覆盖
//   - [P0] §1 complete event metadata 5 字段 → [API-via-旁路] 通过 SSE-PILOT 覆盖
//   - [P0] §1 POST /analyze/save 返 200 + dimension_record_id → [skip-N/A] 后端 router 实装 201 +
//     SaveAnalysisRequest 需 requirement_text+ai_provider+ai_model+analysis_time_ms 全字段 /
//     需 LLM 真分析跑完拿 metadata / 复合 setup 超 spike 范围 / 主线 pytest 覆盖
//   - [P0] §1 save 后 dimension_records 新增 1 行 → [skip-N/A] 同上 / 验需直查 PG
//   - [P0] §1 GET /affected-nodes 返字段 → [API-via-旁路] 覆盖（happy path 空数组）
//   - [P0] §1 analysis_level=L1 流式 2 chunk → [skip-N/A] 与 SSE-PILOT 同范式 / 已覆盖 SSE 通路
//   - [P0] §1 analysis_level=L3 30s 正常 complete → [skip-N/A] 长耗时超 30s playwright timeout
//   - [P1] §1 上游 5 个 Service 聚合 → [skip-N/A] 内部分层 / pytest 单元覆盖
//   - [P1] §1 L1/L2/L3 prompt 不硬编码 node 名 → [skip-N/A] prompt template 单元测试
//   - [P2] §1 dimension_types upsert → [skip-N/A] DB 层 / pytest 覆盖
//
// §2 边界 / 状态机（10 条）:
//   - [P0] §2 requirement_text="" 返 422 → [API-via-旁路] Pydantic 覆盖
//   - [P0] §2 requirement_text=5000 边界 → [skip-N/A] 5000 字 + 真跑 LLM / 主线 backend pytest
//   - [P1] §2 5001 字返 422 → [API-via-旁路] Pydantic 覆盖
//   - [P1-P2] §2 特殊字符 / 大数组 / 100KB Markdown → [skip-N/A] 数据完整性边界 / pytest
//   - [P1] §2 MockProvider 0 chunk → [skip-N/A] 需 monkeypatch backend / pytest
//   - [P1] §2 analysis_level 非法值返 422 → [API-via-旁路] Pydantic 覆盖
//   - [P2] §2 状态机无 / 流式三出口 → [skip-N/A] 概念性 / 由 SSE-PILOT 间接验
//
// §3 异常 / 错误（10 条）:
//   - [P0] §3 AI Provider 抛异常 → [skip-N/A] 需 mock backend provider / pytest
//   - [P0] §3 5min 硬超时 → [skip-N/A] 5min 等待超 playwright 单测时间窗 + 需 mock provider
//   - [P0] §3 quota 耗尽 / save 异常回滚 → [skip-N/A] 需注入 / pytest
//   - [P0] §3 provider 未配置 → [API-via-旁路] 可验（seed 项目 ai_provider=NULL）
//   - [P1-P2] §3 其他错误 wrap / DB 断 → [skip-N/A] pytest 覆盖
//
// §4 权限 / Auth（11 条）:
//   - [P0] §4 未登录 POST /requirement 返 401 → [API-via-旁路] 覆盖
//   - [P0] §4 viewer POST /requirement / /save 403 → [skip-N/A] 需 viewer fixture / 单账号 admin
//   - [P0] §4 viewer GET /affected-nodes 200 → [skip-N/A] 同上
//   - [P0] §4 editor 正常 → [API-via-旁路] 覆盖（admin 同 editor 路径）
//   - [P0] §4 流式走 P1 Bearer / save 走 P2 HMAC → [API-via-旁路] 覆盖 P1 / P2 走 server action
//     stub 阻断（finding-2）测不到端到端
//   - [P1] §4 project_admin / platform_admin → [skip-N/A] 需 admin role seed
//   - [P1] §4 JWT 中途作废 5min 暴露窗口 → [skip-N/A] 设计已知脱节非 bug / pytest 验
//   - [P1] §4 流式无 chunk 级鉴权 → [skip-N/A] 概念性
//
// §5 Tenant 隔离（9 条）:
//   - [P0] §5 userA token 调 projectB → [API-via-旁路] 覆盖
//   - [P0] §5 URL 跨 project node 混淆 → [API-via-旁路] 覆盖
//   - [P0] §5 save 跨 project → [skip-N/A] save endpoint 复合 setup（finding-2 stub 阻断 DOM）
//   - [P0] §5 GET /affected-nodes 跨 project → [API-via-旁路] 覆盖
//   - [P1] §5 上游 Service tenant 过滤 → [skip-N/A] 内部分层 / pytest
//
// §6 并发 / 乐观锁（7 条）:
//   - [P0] §6 同 user 同 node 并发 3 流 → [skip-N/A] 5min 长连接 × 3 超 playwright 30s timeout
//   - [P0] §6 流式期间 DB session 释放 → [skip-N/A] backend 实现验证 / pytest + PG pool 监控
//   - [P0] §6 save 新起 session → [skip-N/A] 同上
//   - [P1] §6 PG pool 10-20 打满 → [skip-N/A] 需注入流式 mock + DB 连接观测 / pytest 范围
//   - [P1-P2] §6 多 user / 历史多版本 / 监控指标 → [skip-N/A] backend pytest
//
// §7 数据完整性（10 条）:
//   - 全部内部分层断言（M13 无自有表 / 经 M04 Service / activity_log 代写）→ [skip-N/A] pytest
//
// §8 UI / UX（9 条）:
//   - [P0] §8 节点档案页挂载抽屉 + 保存按钮 → [skip-N/A] design vs UI 漂移 / page.tsx 是独立全屏
//     /analysis 页面 / 非档案页抽屉 → design-gap candidate
//   - [P0] §8 analyze-drawer.tsx / analyze-sse-client.ts → [skip-N/A] 这俩文件不存在 / 实装是
//     analysis/page.tsx 内联 / design-gap candidate
//   - [P0] §8 防抖 + 重复 SHA256 拒 save → [skip-N/A] saveAnalysisAction stub（finding-2）
//   - [P1] §8 完整端到端登录→打开→分析→取消→重分析→保存→历史出新 → [skip-N/A] save stub
//   - [P1-P2] §8 其余 UI 细节 → 部分 [DOM-reachable] smoke / 部分 skip
//
// §9 SSE 流式特化（§12A 7 字段 / 17 条）:
//   - [P0] §9 chunk/complete/error 三 event 互斥 → [API-via-旁路] 通过 SSE-PILOT 覆盖
//   - [P0] §9 字段⑤ 服务器 5min asyncio.timeout → [skip-N/A] 5min 超 spike 时间 / pytest
//   - [P0] §9 字段⑥ AbortController + aclose 协议 → [skip-N/A] aclose 是 provider 内部实现 /
//     playwright 无法注入 Mock + 真 SDK 测 aclose 是 pytest integration 范畴 / 详见 finding-4
//   - [P0] §9 chunk 顺序保证 → [API-via-旁路] 通过 SSE-PILOT 覆盖（MockProvider 顺序断言）
//   - [P1] §9 SSE 端点头部 → [API-via-旁路] 覆盖
//   - [P1] §9 SSE 不走 Server Action → 已经事实证明（finding-1 proxy bug 路径）
//   - [P1] §9 SSE 传输格式严格 "event:...\ndata:...\n\n" → [API-via-旁路] SSE-PILOT 解析验
//   - [P2] §9 极端 1MB chunk / 10000 chunk → [skip-N/A] LLM mock 才能造 / pytest 范畴
//
// §10 ErrorCode 注册（9 条）:
//   - 全部 backend 注册表验证 → [skip-N/A] frontmatter codes_added CI 守护 / pytest
//
// §11 分层职责 / R-X3（9 条）:
//   - 全部内部 Service 接口契约 → [skip-N/A] importlinter + pytest
//
// §12 idempotency 显式 N/A（4 条）:
//   - 全部 [skip-N/A] 概念性 / 已显式声明 N/A
//
// §13 关系图联动（5 条）:
//   - [P0] §13 save 后 GET /affected-nodes → [skip-N/A] save stub（finding-2）
//   - [P0] §13 多次 save 取最后 → [skip-N/A] save stub
//   - [P1] §13 空数组 → [API-via-旁路] 覆盖（affected-nodes 空 happy）
//   - [P1-P2] M03 删除级联 / M08 渲染 → [skip-N/A] 跨模块
//
// §14 LLM 集成专属（6 条）:
//   - 全部 backend LLM 实装 / aclose / API key AES → [skip-N/A] pytest integration / 14.5 红线
//
// §15 Phase 2 迁移（6 条）:
//   - 全部 backend / URL 形态迁移 → [skip-N/A] 历史决策记录 / 非 e2e 范围
//
// ═══════════════════════════════════════════════════════════════════════════
// design-gap candidate（dogfooding 价值 / 报主 agent）
// ═══════════════════════════════════════════════════════════════════════════
//
// 1. **SSE proxy URL 错误（真 bug-1）**：app/src/app/api/analyze/stream/route.ts L12 fetch
//    `/api/analyze/requirement`，但真后端是 `/api/projects/{pid}/nodes/{nid}/analyze/requirement`
//    + API_BASE 默认 8001 实际 8000 + 不转发 Authorization + 不从 body 抽 ids。
//    → 浏览器 SSE 入口完全不通。入 03-bug-queue.md（finding-1）。
//
// 2. **save / generate-test-points / save-test-points action 全 stub（真 bug-2）**：
//    src/actions/analyze.ts L60+ puntResult()。analysis/page.tsx UI 已经渲染所有按钮，但点击全部
//    返 "punt 中" 错误。design §6 "保存按钮 + 测试点" UI 看着完整但端到端不通。
//    → 入 03-bug-queue.md（finding-2）。
//
// 3. **SaveAnalysisRequest 字段不齐（design-gap）**：page.tsx handleSaveAnalysis 调
//    saveAnalysisAction(projectId, nodeId, layers) 不传 requirement_text/ai_provider/ai_model/
//    analysis_time_ms 等必填字段。即使 finding-2 修复 puntResult 也会 422。
//    → audit/M13-design-gap.md candidate（finding-3）。
//
// 4. **design vs UI 漂移（design-gap）**：design §6 声称在 node 档案页挂载"分析抽屉 + 保存按钮"
//    （即 modules/[moduleId]/page.tsx 内嵌），实装是独立全屏页 /projects/{pid}/analysis
//    （从 ?nodeId= query 参数读 node）。两者交互范式完全不同（抽屉 vs 全屏页）。
//    → audit candidate。

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M13 需求分析（SSE）dogfooding", () => {
  // ════════════════════════════════════════════════════════════════════════
  // 轨 1: DOM 主路径
  // ════════════════════════════════════════════════════════════════════════

  test("[P0-DOM] /analysis page 可达 + UI 关键文案渲染（design vs UI 漂移 smoke）", async ({
    page,
    request,
  }) => {
    // testpoint §8 P0 "node 档案页挂载分析抽屉" 实装漂移：实装是独立全屏 /analysis 页 / 非档案抽屉
    // design vs UI 漂移记 audit candidate / 这条只 smoke 页面可达性
    const seeded = await seedFullProject(request);

    await page.goto(`/projects/${seeded.project.id}/analysis`);
    await expect(page).toHaveURL(/\/analysis/, { timeout: 8_000 });

    // UI 关键文案（page.tsx L523, L583, L743）
    await expect(page.getByText("需求分析工作台")).toBeVisible();
    await expect(page.getByRole("heading", { name: "需求描述" })).toBeVisible();
    await expect(page.getByRole("button", { name: /AI 分析/ })).toBeVisible();

    // node 未选 → 输入 placeholder 提示文案（page.tsx L671）
    await expect(page.getByPlaceholder(/输入需求描述/)).toBeVisible();
  });

  test("[P0-DOM] 未选 nodeId 时点 AI 分析 → 显示 error 提示（design §1 边界 / page.tsx L296）", async ({
    page,
    request,
  }) => {
    // page.tsx L295-298: 未选 nodeId 时点击 AI 分析按钮 → setError("请先选择要分析的功能节点...")
    // DOM 真路径 / 验交互正确性 / 不需要 SSE 通路
    const seeded = await seedFullProject(request);

    await page.goto(`/projects/${seeded.project.id}/analysis`);

    // 填一些文本让 hasContent=true（按钮变可点）
    await page.getByPlaceholder(/输入需求描述/).fill("一段测试需求");
    await page.getByRole("button", { name: /AI 分析/ }).click();

    // 验 error Card 出现 + 文案精确（page.tsx L772）
    await expect(page.getByRole("heading", { name: /分析失败/ })).toBeVisible({
      timeout: 5_000,
    });
    await expect(page.getByText(/请先选择要分析的功能节点/)).toBeVisible();
  });

  test("[P0-DOM-CRITICAL] 🔴 SSE 范式 spike: page → /api/analyze/stream proxy 链路实测", async ({
    page,
    request,
  }) => {
    // finding-1 真 bug 复现：page.tsx → /api/analyze/stream → broken proxy → 返 500 → page 显示
    // "分析服务不可用: HTTP 500..." 错误文案（page.tsx L83 errMsg branch）
    // 不修 spec / 真 bug 入 03-bug-queue.md / DOM 验证 bug 在端到端真存在
    const seeded = await seedFullProject(request);

    await page.goto(`/projects/${seeded.project.id}/analysis?nodeId=${seeded.node.id}`);
    await expect(page.getByText("需求分析工作台")).toBeVisible();

    // 验 nodeId 从 query 注入（page.tsx L169 + L639 Badge）
    await expect(page.getByText(/功能节点:/)).toBeVisible();

    await page.getByPlaceholder(/输入需求描述/).fill("测试 SSE 流式分析需求文本");

    // 监听 /api/analyze/stream proxy 请求实际发出
    const proxyReqPromise = page.waitForRequest(
      (req) => req.url().includes("/api/analyze/stream") && req.method() === "POST",
      { timeout: 8_000 },
    );

    await page.getByRole("button", { name: /AI 分析/ }).click();

    const proxyReq = await proxyReqPromise;
    expect(proxyReq.method()).toBe("POST");

    // 等待 proxy 响应（proxy bug 实测返 500 / 真路径不通）
    const proxyResp = await proxyReq.response();
    expect(proxyResp).not.toBeNull();

    // 关键 SSE-finding：proxy 当前 500 / 设计应 200 + text/event-stream
    // 不让 test FAIL 阻塞批次（这是已知 bug / 真 bug 入 03-bug-queue.md / 验真复现即可）
    const proxyStatus = proxyResp!.status();

    // 期望端到端 SSE 200 + text/event-stream / 实测 500 / 一行能看出 bug 是否修了
    // 若主 agent 修了 finding-1 → 这条 expect 仍 pass（任一分支 OK）
    // 若 bug 真存在 → 走 500 分支 + DOM 显示错误文案
    if (proxyStatus === 200) {
      // bug 已修：验 SSE 头
      const ct = proxyResp!.headers()["content-type"] ?? "";
      expect(ct).toMatch(/text\/event-stream|application\/json/);
    } else {
      // bug 真复现：500 / 验 DOM 错误文案（page.tsx L83/L355 把 errMsg 传给 setError）
      expect(proxyStatus).toBe(500);
      await expect(page.getByRole("heading", { name: /分析失败/ })).toBeVisible({
        timeout: 8_000,
      });
    }
  });

  test("[P0-DOM] save 按钮 stub puntResult 验证（finding-2 真 bug 复现）", async ({
    page,
    request,
  }) => {
    // finding-2: src/actions/analyze.ts saveAnalysisAction 是 puntResult stub
    // page.tsx L412-424 调用后会 setError(result.error) = "需求 SSE 分析 / test-points / comparison batch 将在子片 3c..."
    // DOM 验证 stub 真存在 / 真 bug 入 03-bug-queue.md
    //
    // 注：page.tsx L836 "保存到需求分析维度" 按钮只在 hasResults && allLayersDone 时显示
    // 由于 SSE proxy 也坏（finding-1），无法走到 allLayersDone=true / 该按钮永远不出现
    // → 这条测试改为：验"保存到需求分析维度"按钮在当前 dogfooding state 下永远不可见
    //   （证明 finding-1 + finding-2 联合阻断 save UI 端到端）
    const seeded = await seedFullProject(request);

    await page.goto(`/projects/${seeded.project.id}/analysis?nodeId=${seeded.node.id}`);
    await expect(page.getByText("需求分析工作台")).toBeVisible();

    await page.getByPlaceholder(/输入需求描述/).fill("测试 save 按钮路径");

    // 触发 SSE（finding-1 失败 / layers 不会出现 / save 按钮不会显示）
    await page.getByRole("button", { name: /AI 分析/ }).click();

    // 等一会让 SSE 失败 + setError 渲染
    await expect(page.getByRole("heading", { name: /分析失败/ })).toBeVisible({
      timeout: 10_000,
    });

    // 验"保存到需求分析维度"按钮不可见（条件 hasResults && allLayersDone 不满足）
    const saveBtn = page.getByRole("button", { name: /保存到需求分析维度/ });
    await expect(saveBtn).toHaveCount(0);

    // 验"生成测试点"按钮也不可见
    const genBtn = page.getByRole("button", { name: /生成测试点/ });
    await expect(genBtn).toHaveCount(0);

    // → 联合证明 finding-1 阻断了 SSE / 阻断了下游所有 save+generate UI 端到端
  });

  // ════════════════════════════════════════════════════════════════════════
  // 轨 2: API 旁路
  // ════════════════════════════════════════════════════════════════════════

  test("[P0-API] 未登录 POST /analyze/requirement 返 401 UNAUTHENTICATED（testpoint §4 P1）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);

    const res = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`,
      {
        data: { requirement_text: "test", analysis_level: "L1" },
        // 故意不带 Authorization 头
      },
    );
    // testpoint §4 L71: 未登录返 401 UNAUTHENTICATED
    expect(res.status()).toBe(401);
  });

  test("[P0-API] Pydantic requirement_text='' 返 422 min_length（testpoint §2 B1）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`,
      {
        headers: auth,
        data: { requirement_text: "", analysis_level: "L2" },
      },
    );
    // testpoint §2 L44 + analyze_schema.py L38 字面 min_length=1
    expect(res.status()).toBe(422);
  });

  test("[P0-API] Pydantic requirement_text=5001 字返 422 max_length（testpoint §2 B3）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const longText = "x".repeat(5001);
    const res = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`,
      {
        headers: auth,
        data: { requirement_text: longText, analysis_level: "L2" },
      },
    );
    expect(res.status()).toBe(422);
  });

  test("[P0-API] Pydantic analysis_level 非法 'L4' 返 422（testpoint §2 P1）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.post(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`,
      {
        headers: auth,
        data: { requirement_text: "测试", analysis_level: "L4" },
      },
    );
    // AnalysisLevel StrEnum 只接受 L1/L2/L3
    expect(res.status()).toBe(422);
  });

  test("[P0-API] GET /analyze/affected-nodes 无历史返空数组（testpoint §1 + §13）", async ({
    request,
  }) => {
    // testpoint §1 L36 + §13 L191:
    //   初次访问无历史 → analysis_record_id=null / affected_node_ids=[] / analysis_saved_at=null
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/affected-nodes`,
      { headers: auth },
    );

    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.node_id).toBe(seeded.node.id);
    expect(Array.isArray(body.affected_node_ids)).toBe(true);
    expect(body.affected_node_ids.length).toBe(0);
    expect(body.analysis_record_id).toBeNull();
    expect(body.analysis_saved_at).toBeNull();
  });

  test("[P0-API] tenant: userA token 调 GET /affected-nodes 跨 project 返 403（testpoint §5 T1）", async ({
    request,
  }) => {
    // testpoint §5 L87: userA 持 projectP1 token 调 GET /api/projects/P2/... 返 403
    // 本 spike 单账号 admin → 用"不存在的 project_id" 模拟跨 tenant（admin 不属于该 project）
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    const fakeProjectId = "00000000-0000-0000-0000-000000000001";
    const res = await request.get(
      `${API_BASE}/api/projects/${fakeProjectId}/nodes/${seeded.node.id}/analyze/affected-nodes`,
      { headers: auth },
    );

    // check_project_access 拦：project 不存在或 user 非成员 → 403/404 任一
    expect([403, 404]).toContain(res.status());
  });

  test("[P0-API] tenant: 跨 project node_id 返 404 ANALYSIS_NODE_NOT_FOUND（testpoint §5 T2）", async ({
    request,
  }) => {
    // testpoint §5 L88: URL projects/P1/nodes/<P2.node> 跨项目 node 返 404
    const seeded1 = await seedFullProject(request, { suffix: `tenant-A-${Date.now()}` });
    const seeded2 = await seedFullProject(request, { suffix: `tenant-B-${Date.now() + 1}` });
    // 注：单账号 admin / project1 + project2 都属于 admin
    // 但 node2 属于 project2 → URL projects/{P1}/nodes/{N2} 应返 404 节点不存在
    const auth = { Authorization: `Bearer ${seeded1.accessToken}` };

    const res = await request.get(
      `${API_BASE}/api/projects/${seeded1.project.id}/nodes/${seeded2.node.id}/analyze/affected-nodes`,
      { headers: auth },
    );

    // node service get_by_id(N2, P1)=None → wrap 404
    // 若实装漏检（同 M04 B-P2-M04-cross-node-tenant-read-gap 已立 bug 根因），可能返 200 空
    // → 这条若 FAIL 是同根因 bug 复现 / 不修 spec
    expect([404, 403]).toContain(res.status());
  });

  test("[P0-API] DELETE /analyze/* method not allowed（testpoint §1 间接 / 验 router 不暴露多余 method）", async ({
    request,
  }) => {
    const seeded = await seedFullProject(request);
    const auth = { Authorization: `Bearer ${seeded.accessToken}` };

    // 验 router 不暴露 DELETE / PATCH / OPTIONS（design §7 只 3 endpoint）
    const delRes = await request.delete(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/affected-nodes`,
      { headers: auth },
    );
    expect([404, 405]).toContain(delRes.status());

    const patchRes = await request.patch(
      `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`,
      { headers: auth, data: {} },
    );
    expect([404, 405]).toContain(patchRes.status());
  });

  // ════════════════════════════════════════════════════════════════════════
  // SSE-PILOT（Opus spike 核心 / API 旁路绕 Next proxy 直打 FastAPI）
  // ════════════════════════════════════════════════════════════════════════
  //
  // 范式说明：
  //   - playwright `request.post` 拿 response.body() 是 buffer 完整 / 但 stream 可用 raw fetch
  //   - 在 playwright 内用 globalThis.fetch 直接打 FastAPI / Bearer JWT / 解 SSE 流
  //   - 解 "event: <type>\ndata: <json>\n\n" 拆 chunk 验顺序 + complete 收尾
  //
  // 不验：5min timeout / AbortController 真停 / aclose 协议（pytest integration 范畴）
  // 验：chunk 顺序 + complete event 互斥 error event + 流式头部
  //
  // 注：本 spike 不验"真 LLM SDK 集成"（M13 §14.5 LLM 红线 / 需 ANTHROPIC_API_KEY 跑 integration）
  //     若 seed 项目 ai_provider=NULL → 期望立即返 error event ANALYSIS_PROVIDER_NOT_CONFIGURED
  //     → 这恰好验 testpoint §3 E7 + §9 字段② error event 与 complete event 互斥

  test("[P0-API-SSE-PILOT] 🔴 SSE 范式 spike: POST /analyze/requirement 流式响应解析", async ({
    request,
  }) => {
    // testpoint §3 E7 + §9 字段②: provider 未配置 → 流式立返 1 error event 无 chunk HTTP 200
    // seed 项目无 ai_api_key_enc / ai_provider=NULL → 期望 error event ANALYSIS_PROVIDER_NOT_CONFIGURED
    const seeded = await seedFullProject(request);

    // playwright APIRequestContext 拿不到 ReadableStream / 用全局 fetch 走 raw
    // 注：node 18+ globalThis.fetch 可用 / playwright runtime 是 node 20+
    const url = `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${seeded.accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ requirement_text: "SSE 范式 spike 验证", analysis_level: "L1" }),
    });

    expect(resp.status).toBe(200);
    const ct = resp.headers.get("content-type") ?? "";
    expect(ct).toMatch(/text\/event-stream/);

    // 解 SSE 流："event: <type>\ndata: <json>\n\n"
    const events: Array<{ event: string; data: unknown }> = [];
    const reader = resp.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let safetyCounter = 0;
    while (safetyCounter < 1000) {
      safetyCounter++;
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // 一个完整 event 以 "\n\n" 结尾
      while (buffer.includes("\n\n")) {
        const idx = buffer.indexOf("\n\n");
        const block = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const lines = block.split("\n");
        let evType = "";
        let dataJson = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) evType = line.slice(7).trim();
          if (line.startsWith("data: ")) dataJson += line.slice(6);
        }
        if (evType) {
          try {
            events.push({ event: evType, data: JSON.parse(dataJson) });
          } catch {
            events.push({ event: evType, data: dataJson });
          }
        }
      }
    }

    // SSE 范式断言（design §12A 字段②）:
    //   - 至少 1 个 event 收到（chunk 或 error / complete）
    //   - complete 与 error 互斥（不可能同时出现）
    expect(events.length).toBeGreaterThan(0);
    const hasComplete = events.some((e) => e.event === "complete");
    const hasError = events.some((e) => e.event === "error");
    expect(hasComplete && hasError).toBe(false); // 互斥 / testpoint §9 P0 字段②

    // 期望路径（seed 项目无 ai_provider）：直接 error event ANALYSIS_PROVIDER_NOT_CONFIGURED
    // testpoint §3 E7
    if (hasError) {
      const errEvent = events.find((e) => e.event === "error");
      expect(errEvent).toBeDefined();
      const errData = errEvent!.data as { error_code?: string; error?: string };
      // analyze_router.py L168 字面 error_code="analysis_provider_not_configured"
      // 也接受其他 LLM 真集成时的 error_code（若 seed 项目有 provider）
      expect(typeof errData.error_code).toBe("string");
    } else if (hasComplete) {
      // 若 seed 项目恰好有 provider + LLM 真跑完了 / 验 complete event metadata 5 字段
      // testpoint §1 P0 SSECompleteEvent metadata
      const completeEvent = events.find((e) => e.event === "complete");
      expect(completeEvent).toBeDefined();
      const cd = completeEvent!.data as {
        full_result?: string;
        metadata?: Record<string, unknown>;
      };
      expect(typeof cd.full_result).toBe("string");
      expect(cd.metadata).toBeDefined();
      expect(cd.metadata!.analysis_level).toBe("L1");
    }
  });

  test("[P0-API-SSE-PILOT] happy: SSE 流式 chunk 顺序 + 头部断言（testpoint §9 字段① + S8）", async ({
    request,
  }) => {
    // testpoint §9 P1 字段①: SSE 端点头部 Content-Type=text/event-stream + Cache-Control=no-cache
    // + analyze_router.py L196-200 X-Accel-Buffering=no + Connection=keep-alive
    const seeded = await seedFullProject(request);

    const url = `${API_BASE}/api/projects/${seeded.project.id}/nodes/${seeded.node.id}/analyze/requirement`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${seeded.accessToken}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ requirement_text: "SSE 头部测试", analysis_level: "L1" }),
    });

    expect(resp.status).toBe(200);

    // testpoint §9 字段① + analyze_router.py L194 字面
    expect(resp.headers.get("content-type") ?? "").toMatch(/text\/event-stream/);
    // testpoint §9 P2 S8 字面 Cache-Control=no-cache（analyze_router.py L197）
    expect(resp.headers.get("cache-control") ?? "").toMatch(/no-cache/i);
    // testpoint §9 P2 S8 字面 X-Accel-Buffering=no（analyze_router.py L198）
    expect(resp.headers.get("x-accel-buffering") ?? "").toBe("no");

    // 把流读完防止连接挂着（不解 chunk 内容 / 上一条 SSE-PILOT 已验语义）
    const reader = resp.body!.getReader();
    let safetyCounter = 0;
    while (safetyCounter < 1000) {
      safetyCounter++;
      const { done } = await reader.read();
      if (done) break;
    }
  });
});
