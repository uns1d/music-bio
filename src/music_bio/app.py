import asyncio
import contextlib
import logging
import sys

from music_bio.config import parse_args
from music_bio.lyrics import YandexLyricsProvider
from music_bio.media import WindowsMediaMonitor
from music_bio.models import LyricLine, Settings
from music_bio.telegram_bio import TelegramBioUpdater, format_bio

logger = logging.getLogger(__name__)


class MusicBioApplication:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._media_monitor = WindowsMediaMonitor(settings.source_hints)
        self._bio_updater = TelegramBioUpdater(settings)
        self._lyrics_provider = (
            YandexLyricsProvider(settings.yandex_token)
            if settings.yandex_token and not settings.no_lyrics
            else None
        )

    async def run(self) -> None:
        try:
            await self._media_monitor.start()
            await self._bio_updater.start()
            logger.info("Отслеживание запущено. Для выхода нажмите Ctrl+C.")

            current_track_key: tuple[str, str] | None = None
            current_lrc: list[LyricLine] = []

            while True:
                try:
                    track = await self._media_monitor.get_active_track()

                    if track is None:
                        original_bio = self._bio_updater.original_bio
                        if original_bio is not None:
                            await self._bio_updater.update_bio(original_bio)
                        current_track_key = None
                        current_lrc = []
                    else:
                        if track.key != current_track_key:
                            current_lrc = []
                            if self._lyrics_provider is not None:
                                try:
                                    (
                                        _,
                                        current_lrc,
                                    ) = await self._lyrics_provider.get_lyrics_for_media(
                                        track.artist,
                                        track.title,
                                    )
                                except Exception:
                                    current_track_key = None
                                    logger.exception("Не удалось получить LRC.")
                                    await asyncio.sleep(5.0)
                                    continue

                            current_track_key = track.key
                            logger.info("Новый трек: %s — %s", track.artist, track.title)

                        lyric = ""
                        if self._lyrics_provider is not None and current_lrc:
                            lyric = self._lyrics_provider.get_current_line(
                                current_lrc,
                                track.position,
                            )

                        bio = format_bio(
                            self._settings.template,
                            track.artist,
                            track.title,
                            lyric,
                            limit=self._bio_updater.bio_limit,
                        )
                        await self._bio_updater.update_bio(bio)

                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("Ошибка в цикле отслеживания.")
                    await asyncio.sleep(5.0)

                await asyncio.sleep(self._settings.check_interval)
        finally:
            await self._bio_updater.stop()


async def list_sessions_cli(settings: Settings) -> None:
    monitor = WindowsMediaMonitor(settings.source_hints)
    sessions = await monitor.get_all_sessions()

    print("\n--- Медиасессии Windows GSMTC ---")
    if not sessions:
        print("Активные медиасессии не найдены.")
        return

    for index, session in enumerate(sessions, 1):
        print(f"[{index}] App ID: {session['app_id']}")
        print(f"    Статус: {session['playback_status']}")
        print(f"    Трек:   {session['artist']} — {session['title']}\n")


def main() -> None:
    parsed, settings = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if parsed.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if sys.platform != "win32":
        print("Ошибка: Music Bio работает только в Windows 10/11.")
        sys.exit(1)

    if parsed.list_sessions:
        asyncio.run(list_sessions_cli(settings))
        return

    app = MusicBioApplication(settings)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(app.run())


if __name__ == "__main__":
    main()
