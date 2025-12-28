"""Test configuration and fixtures"""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_html_response():
    """Mock HTML response for testing"""
    return """
    <html>
    <body>
        <div class="list-rst">
            <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000001/">
                テストレストラン1
            </a>
            <span class="c-rating__val">4.5</span>
            <em class="list-rst__rvw-count-num">123</em>
            <span class="list-rst__save-count-num">456</span>
            <div class="list-rst__area-genre"> [東京] 銀座 / 寿司</div>
            <div class="list-rst__catch">新鮮なネタが自慢の寿司店</div>
            <span class="list-rst__budget-val">ディナー ¥5,000～¥5,999</span>
            <span class="c-badge-tpoint">Vpoint</span>
            <div class="list-rst__booking-btn">予約</div>
            <img class="list-rst__photo-img" src="https://example.com/image1.jpg" />
        </div>
        <div class="list-rst">
            <a class="list-rst__rst-name-target" href="/tokyo/A1301/A130101/13000002/">
                テストレストラン2
            </a>
            <span class="c-rating__val">4.2</span>
            <em class="list-rst__rvw-count-num">789</em>
            <span class="list-rst__save-count-num">321</span>
            <div class="list-rst__area-genre"> [東京] 新宿 / 焼肉</div>
            <div class="list-rst__catch">A5ランクの和牛を使用</div>
            <span class="list-rst__budget-val">ランチ ¥2,000～¥2,999</span>
            <img class="list-rst__photo-img" src="https://example.com/image2.jpg" />
        </div>
        <span class="c-page-count__num">100</span>
    </body>
    </html>
    """


@pytest.fixture
def mock_httpx_response(mock_html_response):
    """Mock httpx response"""
    response = Mock()
    response.text = mock_html_response
    response.raise_for_status = Mock()
    response.json = Mock(return_value=[])
    return response


@pytest.fixture
def mock_httpx_client(mock_httpx_response):
    """Mock httpx client"""
    from unittest.mock import AsyncMock

    client = AsyncMock()
    client.get = AsyncMock(return_value=mock_httpx_response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client
