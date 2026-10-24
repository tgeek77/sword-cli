from __future__ import annotations

import pytest

from biblecli.cli import build_parser, main


def test_parser_positional_passage():
    args = build_parser().parse_args(["John", "3:16"])
    assert args.passage == ["John", "3:16"]
    assert args.module is None


def test_parser_flags_still_work():
    args = build_parser().parse_args(["-m", "ASV", "-b", "John", "-v", "3:16"])
    assert args.module == "ASV"
    assert args.book == "John"
    assert args.verse == "3:16"
    assert args.passage == []


def test_help_includes_examples(capsys):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "biblecli John 3:16" in out
    assert "biblecli --search" in out


def test_mixing_passage_and_book_flags_errors(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["John", "3:16", "-b", "John"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "positional reference or -b/-v" in err


def test_search_rejects_positional(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--search", "love", "John"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--search does not take a positional" in err


def test_missing_ref_off_tty_errors(monkeypatch, capsys):
    monkeypatch.setattr("biblecli.cli.sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("biblecli.cli.sys.stdout.isatty", lambda: False)
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "biblecli John 3:16" in err


def test_lookup_positional(monkeypatch, capsys):
    from biblecli.refs import VerseRef

    monkeypatch.setattr("biblecli.cli.resolve_active_module", lambda name: "ASV")
    monkeypatch.setattr("biblecli.cli.resolve_book", lambda module, book: "John")

    captured: dict = {}

    def fake_get(module, book, ref, plain=False):
        captured["args"] = (module, book, ref, plain)
        return "John 3:16 For God so loved the world"

    monkeypatch.setattr("biblecli.cli.get_verses", fake_get)
    monkeypatch.setattr("biblecli.cli.sys.stdout.isatty", lambda: False)
    assert main(["John", "3:16"]) == 0
    assert capsys.readouterr().out == "John 3:16 For God so loved the world\n"
    module, book, ref, plain = captured["args"]
    assert (module, book, plain) == ("ASV", "John", False)
    assert ref == VerseRef(chapter=3, verse_start=16)


def test_interactive_requires_tty(monkeypatch, capsys):
    monkeypatch.setattr("biblecli.cli.resolve_active_module", lambda name: "ASV")
    monkeypatch.setattr("biblecli.cli.sys.stdin.isatty", lambda: False)
    monkeypatch.setattr("biblecli.cli.sys.stdout.isatty", lambda: False)
    assert main(["-i"]) == 1
    err = capsys.readouterr().err
    assert "requires a tty" in err
    assert "biblecli John 3:16" in err


def test_search_prints_hits(monkeypatch, capsys):
    from biblecli.format import Verse

    monkeypatch.setattr("biblecli.cli.resolve_active_module", lambda name: "ASV")
    monkeypatch.setattr(
        "biblecli.cli.search_verses",
        lambda *args, **kwargs: (
            [Verse("John", 3, 16, "For God so loved the world")],
            False,
        ),
    )
    assert main(["--search", "loved"]) == 0
    assert capsys.readouterr().out == "John 3:16 For God so loved the world\n"
