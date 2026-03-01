const BASE_URL = "/api";

export async function transcribeAudio(audio: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("audio", audio, "recording.webm");

  const resp = await fetch(`${BASE_URL}/voice/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "Transcription failed" }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  const data = await resp.json();
  return data.text;
}

export async function textToSpeech(text: string): Promise<Blob> {
  const resp = await fetch(`${BASE_URL}/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: "TTS failed" }));
    throw new Error(err.detail || `HTTP ${resp.status}`);
  }

  return resp.blob();
}
