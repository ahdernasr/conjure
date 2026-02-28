import { useEffect, useRef, useState } from "react";
import ChatInput from "./ChatInput";
import { useCommand } from "../hooks/useCommand";

interface Props {
  onCreateHandoff: (prompt: string) => void;
}

export default function CommandBar({ onCreateHandoff }: Props) {
  const { messages, loading, send, handoff, clearHandoff } = useCommand();
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Handle handoff to create flow
  useEffect(() => {
    if (handoff) {
      onCreateHandoff(handoff.prompt);
      clearHandoff();
    }
  }, [handoff, onCreateHandoff, clearHandoff]);

  // Expand when there are messages
  useEffect(() => {
    if (messages.length > 0) {
      setExpanded(true);
    }
  }, [messages.length]);

  return (
    <div className="sticky bottom-0 border-t border-conjure-border bg-conjure-bg">
      {/* Message area */}
      {expanded && messages.length > 0 && (
        <div
          ref={scrollRef}
          className="max-h-[40vh] overflow-y-auto px-4 py-3 space-y-2"
        >
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`text-sm px-3 py-2 rounded-lg max-w-[85%] ${
                msg.role === "user"
                  ? "ml-auto bg-conjure-accent/20 text-conjure-text"
                  : "mr-auto bg-conjure-card text-conjure-text"
              }`}
            >
              {msg.content}
            </div>
          ))}
          {loading && (
            <div className="mr-auto text-sm px-3 py-2 text-conjure-muted">
              <span className="inline-block w-4 h-4 border-2 border-conjure-muted border-t-transparent rounded-full animate-spin align-middle mr-2" />
              Thinking...
            </div>
          )}
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3">
        <ChatInput
          onSend={send}
          loading={loading}
          placeholder="Ask about your apps..."
          buttonText="Ask"
        />
      </div>
    </div>
  );
}
