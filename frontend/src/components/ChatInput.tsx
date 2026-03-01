import { useState, useCallback, type FormEvent } from "react";
import { Mic, ArrowUp, Loader2 } from "lucide-react";
import { useVoice } from "@/hooks/useVoice";

interface Props {
  onSend: (message: string) => void;
  loading: boolean;
  placeholder?: string;
  showMic?: boolean;
}

export default function ChatInput({
  onSend,
  loading,
  placeholder,
  showMic = true,
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
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 h-11 px-2 rounded-xl border border-border bg-background transition-colors duration-150 focus-within:border-foreground/20"
      >
        {/* Mic button */}
        {showMic && (
          <button
            type="button"
            onClick={toggleRecording}
            disabled={micDisabled}
            className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 ${
              isRecording
                ? "bg-red-50 text-red-600"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            } disabled:opacity-40`}
            aria-label={isRecording ? "Stop recording" : "Start recording"}
          >
            {isTranscribing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Mic className="w-4 h-4" />
            )}
          </button>
        )}

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
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none disabled:opacity-50 py-2"
        />

        {/* Send button */}
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 ${
            input.trim() && !loading
              ? "bg-foreground text-background"
              : "bg-secondary text-muted-foreground"
          } disabled:opacity-40`}
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ArrowUp className="w-4 h-4" />
          )}
        </button>
      </form>

      {voiceError && (
        <p className="text-[11px] text-destructive mt-1.5 px-2">{voiceError}</p>
      )}
    </div>
  );
}
