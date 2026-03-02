import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { ArrowLeft, ArrowRight, ArrowUp, AlertCircle, Loader2, Timer, ListChecks, Trophy, Mic, Keyboard, Zap } from "lucide-react";
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
  { icon: Timer, text: "I'm doing a HIIT workout, 40s on, 20s rest, 8 rounds of burpees" },
  { icon: ListChecks, text: "Track my water intake, I want to hit 3 liters today" },
  { icon: Trophy, text: "Poker night scoreboard for me and my three friends" },
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

  const {
    messages: cmdMessages,
    loading: cmdLoading,
    send: cmdSend,
    handoff,
    clearHandoff,
    iterateHandoff,
    clearIterateHandoff,
    clearConversation,
  } = useCommand();

  // Voice — transcription feeds directly into Command Plane
  const handleVoiceTranscription = useCallback((text: string) => {
    cmdSend(text);
  }, [cmdSend]);
  const { voiceState, error: voiceError, toggleRecording } = useVoice(handleVoiceTranscription);

  const [view, setView] = useState<View>("home");
  const [inputMode, setInputMode] = useState<"speech" | "text">("speech");
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [showInstall, setShowInstall] = useState(false);
  const [installAppName, setInstallAppName] = useState("App");
  const [pendingInstruction, setPendingInstruction] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

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

  // Handle iterate handoff → navigate to app chat with instruction
  useEffect(() => {
    if (iterateHandoff) {
      setSelectedAppId(iterateHandoff.app_id);
      setPendingInstruction(iterateHandoff.instruction);
      setView("chat");
      clearIterateHandoff();
    }
  }, [iterateHandoff, clearIterateHandoff]);

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
    setPendingInstruction(null);
    dismiss();
    clearConversation();
    setView("home");
  };

  const handleInstall = (appName: string) => {
    setInstallAppName(appName);
    setShowInstall(true);
  };

  const handleSuggestion = (text: string) => {
    cmdSend(text);
  };

  const isGenerating = status === "generating";
  const isRecording = voiceState === "recording";
  const isTranscribing = voiceState === "transcribing";
  const hasConversation = cmdMessages.length > 0;
  const hasApps = apps.length > 0;

  // Generate contextual command suggestions based on existing apps
  const commandSuggestions = useMemo(() => {
    if (!hasApps) return [];
    const cmds: string[] = [];
    for (const app of apps.slice(0, 4)) {
      const n = app.name.toLowerCase();
      if (n.includes("todo") || n.includes("task") || n.includes("list")) {
        cmds.push(`What's left on my ${app.name}?`);
      } else if (n.includes("timer") || n.includes("hiit") || n.includes("workout")) {
        cmds.push(`Set my ${app.name} to 30s work, 10s rest`);
      } else if (n.includes("water") || n.includes("hydra") || n.includes("drink")) {
        cmds.push(`Log a glass of water`);
      } else if (n.includes("score") || n.includes("poker") || n.includes("game")) {
        cmds.push(`Add 5 points to my score in ${app.name}`);
      } else if (n.includes("habit") || n.includes("track")) {
        cmds.push(`Mark today's habit as done in ${app.name}`);
      } else {
        cmds.push(`What's the status of my ${app.name}?`);
      }
      if (cmds.length >= 2) break;
    }
    return cmds;
  }, [apps, hasApps]);

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
          initialInstruction={pendingInstruction ?? undefined}
          inputMode={inputMode}
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
        <div className="flex flex-col min-h-[100dvh] max-w-3xl mx-auto w-full">
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

          {!isGenerating && (
            <div className="sticky bottom-0 bg-background border-t border-border px-6 py-3">
              <ChatInput onSend={(msg) => generate(msg)} loading={isGenerating} />
            </div>
          )}
        </div>

      ) : (
        /* ── Home View (Command Plane) ── */
        <div className="flex flex-col min-h-[100dvh] max-w-3xl mx-auto w-full">
          {/* Header */}
          <header className="flex items-center justify-between px-6 py-4">
            <h1 className="text-xl font-bold tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.02em' }}>Conjure</h1>
            <div className="flex items-center gap-3">
              {/* Speech / Text toggle */}
              <div className="flex items-center rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => setInputMode("speech")}
                  className={`flex items-center justify-center w-8 h-8 transition-colors duration-150 ${
                    inputMode === "speech"
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-label="Speech mode"
                >
                  <Mic className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setInputMode("text")}
                  className={`flex items-center justify-center w-8 h-8 transition-colors duration-150 ${
                    inputMode === "text"
                      ? "bg-foreground text-background"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  aria-label="Text mode"
                >
                  <Keyboard className="w-3.5 h-3.5" />
                </button>
              </div>
              {hasApps && (
                <button
                  onClick={() => setView("apps")}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  Your Apps
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </header>

          {/* Main scrollable area */}
          <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto flex flex-col">
            {!hasConversation ? (
              /* Idle state — suggestions above, orb below */
              <div className="flex-1 flex flex-col items-center justify-end px-6 pb-[10%]">
                {/* Suggestion chips */}
                <div className="flex flex-col gap-2 w-full max-w-lg">
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                    Try saying
                  </p>
                  {SUGGESTIONS.map((s, i) => (
                    <button
                      key={i}
                      onClick={() => handleSuggestion(s.text)}
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

                {/* Contextual command suggestions — only when apps exist */}
                {commandSuggestions.length > 0 && (
                  <div className="flex flex-col gap-2 w-full max-w-lg mt-4 mb-[10%]">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                      Your apps
                    </p>
                    {commandSuggestions.map((cmd, i) => (
                      <button
                        key={`cmd-${i}`}
                        onClick={() => handleSuggestion(cmd)}
                        className="flex items-center gap-3 text-left px-4 py-3 rounded-xl
                          border border-border text-sm text-foreground
                          hover:bg-secondary transition-colors duration-150
                          animate-fade-in-up"
                        style={{ animationDelay: `${(SUGGESTIONS.length + i + 1) * 0.05}s` }}
                      >
                        <Zap className="w-4 h-4 text-muted-foreground shrink-0" />
                        <span className="flex-1">{cmd}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                      </button>
                    ))}
                  </div>
                )}

                {/* Spacer when no command suggestions */}
                {commandSuggestions.length === 0 && <div className="mb-[10%]" />}

                {/* Aurora orb — speech mode only */}
                {inputMode === "speech" && (
                  <div className="flex flex-col items-center">
                    <button
                      onClick={toggleRecording}
                      disabled={isTranscribing || cmdLoading}
                      className="relative flex items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 active:scale-95 disabled:opacity-60 outline-none"
                      style={{ width: 80, height: 80 }}
                    >
                      <div
                        className="absolute inset-0"
                        style={{
                          animation: isRecording
                            ? 'aurora-pulse 1.2s ease-in-out infinite'
                            : 'aurora-breathe 3s ease-in-out infinite',
                        }}
                      >
                        <div
                          className={`absolute rounded-full transition-opacity duration-700 ${
                            isRecording ? 'opacity-70' : 'opacity-50'
                          }`}
                          style={{
                            inset: '-8px',
                            background: 'conic-gradient(from 0deg, #818cf8, #38bdf8, #818cf8)',
                            filter: 'blur(20px)',
                            animation: `aurora-spin ${isRecording ? '3s' : '8s'} linear infinite`,
                          }}
                        />
                        <div
                          className={`absolute rounded-full transition-opacity duration-700 ${
                            isRecording ? 'opacity-60' : 'opacity-40'
                          }`}
                          style={{
                            inset: '-2px',
                            background: 'conic-gradient(from 180deg, #c084fc, #2dd4bf, #c084fc)',
                            filter: 'blur(16px)',
                            animation: `aurora-spin ${isRecording ? '2.5s' : '6s'} linear infinite reverse`,
                          }}
                        />
                        <div
                          className={`absolute rounded-full transition-opacity duration-700 ${
                            isRecording ? 'opacity-50' : 'opacity-0'
                          }`}
                          style={{
                            inset: '4px',
                            background: 'conic-gradient(from 90deg, #fb7185, #f472b6, #fb7185)',
                            filter: 'blur(12px)',
                            animation: 'aurora-spin 2s linear infinite',
                          }}
                        />
                      </div>

                      {isTranscribing && (
                        <div className="relative z-10">
                          <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                        </div>
                      )}
                    </button>

                    <p className={`text-xs mt-2 transition-colors duration-300 ${
                      isRecording ? 'text-foreground font-medium' : 'text-muted-foreground'
                    }`}>
                      {isRecording ? 'Listening...' : isTranscribing ? 'Transcribing...' : 'Tap to speak'}
                    </p>

                    {voiceError && (
                      <p className="text-[11px] text-destructive mt-1">{voiceError}</p>
                    )}
                  </div>
                )}
              </div>
            ) : (
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
            )}
          </div>

          {/* Bottom input — respects input mode */}
          {inputMode === "text" ? (
            <div className="shrink-0 bg-background border-t border-border px-6 py-3">
              <ChatInput
                onSend={cmdSend}
                loading={cmdLoading}
                placeholder="Ask anything..."
                showMic={true}
              />
            </div>
          ) : hasConversation ? (
            <div className="shrink-0 bg-background px-6 py-4 flex flex-col items-center">
              <button
                onClick={toggleRecording}
                disabled={isTranscribing || cmdLoading}
                className="relative flex items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 active:scale-95 disabled:opacity-60 outline-none"
                style={{ width: 80, height: 80 }}
              >
                <div
                  className="absolute inset-0"
                  style={{
                    animation: isRecording
                      ? 'aurora-pulse 1.2s ease-in-out infinite'
                      : 'aurora-breathe 3s ease-in-out infinite',
                  }}
                >
                  <div
                    className={`absolute rounded-full transition-opacity duration-700 ${
                      isRecording ? 'opacity-70' : 'opacity-50'
                    }`}
                    style={{
                      inset: '-8px',
                      background: 'conic-gradient(from 0deg, #818cf8, #38bdf8, #818cf8)',
                      filter: 'blur(20px)',
                      animation: `aurora-spin ${isRecording ? '3s' : '8s'} linear infinite`,
                    }}
                  />
                  <div
                    className={`absolute rounded-full transition-opacity duration-700 ${
                      isRecording ? 'opacity-60' : 'opacity-40'
                    }`}
                    style={{
                      inset: '-2px',
                      background: 'conic-gradient(from 180deg, #c084fc, #2dd4bf, #c084fc)',
                      filter: 'blur(16px)',
                      animation: `aurora-spin ${isRecording ? '2.5s' : '6s'} linear infinite reverse`,
                    }}
                  />
                  <div
                    className={`absolute rounded-full transition-opacity duration-700 ${
                      isRecording ? 'opacity-50' : 'opacity-0'
                    }`}
                    style={{
                      inset: '4px',
                      background: 'conic-gradient(from 90deg, #fb7185, #f472b6, #fb7185)',
                      filter: 'blur(12px)',
                      animation: 'aurora-spin 2s linear infinite',
                    }}
                  />
                </div>
                {isTranscribing && (
                  <div className="relative z-10">
                    <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                  </div>
                )}
              </button>
              <p className={`text-xs mt-2 transition-colors duration-300 ${
                isRecording ? 'text-foreground font-medium' : 'text-muted-foreground'
              }`}>
                {isRecording ? 'Listening...' : isTranscribing ? 'Transcribing...' : 'Tap to speak'}
              </p>
              {voiceError && (
                <p className="text-[11px] text-destructive">{voiceError}</p>
              )}
            </div>
          ) : null}
        </div>
      )}

      <InstallPrompt
        appName={installAppName}
        visible={showInstall}
        onClose={() => setShowInstall(false)}
      />
    </div>
  );
}
