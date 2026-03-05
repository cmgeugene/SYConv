Write-Host "Starting SYConv Hybrid App..." -ForegroundColor Cyan

# 1. Validate Env
if (!(Test-Path "backend/.env")) {
    Write-Host "Error: backend/.env missing. Run './setup.ps1' first." -ForegroundColor Red
    exit 1
}

# 2. Start Backend
Write-Host "1. Starting Backend (FastAPI)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location backend; uv run uvicorn main:app --reload"

# 3. Start Frontend
Write-Host "2. Starting Frontend (Vite)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "`nDone! The app is spinning up in separate windows." -ForegroundColor Green
