interface Props {
  appId: string;
  appName: string | null;
  onOpenNewTab: () => void;
  onInstall: () => void;
  onDismiss: () => void;
  onIterate: () => void;
}

export default function AppPreview({
  appId,
  appName,
  onOpenNewTab,
  onInstall,
  onDismiss,
  onIterate,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      {/* App name */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold truncate">
          {appName || "Your App"}
        </h2>
        <button
          onClick={onDismiss}
          className="text-conjure-muted text-sm px-2 py-1"
        >
          Dismiss
        </button>
      </div>

      {/* iframe preview */}
      <div className="relative rounded-xl overflow-hidden border border-conjure-border bg-black"
           style={{ height: "60vh" }}>
        <iframe
          src={`/apps/${appId}/`}
          className="w-full h-full border-0"
          title="App Preview"
          sandbox="allow-scripts allow-same-origin allow-forms"
        />
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-3 gap-2">
        <button
          onClick={onOpenNewTab}
          className="py-3 rounded-lg bg-conjure-accent text-white text-sm font-medium
                     active:scale-95 transition-transform"
        >
          Open App
        </button>
        <button
          onClick={onInstall}
          className="py-3 rounded-lg bg-conjure-card border border-conjure-border
                     text-conjure-text text-sm font-medium
                     active:scale-95 transition-transform"
        >
          Install
        </button>
        <button
          onClick={onIterate}
          className="py-3 rounded-lg bg-conjure-card border border-conjure-border
                     text-conjure-text text-sm font-medium
                     active:scale-95 transition-transform"
        >
          Modify
        </button>
      </div>
    </div>
  );
}
