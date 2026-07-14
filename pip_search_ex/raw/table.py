from wcwidth import wcwidth, wcswidth

BREAK_CHARS = [" ", "-", "_", "/", "."]

def wrap_cell(text, width):
    """Wrap cell text with intelligent line breaking."""
    if not text:
        return [""]

    lines = []
    current = ""
    current_width = 0
    first = True
    max_width = width

    for ch in text:
        w = wcwidth(ch)
        if w < 0:
            w = 0

        if current_width + w > max_width:
            # Find break position
            break_pos = None
            for i in range(len(current) - 1, -1, -1):
                if current[i] in BREAK_CHARS:
                    break_pos = i
                    break

            if break_pos is not None:
                line = current[:break_pos + 1]
                remainder = current[break_pos + 1:]
            else:
                line = current
                remainder = ""

            # Add line with proper indentation
            if first:
                lines.append(line)
                first = False
                max_width = width - 2  # Indent continuation lines
            else:
                lines.append("  " + line)

            current = remainder + ch
            current_width = wcswidth(current)
        else:
            current += ch
            current_width += w

    # Add remaining text
    if current:
        if first:
            lines.append(current)
        else:
            lines.append("  " + current)

    return lines or [""]

def pad_block(lines, width, height):
    """Pad lines to fill a block of given width and height."""
    out = []
    for ln in lines:
        pad_len = width - wcswidth(ln)
        out.append(ln + " " * pad_len)
    while len(out) < height:
        out.append(" " * width)
    return out

def print_table(rows, theme, basic_mode=False, cache_percent=0, result_count_text=None, filters=None):
    """Print formatted table with proper color coding and wrapping.
    
    Args:
        rows: List of (name, version, status_lines, summary) tuples
        theme: Color theme dict
        basic_mode: If True, shows "BASIC MODE" banner
        cache_percent: 0-100, shows cache building status if enhanced mode with <90% cache
        result_count_text: Optional result count text to show in header
        filters: Dict with 'installed', 'outdated', 'query' keys for filter banners
    """
    import shutil
    cols, _ = shutil.get_terminal_size(fallback=(120, 40))
    cols = max(cols - 2, 60)

    VER_WIDTH = 12
    STATUS_WIDTH = 20
    fixed_overhead = 8 + 5 + 2
    remaining = cols - (VER_WIDTH + STATUS_WIDTH + fixed_overhead)
    if remaining < 20:
        remaining = 20

    NAME_WIDTH = max(10, int(remaining * 0.35))
    SUMMARY_WIDTH = max(10, remaining - NAME_WIDTH)

    border = theme["border"]
    header = theme["header"]
    default = theme["default"]
    warning = "\033[38;5;208m"  # Orange color for warning
    info = "\033[38;5;45m"  # Cyan color for info
    
    def display_width(text):
        """Calculate actual display width accounting for emoji and wide characters."""
        # Use wcswidth which properly handles emoji, combining chars, etc.
        width = wcswidth(text)
        # wcswidth returns -1 for non-printable chars, fall back to len()
        return width if width >= 0 else len(text)

    def hline(left, mid, right):
        """Line with column dividers (for table structure)"""
        return (
            f"{border}{left}"
            f"{'─' * (NAME_WIDTH + 2)}{mid}"
            f"{'─' * (VER_WIDTH + 2)}{mid}"
            f"{'─' * (STATUS_WIDTH + 2)}{mid}"
            f"{'─' * (SUMMARY_WIDTH + 2)}"
            f"{right}{default}"
        )
    
    def hline_solid(left, right):
        """Solid line for banner separators (no column dividers)"""
        # Line width: (NAME+2) + │ + (VER+2) + │ + (STATUS+2) + │ + (SUMMARY+2)
        # = columns (116) + padding (8) + dividers (3)
        line_width = NAME_WIDTH + VER_WIDTH + STATUS_WIDTH + SUMMARY_WIDTH + 8 + 3
        return f"{border}{left}{'─' * line_width}{right}{default}"

    # Add blank line before table for readability
    print()
    
    # Top border - solid line (no column dividers in banner section)
    print(hline_solid("┌", "┐"))
    
    # Target width for banners (should match hline solid width)
    banner_target_width = NAME_WIDTH + VER_WIDTH + STATUS_WIDTH + SUMMARY_WIDTH + 8 + 3
    
    # Helper to print left-aligned banner content
    def print_banner_left(text, color=info, print_separator=True, width_adjust=0):
        # Use wcswidth for accurate display width (handles emoji correctly)
        text_display_width = wcswidth(text)
        if text_display_width < 0:
            text_display_width = len(text)

        padding_needed = banner_target_width - text_display_width + width_adjust
        if padding_needed > 0:
            line = text + " " * padding_needed
        else:
            # Text too long - truncate by display width
            out = ""
            wsum = 0
            for ch in text:
                w = wcwidth(ch)
                if w < 0:
                    w = 0
                if wsum + w > banner_target_width:
                    break
                out += ch
                wsum += w
            line = out + " " * max(0, banner_target_width - wsum)

        print(f"{border}│{color}{line}{default}{border}│{default}")
        if print_separator:
            print(hline_solid("├", "┤"))
    
    # Helper to print centered banner
    def print_banner(text, color=info, print_separator=True):
        text_len = len(text)
        padding_total = banner_target_width - text_len
        
        if padding_total > 0:
            padding_left = padding_total // 2
            padding_right = padding_total - padding_left
            line = " " * padding_left + text + " " * padding_right
        else:
            line = text[:banner_target_width]
        
        # Add color codes ONLY in the print statement, not in the padded line
        print(f"{border}│{color}{line}{default}{border}│{default}")
        if print_separator:
            print(hline_solid("├", "┤"))
    
    # Determine if status banner will be shown (show if --status flag, regardless of cache %)
    will_show_status_banner = filters and filters.get('status', False)

    # Combined search + result count banner
    raw_query = filters.get('query') if filters else None
    if isinstance(raw_query, list):
        sep = " OR " if filters.get('or_search') else ", "
        search_text = sep.join(raw_query)
    elif raw_query:
        search_text = raw_query
    else:
        search_text = "<ALL>"
    combined = f"🔍 Search: {search_text}     {result_count_text if result_count_text else ''}"
    has_more_banners = (filters and (filters.get('installed') or filters.get('outdated') or filters.get('full'))) or will_show_status_banner
    print_banner_left(combined, print_separator=has_more_banners)
    
    # Filter banners on second line (if any active) (📦🔓 display wide, need -1)
    filter_tags = []
    if filters:
        if filters.get('installed'):
            filter_tags.append("📦 INSTALLED")
        if filters.get('outdated'):
            filter_tags.append("🔴 OUTDATED")
        if filters.get('full'):
            filter_tags.append("🔓 FULL (no limit)")
    
    has_filter_banner = bool(filter_tags)
    if filter_tags:
        filter_line = "  ".join(filter_tags)
        # Don't print separator if this is the last banner (no status banner after)
        print_banner_left(filter_line, warning, print_separator=will_show_status_banner)
    
    # Show status banner (if --status flag active)
    if will_show_status_banner:
        if cache_percent >= 100:
            print_banner_left("✅ Extended cache complete", info, print_separator=False)
        else:
            print_banner_left(f"📊 Local extended cache: {cache_percent}% complete", info, print_separator=False)

    # Legend -- always last in the banner section, just above the table
    import os
    _is_root = (os.getuid() == 0) if hasattr(os, 'getuid') else False
    dim = "\033[2m"
    if _is_root:
        legend_text = "  [D] = distro-managed (check your package manager)"
    else:
        legend_text = "  [S] = system/root pip install  |  [D] = distro-managed (check your package manager)"
    print(hline_solid("├", "┤"))
    print_banner_left(legend_text, color=dim, print_separator=False)

    # Transition line from banners to table (with column dividers ┬)
    print(hline("├", "┬", "┤"))

    # Header row
    name_hdr = "NAME".center(NAME_WIDTH)
    version_hdr = "VERSION".center(VER_WIDTH)
    status_hdr = "INSTALLATION STATUS".center(STATUS_WIDTH)
    summary_hdr = "SUMMARY".center(SUMMARY_WIDTH)

    print(
        f"{border}│{default} {header}{name_hdr}{default} "
        f"{border}│{default} {header}{version_hdr}{default} "
        f"{border}│{default} {header}{status_hdr}{default} "
        f"{border}│{default} {header}{summary_hdr}{default} {border}│{default}"
    )

    print(hline("├", "┼", "┤"))

    # Data rows
    for idx, (name, version, status_lines, summary) in enumerate(rows):
        # Determine row color based on status
        # Handle all cases: Installed, Outdated, Newer, Not Installed
        if status_lines and len(status_lines) > 0:
            status_head = status_lines[-1].split(" ", 1)[0]
        else:
            # Empty status_lines means "Not Installed"
            status_head = "Not"  # Matches "Not Installed"
            
        if status_head in ("Installed", "Newer"):
            row_color = theme["installed"]
        elif status_head == "Outdated":
            row_color = theme["outdated"]
        elif status_head == "Error":
            row_color = theme["error"]
        else:
            row_color = theme["not_installed"]

        # Wrap cells
        name_lines = wrap_cell(name, NAME_WIDTH)
        summary_lines = wrap_cell(summary, SUMMARY_WIDTH)

        # Process status lines (may already be multi-line)
        status_cell_lines = []
        for line in status_lines:
            vis = wcswidth(line)
            if vis > STATUS_WIDTH:
                # Truncate if too long
                cut = STATUS_WIDTH
                out = ""
                wsum = 0
                for ch in line:
                    w = wcwidth(ch)
                    if w < 0:
                        w = 0
                    if wsum + w > cut:
                        break
                    out += ch
                    wsum += w
                line = out
                vis = wsum
            pad = STATUS_WIDTH - vis
            status_cell_lines.append(line + " " * pad)

        version_lines = [version[:VER_WIDTH].ljust(VER_WIDTH)]

        # Calculate row height
        row_height = max(
            len(name_lines),
            len(summary_lines),
            len(status_cell_lines),
            len(version_lines),
        )

        # Pad all blocks to same height
        name_block = pad_block(name_lines, NAME_WIDTH, row_height)
        version_block = pad_block(version_lines, VER_WIDTH, row_height)
        status_block = pad_block(status_cell_lines, STATUS_WIDTH, row_height)
        summary_block = pad_block(summary_lines, SUMMARY_WIDTH, row_height)

        # Print each line of the row
        for i in range(row_height):
            print(
                f"{border}│{default} {row_color}{name_block[i]}{default} "
                f"{border}│{default} {row_color}{version_block[i]}{default} "
                f"{border}│{default} {row_color}{status_block[i]}{default} "
                f"{border}│{default} {row_color}{summary_block[i]}{default} {border}│{default}"
            )

        # Print separator after row, but not after the last row
        if idx < len(rows) - 1:
            print(hline("├", "┼", "┤"))

    # Bottom border
    print(hline("└", "┴", "┘"))
