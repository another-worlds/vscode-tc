// Grand Contract v1.0 — M12 App Shell: auth-gated layout with nav
import React from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { logout } from "../../api/auth";
import { useAuthStore } from "../../store";

/**
 * AppShell wraps all authenticated pages.
 * Redirects to /login if no access_token in localStorage.
 * Renders top navbar with workspace/project breadcrumbs and user info.
 */
export const AppShell: React.FC = () => {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);

  // TODO: implement per contract — auth guard, user load, navbar render
  return (
    <div className="flex flex-col h-screen bg-gray-950 text-white">
      <nav className="h-14 bg-gray-900 flex items-center px-4 gap-4 border-b border-gray-800">
        <NavLink to="/workspaces" className="font-bold text-lg">TrafficCount</NavLink>
        <div className="flex-1" />
        {user && <span className="text-sm text-gray-400">{user.display_name}</span>}
        <button onClick={logout} className="text-sm text-gray-400 hover:text-white">Logout</button>
      </nav>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};
