"""Integration tests for tabelog package"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from tabelogmcp import PriceRange
from tabelogmcp import RestaurantSearchRequest
from tabelogmcp import SearchRequest
from tabelogmcp import SortType
from tabelogmcp import query_restaurants


class TestIntegration:
    """Integration tests using real-like scenarios"""

    @patch("httpx.get")
    def test_basic_search_integration(self, mock_get):
        """Test basic search integration"""
        mock_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000001/">
                    銀座 久兵衛
                </a>
                <span class="c-rating__val">4.5</span>
                <em class="list-rst__rvw-count-num">1234</em>
                <span class="list-rst__area-genre">銀座、銀座駅 50m</span>
                <span class="list-rst__genre">寿司、日本料理</span>
                <span class="c-badge-tpoint">Vpoint</span>
                <div class="list-rst__booking-btn">予約</div>
            </div>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Test using quick search function
        restaurants = query_restaurants(
            area="銀座",
            keyword="寿司",
            sort_type=SortType.RANKING,
            party_size=2,
        )

        assert len(restaurants) == 1
        restaurant = restaurants[0]
        assert restaurant.name == "銀座 久兵衛"
        assert restaurant.rating == 4.5
        assert restaurant.review_count == 1234
        assert restaurant.area == "銀座"
        assert restaurant.station == "銀座駅"
        assert restaurant.distance == "50m"
        assert restaurant.genres == ["寿司", "日本料理"]
        assert restaurant.has_vpoint is True
        assert restaurant.has_reservation is True

        # Verify the request was made correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["url"] == "https://tabelog.com/rst/rstsearch"
        assert call_args[1]["params"]["sa"] == "銀座"
        assert call_args[1]["params"]["sk"] == "寿司"
        assert call_args[1]["params"]["svps"] == 2
        assert call_args[1]["params"]["SrtT"] == "rt"

    @patch("httpx.get")
    def test_advanced_search_integration(self, mock_get):
        """Test advanced search with filters integration"""
        mock_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1303/A130301/13000001/">
                    渋谷 焼肉 X
                </a>
                <span class="c-rating__val">4.2</span>
                <em class="list-rst__rvw-count-num">567</em>
                <span class="list-rst__area-genre">渋谷、渋谷駅 100m</span>
                <span class="list-rst__genre">焼肉、韓国料理</span>
                <span class="list-rst__budget-val">ディナー ¥4,000～¥4,999</span>
                <div class="list-rst__booking-btn">予約</div>
            </div>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Test using detailed search request
        request = RestaurantSearchRequest(
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

        restaurants = request.do_sync()

        assert len(restaurants) == 1
        restaurant = restaurants[0]
        assert restaurant.name == "渋谷 焼肉 X"
        assert restaurant.rating == 4.2
        assert restaurant.review_count == 567
        assert restaurant.area == "渋谷"
        assert restaurant.station == "渋谷駅"
        assert restaurant.distance == "100m"
        assert restaurant.genres == ["焼肉", "韓国料理"]
        assert restaurant.dinner_price == "ディナー ¥4,000～¥4,999"
        assert restaurant.has_reservation is True

        # Verify the request parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        params = call_args[1]["params"]
        assert params["sa"] == "渋谷"
        assert params["sk"] == "焼肉"
        assert params["svd"] == "20250715"
        assert params["svt"] == "1900"
        assert params["svps"] == 4
        assert params["SrtT"] == "rt"
        assert params["LstCos"] == "C005"
        assert params["ChkOnlineBooking"] == "1"
        assert params["ChkRoom"] == "1"

    @patch("httpx.get")
    def test_multi_page_search_integration(self, mock_get):
        """Test multi-page search integration"""
        # Mock responses for multiple pages
        page1_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1304/A130401/13000001/">
                    新宿 居酒屋 1
                </a>
                <span class="c-rating__val">3.8</span>
                <em class="list-rst__rvw-count-num">100</em>
            </div>
            <span class="c-page-count__num">50</span>
        </body>
        </html>
        """

        page2_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1304/A130401/13000002/">
                    新宿 居酒屋 2
                </a>
                <span class="c-rating__val">3.6</span>
                <em class="list-rst__rvw-count-num">200</em>
            </div>
        </body>
        </html>
        """

        # Mock responses for different pages
        responses = [
            Mock(text=page1_html, raise_for_status=Mock()),
            Mock(text=page2_html, raise_for_status=Mock()),
        ]
        mock_get.side_effect = responses

        # Test using SearchRequest for multi-page
        request = SearchRequest(
            area="新宿",
            keyword="居酒屋",
            max_pages=2,
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status.value == "success"
        assert len(response.restaurants) == 2
        assert response.meta is not None
        assert response.meta.total_count == 50
        assert response.meta.current_page == 1
        assert response.error_message is None

        # Check individual restaurants
        assert response.restaurants[0].name == "新宿 居酒屋 1"
        assert response.restaurants[0].rating == 3.8
        assert response.restaurants[0].review_count == 100

        assert response.restaurants[1].name == "新宿 居酒屋 2"
        assert response.restaurants[1].rating == 3.6
        assert response.restaurants[1].review_count == 200

        # Verify multiple requests were made
        assert mock_get.call_count == 2

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_async_search_integration(self, mock_client_class):
        """Test async search integration"""
        from unittest.mock import AsyncMock

        mock_html = """
        <html>
        <body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/kyoto/A2601/A260301/26000001/">
                    京都 料亭
                </a>
                <span class="c-rating__val">4.7</span>
                <em class="list-rst__rvw-count-num">89</em>
                <span class="list-rst__area-genre">祇園、祇園四条駅 200m</span>
                <span class="list-rst__genre">日本料理、懐石</span>
                <span class="list-rst__budget-val">ディナー ¥15,000～¥19,999</span>
            </div>
            <span class="c-page-count__num">10</span>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        # Test async search
        request = SearchRequest(
            area="京都",
            keyword="料亭",
            max_pages=1,
            include_meta=True,
        )

        response = await request.do()

        assert response.status.value == "success"
        assert len(response.restaurants) == 1
        assert response.meta is not None
        assert response.meta.total_count == 10

        restaurant = response.restaurants[0]
        assert restaurant.name == "京都 料亭"
        assert restaurant.rating == 4.7
        assert restaurant.review_count == 89
        assert restaurant.area == "祇園"
        assert restaurant.station == "祇園四条駅"
        assert restaurant.distance == "200m"
        assert restaurant.genres == ["日本料理", "懐石"]
        assert restaurant.dinner_price == "ディナー ¥15,000～¥19,999"

        # Verify async client was used correctly
        mock_client_class.assert_called_once_with(timeout=30.0, follow_redirects=True)
        mock_client.get.assert_called_once()

    @patch("httpx.get")
    def test_error_handling_integration(self, mock_get):
        """Test error handling integration"""
        # Test HTTP error
        mock_get.side_effect = Exception("Network error")

        request = SearchRequest(area="銀座", keyword="寿司")
        response = request.do_sync()

        assert response.status.value == "error"
        assert "Network error" in response.error_message
        assert len(response.restaurants) == 0
        assert response.meta is None

    @patch("httpx.get")
    def test_no_results_integration(self, mock_get):
        """Test no results integration"""
        mock_html = """
        <html>
        <body>
            <span class="c-page-count__num">0</span>
            <div class="rstlist-notfound">
                <p>該当するお店は見つかりませんでした。</p>
            </div>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="存在しない場所",
            keyword="存在しない料理",
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status.value == "no_results"
        assert len(response.restaurants) == 0
        assert response.meta is not None
        assert response.meta.total_count == 0
        assert response.error_message is None
