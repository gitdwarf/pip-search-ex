import xml.etree.ElementTree as ET
from pathlib import Path
import importlib.resources as pkg_resources  # Python 3.9+

def load_themes(subfolder: str = "themes"):
    """
    Load all theme XML files inside the pip_search_ex package.

    Returns:
        dict: {theme_name: {"aliases": [...], "colors": {...}}}
    """
    themes = {}

    # Get the folder inside the installed package
    try:
        base = pkg_resources.files("pip_search_ex").joinpath(subfolder)
    except Exception as e:
        raise RuntimeError(f"Cannot locate themes folder '{subfolder}' in package: {e}")

    # Iterate over all XML files
    for file in base.glob("*.xml"):
        tree = ET.parse(file)
        root = tree.getroot()

        # Theme name
        name = root.attrib.get("name", file.stem)

        # Aliases
        aliases_el = root.find("aliases")
        aliases = []
        if aliases_el is not None:
            for a in aliases_el.findall("alias"):
                text = (a.text or "").strip()
                if text:
                    aliases.append(text)

        # Colors
        colors_el = root.find("colors")
        colors = {}
        if colors_el is not None:
            for child in colors_el:
                colors[child.tag] = (child.text or "").strip()

        themes[name] = {
            "aliases": aliases,
            "colors": colors,
        }

    return themes
