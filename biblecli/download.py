"""Pure-Python SWORD module catalog refresh and ZIP install (no libsword)."""

from __future__ import annotations

import io
import re
import shutil
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from biblecli import __version__
from biblecli.sword import DEFAULT_SWORD_PATH

USER_AGENT = f"biblecli/{__version__}"
CACHE_ROOT = DEFAULT_SWORD_PATH / "biblecli" / "repos"

_BIBLE_DRIVERS = frozenset({"ztext", "ztext4", "rawtext", "rawtext4"})

_CONF_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_CONF_KEY_RE = re.compile(r"^([^=]+)=(.*)$")


@dataclass(frozen=True)
class Source:
    """HTTPS catalog + ZIP package base for a remote SWORD repository."""

    name: str
    catalog_url: str
    zip_base_url: str


# JSword-style HTTPS endpoints (not FTP masterRepoList).
SOURCES: dict[str, Source] = {
    "CrossWire": Source(
        name="CrossWire",
        catalog_url="https://crosswire.org/ftpmirror/pub/sword/raw/mods.d.tar.gz",
        zip_base_url="https://crosswire.org/ftpmirror/pub/sword/packages/rawzip",
    ),
    "eBible.org": Source(
        name="eBible.org",
        catalog_url="https://ebible.org/sword/mods.d.tar.gz",
        zip_base_url="https://ebible.org/sword/zip",
    ),
}


class DownloadError(Exception):
    """Raised when a catalog refresh or module install fails."""


def list_sources() -> list[Source]:
    """Return built-in download sources in stable order."""
    return [SOURCES[name] for name in sorted(SOURCES)]


def resolve_source(name: str) -> Source:
    """Resolve a source name case-insensitively."""
    needle = name.strip().lower()
    for key, source in SOURCES.items():
        if key.lower() == needle:
            return source
    known = ", ".join(sorted(SOURCES))
    raise DownloadError(f"unknown source {name!r}; known: {known}")


def _cache_mods_d(source: Source) -> Path:
    return CACHE_ROOT / source.name / "mods.d"


def _http_get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=120) as response:
            return response.read()
    except HTTPError as exc:
        raise DownloadError(f"HTTP {exc.code} fetching {url}") from exc
    except URLError as exc:
        raise DownloadError(f"failed to fetch {url}: {exc.reason}") from exc


def _safe_member_path(name: str, allowed_roots: tuple[str, ...]) -> Path | None:
    """Return a relative Path if ``name`` is a safe archive member, else None."""
    # Zip/tar on Windows may use backslashes; normalize.
    normalized = name.replace("\\", "/").lstrip("/")
    if not normalized or normalized.endswith("/"):
        return None
    parts = Path(normalized).parts
    if ".." in parts or parts[0] == "..":
        return None
    if not any(normalized == root or normalized.startswith(root + "/") for root in allowed_roots):
        return None
    return Path(*parts)


def refresh_source(source: Source) -> int:
    """Download and extract a source catalog into the local cache.

    Returns the number of ``.conf`` files written.
    """
    data = _http_get(source.catalog_url)
    dest = _cache_mods_d(source)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    count = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                rel = _safe_member_path(member.name, ("mods.d",))
                if rel is None or rel.suffix.lower() != ".conf":
                    continue
                extracted = archive.extractfile(member)
                if extracted is None:
                    continue
                # Flat cache: only the conf basename under mods.d/
                target = dest / rel.name
                target.write_bytes(extracted.read())
                count += 1
    except tarfile.TarError as exc:
        raise DownloadError(f"invalid catalog archive from {source.name}: {exc}") from exc

    if count == 0:
        raise DownloadError(f"no module conf files found in catalog for {source.name}")
    return count


def refresh_sources(source_name: str | None = None) -> dict[str, int]:
    """Refresh one source or all sources. Returns ``{source_name: conf_count}``."""
    if source_name:
        source = resolve_source(source_name)
        return {source.name: refresh_source(source)}
    results: dict[str, int] = {}
    errors: list[str] = []
    for source in list_sources():
        try:
            results[source.name] = refresh_source(source)
        except DownloadError as exc:
            errors.append(str(exc))
    if not results and errors:
        raise DownloadError("; ".join(errors))
    return results


def _parse_conf(text: str) -> tuple[str | None, dict[str, str]]:
    """Parse a SWORD ``.conf`` into (module_id, lowercased keys)."""
    module_id: str | None = None
    meta: dict[str, str] = {}
    current_key = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        section = _CONF_SECTION_RE.match(line)
        if section:
            module_id = section.group(1)
            continue
        match = _CONF_KEY_RE.match(line)
        if match:
            current_key = match.group(1).strip().lower()
            meta[current_key] = match.group(2).strip()
        elif current_key:
            meta[current_key] = meta[current_key] + "\n" + line
    return module_id, meta


def _is_bible_module(meta: dict[str, str]) -> bool:
    driver = meta.get("moddrv", "").lower()
    return driver in _BIBLE_DRIVERS


def _ensure_cache(source: Source) -> Path:
    mods_d = _cache_mods_d(source)
    if not mods_d.is_dir() or not any(mods_d.glob("*.conf")):
        refresh_source(source)
    return mods_d


def list_remote_modules(
    source_name: str | None = None,
    *,
    lang: str | None = None,
    ensure_fresh: bool = True,
) -> list[dict[str, str]]:
    """List remote Bible modules from cached catalogs.

    If ``lang`` is set, only modules whose ``Lang`` matches (case-insensitive)
    are returned. If ``ensure_fresh`` and a cache is missing, refresh first.
    """
    sources = [resolve_source(source_name)] if source_name else list_sources()
    lang_filter = lang.strip().lower() if lang else None
    rows: list[dict[str, str]] = []
    for source in sources:
        mods_d = _ensure_cache(source) if ensure_fresh else _cache_mods_d(source)
        if not mods_d.is_dir():
            continue
        for conf_path in sorted(mods_d.glob("*.conf")):
            try:
                text = conf_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            module_id, meta = _parse_conf(text)
            if not module_id or not _is_bible_module(meta):
                continue
            module_lang = (meta.get("lang") or "").strip()
            if lang_filter is not None and module_lang.lower() != lang_filter:
                continue
            rows.append(
                {
                    "source": source.name,
                    "id": module_id,
                    "abbreviation": meta.get("abbreviation") or module_id,
                    "lang": module_lang or "?",
                    "description": meta.get("description") or "",
                }
            )
    rows.sort(key=lambda row: (row["source"].lower(), row["id"].lower()))
    return rows


def _find_module_in_cache(
    name: str,
    source: Source | None,
) -> tuple[Source, str]:
    """Return (source, canonical_module_id) for ``name`` from cache."""
    needle = name.strip().lower()
    sources = [source] if source else list_sources()
    id_hits: list[tuple[Source, str]] = []
    abbr_hits: list[tuple[Source, str]] = []

    for src in sources:
        mods_d = _cache_mods_d(src)
        if not mods_d.is_dir():
            continue
        for conf_path in mods_d.glob("*.conf"):
            try:
                text = conf_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            module_id, meta = _parse_conf(text)
            if not module_id or not _is_bible_module(meta):
                continue
            if module_id.lower() == needle:
                id_hits.append((src, module_id))
            abbr = (meta.get("abbreviation") or "").lower()
            if abbr and abbr == needle:
                abbr_hits.append((src, module_id))

    if len(id_hits) == 1:
        return id_hits[0]
    if len(id_hits) > 1:
        locs = ", ".join(f"{s.name}:{mid}" for s, mid in id_hits)
        raise DownloadError(f"module {name!r} found in multiple sources ({locs}); pass -s")
    if len(abbr_hits) == 1:
        return abbr_hits[0]
    if len(abbr_hits) > 1:
        locs = ", ".join(f"{s.name}:{mid}" for s, mid in abbr_hits)
        raise DownloadError(
            f"abbreviation {name!r} is ambiguous ({locs}); use the module id and -s"
        )
    raise DownloadError(f"module {name!r} not found in local catalog cache")


def _extract_zip_to_sword(data: bytes, install_root: Path) -> list[str]:
    """Safely extract a module ZIP into ``install_root``. Returns written paths."""
    written: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                # Skip symlinks (Unix external attr)
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    continue
                rel = _safe_member_path(info.filename, ("mods.d", "modules"))
                if rel is None:
                    continue
                target = install_root / rel
                # Ensure final path is still under install_root
                try:
                    target.resolve().relative_to(install_root.resolve())
                except ValueError as exc:
                    raise DownloadError(f"refusing unsafe zip path {info.filename!r}") from exc
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                written.append(str(rel))
    except zipfile.BadZipFile as exc:
        raise DownloadError(f"invalid module zip: {exc}") from exc

    if not written:
        raise DownloadError("zip contained no installable mods.d/ or modules/ files")
    if not any(path.startswith("mods.d/") and path.endswith(".conf") for path in written):
        raise DownloadError("zip missing mods.d/*.conf")
    return written


def download_module(
    name: str,
    source_name: str | None = None,
    *,
    install_root: Path | None = None,
) -> dict[str, str]:
    """Download and install a Bible module into the SWORD library.

    Returns a dict with ``source``, ``id``, and ``files`` (count as str).
    """
    root = install_root or DEFAULT_SWORD_PATH
    root.mkdir(parents=True, exist_ok=True)

    source = resolve_source(source_name) if source_name else None

    # Ensure catalogs exist, then resolve name -> (source, id)
    try:
        if source:
            _ensure_cache(source)
        else:
            for src in list_sources():
                _ensure_cache(src)
        source, module_id = _find_module_in_cache(name, source)
    except DownloadError:
        # Refresh once and retry
        if source_name:
            refresh_source(resolve_source(source_name))
            source = resolve_source(source_name)
            source, module_id = _find_module_in_cache(name, source)
        else:
            refresh_sources()
            source, module_id = _find_module_in_cache(name, None)

    zip_url = f"{source.zip_base_url.rstrip('/')}/{module_id}.zip"
    data = _http_get(zip_url)
    written = _extract_zip_to_sword(data, root)
    return {
        "source": source.name,
        "id": module_id,
        "files": str(len(written)),
    }
