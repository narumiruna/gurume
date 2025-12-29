"""MCP Server for Tabelog restaurant search

This module provides a Model Context Protocol (MCP) server that exposes
Tabelog search functionality to AI assistants like Claude.

Design principles:
- No AI parsing required (no OpenAI API key dependency)
- Simple, structured parameters
- Zero configuration
- Client-side natural language handling
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
from mcp.types import Tool

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .restaurant import SortType
from .search import SearchRequest
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async

# Create MCP server instance
server = Server("gurume")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools

    Returns:
        List of tool definitions with name, description, and input schema
    """
    return [
        Tool(
            name="search_restaurants",
            description=(
                "Search for restaurants on Tabelog with precise filtering by area, cuisine type, or keywords.\n\n"
                "**WHEN TO USE**:\n"
                "- Finding restaurants in a specific area or cuisine type\n"
                "- Getting top-rated restaurants based on Tabelog rankings\n"
                "- Searching for specific restaurant names or keywords\n\n"
                "**PARAMETER GUIDE**:\n"
                "- `area`: Geographic filtering (e.g., '東京', '大阪', '三重')\n"
                "  - USE: Prefecture names for most accurate results (e.g., '東京都', '大阪府')\n"
                "  - Supports 47 prefectures + major cities\n"
                "  - Returns nationwide results if area cannot be mapped\n\n"
                "- `cuisine`: Precise cuisine type filtering (RECOMMENDED for cuisine searches)\n"
                "  - USE: When looking for restaurants specializing in a specific cuisine\n"
                "  - Uses Tabelog genre codes for accurate filtering\n"
                "  - Examples: 'すき焼き', '焼肉', '寿司', 'ラーメン', '居酒屋'\n"
                "  - Returns only restaurants categorized under that cuisine type\n\n"
                "- `keyword`: General keyword search\n"
                "  - USE: When searching by restaurant name, specific dishes, or other keywords\n"
                "  - Searches in restaurant names, descriptions, reviews, etc.\n"
                "  - Less precise than `cuisine` for cuisine-type searches\n\n"
                "**IMPORTANT**: `cuisine` parameter provides more accurate results than using cuisine names in `keyword`.\n"
                "Example: Use `cuisine='すき焼き'` instead of `keyword='すき焼き'` to find sukiyaki specialists.\n\n"
                "**BEST PRACTICES**:\n"
                "1. Combine `area` + `cuisine` for most precise results (e.g., Tokyo sukiyaki restaurants)\n"
                "2. Use `cuisine` parameter for cuisine-specific searches, not `keyword`\n"
                "3. Use `keyword` only for restaurant names or non-cuisine searches\n"
                "4. Call `list_cuisines` first to verify supported cuisine types\n"
                "5. Call `get_area_suggestions` if user's area name is ambiguous\n\n"
                "**RETURN FORMAT**:\n"
                "Returns JSON array of restaurants with:\n"
                "- name: Restaurant name\n"
                "- rating: Tabelog rating (0.0-5.0)\n"
                "- review_count: Number of reviews\n"
                "- area: Location area\n"
                "- genres: List of cuisine genres\n"
                "- url: Tabelog restaurant page URL\n"
                "- lunch_price: Lunch price range (or null)\n"
                "- dinner_price: Dinner price range (or null)\n\n"
                "**EXAMPLES**:\n"
                "1. Find sukiyaki restaurants in Mie: area='三重', cuisine='すき焼き'\n"
                "2. Find top ramen shops in Tokyo: area='東京', cuisine='ラーメン', sort='ranking'\n"
                "3. Search for a specific restaurant: keyword='和田金'\n"
                "4. Find new restaurants in Osaka: area='大阪', sort='new-open'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": (
                            "Geographic area to search (prefecture, city, or region name). "
                            "Examples: '東京', '大阪府', '三重', '京都'. "
                            "Prefecture names (e.g., '東京都') provide most accurate filtering. "
                            "If the area cannot be mapped, returns nationwide results."
                        ),
                    },
                    "keyword": {
                        "type": "string",
                        "description": (
                            "General keyword search for restaurant names or other terms. "
                            "Examples: '和田金' (restaurant name), 'コスパ' (value for money). "
                            "NOTE: For cuisine type searches, use the 'cuisine' parameter instead for better accuracy."
                        ),
                    },
                    "cuisine": {
                        "type": "string",
                        "description": (
                            "Precise cuisine type filtering using Tabelog genre codes. "
                            "This parameter is HIGHLY RECOMMENDED for cuisine-specific searches. "
                            "Examples: 'すき焼き', '焼肉', '寿司', 'ラーメン', '居酒屋', 'イタリアン'. "
                            "Returns only restaurants categorized under that specific cuisine type. "
                            "Use 'list_cuisines' tool to see all 45+ supported cuisine types."
                        ),
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["ranking", "review-count", "new-open", "standard"],
                        "default": "ranking",
                        "description": (
                            "Result sorting method:\n"
                            "- 'ranking': Sort by Tabelog rating (highest first) - RECOMMENDED\n"
                            "- 'review-count': Sort by number of reviews (most reviewed first)\n"
                            "- 'new-open': Sort by opening date (newest first)\n"
                            "- 'standard': Tabelog default sorting (relevance)"
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 60,
                        "description": "Maximum number of results to return (default: 20, max: 60)",
                    },
                },
            },
        ),
        Tool(
            name="list_cuisines",
            description=(
                "Get complete list of all 45+ supported Japanese cuisine types with their Tabelog genre codes.\n\n"
                "**WHEN TO USE**:\n"
                "- Before calling `search_restaurants` with `cuisine` parameter to verify available options\n"
                "- Providing cuisine type suggestions/autocomplete to users\n"
                "- Validating user's cuisine input against supported types\n"
                "- Building UI dropdown menus or selection lists\n\n"
                "**RETURN FORMAT**:\n"
                "Returns JSON array of all supported cuisines:\n"
                "- name: Cuisine name in Japanese (e.g., 'すき焼き', '焼肉', 'ラーメン')\n"
                "- code: Tabelog genre code (e.g., 'RC0107', 'RC0103') - used internally for filtering\n\n"
                "**CUISINE CATEGORIES** (45+ types total):\n"
                "- Japanese: すき焼き, 焼肉, 寿司, ラーメン, うなぎ, そば, うどん, 天ぷら, とんかつ, 焼き鳥, お好み焼き, たこ焼き\n"
                "- Hotpot/Nabe: しゃぶしゃぶ, もつ鍋, 水炊き\n"
                "- Izakaya: 居酒屋, 焼酎バー, 日本酒バー\n"
                "- Western: イタリアン, フレンチ, スペイン料理, ハンバーガー, ステーキ\n"
                "- Asian: 中華料理, 韓国料理, タイ料理, インド料理, ベトナム料理\n"
                "- Other: カレー, カフェ, スイーツ, パン, ラーメン\n\n"
                "**WORKFLOW EXAMPLE**:\n"
                "1. User asks: 'Find sukiyaki restaurants in Tokyo'\n"
                "2. Call `list_cuisines` to verify 'すき焼き' is supported → Returns {name: 'すき焼き', code: 'RC0107'}\n"
                "3. Call `search_restaurants` with area='東京', cuisine='すき焼き'\n\n"
                "**NO INPUT REQUIRED**: This tool takes no parameters, simply call it to get the full list."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_area_suggestions",
            description=(
                "Get geographic area and station suggestions from Tabelog's autocomplete API.\n\n"
                "**WHEN TO USE**:\n"
                "- User provides ambiguous or partial area name (e.g., '渋谷', 'しぶや', 'shibuya')\n"
                "- Implementing autocomplete/typeahead for area input\n"
                "- Validating and standardizing area names before search\n"
                "- Helping users discover nearby stations or regions\n\n"
                "**INPUT**:\n"
                "- `query`: Partial or complete area name in Japanese, hiragana, or romaji\n"
                "  - Examples: '東京' (complete), '渋' (partial), 'とうきょう' (hiragana), 'ise' (romaji)\n"
                "  - Minimum 1 character, works best with 2+ characters\n\n"
                "**RETURN FORMAT**:\n"
                "Returns JSON array of area suggestions with:\n"
                "- name: Display name (e.g., '東京都', '渋谷駅', '伊勢市')\n"
                "- datatype: Suggestion type (see below)\n"
                "- id_in_datatype: Unique identifier within datatype\n"
                "- lat: Latitude (decimal degrees, may be null)\n"
                "- lng: Longitude (decimal degrees, may be null)\n\n"
                "**DATATYPE VALUES**:\n"
                "- 'AddressMaster': Prefecture, city, or district (e.g., '東京都', '渋谷区', '伊勢市')\n"
                "  - Use for broad geographic searches\n"
                "  - Usually includes coordinates\n"
                "- 'RailroadStation': Train/subway station (e.g., '渋谷駅', '伊勢市駅')\n"
                "  - Use for searches near specific stations\n"
                "  - Always includes coordinates\n\n"
                "**WORKFLOW EXAMPLE**:\n"
                "1. User input: '渋谷でラーメン屋を探して'\n"
                "2. Call `get_area_suggestions` with query='渋谷'\n"
                "3. Review results: [{name: '渋谷区', datatype: 'AddressMaster'}, {name: '渋谷駅', datatype: 'RailroadStation'}]\n"
                "4. Select appropriate suggestion (e.g., '渋谷区' for broader search, '渋谷駅' for station-area search)\n"
                "5. Call `search_restaurants` with area='渋谷区' or area='渋谷駅'\n\n"
                "**TIPS**:\n"
                "- API returns up to 10 suggestions, ordered by relevance\n"
                "- For prefecture-level searches, use full name (e.g., '東京都', '大阪府', '三重県')\n"
                "- Station names usually end with '駅' (eki)\n"
                "- May return empty array if no matches found"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Area search query (partial or complete). "
                            "Accepts Japanese (東京), hiragana (とうきょう), or romaji (tokyo). "
                            "Examples: '東京', '渋谷', '伊勢', 'しぶや', 'ise'. "
                            "Minimum 1 character required, 2+ recommended."
                        ),
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_keyword_suggestions",
            description=(
                "Get dynamic keyword, cuisine, and restaurant name suggestions from Tabelog's autocomplete API.\n\n"
                "**WHEN TO USE**:\n"
                "- User provides partial keyword/cuisine name for autocomplete (e.g., 'すき', '寿', 'ramen')\n"
                "- Discovering related cuisine types or specific restaurants\n"
                "- Finding keyword combinations (e.g., 'すき焼き ランチ', '寿司 接待')\n"
                "- Implementing typeahead/autocomplete for keyword search\n\n"
                "**vs list_cuisines**: Use this for dynamic autocomplete based on user input; use `list_cuisines` for complete static list\n\n"
                "**INPUT**:\n"
                "- `query`: Partial or complete keyword in Japanese, hiragana, or romaji\n"
                "  - Examples: 'すき' (partial), '寿司' (complete), 'らーめん' (hiragana), 'wada' (romaji)\n"
                "  - Minimum 1 character, works best with 2+ characters\n\n"
                "**RETURN FORMAT**:\n"
                "Returns JSON array of keyword suggestions with:\n"
                "- name: Suggestion text (e.g., 'すき焼き', '和田金', 'すき焼き ランチ')\n"
                "- datatype: Suggestion category (see below)\n"
                "- id_in_datatype: Unique identifier within datatype\n"
                "- lat: Latitude (usually null for keywords)\n"
                "- lng: Longitude (usually null for keywords)\n\n"
                "**DATATYPE VALUES** (3 types):\n\n"
                "1. **'Genre2'**: Cuisine/genre type\n"
                "   - Examples: 'すき焼き', '寿司', 'ラーメン', '焼肉'\n"
                "   - USE WITH: `search_restaurants` cuisine parameter for precise filtering\n"
                "   - Best for: Finding restaurants specializing in that cuisine\n\n"
                "2. **'Restaurant'**: Specific restaurant name\n"
                "   - Examples: '和田金', 'すきやき割烹 美川', '次郎'\n"
                "   - USE WITH: `search_restaurants` keyword parameter\n"
                "   - Best for: Finding a known restaurant by name\n\n"
                "3. **'Genre2 DetailCondition'**: Cuisine + condition/modifier\n"
                "   - Examples: 'すき焼き ランチ' (sukiyaki lunch), '寿司 接待' (sushi business dinner), 'ラーメン 深夜' (ramen late-night)\n"
                "   - USE WITH: Parse into separate parameters (cuisine + keyword or other filters)\n"
                "   - Best for: Discovering popular search combinations\n\n"
                "**WORKFLOW EXAMPLES**:\n\n"
                "Example 1 - Cuisine autocomplete:\n"
                "1. User types: 'すき'\n"
                "2. Call `get_keyword_suggestions` with query='すき'\n"
                "3. Review results: [{name: 'すき焼き', datatype: 'Genre2'}, {name: 'すきやき割烹 美川', datatype: 'Restaurant'}]\n"
                "4. User selects 'すき焼き' (Genre2)\n"
                "5. Call `search_restaurants` with cuisine='すき焼き'\n\n"
                "Example 2 - Restaurant name search:\n"
                "1. User types: 'wada'\n"
                "2. Call `get_keyword_suggestions` with query='wada'\n"
                "3. Review results: [{name: '和田金', datatype: 'Restaurant'}]\n"
                "4. User confirms '和田金'\n"
                "5. Call `search_restaurants` with keyword='和田金'\n\n"
                "Example 3 - Keyword combination:\n"
                "1. User types: 'すき焼き'\n"
                "2. Call `get_keyword_suggestions` with query='すき焼き'\n"
                "3. Review results: [{name: 'すき焼き ランチ', datatype: 'Genre2 DetailCondition'}]\n"
                "4. Parse 'ランチ' as a lunch preference\n"
                "5. Call `search_restaurants` with cuisine='すき焼き' + lunch price filter\n\n"
                "**TIPS**:\n"
                "- API returns up to 10 suggestions, ordered by popularity/relevance\n"
                "- Suggestions are context-aware based on popular Tabelog searches\n"
                "- Genre2 suggestions can be used directly with `search_restaurants` cuisine parameter\n"
                "- Restaurant suggestions should use keyword parameter for accurate matching\n"
                "- DetailCondition suggestions reveal popular search patterns (e.g., 'ランチ', '接待', '深夜')\n"
                "- May return empty array if no matches found or query too short"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Keyword search query (partial or complete). "
                            "Accepts Japanese (すき焼き), hiragana (すきやき), or romaji (sukiyaki). "
                            "Examples: 'すき', '寿司', 'ラーメン', 'wada', 'らーめん'. "
                            "Minimum 1 character required, 2+ recommended for better results."
                        ),
                    }
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls

    Args:
        name: Tool name to call
        arguments: Tool arguments

    Returns:
        List of text content results
    """
    if name == "search_restaurants":
        return await _search_restaurants(arguments)
    elif name == "list_cuisines":
        return await _list_cuisines()
    elif name == "get_area_suggestions":
        return await _get_area_suggestions(arguments)
    elif name == "get_keyword_suggestions":
        return await _get_keyword_suggestions(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _search_restaurants(arguments: dict[str, Any]) -> list[TextContent]:
    """Search restaurants implementation"""
    area = arguments.get("area")
    keyword = arguments.get("keyword")
    cuisine = arguments.get("cuisine")
    sort = arguments.get("sort", "ranking")
    limit = arguments.get("limit", 20)

    # Validate and convert sort parameter
    sort_map = {
        "ranking": SortType.RANKING,
        "review-count": SortType.REVIEW_COUNT,
        "new-open": SortType.NEW_OPEN,
        "standard": SortType.STANDARD,
    }
    sort_type = sort_map.get(sort.lower(), SortType.RANKING)

    # Get genre code if cuisine is specified
    genre_code = None
    if cuisine:
        genre_code = get_genre_code(cuisine)

    # Create search request
    request = SearchRequest(
        area=area,
        keyword=keyword,
        genre_code=genre_code,
        sort_type=sort_type,
        max_pages=1,  # Only fetch first page for MCP
    )

    # Execute search
    response = await request.search()

    # Convert restaurants to dict format
    restaurants = []
    for r in response.restaurants[:limit]:
        restaurants.append(
            {
                "name": r.name,
                "rating": r.rating,
                "review_count": r.review_count,
                "area": r.area,
                "genres": r.genres,
                "url": r.url,
                "lunch_price": r.lunch_price,
                "dinner_price": r.dinner_price,
            }
        )

    # Format result
    import json

    result_text = json.dumps(restaurants, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=result_text)]


async def _list_cuisines() -> list[TextContent]:
    """List cuisines implementation"""
    cuisines = get_all_genres()
    result = [{"name": cuisine, "code": get_genre_code(cuisine) or ""} for cuisine in cuisines]

    import json

    result_text = json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=result_text)]


async def _get_area_suggestions(arguments: dict[str, Any]) -> list[TextContent]:
    """Get area suggestions implementation"""
    query = arguments.get("query", "")

    suggestions = await get_area_suggestions_async(query)
    result = [
        {
            "name": s.name,
            "datatype": s.datatype,
            "id_in_datatype": s.id_in_datatype,
            "lat": s.lat,
            "lng": s.lng,
        }
        for s in suggestions
    ]

    import json

    result_text = json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=result_text)]


async def _get_keyword_suggestions(arguments: dict[str, Any]) -> list[TextContent]:
    """Get keyword suggestions implementation"""
    query = arguments.get("query", "")

    suggestions = await get_keyword_suggestions_async(query)
    result = [
        {
            "name": s.name,
            "datatype": s.datatype,
            "id_in_datatype": s.id_in_datatype,
            "lat": s.lat,
            "lng": s.lng,
        }
        for s in suggestions
    ]

    import json

    result_text = json.dumps(result, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=result_text)]


async def main() -> None:
    """Main entry point for MCP server

    Runs the server using stdio transport for communication with MCP clients.
    """
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run() -> None:
    """Synchronous entry point for CLI

    This function is called when running 'gurume mcp' command.
    """
    asyncio.run(main())


if __name__ == "__main__":
    run()
