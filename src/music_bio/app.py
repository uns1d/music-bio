import asyncio
import contextlib
import logging
import sys

from music_bio.config import parse_args
from music_bio.lyrics import YandexLyricsProvider, get_lyric_context
from music_bio.media import TrackSource, WindowsMediaMonitor, create_track_source
from music_bio.models import (
    AppEvent,
    ApplicationState,
    EventCallback,
    LyricLine,
    MediaTrack,
    Settings,
)
from music_bio.telegram_bio import TelegramBioUpdater, format_bio

logger = logging.getLogger(__name__)


class _LyricsLoadError(RuntimeError):
    pass


class MusicBioApplication:
    def __init__(
        self,
        settings: Settings,
        *,
        media_source: TrackSource | None = None,
        bio_updater: TelegramBioUpdater | None = None,
        lyrics_provider: YandexLyricsProvider | None = None,
        event_callback: EventCallback | None = None,
    ) -> None:
        self._settings = settings
        self._event_callback = event_callback
        self._poll_interval = (
            min(settings.check_interval, 0.25)
            if event_callback is not None
            else settings.check_interval
        )
        self._stop_event = asyncio.Event()
        self._media_monitor = media_source or create_track_source(
            settings,
            event_callback=event_callback,
        )
        self._bio_updater = bio_updater or TelegramBioUpdater(
            settings,
            event_callback=event_callback,
        )
        if isinstance(self._bio_updater, TelegramBioUpdater):
            self._bio_updater.set_stop_event(self._stop_event)
        self._lyrics_provider = lyrics_provider
        if self._lyrics_provider is None and settings.yandex_token and not settings.no_lyrics:
            self._lyrics_provider = YandexLyricsProvider(settings.yandex_token)

    def request_stop(self) -> None:
        self._stop_event.set()

    async def _sleep_or_stop(self, delay: float) -> bool:
        if self._stop_event.is_set():
            return True

        sleep_task = asyncio.create_task(asyncio.sleep(delay))
        stop_task = asyncio.create_task(self._stop_event.wait())
        tasks = (sleep_task, stop_task)
        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            return stop_task in done and self._stop_event.is_set()
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _fetch_lyrics_or_stop(
        self,
        artist: str,
        title: str,
    ) -> tuple[str | None, list[LyricLine]] | None:
        if self._lyrics_provider is None or self._stop_event.is_set():
            return None

        lyrics_task = asyncio.create_task(self._lyrics_provider.get_lyrics_for_media(artist, title))
        stop_task = asyncio.create_task(self._stop_event.wait())
        tasks = (lyrics_task, stop_task)
        try:
            done, _ = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if stop_task in done and self._stop_event.is_set():
                return None
            return await lyrics_task
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def run(self) -> None:
        self._emit_state(ApplicationState.STARTING, "Подключение сервисов")
        try:
            await self._media_monitor.start()
            self._emit_connection("source", True, "Источники музыки запущены")
            await self._bio_updater.start()
            self._emit_state(ApplicationState.RUNNING, "Music Bio работает")
            logger.info("Отслеживание запущено. Для выхода нажмите Ctrl+C.")
            await self._run_loop()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._emit_state(ApplicationState.ERROR, str(error))
            raise
        finally:
            self._emit_state(ApplicationState.STOPPING, "Восстановление Bio")
            try:
                await self._bio_updater.stop()
            finally:
                try:
                    await self._media_monitor.stop()
                finally:
                    self._emit_connection("yandex", False, "Воспроизведение остановлено")
                    self._emit_connection("source", False, "Источники музыки остановлены")
                    self._emit_state(ApplicationState.STOPPED, "Остановлено")

    async def _run_loop(self) -> None:
        current_track_key: tuple[str, str] | None = None
        current_lrc: list[LyricLine] = []
        playback_detected = False

        while not self._stop_event.is_set():
            try:
                track = await self._media_monitor.get_active_track()
                if track is None:
                    if playback_detected:
                        self._emit_connection(
                            "yandex",
                            False,
                            "Активный трек Яндекс Музыки не найден",
                        )
                        playback_detected = False
                    if current_track_key is not None:
                        self._emit(AppEvent(kind="track"))
                    original_bio = self._bio_updater.original_bio
                    if original_bio is not None:
                        await self._bio_updater.update_bio(original_bio)
                    current_track_key = None
                    current_lrc = []
                else:
                    if not playback_detected:
                        self._emit_connection(
                            "yandex",
                            True,
                            f"Найден трек через: {track.source_name}",
                        )
                        playback_detected = True
                    if track.key != current_track_key:
                        current_track_key = track.key
                        current_lrc = []
                        logger.info("Новый трек: %s — %s", track.artist, track.title)
                        if self._lyrics_provider is not None:
                            await self._publish_track(track, current_lrc)
                        current_lrc = await self._load_lyrics(track.artist, track.title)
                        if self._stop_event.is_set():
                            break

                    await self._publish_track(track, current_lrc)
            except asyncio.CancelledError:
                raise
            except _LyricsLoadError:
                current_track_key = None
                current_lrc = []
                if await self._sleep_or_stop(5.0):
                    break
            except Exception:
                logger.exception("Ошибка в цикле отслеживания.")
                if await self._sleep_or_stop(5.0):
                    break

            if await self._sleep_or_stop(self._poll_interval):
                break

    async def _load_lyrics(self, artist: str, title: str) -> list[LyricLine]:
        if self._lyrics_provider is None:
            return []
        try:
            result = await self._fetch_lyrics_or_stop(artist, title)
            if result is None:
                return []
            _, lines = result
            self._emit_connection(
                "lyrics",
                True,
                "Синхронизированные тексты подключены",
            )
            return lines
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._emit_connection(
                "lyrics",
                False,
                "Сервис синхронизированных текстов недоступен",
            )
            logger.exception("Не удалось получить LRC.")
            raise _LyricsLoadError from error

    def _lyric_context(
        self,
        lines: list[LyricLine],
        position: float,
    ) -> tuple[str, str]:
        if self._lyrics_provider is None or not lines:
            return "", ""
        return get_lyric_context(lines, position)

    async def _publish_track(
        self,
        track: MediaTrack,
        lines: list[LyricLine],
    ) -> None:
        lyric, next_lyric = self._lyric_context(lines, track.position)
        bio = format_bio(
            self._settings.template,
            track.artist,
            track.title,
            lyric,
            limit=self._bio_updater.bio_limit,
        )
        await self._bio_updater.update_bio(bio)
        self._emit(
            AppEvent(
                kind="track",
                track=track,
                lyric=lyric,
                next_lyric=next_lyric,
                bio=bio,
            )
        )

    def _emit(self, event: AppEvent) -> None:
        if self._event_callback is None:
            return
        try:
            self._event_callback(event)
        except Exception:
            logger.exception("Обработчик события приложения завершился ошибкой.")

    def _emit_state(self, state: ApplicationState, message: str) -> None:
        self._emit(AppEvent(kind="state", state=state, message=message))

    def _emit_connection(self, service: str, connected: bool, message: str) -> None:
        self._emit(
            AppEvent(
                kind="connection",
                service=service,
                connected=connected,
                message=message,
            )
        )


async def list_sessions_cli(settings: Settings) -> None:
    monitor = WindowsMediaMonitor(settings.source_hints)
    sessions = await monitor.get_all_sessions()

    print("\n--- Медиасессии Windows GSMTC ---")
    if not sessions:
        print("Активные медиасессии не найдены.")
        return

    for index, session in enumerate(sessions, 1):
        marker = "Яндекс" if session["is_yandex"] else "игнорируется"
        print(f"[{index}] App ID: {session['app_id']} ({marker})")
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

    application = MusicBioApplication(settings)
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(application.run())


if __name__ == "__main__":
    main()
