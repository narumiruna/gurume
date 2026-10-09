"""Explicit headed-browser retrieval; never an automatic HTTP fallback."""

from importlib import import_module
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


class BrowserRetrievalError(RuntimeError):
    """Browser retrieval failed, optionally with an upstream HTTP status."""

    def __init__(self, message: str, status: int | None = None, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = 500 <= status < 600 if status is not None else retryable


def validate_search_document(html: str, status: int) -> None:
    """Reject challenges and unknown documents instead of reporting no results."""
    soup = BeautifulSoup(html, "html.parser")
    if (
        status == 403
        or soup.select_one("#challenge-form, #cf-challenge-running")
        or (soup.title and soup.title.get_text(strip=True) in {"Just a moment...", "Attention Required! | Cloudflare"})
    ):
        raise BrowserRetrievalError("Browser verification required; manual browser access is needed.", status=403)
    if status >= 400:
        raise BrowserRetrievalError(f"HTTP Error {status}: Browser search failed", status=status)
    if not soup.select_one(".list-rst, .js-rst-cassette-wrap, .rstlist-notfound, .c-page-count"):
        raise RuntimeError("Browser did not return a recognizable restaurant search document")


def _is_transient_navigation_error(error: Exception, timeout_error: type[Exception]) -> bool:
    return isinstance(error, timeout_error) or any(
        code in str(error)
        for code in (
            "net::ERR_CONNECTION_RESET",
            "net::ERR_CONNECTION_CLOSED",
            "net::ERR_CONNECTION_REFUSED",
            "net::ERR_CONNECTION_ABORTED",
            "net::ERR_CONNECTION_TIMED_OUT",
            "net::ERR_TIMED_OUT",
            "net::ERR_NETWORK_CHANGED",
            "net::ERR_INTERNET_DISCONNECTED",
            "net::ERR_NAME_NOT_RESOLVED",
            "net::ERR_ADDRESS_UNREACHABLE",
        )
    )


async def _navigate_search_document(page: Any, api: Any, url: str, navigation_timeout: float) -> tuple[str, str]:
    """Recover a timed-out navigation only with current main-frame response evidence."""
    document_status: int | None = None

    def remember_response(response: Any) -> None:
        nonlocal document_status
        if response.request.is_navigation_request() and response.frame == page.main_frame:
            document_status = response.status

    page.on("response", remember_response)
    try:
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=navigation_timeout * 1000)
        except api.TimeoutError as timeout:
            if document_status is None:
                raise
            html = await page.content()
            try:
                validate_search_document(html, document_status)
            except BrowserRetrievalError:
                raise
            except RuntimeError:
                raise timeout from None
            return html, page.url
        if response is None:
            raise RuntimeError("Browser navigation returned no document response")
        html = await page.content()
    except api.Error as error:
        raise BrowserRetrievalError(
            f"Browser navigation failed: {error}",
            retryable=_is_transient_navigation_error(error, api.TimeoutError),
        ) from error
    validate_search_document(html, response.status)
    return html, page.url


async def fetch_search_document(url: str, navigation_timeout: float) -> tuple[str, str]:
    """Use a dedicated local profile, preserving cookies only within that browser."""
    try:
        api = import_module("playwright.async_api")
    except ImportError as error:
        raise RuntimeError(
            "Browser support is not installed: install gurume[browser], then run playwright install chromium"
        ) from error
    try:
        profile = Path.home() / ".cache" / "gurume" / "browser"
        profile.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise BrowserRetrievalError(f"Cannot prepare Gurume browser profile: {error}") from error
    try:
        async with api.async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(str(profile), headless=False)
            try:
                page = await context.new_page()
                return await _navigate_search_document(page, api, url, navigation_timeout)
            finally:
                await context.close()
    except api.Error as error:
        raise RuntimeError(f"Headed browser retrieval failed: {error}") from error
