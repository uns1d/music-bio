import json
from http import HTTPStatus
from unittest.mock import patch

import pytest

from music_bio.browser_bridge import BrowserBridgeSource


def make_request(
    payload,
    *,
    token="bridge-secret",
    origin="https://music.yandex.ru",
):
    return {
        "method": "POST",
        "path": "/v1/track",
        "headers": {
            "authorization": f"Bearer {token}",
            "origin": origin,
        },
        "body": json.dumps(payload).encode(),
    }


def page_payload(page_id, *, title="Track", playing=True, active=True):
    return {
        "page_id": page_id,
        "url": "https://music.yandex.ru/home",
        "active": active,
        "playing": playing,
        "artist": "Artist",
        "title": title,
        "position": 42,
        "duration": 180,
        "position_known": True,
    }


def make_ping(*, token="bridge-secret"):
    return {
        "method": "GET",
        "path": "/v1/ping",
        "headers": {
            "authorization": f"Bearer {token}",
            "origin": "chrome-extension://music-bio",
        },
        "body": b"",
    }


@pytest.mark.asyncio
async def test_accepts_yandex_music_track_only():
    source = BrowserBridgeSource(token="bridge-secret")
    request = make_request(
        {
            "url": "https://music.yandex.ru/home",
            "playing": True,
            "artist": "Artist",
            "title": "Track",
            "position": 12.5,
            "duration": 180,
            "artwork_url": "https://avatars.yandex.net/cover.jpg",
        }
    )

    status, payload, _ = source._process_request(request)
    track = await source.get_active_track()

    assert status is HTTPStatus.OK
    assert payload == {"ok": True}
    assert track is not None
    assert track.artist == "Artist"
    assert track.title == "Track"
    assert track.source_name == "Яндекс Музыка в браузере"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/music.yandex.ru",
        "https://music.yandex.ru.example.com/track",
        "http://music.yandex.ru/track",
        "https://youtube.com/watch?v=test",
    ],
)
def test_rejects_non_yandex_urls(url):
    source = BrowserBridgeSource(token="bridge-secret")
    request = make_request(
        {
            "url": url,
            "playing": True,
            "artist": "Artist",
            "title": "Track",
        }
    )

    status, payload, _ = source._process_request(request)

    assert status is HTTPStatus.FORBIDDEN
    assert payload["error"] == "invalid_source"


def test_rejects_wrong_token_and_origin():
    source = BrowserBridgeSource(token="bridge-secret")
    payload = {
        "url": "https://music.yandex.ru/track/1",
        "playing": True,
        "title": "Track",
    }

    wrong_token, _, _ = source._process_request(make_request(payload, token="wrong"))
    wrong_origin, body, _ = source._process_request(
        make_request(payload, origin="https://evil.example")
    )

    assert wrong_token is HTTPStatus.UNAUTHORIZED
    assert wrong_origin is HTTPStatus.FORBIDDEN
    assert body["error"] == "invalid_origin"


@pytest.mark.asyncio
async def test_track_expires_when_extension_stops_sending():
    statuses = []
    source = BrowserBridgeSource(
        token="bridge-secret",
        stale_after=6.0,
        status_callback=lambda connected, message: statuses.append((connected, message)),
    )
    request = make_request(
        {
            "url": "https://music.yandex.ru/track/1",
            "playing": True,
            "title": "Track",
            "position": 5,
        }
    )

    with patch("music_bio.browser_bridge.time.monotonic", return_value=100.0):
        source._process_request(request)
    with patch("music_bio.browser_bridge.time.monotonic", return_value=107.0):
        track = await source.get_active_track()

    assert track is None
    assert statuses[0] == (True, "Браузерное расширение подключено")
    assert statuses[-1] == (False, "Расширение Яндекс Музыки не отвечает")


def test_authenticated_ping_reports_extension_connection():
    statuses = []
    source = BrowserBridgeSource(
        token="bridge-secret",
        status_callback=lambda connected, message: statuses.append((connected, message)),
    )

    status, payload, _ = source._process_request(make_ping())
    unauthorized, _, _ = source._process_request(make_ping(token="wrong"))

    assert status is HTTPStatus.OK
    assert payload == {"ok": True}
    assert statuses == [(True, "Браузерное расширение подключено")]
    assert unauthorized is HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_port_binding_error_is_reported_to_interface():
    statuses = []
    source = BrowserBridgeSource(
        port=8767,
        token="bridge-secret",
        status_callback=lambda connected, message: statuses.append((connected, message)),
    )

    with (
        patch(
            "music_bio.browser_bridge.asyncio.start_server",
            side_effect=OSError("address already in use"),
        ),
        pytest.raises(RuntimeError, match="8767"),
    ):
        await source.start()

    assert statuses == [(False, "Не удалось открыть локальный порт 8767: address already in use")]


@pytest.mark.asyncio
async def test_ping_does_not_rewind_track_position():
    source = BrowserBridgeSource(token="bridge-secret")

    with patch("music_bio.browser_bridge.time.monotonic", return_value=100.0):
        source._process_request(make_request(page_payload("playing-page")))
    with patch("music_bio.browser_bridge.time.monotonic", return_value=102.0):
        source._process_request(make_ping())
    with patch("music_bio.browser_bridge.time.monotonic", return_value=103.0):
        track = await source.get_active_track()

    assert track is not None
    assert track.position == pytest.approx(45.0)


@pytest.mark.asyncio
async def test_background_tab_cannot_replace_fresh_playing_track():
    source = BrowserBridgeSource(token="bridge-secret")

    with patch("music_bio.browser_bridge.time.monotonic", return_value=100.0):
        source._process_request(make_request(page_payload("playing-page", title="Playing")))
    with patch("music_bio.browser_bridge.time.monotonic", return_value=101.0):
        source._process_request(
            make_request(page_payload("paused-page", title="Paused", playing=False))
        )
        track = await source.get_active_track()

    assert track is not None
    assert track.title == "Playing"
    assert track.playback_status == "PLAYING"


@pytest.mark.asyncio
async def test_unloading_other_page_does_not_clear_current_track():
    source = BrowserBridgeSource(token="bridge-secret")

    source._process_request(make_request(page_payload("playing-page")))
    source._process_request(make_request(page_payload("other-page", active=False, playing=False)))

    assert await source.get_active_track() is not None


@pytest.mark.asyncio
async def test_unloading_current_page_clears_current_track():
    source = BrowserBridgeSource(token="bridge-secret")

    source._process_request(make_request(page_payload("playing-page")))
    source._process_request(make_request(page_payload("playing-page", active=False, playing=False)))

    assert await source.get_active_track() is None


@pytest.mark.asyncio
async def test_unknown_browser_position_does_not_reset_same_track():
    source = BrowserBridgeSource(token="bridge-secret")
    known_request = make_request(
        {
            "url": "https://music.yandex.ru/track/1",
            "playing": True,
            "artist": "Artist",
            "title": "Track",
            "position": 42,
            "duration": 180,
            "position_known": True,
        }
    )
    unknown_request = make_request(
        {
            "url": "https://music.yandex.ru/track/1",
            "playing": True,
            "artist": "Artist",
            "title": "Track",
            "position": 0,
            "duration": 0,
            "position_known": False,
        }
    )

    with patch("music_bio.browser_bridge.time.monotonic", return_value=100.0):
        source._process_request(known_request)
    with patch("music_bio.browser_bridge.time.monotonic", return_value=102.5):
        source._process_request(unknown_request)
        track = await source.get_active_track()

    assert track is not None
    assert track.position == pytest.approx(44.5)
    assert track.duration == 180


@pytest.mark.asyncio
async def test_paused_track_stays_visible_and_position_is_frozen():
    source = BrowserBridgeSource(token="bridge-secret")
    playing = make_request(
        {
            "url": "https://music.yandex.ru/track/1",
            "active": True,
            "playing": True,
            "artist": "Artist",
            "title": "Track",
            "position": 42,
            "duration": 180,
            "position_known": True,
        }
    )
    paused = make_request(
        {
            "url": "https://music.yandex.ru/track/1",
            "active": True,
            "playing": False,
            "artist": "Artist",
            "title": "Track",
            "position": 44,
            "duration": 180,
            "position_known": True,
        }
    )

    with patch("music_bio.browser_bridge.time.monotonic", return_value=100.0):
        source._process_request(playing)
    with patch("music_bio.browser_bridge.time.monotonic", return_value=102.0):
        source._process_request(paused)
    with patch("music_bio.browser_bridge.time.monotonic", return_value=105.0):
        track = await source.get_active_track()

    assert track is not None
    assert track.playback_status == "PAUSED"
    assert track.position == 44
    assert track.duration == 180


@pytest.mark.asyncio
async def test_unloaded_yandex_page_clears_track():
    source = BrowserBridgeSource(token="bridge-secret")
    source._process_request(
        make_request(
            {
                "url": "https://music.yandex.ru/track/1",
                "active": True,
                "playing": True,
                "artist": "Artist",
                "title": "Track",
            }
        )
    )

    source._process_request(
        make_request(
            {
                "url": "https://music.yandex.ru/track/1",
                "active": False,
                "playing": False,
                "artist": "Artist",
                "title": "Track",
            }
        )
    )

    assert await source.get_active_track() is None
