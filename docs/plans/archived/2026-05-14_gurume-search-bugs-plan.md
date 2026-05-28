## Goal

Fix the live-search correctness bugs exposed by the Osaka tonkatsu lookup so `gurume-cli` and MCP tools can safely support restaurant recommendations without returning validation failures or cross-area keyword results.

Success means:

- MCP area and keyword suggestion tools return structured envelopes for currently observed upstream datatypes instead of failing Pydantic validation.
- CLI keyword searches with an area either preserve the requested area or fail with a clear warning/error instead of silently returning restaurants from other prefectures.
- The recommended query path for cuisine-like requests remains `--cuisine`, with tests locking in the expected behavior.

## Context

Live checks on 2026-05-14 showed two user-visible issues:

- `tabelog_get_area_suggestions("大阪")` failed because upstream returned `datatype="MajorMunicipal"`, which the MCP schema did not accept.
- `tabelog_get_keyword_suggestions("とんかつ")` failed because upstream returned `datatype="Genre3"`, which the MCP schema did not accept.
- `uv run gurume search --area 大阪 --keyword とんかつ定食 --sort ranking --limit 10 --output json` returned restaurants outside Osaka, while `--area 大阪 --cuisine とんかつ` returned correct Osaka tonkatsu results.

## Status

Completed by later, narrower changes. Suggestion datatypes now preserve raw upstream strings, keyword searches expose
low-confidence area evidence and warnings instead of silently presenting cross-area results, and cuisine-like requests
continue to route through `--cuisine` when supported.

## Non-Goals

- Do not reintroduce natural-language parsing inside the CLI or TUI.
- Do not solve full menu/detail extraction from CLI search results in this plan.
- Do not add a new recommendation ranking layer beyond making existing search filters trustworthy.

## Assumptions

- Tabelog suggestion datatypes are upstream-controlled and may expand again, so parsing should be defensive.
- For cuisine-like user intent, structured `--cuisine` searches are the reliable path; keyword searches are for narrower text terms only when area filtering can be verified.

## Unknowns

- Which current upstream datatypes can appear from area and keyword suggestion endpoints beyond `MajorMunicipal` and `Genre3`; resolve by adding focused fixture coverage from observed samples and preserving an unknown-type fallback if feasible.
- Whether Tabelog exposes any keyword search URL shape that simultaneously honors `area` and `keyword` for all mapped city/prefecture paths; resolve with small live probes before changing CLI behavior.

## Plan

- [x] Add regression tests for suggestion parsing with observed `MajorMunicipal` and `Genre3` payloads to produce accepted MCP response models; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_suggest.py tests/test_server.py -v`.
- [x] Update `src/gurume/server_models.py`, `src/gurume/suggest.py`, or the narrowest owning module to accept or safely normalize the observed suggestion datatypes; verified by `SuggestionDatatype = str` and focused tests.
- [x] Add a CLI regression test for `area + keyword` results that include out-of-area URLs, requiring either filtered Osaka-only output or a clear failure/warning; verified by warning and low-confidence metadata coverage in search, server, and CLI tests.
- [x] Investigate the search URL path used by `SearchClient` for `keyword` searches with mapped areas and document the chosen behavior in code or test names; verified by tests that preserve the `rst/rstsearch` keyword endpoint and by live CLI smoke.
- [x] Implement the conservative keyword-area behavior in `src/gurume/search.py` and any CLI presentation path: either enforce post-filtering by mapped area path or return a clear structured warning/error when upstream ignores area; verified by live CLI `大阪 + とんかつ定食` returning `area_filter_confidence="low"` and warnings.
- [x] Preserve `--keyword` exact cuisine auto-detection so values like `カフェ` still route through `--cuisine` and precise area paths; verified by `tests/test_cli.py`.
- [x] Update README or skill guidance only if user-facing CLI behavior changes; no docs update was needed for the existing warning-envelope behavior.
- [x] Run the focused quality gates for the touched surface; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and targeted pytest commands.

## Risks

- Tabelog can change suggestion datatypes or search URL behavior again, so tests should cover graceful handling rather than only exact current strings.
- Post-filtering keyword results may reduce result counts or hide relevant restaurants if area mapping is incomplete.
- Failing keyword searches more strictly may be a user-visible behavior change, so CLI error text must explain using `--cuisine` for supported cuisine types.

## Completion Checklist

- [x] Suggestion tools accept observed `MajorMunicipal` and `Genre3` responses, verified by focused unit tests and live MCP smoke checks.
- [x] `gurume search --area 大阪 --keyword とんかつ定食 --sort ranking --limit 10 --output json` no longer silently returns non-Osaka recommendations, verified by live CLI output with structured low-confidence warnings.
- [x] `gurume search --area 大阪 --cuisine とんかつ --sort ranking --limit 10 --output json` still returns Osaka tonkatsu restaurants, verified by live CLI output.
- [x] Existing CLI cuisine auto-detection behavior remains covered, verified by `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_cli.py -v`.
- [x] Lint, type check, and focused tests pass for the touched modules, verified by recorded command output.
