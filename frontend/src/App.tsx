import { useState, useEffect, useCallback, useRef } from "react";
import { ArrowLeft, ArrowRight, ArrowUp, AlertCircle, Loader2, Timer, ListChecks, Trophy } from "lucide-react";
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
  const [heroInput, setHeroInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Voice for home hero mic — feed transcription into the input field
  const handleVoiceTranscription = useCallback((text: string) => {
    setHeroInput((prev) => (prev ? `${prev} ${text}` : text));
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

          <div className="sticky bottom-0 bg-background border-t border-border px-6 py-3">
            <ChatInput onSend={(msg) => generate(msg)} loading={isGenerating} />
          </div>
        </div>

      ) : (
        /* ── Home View (Voice-First) ── */
        <div className="flex flex-col min-h-[100dvh] max-w-3xl mx-auto w-full">
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
            {!hasConversation ? (
              /* Hero mode */
              <div className="flex-1 flex flex-col items-center justify-center px-6 pb-4">
                <p className="text-2xl font-semibold text-foreground mb-2 tracking-tight">
                  What do you want to build?
                </p>
                <p className="text-sm text-muted-foreground mb-12">
                  Describe an app and we'll create it instantly
                </p>

                {/* Aurora Orb — the blob IS the button */}
                <button
                  onClick={toggleRecording}
                  disabled={isTranscribing || cmdLoading}
                  className="relative flex items-center justify-center mb-2 cursor-pointer transition-transform duration-300 hover:scale-105 active:scale-95 disabled:opacity-60 outline-none"
                  style={{ width: 200, height: 200 }}
                >
                  {/* Glow wrapper — breathes on idle, pulses on record */}
                  <div
                    className="absolute inset-0"
                    style={{
                      animation: isRecording
                        ? 'aurora-pulse 1.2s ease-in-out infinite'
                        : 'aurora-breathe 3s ease-in-out infinite',
                    }}
                  >
                    {/* Layer 1 — indigo/sky conic gradient */}
                    <div
                      className={`absolute rounded-full transition-opacity duration-700 ${
                        isRecording ? 'opacity-70' : 'opacity-30'
                      }`}
                      style={{
                        inset: '-15px',
                        background: 'conic-gradient(from 0deg, #818cf8, #38bdf8, #818cf8)',
                        filter: 'blur(40px)',
                        animation: `aurora-spin ${isRecording ? '3s' : '8s'} linear infinite`,
                      }}
                    />
                    {/* Layer 2 — purple/teal counter-rotate */}
                    <div
                      className={`absolute rounded-full transition-opacity duration-700 ${
                        isRecording ? 'opacity-60' : 'opacity-20'
                      }`}
                      style={{
                        inset: '-5px',
                        background: 'conic-gradient(from 180deg, #c084fc, #2dd4bf, #c084fc)',
                        filter: 'blur(35px)',
                        animation: `aurora-spin ${isRecording ? '2.5s' : '6s'} linear infinite reverse`,
                      }}
                    />
                    {/* Layer 3 — warm accent, fades in when recording */}
                    <div
                      className={`absolute rounded-full transition-opacity duration-700 ${
                        isRecording ? 'opacity-50' : 'opacity-0'
                      }`}
                      style={{
                        inset: '5px',
                        background: 'conic-gradient(from 90deg, #fb7185, #f472b6, #fb7185)',
                        filter: 'blur(28px)',
                        animation: 'aurora-spin 2s linear infinite',
                      }}
                    />
                  </div>

                  {/* Transcribing indicator */}
                  {isTranscribing && (
                    <div className="relative z-10">
                      <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                    </div>
                  )}
                </button>

                {/* Mic status label */}
                <p className={`text-xs mt-4 mb-8 transition-colors duration-300 ${
                  isRecording ? 'text-foreground font-medium' : 'text-muted-foreground'
                }`}>
                  {isRecording ? 'Listening...' : isTranscribing ? 'Transcribing...' : 'Tap to speak'}
                </p>

                {voiceError && (
                  <p className="text-xs text-destructive mb-3 px-1">{voiceError}</p>
                )}

                {/* Text input bar */}
                <div className="w-full max-w-lg mb-8">
                  <div className="flex items-center gap-2 h-12 px-4 rounded-xl border border-border bg-background focus-within:border-foreground/20 transition-all duration-200">
                    <input
                      type="text"
                      value={heroInput}
                      onChange={(e) => setHeroInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && heroInput.trim() && !cmdLoading) {
                          handleSuggest(heroInput.trim());
                          setHeroInput("");
                        }
                      }}
                      placeholder="or type your idea..."
                      disabled={cmdLoading}
                      className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none disabled:opacity-50"
                    />
                    <button
                      onClick={() => {
                        if (heroInput.trim()) {
                          handleSuggest(heroInput.trim());
                          setHeroInput("");
                        }
                      }}
                      disabled={cmdLoading || !heroInput.trim()}
                      className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 ${
                        heroInput.trim() && !cmdLoading
                          ? "bg-foreground text-background"
                          : "bg-secondary text-muted-foreground"
                      } disabled:opacity-40`}
                    >
                      <ArrowUp className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Suggestion chips */}
                <div className="flex flex-col gap-2 w-full max-w-lg">
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
            ) : (
              /* Conversation mode */
              <>
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
              </>
            )}
          </div>

          {/* Bottom input — only in conversation mode */}
          {hasConversation && (
            <div className="shrink-0 bg-background border-t border-border px-6 py-3">
              <ChatInput
                onSend={cmdSend}
                loading={cmdLoading}
                placeholder="Ask about your apps..."
                showMic={false}
              />
            </div>
          )}
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
