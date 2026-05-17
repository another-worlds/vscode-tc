// Grand Contract v1.0 — M12/M13 TypeScript domain types
// Single source of truth for all API response shapes

export type UserRole = "ADMIN" | "MANAGER" | "ANALYST" | "VIEWER";

export type VideoStatus = "PENDING" | "QUEUED" | "PROCESSING" | "PROCESSED" | "ERROR";

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
}

export interface WorkspaceMember {
  user_id: string;
  role: UserRole;
  assigned_at: string;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  location_label: string | null;
  created_at: string;
  created_by: string;
}

export interface Video {
  id: string;
  project_id: string;
  filename: string;
  resolution_w: number | null;
  resolution_h: number | null;
  duration_s: number | null;
  size_bytes: number | null;
  fps: number | null;
  status: VideoStatus;
  error_message: string | null;
  uploaded_at: string;
  uploaded_by: string | null;
  processing_started_at: string | null;
  processed_at: string | null;
  frame_count: number | null;
}

export interface LinePoint {
  x: number;
  y: number;
}

export interface CountingLine {
  id: string;
  video_id: string;
  name: string;
  points: LinePoint[];
  color: string;
  created_at: string;
  created_by: string | null;
}

export interface CountingResult {
  counting_line_id: string;
  count_in: number;
  count_out: number;
  total: number;
  vehicle_pct: Record<string, number> | null;
  computed_at: string;
}

export interface WorkspaceDashboard {
  workspace_id: string;
  total_videos: number;
  processed_videos: number;
  pending_videos: number;
  total_duration_min: number;
  processed_duration_min: number;
  storage_used_gb: number;
  total_projects: number;
  active_projects: number;
  queue_depth: number;
}

export interface VideoSummary {
  id: string;
  filename: string;
  resolution: string | null;
  size_bytes: number | null;
  duration_min: number | null;
  status: VideoStatus;
  has_counting_lines: boolean;
  has_results: boolean;
}

export interface ProjectDashboard {
  project_id: string;
  videos: VideoSummary[];
}

// M13 Counting Line UI types

export interface TrajectoryFrame {
  f: number;    // frame number
  x: number;   // centroid x (pixel)
  y: number;   // centroid y (pixel)
}

export interface Track {
  track_id: number;
  class_id: number;
  frames: TrajectoryFrame[];
}

export interface TrajectoryData {
  tracks: Track[];
  video_width: number;
  video_height: number;
}

export interface HeatmapData {
  width: number;
  height: number;
  grid: number[][];  // normalized 0–1 density
}

/** Segment data point for client-side cluster suggestion */
export interface SegmentPoint {
  x_mid: number;
  y_mid: number;
  angle_deg: number;
}

/** A suggested counting line from client-side DBSCAN cluster */
export interface SuggestedLine {
  points: LinePoint[];
  cluster_id: number;
  segment_count: number;  // number of trajectory segments in cluster
}
