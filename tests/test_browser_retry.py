"""Browser retryability survives retrieval, parsing and MCP output without automatic retries."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from gurume.browser import BrowserRetrievalError
from gurume.search import SearchRequest
from gurume.search import SearchResponse
from gurume.search import SearchStatus
from gurume.server import mcp


class PlaywrightError(Exception):
    pass


class PlaywrightTimeoutError(PlaywrightError):
    pass


@pytest.fixture
def browser(monkeypatch, tmp_path):
    page = SimpleNamespace(
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        content=AsyncMock(return_value='<div class="c-page-count">0</div>'),
        url="https://tabelog.com/mie/rstLst/",
    )
    context = SimpleNamespace(new_page=AsyncMock(return_value=page), close=AsyncMock())
    launcher = AsyncMock(return_value=context)
    manager = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launcher))

    class Manager:
        async def __aenter__(self):
            return manager

        async def __aexit__(self, *_args):
            return False

    api = SimpleNamespace(async_playwright=Manager, Error=PlaywrightError, TimeoutError=PlaywrightTimeoutError)
    monkeypatch.setattr("gurume.browser.import_module", lambda _: api)
    monkeypatch.setattr("gurume.browser.Path.home", lambda: tmp_path)
    return page, context, launcher


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,html,retryable",
    [
        (403, "Denied", False),
        (404, "Not found", False),
        (429, "Rate limited", False),
        (500, "Temporary failure", True),
        (503, "Temporary failure", True),
        (599, "Temporary failure", True),
        (600, "Unknown error", False),
        (200, "<title>Just a moment...</title>", False),
        (503, '<form id="challenge-form"></form>', False),
        (200, "<html>Unknown document</html>", False),
    ],
)
async def test_http_and_challenge_retryability(browser, status, html, retryable):
    page, context, _ = browser
    page.goto.return_value.status = status
    page.content.return_value = html
    _, output = await mcp.call_tool("tabelog_search_restaurants", {"area": "三重", "transport": "browser"})
    assert isinstance(output, dict)
    assert output["status"] == "error"
    assert output["error"]["retryable"] is retryable
    assert output["items"] == []
    assert output["meta"] is None
    assert output["has_more"] is False
    action = output["error"]["suggested_action"]
    assert ("Retry later" in action) is retryable
    page.goto.assert_awaited_once()
    context.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,retryable",
    [
        (PlaywrightTimeoutError("Timed out"), True),
        (PlaywrightError("page.goto: net::ERR_CONNECTION_RESET"), True),
        (PlaywrightError("page.goto: net::ERR_CONNECTION_REFUSED"), True),
        (PlaywrightError("page.goto: net::ERR_NAME_NOT_RESOLVED"), True),
        (PlaywrightError("page.goto: net::ERR_CERT_AUTHORITY_INVALID"), False),
        (PlaywrightError("page.goto: net::ERR_INVALID_URL"), False),
        (PlaywrightError("Unclassified browser error"), False),
    ],
)
async def test_navigation_failure_retryability(browser, failure, retryable):
    page, context, _ = browser
    page.goto.side_effect = failure
    _, output = await mcp.call_tool("tabelog_search_restaurants", {"area": "三重", "transport": "browser"})
    assert isinstance(output, dict)
    assert output["error"]["retryable"] is retryable
    assert output["items"] == []
    page.goto.assert_awaited_once()
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_launch_configuration_failure_is_not_retryable(browser):
    page, _, launcher = browser
    launcher.side_effect = PlaywrightError("Executable missing or graphical display unavailable")
    _, output = await mcp.call_tool("tabelog_search_restaurants", {"transport": "browser"})
    assert isinstance(output, dict)
    assert output["error"]["retryable"] is False
    page.goto.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_dependency_is_not_retryable(monkeypatch):
    def missing(_):
        raise ImportError("not installed")

    monkeypatch.setattr("gurume.browser.import_module", missing)
    _, output = await mcp.call_tool("tabelog_search_restaurants", {"transport": "browser"})
    assert isinstance(output, dict)
    assert output["error"]["retryable"] is False
    assert "gurume[browser]" in output["error"]["detail"]


@pytest.mark.asyncio
async def test_core_preserves_transient_evidence(browser):
    page, _, _ = browser
    page.goto.side_effect = PlaywrightTimeoutError("Timed out")
    result = await SearchRequest(area="三重").search_browser()
    assert result.http_status is None  # Do not invent an HTTP 503 for navigation errors.
    assert result.error_retryable is True
    for response in [result.filter(), result.sort_by("name"), result.top(10)]:
        assert response.error_retryable is True
        assert response.to_dict()["error_retryable"] is True
    assert "error_retryable" not in SearchResponse(status=SearchStatus.ERROR).to_dict()


def test_permanent_http_status_cannot_be_overridden():
    assert BrowserRetrievalError("Forbidden", status=403, retryable=True).retryable is False
