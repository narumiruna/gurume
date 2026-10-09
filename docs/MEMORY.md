## GOTCHA
- `ty` is stricter than Ruff: for timezone constants, use `from datetime import UTC` and pass it to `datetime.now(UTC)`; for parsers over different dataclasses such as area/keyword, use separate typed helpers to avoid union returns that fail type checking.
- Tenacity `RetryCallState.outcome` is `Future | None`; guard both `outcome` and `outcome.exception()` before logging retry exception details.
- `docs/MEMORY.md`, `docs/LOG.md`, and `docs/BACKLOG.md` are the canonical project docs; do not recreate root-level copies.
- User-facing project docs should live under `docs/`; if a root-level guide is moved there, update README links instead of leaving a duplicate at the repo root.
- FastMCP exposes `Annotated[..., Field(...)]` constraints in MCP schemas, but direct Python calls to the tool function still need manual validation if tests or local callers bypass the protocol layer.
- When `ty` checks Pydantic model construction across modules, coerce `str` values to `HttpUrl` and cast narrow `Literal` fields explicitly instead of relying on runtime validation.
- If project code imports a package directly, declare it in `pyproject.toml` even when another dependency currently pulls it in transitively; `ty` resolves against the project environment and can flag unresolved imports in fresh or mismatched environments.
- Tabelog markup changes without warning; CSS selectors and HTML structures are not stable contracts. Write parsing logic defensively and skip malformed items gracefully while keeping failures debuggable.
- Current Tabelog ranking cards can expose lunch/dinner prices under `.list-rst__info` / `.c-rating-v3__val`, with `夜` / `昼` text or `dinner` / `lunch` class markers indicating meal period.
- Do not assume `sa=<area>` query parameters produce correct area filtering. Accurate prefecture-level filtering depends on path-based area slugs such as `/tokyo/rstLst/`; unmapped areas may fall back to broader results.
- Cuisine searches should prefer genre-code-based URL paths over plain keyword matching. Use `genre_mapping.py` to keep cuisine filtering precise before adding ad hoc matching logic.
- Tabelog prefecture cuisine pages no longer honor the legacy `LstG` query alone; build area+cuisine searches from mapped `/AREA/rstLst/<segment>/` paths, where `<segment>` may be a slug like `yakiniku` or a category token like `RC0107` / `MC0101`.
- No-area and `全国` cuisine ranking searches also need path-based URLs such as `/rstLst/RC0107/`; do not rely on `rst/rstsearch` plus `LstG` for supported cuisine filters.
- Major city searches may need nested Tabelog area paths instead of prefecture slugs, for example `札幌 -> hokkaido/A0101`, `名古屋 -> aichi/A2301`, and `神戸 -> hyogo/A2801`.
- Suggestion endpoints and detail pages are upstream-controlled and may change response shape; preserve defensive parsing and actionable error messages when touching these flows.
- Tabelog area suggestions may return `datatype="Town"`; keep MCP `SuggestionDatatype` aligned with upstream values or FastMCP structured output validation will fail before returning an envelope.
- Live Tabelog integration tests can return empty results under the default sandbox network; rerun `GURUME_RUN_INTEGRATION=1 uv run pytest -v -s tests/integration/test_cuisine_filter.py` with network access before treating empty live results as a regression.
- MCP live checks can pass cuisine filtering while still hiding regressions: keyword search on mapped area paths may be ignored upstream, search meta can disagree with parsed results, and detail `fetch_menu` / course parsing can fail or return empty after Tabelog markup or URL changes.
- Tabelog search count markup may expose visible range numbers before the real total, for example `.c-page-count__num` values `1`, `20`, then the total after `全`; parse the final number in `.c-page-count` and use `a[rel="next"]` for pagination.
- Tabelog path-based result pages such as `/tokyo/rstLst/` and cuisine pages may ignore `sk=<keyword>`; keyword searches should use the search endpoint with `sa`, `sk`, and `sw`, and MCP should reject `keyword + cuisine` unless live evidence proves both filters are honored.
- For mapped area keyword searches, `area_filter_confidence` is URL-based and is high only when every parsed restaurant URL starts with the mapped Tabelog area path; mixed-prefecture URLs must stay low-confidence.
- Detail menu pages are optional: some restaurants return 404 for `/dtlmenu/` while `/party/` has current course data in `.rstdtl-course-list`; treat optional menu/course 404s as empty sections and parse `/party/` courses from current selectors.
- CLI keyword auto-detection is a special case: when `--keyword` exactly matches a supported cuisine, clear the keyword and search as area+cuisine so city paths like `/hyogo/A2801/rstLst/cafe/` are used.
- Keep CLI skill guidance and MCP behavior aligned for `area + keyword`: Tabelog can return broad cross-prefecture results, and MCP suggestion `Genre2` values are only valid as `cuisine` when present in `tabelog_list_cuisines`; otherwise preserve upstream datatypes like `Genre3` / `MajorMunicipal` and warn or filter by URL evidence before presenting area-scoped recommendations.
- Tabelog homepage, search paths, and suggestion API currently return Cloudflare headers (`server: cloudflare`, `cf-ray`) and set `__cf_bm`; keep `curl_cffi` as the scraping baseline, but do not assume it bypasses every Cloudflare challenge.
- Tabelog Cloudflare currently rejects `curl_cffi`'s Chrome impersonation with HTTP 403 while Safari succeeds; default to Safari and use `GURUME_IMPERSONATE` for process-startup overrides.
- `skills/gurume-cli/` is the external installer source, while `.codex/skills/gurume-cli/` is a local ignored Codex CLI runtime mirror. Edit `skills/` first, then run `uv run python scripts/sync_skills.py` and verify with `uv run python scripts/sync_skills.py --check`.
- Tabelog area suggestions expose names, datatypes, and IDs, but not reliable URL paths; expand `area_catalog.json` from verified Tabelog path URLs, not suggestion IDs alone.
- Tabelog leaf subareas can be snapshotted from `#js-leftnavi-area-scroll`: prefecture pages expose parent paths and parent pages expose leaf paths. The leaf name `山形` is intentionally shadowed by the legacy prefecture-prefix lookup; use the `山形市` alias for the leaf path.
- Restaurant output projection must keep CLI `json-list` URLs raw while MCP uses `_as_http_url`; validating the URL before the Pydantic restaurant model also preserves existing invalid-URL error text.
- MCP output conversion intentionally runs outside the caught request operation; keep malformed-output errors and cancellation propagating rather than converting them into request-error envelopes.
- `mcp` 2.x removes `mcp.server.fastmcp.FastMCP`; keep the 1.x upper bound until the server and MCP tests migrate to `MCPServer`.
- Live MCP checks on 2026-10-05: Tabelog's Cloudflare returns 403 for restaurant search and detail pages even with Safari impersonation while homepage and suggestion API work; preserve HTTP status from `SearchResponse` instead of parsing error text, and classify both search and detail 403 as non-retryable `upstream_unavailable`.
- TUI search receives `SearchResponse(status=ERROR)` without an exception; check the status and clear prior rows, `self.restaurants`, and selection or failures appear as "No restaurants found" or leave stale results. Keep CLI/TUI text and core validation exceptions in English; Japanese restaurant data and user input may still appear in results.

- Raw live probe with `curl_cffi 0.16.3` and Safari on 2026-10-05: homepage returns 200, but `/mie/rstLst/yakitori/?SrtT=rt` returns 403 with `cf-mitigated: challenge` and a `Just a moment...` page; this is a Cloudflare challenge, not a restaurant parser failure.

- Follow-up live checks on 2026-10-05: Chrome and Firefox profiles also hit the Mie ranking challenge; a Safari Session retaining homepage cookies (including `__cf_bm`) still returns 403. Installed `curl_cffi 0.16.3` matches the latest PyPI release; Chrome DevTools checks are blocked by `Target closed`, so actual browser access remains unverified.

- Homepage `commons.js` appends suggestion IDs/types (`area_datatype`, `area_id`, `key_datatype`, `key_id`, `sa_input`) to GET `/rst/rstsearch/`; this may affect normalization, not the Cloudflare challenge on mapped rankings. `/internal_api/rst_search` is used by a restaurant-link modal, not a verified ranking API. See `docs/tabelog-javascript-research.md`.

- Live check on 2026-10-09: headed Chromium via Chrome DevTools MCP returns 200 for national/Mie yakitori rankings and a detail page while Safari curl_cffi returns challenge 403 on the same URLs; existing parsers consume browser document HTML. Profile/session effects are uncontrolled; do not assume disabling headless alone fixes access. See `docs/tabelog-browser-research.md`.

- Headed map Network inspection on 2026-10-09 found `GET /xml/rstmap`: structured restaurant XML and pagination also return 200 with Safari curl_cffi without browser cookies. It uses geographic bounds and legacy map genre fields, not exact prefecture ranking: the Mie viewport included Aichi and total 271 versus ranking 241. See `docs/tabelog-api-research.md`; do not silently replace ranking semantics.

- `gurume map-search` / `tabelog_search_map_restaurants` use explicit rectangles, fixed upstream pages of 20, and only verified yakitori map categories. `limit` truncates the current page, raw map budgets are not lunch/dinner fields, and XML DTD/entity declarations must be rejected before ElementTree parsing.

- Typer/Rich help can insert ANSI styles inside flag names when CI forces color; strip SGR sequences before help text assertions and test both `FORCE_COLOR=0` and `FORCE_COLOR=1`.

- Python booleans pass numeric checks; reject them explicitly for map bounds and use strict float/int MCP fields to prevent coordinate/pagination coercion before core validation. Check cuisine type before stripping so invalid direct input stays a parameter error. Render review counts using `is not None` so zero stays distinct from missing data.

- Map XML markers need request-rectangle checks in addition to global coordinate ranges; reject empty pages whenever their fixed offset still leaves reported results, not only on page 1; allow empty pages at or beyond the total. Normalize invalid caller limits before constructing a typed error envelope so validation itself cannot mask the original error.

- Both observed map XML pages (40 markers) contain the exact `焼き鳥` genre token. Match that verified label when validating markers, not a substring or an invented alias; retain raw prefecture codes/coordinates in the default map table instead of presenting missing named areas.

- Validate raw map marker counts against the total remaining after the fixed page offset, and restrict all numeric restaurant-path segments to ASCII digits. Reuse `retry.is_retryable_error` for upstream error metadata; treating every HTTP error as retryable incorrectly includes 404/410.

- Map `nextpg`/`prevpg` are optional UI labels, not authoritative flags. Derive next from global total and fixed page size, previous navigation from page > 1; preserve `has_more` for local truncation even on the final page.

## TASTE
- To reduce Ruff complexity, prefer adding private helpers inside the existing module to split the flow before reaching for new files or new abstractions.
