# CLAUDE.md

This file provides working guidance for Claude Code and similar coding agents in this repository.

## Project Overview

`gurume` is a Python library and MCP server for searching restaurants on Tabelog via web scraping.
The repository includes:

- a Python package under `src/gurume/`
- a CLI exposed as `gurume`
- a Textual TUI
- an MCP server for AI assistant integrations

Use this document as an agent-facing execution guide. For user-facing setup and usage examples, see `README.md`.

## Working Principles

- Prefer existing project tooling and patterns over new abstractions.
- Keep changes tightly scoped to the task.
- Add or update tests when behavior changes.
- Treat scraped upstream HTML and internal APIs as unstable inputs.
- Verify commands and assumptions against the current repo before documenting them.

## Repository Map

### Core code

- `src/gurume/restaurant.py`: core scraping request/response logic
- `src/gurume/search.py`: higher-level search API with metadata and pagination
- `src/gurume/detail.py`: restaurant detail fetching and parsing
- `src/gurume/suggest.py`: area and keyword suggestion API integration
- `src/gurume/server.py`: FastMCP server tools
- `src/gurume/cli.py`: Typer CLI entrypoints
- `src/gurume/tui.py`: Textual terminal UI
- `src/gurume/cache.py` and `src/gurume/retry.py`: resilience helpers
- `src/gurume/area_mapping.py` and `src/gurume/genre_mapping.py`: mapping helpers for precise filtering

### Supporting directories

- `tests/`: unit and integration tests, usually mirroring module names
- `examples/`: runnable usage examples

## Development Commands

Use `uv` for Python execution and dependency management.

### Setup

```bash
uv sync --dev
```

### Checks

```bash
make lint
make type
make test
```

Equivalent direct commands:

```bash
uv run ruff check .
uv run ty check .
uv run pytest -v -s --cov=src tests
```

### Run locally

```bash
uv run python examples/basic_search.py
uv run gurume mcp
uv run gurume tui
```

## Coding Guidance

### Python conventions

- Target Python 3.12+.
- Keep full type hints on public and non-trivial internal functions.
- Use built-in generic syntax such as `list[str]` and `X | None`.
- Follow Ruff configuration in `pyproject.toml`.
- Respect the configured 120-character line length.

### Design expectations

- Keep modules focused. Split files before they become difficult to scan.
- Avoid adding dependencies unless there is a concrete need.
- Reuse existing request, parsing, cache, retry, and mapping helpers when possible.
- Prefer explicit behavior over clever abstractions.

## Testing Expectations

- Put tests in `tests/` using names like `test_<feature>.py`.
- Prefer focused unit tests with mocks for HTTP boundaries.
- Add integration coverage only when workflow behavior matters.
- When changing scraping, parsing, CLI, TUI, or MCP behavior, update the corresponding tests in the same change.

Useful examples:

```bash
uv run pytest tests/test_search.py -v
uv run pytest tests/test_server.py -v
uv run pytest tests/test_detail.py -v
```

## Project-Specific Gotchas

### Scraping behavior

- Tabelog markup changes without warning. Write parsing logic defensively.
- CSS selectors and HTML structures are not stable contracts.
- Skip malformed items gracefully when possible, but keep failures debuggable.

### Area filtering

- Do not assume `sa=<area>` query parameters produce correct area filtering.
- Accurate prefecture-level filtering depends on path-based area slugs such as `/tokyo/rstLst/`.
- If an area cannot be mapped, current behavior may fall back to broader results.

### Cuisine filtering

- Cuisine searches should prefer genre-code-based URL paths over plain keyword matching.
- `genre_mapping.py` exists to make cuisine filtering precise; use it before adding new ad hoc matching logic.

### Suggestions and details

- Suggestion endpoints and detail pages are upstream-controlled and may change response shape.
- Preserve defensive parsing and actionable error messages when touching these flows.

## MCP and CLI Notes

- The MCP server is implemented with FastMCP in `src/gurume/server.py`.
- Keep tool outputs structured and validation errors clear.
- CLI and TUI behavior should stay aligned with the underlying search APIs.
- If you change parameters or output behavior in one interface, verify whether the others should change too.

## Documentation Hygiene

- Keep this file short, operational, and current.
- Do not duplicate large sections of `README.md` or `AGENTS.md`.
- Remove stale details instead of preserving them for completeness.
- If commands, tooling, or workflows change, update this file in the same PR.
