import { Loader2, Check } from "lucide-react";

interface Props {
  messages: string[];
  loading: boolean;
}

export default function ThinkingTrace({ messages, loading }: Props) {
  if (messages.length === 0 && !loading) return null;

  return (
    <div className="flex gap-2.5 animate-fade-in-up">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-full shrink-0 bg-secondary flex items-center justify-center mt-0.5">
        <Loader2 className={`w-3.5 h-3.5 text-muted-foreground ${loading ? "animate-spin" : ""}`} />
      </div>

      <div className="flex-1 max-w-[80%]">
        <div className="rounded-2xl border border-border bg-background overflow-hidden">
          {/* Header */}
          <div className="px-4 pt-3 pb-2 border-b border-border">
            <div className="flex items-center gap-2 mb-2">
              {loading ? (
                <div className="w-2 h-2 rounded-full bg-foreground animate-pulse" />
              ) : (
                <div className="w-2 h-2 rounded-full bg-green-600" />
              )}
              <span className="text-xs font-medium text-foreground">
                {loading ? "Building..." : "Complete"}
              </span>
            </div>

            {loading && (
              <div className="w-full h-0.5 bg-border rounded-full overflow-hidden">
                <div
                  className="h-full w-1/3 rounded-full bg-foreground"
                  style={{
                    animation: "progress-indeterminate 1.5s ease-in-out infinite",
                  }}
                />
              </div>
            )}
          </div>

          {/* Steps */}
          <div className="px-4 py-2.5 space-y-2">
            {messages.map((msg, i) => {
              const isLast = i === messages.length - 1 && loading;

              return (
                <div
                  key={i}
                  className="flex items-start gap-2.5 animate-fade-in-up"
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  <div className="mt-0.5 shrink-0">
                    {isLast ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full bg-green-100 flex items-center justify-center">
                        <Check className="w-2.5 h-2.5 text-green-600" />
                      </div>
                    )}
                  </div>

                  <span
                    className={`text-xs leading-relaxed ${
                      isLast ? "text-foreground" : "text-muted-foreground"
                    }`}
                  >
                    {msg}
                  </span>
                </div>
              );
            })}

            {loading && messages.length === 0 && (
              <div className="flex items-center gap-2.5 py-1">
                <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Initializing...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
