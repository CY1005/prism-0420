/**
 * Auth service client.
 * Types mirror api/schemas/auth.py.
 */

const ANALYZER_BASE_URL = process.env.NEXT_PUBLIC_ANALYZER_URL || "http://localhost:8001";

export interface LoginResponse {
  user_id: string;
  email: string;
  name: string;
  token: string;
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
}

export type AuthResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function login(email: string, password: string): Promise<AuthResult<LoginResponse>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) {
      return { ok: false, error: resp.status === 401 ? "邮箱或密码错误" : `HTTP ${resp.status}` };
    }
    const data = (await resp.json()) as LoginResponse;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `认证服务不可用: ${(e as Error).message}` };
  }
}

export async function getCurrentUser(): Promise<AuthResult<UserProfile>> {
  try {
    const resp = await fetch(`${ANALYZER_BASE_URL}/api/auth/me`);
    if (!resp.ok) return { ok: false, error: `HTTP ${resp.status}` };
    const data = (await resp.json()) as UserProfile;
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: `服务不可用: ${(e as Error).message}` };
  }
}
