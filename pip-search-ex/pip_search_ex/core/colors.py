RESET = "\033[0m"

def build_raw_theme(colors: dict):
    """Convert hex colors from theme XML to ANSI 256 color codes."""
    def convert(value):
        if not value:
            return ""
        value = value.strip().lower()
        if value.startswith("#") and len(value) == 7:
            r = int(value[1:3], 16)
            g = int(value[3:5], 16)
            b = int(value[5:7], 16)

            # Handle grayscale
            if r == g == b:
                if r < 8:
                    return "\033[38;5;16m"
                if r > 248:
                    return "\033[38;5;231m"
                gray_index = 232 + round((r - 8) / 247 * 23)
                return f"\033[38;5;{gray_index}m"

            # Handle RGB colors using 6x6x6 color cube
            r_index = round(r / 255 * 5)
            g_index = round(g / 255 * 5)
            b_index = round(b / 255 * 5)
            color_index = 16 + (36 * r_index) + (6 * g_index) + b_index
            return f"\033[38;5;{color_index}m"

        return ""

    return {
        "installed": convert(colors.get("installed")),
        "outdated": convert(colors.get("outdated")),
        "not_installed": convert(colors.get("not_installed")),
        "error": convert(colors.get("error")),
        "header": convert(colors.get("header")),
        "border": convert(colors.get("border")),
        "default": RESET,
    }
