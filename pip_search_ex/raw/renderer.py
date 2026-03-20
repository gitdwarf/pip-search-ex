from pip_search_ex.core.colors import build_raw_theme
from pip_search_ex.core.spinner import Spinner
from pip_search_ex.raw.table import print_table


def run_raw_mode(query, theme_entry, gather_packages, gather_kwargs, filters, raw_level=1):
    """Raw table mode - fetches data and renders table.
    
    Args:
        query: Search query string
        theme_entry: Theme configuration dict
        gather_packages: Function to call for fetching packages
        gather_kwargs: Kwargs to pass to gather_packages (search params)
        filters: Dict of display filters {installed: bool, outdated: bool}
        raw_level: 1=ANSI table, 2+=plain CSV
    """
    import signal
    import sys
    import os
    
    # Set up Ctrl+C handler
    def signal_handler(sig, frame):
        print("\n\nInterrupted by user")
        os._exit(0)  # Force exit without waiting for threads
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Show spinner while fetching
    spinner = Spinner("Searching")
    spinner.start()
    
    def progress(msg):
        # Core sends generic messages, we can ignore or update spinner
        pass
    
    try:
        # Fetch packages from core (now returns cache percent too)
        pkgs_all, is_basic, cache_percent = gather_packages(query, progress_callback=progress, **gather_kwargs)
        
        # Update spinner based on mode (for user feedback)
        mode_text = "basic mode" if is_basic else "enhanced mode"
        spinner.update(f"Searching ({mode_text})")
        
        # Apply display filters
        pkgs_filtered = pkgs_all
        if filters.get('installed'):
            pkgs_filtered = [p for p in pkgs_filtered if p.get("installed")]
        if filters.get('outdated'):
            pkgs_filtered = [p for p in pkgs_filtered if p.get("status") == "Outdated"]
        
        # Apply limit if not --full
        from pip_search_ex.core.pypi import MAX_RESULTS
        pkgs_display = pkgs_filtered
        if not filters.get('full') and len(pkgs_filtered) > MAX_RESULTS:
            pkgs_display = pkgs_filtered[:MAX_RESULTS]
    finally:
        spinner.stop()
    
    # Build result count text
    total = len(pkgs_all)
    filtered = len(pkgs_filtered)
    displayed = len(pkgs_display)
    
    if filters.get('installed') or filters.get('outdated'):
        # Filters applied - show filtered count
        if displayed < filtered:
            result_count_text = f"Showing {displayed} of {filtered} (from {total})"
        else:
            result_count_text = f"Showing {filtered} of {total}"
    else:
        # No filters
        result_count_text = f"Showing {displayed} of {total}"
    
    if raw_level >= 2:
        # CSV mode -- plain text, no ANSI, no borders, machine-readable
        import csv
        writer = csv.writer(sys.stdout)
        writer.writerow(["name", "version", "status", "summary"])
        for p in pkgs_display:
            status = " ".join(p.get("status_lines", [])) if isinstance(p.get("status_lines"), list) else str(p.get("status_lines", ""))
            writer.writerow([
                p.get("name", ""),
                p.get("latest", ""),
                status.strip(),
                p.get("summary", ""),
            ])
        return

    # Render table with result count in header
    theme = build_raw_theme(theme_entry["colors"])
    rows = [(p["name"], p["latest"], p["status_lines"], p["summary"]) for p in pkgs_display]
    
    # Build filters dict for banners
    filter_banners = {
        'query': query if query else None,
        'installed': filters.get('installed', False),
        'outdated': filters.get('outdated', False),
        'full': filters.get('full', False),
        'status': filters.get('status', False),
    }
    
    print_table(rows, theme, basic_mode=is_basic, cache_percent=cache_percent, 
                result_count_text=result_count_text, filters=filter_banners)
