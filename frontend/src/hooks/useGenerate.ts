import { useState, useCallback } from "react";
import { generateApp, iterateApp } from "@/api/generate";

type Status = "idle" | "generating" | "done" | "error";

export function useGenerate(onAppCreated: () => void) {
  const [status, setStatus] = useState<Status>("idle");
  const [generatedAppId, setGeneratedAppId] = useState<string | null>(null);
  const [generatedAppName, setGeneratedAppName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [traceMessages, setTraceMessages] = useState<string[]>([]);

  const onTrace = useCallback((message: string) => {
    setTraceMessages((prev) => [...prev, message]);
  }, []);

  const generate = async (prompt: string) => {
    setStatus("generating");
    setError(null);
    setGeneratedAppId(null);
    setTraceMessages([]);
    try {
      const result = await generateApp(prompt, onTrace);
      setGeneratedAppId(result.id);
      setGeneratedAppName(result.name);
      setStatus("done");
      onAppCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
      setStatus("error");
    }
  };

  const iterate = async (appId: string, instruction: string) => {
    setStatus("generating");
    setError(null);
    setTraceMessages([]);
    try {
      const result = await iterateApp(appId, instruction, onTrace);
      setGeneratedAppId(result.id);
      setGeneratedAppName(result.name);
      setStatus("done");
      onAppCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refinement failed");
      setStatus("error");
    }
  };

  const dismiss = () => {
    setStatus("idle");
    setGeneratedAppId(null);
    setGeneratedAppName(null);
    setError(null);
    setTraceMessages([]);
  };

  return { status, generatedAppId, generatedAppName, error, traceMessages, generate, iterate, dismiss };
}
