import time
import json
import requests
import importlib.metadata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

INDEX_URL = "https://pypi.org/simple/"
HEADERS = {"Accept": "application/vnd.pypi.simple.v1+json"}
META_URL = "https://pypi.org/pypi/{name}/json"

CACHE_TTL = 24 * 60 * 60
CACHE_DIR = Path.home() / ".cache" / "pip_search_ex"
CACHE_FILE = CACHE_DIR / "simple_index.json"

MAX_RESULTS = 200


# ---------------------------------------------------------------------------
# INDEX FETCHING + SMART CACHE
# ---------------------------------------------------------------------------

def fetch_index(force_refresh: bool = False):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache = {}
    headers = dict(HEADERS)

    if CACHE_FILE.exists() and not force_refresh:
        try:
            with CACHE_FILE.open("r", encoding="utf-8") as f:
                cache = json.load(f)

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

        new_cache = {
            "fetched_at": time.time(),
            "etag": r.headers.get("ETag"),
            "last_modified": r.headers.get("Last-Modified"),
            "data": data,
        }

        try:
            with CACHE_FILE.open("w", encoding="utf-8") as f:
                json.dump(new_cache, f)
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
    out = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            out[name.lower()] = dist.version
    return out


# ---------------------------------------------------------------------------
# VERSION COMPARISON
# ---------------------------------------------------------------------------

try:
    from packaging.version import Version, InvalidVersion
except ImportError:
    Version = None
    InvalidVersion = Exception


def compare_versions(inst, latest):
    if not inst or not latest:
        return 0

    if Version:
        try:
            return (Version(latest) > Version(inst)) - (Version(latest) < Version(inst))
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

    a = norm(inst)
    b = norm(latest)
    if a is None or b is None:
        return 0

    return (b > a) - (b < a)


# ---------------------------------------------------------------------------
# METADATA FETCH
# ---------------------------------------------------------------------------

def fetch_meta(name):
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
        return {"name": name, "error": "timeout"}

    except requests.HTTPError as e:
        return {"name": name, "error": f"http {e.response.status_code}"}

    except Exception:
        return {"name": name, "error": "invalid response"}


# ---------------------------------------------------------------------------
# MAIN QUERY PIPELINE
# ---------------------------------------------------------------------------

def gather_packages(query: str, force_refresh: bool = False):
    projects = fetch_index(force_refresh)
    installed = build_installed_map()

    matches = [
        p["name"] for p in projects
        if query in p["name"].lower()
    ][:MAX_RESULTS]

    results = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(fetch_meta, name): name for name in matches}

        for fut in as_completed(futures):
            meta = fut.result()
            name = meta["name"]
            inst = installed.get(name.lower())

            if meta.get("error"):
                results.append({
                    "name": name,
                    "latest": "—",
                    "installed": inst,
                    "status": "Error",
                    "status_lines": [meta["error"]],
                    "summary": "",
                })
                continue

            latest = meta["version"]
            cmp = compare_versions(inst, latest)

            if inst and cmp < 0:
                status = "Outdated"
                status_lines = [f"({inst})", "Outdated"]
            elif inst:
                status = "Installed"
                status_lines = [f"({inst})", "Installed"]
            else:
                status = "Not Installed"
                status_lines = ["Not Installed"]

            results.append({
                "name": name,
                "latest": latest,
                "installed": inst,
                "status": status,
                "status_lines": status_lines,
                "summary": meta["summary"],
            })

    results.sort(key=lambda r: r["name"].lower())
    return results
