# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive MCP server tests (22 tests, 98% coverage) for all 4 tools
- JavaScript rendering verification script (`scripts/verify_js_rendering.py`)
- Detailed verification results documenting httpx reliability (100% success rate)
- MCP server workflow instructions for LLM clients (FastMCP `instructions` parameter)
- Tool-level usage warnings in `tabelog_search_restaurants` docstring

### Changed
- Updated IDEAS.md with JavaScript rendering verification results
- Improved overall test coverage from 52% to 58%
- Enhanced error messages in all MCP tools with actionable next steps

### Fixed
- Verified that current httpx + BeautifulSoup implementation works reliably (no Playwright needed)

## [0.0.2] - 2025-12-29

### Added
- **MCP Server FastMCP Migration** 🎉
  - Migrated from low-level Server API to high-level FastMCP framework
  - Automatic schema generation from Python type hints
  - Pydantic output schemas for type-safe responses (`RestaurantOutput`, `CuisineOutput`, `SuggestionOutput`)
  - Comprehensive tool annotations (`readOnlyHint`, `idempotentHint`, `openWorldHint`)
  - Enhanced error handling with detailed, actionable error messages

- **New MCP Tools**:
  - `tabelog_search_restaurants`: Search with area, keyword, cuisine, sort, limit parameters
  - `tabelog_list_cuisines`: Get all 45+ supported Japanese cuisine types
  - `tabelog_get_area_suggestions`: Get area/station suggestions from Tabelog API
  - `tabelog_get_keyword_suggestions`: Get keyword/cuisine/restaurant suggestions from Tabelog API (🆕)

- **Keyword Suggestion API Integration** (discovered 2025-12-29)
  - New `get_keyword_suggestions()` and `get_keyword_suggestions_async()` functions
  - Support for dynamic autocomplete: cuisine types (Genre2), restaurant names (Restaurant), combinations (Genre2 DetailCondition)
  - Integrated into TUI with intelligent F3 behavior (static list when empty, dynamic API when typing)

- **TUI Enhancements**:
  - Intelligent F3 keyword suggestion behavior (context-aware)
  - F4 AI natural language parsing with auto-triggered suggestions
  - Automatic cuisine type detection in keyword input
  - Smart linking: AI parse automatically triggers area/genre suggestions

- **CLI Enhancements**:
  - `-q/--query` flag for natural language input (AI-powered parsing)
  - Automatic cuisine detection and conversion to precise filtering
  - Support for multiple languages (Chinese, Japanese, English)

- **Caching System** (`cache.py`):
  - `MemoryCache`: In-memory LRU cache with TTL (default 1 hour)
  - `FileCache`: File-based persistent cache for development
  - Global cache helpers: `cached_get()`, `cache_set()`, `clear_cache()`
  - Automatic integration in search operations (30-min TTL)

- **Retry Mechanism** (`retry.py`):
  - Exponential backoff with jitter (1s → 2s → 4s)
  - Smart error detection (retryable vs non-retryable)
  - Custom exceptions: `RateLimitError`, `NetworkError`
  - Automatic integration in HTTP requests

- **Comprehensive Test Coverage**:
  - `test_cache.py`: 12 tests for caching system
  - `test_retry.py`: 11 tests for retry logic
  - Total: 101 tests, 52% overall coverage
  - Core modules: 87-94% coverage

### Changed

- **BREAKING: MCP Tool Names** (Renamed with `tabelog_` prefix):
  - `search_restaurants` → `tabelog_search_restaurants`
  - `list_cuisines` → `tabelog_list_cuisines`
  - `get_area_suggestions` → `tabelog_get_area_suggestions`
  - `get_keyword_suggestions` → `tabelog_get_keyword_suggestions` (new)

- **MCP Server Architecture**:
  - Replaced custom MCP SDK implementation with FastMCP
  - Changed from manual schema definitions to automatic Pydantic generation
  - Improved error messages from generic to specific with next-step guidance
  - Added comprehensive docstrings with usage examples and best practices

- **Documentation**:
  - README.md: Added "Recommended Workflow" section with step-by-step MCP usage guide
  - README.md: Updated MCP server configuration examples (GitHub, PyPI, Local)
  - README.md: Added workflow examples showing multi-step validation pattern
  - SKILL.md: Merged SKILLMCP.md content for unified MCP development guide
  - CLAUDE.md: Updated server.py description with FastMCP details

### Deprecated

- Low-level MCP Server API usage (replaced by FastMCP)
- Manual schema definitions (replaced by automatic Pydantic generation)

### Fixed

- Improved HTML parsing robustness with multiple format support
- Better error handling for malformed restaurant data
- Cache integration preventing redundant HTTP requests
- Retry logic reducing transient network failures

## [0.0.1] - 2025-08-21

### Added
- Initial release of gurume library
- Core restaurant search functionality with httpx + BeautifulSoup
- Support for 45+ Japanese cuisine types with genre code mapping
- Support for all 47 Japanese prefectures with area mapping
- CLI interface with `gurume search` command
- Interactive TUI with Textual framework
- MCP server with basic tools (low-level Server API)
- Comprehensive search parameters:
  - Area, keyword, cuisine type filtering
  - Reservation date/time/party size
  - Sort by ranking, review count, new open
  - Price range filters (lunch/dinner)
  - Restaurant features (private room, parking, etc.)
- Async and sync API support
- Type hints with full type checking support
- Detailed documentation and examples

---

## Migration Guide

### Migrating from 0.0.1 to 0.0.2

#### MCP Server Tool Names

If you're using the MCP server, update your tool calls:

```python
# Old (0.0.1)
search_restaurants(area="東京", cuisine="寿司")
list_cuisines()
get_area_suggestions(query="東京")

# New (0.0.2)
tabelog_search_restaurants(area="東京", cuisine="寿司")
tabelog_list_cuisines()
tabelog_get_area_suggestions(query="東京")
tabelog_get_keyword_suggestions(query="すき")  # NEW!
```

#### Claude Desktop Configuration

Update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gurume": {
      "command": "uvx",
      "args": ["gurume", "mcp"]
    }
  }
}
```

No changes needed for library users (Python API remains backward compatible).

---

[Unreleased]: https://github.com/narumiruna/gurume/compare/v0.0.2...HEAD
[0.0.2]: https://github.com/narumiruna/gurume/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/narumiruna/gurume/releases/tag/v0.0.1
