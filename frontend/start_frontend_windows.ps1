# NakitRadar AI frontend starter for Windows PowerShell
# Run from frontend folder:
#   .\start_frontend_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "[NakitRadar] Frontend baslatiliyor..." -ForegroundColor Cyan
Write-Host "[NakitRadar] Node:" (node -v) " npm:" (npm -v)

# npm 11.x bazi Windows makinelerde "Exit handler never called" hatasi verebiliyor.
# Ilk kurulum basarisiz olursa npm 10'u kullanici klasorune kurup tekrar dener.
try {
    npm install --no-audit --no-fund
}
catch {
    Write-Host "[NakitRadar] npm install basarisiz. npm 10 kullanici klasorune kuruluyor..." -ForegroundColor Yellow
    npm config set prefix "$env:APPDATA\npm"
    $env:Path = "$env:APPDATA\npm;$env:Path"
    npm install -g npm@10
    npm install --no-audit --no-fund
}

npm run dev
