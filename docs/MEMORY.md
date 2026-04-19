## GOTCHA
- `ty` is stricter than Ruff: for timezone constants, use `from datetime import UTC` and pass it to `datetime.now(UTC)`; for parsers over different dataclasses such as area/keyword, use separate typed helpers to avoid union returns that fail type checking.
- `docs/MEMORY.md` and `docs/CHANGELOG.md` are the canonical project docs; do not recreate root-level copies.
- User-facing project docs should live under `docs/`; if a root-level guide is moved there, update README links instead of leaving a duplicate at the repo root.
- FastMCP exposes `Annotated[..., Field(...)]` constraints in MCP schemas, but direct Python calls to the tool function still need manual validation if tests or local callers bypass the protocol layer.

## TASTE
- To reduce Ruff complexity, prefer adding private helpers inside the existing module to split the flow before reaching for new files or new abstractions.
