"""Argparse entrypoint for biblecli."""

from __future__ import annotations

import argparse
import sys

from biblecli import __version__
from biblecli.download import (
    DownloadError,
    download_module,
    list_remote_modules,
    list_sources,
    refresh_sources,
)
from biblecli.refs import parse_verse_ref
from biblecli.sword import (
    ModuleError,
    VerseLookupError,
    get_verses,
    list_books,
    list_modules,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="biblecli",
        description="Read and download SWORD Bible modules from the command line.",
    )
    parser.add_argument(
        "-m",
        "--module",
        help="Bible module id or abbreviation (e.g. ASV)",
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
        help="List books for -m (names usable with -b) and exit",
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
        )
        if enabled
    ]
    if len(action_flags) > 1:
        parser.error("use only one of " + ", ".join(action_flags))

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
    if args.list_books:
        if not args.module:
            parser.error("--list-books requires -m/--module")
        return _print_books(args.module)

    missing = [
        flag
        for flag, value in (
            ("-m/--module", args.module),
            ("-b/--book", args.book),
            ("-v/--verse", args.verse),
        )
        if not value
    ]
    if missing:
        parser.error(
            "the following arguments are required unless a list/download "
            "action is used: " + ", ".join(missing)
        )

    try:
        ref = parse_verse_ref(args.verse)
        text = get_verses(args.module, args.book, ref)
    except ValueError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except ModuleError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1
    except VerseLookupError as exc:
        print(f"biblecli: {exc}", file=sys.stderr)
        return 1

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
