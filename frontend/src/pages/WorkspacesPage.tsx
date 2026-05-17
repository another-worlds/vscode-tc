// Grand Contract v1.0 — M2/M9 Workspaces page with dashboard
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { listWorkspaces, getWorkspaceDashboard } from "../api/workspaces";
import type { Workspace, WorkspaceDashboard } from "../types";

const WorkspaceCard: React.FC<{ workspace: Workspace; onClick: () => void }> = ({ workspace, onClick }) => {
  const { data: dashboard } = useQuery<WorkspaceDashboard>({
    queryKey: ["workspace-dashboard", workspace.id],
    queryFn: () => getWorkspaceDashboard(workspace.id),
  });

  return (
    <div
      className="bg-gray-900 rounded-xl p-6 cursor-pointer hover:bg-gray-800 border border-gray-700"
      onClick={onClick}
    >
      <h2 className="text-lg font-semibold text-white mb-3">{workspace.name}</h2>
      {dashboard ? (
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-gray-400">Videos</div>
          <div className="text-white">{dashboard.processed_videos} / {dashboard.total_videos} processed</div>
          <div className="text-gray-400">Projects</div>
          <div className="text-white">{dashboard.active_projects} / {dashboard.total_projects}</div>
          <div className="text-gray-400">Storage</div>
          <div className="text-white">{dashboard.storage_used_gb.toFixed(2)} GB</div>
          <div className="text-gray-400">Queue depth</div>
          <div className="text-white">{dashboard.queue_depth}</div>
        </div>
      ) : (
        <div className="text-gray-500 text-sm">Loading stats...</div>
      )}
    </div>
  );
};

export const WorkspacesPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: workspaces, isLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: listWorkspaces,
  });

  if (isLoading) return <div className="p-8 text-white">Loading workspaces...</div>;

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-white mb-6">Workspaces</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workspaces?.map((ws) => (
          <WorkspaceCard
            key={ws.id}
            workspace={ws}
            onClick={() => navigate(`/workspaces/${ws.id}/projects`)}
          />
        ))}
      </div>
    </div>
  );
};
