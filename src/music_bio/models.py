import sys
from dataclasses import dataclass, field
from typing import NamedTuple


class LyricLine(NamedTuple):
    timestamp: float
    text: str


@dataclass(frozen=True)
class MediaTrack:
    title: str
    artist: str
    position: float
    app_id: str
    playback_status: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.artist.casefold().strip(), self.title.casefold().strip())


@dataclass
class Settings:
    api_id: int
    api_hash: str
    yandex_token: str | None
    min_bio_interval: float = 12.0
    check_interval: float = 3.0
    template: str = "🎧 {artist} — {title} | {lyric}"
    dry_run: bool = False
    no_lyrics: bool = False
    no_restore: bool = False
    source_hints: list[str] = field(
        default_factory=lambda: [
            "yandexmusic",
            "yandex.music",
            "yandex_music",
        ]
    )

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
