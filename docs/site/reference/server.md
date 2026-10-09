# server

## Explicit headed-browser search

HTTP remains the default. To use a real browser instead, install the optional extra
and its Chromium binary on the MCP server machine:

```bash
uv sync --extra browser
uv run --extra browser playwright install chromium
uv run --extra browser gurume mcp
```

Call `tabelog_search_restaurants` with:

```json
{"area": "三重", "sort": "ranking", "limit": 10, "transport": "browser"}
```

This opens **headed** Chromium and fetches one page using the same URL builder,
restaurant parser, metadata, and area/cuisine checks as HTTP search. A graphical
display is required. CLI and TUI continue to use HTTP; Python callers can explicitly
use `await SearchRequest(...).search_browser()`.

The dedicated profile is `~/.cache/gurume/browser`. Cookies stay within that profile;
they are not copied from other browsers or sent to the HTTP client. Access is not
guaranteed: verification pages return a non-retryable error, not empty results.
Transient HTTP 5xx, navigation timeouts, and recognized network failures return
`retryable: true` with a retry-later action. Verification/403, other HTTP 4xx,
installation/display/profile errors, and unrecognized documents remain
non-retryable. This metadata allows callers to decide whether to retry; the tool
itself performs no automatic fallback, challenge solving, or retry.

If verification is required, manually open the same profile on the server machine:

```bash
uv run --extra browser playwright open --browser chromium \
  --user-data-dir "$HOME/.cache/gurume/browser" \
  'https://tabelog.com/mie/rstLst/?SrtT=rt&PG=1'
```

Complete any verification yourself, then close that browser before calling the tool
again. Concurrent calls sharing the profile are not supported. The tool closes its
browser on success, failure, or cancellation and does not leave a verification
window running. Do not repeatedly call it if access remains denied.

::: gurume.server
