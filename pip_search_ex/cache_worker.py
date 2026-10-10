#!/usr/bin/env python3
"""Background cache worker for pip-search-ex.

This module runs as a separate process to build the PyPI metadata cache
incrementally in the background without blocking the main search interface.

Stages:
1. Searched packages - versions & metadata (high priority)
2. All other packages - versions & metadata (bulk work, long tail)

Both stages run through the same chunk loop, in 200-package chunks for
atomicity and rate-limiting.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path

import requests

# Set up logging only if explicitly enabled via --status flag
CACHE_DIR = Path.home() / ".cache" / "pip_search_ex"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE_DIR / "worker.log"

# Only enable logging if PIP_SEARCH_EX_ENABLE_LOGGING env var is set
if os.environ.get('PIP_SEARCH_EX_ENABLE_LOGGING'):
    logging.basicConfig(
        filename=str(LOG_FILE),
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
else:
    # Disable logging completely
    logging.disable(logging.CRITICAL)

# Import core functionality
from pip_search_ex.core.pypi import (
    fetch_single_metadata,
    fetch_index,
    load_metadata_db_with_index,
    _save_incremental_progress,
    _meta_entry_set,
    canonicalize_name,
    load_version_cache,
    save_version_cache,
)

CHUNK_SIZE = 200  # Process 200 packages at a time
REQUEST_DELAY = 0.5  # Slow and lazy: 500ms = max 2 requests/sec, PyPI will ignore us


def flush_cache_chunk(cache_var):
    """Append cache_var to existing cache file atomically.

    Args:
        cache_var: Dict of {canonical_name: metadata} to add to cache
                   metadata has {name, version, summary}
    """
    try:
        db, _ = load_metadata_db_with_index()
        version_cache = load_version_cache()

        for canon, pkg_data in cache_var.items():
            version_cache[canon] = pkg_data.get("version", "unknown")
            _meta_entry_set(db, canon,
                pkg_data.get("name", canon),
                pkg_data.get("version", "unknown"),
                pkg_data.get("summary", ""),
            )

        _save_incremental_progress(db)
        save_version_cache(version_cache)

        logging.debug(f"Successfully flushed {len(cache_var)} packages to cache")

    except Exception as e:
        logging.error(f"Failed to flush cache chunk: {e}")


def fetch_chunk(chunk):
    """Fetch metadata for one chunk of package names, slowly.

    Returns {canonical_name: metadata}. A package that fails to fetch is
    logged and skipped; it never stops the chunk.
    """
    cache_var = {}
    # One session per chunk for HTTP connection reuse
    session = requests.Session()
    for pkg_name in chunk:
        try:
            metadata = fetch_single_metadata(pkg_name, session=session)
            if metadata:
                cache_var[canonicalize_name(pkg_name)] = metadata
            time.sleep(REQUEST_DELAY)
        except Exception as e:
            logging.warning(f"Failed to fetch {pkg_name}: {e}")
    session.close()
    return cache_var


def process_packages(names, label):
    """Fetch and cache `names` in chunks, flushing each chunk to disk.

    The one chunk loop both stages use. `label` only names the stage in the log.
    """
    total_chunks = (len(names) + CHUNK_SIZE - 1) // CHUNK_SIZE
    for i in range(0, len(names), CHUNK_SIZE):
        chunk = names[i:i + CHUNK_SIZE]
        chunk_num = i // CHUNK_SIZE + 1
        logging.debug(f"{label}: Chunk {chunk_num}/{total_chunks} ({len(chunk)} packages)")
        flush_cache_chunk(fetch_chunk(chunk))
        if chunk_num % 10 == 0:
            logging.info(f"{label}: Completed {chunk_num}/{total_chunks} chunks")


def build_cache(searched_packages):
    """Build cache incrementally in stages.

    Args:
        searched_packages: List of package names that were just searched for
    """
    logging.info("=== Cache worker started ===")
    logging.debug(f"Searched packages: {len(searched_packages)}")

    # Stage 1: packages the user just searched for (high priority)
    if searched_packages:
        logging.info(f"Stage 1: Processing {len(searched_packages)} searched packages")
        process_packages(searched_packages, "Stage 1")
        logging.info("Stage 1: Complete")

    # Stage 2: everything else not yet cached (background fill)
    logging.info("Stage 2: Building full cache")
    try:
        all_packages = fetch_index(force_refresh=False)
        logging.debug(f"Total PyPI packages: {len(all_packages)}")

        db, _ = load_metadata_db_with_index()
        already_cached = set(db.keys())
        logging.debug(f"Already cached: {len(already_cached)} packages")

        remaining = [
            p["name"] for p in all_packages
            if canonicalize_name(p["name"]) not in already_cached
        ]
        logging.info(f"Stage 2: {len(remaining)} packages remaining")

        process_packages(remaining, "Stage 2")
        logging.info("=== Cache worker completed successfully ===")

    except Exception as e:
        logging.error(f"Stage 2 failed: {e}")


def main():
    """Main entry point for cache worker."""
    logging.info("Cache worker process started")

    # Read searched packages from environment
    searched_packages = []
    if 'PIP_SEARCH_EX_PACKAGES' in os.environ:
        try:
            searched_packages = json.loads(os.environ['PIP_SEARCH_EX_PACKAGES'])
            logging.debug(f"Loaded {len(searched_packages)} searched packages from environment")
        except Exception as e:
            logging.error(f"Failed to parse PIP_SEARCH_EX_PACKAGES: {e}")

    # Build cache
    try:
        build_cache(searched_packages)
    except Exception as e:
        logging.error(f"Cache worker crashed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
