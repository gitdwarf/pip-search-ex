# pip-search-ex

**PIP Search, Extended**

A modern replacement for the discontinued 'pip search' command.

Extended pip search with TUI interface and package management capabilities.

## Features

- **Fast package search** - Search PyPI with smart caching
- **Two display modes**:
  - **RAW mode** - Classic table output like the original 'pip search'
  - **TUI mode** - Interactive interface with package management
- **Package management** (TUI mode) - Install, update, and uninstall packages directly
- **Installation status** - See which packages are installed, outdated, or available
- **Multiple themes** - Choose from default, nord, solarized, or no-color themes
- **Concurrent fetching** - Fast parallel metadata retrieval
- **Smart caching** - Efficient index caching with ETags

## Installation

    pip install pip-search-ex

## Usage

### Basic search (TUI mode)

    pip-search-ex django

Opens an interactive terminal interface where you can browse, install, update, and uninstall packages.

### Raw mode (classic pip search style)

    pip-search-ex django --raw

Displays results in a clean table format, just like the original 'pip search' command. Perfect for:
- Quick searches without entering TUI
- Scripting and automation
- Piping to other commands
- Users who prefer the classic experience

### Choose a theme

    # Nord theme
    pip-search-ex pillow --nord

    # Solarized theme
    pip-search-ex flask --theme-solarized

    # No colors
    pip-search-ex requests --no-color

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

Use '--raw' or '--basic' for simple table output that mimics the original 'pip_search':

    pip-search-ex numpy --raw

Features in raw mode:
- Clean, bordered table layout
- Color-coded installation status
- Multi-line text wrapping for long descriptions
- Works great with grep, awk, and other Unix tools:

    pip-search-ex django --raw | grep -i rest
    pip-search-ex --raw flask --no-color > packages.txt

## Themes

pip-search-ex includes 21 built-in themes including:
- 'default' - Classic green/yellow/gray
- 'nord' - Nord color palette
- 'solarized' - Solarized color scheme
- 'dracula' - Dracula theme
- 'monokai' - Monokai color scheme
- 'gruvbox' - Gruvbox theme
- 'rose-pine' variants - Rose Pine, Rose Pine Moon, Rose Pine Dawn
- 'tokyo-night' - Tokyo Night theme
- 'catppuccin' variants - Latte, Frappe, Macchiato, Mocha
- 'one-dark' - Atom One Dark
- And more!
- 'none' - No colors (plain text)

### Using themes

    pip-search-ex django --nord
    pip-search-ex flask --theme-solarized
    pip-search-ex requests --rose-pine-dawn

Each theme has multiple alias flags for convenience (e.g., '--nord', '--theme-nord', '--tn').

### Creating custom themes

You can easily add your own themes by creating an XML file in the 'themes/' directory:

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

The original 'pip search' command was disabled in 2020 due to PyPI infrastructure limitations and hasn't returned. 'pip-search-ex' provides a modern, enhanced replacement:

**What we kept from the original:**
- Simple command-line interface: 'pip-search-ex <query>'
- Clean table output with '--raw' mode
- Color-coded installation status
- Fast search results

**What we improved:**
- **Dual modes**: Use classic RAW mode OR interactive TUI mode
- **Package management**: Install/update/uninstall without leaving the interface
- **Better performance**: Smart caching with ETags, concurrent metadata fetching
- **Customization**: Multiple color themes
- **Reliability**: Uses PyPI's official JSON API
- **Active maintenance**: Modern codebase, actively maintained

Whether you loved the simplicity of 'pip search' or want more power, 'pip-search-ex' has you covered!

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Author

thedwarf

## License

MIT License - see LICENSE file for details
