# 🍜 Gurume

[![PyPI](https://img.shields.io/pypi/v/gurume)](https://pypi.org/project/gurume/)
[![Python](https://img.shields.io/pypi/pyversions/gurume)](https://pypi.org/project/gurume/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/narumiruna/gurume/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-mkdocs--material-blue)](https://narumiruna.github.io/gurume/)

📚 **Documentation:** <https://narumiruna.github.io/gurume/>

**Gurume** is a Python library, CLI, TUI, and MCP server for discovering Japanese restaurants on [Tabelog](https://tabelog.com) — Japan's largest restaurant review platform.

Search by area, cuisine, date, and party size; parse structured detail pages; and plug the same workflows directly into AI assistants via a FastMCP server.

## ✨ Features

- 🔍 Search restaurants by area, keyword, cuisine, date, time, and party size
- 🍣 Filter by 29 supported Japanese cuisine categories with stable Tabelog genre codes
- 📄 Parse restaurant detail pages into structured review, menu, and course data
- ⚡ Use synchronous and asynchronous Python APIs
- 🖥️ Run an interactive TUI with area suggestions, keyword suggestions, and cuisine auto-detection
- 🤖 Start an MCP server with schema-first inputs and structured outputs for AI assistant integrations
- 🔒 Keep MCP responses typed with Pydantic models and Python APIs type-annotated

## 📦 Installation

```bash
uv add gurume
```

Or with `pip`:

```bash
pip install gurume
```

For local development:

```bash
uv sync --dev
```

## 🚀 Quick Start

### 💻 CLI

The built-in CLI currently exposes four commands:

- `gurume search`
- `gurume list-cuisines`
- `gurume tui`
- `gurume mcp`

Examples:

```bash
# Search by area and keyword
gurume search --area 東京 --keyword 寿司

# Search with a precise cuisine filter
gurume search --area 三重 --cuisine すき焼き

# Change sort order and output format
gurume search --area 大阪 --cuisine ラーメン --sort ranking --output json

# List all supported cuisines
gurume list-cuisines

# Start the TUI
gurume tui

# Start the MCP server
gurume mcp
```

Current `gurume search` options:

- `--area`, `-a`
- `--keyword`, `-k`
- `--cuisine`, `-c`
- `--sort`, `-s`: `ranking`, `review-count`, `new-open`, `standard`
- `--limit`, `-n`
- `--output`, `-o`: `table`, `json`, `simple`

Notes:

- For natural-language input, use the [`gurume-cli` agent skill](skills/gurume-cli/) with an AI assistant — it decomposes free-form text into the structured flags above.
- Reservation filters, detail fetching, and page selection are available in the Python API and MCP tools, but are not currently exposed as CLI flags.

### 🐍 Python Library

#### Simple search

```python
from gurume import SortType
from gurume import query_restaurants

restaurants = query_restaurants(
    area="銀座",
    keyword="寿司",
    party_size=2,
    sort_type=SortType.RANKING,
)

for restaurant in restaurants[:3]:
    print(restaurant.name, restaurant.rating, restaurant.url)
```

#### Advanced search with filters

```python
from gurume import PriceRange
from gurume import RestaurantSearchRequest
from gurume import SortType

request = RestaurantSearchRequest(
    area="渋谷",
    keyword="焼肉",
    reservation_date="20250715",
    reservation_time="1900",
    party_size=4,
    sort_type=SortType.RANKING,
    price_range=PriceRange.DINNER_4000_5000,
    online_booking_only=True,
    has_private_room=True,
)

restaurants = request.search_sync()
print(f"Found {len(restaurants)} restaurants")
```

#### Async search with metadata

```python
import asyncio

from gurume import SearchRequest


async def main() -> None:
    request = SearchRequest(
        area="新宿",
        keyword="居酒屋",
        max_pages=2,
        include_meta=True,
    )

    response = await request.search()
    print(response.status)
    print(response.meta.total_count if response.meta else None)

    for restaurant in response.restaurants[:5]:
        print(restaurant.name, restaurant.review_count)


asyncio.run(main())
```

#### Restaurant detail scraping

```python
from gurume import RestaurantDetailRequest

detail = RestaurantDetailRequest(
    restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
    fetch_reviews=True,
    fetch_menu=True,
    fetch_courses=True,
    max_review_pages=2,
).fetch_sync()

print(detail.restaurant.name)
print(len(detail.reviews), len(detail.menu_items), len(detail.courses))
```

#### Cuisine helpers

```python
from gurume import get_all_genres
from gurume import get_genre_code

print(get_genre_code("すき焼き"))
print(get_all_genres()[:5])
```

## 🤖 MCP Server

Gurume ships a FastMCP server for AI assistants and other MCP-compatible clients.

### ⚙️ MCP Configuration

GitHub development version:

```json
{
  "mcpServers": {
    "gurume": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/narumiruna/gurume",
        "gurume",
        "mcp"
      ]
    }
  }
}
```

PyPI release:

```json
{
  "mcpServers": {
    "gurume": {
      "command": "uvx",
      "args": ["gurume", "mcp"]
    }
  }
}
```

Local development:

```json
{
  "mcpServers": {
    "gurume": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/<user>/workspace/gurume",
        "gurume",
        "mcp"
      ]
    }
  }
}
```

### 🛠️ MCP Tools

1. `tabelog_search_restaurants`
   Search by area, keyword, or cuisine with structured pagination metadata.

   Parameters:

   - `area`: optional area, prefecture, city, or station name
   - `keyword`: optional free-text keyword for restaurant names or general matching
   - `cuisine`: optional cuisine name in Japanese for precise genre filtering
   - `sort`: `ranking`, `review-count`, `new-open`, `standard`
   - `limit`: 1 to 60, default `20`
   - `page`: 1-based page number, default `1`
   - `reservation_date`: `YYYYMMDD`
   - `reservation_time`: `HHMM`
   - `party_size`: positive integer

   Returns a structured `RestaurantSearchOutput` envelope with:

   - `status`
   - `items`
   - `returned_count`
   - `limit`
   - `has_more`
   - `meta`
   - `applied_filters`
   - `warnings`
   - `error`

2. `tabelog_list_cuisines`
   Return the supported cuisine list as structured data.

3. `tabelog_get_restaurant_details`
   Fetch a restaurant detail page and optionally collect reviews, menu items, and courses.

   Parameters:

   - `restaurant_url`: required Tabelog restaurant URL
   - `fetch_reviews`: default `true`
   - `fetch_menu`: default `true`
   - `fetch_courses`: default `true`
   - `max_review_pages`: minimum `1`, default `1`

4. `tabelog_get_area_suggestions`
   Return structured area and station suggestions from Tabelog.

5. `tabelog_get_keyword_suggestions`
   Return structured keyword suggestions for cuisines, restaurant names, and combined terms.

### 📋 Recommended MCP Workflow

1. Validate the area with `tabelog_get_area_suggestions` when the user input is ambiguous.
2. Validate cuisines or restaurant names with `tabelog_get_keyword_suggestions`.
3. Call `tabelog_search_restaurants` with normalized values.
4. Continue with `page + 1` when `meta.has_next_page` is true.
5. Call `tabelog_get_restaurant_details` for shortlisted restaurants.

### ⚠️ Error Model

All MCP tools return structured error data instead of relying on free-form exception text.

Current stable error codes:

- `invalid_parameters`
- `unsupported_cuisine`
- `upstream_unavailable`
- `internal_error`

When `status="error"`, inspect `error.error_code`, `error.retryable`, and `error.suggested_action` first.

### 🧪 Testing the MCP Server

```bash
# Run the MCP test suite
uv run pytest -q tests/test_server.py

# Start the server locally (stdio, default)
uv run gurume mcp

# Inspect tools and schemas interactively
npx @modelcontextprotocol/inspector uv run gurume mcp
```

### 🌐 HTTP transport

`gurume mcp` can also run as an HTTP server for clients that speak streamable
HTTP (or SSE):

```bash
# Streamable HTTP (recommended; endpoint at http://127.0.0.1:8000/mcp)
uv run gurume mcp --transport streamable-http

# Custom bind address, port, and path
uv run gurume mcp --transport streamable-http --host 0.0.0.0 --port 9001 --path /api/mcp

# Server-Sent Events transport
uv run gurume mcp --transport sse --port 8765 --path /events
```

Security note: the default bind is `127.0.0.1`. Use `--host 0.0.0.0` only on
trusted networks; the MCP endpoint has no built-in authentication.

## 🖥️ TUI

Start the Textual TUI with:

```bash
uv run gurume tui
```

Or:

```bash
python -m gurume.tui
```

The TUI includes:

- a two-column layout with search results and a detail panel
- area suggestions with `F2`
- keyword and cuisine suggestions with `F3`
- automatic cuisine detection for direct cuisine-name input
- visible sort controls and keyboard navigation

Detailed TUI documentation lives in [`docs/TUI_USAGE.md`](docs/TUI_USAGE.md).

## 🧩 Agent Skill

This repo ships an agent skill at [`skills/gurume-cli/`](skills/gurume-cli/) that teaches AI coding assistants (Claude Code, Codex CLI, etc.) when and how to call the `gurume` CLI for restaurant search on Tabelog.

Install it with [`skills`](https://www.npmjs.com/package/skills):

```bash
npx skills add narumiruna/gurume
```

This pulls `skills/gurume-cli/` into your local agent skills directory. After installing, your agent will reach for `gurume` automatically whenever you ask it to find restaurants in Japan — by area, cuisine, or a vague "where should I eat" prompt.

## 📁 Examples

See the `examples/` directory for runnable scripts:

- `examples/basic_search.py`: simple, advanced, and async search examples
- `examples/restaurant_detail.py`: restaurant detail scraping examples
- `examples/cli_example.py`: standalone example CLI built on the Python API

## 📝 Notes and Limitations

- Gurume scrapes Tabelog pages and internal suggestion endpoints. Upstream HTML or API changes may break parsing.
- Tabelog data is primarily Japanese. Even when user input is multilingual, normalized search values and many results are Japanese.
- Natural-language input is no longer parsed inside the CLI/TUI. Use the [`gurume-cli` agent skill](skills/gurume-cli/) with an AI assistant to translate free-form text into structured flags.
- Reservation-related search results reflect Tabelog availability data and may change over time.
- Use the library responsibly and avoid excessive request volume.

## ⚖️ Legal and Ethical Use

This project is intended for educational and research use.

- Respect Tabelog terms of service and robots policies.
- Do not send excessive or abusive traffic.
- Add your own rate limiting and operational safeguards for production use.

## 📄 License

MIT License

## 🤝 Contributing

Contributions are welcome. Please open an issue or submit a pull request.
