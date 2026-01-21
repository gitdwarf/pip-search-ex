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

def print_table(rows, theme):
    """Print formatted table with proper color coding and wrapping."""
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

    def hline(left, mid, right):
        return (
            f"{border}{left}"
            f"{'─' * (NAME_WIDTH + 2)}{mid}"
            f"{'─' * (VER_WIDTH + 2)}{mid}"
            f"{'─' * (STATUS_WIDTH + 2)}{mid}"
            f"{'─' * (SUMMARY_WIDTH + 2)}"
            f"{right}{default}"
        )

    # Top border
    print(hline("┌", "┬", "┐"))

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
    for name, version, status_lines, summary in rows:
        # Determine row color based on status
        status_head = status_lines[-1].split(" ", 1)[0]
        if status_head == "Installed":
            row_color = theme["installed"]
        elif status_head == "Outdated":
            row_color = theme["outdated"]
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

        print(hline("├", "┼", "┤"))

    # Bottom border
    print(hline("└", "┴", "┘"))
