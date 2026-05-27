## Goal

Make supported cuisine ranking searches use a trustworthy Tabelog cuisine source instead of silently falling back to broad restaurant rankings.

Success means `gurume search --area 全国 --cuisine すき焼き --sort ranking --limit 10 --output json` and `tabelog_search_restaurants(area="全国", cuisine="すき焼き", sort="ranking", limit=10)` return cuisine-matching sukiyaki results from the correct ranking URL, with enough source evidence for agents to trust or reject the result set.

## Context

A live `tabelog_search_restaurants(cuisine="すき焼き", sort="ranking")` call reported `applied_filters.cuisine="すき焼き"` and `genre_code="RC0107"` but returned broad high-ranked restaurants such as sushi, Japanese cuisine, Spanish, and tempura. That makes the filter contract unsafe for recommendations.

The likely root is the no-area cuisine URL path. Current code already records that modern Tabelog cuisine filtering should prefer path-based cuisine URLs over legacy `LstG` query parameters. `build_search_url_and_params()` handles `area + cuisine` with `/{area_slug}/rstLst/{cuisine_slug}/`, but no-area cuisine searches can still fall back to `https://tabelog.com/rst/rstsearch` with `LstG`, which upstream may ignore.

## Architecture

- URL construction belongs in `src/gurume/restaurant.py` via `build_search_url_and_params()`.
- Generic search orchestration belongs in `src/gurume/search.py`.
- Cuisine names and Tabelog path segments belong in `src/gurume/genre_mapping.py`.
- CLI and MCP output contracts are in `src/gurume/cli.py`, `src/gurume/server.py`, `src/gurume/server_helpers.py`, and `src/gurume/server_models.py`.

## Non-Goals

- Do not create a custom Gurume ranking algorithm.
- Do not solve `area + keyword` confidence here; keep that in `docs/plans/2026-05-18_area-filter-confidence-plan.md`.
- Do not broaden the supported cuisine list unless live evidence shows an existing mapping is wrong.

## Unknowns

- Whether every supported cuisine has a reliable no-area path under `/rstLst/{cuisine_slug}/`; resolve with URL-builder tests plus a small opt-in live matrix.
- Whether Tabelog ranking requires `SrtT=rt` alone or also benefits from preserving `Srt=D&sort_mode=1`; resolve with a focused live probe before changing query parameters.
- Whether strict post-validation should return an error or a success with explicit low-confidence warnings when cuisine results do not match; choose the least disruptive policy after tests expose the current mismatch.

## Plan

- [x] Add URL-builder regression tests for no-area cuisine searches such as `genre_code="RC0107"` and `sort_type=SortType.RANKING` to require `https://tabelog.com/rstLst/RC0107/` instead of `https://tabelog.com/rst/rstsearch` with only `LstG`; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_search.py -v`.
- [x] Add a focused parser or search fixture for a Tabelog sukiyaki ranking page where the first results include `東京肉しゃぶ家 秀彬` and `和田金`; verified parsed names, URLs, ratings, review counts, and `すき焼き` genres with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_restaurant.py tests/test_search.py -v`.
- [x] Update `build_search_url_and_params()` so `genre_code` without `area_slug` and without `keyword` uses the cuisine path segment from `get_cuisine_slug_by_code()` and drops legacy-only `LstG`; verified with the URL-builder tests.
- [x] Preserve current keyword behavior so `keyword` searches still use the keyword search endpoint and do not accidentally combine ignored `sk` with cuisine paths; verified existing and new keyword URL tests in `tests/test_search.py`.
- [x] Add machine-readable source evidence to the search envelope, such as `source_url` and normalized request params in `SearchMeta` or the MCP output model; verified CLI JSON and MCP structured output tests assert the expected sukiyaki ranking source URL.
- [x] Add cuisine-result validation for supported cuisine searches that marks the result set low-confidence or errors when parsed top results do not match the requested cuisine terms; verified with fixture tests containing non-sukiyaki genres under `genre_code="RC0107"`.
- [x] Add or extend opt-in live integration coverage for no-area cuisine ranking with `すき焼き`, requiring at least 80% of the top 10 parsed results to include `すき焼き`; verified with `GURUME_RUN_INTEGRATION=1 UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v -s tests/integration/test_cuisine_filter.py`.
- [x] Run one live CLI and one live MCP smoke after implementation; verified `gurume search --area 全国 --cuisine すき焼き --sort ranking --limit 10 --output json` and `tabelog_search_restaurants(area="全国", cuisine="すき焼き", sort="ranking", limit=10)` no longer return broad non-sukiyaki rankings.
- [x] Not applicable: recommended cuisine-search workflow did not change, so no `skills/gurume-cli/SKILL.md` update or mirror sync was required.
- [x] Run focused quality gates for the touched surface; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/gurume/restaurant.py src/gurume/search.py src/gurume/server_helpers.py src/gurume/server_models.py src/gurume/cli.py tests`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and targeted pytest commands.

## Risks

- Tabelog may change which cuisine slugs work for no-area pages, so URL mapping tests should make failures obvious without pretending the mapping is permanent.
- Strict cuisine validation can reject legitimate fusion restaurants whose display genres do not include the exact cuisine term.
- Adding `source_url` to structured output is a user-visible API change; keep it additive and optional for existing clients.

## Completion Checklist

- [x] No-area supported cuisine searches use cuisine path URLs, verified by URL-builder tests in `tests/test_search.py`.
- [x] `全国 + すき焼き + ranking` returns sukiyaki-matching top results instead of broad restaurant rankings, verified by fixture tests and one opt-in live smoke.
- [x] Search output exposes enough source evidence for CLI and MCP callers to audit the upstream URL, verified by CLI JSON and MCP structured output tests.
- [x] Cuisine mismatch behavior is bounded and machine-readable, verified by tests with deliberately mismatched parsed genres.
- [x] Existing `area + cuisine` and `keyword` URL behaviors remain covered, verified by `tests/test_search.py`.
- [x] Lint, type check, targeted tests, and full default tests pass with recorded command output.
