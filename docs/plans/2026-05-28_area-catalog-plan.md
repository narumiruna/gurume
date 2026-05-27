## Goal

Add the first data-backed fine-grained Tabelog area catalog so common Osaka neighborhood searches can use reliable
path-based URLs instead of falling back to broad `sa=<area>` keyword searches.

Success means `get_area_slug()` can resolve a small curated Osaka seed set such as `梅田`, `北新地`, `難波`, `心斎橋`,
and `天王寺` to Tabelog area paths, while existing prefecture and major-city mappings keep working.

## Context

`docs/plans/archived/2026-05-28_area-catalog-representation-plan.md` compares representation choices and recommends a
hybrid: JSON as the source-of-truth catalog, strict validation, then dataclass or indexed dictionary lookup at runtime.

The implementation should apply that choice without attempting a Japan-wide hierarchy in the first PR. The immediate
value is reducing low-confidence `area + keyword` searches for common Osaka requests by mapping user-facing area names
to paths such as `osaka/A2701/A270101`.

## Architecture

- `src/gurume/data/area_catalog.json`: source-of-truth catalog rows.
- `src/gurume/area_mapping.py`: public lookup layer that loads/indexes catalog rows and preserves existing mappings.
- `tests/test_area_mapping.py`: catalog schema, duplicate detection, alias lookup, and backward compatibility tests.
- Search URL construction remains in `restaurant.py` and `search.py`; it should consume `get_area_slug()` without
  knowing whether the path came from the catalog or legacy mappings.

## Non-Goals

- Do not expose new CLI/MCP `list-areas` tools in this first implementation PR.
- Do not generate or scrape the full Tabelog hierarchy.
- Do not remove existing `PREFECTURE_MAPPING`, `CITY_MAPPING`, or `CITY_AREA_PATH_MAPPING` until catalog coverage is
  broad enough to justify a separate migration.

## Assumptions

- The first Osaka paths can be seeded from live Tabelog URL evidence and kept small enough for manual review.
- JSON catalog data should be packaged with the library and available without network access.
- Catalog validation can happen in tests and at import/load time without adding a new runtime dependency.

## Unknowns

- Exact Tabelog paths for each Osaka seed area must be verified before implementation. Resolve this with focused live
  probes before adding rows.
- Alias collisions may appear once Tokyo/Kyoto are added. The first PR can reject duplicate aliases globally and defer
  scoped disambiguation until there is evidence that it is needed.

## Plan

- [ ] Verify the Osaka seed paths for `梅田`, `北新地`, `難波`, `心斎橋`, and `天王寺` with live Tabelog URLs; record the
      chosen paths in the PR notes or catalog `source` fields.
- [ ] Add `src/gurume/data/area_catalog.json` with seed rows containing `name`, `path`, `level`, `parent`, `aliases`,
      `source`, and `verified_at`; verify the file is included by `rg -n "area_catalog" src tests pyproject.toml`.
- [ ] Add a strict catalog loader in `src/gurume/area_mapping.py` that validates required keys, path shape, duplicate
      names, duplicate aliases, and supported `level` values; verify malformed fixture tests fail predictably.
- [ ] Update `get_area_slug()` to consult the catalog index while preserving existing prefecture, city, city-path, and
      suffix-stripping behavior; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_area_mapping.py -v`.
- [ ] Add URL-building tests showing a catalog-backed Osaka area plus supported cuisine produces a path URL such as
      `https://tabelog.com/<catalog-path>/rstLst/<cuisine>/`; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest
      tests/test_search.py -v`.
- [ ] Add one opt-in live smoke for a catalog-backed Osaka area search and confirm `area_filter_confidence="high"` when
      parsed URLs match the catalog path; verify with a documented command/output summary.
- [ ] Update `skills/gurume-cli/SKILL.md` only if the agent workflow should prefer fine-grained area names differently;
      if changed, sync and verify with `UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/sync_skills.py --check`.
- [ ] Run focused gates; verify with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/gurume/area_mapping.py
      src/gurume/search.py tests/test_area_mapping.py tests/test_search.py`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty
      check .`, and the targeted pytest commands above.

## Risks

- Tabelog path drift can make seed rows stale; each row needs `verified_at` and at least one live smoke in the PR.
- Global alias uniqueness is simple and safe for the first PR, but may reject useful aliases later when multiple
  prefectures share a station or neighborhood name.
- If JSON loading happens on every lookup, search hot paths may become slower; build an index once and keep lookup
  constant-time.

## Completion Checklist

- [ ] `src/gurume/data/area_catalog.json` exists with reviewed Osaka seed rows and provenance fields.
- [ ] Catalog validation catches malformed rows and duplicate aliases, verified by `tests/test_area_mapping.py`.
- [ ] `get_area_slug()` resolves the Osaka seed names and aliases while all existing mapping tests still pass.
- [ ] Catalog-backed area+cuisine searches build path-based URLs, verified by `tests/test_search.py`.
- [ ] At least one live smoke confirms a catalog-backed Osaka area produces high-confidence URL evidence, or the PR
      explicitly records why live validation was not run.
- [ ] Focused lint, type check, and pytest gates pass with recorded command output.
