from core.colors import build_raw_theme
from raw.table import print_table

def run_raw_mode(query, theme_entry, gather_packages):
    theme = build_raw_theme(theme_entry["colors"])
    pkgs = gather_packages(query)
    rows = [(p["name"], p["latest"], p["status_lines"], p["summary"]) for p in pkgs]
    print_table(rows, theme)
