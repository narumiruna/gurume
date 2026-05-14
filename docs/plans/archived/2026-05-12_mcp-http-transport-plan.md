# MCP HTTP Transport Support (issue #39)

## Goal

Allow `gurume mcp` to start the MCP server over HTTP (streamable-http or SSE) instead of only stdio. Success: `gurume mcp --transport streamable-http --host 127.0.0.1 --port 8000` boots a working MCP HTTP server, while the default `gurume mcp` keeps booting stdio unchanged.

## Context

- `src/gurume/cli.py::mcp()` currently has no flags and just calls `server.run()`.
- `src/gurume/server.py::run()` hardcodes `mcp.run()` (stdio).
- `FastMCP.run(transport=...)` already supports `stdio | sse | streamable-http`; `FastMCP.settings` holds `host`, `port`, `streamable_http_path`, `sse_path` which can be mutated before `run()`.

## Non-Goals

- No auth / OAuth wiring.
- No deployment, reverse-proxy, or TLS handling.
- No new docs beyond a short README usage block.

## Plan

- [x] Branch off `main`: `git checkout -b feat/mcp-http-transport`; verify with `git branch --show-current`.
- [x] Extend `src/gurume/server.py::run()` to accept `transport: Literal["stdio", "sse", "streamable-http"] = "stdio"`, `host: str = "127.0.0.1"`, `port: int = 8000`, `path: str = "/mcp"`. When transport != `stdio`, set `mcp.settings.host`, `mcp.settings.port`, and `mcp.settings.streamable_http_path` (or `sse_path` for sse) before calling `mcp.run(transport=transport)`; verify with `uv run ty check .`.
- [x] Extend `src/gurume/cli.py::mcp()` with Typer options `--transport`, `--host`, `--port`, `--path` mapped to `server.run()`; keep default behavior (no flags) identical to current stdio mode; verify with `uv run gurume mcp --help` listing the new flags.
- [x] Add CLI tests in `tests/test_cli.py` using `typer.testing.CliRunner` to assert: (a) `gurume mcp --help` exits 0 and shows `--transport`; (b) invoking `gurume mcp --transport streamable-http --port 9001` calls `server.run` with those kwargs (patch `gurume.server.run`); (c) default invocation still calls `server.run(transport="stdio", ...)`. Verify with `uv run pytest tests/test_cli.py -v`.
- [x] Add `tests/test_server.py` (or extend existing) test that patches `FastMCP.run` and asserts `server.run(transport="streamable-http", host="0.0.0.0", port=9001, path="/mcp")` mutates `mcp.settings` to the right values and calls `mcp.run(transport="streamable-http")`. Verify with `uv run pytest tests/test_server.py -v`.
- [x] Append a short HTTP usage block to `README.md` under the MCP section showing the new flags and a security caveat about `0.0.0.0`; verify by `rg "streamable-http" README.md` returning a match.
- [x] Append one line to `docs/LOG.md`: `2026-05-12 | feat(mcp): add http transport flags to \`gurume mcp\` (#39)`.
- [x] Quality gate: `make lint && make type && make test` all pass.
- [x] Pushed branch and opened PR #42 linking issue #39; `gh pr view 42 --json state` returns `OPEN` and CI `python (3.12)` conclusion=SUCCESS.

## Risks

- **Mutating `mcp.settings` after instantiation**: relies on FastMCP not caching settings at construction time. Mitigation: server test asserts the actual values land on `mcp.settings` and `mcp.run` is invoked with the right transport.
- **API surface stability of `streamable_http_path`**: pinned by FastMCP version in `pyproject.toml`. Mitigation: tests will fail loudly on upgrade.

## Completion Checklist

- [x] `gurume mcp --help` shows `--transport`, `--host`, `--port`, `--path`, verified by `uv run gurume mcp --help`.
- [x] Default `gurume mcp` invocation still selects stdio, verified by the CLI default-invocation test in `tests/test_cli.py`.
- [x] `server.run(transport="streamable-http", ...)` mutates `mcp.settings` and calls `FastMCP.run(transport="streamable-http")`, verified by the patched test in `tests/test_server.py`.
- [x] `make lint && make type && make test` all pass.
- [x] README has a short HTTP transport usage block, verified by `rg "streamable-http" README.md`.
- [x] `docs/LOG.md` has the new feat line, verified by `tail -1 docs/LOG.md`.
- [x] PR #42 is OPEN with CI green, verified by `gh pr view 42 --json state,statusCheckRollup` (state=OPEN, `python (3.12)` conclusion=SUCCESS after fixup `6339b7c`).
