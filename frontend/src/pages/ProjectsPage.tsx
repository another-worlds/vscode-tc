// Grand Contract v1.0 — M3/M9 Projects page with video dashboard
import React from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getProjectDashboard, listProjects } from "../api/workspaces";
import { uploadVideo, queueVideo } from "../api/videos";
import type { VideoSummary } from "../types";

/**
 * Section 2: Project control.
 *
 * Shows:
 *   - List of projects in workspace
 *   - Selected project: video inventory table
 *     Columns: filename, resolution, size, duration, status, counting lines, export
 *   - Upload button (drag-drop or file picker)
 *   - Re-queue button for ERROR videos
 *   - Link to counting editor per video (status=PROCESSED only)
 */
export const ProjectsPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(null);

  const { data: projects } = useQuery({
    queryKey: ["projects", workspaceId],
    queryFn: () => listProjects(workspaceId!),
    enabled: !!workspaceId,
  });

  const { data: dashboard } = useQuery({
    queryKey: ["project-dashboard", workspaceId, selectedProjectId],
    queryFn: () => getProjectDashboard(workspaceId!, selectedProjectId!),
    enabled: !!selectedProjectId,
  });

  const handleUpload = async (projectId: string, file: File) => {
    // TODO: implement per contract — show progress bar
  };

  // TODO: implement per contract — full render
  return (
    <div className="flex h-full">
      {/* Project list sidebar */}
      <div className="w-64 bg-gray-900 p-4 border-r border-gray-800">
        <h2 className="text-white font-semibold mb-4">Projects</h2>
        {projects?.map((p) => (
          <div
            key={p.id}
            className={`p-3 rounded cursor-pointer mb-1 ${selectedProjectId === p.id ? "bg-blue-700" : "hover:bg-gray-800"} text-white`}
            onClick={() => setSelectedProjectId(p.id)}
          >
            {p.name}
          </div>
        ))}
      </div>

      {/* Video table */}
      <div className="flex-1 p-6 overflow-auto">
        {/* TODO: implement video inventory table per contract */}
        {dashboard?.videos.map((v) => (
          <div key={v.id} className="bg-gray-900 rounded p-4 mb-2 flex items-center gap-4">
            <span className="text-white flex-1">{v.filename}</span>
            <span className="text-gray-400 text-sm">{v.status}</span>
            {v.status === "PROCESSED" && (
              <button
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
                onClick={() => navigate(`/workspaces/${workspaceId}/projects/${selectedProjectId}/videos/${v.id}/count`)}
              >
                Open Counting
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
