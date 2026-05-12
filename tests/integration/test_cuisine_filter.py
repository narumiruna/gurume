from __future__ import annotations

import os

import pytest

from gurume.genre_mapping import get_genre_code
from gurume.restaurant import SortType
from gurume.search import SearchRequest

LIVE_INTEGRATION_ENV = "GURUME_RUN_INTEGRATION"
LIVE_INTEGRATION_ENABLED = os.getenv(LIVE_INTEGRATION_ENV) == "1"


def _genre_matches(genres: list[str], expected_terms: set[str]) -> bool:
    return any(term in genre for genre in genres for term in expected_terms)


@pytest.mark.integration
@pytest.mark.skipif(
    not LIVE_INTEGRATION_ENABLED,
    reason=f"Set {LIVE_INTEGRATION_ENV}=1 to run live Tabelog integration checks.",
)
@pytest.mark.parametrize(
    ("area", "cuisine", "expected_terms"),
    [
        ("東京", "ラーメン", {"ラーメン", "つけ麺"}),
        ("大阪", "焼肉", {"焼肉", "ホルモン"}),
        ("三重", "すき焼き", {"すき焼き"}),
    ],
)
def test_live_cuisine_filter_returns_matching_genres(
    area: str,
    cuisine: str,
    expected_terms: set[str],
) -> None:
    genre_code = get_genre_code(cuisine)
    assert genre_code is not None

    request = SearchRequest(
        area=area,
        genre_code=genre_code,
        sort_type=SortType.RANKING,
        max_pages=1,
        include_meta=False,
        timeout=30.0,
    )

    response = request.search_sync()
    top_restaurants = response.restaurants[:10]

    assert top_restaurants, f"Expected live results for {area=} {cuisine=}"

    matched_count = sum(_genre_matches(restaurant.genres, expected_terms) for restaurant in top_restaurants)
    match_ratio = matched_count / len(top_restaurants)

    assert match_ratio >= 0.8, (
        f"Expected >=80% cuisine match for {area=} {cuisine=}, got {matched_count}/{len(top_restaurants)}. "
        f"Genres: {[restaurant.genres for restaurant in top_restaurants]}"
    )
