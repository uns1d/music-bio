import logging
import sys
from datetime import UTC, datetime
from typing import Any

from music_bio.models import MediaTrack

logger = logging.getLogger(__name__)

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


class WindowsMediaMonitor:
    def __init__(self, source_hints: list[str] | None = None) -> None:
        self._source_hints = source_hints or [
            "yandexmusic",
            "yandex.music",
            "yandex_music",
        ]
        self._manager: MediaManager | None = None

    async def start(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("WindowsMediaMonitor работает только в Windows.")
        if self._manager is None:
            self._manager = await MediaManager.request_async()

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
                }
            )

        return result

    async def get_active_track(self) -> MediaTrack | None:
        await self.start()
        assert self._manager is not None

        for session in self._manager.get_sessions():
            if not await self._matches_source(session):
                continue

            playback = session.get_playback_info()
            if not playback or playback.playback_status != PlaybackStatus.PLAYING:
                continue

            media = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            if not media or not media.title or timeline is None:
                continue

            return MediaTrack(
                title=media.title.strip(),
                artist=media.artist.strip() if media.artist else "",
                position=self._current_position(session, timeline),
                app_id=session.source_app_user_model_id or "",
                playback_status=self._status_name(playback.playback_status),
            )

        return None

    async def _matches_source(self, session: Any) -> bool:
        app_id = (session.source_app_user_model_id or "").casefold()
        if any(hint in app_id for hint in self._source_hints):
            return True

        try:
            media = await session.try_get_media_properties_async()
        except Exception:
            return False

        if not media or not media.title:
            return False

        title = media.title.casefold()
        return "яндекс музыка" in title or "yandex music" in title

    @staticmethod
    def _current_position(session: Any, timeline: Any) -> float:
        position = timeline.position.total_seconds()
        updated_at = timeline.last_updated_time

        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)
            elapsed = (datetime.now(UTC) - updated_at.astimezone(UTC)).total_seconds()
            playback = session.get_playback_info()
            rate = float(playback.playback_rate or 1.0) if playback else 1.0
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
