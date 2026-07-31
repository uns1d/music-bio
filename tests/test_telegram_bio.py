import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest

from music_bio.app import MusicBioApplication
from music_bio.models import Settings
from music_bio.telegram_bio import TelegramBioUpdater


@pytest.fixture
def settings():
    return Settings(
        api_id=12345,
        api_hash="test_hash",
        yandex_token="test_token",
        min_bio_interval=0.0,
        check_interval=0.1,
        no_lyrics=True,
        source_hints=[],
    )


@pytest.fixture
def telegram_client():
    with patch("music_bio.telegram_bio.TelegramClient") as client_class:
        client = AsyncMock()
        client_class.return_value = client

        user = MagicMock()
        user.premium = False
        full_user = MagicMock()
        full_user.full_user.about = "Original Bio"

        client.get_me.return_value = user
        client.return_value = full_user

        yield client, client_class


@pytest.mark.asyncio
async def test_restore_original_bio(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)

    await updater.start()
    await updater.update_bio("Playing track")
    await updater.stop()

    requests = [
        call.args[0]
        for call in client.call_args_list
        if isinstance(call.args[0], UpdateProfileRequest)
    ]
    assert requests[-1].about == "Original Bio"
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_restore_when_bio_did_not_change(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)

    await updater.start()
    calls_before_stop = client.call_count
    await updater.stop()

    assert client.call_count == calls_before_stop
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_no_restore_flag(settings, telegram_client):
    client, _ = telegram_client
    settings.no_restore = True
    updater = TelegramBioUpdater(settings)

    await updater.start()
    await updater.update_bio("Playing track")
    calls_before_stop = client.call_count
    await updater.stop()

    assert client.call_count == calls_before_stop
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_dry_run_does_not_create_client(settings):
    settings.dry_run = True

    with patch("music_bio.telegram_bio.TelegramClient") as client_class:
        updater = TelegramBioUpdater(settings)
        await updater.start()
        assert await updater.update_bio("Playing track")
        await updater.stop()

    client_class.assert_not_called()


@pytest.mark.asyncio
async def test_failed_profile_read_blocks_updates(settings, telegram_client):
    client, _ = telegram_client
    client.side_effect = RuntimeError("Profile error")
    updater = TelegramBioUpdater(settings)

    await updater.start()
    client.side_effect = None
    updated = await updater.update_bio("Playing track")
    await updater.stop()

    requests = [
        call.args[0]
        for call in client.call_args_list
        if isinstance(call.args[0], UpdateProfileRequest)
    ]
    assert updater.original_bio is None
    assert updated is False
    assert requests == []
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_after_restore_error(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)

    await updater.start()
    await updater.update_bio("Playing track")
    client.side_effect = RuntimeError("Network error")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await updater.stop()

    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_retries_after_transient_network_error(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)

    await updater.start()
    await updater.update_bio("Playing track")
    client.side_effect = [RuntimeError("Proxy reconnect"), MagicMock()]

    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        await updater.stop()

    restore_requests = [
        call.args[0]
        for call in client.call_args_list
        if isinstance(call.args[0], UpdateProfileRequest) and call.args[0].about == "Original Bio"
    ]
    assert len(restore_requests) == 2
    sleep.assert_awaited_once_with(1)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_event_does_not_cancel_restore_flood_wait(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)
    stop_event = asyncio.Event()
    updater.set_stop_event(stop_event)

    await updater.start()
    await updater.update_bio("Playing track")

    flood_wait = FloodWaitError(request=None)
    flood_wait.seconds = 1
    client.side_effect = [flood_wait, MagicMock()]
    stop_event.set()

    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        await updater.stop()

    requests = [
        call.args[0]
        for call in client.call_args_list
        if isinstance(call.args[0], UpdateProfileRequest)
    ]
    assert requests[-1].about == "Original Bio"
    sleep.assert_awaited_once_with(2)
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_minimum_interval_and_force(settings, telegram_client):
    settings.min_bio_interval = 10.0
    updater = TelegramBioUpdater(settings)

    await updater.start()
    with patch(
        "music_bio.telegram_bio._monotonic",
        side_effect=[100.0, 105.0, 105.0],
    ):
        assert await updater.update_bio("Track 1")
        assert not await updater.update_bio("Track 2")
        assert await updater.update_bio("Track 2", force=True)
    await updater.stop()


@pytest.mark.asyncio
async def test_flood_wait_retries_once(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)

    await updater.start()
    flood_wait = FloodWaitError(request=None)
    flood_wait.seconds = 1
    client.side_effect = [flood_wait, MagicMock()]

    with patch("asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await updater.update_bio("Playing track")

    sleep.assert_awaited_once_with(2)
    await updater.stop()


@pytest.mark.asyncio
async def test_stop_event_interrupts_flood_wait(settings, telegram_client):
    client, _ = telegram_client
    updater = TelegramBioUpdater(settings)
    stop_event = asyncio.Event()
    updater.set_stop_event(stop_event)

    await updater.start()
    flood_wait = FloodWaitError(request=None)
    flood_wait.seconds = 600
    client.side_effect = flood_wait

    update_task = asyncio.create_task(updater.update_bio("Playing track"))
    await asyncio.sleep(0)
    stop_event.set()

    assert not await asyncio.wait_for(update_task, timeout=0.5)
    await updater.stop()


@pytest.mark.asyncio
async def test_app_restores_after_transient_error(settings, telegram_client):
    client, _ = telegram_client
    media = AsyncMock()
    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.position = 0.0
    track.key = ("artist", "title")
    media.get_active_track.side_effect = [
        track,
        RuntimeError("GSMTC error"),
        asyncio.CancelledError(),
    ]

    app = MusicBioApplication(settings)
    app._media_monitor = media

    with (
        patch("asyncio.sleep", new_callable=AsyncMock) as sleep,
        pytest.raises(asyncio.CancelledError),
    ):
        await app.run()

    sleep.assert_any_call(5.0)
    requests = [
        call.args[0]
        for call in client.call_args_list
        if isinstance(call.args[0], UpdateProfileRequest)
    ]
    assert requests[-1].about == "Original Bio"
    client.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_app_retries_lyrics_after_failure(settings):
    media = AsyncMock()
    lyrics = AsyncMock()
    updater = AsyncMock()
    updater.original_bio = "Original Bio"
    updater.bio_limit = 70

    track = MagicMock()
    track.artist = "Artist"
    track.title = "Title"
    track.position = 0.0
    track.key = ("artist", "title")

    media.get_active_track.side_effect = [
        track,
        track,
        asyncio.CancelledError(),
    ]
    lyrics.get_lyrics_for_media.side_effect = [
        RuntimeError("Temporary error"),
        ("track-id", []),
    ]

    app = MusicBioApplication(settings)
    app._media_monitor = media
    app._lyrics_provider = lyrics
    app._bio_updater = updater

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(asyncio.CancelledError),
    ):
        await app.run()

    assert lyrics.get_lyrics_for_media.await_count == 2
    updater.stop.assert_awaited_once()
