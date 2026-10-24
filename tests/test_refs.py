from __future__ import annotations

import pytest

from biblecli.refs import parse_passage, parse_verse_ref


def test_parse_chapter():
    ref = parse_verse_ref("3")
    assert ref.chapter == 3
    assert ref.verse_start is None
    assert ref.whole_chapter
    assert ref.verse_list() is None


def test_parse_single_verse():
    ref = parse_verse_ref("3:16")
    assert ref.chapter == 3
    assert ref.verse_start == 16
    assert ref.verse_end is None
    assert ref.verse_list() == [16]


def test_parse_range():
    ref = parse_verse_ref("3:16-18")
    assert ref.verse_list() == [16, 17, 18]


def test_parse_range_end_before_start():
    with pytest.raises(ValueError, match="must be >= start"):
        parse_verse_ref("3:18-16")


def test_parse_invalid_verse():
    with pytest.raises(ValueError, match="invalid verse reference"):
        parse_verse_ref("John 3:16")


@pytest.mark.parametrize(
    "text, book, chapter, start, end",
    [
        ("John 3:16", "John", 3, 16, None),
        ("1 John 3:16-18", "1 John", 3, 16, 18),
        ("John 3", "John", 3, None, None),
        ("Song of Solomon 1:1", "Song of Solomon", 1, 1, None),
        ("1Jn 3:16", "1Jn", 3, 16, None),
    ],
)
def test_parse_passage(text, book, chapter, start, end):
    passage = parse_passage(text)
    assert passage.book == book
    assert passage.ref.chapter == chapter
    assert passage.ref.verse_start == start
    assert passage.ref.verse_end == end


def test_parse_passage_requires_book():
    with pytest.raises(ValueError, match="invalid passage"):
        parse_passage("3:16")


def test_parse_passage_requires_verse():
    with pytest.raises(ValueError, match="invalid passage"):
        parse_passage("John")


def test_parse_passage_collapses_whitespace():
    passage = parse_passage("  1   John   3:16  ")
    assert passage.book == "1 John"
    assert passage.ref.verse_list() == [16]
