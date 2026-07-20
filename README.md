# biblecli

Command-line Bible reader for [SWORD](https://wiki.crosswire.org/Main_Page) modules via [pysword](https://pypi.org/project/pysword/).

## Install

Requires Python 3.9+ and Bible modules under `~/.sword` (the usual CrossWire layout).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
biblecli --list
biblecli -m ASV --list-books
biblecli -m KJVD --list-books
biblecli -m ASV -b John -v 3:16
biblecli -m ASV -b John -v 3:16-18
biblecli -m ASV -b John -v 3
biblecli -m KJVD -b Wisdom -v 1:1
biblecli -m KJVD -b 1Macc -v 1:1
```


From a source checkout (after activating a venv that has `pysword`):

```bash
python -m biblecli -m ASV -b John -v 3:16
./bin/biblecli -m ASV -b John -v 3:16
```

| Flag | Meaning |
|------|---------|
| `-m` / `--module` | Module id (e.g. `ASV`) or unique abbreviation |
| `-b` / `--book` | Book name or abbreviation from `--list-books` (case-insensitive) |
| `-v` / `--verse` | `N` (chapter), `N:M`, or `N:M-P` (same-chapter range) |
| `--list` | List installed modules |
| `--list-books` | List books for `-m` (needed for Apocrypha naming) |

## Modules

Install modules with a SWORD front-end (e.g. BibleTime) or CrossWire tools so that `~/.sword/mods.d/` and `~/.sword/modules/` are populated.
