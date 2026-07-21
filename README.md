# biblecli

Command-line Bible reader for [SWORD](https://wiki.crosswire.org/Main_Page) modules via [pysword](https://pypi.org/project/pysword/).

Downloads use HTTPS catalog + ZIP packages (JSword-style), so no C++ SWORD library is required on Linux or macOS.

## Install

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
# Installed modules
biblecli --list
biblecli -m ASV --list-books
biblecli -m ASV -b John -v 3:16
biblecli -m ASV -b John -v 3:16-18
biblecli -m ASV -b John -v 3

# Download (pure Python, into ~/.sword)
biblecli --sources
biblecli --refresh
biblecli --list-remote -s CrossWire
biblecli --list-remote -s CrossWire --lang es
biblecli --list-remote --lang all
biblecli --download KJV
biblecli --download engKJV1769eb -s eBible.org
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
| `-s` / `--source` | Remote source for refresh / list-remote / download |
| `--lang` | Language for `--list-remote` (default: `en`; use `all` for every language) |
| `--list` | List installed modules |
| `--list-books` | List books for `-m` (needed for Apocrypha naming) |
| `--sources` | List built-in download sources |
| `--refresh` | Refresh remote catalog cache under `~/.sword/biblecli/repos/` |
| `--list-remote` | List remote Bible modules (from cache; refreshes if missing) |
| `--download` | Download and install a module ZIP into `~/.sword` |

## Share one file (zipapp)

Build a single executable that bundles `biblecli` + `pysword` (needs Python 3.9+ on the machine, no venv):

```bash
make zipapp
# creates dist/biblecli
```

Give someone `dist/biblecli`:

```bash
chmod +x biblecli
./biblecli --help
./biblecli --refresh
./biblecli --download KJV
./biblecli -m KJV -b John -v 3:16
```

On Windows, run `python biblecli` (or rename to `biblecli.pyz`). Packaging logic lives only in [`scripts/build_zipapp.sh`](scripts/build_zipapp.sh); use `make clean-zipapp` to remove staging output.

## Modules

Modules install to `~/.sword/mods.d/` and `~/.sword/modules/`. Built-in sources: **CrossWire** and **eBible.org**.
