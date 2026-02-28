import { apiRequest } from "./client";
import type { AppListResponse, App } from "../types/app";

export async function listApps(): Promise<AppListResponse> {
  return apiRequest<AppListResponse>("/apps");
}

export async function getApp(id: string): Promise<App> {
  return apiRequest<App>(`/apps/${id}`);
}

export async function deleteApp(id: string): Promise<void> {
  await apiRequest(`/apps/${id}`, { method: "DELETE" });
}
