from mistralai import Mistral
from ..config import settings
from .generator import GENERATOR_SYSTEM_PROMPT, REFINER_SYSTEM_PROMPT


class MistralClientWrapper:
    """Wraps the Mistral SDK."""

    def __init__(self):
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)

    # -- Simple Chat -----------------------------------------------------------

    async def chat(self, message: str, model: str | None = None) -> str:
        """Send a message, get a text response."""
        response = await self._client.chat.complete_async(
            model=model or settings.MISTRAL_LARGE_MODEL,
            messages=[{"role": "user", "content": message}],
        )
        return response.choices[0].message.content

    # -- Generator Agent -------------------------------------------------------

    async def generate_app(self, prompt: str, app_id: str) -> str:
        """Send prompt to Codestral with generator system prompt.
        Returns raw response text (HTML, possibly with markdown fences)."""
        system_prompt = GENERATOR_SYSTEM_PROMPT.replace("{{APP_ID}}", app_id)

        response = await self._client.chat.complete_async(
            model=settings.CODESTRAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create this app: {prompt}"},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    # -- Refiner Agent ---------------------------------------------------------

    async def refine_app(self, existing_html: str, instruction: str, app_id: str) -> str:
        """Modify existing app based on user instruction.
        Returns raw response text (updated HTML)."""
        response = await self._client.chat.complete_async(
            model=settings.CODESTRAL_MODEL,
            messages=[
                {"role": "system", "content": REFINER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Here is the existing app HTML:\n\n{existing_html}\n\nModification requested: {instruction}",
                },
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    # -- Phase 3: Command Plane Agent ------------------------------------------

    async def command_query(self, message: str, conversation_id: str | None = None) -> tuple[str, str]:
        """Phase 3: Send query to Command Plane, handle tool calls."""
        raise NotImplementedError("Phase 3")

    # -- Phase 4: Voice helpers ------------------------------------------------

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Phase 4: Audio -> text via ElevenLabs STT."""
        raise NotImplementedError("Phase 4")

    async def speak(self, text: str) -> bytes:
        """Phase 4: Text -> audio bytes via ElevenLabs TTS."""
        raise NotImplementedError("Phase 4")
