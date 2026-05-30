## Goal

Expand `src/gurume/data/area_catalog.json` to cover 100% of the verified Tabelog leaf subarea paths,
for example `osaka/A2701/A270101`.

Success means the repository has a committed, reviewable snapshot of the Tabelog leaf-subarea universe and the runtime
catalog has exact path-set coverage against that snapshot. `get_area_slug()` must keep resolving supported names and
aliases to the correct Tabelog path without broad `sa=<area>` fallback for catalog-backed subareas.

## Context

The current catalog is a small Osaka seed set and allows multiple rows to point at the same path, for example `梅田` and
`北新地` both map to `osaka/A2701/A270101`. For 100% leaf-path coverage, treat the Tabelog path as the primary identity:
prefer one catalog row per leaf path, with alternate labels stored in `aliases`.

Tabelog suggestions can help discover wording and aliases, but they do not provide reliable URL paths. The path truth
must come from verified Tabelog URLs, area navigation, or breadcrumb evidence.

## Architecture

- `src/gurume/data/area_catalog.json`: runtime source of truth, one catalog row per verified leaf path.
- `tests/fixtures/tabelog_leaf_subareas_snapshot.json`: committed coverage universe discovered from live Tabelog pages.
- `scripts/discover_area_catalog.py`: opt-in live discovery script using existing `curl_cffi` and BeautifulSoup/lxml
  dependencies, with cache and rate-limit controls.
- `scripts/check_area_catalog_coverage.py`: offline check that catalog paths exactly match the snapshot paths.
- `src/gurume/area_mapping.py`: strict loader, duplicate-path validation, and indexed lookup by canonical name and alias.
- `tests/test_area_mapping.py`: schema, coverage, duplicate rejection, and lookup regression tests.

## Non-Goals

- Do not rely on the Tabelog suggestion API as the canonical path source.
- Do not require live Tabelog access in normal CI; live discovery should be opt-in and snapshot-backed checks should be
  offline.
- Do not add CLI/MCP area-listing features in this coverage PR.
- Do not remove existing prefecture, city, or city-path mappings unless a separate migration plan covers that behavior.

## Assumptions

- Existing dependencies are enough for discovery and parsing; avoid adding a new scraping dependency unless live probes
  prove it is necessary.
- Most leaf subareas follow `prefecture/A####/A######`, but the discovery step must record any live exceptions before
  validation is tightened around that shape.
- Canonical names can be taken from Tabelog link text, page heading, or breadcrumb text; common alternate labels belong
  in `aliases`.

## Unknowns

- Whether every Tabelog leaf subarea has exactly two `A` code segments. Resolve this in the discovery probe before
  enforcing duplicate-path or path-shape rules.
- Whether Tabelog groups multiple user-facing place names under a single leaf path. Resolve this by choosing one
  canonical label per path and preserving other useful labels as aliases.
- Whether Cloudflare or rate limiting blocks a full live crawl from the development environment. Resolve this by adding
  cache, delay, and resume support to the discovery script, then record any blocked prefectures in the PR notes.

## Plan

- [ ] Probe representative Tabelog area pages for Tokyo, Osaka, Hokkaido, and one small prefecture to confirm the leaf
      URL pattern, navigation selectors, and breadcrumb/name sources; verify by documenting the chosen selectors in
      `scripts/discover_area_catalog.py` comments and producing a dry-run output that includes existing Osaka seed paths.
- [ ] Add `scripts/discover_area_catalog.py` to crawl prefecture area pages into sorted leaf-subarea records containing
      `path`, `name`, `parent`, `source`, and `discovered_at`; verify with
      `uv run python scripts/discover_area_catalog.py --prefecture osaka --output /tmp/osaka_leaf_subareas.json`.
- [ ] Create `tests/fixtures/tabelog_leaf_subareas_snapshot.json` from a successful all-prefecture discovery run, sorted
      by `path` with one record per leaf path; verify with
      `uv run python scripts/discover_area_catalog.py --all --output tests/fixtures/tabelog_leaf_subareas_snapshot.json`.
- [ ] Add `scripts/check_area_catalog_coverage.py` to compare the runtime catalog against the snapshot and report missing,
      extra, duplicate, or malformed paths; verify with `uv run python scripts/check_area_catalog_coverage.py` returning
      non-zero before the catalog is fully expanded.
- [ ] Normalize `src/gurume/data/area_catalog.json` to one row per leaf path, merging current duplicate-path rows into
      aliases where needed; verify `get_area_slug("梅田")` and `get_area_slug("北新地")` still both resolve to
      `osaka/A2701/A270101` in `tests/test_area_mapping.py`.
- [ ] Tighten `src/gurume/area_mapping.py` validation to reject duplicate catalog paths, duplicate lookup keys, unsupported
      levels, invalid source URLs, and stale parent/path shape mismatches; verify with focused malformed-row tests in
      `tests/test_area_mapping.py`.
- [ ] Expand `src/gurume/data/area_catalog.json` from the snapshot, preserving manually reviewed aliases and recording
      `source` plus `verified_at` for every row; verify with `uv run python scripts/check_area_catalog_coverage.py`.
- [ ] Replace seed-count assertions in `tests/test_area_mapping.py` with coverage-oriented assertions that load the
      snapshot, compare exact path sets, and exercise canonical-name plus alias lookup; verify with
      `uv run pytest tests/test_area_mapping.py -v`.
- [ ] Run an opt-in live freshness check against the committed snapshot after expansion; verify with a recorded command
      such as `GURUME_RUN_INTEGRATION=1 uv run python scripts/discover_area_catalog.py --all --compare-snapshot` in PR
      notes or local handoff output.
- [ ] Run repository quality gates after the data and script changes; verify with `uv run ruff check .`,
      `uv run ty check .`, and `uv run pytest -v -s --cov=src tests`.
- [ ] Append one summary line to `docs/LOG.md` for the implementation change; verify the final line follows
      `YYYY-MM-DD | type(scope): summary (#ref)`.

## Risks

- Tabelog area markup and URLs can change without warning, so the committed snapshot is a dated coverage target rather
  than a permanent guarantee about future upstream state.
- A full crawl may be slow or blocked; cache, delay, resume, and per-prefecture retry options are necessary to make the
  discovery process repeatable.
- Alias collisions are likely once Japan-wide coverage is added; fail fast on collisions and prefer scoped or explicit
  aliases over guessing.
- One-row-per-path changes the current Osaka seed representation; lookup tests must preserve user-visible behavior for
  existing names.

## Completion Checklist

- [ ] The Tabelog leaf-subarea universe is defined by `tests/fixtures/tabelog_leaf_subareas_snapshot.json` and verified by
      a recorded opt-in live discovery command.
- [ ] `src/gurume/data/area_catalog.json` has exact path-set equality with the snapshot, verified by
      `uv run python scripts/check_area_catalog_coverage.py`.
- [ ] Catalog rows are schema-valid, duplicate-path-free, and lookup-key-collision-free, verified by
      `uv run pytest tests/test_area_mapping.py -v`.
- [ ] Existing search behavior remains type-safe and tested, verified by `uv run ruff check .`, `uv run ty check .`, and
      `uv run pytest -v -s --cov=src tests`.
- [ ] The implementation is documented in `docs/LOG.md` with one final single-line entry.
