"""Explicit headed-browser retrieval; never an automatic HTTP fallback."""

from importlib import import_module
from pathlib import Path

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


async def fetch_search_document(url: str, navigation_timeout: float) -> tuple[str, str]:
    """Use a dedicated local profile, preserving cookies only within that browser."""
    try:
        api = import_module("playwright.async_api")
    except ImportError as error:
        raise RuntimeError(
            "Browser support is not installed: install gurume[browser], then run playwright install chromium"
        ) from error
    profile = Path.home() / ".cache" / "gurume" / "browser"
    profile.mkdir(parents=True, exist_ok=True)
    try:
        async with api.async_playwright() as playwright:
            context = await playwright.chromium.launch_persistent_context(str(profile), headless=False)
            try:
                page = await context.new_page()
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=navigation_timeout * 1000)
                    if response is None:
                        raise RuntimeError("Browser navigation returned no document response")
                    html = await page.content()
                except api.Error as error:
                    transient = isinstance(error, api.TimeoutError) or any(
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
                    raise BrowserRetrievalError(f"Browser navigation failed: {error}", retryable=transient) from error
                validate_search_document(html, response.status)
                return html, page.url
            finally:
                await context.close()
    except api.Error as error:
        raise RuntimeError(f"Headed browser retrieval failed: {error}") from error
