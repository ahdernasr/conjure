# Conjure

Describe an app in one sentence. Get a real, working app you can install on your phone.

Conjure turns natural language into fully functional React PWAs. Generate a water tracker, a tournament bracket, a workout planner -- whatever you need, tailored to you. Then iterate on it conversationally: "make the accent color blue", "add a reset button", done.

Once you have a few apps, the Command Plane ties them together. One voice interface that reads each app's schema, understands what it can do, and executes actions across all of them. "Log a glass of water." "Who's playing next in the tournament?" No app switching.

## How it works

1. You describe what you want (text or voice)
2. Mistral Large expands your sentence into a full spec
3. Devstral generates a complete React + Tailwind + shadcn/ui app via agentic tool calls
4. Vite builds it. If the build fails, Devstral reads the error and fixes it automatically (up to 5 retries)
5. The app deploys as a PWA with a manifest, service worker, and home screen icon
6. You iterate by chatting -- each change is a new version you can roll back to

The Command Plane uses Mistral Large with function calling. Every generated app has a `schema.json` that declares its data shape and available actions. The Command Plane calls `list_apps` to discover what exists, then `execute_app_action` to mutate data or `query_app` to answer questions. Data mutations go through an LLM that reads the current state, applies the action, and writes the result back.

## Stack

- **Mistral Large 3** -- prompt augmentation, intent classification, Command Plane orchestration, data mutations
- **Devstral 2** -- agentic code generation and iteration (write_file, read_file, validate_jsx, check_imports tools)
- **ElevenLabs** -- speech-to-text (Scribe v2) and text-to-speech (Turbo v2.5)
- **Frontend** -- React + TypeScript + Vite
- **Backend** -- FastAPI + aiosqlite
- **Generated apps** -- React + Tailwind CSS + shadcn/ui components, built with Vite, deployed as PWAs

## Project structure

```
backend/
  app/
    main.py              # FastAPI app, CORS, route registration
    config.py            # env vars, model assignments
    routes/
      generate.py        # app generation + iteration endpoints
      chat.py            # per-app chat (iterate or ask questions)
      command.py         # Command Plane voice orchestration
      voice.py           # STT/TTS endpoints
      apps.py            # CRUD, data sync
    services/
      mistral_client.py  # Devstral agentic loop, Mistral Large calls
      generator.py       # build pipeline, tool executor, system prompts
      command_plane.py   # Command Plane tool-calling loop
      voice.py           # ElevenLabs integration
      app_service.py     # DB + filesystem operations
  app/template/          # Vite project template (shadcn components pre-installed)

frontend/
  src/
    components/          # UI: AppCard, PhonePreview, ChatPanel, VoiceOrb, etc.
    pages/               # Home, AppView
```

## Running locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API keys
cd app/template && npm install && cd ../..
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Frontend
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173
```

Set these in `.env`:
```
MISTRAL_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
```

## What makes this different

The generated apps aren't throwaway HTML. They're versioned React apps with persistent state (localStorage + server sync), proper component libraries, and a schema that makes them programmable. The Command Plane isn't a gimmick bolted on top -- it's the reason the schema exists. Every app is built to be controlled by voice from day one.

## Built for

Mistral Worldwide Hackathon 2026 -- "Anything Goes" track. Solo project, 34 hours.
