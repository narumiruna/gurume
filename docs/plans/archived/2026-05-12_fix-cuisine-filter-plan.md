# Fix Cuisine Filter Regression

## Goal

Restore working cuisine filtering for `gurume search --cuisine <name>` (and the equivalent MCP / TUI paths) so that returned restaurants actually match the requested cuisine. Success condition: for at least three representative cuisines (`ラーメン`, `すき焼き`, `焼肉`) in at least two areas (`東京`, `大阪`), ≥80% of the top 10 results have the cuisine in their `genres` field, verified by an integration test that hits real Tabelog.

## Context

Manual testing on `main` (`afcf128`) showed `--cuisine` is silently broken:

- `gurume search --area 東京 --cuisine ラーメン --limit 3` returned `アカ` (スペイン料理), `新ばし 星野` (日本料理), `日本橋蛎殻町 すぎた` (寿司).
- Same pattern for `三重 すき焼き` and `大阪 焼肉`: results are the area's overall top-rated restaurants, not cuisine-filtered.

Curl probes against Tabelog confirmed the upstream URL contract changed:

| URL we send today                                     | Result                                                                |
| ----------------------------------------------------- | --------------------------------------------------------------------- |
| `/tokyo/rstLst/?LstG=RC0501&SrtT=rt`                  | 200, title `東京のおすすめのグルメ情報 ランキング` — `LstG` ignored. |
| `/tokyo/rstLst/RC0501/` (path-based RC code)          | 200 but results are Italian / yakiniku / yakitori (still not filtered). |
| `/tokyo/rstLst/ramen/` (English slug)                 | 200 but returns Chinese restaurants.                                  |
| `/rst/rstsearch/?sa=東京&LstG=RC0501&SrtT=rt`         | 400.                                                                  |

All known URL shapes the current code or obvious alternatives produce are now broken or wrong. The correct URL is unknown.

256 unit tests pass because every test mocks the HTTP boundary; no integration check exercises the area-plus-cuisine path against the real site.

`build_search_url_and_params` (`src/gurume/restaurant.py:33`) is the single chokepoint; both sync (`restaurant.py:413`) and async (`restaurant.py:454`, `search.py:240`) callers go through it.

## Unknowns

- **What URL shape does Tabelog now expect for cuisine filtering inside an area?** Candidates to probe: `/tokyo/rstLst/ramen/RC0501/`, `/tokyo/ramen/rstLst/`, `/tokyo/rstLst/?SrtT=rt&LstRange=…`, cuisine subdomain (`tabelog.com/ramen/tokyo/`), or a form-POST endpoint. The first plan step resolves this.
- **Does each cuisine need a per-cuisine English slug** (e.g. `ramen`, `sushi`, `yakiniku`) **in addition to the existing `RC` code?** If yes, the answer extends `genre_mapping.py`.

## Non-Goals

- Reverse-engineering pagination, reservation filters, or sort options that this regression does not touch.
- Adding offline cuisine inference from `genres` strings as a fallback — if the URL cannot be fixed, surface the failure instead of pretending it works.

## Plan

- [x] Not applicable: separate browser-click discovery was superseded by successful live verification against Tabelog (`GURUME_RUN_INTEGRATION=1 uv run pytest -m integration tests/integration/test_cuisine_filter.py -v`) plus direct CLI validation (`uv run gurume search --area 東京 --cuisine ラーメン --limit 10 --output json`), which proved the implemented URL mapping returns cuisine-matching results.
- [x] Not applicable: a standalone `curl` probe was not required once the live pytest integration checks and direct CLI run both succeeded against real Tabelog and validated the returned cuisines end to end.
- [x] Update `build_search_url_and_params` in `src/gurume/restaurant.py` to emit the discovered URL shape for the `(area_slug, genre_code)` case; verify with a focused unit test asserting the exact URL string for `(tokyo, RC0501)` and `(osaka, RC1501)`.
- [x] If discovery shows cuisines need an English slug in addition to `RC` codes, extend `genre_mapping.py` with a `cuisine_slug` lookup and a unit test covering all 29 entries (no None / no duplicate slugs); otherwise mark this task `Not applicable`.
- [x] Add an opt-in integration test under `tests/integration/test_cuisine_filter.py` that hits real Tabelog for (`東京`, `ラーメン`), (`大阪`, `焼肉`), (`三重`, `すき焼き`) and asserts ≥80% of top 10 results have the cuisine name in `genres`. Mark it with `@pytest.mark.integration` and skip by default; verify with `GURUME_RUN_INTEGRATION=1 uv run pytest -m integration tests/integration/test_cuisine_filter.py -v` passing locally.
- [x] Append one bullet to `docs/MEMORY.md` `## GOTCHA` summarizing the URL-format change and the fix; verify with `tail -n 20 docs/MEMORY.md` showing the new entry.
- [x] Append one line to `docs/LOG.md`; verify with `tail -1 docs/LOG.md`.
- [x] Run `uv run ruff check .`, `uv run ty check .`, and `uv run pytest --cov=src tests`; verify each exits 0 and the existing 256 tests still pass.
- [x] Not applicable: PR creation and merge were accepted by the user as follow-up workflow outside this implementation plan, after the code change, live integration verification, and CLI verification were completed.

## Risks

- **Tabelog blocks repeated programmatic discovery.** Mitigation: throttle manual curl checks; do the bulk of URL discovery in a single browser session and copy the result rather than scripting many requests.
- **Different cuisines use different URL shapes.** Mitigation: discovery covers three diverse cuisines; if shapes diverge, the integration test will catch it on the second cuisine and the plan loops back to discovery.
- **The fix lands but Tabelog changes again.** The integration test makes this loud rather than silent. We do not block CI on it (opt-in marker), but a maintainer running it before a release will notice.

## Completion Checklist

- [x] `gurume search --area 東京 --cuisine ラーメン --limit 10 --output json` returns ≥8 results whose `genres` include ラーメン or a ramen-adjacent label, verified by running the command and counting matches.
- [x] `tests/integration/test_cuisine_filter.py` exists, is marked `@pytest.mark.integration`, and passes locally for the three cuisine/area pairs, verified by `GURUME_RUN_INTEGRATION=1 uv run pytest -m integration tests/integration/test_cuisine_filter.py -v`.
- [x] `uv run ruff check .`, `uv run ty check .`, and `uv run pytest --cov=src tests` all pass (existing 256 unit tests still green), verified by their exit codes and the pytest summary.
- [x] `docs/MEMORY.md` records the Tabelog URL-format change under `## GOTCHA`, verified by `rg -n "LstG|cuisine URL" docs/MEMORY.md` returning the new entry.
- [x] PR handoff is explicitly accepted as out of scope for this plan by user approval in chat after implementation and verification were completed.
