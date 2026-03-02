export interface GenerateResponse {
  id: string;
  name: string;
  description: string;
  theme_color: string;
  version?: number;
  summary?: string;
}

export interface ChatOnlyResponse {
  type: "chat_response";
  message: string;
}

export type IterateResult = GenerateResponse | ChatOnlyResponse;

export function isChatResponse(result: IterateResult): result is ChatOnlyResponse {
  return "type" in result && result.type === "chat_response";
}

async function readSSEStream(
  url: string,
  body: object,
  onTrace?: (message: string) => void,
): Promise<IterateResult> {
  const resp = await fetch(`/api${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  const reader = resp.body?.getReader();
  if (!reader) throw new Error("No response stream");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete SSE lines
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const jsonStr = line.slice(6);
      if (!jsonStr.trim()) continue;

      try {
        const event = JSON.parse(jsonStr);

        if (event.type === "status" || event.type === "tool") {
          onTrace?.(event.message);
        } else if (event.type === "chat_response") {
          return { type: "chat_response", message: event.message } as ChatOnlyResponse;
        } else if (event.type === "complete") {
          return event.data as GenerateResponse;
        } else if (event.type === "error") {
          throw new Error(event.message);
        }
      } catch (e) {
        if (e instanceof Error && e.message !== jsonStr) throw e;
      }
    }
  }

  throw new Error("Stream ended without completion");
}

export async function generateApp(
  prompt: string,
  onTrace?: (message: string) => void,
): Promise<GenerateResponse> {
  // Generation endpoint never returns chat_response, safe to cast
  return readSSEStream(
    "/generate/",
    { prompt },
    onTrace,
  ) as Promise<GenerateResponse>;
}

export async function iterateApp(
  appId: string,
  instruction: string,
  onTrace?: (message: string) => void,
): Promise<IterateResult> {
  return readSSEStream(
    "/generate/iterate",
    { app_id: appId, instruction },
    onTrace,
  );
}
