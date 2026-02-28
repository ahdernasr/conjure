interface Props {
  text: string;
  loading: boolean;
}

export default function ChatResponse({ text, loading }: Props) {
  return (
    <div className="bg-conjure-card border border-conjure-border rounded-xl p-4">
      <p className="text-xs text-conjure-muted mb-1">Conjure</p>
      <p className="text-sm whitespace-pre-wrap leading-relaxed">
        {loading ? "Thinking..." : text}
      </p>
    </div>
  );
}
