import logging
import sys
from datetime import UTC, datetime
from typing import Any, Protocol

from music_bio.models import AppEvent, EventCallback, MediaTrack, Settings, SourceMode

logger = logging.getLogger(__name__)

_GENERIC_BROWSER_IDS = (
    "chrome",
    "msedge",
    "firefox",
    "opera",
    "brave",
    "vivaldi",
    "arc.exe",
)

if sys.platform == "win32":
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    )
    from winsdk.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
else:
    MediaManager = Any
    PlaybackStatus = Any


class TrackSource(Protocol):
    async def start(self) -> None: ...

    async def get_active_track(self) -> MediaTrack | None: ...

    async def stop(self) -> None: ...


class WindowsMediaMonitor:
    def __init__(self, source_hints: list[str] | None = None) -> None:
        hints = source_hints or ["yandexmusic", "yandex.music", "yandex_music"]
        self._source_hints = tuple(hint.casefold() for hint in hints)
        self._manager: MediaManager | None = None

    async def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("WindowsMediaMonitor работает только в Windows.")
        if self._manager is None:
            self._manager = await MediaManager.request_async()

    async def stop(self) -> None:
        self._manager = None

    async def get_all_sessions(self) -> list[dict[str, Any]]:
        await self.start()
        assert self._manager is not None

        result: list[dict[str, Any]] = []
        for session in self._manager.get_sessions():
            app_id = session.source_app_user_model_id or ""
            playback = session.get_playback_info()
            status = self._status_name(playback.playback_status) if playback else "UNKNOWN"
            title = "N/A"
            artist = "N/A"

            try:
                media = await session.try_get_media_properties_async()
                if media:
                    title = media.title or "N/A"
                    artist = media.artist or "N/A"
            except Exception as error:
                logger.debug("Не удалось прочитать сессию %s: %s", app_id, error)

            result.append(
                {
                    "app_id": app_id,
                    "playback_status": status,
                    "title": title,
                    "artist": artist,
                    "is_yandex": self._matches_app_id(app_id),
                }
            )

        return result

    async def get_active_track(self) -> MediaTrack | None:
        await self.start()
        assert self._manager is not None

        for session in self._manager.get_sessions():
            app_id = session.source_app_user_model_id or ""
            if not self._matches_app_id(app_id):
                continue

            playback = session.get_playback_info()
            if not playback or playback.playback_status not in {
                PlaybackStatus.PLAYING,
                PlaybackStatus.PAUSED,
            }:
                continue

            media = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            if not media or not media.title or timeline is None:
                continue

            return MediaTrack(
                title=media.title.strip(),
                artist=media.artist.strip() if media.artist else "",
                position=self._current_position(session, timeline),
                duration=max(0.0, timeline.end_time.total_seconds()),
                app_id=app_id,
                playback_status=self._status_name(playback.playback_status),
                source_name="Приложение Яндекс Музыки",
            )

        return None

    def _matches_app_id(self, app_id: str) -> bool:
        normalized = app_id.casefold()
        if any(browser_id in normalized for browser_id in _GENERIC_BROWSER_IDS):
            return False
        return any(hint in normalized for hint in self._source_hints)

    @staticmethod
    def _current_position(session: Any, timeline: Any) -> float:
        position = timeline.position.total_seconds()
        updated_at = timeline.last_updated_time

        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - updated_at.astimezone(UTC)).total_seconds()
            playback = session.get_playback_info()
            if playback and playback.playback_status == PlaybackStatus.PLAYING:
                rate = float(playback.playback_rate or 1.0)
                position += max(0.0, elapsed) * rate

        duration = timeline.end_time.total_seconds()
        if duration > 0:
            position = min(position, duration)

        return max(0.0, position)

    @staticmethod
    def _status_name(status: Any) -> str:
        name = getattr(status, "name", None)
        if name:
            return str(name).upper()
        return str(status).rsplit(".", 1)[-1].upper()


class AutomaticTrackSource:
    def __init__(self, sources: list[TrackSource]) -> None:
        self._sources = sources
        self._active_sources: list[TrackSource] = []

    async def start(self) -> None:
        self._active_sources = []
        for source in self._sources:
            try:
                await source.start()
            except Exception:
                logger.exception(
                    "Источник %s недоступен.",
                    type(source).__name__,
                )
            else:
                self._active_sources.append(source)
        if not self._active_sources:
            raise RuntimeError("Не удалось запустить ни один источник Яндекс Музыки.")

    async def get_active_track(self) -> MediaTrack | None:
        for source in self._active_sources:
            try:
                track = await source.get_active_track()
            except Exception:
                logger.exception(
                    "Не удалось прочитать источник %s.",
                    type(source).__name__,
                )
                continue
            if track is not None:
                return track
        return None

    async def stop(self) -> None:
        for source in reversed(self._active_sources):
            try:
                await source.stop()
            except Exception:
                logger.exception("Не удалось остановить источник музыки.")
        self._active_sources = []


def create_track_source(
    settings: Settings,
    event_callback: EventCallback | None = None,
) -> TrackSource:
    desktop = WindowsMediaMonitor(settings.source_hints)
    if settings.source_mode == SourceMode.DESKTOP:
        return desktop

    from music_bio.browser_bridge import BrowserBridgeSource

    def report_browser_status(connected: bool, message: str) -> None:
        if event_callback is None:
            return
        event_callback(
            AppEvent(
                kind="connection",
                service="browser",
                connected=connected,
                message=message,
            )
        )

    browser = BrowserBridgeSource(
        port=settings.browser_bridge_port,
        token=settings.browser_bridge_token,
        status_callback=report_browser_status,
    )
    if settings.source_mode == SourceMode.BROWSER:
        return browser
    return AutomaticTrackSource([browser, desktop])
