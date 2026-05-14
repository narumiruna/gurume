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
from gurume.server import CuisineListOutput
from gurume.server import CuisineOutput
from gurume.server import RestaurantDetailOutput
from gurume.server import RestaurantOutput
from gurume.server import RestaurantSearchOutput
from gurume.server import SuggestionListOutput
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
    low_limit = await tabelog_search_restaurants(limit=0)
    high_limit = await tabelog_search_restaurants(limit=100)

    assert low_limit.status == "error"
    assert low_limit.error is not None
    assert low_limit.error.error_code == "invalid_parameters"
    assert "limit must be between 1 and 60" in low_limit.error.detail

    assert high_limit.status == "error"
    assert high_limit.error is not None
    assert high_limit.error.error_code == "invalid_parameters"
    assert "limit must be between 1 and 60" in high_limit.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_invalid_page():
    """Test validation of page parameter"""
    result = await tabelog_search_restaurants(page=0)

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "page must be greater than or equal to 1" in result.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_invalid_sort():
    """Test validation of sort parameter"""
    result = await tabelog_search_restaurants(sort="invalid-sort-type")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "Invalid sort type" in result.error.detail
    assert "ranking, review-count, new-open, or standard" in result.error.suggested_action


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_date():
    """Test validation of reservation_date parameter"""
    result = await tabelog_search_restaurants(reservation_date="2026-04-27")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "reservation_date must be in YYYYMMDD format" in result.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_time():
    """Test validation of reservation_time parameter"""
    result = await tabelog_search_restaurants(reservation_time="19:00")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "reservation_time must be in HHMM format" in result.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_requires_reservation_time_with_date():
    """Test semantic validation for reservation filters"""
    result = await tabelog_search_restaurants(reservation_date="20260427")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "reservation_time is required" in result.error.detail
    assert "Provide `reservation_date` as YYYYMMDD and `reservation_time` as HHMM together" in (
        result.error.suggested_action
    )


@pytest.mark.asyncio
async def test_search_restaurants_requires_reservation_date_with_party_size():
    """Test reservation bundle validation when party_size is set"""
    result = await tabelog_search_restaurants(party_size=2)

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "reservation_date is required" in result.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_invalid_reservation_time_value():
    """Test semantic validation of HHMM values"""
    result = await tabelog_search_restaurants(reservation_date="20260427", reservation_time="2460")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "valid 24-hour time" in result.error.detail


@pytest.mark.asyncio
async def test_search_restaurants_unknown_cuisine():
    """Test error handling for unknown cuisine type"""
    result = await tabelog_search_restaurants(cuisine="存在しない料理")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "unsupported_cuisine"
    assert "Unknown cuisine type" in result.error.detail
    assert "`tabelog_get_keyword_suggestions`" in result.error.suggested_action
    assert "`tabelog_list_cuisines`" in result.error.suggested_action


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

        result = await tabelog_search_restaurants(area="東京")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "internal_error"
    assert result.error.retryable is True
    assert result.error.detail == "Network error"


@pytest.mark.asyncio
async def test_search_restaurants_raises_for_error_status():
    """Test MCP wrapper returns structured errors for SearchResponse failures"""
    mock_response = SearchResponse(
        status=SearchStatus.ERROR,
        restaurants=[],
        meta=None,
        error_message="upstream error",
    )

    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = mock_response

        result = await tabelog_search_restaurants(area="東京")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "upstream_unavailable"
    assert result.error.detail == "upstream error"


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
    assert result.status == "success"
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
    result = await tabelog_get_restaurant_details(
        restaurant_url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
        fetch_reviews=False,
        fetch_menu=False,
        fetch_courses=False,
    )

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "At least one of fetch_reviews" in result.error.detail


@pytest.mark.asyncio
async def test_get_restaurant_details_invalid_url():
    """Test detail tool validates Tabelog URL"""
    result = await tabelog_get_restaurant_details(restaurant_url="https://example.com/restaurant")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "invalid_parameters"
    assert "restaurant_url must be a Tabelog HTTPS URL" in result.error.detail


@pytest.mark.asyncio
async def test_get_restaurant_details_runtime_error():
    """Test detail tool wraps runtime errors with actionable context"""
    with patch("gurume.server.RestaurantDetailRequest") as mock_request_class:
        mock_request = mock_request_class.return_value
        mock_request.fetch = AsyncMock(side_effect=RuntimeError("timeout"))

        result = await tabelog_get_restaurant_details(
            restaurant_url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
        )

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "upstream_unavailable"
    assert result.error.detail == "timeout"


# ============================================================================
# Test tabelog_list_cuisines
# ============================================================================


@pytest.mark.asyncio
async def test_list_cuisines_success():
    """Test successful cuisine list retrieval"""
    results = await tabelog_list_cuisines()

    # Verify results
    assert isinstance(results, CuisineListOutput)
    assert results.status == "success"
    assert len(results.items) > 0  # Should have many cuisines
    assert isinstance(results.items[0], CuisineOutput)

    # Verify common cuisines are present
    cuisine_names = [c.name for c in results.items]
    assert "すき焼き" in cuisine_names
    assert "寿司" in cuisine_names
    assert "ラーメン" in cuisine_names
    assert "焼肉" in cuisine_names

    # Verify each cuisine has a code
    for cuisine in results.items:
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
    assert len(results.items) == len(expected_cuisines)

    # Verify all expected cuisines are present
    result_names = [c.name for c in results.items]
    for expected in expected_cuisines:
        assert expected in result_names


@pytest.mark.asyncio
async def test_list_cuisines_runtime_error():
    """Test error handling when cuisine list retrieval fails"""
    with patch("gurume.server.get_all_genres") as mock_get_all:
        mock_get_all.side_effect = Exception("Unexpected error")

        result = await tabelog_list_cuisines()

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "internal_error"
    assert result.error.detail == "Unexpected error"


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
        assert isinstance(results, SuggestionListOutput)
        assert results.status == "success"
        assert len(results.items) == 2
        assert isinstance(results.items[0], SuggestionOutput)
        assert results.items[0].name == "東京都"
        assert results.items[0].datatype == "AddressMaster"
        assert results.items[0].id_in_datatype == 13
        assert results.items[0].lat == 35.6895
        assert results.items[0].lng == 139.6917

        assert results.items[1].name == "渋谷駅"
        assert results.items[1].datatype == "RailroadStation"

        # Verify API was called with stripped query
        mock_get_suggestions.assert_called_once_with("東京")


@pytest.mark.asyncio
async def test_get_area_suggestions_accepts_town_datatype():
    """Test area suggestions can return upstream Town datatypes."""
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.return_value = [
            AreaSuggestion(
                name="三重町",
                datatype="Town",
                id_in_datatype=12345,
                lat=33.0,
                lng=131.5,
            )
        ]

        results = await tabelog_get_area_suggestions(query="三重")

    assert results.status == "success"
    assert len(results.items) == 1
    assert results.items[0].name == "三重町"
    assert results.items[0].datatype == "Town"


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
    empty_result = await tabelog_get_area_suggestions(query="")
    blank_result = await tabelog_get_area_suggestions(query="   ")

    assert empty_result.status == "error"
    assert empty_result.error is not None
    assert empty_result.error.error_code == "invalid_parameters"
    assert "query parameter cannot be empty" in empty_result.error.detail

    assert blank_result.status == "error"
    assert blank_result.error is not None
    assert blank_result.error.error_code == "invalid_parameters"
    assert "query parameter cannot be empty" in blank_result.error.detail


@pytest.mark.asyncio
async def test_get_area_suggestions_runtime_error():
    """Test error handling when API request fails"""
    with patch(
        "gurume.server.get_area_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.side_effect = Exception("Network error")

        result = await tabelog_get_area_suggestions(query="東京")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "internal_error"
    assert result.error.detail == "Network error"


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
        assert isinstance(results, SuggestionListOutput)
        assert results.status == "success"
        assert len(results.items) == 3
        assert isinstance(results.items[0], SuggestionOutput)

        # Genre2 suggestion
        assert results.items[0].name == "すき焼き"
        assert results.items[0].datatype == "Genre2"
        assert results.items[0].id_in_datatype == 107
        assert results.items[0].lat is None
        assert results.items[0].lng is None

        # Restaurant suggestion
        assert results.items[1].name == "和田金"
        assert results.items[1].datatype == "Restaurant"

        # DetailCondition suggestion
        assert results.items[2].name == "すき焼き ランチ"
        assert results.items[2].datatype == "Genre2 DetailCondition"

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
    empty_result = await tabelog_get_keyword_suggestions(query="")
    blank_result = await tabelog_get_keyword_suggestions(query="   ")

    assert empty_result.status == "error"
    assert empty_result.error is not None
    assert empty_result.error.error_code == "invalid_parameters"
    assert "query parameter cannot be empty" in empty_result.error.detail

    assert blank_result.status == "error"
    assert blank_result.error is not None
    assert blank_result.error.error_code == "invalid_parameters"
    assert "query parameter cannot be empty" in blank_result.error.detail


@pytest.mark.asyncio
async def test_get_keyword_suggestions_runtime_error():
    """Test error handling when API request fails"""
    with patch(
        "gurume.server.get_keyword_suggestions_async",
        new_callable=AsyncMock,
    ) as mock_get_suggestions:
        mock_get_suggestions.side_effect = Exception("Network error")

        result = await tabelog_get_keyword_suggestions(query="すき")

    assert result.status == "error"
    assert result.error is not None
    assert result.error.error_code == "internal_error"
    assert result.error.detail == "Network error"


# ============================================================================
# Integration-style Tests (verify tool interactions)
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_cuisine_validation():
    """Test recommended workflow: list cuisines → validate → search"""
    # Step 1: List cuisines
    cuisines = await tabelog_list_cuisines()
    cuisine_names = [c.name for c in cuisines.items]

    # Step 2: Verify user's cuisine is in the list
    user_cuisine = "すき焼き"
    assert user_cuisine in cuisine_names

    # Step 3: Get cuisine code
    cuisine_obj = next(c for c in cuisines.items if c.name == user_cuisine)
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
    selected_area = area_suggestions.items[0].name  # "東京都"
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
    genre_suggestions = [s for s in keyword_suggestions.items if s.datatype == "Genre2"]
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
    assert output_schema["properties"]["status"]["enum"] == ["success", "no_results", "error"]
    assert "applied_filters" in output_schema["properties"]
    assert "has_more" in output_schema["properties"]
    assert "error" in output_schema["properties"]
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
    assert output_schema["properties"]["status"]["enum"] == ["success", "error"]
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
    assert structured_data["status"] == "success"
    assert structured_data["station"] == "銀座駅"
    assert structured_data["address"] == "東京都中央区銀座1-2-3"
    assert structured_data["reservation_url"] == "https://tabelog.com/tokyo/A1301/A130101/13000001/reserve/"
    assert structured_data["max_review_pages"] == 2
    assert structured_data["fetch_courses"] is False
    assert structured_data["reviews"][0]["reviewer"] == "評論者A"


@pytest.mark.asyncio
async def test_mcp_call_tool_returns_structured_error_for_unknown_cuisine():
    """Test FastMCP search calls preserve structured error details for agent recovery"""
    content, structured = await mcp.call_tool(
        "tabelog_search_restaurants",
        {"cuisine": "存在しない料理"},
    )

    structured_data = cast(dict[str, Any], structured)
    assert content
    assert structured_data["status"] == "error"
    assert structured_data["error"]["error_code"] == "unsupported_cuisine"
    assert structured_data["error"]["retryable"] is False


@pytest.mark.asyncio
async def test_mcp_call_area_suggestions_returns_structured_error_for_empty_query():
    """Test FastMCP suggestion calls preserve structured validation errors"""
    content, structured = await mcp.call_tool(
        "tabelog_get_area_suggestions",
        {"query": "   "},
    )

    structured_data = cast(dict[str, Any], structured)
    assert content
    assert structured_data["status"] == "error"
    assert structured_data["error"]["error_code"] == "invalid_parameters"


# ============================================================================
# Test run() transport switching (issue #39)
# ============================================================================


class TestRunTransport:
    """Test the entry point honors transport flags."""

    def test_stdio_default_does_not_mutate_settings(self):
        from gurume import server

        original_host = server.mcp.settings.host
        original_port = server.mcp.settings.port

        with patch.object(server.mcp, "run") as mock_mcp_run:
            server.run()
            mock_mcp_run.assert_called_once_with(transport="stdio")

        # stdio must NOT mutate HTTP settings
        assert server.mcp.settings.host == original_host
        assert server.mcp.settings.port == original_port

    def test_streamable_http_mutates_settings_and_runs(self):
        from gurume import server

        with patch.object(server.mcp, "run") as mock_mcp_run:
            server.run(
                transport="streamable-http",
                host="0.0.0.0",
                port=9001,
                path="/api/mcp",
            )
            mock_mcp_run.assert_called_once_with(transport="streamable-http")

        assert server.mcp.settings.host == "0.0.0.0"
        assert server.mcp.settings.port == 9001
        assert server.mcp.settings.streamable_http_path == "/api/mcp"

    def test_sse_sets_sse_path(self):
        from gurume import server

        with patch.object(server.mcp, "run") as mock_mcp_run:
            server.run(transport="sse", host="127.0.0.1", port=8765, path="/events")
            mock_mcp_run.assert_called_once_with(transport="sse")

        assert server.mcp.settings.host == "127.0.0.1"
        assert server.mcp.settings.port == 8765
        assert server.mcp.settings.sse_path == "/events"
