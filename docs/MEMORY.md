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
- Suggestion endpoints and detail pages are upstream-controlled and may change response shape; preserve defensive parsing and actionable error messages when touching these flows.

## TASTE
- To reduce Ruff complexity, prefer adding private helpers inside the existing module to split the flow before reaching for new files or new abstractions.
