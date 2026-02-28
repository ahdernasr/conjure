import { apiRequest } from "./client";
import type { ChatResponseData } from "../types/chat";

export async function sendChatMessage(
  message: string
): Promise<ChatResponseData> {
  return apiRequest<ChatResponseData>("/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
