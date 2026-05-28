"""Test restaurant search functionality"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions as request_errors

from gurume.restaurant import PriceRange
from gurume.restaurant import Restaurant
from gurume.restaurant import RestaurantSearchRequest
from gurume.restaurant import SortType
from gurume.restaurant import query_restaurants


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

    def test_parse_sukiyaki_ranking_cards(self):
        """Parse current Tabelog ranking card markup for sukiyaki pages."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="https://tabelog.com/tokyo/A1301/A130101/13287203/">
                    東京肉しゃぶ家 秀彬
                </a>
                <div class="list-rst__area-genre">
                    [東京] 銀座駅 481m / しゃぶしゃぶ、<mark>すき焼き</mark>、とんかつ
                </div>
                <span class="c-rating__val c-rating__val--strong list-rst__rating-val">4.16</span>
                <em class="list-rst__rvw-count-num cpy-review-count">148</em>
                <ul class="list-rst__info">
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--dinner">
                            <i class="c-rating-v3__time">夜</i>
                            <span class="c-rating-v3__val">￥15,000～￥19,999</span>
                        </p>
                    </li>
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--lunch">
                            <i class="c-rating-v3__time">昼</i>
                            <span class="c-rating-v3__val">￥5,000～￥5,999</span>
                        </p>
                    </li>
                </ul>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="https://tabelog.com/mie/A2401/A240102/24000069/">
                    和田金
                </a>
                <div class="list-rst__area-genre">
                    [三重] 松阪市 / <mark>すき焼き</mark>
                </div>
                <span class="c-rating__val c-rating__val--strong list-rst__rating-val">4.13</span>
                <em class="list-rst__rvw-count-num cpy-review-count">1318</em>
                <ul class="list-rst__info">
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--val">
                            <i class="c-rating-v3__time c-rating-v3__time--dinner">夜</i>
                            <span class="c-rating-v3__val">￥20,000～￥29,999</span>
                        </p>
                    </li>
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--val">
                            <i class="c-rating-v3__time c-rating-v3__time--lunch">昼</i>
                            <span class="c-rating-v3__val">￥20,000～￥29,999</span>
                        </p>
                    </li>
                </ul>
            </div>
        </body></html>
        """

        request = RestaurantSearchRequest()
        restaurants = request._parse_restaurants(html)

        assert [restaurant.name for restaurant in restaurants] == ["東京肉しゃぶ家 秀彬", "和田金"]
        assert restaurants[0].url == "https://tabelog.com/tokyo/A1301/A130101/13287203/"
        assert restaurants[0].rating == 4.16
        assert restaurants[0].review_count == 148
        assert restaurants[0].dinner_price == "￥15,000～￥19,999"
        assert restaurants[0].lunch_price == "￥5,000～￥5,999"
        assert any("すき焼き" in genre for genre in restaurants[0].genres)
        assert restaurants[1].url == "https://tabelog.com/mie/A2401/A240102/24000069/"
        assert restaurants[1].rating == 4.13
        assert restaurants[1].review_count == 1318
        assert restaurants[1].dinner_price == "￥20,000～￥29,999"
        assert restaurants[1].lunch_price == "￥20,000～￥29,999"
        assert any("すき焼き" in genre for genre in restaurants[1].genres)

    def test_parse_current_price_under_range_marker(self):
        """Preserve leading markers for under-range list-card prices."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="https://tabelog.com/tokyo/A1301/A130101/13000001/">
                    低価格ランチ
                </a>
                <ul class="list-rst__info">
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--lunch">
                            <i class="c-rating-v3__time">昼</i>
                            <span class="c-rating-v3__val">～￥999</span>
                        </p>
                    </li>
                    <li class="list-rst__info-item">
                        <p class="c-rating-v3 c-rating-v3--dinner">
                            <i class="c-rating-v3__time">夜</i>
                            <span class="c-rating-v3__val">￥1,000～￥1,999</span>
                        </p>
                    </li>
                </ul>
            </div>
        </body></html>
        """

        restaurants = RestaurantSearchRequest()._parse_restaurants(html)

        assert len(restaurants) == 1
        assert restaurants[0].lunch_price == "～￥999"
        assert restaurants[0].dinner_price == "￥1,000～￥1,999"

    @patch("curl_cffi.requests.get")
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

        # Check that curl_cffi.get was called with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["url"] == "https://tabelog.com/rst/rstsearch"
        assert call_args[1]["params"]["sa"] == "銀座"
        assert call_args[1]["params"]["sk"] == "寿司"
        assert int(call_args[1]["params"]["svps"]) == 2
        assert call_args[1]["allow_redirects"] is True
        assert call_args[1]["impersonate"] == "chrome"

    @pytest.mark.asyncio
    @patch("curl_cffi.requests.AsyncSession")
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

        # Check that AsyncSession was created with correct parameters
        mock_client_class.assert_called_once_with(timeout=30.0, allow_redirects=True, impersonate="chrome")
        mock_client.get.assert_called_once()

    @patch("curl_cffi.requests.get")
    def test_do_sync_http_error(self, mock_get):
        """Test handling HTTP errors in synchronous search"""
        mock_get.side_effect = request_errors.HTTPError("404 Not Found", 0, Mock(status_code=404))

        request = RestaurantSearchRequest(area="銀座")

        with pytest.raises(request_errors.HTTPError):
            request.search_sync(use_cache=False, use_retry=False)

    @pytest.mark.asyncio
    @patch("curl_cffi.requests.AsyncSession")
    async def test_do_async_http_error(self, mock_client_class):
        """Test handling HTTP errors in asynchronous search"""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=request_errors.HTTPError("404 Not Found", 0, Mock(status_code=404)))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = RestaurantSearchRequest(area="銀座")

        with pytest.raises(request_errors.HTTPError):
            await request.search(use_cache=False, use_retry=False)


class TestQueryRestaurants:
    """Test query_restaurants function"""

    @patch("gurume.restaurant.RestaurantSearchRequest.search_sync")
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

    @patch("gurume.restaurant.RestaurantSearchRequest.search_sync")
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

    @patch("gurume.restaurant.RestaurantSearchRequest.search_sync")
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

    @patch("gurume.restaurant.RestaurantSearchRequest.search_sync")
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


# ============================================================================
# Test magazine / promo filtering in _parse_basic_info
# ============================================================================


class TestMagazineFiltering:
    """Test that magazine articles and non-restaurant links are excluded."""

    def test_skips_magazine_tabelog_links(self):
        """Items linking to magazine.tabelog.com must be dropped."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target"
                   href="https://magazine.tabelog.com/articles/12345">
                   おすすめ特集
                </a>
            </div>
        </body></html>
        """
        request = RestaurantSearchRequest()
        restaurants = request._parse_restaurants(html)
        assert restaurants == []

    def test_skips_non_restaurant_fallback_links(self):
        """Fallback to first <a> must NOT pick up /About or other non-restaurant paths."""
        html = """
        <html><body>
            <div class="list-rst">
                <a href="/About/help/">About Tabelog</a>
            </div>
        </body></html>
        """
        request = RestaurantSearchRequest()
        restaurants = request._parse_restaurants(html)
        assert restaurants == []

    def test_accepts_real_restaurant_fallback_link(self):
        """Fallback to first <a> must accept real restaurant URL paths."""
        html = """
        <html><body>
            <div class="list-rst">
                <a href="/tokyo/A1301/A130101/13000999/">本物のレストラン</a>
            </div>
        </body></html>
        """
        request = RestaurantSearchRequest()
        restaurants = request._parse_restaurants(html)
        assert len(restaurants) == 1
        assert restaurants[0].name == "本物のレストラン"
        assert restaurants[0].url == "https://tabelog.com/tokyo/A1301/A130101/13000999/"
