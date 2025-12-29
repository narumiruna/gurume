# Tabelog

A Python library for searching restaurants on Tabelog using web scraping.

## Features

- **Comprehensive Search**: Search by area, keyword, cuisine type, date, time, party size, and more
- **Cuisine Type Filtering**: Accurate filtering by 45+ Japanese cuisine genres (すき焼き, 寿司, ラーメン, etc.) (新!)
- **Rich Data**: Extract restaurant details including ratings, reviews, prices, and availability
- **Interactive TUI**: Beautiful terminal UI for interactive restaurant search (新!)
  - **Area Suggestion**: Smart area/station suggestions with F2 key (新!)
  - **Cuisine Selection**: Browse and select from 45+ cuisine types with F4 key (新!)
  - **Auto-Detection**: Automatically detects cuisine types in keyword input (新!)
  - **Accurate Area Filtering**: Prefecture-level filtering for all 47 prefectures (新!)
- **Async Support**: Both synchronous and asynchronous API
- **Type Safe**: Full type hints with type checking
- **Flexible**: Multiple search interfaces from simple to advanced
- **Easy to Use**: Simple and intuitive API


## Usage

### GitHub

```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/narumiruna/tabelog-mcp",
        "tabelog"
      ]
    }
  }
}
```

### PyPI

```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uvx",
      "args": ["tabelog@latest"]
    }
  }
}
```

### Local

```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/<user>/workspace/tabelog-mcp",
        "tabelog"
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

### Interactive TUI (推薦!)

啟動美觀的終端介面來搜尋餐廳：

```bash
# 使用 uv
uv run tabelog tui

# 或直接使用 Python
python -m tabelog.tui
```

TUI 特色：
- 🎨 簡潔美觀的深色主題
- 🔍 即時搜尋結果（地區、關鍵字、料理類別、排序）
- 📊 雙欄式顯示（結果列表 + 詳細資訊）
- ⌨️  完整鍵盤導航支援
- 🚀 自動取消前次搜尋，避免卡住
- 🗺️ **智慧型地區建議（F2）**：自動提供都道府縣、車站、地區選項
- 🍽️ **料理類別選擇（F4）**：瀏覽並選擇 45+ 種日本料理類型（すき焼き、寿司、ラーメン等）
- 🤖 **自動料理識別**：在關鍵字欄位輸入料理名稱，自動轉換為精確過濾
- ✅ **準確地區過濾**：支援 47 個都道府縣的地區限制

詳細使用說明請參考 [TUI_USAGE.md](TUI_USAGE.md)

### Basic Search (程式庫)

```python
from tabelog import query_restaurants, SortType, get_genre_code

# Quick search with keyword
restaurants = query_restaurants(
    area="銀座",
    keyword="寿司",
    party_size=2,
    sort_type=SortType.RANKING,
)

for restaurant in restaurants:
    print(f"{restaurant.name} - {restaurant.rating}")

# Search with cuisine type filtering (更精確!)
from tabelog import RestaurantSearchRequest

genre_code = get_genre_code("すき焼き")  # RC0107
request = RestaurantSearchRequest(
    area="三重",
    genre_code=genre_code,
    sort_type=SortType.RANKING,
)

restaurants = request.search_sync()
for restaurant in restaurants:
    print(f"{restaurant.name} - {restaurant.rating}")
    print(f"  類型: {', '.join(restaurant.genres)}")
```

### Advanced Search

```python
from tabelog import RestaurantSearchRequest, SortType, PriceRange, get_genre_code

# Detailed search with filters
request = RestaurantSearchRequest(
    area="渋谷",
    keyword="焼肉",
    genre_code=get_genre_code("焼肉"),  # 精確過濾焼肉專門店
    reservation_date="20250715",
    reservation_time="1900",
    party_size=4,
    sort_type=SortType.RANKING,
    price_range=PriceRange.DINNER_4000_5000,
    online_booking_only=True,
    has_private_room=True,
)

restaurants = request.search_sync()

# 瀏覽所有支援的料理類別
from tabelog import get_all_genres

all_genres = get_all_genres()
print(f"支援 {len(all_genres)} 種料理類別:")
print(all_genres)
# ['うどん', 'うなぎ', 'すき焼き', 'そば', 'とんかつ', ...]
```

### Async Search with Metadata

```python
import asyncio
from tabelog import SearchRequest, get_genre_code

async def search_example():
    request = SearchRequest(
        area="新宿",
        keyword="居酒屋",
        genre_code=get_genre_code("居酒屋"),  # 精確過濾居酒屋
        max_pages=3,
        include_meta=True,
    )

    response = await request.search()

    print(f"Status: {response.status}")
    print(f"Total results: {response.meta.total_count}")
    print(f"Found {len(response.restaurants)} restaurants")

    for restaurant in response.restaurants:
        print(f"- {restaurant.name} ({restaurant.rating})")
        print(f"  類型: {', '.join(restaurant.genres)}")

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
