/**
 * Phase 2.2 子片 3a — server-http-client unit tests（spec 06 §3）.
 *
 * 验：getServerAccessToken mock + Bearer header 拼接 / 401 抛 UnauthenticatedError / no-store cache.
 * 不验真 cookies()（next/headers Server 专用）/ 通过 vi.mock 替换 server-auth.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./server-auth", () => ({
  getServerAccessToken: vi.fn(),
}));

import { serverApiGet, serverApiPost, UnauthenticatedError, ApiError } from "./server-http-client";
import { getServerAccessToken } from "./server-auth";

const originalFetch = global.fetch;
const mockedToken = vi.mocked(getServerAccessToken);

function mockFetchOnce(status: number, body: unknown) {
  const noBody = [204, 205, 304];
  const blob = noBody.includes(status) ? null : JSON.stringify(body);
  const resp = new Response(blob, {
    status,
    headers: { "Content-Type": "application/json" },
  });
  (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(resp);
}

describe("server-http-client", () => {
  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
    mockedToken.mockReset();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("拼 baseUrl + Bearer header + cache:no-store", async () => {
    mockedToken.mockResolvedValueOnce("server-tok-123");
    mockFetchOnce(200, { ok: true });

    const data = await serverApiGet<{ ok: boolean }>("/projects");

    expect(data).toEqual({ ok: true });
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain("/projects");
    const init = call[1] as RequestInit;
    expect(init.cache).toBe("no-store");
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer server-tok-123");
  });

  it("无 refresh cookie / token null → 抛 UnauthenticatedError 不发请求", async () => {
    mockedToken.mockResolvedValueOnce(null);

    await expect(serverApiGet<unknown>("/projects")).rejects.toThrow(UnauthenticatedError);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("backend 401 → 抛 UnauthenticatedError（不自动 retry）", async () => {
    mockedToken.mockResolvedValueOnce("expired");
    mockFetchOnce(401, { detail: "expired" });

    await expect(serverApiGet<unknown>("/projects")).rejects.toThrow(UnauthenticatedError);
    expect((global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(1);
  });

  it("非 401 错误抛 ApiError 含 errorCode", async () => {
    mockedToken.mockResolvedValueOnce("tok");
    mockFetchOnce(403, { error_code: "permission_denied", message: "no access" });

    await expect(serverApiGet<unknown>("/projects")).rejects.toMatchObject({
      status: 403,
      errorCode: "permission_denied",
    });
  });

  it("POST body 序列化", async () => {
    mockedToken.mockResolvedValueOnce("tok");
    mockFetchOnce(200, { id: "p-1" });

    await serverApiPost("/projects", { name: "demo" });

    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const init = call[1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ name: "demo" }));
  });

  it("204 返 undefined", async () => {
    mockedToken.mockResolvedValueOnce("tok");
    mockFetchOnce(204, "");

    const data = await serverApiGet<void>("/some-delete");
    expect(data).toBeUndefined();
  });

  // ApiError 类型导出存在性
  it("ApiError + UnauthenticatedError 已导出", () => {
    expect(ApiError).toBeDefined();
    expect(UnauthenticatedError).toBeDefined();
  });
});
