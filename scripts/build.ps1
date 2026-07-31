$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

$python = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Окружение не найдено. Сначала выполните .\scripts\install.ps1"
}

& $python -m pip install nuitka ordered-set zstandard
& ".\.venv\Scripts\pyside6-deploy.exe" main.py `
    --name MusicBio `
    --force

if (-not (Test-Path ".\MusicBio.exe")) {
    throw "MusicBio.exe не найден после сборки."
}

$projectVersion = (
    Select-String -Path ".\pyproject.toml" `
        -Pattern '^version = "([^"]+)"$'
).Matches[0].Groups[1].Value
$extensionVersion = (
    Get-Content ".\browser-extension\manifest.json" -Raw |
        ConvertFrom-Json
).version
$releaseDir = Join-Path $projectRoot "release"
$extensionStage = Join-Path $env:TEMP (
    "music-bio-extension-" + [guid]::NewGuid().ToString("N")
)

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
Copy-Item ".\MusicBio.exe" `
    (Join-Path $releaseDir "MusicBio-$projectVersion-Windows.exe") `
    -Force

try {
    New-Item -ItemType Directory -Path $extensionStage | Out-Null
    $extensionFiles = @(
        "README.md",
        "background.js",
        "content.js",
        "manifest.json",
        "options.css",
        "options.html",
        "options.js",
        "page-player.js"
    )
    foreach ($file in $extensionFiles) {
        Copy-Item (Join-Path ".\browser-extension" $file) `
            (Join-Path $extensionStage $file)
    }

    $extensionArchive = Join-Path $releaseDir `
        "MusicBio-Yandex-Bridge-$extensionVersion.zip"
    Compress-Archive -Path (Join-Path $extensionStage "*") `
        -DestinationPath $extensionArchive `
        -Force
} finally {
    if (Test-Path $extensionStage) {
        Remove-Item $extensionStage -Recurse -Force
    }
}

Write-Host ""
Write-Host "Сборка завершена. Файлы для GitHub находятся в папке release." `
    -ForegroundColor Green
