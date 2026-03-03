Write-Host "Starting SYConv Hybrid App..." -ForegroundColor Cyan

# Start Backend
Write-Host "1. Starting Backend (FastAPI on http://localhost:8000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\activate; uvicorn main:app --reload"

# Start Frontend
Write-Host "2. Starting Frontend (React Vite on http://localhost:5173)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host "Done! The developer environment is spinning up in separate windows." -ForegroundColor Green
Write-Host "Make sure you have set OPENAI_API_KEY in your environment variables for the LLM to work." -ForegroundColor Yellow
