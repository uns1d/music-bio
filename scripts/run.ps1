$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path ".venv\Scripts\pythonw.exe")) {
    throw "Окружение не найдено. Сначала выполните .\scripts\install.ps1"
}

Start-Process -FilePath ".\.venv\Scripts\pythonw.exe" `
    -ArgumentList "-m", "music_bio"
