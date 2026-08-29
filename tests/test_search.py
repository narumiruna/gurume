"""Test search functionality"""

from datetime import datetime
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions as request_errors

from gurume.restaurant import Restaurant
from gurume.restaurant import SortType
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
        assert meta.source_url is None
        assert meta.source_params == {}
        assert meta.cuisine_filter_confidence is None
        assert meta.area_filter_applied is None
        assert meta.area_filter_confidence is None
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
        assert response.warnings == []

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
            page=2,
            max_pages=3,
            include_meta=True,
            timeout=30.0,
        )

        assert request.area == "銀座"
        assert request.keyword == "寿司"
        assert request.page == 2
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

    def test_parse_meta_uses_total_count_from_count_block(self):
        """Test current Tabelog count blocks use the final number as total count."""
        request = SearchRequest()
        html = """
        <html>
        <body>
            <div class="c-page-count">
                <span class="c-page-count__num"><strong>1</strong></span>～
                <span class="c-page-count__num"><strong>20</strong></span> 件を表示
                <span class="c-page-count__line">／</span>
                全 <span class="c-page-count__num"><strong>138,635</strong></span> 件
            </div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="c-pagination">
                <a href="/tokyo/rstLst/2/" rel="next" class="c-pagination__arrow c-pagination__arrow--next">
                    次の20件
                </a>
            </div>
        </body>
        </html>
        """

        meta = request._parse_meta(html, current_page=1)

        assert meta.total_count == 138635
        assert meta.results_per_page == 5
        assert meta.total_pages == 27727
        assert meta.has_next_page is True

    def test_parse_meta_ignores_impossible_count_lower_than_results(self):
        """Test metadata does not report totals lower than parsed restaurant count."""
        request = SearchRequest()
        html = """
        <html>
        <body>
            <span class="c-page-count__num">1</span>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
        </body>
        </html>
        """

        meta = request._parse_meta(html, current_page=1)

        assert meta.total_count is None
        assert meta.total_pages == 1
        assert meta.has_next_page is False

    def test_parse_meta_uses_next_link_when_total_count_is_missing(self):
        """Test pagination remains useful when Tabelog omits a total count."""
        request = SearchRequest()
        html = """
        <html>
        <body>
            <div class="list-rst"></div>
            <div class="list-rst"></div>
            <div class="c-pagination">
                <strong class="c-pagination__num is-current">1</strong>
                <a href="/tokyo/rstLst/2/" class="c-pagination__num">2</a>
                <a href="/tokyo/rstLst/2/" rel="next" class="c-pagination__arrow c-pagination__arrow--next">
                    次の20件
                </a>
            </div>
        </body>
        </html>
        """

        meta = request._parse_meta(html, current_page=1)

        assert meta.total_count is None
        assert meta.total_pages == 2
        assert meta.has_next_page is True

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

    @patch("curl_cffi.requests.get")
    def test_do_sync_respects_start_page(self, mock_get, mock_html_response):
        """Test synchronous search starts from the requested page"""
        mock_response = Mock()
        mock_response.text = mock_html_response
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(
            area="銀座",
            keyword="寿司",
            page=2,
            max_pages=1,
            include_meta=True,
        )

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert response.meta is not None
        assert response.meta.current_page == 2
        assert response.meta.has_prev_page is True

        called_params = mock_get.call_args.kwargs["params"]
        assert called_params["PG"] == "2"

    @patch("curl_cffi.requests.get")
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
        assert response.meta.source_url == "https://tabelog.com/rst/rstsearch"
        assert response.meta.source_params["sa"] == "銀座"
        assert response.meta.source_params["sk"] == "寿司"
        assert response.meta.source_params["sw"] == "寿司"
        assert response.error_message is None

        # Check that curl_cffi.get was called once with profile-consistent generated headers.
        mock_get.assert_called_once()
        assert mock_get.call_args.kwargs["impersonate"] == "safari"
        assert "headers" not in mock_get.call_args.kwargs

    @patch("curl_cffi.requests.get")
    def test_cuisine_filter_mismatch_adds_machine_readable_warning(self, mock_get):
        """Supported cuisine searches must expose low-confidence mismatches."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000001/">鮨</a>
                <span class="c-rating__val">4.5</span>
                <em class="list-rst__rvw-count-num">123</em>
                <div class="list-rst__area-genre"> [東京] 銀座 / 寿司</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000002/">天ぷら</a>
                <span class="c-rating__val">4.2</span>
                <em class="list-rst__rvw-count-num">456</em>
                <div class="list-rst__area-genre"> [東京] 銀座 / 天ぷら</div>
            </div>
            <span class="c-page-count__num">2</span>
        </body></html>
        """
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(genre_code="RC0107", sort_type=SortType.RANKING, max_pages=1, include_meta=True)

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert response.meta is not None
        assert response.meta.source_url == "https://tabelog.com/rstLst/RC0107/"
        assert response.meta.source_params["SrtT"] == "rt"
        assert response.meta.cuisine_filter_confidence == "low"
        assert response.meta.cuisine_filter_reason == "0/2 parsed results included すき焼き"
        assert response.warnings == [
            "filter_mismatch:cuisine: only 0/2 parsed results included すき焼き; "
            "verify `meta.source_url` before presenting results as cuisine-scoped."
        ]

    @patch("curl_cffi.requests.get")
    def test_area_keyword_mismatch_adds_machine_readable_warning(self, mock_get):
        """Mapped area keyword searches must expose URL evidence when Tabelog returns other prefectures."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/hiroshima/A3401/A340101/34000001/">広島焼き店</a>
                <span class="c-rating__val">4.0</span>
                <em class="list-rst__rvw-count-num">123</em>
                <div class="list-rst__area-genre"> [広島] 八丁堀 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000002/">東京お好み焼き店</a>
                <span class="c-rating__val">3.9</span>
                <em class="list-rst__rvw-count-num">88</em>
                <div class="list-rst__area-genre"> [東京] 銀座 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270101/27000003/">大阪お好み焼き店</a>
                <span class="c-rating__val">3.8</span>
                <em class="list-rst__rvw-count-num">77</em>
                <div class="list-rst__area-genre"> [大阪] 梅田 / お好み焼き</div>
            </div>
            <span class="c-page-count__num">3</span>
        </body></html>
        """
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(area="大阪", keyword="お好み焼き", sort_type=SortType.RANKING, max_pages=1)

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert response.meta is not None
        assert response.meta.source_url == "https://tabelog.com/rst/rstsearch"
        assert response.meta.source_params["sa"] == "大阪"
        assert response.meta.source_params["sk"] == "お好み焼き"
        assert response.meta.area_filter_applied is False
        assert response.meta.area_filter_confidence == "low"
        assert response.meta.area_filter_reason == "1/3 parsed result URLs matched osaka"
        assert response.warnings == [
            "filter_mismatch:area: only 1/3 parsed result URLs matched osaka; "
            "verify `meta.source_url` before presenting results as area-scoped."
        ]

    @patch("curl_cffi.requests.get")
    def test_area_keyword_matching_urls_sets_high_confidence(self, mock_get):
        """Mapped area keyword searches can be high confidence when result URLs all match the area path."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270101/27000001/">大阪お好み焼き店</a>
                <span class="c-rating__val">4.0</span>
                <em class="list-rst__rvw-count-num">123</em>
                <div class="list-rst__area-genre"> [大阪] 梅田 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270102/27000002/">大阪焼き店</a>
                <span class="c-rating__val">3.9</span>
                <em class="list-rst__rvw-count-num">88</em>
                <div class="list-rst__area-genre"> [大阪] 難波 / お好み焼き</div>
            </div>
            <span class="c-page-count__num">2</span>
        </body></html>
        """
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(area="大阪", keyword="お好み焼き", sort_type=SortType.RANKING, max_pages=1)

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert response.meta is not None
        assert response.meta.area_filter_applied is True
        assert response.meta.area_filter_confidence == "high"
        assert response.meta.area_filter_reason == "2/2 parsed result URLs matched osaka"
        assert response.warnings == []

    @patch("curl_cffi.requests.get")
    def test_area_keyword_single_mismatched_url_keeps_low_confidence(self, mock_get):
        """Any out-of-area parsed URL keeps area confidence low."""
        html = """
        <html><body>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270101/27000001/">大阪お好み焼き1</a>
                <span class="c-rating__val">4.0</span>
                <em class="list-rst__rvw-count-num">123</em>
                <div class="list-rst__area-genre"> [大阪] 梅田 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270102/27000002/">大阪お好み焼き2</a>
                <span class="c-rating__val">3.9</span>
                <em class="list-rst__rvw-count-num">88</em>
                <div class="list-rst__area-genre"> [大阪] 難波 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270103/27000003/">大阪お好み焼き3</a>
                <span class="c-rating__val">3.8</span>
                <em class="list-rst__rvw-count-num">77</em>
                <div class="list-rst__area-genre"> [大阪] 心斎橋 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/osaka/A2701/A270104/27000004/">大阪お好み焼き4</a>
                <span class="c-rating__val">3.7</span>
                <em class="list-rst__rvw-count-num">66</em>
                <div class="list-rst__area-genre"> [大阪] 天王寺 / お好み焼き</div>
            </div>
            <div class="list-rst">
                <a class="list-rst__rst-name-target" href="/hiroshima/A3401/A340101/34000005/">広島お好み焼き</a>
                <span class="c-rating__val">3.6</span>
                <em class="list-rst__rvw-count-num">55</em>
                <div class="list-rst__area-genre"> [広島] 八丁堀 / お好み焼き</div>
            </div>
            <span class="c-page-count__num">5</span>
        </body></html>
        """
        mock_response = Mock()
        mock_response.text = html
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = SearchRequest(area="大阪", keyword="お好み焼き", sort_type=SortType.RANKING, max_pages=1)

        response = request.do_sync()

        assert response.status == SearchStatus.SUCCESS
        assert response.meta is not None
        assert response.meta.area_filter_applied is False
        assert response.meta.area_filter_confidence == "low"
        assert response.meta.area_filter_reason == "4/5 parsed result URLs matched osaka"
        assert response.warnings == [
            "filter_mismatch:area: only 4/5 parsed result URLs matched osaka; "
            "verify `meta.source_url` before presenting results as area-scoped."
        ]

    @patch("curl_cffi.requests.get")
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

        # Check that curl_cffi.get was called 3 times
        assert mock_get.call_count == 3

    @patch("curl_cffi.requests.get")
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

    @patch("curl_cffi.requests.get")
    def test_do_sync_http_error(self, mock_get):
        """Test synchronous search with HTTP error"""
        mock_get.side_effect = request_errors.HTTPError("404 Not Found", 0, Mock(status_code=404))

        request = SearchRequest(area="銀座", keyword="寿司")
        response = request.do_sync()

        assert response.status == SearchStatus.ERROR
        assert response.error_message is not None and "404 Not Found" in response.error_message
        assert len(response.restaurants) == 0

    @patch("curl_cffi.requests.get")
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
    @patch("curl_cffi.requests.AsyncSession")
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

        # Check that AsyncSession was created with correct parameters
        mock_client_class.assert_called_once_with(timeout=30.0, allow_redirects=True, impersonate="safari")
        mock_client.get.assert_called_once()
        assert "headers" not in mock_client.get.call_args.kwargs

    @pytest.mark.asyncio
    @patch("curl_cffi.requests.AsyncSession")
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
    @patch("curl_cffi.requests.AsyncSession")
    async def test_do_async_http_error(self, mock_client_class):
        """Test asynchronous search with HTTP error"""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=request_errors.HTTPError("404 Not Found", 0, Mock(status_code=404)))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_class.return_value = mock_client

        request = SearchRequest(area="銀座", keyword="寿司")
        response = await request.do()

        assert response.status == SearchStatus.ERROR
        assert response.error_message is not None and "404 Not Found" in response.error_message
        assert len(response.restaurants) == 0

    @pytest.mark.asyncio
    @patch("curl_cffi.requests.AsyncSession")
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


# ============================================================================
# Test build_search_url_and_params (URL helper)
# ============================================================================


class TestBuildSearchUrlAndParams:
    """Test the shared URL/params builder used by both restaurant.py and search.py."""

    def test_no_area_no_genre(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "standard"}, None, None)
        assert url == "https://tabelog.com/rst/rstsearch"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_only(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "standard", "sa": "東京"}, "tokyo", None)
        assert url == "https://tabelog.com/tokyo/rstLst/"
        assert "sa" not in params, "area param must move into URL path"
        assert "LstG" not in params

    def test_area_and_keyword_preserves_search_endpoint(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "東京都", "sk": "今半"}, "tokyo", None)
        assert url == "https://tabelog.com/rst/rstsearch"
        assert params["sa"] == "東京都"
        assert params["sk"] == "今半"
        assert params["sw"] == "今半"
        assert "LstG" not in params

    def test_area_keyword_and_area_cuisine_url_policy_is_documented(self):
        """Keyword searches keep rstsearch params while cuisine searches move filters into paths."""
        from gurume.restaurant import build_search_url_and_params

        keyword_url, keyword_params = build_search_url_and_params(
            {"SrtT": "rt", "sa": "大阪", "sk": "お好み焼き"},
            "osaka",
            None,
        )
        cuisine_url, cuisine_params = build_search_url_and_params(
            {"SrtT": "rt", "sa": "大阪"},
            "osaka",
            "RC0107",
        )

        assert keyword_url == "https://tabelog.com/rst/rstsearch"
        assert keyword_params["sa"] == "大阪"
        assert keyword_params["sk"] == "お好み焼き"
        assert keyword_params["sw"] == "お好み焼き"
        assert cuisine_url == "https://tabelog.com/osaka/rstLst/RC0107/"
        assert "sa" not in cuisine_params

    def test_genre_only_uses_cuisine_path_segment(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "standard"}, None, "RC0201")
        assert url == "https://tabelog.com/rstLst/sushi/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_national_area_and_genre_uses_cuisine_path_segment(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "全国"}, None, "RC0107")
        assert url == "https://tabelog.com/rstLst/RC0107/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_and_genre_uses_cuisine_path_segment(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "standard", "sa": "銀座"}, "tokyo", "RC0201")
        assert url == "https://tabelog.com/tokyo/rstLst/sushi/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_and_genre_uses_expected_ramen_path(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "東京"}, "tokyo", "RC0501")
        assert url == "https://tabelog.com/tokyo/rstLst/MC0101/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_and_genre_uses_expected_yakiniku_path(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "大阪"}, "osaka", "RC1501")
        assert url == "https://tabelog.com/osaka/rstLst/yakiniku/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_and_genre_supports_nested_city_path(self):
        from gurume.restaurant import build_search_url_and_params

        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "名古屋"}, "aichi/A2301", "RC0701")
        assert url == "https://tabelog.com/aichi/A2301/rstLst/unagi/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_area_and_genre_supports_catalog_area_path(self):
        from gurume.area_mapping import get_area_slug
        from gurume.restaurant import build_search_url_and_params

        area_slug = get_area_slug("心斎橋")
        url, params = build_search_url_and_params({"SrtT": "rt", "sa": "心斎橋"}, area_slug, "RC1501")

        assert url == "https://tabelog.com/osaka/A2701/A270201/rstLst/yakiniku/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_search_request_build_url_uses_city_cuisine_path(self):
        from gurume.restaurant import SortType
        from gurume.search import SearchRequest

        request = SearchRequest(area="札幌", genre_code="RC1801", sort_type=SortType.RANKING)
        rst_req = request._create_restaurant_request(page=1)
        url, params = request._build_url_and_params(rst_req)

        assert url == "https://tabelog.com/hokkaido/A0101/rstLst/curry/"
        assert "LstG" not in params
        assert "sa" not in params

    def test_search_request_build_url_preserves_keyword_filters(self):
        """SearchRequest._build_url_and_params must not use mapped paths for keyword searches."""
        from gurume.restaurant import SortType
        from gurume.search import SearchRequest

        request = SearchRequest(
            area="東京",
            keyword="寿司",
            genre_code="RC0201",
            sort_type=SortType.STANDARD,
        )
        rst_req = request._create_restaurant_request(page=1)
        url, params = request._build_url_and_params(rst_req)

        assert url == "https://tabelog.com/rst/rstsearch"
        assert params["sa"] == "東京"
        assert params["sk"] == "寿司"
        assert params["sw"] == "寿司"
        assert params["LstG"] == "RC0201"
