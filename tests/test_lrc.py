from music_bio.lyrics import parse_lrc


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
