"use client";

/**
 * Phase 2.2 子片 2 — Auth React context (spec 06 §2 / ADR-004 P1+P3).
 *
 * access token: 内存（auth-token-store 模块层 + 此 context 镜像 user state 用于 re-render）
 * refresh token: httpOnly cookie 由浏览器自动携带（不在前端管理）
 *
 * 启动时调 /auth/refresh 续杯（cookie 存在则自动登录）/ 失败保持未登录态。
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  getAccessToken,
  setAccessToken as setStoreToken,
  clearAccessToken,
} from "@/services/auth-token-store";
import { apiGet, apiPost } from "@/services/http-client";
import type { components } from "@/types/api";

type UserProfile = components["schemas"]["UserProfile"];
type TokenResponse = components["schemas"]["TokenResponse"];
type RefreshResponse = components["schemas"]["RefreshResponse"];

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  logout: () => Promise<void>;
  refresh: () => Promise<UserProfile | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async (): Promise<UserProfile | null> => {
    try {
      const data = await apiPost<RefreshResponse>("/auth/refresh", {});
      setStoreToken(data.access_token);
      const me = await apiGet<UserProfile>("/auth/me");
      setUser(me);
      return me;
    } catch {
      // refresh 失败（401 / 网络）：清状态 / 不抛 / 让页面级 guard 决定跳登录
      clearAccessToken();
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    // 启动续杯：用 cookie 调 /auth/refresh / 失败保持未登录态。
    // setState 在 async 回调内是合理的（与外部系统 backend session 同步）/ React 19 lint 误报。
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    refresh().finally(() => {
      if (!cancelled) setIsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const login = useCallback(async (email: string, password: string): Promise<UserProfile> => {
    const data = await apiPost<TokenResponse>("/auth/login", { email, password });
    setStoreToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiPost("/auth/logout", {});
    } catch {
      // 后端调用失败也强制清前端态（本地 cookie/access 仍要清）
    }
    clearAccessToken();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}

// Re-export 给非 React 调用方（http-client 仍走 module-level store）
export { getAccessToken };
