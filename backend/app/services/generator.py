"""App generation pipeline: prompt → Vite+React PWA via agentic tool calls."""

import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from ..config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# System Prompts
# ─────────────────────────────────────────────────────────────────────────────

AGENTIC_GENERATOR_SYSTEM_PROMPT = """You are Conjure's app generator. You build complete, functional React+Tailwind apps by writing files into a Vite project.

PROJECT STRUCTURE (already set up for you):
```
index.html          — root HTML (DO NOT MODIFY)
vite.config.js      — Vite config (DO NOT MODIFY)
tailwind.config.js  — Tailwind config (DO NOT MODIFY)
postcss.config.js   — PostCSS config (DO NOT MODIFY)
package.json        — dependencies (DO NOT MODIFY)
src/
  main.jsx          — entry point with conjure contract (DO NOT MODIFY)
  index.css         — Tailwind directives + dark base (DO NOT MODIFY)
  App.jsx           — YOUR MAIN COMPONENT (overwrite this)
```

HOW DATA WORKS:
main.jsx defines `window.__conjure` with:
- `window.__conjure.getData()` — returns current state from localStorage
- `window.__conjure.setData(data)` — saves state + syncs to server
- `window.__conjure.getSchema()` — returns app capabilities schema

Use these in your components to persist and read data. Example:
```jsx
const data = window.__conjure.getData();
window.__conjure.setData({ ...data, count: data.count + 1 });
```

WHAT YOU MUST DO:
1. Write `src/App.jsx` with your complete app component (REQUIRED)
2. Write `schema.json` in the project root (REQUIRED) with format:
   {"app_id":"PLACEHOLDER_APP_ID","name":"App Name","capabilities":["..."],"data_shape":{"key":"type"},"actions":{"action":"description"}}
3. You may create additional component files in `src/` (e.g. `src/Timer.jsx`, `src/utils.js`)
4. Do NOT import external packages — only use React, react-dom, and Tailwind CSS classes

DESIGN RULES:
- Dark theme: bg-[#0a0a0a] for body, bg-[#141414] for cards, text-[#e5e5e5] for text
- Choose an accent color that fits the app (e.g. red for fitness, green for money, blue for productivity)
- Mobile-first: min tap targets 44px (min-h-[44px] min-w-[44px]), responsive layouts
- Rounded corners: rounded-xl for cards, rounded-lg for buttons
- Subtle borders: border border-white/[0.06]
- Font: system font stack (inherited from index.css)
- Numbers/stats: text-2xl font-bold tabular-nums
- Transitions: transition-transform duration-150, active:scale-[0.97] on buttons
- Full viewport height: min-h-dvh on root container

INTERACTIVITY:
- App MUST be fully functional, not a mockup
- All actions via tap (not hover-dependent)
- Real-time updates where applicable (timers, counters)
- Haptic feedback: try { navigator.vibrate([10]) } catch(e) {} on key actions
- Use React state (useState, useEffect, useRef) for UI state
- Use window.__conjure for persistent data

IMPORTANT:
- Use `write_file` tool to write each file
- Start by writing src/App.jsx, then schema.json
- Use only Tailwind CSS classes for styling (no inline styles, no CSS files except index.css)
- All components must use `export default`
- Use PLACEHOLDER_APP_ID in schema.json (will be replaced at deploy time)"""

AGENTIC_REFINER_SYSTEM_PROMPT = """You are Conjure's app refiner. You modify existing React+Tailwind apps based on user instructions.

WORKFLOW:
1. First, use `list_files` to see the project structure
2. Use `read_file` to read the existing files you need to understand
3. Use `write_file` to make your changes

RULES:
1. Preserve ALL existing functionality unless the user specifically asks to change it
2. Preserve the window.__conjure data contract (getData, setData)
3. Preserve the localStorage key pattern
4. Preserve the data structure unless the modification requires changing it
5. Keep the same dark theme and design language
6. Make ONLY the requested changes
7. Do NOT modify protected files: src/main.jsx, src/index.css, vite.config.js, package.json, tailwind.config.js, postcss.config.js, index.html
8. Update schema.json if capabilities or data shape changed

HOW DATA WORKS:
main.jsx defines `window.__conjure` with:
- `window.__conjure.getData()` — returns current state from localStorage
- `window.__conjure.setData(data)` — saves state + syncs to server
Use these in your components for persistent data."""

# ─────────────────────────────────────────────────────────────────────────────
# Tool definitions for Devstral agentic mode
# ─────────────────────────────────────────────────────────────────────────────

AGENTIC_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the project. Creates parent directories if needed. Use relative paths like 'src/App.jsx' or 'schema.json'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path (e.g. 'src/App.jsx', 'src/components/Timer.jsx', 'schema.json')"
                    },
                    "content": {
                        "type": "string",
                        "description": "The full file content to write"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file in the project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path to read (e.g. 'src/App.jsx')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the project directory (excluding node_modules).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]

# Protected files that Devstral must not overwrite
PROTECTED_FILES = {
    "src/main.jsx",
    "src/index.css",
    "vite.config.js",
    "package.json",
    "tailwind.config.js",
    "postcss.config.js",
    "index.html",
}

# ─────────────────────────────────────────────────────────────────────────────
# Tool executor
# ─────────────────────────────────────────────────────────────────────────────

def create_tool_executor(build_dir: str):
    """Return a callable (tool_name, args_dict) → result_string."""
    build_path = Path(build_dir).resolve()

    def _validate_path(rel_path: str) -> Path:
        """Validate and resolve a relative path, rejecting escapes."""
        if not rel_path or rel_path.startswith("/"):
            raise ValueError(f"Path must be relative, got: {rel_path}")
        if ".." in rel_path.split("/"):
            raise ValueError(f"Path traversal not allowed: {rel_path}")
        resolved = (build_path / rel_path).resolve()
        if not str(resolved).startswith(str(build_path)):
            raise ValueError(f"Path escapes build directory: {rel_path}")
        return resolved

    def execute(tool_name: str, args: dict) -> str:
        if tool_name == "write_file":
            rel_path = args.get("path", "")
            content = args.get("content", "")
            # Normalize path separators
            rel_path = rel_path.replace("\\", "/")
            # Check protected
            if rel_path in PROTECTED_FILES:
                return f"Error: '{rel_path}' is a protected file and cannot be modified."
            try:
                full_path = _validate_path(rel_path)
            except ValueError as e:
                return f"Error: {e}"
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return f"Wrote {len(content)} bytes to {rel_path}"

        elif tool_name == "read_file":
            rel_path = args.get("path", "").replace("\\", "/")
            try:
                full_path = _validate_path(rel_path)
            except ValueError as e:
                return f"Error: {e}"
            if not full_path.exists():
                return f"Error: File not found: {rel_path}"
            return full_path.read_text(encoding="utf-8")

        elif tool_name == "list_files":
            files = []
            for p in sorted(build_path.rglob("*")):
                if p.is_file() and "node_modules" not in p.parts:
                    files.append(str(p.relative_to(build_path)))
            return "\n".join(files) if files else "(empty project)"

        else:
            return f"Error: Unknown tool '{tool_name}'"

    return execute


# ─────────────────────────────────────────────────────────────────────────────
# Build pipeline functions
# ─────────────────────────────────────────────────────────────────────────────

def setup_build_dir(app_id: str) -> str:
    """Copy template to a temp build dir, symlink node_modules, write .env.
    Returns the build directory path."""
    template_dir = Path(settings.TEMPLATE_DIR)
    build_dir = Path(tempfile.gettempdir()) / f"build-{uuid.uuid4().hex[:8]}"

    # Copy template (skip node_modules)
    shutil.copytree(
        template_dir, build_dir,
        ignore=shutil.ignore_patterns("node_modules", "dist", ".git"),
    )

    # Symlink node_modules from template
    node_modules_src = (template_dir / "node_modules").resolve()
    node_modules_dst = build_dir / "node_modules"
    if node_modules_src.exists():
        os.symlink(str(node_modules_src), str(node_modules_dst))

    # Write .env with app ID
    (build_dir / ".env").write_text(f"VITE_APP_ID={app_id}\n", encoding="utf-8")

    return str(build_dir)


async def run_vite_build(build_dir: str) -> tuple[bool, str]:
    """Run `npx vite build` in build_dir. Returns (success, output)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "vite", "build",
            cwd=build_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "NODE_ENV": "production"},
        )
        stdout, _ = await asyncio.wait_for(
            proc.communicate(),
            timeout=settings.BUILD_TIMEOUT,
        )
        output = stdout.decode("utf-8", errors="replace")
        success = proc.returncode == 0
        return success, output
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, "Build timed out"
    except Exception as e:
        return False, f"Build error: {e}"


def deploy_build(build_dir: str, app_id: str, app_name: str, theme_color: str) -> None:
    """Copy dist/ to apps/{app_id}/, add manifest/icon/sw.js, backup source."""
    dist_dir = Path(build_dir) / "dist"
    app_dir = Path(settings.APPS_DIR) / app_id

    # Preserve existing data.json if present
    existing_data = None
    if (app_dir / "data.json").exists():
        existing_data = (app_dir / "data.json").read_bytes()

    # Copy dist to app dir (overwrite existing)
    if app_dir.exists():
        # Remove old build artifacts but preserve data.json
        for item in app_dir.iterdir():
            if item.name == "data.json":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        app_dir.mkdir(parents=True, exist_ok=True)

    # Copy dist contents
    for item in dist_dir.iterdir():
        dest = app_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # Add PWA files
    manifest = generate_manifest(app_id, app_name, theme_color)
    (app_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    icon = generate_icon_svg(app_name, theme_color)
    (app_dir / "icon.svg").write_text(icon, encoding="utf-8")

    (app_dir / "sw.js").write_text(generate_sw(), encoding="utf-8")

    # Copy schema.json from build dir, replacing PLACEHOLDER_APP_ID
    schema_src = Path(build_dir) / "schema.json"
    if schema_src.exists():
        schema_text = schema_src.read_text(encoding="utf-8")
        schema_text = schema_text.replace("PLACEHOLDER_APP_ID", app_id)
        (app_dir / "schema.json").write_text(schema_text, encoding="utf-8")
    else:
        # Fallback schema
        fallback_schema = {
            "app_id": app_id,
            "name": app_name,
            "capabilities": ["track_data"],
            "data_shape": {},
            "actions": {},
        }
        (app_dir / "schema.json").write_text(json.dumps(fallback_schema, indent=2), encoding="utf-8")

    # Restore or create data.json
    if existing_data:
        (app_dir / "data.json").write_bytes(existing_data)
    elif not (app_dir / "data.json").exists():
        (app_dir / "data.json").write_text("{}", encoding="utf-8")

    # Backup source files to _src/
    src_backup = app_dir / "_src"
    if src_backup.exists():
        shutil.rmtree(src_backup)
    src_dir = Path(build_dir) / "src"
    if src_dir.exists():
        shutil.copytree(src_dir, src_backup)
    # Also backup schema.json to _src
    if schema_src.exists():
        shutil.copy2(schema_src, src_backup / "schema.json")


def cleanup_build_dir(build_dir: str) -> None:
    """Remove the temporary build directory."""
    try:
        build_path = Path(build_dir)
        # Remove symlinked node_modules first (don't follow into real dir)
        nm = build_path / "node_modules"
        if nm.is_symlink():
            nm.unlink()
        shutil.rmtree(build_path, ignore_errors=True)
    except Exception:
        pass


async def generate_app_pipeline(client, prompt: str, app_id: str, app_name: str) -> tuple[bool, str]:
    """Full pipeline: setup → agentic gen → build+retry → deploy → cleanup.
    Returns (success, theme_color)."""
    build_dir = None
    try:
        # 1. Setup build directory
        build_dir = setup_build_dir(app_id)
        tool_executor = create_tool_executor(build_dir)

        # 2. Agentic generation
        messages = await client.generate_app(prompt, build_dir)

        # 3. Build with retries
        theme_color = _extract_theme_from_build(build_dir)
        for attempt in range(1 + settings.MAX_BUILD_RETRIES):
            success, output = await run_vite_build(build_dir)
            if success:
                logger.info(f"Build succeeded for {app_id} (attempt {attempt + 1})")
                break
            logger.warning(f"Build failed for {app_id} (attempt {attempt + 1}): {output}")
            if attempt < settings.MAX_BUILD_RETRIES:
                # Feed error back to Devstral for correction
                messages = await client.fix_build_error(output, build_dir, messages)
        else:
            # All retries exhausted
            return False, "#6366f1"

        # 4. Deploy
        deploy_build(build_dir, app_id, app_name, theme_color)
        return True, theme_color

    except Exception as e:
        logger.error(f"Pipeline failed for {app_id}: {e}")
        return False, "#6366f1"
    finally:
        if build_dir:
            cleanup_build_dir(build_dir)


async def iterate_app_pipeline(client, instruction: str, app_id: str, app_name: str) -> tuple[bool, str]:
    """Iterate pipeline: setup → restore src → agentic refine → build+retry → deploy → cleanup.
    Returns (success, theme_color)."""
    build_dir = None
    try:
        # 1. Setup build directory
        build_dir = setup_build_dir(app_id)

        # 2. Restore source from _src backup
        src_backup = Path(settings.APPS_DIR) / app_id / "_src"
        if src_backup.exists():
            build_src = Path(build_dir) / "src"
            for item in src_backup.iterdir():
                if item.name == "schema.json":
                    # Copy schema to build root
                    shutil.copy2(item, Path(build_dir) / "schema.json")
                else:
                    dest = build_src / item.name
                    if item.is_dir():
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

        # Also copy current schema.json if not already copied from _src
        existing_schema = Path(settings.APPS_DIR) / app_id / "schema.json"
        if existing_schema.exists() and not (Path(build_dir) / "schema.json").exists():
            shutil.copy2(existing_schema, Path(build_dir) / "schema.json")

        tool_executor = create_tool_executor(build_dir)

        # 3. Agentic refinement
        messages = await client.refine_app(instruction, build_dir)

        # 4. Build with retries
        theme_color = _extract_theme_from_build(build_dir)
        for attempt in range(1 + settings.MAX_BUILD_RETRIES):
            success, output = await run_vite_build(build_dir)
            if success:
                logger.info(f"Iterate build succeeded for {app_id} (attempt {attempt + 1})")
                break
            logger.warning(f"Iterate build failed for {app_id} (attempt {attempt + 1}): {output}")
            if attempt < settings.MAX_BUILD_RETRIES:
                messages = await client.fix_build_error(output, build_dir, messages)
        else:
            return False, "#6366f1"

        # 5. Deploy
        deploy_build(build_dir, app_id, app_name, theme_color)
        return True, theme_color

    except Exception as e:
        logger.error(f"Iterate pipeline failed for {app_id}: {e}")
        return False, "#6366f1"
    finally:
        if build_dir:
            cleanup_build_dir(build_dir)


def _extract_theme_from_build(build_dir: str) -> str:
    """Try to extract theme color from App.jsx or schema.json in build dir."""
    # Try schema.json first
    schema_path = Path(build_dir) / "schema.json"
    if schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            if "theme_color" in schema:
                return schema["theme_color"]
        except Exception:
            pass

    # Try to find color in App.jsx
    app_path = Path(build_dir) / "src" / "App.jsx"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        # Look for hex colors used as accent
        match = re.search(r'(?:bg-\[|text-\[|border-\[)(#[0-9a-fA-F]{6})\]', content)
        if match:
            color = match.group(1).lower()
            # Skip the default dark theme colors
            if color not in ("#0a0a0a", "#141414", "#1a1a1a", "#e5e5e5", "#737373", "#a3a3a3", "#525252", "#404040"):
                return color

    return "#6366f1"


# ─────────────────────────────────────────────────────────────────────────────
# Legacy functions (kept for golden template path)
# ─────────────────────────────────────────────────────────────────────────────

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
  var origSet = window.__conjure.setData.bind(window.__conjure);
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
    """Extract a basic schema from the generated app."""
    schema_match = re.search(
        r"getSchema\s*\(\)\s*\{?\s*return\s*(\{.*?\})\s*;?\s*\}",
        html, re.DOTALL
    )
    if schema_match:
        try:
            raw = schema_match.group(1)
            raw = re.sub(r"(\w+)\s*:", r'"\1":', raw)
            raw = raw.replace("'", '"')
            return json.loads(raw)
        except (json.JSONDecodeError, Exception):
            pass

    return {
        "app_id": app_id,
        "name": app_name,
        "capabilities": ["track_data"],
        "data_shape": {},
        "actions": {},
    }


def extract_theme_color(html: str) -> str:
    """Try to extract the theme/accent color from generated HTML."""
    match = re.search(r'content="(#[0-9a-fA-F]{6})"', html)
    if match:
        return match.group(1)
    return "#6366f1"


def write_app_files(app_id: str, html: str, app_name: str, theme_color: str) -> None:
    """Write all app files to apps/{uuid}/ (legacy golden template path)."""
    app_dir = Path(settings.APPS_DIR) / app_id
    app_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "index.html").write_text(html, encoding="utf-8")

    manifest = generate_manifest(app_id, app_name, theme_color)
    (app_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    icon = generate_icon_svg(app_name, theme_color)
    (app_dir / "icon.svg").write_text(icon, encoding="utf-8")

    (app_dir / "sw.js").write_text(generate_sw(), encoding="utf-8")

    schema = extract_schema(html, app_id, app_name)
    (app_dir / "schema.json").write_text(
        json.dumps(schema, indent=2), encoding="utf-8"
    )

    if not (app_dir / "data.json").exists():
        (app_dir / "data.json").write_text("{}", encoding="utf-8")


def process_generated_html(raw_response: str, app_id: str) -> tuple[str, str]:
    """Full pipeline: parse → replace placeholders → inject sync → return (html, theme_color)."""
    html = parse_code_response(raw_response)
    html = replace_app_id_placeholder(html, app_id)
    theme_color = extract_theme_color(html)
    html = inject_sync_script(html, app_id)
    return html, theme_color
