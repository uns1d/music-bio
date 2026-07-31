import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from music_bio.app import MusicBioApplication
from music_bio.models import Settings


@pytest.fixture
def test_settings():
    return Settings(
        api_id=12345,
        api_hash="test_hash",
        yandex_token="test_token",
        min_bio_interval=0.0,
        check_interval=3600.0,
        template="🎧 {artist} — {title} | {lyric}",
        dry_run=False,
        no_lyrics=True,
        no_restore=False,
        source_hints=[],
    )


def setup_mock_updater(updater_mock):
    updater_mock.original_bio = None
    updater_mock.bio_limit = 70


def test_gui_events_enable_quarter_second_display_refresh(test_settings):
    app = MusicBioApplication(
        test_settings,
        media_source=AsyncMock(),
        bio_updater=AsyncMock(),
        event_callback=lambda event: None,
    )

    assert app._poll_interval == 0.25


@pytest.mark.asyncio
async def test_stop_during_check_interval(test_settings, monkeypatch):
    media_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)
    media_mock.get_active_track.return_value = None

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._bio_updater = updater_mock

    wait_started = asyncio.Event()
    original_sleep_or_stop = app._sleep_or_stop

    async def observed_sleep_or_stop(delay: float) -> bool:
        if delay == test_settings.check_interval:
            wait_started.set()
        return await original_sleep_or_stop(delay)

    monkeypatch.setattr(app, "_sleep_or_stop", observed_sleep_or_stop)

    run_task = asyncio.create_task(app.run())
    await asyncio.wait_for(wait_started.wait(), timeout=1.0)

    app.request_stop()
    await asyncio.wait_for(run_task, timeout=1.0)

    assert not run_task.cancelled()
    updater_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_during_gsmtc_backoff(test_settings, monkeypatch):
    media_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)
    media_mock.get_active_track.side_effect = RuntimeError("GSMTC failure")

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._bio_updater = updater_mock

    backoff_started = asyncio.Event()
    original_sleep_or_stop = app._sleep_or_stop

    async def observed_sleep_or_stop(delay: float) -> bool:
        if delay == 5.0:
            backoff_started.set()
        return await original_sleep_or_stop(delay)

    monkeypatch.setattr(app, "_sleep_or_stop", observed_sleep_or_stop)

    run_task = asyncio.create_task(app.run())
    await asyncio.wait_for(backoff_started.wait(), timeout=1.0)

    app.request_stop()
    await asyncio.wait_for(run_task, timeout=1.0)

    updater_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_during_lrc_fetch(test_settings):
    test_settings.no_lyrics = False
    media_mock = AsyncMock()
    lyrics_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)

    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.key = ("Artist", "Title")
    track.position = 0.0
    media_mock.get_active_track.return_value = track

    lyrics_started = asyncio.Event()
    lyrics_cancelled = asyncio.Event()

    async def slow_get_lyrics(artist, title):
        lyrics_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            lyrics_cancelled.set()

    lyrics_mock.get_lyrics_for_media.side_effect = slow_get_lyrics

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._lyrics_provider = lyrics_mock
    app._bio_updater = updater_mock

    run_task = asyncio.create_task(app.run())
    await asyncio.wait_for(lyrics_started.wait(), timeout=1.0)

    app.request_stop()
    await asyncio.wait_for(run_task, timeout=1.0)
    await asyncio.wait_for(lyrics_cancelled.wait(), timeout=1.0)

    updater_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_new_track_is_published_before_slow_lyrics_finish(test_settings):
    test_settings.no_lyrics = False
    media_mock = AsyncMock()
    lyrics_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)

    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.key = ("artist", "title")
    track.position = 12.0
    media_mock.get_active_track.return_value = track

    lyrics_started = asyncio.Event()

    async def slow_get_lyrics(artist, title):
        lyrics_started.set()
        await asyncio.Event().wait()

    lyrics_mock.get_lyrics_for_media.side_effect = slow_get_lyrics
    events = []
    app = MusicBioApplication(
        test_settings,
        media_source=media_mock,
        bio_updater=updater_mock,
        lyrics_provider=lyrics_mock,
        event_callback=events.append,
    )

    run_task = asyncio.create_task(app.run())
    await asyncio.wait_for(lyrics_started.wait(), timeout=1.0)

    track_events = [event for event in events if event.kind == "track" and event.track]
    assert len(track_events) == 1
    assert track_events[0].track.title == "Title"
    assert track_events[0].lyric == ""

    app.request_stop()
    await asyncio.wait_for(run_task, timeout=1.0)


@pytest.mark.asyncio
async def test_external_cancel_during_lrc_fetch(test_settings):
    test_settings.no_lyrics = False
    media_mock = AsyncMock()
    lyrics_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)

    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.key = ("Artist", "Title")
    track.position = 0.0
    media_mock.get_active_track.return_value = track

    lyrics_started = asyncio.Event()
    lyrics_cancelled = asyncio.Event()

    async def slow_get_lyrics(artist, title):
        lyrics_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            lyrics_cancelled.set()

    lyrics_mock.get_lyrics_for_media.side_effect = slow_get_lyrics

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._lyrics_provider = lyrics_mock
    app._bio_updater = updater_mock

    run_task = asyncio.create_task(app.run())
    await asyncio.wait_for(lyrics_started.wait(), timeout=1.0)

    run_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run_task

    await asyncio.wait_for(lyrics_cancelled.wait(), timeout=1.0)
    updater_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_recovery_from_transient_gsmtc_error(test_settings, monkeypatch):
    media_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)

    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.key = ("Artist", "Title")
    track.position = 0.0

    call_count = 0

    async def get_active_track_handler():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient GSMTC error")
        return track

    media_mock.get_active_track.side_effect = get_active_track_handler

    async def stop_after_bio_update(*args, **kwargs):
        app.request_stop()

    updater_mock.update_bio.side_effect = stop_after_bio_update

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._bio_updater = updater_mock

    async def no_real_sleep(delay: float) -> bool:
        return app._stop_event.is_set()

    monkeypatch.setattr(app, "_sleep_or_stop", no_real_sleep)

    await asyncio.wait_for(app.run(), timeout=1.0)

    assert call_count == 2
    updater_mock.update_bio.assert_awaited_once()
    updater_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_stop_call_on_request_stop(test_settings):
    media_mock = AsyncMock()
    updater_mock = AsyncMock()
    setup_mock_updater(updater_mock)

    async def side_effect():
        app.request_stop()
        return None

    media_mock.get_active_track.side_effect = side_effect

    app = MusicBioApplication(test_settings)
    app._media_monitor = media_mock
    app._bio_updater = updater_mock

    await asyncio.wait_for(app.run(), timeout=1.0)

    assert updater_mock.stop.await_count == 1
