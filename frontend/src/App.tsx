import { useState } from "react";
import AppGallery from "./components/AppGallery";
import AppPreview from "./components/AppPreview";
import ChatInput from "./components/ChatInput";
import InstallPrompt from "./components/InstallPrompt";
import VoiceBar from "./components/VoiceBar";
import { useApps } from "./hooks/useApps";
import { useGenerate } from "./hooks/useGenerate";

export default function App() {
  const { apps, loading: appsLoading, refresh: refreshApps } = useApps();
  const {
    status,
    generatedAppId,
    generatedAppName,
    error,
    generate,
    iterate,
    dismiss,
  } = useGenerate(refreshApps);

  const [iterateMode, setIterateMode] = useState(false);
  const [showInstall, setShowInstall] = useState(false);

  const handleSend = (message: string) => {
    if (iterateMode && generatedAppId) {
      iterate(generatedAppId, message);
      setIterateMode(false);
    } else {
      generate(message);
    }
  };

  const handleOpenNewTab = () => {
    if (generatedAppId) {
      window.open(`/apps/${generatedAppId}/`, "_blank");
    }
  };

  const handleIterate = () => {
    setIterateMode(true);
  };

  const handleCancelIterate = () => {
    setIterateMode(false);
  };

  const isGenerating = status === "generating";

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-conjure-border">
        <h1 className="text-xl font-bold tracking-tight">Conjure</h1>
        <span className="text-xs text-conjure-muted">v0.1</span>
      </header>

      {/* Main content area */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {/* Generation status */}
        {isGenerating && (
          <div className="bg-conjure-card border border-conjure-border rounded-xl p-4 text-center">
            <div className="inline-block w-5 h-5 border-2 border-conjure-accent border-t-transparent
                            rounded-full animate-spin mb-2" />
            <p className="text-sm text-conjure-muted">
              {iterateMode ? "Updating your app..." : "Generating your app..."}
            </p>
          </div>
        )}

        {/* Error */}
        {status === "error" && error && (
          <div className="bg-red-900/20 border border-red-500/30 rounded-xl p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Preview of generated app */}
        {status === "done" && generatedAppId && (
          <AppPreview
            appId={generatedAppId}
            appName={generatedAppName}
            onOpenNewTab={handleOpenNewTab}
            onInstall={() => setShowInstall(true)}
            onDismiss={dismiss}
            onIterate={handleIterate}
          />
        )}

        {/* App Gallery */}
        <AppGallery apps={apps} loading={appsLoading} />
      </main>

      {/* Bottom input area */}
      <div className="sticky bottom-0 border-t border-conjure-border bg-conjure-bg px-4 py-3 space-y-2">
        <ChatInput
          onSend={handleSend}
          loading={isGenerating}
          placeholder={
            iterateMode
              ? "Describe what to change..."
              : "Describe an app you want..."
          }
          iterateMode={iterateMode}
          onCancelIterate={handleCancelIterate}
        />
        <VoiceBar />
      </div>

      {/* Install modal */}
      <InstallPrompt
        appName={generatedAppName || "App"}
        visible={showInstall}
        onClose={() => setShowInstall(false)}
      />
    </div>
  );
}
