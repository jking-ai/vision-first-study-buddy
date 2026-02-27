#!/usr/bin/env bash
# Start both backend and frontend dev servers, stop both with Ctrl+C

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIDS=()

cleanup() {
  echo ""
  echo "Stopping dev servers..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null
  done
  echo "All servers stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

# Check for backend .env
if [ ! -f "$PROJECT_ROOT/backend/.env" ]; then
  echo "Warning: backend/.env not found. Copy .env.example and fill in your values:"
  echo "  cp backend/.env.example backend/.env"
  echo ""
fi

# Install dependencies if needed
if [ ! -d "$PROJECT_ROOT/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd "$PROJECT_ROOT/frontend"
  npm install
fi

# Start backend
echo "Starting backend (uvicorn) on :8000..."
cd "$PROJECT_ROOT/backend"
uvicorn app.main:app --reload --port 8000 &
PIDS+=($!)

# Start frontend
echo "Starting frontend (vite) on :5173..."
cd "$PROJECT_ROOT/frontend"
npm run dev &
PIDS+=($!)

echo ""
echo "Both servers running. Press Ctrl+C to stop."
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

# Wait for any child to exit
wait
