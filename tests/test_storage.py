import json

import pytest

from music_bio.models import SourceMode
from music_bio.storage import (
    MemorySecretBackend,
    SettingsStore,
    parse_mtproxy_url,
)


def test_secrets_are_not_written_to_settings_json(tmp_path):
    secrets = MemorySecretBackend()
    store = SettingsStore(tmp_path, secrets)

    store.save_connections(
        api_id=12345,
        phone="+79990000000",
        api_hash="telegram-secret",
        yandex_token="yandex-secret",
        source_mode="browser",
        proxy_enabled=True,
        proxy_host="proxy.example.com",
        proxy_port=443,
        proxy_secret="proxy-secret",
        bridge_port=8765,
        bridge_token="bridge-secret",
    )

    raw = store.config_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    settings = store.runtime_settings()

    assert "telegram-secret" not in raw
    assert "yandex-secret" not in raw
    assert "proxy-secret" not in raw
    assert "bridge-secret" not in raw
    assert data["api_id"] == 12345
    assert settings.api_hash == "telegram-secret"
    assert settings.yandex_token == "yandex-secret"
    assert settings.source_mode is SourceMode.BROWSER


def test_bridge_token_is_generated_once(tmp_path):
    store = SettingsStore(tmp_path, MemorySecretBackend())

    first = store.ensure_bridge_token()
    second = store.ensure_bridge_token()

    assert first
    assert first == second
    assert len(first) >= 32


def test_overlay_keeps_separate_size_for_each_mode(tmp_path):
    store = SettingsStore(tmp_path, MemorySecretBackend())
    store.update_preferences(
        overlay_x=120,
        overlay_y=80,
        overlay_card_width=640,
        overlay_card_height=220,
        overlay_strip_width=700,
        overlay_strip_height=90,
        overlay_orb_width=240,
        overlay_orb_height=300,
    )

    restored = SettingsStore(tmp_path, MemorySecretBackend()).preferences

    assert (restored.overlay_x, restored.overlay_y) == (120, 80)
    assert (restored.overlay_card_width, restored.overlay_card_height) == (640, 220)
    assert (restored.overlay_strip_width, restored.overlay_strip_height) == (700, 90)
    assert (restored.overlay_orb_width, restored.overlay_orb_height) == (240, 300)


def test_existing_env_is_used_for_first_gui_launch(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("TELEGRAM_PHONE", "+79990000000")
    monkeypatch.setenv("TELEGRAM_PROXY_HOST", "proxy.example.com")
    monkeypatch.setenv("TELEGRAM_PROXY_PORT", "443")
    monkeypatch.setenv("TELEGRAM_PROXY_SECRET", "secret")

    store = SettingsStore(tmp_path, MemorySecretBackend())

    assert store.preferences.api_id == 12345
    assert store.preferences.telegram_phone == "+79990000000"
    assert store.preferences.proxy_enabled
    assert store.preferences.proxy_host == "proxy.example.com"
    assert store.preferences.proxy_port == 443


def test_unknown_secret_name_is_rejected(tmp_path):
    store = SettingsStore(tmp_path, MemorySecretBackend())

    with pytest.raises(ValueError, match="Неизвестный секрет"):
        store.set_secret("not_allowed", "secret")


def test_parse_mtproxy_url():
    host, port, secret = parse_mtproxy_url(
        "tg://proxy?server=proxy.example.com&port=443&secret=abcdef"
    )

    assert host == "proxy.example.com"
    assert port == 443
    assert secret == "abcdef"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://example.com",
        "tg://proxy?server=host",
        "tg://proxy?server=host&port=70000&secret=x",
    ],
)
def test_invalid_mtproxy_url(value):
    with pytest.raises(ValueError):
        parse_mtproxy_url(value)
