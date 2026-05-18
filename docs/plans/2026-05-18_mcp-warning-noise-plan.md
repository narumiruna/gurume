## Goal

Reduce noisy MCP search warnings so validated or clearly mapped inputs do not repeatedly tell callers to run suggestion tools first.

Success means MCP still warns on ambiguous or low-confidence inputs, but standard validated `area + supported cuisine` searches no longer emit unnecessary suggestion reminders.

## Context

The skill-vs-MCP comparison found 50 MCP warning entries across 50 successful `area + supported cuisine` searches, even though the inputs were already chosen from `tabelog_list_cuisines` and `tabelog_get_area_suggestions`. That makes warnings less useful for agents because every successful call looks like it needs recovery.

## Non-Goals

- Do not remove low-confidence area warnings for keyword searches; that overlaps with `docs/plans/2026-05-18_area-filter-confidence-plan.md`.
- Do not change search ranking or parsing behavior.
- Do not weaken hard validation errors such as unsupported `keyword + cuisine`.

## Unknowns

- Whether the server can distinguish validated caller inputs from raw user strings without adding new parameters. Resolve by inspecting current warning construction before changing the public tool schema.

## Plan

- [ ] Locate warning generation in `src/gurume/server_helpers.py` and search tests that assert warnings; verify with `rg -n "warning|warnings|suggestions|ambiguous area" src/gurume tests`.
- [ ] Define warning policy for three cases: mapped `area + supported cuisine`, raw ambiguous area, and `area + keyword` low-confidence search; verify the policy is written in test names or comments.
- [ ] Add regression tests where `area="東京都"` and `cuisine="寿司"` returns no suggestion reminder warning; verify with `uv run pytest tests/test_server.py -v`.
- [ ] Add or preserve tests where ambiguous raw area or low-confidence keyword searches still return actionable warnings; verify with `uv run pytest tests/test_server.py -v`.
- [ ] Implement the smallest warning-generation change in `src/gurume/server_helpers.py` or the narrowest owning helper; verify with focused tests.
- [ ] Run one live MCP smoke for a standard validated query and one low-confidence keyword query, recording whether warning counts match policy; verify with saved command output or completion notes.
- [ ] Run focused gates; verify with `uv run ruff check src/gurume/server_helpers.py tests/test_server.py`, `uv run ty check .`, and `uv run pytest tests/test_server.py -v`.

## Risks

- Suppressing warnings too broadly could hide real upstream filter uncertainty.
- If the server cannot know whether an input was validated, the policy may need to rely on mapped area/cuisine evidence instead of caller history.

## Completion Checklist

- [ ] Standard mapped `area + supported cuisine` MCP searches do not emit suggestion-reminder noise, verified by `tests/test_server.py`.
- [ ] Ambiguous or low-confidence searches still emit actionable warnings or structured errors, verified by `tests/test_server.py`.
- [ ] Live smoke output confirms the intended warning behavior for one clean query and one risky query.
- [ ] Focused lint, type check, and server tests pass with recorded command output.
