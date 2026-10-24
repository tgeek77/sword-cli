"""Format verse records for terminal reading or unlabeled pipelines."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Verse:
    """A single verse of Bible text."""

    book: str
    chapter: int
    verse: int
    text: str


def _one_line(text: str) -> str:
    return " ".join(text.split())


def format_verses(
    verses: list[Verse],
    *,
    plain: bool = False,
    whole_chapter: bool = False,
) -> str:
    """Render verses as reading text.

    Numbered output (default):
    - one verse or a range: ``John 3:16 For God so loved...``
    - whole chapter: a ``John 3`` header, then ``1 ...`` lines

    ``plain`` joins cleaned verse text with newlines and no labels,
    matching the historical ``bible.get()`` pipeline output.
    """
    nonempty = [verse for verse in verses if verse.text.strip()]
    if not nonempty:
        return ""

    if plain:
        return "\n".join(_one_line(verse.text) for verse in nonempty)

    if whole_chapter:
        header = f"{nonempty[0].book} {nonempty[0].chapter}"
        lines = [header]
        for verse in nonempty:
            lines.append(f"{verse.verse} {_one_line(verse.text)}")
        return "\n".join(lines)

    return "\n".join(
        f"{verse.book} {verse.chapter}:{verse.verse} {_one_line(verse.text)}"
        for verse in nonempty
    )


def format_ref(book: str, chapter: int, verse: int | None = None) -> str:
    """Return a compact ``Book C`` or ``Book C:V`` label."""
    if verse is None:
        return f"{book} {chapter}"
    return f"{book} {chapter}:{verse}"
