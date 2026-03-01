import type { App } from "@/types/app";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  apps: App[];
  loading: boolean;
  onSelectApp: (appId: string) => void;
  onBack: () => void;
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return "Just now";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function AppGallery({ apps, loading, onSelectApp, onBack }: Props) {
  return (
    <div className="flex flex-col min-h-[100dvh]">
      <header className="flex items-center gap-3 px-6 py-3 border-b border-border">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="shrink-0 rounded-full w-8 h-8"
        >
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <h1 className="text-sm font-semibold">Your Apps</h1>
      </header>

      <div className="flex-1 px-6 py-2">
        {loading ? (
          <div className="space-y-1">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <div className="w-10 h-10 rounded-lg bg-secondary animate-pulse" />
                <div className="flex-1 space-y-2">
                  <div className="w-28 h-3.5 rounded bg-secondary animate-pulse" />
                  <div className="w-16 h-2.5 rounded bg-secondary animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        ) : apps.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-muted-foreground">No apps yet</p>
          </div>
        ) : (
          <div>
            {apps.map((app, i) => {
              const color = app.theme_color || "#6366f1";
              return (
                <button
                  key={app.id}
                  onClick={() => onSelectApp(app.id)}
                  className="w-full flex items-center gap-3 py-3 border-b border-border last:border-b-0 text-left transition-colors hover:bg-secondary/50 animate-fade-in-up"
                  style={{ animationDelay: `${i * 0.03}s` }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
                    style={{ backgroundColor: color }}
                  >
                    {app.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{app.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(app.created_at)}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0" />
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
