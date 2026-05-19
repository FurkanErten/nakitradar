# NakitRadar AI backend starter for Windows PowerShell
# Run this file from the backend folder:
#   .\start_backend_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "[NakitRadar] Backend baslatiliyor..." -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    Write-Host "[NakitRadar] .venv yok, Python 3.10 ile olusturuluyor..." -ForegroundColor Yellow
    py -3.10 -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

$env:PYTHONPATH="."
python -m uvicorn app.main:app --reload --port 8000
