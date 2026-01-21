from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, OptionList, Static, Label
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
                options.append(Option("Reinstall", id="reinstall"))
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
    }
    """

    def __init__(self, title: str):
        super().__init__()
        self.title_text = title
        self.content_widget = None

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Static(self.title_text, id="progress-title")
            self.content_widget = Static("", id="progress-content")
            yield self.content_widget

    def update_content(self, text: str):
        """Update the progress content."""
        if self.content_widget:
            self.content_widget.update(text)

    def on_key(self, event: events.Key) -> None:
        """Handle escape key to close."""
        if event.key == "escape" or event.key == "enter":
            self.dismiss()


class ClickableDataTable(DataTable):
    """DataTable with clickable rows."""

    def on_click(self, event: events.Click) -> None:
        """Handle row clicks - update cursor position first."""
        # Get the row that was clicked
        try:
            # Move cursor to clicked row
            if event.y > 0:  # Skip header row
                row = event.y - 1  # Adjust for header
                if 0 <= row < self.row_count:
                    self.move_cursor(row=row)
                    # Then trigger the action
                    if self.app and hasattr(self.app, 'action_show_package_actions'):
                        self.app.action_show_package_actions()
        except:
            pass


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
        ("t", "show_theme_selector", "Theme"),
        ("enter", "show_package_actions", "Actions"),
    ]

    current_theme_name = reactive("default")

    def __init__(self, pkgs, theme_entry, all_themes, search_query=""):
        super().__init__()
        self.pkgs = pkgs
        self.theme_entry = theme_entry
        self.all_themes = all_themes
        self.search_query = search_query
        self.table = None
        self._initial_theme_name = theme_entry.get("name", "default")

    def compose(self) -> ComposeResult:
        self.table = ClickableDataTable()
        yield self.table
        yield Footer()

    def on_mount(self):
        # Set the theme name now that table exists
        self.current_theme_name = self._initial_theme_name
        self._build_table()

    def watch_current_theme_name(self, new_theme: str) -> None:
        """React to theme changes and rebuild table."""
        # Only rebuild if table exists (not during initialization)
        if self.table is not None and new_theme in self.all_themes:
            self.theme_entry = self.all_themes[new_theme]
            self._build_table()

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

    def _get_selected_package(self):
        """Get the currently selected package info."""
        if not self.table or self.table.cursor_row is None:
            return None
        if self.table.cursor_row < 0 or self.table.cursor_row >= len(self.pkgs):
            return None
        return self.pkgs[self.table.cursor_row]

    def action_show_package_actions(self):
        """Show the package action menu."""
        pkg = self._get_selected_package()
        if not pkg:
            self.notify("No package selected", severity="warning")
            return

        def handle_action(action: str | None):
            if not action:
                return

            if action == "install":
                self._run_pip_install(pkg['name'])
            elif action == "update":
                self._run_pip_install(pkg['name'], upgrade=True)
            elif action == "reinstall":
                self._run_pip_install(pkg['name'], reinstall=True)
            elif action == "uninstall":
                self._run_pip_uninstall(pkg['name'])

        self.push_screen(
            PackageActionScreen(pkg),
            handle_action
        )

    @work(exclusive=True)
    async def _run_pip_install(self, package: str, upgrade: bool = False, reinstall: bool = False):
        """Run pip install in background."""
        action = "Reinstalling" if reinstall else ("Updating" if upgrade else "Installing")
        progress = ProgressScreen(f"{action} {package}")
        self.push_screen(progress)

        cmd = [sys.executable, "-m", "pip", "install"]
        if upgrade:
            cmd.append("--upgrade")
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
                action_past = "reinstalled" if reinstall else ("updated" if upgrade else "installed")
                self.notify(f"Successfully {action_past} {package}", severity="information")
                # Refresh package data
                await self._refresh_packages()
            else:
                action_past = "reinstall" if reinstall else ("update" if upgrade else "install")
                self.notify(f"Failed to {action_past} {package}", severity="error")
        except Exception as e:
            progress.update_content(f"Error: {str(e)}")
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
                self.notify(f"Successfully uninstalled {package}", severity="information")
                # Refresh package data
                await self._refresh_packages()
            else:
                self.notify(f"Failed to uninstall {package}", severity="error")
        except Exception as e:
            progress.update_content(f"Error: {str(e)}")
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
            if status == "Installed":
                color = theme_colors.get("installed", "#00ff00")
            elif status == "Outdated":
                color = theme_colors.get("outdated", "#ffff00")
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
