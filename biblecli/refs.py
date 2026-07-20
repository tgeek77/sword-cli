"""Parse chapter:verse reference strings."""

from __future__ import annotations

import re
from dataclasses import dataclass


_VERSE_RE = re.compile(
    r"""
    ^\s*
    (?P<chapter>\d+)
    (?:
        :(?P<start>\d+)
        (?:-(?P<end>\d+))?
    )?
    \s*$
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class VerseRef:
    """A chapter, optionally narrowed to a verse or same-chapter range."""

    chapter: int
    verse_start: int | None = None
    verse_end: int | None = None

    def verse_list(self) -> list[int] | None:
        """Return verse numbers for pysword, or None for a whole chapter."""
        if self.verse_start is None:
            return None
        end = self.verse_end if self.verse_end is not None else self.verse_start
        return list(range(self.verse_start, end + 1))


def parse_verse_ref(value: str) -> VerseRef:
    """Parse ``N``, ``N:M``, or ``N:M-P`` (same-chapter range).

    Raises:
        ValueError: If the string is not a supported reference form.
    """
    match = _VERSE_RE.match(value)
    if not match:
        raise ValueError(
            f"invalid verse reference {value!r}; "
            "expected N, N:M, or N:M-P (same chapter)"
        )

    chapter = int(match.group("chapter"))
    if chapter < 1:
        raise ValueError("chapter must be >= 1")

    start_raw = match.group("start")
    if start_raw is None:
        return VerseRef(chapter=chapter)

    verse_start = int(start_raw)
    if verse_start < 1:
        raise ValueError("verse must be >= 1")

    end_raw = match.group("end")
    if end_raw is None:
        return VerseRef(chapter=chapter, verse_start=verse_start)

    verse_end = int(end_raw)
    if verse_end < verse_start:
        raise ValueError(
            f"verse range end ({verse_end}) must be >= start ({verse_start})"
        )

    return VerseRef(chapter=chapter, verse_start=verse_start, verse_end=verse_end)
