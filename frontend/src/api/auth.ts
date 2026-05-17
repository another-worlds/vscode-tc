// Grand Contract v1.0 — M1 Auth API calls
import { apiClient } from "./client";
import type { User } from "../types";

/**
 * Redirect browser to backend OAuth2 login URL.
 */
export function redirectToLogin(provider?: string): void {
  const p = provider ?? import.meta.env.VITE_OAUTH_PROVIDER ?? "github";
  window.location.href = `/api/v1/auth/login?provider=${encodeURIComponent(p)}`;
}

/**
 * Exchange OAuth2 code for JWT, store token in localStorage.
 */
export async function handleOAuthCallback(
  code: string,
  state: string,
  provider?: string
): Promise<void> {
  const p = provider ?? import.meta.env.VITE_OAUTH_PROVIDER ?? "github";
  const res = await apiClient.post<{ access_token: string }>("/v1/auth/callback", {
    code,
    state,
    provider: p,
  });
  localStorage.setItem("access_token", res.data.access_token);
}

/**
 * Fetch current authenticated user profile.
 * Returns null if not authenticated.
 */
export async function getCurrentUser(): Promise<User | null> {
  try {
    const res = await apiClient.get<User>("/v1/auth/me");
    return res.data;
  } catch {
    return null;
  }
}

export function logout(): void {
  localStorage.removeItem("access_token");
  window.location.href = "/login";
}
