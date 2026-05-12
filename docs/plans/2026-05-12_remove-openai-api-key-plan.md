# Remove `OPENAI_API_KEY` Support

## Goal

Remove all OpenAI-backed natural-language parsing from gurume so the CLI, TUI, and packaged dependencies no longer depend on `OPENAI_API_KEY`, `openai`, or `python-dotenv`. Users supply structured filters (`--area`, `--keyword`, `--cuisine`) directly; AI-driven decomposition is delegated to upstream agents using the `gurume-cli` skill.

## Context

### Why remove it

Natural-language parsing is now covered by the `gurume-cli` agent skill (PR #46). Upstream agents — Claude Code, Codex, Claude.ai, etc. — decompose the user's free-form text into `--area / --cuisine / --keyword` and then call the CLI. The in-process OpenAI path has become a duplicate implementation: it costs maintenance (OpenAI SDK upgrades, API-key handling, `.env` loading) and keeps `openai` plus `python-dotenv` in the dependency tree solely to serve this one feature. Removing it lets the CLI focus on structured search while the agent + skill owns the natural-language entry point.

Audience note: anyone who set up `OPENAI_API_KEY` for `gurume search -q ...` or TUI `F4` is already an advanced user comfortable with API keys and `.env` files. Switching them to structured flags (`--area / --cuisine / --keyword`) or to any AI assistant with the `gurume-cli` skill is a low-cost migration, not a regression worth preserving the in-process LLM path for.

### Where it lives today

`OPENAI_API_KEY` is currently consumed in one place — `src/gurume/llm.py:parse_user_input` — and reached from two callers:

- `src/gurume/cli.py`: `gurume search --query/-q` calls `_apply_query_parse` → `parse_user_input` (cli.py:17, 56–80, 121).
- `src/gurume/tui.py`: the `F4` "AI Parse" action calls `parse_user_input` (tui.py:31, 447, 656–722).

Dependencies pulled in only for this feature: `openai>=2.32.0` and `python-dotenv` (both in `pyproject.toml`; `dotenv` is used exclusively in `llm.py`). Documentation references live in `README.md`, `AGENTS.md`, `docs/TUI_USAGE.md`, `docs/site/usage/tui.md`, and `skills/gurume-cli/SKILL.md`.

The recently merged `gurume-cli` agent skill (PR #46) already instructs agents to build flags from parsed intent and treats `--query` as a fallback, so removing the fallback is a natural follow-up.

## Non-Goals

- Replacing the LLM parsing with an offline heuristic parser. If users want natural-language input, they use an agent (Claude Code etc.) plus the `gurume-cli` skill.
- Changing search, detail, or MCP behavior beyond removing the `--query` plumbing.
- Adding a deprecation period. This is a clean removal in one release.

## Assumptions

- Bumping the minor version (breaking CLI/TUI surface) is acceptable; `--query` and TUI `F4` will be hard-removed, not soft-deprecated.
- No other module imports from `gurume.llm` (verified: only `cli.py` and `tui.py`).
- `python-dotenv` is only used by `llm.py` (verified via `rg`); no `.env` loading elsewhere.

## Plan

- [ ] Delete `src/gurume/llm.py`; verify with `rg -n "from .llm|from gurume.llm|import llm" src tests` returning no matches.
- [ ] Remove `--query/-q` option, `_apply_query_parse`, `OpenAIError` import, and the related example line from `src/gurume/cli.py`; verify with `uv run gurume search --help` no longer listing `--query` and `uv run gurume search --area 東京 --keyword 寿司 --limit 1 --output json` returning JSON.
- [ ] Remove the `F4` binding, `parse_user_input` import, `OpenAIError`/`TUI_ACTION_EXCEPTIONS` references, and `action_parse_natural_language` from `src/gurume/tui.py`; verify with `rg -n "parse_user_input|F4|action_parse_natural_language|OpenAIError" src/gurume/tui.py` returning no matches and `uv run python -c "from gurume.tui import GurumeApp"` importing cleanly.
- [ ] Drop `openai>=2.32.0` and `python-dotenv` from `pyproject.toml` dependencies; verify with `uv lock` regenerating `uv.lock` and `rg -n "^name = \"(openai|python-dotenv)\"" uv.lock` returning no matches.
- [ ] Update `README.md`: remove the `--query` example block (line ~65–66), the `--query, -q` bullet, the `OPENAI_API_KEY` note (~line 90), and the Notes-and-Limitations line about NL parsing requiring `OPENAI_API_KEY` (~line 396); verify with `rg -n "OPENAI_API_KEY|--query|natural-language" README.md` returning no matches.
- [ ] Update `AGENTS.md` "Security & Configuration Tips" to drop the `OPENAI_API_KEY` sentence; verify with `rg -n "OPENAI_API_KEY|OpenAI" AGENTS.md` returning no matches.
- [ ] Update `docs/TUI_USAGE.md` and `docs/site/usage/tui.md` to remove the `F4` row, the "Using AI natural language parsing" section, and related tips; verify with `rg -n "F4|AI Parse|natural language|自然語言" docs/TUI_USAGE.md docs/site/usage/tui.md` returning no matches.
- [ ] Update `skills/gurume-cli/SKILL.md`: delete the "Fallback: natural-language `--query`" section (currently step 4) and renumber "Present results" to step 4; verify with `rg -n "OPENAI_API_KEY|--query" skills/gurume-cli/SKILL.md` returning no matches.
- [ ] Run quality gates: `uv run ruff check .`, `uv run ty check .`, and `uv run pytest -v -s --cov=src tests`; verify each command exits 0.
- [ ] Append one line to `docs/LOG.md` following the project format (e.g., `2026-05-12 | feat(cli)!: remove OPENAI_API_KEY-based --query and F4 AI parsing (#local)`); verify with `tail -1 docs/LOG.md` showing the new line.
- [ ] Open a PR titled `feat(cli)!: remove OPENAI_API_KEY-based natural-language parsing` summarizing the removal and pointing at the `gurume-cli` skill as the recommended replacement; verify with `gh pr view` showing the PR URL.

## Risks

- **Breaking change for users who relied on `--query` or TUI `F4`.** Mitigation: call this out clearly in the PR description and `docs/LOG.md` with the `!` Conventional Commits marker; point users at the `gurume-cli` skill.
- **Hidden dotenv consumers.** Mitigation: pre-removal `rg` already verified `python-dotenv` is only used in `llm.py`. If a future feature needs `.env`, add it back deliberately.
- **TUI test coverage gap.** The TUI changes are import-only checked. Mitigation: if `tests/` grows TUI coverage later, the smoke import in the verification step catches the obvious regressions; otherwise call this out in the PR.

## Rollback / Recovery

If a regression is reported after release, revert the single PR (`git revert <merge-sha>`) and cut a patch release. The change is self-contained: one deleted module, two files trimmed, dependencies removed, docs reverted.

## Completion Checklist

- [ ] `OPENAI_API_KEY` no longer appears in source, docs, or skills, verified by `rg -n "OPENAI_API_KEY" .` returning no matches outside `docs/LOG.md` history and `docs/plans/`.
- [ ] `openai` and `python-dotenv` are absent from runtime dependencies, verified by `rg -n "^\\s*\"(openai|python-dotenv)" pyproject.toml` returning no matches and `uv.lock` regenerated.
- [ ] `gurume search --help` output no longer lists `--query/-q`, verified by `uv run gurume search --help | rg -n "query"` returning no matches.
- [ ] TUI no longer exposes `F4` AI Parse, verified by `rg -n "F4|action_parse_natural_language" src/gurume/tui.py` returning no matches.
- [ ] `uv run ruff check .`, `uv run ty check .`, and `uv run pytest -v -s --cov=src tests` all pass, verified by their exit codes and the pytest summary line.
- [ ] PR is opened against `main` with the breaking-change marker and merged, verified by `gh pr view` link and `git log --oneline -5` on updated `main`.
