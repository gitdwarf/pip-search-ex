# Changelog

All notable changes to pip-search-ex will be documented in this file.

## [2.0.10] - 2026-10-10

### Bug Fixes

- Fixed the TUI search list never updating a package's status after an install, update, reinstall, downgrade or uninstall. A package would keep showing its old state: still "Installed" after being uninstalled, still "Outdated" after being updated, still "Not Installed" after being installed. The post-install refresh unpacked two values from `gather_packages`, which returns three, so the refresh raised `ValueError` in its background thread and the list never changed. The refresh now unpacks all three (keeping the cache percentage in sync, same as a normal search) and reports a warning instead of failing silently if a refresh ever does fail. Measured on tinydb, all four transitions: Outdated to Installed (update), Installed to Not Installed (uninstall), Not Installed to Installed (install), Installed to Not Installed again; the unfixed build stayed on Outdated through all of them

- TUI and `--raw` now run the exact same search. The TUI never passed `or_search`, `no_live_fetch` or `--flush` to the core, so `pip-search-ex tinydb jsonpickle` gave 29 results with `--raw --raw` but only 2 in the TUI, and `--installed` in the TUI could try live PyPI fetches. All search parameters are now worked out in one place, `plan_search()` in `core/pypi.py`, used by the CLI, `--raw` and the TUI (including words typed into the TUI search box), and the TUI makes its single core call through one method, `_gather()`, instead of three copies. Measured: OR search 29 vs 29, `--packages` 3 vs 3, `--installed` 161 vs 161 (was 2 vs 29 for OR before)
- Toggling Explicit in the TUI no longer silently turns on `--full`; it now follows the same rules as the command line

- The `--installed` / `--outdated` search banner no longer prints the whole generated list of installed package names (1803 characters on a test box). Both `--raw` and the TUI now show `installed packages`, from one shared `query_label()` in `core/pypi.py`. Typed queries still show as typed (`a OR b`, or `a, b` for `--packages`)
- The TUI cursor now stays on the same package after the post-install refresh and after toggling Explicit, Installed, Outdated or Full. It used to jump back to the first row (measured: row 2 became row 0). New searches still start at the top
- Removed `enhanced_search()` from `core/pypi.py`: dead code since 2.0.0, never called

- The TUI list now updates the moment pip finishes, instead of a second or more later (long enough to click the package again and be offered the wrong action). The old refresh re-ran the whole search: measured 1.7s for one package and 32s for `django`. It now re-works only the installed state of the rows on screen, from one new core function `installed_state()` (also catches dependencies pip installed, updated or removed along with the package), in about 0.12s whatever the list size, and does it before the progress screen is marked complete. The result is identical to a full search (checked for Outdated, Installed and Not Installed)

### Code cleanup (no behaviour change)

- The installed / outdated / newer status and `[D]` / `[S]` origin tag logic was copy-pasted five times in `unified_search()` (and twice more in unreachable code). It now exists once, in `installed_state()`, and every result row is built by one `_result_row()`. Measured before and after on four query types (single name, exact list, OR search, `--installed`; 201 rows): zero differences in any field
- Removed about 190 lines of unreachable code left after the `return` in `unified_search()` (the body of `basic_search()`, whose `def` was removed in 2.0.0 but whose body was not), the four never-called `start_background_cache_build` / `stop_background_cache_build` definitions, the unused `display_width()` and `print_banner()` helpers in `raw/table.py`, `c256()` in `ansi.py`, and unused imports and variables. `core/pypi.py` went from 1637 to 1249 lines
- `cache_worker.py`: the two stages (searched packages, then everything else) each carried their own copy of the same fetch-and-flush loop. They now share one `process_packages()` built on one `fetch_chunk()`, and `requests` / `time` are imported once instead of inside both loops. Measured with a no-network harness (1,075 events: fetches, sessions, flushes, failures, order): identical before and after. The request rate is unchanged, still 2 per second, and is now a named constant `REQUEST_DELAY`
- Removed `ansi.py` (referenced by nothing, never packaged) and `testthemes` (the old bash theme check that `validate_themes.py` replaced in 2.0.6) from the source tree
- TUI error handlers now copy the error text before using it in a callback, instead of relying on the exception variable still existing when the callback runs

### Documentation

- README rewritten to the DwarvenSuite template (Philosophy, What it does, Features, Installation, Usage, Part of DwarvenSuite, Author, Tip Jar, License). Release notes now live only in this file

## [2.0.9] - 2026-05-02

### Bug Fixes

- `--installed --raw` and `--outdated --raw` now correctly show results on fresh installs with empty metadata cache. Cache misses with `no_live_fetch=True` were being silently dropped instead of returned as name-only results
- Fixed `OUTDATED` banner line width being off by 1 character depending on terminal emulator -- `⚠️` uses a variation selector that different terminals render inconsistently (1 or 2 columns wide), so no width calculation can be reliably correct for it. Replaced with `🔴`, which is unambiguously double-width in every terminal per the Unicode East Asian Width property. `print_banner_left` no longer needs any per-character width correction
- TUI install/uninstall now automatically adds `--break-system-packages` on PEP 668 externally-managed environments (Ubuntu/Debian etc) -- detected once at startup via `_is_externally_managed()`, applied to all pip calls

## [2.0.8] - 2026-05-02

### New Features

- Multi-word query is now an inclusive OR search: `pip-search-ex pip search ex` returns all packages matching `pip` OR `search` OR `ex` in name or description. Banner shows `pip OR search OR ex`
- When `--explicit` is used with multi-word queries, terms become exclusive exact matches instead of inclusive OR
- `--packages` / `-p` flag: explicit exact multi-package lookup -- `pip-search-ex -p gtk4 jellyfin kodi` looks up all three by exact name, banner shows `gtk4, jellyfin, kodi`
- `--installed`, `--outdated`, and `--newer` are special-case exact lookups -- always explicit, always cache-only, never hit PyPI

### Bug Fixes

- `--installed` / `--outdated` regression fixed -- were rate-limited live-fetching every installed package at 0.15s/req, causing 2+ minute waits. Now correctly use `no_live_fetch=True`
- Search banner displays OR queries as `pip OR search OR ex` and exact lists as `gtk4, jellyfin, kodi`

## [2.0.7] - 2026-04-26

### Cache Behaviour

- Metadata cache now uses LRU-style TTL per entry -- works like a browser cache:
  - Cache hit: serve from disk, reset the 360-day access clock
  - Cache miss: fetch live from PyPI, store with timestamps
  - Stale (not accessed in 360 days): evict, treat as miss, fetch fresh
  - Actively used packages never go stale regardless of age
- Each metadata entry now stores `fetched` (when last pulled from PyPI) and `accessed` (last time a search touched it) timestamps
- All cache read/write sites consolidated into `_meta_entry_get` / `_meta_entry_set` -- single place to change cache behaviour

### Bug Fixes

- Live PyPI fetches now correctly restored for cache misses -- v2.0.6 was too aggressive in killing fetches, causing empty results on fresh installs or sparse caches
- Cache misses are now fetched for all displayed results (up to `MAX_RESULTS` / `--full`), rate-limited at ~6-7 req/sec to be polite to PyPI
- `all_matches` trimmed to display limit before any fetch work begins -- no fetching beyond what the user will actually see

## [2.0.6] - 2026-04-26

### External Theming

- User themes now supported in two locations -- either works:
  - `~/.cache/pip_search_ex/themes/` (legacy, cache-adjacent)
  - `~/.config/pip-search-ex/themes/` (XDG-style, preferred)
- Priority order: bundled themes < cache dir themes < config dir themes. Same-name user theme always wins
- Invalid themes now skipped gracefully at runtime -- PSE falls back to `default` with a warning instead of crashing
- Theme validation is now strict: all 7 required colour keys must be present (`installed`, `outdated`, `not_installed`, `error`, `header`, `border`, `default`)
- `<e>` accepted as alias for `<error>` in theme XML for backwards compatibility
- `validate_themes.py` replaces the old `testthemes` bash script -- scans all three theme dirs, reports missing keys and XML errors per file, exits non-zero if anything is broken

### Bug Fixes
- `light-terminal` theme was missing the `error` colour key -- caught by the new validator, now fixed
- `colors.py` was silently ignoring `<e>` tags in theme XML -- now aliased to `error` correctly

## [2.0.5] - 2026-04-26

### Installation Origin Markers
- Installed packages now display `[S]` (system/root pip install) or `[D]` (distro-managed) in the status column
- Plain `Installed` / `Outdated` / `Newer` shown for normal user pip installs -- no noise when it's just yours
- Context-aware legend line in both TUI (top bar) and raw mode (above table):
  - Running as root: only `[D]` shown in legend (root never sees `[S]`)
  - Running as user: both `[S]` and `[D]` explained
- Distro-agnostic wording: "check your package manager" -- no assumptions about apt/dnf/etc

### Bug Fixes
- Fixed colours being lost for system-installed packages in TUI and raw mode -- `status` field was having origin tag concatenated onto it (e.g. `"Installed [distro]"`), breaking all equality checks. `status` is now always a bare word; `origin` is a separate field on the result dict
- Fixed `[S]` and `[D]` being silently eaten by Textual's markup parser -- escaped as `\[S]` and `\[D]`
- Fixed raw table search line being 1 character too wide -- switched from `len()` to `wcswidth()` for accurate emoji column width
- Fixed raw table bottom border showing column dividers (`┴`) under the legend line -- legend now has its own solid `└──┘` border

### Performance
- `--installed` mode no longer loads the full 500K package index -- skipped entirely when query is a list of specific packages
- Eliminated all live PyPI fetches during foreground search -- cache misses return name-only results instantly; background worker fills metadata over time at 2 req/sec
- `metadata_db.json` no longer embeds a full copy of the package index. Was causing the file to balloon to 41MB regardless of how many packages were actually cached; now grows proportionally to cached metadata only
- `flush_cache_chunk` no longer calls `fetch_index()` on every cache write -- removed a redundant 700ms index parse per chunk flush
- `check_self_update` now TTL-cached for 24 hours -- was hitting PyPI on every single run

## [2.0.4] - 2026-03-20
- **ETag cache warm-restart**: 304 Not Modified responses now correctly reset the cache TTL, so the index stays fresh indefinitely with minimal network usage
- **Root user warning suppressed**: pip install/uninstall no longer shows the root user warning when running as root
- **Package origin indicators**: Installed packages now show `[distro]` if managed by the system package manager (always shown), and `[root]` if installed by pip as root when running as a non-root user. Detection uses INSTALLER file, WHEEL file presence, and path fallback -- handles Slackware and other non-standard layouts correctly
- **CSV output mode**: Double `--raw --raw` flag outputs CSV format (name,version,status,summary) for scripting and piping
- **User theme directory**: Drop custom themes in `~/.cache/pip_search_ex/themes/` -- loaded automatically alongside bundled themes. Invalid or corrupt XML is silently ignored. User themes override bundled themes of the same name

## [2.0.3] - 2026-02-22
- **Update to offline cache**: Renamed from enhanced to extended, and split version into its own sub cache

## [2.0.2] - 2026-02-15
- **Fixed cache display and logger**: Fixing cache status and logging to behaving correctly as per the use (or not) of --status

## [2.0.1] - 2026-02-15
- **Auto restart after self update**: Now will auto restart with the same search if an auto update was requested

## [2.0.0] - 2026-02-15

### Major Changes - Unified Search Architecture

This release represents a major architectural simplification and improvement to the search system.

#### New Features

- **Unified Search**: Replaced complex basic/enhanced mode split with a single, intelligent search flow
  - Name-based search across ALL PyPI packages (always works, even with empty cache)
  - Opportunistic metadata search for richer results (searches summaries in cached packages)
  - Automatic on-demand metadata fetching for search results
  - Background cache building continues seamlessly

- **`--status` Flag**: Display local cache completion percentage
  - Shows cache status as a banner in `--raw` mode
  - Example: `pip-search-ex --raw --status django`

- **Light Terminal Theme**: New theme optimized for white/light backgrounds
  - Aliases: `--light-terminal`, `--lterm`, `--inverse`
  - Perfect for xterm default and other light terminal themes
  - High contrast colors for excellent readability

#### Improvements

- **Banner System Overhaul** (v1.5.7 - v1.7.3):
  - Fixed TUI banner CSS visibility
  - Consistent result count format (always "X of Y")
  - Consolidated banner layout (reduced vertical space)
  - Perfect alignment across all banner types
  - Proper emoji width calculation for all emoji types
  - Clean table borders with proper column dividers

- **Search Performance**:
  - Eliminated "cache ready" checks that caused missed results
  - All packages now searchable immediately, regardless of cache state
  - Metadata enrichment happens progressively as cache builds

#### Technical Changes

- **Removed**:
  - `basic_search()` / `enhanced_search()` split
  - `is_cache_complete()` returning "ready" status
  - Complex mode switching logic
  
- **Added**:
  - `unified_search()` - single search function for all scenarios
  - Intelligent search prioritization (names first, metadata second)
  - Progressive enhancement as cache builds

#### Bug Fixes

- Fixed critical bug where searches would return 0 results if package wasn't in cache yet (v1.8.4)
- Fixed empty banner bar appearing when no filter flags active (v1.8.3)
- Fixed banner width calculations for emoji characters (v1.6.1 - v1.7.3)
- Fixed status flag not being passed through to display layer (v1.8.1)

#### Dependencies

No changes to dependencies. Still uses:
- `requests` for PyPI API
- `textual` for TUI mode
- `wcwidth` for terminal width calculations

---

## [1.0.10] - 2026-02-05

### Features
- TUI mode with real-time search
- Raw table output mode
- Theme support (20+ built-in themes)
- Background cache building
- Filter by installed/outdated packages
- Exact and fuzzy search modes
- Self-update notifications

### Known Issues (Fixed in 2.0.0)
- Search would miss packages not yet in cache
- Complex basic/enhanced mode split caused confusion
- Banner alignment issues with certain emoji
