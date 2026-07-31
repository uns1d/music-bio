import pytest

from music_bio.config import parse_args


def test_invalid_bridge_port_has_readable_error(monkeypatch, capsys):
    monkeypatch.setenv("MUSIC_BIO_BRIDGE_PORT", "not-a-port")
    monkeypatch.setenv("MUSIC_BIO_BRIDGE_TOKEN", "bridge-token")

    with pytest.raises(SystemExit):
        parse_args(["--dry-run", "--source", "browser"])

    assert "порт браузерного моста" in capsys.readouterr().out


def test_default_bridge_port_is_valid(monkeypatch):
    monkeypatch.delenv("MUSIC_BIO_BRIDGE_PORT", raising=False)

    _, settings = parse_args(["--dry-run"])

    assert settings.browser_bridge_port == 8765
