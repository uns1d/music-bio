import sys
from dataclasses import dataclass, field
from enum import StrEnum
from typing import NamedTuple, Protocol


class LyricLine(NamedTuple):
    timestamp: float
    text: str


class SourceMode(StrEnum):
    DESKTOP = "desktop"
    BROWSER = "browser"
    AUTO = "auto"


class ApplicationState(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass(frozen=True)
class MediaTrack:
    title: str
    artist: str
    position: float
    app_id: str
    playback_status: str
    duration: float = 0.0
    artwork_url: str = ""
    source_name: str = "Яндекс Музыка"

    @property
    def key(self) -> tuple[str, str]:
        return (self.artist.casefold().strip(), self.title.casefold().strip())


@dataclass(frozen=True)
class AppEvent:
    kind: str
    state: ApplicationState | None = None
    message: str = ""
    track: MediaTrack | None = None
    lyric: str = ""
    next_lyric: str = ""
    bio: str = ""
    service: str = ""
    connected: bool | None = None


class EventCallback(Protocol):
    def __call__(self, event: AppEvent) -> None: ...


@dataclass
class Settings:
    api_id: int
    api_hash: str
    yandex_token: str | None
    telegram_phone: str = ""
    min_bio_interval: float = 12.0
    check_interval: float = 3.0
    template: str = "🎧 {artist} — {title} | {lyric}"
    dry_run: bool = False
    no_lyrics: bool = False
    no_restore: bool = False
    source_mode: SourceMode = SourceMode.DESKTOP
    source_hints: list[str] = field(
        default_factory=lambda: [
            "yandexmusic",
            "yandex.music",
            "yandex_music",
        ]
    )
    proxy_enabled: bool = False
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_secret: str = ""
    browser_bridge_port: int = 8765
    browser_bridge_token: str = ""
    session_path: str = "music_session"

    def validate(self) -> None:
        if not self.dry_run:
            if self.api_id <= 0:
                print("Ошибка: TELEGRAM_API_ID не задан или имеет неверный формат.")
                sys.exit(1)
            if not self.api_hash:
                print("Ошибка: TELEGRAM_API_HASH не задан.")
                sys.exit(1)

        if not self.no_lyrics and not self.dry_run and not self.yandex_token:
            print("Ошибка: YANDEX_MUSIC_TOKEN не задан. Укажите токен или используйте --no-lyrics.")
            sys.exit(1)

        if self.proxy_enabled:
            if not self.proxy_host or not self.proxy_secret:
                print("Ошибка: для MTProxy необходимо указать сервер и secret.")
                sys.exit(1)
            if not 1 <= self.proxy_port <= 65535:
                print("Ошибка: порт MTProxy должен быть в диапазоне 1–65535.")
                sys.exit(1)

        if self.source_mode in {SourceMode.BROWSER, SourceMode.AUTO}:
            if not self.browser_bridge_token:
                print("Ошибка: MUSIC_BIO_BRIDGE_TOKEN не задан.")
                sys.exit(1)
            if not 1024 <= self.browser_bridge_port <= 65535:
                print("Ошибка: порт браузерного моста должен быть от 1024 до 65535.")
                sys.exit(1)

        try:
            formatted = self.template.format(artist="A", title="T", lyric="L")
        except (KeyError, ValueError) as error:
            print(
                "Ошибка шаблона Bio. Допустимые поля: "
                "{artist}, {title}, {lyric}. "
                f"Подробности: {error}"
            )
            sys.exit(1)

        if not formatted.strip():
            print("Ошибка: шаблон Bio не должен быть пустым.")
            sys.exit(1)
