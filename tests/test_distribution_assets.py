import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_qml_entrypoint_and_overlay_are_packaged():
    qml = ROOT / "src" / "music_bio" / "gui" / "qml"

    assert (qml / "Main.qml").is_file()
    assert (qml / "OverlayWindow.qml").is_file()
    assert (qml / "SoftComboBox.qml").is_file()
    assert (qml / "SoftSlider.qml").is_file()
    assert (qml / "LyricPanel.qml").is_file()
    assert "OverlayWindow" in (qml / "Main.qml").read_text(encoding="utf-8")


def test_extension_permissions_are_limited_to_yandex_music_and_localhost():
    manifest_path = ROOT / "browser-extension" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["version"] == "0.2.3"
    content_matches = manifest["content_scripts"][0]["matches"]
    hosts = manifest["host_permissions"]

    assert content_matches == [
        "https://music.yandex.ru/*",
        "https://music.yandex.com/*",
    ]
    assert "http://127.0.0.1/*" in hosts
    assert all(item != "*://*/*" for item in hosts)
    assert manifest["content_scripts"][0]["js"] == ["page-player.js"]
    assert manifest["content_scripts"][0]["world"] == "MAIN"


def test_release_build_creates_app_and_extension_artifacts():
    script = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
    deploy_config = (ROOT / "scripts" / "pysidedeploy.spec").read_text(encoding="utf-8")

    assert "MusicBio-$projectVersion-Windows.exe" in script
    assert "MusicBio-Yandex-Bridge-$extensionVersion.zip" in script
    assert '$env:PATH = "$venvScripts;$env:PATH"' in script
    assert 'Join-Path $venvScripts "pyside6-qmlimportscanner.exe"' in script
    assert "setuptools>=70" in script
    assert "git archive --format=zip" in script
    assert 'Join-Path $projectRoot "build\\release-stage"' in script
    assert 'Join-Path $buildRoot "extension"' in script
    assert "Remove-Item -LiteralPath $extensionStage" in script
    assert "--config-file $deployConfig" in script
    assert "Nuitka==4.1.3" in deploy_config
    assert "--windows-console-mode=disable" in deploy_config
    assert "--assume-yes-for-downloads" in deploy_config
    assert "release" in (ROOT / ".gitignore").read_text(encoding="utf-8")


def test_overlay_is_independent_movable_and_resizable():
    qml = (ROOT / "src" / "music_bio" / "gui" / "qml" / "OverlayWindow.qml").read_text(
        encoding="utf-8"
    )

    assert "transientParent: null" in qml
    assert "startSystemMove()" in qml
    assert "startSystemResize" in qml
    assert "saveOverlayGeometry" in qml
    assert "overlay.locked" not in qml
    assert 'text: overlay.locked ? "◆"' not in qml


def test_check_script_propagates_external_command_failures():
    script = (ROOT / "scripts" / "check.ps1").read_text(encoding="utf-8")

    assert "function Invoke-Checked" in script
    assert "$LASTEXITCODE -ne 0" in script
    assert 'Invoke-Checked { & $python -m pytest } "Pytest"' in script


def test_ci_uses_one_headless_qt_session_on_each_python_version():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "QT_QPA_PLATFORM: offscreen" in workflow
    assert "QT_QUICK_BACKEND: software" in workflow
    assert "fail-fast: false" in workflow
