import { useState, type FormEvent } from "react";

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
  placeholder?: string;
  iterateMode?: boolean;
  onCancelIterate?: () => void;
}

export default function ChatInput({
  onSend,
  loading,
  placeholder,
  iterateMode,
  onCancelIterate,
}: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      {iterateMode && onCancelIterate && (
        <button
          type="button"
          onClick={onCancelIterate}
          className="px-3 py-3 bg-conjure-card border border-conjure-border rounded-lg
                     text-conjure-muted text-sm active:scale-95 transition-transform"
        >
          &times;
        </button>
      )}
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={placeholder || "Describe an app you want..."}
        disabled={loading}
        className="flex-1 bg-conjure-card border border-conjure-border rounded-lg
                   px-4 py-3 text-sm text-conjure-text placeholder-conjure-muted
                   focus:outline-none focus:border-conjure-accent"
      />
      <button
        type="submit"
        disabled={loading || !input.trim()}
        className="px-4 py-3 bg-conjure-accent rounded-lg text-sm font-medium
                   text-white disabled:opacity-40 active:scale-95 transition-transform"
      >
        {loading ? "..." : iterateMode ? "Update" : "Create"}
      </button>
    </form>
  );
}
