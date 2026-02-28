import { useState, useEffect } from "react";
import AppGallery from "./components/AppGallery";
import ChatInput from "./components/ChatInput";
import CommandBar from "./components/CommandBar";
import InstallPrompt from "./components/InstallPrompt";
import ProjectChat from "./components/ProjectChat";
import { useApps } from "./hooks/useApps";
import { useGenerate } from "./hooks/useGenerate";
import type { App } from "./types/app";

type View = "gallery" | "create" | "chat";

export default function App() {
  const { apps, loading: appsLoading, refresh: refreshApps } = useApps();
  const {
    status,
    generatedAppId,
    generatedAppName,
    error,
    generate,
    dismiss,
  } = useGenerate(refreshApps);

  const [view, setView] = useState<View>("gallery");
  const [selectedAppId, setSelectedAppId] = useState<string | null>(null);
  const [showInstall, setShowInstall] = useState(false);
  const [installAppName, setInstallAppName] = useState("App");

  // Auto-navigate to chat view after generation completes
  useEffect(() => {
    if (status === "done" && generatedAppId) {
      setSelectedAppId(generatedAppId);
      setView("chat");
    }
  }, [status, generatedAppId]);

  const handleCreate = (message: string) => {
    generate(message);
  };

  const handleSelectApp = (appId: string) => {
    setSelectedAppId(appId);
    setView("chat");
  };

  const handleBack = () => {
    setSelectedAppId(null);
    dismiss();
    setView("gallery");
  };

  const handleInstall = (appName: string) => {
    setInstallAppName(appName);
    setShowInstall(true);
  };

  const isGenerating = status === "generating";

  // Build app object for the chat view
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
      ) : view === "create" ? (
        /* ── Create View ── */
        <>
          <header className="flex items-center gap-3 px-4 py-3 border-b border-conjure-border">
            <button
              onClick={() => { dismiss(); setView("gallery"); }}
              className="text-conjure-muted text-sm min-w-[44px] min-h-[44px] flex items-center"
            >
              &larr; Back
            </button>
            <h1 className="text-lg font-semibold">New App</h1>
          </header>

          <main className="flex-1 flex flex-col items-center justify-center px-4 gap-3">
            {isGenerating ? (
              <div className="text-center">
                <div
                  className="inline-block w-6 h-6 border-2 border-conjure-accent border-t-transparent
                              rounded-full animate-spin mb-3"
                />
                <p className="text-sm text-conjure-muted">
                  Generating your app...
                </p>
              </div>
            ) : status === "error" && error ? (
              <div className="w-full max-w-md">
                <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              </div>
            ) : (
              <p className="text-conjure-muted text-sm">
                Describe an app and we'll build it.
              </p>
            )}
          </main>

          <div className="sticky bottom-0 border-t border-conjure-border bg-conjure-bg px-4 py-3">
            <ChatInput onSend={handleCreate} loading={isGenerating} />
          </div>
        </>
      ) : (
        /* ── Gallery View ── */
        <>
          <header className="flex items-center justify-between px-4 py-3 border-b border-conjure-border">
            <h1 className="text-xl font-bold tracking-tight">Conjure</h1>
            <button
              onClick={() => setView("create")}
              className="w-9 h-9 rounded-full bg-conjure-accent flex items-center justify-center
                         text-white text-lg font-bold active:scale-95 transition-transform"
            >
              +
            </button>
          </header>

          <main className="flex-1 overflow-y-auto px-4 py-4">
            <AppGallery
              apps={apps}
              loading={appsLoading}
              onSelectApp={handleSelectApp}
            />
          </main>

          <CommandBar
            onCreateHandoff={(prompt) => {
              generate(prompt);
              setView("create");
            }}
          />
        </>
      )}

      {/* Install modal */}
      <InstallPrompt
        appName={installAppName}
        visible={showInstall}
        onClose={() => setShowInstall(false)}
      />
    </div>
  );
}
