import { useState, useRef, useCallback } from "react";
import { transcribeAudio } from "../api/voice";

export type VoiceState = "idle" | "recording" | "transcribing";

export function useVoice(onTranscription: (text: string) => void) {
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());

        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setVoiceState("transcribing");

        try {
          const text = await transcribeAudio(blob);
          if (text.trim()) onTranscription(text.trim());
        } catch (err) {
          setError(err instanceof Error ? err.message : "Transcription failed");
        } finally {
          setVoiceState("idle");
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setVoiceState("recording");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Microphone access denied"
      );
      setVoiceState("idle");
    }
  }, [onTranscription]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const toggleRecording = useCallback(() => {
    if (voiceState === "idle") {
      startRecording();
    } else if (voiceState === "recording") {
      stopRecording();
    }
  }, [voiceState, startRecording, stopRecording]);

  return { voiceState, error, toggleRecording };
}
