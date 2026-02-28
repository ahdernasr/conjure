import { apiRequest } from "./client";

export interface GenerateResponse {
  id: string;
  name: string;
  description: string;
  theme_color: string;
}

export async function generateApp(
  prompt: string,
  goldenId?: string
): Promise<GenerateResponse> {
  return apiRequest<GenerateResponse>("/generate/", {
    method: "POST",
    body: JSON.stringify({ prompt, golden_id: goldenId || null }),
  });
}

export async function iterateApp(
  appId: string,
  instruction: string
): Promise<GenerateResponse> {
  return apiRequest<GenerateResponse>("/generate/iterate", {
    method: "POST",
    body: JSON.stringify({ app_id: appId, instruction }),
  });
}
