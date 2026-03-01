import { useState } from "react";
import { sendChatMessage } from "@/api/chat";

export function useChat() {
  const [response, setResponse] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const sendMessage = async (message: string) => {
    setLoading(true);
    setResponse(null);
    try {
      const data = await sendChatMessage(message);
      setResponse(data.response);
    } catch (err) {
      setResponse(
        `Error: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(false);
    }
  };

  return { response, loading, sendMessage };
}
