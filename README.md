# Tabelog

A Python library for searching restaurants on Tabelog using web scraping.

## Features

- **Comprehensive Search**: Search by area, keyword, cuisine type, date, time, party size, and more
- **Cuisine Type Filtering**: Accurate filtering by 45+ Japanese cuisine genres (すき焼き, 寿司, ラーメン, etc.) (新!)
- **Rich Data**: Extract restaurant details including ratings, reviews, prices, and availability
- **Interactive TUI**: Beautiful terminal UI for interactive restaurant search (新!)
  - **Area Suggestion**: Smart area/station suggestions with F2 key (新!)
  - **Intelligent Keyword Suggestion (F3)**: Context-aware suggestions - static cuisine list when empty, dynamic API results when typing (新!)
  - **AI Natural Language Parsing (F4)**: Parse natural language queries with AI (新!)
  - **Auto-Detection**: Automatically detects cuisine types in keyword input (新!)
  - **Accurate Area Filtering**: Prefecture-level filtering for all 47 prefectures (新!)
- **Async Support**: Both synchronous and asynchronous API
- **Type Safe**: Full type hints with type checking
- **Flexible**: Multiple search interfaces from simple to advanced
- **Easy to Use**: Simple and intuitive API


## Usage

### MCP Server (for Claude Desktop / AI Assistants)

The Tabelog MCP server provides restaurant search functionality to AI assistants like Claude.

**GitHub (Latest Development Version)**:
```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/narumiruna/tabelog",
        "tabelog-mcp"
      ]
    }
  }
}
```

**PyPI (Stable Release)**:
```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uvx",
      "args": ["--from", "tabelog", "tabelog-mcp"]
    }
  }
}
```

**Local Development**:
```json
{
  "mcpServers": {
    "tabelog": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/home/<user>/workspace/tabelog",
        "tabelog-mcp"
      ]
    }
  }
}
```

**Available Tools**:
- `search_restaurants`: Search restaurants by area, keyword, or cuisine type
- `list_cuisines`: Get all 45+ supported Japanese cuisine types with genre codes
- `get_area_suggestions`: Get area/station suggestions from Tabelog API
- `get_keyword_suggestions`: Get keyword/cuisine/restaurant name suggestions

**Design Principles**:
- ✅ **Zero Configuration**: No API keys required
- ✅ **Simple Parameters**: Direct structured inputs (area, keyword, cuisine)
- ✅ **Client-Side NLP**: AI clients handle natural language parsing
- ✅ **Accurate Filtering**: Uses Tabelog genre codes for precise cuisine filtering


## Installation

```bash
uv add tabelog
```

Or with pip:

```bash
pip install tabelog
```

## Quick Start

### Command Line Interface (CLI)

使用命令列快速搜尋餐廳：

```bash
# 基本搜尋
tabelog search --area 東京 --keyword 寿司

# 使用料理類別精確過濾
tabelog search -a 三重 -c すき焼き

# 指定排序方式和輸出格式
tabelog search -a 大阪 -c ラーメン --sort ranking -o json

# 🆕 使用自然語言查詢（AI 自動解析地區和關鍵字）
tabelog search -q 三重すきやき
tabelog search -q "我想吃東京的拉麵"
tabelog search -q "sushi in Osaka"

# 查看所有支援的料理類別
tabelog list-cuisines

# 查看完整說明
tabelog search --help
```

**CLI 選項：**
- `-a, --area`: 搜尋地區（例如：東京、大阪）
- `-k, --keyword`: 關鍵字（例如：寿司、ラーメン）
- `-c, --cuisine`: 料理類別（例如：すき焼き、焼肉）- 自動精確過濾
- `-q, --query`: 🆕 自然語言查詢（會自動解析地區和關鍵字，支援多語言）
- `-s, --sort`: 排序方式（ranking, review-count, new-open, standard）
- `-n, --limit`: 顯示結果數量（預設：20）
- `-o, --output`: 輸出格式（table, json, simple）

**自然語言查詢功能 (-q):**
- ✅ 支援多語言輸入（中文、日文、英文等）
- ✅ 自動解析地區和料理類型
- ✅ 智慧型翻譯（例如：「壽喜燒」→「すき焼き」）
- ⚠️ 需要設定 OpenAI API 金鑰（`.env` 檔案中的 `OPENAI_API_KEY`）

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
- 🍽️ **智慧型關鍵字建議（F3）**（新！）：
  - 關鍵字為空 → 顯示 45+ 種料理類別列表（すき焼き、寿司、ラーメン等）
  - 關鍵字有內容 → 呼叫 API 提供動態建議（料理類型、餐廳名稱、組合關鍵字）
- 🤖 **AI 自然語言解析（F4）**：輸入自然語言（例如：三重的すき焼き），自動解析並觸發建議
- ✨ **智慧聯動**：AI 解析後自動觸發地區建議（F2）或料理選擇（F3）
- 🎯 **自動料理識別**：在關鍵字欄位輸入料理名稱，自動轉換為精確過濾
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
