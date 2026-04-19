"""MCP Server for Tabelog restaurant search using FastMCP.

This module keeps the FastMCP instance and tool entrypoints together while
delegating response schemas and helper logic to focused modules.
"""

from __future__ import annotations

from typing import Annotated
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .detail import RestaurantDetailRequest
from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .search import SearchRequest
from .search import SearchStatus
from .server_helpers import _build_cuisine_list_error_output
from .server_helpers import _build_cuisine_list_output
from .server_helpers import _build_detail_error_output
from .server_helpers import _build_search_error_output
from .server_helpers import _build_search_output
from .server_helpers import _build_suggestion_list_error_output
from .server_helpers import _build_suggestion_list_output
from .server_helpers import _build_tool_error
from .server_helpers import _resolve_genre_code
from .server_helpers import _to_detail_output
from .server_helpers import _to_restaurant_outputs
from .server_helpers import _to_suggestion_outputs
from .server_helpers import _validate_detail_params
from .server_helpers import _validate_search_params
from .server_models import CourseOutput
from .server_models import CuisineListOutput
from .server_models import CuisineOutput
from .server_models import MenuItemOutput
from .server_models import RestaurantDetailOutput
from .server_models import RestaurantOutput
from .server_models import RestaurantSearchOutput
from .server_models import ReviewOutput
from .server_models import SearchFiltersOutput
from .server_models import SearchMetaOutput
from .server_models import SortOption
from .server_models import SuggestionDatatype
from .server_models import SuggestionListOutput
from .server_models import SuggestionOutput
from .server_models import ToolErrorOutput
from .suggest import get_area_suggestions_async
from .suggest import get_keyword_suggestions_async

__all__ = [
    "CourseOutput",
    "CuisineListOutput",
    "CuisineOutput",
    "MenuItemOutput",
    "RestaurantDetailOutput",
    "RestaurantOutput",
    "RestaurantSearchOutput",
    "ReviewOutput",
    "SearchFiltersOutput",
    "SearchMetaOutput",
    "SortOption",
    "SuggestionDatatype",
    "SuggestionListOutput",
    "SuggestionOutput",
    "ToolErrorOutput",
    "mcp",
    "run",
    "tabelog_get_area_suggestions",
    "tabelog_get_keyword_suggestions",
    "tabelog_get_restaurant_details",
    "tabelog_list_cuisines",
    "tabelog_search_restaurants",
]

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

        request = SearchRequest(
            area=area,
            keyword=keyword,
            genre_code=genre_code,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            sort_type=sort_type,
            page=page,
            max_pages=1,
        )
        response = await request.search()
    except ValueError as e:
        error_code = "unsupported_cuisine" if cuisine and "Unknown cuisine type" in str(e) else "invalid_parameters"
        return _build_search_error_output(
            limit=limit,
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            error=_build_tool_error(
                error_code=error_code,
                message=f"Invalid search parameters: {e}",
                retryable=False,
                suggested_action=(
                    "Call `tabelog_list_cuisines` or `tabelog_get_keyword_suggestions` to validate the cuisine first."
                    if error_code == "unsupported_cuisine"
                    else "Check the input fields and retry with values that satisfy the tool schema."
                ),
                detail=str(e),
            ),
        )
    except RuntimeError as e:
        return _build_search_error_output(
            limit=limit,
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            error=_build_tool_error(
                error_code="upstream_unavailable",
                message="Restaurant search failed because the upstream service did not return usable results.",
                retryable=True,
                suggested_action=(
                    "Retry later, or validate the area and cuisine with suggestion tools before searching again."
                ),
                detail=str(e),
            ),
        )
    except Exception as e:  # noqa: BLE001
        return _build_search_error_output(
            limit=limit,
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            error=_build_tool_error(
                error_code="internal_error",
                message="Restaurant search failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            ),
        )

    if response.status == SearchStatus.ERROR:
        return _build_search_error_output(
            limit=limit,
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
            error=_build_tool_error(
                error_code="upstream_unavailable",
                message="Restaurant search failed because Tabelog returned an error response.",
                retryable=True,
                suggested_action="Validate the area or cuisine first, then retry the search.",
                detail=response.error_message,
            ),
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
        openWorldHint=True,
    ),
    structured_output=True,
)
async def tabelog_get_restaurant_details(
    restaurant_url: Annotated[
        str,
        Field(
            description="Tabelog restaurant URL from search results. Must start with https://tabelog.com/.",
            pattern=r"^https://tabelog\.com/.+",
        ),
    ],
    fetch_reviews: Annotated[
        bool,
        Field(default=True, description="Whether to fetch review pages from Tabelog."),
    ] = True,
    fetch_menu: Annotated[
        bool,
        Field(default=True, description="Whether to fetch the restaurant menu page."),
    ] = True,
    fetch_courses: Annotated[
        bool,
        Field(default=True, description="Whether to fetch the restaurant course page."),
    ] = True,
    max_review_pages: Annotated[
        int,
        Field(
            default=1,
            description="Maximum number of review pages to fetch when fetch_reviews is true.",
            ge=1,
        ),
    ] = 1,
) -> RestaurantDetailOutput:
    """Fetch detailed restaurant information including reviews, menu items, and courses."""
    try:
        _validate_detail_params(restaurant_url, fetch_reviews, fetch_menu, fetch_courses, max_review_pages)
        request = RestaurantDetailRequest(
            restaurant_url=restaurant_url,
            fetch_reviews=fetch_reviews,
            fetch_menu=fetch_menu,
            fetch_courses=fetch_courses,
            max_review_pages=max_review_pages,
        )
        detail = await request.fetch()
    except ValueError as e:
        return _build_detail_error_output(
            restaurant_url=restaurant_url,
            fetch_reviews=fetch_reviews,
            fetch_menu=fetch_menu,
            fetch_courses=fetch_courses,
            max_review_pages=max_review_pages,
            error=_build_tool_error(
                error_code="invalid_parameters",
                message=f"Invalid detail request parameters: {e}",
                retryable=False,
                suggested_action=(
                    "Pass a non-empty `https://tabelog.com/` restaurant URL and enable at least one fetch option."
                ),
                detail=str(e),
            ),
        )
    except RuntimeError as e:
        return _build_detail_error_output(
            restaurant_url=restaurant_url,
            fetch_reviews=fetch_reviews,
            fetch_menu=fetch_menu,
            fetch_courses=fetch_courses,
            max_review_pages=max_review_pages,
            error=_build_tool_error(
                error_code="upstream_unavailable",
                message="Restaurant detail request failed because the upstream service did not return usable data.",
                retryable=True,
                suggested_action="Verify the restaurant URL from search results and retry later.",
                detail=str(e),
            ),
        )
    except Exception as e:  # noqa: BLE001
        return _build_detail_error_output(
            restaurant_url=restaurant_url,
            fetch_reviews=fetch_reviews,
            fetch_menu=fetch_menu,
            fetch_courses=fetch_courses,
            max_review_pages=max_review_pages,
            error=_build_tool_error(
                error_code="internal_error",
                message="Restaurant detail request failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            ),
        )

    return _to_detail_output(
        detail,
        fetch_reviews=fetch_reviews,
        fetch_menu=fetch_menu,
        fetch_courses=fetch_courses,
        max_review_pages=max_review_pages,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        idempotentHint=True,
    ),
    structured_output=True,
)
async def tabelog_list_cuisines() -> CuisineListOutput:
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
        return _build_cuisine_list_error_output(
            _build_tool_error(
                error_code="internal_error",
                message="Cuisine list retrieval failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            )
        )
    except Exception as e:  # noqa: BLE001
        return _build_cuisine_list_error_output(
            _build_tool_error(
                error_code="internal_error",
                message="Cuisine list retrieval failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            )
        )

    return _build_cuisine_list_output(
        [CuisineOutput(name=cuisine, code=code) for cuisine in cuisines if (code := get_genre_code(cuisine))]
    )


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
) -> SuggestionListOutput:
    """Get area and station suggestions for validating user-provided locations."""
    normalized_query = query.strip()

    try:
        if not normalized_query:
            raise ValueError("query parameter cannot be empty")

        suggestions = await get_area_suggestions_async(normalized_query)
    except ValueError as e:
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="invalid_parameters",
                message=f"Invalid suggestion query: {e}",
                retryable=False,
                suggested_action="Pass a non-empty area query string before calling this tool again.",
                detail=str(e),
            ),
        )
    except RuntimeError as e:
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="upstream_unavailable",
                message="Area suggestion request failed because the upstream service was unavailable.",
                retryable=True,
                suggested_action="Retry later, or try a broader area query.",
                detail=str(e),
            ),
        )
    except Exception as e:  # noqa: BLE001
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="internal_error",
                message="Area suggestion request failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            ),
        )

    return _build_suggestion_list_output(normalized_query, _to_suggestion_outputs(suggestions))


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
) -> SuggestionListOutput:
    """Get keyword suggestions for cuisine names, restaurant names, and popular search variants."""
    normalized_query = query.strip()

    try:
        if not normalized_query:
            raise ValueError("query parameter cannot be empty")

        suggestions = await get_keyword_suggestions_async(normalized_query)
    except ValueError as e:
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="invalid_parameters",
                message=f"Invalid suggestion query: {e}",
                retryable=False,
                suggested_action="Pass a non-empty keyword query string before calling this tool again.",
                detail=str(e),
            ),
        )
    except RuntimeError as e:
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="upstream_unavailable",
                message="Keyword suggestion request failed because the upstream service was unavailable.",
                retryable=True,
                suggested_action="Retry later, or try a shorter keyword query.",
                detail=str(e),
            ),
        )
    except Exception as e:  # noqa: BLE001
        return _build_suggestion_list_error_output(
            normalized_query,
            _build_tool_error(
                error_code="internal_error",
                message="Keyword suggestion request failed unexpectedly.",
                retryable=True,
                suggested_action="Retry the tool call. If the same error repeats, inspect the server logs.",
                detail=str(e),
            ),
        )

    return _build_suggestion_list_output(normalized_query, _to_suggestion_outputs(suggestions))


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
