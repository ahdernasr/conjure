import json
import logging
from mistralai import Mistral
from ..config import settings
from .generator import (
    GENERATOR_SYSTEM_PROMPT,
    REFINER_SYSTEM_PROMPT,
    AGENTIC_GENERATOR_SYSTEM_PROMPT,
    AGENTIC_REFINER_SYSTEM_PROMPT,
    AGENTIC_TOOLS,
    create_tool_executor,
)

logger = logging.getLogger(__name__)


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

    # -- Prompt Augmentation ---------------------------------------------------

    async def augment_prompt(self, prompt: str, system_prompt: str) -> str:
        """Use Mistral Large to expand a terse prompt into a full spec.

        Falls back to the raw prompt on any failure.
        """
        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            result = response.choices[0].message.content
            if result and result.strip():
                logger.info(f"Augmented prompt ({len(result)} chars) from input ({len(prompt)} chars)")
                return result.strip()
            logger.warning("Augmentation returned empty response, using raw prompt")
            return prompt
        except Exception as e:
            logger.warning(f"Augmentation failed, using raw prompt: {e}")
            return prompt

    # -- Agentic Loop ----------------------------------------------------------

    async def run_agentic_loop(
        self,
        system_prompt: str,
        user_message: str,
        build_dir: str,
        max_turns: int = 25,
        on_progress=None,
    ) -> list[dict]:
        """Run Devstral in agentic mode with tool calls.

        Args:
            on_progress: Optional async callback(tool_name, args) called after each tool execution.
        Returns the full message history for potential follow-up (e.g. build error fixes).
        """
        tool_executor = create_tool_executor(build_dir)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for turn in range(max_turns):
            # First turn: force at least one tool call
            tool_choice = "any" if turn == 0 else "auto"

            response = await self._client.chat.complete_async(
                model=settings.DEVSTRAL_MODEL,
                messages=messages,
                tools=AGENTIC_TOOLS,
                tool_choice=tool_choice,
                temperature=0.3,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            # Build the assistant message dict for history
            assistant_dict = {"role": "assistant", "content": assistant_msg.content or ""}
            if assistant_msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            messages.append(assistant_dict)

            # If no tool calls, the model is done
            if not assistant_msg.tool_calls:
                logger.info(f"Agentic loop completed after {turn + 1} turns")
                break

            # Execute each tool call and append results
            for tc in assistant_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                logger.info(f"Tool call: {tool_name}({list(args.keys())})")
                result = tool_executor(tool_name, args)

                if on_progress:
                    await on_progress(tool_name, args)

                # Truncate very long results to avoid context overflow
                if len(result) > 10000:
                    result = result[:10000] + "\n... (truncated)"

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                    "tool_call_id": tc.id,
                })
        else:
            logger.warning(f"Agentic loop hit max turns ({max_turns})")

        return messages

    # -- Generator Agent (Agentic) ---------------------------------------------

    async def generate_app(self, prompt: str, build_dir: str, on_progress=None) -> list[dict]:
        """Run agentic generation loop. Returns message history."""
        user_message = f"Create the following app according to this specification:\n\n{prompt}"
        return await self.run_agentic_loop(
            AGENTIC_GENERATOR_SYSTEM_PROMPT,
            user_message,
            build_dir,
            on_progress=on_progress,
        )

    # -- Refiner Agent (Agentic) -----------------------------------------------

    async def refine_app(self, instruction: str, build_dir: str, on_progress=None) -> list[dict]:
        """Run agentic refinement loop. Returns message history."""
        user_message = f"Modify the existing app according to this specification:\n\n{instruction}"
        return await self.run_agentic_loop(
            AGENTIC_REFINER_SYSTEM_PROMPT,
            user_message,
            build_dir,
            on_progress=on_progress,
        )

    # -- Build Error Fix -------------------------------------------------------

    async def fix_build_error(
        self,
        error_output: str,
        build_dir: str,
        messages: list[dict],
        on_progress=None,
    ) -> list[dict]:
        """Append build error as user message and continue the agentic loop."""
        tool_executor = create_tool_executor(build_dir)

        messages.append({
            "role": "user",
            "content": (
                f"The Vite build failed with the following error:\n\n```\n{error_output}\n```\n\n"
                "Please fix the code and write the corrected files."
            ),
        })

        # Continue the agentic loop
        for turn in range(10):
            response = await self._client.chat.complete_async(
                model=settings.DEVSTRAL_MODEL,
                messages=messages,
                tools=AGENTIC_TOOLS,
                tool_choice="any" if turn == 0 else "auto",
                temperature=0.2,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            assistant_dict = {"role": "assistant", "content": assistant_msg.content or ""}
            if assistant_msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            messages.append(assistant_dict)

            if not assistant_msg.tool_calls:
                break

            for tc in assistant_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                result = tool_executor(tool_name, args)

                if on_progress:
                    await on_progress(tool_name, args)

                if len(result) > 10000:
                    result = result[:10000] + "\n... (truncated)"

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                    "tool_call_id": tc.id,
                })

        return messages

    # -- Legacy (non-agentic, for golden fallback) -----------------------------

    async def generate_app_legacy(self, prompt: str, app_id: str) -> str:
        """Send prompt to Devstral with generator system prompt (legacy HTML mode).
        Returns raw response text (HTML, possibly with markdown fences)."""
        system_prompt = GENERATOR_SYSTEM_PROMPT.replace("{{APP_ID}}", app_id)

        response = await self._client.chat.complete_async(
            model=settings.DEVSTRAL_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create this app: {prompt}"},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content

    async def refine_app_legacy(self, existing_html: str, instruction: str, app_id: str) -> str:
        """Modify existing app based on user instruction (legacy HTML mode).
        Returns raw response text (updated HTML)."""
        response = await self._client.chat.complete_async(
            model=settings.DEVSTRAL_MODEL,
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

    # -- Phase 4: Voice helpers ------------------------------------------------

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Phase 4: Audio -> text via ElevenLabs STT."""
        raise NotImplementedError("Phase 4")

    async def speak(self, text: str) -> bytes:
        """Phase 4: Text -> audio bytes via ElevenLabs TTS."""
        raise NotImplementedError("Phase 4")
