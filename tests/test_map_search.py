"""Map XML parsing and transport tests; no live HTTP."""

from asyncio import CancelledError
from pathlib import Path
from typing import TypedDict
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions as request_errors

from gurume.exceptions import ParseError
from gurume.http_client import DEFAULT_IMPERSONATE
from gurume.map_search import MAP_SEARCH_URL
from gurume.map_search import MapSearchRequest


class MapBounds(TypedDict):
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


BOUNDS: MapBounds = {"min_lat": 34.36, "max_lat": 35.15, "min_lon": 135.85, "max_lon": 137.25}
XML = (Path(__file__).parent / "fixtures/map_yakitori.xml").read_text()


def test_params_use_map_categories_not_ranking_genre_code():
    params = MapSearchRequest(**BOUNDS, page=2)._build_params()
    assert params == {
        "minLat": "34.36",
        "maxLat": "35.15",
        "minLon": "135.85",
        "maxLon": "137.25",
        "cat0": "RC",
        "cat1": "RC01",
        "cat2": "RC0106",
        "cat3": "RC010601",
        "pg": "2",
        "lst": "20",
        "SrtT": "rt",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"min_lat": float("nan")},
        {"max_lon": float("inf")},
        {"min_lat": -91},
        {"max_lon": 181},
        {"min_lat": 36},
        {"min_lon": 138},
        {"max_lat": 34.36},
        {"page": 0},
        {"page": 1.5},
        {"page": True},
        {"cuisine": "寿司"},
    ],
)
def test_invalid_requests(overrides):
    with pytest.raises(ValueError):
        MapSearchRequest(**(BOUNDS | overrides))


def test_parse_keeps_geographic_scope_and_raw_budgets():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    assert result.total_count == 271
    assert result.upstream_count == 2
    assert result.skipped_count == 0
    assert result.has_next_page and not result.has_prev_page
    first = result.items[0]
    assert first.restaurant.name == "にかわ"
    assert first.restaurant.rating == 3.93
    assert first.restaurant.review_count == 149
    assert first.restaurant.genres == ["焼き鳥", "創作料理"]
    assert first.restaurant.url == "https://tabelog.com/mie/A2403/A240301/24019007/"
    assert first.latitude == pytest.approx(34.49462941849498)
    assert first.restaurant.station == "伊勢市、宮町、宇治山田"
    assert first.price_range1 is None
    assert first.price_range2 == "￥15,000～￥19,999"
    assert first.restaurant.lunch_price is None and first.restaurant.dinner_price is None
    assert result.items[1].prefecture_code == "23"  # Not silently prefecture-filtered.
    assert result.items[1].restaurant.review_count == 0
    assert result.items[1].restaurant.closed_days == "月曜日"


@pytest.mark.parametrize(
    "xml",
    [
        "not xml",
        "<html><title>Just a moment...</title></html>",
        "<markers/>",
        '<markers><srchinfo cnt="-1"/></markers>',
        '<markers><srchinfo cnt="unknown"/></markers>',
        "<markers><srchinfo/></markers>",
        '<!DOCTYPE markers><markers><srchinfo cnt="0"/></markers>',
        '<!DOCTYPE markers [<!ENTITY x "test">]><markers><srchinfo cnt="0"/></markers>',
        XML.replace('cnt="271"', 'cnt="1"'),
    ],
)
def test_bad_or_challenged_xml_is_not_no_results(xml):
    with pytest.raises(ParseError):
        MapSearchRequest(**BOUNDS)._parse(xml)


def test_empty_result_and_previous_page():
    result = MapSearchRequest(**BOUNDS, page=2)._parse('<markers><srchinfo cnt="0" prevpg="前の20件"/></markers>')
    assert result.items == [] and result.total_count == 0
    assert result.has_prev_page and not result.has_next_page


@pytest.mark.parametrize(
    "old,new",
    [
        ('lat="35.0"', 'lat="nan"'),
        ('score="3.20"', 'score="inf"'),
        ('score="3.20"', 'score="6"'),
        ('rvwcnt="0"', 'rvwcnt="-1"'),
        ('rstname="炭火焼鳥 かぐら"', 'rstname=""'),
        ('rsturl="/aichi/A2304/A230401/23073004/"', 'rsturl="https://evil.example/x"'),
        ('id="23073004"', 'id="999"'),
        ('lng="136.8"', 'lng="181"'),
    ],
)
def test_partial_bad_markers_are_skipped_with_warning(old, new):
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace(old, new))
    assert len(result.items) == 1
    assert result.total_count == 271 and result.skipped_count == 1
    assert "Skipped 1" in result.warnings[-1]


def test_all_invalid_markers_fail():
    with pytest.raises(ParseError, match="no valid"):
        MapSearchRequest(**BOUNDS)._parse(
            XML.replace('rstname="にかわ"', 'rstname=""').replace('lat="35.0"', 'lat="nan"')
        )


def test_duplicate_markers_are_skipped():
    result = MapSearchRequest(**BOUNDS)._parse(
        XML.replace('id="23073004"', 'id="24019007"').replace(
            "/aichi/A2304/A230401/23073004/",
            "/mie/A2403/A240301/24019007/",
        )
    )
    assert len(result.items) == 1 and result.skipped_count == 1


def test_sync_transport_checks_status_and_uses_shared_profile():
    response = Mock(text=XML)
    with patch("gurume.map_search.requests.get", return_value=response) as get:
        result = MapSearchRequest(**BOUNDS).search_sync()
    response.raise_for_status.assert_called_once()
    assert result.total_count == 271
    assert get.call_args.args == (MAP_SEARCH_URL,)
    assert get.call_args.kwargs["impersonate"] == DEFAULT_IMPERSONATE
    assert get.call_args.kwargs["timeout"] == 30.0
    assert get.call_args.kwargs["params"]["pg"] == "1"


def test_http_failure_is_not_parsed_or_retried():
    response = Mock(text=XML)
    error = request_errors.HTTPError("403", response=Mock(status_code=403))
    response.raise_for_status.side_effect = error
    with (
        patch("gurume.map_search.requests.get", return_value=response) as get,
        pytest.raises(request_errors.HTTPError),
    ):
        MapSearchRequest(**BOUNDS).search_sync()
    get.assert_called_once()


@pytest.mark.asyncio
async def test_async_transport_closes_session():
    response = Mock(text=XML)
    client = AsyncMock()
    client.get.return_value = response
    client.__aenter__.return_value = client
    with patch("gurume.map_search.requests.AsyncSession", return_value=client) as session:
        result = await MapSearchRequest(**BOUNDS, page=2).search()
    session.assert_called_once_with(timeout=30.0, impersonate=DEFAULT_IMPERSONATE)
    assert client.get.call_args.kwargs["params"]["pg"] == "2"
    response.raise_for_status.assert_called_once()
    client.__aexit__.assert_awaited_once()
    assert result.page == 2


@pytest.mark.asyncio
async def test_async_cancellation_propagates_and_closes_session():
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.get.side_effect = CancelledError()
    with patch("gurume.map_search.requests.AsyncSession", return_value=client), pytest.raises(CancelledError):
        await MapSearchRequest(**BOUNDS).search()
    client.__aexit__.assert_awaited_once()
