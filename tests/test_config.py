from __future__ import annotations

from pathlib import Path

from biblecli.config import configured_module, load_config, save_config


def test_save_and_load_roundtrip(tmp_path: Path):
    path = tmp_path / "config.toml"
    save_config({"module": "ASV", "last_book": "John", "last_chapter": 3}, path=path)
    data = load_config(path)
    assert data["module"] == "ASV"
    assert data["last_book"] == "John"
    assert data["last_chapter"] == 3


def test_save_merges_keys(tmp_path: Path):
    path = tmp_path / "config.toml"
    save_config({"module": "ASV"}, path=path)
    save_config({"last_book": "Matthew"}, path=path)
    data = load_config(path)
    assert data["module"] == "ASV"
    assert data["last_book"] == "Matthew"


def test_missing_config_is_empty(tmp_path: Path):
    assert load_config(tmp_path / "missing.toml") == {}


def test_configured_module_prefers_env(tmp_path: Path):
    path = tmp_path / "config.toml"
    save_config({"module": "ASV"}, path=path)
    assert (
        configured_module(env="KJV", config_path=path) == "KJV"
    )
    assert configured_module(env="", config_path=path) == "ASV"
    assert configured_module(env="", config={"module": "WEB"}) == "WEB"
    assert configured_module(env="", config={}) is None
