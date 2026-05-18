## Goal

Add an opt-in CLI JSON envelope that exposes search metadata, warnings, applied filters, and structured errors in a shape close to MCP search output while preserving the existing list-only JSON behavior by default.

Success means agents and scripts can request a richer JSON response from `gurume search` without scraping stderr, and existing callers using `--output json` still receive the current list of restaurants unless they opt in.

## Context

The skill-vs-MCP research showed that standard `area + supported cuisine` searches return identical restaurant rankings through CLI and MCP. The practical gap is output shape: CLI JSON is compact but only returns a restaurant list, while MCP returns `status`, `items`, `meta`, `applied_filters`, `warnings`, and `error`.

## Non-Goals

- Do not change the default `--output json` list contract in this phase.
- Do not redesign TUI output.
- Do not solve low-confidence `area + keyword` behavior here; that is covered by `docs/plans/2026-05-18_area-filter-confidence-plan.md`.

## Plan

- [x] Inspect current CLI JSON tests and MCP output model fields to define a minimal CLI envelope schema; verified with `rg -n "output json|_output_json|RestaurantSearchOutput|applied_filters|warnings" src tests`.
- [x] Add a CLI option such as `--json-envelope` or a new output value such as `--output json-envelope` that is clearly opt-in; verified with `env UV_CACHE_DIR=/tmp/uv-cache uv run gurume search --help`.
- [x] Implement the envelope output for successful searches with `status`, `items`, `returned_count`, `limit`, `applied_filters`, and `warnings`; verified with `tests/test_cli.py` JSON assertions.
- [x] Implement envelope output for CLI validation/search errors so scripts can parse `status="error"` and a structured `error` object instead of stderr text; verified with `tests/test_cli.py`.
- [x] Keep existing `--output json` unchanged as a plain list; verified with `tests/test_cli.py`.
- [x] Review `skills/gurume-cli/SKILL.md` for agent workflows; keep the default command on compact `--output json` for convenience and document `--output json-envelope` for structured warnings/errors. Synced with `uv run python scripts/sync_skills.py` and verified with `uv run python scripts/sync_skills.py --check`.
- [x] Update README/TUI docs only where they mention JSON output behavior; verified with `rg -n -- "json-envelope|--output json|JSON" README.md docs skills`.
- [x] Run focused gates; verified with `uv run ruff check src/gurume/cli.py tests/test_cli.py`, `uv run ty check .`, and `uv run pytest tests/test_cli.py -v`.

## Risks

- Changing `--output json` directly would break scripts, so this plan requires opt-in behavior.
- Duplicating MCP schemas in CLI could drift; keep the CLI envelope minimal and reuse helper/model concepts where practical.

## Completion Checklist

- [x] Existing `gurume search --output json` still returns a JSON list, verified by `tests/test_cli.py`.
- [x] The new envelope mode returns parseable `status`, `items`, `applied_filters`, `warnings`, and structured `error` fields, verified by `tests/test_cli.py`.
- [x] Agent-facing skill guidance is updated and synced, with compact `--output json` as the default and `--output json-envelope` documented for structured responses; verified by `uv run python scripts/sync_skills.py --check`.
- [x] Focused lint, type check, and CLI tests pass with recorded command output.

## Completion Evidence

- `env UV_CACHE_DIR=/tmp/uv-cache uv run gurume search --help`: `--output` includes `json-envelope`.
- `uv run pytest tests/test_cli.py -v`: 23 passed.
- `uv run pytest -q tests`: 294 passed, 3 skipped.
- `uv run ruff check src/gurume/cli.py tests/test_cli.py`: passed.
- `uv run ty check .`: passed.
- `uv run python scripts/sync_skills.py --check`: `.codex/skills/ is in sync with skills/`.
