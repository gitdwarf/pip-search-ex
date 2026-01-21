#!/usr/bin/env python3
import argparse

from core.theme_loader import load_themes
from core.pypi import gather_packages
from raw.renderer import run_raw_mode
from tui.app import PipSearchApp

THEMES = load_themes("themes")

def add_theme_flags(parser):
    for name, data in THEMES.items():
        for alias in data["aliases"]:
            parser.add_argument(alias, action="store_const", const=name, dest="theme")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("query", nargs="?", default="")
    p.add_argument("--raw", action="store_true")
    add_theme_flags(p)
    p.set_defaults(theme="default")
    return p.parse_args()

def main():
    a = parse_args()
    theme_entry = THEMES[a.theme]
    query = a.query.lower()
    if a.raw:
        run_raw_mode(query, theme_entry, gather_packages)
    else:
        pkgs = gather_packages(query)
        app = PipSearchApp(pkgs, theme_entry, THEMES, query)
        app.run()

if __name__ == "__main__":
    main()
