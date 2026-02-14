from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, OptionList, Static, Label, Input
from textual.widgets.option_list import Option
from textual.containers import Container, Vertical, Horizontal
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual import events
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

            # Check if package requires root/sudo to modify
            from pip_search_ex.core.pypi import package_needs_root
            needs_root, install_location = package_needs_root(self.package['name'])

            # If installed package needs root, show message instead of actions
            if needs_root and self.package['installed']:
                yield Static(
                    f"\n⚠️  Installed system-wide ({install_location})\n"
                    f"Run with sudo/root to modify:\n"
                    f"sudo pip-search-ex\n",
                    id="needs-root-message"
                )
                options.append(Option("Close", id="cancel"))
            else:
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
        self._spinner_frame = 0
        self._spinner_timer = None
        self._spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def on_mount(self) -> None:
        """Start spinner animation when mounted."""
        self._spinner_timer = self.set_interval(0.1, self._update_spinner)
    
    def _update_spinner(self) -> None:
        """Update spinner animation."""
        if self.content_widget:
            frame = self._spinner_frames[self._spinner_frame % len(self._spinner_frames)]
            self.content_widget.update(f"{frame} {self._content_text}")
            self._spinner_frame += 1

    def compose(self) -> ComposeResult:
        with Container(id="progress-dialog"):
            yield Static(self.title_text, id="progress-title")
            self.content_widget = Static("", id="progress-content")
            yield self.content_widget

    def update_content(self, text: str):
        """Update the progress content."""
        self._content_text = text
        # Spinner will update display automatically

    def set_complete(self):
        """Mark progress as complete and show exit hint."""
        # CRITICAL: Stop spinner first so it doesn't overwrite our message!
        if self._spinner_timer:
            self._spinner_timer.stop()
            self._spinner_timer = None
        
        if self.content_widget and hasattr(self, '_content_text'):
            separator = "="*60
            header = f"[bold cyan]Press any key to return to package list[/bold cyan]\n{separator}\n\n"
            self.content_widget.update(f"{header}{self._content_text}")
    
    def on_unmount(self) -> None:
        """Stop spinner when unmounting."""
        if self._spinner_timer:
            self._spinner_timer.stop()

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

    #banner-bar {
        dock: top;
        height: auto;
        width: 100%;
    }

    .banner-query {
        background: #4169e1;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }

    .banner-result-count {
        background: #20b2aa;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }

    .banner-explicit {
        background: #b8860b;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }

    .banner-installed {
        background: #2e8b57;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }

    .banner-nolimit {
        background: #8b008b;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }
    
    .banner-outdated {
        background: #ff0000;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
    }
    
    .banner-basic {
        background: #ff8c00;
        color: white;
        text-style: bold;
        padding: 0 1;
        width: auto;
        display: none;
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
        ("e", "toggle_explicit", "Explicit"),
        ("i", "toggle_installed", "Installed"),
        ("o", "toggle_outdated", "Outdated"),
        ("f", "toggle_full", "Full"),
    ]

    current_theme_name = reactive("default")
    
    def action_quit(self):
        """Override quit to cancel workers first."""
        self._cancel_all_workers()
        self.exit()

    def __init__(self, pkgs, theme_entry, all_themes, search_query="",
                 explicit=False, installed_only=False, outdated_only=False, full_mode=False, basic_mode=False,
                 initial_search=False):
        super().__init__()
        self.pkgs_full = pkgs          # Full unfiltered results (for re-filtering on toggle)
        self.theme_entry = theme_entry
        self.all_themes = all_themes
        self.search_query = search_query
        self.table = None
        self.basic_mode = basic_mode   # True if using basic search mode
        self.cache_percent = 0  # Cache completeness percentage (0-100)
        self.initial_search = initial_search  # If True, search on mount

        # Toggle state (initialised from CLI flags)
        self.explicit = explicit
        self.installed_only = installed_only
        self.outdated_only = outdated_only
        self.full_mode = full_mode
        
        # Worker state and cancellation
        self._search_worker = None  # Current search worker (if any)
        self._is_searching = False  # True when search is running
        self._cancel_search = False  # Flag to signal worker cancellation
        self._search_progress_screen = None  # Progress modal during search
        
        # Apply initial filters based on CLI flags
        filtered = pkgs
        if self.installed_only:
            filtered = [p for p in filtered if p.get("installed")]
        if self.outdated_only:
            filtered = [p for p in filtered if p.get("status") == "Outdated"]
        
        self.pkgs = filtered  # Currently displayed (filtered) results

        # Find which theme name matches the current theme_entry
        matched_theme = "default"
        for name, entry in all_themes.items():
            if entry is theme_entry:
                matched_theme = name
                break

        self.current_theme_name = matched_theme
        self._quit_requested = False
        self._quit_timer = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="banner-bar"):
            yield Static("", id="banner-query", classes="banner-query")
            yield Static("", id="banner-result-count", classes="banner-result-count")
            yield Static("", id="banner-explicit", classes="banner-explicit")
            yield Static("", id="banner-installed", classes="banner-installed")
            yield Static("", id="banner-outdated", classes="banner-outdated")
            yield Static("", id="banner-nolimit", classes="banner-nolimit")
            yield Static("", id="banner-basic", classes="banner-basic")
        self.table = DataTable()
        yield self.table
        yield Footer()

    def on_mount(self):
        self._update_banners()
        self._build_table()
        
        # If launched with initial_search=True, start search in background
        if self.initial_search:
            self.initial_search = False  # Only do this once
            # Show progress screen and start search
            self._search_progress_screen = ProgressScreen("Searching...")
            self.push_screen(self._search_progress_screen)
            self._search_progress_screen.update_content("Searching PyPI...")
            self._perform_search()


    def _update_banners(self):
        """Show/hide banner labels based on current toggle state."""
        query_widget = self.query_one("#banner-query", Static)
        result_count_widget = self.query_one("#banner-result-count", Static)
        explicit_widget = self.query_one("#banner-explicit", Static)
        installed_widget = self.query_one("#banner-installed", Static)
        outdated_widget = self.query_one("#banner-outdated", Static)
        nolimit_widget = self.query_one("#banner-nolimit", Static)
        basic_widget = self.query_one("#banner-basic", Static)

        # Search query banner
        if self.search_query:
            query_widget.update(f" 🔍 {self.search_query} ")
            query_widget.display = True
        else:
            query_widget.display = False
        
        # Result count banner
        if hasattr(self, 'pkgs') and hasattr(self, 'pkgs_full'):
            total = len(self.pkgs_full)
            displayed = len(self.pkgs)
            # Always show "X of Y" format
            result_count_widget.update(f" Showing {displayed} of {total} ")
            result_count_widget.display = True
        else:
            result_count_widget.display = False

        explicit_widget.update(" EXPLICIT " if self.explicit else "")
        explicit_widget.display = self.explicit

        installed_widget.update(" INSTALLED ONLY " if self.installed_only else "")
        installed_widget.display = self.installed_only

        outdated_widget.update(" OUTDATED ONLY " if self.outdated_only else "")
        outdated_widget.display = self.outdated_only

        nolimit_widget.update(" FULL (no limit) " if self.full_mode else "")
        nolimit_widget.display = self.full_mode
        
        # Show mode banner based on search mode and cache completeness
        if self.basic_mode:
            basic_widget.update(" BASIC MODE (cache building) ")
            basic_widget.display = True
        elif self.cache_percent > 0 and self.cache_percent < 90:
            basic_widget.update(f" ENHANCED MODE (cache {self.cache_percent}% complete) ")
            basic_widget.display = True
        else:
            # Enhanced mode with complete cache - no banner
            basic_widget.display = False

    def _apply_filters_async(self):
        """Re-fetch data in background (for explicit mode changes).
        
        Uses daemon thread - can be cancelled, dies with app.
        Updates banners/state happen BEFORE this is called.
        """
        import threading
        from pip_search_ex.core.pypi import gather_packages
        
        def _filter_worker():
            self._is_searching = True
            
            try:
                if self.explicit:
                    # Explicit mode: re-fetch with explicit flag
                    pkgs_full, basic_mode, cache_percent = gather_packages(
                        self.search_query,
                        explicit=True,
                        override_limit=True,
                    )
                else:
                    # Default mode: re-fetch without explicit
                    pkgs_full, basic_mode, cache_percent = gather_packages(
                        self.search_query,
                        explicit=False,
                        override_limit=self.full_mode,
                    )
                
                # Update results (back on main thread)
                def _update():
                    self.pkgs_full = pkgs_full
                    self.basic_mode = basic_mode
                    self.cache_percent = cache_percent
                    self._apply_client_side_filters()
                
                self.call_from_thread(_update)
                
            finally:
                self._is_searching = False
        
        # Start daemon thread
        thread = threading.Thread(target=_filter_worker, daemon=True)
        thread.start()
    
    def _apply_client_side_filters(self):
        """Apply client-side filters and update table.
        
        This is INSTANT - no network calls, just filtering local data.
        """
        from pip_search_ex.core.pypi import MAX_RESULTS
        
        # Filter on client side (instant)
        filtered = self.pkgs_full
        
        if self.installed_only:
            filtered = [p for p in filtered if p.get("installed")]
        
        if self.outdated_only:
            filtered = [p for p in filtered if p.get("status") == "Outdated"]
        
        if not self.full_mode and not self.explicit:
            filtered = filtered[:MAX_RESULTS]
        
        self.pkgs = filtered
        self._update_banners()
        self._build_table()

    def action_toggle_explicit(self):
        """Toggle explicit search mode (instant state change, background re-fetch)."""
        self.explicit = not self.explicit
        self.notify("Explicit: ON" if self.explicit else "Explicit: OFF")
        
        # Update banners INSTANTLY
        self._update_banners()
        
        # Re-fetch in background (explicit changes search logic)
        self._apply_filters_async()

    def action_toggle_installed(self):
        """Toggle installed-only filter (instant - client-side only)."""
        self.installed_only = not self.installed_only
        self.notify("Installed only: ON" if self.installed_only else "Installed only: OFF")
        
        # This is instant - just filter existing data
        self._apply_client_side_filters()

    def action_toggle_outdated(self):
        """Toggle outdated-only filter (instant - client-side only)."""
        self.outdated_only = not self.outdated_only
        self.notify("Outdated only: ON" if self.outdated_only else "Outdated only: OFF")
        
        # This is instant - just filter existing data
        self._apply_client_side_filters()

    def action_toggle_full(self):
        """Toggle the 200-result limit (instant - client-side only)."""
        self.full_mode = not self.full_mode
        self.notify("Full results (no limit)" if self.full_mode else "Limited to 200 results")
        
        # This is instant - just change the slice
        self._apply_client_side_filters()

    def watch_current_theme_name(self, new_theme: str) -> None:
        """React to theme changes and rebuild table."""
        # Only rebuild if table exists (not during initialization)
        if self.table is not None and new_theme in self.all_themes:
            self.theme_entry = self.all_themes[new_theme]
            self._build_table()

    def action_request_quit(self):
        """Handle ESC key - cancel search first, then double press to quit."""
        # If searching, first ESC cancels search
        if self._is_searching:
            self._cancel_search = True
            self._is_searching = False  # Clear flag immediately
            # Only pop screen if progress screen is actually on the stack
            if self._search_progress_screen and len(self.app.screen_stack) > 1:
                try:
                    self.app.pop_screen()
                except Exception:
                    pass  # Screen might have already been dismissed
            self._search_progress_screen = None
            self.notify("Search cancelled")
            self._quit_requested = False  # Reset quit flag
            return
        
        # Not searching - normal quit behavior
        if self._quit_requested:
            # Second ESC within timeout - actually quit
            # Cancel any running workers
            self._cancel_all_workers()
            self.exit()
        else:
            # First ESC - show message and start timer
            self._quit_requested = True
            self.notify("Press ESC again to quit", timeout=1)
            # Reset flag after 1 second
            if self._quit_timer:
                self._quit_timer.cancel()
            self._quit_timer = self.set_timer(1.0, self._reset_quit_request)
    
    def _cancel_all_workers(self):
        """Cancel all running background workers."""
        self._cancel_search = True
        # Textual workers will be cancelled when app exits
        # But we set flags so they can check and exit cleanly

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
                # Show progress screen with spinner while searching
                self._search_progress_screen = ProgressScreen("Searching...")
                self.push_screen(self._search_progress_screen)
                self._search_progress_screen.update_content("Searching PyPI...")
                # Start search in background
                self._perform_search()

        self.push_screen(
            SearchScreen(self.search_query),
            handle_search
        )

    def _perform_search(self):
        """Perform a new search with the current query in background.
        
        Uses daemon thread so it dies immediately when app exits.
        UI stays responsive - user can press ESC to cancel, q to quit.
        """
        import threading
        from pip_search_ex.core.pypi import gather_packages
        
        def _search_worker():
            self._is_searching = True
            self._cancel_search = False
            
            try:
                # Fetch in background thread (non-blocking)
                pkgs_full, basic_mode, cache_percent = gather_packages(
                    self.search_query,
                    explicit=self.explicit,
                    override_limit=self.full_mode,
                )
                
                # Check if cancelled
                if self._cancel_search:
                    if self._search_progress_screen:
                        self.call_from_thread(self.app.pop_screen)
                        self._search_progress_screen = None
                    return
                
                # Update on main thread
                def _update_results():
                    self.pkgs_full = pkgs_full
                    self.basic_mode = basic_mode
                    self.cache_percent = cache_percent
                    self._apply_client_side_filters()
                    
                    # Dismiss progress screen
                    if self._search_progress_screen:
                        try:
                            self.app.pop_screen()
                        except Exception:
                            pass
                        self._search_progress_screen = None
                    
                    # Show result count
                    total = len(self.pkgs_full)
                    displayed = len(self.pkgs)
                    if displayed < total:
                        msg = f"Showing {displayed} of {total} results"
                    else:
                        msg = f"Showing {total} result{'s' if total != 1 else ''}"
                    
                    if self.search_query:
                        self.notify(f"{msg} for '{self.search_query}'")
                    else:
                        self.notify(msg)
                
                self.call_from_thread(_update_results)
            
            except Exception as e:
                # Dismiss progress screen on error
                def _show_error():
                    if self._search_progress_screen:
                        try:
                            self.app.pop_screen()
                        except Exception:
                            pass
                        self._search_progress_screen = None
                    self.notify(f"Search error: {e}", severity="error")
                
                self.call_from_thread(_show_error)
            
            finally:
                self._is_searching = False
        
        # Start daemon thread - dies when app exits
        thread = threading.Thread(target=_search_worker, daemon=True)
        thread.start()

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

    def _run_pip_install(self, package: str, upgrade: bool = False, downgrade: bool = False, reinstall: bool = False):
        """Run pip install in background daemon thread."""
        import threading
        
        def _install_worker():
            action = "Reinstalling" if reinstall else ("Downgrading" if downgrade else ("Updating" if upgrade else "Installing"))
            
            # Push progress screen on main thread
            progress = ProgressScreen(f"{action} {package}")
            self.call_from_thread(lambda: self.push_screen(progress))

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
                self.call_from_thread(lambda: progress.update_content(output))

                if result.returncode == 0:
                    action_past = "reinstalled" if reinstall else ("downgraded" if downgrade else ("updated" if upgrade else "installed"))
                    self.call_from_thread(progress.set_complete)
                    self._refresh_packages()
                    self.call_from_thread(lambda: self.notify(f"Successfully {action_past} {package}", severity="information"))
                else:
                    action_past = "reinstall" if reinstall else ("downgrade" if downgrade else ("update" if upgrade else "install"))
                    self.call_from_thread(progress.set_complete)
                    self.call_from_thread(lambda: self.notify(f"Failed to {action_past} {package}", severity="error"))
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.call_from_thread(lambda: progress.update_content(error_msg))
                self.call_from_thread(progress.set_complete)
                self.call_from_thread(lambda: self.notify(f"Error: {str(e)}", severity="error"))
        
        # Start daemon thread
        thread = threading.Thread(target=_install_worker, daemon=True)
        thread.start()

    def _run_pip_uninstall(self, package: str):
        """Run pip uninstall in background daemon thread."""
        import threading
        
        def _uninstall_worker():
            # Push progress screen on main thread
            progress = ProgressScreen(f"Uninstalling {package}")
            self.call_from_thread(lambda: self.push_screen(progress))

            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package]

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                output = result.stdout + result.stderr
                self.call_from_thread(lambda: progress.update_content(output))

                if result.returncode == 0:
                    self.call_from_thread(progress.set_complete)
                    self._refresh_packages()
                    self.call_from_thread(lambda: self.notify(f"Successfully uninstalled {package}", severity="information"))
                else:
                    self.call_from_thread(progress.set_complete)
                    self.call_from_thread(lambda: self.notify(f"Failed to uninstall {package}", severity="error"))
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                self.call_from_thread(lambda: progress.update_content(error_msg))
                self.call_from_thread(progress.set_complete)
                self.call_from_thread(lambda: self.notify(f"Error: {str(e)}", severity="error"))
        
        # Start daemon thread
        thread = threading.Thread(target=_uninstall_worker, daemon=True)
        thread.start()

    def _refresh_packages(self):
        """Refresh the package list after install/uninstall in background.
        
        Uses daemon thread - dies with app.
        """
        import threading
        from pip_search_ex.core.pypi import gather_packages
        
        def _refresh_worker():
            self._is_searching = True
            
            try:
                # Fetch in background
                pkgs_full, basic_mode = gather_packages(
                    self.search_query,
                    explicit=self.explicit,
                    override_limit=self.full_mode,
                )
                
                # Apply filters and update
                def _update():
                    self.pkgs_full = pkgs_full
                    self.basic_mode = basic_mode
                    self._apply_client_side_filters()
                
                self.call_from_thread(_update)
            
            finally:
                self._is_searching = False
        
        # Start daemon thread
        thread = threading.Thread(target=_refresh_worker, daemon=True)
        thread.start()

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
