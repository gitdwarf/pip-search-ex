#!/usr/bin/env python3
"""Validate all PSE theme XML files across all theme directories.

Checks bundled themes, ~/.cache/pip_search_ex/themes/, and
~/.config/pip-search-ex/themes/ -- reporting any missing required
colour keys or XML errors.

Usage:
    python3 validate_themes.py
"""
import sys
from pathlib import Path

# Allow running from the repo root without installing
sys.path.insert(0, str(Path(__file__).parent))

from pip_search_ex.core.theme_loader import validate_theme_file, REQUIRED_COLOR_KEYS, USER_THEME_DIRS
import importlib.resources as pkg_resources


def check_dir(label, files):
    if not files:
        print(f"\n{label}: (none found)")
        return 0, 0

    print(f"\n{label}:")
    ok = 0
    bad = 0
    for f in sorted(files):
        name, error = validate_theme_file(f)
        if error is None:
            print(f"  OK  {name}  ({Path(str(f)).name})")
            ok += 1
        else:
            print(f"  !!  {name}  ({Path(str(f)).name})")
            print(f"        {error}")
            bad += 1
    return ok, bad


def main():
    print(f"Required colour keys: {', '.join(sorted(REQUIRED_COLOR_KEYS))}")

    total_ok = 0
    total_bad = 0

    # 1. Bundled themes
    try:
        base = pkg_resources.files("pip_search_ex").joinpath("themes")
        files = list(base.glob("*.xml"))
    except Exception:
        # Fallback for running from repo root
        files = list((Path(__file__).parent / "pip_search_ex" / "themes").glob("*.xml"))
    ok, bad = check_dir("Bundled themes", files)
    total_ok += ok; total_bad += bad

    # 2 & 3. User theme directories
    for user_dir in USER_THEME_DIRS:
        files = list(user_dir.glob("*.xml")) if user_dir.exists() else []
        ok, bad = check_dir(f"User themes  ({user_dir})", files)
        total_ok += ok; total_bad += bad

    # Summary
    print(f"\n{'='*60}")
    print(f"  {total_ok} valid   {total_bad} invalid   {total_ok + total_bad} total")
    if total_bad:
        print("  Fix invalid themes before using them -- PSE will skip them at runtime.")
        sys.exit(1)
    else:
        print("  All themes valid.")


if __name__ == "__main__":
    main()
