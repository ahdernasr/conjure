import { Card } from "@/components/ui/card";

interface Props {
  text: string;
  loading: boolean;
}

export default function ChatResponse({ text, loading }: Props) {
  return (
    <Card className="p-4">
      <p className="text-xs text-muted-foreground mb-1 font-bold" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>Conjure</p>
      <p className="text-sm whitespace-pre-wrap leading-relaxed">
        {loading ? "Thinking..." : text}
      </p>
    </Card>
  );
}
