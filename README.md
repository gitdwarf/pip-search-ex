# pip-search-ex

**Modern PyPI Package Search - Fast, Smart, Beautiful**. Part of the [DwarvenSuite](https://github.com/gitdwarf).

A complete replacement for the discontinued `pip search` command with unified search architecture, interactive TUI, and 20+ themes.

## What's New in v2.0.8

- **OR search**: `pip-search-ex pip search ex` returns packages matching `pip` OR `search` OR `ex` in name or description -- inclusive, no quotes needed. Add `--explicit` to flip to exclusive exact matching
- **`--packages` / `-p`**: exact lookup for specific package names -- `pip-search-ex -p gtk4 jellyfin kodi`
- **`--installed` / `--outdated` / `--newer`**: always exact, always cache-only, never hit PyPI

## What's New in v2.0.7

- **Browser-style metadata cache**: Each cached package entry now has a 360-day LRU TTL. Access a package in a search and its clock resets. Don't touch it for 360 days and it gets evicted and re-fetched fresh next time. Actively used packages never go stale
- **Live fetch restored correctly**: Cache misses now fetch live from PyPI for all displayed results, rate-limited to ~6-7 req/sec. No more empty results on fresh installs or sparse caches

## What's New in v2.0.6

- **External theming -- two user theme dirs**: Drop your own theme XML files into either `~/.cache/pip_search_ex/themes/` or `~/.config/pip-search-ex/themes/`. Both are scanned automatically; config dir takes priority over cache dir
- **Invalid themes never crash PSE**: Bad XML, missing colour keys, or corrupt files are skipped at runtime with a warning -- PSE falls back to `default`
- **`validate_themes.py`**: Replaces the old `testthemes` bash script. Run it to check all theme dirs for missing required colour keys or XML errors before deploying themes

## What's New in v2.0.5

- **[S] / [D] origin markers**: Installed packages now show `[S]` (system/root pip install) or `[D]` (distro-managed) in the status column. Normal user installs show no marker -- no noise when it's just yours. Context-aware legend line appears at the top of both TUI and raw output, and omits `[S]` automatically when running as root
- **No more PyPI hammering**: All live fetches removed from the foreground search path. Cache misses return name-only results instantly; the background worker fills metadata in over time at 2 req/sec. PSE is now friendlier to PyPI than searching on PyPI directly
- **`--installed` is now fast**: No longer loads the full 500K package index when you only want to see what's installed
- **Lean cache**: `metadata_db.json` no longer embeds a redundant copy of the package index -- it now grows proportionally to cached metadata only

## What's New in v2.0.0

- **Unified Search**: Intelligent search that works immediately -- searches ALL PyPI packages by name, with opportunistic metadata enrichment as the cache builds
- **Cache Status**: New `--status` flag shows cache completion percentage
- **Light Terminal Theme**: Perfect for white/light backgrounds with `--inverse` / `--light-terminal`

## Features

- **🔍 Unified Search** - One intelligent search flow that just works:
  - Searches ALL PyPI packages by name (738K+ packages)
  - Opportunistic metadata search (summaries/descriptions from cache)
  - Progressive enhancement as cache builds in background
- **Two display modes**:
  - **RAW mode** - --raw: Classic table output like the original `pip search`
  - **TUI mode (default)** - Interactive interface with package management
- **📦 Package management** (TUI mode) - Install, update, and uninstall packages directly
- **📊 Installation status** - See which packages are installed, outdated, or available
- **🎨 20+ themes** - Including new light terminal theme (--inverse) for white backgrounds
- **⚡ Fast performance** - Concurrent fetching, smart caching with ETags
- **🔄 Background cache** - Builds progressively without blocking searches
- **📈 Cache visibility** - `--status` flag shows cache completion percentage

## Installation

    pip install pip-search-ex

## Usage

### Basic search (TUI mode)

    pip-search-ex django

Opens an interactive terminal interface where you can browse, install, update, and uninstall packages.

### Raw mode (classic pip search style)

    pip-search-ex django --raw

Displays results in a clean table format, just like the original `pip search` command. Perfect for:
- Quick searches without entering TUI
- Scripting and automation
- Piping to other commands
- Users who prefer the classic experience

### Show cache status

    pip-search-ex django --raw --status

Displays cache completion percentage to see background cache building progress.

### Choose a theme

    # Nord theme
    pip-search-ex pillow --nord

    # Solarized theme
    pip-search-ex flask --theme-solarized

    # No colors
    pip-search-ex requests --no-color
  
    # Inverted (for use with --raw on white terminal windows, eg default xterm)
    pip-search-ex pip-search --inverse

## TUI Mode

In TUI mode, you can:

- **Navigate** with arrow keys or mouse
- **Press Enter** or **click** on a package to see available actions:
  - Install (for uninstalled packages)
  - Update (for outdated packages)
  - Reinstall (for installed packages)
  - Uninstall (for installed packages)
  - Downgrade (for installed packages that are newer-than-server version)
- **Press 't'** to change themes on the fly
- **Press 'q'** to quit
- **Press 'esc' twice** to quit

## Raw Mode

Use '--raw' for simple table output that mimics the original 'pip_search':

    pip-search-ex numpy --raw

Features in raw mode:
- Clean, bordered table layout
- Color-coded installation status with origin markers (`[S]` = system/root pip install, `[D]` = distro-managed)
- Multi-line text wrapping for long descriptions
- Works great with grep, awk, and other Unix tools:

    pip-search-ex django --raw | grep -i rest
    pip-search-ex --raw flask --no-color > packages.txt

### CSV output mode

Use '--raw --raw' (double flag) for machine-readable CSV output:

    pip-search-ex numpy --raw --raw

Outputs `name,version,status,summary` -- perfect for scripting and automation:

    pip-search-ex requests --raw --raw | awk -F, '{print $1}'
    pip-search-ex flask --raw --raw | grep "Installed"

## Themes

pip-search-ex includes 21+ built-in themes including:
- **'light-terminal'** - Optimized for white/light backgrounds (NEW in v2.0.0!)
- 'default' - Classic green/yellow/gray
- 'nord' - Nord color palette
- 'solarized' - Solarized color scheme (dark and light variants)
- 'dracula' - Dracula theme
- 'monokai' - Monokai color scheme
- 'gruvbox' - Gruvbox theme
- 'rose-pine' variants - Rose Pine, Rose Pine Moon, Rose Pine Dawn
- 'tokyo-night' - Tokyo Night theme
- 'catppuccin' variants - Latte, Frappe, Macchiato, Mocha
- 'atom-one' variants - Dark and Light
- And more!
- 'none' - No colors (plain text)

### Using themes

    pip-search-ex django --nord
    pip-search-ex flask --theme-solarized
    pip-search-ex requests --rose-pine-dawn
    pip-search-ex numpy --inverse           # Light terminal theme
    pip-search-ex pandas --light-terminal   # Same as --inverse

Each theme has multiple alias flags for convenience (e.g., '--nord', '--theme-nord', '--tn').

### Creating custom themes

Drop your own theme XML files into either user theme directory -- both are scanned automatically:

- `~/.config/pip-search-ex/themes/` (preferred, XDG-style)
- `~/.cache/pip_search_ex/themes/` (also supported)

Config dir takes priority over cache dir. Both override bundled themes of the same name. Invalid or corrupt files are silently skipped -- they will never crash PSE.

To check your themes before use, run:

    python3 validate_themes.py

This scans all three directories (bundled, cache, config) and reports any missing required colour keys or XML errors.

A valid theme XML file looks like this:

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

Colors are specified as hex values and automatically converted to ANSI 256-color codes for terminal display.

## Requirements

- Python 3.8+
- requests
- wcwidth
- textual
- packaging (optional, for better version comparison)

## Why pip-search-ex?

The original `pip search` command was disabled in 2020 due to PyPI infrastructure limitations and hasn't returned. `pip-search-ex` provides a modern, enhanced replacement:

**What we kept from the original:**
- Simple command-line interface: `pip-search-ex <query>`
- Clean table output with `--raw` mode
- Color-coded installation status
- Fast search results

**What we improved:**
- **🔍 Unified Search**: Searches both names and progressivley over time package summaries!
- **📊 Cache visibility**: See cache progress with `--status` flag
- **Dual modes**: Use classic RAW mode OR interactive TUI mode
- **Package management**: Install/update/uninstall without leaving the interface
- **Better performance**: Smart caching, concurrent metadata fetching, background cache building
- **20+ themes**: Including light terminal theme for white backgrounds
- **Reliability**: Uses PyPI's official JSON API
- **Active maintenance**: Modern codebase with v2.0.0 release

Whether you loved the simplicity of `pip search` or want more power, `pip-search-ex` has you covered!

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Part of DwarvenSuite

All tools follow the same philosophy: small, fast, correct, as few dependencies as possible!

## Author

thedwarf -- gitdwarf

## Support / Tip Jar

If you find pip-search-ex useful, you can support the project:

[![Donate via PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://www.paypal.com/paypalme/gitdwarf)

## License

MIT License - see LICENSE file for details
