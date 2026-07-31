$ErrorActionPreference = "Stop"

$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock] $Command,

        [Parameter(Mandatory = $true)]
        [string] $Description
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

$venvRoot = (Resolve-Path ".\.venv" -ErrorAction SilentlyContinue).Path
if (-not $venvRoot) {
    throw "Virtual environment not found. Run .\scripts\install.ps1 first."
}

$venvScripts = Join-Path $venvRoot "Scripts"
$python = Join-Path $venvScripts "python.exe"
if (-not (Test-Path $python)) {
    throw "Python executable not found in .venv. Run .\scripts\install.ps1 first."
}

$deploy = Join-Path $venvScripts "pyside6-deploy.exe"
$qmlScanner = Join-Path $venvScripts "pyside6-qmlimportscanner.exe"
foreach ($tool in @($deploy, $qmlScanner)) {
    if (-not (Test-Path $tool)) {
        throw "Required PySide6 tool not found: $tool"
    }
}

$env:VIRTUAL_ENV = $venvRoot
$env:PATH = "$venvScripts;$env:PATH"

$buildPackages = @(
    "setuptools>=70"
    "nuitka==4.1.3"
    "ordered-set==4.1.0"
    "zstandard==0.25.0"
)
Invoke-Checked {
    & $python -m pip install --upgrade @buildPackages
} "Build dependency installation"

$buildRoot = Join-Path $projectRoot "build\release-stage"
$sourceArchive = Join-Path $buildRoot "source.zip"
$sourceRoot = Join-Path $buildRoot "source"
$deployRoot = Join-Path $buildRoot "deploy"
if (Test-Path $buildRoot) {
    Remove-Item $buildRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $sourceRoot -Force | Out-Null
New-Item -ItemType Directory -Path $deployRoot -Force | Out-Null

Invoke-Checked {
    git archive --format=zip --output=$sourceArchive HEAD main.py src/music_bio
} "Clean source export"
Expand-Archive -Path $sourceArchive -DestinationPath $sourceRoot -Force
Copy-Item (Join-Path $sourceRoot "main.py") $deployRoot
Copy-Item (Join-Path $sourceRoot "src\music_bio") `
    (Join-Path $deployRoot "music_bio") `
    -Recurse
Copy-Item ".\scripts\pysidedeploy.spec" $deployRoot

$deployMain = Join-Path $deployRoot "main.py"
$deployConfig = Join-Path $deployRoot "pysidedeploy.spec"
Invoke-Checked {
    & $deploy $deployMain `
        --config-file $deployConfig `
        --nuitka-version 4.1.3 `
        --force
} "PySide6 deployment"

$builtExecutable = Join-Path $deployRoot "MusicBio.exe"
if (-not (Test-Path $builtExecutable)) {
    throw "MusicBio.exe was not found after the build."
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
$extensionStage = Join-Path $buildRoot "extension"

New-Item -ItemType Directory -Path $releaseDir -Force | Out-Null
Copy-Item $builtExecutable `
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
        Remove-Item -LiteralPath $extensionStage -Recurse -Force
    }
}

Write-Host ""
Write-Host "Build complete. GitHub release files are in the release directory." `
    -ForegroundColor Green
