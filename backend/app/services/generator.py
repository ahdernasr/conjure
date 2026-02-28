"""App generation pipeline: prompt → self-contained PWA."""

import json
import re
from pathlib import Path
from ..config import settings

GENERATOR_SYSTEM_PROMPT = """You are Conjure's app generator. You create complete, self-contained PWA applications from natural language descriptions.

OUTPUT FORMAT: You MUST output ONLY valid HTML. No markdown, no explanation, no code fences. Just the complete HTML document starting with <!DOCTYPE html>.

REQUIREMENTS FOR EVERY APP:
1. Single self-contained index.html file (CSS and JS inline, inside <style> and <script> tags)
2. Mobile-first responsive design (viewport meta, touch-friendly tap targets min 44px)
3. Dark theme: background #0a0a0a, cards #141414, text #e5e5e5, accent color chosen per app
4. Modern UI: rounded corners (border-radius: 12px), subtle borders (rgba(255,255,255,0.06)), clean typography
5. All data persisted to localStorage under key "conjure_{{APP_ID}}"
6. Expose window.__conjure = { getData(), setData(data), getSchema() }
7. Offline-capable (no external dependencies, no CDN links, no imports, inline everything)
8. The app must be FULLY FUNCTIONAL with real interactivity, not a mockup

DESIGN RULES:
- Use CSS Grid or Flexbox for layout
- Font: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
- Buttons: min-height 44px, border-radius 8px, clear active states with transform scale(0.97)
- Cards: background #141414, border 1px solid rgba(255,255,255,0.06), border-radius 12px, padding 16px
- Animations: subtle transitions (150ms ease), no jarring effects
- Numbers/stats: large font-size, font-weight bold, font-variant-numeric tabular-nums
- Full viewport height: min-height 100dvh, no scrollbar unless content overflows

INTERACTIVITY:
- All actions must work via tap (not hover-dependent)
- Real-time updates where applicable (timers tick, counters increment live)
- Use pointer events where needed
- Haptic feedback via navigator.vibrate([10]) on key actions (wrap in try/catch)

DATA CONTRACT (CRITICAL - follow exactly):
window.__conjure MUST be defined BEFORE any app logic that uses it.
- window.__conjure.getData() returns the current state as a plain JS object
- window.__conjure.setData(obj) replaces state, saves to localStorage, and updates the UI
- window.__conjure.getSchema() returns { app_id: "{{APP_ID}}", name: "APP_NAME", capabilities: [...], data_shape: {...}, actions: {...} }
- The localStorage key MUST be "conjure_{{APP_ID}}"

STRUCTURE YOUR HTML EXACTLY LIKE THIS:
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="ACCENT_COLOR">
  <title>APP_NAME</title>
  <style>
    /* ALL CSS HERE */
  </style>
</head>
<body>
  <!-- ALL HTML HERE -->
  <script>
    // 1. Define window.__conjure FIRST
    // 2. Then all app logic
  </script>
</body>
</html>

IMPORTANT: The {{APP_ID}} placeholder will be replaced with the actual UUID after generation. Use it exactly as {{APP_ID}} in your code."""


REFINER_SYSTEM_PROMPT = """You are Conjure's app refiner. You modify existing PWA applications based on user instructions.

You will receive the COMPLETE existing HTML of an app, followed by a modification request.

OUTPUT FORMAT: You MUST output ONLY the complete, modified HTML document. No markdown, no explanation, no code fences. Output the ENTIRE updated HTML starting with <!DOCTYPE html>.

RULES:
1. Preserve ALL existing functionality unless the user specifically asks to change it
2. Preserve the window.__conjure contract (getData, setData, getSchema)
3. Preserve the localStorage key
4. Preserve the data structure unless the modification requires changing it
5. Keep the same dark theme and design language
6. Make ONLY the requested changes
7. The output must be a complete, working HTML file (not a diff or partial update)"""


def parse_code_response(raw_response: str) -> str:
    """Extract HTML from Mistral response, stripping markdown fences if present."""
    text = raw_response.strip()

    # Try to extract from ```html ... ``` fences
    match = re.search(r"```html\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Try generic ``` fences
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith("<!DOCTYPE") or candidate.startswith("<html"):
            return candidate

    # If it starts with <!DOCTYPE or <html, it's already clean
    if text.startswith("<!DOCTYPE") or text.startswith("<html"):
        return text

    # Last resort: find the HTML document within the response
    match = re.search(r"(<!DOCTYPE html>.*</html>)", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # Return as-is and hope for the best
    return text


def inject_sync_script(html: str, app_id: str) -> str:
    """Inject the phone-home sync script before </body>."""
    sync_script = f"""
<script>
(function() {{
  var APP_ID = '{app_id}';
  var SYNC_URL = '/api/apps/' + APP_ID + '/sync';
  function syncToServer() {{
    try {{
      var data = window.__conjure.getData();
      navigator.sendBeacon(SYNC_URL, JSON.stringify(data));
    }} catch(e) {{}}
  }}
  var origSet = window.__conjure.setData;
  window.__conjure.setData = function(data) {{
    origSet(data);
    syncToServer();
  }};
  document.addEventListener('visibilitychange', function() {{
    if (document.visibilityState === 'hidden') syncToServer();
  }});
  window.addEventListener('beforeunload', syncToServer);
  syncToServer();
}})();
</script>"""

    # Insert before </body>
    if "</body>" in html.lower():
        idx = html.lower().rfind("</body>")
        return html[:idx] + sync_script + "\n" + html[idx:]
    else:
        return html + sync_script


def replace_app_id_placeholder(html: str, app_id: str) -> str:
    """Replace {{APP_ID}} placeholders with actual UUID."""
    return html.replace("{{APP_ID}}", app_id)


def generate_manifest(app_id: str, app_name: str, theme_color: str) -> dict:
    """Generate PWA manifest for a generated app."""
    return {
        "name": app_name,
        "short_name": app_name[:12],
        "description": f"Generated by Conjure",
        "start_url": f"/apps/{app_id}/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": theme_color,
        "icons": [
            {
                "src": f"/apps/{app_id}/icon.svg",
                "sizes": "any",
                "type": "image/svg+xml",
            }
        ],
    }


def generate_icon_svg(app_name: str, theme_color: str) -> str:
    """Generate a simple SVG icon: colored circle with first letter."""
    letter = app_name[0].upper() if app_name else "?"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="128" fill="{theme_color}"/>
  <text x="256" y="280" text-anchor="middle" font-family="system-ui,sans-serif" font-size="280" font-weight="bold" fill="white">{letter}</text>
</svg>"""


def generate_sw() -> str:
    """Generate service worker for a generated app."""
    return """const CACHE_NAME = 'conjure-app-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(clients.claim()));

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetched = fetch(event.request).then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});"""


def extract_schema(html: str, app_id: str, app_name: str) -> dict:
    """Extract a basic schema from the generated app.
    Tries to parse getSchema() from the HTML, falls back to a generic schema."""
    # Try to find getSchema definition in the code
    schema_match = re.search(
        r"getSchema\s*\(\)\s*\{?\s*return\s*(\{.*?\})\s*;?\s*\}",
        html, re.DOTALL
    )
    if schema_match:
        try:
            # This is JS, not JSON, but worth a try
            raw = schema_match.group(1)
            # Very basic JS → JSON: replace single quotes, unquoted keys
            raw = re.sub(r"(\w+)\s*:", r'"\1":', raw)
            raw = raw.replace("'", '"')
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            pass

    # Fallback: generic schema
    return {
        "app_id": app_id,
        "name": app_name,
        "capabilities": ["track_data"],
        "data_shape": {},
        "actions": {},
    }


def extract_theme_color(html: str) -> str:
    """Try to extract the theme/accent color from generated HTML."""
    # Look for theme-color meta tag
    match = re.search(r'content="(#[0-9a-fA-F]{6})"', html)
    if match:
        return match.group(1)
    return "#6366f1"


def write_app_files(app_id: str, html: str, app_name: str, theme_color: str) -> None:
    """Write all app files to apps/{uuid}/."""
    app_dir = Path(settings.APPS_DIR) / app_id
    app_dir.mkdir(parents=True, exist_ok=True)

    # index.html
    (app_dir / "index.html").write_text(html, encoding="utf-8")

    # manifest.json
    manifest = generate_manifest(app_id, app_name, theme_color)
    (app_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    # icon.svg
    icon = generate_icon_svg(app_name, theme_color)
    (app_dir / "icon.svg").write_text(icon, encoding="utf-8")

    # sw.js
    (app_dir / "sw.js").write_text(generate_sw(), encoding="utf-8")

    # schema.json
    schema = extract_schema(html, app_id, app_name)
    (app_dir / "schema.json").write_text(
        json.dumps(schema, indent=2), encoding="utf-8"
    )

    # Empty data.json
    if not (app_dir / "data.json").exists():
        (app_dir / "data.json").write_text("{}", encoding="utf-8")


def process_generated_html(raw_response: str, app_id: str) -> tuple[str, str]:
    """Full pipeline: parse → replace placeholders → inject sync → return (html, theme_color)."""
    html = parse_code_response(raw_response)
    html = replace_app_id_placeholder(html, app_id)
    theme_color = extract_theme_color(html)
    html = inject_sync_script(html, app_id)
    return html, theme_color
