import { useState, useRef, useEffect } from "react";
import type { App } from "../types/app";
import { iterateApp } from "../api/generate";
import PhonePreview from "./PhonePreview";
import ChatInput from "./ChatInput";

interface ChatEntry {
  id: number;
  role: "user" | "preview";
  content: string;
}

interface Props {
  app: App;
  onBack: () => void;
  onInstall: (appName: string) => void;
}

export default function ProjectChat({ app, onBack, onInstall }: Props) {
  const [messages, setMessages] = useState<ChatEntry[]>([
    { id: 0, role: "preview", content: "" },
  ]);
  const [isIterating, setIsIterating] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isIterating]);

  const handleSend = async (instruction: string) => {
    const userId = nextId.current++;
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", content: instruction },
    ]);

    setIsIterating(true);
    setError(null);
    try {
      await iterateApp(app.id, instruction);
      setIframeKey((prev) => prev + 1);
      const previewId = nextId.current++;
      setMessages((prev) => [
        ...prev,
        { id: previewId, role: "preview", content: "" },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Iteration failed");
    } finally {
      setIsIterating(false);
    }
  };

  const handleOpen = () => window.open(`/apps/${app.id}/`, "_blank");

  // Find the last preview message index so we only render one live iframe
  const lastPreviewId = (() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "preview") return messages[i].id;
    }
    return -1;
  })();

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {/* Header */}
      <header className="flex items-center gap-3 px-4 py-3 border-b border-conjure-border">
        <button
          onClick={onBack}
          className="text-conjure-muted text-sm min-w-[44px] min-h-[44px] flex items-center"
        >
          &larr; Back
        </button>
        <h1 className="text-lg font-semibold truncate">{app.name}</h1>
      </header>

      {/* Scrollable chat area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
      >
        {messages.map((msg) =>
          msg.role === "user" ? (
            <div key={msg.id} className="flex justify-end">
              <div
                className="bg-conjure-accent/20 border border-conjure-accent/30
                            rounded-xl px-4 py-2 max-w-[80%]"
              >
                <p className="text-sm">{msg.content}</p>
              </div>
            </div>
          ) : msg.id === lastPreviewId ? (
            <div key={msg.id} className="space-y-3">
              <PhonePreview appId={app.id} iframeKey={iframeKey} />
              <div className="flex gap-2 justify-center">
                <button
                  onClick={handleOpen}
                  className="px-4 py-2 rounded-lg bg-conjure-accent text-white text-sm font-medium
                             active:scale-95 transition-transform"
                >
                  Open App
                </button>
                <button
                  onClick={() => onInstall(app.name)}
                  className="px-4 py-2 rounded-lg bg-conjure-card border border-conjure-border
                             text-conjure-text text-sm font-medium
                             active:scale-95 transition-transform"
                >
                  Install
                </button>
              </div>
            </div>
          ) : (
            <div
              key={msg.id}
              className="text-center text-xs text-conjure-muted py-2"
            >
              Previous version
            </div>
          )
        )}

        {/* Loading spinner */}
        {isIterating && (
          <div className="flex justify-center py-4">
            <div
              className="inline-block w-5 h-5 border-2 border-conjure-accent
                          border-t-transparent rounded-full animate-spin"
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-3">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {/* Sticky bottom input */}
      <div className="sticky bottom-0 border-t border-conjure-border bg-conjure-bg px-4 py-3">
        <ChatInput
          onSend={handleSend}
          loading={isIterating}
          placeholder="Describe a change..."
          buttonText="Send"
        />
      </div>
    </div>
  );
}
