export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatRequest {
  message: string;
}

export interface ChatResponseData {
  response: string;
}
