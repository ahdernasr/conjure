"""Phase 2: App generation pipeline.

Responsibilities:
- Parse Codestral response to extract clean HTML
- Inject phone-home sync script with correct app_id
- Generate manifest.json for each app
- Generate sw.js (service worker)
- Generate schema.json from app analysis
- Write all files to apps/{uuid}/ directory
"""

# Full generator system prompt from HACKATHON_v2.md will be placed here
GENERATOR_SYSTEM_PROMPT = ""  # Phase 2


async def parse_code_response(raw_response: str) -> str:
    """Extract HTML from Mistral response (strip markdown fences, etc)."""
    raise NotImplementedError("Phase 2")


async def inject_sync_script(html: str, app_id: str) -> str:
    """Inject the phone-home sync script into generated HTML."""
    raise NotImplementedError("Phase 2")


async def write_app_files(
    app_id: str, html: str, app_name: str, theme_color: str
) -> None:
    """Write index.html, manifest.json, sw.js, schema.json to apps/{uuid}/."""
    raise NotImplementedError("Phase 2")
