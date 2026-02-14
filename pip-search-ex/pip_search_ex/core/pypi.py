import time
import json
import requests
import importlib.metadata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from packaging.utils import canonicalize_name
import subprocess
import sys
import os

try:
    from packaging.version import Version, InvalidVersion
except ImportError:
    Version = None
    InvalidVersion = Exception


# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------

INDEX_URL = "https://pypi.org/simple/"
HEADERS = {"Accept": "application/vnd.pypi.simple.v1+json"}
META_URL = "https://pypi.org/pypi/{name}/json"

CACHE_DIR = Path.home() / ".cache" / "pip_search_ex"
INDEX_CACHE_FILE = CACHE_DIR / "simple_index.json"
METADATA_DB_FILE = CACHE_DIR / "metadata_db.json"
METADATA_DB_LOCK = CACHE_DIR / "metadata_db.lock"

CACHE_TTL = 365 * 24 * 60 * 60  # 1 year
MAX_RESULTS = 200


# ---------------------------------------------------------------------------
# SELF-UPDATE CHECK
# ---------------------------------------------------------------------------

def check_self_update():
    """Check if pip-search-ex itself is outdated.
    
    Shows notification but doesn't prompt if:
    - Installed as root but running as user
    - No response after 5 seconds
    """
    try:
        installed_version = importlib.metadata.version("pip-search-ex")
    except importlib.metadata.PackageNotFoundError:
        return False
    
    try:
        r = requests.get(META_URL.format(name="pip-search-ex"), timeout=5)
        r.raise_for_status()
        latest_version = r.json().get("info", {}).get("version")
        
        if not latest_version or latest_version == installed_version:
            return False
        
        if Version:
            try:
                if Version(latest_version) <= Version(installed_version):
                    return False
            except InvalidVersion:
                return False
        
        # Check if installed as root but running as user
        install_path = None
        try:
            dist = importlib.metadata.distribution("pip-search-ex")
            install_path = Path(dist._path).parent
        except Exception:
            pass
        
        needs_root = False
        if install_path and not os.access(install_path, os.W_OK):
            needs_root = True
        
        if needs_root:
            print(f"\n⚠️  pip-search-ex {latest_version} is available (you have {installed_version})")
            print("Run with sudo/root to update: sudo pip install --upgrade pip-search-ex\n")
            return False
        
        # Prompt with 5-second timeout
        print(f"\n⚠️  pip-search-ex {latest_version} is available (you have {installed_version})")
        print("Update now? [Y/n] (auto-decline in 5s): ", end="", flush=True)
        
        import select
        if sys.stdin.isatty():
            ready, _, _ = select.select([sys.stdin], [], [], 5.0)
            if ready:
                response = sys.stdin.readline().strip().lower()
            else:
                print("\n(timed out)")
                return False
        else:
            # Non-interactive, skip
            print("(non-interactive)")
            return False
        
        if response in ('', 'y', 'yes'):
            print("Updating pip-search-ex...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "pip-search-ex"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✓ Updated! Restarting with your search...\n")
                # Re-execute with same arguments
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                print(f"✗ Update failed: {result.stderr}\n")
        
        print()
        return False
        
    except Exception:
        return False


def package_needs_root(package_name):
    """Check if a package requires root/sudo privileges to modify.
    
    Returns:
        (bool, str): (needs_root, install_location)
        - needs_root: True if package is installed system-wide and user can't modify
        - install_location: "system" or "user" or "unknown"
    """
    try:
        dist = importlib.metadata.distribution(package_name)
        install_path = Path(dist._path).parent
        
        # Check if we have write access to the install location
        if not os.access(install_path, os.W_OK):
            # Determine if system or user install
            install_str = str(install_path).lower()
            if any(x in install_str for x in ['/usr/', '/lib/python', 'site-packages']):
                if '/local/' not in install_str and '/.local/' not in install_str:
                    return True, "system"
            return True, "system"  # Can't write but installed somewhere
        else:
            # We have write access - user install or we're root
            if '/.local/' in str(install_path).lower():
                return False, "user"
            else:
                return False, "system"  # Running as root
    except Exception:
        return False, "unknown"


# ---------------------------------------------------------------------------
# INDEX FETCHING
# ---------------------------------------------------------------------------

def fetch_index(force_refresh=False):
    """Fetch PyPI simple index (list of package names only)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}
    headers = dict(HEADERS)

    if INDEX_CACHE_FILE.exists() and not force_refresh:
        try:
            with INDEX_CACHE_FILE.open("r", encoding="utf-8") as f:
                cache = json.load(f)

            fetched_at = cache.get("fetched_at", 0)
            if (time.time() - fetched_at) < CACHE_TTL and cache.get("data"):
                return cache["data"].get("projects", [])

            if cache.get("etag"):
                headers["If-None-Match"] = cache["etag"]
            if cache.get("last_modified"):
                headers["If-Modified-Since"] = cache["last_modified"]
        except Exception:
            cache = {}

    try:
        r = requests.get(INDEX_URL, headers=headers, timeout=20)
        if r.status_code == 304 and cache:
            return cache["data"].get("projects", [])

        r.raise_for_status()
        data = r.json()

        try:
            with INDEX_CACHE_FILE.open("w", encoding="utf-8") as f:
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
# BACKGROUND CACHE WORKER MANAGEMENT
# ---------------------------------------------------------------------------

def stop_cache_worker():
    """Kill any existing cache worker processes for this user."""
    import subprocess
    
    try:
        # Find all cache worker processes for this user
        result = subprocess.run(
            ['pgrep', '-u', os.getenv('USER', 'unknown'), '-f', 'pip_search_ex.cache_worker'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid and pid.strip():
                    try:
                        subprocess.run(['kill', '-9', pid.strip()], stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
    except Exception:
        pass


def start_cache_worker(searched_packages=None):
    """Start background cache worker process.
    
    Args:
        searched_packages: List of package names that were just searched for (optional)
    """
    import subprocess
    import json
    
    if searched_packages is None:
        searched_packages = []
    
    # Limit to 200 packages to avoid environment variable size limits
    if len(searched_packages) > 200:
        searched_packages = searched_packages[:200]
    
    try:
        # Kill any existing workers first
        stop_cache_worker()
        
        # Prepare environment with searched packages
        env = os.environ.copy()
        if searched_packages:
            env['PIP_SEARCH_EX_PACKAGES'] = json.dumps(searched_packages)
        
        # Spawn worker as fully detached process
        subprocess.Popen(
            [sys.executable, '-m', 'pip_search_ex.cache_worker'],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Fully detach from parent
        )
    except Exception:
        # Worker failed to start - not critical, just means no background caching
        pass


# Keep old function names for compatibility but redirect to new ones
def stop_background_cache_build():
    """Deprecated: Use stop_cache_worker() instead."""
    stop_cache_worker()


def start_background_cache_build(force_refresh=False):
    """Deprecated: Use start_cache_worker() instead."""
    start_cache_worker()

def load_metadata_db_with_index():
    """Load metadata DB along with the package index snapshot.
    
    Auto-recovers from corrupted cache by deleting and starting fresh.
    """
    if not METADATA_DB_FILE.exists():
        return {}, []
    
    try:
        with METADATA_DB_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            packages = data.get("packages", {})
            index_snapshot = data.get("index_snapshot", [])
            
            # Validate data structure
            if not isinstance(packages, dict):
                raise ValueError("Corrupted cache: packages not a dict")
            if not isinstance(index_snapshot, list):
                raise ValueError("Corrupted cache: index_snapshot not a list")
            
            return packages, index_snapshot
    except Exception as e:
        # Cache is corrupted - delete it and start fresh
        print(f"Warning: Corrupted cache detected, rebuilding...")
        try:
            METADATA_DB_FILE.unlink()
        except Exception:
            pass
        return {}, []


def stop_background_cache_build():
    """Stop any running background cache build process.
    
    Called before starting a new search to ensure clean state.
    """
    if not METADATA_DB_LOCK.exists():
        return  # No background process running
    
    try:
        # Read PID from lock file
        pid_str = METADATA_DB_LOCK.read_text().strip()
        if not pid_str:
            METADATA_DB_LOCK.unlink()
            return
        
        pid = int(pid_str)
        
        # Try to kill the process
        try:
            import signal
            os.kill(pid, signal.SIGTERM)  # Graceful termination
            time.sleep(0.1)  # Give it a moment
            # Check if still alive
            try:
                os.kill(pid, 0)  # Check if process exists
                # Still alive, force kill
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass  # Already dead
        except (ProcessLookupError, OSError):
            pass  # Process doesn't exist
        
        # Remove lock file
        METADATA_DB_LOCK.unlink()
        
    except Exception:
        # If anything fails, just remove the lock file
        try:
            METADATA_DB_LOCK.unlink()
        except Exception:
            pass


def start_background_cache_build(force_refresh=False):
    """Start background process to build/update full metadata cache incrementally.
    
    Only fetches metadata for NEW packages since last sync.
    Runs as FULLY DETACHED process (like bash &).
    """
    # Background sync now ENABLED
    if METADATA_DB_LOCK.exists() and not force_refresh:
        # Check if lock is stale (older than 1 hour - assume crashed)
        try:
            lock_time = METADATA_DB_LOCK.stat().st_mtime
            if time.time() - lock_time < 3600:  # Less than 1 hour old
                return  # Already building
        except Exception:
            pass
    
    # Create lock file
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        METADATA_DB_LOCK.write_text(str(os.getpid()))
    except Exception:
        pass
    
    # Fork a completely detached background process
    # This is the Python equivalent of "command &" in bash
    try:
        pid = os.fork()
        if pid > 0:
            # Parent process - return immediately
            return
    except (AttributeError, OSError):
        # fork() not available (Windows) - fall back to thread
        import threading
        thread = threading.Thread(
            target=_background_sync_worker,
            args=(force_refresh,),
            daemon=True
        )
        thread.start()
        return
    
    # Child process - detach completely
    try:
        # Create new session (detach from terminal)
        os.setsid()
        
        # Redirect stdout/stderr to log file for debugging
        log_file = CACHE_DIR / "sync.log"
        log_fd = open(log_file, 'a')
        sys.stdin.close()
        sys.stdout = log_fd
        sys.stderr = log_fd
        
        print(f"\n=== Background sync started at {time.ctime()} ===")
        
        # Run the sync
        _background_sync_worker(force_refresh)
        
        print(f"=== Background sync completed at {time.ctime()} ===\n")
        log_fd.close()
        
        # Exit child process
        os._exit(0)
        
    except Exception as e:
        # Log the error
        try:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        except Exception:
            pass
        
        # Clean up on error
        try:
            METADATA_DB_LOCK.unlink()
        except Exception:
            pass
        os._exit(1)


def _background_sync_worker(force_refresh=False):
    """Worker function that runs the incremental metadata sync in background.
    
    Fetches metadata for packages NOT in cache (regardless of when added to PyPI).
    """
    try:
        # Load existing DB and index snapshot
        db, old_index_snapshot = load_metadata_db_with_index()
        
        # Get current index
        projects = fetch_index(force_refresh)
        
        # Find packages missing from cache
        # (Don't just check for new additions to PyPI - fill in ALL gaps!)
        packages_to_fetch = []
        for p in projects:
            canon = canonicalize_name(p["name"])
            if canon not in db:
                packages_to_fetch.append(p["name"])
        
        total_missing = len(packages_to_fetch)
        
        if total_missing == 0 and not force_refresh:
            # Cache is complete!
            try:
                METADATA_DB_LOCK.unlink()
            except Exception:
                pass
            return
        
        # Fetch metadata for missing packages
        completed = 0
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(fetch_single_metadata, name): name
                for name in packages_to_fetch
            }
            
            for future in as_completed(futures):
                pkg = future.result()
                if pkg:
                    canonical = canonicalize_name(pkg["name"])
                    db[canonical] = pkg
                
                completed += 1
                
                # Save progress periodically (every 1000 packages)
                if completed % 1000 == 0:
                    _save_incremental_progress(db, projects)
        
        # Save final DB
        _save_incremental_progress(db, projects)
        
        # Remove lock
        try:
            METADATA_DB_LOCK.unlink()
        except Exception:
            pass
            
    except Exception:
        # Clean up lock on error
        try:
            METADATA_DB_LOCK.unlink()
        except Exception:
            pass


def _save_incremental_progress(packages_dict, index_snapshot):
    """Save metadata DB with index snapshot for next incremental sync.
    
    Uses atomic write (temp file + rename) to prevent corruption if killed mid-write.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first
        import tempfile
        temp_fd, temp_path = tempfile.mkstemp(dir=CACHE_DIR, prefix='.metadata_tmp_', suffix='.json')
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": time.time(),
                    "packages": packages_dict,
                    "index_snapshot": index_snapshot,
                }, f)
                # Explicitly flush to disk
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic rename (POSIX guarantees atomicity)
            import shutil
            shutil.move(temp_path, str(METADATA_DB_FILE))
            
        except Exception:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise
            
    except Exception:
        pass  # Don't fail if we can't save


# Alias for convenience
_save_metadata_db = _save_incremental_progress


def is_cache_complete():
    """Check if metadata cache exists and is usable.
    
    Returns: (usable, completeness_percent)
        - usable: True if cache exists and can be used
        - completeness_percent: 0-100, percentage of PyPI cached
    """
    if not METADATA_DB_FILE.exists():
        return False, 0
    
    try:
        with METADATA_DB_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
            # Check if we have any packages cached
            packages = data.get("packages", {})
            cache_size = len(packages)
            
            if cache_size == 0:
                return False, 0
            
            # Calculate completeness percentage
            try:
                index_snapshot = data.get("index_snapshot", [])
                pypi_size = len(index_snapshot) if index_snapshot else 0
                
                if pypi_size == 0:
                    # Fetch current index size
                    projects = fetch_index(force_refresh=False)
                    pypi_size = len(projects)
                
                if pypi_size > 0:
                    completeness = int((cache_size / pypi_size) * 100)
                else:
                    # Estimate based on typical PyPI size (~738K)
                    completeness = int((cache_size / 738000) * 100)
            except Exception:
                # Estimate based on typical PyPI size
                completeness = int((cache_size / 738000) * 100)
            
            # Clamp to 0-100
            completeness = max(0, min(100, completeness))
            
            # Check age - cache is valid if less than 1 year old
            timestamp = data.get("timestamp", 0)
            age = time.time() - timestamp
            
            if age >= CACHE_TTL:
                return False, 0
            
            # Never use cache as "ready" - always do name-based search first
            # Metadata search is opportunistic based on what's cached
            return False, completeness
    except Exception:
        return False, 0


# ---------------------------------------------------------------------------
# INSTALLED PACKAGES
# ---------------------------------------------------------------------------

def build_installed_map():
    """Build map of installed packages."""
    installed = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name")
        if name:
            installed[canonicalize_name(name)] = dist.version
    return installed


# ---------------------------------------------------------------------------
# VERSION COMPARISON
# ---------------------------------------------------------------------------

def compare_versions(installed_version, latest_version):
    """Compare versions. Returns: -1 (newer), 0 (equal/unknown), 1 (outdated)."""
    if not installed_version or not latest_version:
        return 0

    if Version:
        try:
            return (
                Version(latest_version) > Version(installed_version)
            ) - (
                Version(latest_version) < Version(installed_version)
            )
        except InvalidVersion:
            return 0

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
# SEARCH MATCHING
# ---------------------------------------------------------------------------

def _normalize_name(name):
    """Normalize package name for comparison."""
    return name.lower().replace("-", "_").replace(".", "_")


def _is_explicit_match(query, pkg_name):
    """Exact name match."""
    return _normalize_name(query) == _normalize_name(pkg_name)


def _is_fuzzy_match(query, pkg_name):
    """Substring match against name."""
    return _normalize_name(query) in _normalize_name(pkg_name)


# ---------------------------------------------------------------------------
# BASIC SEARCH (Fast, Name-Only)
# ---------------------------------------------------------------------------

def unified_search(query, projects, installed_map, explicit=False, override_limit=False):
    """Unified search: name-first with opportunistic metadata search.
    
    1. Name matching against ALL packages (simple_index.json)
    2. Opportunistic summary matching against cached metadata
    3. Fetch metadata on-demand for name matches
    4. Cache worker continues building in background
    
    Args:
        query: Either a string (search term) OR a list (specific package names to fetch)
    """
    # Handle query as list (specific packages) or string (search term)
    if isinstance(query, list):
        # Query is a list of package names - search for these specific packages
        name_matches = query
    else:
        # Query is a string - do normal fuzzy/explicit matching
        q = query.strip().lower()
        name_matches = []
        
        # STEP 1: Match against package NAMES in full index
        for p in projects:
            name = p["name"]
            
            if q:  # If query provided, apply filtering
                if explicit:
                    if not _is_explicit_match(q, name):
                        continue
                else:
                    if not _is_fuzzy_match(q, name):
                        continue
            # Empty query: include everything
            
            name_matches.append(name)
    
    # Load existing cache (if any) for opportunistic metadata search
    try:
        db, _ = load_metadata_db_with_index()
    except Exception:
        db = {}
    
    # STEP 2: Opportunistic metadata search (only if we have query and cache)
    metadata_matches = set()
    if not isinstance(query, list) and query.strip() and db:
        q = query.strip().lower()
        for canonical, pkg in db.items():
            name = pkg["name"]
            summary = pkg.get("summary", "")
            
            # Skip if already matched by name
            if name in name_matches:
                continue
            
            # Check if query is in summary
            if not explicit and q in summary.lower():
                metadata_matches.add(name)
    
    # Combine matches: name matches first, then metadata matches
    all_matches = list(name_matches) + list(metadata_matches)
    
    # Build results from cache + fetch missing
    results = []
    to_fetch = []
    
    for name in all_matches:
        canon = canonicalize_name(name)
        cached = db.get(canon)
        
        if cached:
            # Use cached data
            installed_version = installed_map.get(canon)
            latest = cached["version"]
            
            # Build status
            if installed_version:
                cmp = compare_versions(installed_version, latest)
                if cmp > 0:
                    status = "Outdated"
                    status_lines = [f"({installed_version})", "Outdated"]
                elif cmp < 0:
                    status = "Newer"
                    status_lines = [f"({installed_version})", "Newer"]
                else:
                    status = "Installed"
                    status_lines = [f"({installed_version})", "Installed"]
            else:
                status = "Not Installed"
                status_lines = []
            
            results.append({
                "name": name,
                "latest": latest,
                "installed": installed_version,
                "status": status,
                "status_lines": status_lines,
                "summary": cached.get("summary", ""),
            })
        else:
            # Need to fetch
            to_fetch.append(name)
    
    # Fetch missing packages if any
    if to_fetch:
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(fetch_single_metadata, name): name for name in to_fetch}
            
            for future in as_completed(futures):
                pkg = future.result()
                if not pkg:
                    continue
                
                name = pkg["name"]
                canon = canonicalize_name(name)
                latest = pkg.get("version", "unknown")
                summary = pkg.get("summary", "")
                
                # Cache it
                db[canon] = {
                    "name": name,
                    "version": latest,
                    "summary": summary,
                }
                
                # Build result
                installed_version = installed_map.get(canon)
                
                if installed_version:
                    cmp = compare_versions(installed_version, latest)
                    if cmp > 0:
                        status = "Outdated"
                        status_lines = [f"({installed_version})", "Outdated"]
                    elif cmp < 0:
                        status = "Newer"
                        status_lines = [f"({installed_version})", "Newer"]
                    else:
                        status = "Installed"
                        status_lines = [f"({installed_version})", "Installed"]
                else:
                    status = "Not Installed"
                    status_lines = []
                
                results.append({
                    "name": name,
                    "latest": latest,
                    "installed": installed_version,
                    "status": status,
                    "status_lines": status_lines,
                    "summary": summary,
                })
        
        # Save updated cache
        try:
            _save_metadata_db(db, projects)
        except Exception:
            pass
    
    results.sort(key=lambda r: r["name"].lower())
    return results
    """Quick name-only search with incremental caching.
    
    This is the fallback when full cache isn't ready yet.
    IMPORTANT: Only matches package NAMES, not summaries (we don't have those yet).
    
    For empty query: Returns name-only list instantly, fetches metadata in background.
    For normal query: Fetches and caches ALL matching packages.
    Returns all results - frontends apply display limits.
    """
    q = query.strip().lower()
    matches = []
    
    # Match against names only - collect ALL matches
    for p in projects:
        name = p["name"]
        
        if q:  # If query provided, apply filtering
            if explicit:
                if not _is_explicit_match(q, name):
                    continue
            else:
                if not _is_fuzzy_match(q, name):
                    continue
        # Empty query: include everything (but we'll handle it specially below)
        
        matches.append(name)
        # NO LIMIT HERE - fetch everything, frontends filter for display
    
    # Load existing cache (if any)
    try:
        db, _ = load_metadata_db_with_index()
    except Exception:
        db = {}
    
    # EMPTY QUERY OPTIMIZATION: Don't fetch metadata for all 500K packages
    # Return name-only results immediately, let background sync handle metadata
    if not q:
        # Build name-only results from index + installed status
        results = []
        for name in matches:
            canon = canonicalize_name(name)
            
            # Get installed version (just a string)
            installed_version = installed_map.get(canon)
            
            # Check if we have metadata cached
            cached = db.get(canon)
            
            # Determine latest version - prefer cache, fallback to installed version
            if cached:
                latest = cached["version"]
            elif installed_version:
                latest = installed_version  # Use installed as "latest" if no cache
            else:
                latest = "unknown"
            
            # Build status info
            if installed_version:
                cmp = compare_versions(installed_version, latest)
                if cmp > 0:
                    status = "Outdated"
                    status_lines = [f"({installed_version})", "Outdated"]
                elif cmp < 0:
                    status = "Newer"
                    status_lines = [f"({installed_version})", "Newer"]
                else:
                    status = "Installed"
                    status_lines = [f"({installed_version})", "Installed"]
            else:
                status = "Not Installed"
                status_lines = []
            
            results.append({
                "name": name,
                "latest": latest,
                "installed": installed_version,
                "status": status,
                "status_lines": status_lines,
                "summary": cached.get("summary", "") if cached else "",
            })
        
        # Trigger background cache build for metadata (non-blocking)
        start_background_cache_build(force_refresh=False)
        
        return results
    
    # NORMAL QUERY: Fetch metadata for matching packages (blocks until done)
    # Determine which packages need fetching
    to_fetch = []
    for name in matches:
        canon = canonicalize_name(name)
        if canon not in db:
            to_fetch.append(name)
    
    # Fetch missing packages (all of them, not just 200)
    if to_fetch:
        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(fetch_single_metadata, name): name for name in to_fetch}
            
            for future in as_completed(futures):
                pkg = future.result()
                if not pkg:
                    continue
                
                name = pkg["name"]
                canon = canonicalize_name(name)
                
                # Add to cache
                db[canon] = {
                    "name": name,
                    "version": pkg.get("version", "unknown"),
                    "summary": pkg.get("summary", ""),
                }
        
        # Save updated cache (incremental)
        try:
            _save_metadata_db(db, [])  # Empty index snapshot for now
        except Exception:
            pass  # Don't fail if we can't save
    
    # Build results from cache - return ALL results
    results = []
    for name in matches:
        canon = canonicalize_name(name)
        pkg_data = db.get(canon)
        
        if not pkg_data:
            continue  # Skip if fetch failed
        
        name = pkg_data["name"]
        latest = pkg_data.get("version", "unknown")
        summary = pkg_data.get("summary", "")
        installed = installed_map.get(canon)
        
        if installed:
            cmp = compare_versions(installed, latest)
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
            "summary": summary,
        })
    
    results.sort(key=lambda r: r["name"].lower())
    
    # ALWAYS restart background cache after search completes
    # This ensures cache continues building even after foreground search is done
    start_background_cache_build(force_refresh=False)
    
    return results  # Return ALL - frontends apply limit if needed


def fetch_single_metadata(name):
    """Fetch metadata for one package."""
    try:
        r = requests.get(META_URL.format(name=name), timeout=5)
        r.raise_for_status()
        info = r.json().get("info", {})
        return {
            "name": name,
            "version": info.get("version", "unknown"),
            "summary": (info.get("summary") or "").strip(),
        }
    except Exception:
        return {"name": name, "version": "unknown", "summary": ""}


# ---------------------------------------------------------------------------
# ENHANCED SEARCH (Full Cache)
# ---------------------------------------------------------------------------

def enhanced_search(query, db, installed_map, explicit=False, override_limit=False):
    """Full search with summaries (requires complete cache).
    
    Returns ALL matching packages - frontends apply display limits.
    """
    q = query.strip().lower()
    matches = []
    
    for canonical, pkg in db.items():
        name = pkg["name"]
        summary = pkg.get("summary", "")
        
        if explicit:
            if not _is_explicit_match(q, name):
                continue
        else:
            if not (_is_fuzzy_match(q, name) or (q in summary.lower())):
                continue
        
        matches.append(canonical)
    
    # NO LIMIT - return all matches, frontends filter for display
    
    results = []
    for canonical in matches:
        pkg = db[canonical]
        name = pkg["name"]
        latest = pkg.get("version", "unknown")
        summary = pkg.get("summary", "")
        installed = installed_map.get(canonical)
        
        if installed:
            cmp = compare_versions(installed, latest)
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
            "summary": summary,
        })
    
    results.sort(key=lambda r: r["name"].lower())
    return results


# ---------------------------------------------------------------------------
# MAIN SEARCH FUNCTION
# ---------------------------------------------------------------------------

def gather_packages(
    query,
    force_refresh=False,
    explicit=False,
    override_limit=False,
    progress_callback=None,
):
    """Search PyPI packages.
    
    Uses unified search: name-first with opportunistic metadata matching.
    
    Returns: (results, is_basic_mode, cache_percent)
        - results: List of package dicts
        - is_basic_mode: Always False now (unified search)
        - cache_percent: 0-100, percentage of PyPI cached
    """
    def progress(msg):
        if progress_callback:
            progress_callback(msg)
    
    progress("Loading package index")
    projects = fetch_index(force_refresh)
    
    progress("Checking installed packages")
    installed_map = build_installed_map()
    
    # Check cache completeness (for display purposes only)
    _, cache_percent = is_cache_complete()
    
    # Always use unified search (name + opportunistic metadata)
    progress("Searching")
    results = unified_search(query, projects, installed_map, explicit, override_limit)
    
    # Start cache worker to build/update cache in background
    searched_names = [r["name"] for r in results]
    start_cache_worker(searched_names)
    
    return results, False, cache_percent  # Always unified mode



