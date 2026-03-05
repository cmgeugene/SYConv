Write-Host "Starting SYConv Setup..." -ForegroundColor Cyan

# 1. Check for uv
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv not found. Installing uv..." -ForegroundColor Yellow
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path += ";$HOME\.cargo\bin"
}
else {
    Write-Host "uv found." -ForegroundColor Green
}

# 2. Setup Backend
Write-Host "`n[1/3] Setting up Backend..." -ForegroundColor Cyan
Set-Location backend
if (!(Test-Path .venv)) {
    uv venv
}
uv pip install -r requirements.txt
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host ".env created from .env.example. Please update your keys." -ForegroundColor Yellow
}
Set-Location ..

# 3. Setup Frontend
Write-Host "`n[2/3] Setting up Frontend..." -ForegroundColor Cyan
Set-Location frontend
if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Node.js (npm) not found. Please install Node.js." -ForegroundColor Red
    exit 1
}
npm install
Set-Location ..

Write-Host "`n[3/3] Setup Complete!" -ForegroundColor Green
Write-Host "Run './start.ps1' to launch the app." -ForegroundColor Cyan
