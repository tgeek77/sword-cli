"""SWORD module discovery and verse lookup via pysword."""

from __future__ import annotations

from pathlib import Path

from biblecli.config import configured_module
from biblecli.format import Verse, format_ref, format_verses
from biblecli.paths import DEFAULT_SWORD_PATH
from biblecli.refs import VerseRef
from biblecli.search import DEFAULT_MAX_RESULTS, verse_matches

# Re-export for callers that imported the path from this module.
__all__ = [
    "DEFAULT_SWORD_PATH",
    "ModuleError",
    "VerseLookupError",
    "fetch_verses",
    "get_verses",
    "list_books",
    "list_modules",
    "list_structure_books",
    "resolve_active_module",
    "resolve_book",
    "resolve_module_id",
    "search_verses",
]


class ModuleError(Exception):
    """Raised when a module cannot be resolved or loaded."""


class VerseLookupError(Exception):
    """Raised when a book/verse lookup fails."""


def _load_modules(path: Path | None = None):
    from pysword.modules import SwordModules

    sword_path = path or DEFAULT_SWORD_PATH
    try:
        modules = SwordModules(str(sword_path))
        found = modules.parse_modules() or {}
        return modules, found
    except FileNotFoundError:
        return None, {}


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
    if modules is None:
        raise ModuleError(f"no SWORD modules found under {DEFAULT_SWORD_PATH}")
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


def list_structure_books(module: str, path: Path | None = None) -> list[dict[str, str | int]]:
    """Return versification books without scanning stored text.

    Used by the interactive reader so startup does not iterate the whole
    module. Each row has ``section``, ``name``, ``abbreviation``, ``chapters``.
    """
    _, bible = _get_bible(module, path=path)
    structure = bible.get_structure().get_books()
    rows: list[dict[str, str | int]] = []
    for section in ("ot", "nt"):
        for book in structure.get(section, []):
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
        raise ModuleError(
            f"no SWORD modules found under {DEFAULT_SWORD_PATH}\n"
            "  biblecli --list-remote -s CrossWire\n"
            "  biblecli --download KJV"
        )

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


def resolve_active_module(
    cli_name: str | None,
    path: Path | None = None,
    *,
    env: str | None = None,
    config: dict[str, object] | None = None,
) -> str:
    """Resolve ``-m``, env, config, or the only installed module.

    Raises:
        ModuleError: If no module can be chosen.
    """
    _, found = _load_modules(path)
    if cli_name and cli_name.strip():
        return resolve_module_id(cli_name, found)

    configured = configured_module(env=env, config=config)
    if configured:
        return resolve_module_id(configured, found)

    if len(found) == 1:
        return next(iter(found))

    if not found:
        raise ModuleError(
            f"no SWORD modules found under {DEFAULT_SWORD_PATH}\n"
            "  biblecli --list-remote -s CrossWire\n"
            "  biblecli --download KJV"
        )

    raise ModuleError(
        "no default module set; pick one:\n"
        "  biblecli --list\n"
        "  biblecli --set-module ASV\n"
        "  biblecli -m ASV John 3:16"
    )


def resolve_book(module: str, name: str, path: Path | None = None) -> str:
    """Resolve a book name or abbreviation to the module's canonical name."""
    _, bible = _get_bible(module, path=path)
    try:
        _, book = bible.get_structure().find_book(name)
    except ValueError as exc:
        raise VerseLookupError(
            f"unknown book {name!r} in {module}; try --list-books"
        ) from exc
    return book.name


def _chapter_verse_count(bible, book_name: str, chapter: int) -> int:
    try:
        _, book = bible.get_structure().find_book(book_name)
    except ValueError as exc:
        raise VerseLookupError(
            f"unknown book {book_name!r}; try --list-books"
        ) from exc
    if chapter < 1 or chapter > book.num_chapters:
        raise VerseLookupError(
            f"{book.name} has {book.num_chapters} chapters"
        )
    return int(book.chapter_lengths[chapter - 1])


def _iter_chapter(
    bible,
    book_name: str,
    chapter: int,
    verses: list[int] | None,
) -> list[Verse]:
    display_name = resolve_book_from_bible(bible, book_name)
    max_verse = _chapter_verse_count(bible, display_name, chapter)
    verse_nums = verses if verses is not None else list(range(1, max_verse + 1))
    if verse_nums and verse_nums[-1] > max_verse:
        raise VerseLookupError(
            f"{display_name} {chapter} has {max_verse} verses"
        )
    try:
        texts = list(
            bible.get_iter(
                books=[display_name],
                chapters=[chapter],
                verses=verse_nums,
                clean=True,
            )
        )
    except ValueError as exc:
        raise VerseLookupError(str(exc)) from exc
    except Exception as exc:
        label = format_ref(display_name, chapter, verse_nums[0] if verse_nums else None)
        raise VerseLookupError(f"could not look up {label}: {exc}") from exc

    records: list[Verse] = []
    for number, text in zip(verse_nums, texts):
        records.append(
            Verse(
                book=display_name,
                chapter=chapter,
                verse=number,
                text=str(text).strip() if text else "",
            )
        )
    return records


def resolve_book_from_bible(bible, name: str) -> str:
    try:
        _, book = bible.get_structure().find_book(name)
    except ValueError as exc:
        raise VerseLookupError(
            f"unknown book {name!r}; try --list-books"
        ) from exc
    return book.name


def fetch_verses(
    module: str,
    book: str,
    ref: VerseRef,
    path: Path | None = None,
) -> list[Verse]:
    """Fetch cleaned verse records for a book and verse reference."""
    module_id, bible = _get_bible(module, path=path)
    book_name = resolve_book_from_bible(bible, book)
    verses = _iter_chapter(bible, book_name, ref.chapter, ref.verse_list())
    if not any(verse.text.strip() for verse in verses):
        label = _format_lookup_label(book_name, ref)
        raise VerseLookupError(
            f"no text found for {label} in {module_id} "
            f"(book may be absent from this module; try --list-books)"
        )
    return verses


def _format_lookup_label(book: str, ref: VerseRef) -> str:
    verses = ref.verse_list()
    if verses and len(verses) == 1:
        return format_ref(book, ref.chapter, verses[0])
    if verses and len(verses) > 1:
        return f"{book} {ref.chapter}:{verses[0]}-{verses[-1]}"
    return format_ref(book, ref.chapter)


def get_verses(
    module: str,
    book: str,
    ref: VerseRef,
    path: Path | None = None,
    *,
    plain: bool = False,
) -> str:
    """Fetch and format verse text for a book and verse reference."""
    verses = fetch_verses(module, book, ref, path=path)
    return format_verses(verses, plain=plain, whole_chapter=ref.whole_chapter)


def search_verses(
    module: str,
    query: str,
    *,
    book: str | None = None,
    ignore_case: bool = True,
    max_results: int = DEFAULT_MAX_RESULTS,
    path: Path | None = None,
) -> tuple[list[Verse], bool]:
    """Scan a module for verses containing ``query``.

    Restrict to one book when ``book`` is set. Returns ``(matches, truncated)``.
    """
    needle = query.strip()
    if not needle:
        raise ValueError("search query is empty")
    if max_results < 1:
        raise ValueError("max results must be >= 1")

    _, bible = _get_bible(module, path=path)
    structure = bible.get_structure().get_books()
    books: list[str] = []
    if book:
        books.append(resolve_book_from_bible(bible, book))
    else:
        for section in ("ot", "nt"):
            for item in structure.get(section, []):
                books.append(item.name)

    matches: list[Verse] = []
    for book_name in books:
        _, book_struct = bible.get_structure().find_book(book_name)
        for chapter in range(1, book_struct.num_chapters + 1):
            records = _iter_chapter(bible, book_name, chapter, None)
            for verse in records:
                if not verse_matches(verse.text, needle, ignore_case=ignore_case):
                    continue
                if len(matches) >= max_results:
                    return matches, True
                matches.append(verse)
    return matches, False
