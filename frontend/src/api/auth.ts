// Grand Contract v1.0 — M1 Auth API calls
import { apiClient } from "./client";
import type { User } from "../types";

/**
 * Redirect browser to backend OAuth2 login URL.
 * provider defaults to VITE_OAUTH_PROVIDER env.
 */
export function redirectToLogin(provider?: string): void {
  // TODO: implement per contract
}

/**
 * Exchange OAuth2 code for JWT, store token in localStorage.
 * Called from OAuthCallback page.
 *
 * @param code     authorization code from query string
 * @param state    state param for CSRF validation
 * @param provider oauth provider name
 */
export async function handleOAuthCallback(
  code: string,
  state: string,
  provider?: string
): Promise<void> {
  // TODO: implement per contract
}

/**
 * Fetch current authenticated user profile.
 * Returns null if not authenticated.
 */
export async function getCurrentUser(): Promise<User | null> {
  // TODO: implement per contract
  return null;
}

export function logout(): void {
  localStorage.removeItem("access_token");
  window.location.href = "/login";
}
