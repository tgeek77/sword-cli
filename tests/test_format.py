from __future__ import annotations

from biblecli.format import Verse, format_verses


def _verses() -> list[Verse]:
    return [
        Verse("John", 3, 16, "For God so loved the world,"),
        Verse("John", 3, 17, "For God sent not his Son into the world"),
    ]


def test_format_range_numbered():
    text = format_verses(_verses())
    assert text.splitlines() == [
        "John 3:16 For God so loved the world,",
        "John 3:17 For God sent not his Son into the world",
    ]


def test_format_whole_chapter():
    verses = [
        Verse("John", 3, 1, "There was a man of the Pharisees,"),
        Verse("John", 3, 2, "The same came to Jesus by night"),
    ]
    text = format_verses(verses, whole_chapter=True)
    assert text.splitlines() == [
        "John 3",
        "1 There was a man of the Pharisees,",
        "2 The same came to Jesus by night",
    ]


def test_format_plain():
    text = format_verses(_verses(), plain=True)
    assert text == (
        "For God so loved the world,\n"
        "For God sent not his Son into the world"
    )


def test_format_skips_empty_and_collapses_whitespace():
    verses = [
        Verse("John", 3, 16, "  For God\nso loved  "),
        Verse("John", 3, 17, "   "),
    ]
    text = format_verses(verses)
    assert text == "John 3:16 For God so loved"


def test_format_empty_list():
    assert format_verses([]) == ""
