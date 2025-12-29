# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **tabelog** - a Python library and MCP (Model Context Protocol) server for searching restaurants on Tabelog using web scraping. It provides both a Python library (`tabelog`) and an MCP server (`tabelog`) for integration with AI assistants.

**See also**: [IDEAS.md](IDEAS.md) - Feature ideas, improvements, and development notes

## Development Commands

### Testing
```bash
# Run all tests with coverage
make test
# or
uv run pytest -v -s --cov=src tests

# Run specific test file
uv run pytest tests/test_models.py -v
uv run pytest tests/test_restaurant.py -v
uv run pytest tests/test_search.py -v
```

### Code Quality
```bash
# Run linter
make lint
# or
uv run ruff check .

# Run type checker (重要！每次修改程式碼後都要執行)
make type
# or
uv run ty check .

# 完整檢查流程
uv run ruff check .  # 程式碼風格檢查
uv run ty check .    # 型別檢查
uv run pytest -v     # 執行測試
```

### Publishing
```bash
make publish  # Builds wheel and publishes to PyPI
```

### Running Examples
```bash
# Basic search example
PYTHONPATH=/home/narumi/workspace/tabelog/src python examples/basic_search.py

# Or with uv (推薦)
uv run python examples/basic_search.py
```

**重要**: 執行 Python 腳本時，**務必**使用 `uv run python` 而不是直接 `python`，以確保使用正確的虛擬環境和依賴套件。

### Running MCP Server
```bash
# Via entry point (requires installation)
uv run tabelog-mcp

# Local development
uv run --directory /path/to/tabelog tabelog-mcp

# Direct execution
uv run python -m tabelog.server
```

## Architecture

### Core Modules (src/tabelog/)

The codebase has the following main files:

1. **restaurant.py** - Core scraping and search implementation
   - `Restaurant` dataclass: Represents restaurant data (name, rating, reviews, prices, etc.)
   - `RestaurantSearchRequest` dataclass: Builds search URLs and scrapes Tabelog
   - `SortType` enum: Search sorting options (STANDARD, RANKING, REVIEW_COUNT, NEW_OPEN)
   - `PriceRange` enum: Extensive lunch/dinner price ranges (B001-B012, C001-C012)
   - `query_restaurants()` function: Cached convenience function for quick searches
   - Key methods: `_build_params()`, `_parse_restaurants()`, `search_sync()`, `search()`
   - **Area filtering**: Uses area slug paths (e.g., `/tokyo/rstLst/`) for accurate prefecture-level filtering
   - **Cuisine filtering**: Supports `genre_code` parameter for precise cuisine type filtering (e.g., `RC0107` for すき焼き)
   - **Caching and retry**: Integrated with cache.py and retry.py via `use_cache` and `use_retry` parameters (both default to True)

2. **cache.py** - Caching system for HTTP responses (🆕)
   - `CacheEntry` dataclass: Stores data with timestamp and TTL
   - `MemoryCache` class: In-memory cache with LRU eviction
     - Default: 1000 entries max, 1 hour TTL
     - Methods: `get()`, `set()`, `clear()`, `size()`
     - Automatic oldest entry eviction when full
   - `FileCache` class: File-based persistent cache
     - Stores as JSON with SHA256 hashed filenames
     - Useful for development and debugging
   - Global cache functions:
     - `get_cache()`: Returns global cache instance
     - `set_cache()`: Sets cache backend (memory or file)
     - `generate_cache_key()`: Creates consistent keys from URL + params
     - `cached_get()`: Get from cache with force refresh option
     - `cache_set()`: Store to cache with custom TTL
     - `clear_cache()`: Clear all entries
   - **Integration**: Automatically used in `RestaurantSearchRequest.search_sync()` and `.search()` with 30-min TTL

3. **retry.py** - Retry and resilience mechanisms (🆕)
   - `is_retryable_error()`: Checks if exception should trigger retry
   - `handle_http_errors()`: Converts HTTP errors to custom exceptions
   - `fetch_with_retry()`: Sync fetch with automatic retry
     - Max 3 attempts with exponential backoff (1s, 2s, 4s)
     - Retries on: ConnectError, TimeoutException, NetworkError, 5xx errors
     - Raises: RateLimitError (429), NetworkError (other errors)
   - `fetch_with_retry_async()`: Async version with manual retry loop
   - Configuration: `DEFAULT_MAX_ATTEMPTS=3`, `DEFAULT_MIN_WAIT=1`, `DEFAULT_MAX_WAIT=10`
   - Uses `tenacity` library for retry decorators with exponential backoff and jitter
   - **Integration**: Automatically used in `RestaurantSearchRequest.search_sync()` and `.search()` when `use_retry=True`

4. **search.py** - Higher-level search API with metadata and pagination
   - `SearchRequest` dataclass: Wraps `RestaurantSearchRequest` with pagination support
   - `SearchResponse` dataclass: Structured response with status and metadata
   - `SearchMeta` dataclass: Total counts, page info, navigation flags
   - `SearchStatus` enum: SUCCESS, NO_RESULTS, ERROR
   - Supports multi-page scraping via `max_pages` parameter
   - Both sync (`search_sync()`) and async (`search()`) methods
   - **Area filtering**: Automatically uses area slug paths when prefecture can be mapped
   - **Cuisine filtering**: Supports `genre_code` parameter for URL path construction with cuisine types

5. **area_mapping.py** - Area name to URL slug mapping
   - `PREFECTURE_MAPPING`: Maps all 47 prefectures to Tabelog URL slugs
   - `CITY_MAPPING`: Maps major cities to URL slugs (tokyo, osaka, kyoto, etc.)
   - `get_area_slug()`: Converts area names (東京都, 大阪府) to URL slugs (tokyo, osaka)
   - **Purpose**: Enables accurate area filtering by using Tabelog's path-based filtering

6. **genre_mapping.py** - Cuisine type to genre code mapping
   - `GENRE_CODE_MAPPING`: Maps 45+ Japanese cuisine types to Tabelog genre codes (RC codes)
   - `get_genre_code()`: Converts cuisine name (すき焼き) to genre code (RC0107)
   - `get_genre_name_by_code()`: Reverse lookup from genre code to cuisine name
   - `get_all_genres()`: Returns list of all supported cuisine types
   - **Purpose**: Enables accurate cuisine filtering via URL path-based genre codes
   - **Coverage**: Supports common Japanese cuisine types (和食, 洋食, 中華, 焼肉, 鍋, 居酒屋, カレー, カフェ, etc.)

7. **suggest.py** - Area and keyword suggestion API integration
   - `AreaSuggestion` dataclass: Represents area/station suggestions from Tabelog
   - `KeywordSuggestion` dataclass: Represents keyword suggestions (cuisine types, restaurant names, combinations)
   - `get_area_suggestions()`: Sync function to get area suggestions
   - `get_area_suggestions_async()`: Async function to get area suggestions
   - `get_keyword_suggestions()`: Sync function to get keyword suggestions (🆕)
   - `get_keyword_suggestions_async()`: Async function to get keyword suggestions (🆕)
   - **API**: Uses `https://tabelog.com/internal_api/suggest_form_words`
     - `sa=query`: Area suggestions (prefecture, city, station)
     - `sk=query`: Keyword suggestions (cuisine, restaurant, combinations) (🆕)
   - **Response datatypes**:
     - Area: `AddressMaster`, `RailroadStation`
     - Keyword: `Genre2` (cuisine type), `Restaurant` (restaurant name), `Genre2 DetailCondition` (cuisine + condition)

8. **cli.py** - Command-line interface using Typer and Rich
   - `app`: Main Typer application instance
   - `search()`: Search restaurants with various filters (area, keyword, cuisine, query, sort, limit, output format)
   - `list_cuisines()`: Display all supported cuisine types in a table
   - `tui()`: Launch the interactive TUI
   - **Output formats**: table (Rich table), json (structured JSON), simple (plain text)
   - **Features**: Color-coded output, error handling, cuisine auto-detection, genre code filtering, AI natural language parsing
   - **CLI options**: -a/--area, -k/--keyword, -c/--cuisine, -q/--query (🆕), -s/--sort, -n/--limit, -o/--output
   - **Natural language query (-q)**: Uses `llm.parse_user_input()` to parse user input in multiple languages (Chinese, Japanese, English)
   - **Auto-detection**: Automatically detects cuisine types in keyword and converts to genre_code for precise filtering
   - Entry point: `tabelog search` or direct execution

9. **tui.py** - Interactive terminal UI using Textual framework
   - `TabelogApp`: Main TUI application class
   - `SearchPanel`: Search input panel with area, keyword, and sorting options
   - `ResultsTable`: DataTable for displaying restaurant results
   - `DetailPanel`: Panel showing detailed restaurant information
   - `AreaSuggestModal`: Modal popup for area suggestions (F2 key)
   - `GenreSuggestModal`: Modal popup for static cuisine type list (F3 key, when keyword is empty)
   - `KeywordSuggestModal`: Modal popup for dynamic keyword suggestions (F3 key, when keyword has content) (🆕)
   - **Intelligent F3 behavior** (🆕):
     - Empty keyword → Shows `GenreSuggestModal` with 45+ static cuisine types (fast, no API call)
     - Non-empty keyword → Calls API and shows `KeywordSuggestModal` with dynamic suggestions (cuisine types, restaurant names, combinations)
     - Icon differentiation: 🍜 (Genre2/cuisine), 🏪 (Restaurant), 🔖 (combinations)
   - **Auto-detection**: Automatically detects cuisine names in keyword input and converts to genre_code
   - **Smart linking**: AI parse (F4) automatically triggers area suggest (F2) or genre suggest (F3) after parsing
   - Features: RadioButton sorting, two-column layout, async worker management, context-aware autocomplete
   - Keybindings: F2 (area suggest), F3 (intelligent keyword/genre suggest), F4 (AI parse), s (search), r (results), d (detail), q (quit)
   - Entry point: `python -m tabelog.tui` or `uv run tabelog tui`

10. **server.py** - MCP (Model Context Protocol) server implementation (🆕)
    - `server`: Main MCP Server instance
    - **Tools** (4 total):
      - `search_restaurants`: Search restaurants with area, keyword, cuisine, sort, limit parameters
      - `list_cuisines`: Get all 45+ cuisine types with genre codes
      - `get_area_suggestions`: Get area/station suggestions from Tabelog API
      - `get_keyword_suggestions`: Get keyword/cuisine/restaurant suggestions from Tabelog API
    - **Design principles**:
      - ❌ No AI parsing (no OpenAI API key dependency)
      - ✅ Zero configuration
      - ✅ Simple structured parameters
      - ✅ Client-side natural language handling
    - **Implementation**: Uses MCP SDK's `@server.list_tools()` and `@server.call_tool()` decorators
    - **Transport**: stdio (standard input/output)
    - Entry point: `tabelog-mcp` command

11. **__init__.py** - Public API exports
   - Exports: `Restaurant`, `RestaurantSearchRequest`, `SearchRequest`, `SearchResponse`, `SortType`, `PriceRange`, `query_restaurants`, `AreaSuggestion`, `get_area_suggestions`, `get_area_suggestions_async`, `get_genre_code`, `get_genre_name_by_code`, `get_all_genres`

### API Patterns

The library provides **three levels of abstraction**:

1. **Quick function** (simplest): `query_restaurants()` - cached, sync-only
2. **Core request** (flexible): `RestaurantSearchRequest` - full control, sync/async
3. **Advanced search** (metadata): `SearchRequest` - pagination, status, metadata

### Important Implementation Details

- **Web scraping**: Uses `httpx` for requests and `BeautifulSoup` (lxml parser) for HTML parsing
- **CSS selectors**: Relies on specific Tabelog CSS classes (`list-rst`, `c-rating__val`, etc.)
- **HTML format handling**: Supports multiple Tabelog HTML formats for backward compatibility:
  - New format: `<div class="list-rst__area-genre"> [縣] 市區 / 類型</div>` (優先)
  - Old format: `<span class="list-rst__area-genre">地區、駅名 距離</span>` (fallback)
  - Genre extraction: Parses from area-genre field and separate `list-rst__genre` element
- **Area filtering** (CRITICAL):
  - **Problem**: Tabelog's `/rst/rstsearch?sa=area` endpoint DOES NOT filter by area - always returns national results
  - **Solution**: Use path-based URLs (e.g., `/tokyo/rstLst/` instead of `/rst/rstsearch?sa=東京`)
  - **Implementation**: `area_mapping.py` maps prefecture names to URL slugs, automatically used in search methods
  - **Limitation**: Only works for 47 prefectures + major cities; city/station-level filtering not supported
  - **Fallback**: If area cannot be mapped to slug, falls back to `/rst/rstsearch` (returns national results)
- **Cuisine filtering** (CRITICAL):
  - **Problem**: Using `keyword` parameter for cuisine types returns broad results (restaurants mentioning the cuisine, not specialists)
  - **Solution**: Use genre codes in URL path (e.g., `/mie/rstLst/RC0107/` for すき焼き specialists in 三重)
  - **Implementation**: `genre_mapping.py` maps cuisine names to genre codes, automatically used in search methods
  - **URL patterns**: Three combinations supported:
    - Area + Cuisine: `/area_slug/rstLst/GENRE_CODE/` (most precise)
    - Area only: `/area_slug/rstLst/`
    - Cuisine only: `/rstLst/GENRE_CODE/`
  - **Coverage**: 45+ common Japanese cuisine types with RC codes (RC0107-RC2101)
  - **Auto-detection**: TUI automatically detects cuisine names in keyword input and converts to genre_code
- **Keyword/Cuisine suggestion API** (NEW - discovered 2025-12-29):
  - **Endpoint**: `https://tabelog.com/internal_api/suggest_form_words`
  - **Parameters**:
    - `sa=query`: Area suggestions (prefecture, station, city)
    - `sk=query`: Keyword suggestions (cuisine, restaurant names, combinations) (🆕)
  - **Response structure**: JSON array with `name`, `datatype`, `id_in_datatype`, optional `lat`/`lng`
  - **datatypes** for keyword (`sk`):
    - `Genre2`: Cuisine type (すき焼き, 寿司, ラーメン)
    - `Restaurant`: Restaurant name (和田金, すきやき割烹 美川)
    - `Genre2 DetailCondition`: Cuisine + condition (すき焼き ランチ, 寿司 接待)
  - **Usage in TUI**: F3 key intelligently switches between static genre list (empty keyword) and dynamic API suggestions (non-empty keyword)
- **Error handling**: Gracefully skips malformed items during parsing (try/except with continue)
- **Caching**: `query_restaurants()` uses `@cache` decorator for performance
- **User-Agent**: All requests include browser User-Agent to avoid bot detection
- **Date/time format**: Validates `YYYYMMDD` for dates, `HHMM` for times in `__post_init__`
- **String cleaning**: Auto-strips whitespace from `area` and `keyword` parameters

## Testing Strategy

- **Location**: All tests in `tests/` directory
- **Current coverage**: 71% overall, 87-94% on core modules (target: 90%+)
- **Total tests**: 101 tests (all passing ✓)
- **Test types**:
  - Unit tests: Models, validation, parameter building, caching, retry logic
  - Function tests: HTTP requests, HTML parsing, error handling
  - Integration tests: End-to-end search workflows
- **New test files** (🆕):
  - `test_cache.py`: 12 tests for MemoryCache, FileCache, and cache helpers
  - `test_retry.py`: 11 tests for retry logic, error handling, and exponential backoff
- **Mocking**: Mock `httpx.get` and `httpx.AsyncClient` for HTTP tests (no real network calls)
- **Async**: Uses `pytest-asyncio` with `AsyncMock` for async operations
- **Performance**: All tests run in ~6 seconds with mocking (no actual retry delays)
- **Note**: TUI (tui.py) and CLI (cli.py) currently have 0% coverage (UI modules)

## Type Annotations

- **Required**: Full type hints on all functions
- **Style**: Built-in types only (e.g., `list[str]`, `dict[str, Any]`, `X | None`)
- **Checker**: Uses `ty` (configured in Makefile and pyproject.toml)
- **py.typed marker**: Present in `src/tabelog/py.typed` for library consumers

## Code Style

- **Formatter/Linter**: ruff with specific rules (see pyproject.toml)
- **Line length**: 120 characters max
- **Import sorting**: Single-line imports enforced (`force-single-line = true`)
- **Ignored**: E501, C901 per pyproject.toml
- **Selected rules**: B (bugbear), C (comprehensions), E/W (pycodestyle), F (pyflakes), I (isort), N (naming), SIM (simplify), UP (pyupgrade)

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:
1. Basic checks (YAML, EOF, trailing whitespace)
2. Ruff (lint + format)
3. MyPy (type checking)
4. UV lock file sync

## Key Constraints & Considerations

- **Web scraping fragility**: Tabelog's HTML structure may change without notice
- **Rate limiting**: No built-in rate limiting - users must implement for production use
- **Legal compliance**: Library is for educational/research purposes - respect robots.txt and ToS
- **Fallback selectors**: Parser includes backup CSS selectors for robustness
- **MCP server** (🆕): Fully implemented in `server.py` with 4 tools, zero-config design, no API key required

## Dependencies

**Production**:
- `beautifulsoup4` - HTML parsing
- `lxml` - BeautifulSoup parser backend
- `httpx` - HTTP client (sync + async)
- `loguru` - Logging
- `mcp[cli]` - MCP server framework
- `typer` - CLI framework
- `tenacity` - Retry logic with exponential backoff (🆕)

**Development**:
- `pytest`, `pytest-asyncio`, `pytest-cov` - Testing
- `ruff` - Linting/formatting
- `ty` - Type checking
