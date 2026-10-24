"""Load and save biblecli settings under ~/.sword/biblecli/config.toml."""

from __future__ import annotations

import os
import re
from pathlib import Path

from biblecli.paths import DEFAULT_SWORD_PATH

ENV_MODULE = "BIBLECLI_MODULE"
CONFIG_NAME = "config.toml"

_LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
_INT_RE = re.compile(r"^-?\d+$")


def default_config_path(sword_path: Path | None = None) -> Path:
    root = sword_path or DEFAULT_SWORD_PATH
    return root / "biblecli" / CONFIG_NAME


def _unquote(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        inner = raw[1:-1]
        return inner.replace(r"\"", '"').replace(r"\'", "'")
    return raw


def _parse_value(raw: str):
    text = raw.strip()
    if not text:
        return ""
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if _INT_RE.match(text):
        return int(text)
    return _unquote(text)


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', r"\"")
    return f'"{text}"'


def load_config(path: Path | None = None) -> dict[str, object]:
    """Return parsed config keys. Missing files yield an empty dict."""
    config_path = path or default_config_path()
    try:
        raw = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError:
        return {}

    data: dict[str, object] = {}
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _LINE_RE.match(stripped)
        if not match:
            continue
        data[match.group(1)] = _parse_value(match.group(2))
    return data


def save_config(
    updates: dict[str, object],
    path: Path | None = None,
) -> dict[str, object]:
    """Merge ``updates`` into the config file and return the new data."""
    config_path = path or default_config_path()
    data = load_config(config_path)
    for key, value in updates.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    config_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{key} = {_format_value(value)}" for key, value in data.items()]
    config_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return data


def configured_module(
    *,
    env: str | None = None,
    config: dict[str, object] | None = None,
    config_path: Path | None = None,
) -> str | None:
    """Module from ``BIBLECLI_MODULE`` or config, without touching SWORD files.

    ``env`` overrides the process environment when not None (pass ``""`` to
    ignore the environment). ``config`` overrides loading the config file.
    """
    if env is None:
        env_val = os.environ.get(ENV_MODULE)
    else:
        env_val = env
    if env_val and env_val.strip():
        return env_val.strip()

    data = load_config(config_path) if config is None else config
    module = data.get("module")
    if isinstance(module, str) and module.strip():
        return module.strip()
    return None
