$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command,

        [Parameter(Mandatory = $true)]
        [string] $Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description завершилась с кодом $LASTEXITCODE."
    }
}

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Run .\scripts\install.ps1 first."
}

Invoke-Checked { & $python -m compileall src tests } "Python syntax check"
Invoke-Checked { & $python -m ruff check . } "Ruff check"
Invoke-Checked { & $python -m ruff format --check . } "Ruff format"
Get-ChildItem src/music_bio/gui/qml/*.qml |
    ForEach-Object {
        $qmlFile = $_.FullName
        Invoke-Checked {
            & ".\.venv\Scripts\pyside6-qmllint.exe" `
                --unqualified disable `
                --max-warnings 0 `
                $qmlFile
        } "QML lint: $($_.Name)"
    }

$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Invoke-Checked { node --check browser-extension/background.js } "Node syntax: background.js"
    Invoke-Checked { node --check browser-extension/content.js } "Node syntax: content.js"
    Invoke-Checked { node --check browser-extension/options.js } "Node syntax: options.js"
    Invoke-Checked { node --check browser-extension/page-player.js } "Node syntax: page-player.js"
    Invoke-Checked { node browser-extension/tests/content.test.cjs } "Content tests"
    Invoke-Checked { node browser-extension/tests/options.test.cjs } "Options tests"
    Invoke-Checked { node browser-extension/tests/page-player.test.cjs } "Page player tests"
} else {
    Write-Warning "Node.js not found; browser extension tests were skipped."
}

Invoke-Checked { & $python -m pytest } "Pytest"

Write-Host ""
Write-Host "All checks passed." -ForegroundColor Green
