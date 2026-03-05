#!/bin/bash

# SYConv Start Script (macOS/Linux)
echo -e "\033[0;36mStarting SYConv Hybrid App...\033[0m"

# 1. Validate Env
if [ ! -f "backend/.env" ]; then
    echo -e "\033[0;31mError: backend/.env missing. Run './setup.sh' first.\033[0m"
    exit 1
fi

# 2. Start Processes
# We use & to run in background, but ideally we want separate terminals or a grouped tool like 'overmind' or 'tmux'
# For simplicity, we'll run backend in background and frontend in foreground

echo "1. Starting Backend (FastAPI)..."
cd backend
uv run uvicorn main:app --reload &
BACKEND_PID=$!
cd ..

echo "2. Starting Frontend (Vite)..."
cd frontend
npm run dev

# Cleanup
kill $BACKEND_PID
