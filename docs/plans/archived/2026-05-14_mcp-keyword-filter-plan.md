## Goal

Make MCP keyword searches apply the requested keyword instead of returning broad area rankings.

Success condition: `tabelog_search_restaurants(area="東京都", keyword="今半")` returns restaurants matching `今半`, and `keyword` combined with `cuisine` either narrows results as documented or returns a clear warning/error that the combination is unsupported.

## Context

Live MCP checks on 2026-05-14 showed that `area="東京都", keyword="今半"` and `area="東京", keyword="すき焼き"` returned general Tokyo ranking results such as Spanish, Japanese, and sushi restaurants. The MCP warning says `keyword + cuisine` narrows results, but `area="東京都", keyword="今半", cuisine="すき焼き"` returned the same broad sukiyaki ranking and did not narrow to `今半`.

Relevant files:

- `src/gurume/server.py`: MCP tool input handling.
- `src/gurume/search.py`: `SearchRequest` URL/params construction.
- `src/gurume/restaurant.py`: `build_search_url_and_params()` and basic params.
- `src/gurume/area_mapping.py`: area path mapping.
- `tests/test_server.py`, `tests/test_search.py`, `tests/test_restaurant.py`: expected coverage points.

## Non-Goals

- Do not redesign the whole search API.
- Do not add browser rendering or JavaScript execution.
- Do not expand all possible Japanese area mappings in this plan.

## Unknowns

- Which Tabelog URL shape currently preserves both mapped area paths and `sk=<keyword>` filtering.
- Whether `keyword + cuisine` is supported by Tabelog for path-based cuisine URLs or should be rejected by Gurume as misleading.

## Plan

- [x] Reproduce the MCP keyword issue with a small live probe for `東京都 + 今半`, `東京 + すき焼き`, and `東京都 + 今半 + すき焼き`; verify by recording URL, params, top 5 names, and top 5 genres in this plan or a linked issue note.
- [x] Probe candidate Tabelog URL shapes for area keyword filtering, including `/tokyo/rstLst/?sk=今半`, `/rst/rstsearch?sa=東京都&sk=今半`, and any current form-derived URL; verify by checking that top results contain `今半` or the requested keyword. Evidence: path-based `/tokyo/rstLst/?sk=今半` returned broad ranking, while `rst/rstsearch` with `sa`, `sk`, and `sw` redirected to keyword-filtered results.
- [x] Update `build_search_url_and_params()` or `SearchRequest._build_url_and_params()` so mapped area + keyword requests preserve keyword filtering; verify with focused tests in `tests/test_search.py` or `tests/test_restaurant.py` asserting exact URL and params.
- [x] Decide and encode `keyword + cuisine` behavior: either keep both filters only when live probing proves Tabelog honors both, or return an MCP warning/error when the combination would be ignored; verify with `tests/test_server.py`. Decision: MCP rejects `keyword + cuisine` because path-based cuisine pages ignore `sk`, and search-endpoint genre filtering was not reliable enough to claim both filters are honored.
- [x] Update MCP warnings in `server_helpers.py` so they describe the actual supported behavior; verify with server unit tests that warning text changes only for affected cases.
- [x] Run `uv run ruff check .`, `uv run ty check .`, and `uv run pytest tests/test_server.py tests/test_search.py tests/test_restaurant.py -v` after implementation.
- [x] Run a final live MCP smoke check for `東京都 + 今半` and `東京都 + 今半 + すき焼き`; verify the returned restaurants match the selected behavior. Evidence used local branch code: `東京都 + 今半` returned `人形町今半 本店`, `代々木 今半`, `人形町今半 上野広小路店`, `人形町今半 銀座店`, and `今半 別館`; `東京都 + 今半 + すき焼き` returned structured `invalid_parameters`.

## Risks

- Tabelog may ignore `sk` on some path-based pages while still returning HTTP 200, so tests must assert URL/params and use live smoke results as evidence instead of trusting success status.
- Combining keyword and cuisine may reduce recall or behave inconsistently across regions; rejecting unsupported combinations may be more honest than returning broad results.

## Completion Checklist

- [x] MCP keyword-only search no longer returns broad Tokyo ranking for `東京都 + 今半`, verified by live MCP output.
- [x] `keyword + cuisine` behavior is explicitly supported or explicitly rejected, verified by `tests/test_server.py` and live MCP output.
- [x] URL/params construction for mapped area + keyword is covered by unit tests, verified by `uv run pytest tests/test_search.py tests/test_restaurant.py -v`.
- [x] Quality gates pass, verified by `uv run ruff check .`, `uv run ty check .`, and the focused pytest command.
