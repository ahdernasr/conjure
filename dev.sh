#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

# Backend
cd "$ROOT/backend"
if [ ! -d venv ]; then
  echo "Creating Python venv..."
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt -q
fi
echo "Starting backend on :8001"
./venv/bin/python run.py &
BACKEND_PID=$!

# Frontend
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  echo "Installing frontend deps..."
  npm install --silent
fi
echo "Starting frontend on :5173"
npx vite --host &
FRONTEND_PID=$!

echo ""
echo "Conjure running:"
echo "  Frontend → http://localhost:5173"
echo "  Backend  → http://localhost:8001"
echo "  Press Ctrl+C to stop"
echo ""

wait
