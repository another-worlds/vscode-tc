// Grand Contract v1.0 — M12 App routing
import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AppShell } from "./components/layout/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { OAuthCallback } from "./pages/OAuthCallback";
import { WorkspacesPage } from "./pages/WorkspacesPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { CountingPage } from "./pages/CountingPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

export const App: React.FC = () => (
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<OAuthCallback />} />
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/workspaces" replace />} />
          <Route path="/workspaces" element={<WorkspacesPage />} />
          <Route path="/workspaces/:workspaceId/projects" element={<ProjectsPage />} />
          <Route path="/workspaces/:workspaceId/projects/:projectId/videos/:videoId/count" element={<CountingPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>
);
