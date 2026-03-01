import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, ExternalLink, Download, AlertCircle, Loader2 } from "lucide-react";
import type { App } from "@/types/app";
import { iterateApp } from "@/api/generate";
import PhonePreview from "@/components/PhonePreview";
import ChatInput from "@/components/ChatInput";
import ThinkingTrace from "@/components/ThinkingTrace";
import { Button } from "@/components/ui/button";

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

  const versions = Array.from({ length: version }, (_, i) => i + 1);
  const color = app.theme_color || "#6366f1";

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {/* Header */}
      <header className="flex items-center gap-3 px-6 py-3 border-b border-border">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="shrink-0 rounded-full w-8 h-8"
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>

        {/* App identity */}
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
            style={{ backgroundColor: color }}
          >
            {app.name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-semibold truncate">{app.name}</h1>
            <p className="text-[11px] text-muted-foreground">
              v{activeVersion} {isIterating ? "— Updating..." : "— Ready"}
            </p>
          </div>
        </div>

        {/* Quick actions */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleOpen}
            className="rounded-full w-8 h-8"
          >
            <ExternalLink className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onInstall(app.name)}
            className="rounded-full w-8 h-8"
          >
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </header>

      {/* Pinned preview section */}
      <div className="px-6 py-5 border-b border-border">
        <PhonePreview appId={app.id} iframeKey={iframeKey} />

        {/* Version pills */}
        {versions.length > 1 && (
          <div className="flex items-center justify-center gap-1.5 mt-4">
            {versions.map((v) => (
              <button
                key={v}
                onClick={() => handleVersionTap(v)}
                className={`flex items-center justify-center transition-all duration-200 ${
                  v === activeVersion
                    ? "w-8 h-8 rounded-full bg-foreground text-background text-xs font-bold"
                    : "w-6 h-6 rounded-full bg-secondary text-muted-foreground text-[10px] hover:bg-secondary/80"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Scrollable conversation */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-3"
      >
        {messages.map((msg, i) => (
          <div
            key={msg.id}
            className={`flex animate-fade-in-up ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
            style={{ animationDelay: `${i * 0.03}s` }}
          >
            <div
              className={`rounded-2xl px-4 py-2.5 max-w-[80%] text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-foreground text-background"
                  : "bg-secondary text-foreground"
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
          <div className="flex items-center gap-2 text-sm text-destructive animate-fade-in-up">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <p>{error}</p>
          </div>
        )}
      </div>

      {/* Sticky bottom input */}
      <div className="sticky bottom-0 bg-background border-t border-border px-6 py-3">
        <ChatInput
          onSend={handleSend}
          loading={isIterating}
          placeholder="Describe a change..."
        />
      </div>
    </div>
  );
}
