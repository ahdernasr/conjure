import { apiRequest } from "./client";

export interface CommandResponse {
  response: string;
  conversation_id: string;
  handoff_create: boolean;
  create_prompt?: string;
}

export async function sendCommand(
  message: string,
  conversationId?: string
): Promise<CommandResponse> {
  return apiRequest<CommandResponse>("/command/", {
    method: "POST",
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
    }),
  });
}
