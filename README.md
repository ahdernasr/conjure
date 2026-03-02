# Conjure

Describe an app in one sentence. Get a real, working app you can install on your phone.

Conjure turns natural language into fully functional React PWAs. Generate a water tracker, a tournament bracket, a workout planner: whatever you need, tailored to you. Then iterate on it conversationally: "make the accent color blue", "add a reset button", done.

Once you have a few apps, the Command Plane ties them together. One voice interface that reads each app's schema, understands what it can do, and executes actions across all of them. "Log a glass of water." "Who's playing next in the tournament?" No app switching.

## Why this exists

You're hosting a ping pong tournament with friends. You need a bracket for 8 players, best of 3, single elimination. You could use Challonge, make an account, configure a bunch of settings, and share a link nobody bookmarks. Or you could say one sentence and have a custom app on your phone in 15 seconds.

Your doctor tells you to drink 3 liters of water a day. Every hydration app in the App Store has premium tiers, social features, and plant animations you didn't ask for. You just want a glass counter with your goal.

You're tracking your roommate's chore rotation. You're scoring a card game at the cottage. You're logging reps at the gym with your specific split. These are all apps that should exist for 5 minutes of effort, not 5 hours of searching for something close enough.

Conjure is for the apps that are too specific for the App Store and too interactive for a ChatGPT response. Things that need persistent state, a UI you come back to, and the ability to change over time.

## How it works

1. You describe what you want (text or voice)
2. Mistral Large expands your sentence into a full spec
3. Devstral generates a complete React + Tailwind + shadcn/ui app via agentic tool calls
4. Vite builds it. If the build fails, Devstral reads the error and fixes it automatically (up to 5 retries)
5. The app deploys as a PWA with a manifest, service worker, and home screen icon
6. You iterate by chatting: each change is a new version you can roll back to

The Command Plane uses Mistral Large with function calling. Every generated app has a `schema.json` that declares its data shape and available actions. The Command Plane calls `list_apps` to discover what exists, then `execute_app_action` to mutate data or `query_app` to answer questions. Data mutations go through an LLM that reads the current state, applies the action, and writes the result back.

## Stack

- **Mistral Large 3**: prompt augmentation, intent classification, Command Plane orchestration, data mutations
- **Devstral 2**: agentic code generation and iteration (write_file, read_file, validate_jsx, check_imports tools)
- **ElevenLabs**: speech-to-text (Scribe v2) and text-to-speech (Turbo v2.5)
- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + aiosqlite
- **Generated apps**: React + Tailwind CSS + shadcn/ui components, built with Vite, deployed as PWAs

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
python -m uvicorn app.main:app :host 0.0.0.0 :port 8001

# Frontend
cd frontend
npm install
npx vite :host 0.0.0.0 :port 5173
```

Set these in `.env`:
```
MISTRAL_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
```

## Built for

Mistral Worldwide Hackathon 2026: "Anything Goes" track. Solo project, 48 hours.
