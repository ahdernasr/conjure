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
# Shared prompt building blocks (composed into both generator & refiner)
# ─────────────────────────────────────────────────────────────────────────────

_PROJECT_STRUCTURE = """PROJECT STRUCTURE (already set up for you):
```
index.html          — root HTML (DO NOT MODIFY)
vite.config.js      — Vite config (DO NOT MODIFY)
tailwind.config.js  — Tailwind config with shadcn theme (DO NOT MODIFY)
postcss.config.js   — PostCSS config (DO NOT MODIFY)
package.json        — dependencies (DO NOT MODIFY)
src/
  main.jsx          — entry point with conjure contract (DO NOT MODIFY)
  index.css         — Tailwind directives + CSS variables (DO NOT MODIFY)
  App.jsx           — YOUR MAIN COMPONENT (overwrite this)
  lib/
    utils.js        — cn() utility (DO NOT MODIFY)
  components/ui/    — Pre-built shadcn components (DO NOT MODIFY)
    button.jsx      — Button (variant: default|destructive|outline|secondary|ghost|link, size: default|sm|lg|icon)
    card.jsx        — Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
    badge.jsx       — Badge (variant: default|secondary|destructive|outline)
    input.jsx       — Input
    progress.jsx    — Progress (value: 0-100)
    tabs.jsx        — Tabs, TabsList, TabsTrigger, TabsContent
    separator.jsx   — Separator (orientation: horizontal|vertical)
    switch.jsx      — Switch (checked, onCheckedChange)
    dialog.jsx      — Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
```"""

_AVAILABLE_IMPORTS = """AVAILABLE IMPORTS (use ONLY these — no other external packages):
- react, react-dom
- lucide-react (icons: e.g. Plus, Trash2, Check, X, ChevronRight, ArrowLeft, Loader2, etc.)
- Components from ./components/ui/ (e.g. import { Button } from "./components/ui/button")
- cn() from ./lib/utils (e.g. import { cn } from "./lib/utils")"""

_DATA_PATTERN = """HOW DATA WORKS:
main.jsx defines `window.__conjure` with:
- `window.__conjure.getData()` — returns current state from localStorage
- `window.__conjure.setData(data)` — saves state + syncs to server
- `window.__conjure.getSchema()` — returns app capabilities schema

Use these in your components to persist and read data.

WARNING: setData() REPLACES ALL stored data. Always include ALL data keys in every setData() call. If your app has `items` and `filter`, calling setData({ items }) will erase `filter`.

CANONICAL DATA LOADING PATTERN (use this in every app):
```jsx
// Use ONE combined state object so setData always writes ALL keys
const [state, setState] = useState(() => {
  const data = window.__conjure.getData()
  return { items: data.items ?? [], filter: data.filter ?? "all" }
})

// ONE useEffect syncs the entire state — no data loss
useEffect(() => {
  window.__conjure.setData(state)
}, [state])

// Update individual fields by spreading previous state
const addItem = (item) => setState(prev => ({ ...prev, items: [...prev.items, item] }))
const setFilter = (f) => setState(prev => ({ ...prev, filter: f }))
```
Use ONE useState with a combined object + ONE useEffect to sync. Update fields via setState(prev => ({ ...prev, key: newValue })). This prevents multiple useEffects from overwriting each other."""

_DESIGN_RULES = """DESIGN RULES:
- Use CSS variable classes: bg-background, text-foreground, bg-card, text-card-foreground, bg-primary, text-primary-foreground, bg-secondary, text-secondary-foreground, text-muted-foreground, bg-muted, border-border, bg-destructive
- Do NOT use hardcoded hex colors. Use the CSS variable classes above.
- To set a custom accent color, override --primary in a <style> tag: :root { --primary: 142 71% 45%; } (HSL values without commas)
- CRITICAL: Do NOT render an app name, title header, logo, or any branding in the UI. No "FocusPulse" header, no app logo, no settings icon in a top bar. These are mini utility apps — the very first thing the user sees should be the core functionality (e.g. the timer itself, the list itself, the scoreboard itself). Jump straight into it.
- PHONE VIEWPORT (390×844px frame — STRICT RULES):
  - Root container: min-h-dvh flex flex-col
  - Main content area: flex-1 (never explicit heights like h-screen or h-[600px])
  - Horizontal padding: px-4, section spacing: py-3
  - Use full 390px width — do NOT add max-w-sm, max-w-md, or other inner width constraints
  - Scrollable lists: put overflow-y-auto on the list container, NOT the whole page
  - Bottom actions: use mt-auto or shrink-0 at end of flex column
  - No position: fixed — it breaks inside the iframe preview
  - Max 2 columns for cards/items, max 4 columns for icon buttons
  - Font sizes: headings text-xl, body text-sm, labels/captions text-xs
  - No decorative elements larger than 120px
  - Keep layouts compact and dense — no large empty gaps
- Min tap targets 44px (min-h-[44px] min-w-[44px])
- Use shadcn components: Button for actions, Card for containers, Badge for status, Input for text fields, Progress for bars, Tabs for sections, Switch for toggles, Dialog for modals
- Numbers/stats: text-2xl font-bold tabular-nums
- Transitions: transition-transform duration-150, active:scale-[0.97] on buttons
- Full viewport height: min-h-dvh on root container, use flex column layout to distribute space evenly — do NOT rely on large fixed margins or padding
- Primary-foreground contrast: When overriding --primary, also override --primary-foreground for contrast. Bright accents (yellow, lime, cyan) → use black text (`--primary-foreground: 0 0% 0%`). Dark accents (navy, purple, dark green) → use white text (`--primary-foreground: 0 0% 100%`).
- The default theme is LIGHT. No dark mode class variant exists. Do not add `dark:` Tailwind variants.
- Scroll handling: The iframe is 844px tall. Design so the root container fits in 844px. Scrollable regions (long lists, feeds) go inside a flex-1 area with `overflow-y-auto`, not on the whole page.
- Text overflow: Truncate long text with `truncate` (single line) or `line-clamp-2` / `line-clamp-3` (multi-line). Never allow horizontal scroll.
- Empty states: Always show a friendly empty state message when lists are empty (e.g. "No items yet — tap + to add one")."""

_COMPONENT_USAGE = """COMPONENT USAGE EXAMPLES:
```jsx
import { Button } from "./components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "./components/ui/card"
import { Badge } from "./components/ui/badge"
import { Input } from "./components/ui/input"
import { Progress } from "./components/ui/progress"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
import { Switch } from "./components/ui/switch"
import { Separator } from "./components/ui/separator"
import { cn } from "./lib/utils"
import { Plus, Trash2, Check } from "lucide-react"

<Button variant="outline" size="sm" onClick={handleClick}><Plus className="w-4 h-4 mr-2" />Add</Button>
<Card><CardHeader><CardTitle>Title</CardTitle></CardHeader><CardContent>...</CardContent></Card>
<Badge variant="secondary">Active</Badge>
<Input placeholder="Enter value..." value={val} onChange={e => setVal(e.target.value)} />
<Progress value={75} />
<Switch checked={on} onCheckedChange={setOn} />
```"""

_DO_NOT_RULES = """DO NOT (common mistakes that break builds):
- Do NOT import from "react/jsx-runtime" — Vite handles JSX transform automatically
- Do NOT use TypeScript syntax — no .tsx files, no type annotations, no interfaces, no `as` casts. This is a .jsx project.
- Do NOT use require() — this is an ESM project, use import only
- Do NOT use `export const App` or named exports for the main component — MUST be `export default function App()`
- Do NOT use @/ path aliases — use relative paths like ./components/ui/button
- Do NOT use React.lazy() or dynamic import() — everything is bundled together
- Do NOT use "use client" or "use server" directives — this is NOT Next.js
- Do NOT use position: fixed — it breaks inside the iframe preview. Use flex layout with mt-auto for bottom elements.
- Do NOT use window.location or window.history for navigation — these are single-screen utility apps
- Do NOT import React itself (e.g. `import React from "react"`) — only import hooks and functions you actually use: `import { useState, useEffect } from "react"`
- Do NOT use className on React fragments (<> or <React.Fragment>) — fragments don't accept props
- Do NOT import from `@radix-ui/*` directly — use the shadcn wrappers in `./components/ui/` (e.g. use `./components/ui/dialog` not `@radix-ui/react-dialog`)
- Do NOT use `onChange` on Switch (use `onCheckedChange`) or on Tabs (use `onValueChange`) — these are Radix-based components with different event APIs
- Do NOT invent lucide-react icon names — only use these known icons: Plus, Minus, X, Check, ChevronRight, ChevronLeft, ChevronDown, ChevronUp, ArrowLeft, ArrowRight, Trash2, Edit, Search, Settings, Star, Heart, Home, User, Bell, Calendar, Clock, Filter, MoreHorizontal, MoreVertical, Loader2, RotateCcw, Share, Download, Upload, Eye, EyeOff, Copy, Sparkles
- Do NOT call hooks (useState, useEffect, useRef, useMemo, useCallback) inside conditionals, loops, or callbacks — hooks must be at the top level of the component function
- Do NOT render list `.map()` items without a unique `key` prop — always add key={item.id} or key={index} as last resort
- Do NOT use inline `style={{}}` for layout — use Tailwind classes. Inline styles are ONLY acceptable inside `<style>` tags for CSS variable overrides (e.g. `:root { --primary: ... }`)
- Do NOT add voice input, speech recognition, microphone buttons, text-to-speech, or any voice/speech features — the parent platform handles all voice interactions"""

_COMMON_PATTERNS = """COMMON PATTERNS (use these instead of reinventing):

Form submit + clear input:
```jsx
const [input, setInput] = useState("")
const handleAdd = () => {
  if (!input.trim()) return
  setState(prev => ({ ...prev, items: [...prev.items, { id: crypto.randomUUID(), text: input.trim() }] }))
  setInput("")
}
<div className="flex gap-2">
  <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleAdd()} placeholder="Add item..." />
  <Button onClick={handleAdd} size="icon"><Plus className="w-4 h-4" /></Button>
</div>
```

Unique ID generation — use `crypto.randomUUID()`. Do NOT import uuid or nanoid.

Date formatting — use `new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(date)` or `date.toLocaleDateString()`. Do NOT import date-fns, moment, or dayjs.

Delete with confirmation — use Dialog component:
```jsx
const [deleteId, setDeleteId] = useState(null)
<Dialog open={deleteId !== null} onOpenChange={(open) => !open && setDeleteId(null)}>
  <DialogContent>
    <DialogHeader><DialogTitle>Delete this item?</DialogTitle></DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setDeleteId(null)}>Cancel</Button>
      <Button variant="destructive" onClick={() => { handleDelete(deleteId); setDeleteId(null) }}>Delete</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```"""

# ─────────────────────────────────────────────────────────────────────────────
# System Prompts (composed from shared blocks)
# ─────────────────────────────────────────────────────────────────────────────

AGENTIC_GENERATOR_SYSTEM_PROMPT = f"""You are Conjure's app generator. You build complete, functional React+Tailwind apps by writing files into a Vite project.

{_PROJECT_STRUCTURE}

{_AVAILABLE_IMPORTS}

{_DATA_PATTERN}

WHAT YOU MUST DO:
1. Write `src/App.jsx` with your complete app component (REQUIRED)
2. Write `schema.json` in the project root (REQUIRED) with format:
   {{
     "app_id": "PLACEHOLDER_APP_ID",
     "name": "App Name",
     "capabilities": ["..."],
     "data_shape": {{ "key": "type_description" }},
     "actions": {{
       "action_name": {{
         "params": {{ "param_name": "type" }},
         "description": "Human-readable description of what this action does"
       }}
     }}
   }}

   Every user-facing operation MUST be an action. Include read actions (get_X) and write actions (add_X, remove_X, update_X, toggle_X). Each param must have a type: "string", "number", "boolean". Actions with no params use an empty object {{}}.
3. You may create additional component files in `src/` (e.g. `src/Timer.jsx`, `src/utils.js`)

{_DESIGN_RULES}

{_COMPONENT_USAGE}

COMPLETE WORKING EXAMPLE — Counter App (src/App.jsx):
```jsx
import {{ useState, useEffect }} from "react"
import {{ Button }} from "./components/ui/button"
import {{ Card, CardContent }} from "./components/ui/card"
import {{ Plus, Minus, RotateCcw }} from "lucide-react"

export default function App() {{
  const [count, setCount] = useState(() => {{
    const data = window.__conjure.getData()
    return data.count ?? 0
  }})

  useEffect(() => {{
    window.__conjure.setData({{ count }})
  }}, [count])

  const vibrate = () => {{ try {{ navigator.vibrate([10]) }} catch(e) {{}} }}

  return (
    <>
      <style>{{`:root {{ --primary: 262 83% 58%; }}`}}</style>
      <div className="min-h-dvh flex flex-col bg-background text-foreground px-4 py-6">
        <div className="flex-1 flex flex-col items-center justify-center gap-6">
          <span className="text-6xl font-bold tabular-nums text-foreground">{{count}}</span>
          <div className="flex gap-3">
            <Button size="lg" variant="outline" className="min-h-[44px] min-w-[44px] active:scale-[0.97] transition-transform duration-150" onClick={{() => {{ setCount(c => c - 1); vibrate() }}}}>
              <Minus className="w-5 h-5" />
            </Button>
            <Button size="lg" className="min-h-[44px] min-w-[44px] active:scale-[0.97] transition-transform duration-150" onClick={{() => {{ setCount(c => c + 1); vibrate() }}}}>
              <Plus className="w-5 h-5" />
            </Button>
          </div>
        </div>
        <Button variant="ghost" className="mt-auto shrink-0 min-h-[44px] active:scale-[0.97] transition-transform duration-150" onClick={{() => {{ setCount(0); vibrate() }}}}>
          <RotateCcw className="w-4 h-4 mr-2" /> Reset
        </Button>
      </div>
    </>
  )
}}
```

Matching schema.json:
```json
{{
  "app_id": "PLACEHOLDER_APP_ID",
  "name": "Counter",
  "capabilities": ["count_tracking", "increment", "decrement", "reset"],
  "data_shape": {{ "count": "number" }},
  "actions": {{
    "get_count": {{ "params": {{}}, "description": "Get the current count value" }},
    "set_count": {{ "params": {{ "value": "number" }}, "description": "Set count to a specific value" }},
    "increment": {{ "params": {{}}, "description": "Increase count by 1" }},
    "decrement": {{ "params": {{}}, "description": "Decrease count by 1" }},
    "reset": {{ "params": {{}}, "description": "Reset count to 0" }}
  }}
}}
```

INTERACTIVITY:
- App MUST be fully functional, not a mockup
- All actions via tap (not hover-dependent)
- Real-time updates where applicable (timers, counters)
- Haptic feedback: try {{ navigator.vibrate([10]) }} catch(e) {{}} on key actions
- Use React state (useState, useEffect, useRef) for UI state
- Use window.__conjure for persistent data

IMPORTANT:
- Use `write_file` tool to write each file
- Start by writing src/App.jsx, then schema.json
- Use only Tailwind CSS classes for styling (no inline styles, no CSS files except index.css)
- All components must use `export default`
- Use PLACEHOLDER_APP_ID in schema.json (will be replaced at deploy time)

{_DO_NOT_RULES}

{_COMMON_PATTERNS}

RECOMMENDED WORKFLOW:
1. Write src/App.jsx and any helper component files
2. Write schema.json
3. Run validate_jsx on ALL .jsx files you created (not just App.jsx) — e.g. validate_jsx("src/App.jsx"), validate_jsx("src/Timer.jsx")
4. Run check_imports("src/App.jsx") to verify all imports resolve
5. Fix any issues found before finishing

NOTE: The Dialog component uses fixed positioning internally — this is fine and expected. It may display slightly off-center in the iframe preview, but works correctly on the deployed app."""

AUGMENTATION_SYSTEM_PROMPT = """You are Conjure's prompt architect. The user will give you a short app idea. Your job is to expand it into a complete, opinionated specification that a code-generation model can implement without asking any follow-up questions.

CRITICAL SCOPE RULE: These are MICRO-APPS — small, single-purpose utilities displayed in a phone frame. Limit the spec to ONE core screen with ONE primary function. 3-5 features maximum. Do NOT design multi-screen apps, do NOT add settings pages, onboarding flows, or secondary views.

Output ONLY the specification using the sections below. Be opinionated — never say "optionally" or "you could". Fill in every detail the user left out. Keep under 800 words total.

APP_NAME: A short, catchy name (2-3 words max). This is for internal metadata ONLY — the generated app must NOT display it as a visible header, logo, or branding in the UI.

DESCRIPTION: One sentence explaining what the app does and who it's for.

FEATURES:
- List 3-5 concrete features (no more than 5)
- Each feature is one line: "- Feature name: brief explanation"

DATA MODEL:
- List every piece of state with its type and default value
- Format: "- fieldName (type): description [default: value]"

USER INTERACTIONS:
- Every tap/gesture and what it does
- Format: "- Action: result"

EDGE CASES:
- At least 3 edge cases the app must handle gracefully
- Format: "- Scenario: how the app responds"

UI LAYOUT:
- Design for a 390×844px phone screen — NO desktop layouts, NO sidebar navigation. Maximum 2 columns for cards. Single-column stacked layout preferred. Every interactive element at least 44×44px.
- Describe the visual layout section by section (main area, controls, etc.) — do NOT include an app name header, logo, or branding section. Jump straight into the core functionality.
- Root layout: min-h-dvh flex flex-col with px-4 horizontal padding
- Specify an accent color as HSL values (e.g. "142 71% 45%" for green) that fits the app's purpose
- Format: "Accent color: H S% L%"
- Reference available shadcn components: Button, Card, Badge, Input, Progress, Tabs, Switch, Separator, Dialog

SCHEMA:
- capabilities: list of capability strings
- data_shape: key-type pairs matching the data model
- actions: for EVERY user operation, provide { "params": {"param": "type"}, "description": "what it does" }. Include both read and write actions."""

ITERATION_AUGMENTATION_SYSTEM_PROMPT = """You are Conjure's prompt architect. The user wants to modify an existing React+Tailwind app running in a 390×844px phone frame. The app uses shadcn/ui components (Button, Card, Badge, Input, Progress, Tabs, Switch, Separator, Dialog), Tailwind CSS variable classes (bg-background, text-foreground, bg-primary, etc.), and persists data via window.__conjure.getData()/setData().

Expand their terse instruction into a clear, complete modification spec. Be opinionated — fill in details they left out.

CRITICAL: The modification spec should describe ONLY the changes requested. Do NOT re-architect the entire app. Keep modifications surgical — change the minimum needed to fulfill the request. Do NOT redesign layouts, swap component libraries, or refactor working code.

COMPLEXITY SCALING: Match your output detail to the input complexity.
- TRIVIAL changes (color, text, single property, show/hide an element): Output ONLY "CHANGE SUMMARY" and "MODIFICATIONS" sections. Skip all other sections. Keep under 100 words.
- SIMPLE changes (add a button, change layout of one area, swap a component): Output "CHANGE SUMMARY", "MODIFICATIONS", and "UI DETAILS". Keep under 200 words.
- COMPLEX changes (new feature, new data fields, multi-component changes): Use ALL sections below. Keep under 400 words.

When the user's exact request is simple, implement it directly. Do not over-engineer based on the expanded specification.

Output ONLY the specification using the applicable sections below.

CHANGE SUMMARY: One sentence describing the modification.

MODIFICATIONS:
- List every specific change to make
- Be precise: name the shadcn component to use (e.g. "Add a Button variant='destructive' size='sm'"), specify layout details (e.g. "flex row with gap-2"), and note Tailwind classes where relevant
- Format: "- What to change: how to change it"

DATA MODEL CHANGES (skip for trivial/simple changes):
- List any new state variables, removed state variables, or changes to the data shape
- If the window.__conjure data shape changes, describe the new/modified keys
- Format: "- fieldName (type): what changed [default: value]"
- If no data model changes needed, write "None"

UI DETAILS (skip for trivial changes):
- Describe specific visual changes for the 390×844px viewport
- Specify component variants, sizes, and Tailwind classes to use
- Note layout approach (flex direction, gap, padding)
- Format: "- Element: visual specification"

PRESERVATION (skip for trivial changes):
- List critical things that must NOT change
- Format: "- Preserve: what and why"

EDGE CASES (skip for trivial/simple changes):
- At least 2 edge cases the modification introduces
- Format: "- Scenario: how the app should respond" """


def extract_app_name_from_spec(spec: str, fallback: str) -> str:
    """Extract the APP_NAME from an augmented spec, or return a fallback."""
    for line in spec.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("APP_NAME:"):
            name = stripped.split(":", 1)[1].strip()
            if name:
                return name[:50]
    return fallback[:50]


AGENTIC_REFINER_SYSTEM_PROMPT = f"""You are Conjure's app refiner. You modify existing React+Tailwind apps based on user instructions.

{_PROJECT_STRUCTURE}

{_AVAILABLE_IMPORTS}

{_DATA_PATTERN}

{_DESIGN_RULES}

{_COMPONENT_USAGE}

{_DO_NOT_RULES}

{_COMMON_PATTERNS}

MANDATORY WORKFLOW (follow this exact order every time):
1. ALWAYS run `list_files` first to see the project structure
2. ALWAYS run `read_file("src/App.jsx")` to understand the current code
3. ALWAYS run `read_file("schema.json")` to understand the data contract
4. Read any other custom component files listed by list_files
5. Plan the minimum edits needed to fulfill the request
6. Write ONLY the files that need to change — do not rewrite files that don't need changes
7. If the data shape changed, update schema.json too
8. Run `validate_jsx("src/App.jsx")` to check for syntax issues
9. Run `check_imports("src/App.jsx")` to verify all imports resolve

PRESERVATION RULES:
1. Preserve ALL existing functionality unless the user specifically asks to change it
2. Preserve the window.__conjure data contract (getData, setData) and the canonical loading pattern
3. Preserve the localStorage key pattern
4. Preserve the data structure unless the modification requires changing it
5. Keep the same design language (use CSS variable classes: bg-background, text-foreground, bg-card, bg-primary, etc.)
6. Do NOT add app name headers, logos, or branding. These are mini utility apps — keep just the functionality.
7. Make ONLY the requested changes — surgical modifications, not rewrites
8. Do NOT modify protected files: src/main.jsx, src/index.css, vite.config.js, package.json, tailwind.config.js, postcss.config.js, index.html, src/components/ui/*, src/lib/*
9. Update schema.json if capabilities, data shape, or actions changed. Every action must have {{"params": {{...}}, "description": "..."}} format"""

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
    {
        "type": "function",
        "function": {
            "name": "validate_jsx",
            "description": "Validate a JSX file for common syntax errors before building. Checks bracket balance, bad imports, TypeScript syntax, missing default export, and other common mistakes. Run this after writing src/App.jsx.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the JSX file to validate (e.g. 'src/App.jsx')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_imports",
            "description": "Scan a JSX file and verify every import path resolves to an existing file in the project. Catches 'module not found' errors before building.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the JSX file to check (e.g. 'src/App.jsx')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_component_api",
            "description": "Get the props, variants, and usage example for a shadcn/ui component. Use this to check correct component API before writing code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "component": {
                        "type": "string",
                        "description": "Component name: button, card, badge, input, progress, tabs, separator, switch, or dialog"
                    }
                },
                "required": ["component"]
            }
        }
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Component API reference (for get_component_api tool)
# ─────────────────────────────────────────────────────────────────────────────

SHADCN_COMPONENT_API = {
    "button": {
        "import": 'import { Button } from "./components/ui/button"',
        "props": {
            "variant": "default | destructive | outline | secondary | ghost | link",
            "size": "default | sm | lg | icon",
            "asChild": "boolean (render as child element)",
            "disabled": "boolean",
            "className": "string (additional classes)",
        },
        "example": '<Button variant="outline" size="sm" onClick={handleClick}><Plus className="w-4 h-4 mr-2" />Add</Button>',
    },
    "card": {
        "import": 'import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./components/ui/card"',
        "props": {
            "className": "string (additional classes)",
        },
        "subcomponents": ["Card", "CardHeader", "CardTitle", "CardDescription", "CardContent", "CardFooter"],
        "example": "<Card><CardHeader><CardTitle>Title</CardTitle><CardDescription>Description</CardDescription></CardHeader><CardContent>Content here</CardContent><CardFooter>Footer</CardFooter></Card>",
    },
    "badge": {
        "import": 'import { Badge } from "./components/ui/badge"',
        "props": {
            "variant": "default | secondary | destructive | outline",
            "className": "string",
        },
        "example": '<Badge variant="secondary">Active</Badge>',
    },
    "input": {
        "import": 'import { Input } from "./components/ui/input"',
        "props": {
            "type": "string (text, number, email, password, etc.)",
            "placeholder": "string",
            "value": "string",
            "onChange": "function",
            "disabled": "boolean",
            "className": "string",
        },
        "example": '<Input placeholder="Enter value..." value={val} onChange={e => setVal(e.target.value)} />',
    },
    "progress": {
        "import": 'import { Progress } from "./components/ui/progress"',
        "props": {
            "value": "number (0-100)",
            "className": "string",
        },
        "example": "<Progress value={75} />",
    },
    "tabs": {
        "import": 'import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"',
        "props": {
            "defaultValue": "string (initial active tab)",
            "value": "string (controlled active tab)",
            "onValueChange": "function(value)",
            "className": "string",
        },
        "subcomponents": ["Tabs", "TabsList", "TabsTrigger (value: string)", "TabsContent (value: string)"],
        "example": '<Tabs defaultValue="tab1"><TabsList><TabsTrigger value="tab1">Tab 1</TabsTrigger><TabsTrigger value="tab2">Tab 2</TabsTrigger></TabsList><TabsContent value="tab1">Content 1</TabsContent><TabsContent value="tab2">Content 2</TabsContent></Tabs>',
    },
    "separator": {
        "import": 'import { Separator } from "./components/ui/separator"',
        "props": {
            "orientation": "horizontal | vertical",
            "className": "string",
        },
        "example": "<Separator />",
    },
    "switch": {
        "import": 'import { Switch } from "./components/ui/switch"',
        "props": {
            "checked": "boolean",
            "onCheckedChange": "function(checked: boolean)",
            "disabled": "boolean",
            "className": "string",
        },
        "example": "<Switch checked={on} onCheckedChange={setOn} />",
    },
    "dialog": {
        "import": 'import { Dialog, DialogTrigger, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./components/ui/dialog"',
        "props": {
            "open": "boolean (controlled)",
            "onOpenChange": "function(open: boolean)",
        },
        "subcomponents": ["Dialog", "DialogTrigger", "DialogContent", "DialogHeader", "DialogTitle", "DialogDescription", "DialogFooter"],
        "example": '<Dialog><DialogTrigger asChild><Button>Open</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Title</DialogTitle><DialogDescription>Description</DialogDescription></DialogHeader><DialogFooter><Button>Save</Button></DialogFooter></DialogContent></Dialog>',
    },
}

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

# Protected path prefixes (pre-built UI components and utilities)
PROTECTED_PREFIXES = ("src/components/ui/", "src/lib/")

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
            if rel_path in PROTECTED_FILES or rel_path.startswith(PROTECTED_PREFIXES):
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

        elif tool_name == "validate_jsx":
            rel_path = args.get("path", "").replace("\\", "/")
            try:
                full_path = _validate_path(rel_path)
            except ValueError as e:
                return f"Error: {e}"
            if not full_path.exists():
                return f"Error: File not found: {rel_path}"
            content = full_path.read_text(encoding="utf-8")
            return _validate_jsx_content(content, rel_path)

        elif tool_name == "check_imports":
            rel_path = args.get("path", "").replace("\\", "/")
            try:
                full_path = _validate_path(rel_path)
            except ValueError as e:
                return f"Error: {e}"
            if not full_path.exists():
                return f"Error: File not found: {rel_path}"
            content = full_path.read_text(encoding="utf-8")
            return _check_imports_content(content, rel_path, build_path)

        elif tool_name == "get_component_api":
            component = args.get("component", "").lower().strip()
            if component not in SHADCN_COMPONENT_API:
                available = ", ".join(sorted(SHADCN_COMPONENT_API.keys()))
                return f"Unknown component '{component}'. Available: {available}"
            api = SHADCN_COMPONENT_API[component]
            lines = [f"## {component}"]
            lines.append(f"Import: {api['import']}")
            lines.append("Props:")
            for prop, desc in api["props"].items():
                lines.append(f"  - {prop}: {desc}")
            if "subcomponents" in api:
                lines.append(f"Subcomponents: {', '.join(api['subcomponents'])}")
            lines.append(f"Example: {api['example']}")
            return "\n".join(lines)

        else:
            return f"Error: Unknown tool '{tool_name}'"

    return execute


def _validate_jsx_content(content: str, file_path: str) -> str:
    """Validate JSX content for common errors. Returns issues or 'OK'."""
    issues = []

    # Check bracket balance
    for open_b, close_b, name in [("{", "}", "curly braces"), ("(", ")", "parentheses"), ("[", "]", "square brackets")]:
        depth = 0
        in_string = False
        string_char = None
        for i, ch in enumerate(content):
            if in_string:
                if ch == string_char and (i == 0 or content[i-1] != "\\"):
                    in_string = False
                continue
            if ch in ('"', "'", "`"):
                in_string = True
                string_char = ch
                continue
            if ch == open_b:
                depth += 1
            elif ch == close_b:
                depth -= 1
        if depth != 0:
            issues.append(f"Mismatched {name}: {'more opens' if depth > 0 else 'more closes'} (off by {abs(depth)})")

    # Check for bad imports
    bad_import_patterns = [
        (r'''from\s+['"]react/jsx-runtime['"]''', "Do not import from 'react/jsx-runtime' — Vite handles JSX transform"),
        (r'''\brequire\s*\(''', "Do not use require() — this is an ESM project, use import"),
        (r'''from\s+['"]@/''', "Do not use @/ path aliases — use relative paths like ./components/ui/"),
        (r'''\bimport\s+React[\s,]+from\s+['"]react['"]''', "Do not import React default — import only hooks: import { useState } from 'react'"),
        (r'''from\s+['"]@radix-ui/''', "Do not import from @radix-ui/* directly — use shadcn wrappers in ./components/ui/"),
    ]
    for pattern, message in bad_import_patterns:
        if re.search(pattern, content):
            issues.append(message)

    # Check for TypeScript syntax
    ts_patterns = [
        (r''':\s*(string|number|boolean|any|void|never|unknown)\s*[;,\)=]''', "TypeScript type annotation detected — this is a .jsx project, remove type annotations"),
        (r'''\binterface\s+\w+\s*\{''', "TypeScript interface detected — not allowed in .jsx"),
        (r'''\btype\s+\w+\s*=''', "TypeScript type alias detected — not allowed in .jsx"),
        (r'''\bas\s+(string|number|boolean|any|const)\b''', "TypeScript 'as' cast detected — not allowed in .jsx"),
        (r'''<\w+>\s*\(''', None),  # Skip — could be JSX, not TS generic
    ]
    for pattern, message in ts_patterns:
        if message and re.search(pattern, content):
            issues.append(message)

    # Check for missing export default
    if not re.search(r'''export\s+default\s+function''', content):
        if not re.search(r'''export\s+default\s+''', content):
            issues.append("Missing 'export default function' — main component must use export default")

    # Check for Next.js directives
    if '"use client"' in content or "'use client'" in content:
        issues.append("Remove 'use client' directive — this is NOT Next.js")
    if '"use server"' in content or "'use server'" in content:
        issues.append("Remove 'use server' directive — this is NOT Next.js")

    # Check for React.lazy
    if "React.lazy" in content or "React.lazy(" in content:
        issues.append("Do not use React.lazy() — no code splitting needed")

    # Check for position fixed — in inline styles, className strings, template literals, and cn() calls
    has_fixed = False
    if "position: fixed" in content or "position:fixed" in content:
        has_fixed = True
    if re.search(r'className="[^"]*\bfixed\b[^"]*"', content):
        has_fixed = True
    if re.search(r'className=\{[^}]*\bfixed\b[^}]*\}', content):
        has_fixed = True
    if re.search(r'`[^`]*\bfixed\b[^`]*`', content):
        has_fixed = True
    if re.search(r'cn\([^)]*\bfixed\b[^)]*\)', content):
        has_fixed = True
    if has_fixed:
        issues.append("Avoid position:fixed — it breaks inside iframe preview. Use flex layout with mt-auto.")

    if issues:
        return f"VALIDATION ISSUES in {file_path}:\n" + "\n".join(f"- {issue}" for issue in issues)
    return f"OK — {file_path} passed all checks"


def _check_imports_content(content: str, file_path: str, build_path: Path) -> str:
    """Check that all import paths in a JSX file resolve to existing files."""
    # Known external packages that don't need file resolution
    external_packages = {"react", "react-dom", "lucide-react"}

    issues = []
    import_pattern = re.compile(r'''(?:import|from)\s+['"]([^'"]+)['"]''')
    file_dir = (build_path / file_path).parent

    for match in import_pattern.finditer(content):
        import_path = match.group(1)

        # Skip external packages
        if import_path in external_packages or import_path.startswith("react/") or import_path.startswith("react-dom/"):
            continue

        # Relative imports — resolve to file
        if import_path.startswith("."):
            # Try with common extensions
            resolved_base = (file_dir / import_path).resolve()
            found = False
            candidates = [
                resolved_base,
                resolved_base.with_suffix(".jsx"),
                resolved_base.with_suffix(".js"),
                resolved_base.with_suffix(".json"),
                resolved_base / "index.jsx",
                resolved_base / "index.js",
            ]
            for candidate in candidates:
                if candidate.exists() and str(candidate).startswith(str(build_path)):
                    found = True
                    break
            if not found:
                issues.append(f"Import '{import_path}' not found (tried: {import_path}.jsx, {import_path}.js, {import_path}/index.jsx)")
        else:
            # Non-relative, non-external — likely an error
            if import_path not in external_packages:
                issues.append(f"Import '{import_path}' is not a known package. Use relative paths for local files (e.g., ./{import_path})")

    if issues:
        return f"IMPORT ISSUES in {file_path}:\n" + "\n".join(f"- {issue}" for issue in issues)
    return f"OK — all imports in {file_path} resolve correctly"


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


def deploy_build(build_dir: str, app_id: str, app_name: str, theme_color: str, version: int = 1) -> None:
    """Copy dist/ to apps/{app_id}/, add manifest/icon/sw.js, backup source, snapshot version."""
    dist_dir = Path(build_dir) / "dist"
    app_dir = Path(settings.APPS_DIR) / app_id

    # Preserve existing data.json if present
    existing_data = None
    if (app_dir / "data.json").exists():
        existing_data = (app_dir / "data.json").read_bytes()

    # Copy dist to app dir (overwrite existing)
    if app_dir.exists():
        # Remove old build artifacts but preserve data.json, _versions, _src_versions
        for item in app_dir.iterdir():
            if item.name in ("data.json", "_versions", "_src_versions"):
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

    # Snapshot this version's dist into _versions/{N}/
    version_dir = app_dir / "_versions" / str(version)
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True, exist_ok=True)
    skip_names = {"data.json", "_src", "_versions", "_src_versions"}
    for item in app_dir.iterdir():
        if item.name in skip_names:
            continue
        dest = version_dir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    # Snapshot source into _src_versions/{N}/
    src_version_dir = app_dir / "_src_versions" / str(version)
    if src_version_dir.exists():
        shutil.rmtree(src_version_dir)
    if src_backup.exists():
        shutil.copytree(src_backup, src_version_dir)


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


def _tool_progress(on_status):
    """Create an on_progress callback that suppresses per-file noise.
    We only report high-level phase changes from the pipeline functions themselves."""
    async def callback(tool_name, args):
        pass  # Intentionally silent — phase messages come from the pipeline
    return callback


async def generate_app_pipeline(client, prompt: str, app_id: str, app_name: str, on_status=None) -> tuple[bool, str]:
    """Full pipeline: setup → agentic gen → build+retry → deploy → cleanup.
    Returns (success, theme_color).
    on_status: Optional async callback(message) for progress reporting.
    """
    build_dir = None
    try:
        # 1. Setup build directory
        build_dir = setup_build_dir(app_id)
        tool_executor = create_tool_executor(build_dir)

        # 2. Agentic generation
        if on_status:
            await on_status("Crafting your app...")
        messages = await client.generate_app(prompt, build_dir, on_progress=on_status and _tool_progress(on_status))

        # 3. Build with retries — keep going until it works
        theme_color = _extract_theme_from_build(build_dir)
        if on_status:
            await on_status("Putting it all together...")
        last_error = None
        for attempt in range(settings.MAX_BUILD_RETRIES + 1):
            success, output = await run_vite_build(build_dir)
            if success:
                logger.info(f"Build succeeded for {app_id} (attempt {attempt + 1})")
                break
            logger.warning(f"Build failed for {app_id} (attempt {attempt + 1}): {output}")
            # Detect duplicate errors — abort early if same error repeats
            error_sig = output.strip()[:200]
            if last_error and error_sig == last_error:
                logger.error(f"Duplicate build error for {app_id}, aborting retries")
                return False, "#6366f1"
            last_error = error_sig
            if on_status:
                await on_status("Tweaking a few things...")
            messages = await client.fix_build_error(output, build_dir, messages, on_progress=on_status and _tool_progress(on_status))
        else:
            return False, "#6366f1"

        # 4. Post-build quality check
        qc_warnings = post_build_quality_check(build_dir)
        for warning in qc_warnings:
            logger.warning(f"Quality check [{app_id}]: {warning}")

        # 5. Deploy
        if on_status:
            await on_status("Almost ready...")
        deploy_build(build_dir, app_id, app_name, theme_color, version=1)
        return True, theme_color

    except Exception as e:
        logger.error(f"Pipeline failed for {app_id}: {e}")
        return False, "#6366f1"
    finally:
        if build_dir:
            cleanup_build_dir(build_dir)


async def iterate_app_pipeline(
    client, instruction: str, app_id: str, app_name: str,
    on_status=None, current_version: int = 1,
    raw_instruction: str = "", chat_history: list[dict] | None = None,
) -> tuple[bool, str, int]:
    """Iterate pipeline: setup → restore src → agentic refine → build+retry → deploy → cleanup.
    Returns (success, theme_color, new_version).
    on_status: Optional async callback(message) for progress reporting.
    """
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
        if on_status:
            await on_status("Making your changes...")
        messages = await client.refine_app(
            instruction, build_dir,
            on_progress=on_status and _tool_progress(on_status),
            raw_instruction=raw_instruction,
            chat_history=chat_history,
        )

        # 4. Build with retries — keep going until it works
        theme_color = _extract_theme_from_build(build_dir)
        if on_status:
            await on_status("Putting it all together...")
        last_error = None
        for attempt in range(settings.MAX_BUILD_RETRIES + 1):
            success, output = await run_vite_build(build_dir)
            if success:
                logger.info(f"Iterate build succeeded for {app_id} (attempt {attempt + 1})")
                break
            logger.warning(f"Iterate build failed for {app_id} (attempt {attempt + 1}): {output}")
            # Detect duplicate errors — abort early if same error repeats
            error_sig = output.strip()[:200]
            if last_error and error_sig == last_error:
                logger.error(f"Duplicate build error for {app_id}, aborting retries")
                return False, "#6366f1"
            last_error = error_sig
            if on_status:
                await on_status("Tweaking a few things...")
            messages = await client.fix_build_error(output, build_dir, messages, on_progress=on_status and _tool_progress(on_status))
        else:
            return False, "#6366f1"

        # 5. Post-build quality check
        qc_warnings = post_build_quality_check(build_dir)
        for warning in qc_warnings:
            logger.warning(f"Quality check [{app_id}]: {warning}")

        # 6. Deploy
        new_version = current_version + 1
        if on_status:
            await on_status("Almost ready...")
        deploy_build(build_dir, app_id, app_name, theme_color, version=new_version)
        return True, theme_color, new_version

    except Exception as e:
        logger.error(f"Iterate pipeline failed for {app_id}: {e}")
        return False, "#6366f1", current_version
    finally:
        if build_dir:
            cleanup_build_dir(build_dir)


def post_build_quality_check(build_dir: str) -> list[str]:
    """Run quality checks after a successful build. Returns list of warnings."""
    warnings = []
    build_path = Path(build_dir)

    # Check schema.json exists and has required fields
    schema_path = build_path / "schema.json"
    if not schema_path.exists():
        warnings.append("schema.json is missing")
    else:
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            if not schema.get("actions"):
                warnings.append("schema.json has no actions — Command Plane won't be able to interact with this app")
            if not schema.get("data_shape"):
                warnings.append("schema.json has no data_shape")
        except (json.JSONDecodeError, Exception):
            warnings.append("schema.json is not valid JSON")

    # Check App.jsx quality
    app_path = build_path / "src" / "App.jsx"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")

        # Check for min-h-dvh (fills viewport)
        if "min-h-dvh" not in content and "min-h-screen" not in content:
            warnings.append("App.jsx missing min-h-dvh — app may not fill the phone viewport")

        # Check for export default
        if "export default" not in content:
            warnings.append("App.jsx missing export default")

        # Check for excessive hardcoded colors
        hex_colors = re.findall(r'#[0-9a-fA-F]{6}', content)
        # Filter out common theme-related ones that appear in style tags
        unique_colors = set(c.lower() for c in hex_colors)
        if len(unique_colors) > 5:
            warnings.append(f"App.jsx has {len(unique_colors)} hardcoded hex colors — prefer CSS variable classes (bg-primary, text-foreground, etc.)")

        # Check that data persistence functions are used
        if "window.__conjure.getData()" not in content and "__conjure.getData()" not in content:
            warnings.append("App.jsx never calls getData() — app won't load persisted data on reload")
        if "window.__conjure.setData(" not in content and "__conjure.setData(" not in content:
            warnings.append("App.jsx never calls setData() — app won't persist any data")

    # Check minimum dist size (< 5KB likely means blank page)
    dist_dir = build_path / "dist"
    if dist_dir.exists():
        total_size = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file())
        if total_size < 5000:
            warnings.append(f"dist/ is only {total_size} bytes — likely a blank page or missing content")

    return warnings


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
            # Skip default theme colors (light and dark)
            if color not in ("#0a0a0a", "#141414", "#1a1a1a", "#e5e5e5", "#737373", "#a3a3a3", "#525252", "#404040", "#ffffff", "#f5f5f5", "#fafafa", "#18181b", "#1c1c1e"):
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
5. Keep the same light theme and design language
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
