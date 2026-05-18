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

- [ ] Inspect current CLI JSON tests and MCP output model fields to define a minimal CLI envelope schema; verify with `rg -n "output json|_output_json|RestaurantSearchOutput|applied_filters|warnings" src tests`.
- [ ] Add a CLI option such as `--json-envelope` or a new output value such as `--output json-envelope` that is clearly opt-in; verify the chosen option appears in `uv run gurume search --help`.
- [ ] Implement the envelope output for successful searches with `status`, `items`, `returned_count`, `limit`, `applied_filters`, and `warnings`; verify with a focused `tests/test_cli.py` snapshot or JSON assertion.
- [ ] Implement envelope output for CLI validation/search errors so scripts can parse `status="error"` and a structured `error` object instead of stderr text; verify with `tests/test_cli.py`.
- [ ] Keep existing `--output json` unchanged as a plain list; verify with an existing or new regression test in `tests/test_cli.py`.
- [ ] Update `skills/gurume-cli/SKILL.md` only if the skill should prefer the envelope for agent workflows; sync with `uv run python scripts/sync_skills.py` and verify with `uv run python scripts/sync_skills.py --check`.
- [ ] Update README/TUI docs only where they mention JSON output behavior; verify with `rg -n "json-envelope|--output json|JSON" README.md docs skills`.
- [ ] Run focused gates; verify with `uv run ruff check src/gurume/cli.py tests/test_cli.py`, `uv run ty check .`, and `uv run pytest tests/test_cli.py -v`.

## Risks

- Changing `--output json` directly would break scripts, so this plan requires opt-in behavior.
- Duplicating MCP schemas in CLI could drift; keep the CLI envelope minimal and reuse helper/model concepts where practical.

## Completion Checklist

- [ ] Existing `gurume search --output json` still returns a JSON list, verified by `tests/test_cli.py`.
- [ ] The new envelope mode returns parseable `status`, `items`, `applied_filters`, `warnings`, and structured `error` fields, verified by `tests/test_cli.py`.
- [ ] Agent-facing skill guidance is either updated and synced or explicitly left unchanged with evidence from `rg`.
- [ ] Focused lint, type check, and CLI tests pass with recorded command output.
