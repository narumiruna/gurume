## Goal

Create a reusable, low-noise research harness for comparing Gurume CLI and MCP behavior without committing large ad hoc raw-output scripts into main.

Success means future live comparisons can be rerun with resumable collection, stable ASCII-safe filenames, normalized outputs, and clear instructions for storing heavy research artifacts on non-main branches.

## Context

The skill-vs-MCP experiment produced useful evidence but required a one-off runner, 226 output files, and direct Japanese filenames that made git status hard to scan. The results are intentionally kept on a research branch instead of main, but the workflow itself is worth standardizing.

## Non-Goals

- Do not commit the 2026-05-18 raw research outputs to main.
- Do not add CI that hits live Tabelog by default.
- Do not replace focused unit tests with live research output.

## Plan

- [ ] Review the research branch runner and output layout to identify reusable pieces and noisy artifacts; verify with `git show research/skill-mcp-gurume-comparison-2026-05-18:docs/research/skill-mcp-gurume-comparison/2026-05-18/run_comparison.py`.
- [ ] Add a reusable script under `scripts/` or `docs/research/tools/` that supports `collect`, `normalize`, and `report` phases; verify with `uv run ruff check <script>` and `uv run ty check <script>`.
- [ ] Add resume behavior that skips existing valid output envelopes and records explicit failure envelopes for timeouts or network errors; verify with a small fixture or dry-run mode.
- [ ] Replace raw Japanese filenames with stable ASCII slugs or hash-based filenames while preserving original area/cuisine values inside JSON; verify with a sample dry run and `find` output.
- [ ] Add a compact README under `docs/research/` explaining when to use a research branch, what not to merge to main, and how to summarize findings back into normal docs; verify with link checks or `rg -n "research branch|do not merge|raw output" docs/research README.md`.
- [ ] Add an optional small matrix fixture mode that does not hit the network, so report generation can be tested offline; verify with `uv run pytest` for the harness if tests are added.
- [ ] Run one minimal live smoke with a 1 area x 1 cuisine matrix only when network access is explicitly intended; verify raw output, normalized output, and final report are generated.

## Risks

- A reusable harness can become overbuilt for occasional research; keep it script-level until repeated use proves it belongs in package code.
- Live data can drift, so reports must record timestamps and raw evidence paths.
- Network tests must remain opt-in to avoid flaky default CI.

## Completion Checklist

- [ ] A reusable research harness exists outside one-off output directories, verified by script path and quality checks.
- [ ] Resume and failure-envelope behavior is verified by dry-run, fixture, or focused tests.
- [ ] Output filenames are ASCII-safe while preserving original Japanese query values inside JSON.
- [ ] Research branch guidance is documented so large raw outputs are not merged to main by accident.
- [ ] A minimal smoke or offline fixture proves collect, normalize, and report phases work end to end.
