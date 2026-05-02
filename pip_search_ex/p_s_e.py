#!/usr/bin/env python3
import argparse
from importlib.metadata import version as pkg_version, PackageNotFoundError

from pip_search_ex.core.theme_loader import load_themes
from pip_search_ex.core.pypi import gather_packages
from pip_search_ex.raw.renderer import run_raw_mode
from pip_search_ex.tui.app import PipSearchApp

THEMES = load_themes("themes")

def get_version():
    try:
        return pkg_version("pip-search-ex")
    except PackageNotFoundError:
        return "dev"

def add_theme_flags(parser):
    for name, data in THEMES.items():
        for alias in data["aliases"]:
            parser.add_argument(alias, action="store_const", const=name, dest="theme")

def parse_args():
    p = argparse.ArgumentParser(
        prog="pip-search-ex",
        description="Search PyPI packages with TUI or raw output."
    )
    p.add_argument("--version", action="version", version=f"pip-search-ex {get_version()}")
    p.add_argument("query", nargs="*", default=[])
    p.add_argument("--packages", "-p", nargs="+", metavar="PKG",
                   help="Look up specific packages by exact name (multi-item)")
    p.add_argument("--raw", action="count", default=0, help="Raw table output. Use twice for CSV.")

    # Cache control
    p.add_argument("--flush", "--force-refresh", action="store_true", dest="flush",
                   help="Force a fresh download of the PyPI index (ignore cache)")

    # Search mode
    p.add_argument("--explicit", action="store_true",
                   help="Exact name match only (case-insensitive, - _ . equivalent). No description search.")

    # Filters
    p.add_argument("--installed", action="store_true",
                   help="Show only installed packages (includes outdated, current, and newer)")
    p.add_argument("--outdated", action="store_true",
                   help="Show only outdated packages (installed but newer version available)")
    
    # Status display
    p.add_argument("--status", action="store_true",
                   help="Show cache status banner (local enhanced cache percentage)")

    # Limit
    p.add_argument("--full", action="store_true", dest="full",
                   help="Return all matches (no 200-result cap)")
    p.add_argument("--override-limit", action="store_true", dest="full",
                   help=argparse.SUPPRESS)  # Hidden backward compatibility alias

    add_theme_flags(p)
    p.set_defaults(theme="default")
    return p.parse_args()

def main():
    a = parse_args()
    theme_name = a.theme
    if theme_name not in THEMES:
        import sys
        print(f"Warning: theme '{theme_name}' not found or invalid -- falling back to 'default'", file=sys.stderr)
        theme_name = "default"
    theme_entry = THEMES[theme_name]

    # --packages = explicit multi-item exact lookup
    # multi-word query = OR substring search (each word searched independently, results unioned)
    # single word = normal substring search
    or_search = False
    if a.packages:
        query = [p.lower() for p in a.packages]
    elif len(a.query) > 1:
        query = [q.lower() for q in a.query]
        or_search = True
    elif len(a.query) == 1:
        query = a.query[0].lower()
    else:
        query = ""

    # Set cache logging preference (core state, set once at startup)
    from pip_search_ex.core.pypi import set_cache_logging, check_self_update, gather_packages
    set_cache_logging(a.status)

    # Self-update check (before anything else)
    check_self_update()

    # SMART OPTIMIZATION: If no query but filter flags present,
    # search only installed packages (much faster than all 738K!)
    no_live_fetch = False
    if not query and (a.installed or a.outdated):
        from pip_search_ex.core.pypi import build_installed_map, canonicalize_name
        installed_map = build_installed_map()
        query = list(installed_map.keys())  # List of canonical names
        no_live_fetch = True  # Don't fetch live for installed -- use cache only

    # Shared kwargs for gather_packages (core search params only)
    gather_kwargs = dict(
        force_refresh=a.flush,
        explicit=a.explicit,
        override_limit=a.full,
        no_live_fetch=no_live_fetch,
        or_search=or_search,
    )
    
    # Filter state (separate from search params)
    filters = dict(
        installed=a.installed,
        outdated=a.outdated,
        full=a.full,
        status=a.status,
        or_search=or_search,
    )

    if a.raw:
        # Raw mode: pass function + params, it handles everything
        from pip_search_ex.raw.renderer import run_raw_mode
        run_raw_mode(query, theme_entry, gather_packages, gather_kwargs, filters, raw_level=a.raw)
    else:
        # TUI mode: Launch immediately with empty data, search in background
        # This prevents blocking before TUI even starts
        app = PipSearchApp(
            [],  # Start with empty results
            theme_entry, THEMES, query,
            explicit=a.explicit,
            installed_only=a.installed,
            outdated_only=a.outdated,
            full_mode=a.full,
            basic_mode=True,  # Will be updated when search completes
            initial_search=True,  # Signal that we need to search on mount
            show_cache_status=a.status,  # Pass --status flag
        )
        app.run()
        
        # Force exit to kill any lingering threads
        # os._exit(0) bypasses cleanup and kills ThreadPoolExecutor workers immediately
        import os
        os._exit(0)

if __name__ == "__main__":
    main()
