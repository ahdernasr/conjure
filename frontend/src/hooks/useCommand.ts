import { useState, useCallback, useRef } from "react";
import { sendCommand } from "../api/command";
import { textToSpeech } from "../api/voice";

export interface CommandMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface Handoff {
  prompt: string;
}

export function useCommand() {
  const [messages, setMessages] = useState<CommandMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [handoff, setHandoff] = useState<Handoff | null>(null);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speakResponse = useCallback(async (text: string) => {
    try {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      const blob = await textToSpeech(text);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => URL.revokeObjectURL(url);
      await audio.play();
    } catch {
      console.warn("TTS playback failed");
    }
  }, []);

  const send = useCallback(async (message: string) => {
    const userMsg: CommandMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: message,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendCommand(message, conversationIdRef.current);
      conversationIdRef.current = data.conversation_id;

      const assistantMsg: CommandMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.response,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      speakResponse(data.response);

      if (data.handoff_create && data.create_prompt) {
        setHandoff({ prompt: data.create_prompt });
      }
    } catch (err) {
      const errorMsg: CommandMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, something went wrong. Please try again.",
      };
      setMessages((prev) => [...prev, errorMsg]);
      console.error("Command error:", err);
    } finally {
      setLoading(false);
    }
  }, [speakResponse]);

  const clearHandoff = useCallback(() => setHandoff(null), []);

  return { messages, loading, send, handoff, clearHandoff };
}
