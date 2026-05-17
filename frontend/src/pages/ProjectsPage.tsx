// Grand Contract v1.0 - M3/M9 Projects page
import React, { useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getProjectDashboard, listProjects } from "../api/workspaces";
import { uploadVideo } from "../api/videos";
import type { VideoSummary } from "../types";

const STATUS_BADGE: Record<string, string> = {
  PENDING: "bg-gray-600",
  QUEUED: "bg-yellow-600",
  PROCESSING: "bg-blue-600",
  PROCESSED: "bg-green-600",
  ERROR: "bg-red-600",
};

export const ProjectsPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedProjectId, setSelectedProjectId] = React.useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleUpload = async (file: File) => {
    if (!selectedProjectId) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("project_id", selectedProjectId);
    try {
      await uploadVideo(fd);
      queryClient.invalidateQueries({ queryKey: ["project-dashboard", workspaceId, selectedProjectId] });
    } catch (e) {
      console.error("Upload failed", e);
    }
  };

  return (
    <div className="flex h-full">
      <div className="w-64 bg-gray-900 p-4 border-r border-gray-800 flex flex-col gap-2">
        <h2 className="text-white font-semibold mb-2">Projects</h2>
        {projects?.map((p) => (
          <div
            key={p.id}
            className={"p-3 rounded cursor-pointer " + (selectedProjectId === p.id ? "bg-blue-700" : "hover:bg-gray-800") + " text-white"}
            onClick={() => setSelectedProjectId(p.id)}
          >
            {p.name}
            {p.location_label && <div className="text-xs text-gray-400">{p.location_label}</div>}
          </div>
        ))}
      </div>

      <div className="flex-1 p-6 overflow-auto">
        {selectedProjectId ? (
          <>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-white text-xl font-semibold">Videos</h2>
              <button
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
                onClick={() => fileInputRef.current?.click()}
              >Upload Video</button>
              <input
                ref={fileInputRef} type="file" accept=".mp4" className="hidden"
                onChange={(e) => { const file = e.target.files?.[0]; if (file) handleUpload(file); }}
              />
            </div>
            {dashboard?.videos.map((v: VideoSummary) => (
              <div key={v.id} className="bg-gray-900 rounded-lg p-4 mb-2 flex items-center gap-4 border border-gray-700">
                <div className="flex-1">
                  <div className="text-white font-medium">{v.filename}</div>
                  <div className="text-gray-400 text-sm">
                    {v.resolution ?? "unknown"}{v.duration_min != null ? " - " + v.duration_min.toFixed(1) + " min" : ""}{v.size_bytes != null ? " - " + (v.size_bytes / 1e6).toFixed(1) + " MB" : ""}
                  </div>
                </div>
                <span className={"text-xs text-white px-2 py-1 rounded " + (STATUS_BADGE[v.status] ?? "bg-gray-600")}>{v.status}</span>
                {v.has_counting_lines && <span className="text-xs text-green-400">Lines</span>}
                {v.status === "PROCESSED" && (
                  <button
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded text-sm"
                    onClick={() => navigate("/workspaces/" + workspaceId + "/projects/" + selectedProjectId + "/videos/" + v.id + "/count")}
                  >Count</button>
                )}
              </div>
            ))}
          </>
        ) : (
          <div className="text-gray-400 pt-12 text-center">Select a project</div>
        )}
      </div>
    </div>
  );
};
