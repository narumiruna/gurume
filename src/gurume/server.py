"""MCP Server for Tabelog restaurant search using FastMCP

This module provides a Model Context Protocol (MCP) server that exposes
Tabelog search functionality to AI assistants like Claude.

Design principles:
- FastMCP framework for automatic schema generation
- Structured Pydantic models for type-safe responses
- Comprehensive error handling with actionable messages
- Read-only operations with proper annotations
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel
from pydantic import Field

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .restaurant import SortType
from .search import SearchRequest
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async

# Create FastMCP server instance
mcp = FastMCP("gurume")


# ============================================================================
# Output Schemas - Pydantic Models
# ============================================================================


class RestaurantOutput(BaseModel):
    """Restaurant search result output schema"""

    name: str = Field(description="Restaurant name")
    rating: float | None = Field(description="Tabelog rating (0.0-5.0)")
    review_count: int | None = Field(description="Number of reviews")
    area: str | None = Field(description="Location area")
    genres: list[str] = Field(description="List of cuisine genres")
    url: str = Field(description="Tabelog restaurant page URL")
    lunch_price: str | None = Field(description="Lunch price range")
    dinner_price: str | None = Field(description="Dinner price range")


class CuisineOutput(BaseModel):
    """Cuisine type output schema"""

    name: str = Field(description="Cuisine name in Japanese")
    code: str = Field(description="Tabelog genre code (e.g., 'RC0107')")


class SuggestionOutput(BaseModel):
    """Area or keyword suggestion output schema"""

    name: str = Field(description="Suggestion display name")
    datatype: str = Field(description="Suggestion type (AddressMaster, RailroadStation, Genre2, Restaurant, etc.)")
    id_in_datatype: str | int = Field(description="Unique identifier within datatype")
    lat: float | None = Field(description="Latitude (decimal degrees)")
    lng: float | None = Field(description="Longitude (decimal degrees)")


# ============================================================================
# Tool Implementations
# ============================================================================


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=True,
    )
)
async def tabelog_search_restaurants(
    area: str | None = None,
    keyword: str | None = None,
    cuisine: str | None = None,
    sort: str = "ranking",
    limit: int = 20,
) -> list[RestaurantOutput]:
    """Search for restaurants on Tabelog with precise filtering by area, cuisine type, or keywords.

    **WHEN TO USE**:
    - Finding restaurants in a specific area or cuisine type
    - Getting top-rated restaurants based on Tabelog rankings
    - Searching for specific restaurant names or keywords

    **PARAMETER GUIDE**:
    - `area`: Geographic filtering (e.g., '東京', '大阪', '三重')
      - USE: Prefecture names for most accurate results (e.g., '東京都', '大阪府')
      - Supports 47 prefectures + major cities
      - Returns nationwide results if area cannot be mapped

    - `cuisine`: Precise cuisine type filtering (RECOMMENDED for cuisine searches)
      - USE: When looking for restaurants specializing in a specific cuisine
      - Uses Tabelog genre codes for accurate filtering
      - Examples: 'すき焼き', '焼肉', '寿司', 'ラーメン', '居酒屋'
      - Returns only restaurants categorized under that cuisine type

    - `keyword`: General keyword search
      - USE: When searching by restaurant name, specific dishes, or other keywords
      - Searches in restaurant names, descriptions, reviews, etc.
      - Less precise than `cuisine` for cuisine-type searches

    **IMPORTANT**: `cuisine` parameter provides more accurate results than using cuisine names in `keyword`.
    Example: Use `cuisine='すき焼き'` instead of `keyword='すき焼き'` to find sukiyaki specialists.

    **BEST PRACTICES**:
    1. Combine `area` + `cuisine` for most precise results (e.g., Tokyo sukiyaki restaurants)
    2. Use `cuisine` parameter for cuisine-specific searches, not `keyword`
    3. Use `keyword` only for restaurant names or non-cuisine searches
    4. Call `tabelog_list_cuisines` first to verify supported cuisine types
    5. Call `tabelog_get_area_suggestions` if user's area name is ambiguous

    **RETURN FORMAT**:
    Returns list of restaurants with:
    - name: Restaurant name
    - rating: Tabelog rating (0.0-5.0)
    - review_count: Number of reviews
    - area: Location area
    - genres: List of cuisine genres
    - url: Tabelog restaurant page URL
    - lunch_price: Lunch price range (or null)
    - dinner_price: Dinner price range (or null)

    **EXAMPLES**:
    1. Find sukiyaki restaurants in Mie: area='三重', cuisine='すき焼き'
    2. Find top ramen shops in Tokyo: area='東京', cuisine='ラーメン', sort='ranking'
    3. Search for a specific restaurant: keyword='和田金'
    4. Find new restaurants in Osaka: area='大阪', sort='new-open'

    Args:
        area: Geographic area to search (prefecture, city, or region name).
            Examples: '東京', '大阪府', '三重', '京都'.
            Prefecture names (e.g., '東京都') provide most accurate filtering.
            If the area cannot be mapped, returns nationwide results.
        keyword: General keyword search for restaurant names or other terms.
            Examples: '和田金' (restaurant name), 'コスパ' (value for money).
            NOTE: For cuisine type searches, use the 'cuisine' parameter instead for better accuracy.
        cuisine: Precise cuisine type filtering using Tabelog genre codes.
            This parameter is HIGHLY RECOMMENDED for cuisine-specific searches.
            Examples: 'すき焼き', '焼肉', '寿司', 'ラーメン', '居酒屋', 'イタリアン'.
            Returns only restaurants categorized under that specific cuisine type.
            Use 'tabelog_list_cuisines' tool to see all 45+ supported cuisine types.
        sort: Result sorting method (default: 'ranking'):
            - 'ranking': Sort by Tabelog rating (highest first) - RECOMMENDED
            - 'review-count': Sort by number of reviews (most reviewed first)
            - 'new-open': Sort by opening date (newest first)
            - 'standard': Tabelog default sorting (relevance)
        limit: Maximum number of results to return (default: 20, max: 60)

    Returns:
        List of restaurant search results

    Raises:
        ValueError: If parameters are invalid (e.g., unknown sort type, limit out of range)
        RuntimeError: If search operation fails (network error, parsing error, etc.)
    """
    try:
        # Validate limit
        if limit < 1 or limit > 60:
            raise ValueError("limit must be between 1 and 60")

        # Validate and convert sort parameter
        sort_map = {
            "ranking": SortType.RANKING,
            "review-count": SortType.REVIEW_COUNT,
            "new-open": SortType.NEW_OPEN,
            "standard": SortType.STANDARD,
        }
        sort_lower = sort.lower()
        if sort_lower not in sort_map:
            raise ValueError(f"Invalid sort type: {sort}. Must be one of: {', '.join(sort_map.keys())}")
        sort_type = sort_map[sort_lower]

        # Get genre code if cuisine is specified
        genre_code = None
        if cuisine:
            genre_code = get_genre_code(cuisine)
            if not genre_code:
                raise ValueError(
                    f"Unknown cuisine type: {cuisine}. Use 'tabelog_list_cuisines' to see supported cuisines."
                )

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

        # Convert to output schema
        results = []
        for r in response.restaurants[:limit]:
            results.append(
                RestaurantOutput(
                    name=r.name,
                    rating=r.rating,
                    review_count=r.review_count,
                    area=r.area,
                    genres=r.genres,
                    url=r.url,
                    lunch_price=r.lunch_price,
                    dinner_price=r.dinner_price,
                )
            )

        return results

    except ValueError as e:
        # Re-raise validation errors with clear messages
        raise ValueError(f"Invalid parameters: {e}") from e
    except Exception as e:
        # Wrap other errors with context
        raise RuntimeError(
            f"Restaurant search failed: {e}. "
            "Please check your search parameters and try again. "
            "If the problem persists, the Tabelog service may be unavailable."
        ) from e


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    )
)
async def tabelog_list_cuisines() -> list[CuisineOutput]:
    """Get complete list of all 45+ supported Japanese cuisine types with their Tabelog genre codes.

    **WHEN TO USE**:
    - Before calling `tabelog_search_restaurants` with `cuisine` parameter to verify available options
    - Providing cuisine type suggestions/autocomplete to users
    - Validating user's cuisine input against supported types
    - Building UI dropdown menus or selection lists

    **RETURN FORMAT**:
    Returns list of all supported cuisines:
    - name: Cuisine name in Japanese (e.g., 'すき焼き', '焼肉', 'ラーメン')
    - code: Tabelog genre code (e.g., 'RC0107', 'RC0103') - used internally for filtering

    **CUISINE CATEGORIES** (45+ types total):
    - Japanese: すき焼き, 焼肉, 寿司, ラーメン, うなぎ, そば, うどん, 天ぷら, とんかつ, 焼き鳥, お好み焼き, たこ焼き
    - Hotpot/Nabe: しゃぶしゃぶ, もつ鍋, 水炊き
    - Izakaya: 居酒屋, 焼酎バー, 日本酒バー
    - Western: イタリアン, フレンチ, スペイン料理, ハンバーガー, ステーキ
    - Asian: 中華料理, 韓国料理, タイ料理, インド料理, ベトナム料理
    - Other: カレー, カフェ, スイーツ, パン, ラーメン

    **WORKFLOW EXAMPLE**:
    1. User asks: 'Find sukiyaki restaurants in Tokyo'
    2. Call `tabelog_list_cuisines` to verify 'すき焼き' is supported → Returns {name: 'すき焼き', code: 'RC0107'}
    3. Call `tabelog_search_restaurants` with area='東京', cuisine='すき焼き'

    **NO INPUT REQUIRED**: This tool takes no parameters, simply call it to get the full list.

    Returns:
        List of all supported cuisine types with their genre codes

    Raises:
        RuntimeError: If cuisine list retrieval fails (should be rare as data is static)
    """
    try:
        cuisines = get_all_genres()
        results = []
        for cuisine in cuisines:
            code = get_genre_code(cuisine)
            if code:  # Only include cuisines with valid codes
                results.append(CuisineOutput(name=cuisine, code=code))

        return results

    except Exception as e:
        raise RuntimeError(
            f"Failed to retrieve cuisine list: {e}. This is an unexpected error as cuisine data is static."
        ) from e


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=True,
    )
)
async def tabelog_get_area_suggestions(query: str) -> list[SuggestionOutput]:
    """Get geographic area and station suggestions from Tabelog's autocomplete API.

    **WHEN TO USE**:
    - User provides ambiguous or partial area name (e.g., '渋谷', 'しぶや', 'shibuya')
    - Implementing autocomplete/typeahead for area input
    - Validating and standardizing area names before search
    - Helping users discover nearby stations or regions

    **INPUT**:
    - `query`: Partial or complete area name in Japanese, hiragana, or romaji
      - Examples: '東京' (complete), '渋' (partial), 'とうきょう' (hiragana), 'ise' (romaji)
      - Minimum 1 character, works best with 2+ characters

    **RETURN FORMAT**:
    Returns list of area suggestions with:
    - name: Display name (e.g., '東京都', '渋谷駅', '伊勢市')
    - datatype: Suggestion type (see below)
    - id_in_datatype: Unique identifier within datatype
    - lat: Latitude (decimal degrees, may be null)
    - lng: Longitude (decimal degrees, may be null)

    **DATATYPE VALUES**:
    - 'AddressMaster': Prefecture, city, or district (e.g., '東京都', '渋谷区', '伊勢市')
      - Use for broad geographic searches
      - Usually includes coordinates
    - 'RailroadStation': Train/subway station (e.g., '渋谷駅', '伊勢市駅')
      - Use for searches near specific stations
      - Always includes coordinates

    **WORKFLOW EXAMPLE**:
    1. User input: '渋谷でラーメン屋を探して'
    2. Call `tabelog_get_area_suggestions` with query='渋谷'
    3. Review results: [{name: '渋谷区', datatype: 'AddressMaster'}, {name: '渋谷駅', datatype: 'RailroadStation'}]
    4. Select appropriate suggestion (e.g., '渋谷区' for broader search, '渋谷駅' for station-area search)
    5. Call `tabelog_search_restaurants` with area='渋谷区' or area='渋谷駅'

    **TIPS**:
    - API returns up to 10 suggestions, ordered by relevance
    - For prefecture-level searches, use full name (e.g., '東京都', '大阪府', '三重県')
    - Station names usually end with '駅' (eki)
    - May return empty list if no matches found

    Args:
        query: Area search query (partial or complete).
            Accepts Japanese (東京), hiragana (とうきょう), or romaji (tokyo).
            Examples: '東京', '渋谷', '伊勢', 'しぶや', 'ise'.
            Minimum 1 character required, 2+ recommended.

    Returns:
        List of area suggestions from Tabelog API

    Raises:
        ValueError: If query is empty or invalid
        RuntimeError: If API request fails (network error, API error, etc.)
    """
    try:
        # Validate input
        if not query or not query.strip():
            raise ValueError("query parameter cannot be empty")

        # Call API
        suggestions = await get_area_suggestions_async(query.strip())

        # Convert to output schema
        results = []
        for s in suggestions:
            results.append(
                SuggestionOutput(
                    name=s.name,
                    datatype=s.datatype,
                    id_in_datatype=s.id_in_datatype,
                    lat=s.lat,
                    lng=s.lng,
                )
            )

        return results

    except ValueError as e:
        raise ValueError(f"Invalid query parameter: {e}") from e
    except Exception as e:
        raise RuntimeError(
            f"Area suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        openWorldHint=True,
    )
)
async def tabelog_get_keyword_suggestions(query: str) -> list[SuggestionOutput]:
    """Get dynamic keyword, cuisine, and restaurant name suggestions from Tabelog's autocomplete API.

    **WHEN TO USE**:
    - User provides partial keyword/cuisine name for autocomplete (e.g., 'すき', '寿', 'ramen')
    - Discovering related cuisine types or specific restaurants
    - Finding keyword combinations (e.g., 'すき焼き ランチ', '寿司 接待')
    - Implementing typeahead/autocomplete for keyword search

    **vs tabelog_list_cuisines**: Use this for dynamic autocomplete based on user input;
    use `tabelog_list_cuisines` for complete static list

    **INPUT**:
    - `query`: Partial or complete keyword in Japanese, hiragana, or romaji
      - Examples: 'すき' (partial), '寿司' (complete), 'らーめん' (hiragana), 'wada' (romaji)
      - Minimum 1 character, works best with 2+ characters

    **RETURN FORMAT**:
    Returns list of keyword suggestions with:
    - name: Suggestion text (e.g., 'すき焼き', '和田金', 'すき焼き ランチ')
    - datatype: Suggestion category (see below)
    - id_in_datatype: Unique identifier within datatype
    - lat: Latitude (usually null for keywords)
    - lng: Longitude (usually null for keywords)

    **DATATYPE VALUES** (3 types):

    1. **'Genre2'**: Cuisine/genre type
       - Examples: 'すき焼き', '寿司', 'ラーメン', '焼肉'
       - USE WITH: `tabelog_search_restaurants` cuisine parameter for precise filtering
       - Best for: Finding restaurants specializing in that cuisine

    2. **'Restaurant'**: Specific restaurant name
       - Examples: '和田金', 'すきやき割烹 美川', '次郎'
       - USE WITH: `tabelog_search_restaurants` keyword parameter
       - Best for: Finding a known restaurant by name

    3. **'Genre2 DetailCondition'**: Cuisine + condition/modifier
       - Examples: 'すき焼き ランチ' (sukiyaki lunch), '寿司 接待' (sushi business dinner), 'ラーメン 深夜' (ramen late-night)
       - USE WITH: Parse into separate parameters (cuisine + keyword or other filters)
       - Best for: Discovering popular search combinations

    **WORKFLOW EXAMPLES**:

    Example 1 - Cuisine autocomplete:
    1. User types: 'すき'
    2. Call `tabelog_get_keyword_suggestions` with query='すき'
    3. Review results: [{name: 'すき焼き', datatype: 'Genre2'}, {name: 'すきやき割烹 美川', datatype: 'Restaurant'}]
    4. User selects 'すき焼き' (Genre2)
    5. Call `tabelog_search_restaurants` with cuisine='すき焼き'

    Example 2 - Restaurant name search:
    1. User types: 'wada'
    2. Call `tabelog_get_keyword_suggestions` with query='wada'
    3. Review results: [{name: '和田金', datatype: 'Restaurant'}]
    4. User confirms '和田金'
    5. Call `tabelog_search_restaurants` with keyword='和田金'

    Example 3 - Keyword combination:
    1. User types: 'すき焼き'
    2. Call `tabelog_get_keyword_suggestions` with query='すき焼き'
    3. Review results: [{name: 'すき焼き ランチ', datatype: 'Genre2 DetailCondition'}]
    4. Parse 'ランチ' as a lunch preference
    5. Call `tabelog_search_restaurants` with cuisine='すき焼き' + lunch price filter

    **TIPS**:
    - API returns up to 10 suggestions, ordered by popularity/relevance
    - Suggestions are context-aware based on popular Tabelog searches
    - Genre2 suggestions can be used directly with `tabelog_search_restaurants` cuisine parameter
    - Restaurant suggestions should use keyword parameter for accurate matching
    - DetailCondition suggestions reveal popular search patterns (e.g., 'ランチ', '接待', '深夜')
    - May return empty list if no matches found or query too short

    Args:
        query: Keyword search query (partial or complete).
            Accepts Japanese (すき焼き), hiragana (すきやき), or romaji (sukiyaki).
            Examples: 'すき', '寿司', 'ラーメン', 'wada', 'らーめん'.
            Minimum 1 character required, 2+ recommended for better results.

    Returns:
        List of keyword suggestions from Tabelog API

    Raises:
        ValueError: If query is empty or invalid
        RuntimeError: If API request fails (network error, API error, etc.)
    """
    try:
        # Validate input
        if not query or not query.strip():
            raise ValueError("query parameter cannot be empty")

        # Call API
        suggestions = await get_keyword_suggestions_async(query.strip())

        # Convert to output schema
        results = []
        for s in suggestions:
            results.append(
                SuggestionOutput(
                    name=s.name,
                    datatype=s.datatype,
                    id_in_datatype=s.id_in_datatype,
                    lat=s.lat,
                    lng=s.lng,
                )
            )

        return results

    except ValueError as e:
        raise ValueError(f"Invalid query parameter: {e}") from e
    except Exception as e:
        raise RuntimeError(
            f"Keyword suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e


# ============================================================================
# Server Entry Points
# ============================================================================


def run() -> None:
    """Synchronous entry point for CLI

    This function is called when running 'gurume mcp' command.
    """
    mcp.run()


if __name__ == "__main__":
    run()
