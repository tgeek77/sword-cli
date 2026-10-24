from __future__ import annotations

import pytest

from biblecli.sword import ModuleError, list_modules, resolve_active_module, resolve_module_id


def _modules(monkeypatch, found: dict) -> None:
    monkeypatch.setattr(
        "biblecli.sword._load_modules",
        lambda path=None: (None, found),
    )


def test_cli_flag_wins(monkeypatch):
    _modules(
        monkeypatch,
        {"ASV": {"abbreviation": "ASV"}, "KJV": {"abbreviation": "KJV"}},
    )
    assert resolve_active_module("kjv", env="ASV", config={"module": "ASV"}) == "KJV"


def test_env_then_config(monkeypatch):
    _modules(
        monkeypatch,
        {"ASV": {"abbreviation": "ASV"}, "KJV": {"abbreviation": "KJV"}},
    )
    assert resolve_active_module(None, env="ASV", config={"module": "KJV"}) == "ASV"
    assert resolve_active_module(None, env="", config={"module": "KJV"}) == "KJV"


def test_only_installed_module(monkeypatch):
    _modules(monkeypatch, {"ASV": {"abbreviation": "ASV"}})
    assert resolve_active_module(None, env="", config={}) == "ASV"


def test_multiple_without_default(monkeypatch):
    _modules(
        monkeypatch,
        {"ASV": {"abbreviation": "ASV"}, "KJV": {"abbreviation": "KJV"}},
    )
    with pytest.raises(ModuleError, match="no default module"):
        resolve_active_module(None, env="", config={})


def test_none_installed(monkeypatch):
    _modules(monkeypatch, {})
    with pytest.raises(ModuleError, match="no SWORD modules"):
        resolve_active_module(None, env="", config={})


def test_list_modules_missing_library(tmp_path):
    assert list_modules(path=tmp_path / "missing-sword") == []


def test_ambiguous_abbreviation():
    found = {
        "ASV": {"abbreviation": "KJV"},
        "WEB": {"abbreviation": "KJV"},
    }
    with pytest.raises(ModuleError, match="ambiguous"):
        resolve_module_id("KJV", found)
    assert resolve_module_id("ASV", found) == "ASV"
