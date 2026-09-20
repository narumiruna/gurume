"""Contract tests for the shared restaurant output projection."""

import pytest
from pydantic import ValidationError

from gurume.cli import _build_json_data
from gurume.detail import RestaurantDetail
from gurume.restaurant import Restaurant
from gurume.server_helpers import _to_detail_output
from gurume.server_helpers import _to_restaurant_outputs


@pytest.mark.parametrize("url", ["https://EXAMPLE.com", "https://tabelog.com/寿司/?q=日本料理", "not-a-url"])
def test_legacy_json_preserves_raw_restaurant_values(url: str):
    restaurant = Restaurant(
        name="寿司店",
        url=url,
        rating=0.0,
        review_count=0,
        area="銀座",
        genres=["寿司", "日本料理"],
        lunch_price="￥1,000～￥1,999",
        dinner_price=None,
        phone="03-1111-2222",
    )
    assert _build_json_data([restaurant]) == [
        {
            "name": "寿司店",
            "rating": 0.0,
            "review_count": 0,
            "area": "銀座",
            "genres": ["寿司", "日本料理"],
            "url": url,
            "lunch_price": "￥1,000～￥1,999",
            "dinner_price": None,
        }
    ]


def test_search_and_detail_outputs_share_projection_and_url_normalization():
    restaurant = Restaurant(name="寿司店", url="https://EXAMPLE.com", genres=["寿司"])
    search_items = _to_restaurant_outputs([restaurant, restaurant], limit=1)
    detail = _to_detail_output(
        RestaurantDetail(restaurant=restaurant),
        fetch_reviews=False,
        fetch_menu=False,
        fetch_courses=False,
        max_review_pages=1,
    )
    expected = {
        "name": "寿司店",
        "rating": None,
        "review_count": None,
        "area": None,
        "genres": ["寿司"],
        "url": "https://example.com/",
        "lunch_price": None,
        "dinner_price": None,
    }
    assert len(search_items) == 1
    assert search_items[0].model_dump(mode="json") == expected
    assert detail.restaurant is not None
    assert detail.restaurant.model_dump(mode="json") == expected
    assert detail.restaurant_url == restaurant.url
    assert _to_restaurant_outputs([restaurant], limit=0) == []
    assert _to_restaurant_outputs([], limit=1) == []


def test_mcp_restaurant_outputs_reject_invalid_url():
    restaurant = Restaurant(name="寿司店", url="not-a-url")
    with pytest.raises(ValidationError):
        _to_restaurant_outputs([restaurant], limit=1)
    with pytest.raises(ValidationError):
        _to_detail_output(
            RestaurantDetail(restaurant=restaurant),
            fetch_reviews=False,
            fetch_menu=False,
            fetch_courses=False,
            max_review_pages=1,
        )
