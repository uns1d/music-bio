from music_bio.telegram_bio import format_bio


def test_full_bio():
    result = format_bio(
        "🎧 {artist} — {title} | {lyric}",
        "The Beatles",
        "Yesterday",
        "All my troubles seemed so far away",
    )

    assert result == "🎧 The Beatles — Yesterday | All my troubles seemed so far away"


def test_bio_without_lyric():
    result = format_bio(
        "🎧 {artist} — {title} | {lyric}",
        "The Beatles",
        "Yesterday",
        "",
    )

    assert result == "🎧 The Beatles — Yesterday"


def test_bio_without_artist():
    result = format_bio(
        "🎧 {artist} — {title} | {lyric}",
        "",
        "Untitled",
        "Piano",
    )

    assert result == "🎧 Untitled | Piano"


def test_bio_length_limits():
    template = "🎧 {artist} — {title} | {lyric}"
    lyric = "A" * 150

    standard = format_bio(template, "Artist", "Title", lyric, limit=70)
    premium = format_bio(template, "Artist", "Title", lyric, limit=140)

    assert len(standard) == 70
    assert len(premium) == 140
    assert standard.endswith("…")
    assert premium.endswith("…")
