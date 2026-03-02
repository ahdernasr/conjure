"""Phase 3: Command Plane orchestrator.

Responsibilities:
- Define function calling tools (list_apps, query_app, execute_app_action, summarize_all)
- Execute tool calls by reading/writing app data.json files
- Use LLM to interpret schema-defined actions and mutate app data
- Agentic tool-calling loop using Mistral Large
"""

import json
import logging
from pathlib import Path
from mistralai import Mistral
from ..config import settings
from .app_service import AppService

logger = logging.getLogger(__name__)

# Tool definitions for the Command Plane agent
COMMAND_PLANE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_apps",
            "description": "Returns all apps with their names, capability schemas, and available actions",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_app",
            "description": "Reads an app's current data and answers questions about it",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "The app UUID to query"},
                    "question": {"type": "string", "description": "What to find out about the app's data"},
                },
                "required": ["app_id", "question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_app_action",
            "description": "Execute a schema-defined action on an app. Reads the app's schema.json to find the action, then applies the mutation to data.json.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "The app UUID to act on"},
                    "action_name": {"type": "string", "description": "The action name from the app's schema (e.g. add_task, mark_done)"},
                    "params": {"type": "object", "description": "Parameters for the action as defined in the schema"},
                },
                "required": ["app_id", "action_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_all",
            "description": "Aggregates data from all apps into a summary",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

COMMAND_PLANE_SYSTEM_PROMPT = """You are Conjure's Command Plane -- a voice-first AI assistant that orchestrates all of the user's generated micro-apps.

You have access to these tools:
- list_apps(): Returns all apps with their names, schemas, and available actions. ALWAYS call this first to discover app IDs and what actions are available.
- query_app(app_id, question): Reads an app's current data and answers questions about it
- execute_app_action(app_id, action_name, params): Execute a schema-defined action on an app. Use the action names and param shapes from list_apps.
- summarize_all(): Aggregates data from all apps into a daily summary

BEHAVIOR:
- Keep responses SHORT and conversational (they will be spoken aloud). Use plain text only — no markdown, no **bold**, no *italics*, no bullet points, no code fences.
- When asked to CREATE a new app, respond with exactly: __HANDOFF_CREATE__: <description of the app the user wants>
  The description must ONLY describe the app itself (features, UI, data). Do NOT mention voice, speech, microphone, or any Conjure platform features — the parent app handles those.
- When asked to MODIFY/UPDATE an existing app's code or UI (e.g. add dark mode, change layout, redesign), respond with exactly: __HANDOFF_ITERATE__:<app_id>:<description of the change>
  Example: __HANDOFF_ITERATE__:abc-123:add a dark mode toggle
  Only use this for changes that require editing the app's code/UI, NOT for data actions like adding items.
- ALWAYS call list_apps() first to discover available apps and their actions before executing anything
- When the user wants to DO something (add, remove, update, toggle), use execute_app_action with the correct action_name and params from the schema
- When the user wants to KNOW something, use query_app to read the data
- For cross-app queries, pull from multiple apps and synthesize
- Always confirm actions: "Done, I've added buy groceries to your todo list"
- If unsure which app, ask: "Do you mean your todo list or your shopping list?"
"""

MUTATION_SYSTEM_PROMPT = """You are a precise data mutation engine. Given an app's current data, a schema-defined action, and parameters, return the updated data as valid JSON.

Rules:
- Return ONLY the complete updated JSON data object, no explanation
- For add/create actions: append to the relevant array with a generated UUID for the id field
- For remove/delete actions: filter the item out of the relevant array
- For toggle/mark actions: find the item and flip the relevant boolean
- For update actions: find the item and merge the new values
- For get/list/read actions: return the data unchanged (read-only)
- Preserve all existing data that isn't being modified
- Generate UUIDs as 8-character hex strings for new item IDs"""


class CommandPlaneService:
    """Orchestrates queries across all generated apps via tool-calling loop."""

    def __init__(self, db):
        self._client = Mistral(api_key=settings.MISTRAL_API_KEY)
        self._app_service = AppService(db)
        self._apps_dir = Path(settings.APPS_DIR)

    async def process_query(
        self,
        message: str,
        conversation_history: list[dict] | None = None,
        max_turns: int = 10,
    ) -> tuple[str, list[dict]]:
        """Run the command plane tool-calling loop.

        Returns (response_text, updated_conversation_history).
        """
        if conversation_history is None:
            conversation_history = []

        # Add user message to history
        conversation_history.append({"role": "user", "content": message})

        # Build messages with system prompt prepended (not stored in history)
        messages = [
            {"role": "system", "content": COMMAND_PLANE_SYSTEM_PROMPT},
            *conversation_history,
        ]

        for turn in range(max_turns):
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=messages,
                tools=COMMAND_PLANE_TOOLS,
                tool_choice="auto",
                temperature=0.3,
            )

            choice = response.choices[0]
            assistant_msg = choice.message

            # Build assistant dict for history
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

            conversation_history.append(assistant_dict)
            messages.append(assistant_dict)

            # If no tool calls, the model is done
            if not assistant_msg.tool_calls:
                logger.info(f"Command plane completed after {turn + 1} turns")
                break

            # Execute each tool call
            for tc in assistant_msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}

                logger.info(f"Command plane tool: {tool_name}({list(args.keys())})")
                result = await self._execute_tool(tool_name, args)

                # Truncate very long results
                if len(result) > 10000:
                    result = result[:10000] + "\n... (truncated)"

                tool_msg = {
                    "role": "tool",
                    "name": tool_name,
                    "content": result,
                    "tool_call_id": tc.id,
                }
                conversation_history.append(tool_msg)
                messages.append(tool_msg)
        else:
            logger.warning(f"Command plane hit max turns ({max_turns})")

        # Extract final response text
        final_text = ""
        for msg in reversed(conversation_history):
            if msg["role"] == "assistant" and msg.get("content"):
                final_text = msg["content"]
                break

        return final_text, conversation_history

    async def _execute_tool(self, tool_name: str, args: dict) -> str:
        """Route tool calls to the appropriate handler."""
        handlers = {
            "list_apps": self._tool_list_apps,
            "query_app": self._tool_query_app,
            "execute_app_action": self._tool_execute_app_action,
            "summarize_all": self._tool_summarize_all,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            return await handler(args)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            return json.dumps({"error": str(e)})

    async def _tool_list_apps(self, _args: dict) -> str:
        """List all apps with their schemas and available actions."""
        apps = await self._app_service.list_apps()
        result = []
        for app in apps:
            entry = {
                "id": app["id"],
                "name": app["name"],
                "description": app.get("description", ""),
            }
            schema = self._load_schema(app["id"])
            if schema:
                entry["schema"] = schema
            result.append(entry)
        return json.dumps(result, indent=2)

    async def _tool_query_app(self, args: dict) -> str:
        """Load an app's data and schema for querying."""
        app_id = args.get("app_id", "")
        question = args.get("question", "")
        data = await self._app_service.get_app_data(app_id)
        schema = self._load_schema(app_id)
        app = await self._app_service.get_app(app_id)
        return json.dumps({
            "app_name": app["name"] if app else "Unknown",
            "question": question,
            "schema": schema,
            "data": data,
        }, indent=2)

    async def _tool_execute_app_action(self, args: dict) -> str:
        """Execute a schema-defined action on an app using LLM-based mutation."""
        app_id = args.get("app_id", "")
        action_name = args.get("action_name", "")
        params = args.get("params", {})

        # Load schema and validate action exists
        schema = self._load_schema(app_id)
        if not schema:
            return json.dumps({"error": f"No schema found for app {app_id}"})

        actions = schema.get("actions", {})
        action_def = actions.get(action_name)
        if not action_def:
            available = list(actions.keys())
            return json.dumps({
                "error": f"Unknown action '{action_name}'. Available actions: {available}"
            })

        # Normalize old-style string action defs to new format
        if isinstance(action_def, str):
            action_def = {"params": {}, "description": action_def}

        # Load current data
        data = await self._app_service.get_app_data(app_id)

        # Use LLM to compute the mutation
        mutation_prompt = (
            f"App schema:\n{json.dumps(schema, indent=2)}\n\n"
            f"Current data:\n{json.dumps(data, indent=2)}\n\n"
            f"Action to execute: {action_name}\n"
            f"Action definition: {json.dumps(action_def)}\n"
            f"Parameters: {json.dumps(params)}\n\n"
            f"Return the complete updated data JSON object after applying this action."
        )

        try:
            response = await self._client.chat.complete_async(
                model=settings.MISTRAL_LARGE_MODEL,
                messages=[
                    {"role": "system", "content": MUTATION_SYSTEM_PROMPT},
                    {"role": "user", "content": mutation_prompt},
                ],
                temperature=0.1,
            )
            raw_result = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            if raw_result.startswith("```"):
                lines = raw_result.split("\n")
                lines = lines[1:]  # remove opening fence
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_result = "\n".join(lines)

            updated_data = json.loads(raw_result)
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Mutation LLM failed for {action_name}: {e}")
            return json.dumps({"error": f"Failed to execute action: {e}"})

        # Write updated data back
        data_path = self._apps_dir / app_id / "data.json"
        data_path.write_text(json.dumps(updated_data, indent=2))

        return json.dumps({
            "status": "success",
            "action": action_name,
            "params": params,
            "updated_data": updated_data,
        }, indent=2)

    async def _tool_summarize_all(self, _args: dict) -> str:
        """Load all apps' data and schemas for aggregation."""
        apps = await self._app_service.list_apps()
        result = []
        for app in apps:
            entry = {
                "id": app["id"],
                "name": app["name"],
                "description": app.get("description", ""),
            }
            schema = self._load_schema(app["id"])
            if schema:
                entry["schema"] = schema
            data = await self._app_service.get_app_data(app["id"])
            if data:
                entry["data"] = data
            result.append(entry)
        return json.dumps(result, indent=2)

    def _load_schema(self, app_id: str) -> dict | None:
        """Read schema.json for an app, return None if missing."""
        schema_path = self._apps_dir / app_id / "schema.json"
        if not schema_path.exists():
            return None
        try:
            return json.loads(schema_path.read_text())
        except (json.JSONDecodeError, OSError):
            return None
