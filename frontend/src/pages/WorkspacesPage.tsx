// Grand Contract v1.0 — M2/M9 Workspaces page with dashboard
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { listWorkspaces, getWorkspaceDashboard } from "../api/workspaces";
import type { WorkspaceDashboard } from "../types";

/**
 * Section 1: Workspace control.
 *
 * Shows:
 *   - List of workspaces user is member of
 *   - Per-workspace dashboard card:
 *     total/processed videos, storage GB, queue depth, project counts
 *   - Button to create new workspace (ADMIN only)
 *   - Link to projects per workspace
 */
export const WorkspacesPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: workspaces, isLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: listWorkspaces,
  });

  // TODO: implement per contract — render dashboard cards
  if (isLoading) return <div className="p-8 text-white">Loading workspaces...</div>;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Workspaces</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces?.map((ws) => (
          <div
            key={ws.id}
            className="bg-gray-900 rounded-xl p-6 cursor-pointer hover:bg-gray-800"
            onClick={() => navigate(`/workspaces/${ws.id}/projects`)}
          >
            <h2 className="text-lg font-semibold text-white">{ws.name}</h2>
            {/* TODO: embed WorkspaceDashboard stats */}
          </div>
        ))}
      </div>
    </div>
  );
};
