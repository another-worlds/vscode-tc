// Grand Contract v1.0 — M13 Counting page: Section 3
import React from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getVideo } from "../api/videos";
import { CountingLineEditor } from "../components/counting/CountingLineEditor";

/**
 * Section 3: Counting lines interface.
 * Loads the video record and renders CountingLineEditor.
 * Shows error if video not yet PROCESSED.
 */
export const CountingPage: React.FC = () => {
  const { workspaceId, projectId, videoId } = useParams<{
    workspaceId: string; projectId: string; videoId: string;
  }>();

  const { data: video, isLoading, error } = useQuery({
    queryKey: ["video", projectId, videoId],
    queryFn: () => getVideo(projectId!, videoId!),
    enabled: !!projectId && !!videoId,
    refetchInterval: (data) =>
      data?.status !== "PROCESSED" && data?.status !== "ERROR" ? 5000 : false,
  });

  if (isLoading) return <div className="p-8 text-white">Loading video...</div>;
  if (!video) return <div className="p-8 text-red-400">Video not found.</div>;
  if (video.status !== "PROCESSED")
    return (
      <div className="p-8 text-yellow-400">
        Video status: <strong>{video.status}</strong> — counting available after processing completes.
      </div>
    );

  return (
    <div className="h-full">
      <CountingLineEditor video={video} projectId={projectId!} />
    </div>
  );
};
