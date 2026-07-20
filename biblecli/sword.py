"""SWORD module discovery and verse lookup via pysword."""

from __future__ import annotations

from pathlib import Path

from pysword.modules import SwordModules

from biblecli.refs import VerseRef

DEFAULT_SWORD_PATH = Path.home() / ".sword"


class ModuleError(Exception):
    """Raised when a module cannot be resolved or loaded."""


class VerseLookupError(Exception):
    """Raised when a book/verse lookup fails."""


def _load_modules(path: Path | None = None) -> tuple[SwordModules, dict]:
    sword_path = path or DEFAULT_SWORD_PATH
    modules = SwordModules(str(sword_path))
    found = modules.parse_modules()
    return modules, found


def list_modules(path: Path | None = None) -> list[dict[str, str]]:
    """Return installed Bible modules as dicts with id, abbreviation, description."""
    _, found = _load_modules(path)
    rows: list[dict[str, str]] = []
    for module_id, meta in sorted(found.items(), key=lambda item: item[0].lower()):
        rows.append(
            {
                "id": module_id,
                "abbreviation": str(meta.get("abbreviation") or module_id),
                "description": str(meta.get("description") or ""),
            }
        )
    return rows


def _get_bible(module: str, path: Path | None = None):
    """Resolve and load a SwordBible for ``module``."""
    modules, found = _load_modules(path)
    module_id = resolve_module_id(module, found)
    try:
        bible = modules.get_bible_from_module(module_id)
    except Exception as exc:  # pysword raises variously
        raise ModuleError(f"failed to load module {module_id!r}: {exc}") from exc
    return module_id, bible


def _book_has_text(bible, book_name: str) -> bool:
    """True if the module stores any non-empty verse for ``book_name``."""
    try:
        for text in bible.get_iter(books=[book_name], clean=False):
            if text and str(text).strip():
                return True
    except Exception:
        return False
    return False


def list_books(module: str, path: Path | None = None) -> list[dict[str, str | int]]:
    """Return books that have text in a module, in testament order.

    Versification can list books the module does not include (e.g. empty
    Apocrypha slots). Those are omitted so ``-b`` names are usable.

    Each row has ``section`` (``ot``/``nt``), ``name`` (pass to ``-b``),
    ``abbreviation``, and ``chapters``.
    """
    _, bible = _get_bible(module, path=path)
    structure = bible.get_structure().get_books()
    rows: list[dict[str, str | int]] = []
    for section in ("ot", "nt"):
        for book in structure.get(section, []):
            if not _book_has_text(bible, book.name):
                continue
            rows.append(
                {
                    "section": section,
                    "name": book.name,
                    "abbreviation": book.preferred_abbreviation,
                    "chapters": int(book.num_chapters),
                }
            )
    return rows


def resolve_module_id(name: str, found: dict) -> str:
    """Resolve a module id or abbreviation to the conf section name.

    Matching is case-insensitive. Abbreviation matches must be unique.
    """
    if not found:
        raise ModuleError(f"no SWORD modules found under {DEFAULT_SWORD_PATH}")

    needle = name.strip().lower()
    by_id = {key.lower(): key for key in found}
    if needle in by_id:
        return by_id[needle]

    abbr_hits: list[str] = []
    for module_id, meta in found.items():
        abbr = str(meta.get("abbreviation") or "").lower()
        if abbr and abbr == needle:
            abbr_hits.append(module_id)

    if len(abbr_hits) == 1:
        return abbr_hits[0]
    if len(abbr_hits) > 1:
        raise ModuleError(
            f"abbreviation {name!r} is ambiguous: {', '.join(sorted(abbr_hits))}; "
            "use the module id (see --list)"
        )

    raise ModuleError(
        f"unknown module {name!r}; use --list to see installed modules"
    )


def _format_ref(book: str, ref: VerseRef, verses: list[int] | None) -> str:
    label = f"{book} {ref.chapter}"
    if verses and len(verses) == 1:
        return f"{label}:{verses[0]}"
    if verses and len(verses) > 1:
        return f"{label}:{verses[0]}-{verses[-1]}"
    return label


def get_verses(
    module: str,
    book: str,
    ref: VerseRef,
    path: Path | None = None,
) -> str:
    """Fetch cleaned verse text for a book and verse reference."""
    module_id, bible = _get_bible(module, path=path)

    kwargs: dict = {
        "books": [book.lower()],
        "chapters": [ref.chapter],
    }
    verses = ref.verse_list()
    if verses is not None:
        kwargs["verses"] = verses

    label = _format_ref(book, ref, verses)
    try:
        text = bible.get(**kwargs)
    except Exception as exc:
        raise VerseLookupError(f"could not look up {label} in {module_id}: {exc}") from exc

    if not text or not str(text).strip():
        raise VerseLookupError(
            f"no text found for {label} in {module_id} "
            f"(book may be absent from this module; try --list-books)"
        )

    return str(text).strip()
