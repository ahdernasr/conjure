import { useState, useEffect, useCallback, useRef } from "react";
import { ArrowLeft, ArrowRight, AlertCircle, Mic, Loader2, Timer, ListChecks, Trophy } from "lucide-react";
import AppGallery from "@/components/AppGallery";
import ChatInput from "@/components/ChatInput";
import InstallPrompt from "@/components/InstallPrompt";
import ProjectChat from "@/components/ProjectChat";
import ThinkingTrace from "@/components/ThinkingTrace";
import { useApps } from "@/hooks/useApps";
import { useGenerate } from "@/hooks/useGenerate";
import { useCommand, type CommandMessage } from "@/hooks/useCommand";
import { useVoice } from "@/hooks/useVoice";
import { Button } from "@/components/ui/button";
import type { App } from "@/types/app";

type View = "home" | "apps" | "create" | "chat";

const SUGGESTIONS = [
  { icon: Timer, text: "HIIT timer, 40s work, 20s rest" },
  { icon: ListChecks, text: "Packing list with checkboxes" },
  { icon: Trophy, text: "Poker night scoreboard for 4" },
];

export default function App() {
  const { apps, loading: appsLoading, refresh: refreshApps } = useApps();
  const {
    status,
    generatedAppId,
    generatedAppName,
    error: generateError,
    traceMessages,
    generate,
    dismiss,
  } = useGenerate(refreshApps);

  const { messages: cmdMessages, loading: cmdLoading, send: cmdSend, handoff, clearHandoff } = useCommand();

  const [view, setView] = useState<View>("home");
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [showInstall, setShowInstall] = useState(false);
  const [installAppName, setInstallAppName] = useState("App");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Voice for home hero mic
  const handleVoiceTranscription = useCallback((text: string) => {
    cmdSend(text);
  }, [cmdSend]);

  const { voiceState, error: voiceError, toggleRecording } = useVoice(handleVoiceTranscription);

  // Auto-scroll command messages
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [cmdMessages, cmdLoading]);

  // Handle command handoff → create
  useEffect(() => {
    if (handoff) {
      generate(handoff.prompt);
      setView("create");
      clearHandoff();
    }
  }, [handoff, generate, clearHandoff]);

  // When generation completes → chat
  useEffect(() => {
    if (status === "done" && generatedAppId) {
      setSelectedAppId(generatedAppId);
      setView("chat");
    }
  }, [status, generatedAppId]);

  const handleSelectApp = (appId: string) => {
    setSelectedAppId(appId);
    setView("chat");
  };

  const handleBack = () => {
    setSelectedAppId(null);
    dismiss();
    setView("home");
  };

  const handleInstall = (appName: string) => {
    setInstallAppName(appName);
    setShowInstall(true);
  };

  const handleSuggest = (prompt: string) => {
    generate(prompt);
    setView("create");
  };

  const isGenerating = status === "generating";
  const isRecording = voiceState === "recording";
  const isTranscribing = voiceState === "transcribing";
  const hasConversation = cmdMessages.length > 0;

  const selectedApp: App | null = selectedAppId
    ? apps.find((a) => a.id === selectedAppId) ?? {
        id: selectedAppId,
        name: generatedAppName || "Your App",
        description: "",
        theme_color: "#6366f1",
        created_at: "",
        updated_at: "",
        status: "ready",
      }
    : null;

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {/* ── Chat View ── */}
      {view === "chat" && selectedApp ? (
        <ProjectChat
          app={selectedApp}
          onBack={handleBack}
          onInstall={handleInstall}
        />

      ) : view === "apps" ? (
        /* ── Apps List View ── */
        <AppGallery
          apps={apps}
          loading={appsLoading}
          onSelectApp={handleSelectApp}
          onBack={() => setView("home")}
          onDeleted={refreshApps}
          onAddApp={() => setView("home")}
        />

      ) : view === "create" ? (
        /* ── Create View ── */
        <>
          <header className="flex items-center gap-3 px-6 py-3 border-b border-border">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => { dismiss(); setView("home"); }}
              className="rounded-full w-8 h-8"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <h1 className="text-sm font-semibold">New App</h1>
              <p className="text-[11px] text-muted-foreground">
                {isGenerating ? "Generating..." : "Describe what you need"}
              </p>
            </div>
          </header>

          <main className="flex-1 flex flex-col items-center justify-center px-6 gap-4">
            {isGenerating ? (
              <div className="w-full max-w-md">
                <ThinkingTrace messages={traceMessages} loading={isGenerating} />
              </div>
            ) : status === "error" && generateError ? (
              <div className="flex items-center gap-2 text-sm text-destructive max-w-md">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <p>{generateError}</p>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm text-center max-w-[260px]">
                Describe an app and we'll build it in seconds.
              </p>
            )}
          </main>

          <div className="sticky bottom-0 bg-background border-t border-border px-6 py-3">
            <ChatInput onSend={(msg) => generate(msg)} loading={isGenerating} />
          </div>
        </>

      ) : (
        /* ── Home View (Voice-First) ── */
        <>
          {/* Header */}
          <header className="flex items-center justify-between px-6 py-4">
            <h1 className="text-xl font-bold tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em' }}>Conjure</h1>
            {apps.length > 0 && (
              <button
                onClick={() => setView("apps")}
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Your Apps
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </header>

          {/* Center content */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto flex flex-col">
            {hasConversation ? (
              /* Conversation mode */
              <div className="flex-1 px-6 py-4 space-y-3">
                {cmdMessages.map((msg: CommandMessage, i: number) => (
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
                {cmdLoading && (
                  <div className="flex justify-start animate-fade-in-up">
                    <div className="bg-secondary rounded-2xl px-4 py-2.5">
                      <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Hero mode */
              <div className="flex-1 flex flex-col items-center justify-center px-6 pb-4">
                <p className="text-xl font-medium text-foreground mb-1">
                  What do you want to build?
                </p>
                <p className="text-sm text-muted-foreground mb-10">
                  Tap to speak or type below
                </p>

                {/* Hero mic button */}
                <button
                  onClick={toggleRecording}
                  disabled={isTranscribing}
                  className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-200 mb-3 ${
                    isRecording
                      ? "bg-red-50 text-red-600"
                      : "bg-secondary text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
                  } disabled:opacity-50`}
                >
                  {isTranscribing ? (
                    <Loader2 className="w-8 h-8 animate-spin" />
                  ) : (
                    <Mic className="w-8 h-8" />
                  )}
                  {isRecording && (
                    <span className="absolute inset-0 rounded-full border-2 border-red-300 animate-ping pointer-events-none" />
                  )}
                </button>

                <p className="text-xs text-muted-foreground mb-10">
                  {isRecording ? "Listening..." : isTranscribing ? "Transcribing..." : "Tap to speak"}
                </p>

                {voiceError && (
                  <p className="text-xs text-destructive mb-6">{voiceError}</p>
                )}

                {/* Suggestion chips */}
                <div className="flex flex-col gap-2 w-full max-w-sm">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Try saying
                  </p>
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggest(s.text)}
                      className="flex items-center gap-3 text-left px-4 py-3 rounded-xl
                        border border-border text-sm text-foreground
                        hover:bg-secondary transition-colors duration-150
                        animate-fade-in-up"
                      style={{ animationDelay: `${(i + 1) * 0.05}s` }}
                    >
                      <s.icon className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span className="flex-1">{s.text}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Bottom input */}
          <div className="sticky bottom-0 bg-background border-t border-border px-6 py-3">
            <ChatInput
              onSend={cmdSend}
              loading={cmdLoading}
              placeholder={hasConversation ? "Ask about your apps..." : "Or type here..."}
              showMic={false}
            />
          </div>
        </>
      )}

      <InstallPrompt
        appName={installAppName}
        visible={showInstall}
        onClose={() => setShowInstall(false)}
      />
    </div>
  );
}
