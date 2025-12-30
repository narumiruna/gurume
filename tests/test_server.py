"""Tests for MCP server tools (FastMCP implementation)"""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from gurume.genre_mapping import get_all_genres
from gurume.genre_mapping import get_genre_code
from gurume.restaurant import Restaurant
from gurume.search import SearchResponse
from gurume.search import SearchStatus
from gurume.server import CuisineOutput
from gurume.server import RestaurantOutput
from gurume.server import SuggestionOutput
from gurume.server import tabelog_get_area_suggestions
from gurume.server import tabelog_get_keyword_suggestions
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


# ============================================================================
# Test tabelog_search_restaurants
# ============================================================================


@pytest.mark.asyncio
async def test_search_restaurants_success(sample_restaurants):
    """Test successful restaurant search"""
    mock_response = SearchResponse(
        status=SearchStatus.SUCCESS,
        restaurants=sample_restaurants,
        meta=None,
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
        assert len(results) == 2
        assert isinstance(results[0], RestaurantOutput)
        assert results[0].name == "テスト寿司"
        assert results[0].rating == 4.5
        assert results[0].review_count == 123
        assert results[0].area == "銀座"
        assert results[0].genres == ["寿司", "和食"]
        assert results[0].lunch_price == "¥5,000～¥5,999"
        assert results[0].dinner_price == "¥10,000～¥14,999"

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

        assert len(results) == 2
        mock_search.assert_called_once()


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
        assert len(results) == 3


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
async def test_search_restaurants_invalid_sort():
    """Test validation of sort parameter"""
    with pytest.raises(ValueError, match="Invalid sort type"):
        await tabelog_search_restaurants(sort="invalid-sort-type")


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
            assert len(results) == 2


@pytest.mark.asyncio
async def test_search_restaurants_runtime_error():
    """Test error handling when search operation fails"""
    with patch("gurume.server.SearchRequest.search", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError, match="Restaurant search failed"):
            await tabelog_search_restaurants(area="東京")


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

    assert len(results) == 2


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

    assert len(results) == 2
