"""MCP map search schema and structured responses."""

from asyncio import CancelledError
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions as request_errors
from mcp.server.fastmcp.exceptions import ToolError

from gurume.exceptions import ParseError
from gurume.map_search import MapSearchRequest
from gurume.server import mcp
from gurume.server import tabelog_search_map_restaurants

from .test_map_search import BOUNDS
from .test_map_search import XML
from .test_map_search import MapBounds


@pytest.mark.asyncio
async def test_mcp_map_schema():
    tool = next(t for t in await mcp.list_tools() if t.name == "tabelog_search_map_restaurants")
    assert tool.annotations is not None and tool.annotations.readOnlyHint is True
    assert set(tool.inputSchema["required"]) == set(BOUNDS)
    assert tool.inputSchema["properties"]["limit"]["maximum"] == 20
    assert tool.inputSchema["properties"]["page"]["minimum"] == 1
    assert tool.inputSchema["properties"]["min_lon"]["minimum"] == -180
    assert tool.outputSchema is not None
    assert tool.outputSchema["properties"]["scope"]["const"] == "geographic_rectangle"


@pytest.mark.asyncio
async def test_mcp_call_returns_validated_structured_output():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock, return_value=result):
        content, structured = await mcp.call_tool("tabelog_search_map_restaurants", BOUNDS | {"limit": 1})
    assert isinstance(structured, dict) and content
    assert structured["status"] == "success"
    assert structured["returned_count"] == 1 and structured["has_more"] is True
    assert structured["meta"]["upstream_count"] == 2
    assert structured["meta"]["total_count"] == 271
    assert structured["applied_filters"]["cuisine"] == "焼き鳥"
    assert structured["items"][0]["dinner_price"] is None
    assert structured["items"][0]["price_range2"] == "￥15,000～￥19,999"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "override", [{"limit": 21}, {"page": 0}, {"cuisine": "寿司"}, {"min_lat": 36}, {"min_lon": float("nan")}]
)
async def test_direct_validation_precedes_http(override):
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock) as fetch:
        result = await tabelog_search_map_restaurants(**(BOUNDS | override))
    assert result.status == "error" and result.error is not None
    assert result.error.error_code == "invalid_parameters" and not result.error.retryable
    fetch.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", list(BOUNDS))
@pytest.mark.parametrize("value", [False, True])
async def test_boolean_bounds_rejected_by_direct_and_protocol_calls(field, value):
    bounds: MapBounds = {"min_lat": -2.0, "max_lat": 2.0, "min_lon": -2.0, "max_lon": 2.0}
    kwargs = bounds | {field: value}
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock) as fetch:
        direct = await tabelog_search_map_restaurants(**kwargs)
        assert direct.error is not None and direct.error.error_code == "invalid_parameters"
        with pytest.raises(ToolError, match=field):
            await mcp.call_tool("tabelog_search_map_restaurants", dict(kwargs))
    fetch.assert_not_called()


@pytest.mark.asyncio
async def test_protocol_accepts_integer_coordinates_as_numbers():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock, return_value=result) as fetch:
        _, structured = await mcp.call_tool(
            "tabelog_search_map_restaurants", {"min_lat": -2, "max_lat": 2, "min_lon": -2, "max_lon": 2}
        )
    assert isinstance(structured, dict) and structured["status"] == "success"
    fetch.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error,code,retryable",
    [
        (ParseError("bad XML"), "upstream_unavailable", False),
        (request_errors.HTTPError("403", response=Mock(status_code=403)), "upstream_unavailable", False),
        (request_errors.Timeout("timeout"), "upstream_unavailable", True),
        (RuntimeError("unexpected"), "internal_error", True),
    ],
)
async def test_mcp_failures(error, code, retryable):
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock, side_effect=error) as fetch:
        result = await tabelog_search_map_restaurants(**BOUNDS)
    assert result.status == "error" and result.error is not None
    assert result.error.error_code == code and result.error.retryable is retryable
    assert not result.items and result.meta is None
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_empty_response():
    empty = MapSearchRequest(**BOUNDS)._parse('<markers><srchinfo cnt="0"/></markers>')
    with patch.object(MapSearchRequest, "search", new_callable=AsyncMock, return_value=empty):
        result = await tabelog_search_map_restaurants(**BOUNDS)
    assert result.status == "no_results" and not result.has_more and result.meta is not None
    assert result.meta.total_count == 0


@pytest.mark.asyncio
async def test_mcp_cancellation_propagates():
    with (
        patch.object(MapSearchRequest, "search", new_callable=AsyncMock, side_effect=CancelledError),
        pytest.raises(CancelledError),
    ):
        await tabelog_search_map_restaurants(**BOUNDS)


@pytest.mark.asyncio
async def test_output_conversion_errors_propagate():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with (
        patch.object(MapSearchRequest, "search", new_callable=AsyncMock, return_value=result),
        patch("gurume.server.build_map_output", side_effect=ValueError("output conversion")),
        pytest.raises(ValueError, match="output conversion"),
    ):
        await tabelog_search_map_restaurants(**BOUNDS)
