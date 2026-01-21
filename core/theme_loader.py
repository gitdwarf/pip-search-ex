import xml.etree.ElementTree as ET
from pathlib import Path

def load_themes(theme_dir: str = "themes"):
    themes = {}
    base = Path(theme_dir)

    for file in base.glob("*.xml"):
        tree = ET.parse(file)
        root = tree.getroot()

        name = root.attrib["name"]

        # aliases
        aliases_el = root.find("aliases")
        aliases = []
        if aliases_el is not None:
            for a in aliases_el.findall("alias"):
                text = (a.text or "").strip()
                if text:
                    aliases.append(text)

        # colors
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
