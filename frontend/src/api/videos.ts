// Grand Contract v1.0 — M4/M8 Video & Counting Line API
import { apiClient } from "./client";
import type {
  Video, CountingLine, CountingLineCreate,
  CountingResult, TrajectoryData, HeatmapData, SegmentPoint
} from "../types";

// ── Videos ────────────────────────────────────────────────────────

export async function listVideos(projectId: string): Promise<Video[]> {
  const { data } = await apiClient.get(`/v1/projects/${projectId}/videos/`);
  return data;
}

export async function uploadVideo(projectId: string, file: File, onProgress?: (pct: number) => void): Promise<Video> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post(`/v1/projects/${projectId}/videos/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => onProgress?.(Math.round((e.loaded / (e.total ?? 1)) * 100)),
  });
  return data;
}

export async function getVideo(projectId: string, videoId: string): Promise<Video> {
  const { data } = await apiClient.get(`/v1/projects/${projectId}/videos/${videoId}`);
  return data;
}

export function getFrameUrl(projectId: string, videoId: string, frameNumber: number): string {
  return `/api/v1/projects/${projectId}/videos/${videoId}/frames/${frameNumber}`;
}

export async function getTrajectories(projectId: string, videoId: string): Promise<TrajectoryData> {
  const { data } = await apiClient.get(`/v1/projects/${projectId}/videos/${videoId}/trajectories`);
  return data;
}

export async function queueVideo(projectId: string, videoId: string): Promise<void> {
  await apiClient.post(`/v1/projects/${projectId}/videos/${videoId}/queue`);
}

// ── Counting Lines ────────────────────────────────────────────────

export async function listCountingLines(videoId: string): Promise<CountingLine[]> {
  const { data } = await apiClient.get(`/v1/videos/${videoId}/lines/`);
  return data;
}

export async function createCountingLine(videoId: string, payload: CountingLineCreate): Promise<CountingLine> {
  const { data } = await apiClient.post(`/v1/videos/${videoId}/lines/`, payload);
  return data;
}

export async function deleteCountingLine(videoId: string, lineId: string): Promise<void> {
  await apiClient.delete(`/v1/videos/${videoId}/lines/${lineId}`);
}

export async function getCountingResult(videoId: string, lineId: string): Promise<CountingResult> {
  const { data } = await apiClient.get(`/v1/videos/${videoId}/lines/${lineId}/result`);
  return data;
}

export async function getHeatmapData(videoId: string): Promise<HeatmapData> {
  const { data } = await apiClient.get(`/v1/videos/${videoId}/lines/heatmap`);
  return data;
}

export async function getSuggestData(videoId: string): Promise<SegmentPoint[]> {
  const { data } = await apiClient.get(`/v1/videos/${videoId}/lines/suggest`);
  return data;
}

export function getExportUrl(videoId: string): string {
  return `/api/v1/videos/${videoId}/export/xlsx`;
}
