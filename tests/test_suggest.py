"""Tests for suggestion API (area and keyword suggestions)"""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import httpx
import pytest

from gurume.suggest import AreaSuggestion
from gurume.suggest import KeywordSuggestion
from gurume.suggest import get_area_suggestions
from gurume.suggest import get_area_suggestions_async
from gurume.suggest import get_keyword_suggestions
from gurume.suggest import get_keyword_suggestions_async

# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_area_response():
    """Sample API response for area suggestions"""
    return [
        {
            "name": "東京都",
            "datatype": "AddressMaster",
            "id_in_datatype": 13,
            "lat": 35.6895,
            "lng": 139.6917,
            "related_info": "",
        },
        {
            "name": "渋谷駅",
            "datatype": "RailroadStation",
            "id_in_datatype": 1001,
            "lat": 35.6580,
            "lng": 139.7016,
            "related_info": "",
        },
        {
            "name": "新宿区",
            "datatype": "AddressMaster",
            "id_in_datatype": 131,
            "lat": 35.6938,
            "lng": 139.7034,
            "related_info": "",
        },
    ]


@pytest.fixture
def sample_keyword_response():
    """Sample API response for keyword suggestions"""
    return [
        {
            "name": "すき焼き",
            "datatype": "Genre2",
            "id_in_datatype": 107,
            "lat": None,
            "lng": None,
            "related_info": "",
        },
        {
            "name": "和田金",
            "datatype": "Restaurant",
            "id_in_datatype": 24000123,
            "lat": None,
            "lng": None,
            "related_info": "",
        },
        {
            "name": "すき焼き ランチ",
            "datatype": "Genre2 DetailCondition",
            "id_in_datatype": 107,
            "lat": None,
            "lng": None,
            "related_info": "",
        },
    ]


# ============================================================================
# Test get_area_suggestions (sync)
# ============================================================================


def test_get_area_suggestions_success(sample_area_response):
    """Test successful area suggestions retrieval"""
    mock_response = Mock()
    mock_response.json.return_value = sample_area_response
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        results = get_area_suggestions(query="東京")

        # Verify results
        assert len(results) == 3
        assert isinstance(results[0], AreaSuggestion)

        # First suggestion
        assert results[0].name == "東京都"
        assert results[0].datatype == "AddressMaster"
        assert results[0].id_in_datatype == 13
        assert results[0].lat == 35.6895
        assert results[0].lng == 139.6917

        # Second suggestion
        assert results[1].name == "渋谷駅"
        assert results[1].datatype == "RailroadStation"

        # Third suggestion
        assert results[2].name == "新宿区"

        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"] == {"sa": "東京"}
        assert "User-Agent" in call_args.kwargs["headers"]


def test_get_area_suggestions_empty_query():
    """Test with empty query returns empty list"""
    assert get_area_suggestions(query="") == []
    assert get_area_suggestions(query="   ") == []


def test_get_area_suggestions_strips_whitespace(sample_area_response):
    """Test that query whitespace is stripped"""
    mock_response = Mock()
    mock_response.json.return_value = sample_area_response
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        get_area_suggestions(query="  東京  ")

        call_args = mock_get.call_args
        assert call_args.kwargs["params"] == {"sa": "東京"}


def test_get_area_suggestions_http_error():
    """Test handling HTTP errors"""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock())

        # Should return empty list on error
        results = get_area_suggestions(query="東京")
        assert results == []


def test_get_area_suggestions_network_error():
    """Test handling network errors"""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        # Should return empty list on error
        results = get_area_suggestions(query="東京")
        assert results == []


def test_get_area_suggestions_json_error():
    """Test handling JSON parsing errors"""
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response):
        # Should return empty list on JSON error
        results = get_area_suggestions(query="東京")
        assert results == []


def test_get_area_suggestions_empty_response():
    """Test with empty API response"""
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response):
        results = get_area_suggestions(query="東京")
        assert results == []


def test_get_area_suggestions_missing_fields():
    """Test handling responses with missing fields"""
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "name": "東京都",
            # Missing datatype, id_in_datatype, lat, lng
        }
    ]
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response):
        results = get_area_suggestions(query="東京")

        # Should use defaults for missing fields
        assert len(results) == 1
        assert results[0].name == "東京都"
        assert results[0].datatype == ""
        assert results[0].id_in_datatype == 0
        assert results[0].lat is None
        assert results[0].lng is None


# ============================================================================
# Test get_area_suggestions_async (async)
# ============================================================================


@pytest.mark.asyncio
async def test_get_area_suggestions_async_success(sample_area_response):
    """Test successful async area suggestions retrieval"""
    mock_response = Mock()
    mock_response.json.return_value = sample_area_response
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await get_area_suggestions_async(query="東京")

        # Verify results
        assert len(results) == 3
        assert isinstance(results[0], AreaSuggestion)
        assert results[0].name == "東京都"
        assert results[0].datatype == "AddressMaster"
        assert results[1].name == "渋谷駅"
        assert results[2].name == "新宿区"

        # Verify API was called
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_area_suggestions_async_empty_query():
    """Test async with empty query"""
    assert await get_area_suggestions_async(query="") == []
    assert await get_area_suggestions_async(query="   ") == []


@pytest.mark.asyncio
async def test_get_area_suggestions_async_http_error():
    """Test async handling HTTP errors"""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("404", request=Mock(), response=Mock()))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await get_area_suggestions_async(query="東京")
        assert results == []


# ============================================================================
# Test get_keyword_suggestions (sync)
# ============================================================================


def test_get_keyword_suggestions_success(sample_keyword_response):
    """Test successful keyword suggestions retrieval"""
    mock_response = Mock()
    mock_response.json.return_value = sample_keyword_response
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        results = get_keyword_suggestions(query="すき")

        # Verify results
        assert len(results) == 3
        assert isinstance(results[0], KeywordSuggestion)

        # Genre2 suggestion
        assert results[0].name == "すき焼き"
        assert results[0].datatype == "Genre2"
        assert results[0].id_in_datatype == 107
        assert results[0].lat is None
        assert results[0].lng is None

        # Restaurant suggestion
        assert results[1].name == "和田金"
        assert results[1].datatype == "Restaurant"
        assert results[1].id_in_datatype == 24000123

        # DetailCondition suggestion
        assert results[2].name == "すき焼き ランチ"
        assert results[2].datatype == "Genre2 DetailCondition"

        # Verify API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"] == {"sk": "すき"}
        assert "User-Agent" in call_args.kwargs["headers"]


def test_get_keyword_suggestions_empty_query():
    """Test with empty query returns empty list"""
    assert get_keyword_suggestions(query="") == []
    assert get_keyword_suggestions(query="   ") == []


def test_get_keyword_suggestions_strips_whitespace(sample_keyword_response):
    """Test that query whitespace is stripped"""
    mock_response = Mock()
    mock_response.json.return_value = sample_keyword_response
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        get_keyword_suggestions(query="  すき  ")

        call_args = mock_get.call_args
        assert call_args.kwargs["params"] == {"sk": "すき"}


def test_get_keyword_suggestions_http_error():
    """Test handling HTTP errors"""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError("500 Server Error", request=Mock(), response=Mock())

        # Should return empty list on error
        results = get_keyword_suggestions(query="すき")
        assert results == []


def test_get_keyword_suggestions_network_error():
    """Test handling network errors"""
    with patch("httpx.get") as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timeout")

        # Should return empty list on error
        results = get_keyword_suggestions(query="すき")
        assert results == []


def test_get_keyword_suggestions_empty_response():
    """Test with empty API response"""
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response):
        results = get_keyword_suggestions(query="すき")
        assert results == []


# ============================================================================
# Test get_keyword_suggestions_async (async)
# ============================================================================


@pytest.mark.asyncio
async def test_get_keyword_suggestions_async_success(sample_keyword_response):
    """Test successful async keyword suggestions retrieval"""
    mock_response = Mock()
    mock_response.json.return_value = sample_keyword_response
    mock_response.raise_for_status = Mock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await get_keyword_suggestions_async(query="すき")

        # Verify results
        assert len(results) == 3
        assert isinstance(results[0], KeywordSuggestion)
        assert results[0].name == "すき焼き"
        assert results[0].datatype == "Genre2"
        assert results[1].name == "和田金"
        assert results[1].datatype == "Restaurant"
        assert results[2].name == "すき焼き ランチ"

        # Verify API was called
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_keyword_suggestions_async_empty_query():
    """Test async with empty query"""
    assert await get_keyword_suggestions_async(query="") == []
    assert await get_keyword_suggestions_async(query="   ") == []


@pytest.mark.asyncio
async def test_get_keyword_suggestions_async_http_error():
    """Test async handling HTTP errors"""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("500", request=Mock(), response=Mock()))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        results = await get_keyword_suggestions_async(query="すき")
        assert results == []


# ============================================================================
# Integration Tests
# ============================================================================


def test_area_and_keyword_dataclass_compatibility():
    """Test that AreaSuggestion and KeywordSuggestion dataclasses work correctly"""
    # AreaSuggestion with all fields
    area1 = AreaSuggestion(
        name="東京都",
        datatype="AddressMaster",
        id_in_datatype=13,
        lat=35.6895,
        lng=139.6917,
    )
    assert area1.name == "東京都"
    assert area1.lat == 35.6895

    # AreaSuggestion with optional fields
    area2 = AreaSuggestion(
        name="渋谷区",
        datatype="AddressMaster",
        id_in_datatype=131,
    )
    assert area2.lat is None
    assert area2.lng is None

    # KeywordSuggestion with all fields
    keyword1 = KeywordSuggestion(
        name="すき焼き",
        datatype="Genre2",
        id_in_datatype=107,
    )
    assert keyword1.name == "すき焼き"
    assert keyword1.datatype == "Genre2"
    assert keyword1.lat is None

    # KeywordSuggestion with string id
    keyword2 = KeywordSuggestion(
        name="和田金",
        datatype="Restaurant",
        id_in_datatype="rest_123",
    )
    assert keyword2.id_in_datatype == "rest_123"
