/**
 * In-memory access token store (Phase 2.2 子片 1 占位).
 *
 * 子片 2 将替换为 React context (src/contexts/auth-context.tsx) 提供同接口。
 * 不入 localStorage / 不入 cookie——access token 仅在内存（spec 06 §2 B 路径 / XSS 抵御）。
 * Refresh token 走 httpOnly cookie 由浏览器自动携带（不在本模块管理）。
 */

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}
