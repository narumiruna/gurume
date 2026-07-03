## Goal

Reduce repository over-engineering found by the ponytail audit with the smallest safe cleanup set.

Success means dead or duplicate project files are removed or made single-source, avoidable runtime dependencies are cut where tests still pass, and any public API break is explicitly accepted or deferred.

## Context

The audit identified duplicate docs and skill mirrors, stale packaging/deploy lanes, small dependencies that can be replaced with stdlib code, and compatibility surfaces that may no longer earn their keep.

## Tech Stack

- Python runtime dependencies under `pyproject.toml` / `uv.lock`.
- CI workflows under `.github/workflows/`.
- MkDocs source under `docs/site/`.

## Non-Goals

- Do not change Tabelog scraping semantics beyond parser-equivalent replacements.
- Do not remove public API names (`do`, `do_sync`, `ReservationDate`, `json-envelope`) without explicit maintainer acceptance or a breaking-release note.
- Do not add replacement abstractions for deleted code.

## Unknowns

- [x] Breaking cleanup release timing is deferred. No explicit maintainer acceptance was given for public API removals, so public API aliases and CLI output values stay in this cleanup.

## Plan

- [x] Capture a baseline before cleanup so regressions are obvious; verified with `uv run ruff check .`, `uv run ty check .`, and `uv run pytest -q tests` (`324 passed, 4 skipped`).
- [x] Delete or single-source duplicate project files (`docs/TUI_USAGE.md`, tracked `.codex/skills/gurume-cli/`, no-op `tests/test_hello.py`) to reduce repo noise; verified with `test ! -e docs/TUI_USAGE.md tests/test_hello.py`, `git rm --cached -r .codex/skills`, `uv run python scripts/sync_skills.py --check`, and `uv run pytest -q tests`.
- [x] Not applicable: deleting archived implementation plans is not part of this pass because `writing-plans` uses `docs/plans/archived/` as the completion archive and this plan is archived there; verified with `find docs/plans/archived -type f -name '*.md' | wc -l` returning `19` before archiving this plan.
- [x] Remove stale Docker distribution files if Docker publishing is unused (`Dockerfile`, `.github/workflows/docker.yml`); verified with `test ! -e Dockerfile .github/workflows/docker.yml` and `rg -n "docker|Dockerfile" README.md .github docs pyproject.toml` returning only this plan before archive.
- [x] Replace BeautifulSoup `"lxml"` parser use with stdlib `"html.parser"`, then drop `lxml`; verified with `rg -n '"lxml"|lxml' src pyproject.toml uv.lock` returning no output and `uv run pytest -q tests/test_restaurant.py tests/test_detail.py tests/test_search.py`.
- [x] Replace `loguru` with stdlib `logging` in cache/retry modules, then drop `loguru`; verified with `rg -n "loguru" src pyproject.toml uv.lock` returning no output and `uv run pytest -q tests/test_cache.py tests/test_retry.py`.
- [x] Remove `tenacity` by using one small retry loop for sync and async fetches; verified with `rg -n "tenacity|RetryCallState" src pyproject.toml uv.lock` returning no output and `uv run pytest -q tests/test_retry.py`.
- [x] Shrink `src/gurume/cache.py` to the cache behavior actually used by restaurant search, deferring `FileCache` unless a caller needs it; verified with `rg -n "FileCache|set_cache" src tests README.md` returning no output and `uv run pytest -q tests/test_cache.py`.
- [x] Deduplicate area and keyword suggestion request handling behind one sync helper and one async helper; verified with `uv run pytest -q tests/test_suggest.py tests/test_server.py`.
- [x] Resolve public API cleanup (`do`/`do_sync`, `types.py` aliases, `json-envelope`) only after the breaking-release unknown is answered; deferred because no explicit maintainer acceptance was given for public API removals.
- [x] Regenerate dependency lock and run full validation after accepted cleanup; verified with `uv lock`, `uv run ruff check .`, `uv run ty check .`, and `uv run pytest -q tests` (`320 passed, 4 skipped`).
- [x] Append one concise project log line for the cleanup implementation; verified with the last line of `docs/LOG.md`: `2026-07-03 | refactor(repo): remove ponytail audit cleanup bloat (#87)`.

## Risks

- Parser replacement can subtly change malformed HTML parsing; mitigated by existing parser fixtures and full test pass.
- Removing public aliases or CLI output values can break downstream users; mitigated by deferring those removals.
- Removing tracked `.codex` mirrors may conflict with current local skill workflow; mitigated by ignoring the local mirror and verifying `uv run python scripts/sync_skills.py --check`.

## Rollback / Recovery

- Revert individual deletion commits if a removed file or public surface is still needed.
- Restore dropped dependencies by reverting `pyproject.toml` and `uv.lock`, then rerun the focused test listed in the task that removed them.

## Completion Checklist

- [x] Accepted cleanup scope is verified by checked plan items and explicit deferrals for public API breaks.
- [x] Repo-noise deletions are verified by `git status --short` showing intended removed/edited paths only.
- [x] Dropped dependencies are verified by `rg -n "lxml|loguru|tenacity" pyproject.toml uv.lock src` returning no output.
- [x] Search, detail, suggest, cache, retry, CLI, and server behavior are verified by focused tests plus `uv run pytest -q tests` (`320 passed, 4 skipped`).
- [x] Lint and type checks pass, verified by `uv run ruff check .` and `uv run ty check .`.
- [x] Documentation and log updates are verified by README/docs references and the appended `docs/LOG.md` line.
