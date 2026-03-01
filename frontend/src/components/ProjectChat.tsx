import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, ExternalLink, Download, AlertCircle, Loader2, ChevronLeft, ChevronRight } from "lucide-react";
import type { App } from "@/types/app";
import { iterateApp } from "@/api/generate";
import { getMessages, addMessage, type ChatMessage } from "@/api/apps";
import PhonePreview from "@/components/PhonePreview";
import ChatInput from "@/components/ChatInput";
import ThinkingTrace from "@/components/ThinkingTrace";
import { Button } from "@/components/ui/button";

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

  // Load persisted messages on mount
  useEffect(() => {
    let cancelled = false;
    getMessages(app.id).then((msgs) => {
      if (cancelled) return;
      setMessages(msgs);
      // Derive version from the highest version in saved messages
      const maxVersion = msgs.reduce((max, m) => Math.max(max, m.version ?? 0), 0);
      if (maxVersion > 0) {
        setVersion(maxVersion);
        setActiveVersion(maxVersion);
      }
    }).catch(() => {});
    return () => { cancelled = true; };
  }, [app.id]);

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
    // Optimistically add user message to UI
    const userMsg: ChatMessage = { id: Date.now(), role: "user", content: instruction, version: null };
    setMessages((prev) => [...prev, userMsg]);

    setIsIterating(true);
    setTraceMessages([]);
    setError(null);
    try {
      await iterateApp(app.id, instruction, onTrace);
      const newVersion = version + 1;
      setVersion(newVersion);
      setActiveVersion(newVersion);
      setIframeKey((prev) => prev + 1);

      const assistantContent = `Done — version ${newVersion}`;
      const assistantMsg: ChatMessage = { id: Date.now() + 1, role: "assistant", content: assistantContent, version: newVersion };
      setMessages((prev) => [...prev, assistantMsg]);

      // Persist both messages to backend
      addMessage(app.id, "user", instruction, newVersion).catch(() => {});
      addMessage(app.id, "assistant", assistantContent, newVersion).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Iteration failed");
    } finally {
      setIsIterating(false);
      setTraceMessages([]);
    }
  };

  const handleOpen = () => window.open(`/apps/${app.id}/`, "_blank");

  const handleVersionTap = (v: number) => {
    if (v < 1 || v > version) return;
    setActiveVersion(v);
    setIframeKey((prev) => prev + 1);
  };

  const color = app.theme_color || "#6366f1";

  // Version switcher — shared between mobile and desktop
  const versionSwitcher = version > 1 && (
    <div className="flex items-center justify-center gap-3 mt-4">
      <button
        onClick={() => handleVersionTap(activeVersion - 1)}
        disabled={activeVersion <= 1}
        className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-30 disabled:pointer-events-none"
      >
        <ChevronLeft className="w-4 h-4" />
      </button>
      <span className="text-sm text-muted-foreground tabular-nums">
        Version {activeVersion} of {version}
      </span>
      <button
        onClick={() => handleVersionTap(activeVersion + 1)}
        disabled={activeVersion >= version}
        className="w-7 h-7 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors disabled:opacity-30 disabled:pointer-events-none"
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );

  return (
    <div className="flex flex-col h-[100dvh] overflow-hidden">
      {/* Header — full width */}
      <header className="flex items-center gap-3 px-6 py-3 border-b border-border shrink-0">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="shrink-0 rounded-full w-8 h-8"
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>

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

      {/* Body — split on desktop, stacked on mobile */}
      <div className="flex-1 flex flex-col md:flex-row min-h-0">
        {/* Left panel: phone preview (desktop — sticky) */}
        <div className="hidden md:block md:w-[45%] md:shrink-0 border-r border-border">
          <div className="sticky top-0 h-[calc(100dvh-49px)] flex flex-col justify-center px-10">
            <PhonePreview appId={app.id} iframeKey={iframeKey} />
            {versionSwitcher}
          </div>
        </div>

        {/* Mobile phone preview */}
        <div className="md:hidden px-6 py-5 border-b border-border">
          <PhonePreview appId={app.id} iframeKey={iframeKey} />
          {versionSwitcher}
        </div>

        {/* Right panel: chat */}
        <div className="flex-1 flex flex-col min-h-0">
          {/* Scrollable conversation */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-6 py-4 space-y-3"
          >
            {messages.length === 0 && !isIterating && !error && (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-muted-foreground">Describe a change to get started</p>
              </div>
            )}

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

            {isIterating && (
              <ThinkingTrace messages={traceMessages} loading={isIterating} />
            )}

            {error && (
              <div className="flex items-center gap-2 text-sm text-destructive animate-fade-in-up">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{error}</p>
              </div>
            )}
          </div>

          {/* Sticky bottom input */}
          <div className="shrink-0 bg-background border-t border-border px-6 py-3">
            <ChatInput
              onSend={handleSend}
              loading={isIterating}
              placeholder="Describe a change..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}
