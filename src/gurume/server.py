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

from datetime import date
from datetime import time
from typing import Annotated
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl

from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .restaurant import SortType
from .search import SearchMeta
from .search import SearchRequest
from .search import SearchStatus
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async

# Create FastMCP server instance
mcp = FastMCP(
    "gurume",
    instructions="""Tabelog restaurant search MCP server for Japanese restaurants.

🎯 RECOMMENDED WORKFLOW:
1. Validate inputs FIRST using suggestion tools
2. Then perform search with validated parameters

📋 STEP-BY-STEP GUIDE:

Step 1: Get area suggestions (if user provides area)
→ Use: tabelog_get_area_suggestions(query="user's area")
→ Pick the best match from suggestions

Step 2: Get keyword/cuisine suggestions (if searching by cuisine/keyword)
→ Use: tabelog_get_keyword_suggestions(query="user's keyword")
→ Identify if it's Genre2 (cuisine) or Restaurant (name)

Step 3: Search with validated parameters
→ Use: tabelog_search_restaurants(area=validated_area, cuisine=validated_cuisine)

Optional Step 4: Filter by reservation availability
→ Add reservation_date='YYYYMMDD', reservation_time='HHMM', party_size=N
→ Example: reservation_date='20260427', reservation_time='1900', party_size=2

🔑 KEY PRINCIPLES:
- Cuisine searches: Use `cuisine` parameter (more accurate than `keyword`)
- Always validate user input with suggestion tools before searching
- All parameters and results are in Japanese
- Use reservation filters to check availability on specific dates

Example:
User: "Find sukiyaki in Tokyo available April 27 at 7pm for 2 people"
1. tabelog_get_area_suggestions(query="Tokyo") → Get "東京都"
2. tabelog_get_keyword_suggestions(query="sukiyaki") → Get "すき焼き" (Genre2)
3. tabelog_search_restaurants(area="東京都", cuisine="すき焼き",
   reservation_date="20260427", reservation_time="1900", party_size=2)
""",
)

SortOption = Literal["ranking", "review-count", "new-open", "standard"]
SuggestionDatatype = Literal["AddressMaster", "RailroadStation", "Genre2", "Restaurant", "Genre2 DetailCondition"]


# ============================================================================
# Output Schemas - Pydantic Models
# ============================================================================


class RestaurantOutput(BaseModel):
    """Restaurant search result output schema"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Restaurant name")
    rating: float | None = Field(description="Tabelog rating (0.0-5.0)")
    review_count: int | None = Field(description="Number of reviews")
    area: str | None = Field(description="Location area")
    genres: list[str] = Field(description="List of cuisine genres")
    url: HttpUrl = Field(description="Tabelog restaurant page URL")
    lunch_price: str | None = Field(description="Lunch price range")
    dinner_price: str | None = Field(description="Dinner price range")


class CuisineOutput(BaseModel):
    """Cuisine type output schema"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Cuisine name in Japanese")
    code: str = Field(description="Tabelog genre code (e.g., 'RC0107')", pattern=r"^RC\d{4}$")


class SuggestionOutput(BaseModel):
    """Area or keyword suggestion output schema"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Suggestion display name")
    datatype: SuggestionDatatype = Field(
        description="Suggestion type (AddressMaster, RailroadStation, Genre2, Restaurant, etc.)"
    )
    id_in_datatype: str | int = Field(description="Unique identifier within datatype")
    lat: float | None = Field(description="Latitude (decimal degrees)")
    lng: float | None = Field(description="Longitude (decimal degrees)")


class SearchMetaOutput(BaseModel):
    """Pagination and result metadata for restaurant search."""

    model_config = ConfigDict(extra="forbid")

    total_count: int | None = Field(description="Total restaurants reported by Tabelog for this query")
    current_page: int = Field(description="Current result page returned by the tool")
    results_per_page: int | None = Field(description="Number of restaurants parsed from the fetched page")
    total_pages: int | None = Field(description="Total number of result pages reported by Tabelog")
    has_next_page: bool = Field(description="Whether Tabelog reports a next result page")
    has_prev_page: bool = Field(description="Whether Tabelog reports a previous result page")


class SearchFiltersOutput(BaseModel):
    """Normalized filters used for a search request."""

    model_config = ConfigDict(extra="forbid")

    area: str | None = Field(description="Area filter used for the search")
    keyword: str | None = Field(description="Keyword filter used for the search")
    cuisine: str | None = Field(description="Cuisine filter used for the search")
    genre_code: str | None = Field(description="Resolved Tabelog genre code for the cuisine filter")
    sort: SortOption = Field(description="Sort option used for the search")
    page: int = Field(description="Requested result page", ge=1)
    reservation_date: str | None = Field(description="Reservation date used for filtering, if any")
    reservation_time: str | None = Field(description="Reservation time used for filtering, if any")
    party_size: int | None = Field(description="Party size used for filtering, if any")


class RestaurantSearchOutput(BaseModel):
    """Structured restaurant search output for MCP clients."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "no_results"] = Field(description="Search status after executing the query")
    items: list[RestaurantOutput] = Field(description="Restaurants returned for the current page")
    returned_count: int = Field(description="Number of restaurants returned in this response")
    limit: int = Field(description="Maximum number of restaurants requested by the caller")
    has_more: bool = Field(description="Whether more matching restaurants likely exist beyond this response")
    meta: SearchMetaOutput | None = Field(description="Tabelog pagination metadata for the current query")
    applied_filters: SearchFiltersOutput = Field(description="Normalized search filters used by the server")
    warnings: list[str] = Field(description="Non-fatal usage guidance for the caller")


SORT_MAP = {
    "ranking": SortType.RANKING,
    "review-count": SortType.REVIEW_COUNT,
    "new-open": SortType.NEW_OPEN,
    "standard": SortType.STANDARD,
}


def _validate_search_params(
    sort: SortOption,
    limit: int,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
) -> SortType:
    _validate_pagination_params(limit, page, sort)
    _validate_reservation_params(reservation_date, reservation_time, party_size)
    return SORT_MAP[sort]


def _validate_pagination_params(limit: int, page: int, sort: SortOption) -> None:
    if limit < 1 or limit > 60:
        raise ValueError("limit must be between 1 and 60")

    if page < 1:
        raise ValueError("page must be greater than or equal to 1")

    if sort not in SORT_MAP:
        raise ValueError(f"Invalid sort type: {sort}. Must be one of: {', '.join(SORT_MAP)}")


def _validate_reservation_params(
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
) -> None:
    if reservation_date is not None and (not reservation_date.isdigit() or len(reservation_date) != 8):
        raise ValueError("reservation_date must be in YYYYMMDD format (e.g., '20260427')")

    if reservation_time is not None and (not reservation_time.isdigit() or len(reservation_time) != 4):
        raise ValueError("reservation_time must be in HHMM format (e.g., '1900')")

    if reservation_date is None and reservation_time is None and party_size is None:
        return

    if reservation_date is None:
        raise ValueError("reservation_date is required when using reservation_time or party_size")

    if reservation_time is None:
        raise ValueError("reservation_time is required when using reservation_date or party_size")

    try:
        date(int(reservation_date[:4]), int(reservation_date[4:6]), int(reservation_date[6:8]))
    except ValueError as e:
        raise ValueError("reservation_date must be a valid date in YYYYMMDD format (e.g., '20260427')") from e

    try:
        time(int(reservation_time[:2]), int(reservation_time[2:4]))
    except ValueError as e:
        raise ValueError("reservation_time must be a valid 24-hour time in HHMM format (e.g., '1900')") from e


def _resolve_genre_code(cuisine: str | None) -> str | None:
    if not cuisine:
        return None

    genre_code = get_genre_code(cuisine)
    if not genre_code:
        raise ValueError(f"Unknown cuisine type: {cuisine}. Use 'tabelog_list_cuisines' to see supported cuisines.")
    return genre_code


def _to_restaurant_outputs(response: list, limit: int) -> list[RestaurantOutput]:
    return [
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
        for r in response[:limit]
    ]


def _to_search_meta_output(meta: SearchMeta | None) -> SearchMetaOutput | None:
    if meta is None:
        return None

    return SearchMetaOutput(
        total_count=meta.total_count,
        current_page=meta.current_page,
        results_per_page=meta.results_per_page,
        total_pages=meta.total_pages,
        has_next_page=meta.has_next_page,
        has_prev_page=meta.has_prev_page,
    )


def _to_suggestion_outputs(suggestions: list) -> list[SuggestionOutput]:
    return [
        SuggestionOutput(
            name=s.name,
            datatype=s.datatype,
            id_in_datatype=s.id_in_datatype,
            lat=s.lat,
            lng=s.lng,
        )
        for s in suggestions
    ]


def _build_search_warnings(
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    reservation_date: str | None,
) -> list[str]:
    warnings: list[str] = []

    if area is not None:
        warnings.append("Use `tabelog_get_area_suggestions` first when the user provides an ambiguous area name.")

    if cuisine is None and keyword is not None:
        warnings.append(
            "If the keyword is actually a cuisine type, call `tabelog_get_keyword_suggestions` and pass the "
            "Genre2 result as `cuisine` for more precise matches."
        )

    if cuisine is not None and keyword is not None:
        warnings.append(
            "Using both `cuisine` and `keyword` narrows results. Remove `keyword` if you want broader cuisine matches."
        )

    if reservation_date is not None:
        warnings.append("Reservation filters reflect Tabelog availability data and may change over time.")

    return warnings


def _build_search_output(
    *,
    items: list[RestaurantOutput],
    limit: int,
    meta: SearchMeta | None,
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    genre_code: str | None,
    sort: SortOption,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
    status: Literal["success", "no_results"],
) -> RestaurantSearchOutput:
    meta_output = _to_search_meta_output(meta)
    returned_count = len(items)
    has_more = False
    if meta is not None:
        has_more = meta.has_next_page

    return RestaurantSearchOutput(
        status=status,
        items=items,
        returned_count=returned_count,
        limit=limit,
        has_more=has_more,
        meta=meta_output,
        applied_filters=SearchFiltersOutput(
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            genre_code=genre_code,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
        ),
        warnings=_build_search_warnings(area, keyword, cuisine, reservation_date),
    )


def _reraise_if_fatal(error: BaseException) -> None:
    if isinstance(error, KeyboardInterrupt | SystemExit):
        raise error


# ============================================================================
# Tool Implementations
# ============================================================================


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
    structured_output=True,
)
async def tabelog_search_restaurants(
    area: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Area name in Japanese. Prefer a validated prefecture, city, or station from "
                "`tabelog_get_area_suggestions`."
            ),
            min_length=1,
        ),
    ] = None,
    keyword: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "General keyword for restaurant names or free-text matching. Use `cuisine` for cuisine-type searches."
            ),
            min_length=1,
        ),
    ] = None,
    cuisine: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Cuisine name in Japanese. Validate with `tabelog_get_keyword_suggestions` or "
                "`tabelog_list_cuisines` before searching."
            ),
            min_length=1,
        ),
    ] = None,
    sort: Annotated[
        SortOption,
        Field(default="ranking", description="Result ordering: ranking, review-count, new-open, or standard."),
    ] = "ranking",
    limit: Annotated[
        int,
        Field(
            default=20,
            description="Maximum number of restaurants to return from the first fetched page.",
            ge=1,
            le=60,
        ),
    ] = 20,
    page: Annotated[
        int,
        Field(
            default=1,
            description="1-based result page to fetch from Tabelog. Use the returned metadata to continue paging.",
            ge=1,
        ),
    ] = 1,
    reservation_date: Annotated[
        str | None,
        Field(
            default=None,
            description="Reservation date in YYYYMMDD format. Must be used together with reservation_time.",
            pattern=r"^\d{8}$",
        ),
    ] = None,
    reservation_time: Annotated[
        str | None,
        Field(
            default=None,
            description="Reservation time in 24-hour HHMM format. Must be used together with reservation_date.",
            pattern=r"^\d{4}$",
        ),
    ] = None,
    party_size: Annotated[
        int | None,
        Field(default=None, description="Optional party size for reservation filtering.", ge=1),
    ] = None,
) -> RestaurantSearchOutput:
    """Search Tabelog restaurants with validated filters and pagination metadata.

    Recommended workflow:
    1. Validate ambiguous areas with `tabelog_get_area_suggestions`.
    2. Validate cuisines or names with `tabelog_get_keyword_suggestions`.
    3. Search using the normalized area and cuisine values.
    4. Use `page` together with the returned `meta.has_next_page` and `has_more` fields to fetch later pages.

    Returns a structured envelope with restaurants, applied filters, pagination metadata,
    and non-fatal warnings that help the caller refine follow-up tool calls.
    """
    try:
        sort_type = _validate_search_params(sort, limit, page, reservation_date, reservation_time, party_size)
        genre_code = _resolve_genre_code(cuisine)

        # Create search request
        request = SearchRequest(
            area=area,
            keyword=keyword,
            genre_code=genre_code,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            sort_type=sort_type,
            page=page,
            max_pages=1,  # Only fetch first page for MCP
        )

        # Execute search
        response = await request.search()
    except ValueError as e:
        # Re-raise validation errors with clear messages
        raise ValueError(f"Invalid parameters: {e}") from e
    except RuntimeError as e:
        # Wrap other errors with context
        raise RuntimeError(
            f"Restaurant search failed: {e}. "
            "Please check your search parameters and try again. "
            "If the problem persists, the Tabelog service may be unavailable."
        ) from e
    except BaseException as e:
        _reraise_if_fatal(e)
        raise RuntimeError(
            f"Restaurant search failed: {e}. "
            "Please check your search parameters and try again. "
            "If the problem persists, the Tabelog service may be unavailable."
        ) from e
    else:
        if response.status == SearchStatus.ERROR:
            raise RuntimeError(
                f"Restaurant search failed: {response.error_message}. "
                "Try validating the area or cuisine first, then retry the search."
            )

        items = _to_restaurant_outputs(response.restaurants, limit)
        status: Literal["success", "no_results"] = "success"
        if response.status == SearchStatus.NO_RESULTS:
            status = "no_results"

        return _build_search_output(
            items=items,
            limit=limit,
            meta=response.meta,
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            genre_code=genre_code,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            status=status,
        )


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    ),
    structured_output=True,
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
    except ValueError as e:
        raise RuntimeError(
            f"Failed to retrieve cuisine list: {e}. This is an unexpected error as cuisine data is static."
        ) from e
    except BaseException as e:
        _reraise_if_fatal(e)
        raise RuntimeError(
            f"Failed to retrieve cuisine list: {e}. This is an unexpected error as cuisine data is static."
        ) from e
    else:
        return [CuisineOutput(name=cuisine, code=code) for cuisine in cuisines if (code := get_genre_code(cuisine))]


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
    structured_output=True,
)
async def tabelog_get_area_suggestions(
    query: Annotated[
        str,
        Field(
            description=(
                "Area query in Japanese, hiragana, or romaji. Use this before searching when area names are ambiguous."
            ),
            min_length=1,
        ),
    ],
) -> list[SuggestionOutput]:
    """Get area and station suggestions for validating user-provided locations."""
    try:
        # Validate input
        if not query or not query.strip():
            raise ValueError("query parameter cannot be empty")

        # Call API
        suggestions = await get_area_suggestions_async(query.strip())
    except ValueError as e:
        raise ValueError(f"Invalid query parameter: {e}") from e
    except RuntimeError as e:
        raise RuntimeError(
            f"Area suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e
    except BaseException as e:
        _reraise_if_fatal(e)
        raise RuntimeError(
            f"Area suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e
    else:
        return _to_suggestion_outputs(suggestions)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
    structured_output=True,
)
async def tabelog_get_keyword_suggestions(
    query: Annotated[
        str,
        Field(
            description=(
                "Keyword query in Japanese, hiragana, or romaji. Use this to detect Genre2 cuisines or "
                "restaurant-name suggestions before searching."
            ),
            min_length=1,
        ),
    ],
) -> list[SuggestionOutput]:
    """Get keyword suggestions for cuisine names, restaurant names, and popular search variants."""
    try:
        # Validate input
        if not query or not query.strip():
            raise ValueError("query parameter cannot be empty")

        # Call API
        suggestions = await get_keyword_suggestions_async(query.strip())
    except ValueError as e:
        raise ValueError(f"Invalid query parameter: {e}") from e
    except RuntimeError as e:
        raise RuntimeError(
            f"Keyword suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e
    except BaseException as e:
        _reraise_if_fatal(e)
        raise RuntimeError(
            f"Keyword suggestion request failed: {e}. "
            "This may be due to network issues or Tabelog API being temporarily unavailable. "
            "Please try again in a moment."
        ) from e
    else:
        return _to_suggestion_outputs(suggestions)


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
