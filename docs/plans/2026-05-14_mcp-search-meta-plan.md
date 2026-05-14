## Goal

Make MCP search metadata match the parsed search result page closely enough for pagination decisions.

Success condition: MCP responses do not report impossible metadata such as `total_count=1` while returning 5 or more items from a page, and `has_more` reflects actual pagination when Tabelog exposes it.

## Context

Live MCP checks on 2026-05-14 showed cuisine searches returning valid restaurant lists while metadata was inconsistent:

- `area="三重県", cuisine="すき焼き", limit=5` returned 5 restaurants but `meta.total_count=1`.
- `area="東京都", cuisine="すき焼き", limit=5` returned 5 restaurants but `meta.total_count=1`.
- `area="札幌", cuisine="ラーメン", limit=5` returned 5 restaurants but `meta.total_count=1`.
- `page=2` for Tokyo sushi returned valid page 2 restaurants but metadata implied only 2 pages and `has_more=false`, which needs verification against current Tabelog markup.

Relevant files:

- `src/gurume/search.py`: `_parse_meta()` and `_update_meta()`.
- `src/gurume/server_helpers.py`: `_to_search_meta_output()` and `has_more` mapping.
- `tests/test_search.py`, `tests/test_server.py`: metadata coverage.

## Non-Goals

- Do not make live Tabelog tests mandatory in the default test suite.
- Do not guarantee exact total counts when Tabelog hides or changes counts; prefer honest `None` or conservative pagination flags over false precision if needed.

## Unknowns

- Which current Tabelog markup element is the reliable source for result counts and next-page links.
- Whether some cuisine pages intentionally display ranking position/count text that is not total result count.

## Plan

- [ ] Capture representative HTML snippets for `東京都 + すき焼き`, `三重県 + すき焼き`, `札幌 + ラーメン`, and `東京都 + 寿司 page=2`; verify by saving sanitized snippets as test fixtures or documenting exact selectors in the plan.
- [ ] Inspect current pagination and count markup to identify reliable selectors for total count, current page, next page, and result item count; verify with a small parser experiment using `uv run python`.
- [ ] Update `SearchMeta` fields if exact total count can be absent, or adjust `_parse_meta()` to avoid returning false totals; verify with type checks and focused parser tests.
- [ ] Add fixture-based tests in `tests/test_search.py` for the captured count/pagination cases; verify `returned_count <= results_per_page`, `total_count >= returned_count` when total count is present, and `has_next_page` follows next-page markup.
- [ ] Update `server_helpers.py` if `has_more` should use a conservative fallback when metadata is partial; verify with `tests/test_server.py`.
- [ ] Run `uv run ruff check .`, `uv run ty check .`, and `uv run pytest tests/test_search.py tests/test_server.py -v`.
- [ ] Run live MCP checks for the three known inconsistent queries and record the corrected metadata values in the completion evidence.

## Risks

- Tabelog may omit total counts on some result pages; forcing an integer can keep producing misleading metadata.
- Parser fixes based only on one cuisine page may fail on station, keyword, or reservation pages.

## Completion Checklist

- [ ] MCP no longer reports `total_count` lower than `returned_count` for the known live queries, verified by live MCP output.
- [ ] Search metadata parser has fixture coverage for count and pagination markup, verified by `uv run pytest tests/test_search.py -v`.
- [ ] MCP `has_more` behavior is covered by server tests, verified by `uv run pytest tests/test_server.py -v`.
- [ ] Quality gates pass, verified by `uv run ruff check .`, `uv run ty check .`, and the focused pytest commands.
