// Grand Contract v1.0 — M1 OAuth2 callback page
import React, { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { handleOAuthCallback } from "../api/auth";

/**
 * Receives OAuth2 redirect with ?code=...&state=...
 * Exchanges code for JWT, stores in localStorage, redirects to /workspaces.
 */
export const OAuthCallback: React.FC = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const code = params.get("code") ?? "";
    const state = params.get("state") ?? "";
    const provider = params.get("provider") ?? undefined;
    handleOAuthCallback(code, state, provider)
      .then(() => navigate("/workspaces", { replace: true }))
      .catch(() => navigate("/login?error=oauth_failed", { replace: true }));
  }, []);

  return (
    <div className="flex items-center justify-center h-screen bg-gray-950 text-white">
      Authenticating...
    </div>
  );
};
