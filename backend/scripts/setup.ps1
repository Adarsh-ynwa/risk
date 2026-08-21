# One-time backend setup for AI Risk Manager (Windows PowerShell)
# Usage: .\scripts\setup.ps1
#        .\scripts\setup.ps1 -UseKaggle   # skip sample data generation

param(
    [switch]$UseKaggle
)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $BackendRoot

Write-Host "=== AI Risk Manager Backend Setup ===" -ForegroundColor Cyan

if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv venv
}

Write-Host "Activating venv and installing dependencies..."
& ".\venv\Scripts\Activate.ps1"
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example — add GROQ_API_KEY if you have one."
}

if (-not $UseKaggle) {
    if (-not (Test-Path "data\bank_fraud.csv")) {
        Write-Host "Generating sample dataset..."
        python scripts/generate_sample_data.py
    } else {
        Write-Host "Found data\bank_fraud.csv — skipping sample generation."
    }
} else {
    if (-not (Test-Path "data\bank_fraud.csv")) {
        Write-Host "ERROR: Place bank_fraud.csv in backend/data/ first." -ForegroundColor Red
        exit 1
    }
    Write-Host "Using Kaggle dataset at data\bank_fraud.csv"
    python scripts/inspect_dataset.py
}

Write-Host "Training ML model (may take a few minutes)..."
python scripts/train_model.py

Write-Host "Loading data into SQLite and pre-analyzing high-risk sample..."
python scripts/load_data.py --force-reload

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Start API:  uvicorn app.main:app --reload --port 8000"
Write-Host "Health:     http://localhost:8000/health"
