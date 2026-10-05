"""Headless checks for user-facing TUI error messages."""

from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from textual.widgets import Input
from textual.widgets import Static

from gurume.search import SearchResponse
from gurume.search import SearchStatus
from gurume.suggest import TabelogSuggestUnavailableError
from gurume.tui import TabelogApp


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            SearchResponse(status=SearchStatus.ERROR, error_message="HTTP Error 403: ", http_status=403),
            "Search failed: Tabelog denied access (HTTP 403). Retrying the same request will not help.",
        ),
        (SearchResponse(status=SearchStatus.ERROR, error_message="HTTP Error 500"), "Search failed: HTTP Error 500"),
        (SearchResponse(status=SearchStatus.NO_RESULTS), "No restaurants found."),
    ],
)
async def test_tui_search_failures_are_english(response: SearchResponse, expected: str) -> None:
    app = TabelogApp()
    async with app.run_test():
        app.query_one("#area-input", Input).value = "Tokyo"
        with patch("gurume.tui.SearchRequest.search", new_callable=AsyncMock, return_value=response):
            await app.perform_search()

        assert str(app.query_one("#detail-content", Static).content) == expected


@pytest.mark.asyncio
async def test_tui_area_suggestion_error_is_english() -> None:
    app = TabelogApp()
    async with app.run_test():
        app.query_one("#area-input", Input).value = "Tokyo"
        with patch(
            "gurume.tui.get_area_suggestions_async",
            new_callable=AsyncMock,
            side_effect=TabelogSuggestUnavailableError("Autocomplete unavailable"),
        ):
            await app.action_show_area_suggest()

        message = str(app.query_one("#detail-content", Static).content)
        assert "Area suggestions are temporarily unavailable" in message
        assert "Autocomplete unavailable" in message


@pytest.mark.asyncio
async def test_tui_empty_suggestions_are_english() -> None:
    app = TabelogApp()
    async with app.run_test():
        app.query_one("#area-input", Input).value = "Tokyo"
        with patch("gurume.tui.get_area_suggestions_async", new_callable=AsyncMock, return_value=[]):
            await app.action_show_area_suggest()
        assert "No area suggestions found" in str(app.query_one("#detail-content", Static).content)

        app.query_one("#keyword-input", Input).value = "sushi"
        with patch("gurume.tui.get_keyword_suggestions_async", new_callable=AsyncMock, return_value=[]):
            await app.action_show_genre_suggest()
        assert "No keyword suggestions found" in str(app.query_one("#detail-content", Static).content)


@pytest.mark.asyncio
async def test_tui_keyword_suggestion_error_is_english() -> None:
    app = TabelogApp()
    async with app.run_test():
        app.query_one("#keyword-input", Input).value = "sushi"
        with patch(
            "gurume.tui.get_keyword_suggestions_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("offline"),
        ):
            await app.action_show_genre_suggest()

        message = str(app.query_one("#detail-content", Static).content)
        assert "Could not fetch keyword suggestions" in message
        assert "Error: offline" in message
