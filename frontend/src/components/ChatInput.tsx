import { useState, useCallback, type FormEvent } from "react";
import { useVoice } from "../hooks/useVoice";

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
  placeholder?: string;
  buttonText?: string;
}

export default function ChatInput({
  onSend,
  loading,
  placeholder,
  buttonText = "Create",
}: Props) {
  const [input, setInput] = useState("");

  const handleTranscription = useCallback((text: string) => {
    setInput((prev) => (prev ? `${prev} ${text}` : text));
  }, []);

  const { voiceState, error: voiceError, toggleRecording } = useVoice(handleTranscription);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setInput("");
  };

  const isRecording = voiceState === "recording";
  const isTranscribing = voiceState === "transcribing";
  const micDisabled = loading || isTranscribing;

  return (
    <div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        {/* Mic button */}
        <button
          type="button"
          onClick={toggleRecording}
          disabled={micDisabled}
          className={`w-11 h-11 flex items-center justify-center rounded-lg border
                      transition-all shrink-0
                      ${isRecording
                        ? "bg-red-500/20 border-red-500 text-red-400 animate-pulse"
                        : "bg-conjure-card border-conjure-border text-conjure-muted"
                      }
                      ${micDisabled ? "opacity-40" : "active:scale-95"}`}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
        >
          {isTranscribing ? (
            <span className="w-4 h-4 border-2 border-conjure-muted border-t-transparent
                             rounded-full animate-spin" />
          ) : (
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="9" y="1" width="6" height="12" rx="3" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </button>

        {/* Text input */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            isRecording
              ? "Listening..."
              : isTranscribing
                ? "Transcribing..."
                : placeholder || "Describe an app you want..."
          }
          disabled={loading}
          className="flex-1 bg-conjure-card border border-conjure-border rounded-lg
                     px-4 py-3 text-sm text-conjure-text placeholder-conjure-muted
                     focus:outline-none focus:border-conjure-accent"
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-3 bg-conjure-accent rounded-lg text-sm font-medium
                     text-white disabled:opacity-40 active:scale-95 transition-transform"
        >
          {loading ? "..." : buttonText}
        </button>
      </form>

      {voiceError && (
        <p className="text-xs text-red-400 mt-1 px-1">{voiceError}</p>
      )}
    </div>
  );
}
