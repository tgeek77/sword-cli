from __future__ import annotations

import pytest

from biblecli.format import Verse
from biblecli.search import take_matches, verse_matches


def _sample() -> list[Verse]:
    return [
        Verse("John", 3, 16, "For God so loved the world"),
        Verse("John", 3, 17, "For God sent not his Son"),
        Verse("1 John", 4, 8, "He that loveth not knoweth not God"),
        Verse("Genesis", 1, 1, "In the beginning God created"),
    ]


def test_verse_matches_case_insensitive_by_default():
    assert verse_matches("For God so loved", "LOVED")
    assert not verse_matches("For God so loved", "LOVED", ignore_case=False)


def test_take_matches_and_cap():
    matches, truncated = take_matches(_sample(), "god", max_results=2)
    assert [f"{v.book} {v.chapter}:{v.verse}" for v in matches] == [
        "John 3:16",
        "John 3:17",
    ]
    assert truncated


def test_take_matches_all():
    matches, truncated = take_matches(_sample(), "god", max_results=50)
    assert len(matches) == 4
    assert not truncated


def test_take_matches_rejects_bad_max():
    with pytest.raises(ValueError, match="max results"):
        take_matches(_sample(), "god", max_results=0)
