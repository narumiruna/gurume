# Tabelog

A Python library for searching restaurants on Tabelog using web scraping.

## Features

- Comprehensive Search: Search by area, keyword, date, time, party size, and more
- Rich Data: Extract restaurant details including ratings, reviews, prices, and availability
- Async Support: Both synchronous and asynchronous API
- Type Safe: Full type hints with Pydantic models
- Flexible: Multiple search interfaces from simple to advanced
- Easy to Use: Simple API inspired by the wisest library


## Usage

### GitHub

```json
{
  "mcpServers": {
    "tabelogmcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/narumiruna/tabelog-mcp",
        "tabelogmcp"
      ]
    }
  }
}
```

### PyPI

```json
{
  "mcpServers": {
    "tabelogmcp": {
      "command": "uvx",
      "args": ["tabelogmcp@latest"]
    }
  }
}
```

### Local

```json
{
  "mcpServers": {
    "tabelogmcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/<user>/workspace/tabelog-mcp",
        "tabelogmcp"
      ]
    }
  }
}
```


## Installation

```bash
uv add tabelog
```

Or with pip:

```bash
pip install tabelog
```

## Quick Start

### Basic Search

```python
from tabelog import query_restaurants, SortType

# Quick search
restaurants = query_restaurants(
    area="銀座",
    keyword="寿司",
    party_size=2,
    sort_type=SortType.RANKING,
)

for restaurant in restaurants:
    print(f"{restaurant.name} - {restaurant.rating}")
```

### Advanced Search

```python
from tabelog import RestaurantSearchRequest, SortType, PriceRange

# Detailed search with filters
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

restaurants = request.do_sync()
```

### Async Search with Metadata

```python
import asyncio
from tabelog import SearchRequest

async def search_example():
    request = SearchRequest(
        area="新宿",
        keyword="居酒屋",
        max_pages=3,
        include_meta=True,
    )

    response = await request.do()

    print(f"Status: {response.status}")
    print(f"Total results: {response.meta.total_count}")
    print(f"Found {len(response.restaurants)} restaurants")

    for restaurant in response.restaurants:
        print(f"- {restaurant.name} ({restaurant.rating})")

asyncio.run(search_example())
```

## Examples

See the `examples/` directory for more detailed examples:

- `basic_search.py`: Basic usage examples
- `cli_example.py`: Command-line interface example

## Important Notes

Legal Compliance: This library is for educational and research purposes. Make sure to:
- Respect Tabelog's robots.txt and terms of service
- Don't make excessive requests that could overload their servers
- Consider rate limiting in production use
- Use responsibly and ethically

Web Scraping: This library scrapes Tabelog's web interface. The structure may change without notice, which could break functionality.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
