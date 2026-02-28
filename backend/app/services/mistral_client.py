from mistralai import Mistral
from ..config import settings


class MistralClientWrapper:
    """Wraps the Mistral SDK. Phase 1: chat only. Phase 2+: agents."""

    def __init__(self):
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)

    # -- Phase 1: Simple Chat --------------------------------------------------

    async def chat(self, message: str, model: str | None = None) -> str:
        """Send a message, get a text response."""
        response = await self._client.chat.complete_async(
            model=model or settings.MISTRAL_LARGE_MODEL,
            messages=[{"role": "user", "content": message}],
        )
        return response.choices[0].message.content

    # -- Phase 2: Generator Agent ----------------------------------------------

    async def generate_app(self, prompt: str, app_id: str) -> str:
        """Phase 2: Send prompt to Codestral with generator system prompt.
        Returns raw HTML string of the generated app.

        Will:
        1. Build messages with GENERATOR_SYSTEM_PROMPT
        2. Call chat.complete_async with codestral model
        3. Parse response to extract HTML
        4. Inject phone-home sync script with app_id
        """
        raise NotImplementedError("Phase 2")

    async def refine_app(self, existing_html: str, instruction: str, app_id: str) -> str:
        """Phase 2: Modify existing app based on user instruction.

        Will:
        1. Build messages with existing code + modification request
        2. Call Codestral with refiner system prompt
        3. Return updated HTML
        """
        raise NotImplementedError("Phase 2")

    # -- Phase 3: Command Plane Agent ------------------------------------------

    async def command_query(self, message: str, conversation_id: str | None = None) -> tuple[str, str]:
        """Phase 3: Send query to Command Plane, handle tool calls.
        Returns (response_text, conversation_id).

        Will use Mistral Agents API with function calling tools:
        - list_apps, query_app, update_app, summarize_all
        """
        raise NotImplementedError("Phase 3")

    # -- Phase 4: Voice helpers ------------------------------------------------

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Phase 4: Audio -> text via ElevenLabs STT."""
        raise NotImplementedError("Phase 4")

    async def speak(self, text: str) -> bytes:
        """Phase 4: Text -> audio bytes via ElevenLabs TTS."""
        raise NotImplementedError("Phase 4")
