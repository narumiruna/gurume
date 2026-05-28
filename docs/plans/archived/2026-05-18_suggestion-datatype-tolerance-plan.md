## Goal

Make Tabelog suggestion tools tolerate upstream suggestion datatypes that are valid in practice but not yet listed in Gurume's MCP response schema.

Success means `tabelog_get_area_suggestions` and `tabelog_get_keyword_suggestions` return structured success envelopes for observed datatypes such as `MajorMunicipal` and `Genre3` instead of failing FastMCP/Pydantic output validation.

## Context

Live usage exposed two schema drift failures:

- `tabelog_get_area_suggestions("大阪")` can return `datatype="MajorMunicipal"`.
- `tabelog_get_keyword_suggestions("お好み焼き")` or `tabelog_get_keyword_suggestions("豚しゃぶ")` can return `datatype="Genre3"`.

`src/gurume/suggest.py` stores datatype as a plain string, but `src/gurume/server_models.py` narrows MCP `SuggestionOutput.datatype` to a `Literal`. `src/gurume/server_helpers.py` casts the raw string to that literal, so unknown-but-real upstream values can fail only when the structured MCP output is validated.

## Status

Completed by the current implementation. `SuggestionDatatype` is now a plain `str`, server and parser tests preserve
`MajorMunicipal` and `Genre3`, and live MCP smoke checks returned successful envelopes for `大阪` and `お好み焼き`.

## Non-Goals

- Do not redesign the suggestion API response shape beyond datatype tolerance.
- Do not infer cuisine semantics from `Genre3`; this plan only prevents schema validation failures.
- Do not add a broad natural-language query parser.

## Assumptions

- Upstream suggestion datatypes are controlled by Tabelog and may expand again.
- Preserving raw datatype strings is more useful to callers than dropping otherwise valid suggestions.

## Plan

- [x] Add server-level regression tests for `MajorMunicipal` and `Genre3` suggestion payloads in `tests/test_server.py`, expecting `SuggestionListOutput.status == "success"` and the raw datatype to be returned; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py tests/test_suggest.py -v`.
- [x] Add parser-level fixture coverage in `tests/test_suggest.py` for unknown or newly observed datatype strings, expecting `AreaSuggestion.datatype` and `KeywordSuggestion.datatype` to preserve the raw value; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py tests/test_suggest.py -v`.
- [x] Update `src/gurume/server_models.py` to accept observed and future-safe suggestion datatypes without making MCP output validation brittle; verified by `SuggestionDatatype = str`.
- [x] Keep `_to_suggestion_outputs` in `src/gurume/server_helpers.py` type-checkable after the schema change, removing unsafe casts if the model no longer needs them; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`.
- [x] Review `docs/site/reference/server.md` and `docs/site/reference/suggest.md` only if the public datatype contract changes; no docs update was needed because the public contract preserves raw datatype strings.
- [x] Run focused quality gates for the touched surface; verified with `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`, `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`, and `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/test_server.py tests/test_suggest.py -v`.

## Risks

- Allowing arbitrary datatype strings can weaken client-side enum guarantees, but failing the entire tool call is worse for an upstream-controlled autocomplete API.
- Adding only `MajorMunicipal` and `Genre3` to the literal may fix today's issue while leaving the same failure mode for the next upstream datatype.

## Completion Checklist

- [x] `MajorMunicipal` area suggestions return a successful MCP suggestion envelope, verified by a regression test in `tests/test_server.py` and live `tabelog_get_area_suggestions("大阪")`.
- [x] `Genre3` keyword suggestions return a successful MCP suggestion envelope, verified by a regression test in `tests/test_server.py` and live `tabelog_get_keyword_suggestions("お好み焼き")`.
- [x] Raw suggestion datatype strings remain preserved from `src/gurume/suggest.py`, verified by `tests/test_suggest.py`.
- [x] Type checking remains clean for the suggestion output path, verified by `UV_CACHE_DIR=/tmp/uv-cache uv run ty check .`.
- [x] Lint and focused tests pass for suggestion and MCP output modules, verified by recorded `ruff` and `pytest` command output.
