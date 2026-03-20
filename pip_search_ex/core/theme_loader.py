import xml.etree.ElementTree as ET
from pathlib import Path
import importlib.resources as pkg_resources  # Python 3.9+

# User theme directory -- scanned in addition to bundled themes
USER_THEME_DIR = Path.home() / ".cache" / "pip_search_ex" / "themes"


def _parse_theme_file(file):
    """Parse a single theme XML file.

    Returns (name, theme_dict) on success, or None if invalid/corrupt.
    Invalid themes are silently ignored -- no exceptions propagate.
    """
    try:
        tree = ET.parse(file)
        root = tree.getroot()

        name = root.attrib.get("name", Path(file).stem)
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
                colors[child.tag] = (child.text or "").strip()

        # Minimum validity: must have at least one colour defined
        if not colors:
            return None

        return name, {"aliases": aliases, "colors": colors}

    except Exception:
        # Corrupt XML, missing file, permission error -- silently ignore
        return None


def load_themes(subfolder: str = "themes"):
    """Load all theme XML files.

    Loads from two sources:
    1. Bundled package themes (pip_search_ex/themes/)
    2. User themes (~/.cache/pip_search_ex/themes/)

    User themes with the same name as a bundled theme override the bundled one.
    Invalid or corrupt theme files are silently ignored.

    Returns:
        dict: {theme_name: {"aliases": [...], "colors": {...}}}
    """
    themes = {}

    # Load bundled themes from package
    try:
        base = pkg_resources.files("pip_search_ex").joinpath(subfolder)
        for file in base.glob("*.xml"):
            result = _parse_theme_file(file)
            if result:
                name, theme = result
                themes[name] = theme
    except Exception:
        pass  # Package themes unavailable -- continue to user themes

    # Load user themes -- override bundled if same name, silently skip invalid
    if USER_THEME_DIR.exists():
        for file in sorted(USER_THEME_DIR.glob("*.xml")):
            result = _parse_theme_file(file)
            if result:
                name, theme = result
                themes[name] = theme

    return themes
