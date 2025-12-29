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
server = Server("tabelog")


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
                "Search restaurants on Tabelog by area, keyword, or cuisine type. "
                "Returns restaurant details including name, rating, reviews, area, genres, URL, and prices. "
                "Supports accurate cuisine filtering using genre codes (e.g., すき焼き専門店)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "area": {
                        "type": "string",
                        "description": "Search area (e.g., '東京', '大阪', '三重'). Prefecture names recommended for accurate filtering.",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Search keyword (e.g., '寿司', 'ラーメン'). Can be cuisine type, restaurant name, or other keywords.",
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "Cuisine type for precise filtering (e.g., 'すき焼き', '焼肉'). Uses genre codes for accurate results.",
                    },
                    "sort": {
                        "type": "string",
                        "enum": ["ranking", "review-count", "new-open", "standard"],
                        "default": "ranking",
                        "description": "Sort type: 'ranking' (by rating), 'review-count', 'new-open', or 'standard'",
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 60,
                        "description": "Maximum number of results to return (default: 20)",
                    },
                },
            },
        ),
        Tool(
            name="list_cuisines",
            description=(
                "Get all 45+ supported Japanese cuisine types with their genre codes. "
                "Use this for autocomplete, suggestions, or letting users select from available cuisines. "
                "Returns cuisine names (e.g., 'すき焼き') and their genre codes (e.g., 'RC0107')."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_area_suggestions",
            description=(
                "Get area/station suggestions from Tabelog's suggest API. "
                "Helps users find correct area names for accurate search results. "
                "Returns suggestions for prefectures, cities, and stations with coordinates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Area search query (e.g., '東京', '渋谷', '伊勢')",
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_keyword_suggestions",
            description=(
                "Get keyword/cuisine/restaurant name suggestions from Tabelog's suggest API. "
                "Returns dynamic suggestions including cuisine types (Genre2), restaurant names (Restaurant), "
                "and keyword combinations (Genre2 DetailCondition like 'すき焼き ランチ')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword search query (e.g., 'すき', '寿司')",
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

    This function is called when running 'tabelog-mcp' command.
    """
    asyncio.run(main())


if __name__ == "__main__":
    run()
