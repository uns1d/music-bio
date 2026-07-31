import contextlib
import json
import os
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from music_bio.models import Settings, SourceMode

_SERVICE_NAME = "Music Bio"


class SecretBackend(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> None: ...

    def delete(self, name: str) -> None: ...


class SystemSecretBackend:
    def get(self, name: str) -> str | None:
        import keyring

        return keyring.get_password(_SERVICE_NAME, name)

    def set(self, name: str, value: str) -> None:
        import keyring

        keyring.set_password(_SERVICE_NAME, name, value)

    def delete(self, name: str) -> None:
        import keyring
        from keyring.errors import PasswordDeleteError

        with contextlib.suppress(PasswordDeleteError):
            keyring.delete_password(_SERVICE_NAME, name)


class MemorySecretBackend:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def set(self, name: str, value: str) -> None:
        self._values[name] = value

    def delete(self, name: str) -> None:
        self._values.pop(name, None)


@dataclass
class UserPreferences:
    api_id: int = 0
    telegram_phone: str = ""
    source_mode: str = SourceMode.AUTO.value
    proxy_enabled: bool = False
    proxy_host: str = ""
    proxy_port: int = 443
    check_interval: float = 3.0
    min_bio_interval: float = 12.0
    template: str = "🎧 {artist} — {title} | {lyric}"
    lyrics_enabled: bool = True
    restore_bio: bool = True
    bridge_port: int = 8765
    overlay_mode: str = "card"
    overlay_opacity: float = 0.94
    overlay_always_on_top: bool = True
    overlay_click_through: bool = False
    overlay_x: int = -1
    overlay_y: int = -1
    overlay_card_width: int = 490
    overlay_card_height: int = 138
    overlay_strip_width: int = 570
    overlay_strip_height: int = 76
    overlay_orb_width: int = 188
    overlay_orb_height: int = 226
    animation_level: int = 2
    start_minimized: bool = False


class SettingsStore:
    def __init__(
        self,
        app_dir: Path | None = None,
        secrets_backend: SecretBackend | None = None,
    ) -> None:
        self.app_dir = app_dir or default_app_dir()
        self.config_path = self.app_dir / "settings.json"
        self.session_path = self.app_dir / "music_session"
        self._secrets = secrets_backend or SystemSecretBackend()
        self._preferences = self._load_preferences()

    @property
    def preferences(self) -> UserPreferences:
        return self._preferences

    def public_values(self) -> dict[str, object]:
        return asdict(self._preferences)

    def secret_value(self, name: str) -> str:
        value = self._secrets.get(name)
        if value is not None:
            return value
        return self._environment_fallback(name)

    def save_connections(
        self,
        *,
        api_id: int,
        phone: str,
        api_hash: str,
        yandex_token: str,
        source_mode: str,
        proxy_enabled: bool,
        proxy_host: str,
        proxy_port: int,
        proxy_secret: str,
        bridge_port: int,
        bridge_token: str,
    ) -> None:
        self._preferences.api_id = max(0, int(api_id))
        self._preferences.telegram_phone = phone.strip()
        self._preferences.source_mode = SourceMode(source_mode).value
        self._preferences.proxy_enabled = bool(proxy_enabled)
        self._preferences.proxy_host = proxy_host.strip()
        self._preferences.proxy_port = int(proxy_port)
        self._preferences.bridge_port = int(bridge_port)

        self._set_or_delete("telegram_api_hash", api_hash)
        self._set_or_delete("yandex_token", yandex_token)
        self._set_or_delete("proxy_secret", proxy_secret)
        self._set_or_delete("bridge_token", bridge_token)
        self.save()

    def update_preferences(self, **values: object) -> None:
        for name, value in values.items():
            if hasattr(self._preferences, name):
                setattr(self._preferences, name, value)
        self.save()

    def ensure_bridge_token(self) -> str:
        token = self.secret_value("bridge_token")
        if token:
            return token
        token = secrets.token_urlsafe(32)
        self._secrets.set("bridge_token", token)
        return token

    def set_secret(self, name: str, value: str) -> None:
        allowed = {
            "telegram_api_hash",
            "yandex_token",
            "proxy_secret",
            "bridge_token",
        }
        if name not in allowed:
            raise ValueError(f"Неизвестный секрет: {name}")
        self._set_or_delete(name, value)

    def runtime_settings(self, *, dry_run: bool = False) -> Settings:
        preferences = self._preferences
        return Settings(
            api_id=preferences.api_id,
            api_hash=self.secret_value("telegram_api_hash"),
            yandex_token=self.secret_value("yandex_token") or None,
            telegram_phone=preferences.telegram_phone,
            min_bio_interval=max(1.0, float(preferences.min_bio_interval)),
            check_interval=max(1.0, float(preferences.check_interval)),
            template=preferences.template,
            dry_run=dry_run,
            no_lyrics=not preferences.lyrics_enabled,
            no_restore=not preferences.restore_bio,
            source_mode=SourceMode(preferences.source_mode),
            proxy_enabled=preferences.proxy_enabled,
            proxy_host=preferences.proxy_host,
            proxy_port=preferences.proxy_port,
            proxy_secret=self.secret_value("proxy_secret"),
            browser_bridge_port=preferences.bridge_port,
            browser_bridge_token=self.ensure_bridge_token(),
            session_path=str(self.session_path),
        )

    def save(self) -> None:
        self.app_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix(".tmp")
        payload = json.dumps(
            asdict(self._preferences),
            ensure_ascii=False,
            indent=2,
        )
        temporary.write_text(payload + "\n", encoding="utf-8")
        temporary.replace(self.config_path)

    def _load_preferences(self) -> UserPreferences:
        load_dotenv()
        if not self.config_path.exists():
            preferences = UserPreferences()
            raw_api_id = os.getenv("TELEGRAM_API_ID", "")
            if raw_api_id.isdigit():
                preferences.api_id = int(raw_api_id)
            preferences.telegram_phone = os.getenv("TELEGRAM_PHONE", "").strip()
            preferences.proxy_host = os.getenv("TELEGRAM_PROXY_HOST", "").strip()
            raw_proxy_port = os.getenv("TELEGRAM_PROXY_PORT", "")
            if raw_proxy_port.isdigit():
                preferences.proxy_port = int(raw_proxy_port)
            preferences.proxy_enabled = bool(
                preferences.proxy_host
                or raw_proxy_port
                or os.getenv("TELEGRAM_PROXY_SECRET", "").strip()
            )
            raw_bridge_port = os.getenv("MUSIC_BIO_BRIDGE_PORT", "")
            if raw_bridge_port.isdigit():
                preferences.bridge_port = int(raw_bridge_port)
            return preferences

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UserPreferences()

        defaults = asdict(UserPreferences())
        values = {name: raw.get(name, default) for name, default in defaults.items()}
        try:
            values["source_mode"] = SourceMode(values["source_mode"]).value
        except ValueError:
            values["source_mode"] = SourceMode.AUTO.value
        return UserPreferences(**values)

    def _set_or_delete(self, name: str, value: str) -> None:
        normalized = value.strip()
        if normalized:
            self._secrets.set(name, normalized)
        else:
            self._secrets.delete(name)

    @staticmethod
    def _environment_fallback(name: str) -> str:
        variables = {
            "telegram_api_hash": "TELEGRAM_API_HASH",
            "yandex_token": "YANDEX_MUSIC_TOKEN",
            "proxy_secret": "TELEGRAM_PROXY_SECRET",
            "bridge_token": "MUSIC_BIO_BRIDGE_TOKEN",
        }
        variable = variables.get(name)
        return os.getenv(variable, "").strip() if variable else ""


def default_app_dir() -> Path:
    root = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
    if root:
        return Path(root) / "Music Bio"
    return Path.home() / ".music-bio"


def parse_mtproxy_url(value: str) -> tuple[str, int, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "tg" or parsed.netloc.casefold() != "proxy":
        raise ValueError("Ожидается ссылка вида tg://proxy?server=...&port=...&secret=...")

    query = parse_qs(parsed.query)
    host = query.get("server", [""])[0].strip()
    port_value = query.get("port", [""])[0].strip()
    secret = query.get("secret", [""])[0].strip()
    if not host or not port_value or not secret:
        raise ValueError("В ссылке MTProxy отсутствуют server, port или secret.")

    try:
        port = int(port_value)
    except ValueError as error:
        raise ValueError("Порт MTProxy должен быть целым числом.") from error
    if not 1 <= port <= 65535:
        raise ValueError("Порт MTProxy должен быть в диапазоне 1–65535.")
    return host, port, secret
