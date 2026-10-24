from __future__ import annotations

from biblecli.tui import _advance, _clamp_chapter, _default_book_index


def _books():
    return [
        {"name": "Genesis", "chapters": 50},
        {"name": "Exodus", "chapters": 40},
        {"name": "Matthew", "chapters": 28},
    ]


def test_advance_within_book():
    idx, chapter = _advance(_books(), 0, 1, 1)
    assert (idx, chapter) == (0, 2)


def test_advance_wraps_to_next_book():
    idx, chapter = _advance(_books(), 0, 50, 1)
    assert (idx, chapter) == (1, 1)


def test_advance_wraps_to_previous_book():
    idx, chapter = _advance(_books(), 1, 1, -1)
    assert (idx, chapter) == (0, 50)


def test_advance_stops_at_ends():
    books = _books()
    assert _advance(books, 0, 1, -1) == (0, 1)
    assert _advance(books, 2, 28, 1) == (2, 28)


def test_clamp_and_default_book():
    books = _books()
    assert _clamp_chapter(books, 0, 99) == 50
    assert _clamp_chapter(books, 0, 0) == 1
    assert _default_book_index(books) == 0
    assert _default_book_index([{"name": "Matthew", "chapters": 28}]) == 0
