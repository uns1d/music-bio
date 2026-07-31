$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Окружение не найдено. Сначала выполните .\scripts\install.ps1"
}

& $python -m compileall src tests
& $python -m ruff check .
& $python -m ruff format --check .
Get-ChildItem src/music_bio/gui/qml/*.qml |
    ForEach-Object {
        & ".\.venv\Scripts\pyside6-qmllint.exe" `
            --unqualified disable `
            --max-warnings 0 `
            $_.FullName
    }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    node --check browser-extension/background.js
    node --check browser-extension/content.js
    node --check browser-extension/options.js
    node --check browser-extension/page-player.js
    node browser-extension/tests/content.test.cjs
    node browser-extension/tests/options.test.cjs
    node browser-extension/tests/page-player.test.cjs
} else {
    Write-Warning "Node.js не найден: тесты браузерного расширения пропущены."
}

& $python -m pytest

Write-Host ""
Write-Host "Все проверки пройдены." -ForegroundColor Green
