#!/bin/bash

# SYConv Setup Script (macOS/Linux)
echo -e "\033[0;36mStarting SYConv Setup...\033[0m"

# 1. Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "\033[0;33muv not found. Installing uv...\033[0m"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo -e "\033[0;32muv found.\033[0m"
fi

# 2. Setup Backend
echo -e "\n\033[0;36m[1/3] Setting up Backend...\033[0m"
cd backend
if [ ! -d ".venv" ]; then
    uv venv
fi
uv pip install -r requirements.txt
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "\033[0;33m.env created from .env.example. Please update your keys.\033[0m"
fi
cd ..

# 3. Setup Frontend
echo -e "\n\033[0;36m[2/3] Setting up Frontend...\033[0m"
cd frontend
if ! command -v npm &> /dev/null; then
    echo -e "\033[0;31mError: Node.js (npm) not found. Please install Node.js.\033[0m"
    exit 1
fi
npm install
cd ..

echo -e "\n\033[0;32m[3/3] Setup Complete!\033[0m"
echo -e "\033[0;36mRun './start.sh' to launch the app.\033[0m"
