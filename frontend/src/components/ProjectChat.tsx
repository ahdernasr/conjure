import { useState, useRef, useEffect, useCallback } from "react";
import type { App } from "../types/app";
import { iterateApp } from "../api/generate";
import PhonePreview from "./PhonePreview";
import ChatInput from "./ChatInput";
import ThinkingTrace from "./ThinkingTrace";

interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
}

interface Props {
  app: App;
  onBack: () => void;
  onInstall: (appName: string) => void;
}

export default function ProjectChat({ app, onBack, onInstall }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isIterating, setIsIterating] = useState(false);
  const [traceMessages, setTraceMessages] = useState<string[]>([]);
  const [iframeKey, setIframeKey] = useState(0);
  const [version, setVersion] = useState(1);
  const [activeVersion, setActiveVersion] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isIterating, traceMessages]);

  const onTrace = useCallback((message: string) => {
    setTraceMessages((prev) => [...prev, message]);
  }, []);

  const handleSend = async (instruction: string) => {
    const userId = nextId.current++;
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", content: instruction },
    ]);

    setIsIterating(true);
    setTraceMessages([]);
    setError(null);
    try {
      await iterateApp(app.id, instruction, onTrace);
      const newVersion = version + 1;
      setVersion(newVersion);
      setActiveVersion(newVersion);
      setIframeKey((prev) => prev + 1);

      const confirmId = nextId.current++;
      setMessages((prev) => [
        ...prev,
        { id: confirmId, role: "assistant", content: `Updated! (v${newVersion})` },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Iteration failed");
    } finally {
      setIsIterating(false);
      setTraceMessages([]);
    }
  };

  const handleOpen = () => window.open(`/apps/${app.id}/`, "_blank");

  const handleVersionTap = (v: number) => {
    setActiveVersion(v);
    setIframeKey((prev) => prev + 1);
  };

  // Build version pills array
  const versions = Array.from({ length: version }, (_, i) => i + 1);

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

      {/* Pinned preview section */}
      <div className="border-b border-conjure-border px-4 py-4 space-y-3">
        <PhonePreview appId={app.id} iframeKey={iframeKey} />

        {/* Version pills */}
        <div className="flex items-center justify-center gap-2 flex-wrap">
          {versions.map((v) => (
            <button
              key={v}
              onClick={() => handleVersionTap(v)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                v === activeVersion
                  ? "bg-conjure-accent text-white"
                  : "bg-conjure-card border border-conjure-border text-conjure-muted"
              }`}
            >
              v{v}
            </button>
          ))}
        </div>

        {/* Action buttons */}
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

      {/* Scrollable conversation */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-xl px-4 py-2 max-w-[80%] text-sm ${
                msg.role === "user"
                  ? "bg-conjure-accent/20 border border-conjure-accent/30 text-conjure-text"
                  : "bg-conjure-card border border-conjure-border text-conjure-muted"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {/* Thinking trace */}
        {isIterating && (
          <ThinkingTrace messages={traceMessages} loading={isIterating} />
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
