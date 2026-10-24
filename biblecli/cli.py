"""Argparse entrypoint for biblecli."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import textwrap

from biblecli import __version__
from biblecli.config import save_config
from biblecli.download import (
    DownloadError,
    download_module,
    list_remote_modules,
    list_sources,
    refresh_sources,
)
from biblecli.format import format_verses
from biblecli.refs import VerseRef, parse_passage, parse_verse_ref
from biblecli.search import DEFAULT_MAX_RESULTS
from biblecli.sword import (
    ModuleError,
    VerseLookupError,
    get_verses,
    list_books,
    list_modules,
    resolve_active_module,
    resolve_book,
    search_verses,
)


EPILOG = textwrap.dedent(
    """\
    Examples:
      biblecli John 3:16
      biblecli -m KJV John 3:16-18
      biblecli John 3
      biblecli --search "only begotten"
      biblecli --search "love" -b John
      biblecli --set-module ASV
      biblecli -i
      biblecli --list
      biblecli --download KJV
    """
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biblecli",
        description="Read and download SWORD Bible modules from the command line.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-m",
        "--module",
        help="Bible module id or abbreviation (e.g. ASV); default from config",
    )
    parser.add_argument(
        "-b",
        "--book",
        help="Book name or abbreviation (e.g. John, 1Macc)",
    )
    parser.add_argument(
        "-v",
        "--verse",
        help="Chapter or verse: N, N:M, or N:M-P",
    )
    parser.add_argument(
        "passage",
        nargs="*",
        help="Book and verse, e.g. John 3:16 or 1 John 3:16-18",
    )
    parser.add_argument(
        "-s",
        "--source",
        help="Remote source name for refresh / list-remote / download",
    )
    parser.add_argument(
        "--lang",
        metavar="CODE",
        default="en",
        help="Language for --list-remote (default: en; use 'all' for every language)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List installed Bible modules and exit",
    )
    parser.add_argument(
        "--list-books",
        action="store_true",
        help="List books for the active module (names usable with -b) and exit",
    )
    parser.add_argument(
        "--sources",
        action="store_true",
        help="List built-in download sources and exit",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh remote module catalog(s) into local cache",
    )
    parser.add_argument(
        "--list-remote",
        action="store_true",
        help="List remote Bible modules from cached catalogs",
    )
    parser.add_argument(
        "--download",
        metavar="NAME",
        help="Download and install a Bible module by id or abbreviation",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help="Search verse text in the active module",
    )
    parser.add_argument(
        "--max",
        metavar="N",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum search hits (default: {DEFAULT_MAX_RESULTS})",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Make --search case-sensitive (default: ignore case)",
    )
    parser.add_argument(
        "--set-module",
        metavar="NAME",
        help="Save NAME as the default module in ~/.sword/biblecli/config.toml",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Open the interactive chapter reader (tty required)",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Print verse text without numbers or reference labels",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _print_modules() -> int:
    try:
        rows = list_modules()
    except Exception as exc:
        print(f"biblecli: failed to list modules: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("No SWORD Bible modules found under ~/.sword", file=sys.stderr)
        return 1
    width = max(len(row["id"]) for row in rows)
    for row in rows:
        abbr = row["abbreviation"]
        desc = row["description"]
        print(f"{row['id']:<{width}}  {abbr:<12}  {desc}")
    return 0


def _print_books(module: str) -> int:
    try:
        rows = list_books(module)
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"biblecli: failed to list books: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print(f"biblecli: no books found for module {module!r}", file=sys.stderr)
        return 1

    name_w = max(len(str(row["name"])) for row in rows)
    abbr_w = max(len(str(row["abbreviation"])) for row in rows)
    current_section: str | None = None
    for row in rows:
        section = str(row["section"])
        if section != current_section:
            current_section = section
            print(section)
        print(
            f"  {row['name']:<{name_w}}  {row['abbreviation']:<{abbr_w}}  "
            f"{row['chapters']} chapters"
        )
    return 0


def _print_sources() -> int:
    for source in list_sources():
        print(source.name)
        print(f"  catalog  {source.catalog_url}")
        print(f"  zip      {source.zip_base_url}/{{id}}.zip")
    return 0


def _do_refresh(source: str | None) -> int:
    try:
        results = refresh_sources(source)
    except DownloadError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    for name, count in sorted(results.items()):
        print(f"Refreshed {name}: {count} module confs")
    return 0


def _print_remote(source: str | None, lang: str | None) -> int:
    try:
        rows = list_remote_modules(source, lang=lang)
    except DownloadError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    if not rows:
        hint = f" for lang={lang}" if lang else ""
        print(f"biblecli: no remote Bible modules found{hint}", file=sys.stderr)
        return 1
    id_w = max(len(row["id"]) for row in rows)
    src_w = max(len(row["source"]) for row in rows)
    abbr_w = max(len(row["abbreviation"]) for row in rows)
    lang_w = max(len(row["lang"]) for row in rows)
    for row in rows:
        print(
            f"{row['source']:<{src_w}}  {row['id']:<{id_w}}  "
            f"{row['abbreviation']:<{abbr_w}}  {row['lang']:<{lang_w}}  "
            f"{row['description']}"
        )
    return 0


def _do_download(name: str, source: str | None) -> int:
    try:
        result = download_module(name, source)
    except DownloadError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    print(
        f"Installed {result['id']} from {result['source']} "
        f"({result['files']} files) into ~/.sword"
    )
    return 0


def _resolve_module(name: str | None) -> str | None:
    try:
        return resolve_active_module(name)
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return None


def _do_set_module(name: str) -> int:
    try:
        module_id = resolve_active_module(name)
        save_config({"module": module_id})
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"biblecli: failed to write config: {exc}", file=sys.stderr)
        return 1
    print(f"Default module set to {module_id}")
    return 0


def _do_search(
    module: str,
    query: str,
    *,
    book: str | None,
    ignore_case: bool,
    max_results: int,
) -> int:
    if max_results < 1:
        print("biblecli: --max must be >= 1", file=sys.stderr)
        print('  biblecli --search "only begotten" --max 50', file=sys.stderr)
        return 1
    try:
        matches, truncated = search_verses(
            module,
            query,
            book=book,
            ignore_case=ignore_case,
            max_results=max_results,
        )
    except ValueError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        print('  biblecli --search "only begotten"', file=sys.stderr)
        return 1
    except (ModuleError, VerseLookupError) as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    if not matches:
        where = f" in {book}" if book else ""
        print(f"biblecli: no matches for {query!r}{where} in {module}", file=sys.stderr)
        return 1
    print(format_verses(matches))
    if truncated:
        print(
            f"biblecli: showing {len(matches)} matches; pass --max N for more",
            file=sys.stderr,
        )
    return 0


def _page_text(text: str) -> None:
    pager = os.environ.get("PAGER")
    cmd = shlex.split(pager) if pager else ["less", "-FRX"]
    try:
        subprocess.run(cmd, input=text + "\n", text=True, check=False)
        return
    except (FileNotFoundError, OSError):
        pass
    print(text)


def _emit_lookup(text: str, *, page: bool) -> None:
    if page and sys.stdout.isatty() and sys.stdin.isatty():
        _page_text(text)
        return
    print(text)


def _lookup(
    module: str,
    book: str,
    ref: VerseRef,
    *,
    plain: bool,
) -> int:
    try:
        canonical = resolve_book(module, book)
        text = get_verses(module, canonical, ref, plain=plain)
    except ValueError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except VerseLookupError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    _emit_lookup(text, page=ref.whole_chapter and not plain)
    return 0


def _run_interactive(
    module: str,
    *,
    book: str | None = None,
    chapter: int | None = None,
) -> int:
    from biblecli.tui import run_reader

    return run_reader(module, book=book, chapter=chapter)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    action_flags = [
        flag
        for flag, enabled in (
            ("--list", args.list),
            ("--list-books", args.list_books),
            ("--sources", args.sources),
            ("--refresh", args.refresh),
            ("--list-remote", args.list_remote),
            ("--download", bool(args.download)),
            ("--search", bool(args.search)),
            ("--set-module", bool(args.set_module)),
        )
        if enabled
    ]
    if len(action_flags) > 1:
        parser.error("use only one of " + ", ".join(action_flags))

    passage = " ".join(args.passage).strip()
    if passage and (args.book or args.verse):
        parser.error("use either a positional reference or -b/-v, not both")
    if args.search and passage:
        parser.error(
            '--search does not take a positional reference; '
            'use -b to limit books (biblecli --search "love" -b John)'
        )

    if args.sources:
        return _print_sources()
    if args.refresh:
        return _do_refresh(args.source)
    if args.list_remote:
        lang = None if args.lang.strip().lower() == "all" else args.lang
        return _print_remote(args.source, lang)
    if args.download:
        return _do_download(args.download, args.source)
    if args.list:
        return _print_modules()
    if args.set_module:
        return _do_set_module(args.set_module)
    if args.list_books:
        module = _resolve_module(args.module)
        if module is None:
            return 1
        return _print_books(module)
    if args.search:
        module = _resolve_module(args.module)
        if module is None:
            return 1
        return _do_search(
            module,
            args.search,
            book=args.book,
            ignore_case=not args.case_sensitive,
            max_results=args.max,
        )

    book: str | None = None
    ref: VerseRef | None = None
    if passage:
        try:
            parsed = parse_passage(passage)
        except ValueError as exc:
            print(f"biblecli: {exc}", file=sys.stderr)
            return 1
        book, ref = parsed.book, parsed.ref
    elif args.book and args.verse:
        try:
            ref = parse_verse_ref(args.verse)
        except ValueError as exc:
            print(f"biblecli: {exc}", file=sys.stderr)
            return 1
        book = args.book
    elif args.book or args.verse:
        parser.error(
            "both -b/--book and -v/--verse are required "
            "(or pass a positional reference: biblecli John 3:16)"
        )

    if args.interactive:
        module = _resolve_module(args.module)
        if module is None:
            return 1
        chapter = ref.chapter if ref is not None else None
        return _run_interactive(module, book=book, chapter=chapter)

    if book is not None and ref is not None:
        module = _resolve_module(args.module)
        if module is None:
            return 1
        return _lookup(module, book, ref, plain=args.plain)

    # No action and no reference: interactive on a tty, else a fast error.
    if sys.stdin.isatty() and sys.stdout.isatty():
        module = _resolve_module(args.module)
        if module is None:
            return 1
        return _run_interactive(module)

    parser.error(
        "missing reference; examples:\n"
        "  biblecli John 3:16\n"
        "  biblecli --search \"only begotten\"\n"
        "  biblecli --list\n"
        "  biblecli -i"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
