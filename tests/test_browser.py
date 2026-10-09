"""Explicit browser search uses shared parsing and does not retry challenges."""

from asyncio import CancelledError
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from gurume.browser import BrowserRetrievalError
from gurume.browser import fetch_search_document
from gurume.browser import validate_search_document
from gurume.search import SearchRequest
from gurume.search import SearchStatus
from gurume.server import mcp
from gurume.server import tabelog_search_restaurants

HTML = """<div class="c-page-count"><span class="c-page-count__num">1</span></div>
<div class="list-rst"><a class="list-rst__rst-name-target"
href="https://tabelog.com/mie/A2403/A240301/24012212/">こま田</a>
<span class="c-rating__val">4.60</span></div>"""


@pytest.mark.parametrize(
    "html,status",
    [
        ("<title>Just a moment...</title>", 200),
        ('<form id="challenge-form"></form>', 200),
        (HTML, 403),
        (HTML, 404),
        ("<html>Unknown document</html>", 200),
    ],
)
def test_unusable_document_rejected(html, status):
    with pytest.raises(RuntimeError):
        validate_search_document(html, status)


def test_recognized_no_results():
    validate_search_document('<div class="rstlist-notfound"></div>', 200)


@pytest.mark.asyncio
async def test_browser_search_reuses_parser_and_meta():
    fetch = AsyncMock(return_value=(HTML, "https://tabelog.com/mie/rstLst/?SrtT=rt&PG=2"))
    with patch("gurume.browser.fetch_search_document", fetch), patch("gurume.search.requests.AsyncSession") as http:
        result = await tabelog_search_restaurants(area="三重", page=2, limit=10, transport="browser")
    assert result.status == "success"
    assert result.items[0].name == "こま田"
    assert result.items[0].rating == 4.6
    assert result.meta.current_page == 2
    assert result.meta.area_filter_confidence == "high"
    assert "PG=2" in fetch.call_args.args[0]
    http.assert_not_called()


@pytest.mark.asyncio
async def test_challenge_is_non_retryable():
    fetch = AsyncMock(side_effect=BrowserRetrievalError("Verification required", status=403))
    with patch("gurume.browser.fetch_search_document", fetch):
        result = await tabelog_search_restaurants(area="三重", transport="browser")
    assert result.status == "error"
    assert result.error.retryable is False
    assert result.items == []
    fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_browser_mcp_protocol():
    with patch("gurume.browser.fetch_search_document", AsyncMock(return_value=(HTML, "https://tabelog.com/mie/rstLst/"))):
        _, result = await mcp.call_tool(
            "tabelog_search_restaurants", {"area": "三重", "limit": 10, "transport": "browser"}
        )
    assert isinstance(result, dict)
    assert result["status"] == "success"
    assert result["items"][0]["name"] == "こま田"


@pytest.mark.asyncio
async def test_browser_mcp_challenge():
    with patch("gurume.browser.fetch_search_document", AsyncMock(side_effect=BrowserRetrievalError("blocked", 403))):
        _, result = await mcp.call_tool("tabelog_search_restaurants", {"area": "三重", "transport": "browser"})
    assert isinstance(result, dict)
    assert result["status"] == "error"
    assert result["error"]["retryable"] is False
    assert result["items"] == []


@pytest.mark.asyncio
async def test_http_remains_default():
    with (
        patch(
            "gurume.search.SearchRequest.search",
            AsyncMock(
                return_value=SimpleNamespace(status=SearchStatus.NO_RESULTS, restaurants=[], meta=None, warnings=[])
            ),
        ) as http,
        patch("gurume.search.SearchRequest.search_browser") as browser,
    ):
        await tabelog_search_restaurants(area="三重")
    http.assert_awaited_once()
    browser.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_transport():
    result = await tabelog_search_restaurants(transport="invalid")
    assert result.error.error_code == "invalid_parameters"


@pytest.mark.asyncio
async def test_browser_one_page_bound():
    result = await SearchRequest(max_pages=2).search_browser()
    assert result.status == SearchStatus.ERROR


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, BrowserRetrievalError("blocked", 403), CancelledError()])
async def test_context_cleanup(tmp_path, failure):
    page = SimpleNamespace(
        goto=AsyncMock(return_value=SimpleNamespace(status=200)),
        content=AsyncMock(return_value=HTML),
        url="https://tabelog.com/mie/rstLst/",
        on=Mock(),
        main_frame=object(),
    )
    if failure:
        page.goto.side_effect = failure
    context = SimpleNamespace(new_page=AsyncMock(return_value=page), close=AsyncMock())
    launcher = AsyncMock(return_value=context)
    manager = MagicMock()
    manager.__aenter__ = AsyncMock(
        return_value=SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launcher))
    )
    manager.__aexit__ = AsyncMock(return_value=False)
    api_error = type("PlaywrightError", (Exception,), {})
    api = SimpleNamespace(
        async_playwright=lambda: manager,
        Error=api_error,
        TimeoutError=type("PlaywrightTimeoutError", (api_error,), {}),
    )
    with (
        patch("gurume.browser.import_module", return_value=api),
        patch("gurume.browser.Path.home", return_value=tmp_path),
    ):
        if failure:
            with pytest.raises(type(failure)):
                await fetch_search_document(page.url, 30)
        else:
            assert await fetch_search_document(page.url, 30) == (HTML, page.url)
    assert launcher.call_args.kwargs["headless"] is False
    context.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_optional_dependency():
    with (
        patch("gurume.browser.import_module", side_effect=ImportError),
        pytest.raises(RuntimeError, match=r"gurume\[browser\]"),
    ):
        await fetch_search_document("https://tabelog.com/mie/rstLst/", 30)
