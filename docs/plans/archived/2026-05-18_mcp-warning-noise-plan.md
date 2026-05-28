## Goal

Reduce noisy MCP search warnings so validated or clearly mapped inputs do not repeatedly tell callers to run suggestion tools first.

Success means MCP still warns on ambiguous or low-confidence inputs, but standard validated `area + supported cuisine` searches no longer emit unnecessary suggestion reminders.

## Context

The skill-vs-MCP comparison found 50 MCP warning entries across 50 successful `area + supported cuisine` searches, even though the inputs were already chosen from `tabelog_list_cuisines` and `tabelog_get_area_suggestions`. That makes warnings less useful for agents because every successful call looks like it needs recovery.

## Status

Completed by the current warning policy. Mapped `area + supported cuisine` searches no longer emit suggestion-reminder
warnings, while ambiguous area-only and low-confidence `area + keyword` searches still return actionable warnings.

## Non-Goals

- Do not remove low-confidence area warnings for keyword searches; that overlaps with `docs/plans/2026-05-18_area-filter-confidence-plan.md`.
- Do not change search ranking or parsing behavior.
- Do not weaken hard validation errors such as unsupported `keyword + cuisine`.

## Unknowns

- Whether the server can distinguish validated caller inputs from raw user strings without adding new parameters. Resolve by inspecting current warning construction before changing the public tool schema.

## Plan

- [x] Locate warning generation in `src/gurume/server_helpers.py` and search tests that assert warnings; verified with `rg -n "warning|warnings|suggestions|ambiguous area" src/gurume tests`.
- [x] Define warning policy for three cases: mapped `area + supported cuisine`, raw ambiguous area, and `area + keyword` low-confidence search; verified by server test names and warning assertions.
- [x] Add regression tests where `area="東京都"` and `cuisine="寿司"` returns no suggestion reminder warning; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py tests/test_suggest.py -v`.
- [x] Add or preserve tests where ambiguous raw area or low-confidence keyword searches still return actionable warnings; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py tests/test_suggest.py -v`.
- [x] Implement the smallest warning-generation change in `src/gurume/server_helpers.py` or the narrowest owning helper; verified by current server helper behavior and focused tests.
- [x] Run one live MCP smoke for a standard validated query and one low-confidence keyword query, recording whether warning counts match policy; verified by `東京都 + 寿司` returning no warnings and `大阪 + とんかつ定食` returning low-confidence warnings.
- [x] Run focused gates; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and targeted pytest commands.

## Risks

- Suppressing warnings too broadly could hide real upstream filter uncertainty.
- If the server cannot know whether an input was validated, the policy may need to rely on mapped area/cuisine evidence instead of caller history.

## Completion Checklist

- [x] Standard mapped `area + supported cuisine` MCP searches do not emit suggestion-reminder noise, verified by `tests/test_server.py`.
- [x] Ambiguous or low-confidence searches still emit actionable warnings or structured errors, verified by `tests/test_server.py`.
- [x] Live smoke output confirms the intended warning behavior for one clean query and one risky query.
- [x] Focused lint, type check, and server tests pass with recorded command output.
