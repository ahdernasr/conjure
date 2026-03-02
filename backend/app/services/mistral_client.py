import json
import logging
import re
from pathlib import Path
from mistralai import Mistral
from ..config import settings
from .generator import (
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

    # -- App Name Generation ---------------------------------------------------

    async def generate_app_name(self, prompt: str) -> str:
        """Generate a short, catchy app name from a user prompt.

        Uses a lightweight call with minimal tokens. Returns 1-3 word name.
        Falls back to first few words of the prompt on failure.
        """
        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Generate a plain, descriptive name (2-4 words) for the described app. "
                            "It should describe what the app does, NOT be a catchy brand name. "
                            "Reply with ONLY the name, nothing else. No quotes, no punctuation, no explanation. "
                            "Good examples: 'HIIT Timer', 'Poker Scoreboard', 'Water Tracker', 'Packing Checklist', 'Habit Tracker' "
                            "Bad examples: 'PokerPal', 'HydroFlow', 'PackMate', 'FitPulse' — never use these mashup brand names."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
                max_tokens=15,
            )
            name = response.choices[0].message.content.strip().strip('"\'')
            if name and len(name) <= 30:
                return name
        except Exception as e:
            logger.warning(f"App name generation failed: {e}")
        # Fallback: first 3 words of the prompt
        words = prompt.strip().split()[:3]
        return " ".join(words)[:30]

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

    # -- Intent Classification -------------------------------------------------

    async def classify_intent(self, message: str) -> str:
        """Classify whether a user message is a code change request or a question.

        Returns "code_change" or "text_response". Falls back to "code_change" on failure.
        """
        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the user message as either CODE (they want to change/add/remove/fix something in the app) "
                            "or CHAT (they are asking a question, requesting an explanation, or making conversation). "
                            "Reply with exactly one word: CODE or CHAT"
                        ),
                    },
                    {"role": "user", "content": message},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            result = response.choices[0].message.content.strip().upper()
            if "CHAT" in result:
                return "text_response"
            return "code_change"
        except Exception as e:
            logger.warning(f"Intent classification failed, defaulting to code_change: {e}")
            return "code_change"

    # -- Question Answering ----------------------------------------------------

    async def answer_question(self, question: str, app_id: str) -> str:
        """Answer a question about the user's app using its source code as context.

        Returns a concise 2-4 sentence answer.
        """
        try:
            app_dir = Path(settings.APPS_DIR) / app_id / "_src"
            context_parts = []

            app_jsx = app_dir / "App.jsx"
            if app_jsx.exists():
                context_parts.append(f"src/App.jsx:\n```jsx\n{app_jsx.read_text(encoding='utf-8')}\n```")

            schema_file = app_dir / "schema.json"
            if schema_file.exists():
                context_parts.append(f"schema.json:\n```json\n{schema_file.read_text(encoding='utf-8')}\n```")

            context = "\n\n".join(context_parts) if context_parts else "No source code available."

            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant for Conjure, a platform that builds small React+Tailwind phone apps. "
                            "The user is asking about their app. Answer concisely in 2-4 sentences based on the app's source code below. "
                            "Use plain text only — no markdown, no **bold**, no *italics*, no bullet points, no code fences.\n\n"
                            f"{context}"
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                temperature=0.3,
                max_tokens=300,
            )
            result = response.choices[0].message.content
            if result and result.strip():
                return result.strip()
            return "I couldn't find a clear answer. Try rephrasing your question or describe a change you'd like to make."
        except Exception as e:
            logger.warning(f"Question answering failed: {e}")
            return "I had trouble reading the app's code. Try asking again or describe a change you'd like to make."

    # -- Change Summary --------------------------------------------------------

    async def summarize_changes(self, instruction: str) -> str:
        """Generate a short, past-tense summary of what was changed.

        Returns a 1-sentence confirmation like "Added a delete button to each item".
        Falls back to a generic confirmation on failure.
        """
        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "The user asked for a change to their app and it was successfully applied. "
                            "Write a single short sentence (under 12 words) confirming what was done, in past tense. "
                            "Do NOT use quotes. Do NOT start with 'I'. Start with a past-tense verb like 'Added', 'Updated', 'Changed', 'Removed'. "
                            "Use plain text only — no markdown formatting."
                        ),
                    },
                    {"role": "user", "content": instruction},
                ],
                temperature=0.2,
                max_tokens=40,
            )
            result = response.choices[0].message.content.strip()
            if result:
                return result
        except Exception as e:
            logger.warning(f"Change summary failed: {e}")
        return "Changes applied successfully"

    # -- Generation Verification -----------------------------------------------

    async def verify_generation(self, prompt: str, code: str) -> tuple[bool, str]:
        """Check whether generated App.jsx actually implements the user's request.

        Returns (passed, reason). Uses Mistral Large for fast judgement.
        """
        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a code reviewer. The user asked for an app and a model generated React code. "
                            "Determine if the generated code is a real implementation of what was requested, "
                            "or if it is a placeholder, skeleton, empty shell, or completely unrelated. "
                            "A real implementation has state management, UI components, and interactivity matching the request. "
                            "A placeholder just shows static text like 'Hello' or 'App' with no real functionality. "
                            "Reply with exactly PASS or FAIL followed by a short reason (under 15 words). "
                            "Example: PASS - implements water tracking with daily goal and history. "
                            "Example: FAIL - just a placeholder div with no actual functionality."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"USER REQUEST:\n{prompt[:500]}\n\nGENERATED CODE:\n{code[:6000]}",
                    },
                ],
                temperature=0.0,
                max_tokens=50,
            )
            result = response.choices[0].message.content.strip()
            if result.upper().startswith("PASS"):
                return True, result
            return False, result
        except Exception as e:
            logger.warning(f"Generation verification failed, assuming pass: {e}")
            return True, "verification error, assuming pass"

    async def verify_iteration(self, instruction: str, code_before: str, code_after: str) -> tuple[bool, str]:
        """Check whether a code iteration actually applied the requested changes.

        Returns (passed, reason). Compares before/after code against the instruction.
        """
        try:
            # Truncate to fit context
            before_snippet = code_before[:3000]
            after_snippet = code_after[:3000]

            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a code reviewer. The user requested changes to their React app. "
                            "You will see the BEFORE code, the AFTER code, and what the user asked for. "
                            "Determine if the AFTER code actually implements ALL the requested changes. "
                            "Check each part of the request individually. If any part is missing, FAIL. "
                            "Reply with exactly PASS or FAIL followed by a short reason (under 20 words). "
                            "Example: PASS - added green highlight to current match and score display per set. "
                            "Example: FAIL - only added scores, did not highlight current match in green."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"USER REQUEST:\n{instruction[:500]}\n\n"
                            f"BEFORE CODE:\n{before_snippet}\n\n"
                            f"AFTER CODE:\n{after_snippet}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=50,
            )
            result = response.choices[0].message.content.strip()
            if result.upper().startswith("PASS"):
                return True, result
            return False, result
        except Exception as e:
            logger.warning(f"Iteration verification failed, assuming pass: {e}")
            return True, "verification error, assuming pass"

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
            # First turn: use "auto" so model can output planning text before tool calls
            tool_choice = "auto"

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
                if len(result) > 20000:
                    result = result[:20000] + "\n... (truncated)"

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
        user_message = (
            f"Build this app:\n\n{prompt}\n\n"
            "Plan briefly, then write the files:\n"
            "1. State variables and data shape for window.__conjure\n"
            "2. Which shadcn components to use\n"
            "3. Layout structure for the 390x844px phone screen\n\n"
            "Then call write_file(\"src/App.jsx\", ...) with the COMPLETE app code, "
            "followed by write_file(\"schema.json\", ...). "
            "Do NOT leave any placeholder or TODO — write the full working implementation."
        )
        return await self.run_agentic_loop(
            AGENTIC_GENERATOR_SYSTEM_PROMPT,
            user_message,
            build_dir,
            on_progress=on_progress,
        )

    # -- Refiner Agent (Agentic) -----------------------------------------------

    async def refine_app(
        self,
        instruction: str,
        build_dir: str,
        on_progress=None,
        raw_instruction: str = "",
        chat_history: list[dict] | None = None,
    ) -> list[dict]:
        """Run agentic refinement loop. Returns message history."""
        parts = []

        # Include recent conversation for context on follow-ups
        if chat_history:
            parts.append("--- CONVERSATION HISTORY (context only) ---")
            for msg in chat_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                parts.append(f"{role}: {msg['content']}")
            parts.append("--- END HISTORY ---\n")

        # Pre-load current code so the refiner has it immediately (saves 2-3 tool call turns)
        build_path = Path(build_dir)
        app_jsx_path = build_path / "src" / "App.jsx"
        schema_path = build_path / "schema.json"
        if app_jsx_path.exists():
            app_code = app_jsx_path.read_text(encoding="utf-8")
            parts.append(f"CURRENT src/App.jsx:\n```jsx\n{app_code}\n```\n")
        if schema_path.exists():
            schema_code = schema_path.read_text(encoding="utf-8")
            parts.append(f"CURRENT schema.json:\n```json\n{schema_code}\n```\n")

        parts.append("Modify the existing app according to this specification:\n")

        # Include raw instruction so the refiner sees exactly what the user typed
        if raw_instruction and raw_instruction != instruction:
            parts.append(f"USER'S EXACT REQUEST: {raw_instruction}\n")
            parts.append(f"EXPANDED SPECIFICATION:\n{instruction}")
        else:
            parts.append(instruction)

        parts.append(
            "\n\nIMPORTANT: Apply ALL of the requested changes, not just some. "
            "If the request has multiple parts, implement every single one.\n\n"
            "Steps:\n"
            "1. Read current src/App.jsx and schema.json\n"
            "2. Identify every change the user asked for\n"
            "3. Rewrite src/App.jsx with ALL changes applied\n"
            "4. Update schema.json if data shape or actions changed\n"
            "5. Run validate_jsx and check_imports\n\n"
            "Call write_file to save your changes. Do NOT just plan — actually write the modified code."
        )

        user_message = "\n".join(parts)
        return await self.run_agentic_loop(
            AGENTIC_REFINER_SYSTEM_PROMPT,
            user_message,
            build_dir,
            on_progress=on_progress,
        )

    # -- Build Error Fix -------------------------------------------------------

    @staticmethod
    def _clean_build_errors(error_output: str) -> str:
        """Pre-process Vite build output to extract relevant error lines."""
        error_keywords = {"error", "Error", "ERROR", "failed", "Failed", "Cannot", "cannot",
                          "not found", "unexpected", "Unexpected", "SyntaxError", "TypeError",
                          "ReferenceError", "is not defined", "is not a function", "Module",
                          "resolve", "ENOENT"}
        lines = error_output.splitlines()
        relevant = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if any(kw in stripped for kw in error_keywords):
                # Strip temp directory paths for clarity
                cleaned = re.sub(r'/tmp/build-[a-f0-9]+/', './', stripped)
                cleaned = re.sub(r'/var/folders/[^\s]+/build-[a-f0-9]+/', './', cleaned)
                relevant.append(cleaned)
        # Limit to 10 most relevant lines
        if not relevant:
            relevant = lines[:10]  # fallback: first 10 lines
        return "\n".join(relevant[:10])

    async def fix_build_error(
        self,
        error_output: str,
        build_dir: str,
        messages: list[dict],
        on_progress=None,
    ) -> list[dict]:
        """Append build error as user message and continue the agentic loop."""
        tool_executor = create_tool_executor(build_dir)
        cleaned_errors = self._clean_build_errors(error_output)

        messages.append({
            "role": "user",
            "content": (
                f"The Vite build failed with the following error:\n\n```\n{cleaned_errors}\n```\n\n"
                "Please fix the code and write the corrected files. "
                "After fixing, run validate_jsx on the changed files to verify."
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

                if len(result) > 20000:
                    result = result[:20000] + "\n... (truncated)"

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                    "tool_call_id": tc.id,
                })

        return messages

    # -- Phase 4: Voice helpers ------------------------------------------------

    async def transcribe(self, audio_bytes: bytes) -> str:
        """Phase 4: Audio -> text via ElevenLabs STT."""
        raise NotImplementedError("Phase 4")

    async def speak(self, text: str) -> bytes:
        """Phase 4: Text -> audio bytes via ElevenLabs TTS."""
        raise NotImplementedError("Phase 4")
