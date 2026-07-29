from dataclasses import dataclass

from music_bio.lyrics import find_best_matching_track


@dataclass
class MockArtist:
    name: str


@dataclass
class MockTrack:
    id: int
    title: str
    artists: list[MockArtist]


def test_exact_track_match():
    results = [
        MockTrack(1, "The Trooper", [MockArtist("Iron Maiden")]),
        MockTrack(2, "Fear of the Dark", [MockArtist("Iron Maiden")]),
    ]

    matched = find_best_matching_track(results, "Iron Maiden", "The Trooper")

    assert matched is not None
    assert matched.id == 1


def test_reject_remix_and_live_versions():
    results = [
        MockTrack(1, "Numb (Live in Dallas)", [MockArtist("Linkin Park")]),
        MockTrack(2, "Numb (Official Remix)", [MockArtist("Linkin Park")]),
    ]

    matched = find_best_matching_track(results, "Linkin Park", "Numb")

    assert matched is None


def test_multi_artist_track():
    results = [
        MockTrack(
            1,
            "Starboy",
            [MockArtist("The Weeknd"), MockArtist("Daft Punk")],
        )
    ]

    matched = find_best_matching_track(results, "The Weeknd", "Starboy")

    assert matched is not None
    assert matched.id == 1
