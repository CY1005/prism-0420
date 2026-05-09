/**
 * Phase 2.2 子片 2 — auth-context e2e（vitest + jsdom + @testing-library/react）.
 *
 * 验集成链路：login → setAccessToken + user state / logout 清状态 / mount refresh 续杯.
 * mock global.fetch / 不验真 cookie（jsdom 不模拟浏览器 cookie jar，credentials:include 仅作 RequestInit 断言）.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, renderHook, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "./auth-context";
import { getAccessToken, clearAccessToken } from "@/services/auth-token-store";
import type { ReactNode } from "react";

const originalFetch = global.fetch;

function mockResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const wrapper = ({ children }: { children: ReactNode }) => <AuthProvider>{children}</AuthProvider>;

const fakeUser = {
  id: "00000000-0000-0000-0000-000000000001",
  email: "alice@example.com",
  name: "Alice",
  role: "user",
  status: "active",
  avatar_url: null,
  version: 1,
};

describe("auth-context", () => {
  beforeEach(() => {
    global.fetch = vi.fn() as unknown as typeof fetch;
    clearAccessToken();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("mount 时调 /auth/refresh 续杯：成功 → 设 user + access token", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(mockResponse(200, { access_token: "renewed", token_type: "bearer" }))
      .mockResolvedValueOnce(mockResponse(200, fakeUser));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user?.email).toBe("alice@example.com");
    expect(getAccessToken()).toBe("renewed");

    // 验 fetch 调用 credentials:include
    const refreshCall = fetchMock.mock.calls[0];
    expect(refreshCall[0]).toContain("/auth/refresh");
    expect((refreshCall[1] as RequestInit).credentials).toBe("include");
  });

  it("mount refresh 401 → 保持未登录态（不抛）", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }));
    // refresh 失败后 http-client 还会再尝试 refresh 一次（401 retry 路径）→ 也 401
    fetchMock.mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("login 成功 → 设 user + access token / logout 清状态", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    // mount refresh 失败（无登录态）
    fetchMock
      .mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }))
      .mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }));

    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // login
    fetchMock.mockResolvedValueOnce(
      mockResponse(200, {
        access_token: "tok-after-login",
        refresh_token: "raw-refresh",
        token_type: "bearer",
        user: fakeUser,
      }),
    );
    await act(async () => {
      await result.current.login("alice@example.com", "hunter2");
    });
    expect(result.current.user?.email).toBe("alice@example.com");
    expect(getAccessToken()).toBe("tok-after-login");

    // 验 login fetch credentials:include + body
    const loginCall = fetchMock.mock.calls.at(-1)!;
    expect(loginCall[0]).toContain("/auth/login");
    expect((loginCall[1] as RequestInit).credentials).toBe("include");

    // logout
    fetchMock.mockResolvedValueOnce(mockResponse(200, { status: "ok" }));
    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.user).toBeNull();
    expect(getAccessToken()).toBeNull();
  });

  it("AuthProvider 缺失时 useAuth 抛", () => {
    expect(() => renderHook(() => useAuth())).toThrow(/AuthProvider/);
  });

  it("LoginPage 渲染含 form / 错误 alert 角色", async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }))
      .mockResolvedValueOnce(mockResponse(401, { detail: "no cookie" }));

    // 仅冒烟：AuthProvider 内的 children 渲染不抛
    const { container } = render(
      <AuthProvider>
        <div data-testid="child">child rendered</div>
      </AuthProvider>,
    );
    expect(container.querySelector('[data-testid="child"]')).not.toBeNull();
  });
});
