## Goal

Choose a maintainable representation for a Tabelog area catalog that can cover fine-grained paths such as
`osaka/A2701/A270101` without turning `src/gurume/area_mapping.py` into a large hand-edited dictionary.

Success means the implementation choice is explicit, testable, and suitable for adding Osaka seed areas first while
leaving room for broader Tabelog area coverage later.

The executable implementation plan is `docs/plans/2026-05-28_area-catalog-plan.md`; this document records the
representation decision and tradeoffs.

## Context

Current `area_mapping.py` contains compact Python dictionaries for prefectures, a few city aliases, and a few nested
city paths. That is appropriate for a small curated set, but fine-grained Tabelog paths introduce different needs:

- More rows, aliases, and hierarchy than a small code mapping.
- Confidence and provenance fields such as `verified_at`, `source`, and `level`.
- Lookup from user-facing names such as `梅田` or `北新地` to Tabelog paths such as `osaka/A2701/A270101`.
- Optional CLI/MCP listing behavior, for example `list-areas --area 大阪`.

## Representation Options

| Option | Pros | Cons | Fit |
| --- | --- | --- | --- |
| JSON data file | Easy to review, diff, generate, and extend without importing Python; good for a data catalog with many rows; works well with fixture validation and package data. | Needs a loader and validation; no type safety until runtime; comments are not available in strict JSON. | Best source-of-truth format for the catalog rows. |
| Python dict mapping | Simple and consistent with current `area_mapping.py`; no loader required; type checkers can inspect it. | Becomes noisy with many rows and aliases; hard to attach metadata cleanly; generated updates create large code diffs. | Good for the existing small curated mappings, poor for a full fine-grained catalog. |
| Enum | Strong symbolic names and autocomplete for a small stable set. | Bad fit for upstream-controlled data; aliases and metadata are awkward; every new area is a code change; user-provided names do not map naturally to enum members. | Not recommended for the catalog source. Possibly useful only for fixed `level` values. |
| Dataclass records | Lightweight typed runtime model; good internal API for `AreaEntry(name, path, level, parent, aliases, ...)`; no heavy dependency. | Does not validate raw data by itself; still needs parsing checks; schema evolution requires custom validation code. | Good internal representation after loading JSON. |
| Pydantic BaseModel | Strong runtime validation, schema export, clear errors for malformed catalog rows; useful if catalog is generated or exposed through MCP. | More overhead than dataclasses; can be too heavy for hot lookup if used directly for every call; repo already uses Pydantic mainly for server outputs. | Good for validating catalog data at load/test time, not necessarily for the hot lookup object. |

## Recommendation

Use a hybrid:

- Store catalog rows in `src/gurume/data/area_catalog.json`.
- Validate the JSON with a small Pydantic model or equivalent strict loader in tests.
- Convert validated rows into frozen dataclass records or plain indexed dictionaries for runtime lookup.
- Keep small fixed vocabularies, such as `level`, as `Literal` values rather than broad enums unless repeated use proves an enum helps.
- Leave `area_mapping.py` as the public lookup layer and have it consult the catalog before or alongside existing curated mappings.

This keeps the source of truth data-oriented and reviewable while avoiding untyped JSON spreading through the codebase.

## Non-Goals

- Do not attempt to scrape or generate the full Japan-wide Tabelog hierarchy in the first PR.
- Do not replace existing prefecture and major-city mappings until the catalog loader has tests and seed data.
- Do not rely on Tabelog suggestions alone as path truth unless live evidence maps suggestions to stable URL paths.

## Plan

- [ ] Review the representation options and confirm whether the hybrid JSON plus typed loader recommendation is still
      the intended direction; verify by checking this document into `docs/plans/`.
- [ ] Use `docs/plans/2026-05-28_area-catalog-plan.md` for implementation sequencing; verify the implementation plan
      references this representation decision.
- [ ] Revisit this decision if catalog generation, CLI/MCP listing, or Japan-wide coverage changes the constraints;
      verify by updating this plan or adding a follow-up ADR-like note.

## Risks

- Tabelog area paths can drift, so rows need `verified_at` and live smoke coverage rather than pretending the catalog is
  permanent truth.
- Aliases can collide across prefectures, for example station or neighborhood names that exist in more than one region.
  The first implementation should prefer exact scoped names or require parent context when collisions appear.
- Pydantic validation in hot search paths would be unnecessary overhead; validation should happen at load time, import
  time, or test time, with indexed lookup used during search.

## Completion Checklist

- [ ] JSON source data, typed validation, and indexed runtime lookup are documented as the recommended representation.
- [ ] The tradeoffs for JSON, Python dict mapping, enum, dataclass records, and Pydantic BaseModel are documented.
- [ ] The implementation work is delegated to `docs/plans/2026-05-28_area-catalog-plan.md`.
