import xml.etree.ElementTree as ET
from pathlib import Path
import importlib.resources as pkg_resources  # Python 3.9+

# Required colour keys -- themes missing any of these are invalid
REQUIRED_COLOR_KEYS = {
    "installed", "outdated", "not_installed", "error",
    "header", "border", "default",
}

# User theme directories -- both supported, config dir takes priority over cache dir
USER_THEME_DIRS = [
    Path.home() / ".cache" / "pip_search_ex" / "themes",   # legacy / cache-adjacent
    Path.home() / ".config" / "pip-search-ex" / "themes",  # XDG-style config
]


def _parse_theme_file(file):
    """Parse and validate a single theme XML file.

    Returns (name, theme_dict) if valid.
    Returns (name, error_string) if parseable but invalid.
    Returns None if completely unreadable.
    """
    try:
        tree = ET.parse(file)
        root = tree.getroot()

        name = root.attrib.get("name", Path(str(file)).stem)
        if not name:
            return None

        aliases_el = root.find("aliases")
        aliases = []
        if aliases_el is not None:
            for a in aliases_el.findall("alias"):
                text = (a.text or "").strip()
                if text:
                    aliases.append(text)

        colors_el = root.find("colors")
        colors = {}
        if colors_el is not None:
            for child in colors_el:
                val = (child.text or "").strip()
                if val:
                    colors[child.tag] = val

        # Accept 'e' as an alias for 'error' in theme files
        effective_keys = set(colors.keys())
        if 'e' in effective_keys:
            effective_keys.add('error')
        missing = REQUIRED_COLOR_KEYS - effective_keys
        if missing:
            return name, f"missing required colour keys: {', '.join(sorted(missing))}"

        return name, {"aliases": aliases, "colors": colors}

    except ET.ParseError as e:
        return Path(str(file)).stem, f"XML parse error: {e}"
    except Exception as e:
        return Path(str(file)).stem, f"unexpected error: {e}"


def validate_theme_file(file):
    """Validate a single theme file. Returns (name, None) if valid, (name, error) if not."""
    result = _parse_theme_file(file)
    if result is None:
        return Path(str(file)).stem, "unreadable or empty file"
    name, payload = result
    if isinstance(payload, str):
        return name, payload
    return name, None


def load_themes(subfolder: str = "themes"):
    """Load all theme XML files.

    Priority (lowest to highest):
    1. Bundled package themes (pip_search_ex/themes/)
    2. User cache themes (~/.cache/pip_search_ex/themes/)
    3. User config themes (~/.config/pip-search-ex/themes/)

    Higher-priority themes override lower-priority ones of the same name.
    Invalid themes are silently skipped -- they never crash PSE.

    Returns:
        dict: {theme_name: {"aliases": [...], "colors": {...}}}
    """
    themes = {}

    # 1. Bundled themes
    try:
        base = pkg_resources.files("pip_search_ex").joinpath(subfolder)
        for file in base.glob("*.xml"):
            result = _parse_theme_file(file)
            if result is not None:
                name, payload = result
                if isinstance(payload, dict):
                    themes[name] = payload
    except Exception:
        pass

    # 2 & 3. User theme directories (cache first, then config -- config wins)
    for user_dir in USER_THEME_DIRS:
        if user_dir.exists():
            for file in sorted(user_dir.glob("*.xml")):
                result = _parse_theme_file(file)
                if result is not None:
                    name, payload = result
                    if isinstance(payload, dict):
                        themes[name] = payload

    return themes
