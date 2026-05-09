/**
 * Phase 2.2 子片 1 — http-client unit tests.
 *
 * 验：baseUrl + headers 拼接 / 401 refresh+retry 路径 / refresh 失败抛 UnauthenticatedError.
 * 不验真实 endpoint（子片 2 加 e2e）/ mock global.fetch.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet, UnauthenticatedError } from "./http-client";
import { setAccessToken, clearAccessToken } from "./auth-token-store";

const originalFetch = global.fetch;

function mockFetchOnce(status: number, body: unknown, init?: ResponseInit) {
  // 204/205/304 不允许 body / Response constructor 抛错
  const noBodyStatuses = [204, 205, 304];
  const blob = noBodyStatuses.includes(status)
    ? null
    : typeof body === "string"
      ? body
      : JSON.stringify(body);
  const resp = new Response(blob, {
    status,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  (global.fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(resp);
}

describe("http-client", () => {
  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
    clearAccessToken();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("拼 baseUrl + 携带 Bearer header + credentials:include", async () => {
    setAccessToken("tok-123");
    mockFetchOnce(200, { ok: true });

    const data = await apiGet<{ ok: boolean }>("/projects");

    expect(data).toEqual({ ok: true });
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toContain("/projects");
    const init = call[1] as RequestInit;
    expect(init.credentials).toBe("include");
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok-123");
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("无 access token 时不带 Authorization header", async () => {
    mockFetchOnce(200, { ok: true });

    await apiGet<unknown>("/health");

    const init = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0][1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("401 → refresh 200 → retry 原请求 → 200 通过", async () => {
    setAccessToken("expired");
    mockFetchOnce(401, { detail: "expired" }); // 1: 原请求 401
    mockFetchOnce(200, { access_token: "new-tok" }); // 2: refresh 成功
    mockFetchOnce(200, { ok: true }); // 3: retry 成功

    const data = await apiGet<{ ok: boolean }>("/projects");

    expect(data).toEqual({ ok: true });
    expect((global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls).toHaveLength(3);
    // retry 用新 token
    const retryInit = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[2][1] as RequestInit;
    expect((retryInit.headers as Record<string, string>).Authorization).toBe("Bearer new-tok");
  });

  it("401 → refresh 401 → 抛 UnauthenticatedError", async () => {
    setAccessToken("expired");
    mockFetchOnce(401, { detail: "expired" });
    mockFetchOnce(401, { detail: "refresh expired" });

    await expect(apiGet<unknown>("/projects")).rejects.toThrow(UnauthenticatedError);
  });

  it("非 401 错误抛 ApiError 含 errorCode + message", async () => {
    mockFetchOnce(403, { error_code: "permission_denied", message: "no access" });

    await expect(apiGet<unknown>("/projects")).rejects.toMatchObject({
      status: 403,
      errorCode: "permission_denied",
      message: "no access",
    });
  });

  it("204 返 undefined", async () => {
    mockFetchOnce(204, "");

    const data = await apiGet<void>("/some-delete");

    expect(data).toBeUndefined();
  });
});
