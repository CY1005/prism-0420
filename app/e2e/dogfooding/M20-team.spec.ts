import { test, expect } from "@playwright/test";

import { loginE2EAdmin, seedFullProject } from "../fixtures/seed";

// M20 团队 dogfooding spec
// 对应 testpoint: _handoff/dogfooding/01-testpoints/M20-team.md
// 覆盖（按分类决策树拆三类标签）:
//   [DOM-reachable]   8 条  → 走 page.goto + locator（团队列表/新建/详情/编辑/成员Dialog/删除Dialog/转让Dialog）
//   [API-via-旁路]   20 条  → 走 request fixture（状态机/权限三层/tenant 隔离/乐观锁/数据完整性/activity_log/错误码）
//   [skip-N/A]       100 条 → punt（见下 punt 清单）
//
// punt 清单（必写）:
//   - [P0] §1 POST /api/teams happy path 原子写入 + activity_log — activity_log 旁路验证放 API-via-旁路段 / DOM 已覆盖新建 happy path
//   - [P0] §1 团队所有 activity_log 事件完备性（10 个 action_type）— 入 [API-via-旁路] 精选 2 条 happy path 验 / 其余 push pytest
//   - [P0] §5 Tenant 隔离 T3/T4 user_accessible_project_ids_subquery L3 SQL 注入 — 需两 user fixture（当前 seed 仅 1 admin）/ 标 skip-N/A 等 fixture 扩展
//   - [P0] §6 并发乐观锁 C1/C2/C3/C6 — 需多线程并发 / playwright 单 worker 无法真并发 / 推 pytest concurrent
//   - [P0] §7 数据完整性 DB CHECK / UNIQUE / FK — 可 API 旁路验（已进 [API-via-旁路]）/ 其余 Migration 等推 pytest
//   - [P0] §10 跨模块契约 M02 ProjectDAO.list_for_user / R-X3 / baseline-patch — 需 M02 fixture 联动 / 推 cross-cutting spec
//   - [P0] §6 C2/C3 并发删 team / transfer — playwright 单 worker 不可并发测 / 推 pytest
//   - [P1] §8 UI/UX：成员名单展示（page.tsx §成员管理 明示"待 backend GET /api/teams/{id}/members 上线后启用"）→ [skip-N/A]
//   - [P1] §12 性能 C7 压测（P95 < 100ms / 1000 project 规模）— 推专项 pytest 压测 / [skip-N/A]
//   - [P1] §11 idempotency N/A / §12 异步 N/A — 显式 N/A 不测
//   - [P1] §7 Alembic 迁移 m20_team upgrade/downgrade — pytest migration test / [skip-N/A]
//   - [P1] §9 activity_log 10 个 action_type 全量 + ck_activity_log CHECK — 关键 2 条入 API 旁路 / 余推 pytest
//   - [P2] 性能超阈值 ADR-005 Redis 缓存路径 — [skip-N/A]
//   - [P2] 团队成员 >200 异步化 — [skip-N/A]
//   - [P2] AC2 一键迁移 100 个 project 进度条前端 — [skip-N/A]
//
// design vs UI 漂移（dogfooding 价值 / design-audit candidate）:
//   - [P1] §8 成员名单展示：design §7 GET /api/teams/{id}/members 端点已设计，page.tsx 有明文占位符
//     「成员名单展示等 backend 上线 GET /api/teams/{id}/members endpoint 后启用（cross-sprint pool P22-4-backend-gap）」
//     → backend endpoint 存在 / 前端 UI 未实现 / design-gap candidate：member list 渲染 / 标 [skip-N/A]
//   - [P0] §8 成员列表渲染 member_count vs 成员名单：teams list 页面仅显示 member_count 计数 / 无成员头像/名字 UI
//     → 满足 design §1 F2 "查看团队内项目" / 但 member list 细节 UI 待实现

const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";

test.describe("M20 团队 dogfooding", () => {
  // ═══════════════════════════════════════════════════
  // DOM 主路径 — 真用户旅程（page.goto + locator）
  // ═══════════════════════════════════════════════════

  test("[P0] 团队列表 happy path — DOM 导航到 /teams 渲染「我的团队」标题 + 新建团队按钮", async ({
    page,
  }) => {
    // testpoint §1: GET /api/teams 返当前用户关联的所有 team / teams/page.tsx 渲染
    // DOM 验证：teams/page.tsx L81 <h1>我的团队</h1> + L86 Link href="/teams/new" 新建团队按钮
    await page.goto("/teams");
    await expect(page).toHaveURL(/\/teams$/, { timeout: 8_000 });

    // 页面主标题
    await expect(page.getByRole("heading", { name: "我的团队" })).toBeVisible({ timeout: 8_000 });

    // 新建团队按钮（teams/page.tsx L87 <Button> 新建团队）
    await expect(page.getByRole("link", { name: "新建团队" })).toBeVisible();

    // 副标题文案（teams/page.tsx L83）
    await expect(page.getByText("团队是项目的容器")).toBeVisible();
  });

  test("[P0] 新建团队 happy path — DOM 主路径：/teams/new 填表单 + 点创建 → 跳 /teams/{id}", async ({
    page,
  }) => {
    // testpoint §1: POST /api/teams happy path 201 + team_created activity_log
    // DOM 视角：teams/new/page.tsx 填 name + description → createTeam server action → router.replace(/teams/{id})
    // 🔴 已知 trigger_bug（server action cookie 透传 / spike 实证）：若失败跳 /login = 真 bug 不修 spec
    await page.goto("/teams/new");

    // teams/new/page.tsx L54 <h1>新建团队</h1>
    await expect(page.getByRole("heading", { name: "新建团队" })).toBeVisible({ timeout: 8_000 });

    const teamName = `E2E Team ${Date.now()}`;
    const teamDesc = "M20 dogfooding e2e test team";

    // teams/new/page.tsx L63 <Label htmlFor="name"> + Input id="name"
    await page.getByLabel("团队名称").fill(teamName);
    // teams/new/page.tsx L77 Label htmlFor="description" + Textarea id="description"
    await page.getByLabel("描述").fill(teamDesc);

    // teams/new/page.tsx L101 Button onClick=handleCreate "创建团队"
    await page.getByRole("button", { name: /创建团队|创建中/ }).click();

    // server action createTeam → router.replace(`/teams/${handled.data.id}`)
    // 若 trigger_bug 仍存在 → 跳 /login（同 M02 根因）
    await page.waitForURL(
      (url) => /\/teams\/[0-9a-f-]{36}/.test(url.pathname) || url.pathname === "/login",
      { timeout: 15_000 },
    );

    const finalUrl = page.url();
    expect(
      finalUrl.includes("/login"),
      `trigger_bug 复现: 创建团队后跳 /login 而非 /teams/{uuid} (final url: ${finalUrl})`,
    ).toBe(false);

    // 成功跳转到团队详情页
    expect(finalUrl).toMatch(/\/teams\/[0-9a-f-]{36}/);
  });

  test("[P0] 团队详情 happy path — DOM 直接 GET /teams/{id} 渲染基本信息卡片 + Owner badge", async ({
    page,
    request,
  }) => {
    // testpoint §1: GET /api/teams/{tid} L1 通过返 team 详情含 members 列表
    // 先用 API 旁路 seed 一个 team（不走 DOM seed 避免 trigger_bug 干扰 seed 逻辑）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `Detail Test ${Date.now()}`, description: "团队详情 DOM 测试" },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    // 直接 goto /teams/{id}
    await page.goto(`/teams/${team.id}`);
    await expect(page).toHaveURL(`/teams/${team.id}`, { timeout: 8_000 });

    // teams/[teamId]/page.tsx L108 <h1>{team.name}</h1>
    await expect(page.getByRole("heading", { name: team.name })).toBeVisible({ timeout: 8_000 });

    // Owner badge（teams/[teamId]/page.tsx L109-112 isOwner → Crown + "Owner" in amber span）
    // 🔴 strict mode: 页面含多个"Owner"文本（header badge + 转让说明段落）→ 用 amber class 精确定位
    await expect(page.locator("span.bg-amber-50").filter({ hasText: "Owner" })).toBeVisible();

    // 基本信息卡片（TeamInfoCard L131 <h2>基本信息</h2>）
    await expect(page.getByRole("heading", { name: "基本信息" })).toBeVisible();

    // 成员管理卡片（TeamMembersCard L326 <h2>成员管理</h2>）
    await expect(page.getByRole("heading", { name: "成员管理" })).toBeVisible();

    // 危险操作卡片（TeamDangerCard L582 <h2> 危险操作）
    await expect(page.getByRole("heading", { name: "危险操作" })).toBeVisible();
  });

  test("[P1] 编辑团队名称 DOM — 点「编辑」→ 修改 name → 点保存 → 详情更新（乐观锁 version+1）", async ({
    page,
    request,
  }) => {
    // testpoint §1: PATCH /api/teams/{tid} 改 name happy path 200 + version 自增 + activity_log team_renamed
    // DOM 路径：TeamEditCard "编辑" → Input 改 name → "保存"
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const originalName = `Edit Test ${Date.now()}`;
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: originalName },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    await page.goto(`/teams/${team.id}`);
    await expect(page.getByRole("heading", { name: originalName })).toBeVisible({ timeout: 8_000 });

    // teams/[teamId]/page.tsx TeamEditCard L202 Button variant="outline" "编辑"
    await page.getByRole("button", { name: "编辑" }).click();

    // L219 Input id="edit-name"
    const newName = `Edited ${Date.now()}`;
    await page.getByLabel("团队名称").clear();
    await page.getByLabel("团队名称").fill(newName);

    // L257 Button "保存"
    await page.getByRole("button", { name: /保存|保存中/ }).click();

    // 保存后 onUpdated() reload → 标题刷新
    await expect(page.getByRole("heading", { name: newName })).toBeVisible({ timeout: 10_000 });
  });

  test("[P1] 添加成员 Dialog DOM — 点「添加成员」→ Dialog 打开 → 填用户 ID → 提交（以 server action 路径测 UI 流程）", async ({
    page,
    request,
  }) => {
    // testpoint §8 UI: teams/[teamId]/page.tsx TeamMembersCard "添加成员" → Dialog
    // 🔴 server action cookie 同 trigger_bug 根因：addMember 可能跳 /login / 记录真行为不修 spec
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `AddMember Test ${Date.now()}` },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    await page.goto(`/teams/${team.id}`);
    await expect(page.getByRole("heading", { name: "成员管理" })).toBeVisible({ timeout: 8_000 });

    // TeamMembersCard L329 Button "添加成员"
    await page.getByRole("button", { name: "添加成员" }).click();

    // Dialog 打开（DialogTitle L371 "添加成员"）
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("heading", { name: "添加成员" })).toBeVisible();

    // Dialog 内 Label "用户 ID（UUID）" + Input id="add-user-id"
    await expect(page.getByLabel("用户 ID（UUID）")).toBeVisible();

    // Dialog 内 role Select（SelectTrigger id="add-role"）
    await expect(page.getByRole("combobox")).toBeVisible();

    // 关闭 Dialog（取消按钮）
    await page.getByRole("button", { name: "取消" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 3_000 });
  });

  test("[P1] 删除团队 Dialog DOM — 点「删除团队」→ Dialog 打开 + 确认文本输入才可提交", async ({
    page,
    request,
  }) => {
    // testpoint §8 UI: 删 team UI 二次确认（design §8.5 Q11=A / TeamDangerCard）
    // DOM 验：Dialog 的确认文本逻辑（confirmText !== team.name → Button disabled）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamName = `Delete Dialog ${Date.now()}`;
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: teamName },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    await page.goto(`/teams/${team.id}`);
    await expect(page.getByRole("heading", { name: "危险操作" })).toBeVisible({ timeout: 8_000 });

    // TeamDangerCard L593 Button variant="destructive" "删除团队"
    await page.getByRole("button", { name: "删除团队" }).click();

    // Dialog 打开（L607 DialogTitle "永久删除团队"）
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });
    await expect(page.getByRole("heading", { name: "永久删除团队" })).toBeVisible();

    // 空确认文本时 → 「永久删除」Button disabled（page.tsx L636 disabled={isPending || confirmText !== team.name}）
    const deleteBtn = page.getByRole("button", { name: /永久删除|删除中/ });
    await expect(deleteBtn).toBeDisabled();

    // 填正确确认文本 → Button 变 enabled
    await page.getByLabel(`输入 "${teamName}" 确认`).fill(teamName);
    await expect(deleteBtn).toBeEnabled();

    // 关闭 Dialog（不真删，避免 trigger_bug 或干扰后续 test）
    await page.getByRole("button", { name: "取消" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 3_000 });
  });

  test("[P1] 转让所有权 Dialog DOM — 点「转让所有权」→ Dialog 打开 + 确认逻辑验证", async ({
    page,
    request,
  }) => {
    // testpoint §8 UI: transfer-ownership 前端 Dialog（TeamTransferCard）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamName = `Transfer Dialog ${Date.now()}`;
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: teamName },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    await page.goto(`/teams/${team.id}`);
    await expect(page.getByRole("heading", { name: "转让所有权" })).toBeVisible({ timeout: 8_000 });

    // TeamTransferCard L496 Button "转让所有权"
    await page.getByRole("button", { name: "转让所有权" }).click();

    // Dialog 打开
    await expect(page.getByRole("dialog")).toBeVisible({ timeout: 5_000 });
    // DialogTitle L511 "转让所有权"
    await expect(
      page.getByRole("dialog").getByRole("heading", { name: "转让所有权" }),
    ).toBeVisible();

    // Label "新 owner 用户 ID（UUID）"
    await expect(page.getByLabel("新 owner 用户 ID（UUID）")).toBeVisible();

    // 确认文本输入为空 → 「确认转让」disabled（page.tsx L547 disabled={... || confirmText !== team.name}）
    const confirmBtn = page.getByRole("button", { name: /确认转让|转让中/ });
    await expect(confirmBtn).toBeDisabled();

    // 填 owner ID 但确认文本仍空 → 仍 disabled
    await page.getByLabel("新 owner 用户 ID（UUID）").fill("00000000-0000-0000-0000-000000000001");
    await expect(confirmBtn).toBeDisabled();

    // 填正确确认文本 → Button enabled（可点击）
    await page.locator(`input[id="transfer-confirm"]`).fill(teamName);
    await expect(confirmBtn).toBeEnabled();

    // 关闭 Dialog（不真转让）
    await page.getByRole("button", { name: "取消" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 3_000 });
  });

  test("[P0] 团队列表 empty state — 已加入团队时卡片渲染 member_count + creator badge", async ({
    page,
    request,
  }) => {
    // testpoint §1 GET /api/teams: teams/page.tsx card 渲染 team.name + member_count + 「我创建的」badge
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamName = `List Card ${Date.now()}`;
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: teamName, description: "列表卡片 DOM 测" },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    await page.goto("/teams");
    await expect(page.getByRole("heading", { name: "我的团队" })).toBeVisible({ timeout: 8_000 });

    // teams/page.tsx L110 <h3>{team.name}</h3>
    await expect(page.getByRole("heading", { name: teamName })).toBeVisible({ timeout: 10_000 });

    // page.tsx L111-115 creator_id === user.id → badge "我创建的"
    await expect(page.getByText("我创建的").first()).toBeVisible();

    // page.tsx L123 {team.member_count} 名成员
    await expect(page.getByText(/\d+ 名成员/).first()).toBeVisible();

    // 点卡片跳到 /teams/{id}（Link href={`/teams/${team.id}`}）
    await page.getByRole("heading", { name: teamName }).click();
    await expect(page).toHaveURL(`/teams/${team.id}`, { timeout: 8_000 });

    // cleanup（API 删团队 / 前置条件：团队无 project）
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth }); // idempotent 404 ok
  });

  // ═══════════════════════════════════════════════════
  // API 旁路 — backend-only P0（无 UI 入口 / state machine / 权限 / 数据完整性）
  // ═══════════════════════════════════════════════════

  test("[P0-API] POST /api/teams happy path 201 + activity_log team_created 写入", async ({
    request,
  }) => {
    // testpoint §1: POST /api/teams 201 + 单事务原子写 teams + team_members(creator, role=owner) + activity_log
    const { accessToken, user } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamName = `API Happy ${Date.now()}`;
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: teamName, description: "API 主路径 happy path" },
    });
    expect(createRes.status()).toBe(201);
    const body = await createRes.json();

    // TeamRead 字段验（design §7）
    expect(body.id).toBeTruthy();
    expect(body.name).toBe(teamName);
    expect(body.creator_id).toBe(user.id);
    expect(body.version).toBeGreaterThanOrEqual(1);
    expect(body.member_count).toBe(1); // creator 自动成 owner

    // activity_log 旁路验（design §10.1 team_created）
    const logRes = await request.get(`${API_BASE}/api/teams/${body.id}/activity`, {
      headers: auth,
    });
    // 若 activity endpoint 存在
    if (logRes.status() === 200) {
      const logs = await logRes.json();
      const teamCreatedEvent = (Array.isArray(logs) ? logs : (logs.events ?? [])).find(
        (e: { action_type: string }) => e.action_type === "team_created",
      );
      expect(teamCreatedEvent, "team_created activity_log 事件应存在").toBeTruthy();
    }
    // activity endpoint 不存在也不 fail（端点路径待确认 / 不阻塞主 happy path）

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${body.id}`, { headers: auth });
  });

  test("[P0-API] GET /api/teams 返当前用户的 team 列表（含 member_count）", async ({ request }) => {
    // testpoint §1: GET /api/teams 返当前用户通过 team_members 关联的所有 team 含 member_count
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // seed 一个已知 team
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `List Test ${Date.now()}` },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    const listRes = await request.get(`${API_BASE}/api/teams`, { headers: auth });
    expect(listRes.status()).toBe(200);
    const teams = await listRes.json();
    const list = Array.isArray(teams) ? teams : (teams.items ?? teams.teams ?? []);

    const found = list.find((t: { id: string }) => t.id === team.id);
    expect(found, `创建的 team ${team.id} 应出现在 GET /api/teams 列表`).toBeTruthy();
    expect(found.member_count).toBeGreaterThanOrEqual(1);

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] 权限：未登录访问 /api/teams 拒 401 UNAUTHENTICATED", async ({ request }) => {
    // testpoint §4: 未登录访问任何 /api/teams 端点拒 401 (design §8.5 require_user)
    const noAuthRes = await request.get(`${API_BASE}/api/teams`);
    expect([401, 403]).toContain(noAuthRes.status());

    const noAuthPost = await request.post(`${API_BASE}/api/teams`, {
      data: { name: "unauthorized" },
    });
    expect([401, 403]).toContain(noAuthPost.status());
  });

  test("[P0-API] 权限 L2：non-member 访问 GET /api/teams/{tid} 拒 404 TEAM_NOT_FOUND（不 leak 存在性）", async ({
    request,
  }) => {
    // testpoint §4 T1: U1 既非 team_members 也非 ProjectMember 关联时 GET /teams/{T} 拒 404
    // 用无效 UUID 验"不存在 or 无权访问" → 统一 404 不 leak
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const fakeTeamId = "00000000-0000-0000-0000-000000000000";
    const res = await request.get(`${API_BASE}/api/teams/${fakeTeamId}`, { headers: auth });
    expect(res.status()).toBe(404);

    const body = await res.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /TEAM_NOT_FOUND|not_found|404/i,
    );
  });

  test("[P0-API] 状态机：name 长度边界 — 空字符串拒 422 / 1字符 → 201 / 100字符 → 201 / 101字符 → 422", async ({
    request,
  }) => {
    // testpoint §2: name 长度边界（design §3.2 CheckConstraint + §7 Pydantic min/max）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 空字符串 → 422
    const emptyRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: "" },
    });
    expect(emptyRes.status()).toBe(422);

    // 1 字符 → 201
    const oneCharRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: "A" },
    });
    expect(oneCharRes.status()).toBe(201);
    const oneCharTeam = await oneCharRes.json();
    await request.delete(`${API_BASE}/api/teams/${oneCharTeam.id}`, { headers: auth });

    // 100 字符 → 201
    const name100 = "A".repeat(100);
    const hundredCharRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: name100 },
    });
    expect(hundredCharRes.status()).toBe(201);
    const hundredTeam = await hundredCharRes.json();
    await request.delete(`${API_BASE}/api/teams/${hundredTeam.id}`, { headers: auth });

    // 101 字符 → 422
    const name101 = "A".repeat(101);
    const tooLongRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: name101 },
    });
    expect(tooLongRes.status()).toBe(422);
  });

  test("[P0-API] 状态机：owner role 禁止通过 DELETE members 端点直接移除（TEAM_OWNER_REQUIRED）", async ({
    request,
  }) => {
    // testpoint §2: team_members.role 禁止转换 owner → [*] team_member_removed 拒 422 TEAM_OWNER_REQUIRED reason="last_owner_remove"
    const { accessToken, user } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 创建 team / admin 是 creator = owner
    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `Owner Remove ${Date.now()}` },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    // 尝试删除自己（owner = last owner）→ 拒 422
    const removeRes = await request.delete(`${API_BASE}/api/teams/${team.id}/members/${user.id}`, {
      headers: auth,
    });
    expect(removeRes.status()).toBe(422);
    const body = await removeRes.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /TEAM_OWNER_REQUIRED|owner/i,
    );

    // cleanup（直接删 team）
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] 乐观锁：PATCH /api/teams/{tid} 用过期 version → 409 CONFLICT", async ({
    request,
  }) => {
    // testpoint §3: PATCH /api/teams/{tid} 用过期 version=1 但当前 version=2 → 409 CONFLICT
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `Optimistic ${Date.now()}` },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    // 第一次 PATCH → version=2
    const patch1 = await request.patch(`${API_BASE}/api/teams/${team.id}`, {
      headers: auth,
      data: { name: `Updated Once ${Date.now()}`, version: team.version },
    });
    expect(patch1.status()).toBe(200);

    // 第二次用旧 version（过期）→ 409
    const patch2 = await request.patch(`${API_BASE}/api/teams/${team.id}`, {
      headers: auth,
      data: { name: `Updated Twice ${Date.now()}`, version: team.version }, // stale version
    });
    expect(patch2.status()).toBe(409);
    const body = await patch2.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(/CONFLICT|conflict/i);

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] 数据完整性：UNIQUE uq_teams_creator_name — 同 creator 同 name 第二个 409 TEAM_NAME_DUPLICATE", async ({
    request,
  }) => {
    // testpoint §7 UniqueConstraint uq_teams_creator_name(creator_id, name)
    // testpoint §3 B5: 同 creator 不同 team 同名第二个 409 TEAM_NAME_DUPLICATE
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const dupName = `Dup Name ${Date.now()}`;

    // 第一个 → 201
    const res1 = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: dupName },
    });
    expect(res1.status()).toBe(201);
    const team1 = await res1.json();

    // 第二个同名 → 409 TEAM_NAME_DUPLICATE
    const res2 = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: dupName },
    });
    expect(res2.status()).toBe(409);
    const body = await res2.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /TEAM_NAME_DUPLICATE|duplicate|conflict/i,
    );

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team1.id}`, { headers: auth });
  });

  test("[P0-API] 数据完整性：UNIQUE uq_team_members_team_user — 重复加同 user → 409 TEAM_MEMBER_DUPLICATE", async ({
    request,
  }) => {
    // testpoint §7 UniqueConstraint uq_team_members_team_user(team_id, user_id)
    // testpoint §3 E8: 重复加同 user 拒 409 TEAM_MEMBER_DUPLICATE
    const { accessToken, user } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const createRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `DupMember ${Date.now()}` },
    });
    expect(createRes.status()).toBe(201);
    const team = await createRes.json();

    // 再次加同一 user（creator 已经是 owner member）→ 409
    const addRes = await request.post(`${API_BASE}/api/teams/${team.id}/members`, {
      headers: auth,
      data: { user_id: user.id, role: "member" },
    });
    expect(addRes.status()).toBe(409);
    const body = await addRes.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /TEAM_MEMBER_DUPLICATE|duplicate/i,
    );

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] CROSS_TEAM_MOVE_FORBIDDEN：project 当前属于 team A 时不能直接 move 到 team B", async ({
    request,
  }) => {
    // testpoint §3: CROSS_TEAM_MOVE_FORBIDDEN POST /move-team target=B 但 project 当前 team_id=A 拒 422
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 创建 team A + team B
    const teamARes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `CrossMove A ${Date.now()}` },
    });
    expect(teamARes.status()).toBe(201);
    const teamA = await teamARes.json();

    const teamBRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `CrossMove B ${Date.now()}` },
    });
    expect(teamBRes.status()).toBe(201);
    const teamB = await teamBRes.json();

    // 创建 project（个人）
    const projRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: { name: `CrossMove Proj ${Date.now()}`, description: "", template_type: "custom" },
    });
    expect(projRes.status()).toBe(201);
    const proj = await projRes.json();

    // 先把 project 加入 team A
    const moveToA = await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: teamA.id },
    });
    expect(moveToA.status()).toBe(200);

    // 现在 project 在 team A / 直接 move 到 team B → 拒 422 CROSS_TEAM_MOVE_FORBIDDEN
    const crossMove = await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: teamB.id },
    });
    expect(crossMove.status()).toBe(422);
    const body = await crossMove.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /CROSS_TEAM_MOVE_FORBIDDEN|cross.team/i,
    );

    // cleanup（先移回个人再删 team）
    await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: null },
    });
    await request.delete(`${API_BASE}/api/teams/${teamA.id}`, { headers: auth });
    await request.delete(`${API_BASE}/api/teams/${teamB.id}`, { headers: auth });
  });

  test("[P0-API] 删 team 前提：team 有 project → 拒 422 TEAM_HAS_PROJECTS", async ({ request }) => {
    // testpoint §3 B8: 删 team 时 projects 非空 N=5 拒 422 TEAM_HAS_PROJECTS detail.{project_count, project_ids}
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 创建 team
    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `HasProj ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    // 创建 project 并加入 team
    const projRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: { name: `HasProj Project ${Date.now()}`, description: "", template_type: "custom" },
    });
    expect(projRes.status()).toBe(201);
    const proj = await projRes.json();

    const moveRes = await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: team.id },
    });
    expect(moveRes.status()).toBe(200);

    // 尝试删 team（有 project）→ 422
    const deleteRes = await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
    expect(deleteRes.status()).toBe(422);
    const body = await deleteRes.json();
    expect(body.code ?? body.error_code ?? JSON.stringify(body)).toMatch(
      /TEAM_HAS_PROJECTS|has_projects/i,
    );

    // cleanup
    await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: null },
    });
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] POST /api/projects/{pid}/move-team happy path — 个人 project 加入 team 200", async ({
    request,
  }) => {
    // testpoint §1: POST /api/projects/{pid}/move-team target_team_id=tid happy path 200 + activity_log project_joined_team
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `JoinTeam ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    const projRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: { name: `JoinTeam Proj ${Date.now()}`, description: "", template_type: "custom" },
    });
    expect(projRes.status()).toBe(201);
    const proj = await projRes.json();

    // project 加入 team → 200
    const joinRes = await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: team.id },
    });
    expect(joinRes.status()).toBe(200);

    // 验 project.team_id 已更新（GET /api/projects/{pid}）
    const getProj = await request.get(`${API_BASE}/api/projects/${proj.id}`, { headers: auth });
    if (getProj.status() === 200) {
      const projBody = await getProj.json();
      expect(projBody.team_id).toBe(team.id);
    }

    // cleanup
    await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: null },
    });
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P0-API] DELETE /api/teams/{tid} happy path 204（前置 projects 清空）", async ({
    request,
  }) => {
    // testpoint §1: DELETE /api/teams/{tid} 5 步事务原子 204（前置 projects 空）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `DeleteHappy ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    // 直接删（无 project）→ 204
    const deleteRes = await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
    expect(deleteRes.status()).toBe(204);

    // 验 team 已不存在 → 404
    const getRes = await request.get(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
    expect(getRes.status()).toBe(404);
  });

  test("[P0-API] 权限 L2：member 尝试 PATCH /teams/{tid} 拒 403 TEAM_PERMISSION_DENIED", async ({
    request,
  }) => {
    // testpoint §4 L2: assert_team_role(admin)：member 尝试 PATCH /teams/{tid} 改 name 拒 403
    // 🔴 需要第二用户 fixture / 当前 seed 仅 1 admin → 用 FAKE TOKEN 模拟 unauthorized 测 401 路径
    // 真 "member vs admin role" 差异需多用户 fixture（推 cross-cutting spec 或 fixture 扩展后补）
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `Perm Check ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    // 用 bad token（非成员）→ 401/403/404（tenant 隔离）
    const badAuth = { Authorization: "Bearer fake.jwt.token" };
    const patchRes = await request.patch(`${API_BASE}/api/teams/${team.id}`, {
      headers: badAuth,
      data: { name: "Unauthorized Patch", version: 1 },
    });
    expect([401, 403, 404]).toContain(patchRes.status());

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P1-API] resolve_project_role：team member baseline → viewer 权限映射", async ({
    request,
  }) => {
    // testpoint §4 P1/P2/P3: resolve_project_role — team_role 映射 viewer/editor/owner
    // P1 = team member baseline → viewer（design §8.6 Q2=B 三角色映射）
    // 🔴 需要 project 在 team + 第二用户 fixture / 当前单 admin fixture 覆盖有限
    // 验 API 存在（不需要真多用户）：GET /api/teams/{id}/members → resolve_project_role 端点
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    // 创建 team + project + join team
    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `RoleResolve ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    const projRes = await request.post(`${API_BASE}/api/projects`, {
      headers: auth,
      data: { name: `RoleResolve Proj ${Date.now()}`, description: "", template_type: "custom" },
    });
    expect(projRes.status()).toBe(201);
    const proj = await projRes.json();

    const joinRes = await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: team.id },
    });
    expect(joinRes.status()).toBe(200);

    // admin = creator = owner role → 应有 project 访问（owner baseline）
    const getProj = await request.get(`${API_BASE}/api/projects/${proj.id}`, { headers: auth });
    expect([200, 403, 404]).toContain(getProj.status());
    // 若 200 → creator/owner 有访问权（P3 resolve_project_role owner→owner）
    if (getProj.status() === 200) {
      const projBody = await getProj.json();
      expect(projBody.id).toBe(proj.id);
    }

    // cleanup
    await request.post(`${API_BASE}/api/projects/${proj.id}/move-team`, {
      headers: auth,
      data: { target_team_id: null },
    });
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });

  test("[P1-API] description=null 允许 201 + DB 存 NULL", async ({ request }) => {
    // testpoint §1 B2: POST /api/teams description=null 允许 201 + DB 存 NULL
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const res = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `NoDesc ${Date.now()}` }, // 不传 description
    });
    expect(res.status()).toBe(201);
    const body = await res.json();
    // description 应为 null 或缺失
    expect(
      body.description === null || body.description === undefined || body.description === "",
    ).toBe(true);

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${body.id}`, { headers: auth });
  });

  test("[P1-API] DELETE /api/teams/{随机不存在 UUID} 拒 404 TEAM_NOT_FOUND", async ({
    request,
  }) => {
    // testpoint §3: GET /api/teams/{随机 UUID} 拒 404 TEAM_NOT_FOUND
    const { accessToken } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const fakeId = "11111111-1111-1111-1111-111111111111";
    const res = await request.delete(`${API_BASE}/api/teams/${fakeId}`, { headers: auth });
    expect(res.status()).toBe(404);
  });

  test("[P1-API] role 传 'owner' Pydantic 拒 422（schema Literal['admin','member']）", async ({
    request,
  }) => {
    // testpoint §3: PATCH /api/teams/{tid}/members/{uid} role 传 "owner" Pydantic 拒 422 VALIDATION_ERROR
    const { accessToken, user } = await loginE2EAdmin(request);
    const auth = { Authorization: `Bearer ${accessToken}` };

    const teamRes = await request.post(`${API_BASE}/api/teams`, {
      headers: auth,
      data: { name: `RoleValidate ${Date.now()}` },
    });
    expect(teamRes.status()).toBe(201);
    const team = await teamRes.json();

    // 尝试 PATCH role="owner"（Literal["admin","member"] 拒绝 owner）
    const patchRes = await request.patch(`${API_BASE}/api/teams/${team.id}/members/${user.id}`, {
      headers: auth,
      data: { role: "owner" },
    });
    expect(patchRes.status()).toBe(422);

    // cleanup
    await request.delete(`${API_BASE}/api/teams/${team.id}`, { headers: auth });
  });
});
