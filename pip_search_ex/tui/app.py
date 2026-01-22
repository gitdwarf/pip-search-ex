from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, OptionList, Static, Label, Input
from textual.widgets.option_list import Option
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual import events, work
import subprocess
import sys

class ThemeSelectorScreen(ModalScreen):
    """Modal screen for selecting themes."""

    CSS = """
    ThemeSelectorScreen {
        align: center middle;
    }

    #theme-dialog {
        width: 50;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }

    #theme-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $boost;
        color: $text;
        height: 3;
    }

    OptionList {
        height: auto;
        max-height: 15;
        border: none;
    }
    """

    def __init__(self, themes: dict, current_theme: str):
        super().__init__()
        self.themes = themes
        self.current_theme = current_theme

    def compose(self) -> ComposeResult:
        with Container(id="theme-dialog"):
            yield Static("Select Theme", id="theme-title")

            options = []
            for theme_name in self.themes.keys():
                # Mark current theme
                if theme_name == self.current_theme:
                    options.append(Option(f"{theme_name.capitalize()} ✓", id=theme_name))
                else:
                    options.append(Option(theme_name.capitalize(), id=theme_name))

            yield OptionList(*options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle theme selection."""
        self.dismiss(event.option_id)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to close."""
        if event.key == "escape":
            self.dismiss(None)


class SearchScreen(ModalScreen[str]):
    """Modal screen for entering a new search query."""

    CSS = """
    SearchScreen {
        align: center middle;
    }

    #search-dialog {
        width: 60;
        height: auto;
        border: thick $background 80%;
        background: $surface;
        padding: 2;
    }

    #search-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        padding: 0 0 1 0;
    }

    Input {
        width: 100%;
        margin: 1 0;
    }

    #search-hint {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        padding: 1 0 0 0;
    }
    """

    def __init__(self, current_query: str = ""):
        super().__init__()
        self.current_query = current_query

    def compose(self) -> ComposeResult:
        with Container(id="search-dialog"):
            yield Static("Search PyPI Packages", id="search-title")
            search_input = Input(placeholder="Enter package name...", value=self.current_query, id="search-input")
            yield search_input
            yield Static("Press Enter to search, Escape to cancel", id="search-hint")

    def on_mount(self) -> None:
        """Focus the input when mounted."""
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        query = event.value.strip().lower()
        self.dismiss(query)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to cancel."""
        if event.key == "escape":
            self.dismiss(None)


class PackageActionScreen(ModalScreen):
    """Modal screen for package actions."""

    CSS = """
    PackageActionScreen {
        align: center middle;
    }

    #action-dialog {
        width: 50;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }

    #action-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $boost;
        color: $text;
        height: 3;
    }

    OptionList {
        height: auto;
        max-height: 10;
        border: none;
    }
    """

    def __init__(self, package: dict):
        super().__init__()
        self.package = package

    def compose(self) -> ComposeResult:
        with Container(id="action-dialog"):
            title = f"{self.package['name']} {self.package['latest']}"
            if self.package['installed']:
                title += f" (installed: {self.package['installed']})"
            yield Static(title, id="action-title")

            options = []

            # Build options based on package status
            if not self.package['installed']:
                options.append(Option("Install", id="install"))
            elif self.package['status'] == "Outdated":
                options.append(Option(f"Update to {self.package['latest']}", id="update"))
                options.append(Option("Uninstall", id="uninstall"))
            elif self.package['status'] == "Newer":
                options.append(Option(f"Downgrade to {self.package['latest']}", id="downgrade"))
                options.append(Option("Uninstall", id="uninstall"))
            else:  # Installed and up-to-date
                options.append(Option("Reinstall", id="reinstall"))
                options.append(Option("Uninstall", id="uninstall"))

            # Always add cancel option
            options.append(Option("Cancel", id="cancel"))

            yield OptionList(*options)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle action selection."""
        self.dismiss(event.option_id)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to close."""
        if event.key == "escape":
            self.dismiss(None)


class ProgressScreen(ModalScreen):
    """Modal screen showing progress/results."""

    CSS = """
    ProgressScreen {
        align: center middle;
    }

    #progress-dialog {
        width: 80;
        height: 20;
        border: thick $background 80%;
        background: $surface;
    }

    #progress-title {
        dock: top;
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $boost;
        color: $text;
        height: 3;
    }

    #progress-content {
        width: 100%;
        height: 1fr;
        padding: 1 2;
        overflow-y: auto;
        scrollbar-gutter: stable;
    }

    #progress-content:focus {
        scrollbar-gutter: stable;
    }
    """

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title
        self.content_widget = None
        self._content_text = ""

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Static(self.title_text, id="progress-title")
            self.content_widget = Static("", id="progress-content")
            yield self.content_widget

    def update_content(self, text: str):
        """Update the progress content."""
        if self.content_widget:
            self._content_text = text
            self.content_widget.update(text)

    def set_complete(self):
        """Mark progress as complete and show exit hint."""
        if self.content_widget and hasattr(self, '_content_text'):
            separator = "="*60
            header = f"[bold cyan]Press any key to return to package list[/bold cyan]\n{separator}\n\n"
            self.content_widget.update(f"{header}{self._content_text}")

    def on_key(self, event: events.Key) -> None:
        """Handle any key to close."""
        event.stop()
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        """Handle mouse click to close."""
        event.stop()
        self.dismiss()


class PipSearchApp(App):
    """TUI application for searching PyPI packages."""

    CSS = """
    Screen {
        background: black;
    }

    DataTable {
        height: 1fr;
    }

    Footer {
        dock: bottom;
    }
    """

    # Disable the palette button
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "request_quit", ""),
        ("t", "show_theme_selector", "Theme"),
        ("enter", "show_package_actions", "Actions"),
        ("s", "show_search", "Search"),
    ]

    current_theme_name = reactive("default")

    def __init__(self, pkgs, theme_entry, all_themes, search_query=""):
        super().__init__()
        self.pkgs = pkgs
        self.theme_entry = theme_entry  # CLI-selected theme
        self.all_themes = all_themes
        self.search_query = search_query
        self.table = None

        # Find which theme name matches the current theme_entry
        # by comparing the actual dict objects
        matched_theme = "default"
        for name, entry in all_themes.items():
            if entry is theme_entry:
                matched_theme = name
                break

        self.current_theme_name = matched_theme
        self._quit_requested = False
        self._quit_timer = None

    def compose(self) -> ComposeResult:
        self.table = DataTable()
        yield self.table
        yield Footer()

    def on_mount(self):
        self._build_table()

    def watch_current_theme_name(self, new_theme: str) -> None:
        """React to theme changes and rebuild table."""
        # Only rebuild if table exists (not during initialization)
        if self.table is not None and new_theme in self.all_themes:
            self.theme_entry = self.all_themes[new_theme]
            self._build_table()

    def action_request_quit(self):
        """Handle ESC key - require double press to quit."""
        if self._quit_requested:
            # Second ESC within timeout - actually quit
            self.exit()
        else:
            # First ESC - show message and start timer
            self._quit_requested = True
            self.notify("Press ESC again to quit", timeout=1)
            # Reset flag after 1 second
            if self._quit_timer:
                self._quit_timer.cancel()
            self._quit_timer = self.set_timer(1.0, self._reset_quit_request)

    def _reset_quit_request(self):
        """Reset the quit request flag."""
        self._quit_requested = False
        self._quit_timer = None

    def action_show_theme_selector(self):
        """Show the theme selector modal."""
        def handle_theme_selection(theme_name: str | None) -> None:
            if theme_name and theme_name in self.all_themes:
                self.current_theme_name = theme_name
                # Force a complete rebuild
                if self.table:
                    self.table.focus()

        self.push_screen(
            ThemeSelectorScreen(self.all_themes, self.current_theme_name),
            handle_theme_selection
        )

    def action_show_search(self):
        """Show the search input modal."""
        def handle_search(query: str | None):
            if query is not None:  # None = cancelled, "" = search all
                self.search_query = query
                self._perform_search()

        self.push_screen(
            SearchScreen(self.search_query),
            handle_search
        )

    @work(exclusive=True)
    async def _perform_search(self):
        """Perform a new search with the current query."""
        from pip_search_ex.core.pypi import gather_packages

        # Show loading message
        self.notify(f"Searching for '{self.search_query}'..." if self.search_query else "Loading all packages...")

        # Fetch new results
        self.pkgs = gather_packages(self.search_query)

        # Rebuild table
        self._build_table()

        # Show result count
        count = len(self.pkgs)
        if self.search_query:
            self.notify(f"Found {count} package{'s' if count != 1 else ''} matching '{self.search_query}'")
        else:
            self.notify(f"Showing all packages (limited to {count})")

    def _get_selected_package(self):
        """Get the currently selected package info."""
        if not self.table or self.table.cursor_row is None:
            return None
        if self.table.cursor_row < 0 or self.table.cursor_row >= len(self.pkgs):
            return None
        return self.pkgs[self.table.cursor_row]

    def action_show_package_actions(self):
        """Show the package action menu for currently selected row."""
        pkg = self._get_selected_package()
        if not pkg:
            self.notify("No package selected", severity="warning")
            return
        self._show_package_actions_for(pkg)

    def _show_package_actions_for(self, pkg):
        """Show the package action menu for a specific package."""
        def handle_action(action: str | None):
            if not action or action == "cancel":
                return

            if action == "install":
                self._run_pip_install(pkg['name'])
            elif action == "update":
                self._run_pip_install(pkg['name'], upgrade=True)
            elif action == "downgrade":
                self._run_pip_install(pkg['name'], downgrade=True)
            elif action == "reinstall":
                self._run_pip_install(pkg['name'], reinstall=True)
            elif action == "uninstall":
                self._run_pip_uninstall(pkg['name'])

        self.push_screen(
            PackageActionScreen(pkg),
            handle_action
        )

    @work(exclusive=True)
    async def _run_pip_install(self, package: str, upgrade: bool = False, downgrade: bool = False, reinstall: bool = False):
        """Run pip install in background."""
        action = "Reinstalling" if reinstall else ("Downgrading" if downgrade else ("Updating" if upgrade else "Installing"))
        progress = ProgressScreen(f"{action} {package}")
        self.push_screen(progress)

        cmd = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
        if downgrade:
            cmd.append("--force-reinstall")
        if reinstall:
            cmd.extend(["--force-reinstall", "--no-deps"])
        cmd.append(package)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout + result.stderr
            progress.update_content(output)

            if result.returncode == 0:
                action_past = "reinstalled" if reinstall else ("downgraded" if downgrade else ("updated" if upgrade else "installed"))
                progress.set_complete()
                await self._refresh_packages()
                self.notify(f"Successfully {action_past} {package}", severity="information")
            else:
                action_past = "reinstall" if reinstall else ("downgrade" if downgrade else ("update" if upgrade else "install"))
                progress.set_complete()
                self.notify(f"Failed to {action_past} {package}", severity="error")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            progress.update_content(error_msg)
            progress.set_complete()
            self.notify(f"Error: {str(e)}", severity="error")

    @work(exclusive=True)
    async def _run_pip_uninstall(self, package: str):
        """Run pip uninstall in background."""
        progress = ProgressScreen(f"Uninstalling {package}")
        self.push_screen(progress)

        cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout + result.stderr
            progress.update_content(output)

            if result.returncode == 0:
                progress.set_complete()
                await self._refresh_packages()
                self.notify(f"Successfully uninstalled {package}", severity="information")
            else:
                progress.set_complete()
                self.notify(f"Failed to uninstall {package}", severity="error")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            progress.update_content(error_msg)
            progress.set_complete()
            self.notify(f"Error: {str(e)}", severity="error")

    async def _refresh_packages(self):
        """Refresh the package list after install/uninstall."""
        # Re-fetch package data with the original search query
        from pip_search_ex.core.pypi import gather_packages
        self.pkgs = gather_packages(self.search_query)
        self._build_table()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        self.action_show_package_actions()

    def _build_table(self):
        """Build the data table with current theme colors."""
        self.table.clear(columns=True)

        # Add columns - back to simple headers
        self.table.add_columns(
            "NAME",
            "VERSION",
            "INSTALLED",
            "STATUS",
            "SUMMARY"
        )

        theme_colors = self.theme_entry["colors"]

        for p in self.pkgs:
            status = p["status"]
            if status in ("Installed", "Newer"):
                color = theme_colors.get("installed", "#00ff00")
            elif status == "Outdated":
                color = theme_colors.get("outdated", "#ffff00")
            elif status == "Error":
                color = theme_colors.get("error", "#ff0000")
            else:
                color = theme_colors.get("not_installed", "#808080")

            self.table.add_row(
                f"[{color}]{p['name']}[/]",
                f"[{color}]{p['latest']}[/]",
                f"[{color}]{p['installed'] or ''}[/]",
                f"[{color}]{p['status']}[/]",
                f"[{color}]{p['summary']}[/]"
            )

        if self.pkgs:
            self.table.cursor_type = "row"
            self.table.focus()
