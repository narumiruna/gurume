## Goal

Make MCP restaurant detail fetching resilient when menu or course pages are missing or when Tabelog uses the current `/party/` menu/course page.

Success condition: `tabelog_get_restaurant_details()` default options do not fail an otherwise valid restaurant detail request just because `/dtlmenu/` returns 404, and course parsing returns structured course data from a known `/party/` page.

## Context

Live MCP checks on 2026-05-14 showed:

- `tabelog_get_restaurant_details("https://tabelog.com/tokyo/A1302/A130204/13003043/")` failed because `fetch_menu=true` requested `/dtlmenu/`, which returned 404.
- The same restaurant succeeded with `fetch_menu=false, fetch_courses=true`, but `course_count=0` even though the `/party/` page lists multiple courses.
- The public Tabelog page links `メニュー・コース` to `/party/`, while older code still treats `/dtlmenu/` as the menu page.

Relevant files:

- `src/gurume/detail.py`: `RestaurantDetailRequest.fetch()` / `fetch_sync()`, `_parse_menu_items()`, `_parse_courses()`.
- `src/gurume/server.py`: MCP detail tool defaults and error mapping.
- `src/gurume/server_helpers.py`: detail output construction.
- `tests/test_detail.py`, `tests/test_server.py`: detail and MCP coverage.

## Non-Goals

- Do not scrape every menu subtab or photo-only menu page in this plan.
- Do not change the public output schema unless a field becomes impossible to represent accurately.
- Do not make live Tabelog detail tests part of the default test suite.

## Unknowns

- Whether `/dtlmenu/` is gone globally or only absent for some restaurants.
- Whether menu items and courses should both come from `/party/`, or whether menu-only pages have another current URL.

## Plan

- [x] Reproduce detail failures for `和田金` and `すき焼割烹 日山` with MCP and direct `RestaurantDetailRequest`; verify by recording which subrequest URL returns 404 and which options still succeed. Evidence: 日山 default detail fetched main/reviews, got `/dtlmenu/` 404, then `/party/` 200.
- [x] Inspect current Tabelog links on known detail pages to identify menu/course URL candidates such as `/party/`; verify by opening the linked page and confirming visible course/menu entries. Evidence: 日山 page links `メニュー・コース` to `/party/`, where `.rstdtl-course-list` entries contain course names, prices, and item counts.
- [x] Change detail subpage fetching so optional menu/course pages that return 404 do not fail the entire detail request; verify with unit tests that main restaurant data still returns and missing optional sections are empty.
- [x] Update course parsing for current `/party/` markup to extract course name, price, description when available, and item count/text when available; verify with fixture-based tests in `tests/test_detail.py`.
- [x] Decide whether `fetch_menu=true` should fetch `/party/`, skip unsupported menu tabs, or return a warning field through MCP; verify the chosen behavior in `tests/test_server.py`. Decision: keep `fetch_menu=true` on `/dtlmenu/` for menu items, but treat 404 as an empty optional section; `fetch_courses=true` owns `/party/`.
- [x] Update MCP detail error classification so optional subpage misses are not reported as `internal_error`; verify with server tests for 404 optional pages and true main-page failures. The request layer now converts optional menu/course 404s into empty sections before the MCP wrapper sees them.
- [x] Run `uv run ruff check .`, `uv run ty check .`, and `uv run pytest tests/test_detail.py tests/test_server.py -v`.
- [x] Run final live MCP checks for 日山 and 和田金 with default options and with `fetch_courses=true`; verify successful status and nonzero course count when the live page has courses. Evidence: 日山 default MCP detail returned success with `course_count=19`; direct 和田金 detail returned `course_count=8`.

## Risks

- Tabelog course markup may differ between restaurants with online reservations and restaurants without them.
- Suppressing optional subpage failures could hide real parser regressions unless warnings or tests distinguish missing pages from malformed pages.

## Completion Checklist

- [x] Default MCP detail fetch for a valid restaurant no longer fails on `/dtlmenu/` 404, verified by live MCP output.
- [x] Known `/party/` course page returns at least one structured course in tests and live smoke checks, verified by `tests/test_detail.py` and MCP output.
- [x] Optional detail subpage failures are represented without `internal_error`, verified by `tests/test_detail.py` and live MCP output.
- [x] Quality gates pass, verified by `uv run ruff check .`, `uv run ty check .`, and focused pytest commands.
