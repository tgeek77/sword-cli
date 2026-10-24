"""Interactive chapter reader using stdlib curses."""

from __future__ import annotations

import sys
import textwrap

from biblecli.config import load_config, save_config
from biblecli.format import format_verses
from biblecli.refs import VerseRef, parse_passage
from biblecli.search import DEFAULT_MAX_RESULTS
from biblecli.sword import (
    ModuleError,
    VerseLookupError,
    fetch_verses,
    list_structure_books,
    resolve_book,
    search_verses,
)


def run_reader(
    module: str,
    *,
    book: str | None = None,
    chapter: int | None = None,
) -> int:
    """Open a curses chapter reader. Requires a tty."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("biblecli: interactive reader requires a tty", file=sys.stderr)
        print("  biblecli John 3:16", file=sys.stderr)
        print("  biblecli --search \"only begotten\"", file=sys.stderr)
        return 1
    try:
        import curses
    except ImportError:
        print("biblecli: curses is not available on this Python", file=sys.stderr)
        print("  biblecli John 3:16", file=sys.stderr)
        return 1

    try:
        books = list_structure_books(module)
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    if not books:
        print(f"biblecli: no books found for module {module!r}", file=sys.stderr)
        return 1

    start_idx, start_chapter = _starting_position(module, books, book, chapter)

    def _wrapped(stdscr) -> int:
        return _loop(curses, stdscr, module, books, start_idx, start_chapter)

    return int(curses.wrapper(_wrapped) or 0)


def _starting_position(
    module: str,
    books: list[dict[str, str | int]],
    book: str | None,
    chapter: int | None,
) -> tuple[int, int]:
    if book:
        idx = _book_index(module, books, book)
        chap = chapter or 1
        return idx, _clamp_chapter(books, idx, chap)

    data = load_config()
    last_book = data.get("last_book")
    last_chapter = data.get("last_chapter")
    if isinstance(last_book, str) and last_book.strip():
        try:
            idx = _book_index(module, books, last_book)
        except VerseLookupError:
            idx = _default_book_index(books)
        chap = last_chapter if isinstance(last_chapter, int) else 1
        return idx, _clamp_chapter(books, idx, chap)

    idx = _default_book_index(books)
    return idx, 1


def _default_book_index(books: list[dict[str, str | int]]) -> int:
    for i, row in enumerate(books):
        if str(row["name"]).lower() == "genesis":
            return i
    for i, row in enumerate(books):
        if str(row["name"]).lower() == "matthew":
            return i
    return 0


def _book_index(
    module: str,
    books: list[dict[str, str | int]],
    name: str,
) -> int:
    canonical = resolve_book(module, name)
    needle = canonical.lower()
    for i, row in enumerate(books):
        if str(row["name"]).lower() == needle:
            return i
    raise VerseLookupError(f"unknown book {name!r}; try --list-books")


def _clamp_chapter(books: list[dict[str, str | int]], idx: int, chapter: int) -> int:
    nchap = int(books[idx]["chapters"])
    if nchap < 1:
        return 1
    return max(1, min(chapter, nchap))


def _advance(
    books: list[dict[str, str | int]],
    idx: int,
    chapter: int,
    delta: int,
) -> tuple[int, int]:
    chapter += delta
    while True:
        nchap = int(books[idx]["chapters"])
        if 1 <= chapter <= nchap:
            return idx, chapter
        if delta > 0:
            if idx + 1 >= len(books):
                return idx, max(nchap, 1)
            idx += 1
            chapter = 1
        else:
            if idx <= 0:
                return 0, 1
            idx -= 1
            chapter = int(books[idx]["chapters"]) or 1


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _chapter_lines(module: str, book: str, chapter: int, width: int) -> tuple[list[str], int | None]:
    wrap_width = max(width, 8)
    try:
        verses = fetch_verses(module, book, VerseRef(chapter=chapter))
    except (VerseLookupError, ModuleError) as exc:
        return [str(exc)], None
    body = format_verses(verses, whole_chapter=True)
    lines: list[str] = []
    for raw in body.splitlines():
        wrapped = textwrap.wrap(
            raw,
            width=wrap_width,
            subsequent_indent="  ",
        )
        lines.extend(wrapped or [""])
    return lines or ["(no text in this chapter)"], verses[0].verse if verses else None


def _prompt(curses, stdscr, label: str) -> str | None:
    curses.echo()
    curses.curs_set(1)
    height, width = stdscr.getmaxyx()
    row = max(height - 1, 0)
    try:
        stdscr.move(row, 0)
        stdscr.clrtoeol()
        stdscr.addnstr(row, 0, label, max(width - 1, 1))
        stdscr.refresh()
        n = max(width - len(label) - 1, 1)
        raw = stdscr.getstr(row, min(len(label), width - 2), n)
    except curses.error:
        raw = b""
    curses.noecho()
    curses.curs_set(0)
    if not raw:
        return None
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", "replace").strip()
    else:
        text = str(raw).strip()
    return text or None


def _add_line(curses, stdscr, row: int, col: int, text: str, width: int, attr: int = 0) -> None:
    if width <= 0:
        return
    clipped = text[:width]
    try:
        stdscr.addnstr(row, col, clipped, width, attr)
    except curses.error:
        pass


def _loop(
    curses,
    stdscr,
    module: str,
    books: list[dict[str, str | int]],
    idx: int,
    chapter: int,
) -> int:
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.nodelay(False)

    offset = 0
    status = ""
    lines: list[str] = []
    dirty = True

    def load_chapter() -> None:
        nonlocal lines, offset, dirty
        height, width = stdscr.getmaxyx()
        body_width = max(width - 1, 8)
        book_name = str(books[idx]["name"])
        lines, _ = _chapter_lines(module, book_name, chapter, body_width)
        offset = 0
        dirty = False
        save_config({"last_book": book_name, "last_chapter": chapter})

    while True:
        height, width = stdscr.getmaxyx()
        if height < 3 or width < 16:
            stdscr.erase()
            _add_line(curses, stdscr, 0, 0, "terminal too small", max(width - 1, 1))
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord("q"), 27):
                return 0
            continue

        if dirty:
            load_chapter()

        body_h = max(height - 1, 1)
        max_off = max(len(lines) - body_h, 0)
        offset = max(0, min(offset, max_off))

        stdscr.erase()
        for row, line in enumerate(lines[offset : offset + body_h]):
            _add_line(curses, stdscr, row, 0, line, width - 1)

        book_name = str(books[idx]["name"])
        nchap = int(books[idx]["chapters"])
        help_bits = "n/p chapter  j/k scroll  g go  / search  q quit"
        bar = f"{module}  {book_name} {chapter}/{nchap}  {help_bits}"
        if status:
            bar = f"{status}  |  {bar}"
        _add_line(
            curses,
            stdscr,
            height - 1,
            0,
            bar,
            width - 1,
            curses.A_REVERSE,
        )
        stdscr.refresh()
        status = ""

        key = stdscr.getch()
        if key in (ord("q"), 27):
            return 0
        if key == curses.KEY_RESIZE:
            dirty = True
            continue
        if key in (ord("n"), curses.KEY_RIGHT):
            idx, chapter = _advance(books, idx, chapter, 1)
            dirty = True
            continue
        if key in (ord("p"), curses.KEY_LEFT):
            idx, chapter = _advance(books, idx, chapter, -1)
            dirty = True
            continue
        if key in (ord("j"), curses.KEY_DOWN):
            offset += 1
            continue
        if key in (ord("k"), curses.KEY_UP):
            offset -= 1
            continue
        if key in (ord(" "), curses.KEY_NPAGE):
            offset += body_h
            continue
        if key == curses.KEY_PPAGE:
            offset -= body_h
            continue
        if key in (ord("g"),):
            typed = _prompt(curses, stdscr, "Go to: ")
            if not typed:
                continue
            try:
                passage = parse_passage(typed)
                idx = _book_index(module, books, passage.book)
                chapter = _clamp_chapter(books, idx, passage.ref.chapter)
                dirty = True
            except (ValueError, VerseLookupError) as exc:
                status = str(exc)
            continue
        if key in (ord("/"), ord("s")):
            typed = _prompt(curses, stdscr, "Search: ")
            if not typed:
                continue
            jumped = _search_screen(curses, stdscr, module, typed)
            if jumped is not None:
                jump_book, jump_chapter = jumped
                try:
                    idx = _book_index(module, books, jump_book)
                    chapter = _clamp_chapter(books, idx, jump_chapter)
                    dirty = True
                except VerseLookupError as exc:
                    status = str(exc)
            continue


def _search_screen(
    curses,
    stdscr,
    module: str,
    query: str,
) -> tuple[str, int] | None:
    try:
        matches, truncated = search_verses(
            module,
            query,
            max_results=DEFAULT_MAX_RESULTS,
        )
    except (ModuleError, ValueError) as exc:
        _flash(curses, stdscr, str(exc))
        return None
    if not matches:
        _flash(curses, stdscr, f"no matches for {query!r}")
        return None

    rows = [
        f"{verse.book} {verse.chapter}:{verse.verse} {_one_line(verse.text)}"
        for verse in matches
    ]
    header = f"Search {query!r}  {len(matches)} hits"
    if truncated:
        header += " (capped)"
    footer = "j/k move  enter open  q back"

    sel = 0
    offset = 0
    while True:
        height, width = stdscr.getmaxyx()
        body_h = max(height - 2, 1)
        max_off = max(len(rows) - body_h, 0)
        if sel < offset:
            offset = sel
        if sel >= offset + body_h:
            offset = sel - body_h + 1
        offset = max(0, min(offset, max_off))

        stdscr.erase()
        _add_line(curses, stdscr, 0, 0, header, width - 1, curses.A_BOLD)
        for row, line in enumerate(rows[offset : offset + body_h]):
            attr = curses.A_REVERSE if offset + row == sel else 0
            _add_line(curses, stdscr, row + 1, 0, line, width - 1, attr)
        _add_line(
            curses,
            stdscr,
            height - 1,
            0,
            footer,
            width - 1,
            curses.A_REVERSE,
        )
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord("q"), 27):
            return None
        if key in (ord("j"), curses.KEY_DOWN):
            sel = min(sel + 1, len(rows) - 1)
        elif key in (ord("k"), curses.KEY_UP):
            sel = max(sel - 1, 0)
        elif key in (curses.KEY_NPAGE, ord(" ")):
            sel = min(sel + body_h, len(rows) - 1)
        elif key in (curses.KEY_PPAGE,):
            sel = max(sel - body_h, 0)
        elif key in (curses.KEY_ENTER, 10, 13):
            hit = matches[sel]
            return hit.book, hit.chapter


def _flash(curses, stdscr, message: str) -> None:
    height, width = stdscr.getmaxyx()
    _add_line(
        curses,
        stdscr,
        max(height - 1, 0),
        0,
        message,
        max(width - 1, 1),
        curses.A_REVERSE,
    )
    stdscr.refresh()
    stdscr.getch()
