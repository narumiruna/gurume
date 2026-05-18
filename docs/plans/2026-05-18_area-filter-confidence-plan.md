## Goal

Make restaurant search report area-filter reliability honestly when Gurume cannot prove that Tabelog honored the requested area.

Success means `tabelog_search_restaurants(area=..., keyword=...)` no longer presents broad or cross-prefecture results as a clean area-scoped success. The response must either use a reliable area-scoped URL path, return a clear structured warning/error, or mark area filtering as low confidence in a way MCP callers can act on.

## Context

Live usage exposed misleading search output:

- `area="大阪"` and `keyword="お好み焼き"` returned Hiroshima, Tokyo, Yamaguchi, and Osaka results while `applied_filters.area` still showed `大阪`.
- `area="四ツ橋"` and `keyword="お好み焼き"` also returned broad national results.
- `docs/MEMORY.md` already records that `sa=<area>` cannot be assumed to produce correct area filtering and that accurate filtering depends on mapped path-based area slugs.

Current flow:

- `SearchRequest._build_url_and_params` calls `get_area_slug(self.area)`.
- `build_search_url_and_params` uses path-based area pages for area-only and area+cuisine searches.
- Keyword searches intentionally stay on `https://tabelog.com/rst/rstsearch` with `sa`, `sk`, and `sw`, because prior evidence showed path pages can ignore `sk`.
- MCP search output has `warnings`, but no structured `filter_confidence`, `filter_applied`, or per-filter evidence.

## Non-Goals

- Do not implement station radius search or lat/lng ranking in this plan.
- Do not change cuisine searches that already use mapped area+cuisine paths unless tests expose a regression.
- Do not silently post-filter by restaurant display text alone unless the chosen acceptance criteria prove it is reliable.

## Unknowns

- Whether any Tabelog URL shape can reliably combine mapped area paths with keyword search for prefectures, cities, and stations; resolve with focused live probes before changing URL construction.
- Whether restaurant result URLs always provide enough area evidence for post-validation, for example `/osaka/` for Osaka prefecture; resolve with parser fixtures and live samples.

## Plan

- [ ] Add a failing regression test for keyword search with a mapped area where returned restaurant URLs include a different prefecture path; require a structured low-confidence warning/error instead of clean success; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_search.py tests/test_server.py -v`.
- [ ] Add URL-building tests that document current keyword behavior for `area + keyword` and why it differs from `area + cuisine`; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_search.py -v`.
- [ ] Design a minimal filter reliability model in `src/gurume/search.py` or `src/gurume/server_models.py`, such as `area_filter_applied`, `area_filter_confidence`, and `area_filter_reason`; verify the design by updating MCP output tests in `tests/test_server.py`.
- [ ] Implement area evidence detection for mapped prefecture/city paths using restaurant URLs where possible, without relying only on display-area text; verify with fixtures containing `/osaka/`, `/hiroshima/`, and `/tokyo/` restaurant URLs.
- [ ] Update `src/gurume/server_helpers.py` so MCP callers receive actionable guidance when area confidence is low, for example "area parameter was passed through Tabelog keyword search but parsed results do not match the mapped area"; verify with `tests/test_server.py`.
- [ ] Decide the conservative behavior for low-confidence area keyword searches: return `success` with explicit low-confidence metadata, or return `error`/`no_results` when most results are out of area; verify the chosen behavior with a test name that states the policy.
- [ ] Run one live smoke check for the observed failure after implementation: `tabelog_search_restaurants(area="大阪", keyword="お好み焼き", sort="ranking", limit=10)` must not look like a trustworthy Osaka-only result set if non-Osaka URLs are returned; record the output summary in the PR or completion notes.
- [ ] Run focused quality gates for search and MCP output surfaces; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/gurume/search.py src/gurume/restaurant.py src/gurume/server_helpers.py src/gurume/server_models.py tests/test_search.py tests/test_server.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and the targeted pytest commands above.

## Risks

- Returning warnings instead of filtering may still require caller discipline, but it avoids hiding relevant results with a weak local heuristic.
- Returning errors for low-confidence area keyword searches is safer but may break existing callers that expect best-effort keyword results.
- URL-based validation works well for prefecture slugs but may not prove station-level areas such as `四ツ橋`.

## Completion Checklist

- [ ] `area + keyword` searches cannot silently report cross-prefecture results as a clean area-scoped success, verified by regression tests in `tests/test_search.py` or `tests/test_server.py`.
- [ ] MCP search output exposes machine-readable area filter confidence or an equivalent structured error, verified by `tests/test_server.py`.
- [ ] Existing mapped `area + cuisine` searches still use precise area+cuisine paths, verified by URL-building tests in `tests/test_search.py`.
- [ ] The observed Osaka okonomiyaki failure mode is covered by either a live smoke result summary or a representative fixture test with non-Osaka result URLs.
- [ ] Lint, type check, and focused tests pass for search and MCP output modules, verified by recorded command output.
