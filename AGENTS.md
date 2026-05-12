# Repository Guidelines

## Project Structure & Module Organization
`src/gurume/` contains the library, CLI, TUI, and MCP server. Key modules:

- `restaurant.py`: core scraping request/response logic.
- `search.py`: higher-level search API with metadata and pagination.
- `detail.py`: restaurant detail fetching and parsing.
- `suggest.py`: area and keyword suggestion API integration.
- `server.py`: FastMCP server tools.
- `cli.py`: Typer CLI entrypoints.
- `tui.py`: Textual terminal UI.
- `cache.py`, `retry.py`: resilience helpers.
- `area_mapping.py`, `genre_mapping.py`: mapping helpers for precise filtering.

Tests are in `tests/` and generally mirror module names, for example `tests/test_search.py` and `tests/test_server.py`. Runnable usage examples live in `examples/`.

## Build, Test, and Development Commands
Use `uv` for all local Python workflows.

- `uv sync --dev`: install runtime and development dependencies.
- `make lint` or `uv run ruff check .`: run lint and import-order checks.
- `make type` or `uv run ty check .`: run static type checks. Run this after code changes.
- `make test` or `uv run pytest -v -s --cov=src tests`: run the full test suite with coverage.
- `uv run python examples/basic_search.py`: run a basic example locally.
- `uv run gurume mcp`: start the MCP server for local integration testing.
- `uv run gurume tui`: launch the Textual TUI for interactive search.

## Coding Style & Naming Conventions
Target Python 3.12 and keep code type-annotated, using built-in generic syntax such as `list[str]` and `X | None` rather than `typing` aliases. Follow Ruff settings in `pyproject.toml`: 120-character line length, single-line imports where isort rewrites them, and standard `snake_case` for functions/modules, `PascalCase` for classes, and `UPPER_CASE` for constants and enums. Keep modules focused; split files before they become difficult to navigate. Reuse existing request, parsing, cache, retry, and mapping helpers before introducing new ones, and avoid adding dependencies or abstractions unless the current code clearly needs them.

## Testing Guidelines
Write tests under `tests/` with names like `test_<feature>.py` and test functions named `test_<behavior>`. Prefer focused unit tests with mocks for HTTP boundaries, and add integration coverage only where real workflow behavior matters. When changing search, parsing, CLI, TUI-adjacent logic, or MCP tools, add or update the corresponding test file before merging.

## Commit & Pull Request Guidelines
Recent history favors short imperative messages such as `fix lint errors`, `remove codecov from ci workflow`, and scoped prefixes like `feat(mcp): expose ...` or `test: Add comprehensive tests ...`. Keep commit messages specific to one change. Pull requests should explain user-visible impact, list validation steps (`ruff`, `ty`, `pytest`), link related issues, and include screenshots or terminal output when changing CLI or TUI behavior.

## Security & Configuration Tips
Do not commit secrets. Natural-language parsing has been removed from the CLI/TUI; route free-form user input through the `gurume-cli` agent skill instead. Treat scraped upstream HTML as unstable: prefer defensive parsing, clear exceptions, and tests that lock in expected behavior.

## MCP and CLI Consistency
The MCP server (`src/gurume/server.py`, FastMCP), CLI, and TUI all sit on top of the same search APIs. Keep tool outputs structured and validation errors clear, and when you change parameters or output behavior in one interface, check whether the others should change too.

## MEMORY.md

- `docs/MEMORY.md` is not auto-loaded. Check it before non-trivial debugging or design work when prior project context may matter.
- Keep entries short and reusable.
- `docs/MEMORY.md` must use `## GOTCHA` and `## TASTE` sections.
- After a non-trivial error or discovery, add one concise entry if it will help future work.

## LOG.md

- Append ONE line to the end of `docs/LOG.md`.
- Format: `YYYY-MM-DD | type(scope): summary (#ref)`.
- Do not modify existing content.
