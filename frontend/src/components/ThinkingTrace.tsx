interface Props {
  messages: string[];
  loading: boolean;
}

export default function ThinkingTrace({ messages, loading }: Props) {
  if (messages.length === 0 && !loading) return null;

  return (
    <div className="flex justify-start">
      <div className="rounded-xl bg-conjure-card border border-conjure-border px-4 py-3 max-w-[85%] space-y-1.5">
        {messages.map((msg, i) => {
          const isLast = i === messages.length - 1 && loading;
          return (
            <div
              key={i}
              className={`flex items-center gap-2 text-xs ${
                isLast ? "text-conjure-text" : "text-conjure-muted"
              }`}
            >
              {isLast ? (
                <span className="w-3 h-3 border-2 border-conjure-accent border-t-transparent rounded-full animate-spin shrink-0" />
              ) : (
                <span className="text-green-500 shrink-0">&#10003;</span>
              )}
              <span>{msg}</span>
            </div>
          );
        })}
        {loading && messages.length === 0 && (
          <div className="flex items-center gap-2 text-xs text-conjure-muted">
            <span className="w-3 h-3 border-2 border-conjure-accent border-t-transparent rounded-full animate-spin shrink-0" />
            <span>Starting...</span>
          </div>
        )}
      </div>
    </div>
  );
}
