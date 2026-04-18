# Backlog

This document tracks active backlog items for `gurume`. It is intentionally focused on actionable work that matches
the current repository state.

## Current Priorities

### High

- **Improve server-side test depth**
  - What: Expand MCP and search-path tests with additional edge cases, schema assertions, and failure handling.
  - Why now: The FastMCP server and search flow are already covered, but these paths remain core to the project and
    are the highest-value place to tighten regressions.
  - Done when: Tests cover validation failures, representative error paths, and output shape expectations without
    relying on live network calls.

- **Add `CHANGELOG.md`**
  - What: Create a changelog that captures the recent MCP/server evolution and user-visible changes.
  - Why now: The project already documents MCP usage in the README, but release-oriented changes are not summarized in
    one place.
  - Done when: A changelog exists with the current released history and clearly notes notable MCP-related changes.

- **Sync documentation with current behavior**
  - What: Review README and examples for consistency with current CLI, TUI, suggestions, and MCP tools.
  - Why now: The repo already ships keyword suggestions, TUI support, and MCP tests; documentation should reflect that
    stable baseline without stale caveats.
  - Done when: Public docs describe current features accurately and no longer imply that existing functionality is
    future work.

### Medium

- **Improve MCP error messages**
  - What: Make invalid cuisine/area/keyword failures more actionable, including nearby matches or clear next steps.
  - Why now: The server already validates inputs; better error text would reduce trial-and-error for MCP clients.
  - Done when: Common invalid-input failures point callers to `tabelog_list_cuisines`,
    `tabelog_get_area_suggestions`, or `tabelog_get_keyword_suggestions` with concrete guidance.

- **Add MCP usage examples**
  - What: Add concise examples for multi-step area/cuisine selection and restaurant search flows.
  - Why now: The MCP interface is one of the main entry points, and examples are cheaper than expanding API surface.
  - Done when: Example documentation shows at least the common area-first and cuisine-first flows and matches current
    tool names.

- **Extend detail page coverage carefully**
  - What: Continue `detail.py` work in small increments for fields that are stable and easy to test.
  - Why now: Detail scraping is useful, but it should grow from verified selectors rather than broad speculative
    parsing.
  - Done when: Each newly parsed field has fixture-backed tests and graceful handling for missing sections.

### Low

- **Increase CLI/TUI test coverage**
  - What: Add focused tests for CLI commands and high-value TUI behaviors.
  - Why now: The interfaces already exist and work, but regressions here are less critical than server/search paths.
  - Done when: CLI flows and a small set of TUI interactions are covered by stable tests.

- **Polish TUI workflows**
  - What: Improve discoverability, navigation, and result/detail ergonomics in the existing Textual app.
  - Why now: The TUI is already implemented, so follow-up work should target usability rather than greenfield design.
  - Done when: Specific pain points are identified and addressed without changing the current TUI scope.

## Deferred / Conditional

- **Playwright-based scraping fallback**
  - Only consider this if a reproducible Tabelog regression shows that core data is no longer available through the
    current `httpx` + BeautifulSoup flow, or if a new feature requires browser-only behavior.

- **Large API redesign**
  - Defer fluent builders, broad convenience layers, and major request/response API reshaping unless current usage
    shows a concrete problem that small helpers cannot solve.

- **Multi-platform restaurant support**
  - Defer support for other restaurant sites unless the project explicitly expands beyond Tabelog.

## Notes

- Core restaurant search currently works with `httpx` + BeautifulSoup; Playwright is not needed for the main search
  path.
- Area suggestions and keyword suggestions are already implemented in `suggest.py`.
- The Textual TUI already exists and should be treated as a maintained feature, not a future concept.
