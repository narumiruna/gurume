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

## Features

- 🔍 Search restaurants by area, keyword, cuisine, date, time, and party size
- 🍣 Filter by 45+ supported Japanese cuisine categories with stable Tabelog genre codes
- 📄 Parse restaurant detail pages into structured review, menu, and course data
- ⚡ Synchronous and asynchronous Python APIs
- 🖥️ Interactive TUI with area suggestions, keyword suggestions, and AI-assisted query parsing
- 🤖 MCP server with schema-first inputs and structured outputs for AI assistant integrations
- 🔒 Typed responses backed by Pydantic models

See the full [README on GitHub](https://github.com/narumiruna/gurume#readme) for examples.
