# pip-search-ex

**A fast PyPI search with a classic table mode and an interactive TUI that can install, update and uninstall what it finds. The replacement for the discontinued `pip search`. Part of the [DwarvenSuite](https://github.com/gitdwarf).**

## Philosophy

- **One search, two front ends** -- the TUI, `--raw` and `--raw --raw` (CSV) all run the same core search. They differ only in how the results are drawn
- **Works immediately** -- every package name on PyPI is searchable from the first run; descriptions fill in as the cache grows
- **Gentle on PyPI** -- ETag-validated index, a browser-style metadata cache, and a rate-limited background worker. Never a request storm
- **No surprises** -- the status column tells you what is installed, what is outdated, and who installed it

## What it does

`pip-search-ex` searches all of PyPI by package name, and by summary wherever the local metadata cache already knows it. The cache builds quietly in the background, so searches get richer the more you use it.

- **Name search** -- all 790K+ PyPI package names, instantly, from a local index
- **Description search** -- opportunistic, from cached metadata, improving over time
- **Installed status** -- every result is marked Installed, Outdated, Newer or Not Installed
- **Package management** -- install, update, reinstall, downgrade and uninstall from inside the TUI, with the list refreshing as soon as the action finishes

## Features

- **Inclusive OR search** -- `pip-search-ex pip search ex` matches `pip` OR `search` OR `ex` in name or description. No quotes needed
- **Exact lookups** -- `--packages` / `-p` looks up specific names; `--explicit` makes a normal query exact
- **Filters** -- `--installed` and `--outdated` are always exact and cache-only, so they never hit PyPI
- **Origin markers** -- `[S]` for a system (root) pip install, `[D]` for a distro-managed package. Your own user installs are left plain. A legend line explains them, and drops `[S]` when you are root
- **Two display modes** -- interactive TUI (default), or `--raw` for the classic table
- **CSV output** -- `--raw --raw` for scripts and pipes
- **PEP 668 aware** -- on externally-managed systems (Ubuntu, Debian and friends) the TUI adds `--break-system-packages` for you
- **20+ themes** -- including a light-terminal theme, plus your own drop-in XML themes
- **Cache status** -- `--status` shows how complete the local metadata cache is
- **Self-update notice** -- checked at most once every 24 hours

## Installation

    pip install pip-search-ex

Or from source:

    git clone https://github.com/gitdwarf/pip-search-ex.git
    cd pip-search-ex
    pip install -e .

Requires Python 3.8+. Dependencies: requests, wcwidth, textual, packaging.

## Usage

    # Interactive TUI
    pip-search-ex django

    # Classic table
    pip-search-ex django --raw

    # CSV: name,version,status,summary
    pip-search-ex django --raw --raw

    # Inclusive OR across several words
    pip-search-ex pip search ex

    # Exact lookups
    pip-search-ex -p gtk4 jellyfin kodi
    pip-search-ex --explicit requests

    # What you have
    pip-search-ex --installed --raw
    pip-search-ex --outdated --raw

    # No 200-result cap
    pip-search-ex flask --full

    # Cache completion
    pip-search-ex django --raw --status

    # Force a fresh download of the PyPI index
    pip-search-ex django --flush

## Flags

| Flag | Action |
|---|---|
| `--raw` | Table output. Twice (`--raw --raw`) gives CSV |
| `--packages`, `-p` | Exact lookup of one or more package names |
| `--explicit` | Exact name match only (case-insensitive; `-` `_` `.` equivalent) |
| `--installed` | Only installed packages |
| `--outdated` | Only outdated packages |
| `--full` | Return every match instead of the first 200 |
| `--status` | Show the cache status banner |
| `--flush` | Force a fresh download of the PyPI index |
| `--version` | Print the version |
| theme flags | `--nord`, `--dracula`, `--inverse` and so on (see Themes) |

## TUI

- **Arrow keys or mouse** to move through results
- **Enter or click** on a package for its actions:
  - Install (not installed)
  - Update (outdated)
  - Reinstall (installed)
  - Uninstall (installed)
  - Downgrade (installed version newer than the server's)
- **s** opens the search box. It takes the same input as the command line: several words are an inclusive OR search, exactly as `--raw` treats them
- **e** toggles Explicit, **i** Installed only, **o** Outdated only, **f** Full (no 200-result cap)
- **t** changes theme on the fly
- **q** quits (or press **esc** twice)

## Raw mode

`--raw` prints a bordered table like the original `pip search`, with colour-coded status, origin markers, and wrapped descriptions. It plays well with the usual tools:

    pip-search-ex django --raw | grep -i rest
    pip-search-ex flask --raw --no-color > packages.txt

## Origin markers

| Marker | Meaning |
|---|---|
| (none) | Installed by you with pip, as your user |
| `[S]` | Installed system-wide by pip as root (not shown when you are root) |
| `[D]` | Distro-managed; check your package manager |

## Themes

Built in: `default`, `light-terminal`, `nord`, `solarized` (dark and light), `dracula`, `monokai`, `gruvbox`, `rose-pine` (and Moon, Dawn), `tokyo-night`, `catppuccin` (Latte, Frappe, Macchiato, Mocha), `atom-one` (dark and light), and more. `none` gives plain text.

    pip-search-ex django --nord
    pip-search-ex flask --theme-solarized
    pip-search-ex numpy --inverse           # light terminal theme
    pip-search-ex pandas --light-terminal   # same thing
    pip-search-ex requests --no-color

Each theme has several alias flags (for example `--nord`, `--theme-nord`, `--tn`).

### Custom themes

Drop theme XML files into either directory. Both are scanned automatically; the config directory wins on a name clash, and both override bundled themes of the same name.

- `~/.config/pip-search-ex/themes/`
- `~/.cache/pip_search_ex/themes/`

Invalid or corrupt files are skipped with a warning and never crash PSE (it falls back to `default`). Check your themes with:

    python3 validate_themes.py

A valid theme needs all seven colour keys:

    <theme name="my-theme">
      <aliases>
        <alias>--theme-my-theme</alias>
        <alias>--my-theme</alias>
      </aliases>
      <colors>
        <installed>#56949f</installed>
        <outdated>#ea9d34</outdated>
        <not_installed>#575279</not_installed>
        <error>#b4637a</error>
        <header>#907aa9</header>
        <border>#cecacd</border>
        <default>#575279</default>
      </colors>
    </theme>

Colours are hex values, converted to ANSI 256-colour codes for the terminal.

## Cache

Everything lives in `~/.cache/pip_search_ex/`:

| File | Holds |
|---|---|
| `simple_index.json` | Every PyPI package name. Refreshed with ETags, 24 hour TTL |
| `metadata_db.json` | Version and summary per package. Each entry expires 360 days after it was last used, so packages you touch never go stale |
| `version_cache.json` | Fast version lookups |

A detached background worker fills the metadata cache at 2 requests a second.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for what changed in each release.

## Part of DwarvenSuite

All tools follow the same philosophy: small, fast, correct, as few dependencies as possible.

## Author

thedwarf -- gitdwarf

## Support / Tip Jar

If you find pip-search-ex useful, you can support the project:

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://www.paypal.com/paypalme/gitdwarf)

## License

MIT -- see the LICENSE file for details.
