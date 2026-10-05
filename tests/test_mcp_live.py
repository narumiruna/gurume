"""Offline checks for the optional stdio MCP live probe."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from mcp.types import CallToolResult

from scripts.check_mcp_live import check_live
from scripts.check_mcp_live import summarize


def _response(status: str, **fields: object) -> CallToolResult:
    return CallToolResult(content=[], structuredContent={"status": status, **fields})


def test_summarize_preserves_errors_and_requires_results() -> None:
    error = {"error_code": "upstream_unavailable", "retryable": False}
    assert summarize(_response("error", error=error)) == {"status": "error", "error": error}
    assert summarize(_response("success", returned_count=0), require_items=True)["status"] == "no_results"
    assert summarize(_response("success", returned_count=2), require_items=True)["status"] == "success"
    assert summarize(CallToolResult(content=[], isError=True))["status"] == "error"


@pytest.mark.asyncio
@pytest.mark.parametrize("search_available", [False, True])
async def test_check_live_reports_upstream_state(search_available: bool) -> None:
    url = "https://tabelog.com/tokyo/A1301/A130101/13000001/"
    search = (
        _response("success", returned_count=1, items=[{"url": url}])
        if search_available
        else _response("error", error={"error_code": "upstream_unavailable", "retryable": False})
    )
    session = AsyncMock()
    session.call_tool.side_effect = [
        _response("success", returned_count=29),
        _response("success", returned_count=10),
        search,
        _response("success") if search_available else _response("error", error={"error_code": "upstream_unavailable"}),
    ]

    @asynccontextmanager
    async def fake_stdio(_server):
        yield None, None

    with patch("scripts.check_mcp_live.stdio_client", fake_stdio), patch(
        "scripts.check_mcp_live.ClientSession"
    ) as client:
        client.return_value.__aenter__.return_value = session
        result = await check_live(restaurant_url=url if not search_available else None)

    assert result["status"] == ("ok" if search_available else "degraded")
    assert result["checks"]["cuisines"]["status"] == "success"
    assert result["checks"]["search"]["status"] == ("success" if search_available else "error")
    assert result["checks"]["details"]["status"] == ("success" if search_available else "error")
    assert session.call_tool.call_args.args[1]["restaurant_url"] == url


@pytest.mark.asyncio
async def test_check_live_skips_detail_when_search_fails_without_url() -> None:
    session = AsyncMock()
    session.call_tool.side_effect = [
        _response("success", returned_count=29),
        _response("success", returned_count=10),
        _response("error", error={"error_code": "upstream_unavailable"}),
    ]

    @asynccontextmanager
    async def fake_stdio(_server):
        yield None, None

    with patch("scripts.check_mcp_live.stdio_client", fake_stdio), patch(
        "scripts.check_mcp_live.ClientSession"
    ) as client:
        client.return_value.__aenter__.return_value = session
        result = await check_live()

    assert result["status"] == "degraded"
    assert result["checks"]["details"]["status"] == "skipped"
    assert session.call_tool.call_count == 3
