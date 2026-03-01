import { apiRequest } from "./client";
import type { AppListResponse, App } from "@/types/app";

export async function listApps(): Promise<AppListResponse> {
  return apiRequest<AppListResponse>("/apps/");
}

export async function getApp(id: string): Promise<App> {
  return apiRequest<App>(`/apps/${id}`);
}

export async function deleteApp(id: string): Promise<void> {
  await apiRequest(`/apps/${id}`, { method: "DELETE" });
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  version: number | null;
}

export async function getMessages(appId: string): Promise<ChatMessage[]> {
  const res = await apiRequest<{ messages: ChatMessage[] }>(`/apps/${appId}/messages`);
  return res.messages;
}

export async function addMessage(
  appId: string,
  role: string,
  content: string,
  version?: number,
): Promise<ChatMessage> {
  return apiRequest<ChatMessage>(`/apps/${appId}/messages`, {
    method: "POST",
    body: JSON.stringify({ role, content, version: version ?? null }),
  });
}
