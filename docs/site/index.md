---
title: Gurume
---

# 🍜 Gurume

**Gurume** is a Python library, CLI, TUI, and MCP server for discovering Japanese restaurants on [Tabelog](https://tabelog.com).

Search by area, cuisine, date, and party size; parse structured detail pages; and plug the same workflows into AI assistants via a FastMCP server.

## Quick Links

- [TUI Usage](usage/tui.md)
- [API Reference](reference/index.md)
- [GitHub Repository](https://github.com/narumiruna/gurume)
- [PyPI](https://pypi.org/project/gurume/)

## Installation

```bash
uv add gurume
# or
pip install gurume
```

## HTTP Configuration

No additional HTTP setup is required for normal use.
Gurume uses `curl_cffi` with Safari impersonation by default so its TLS fingerprint and generated browser headers remain consistent.

If Tabelog starts returning HTTP 403 for the default profile, set `GURUME_IMPERSONATE` before starting the CLI, TUI, MCP server, or Python process:

```bash
GURUME_IMPERSONATE=firefox gurume search --area 三重 --cuisine すき焼き
```

PowerShell users can set the same process environment variable before running Gurume:

```powershell
$env:GURUME_IMPERSONATE = "firefox"
gurume search --area 三重 --cuisine すき焼き
```

The value must be an impersonation profile supported by the installed `curl_cffi` version.
An unsupported value is rejected by `curl_cffi`.

## Features

- 🔍 Search restaurants by area, keyword, cuisine, date, time, and party size
- 🍣 Filter by 29 supported Japanese cuisine categories with stable Tabelog genre codes
- 📄 Parse restaurant detail pages into structured review, menu, and course data
- ⚡ Synchronous and asynchronous Python APIs
- 🖥️ Interactive TUI with area suggestions, keyword suggestions, and cuisine auto-detection
- 🤖 MCP server with schema-first inputs and structured outputs for AI assistant integrations
- 🔒 MCP responses backed by Pydantic models and Python APIs type-annotated

See the full [README on GitHub](https://github.com/narumiruna/gurume#readme) for examples.
