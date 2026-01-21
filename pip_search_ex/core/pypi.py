import time
import json
import requests
import importlib.metadata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from packaging.version import Version, InvalidVersion
except ImportError:
    Version = None
    InvalidVersion = Exception

# ---------------------------------------------------------------------------
# CONSTANTS / CONFIG
# ---------------------------------------------------------------------------

INDEX_URL = "https://pypi.org/simple/"
HEADERS = {"Accept": "application/vnd.pypi.simple.v1+json"}
META_URL = "https://pypi.org/pypi/{name}/json"

CACHE_TTL = 24 * 60 * 60
CACHE_DIR = Path.home() / ".cache" / "pip_search_ex"
CACHE_FILE = CACHE_DIR / "simple_index.json"

MAX_RESULTS = 200  # default, can override in gather_packages()


# ---------------------------------------------------------------------------
# INDEX FETCHING + SMART CACHE
# ---------------------------------------------------------------------------

def fetch_index(force_refresh: bool = False):
    """Fetch PyPI simple index with caching and HTTP conditional requests."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}
    headers = dict(HEADERS)

    if CACHE_FILE.exists() and not force_refresh:
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as f:
                cache = json.load(f)
            # Conditional HTTP headers
            if cache.get("etag"):
                headers["If-None-Match"] = cache["etag"]
            if cache.get("last_modified"):
                headers["If-Modified-Since"] = cache["last_modified"]

            age = time.time() - cache.get("fetched_at", 0)
            if age < CACHE_TTL:
                return cache["data"].get("projects", [])
        except Exception:
            cache = {}

    try:
        r = requests.get(INDEX_URL, headers=headers, timeout=20)
        if r.status_code == 304 and cache:
            return cache["data"].get("projects", [])
        r.raise_for_status()
        data = r.json()

        # Update cache
        try:
            with CACHE_FILE.open("w", encoding="utf-8") as f:
                json.dump({
                    "fetched_at": time.time(),
                    "etag": r.headers.get("ETag"),
                    "last_modified": r.headers.get("Last-Modified"),
                    "data": data,
                }, f)
        except Exception:
            pass

        return data.get("projects", [])
    except requests.RequestException:
        if cache:
            return cache.get("data", {}).get("projects", [])
        raise


# ---------------------------------------------------------------------------
# INSTALLED PACKAGES
# ---------------------------------------------------------------------------

def build_installed_map():
    """Return a dict of installed package names -> version."""
    out = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            out[name.lower()] = dist.version
    return out


# ---------------------------------------------------------------------------
# METADATA FETCH
# ---------------------------------------------------------------------------

def fetch_meta(name: str):
    """Fetch package metadata from PyPI."""
    try:
        r = requests.get(META_URL.format(name=name), timeout=5)
        r.raise_for_status()
        info = r.json().get("info", {})

        return {
            "name": name,
            "version": info.get("version", "unknown"),
            "summary": (info.get("summary") or "").strip(),
            "error": None,
        }
    except requests.Timeout:
        return {"name": name, "version": None, "summary": "", "error": "timeout"}
    except requests.HTTPError as e:
        return {"name": name, "version": None, "summary": "", "error": f"http {e.response.status_code}"}
    except Exception:
        return {"name": name, "version": None, "summary": "", "error": "invalid response"}


# ---------------------------------------------------------------------------
# VERSION COMPARISON
# ---------------------------------------------------------------------------

def compare_versions(installed_version: str, latest_version: str) -> int:
    """Compare installed vs latest. Returns: -1 outdated, 0 equal/unknown, 1 newer."""
    if not installed_version or not latest_version:
        return 0
    if Version:
        try:
            return (Version(latest_version) > Version(installed_version)) - \
                   (Version(latest_version) < Version(installed_version))
        except InvalidVersion:
            return 0

    # fallback: integer-dot comparison
    def norm(v):
        parts = []
        for p in v.split("."):
            if p.isdigit():
                parts.append(int(p))
            else:
                return None
        return parts

    a = norm(installed_version)
    b = norm(latest_version)
    if a is None or b is None:
        return 0
    return (b > a) - (b < a)


# ---------------------------------------------------------------------------
# MAIN QUERY PIPELINE
# ---------------------------------------------------------------------------

def gather_packages(query: str, force_refresh: bool = False, max_results: int = MAX_RESULTS):
    """
    Return a list of packages matching the query with installed/latest info.
    Each entry contains: name, latest, installed, status, status_lines, summary
    """
    projects = fetch_index(force_refresh)
    installed_map = build_installed_map()

    # filter matches
    matches = [p["name"] for p in projects if query in p["name"].lower()][:max_results]
    results = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(fetch_meta, name): name for name in matches}
        for fut in as_completed(futures):
            meta = fut.result()
            name = meta["name"]
            installed = installed_map.get(name.lower())

            # --- Error ---
            if meta.get("error"):
                results.append({
                    "name": name,
                    "latest": "—",
                    "installed": installed,
                    "status": "Error",
                    "status_lines": [meta["error"]],
                    "summary": meta.get("summary", ""),
                })
                continue

            latest = meta.get("version", "unknown")
            cmp = compare_versions(installed, latest)

            # --- Status determination ---
            if installed:
                if cmp > 0:
                    status = "Outdated"
                    status_lines = [f"({installed})", "Outdated"]
                elif cmp < 0:
                    status = "Newer"
                    status_lines = [f"({installed})", "Newer"]
                else:
                    status = "Installed"
                    status_lines = [f"({installed})", "Installed"]
            else:
                status = "Not Installed"
                status_lines = ["Not Installed"]

            results.append({
                "name": name,
                "latest": latest,
                "installed": installed,
                "status": status,
                "status_lines": status_lines,
                "summary": meta.get("summary", ""),
            })

    # sort alphabetically
    results.sort(key=lambda r: r["name"].lower())
    return results
