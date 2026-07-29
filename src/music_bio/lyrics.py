import asyncio
import logging
import re
from collections import OrderedDict
from typing import Any

from yandex_music import Client
from yandex_music.exceptions import NotFoundError

from music_bio.models import LyricLine

logger = logging.getLogger(__name__)


def parse_lrc(lrc_text: str | None) -> list[LyricLine]:
    if not lrc_text:
        return []

    lines: list[LyricLine] = []
    offset_seconds = 0.0
    offset_match = re.search(r"\[offset:\s*([+-]?\d+)\]", lrc_text, re.IGNORECASE)

    if offset_match:
        offset_seconds = float(offset_match.group(1)) / 1000.0

    timestamp_pattern = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")

    for raw_line in lrc_text.splitlines():
        line = raw_line.strip()
        if not line or line.casefold().startswith("[offset:"):
            continue

        timestamps = timestamp_pattern.findall(line)
        text = timestamp_pattern.sub("", line).strip()
        if not timestamps or not text:
            continue

        for minutes, seconds in timestamps:
            timestamp = int(minutes) * 60 + float(seconds) + offset_seconds
            lines.append(LyricLine(max(0.0, timestamp), text))

    lines.sort(key=lambda item: item.timestamp)
    return lines


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold()))


def find_best_matching_track(
    results: list[Any],
    target_artist: str,
    target_title: str,
) -> Any | None:
    expected_title = normalize_text(target_title)
    expected_artist = normalize_text(target_artist)

    for track in results[:10]:
        if normalize_text(track.title or "") != expected_title:
            continue

        artists = {normalize_text(artist.name or "") for artist in (track.artists or [])}
        if not expected_artist or expected_artist in artists:
            return track

    return None


class YandexLyricsProvider:
    def __init__(self, token: str, cache_size: int = 100) -> None:
        self._token = token
        self._cache_size = cache_size
        self._client: Client | None = None
        self._cache: OrderedDict[str, list[LyricLine]] = OrderedDict()

    def _init_client(self) -> None:
        if self._client is None:
            logger.info("Подключение к API Яндекс Музыки...")
            self._client = Client(self._token).init()

    def _load_lrc(self, track_id: str) -> list[LyricLine]:
        if track_id in self._cache:
            self._cache.move_to_end(track_id)
            return self._cache[track_id]

        self._init_client()
        assert self._client is not None

        try:
            tracks = self._client.tracks([track_id])
            if not tracks:
                return self._cache_result(track_id, [])

            lyrics = tracks[0].get_lyrics(format_="LRC")
            if not lyrics:
                return self._cache_result(track_id, [])

            return self._cache_result(track_id, parse_lrc(lyrics.fetch_lyrics()))
        except NotFoundError:
            logger.debug("Синхронизированный текст трека %s не найден.", track_id)
            return self._cache_result(track_id, [])

    def _cache_result(
        self,
        track_id: str,
        value: list[LyricLine],
    ) -> list[LyricLine]:
        if len(self._cache) >= self._cache_size:
            self._cache.popitem(last=False)
        self._cache[track_id] = value
        return value

    async def get_lyrics_for_media(
        self,
        artist: str,
        title: str,
    ) -> tuple[str | None, list[LyricLine]]:
        def search_and_load() -> tuple[str | None, list[LyricLine]]:
            self._init_client()
            assert self._client is not None

            query = f"{artist} - {title}" if artist else title
            search = self._client.search(query, type_="track")
            if not search or not search.tracks or not search.tracks.results:
                return None, []

            track = find_best_matching_track(search.tracks.results, artist, title)
            if track is None:
                logger.debug("Точное совпадение для %s — %s не найдено.", artist, title)
                return None, []

            track_id = str(track.id)
            return track_id, self._load_lrc(track_id)

        delay = 2.0
        for attempt in range(3):
            try:
                return await asyncio.to_thread(search_and_load)
            except Exception as error:
                if attempt == 2:
                    raise
                logger.warning(
                    "Ошибка получения LRC: %s. Повтор через %.0f сек.",
                    error,
                    delay,
                )
                await asyncio.sleep(delay)
                delay *= 2

        return None, []

    @staticmethod
    def get_current_line(
        lines: list[LyricLine],
        current_seconds: float,
    ) -> str:
        current_text = ""
        for timestamp, text in lines:
            if current_seconds < timestamp:
                break
            current_text = text
        return current_text
