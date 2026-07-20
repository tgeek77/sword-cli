"""Argparse entrypoint for biblecli."""

from __future__ import annotations

import argparse
import sys

from biblecli import __version__
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
        description="Read installed SWORD Bible modules from the command line.",
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list and args.list_books:
        parser.error("use only one of --list and --list-books")

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
            "the following arguments are required unless --list or "
            "--list-books is used: " + ", ".join(missing)
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
