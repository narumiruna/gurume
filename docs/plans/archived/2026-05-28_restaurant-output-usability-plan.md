## Goal

Make Gurume restaurant outputs useful enough for recommendations without requiring agents to fetch raw Tabelog HTML for ordinary fields.

Success means search results include available lunch and dinner price ranges, and detail requests can fetch basic restaurant information even when reviews, menu items, and courses are not requested.

## Context

During the sukiyaki lookup, Gurume search returned names, ratings, review counts, areas, genres, and URLs, but `lunch_price` and `dinner_price` were `null` even when the Tabelog ranking page showed price ranges in each result card.

The detail tool also rejected a basic-info-only request when `fetch_reviews=false`, `fetch_menu=false`, and `fetch_courses=false`, even though `RestaurantDetailRequest.fetch()` already fetches and parses the base restaurant page before optional subpages. That forced the caller to request an unrelated optional section just to get address, station, phone, business hours, closed days, and price fields.

## Architecture

- Search-card parsing belongs in `src/gurume/restaurant.py`.
- Detail base-page parsing belongs in `src/gurume/detail.py`.
- MCP detail validation and output shaping belong in `src/gurume/server_helpers.py`, `src/gurume/server.py`, and `src/gurume/server_models.py`.
- CLI and TUI should continue to consume `Restaurant.lunch_price` and `Restaurant.dinner_price` without adding separate display-only fields.

## Non-Goals

- Do not redesign course or menu parsing; optional menu/course 404 behavior is already covered by prior work.
- Do not add a separate recommendation scoring layer.
- Do not make live network calls part of default test runs.

## Unknowns

- Resolved: current ranking list prices are available through `.list-rst__info` / `.c-rating-v3__val` blocks with `夜` / `昼` labels and lunch/dinner class markers; fixture tests cover both shapes.
- Resolved: MCP does not need a new `fetch_basic` parameter. A valid detail URL can set all optional fetch flags to false and still fetch the base restaurant page.

## Plan

- [x] Add search-card HTML fixtures that include current `.list-rst__info` / `.c-rating-v3__val` price markup from ranking pages; verified expected `lunch_price` and `dinner_price` with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_restaurant.py tests/test_search.py -v`.
- [x] Update `RestaurantSearchRequest._parse_prices()` with defensive selectors for current desktop list markup while keeping existing fallback behavior; verified existing price parser tests still pass.
- [x] Add CLI JSON and MCP output tests proving parsed price fields survive serialization in `RestaurantOutput`; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_cli.py tests/test_server.py -v`.
- [x] Add server validation tests for `tabelog_get_restaurant_details(..., fetch_reviews=false, fetch_menu=false, fetch_courses=false)` expecting a successful basic-info response instead of `invalid_parameters`; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py -v`.
- [x] Relax `_validate_detail_params()` so a valid Tabelog URL can request only the base restaurant page, and update the invalid-parameter suggested action to stop requiring an optional section; verified with the new server tests.
- [x] Add sync and async detail request tests showing all optional fetch flags false causes only the base URL to be fetched and still returns address, station, phone, business hours, closed days, and budget fields; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_detail.py -v`.
- [x] Keep `review_count`, `menu_item_count`, and `course_count` semantics clear when optional sections are not fetched, for example counts remain zero and the boolean fetch flags show what was skipped; verified with `tests/test_server.py`.
- [x] Update MCP docs or tool descriptions only if the public detail workflow changes; verified references with `rg -n "fetch_reviews|fetch_menu|fetch_courses|basic" README.md docs src/gurume` and updated `README.md` plus tool descriptions.
- [x] Run one opt-in live smoke for a known sukiyaki ranking result and one detail basic-only call; verified search prices and detail basic fields for `東京肉しゃぶ家 秀彬`.
- [x] Run focused quality gates for the touched surface; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/gurume/restaurant.py src/gurume/detail.py src/gurume/server.py src/gurume/server_helpers.py src/gurume/server_models.py tests`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and the targeted pytest commands above.

## Risks

- Tabelog price markup can drift, so parser tests should cover current selectors and preserve graceful `None` values when price elements are absent.
- Allowing basic-only detail calls may surprise clients that assumed at least one optional section was always fetched; output booleans must make skipped sections explicit.
- Search result prices may differ from detail-page budgets; do not normalize or merge them unless a separate evidence-backed plan covers that behavior.

## Completion Checklist

- [x] Search result price ranges are parsed from current list-card markup, verified by fixture tests in `tests/test_restaurant.py` and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_restaurant.py tests/test_search.py -v`.
- [x] CLI JSON, MCP search output, and TUI-facing `Restaurant` fields expose non-null prices when upstream markup contains them, verified by `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_cli.py tests/test_server.py -v`.
- [x] Detail basic-only requests succeed without fetching reviews, menus, or courses, verified by server and detail request tests.
- [x] Detail output clearly reports skipped optional sections with fetch booleans and zero counts, verified by `tests/test_server.py`.
- [x] One live smoke confirms search prices and basic detail fields for a real Tabelog restaurant: search returned lunch `￥15,000～￥19,999` and dinner `￥40,000～￥49,999`; basic-only detail returned base fields with zero reviews, menu items, and courses.
- [x] Lint, type check, and focused tests pass with recorded command output; full suite also passed with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -v` (`318 passed, 4 skipped`).
