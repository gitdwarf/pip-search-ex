# Changelog

All notable changes to pip-search-ex will be documented in this file.

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
