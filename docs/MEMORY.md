## GOTCHA
- `ty` is stricter than Ruff: for timezone constants, use `from datetime import UTC` and pass it to `datetime.now(UTC)`; for parsers over different dataclasses such as area/keyword, use separate typed helpers to avoid union returns that fail type checking.
- `docs/MEMORY.md` and `docs/CHANGELOG.md` are the canonical project docs; do not recreate root-level copies.
- User-facing project docs should live under `docs/`; if a root-level guide is moved there, update README links instead of leaving a duplicate at the repo root.
- FastMCP exposes `Annotated[..., Field(...)]` constraints in MCP schemas, but direct Python calls to the tool function still need manual validation if tests or local callers bypass the protocol layer.
- When `ty` checks Pydantic model construction across modules, coerce `str` values to `HttpUrl` and cast narrow `Literal` fields explicitly instead of relying on runtime validation.
- If project code imports a package directly, declare it in `pyproject.toml` even when another dependency currently pulls it in transitively; `ty` resolves against the project environment and can flag unresolved imports in fresh or mismatched environments.
- Tabelog markup changes without warning; CSS selectors and HTML structures are not stable contracts. Write parsing logic defensively and skip malformed items gracefully while keeping failures debuggable.
- Do not assume `sa=<area>` query parameters produce correct area filtering. Accurate prefecture-level filtering depends on path-based area slugs such as `/tokyo/rstLst/`; unmapped areas may fall back to broader results.
- Cuisine searches should prefer genre-code-based URL paths over plain keyword matching. Use `genre_mapping.py` to keep cuisine filtering precise before adding ad hoc matching logic.
- Tabelog prefecture cuisine pages no longer honor the legacy `LstG` query alone; build area+cuisine searches from mapped `/AREA/rstLst/<segment>/` paths, where `<segment>` may be a slug like `yakiniku` or a category token like `RC0107` / `MC0101`.
- Major city searches may need nested Tabelog area paths instead of prefecture slugs, for example `札幌 -> hokkaido/A0101`, `名古屋 -> aichi/A2301`, and `神戸 -> hyogo/A2801`.
- Suggestion endpoints and detail pages are upstream-controlled and may change response shape; preserve defensive parsing and actionable error messages when touching these flows.
- Tabelog area suggestions may return `datatype="Town"`; keep MCP `SuggestionDatatype` aligned with upstream values or FastMCP structured output validation will fail before returning an envelope.
- Live Tabelog integration tests can return empty results under the default sandbox network; rerun `GURUME_RUN_INTEGRATION=1 uv run pytest -v -s tests/integration/test_cuisine_filter.py` with network access before treating empty live results as a regression.
- MCP live checks can pass cuisine filtering while still hiding regressions: keyword search on mapped area paths may be ignored upstream, search meta can disagree with parsed results, and detail `fetch_menu` / course parsing can fail or return empty after Tabelog markup or URL changes.
- Tabelog search count markup may expose visible range numbers before the real total, for example `.c-page-count__num` values `1`, `20`, then the total after `全`; parse the final number in `.c-page-count` and use `a[rel="next"]` for pagination.
- Tabelog path-based result pages such as `/tokyo/rstLst/` and cuisine pages may ignore `sk=<keyword>`; keyword searches should use the search endpoint with `sa`, `sk`, and `sw`, and MCP should reject `keyword + cuisine` unless live evidence proves both filters are honored.
- Detail menu pages are optional: some restaurants return 404 for `/dtlmenu/` while `/party/` has current course data in `.rstdtl-course-list`; treat optional menu/course 404s as empty sections and parse `/party/` courses from current selectors.
- CLI keyword auto-detection is a special case: when `--keyword` exactly matches a supported cuisine, clear the keyword and search as area+cuisine so city paths like `/hyogo/A2801/rstLst/cafe/` are used.

## TASTE
- To reduce Ruff complexity, prefer adding private helpers inside the existing module to split the flow before reaching for new files or new abstractions.
