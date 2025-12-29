"""Test restaurant search functionality"""

from unittest.mock import Mock
from unittest.mock import patch

import httpx
import pytest

from tabelog.restaurant import PriceRange
from tabelog.restaurant import Restaurant
from tabelog.restaurant import RestaurantSearchRequest
from tabelog.restaurant import SortType
from tabelog.restaurant import query_restaurants


class TestRestaurantSearchRequest:
    """Test RestaurantSearchRequest functionality"""

    def test_parse_restaurants(self, mock_html_response):
        """Test parsing restaurants from HTML"""
        request = RestaurantSearchRequest()
        restaurants = request._parse_restaurants(mock_html_response)

        assert len(restaurants) == 2

        # Test first restaurant
        restaurant1 = restaurants[0]
        assert restaurant1.name == "テストレストラン1"
        assert restaurant1.url == "https://tabelog.com/tokyo/A1301/A130101/13000001/"
        assert restaurant1.rating == 4.5
        assert restaurant1.review_count == 123
        assert restaurant1.save_count == 456
        assert restaurant1.area == "銀座"
        assert restaurant1.station is None
        assert restaurant1.distance is None
        assert restaurant1.genres == ["寿司"]
        assert restaurant1.description == "新鮮なネタが自慢の寿司店"
        assert restaurant1.dinner_price == "ディナー ¥5,000～¥5,999"
        assert restaurant1.has_vpoint is True
        assert restaurant1.has_reservation is True
        assert restaurant1.image_urls == ["https://example.com/image1.jpg"]

        # Test second restaurant
        restaurant2 = restaurants[1]
        assert restaurant2.name == "テストレストラン2"
        assert restaurant2.url == "https://tabelog.com/tokyo/A1301/A130101/13000002/"
        assert restaurant2.rating == 4.2
        assert restaurant2.review_count == 789
        assert restaurant2.save_count == 321
        assert restaurant2.area == "新宿"
        assert restaurant2.station is None
        assert restaurant2.distance is None
        assert restaurant2.genres == ["焼肉"]
        assert restaurant2.description == "A5ランクの和牛を使用"
        assert restaurant2.lunch_price == "ランチ ¥2,000～¥2,999"
        assert restaurant2.has_vpoint is False
        assert restaurant2.has_reservation is False
        assert restaurant2.image_urls == ["https://example.com/image2.jpg"]

    def test_parse_restaurants_empty(self):
        """Test parsing empty HTML"""
        request = RestaurantSearchRequest()
        empty_html = "<html><body></body></html>"
        restaurants = request._parse_restaurants(empty_html)

        assert len(restaurants) == 0

    def test_parse_restaurants_malformed(self):
        """Test parsing malformed HTML"""
        request = RestaurantSearchRequest()
        malformed_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/test/">テスト</a>
                <span class="c-rating__val">invalid</span>
                <em class="list-rst__rvw-count-num">invalid</em>
            </div>
        </body>
        </html>
        """
        restaurants = request._parse_restaurants(malformed_html)

        assert len(restaurants) == 1
        assert restaurants[0].name == "テスト"
        assert restaurants[0].rating is None
        assert restaurants[0].review_count is None

    @patch("httpx.get")
    def test_do_sync(self, mock_get, mock_html_response):
        """Test synchronous search"""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = RestaurantSearchRequest(
            area="銀座",
            keyword="寿司",
            party_size=2,
        )

        restaurants = request.search_sync(use_cache=False, use_retry=False)

        assert len(restaurants) == 2
        assert restaurants[0].name == "テストレストラン1"

        # Check that httpx.get was called with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["url"] == "https://tabelog.com/rst/rstsearch"
        assert call_args[1]["params"]["sa"] == "銀座"
        assert call_args[1]["params"]["sk"] == "寿司"
        assert int(call_args[1]["params"]["svps"]) == 2
        assert call_args[1]["follow_redirects"] is True

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async(self, mock_client_class, mock_html_response):
        """Test asynchronous search"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = RestaurantSearchRequest(
            area="銀座",
            keyword="寿司",
            party_size=2,
        )

        restaurants = await request.search(use_cache=False, use_retry=False)

        assert len(restaurants) == 2
        assert restaurants[0].name == "テストレストラン1"

        # Check that AsyncClient was created with correct parameters
        mock_client_class.assert_called_once_with(timeout=30.0, follow_redirects=True)
        mock_client.get.assert_called_once()

    @patch("httpx.get")
    def test_do_sync_http_error(self, mock_get):
        """Test handling HTTP errors in synchronous search"""
        mock_get.side_effect = httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock())

        request = RestaurantSearchRequest(area="銀座")

        with pytest.raises(httpx.HTTPStatusError):
            request.search_sync(use_cache=False, use_retry=False)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_do_async_http_error(self, mock_client_class):
        """Test handling HTTP errors in asynchronous search"""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock()))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = RestaurantSearchRequest(area="銀座")

        with pytest.raises(httpx.HTTPStatusError):
            await request.search(use_cache=False, use_retry=False)


class TestQueryRestaurants:
    """Test query_restaurants function"""

    @patch("tabelog.restaurant.RestaurantSearchRequest.search_sync")
    def test_query_restaurants_basic(self, mock_search_sync):
        """Test basic query_restaurants function"""
        mock_restaurants = [
            Restaurant(name="テスト1", url="https://test1.com"),
            Restaurant(name="テスト2", url="https://test2.com"),
        ]
        mock_search_sync.return_value = mock_restaurants

        restaurants = query_restaurants(
            area="銀座",
            keyword="寿司",
            party_size=2,
            sort_type=SortType.RANKING,
        )

        assert len(restaurants) == 2
        assert restaurants[0].name == "テスト1"
        assert restaurants[1].name == "テスト2"

        # Check that do_sync was called
        mock_search_sync.assert_called_once()

    @patch("tabelog.restaurant.RestaurantSearchRequest.search_sync")
    def test_query_restaurants_with_filters(self, mock_search_sync):
        """Test query_restaurants with filters"""
        mock_restaurants = [Restaurant(name="テスト", url="https://test.com")]
        mock_search_sync.return_value = mock_restaurants

        restaurants = query_restaurants(
            area="渋谷",
            keyword="焼肉",
            reservation_date="20250715",
            reservation_time="1900",
            party_size=4,
            sort_type=SortType.RANKING,
            price_range=PriceRange.DINNER_4000_5000,
            online_booking_only=True,
            has_private_room=True,
        )

        assert len(restaurants) == 1
        mock_search_sync.assert_called_once()

    @patch("tabelog.restaurant.RestaurantSearchRequest.search_sync")
    def test_query_restaurants_caching(self, mock_search_sync):
        """Test that query_restaurants uses caching"""
        mock_restaurants = [Restaurant(name="テスト", url="https://test.com")]
        mock_search_sync.return_value = mock_restaurants

        # Clear cache first
        query_restaurants.cache_clear()

        # First call
        restaurants1 = query_restaurants(area="銀座", keyword="寿司")

        # Second call with same parameters should use cache
        restaurants2 = query_restaurants(area="銀座", keyword="寿司")

        assert len(restaurants1) == 1
        assert len(restaurants2) == 1
        assert restaurants1[0].name == restaurants2[0].name

        # do_sync should only be called once due to caching
        mock_search_sync.assert_called_once()

    @patch("tabelog.restaurant.RestaurantSearchRequest.search_sync")
    def test_query_restaurants_no_cache_different_params(self, mock_search_sync):
        """Test that different parameters don't use cache"""
        mock_restaurants = [Restaurant(name="テスト", url="https://test.com")]
        mock_search_sync.return_value = mock_restaurants

        # Clear cache first
        query_restaurants.cache_clear()

        # First call
        query_restaurants(area="銀座", keyword="寿司")

        # Second call with different parameters should not use cache
        query_restaurants(area="渋谷", keyword="焼肉")

        # do_sync should be called twice
        assert mock_search_sync.call_count == 2
