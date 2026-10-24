# biblecli

Command-line Bible reader for [SWORD](https://wiki.crosswire.org/Main_Page) modules via [pysword](https://pypi.org/project/pysword/).

Downloads use HTTPS catalog + ZIP packages (JSword-style), so no C++ SWORD library is required on Linux or macOS.

## Install

Requires Python 3.9+. Build the standalone zipapp, then copy that file (not `bin/biblecli`, which only works inside this checkout):

```bash
make zipapp
cp dist/biblecli ~/Applications/    # or: sudo cp dist/biblecli /usr/local/bin/
```

## Usage

```bash
# Read (uses the default module once set)
biblecli John 3:16
biblecli John 3:16-18
biblecli John 3
biblecli -m KJV John 3:16
biblecli -m ASV -b John -v 3:16

# Default module
biblecli --list
biblecli --set-module ASV

# Search
biblecli --search "only begotten"
biblecli --search "love" -b John
biblecli --search "love" --max 100
biblecli --search "Love" --case-sensitive

# Interactive chapter reader (tty)
biblecli -i
biblecli -i John 3

# Installed modules
biblecli --list
biblecli --list-books
biblecli -m ASV --list-books

# Download (pure Python, into ~/.sword)
biblecli --sources
biblecli --refresh
biblecli --list-remote -s CrossWire
biblecli --list-remote -s CrossWire --lang es
biblecli --list-remote --lang all
biblecli --download KJV
biblecli --download engKJV1769eb -s eBible.org
```

| Flag | Meaning |
|------|---------|
| *(positional)* | Book and verse, e.g. `John 3:16`, `1 John 3:16-18`, `John 3` |
| `-m` / `--module` | Module id (e.g. `ASV`) or unique abbreviation |
| `-b` / `--book` | Book name or abbreviation from `--list-books` (case-insensitive) |
| `-v` / `--verse` | `N` (chapter), `N:M`, or `N:M-P` (same-chapter range) |
| `-s` / `--source` | Remote source for refresh / list-remote / download |
| `--lang` | Language for `--list-remote` (default: `en`; use `all` for every language) |
| `--list` | List installed modules |
| `--list-books` | List books for the active module (needed for Apocrypha naming) |
| `--search QUERY` | Search verse text in the active module |
| `--max N` | Maximum search hits (default: 50) |
| `--case-sensitive` | Make `--search` match case (default: ignore case) |
| `--set-module NAME` | Save the default module in `~/.sword/biblecli/config.toml` |
| `-i` / `--interactive` | Open the chapter reader (requires a tty) |
| `--plain` | Print verse text without numbers or reference labels |
| `--sources` | List built-in download sources |
| `--refresh` | Refresh remote catalog cache under `~/.sword/biblecli/repos/` |
| `--list-remote` | List remote Bible modules (from cache; refreshes if missing) |
| `--download` | Download and install a module ZIP into `~/.sword` |

Reading output is numbered (`John 3:16 For God so loved...`). A whole chapter prints a header and per-verse numbers, and pages through `$PAGER` or `less` when stdout is a tty. Use `--plain` for unlabeled pipeline text.

The active module is `-m`, then `BIBLECLI_MODULE`, then `module` in `~/.sword/biblecli/config.toml`, then the only installed module.

## Modules

Modules install to `~/.sword/mods.d/` and `~/.sword/modules/`. Built-in sources: **CrossWire** and **eBible.org**.

## Changelog

### 0.2.0

- Numbered verse output (chapter header + per-verse numbers); `--plain` for unlabeled pipelines
- Positional references: `biblecli John 3:16`, `1 John 3:16-18`, `John 3`
- Default module via `--set-module`, `BIBLECLI_MODULE`, or `~/.sword/biblecli/config.toml`
- Full-text `--search` with `-b`, `--max`, and `--case-sensitive`
- Interactive curses chapter reader (`-i`, or no args on a tty)
- TTY pager for whole-chapter reads (`$PAGER` or `less`)
- Checkout launcher (`bin/biblecli`) runs from any cwd; install the zipapp from `dist/biblecli`

### 0.1.0

- Look up a verse, range, or chapter from an installed SWORD module (`-m` `-b` `-v`)
- List installed modules and books
- Download Bible modules over HTTPS from CrossWire and eBible.org (no libsword)
- Remote catalog refresh, language filter, and zipapp packaging

## Todo

- More SWORD sources (CrossWire Beta/Attic, IBT) and user-defined catalog URLs
- Parallel translations in one invocation
- `--json` output for lookup and search
- Module uninstall and update
- Commentaries and other non-Bible module types (needs more than pysword)
