"""Tests for MCP server tools (FastMCP implementation)"""

from typing import Any
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from gurume.detail import Course
from gurume.detail import MenuItem
from gurume.detail import RestaurantDetail
from gurume.detail import Review
from gurume.genre_mapping import get_all_genres
from gurume.genre_mapping import get_genre_code
from gurume.restaurant import Restaurant
from gurume.search import SearchMeta
from gurume.search import SearchResponse
from gurume.search import SearchStatus
from gurume.server import CuisineOutput
from gurume.server import RestaurantDetailOutput
from gurume.server import RestaurantOutput
from gurume.server import RestaurantSearchOutput
from gurume.server import SuggestionOutput
from gurume.server import mcp
from gurume.server import tabelog_get_area_suggestions
from gurume.server import tabelog_get_keyword_suggestions
from gurume.server import tabelog_get_restaurant_details
from gurume.server import tabelog_list_cuisines
from gurume.server import tabelog_search_restaurants
from gurume.suggest import AreaSuggestion
from gurume.suggest import KeywordSuggestion

# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_restaurants():
    """Sample restaurant data for testing"""
    return [
        Restaurant(
            name="テスト寿司",
            url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
            rating=4.5,
            review_count=123,
            area="銀座",
            genres=["寿司", "和食"],
            lunch_price="¥5,000～¥5,999",
            dinner_price="¥10,000～¥14,999",
        ),
        Restaurant(
            name="テストラーメン",
            url="https://tabelog.com/tokyo/A1301/A130102/13000002/",
            rating=3.8,
            review_count=456,
            area="新宿",
            genres=["ラーメン"],
            lunch_price="¥1,000～¥1,999",
            dinner_price=None,
        ),
    ]


@pytest.fixture
def sample_area_suggestions():
    """Sample area suggestion data"""
    return [
        AreaSuggestion(
            name="東京都",
            datatype="AddressMaster",
            id_in_datatype=13,
            lat=35.6895,
            lng=139.6917,
        ),
        AreaSuggestion(
            name="渋谷駅",
            datatype="RailroadStation",
            id_in_datatype=1001,
            lat=35.6580,
            lng=139.7016,
        ),
    ]


@pytest.fixture
def sample_keyword_suggestions():
    """Sample keyword suggestion data"""
    return [
        KeywordSuggestion(
            name="すき焼き",
            datatype="Genre2",
            id_in_datatype=107,
            lat=None,
            lng=None,
        ),
        KeywordSuggestion(
            name="和田金",
            datatype="Restaurant",
            id_in_datatype=24000123,
            lat=None,
            lng=None,
        ),
        KeywordSuggestion(
            name="すき焼き ランチ",
            datatype="Genre2 DetailCondition",
            id_in_datatype=107,
            lat=None,
            lng=None,
        ),
    ]


@pytest.fixture
def sample_restaurant_detail(sample_restaurants):
    """Sample restaurant detail for MCP detail tool tests"""
    restaurant = sample_restaurants[0]
    restaurant.station = "銀座駅"
    restaurant.address = "東京都中央区銀座1-2-3"
    restaurant.phone = "03-1111-2222"
    restaurant.business_hours = "11:00 - 22:00"
    restaurant.closed_days = "日曜日"
    restaurant.reservation_url = "https://tabelog.com/tokyo/A1301/A130101/13000001/reserve/"
    return RestaurantDetail(
        restaurant=restaurant,
        reviews=[
            Review(
                reviewer="評論者A",
                content="服務很好",
                rating=4.2,
                visit_date="2026/04訪問",
                title="值得再訪",
                helpful_count=3,
            )
        ],
        menu_items=[
            MenuItem(
                name="特上壽司",
                price="¥4,800",
                description="主廚精選握壽司",
                category="握り",
            )
        ],
        courses=[
            Course(
                name="旬のコース",
                price="¥12,000",
                description="季節限定套餐",
                items=["前菜", "握壽司", "味噌湯"],
            )
        ],
    )


# ============================================================================
# Test tabelog_search_restaurants
# ============================================================================


@pytest.mark.asyncio
async def test_search_restaurants_success(sample_restaurants):
    """Test successful restaurant search"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=SearchMeta(
            total_count=2,
            current_page=1,
            results_per_page=2,
            total_pages=1,
            has_next_page=False,
            has_prev_page=False,
        ),
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        results = await tabelog_search_restaurants(
            area="東京",
            cuisine="寿司",
            sort="ranking",
            limit=20,
        )

        # Verify results
        assert isinstance(results, RestaurantSearchOutput)
        assert results.status == "success"
        assert len(results.items) == 2
        assert isinstance(results.items[0], RestaurantOutput)
        assert results.items[0].name == "テスト寿司"
        assert results.items[0].rating == 4.5
        assert results.items[0].review_count == 123
        assert results.items[0].area == "銀座"
        assert results.items[0].genres == ["寿司", "和食"]
        assert results.items[0].lunch_price == "¥5,000～¥5,999"
        assert results.items[0].dinner_price == "¥10,000～¥14,999"
        assert results.returned_count == 2
        assert results.limit == 20
        assert results.applied_filters.area == "東京"
        assert results.applied_filters.cuisine == "寿司"
        assert results.applied_filters.genre_code == "RC0201"
        assert results.applied_filters.page == 1
        assert results.has_more is False
        assert results.meta is not None
        assert results.meta.current_page == 1

        # Verify SearchRequest was called correctly
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_restaurants_with_keyword(sample_restaurants):
    """Test restaurant search with keyword parameter"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        results = await tabelog_search_restaurants(
            area="東京",
            keyword="ラーメン",
            sort="review-count",
            limit=10,
        )

        assert len(results.items) == 2
        assert results.applied_filters.keyword == "ラーメン"
        assert results.applied_filters.sort == "review-count"
        assert results.applied_filters.page == 1
        mock_search.assert_called_once()


@pytest.mark.asyncio
async def test_search_restaurants_with_reservation_filters(sample_restaurants):
    """Test restaurant search forwards reservation filters to SearchRequest"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.search = AsyncMock(return_value=mock_response)

        results = await tabelog_search_restaurants(
            area="東京",
            reservation_date="20260427",
            reservation_time="1900",
            party_size=2,
        )

        assert len(results.items) == 2
        assert results.applied_filters.reservation_date == "20260427"
        assert results.applied_filters.reservation_time == "1900"
        assert results.applied_filters.party_size == 2
        assert results.applied_filters.page == 1
        mock_request.search.assert_awaited_once()
        mock_request_class.assert_called_once()

        assert mock_request_class.call_args.kwargs["reservation_date"] == "20260427"
        assert mock_request_class.call_args.kwargs["reservation_time"] == "1900"
        assert mock_request_class.call_args.kwargs["party_size"] == 2


@pytest.mark.asyncio
async def test_search_restaurants_limit_applied(sample_restaurants):
    """Test that limit parameter is correctly applied"""
    # Create 5 sample restaurants
    many_restaurants = sample_restaurants * 3  # 6 restaurants

    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=many_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        # Request only 3 results
        results = await tabelog_search_restaurants(
            area="東京",
            limit=3,
        )

        # Should only return 3 results, not all 6
        assert len(results.items) == 3
        assert results.returned_count == 3


@pytest.mark.asyncio
async def test_search_restaurants_invalid_limit():
    """Test validation of limit parameter"""
    # Test limit < 1
    with pytest.raises(ValueError, match="limit must be between 1 and 60"):
        await tabelog_search_restaurants(limit=0)

    # Test limit > 60
    with pytest.raises(ValueError, match="limit must be between 1 and 60"):
        await tabelog_search_restaurants(limit=100)


@pytest.mark.asyncio
async def test_search_restaurants_invalid_page():
    """Test validation of page parameter"""
    with pytest.raises(ValueError, match="page must be greater than or equal to 1"):
        await tabelog_search_restaurants(page=0)


@pytest.mark.asyncio
async def test_search_restaurants_invalid_sort():
    """Test validation of sort parameter"""
    with pytest.raises(ValueError, match="Invalid sort type"):
        await tabelog_search_restaurants(sort="invalid-sort-type")


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_date():
    """Test validation of reservation_date parameter"""
    with pytest.raises(ValueError, match="reservation_date must be in YYYYMMDD format"):
        await tabelog_search_restaurants(reservation_date="2026-04-27")


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_time():
    """Test validation of reservation_time parameter"""
    with pytest.raises(ValueError, match="reservation_time must be in HHMM format"):
        await tabelog_search_restaurants(reservation_time="19:00")


@pytest.mark.asyncio
async def test_search_restaurants_requires_reservation_time_with_date():
    """Test semantic validation for reservation filters"""
    with pytest.raises(ValueError, match="reservation_time is required"):
        await tabelog_search_restaurants(reservation_date="20260427")


@pytest.mark.asyncio
async def test_search_restaurants_requires_reservation_date_with_party_size():
    """Test reservation bundle validation when party_size is set"""
    with pytest.raises(ValueError, match="reservation_date is required"):
        await tabelog_search_restaurants(party_size=2)


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_time_value():
    """Test semantic validation of HHMM values"""
    with pytest.raises(ValueError, match="valid 24-hour time"):
        await tabelog_search_restaurants(reservation_date="20260427", reservation_time="2460")


@pytest.mark.asyncio
async def test_search_restaurants_unknown_cuisine():
    """Test error handling for unknown cuisine type"""
    with pytest.raises(ValueError, match="Unknown cuisine type"):
        await tabelog_search_restaurants(cuisine="存在しない料理")


@pytest.mark.asyncio
async def test_search_restaurants_all_sort_types(sample_restaurants):
    """Test all valid sort type values"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    sort_types = ["ranking", "review-count", "new-open", "standard"]

    for sort_type in sort_types:
        with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_response

            results = await tabelog_search_restaurants(sort=sort_type)
        assert len(results.items) == 2


@pytest.mark.asyncio
async def test_search_restaurants_runtime_error():
    """Test error handling when search operation fails"""
    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Restaurant search failed"):
            await tabelog_search_restaurants(area="東京")


@pytest.mark.asyncio
async def test_search_restaurants_raises_for_error_status():
    """Test MCP wrapper surfaces SearchResponse errors instead of returning empty data"""
    mock_response = SearchResponse(
        status=SearchStatus.ERROR,
        restaurants=[],
        meta=None,
        error_message="upstream error",
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        with pytest.raises(RuntimeError, match="upstream error"):
            await tabelog_search_restaurants(area="東京")


@pytest.mark.asyncio
async def test_search_restaurants_no_results_envelope():
    """Test empty searches return a no_results envelope"""
    mock_response = SearchResponse(
        status=SearchStatus.NO_RESULTS,
        restaurants=[],
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        results = await tabelog_search_restaurants(area="東京")

    assert results.status == "no_results"
    assert results.items == []
    assert results.returned_count == 0
    assert results.has_more is False


@pytest.mark.asyncio
async def test_search_restaurants_forwards_page_and_has_more(sample_restaurants):
    """Test explicit MCP page requests propagate to SearchRequest and metadata"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=SearchMeta(
            total_count=10,
            current_page=2,
            results_per_page=2,
            total_pages=5,
            has_next_page=True,
            has_prev_page=True,
        ),
    )

    with patch("gurume.server.SearchRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.search = AsyncMock(return_value=mock_response)

        results = await tabelog_search_restaurants(area="東京", cuisine="寿司", page=2, limit=2)

    assert results.applied_filters.page == 2
    assert results.meta is not None
    assert results.meta.current_page == 2
    assert results.has_more is True
    assert mock_request_class.call_args.kwargs["page"] == 2


# ============================================================================
# Test tabelog_get_restaurant_details
# ============================================================================


@pytest.mark.asyncio
async def test_get_restaurant_details_success(sample_restaurant_detail):
    """Test successful restaurant detail fetch"""
    with patch("gurume.server.RestaurantDetailRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.fetch = AsyncMock(return_value=sample_restaurant_detail)

        result = await tabelog_get_restaurant_details(
            restaurant_url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
            fetch_reviews=True,
            fetch_menu=True,
            fetch_courses=False,
            max_review_pages=2,
        )

    assert isinstance(result, RestaurantDetailOutput)
    assert str(result.restaurant_url) == "https://tabelog.com/tokyo/A1301/A130101/13000001/"
    assert result.review_count == 1
    assert result.menu_item_count == 1
    assert result.course_count == 1
    assert result.restaurant.name == "テスト寿司"
    assert result.station == "銀座駅"
    assert result.address == "東京都中央区銀座1-2-3"
    assert result.phone == "03-1111-2222"
    assert str(result.reservation_url) == "https://tabelog.com/tokyo/A1301/A130101/13000001/reserve/"
    assert result.fetch_courses is False
    assert result.max_review_pages == 2
    assert result.reviews[0].reviewer == "評論者A"
    assert result.menu_items[0].name == "特上壽司"
    assert result.courses[0].items == ["前菜", "握壽司", "味噌湯"]
    assert mock_request_class.call_args.kwargs["max_review_pages"] == 2


@pytest.mark.asyncio
async def test_get_restaurant_details_requires_one_enabled_fetch():
    """Test detail tool rejects empty fetch selection"""
    with pytest.raises(ValueError, match="At least one of fetch_reviews"):
        await tabelog_get_restaurant_details(
            restaurant_url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
            fetch_reviews=False,
            fetch_menu=False,
            fetch_courses=False,
        )


@pytest.mark.asyncio
async def test_get_restaurant_details_invalid_url():
    """Test detail tool validates Tabelog URL"""
    with pytest.raises(ValueError, match="restaurant_url must be a Tabelog HTTPS URL"):
        await tabelog_get_restaurant_details(restaurant_url="https://example.com/restaurant")


@pytest.mark.asyncio
async def test_get_restaurant_details_runtime_error():
    """Test detail tool wraps runtime errors with actionable context"""
    with patch("gurume.server.RestaurantDetailRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.fetch = AsyncMock(side_effect=RuntimeError("timeout"))

        with pytest.raises(RuntimeError, match="Restaurant detail request failed"):
            await tabelog_get_restaurant_details(
                restaurant_url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
            )


# ============================================================================
# Test tabelog_list_cuisines
# ============================================================================


@pytest.mark.asyncio
async def test_list_cuisines_success():
    """Test successful cuisine list retrieval"""
    results = await tabelog_list_cuisines()

    # Verify results
    assert len(results) > 0  # Should have many cuisines
    assert isinstance(results[0], CuisineOutput)

    # Verify common cuisines are present
    cuisine_names = [c.name for c in results]
    assert "すき焼き" in cuisine_names
    assert "寿司" in cuisine_names
    assert "ラーメン" in cuisine_names
    assert "焼肉" in cuisine_names

    # Verify each cuisine has a code
    for cuisine in results:
        assert cuisine.name
        assert cuisine.code
        assert cuisine.code.startswith("RC")


@pytest.mark.asyncio
async def test_list_cuisines_matches_genre_mapping():
    """Test that list_cuisines matches genre_mapping data"""
    results = await tabelog_list_cuisines()

    # Get expected cuisines from genre_mapping
    all_genres = get_all_genres()

    # Filter out cuisines without codes
    expected_cuisines = []
    for genre in all_genres:
        code = get_genre_code(genre)
        if code:
            expected_cuisines.append(genre)

    # Verify counts match
    assert len(results) == len(expected_cuisines)

    # Verify all expected cuisines are present
    result_names = [c.name for c in results]
    for expected in expected_cuisines:
        assert expected in result_names


@pytest.mark.asyncio
async def test_list_cuisines_runtime_error():
    """Test error handling when cuisine list retrieval fails"""
    with patch("gurume.server.get_all_genres") as mock_get_all:
        mock_get_all.side_effect = Exception("Unexpected error")

        with pytest.raises(RuntimeError, match="Failed to retrieve cuisine list"):
            await tabelog_list_cuisines()


# ============================================================================
# Test tabelog_get_area_suggestions
# ============================================================================


@pytest.mark.asyncio
async def test_get_area_suggestions_success(sample_area_suggestions):
    """Test successful area suggestions retrieval"""
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = sample_area_suggestions

        results = await tabelog_get_area_suggestions(query="東京")

        # Verify results
        assert len(results) == 2
        assert isinstance(results[0], SuggestionOutput)
        assert results[0].name == "東京都"
        assert results[0].datatype == "AddressMaster"
        assert results[0].id_in_datatype == 13
        assert results[0].lat == 35.6895
        assert results[0].lng == 139.6917

        assert results[1].name == "渋谷駅"
        assert results[1].datatype == "RailroadStation"

        # Verify API was called with stripped query
        mock_get_suggestions.assert_called_once_with("東京")


@pytest.mark.asyncio
async def test_get_area_suggestions_strips_whitespace(sample_area_suggestions):
    """Test that query whitespace is stripped"""
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = sample_area_suggestions

        await tabelog_get_area_suggestions(query="  東京  ")

        # Should be called with stripped query
        mock_get_suggestions.assert_called_once_with("東京")


@pytest.mark.asyncio
async def test_get_area_suggestions_empty_query():
    """Test validation of empty query"""
    with pytest.raises(ValueError, match="query parameter cannot be empty"):
        await tabelog_get_area_suggestions(query="")

    with pytest.raises(ValueError, match="query parameter cannot be empty"):
        await tabelog_get_area_suggestions(query="   ")


@pytest.mark.asyncio
async def test_get_area_suggestions_runtime_error():
    """Test error handling when API request fails"""
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Area suggestion request failed"):
            await tabelog_get_area_suggestions(query="東京")


# ============================================================================
# Test tabelog_get_keyword_suggestions
# ============================================================================


@pytest.mark.asyncio
async def test_get_keyword_suggestions_success(sample_keyword_suggestions):
    """Test successful keyword suggestions retrieval"""
    with patch(
        "gurume.server.get_keyword_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = sample_keyword_suggestions

        results = await tabelog_get_keyword_suggestions(query="すき")

        # Verify results
        assert len(results) == 3
        assert isinstance(results[0], SuggestionOutput)

        # Genre2 suggestion
        assert results[0].name == "すき焼き"
        assert results[0].datatype == "Genre2"
        assert results[0].id_in_datatype == 107
        assert results[0].lat is None
        assert results[0].lng is None

        # Restaurant suggestion
        assert results[1].name == "和田金"
        assert results[1].datatype == "Restaurant"

        # DetailCondition suggestion
        assert results[2].name == "すき焼き ランチ"
        assert results[2].datatype == "Genre2 DetailCondition"

        # Verify API was called with stripped query
        mock_get_suggestions.assert_called_once_with("すき")


@pytest.mark.asyncio
async def test_get_keyword_suggestions_strips_whitespace(sample_keyword_suggestions):
    """Test that query whitespace is stripped"""
    with patch(
        "gurume.server.get_keyword_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = sample_keyword_suggestions

        await tabelog_get_keyword_suggestions(query="  すき  ")

        # Should be called with stripped query
        mock_get_suggestions.assert_called_once_with("すき")


@pytest.mark.asyncio
async def test_get_keyword_suggestions_empty_query():
    """Test validation of empty query"""
    with pytest.raises(ValueError, match="query parameter cannot be empty"):
        await tabelog_get_keyword_suggestions(query="")

    with pytest.raises(ValueError, match="query parameter cannot be empty"):
        await tabelog_get_keyword_suggestions(query="   ")


@pytest.mark.asyncio
async def test_get_keyword_suggestions_runtime_error():
    """Test error handling when API request fails"""
    with patch(
        "gurume.server.get_keyword_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Keyword suggestion request failed"):
            await tabelog_get_keyword_suggestions(query="すき")


# ============================================================================
# Integration-style Tests (verify tool interactions)
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_cuisine_validation():
    """Test recommended workflow: list cuisines → validate → search"""
    # Step 1: List cuisines
    cuisines = await tabelog_list_cuisines()
    cuisine_names = [c.name for c in cuisines]

    # Step 2: Verify user's cuisine is in the list
    user_cuisine = "すき焼き"
    assert user_cuisine in cuisine_names

    # Step 3: Get cuisine code
    cuisine_obj = next(c for c in cuisines if c.name == user_cuisine)
    assert cuisine_obj.code == "RC0107"


@pytest.mark.asyncio
async def test_workflow_area_validation(sample_area_suggestions, sample_restaurants):
    """Test recommended workflow: get area suggestions → search"""
    # Step 1: Get area suggestions
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_area:
        mock_area.return_value = sample_area_suggestions
        area_suggestions = await tabelog_get_area_suggestions(query="東京")

    # Step 2: Select best area suggestion
    selected_area = area_suggestions[0].name  # "東京都"
    assert selected_area == "東京都"

    # Step 3: Search with validated area
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response
        results = await tabelog_search_restaurants(area=selected_area)

    assert len(results.items) == 2


@pytest.mark.asyncio
async def test_workflow_keyword_to_cuisine(sample_keyword_suggestions, sample_restaurants):
    """Test recommended workflow: keyword suggestions → detect Genre2 → search with cuisine"""
    # Step 1: Get keyword suggestions
    with patch(
        "gurume.server.get_keyword_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_keyword:
        mock_keyword.return_value = sample_keyword_suggestions
        keyword_suggestions = await tabelog_get_keyword_suggestions(query="すき")

    # Step 2: Identify Genre2 suggestions (cuisine types)
    genre_suggestions = [s for s in keyword_suggestions if s.datatype == "Genre2"]
    assert len(genre_suggestions) > 0
    selected_cuisine = genre_suggestions[0].name  # "すき焼き"

    # Step 3: Search using cuisine parameter (not keyword)
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response
        results = await tabelog_search_restaurants(cuisine=selected_cuisine)

    assert len(results.items) == 2


@pytest.mark.asyncio
async def test_mcp_tool_schema_exposes_search_constraints():
    """Test FastMCP exposes the richer search schema and annotations"""
    tools = await mcp.list_tools()
    search_tool = next(tool for tool in tools if tool.name == "tabelog_search_restaurants")

    assert search_tool.annotations is not None
    assert search_tool.annotations.readOnlyHint is True
    assert search_tool.annotations.idempotentHint is True
    assert search_tool.annotations.openWorldHint is True

    limit_schema = search_tool.inputSchema["properties"]["limit"]
    assert limit_schema["minimum"] == 1
    assert limit_schema["maximum"] == 60

    page_schema = search_tool.inputSchema["properties"]["page"]
    assert page_schema["minimum"] == 1

    sort_schema = search_tool.inputSchema["properties"]["sort"]
    assert sort_schema["enum"] == ["ranking", "review-count", "new-open", "standard"]

    assert search_tool.outputSchema is not None
    output_schema = search_tool.outputSchema
    assert output_schema["properties"]["status"]["enum"] == ["success", "no_results"]
    assert "applied_filters" in output_schema["properties"]
    assert "has_more" in output_schema["properties"]
    assert output_schema["properties"]["applied_filters"]["$ref"] == "#/$defs/SearchFiltersOutput"


@pytest.mark.asyncio
async def test_mcp_tool_schema_exposes_detail_constraints():
    """Test FastMCP exposes the restaurant detail tool schema"""
    tools = await mcp.list_tools()
    detail_tool = next(tool for tool in tools if tool.name == "tabelog_get_restaurant_details")

    assert detail_tool.annotations is not None
    assert detail_tool.annotations.readOnlyHint is True
    assert detail_tool.annotations.idempotentHint is True
    assert detail_tool.annotations.openWorldHint is True

    url_schema = detail_tool.inputSchema["properties"]["restaurant_url"]
    assert url_schema["pattern"] == r"^https://tabelog\.com/.+"

    review_pages_schema = detail_tool.inputSchema["properties"]["max_review_pages"]
    assert review_pages_schema["minimum"] == 1

    assert detail_tool.outputSchema is not None
    output_schema = detail_tool.outputSchema
    assert "restaurant" in output_schema["properties"]
    assert "address" in output_schema["properties"]
    assert "reservation_url" in output_schema["properties"]
    assert "review_count" in output_schema["properties"]
    assert "menu_items" in output_schema["properties"]
    assert "courses" in output_schema["properties"]


@pytest.mark.asyncio
async def test_mcp_call_tool_returns_structured_envelope(sample_restaurants):
    """Test calling the tool through FastMCP returns the structured envelope"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response
        content, structured = await mcp.call_tool(
            "tabelog_search_restaurants",
            {"area": "東京", "cuisine": "寿司", "limit": 5, "page": 2},
        )

    structured_data = cast(dict[str, Any], structured)
    assert mock_search.await_count == 1
    assert content
    assert structured_data["status"] == "success"
    assert structured_data["returned_count"] == 2
    assert structured_data["limit"] == 5
    assert structured_data["applied_filters"]["page"] == 2
    assert structured_data["applied_filters"]["cuisine"] == "寿司"
    assert structured_data["items"][0]["name"] == "テスト寿司"


@pytest.mark.asyncio
async def test_mcp_call_detail_tool_returns_structured_data(sample_restaurant_detail):
    """Test calling the detail tool through FastMCP returns structured content"""
    with patch("gurume.server.RestaurantDetailRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.fetch = AsyncMock(return_value=sample_restaurant_detail)

        content, structured = await mcp.call_tool(
            "tabelog_get_restaurant_details",
            {
                "restaurant_url": "https://tabelog.com/tokyo/A1301/A130101/13000001/",
                "max_review_pages": 2,
                "fetch_courses": False,
            },
        )

    structured_data = cast(dict[str, Any], structured)
    assert content
    assert structured_data["review_count"] == 1
    assert structured_data["menu_item_count"] == 1
    assert structured_data["course_count"] == 1
    assert structured_data["restaurant"]["name"] == "テスト寿司"
    assert structured_data["station"] == "銀座駅"
    assert structured_data["address"] == "東京都中央区銀座1-2-3"
    assert structured_data["reservation_url"] == "https://tabelog.com/tokyo/A1301/A130101/13000001/reserve/"
    assert structured_data["max_review_pages"] == 2
    assert structured_data["fetch_courses"] is False
    assert structured_data["reviews"][0]["reviewer"] == "評論者A"
