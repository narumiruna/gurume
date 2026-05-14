# Test Suite

This directory contains the test suite for `gurume`.

## Structure

Current test files:

- `test_area_mapping.py`: area-name to Tabelog path mapping.
- `test_cache.py`: in-memory and file cache helpers.
- `test_cli.py`: Typer CLI commands and output behavior.
- `test_detail.py`: restaurant detail parsing and fetch behavior.
- `test_genre_mapping.py`: cuisine-name, genre-code, and path-segment mapping.
- `test_hello.py`: minimal package smoke test.
- `test_integration.py`: mocked end-to-end search flows.
- `test_models.py`: dataclass and enum behavior.
- `test_restaurant.py`: core restaurant search request and HTML parsing.
- `test_retry.py`: retry and HTTP error handling helpers.
- `test_search.py`: higher-level search response, metadata, pagination, and URL construction.
- `test_server.py`: FastMCP tool wrappers, structured outputs, and transport options.
- `test_suggest.py`: area and keyword suggestion parsing.
- `integration/test_cuisine_filter.py`: opt-in live Tabelog cuisine-filter checks.

Shared fixtures live in `conftest.py`. Pytest configuration is in `pyproject.toml`.

## Running Tests

Run the default project test command:

```bash
uv run pytest -v -s --cov=src tests
```

Run focused test files:

```bash
uv run pytest tests/test_search.py -v
uv run pytest tests/test_server.py -v
uv run pytest tests/test_cli.py -v
```

Run with coverage details:

```bash
uv run pytest tests --cov=src --cov-report=term-missing
```

Run opt-in live integration checks:

```bash
GURUME_RUN_INTEGRATION=1 uv run pytest -m integration tests/integration/test_cuisine_filter.py -v
```

Only the `integration` marker is currently declared. Live integration tests are skipped by default unless
`GURUME_RUN_INTEGRATION=1` is set.

## Testing Style

- Prefer focused unit tests with mocked HTTP boundaries.
- Use realistic Tabelog HTML snippets for parser behavior.
- Keep live network checks opt-in and isolated under `tests/integration/`.
- When changing CLI, TUI-adjacent behavior, MCP tools, search metadata, parsing, or mappings, update the corresponding
  focused test file.
- Avoid relying on exact live Tabelog counts in default tests; upstream markup and data can change without warning.
