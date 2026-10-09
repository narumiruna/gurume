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


@pytest.mark.parametrize("field", list(BOUNDS))
@pytest.mark.parametrize("value", [False, True])
def test_boolean_bounds_are_rejected_before_http(field, value):
    bounds: MapBounds = {"min_lat": -2.0, "max_lat": 2.0, "min_lon": -2.0, "max_lon": 2.0}
    with (
        patch("gurume.map_search.requests.get") as get,
        pytest.raises(ValueError, match=f"{field}.*not a Boolean"),
    ):
        MapSearchRequest(**(bounds | {field: value})).search_sync()
    get.assert_not_called()


@pytest.mark.parametrize("cuisine", [None, 26, True, [], {}])
def test_nonstring_cuisine_rejected_before_http(cuisine):
    with patch("gurume.map_search.requests.get") as get, pytest.raises(TypeError, match="cuisine must be a string"):
        MapSearchRequest(**BOUNDS, cuisine=cuisine).search_sync()
    get.assert_not_called()


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
        '<markers><srchinfo cnt="271"/></markers>',
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


@pytest.mark.parametrize(
    "old,new",
    [
        ('lat="35.0"', 'lat="34.35"'),
        ('lat="35.0"', 'lat="35.16"'),
        ('lat="35.0"', 'lat="80.0"'),
        ('lng="136.8"', 'lng="135.84"'),
        ('lng="136.8"', 'lng="137.26"'),
    ],
)
def test_outside_rectangle_markers_are_skipped(old, new):
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace(old, new))
    assert len(result.items) == 1 and result.items[0].restaurant_id == "24019007"
    assert result.skipped_count == 1 and result.upstream_count == 2 and result.total_count == 271
    assert "out-of-bounds" in result.warnings[-1]


@pytest.mark.parametrize(
    "old,bound,attribute",
    [
        ('lat="35.0"', "min_lat", "lat"),
        ('lat="35.0"', "max_lat", "lat"),
        ('lng="136.8"', "min_lon", "lng"),
        ('lng="136.8"', "max_lon", "lng"),
    ],
)
def test_rectangle_boundaries_are_inclusive(old, bound, attribute):
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace(old, f'{attribute}="{BOUNDS[bound]}"'))
    assert len(result.items) == 2 and result.skipped_count == 0


@pytest.mark.parametrize("page,total", [(1, 0), (2, 0), (2, 2), (2, 20), (14, 260), (15, 271)])
def test_empty_pages_at_or_beyond_total_are_allowed(page, total):
    prevpg = "prev" if page > 1 else ""
    result = MapSearchRequest(**BOUNDS, page=page)._parse(
        f'<markers><srchinfo cnt="{total}" prevpg="{prevpg}"/></markers>'
    )
    assert result.items == [] and result.total_count == total
    assert result.has_prev_page is (page > 1) and not result.has_next_page


@pytest.mark.parametrize("page,total", [(2, 271), (2, 21), (3, 41), (14, 271)])
@pytest.mark.parametrize("nextpg", ["", "next"])
def test_empty_pages_with_remaining_results_fail(page, total, nextpg):
    with pytest.raises(ParseError, match="inconsistent result counts"):
        MapSearchRequest(**BOUNDS, page=page)._parse(
            f'<markers><srchinfo cnt="{total}" nextpg="{nextpg}"/></markers>'
        )


@pytest.mark.parametrize("page,total", [(2, 0), (2, 2), (2, 20), (2, 21), (3, 40), (15, 271)])
def test_markers_beyond_remaining_page_count_fail(page, total):
    with pytest.raises(ParseError, match="inconsistent result counts"):
        MapSearchRequest(**BOUNDS, page=page)._parse(XML.replace('cnt="271"', f'cnt="{total}"'))


@pytest.mark.parametrize("page,total", [(1, 2), (2, 22), (3, 42), (14, 262)])
def test_markers_within_remaining_page_count_are_accepted(page, total):
    result = MapSearchRequest(**BOUNDS, page=page)._parse(XML.replace('cnt="271"', f'cnt="{total}"'))
    assert len(result.items) == 2 and result.total_count == total and result.page == page


def test_all_outside_rectangle_markers_fail():
    with pytest.raises(ParseError, match="no valid"):
        MapSearchRequest(**BOUNDS)._parse(
            XML.replace('lat="34.49462941849498"', 'lat="80.0"').replace('lat="35.0"', 'lat="80.0"')
        )


@pytest.mark.parametrize("genre", ["寿司", "焼き鳥屋", "", None])
def test_missing_or_nonmatching_cuisine_markers_are_skipped(genre):
    replacement = f'rstcat="{genre}"' if genre is not None else ""
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace('rstcat="焼き鳥"', replacement))
    assert len(result.items) == 1 and result.items[0].restaurant_id == "24019007"
    assert result.skipped_count == 1 and result.total_count == 271
    assert "cuisine-mismatched" in result.warnings[-1]


def test_all_cuisine_mismatches_fail():
    with pytest.raises(ParseError, match="no valid"):
        MapSearchRequest(**BOUNDS)._parse(
            XML.replace('rstcat="焼き鳥、創作料理"', 'rstcat="寿司"').replace('rstcat="焼き鳥"', 'rstcat="寿司"')
        )


def test_supported_cuisine_among_other_genres_is_accepted():
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace('rstcat="焼き鳥"', 'rstcat="寿司、 焼き鳥 "'))
    assert len(result.items) == 2 and result.skipped_count == 0
    assert result.items[1].restaurant.genres == ["寿司", "焼き鳥"]


def test_all_invalid_markers_fail():
    with pytest.raises(ParseError, match="no valid"):
        MapSearchRequest(**BOUNDS)._parse(
            XML.replace('rstname="にかわ"', 'rstname=""').replace('lat="35.0"', 'lat="nan"')
        )


@pytest.mark.parametrize("digits", ["０１２３４５６７８９", "٠١٢٣٤٥٦٧٨٩"])
@pytest.mark.parametrize("segment", ["23073004", "A2304", "A230401"])
def test_nonascii_identity_or_area_segments_are_skipped(digits, segment):
    nonascii = segment.translate(str.maketrans("0123456789", digits))
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace(segment, nonascii))
    assert len(result.items) == 1 and result.skipped_count == 1
    assert result.items[0].restaurant_id == "24019007" and result.items[0].restaurant.url.isascii()


def test_all_nonascii_identities_fail():
    mapping = str.maketrans("0123456789", "０１２３４５６７８９")
    xml = XML
    for identity in ("24019007", "23073004"):
        xml = xml.replace(identity, identity.translate(mapping))
    with pytest.raises(ParseError, match="no valid"):
        MapSearchRequest(**BOUNDS)._parse(xml)


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
