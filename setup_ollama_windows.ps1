# NakitRadar AI - Ollama local AI setup helper
# Run from project root with PowerShell:
#   .\setup_ollama_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "[NakitRadar] Ollama kontrol ediliyor..." -ForegroundColor Cyan

function Add-OllamaPathForCurrentSession {
    $candidatePaths = @(
        "$env:LOCALAPPDATA\Programs\Ollama",
        "C:\Program Files\Ollama"
    )

    foreach ($p in $candidatePaths) {
        if (Test-Path $p) {
            $env:Path = "$p;$env:Path"
        }
    }
}

Add-OllamaPathForCurrentSession

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "[NakitRadar] Ollama bulunamadi." -ForegroundColor Yellow

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "[NakitRadar] winget bulundu, Ollama kuruluyor..." -ForegroundColor Cyan
        winget install --id Ollama.Ollama -e
        Write-Host "[NakitRadar] Kurulum bittiyse PowerShell'i kapatip tekrar ac ve scripti yeniden calistir." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "[NakitRadar] winget de bulunamadi. Manuel kurulum sayfasi aciliyor..." -ForegroundColor Yellow
    Start-Process "https://ollama.com/download/windows"
    Write-Host "[NakitRadar] Installer'i kur. Sonra PowerShell'i kapatip tekrar ac ve su komutu calistir:" -ForegroundColor Yellow
    Write-Host "ollama pull qwen2.5:3b" -ForegroundColor Green
    exit 0
}

$model = "qwen2.5:3b"
Write-Host "[NakitRadar] Model indiriliyor/kontrol ediliyor: $model" -ForegroundColor Cyan
ollama pull $model

Write-Host "[NakitRadar] Ollama modelleri:" -ForegroundColor Cyan
ollama list

Write-Host "[NakitRadar] Tamam. backend\.env icinde su ayarlari kullan:" -ForegroundColor Green
Write-Host "LLM_PROVIDER=auto"
Write-Host "OLLAMA_BASE_URL=http://127.0.0.1:11434"
Write-Host "OLLAMA_MODEL=$model"
Write-Host "OPENAI_API_KEY="
