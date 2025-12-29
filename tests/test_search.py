"""Test search functionality"""

from datetime import datetime
from unittest.mock import Mock
from unittest.mock import patch

import httpx
import pytest

from gurume.restaurant import Restaurant
from gurume.search import SearchMeta
from gurume.search import SearchRequest
from gurume.search import SearchResponse
from gurume.search import SearchStatus


class TestSearchMeta:
    """Test SearchMeta model"""

    def test_search_meta_creation(self):
        """Test creating SearchMeta instance"""
        meta = SearchMeta(
            total_count=100,
            current_page=1,
            results_per_page=20,
            total_pages=5,
            has_next_page=True,
            has_prev_page=False,
        )

        assert meta.total_count == 100
        assert meta.current_page == 1
        assert meta.results_per_page == 20
        assert meta.total_pages == 5
        assert meta.has_next_page is True
        assert meta.has_prev_page is False
        assert isinstance(meta.search_time, datetime)


class TestSearchResponse:
    """Test SearchResponse model"""

    def test_search_response_success(self):
        """Test successful search response"""
        restaurants = [
            Restaurant(name="テスト1", url="https://test1.com"),
            Restaurant(name="テスト2", url="https://test2.com"),
        ]

        meta = SearchMeta(
            total_count=2,
            current_page=1,
            results_per_page=20,
            total_pages=1,
            has_next_page=False,
            has_prev_page=False,
        )

        response = SearchResponse(
            status=SearchStatus.SUCCESS,
            restaurants=restaurants,
            meta=meta,
        )

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 2
        assert response.meta is not None and response.meta.total_count == 2
        assert response.error_message is None

    def test_search_response_no_results(self):
        """Test no results search response"""
        response = SearchResponse(
            status=SearchStatus.NO_RESULTS,
            restaurants=[],
        )

        assert response.status == SearchStatus.NO_RESULTS
        assert len(response.restaurants) == 0
        assert response.meta is None

    def test_search_response_error(self):
        """Test error search response"""
        response = SearchResponse(
            status=SearchStatus.ERROR,
            error_message="HTTP 404 Not Found",
        )

        assert response.status == SearchStatus.ERROR
        assert len(response.restaurants) == 0
        assert response.error_message == "HTTP 404 Not Found"


class TestSearchRequest:
    """Test SearchRequest functionality"""

    def test_search_request_creation(self):
        """Test creating SearchRequest instance"""
        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=3,
            include_meta=True,
            timeout=30.0,
        )

        assert request.area == "銀座"
        assert request.keyword == "寿司"
        assert request.max_pages == 3
        assert request.include_meta is True
        assert request.timeout == 30.0

    def test_parse_meta(self, mock_html_response):
        """Test parsing search metadata"""
        request = SearchRequest()
        meta = request._parse_meta(mock_html_response, current_page=1)

        assert meta.total_count == 100
        assert meta.current_page == 1
        assert meta.results_per_page == 2  # 我們的 mock HTML 只有 2 個餐廳
        assert meta.total_pages == 50  # 100 / 2 = 50
        assert meta.has_next_page is True
        assert meta.has_prev_page is False

    def test_parse_meta_no_results(self):
        """Test parsing metadata when no results"""
        request = SearchRequest()
        empty_html = "<html><body><span class='c-page-count__num'>0</span></body></html>"
        meta = request._parse_meta(empty_html, current_page=1)

        assert meta.total_count == 0
        assert meta.current_page == 1
        assert meta.total_pages == 1
        assert meta.has_next_page is False
        assert meta.has_prev_page is False

    def test_create_restaurant_request(self):
        """Test creating restaurant request"""
        search_request = SearchRequest(
            area="銀座",
            keyword="寿司",
            reservation_date="20250715",
            reservation_time="1900",
            party_size=2,
        )

        restaurant_request = search_request._create_restaurant_request(page=2)

        assert restaurant_request.area == "銀座"
        assert restaurant_request.keyword == "寿司"
        assert restaurant_request.reservation_date == "20250715"
        assert restaurant_request.reservation_time == "1900"
        assert restaurant_request.party_size == 2
        assert restaurant_request.page == 2

    @patch("httpx.get")
    def test_do_sync_single_page(self, mock_get, mock_html_response):
        """Test synchronous search for single page"""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=1,
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 2
        assert response.meta is not None
        assert response.meta.total_count == 100
        assert response.error_message is None

        # Check that httpx.get was called once
        mock_get.assert_called_once()

    @patch("httpx.get")
    def test_do_sync_multiple_pages(self, mock_get, mock_html_response):
        """Test synchronous search for multiple pages"""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=3,
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 6  # 2 restaurants per page * 3 pages
        assert response.meta is not None

        # Check that httpx.get was called 3 times
        assert mock_get.call_count == 3

    @patch("httpx.get")
    def test_do_sync_no_results(self, mock_get):
        """Test synchronous search with no results"""
        mock_response = Mock()
        mock_response.text = "<html><body><span class='c-page-count__num'>0</span></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=1,
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status == SearchStatus.NO_RESULTS
        assert len(response.restaurants) == 0
        assert response.meta is not None
        assert response.meta.total_count == 0

    @patch("httpx.get")
    def test_do_sync_http_error(self, mock_get):
        """Test synchronous search with HTTP error"""
        mock_get.side_effect = httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock())

        request = SearchRequest(area="銀座", keyword="寿司")
        response = request.do_sync()

        assert response.status == SearchStatus.ERROR
        assert response.error_message is not None and "404 Not Found" in response.error_message
        assert len(response.restaurants) == 0

    @patch("httpx.get")
    def test_do_sync_without_meta(self, mock_get, mock_html_response):
        """Test synchronous search without metadata"""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=1,
            include_meta=False,
        )

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 2
        assert response.meta is None

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async_single_page(self, mock_client_class, mock_html_response):
        """Test asynchronous search for single page"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=1,
            include_meta=True,
        )

        response = await request.do()

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 2
        assert response.meta is not None
        assert response.meta.total_count == 100

        # Check that AsyncClient was created with correct parameters
        mock_client_class.assert_called_once_with(timeout=30.0, follow_redirects=True)
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async_multiple_pages(self, mock_client_class, mock_html_response):
        """Test asynchronous search for multiple pages"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=2,
            include_meta=True,
        )

        response = await request.do()

        assert response.status == SearchStatus.SUCCESS
        assert len(response.restaurants) == 4  # 2 restaurants per page * 2 pages
        assert response.meta is not None

        # Check that get was called 2 times
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async_http_error(self, mock_client_class):
        """Test asynchronous search with HTTP error"""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock()))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = SearchRequest(area="銀座", keyword="寿司")
        response = await request.do()

        assert response.status == SearchStatus.ERROR
        assert response.error_message is not None and "404 Not Found" in response.error_message
        assert len(response.restaurants) == 0

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async_no_results(self, mock_client_class):
        """Test asynchronous search with no results"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.text = "<html><body><span class='c-page-count__num'>0</span></body></html>"
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            max_pages=1,
            include_meta=True,
        )

        response = await request.do()

        assert response.status == SearchStatus.NO_RESULTS
        assert len(response.restaurants) == 0
        assert response.meta is not None
        assert response.meta.total_count == 0
