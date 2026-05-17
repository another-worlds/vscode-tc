// Grand Contract v1.0 — M2/M3 Workspace & Project API
import { apiClient } from "./client";
import type { Workspace, WorkspaceDashboard, Project, ProjectDashboard, MemberAdd, WorkspaceMember } from "../types";

// ── Workspaces ────────────────────────────────────────────────────

export async function listWorkspaces(): Promise<Workspace[]> {
  const { data } = await apiClient.get("/v1/workspaces/");
  return data;
}

export async function createWorkspace(name: string): Promise<Workspace> {
  const { data } = await apiClient.post("/v1/workspaces/", { name });
  return data;
}

export async function getWorkspaceDashboard(workspaceId: string): Promise<WorkspaceDashboard> {
  const { data } = await apiClient.get(`/v1/workspaces/${workspaceId}/dashboard`);
  return data;
}

export async function addWorkspaceMember(workspaceId: string, payload: { user_id: string; role: string }): Promise<WorkspaceMember> {
  const { data } = await apiClient.post(`/v1/workspaces/${workspaceId}/members`, payload);
  return data;
}

// ── Projects ──────────────────────────────────────────────────────

export async function listProjects(workspaceId: string): Promise<Project[]> {
  const { data } = await apiClient.get(`/v1/workspaces/${workspaceId}/projects/`);
  return data;
}

export async function createProject(workspaceId: string, name: string, location_label?: string): Promise<Project> {
  const { data } = await apiClient.post(`/v1/workspaces/${workspaceId}/projects/`, { name, location_label });
  return data;
}

export async function getProjectDashboard(workspaceId: string, projectId: string): Promise<ProjectDashboard> {
  const { data } = await apiClient.get(`/v1/workspaces/${workspaceId}/projects/${projectId}/dashboard`);
  return data;
}
