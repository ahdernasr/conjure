import AppGallery from "./components/AppGallery";
import ChatInput from "./components/ChatInput";
import ChatResponse from "./components/ChatResponse";
import VoiceBar from "./components/VoiceBar";
import { useApps } from "./hooks/useApps";
import { useChat } from "./hooks/useChat";

export default function App() {
  const { apps, loading: appsLoading } = useApps();
  const { response, loading: chatLoading, sendMessage } = useChat();

  return (
    <div className="flex flex-col min-h-[100dvh]">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-conjure-border">
        <h1 className="text-xl font-bold tracking-tight">Conjure</h1>
        <span className="text-xs text-conjure-muted">v0.1</span>
      </header>

      {/* Main content area — scrollable */}
      <main className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Chat response display */}
        {response && <ChatResponse text={response} loading={chatLoading} />}

        {/* App Gallery */}
        <AppGallery apps={apps} loading={appsLoading} />

        {/* Phase 2: AppPreview iframe will go here */}
        {/* Phase 2: InstallPrompt modal will go here */}
      </main>

      {/* Bottom input area */}
      <div className="sticky bottom-0 border-t border-conjure-border bg-conjure-bg px-4 py-3 space-y-2">
        <ChatInput onSend={sendMessage} loading={chatLoading} />
        {/* Phase 4: VoiceBar replaces/augments ChatInput */}
        <VoiceBar />
      </div>
    </div>
  );
}
