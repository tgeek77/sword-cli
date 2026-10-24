"""Match and cap verse search results (no SWORD I/O)."""

from __future__ import annotations

from biblecli.format import Verse

DEFAULT_MAX_RESULTS = 50


def verse_matches(text: str, query: str, *, ignore_case: bool = True) -> bool:
    """True if ``query`` occurs in ``text``."""
    hay = text.strip()
    needle = query.strip()
    if not hay or not needle:
        return False
    if ignore_case:
        return needle.lower() in hay.lower()
    return needle in hay


def take_matches(
    verses: list[Verse],
    query: str,
    *,
    ignore_case: bool = True,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> tuple[list[Verse], bool]:
    """Return matching verses and whether the cap truncated the list."""
    if max_results < 1:
        raise ValueError("max results must be >= 1")
    matches: list[Verse] = []
    truncated = False
    for verse in verses:
        if not verse_matches(verse.text, query, ignore_case=ignore_case):
            continue
        if len(matches) >= max_results:
            truncated = True
            break
        matches.append(verse)
    return matches, truncated
