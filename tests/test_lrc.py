from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from music_bio.lyrics import YandexLyricsProvider, get_lyric_context, parse_lrc
from music_bio.models import LyricLine


def test_parse_simple_lrc():
    lines = parse_lrc("[00:12.50]First line\n[00:15.00]Second line")

    assert len(lines) == 2
    assert lines[0].timestamp == 12.5
    assert lines[0].text == "First line"
    assert lines[1].timestamp == 15.0
    assert lines[1].text == "Second line"


def test_parse_multiple_timestamps():
    lines = parse_lrc("[00:10.00][00:20.00]Repeated line")

    assert [line.timestamp for line in lines] == [10.0, 20.0]
    assert all(line.text == "Repeated line" for line in lines)


def test_parse_offsets():
    positive = parse_lrc("[offset:1000]\n[00:10.00]Positive")
    negative = parse_lrc("[offset:-2000]\n[00:10.00]Negative")

    assert positive[0].timestamp == 11.0
    assert negative[0].timestamp == 8.0


def test_parse_invalid_lrc():
    assert parse_lrc(None) == []
    assert parse_lrc("") == []
    assert parse_lrc("[invalid]Text") == []
    assert parse_lrc("[xx:yy]Text") == []


def test_timestamp_without_fraction():
    lines = parse_lrc("[00:05]Valid line")

    assert lines[0].timestamp == 5.0


def test_current_line_switches_exactly_on_lrc_timestamp():
    lines = parse_lrc("[00:10.00]First\n[00:12.50]Second")

    assert YandexLyricsProvider.get_current_line(lines, 9.999) == ""
    assert YandexLyricsProvider.get_current_line(lines, 10.0) == "First"
    assert YandexLyricsProvider.get_current_line(lines, 12.499) == "First"
    assert YandexLyricsProvider.get_current_line(lines, 12.5) == "Second"


def test_lyric_context_includes_the_next_line():
    lines = parse_lrc("[00:10.00]First\n[00:12.50]Second\n[00:15.00]Third")

    assert get_lyric_context(lines, 9.999) == ("", "First")
    assert get_lyric_context(lines, 10.0) == ("First", "Second")
    assert get_lyric_context(lines, 12.5) == ("Second", "Third")
    assert get_lyric_context(lines, 15.0) == ("Third", "")


@pytest.mark.asyncio
async def test_provider_tries_another_exact_track_when_first_has_no_lrc():
    first = SimpleNamespace(
        id=1,
        title="Track",
        artists=[SimpleNamespace(name="Artist")],
        lyrics_info=None,
    )
    second = SimpleNamespace(
        id=2,
        title="Track",
        artists=[SimpleNamespace(name="Artist")],
        lyrics_info=None,
    )
    search = SimpleNamespace(
        tracks=SimpleNamespace(results=[first, second]),
    )

    provider = YandexLyricsProvider("token")
    provider._client = MagicMock()
    provider._client.search.return_value = search
    provider._load_lrc = MagicMock(
        side_effect=[
            [],
            [LyricLine(10.0, "Found in another release")],
        ]
    )

    track_id, lines = await provider.get_lyrics_for_media("Artist", "Track")

    assert track_id == "2"
    assert lines == [LyricLine(10.0, "Found in another release")]
    assert provider._load_lrc.call_count == 2
