# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **tabelogmcp** - a Python library and MCP (Model Context Protocol) server for searching restaurants on Tabelog using web scraping. It provides both a Python library (`tabelog`) and an MCP server (`tabelogmcp`) for integration with AI assistants.

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

# Run type checker
make type
# or
uv run ty check .
```

### Publishing
```bash
make publish  # Builds wheel and publishes to PyPI
```

### Running Examples
```bash
# Basic search example
PYTHONPATH=/home/narumi/workspace/tabelog/src python examples/basic_search.py

# Or with uv
uv run python examples/basic_search.py
```

### Running MCP Server
```bash
# Via entry point (requires installation)
uv run tabelogmcp

# Local development
uv run --directory /path/to/tabelog-mcp tabelogmcp
```

## Architecture

### Core Modules (src/tabelogmcp/)

The codebase is intentionally simple with only 3 main files:

1. **restaurant.py** - Core scraping and search implementation
   - `Restaurant` dataclass: Represents restaurant data (name, rating, reviews, prices, etc.)
   - `RestaurantSearchRequest` dataclass: Builds search URLs and scrapes Tabelog
   - `SortType` enum: Search sorting options (STANDARD, RANKING, REVIEW_COUNT, NEW_OPEN)
   - `PriceRange` enum: Extensive lunch/dinner price ranges (B001-B012, C001-C012)
   - `query_restaurants()` function: Cached convenience function for quick searches
   - Key methods: `_build_params()`, `_parse_restaurants()`, `do_sync()`, `do()`

2. **search.py** - Higher-level search API with metadata and pagination
   - `SearchRequest` dataclass: Wraps `RestaurantSearchRequest` with pagination support
   - `SearchResponse` dataclass: Structured response with status and metadata
   - `SearchMeta` dataclass: Total counts, page info, navigation flags
   - `SearchStatus` enum: SUCCESS, NO_RESULTS, ERROR
   - Supports multi-page scraping via `max_pages` parameter
   - Both sync (`do_sync()`) and async (`do()`) methods

3. **__init__.py** - Public API exports
   - Exports: `Restaurant`, `RestaurantSearchRequest`, `SearchRequest`, `SearchResponse`, `SortType`, `PriceRange`, `query_restaurants`

### API Patterns

The library provides **three levels of abstraction**:

1. **Quick function** (simplest): `query_restaurants()` - cached, sync-only
2. **Core request** (flexible): `RestaurantSearchRequest` - full control, sync/async
3. **Advanced search** (metadata): `SearchRequest` - pagination, status, metadata

### Important Implementation Details

- **Web scraping**: Uses `httpx` for requests and `BeautifulSoup` (lxml parser) for HTML parsing
- **CSS selectors**: Relies on specific Tabelog CSS classes (`list-rst`, `c-rating__val`, etc.)
- **Error handling**: Gracefully skips malformed items during parsing (try/except with continue)
- **Caching**: `query_restaurants()` uses `@cache` decorator for performance
- **User-Agent**: All requests include browser User-Agent to avoid bot detection
- **Date/time format**: Validates `YYYYMMDD` for dates, `HHMM` for times in `__post_init__`
- **String cleaning**: Auto-strips whitespace from `area` and `keyword` parameters

## Testing Strategy

- **Location**: All tests in `tests/` directory
- **Current coverage**: 96% (target: 90%+)
- **Test types**:
  - Unit tests: Models, validation, parameter building
  - Function tests: HTTP requests, HTML parsing, error handling
  - Integration tests: End-to-end search workflows
- **Mocking**: Mock `httpx.get` and `httpx.AsyncClient` for HTTP tests
- **Async**: Uses `pytest-asyncio` with `AsyncMock` for async operations

## Type Annotations

- **Required**: Full type hints on all functions
- **Style**: Built-in types only (e.g., `list[str]`, `dict[str, Any]`, `X | None`)
- **Checker**: Uses `ty` (configured in Makefile and pyproject.toml)
- **py.typed marker**: Present in `src/tabelogmcp/py.typed` for library consumers

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
- **No MCP server code**: Despite `tabelogmcp` package name and entry point in pyproject.toml, the actual MCP server implementation (`server.py`) is currently missing

## Dependencies

**Production**:
- `beautifulsoup4` - HTML parsing
- `lxml` - BeautifulSoup parser backend
- `httpx` - HTTP client (sync + async)
- `loguru` - Logging
- `mcp[cli]` - MCP server framework
- `typer` - CLI framework

**Development**:
- `pytest`, `pytest-asyncio`, `pytest-cov` - Testing
- `ruff` - Linting/formatting
- `ty` - Type checking
