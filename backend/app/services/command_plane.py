"""Phase 3: Command Plane orchestrator.

Responsibilities:
- Define function calling tools (list_apps, query_app, update_app, summarize_all)
- Execute tool calls by reading/writing app data.json files
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
            "description": "Returns all apps with their names and capability schemas",
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
            "name": "update_app",
            "description": "Modifies an app's data",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_id": {"type": "string", "description": "The app UUID to update"},
                    "action": {"type": "string", "description": "The action to perform"},
                    "params": {"type": "object", "description": "Parameters for the action"},
                },
                "required": ["app_id", "action"],
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
- list_apps(): Returns all apps with their names and capability schemas
- query_app(app_id, question): Reads an app's current data and answers questions about it
- update_app(app_id, action, params): Modifies an app's data
- summarize_all(): Aggregates data from all apps into a daily summary

BEHAVIOR:
- Keep responses SHORT and conversational (they will be spoken aloud)
- When asked to create a new app, respond with exactly: __HANDOFF_CREATE__: <description of the app the user wants>
- When asked about data, determine which app(s) to query
- For cross-app queries, pull from multiple apps and synthesize
- Always confirm actions: "Done, I've added $50 to Jake's score"
- If unsure which app, ask: "Do you mean your HIIT timer or your workout log?"
"""


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
            "update_app": self._tool_update_app,
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
        """List all apps with their schemas."""
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

    async def _tool_update_app(self, args: dict) -> str:
        """Update an app's data.json with the provided params."""
        app_id = args.get("app_id", "")
        action = args.get("action", "")
        params = args.get("params", {})

        data = await self._app_service.get_app_data(app_id)
        # Apply params as key updates
        if params:
            data.update(params)

        # Write back
        data_path = self._apps_dir / app_id / "data.json"
        data_path.write_text(json.dumps(data, indent=2))

        return json.dumps({
            "status": "updated",
            "action": action,
            "updated_keys": list(params.keys()) if params else [],
            "data": data,
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
