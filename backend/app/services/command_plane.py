"""Phase 3: Command Plane orchestrator.

Responsibilities:
- Define function calling tools (list_apps, query_app, update_app, summarize_all)
- Execute tool calls by reading/writing app data.json files
- Manage persistent conversations via Conversations API
"""

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

COMMAND_PLANE_SYSTEM_PROMPT = ""  # Phase 3: from HACKATHON_v2.md
