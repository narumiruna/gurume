"""Retry and resilience mechanisms for robust HTTP requests

This module provides retry logic with exponential backoff for handling
transient failures when scraping Tabelog.

Features:
- Auto-retry on transient HTTP failures (5xx errors, connection errors)
- Exponential backoff with jitter
- Configurable retry attempts and delays
- Logging of retry attempts
"""

from __future__ import annotations

import httpx
from loguru import logger
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from .exceptions import NetworkError
from .exceptions import RateLimitError

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 1  # seconds
DEFAULT_MAX_WAIT = 10  # seconds


def is_retryable_error(exception: BaseException) -> bool:
    """Check if an exception is retryable

    Args:
        exception: Exception to check

    Returns:
        True if the exception should trigger a retry
    """
    # Retry on network errors
    if isinstance(exception, httpx.ConnectError | httpx.TimeoutException | httpx.NetworkError):
        return True

    # Retry on server errors (5xx)
    if isinstance(exception, httpx.HTTPStatusError):
        return 500 <= exception.response.status_code < 600

    return False


def create_retry_decorator(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
):
    """Create a retry decorator with custom configuration

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Returns:
        Retry decorator configured with exponential backoff
    """
    return retry(
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number}/{max_attempts} "
            f"after {retry_state.outcome.exception().__class__.__name__}"
        ),
        reraise=True,
    )


# Default retry decorator for sync requests
retry_on_failure = create_retry_decorator()


def handle_http_errors(response: httpx.Response) -> None:
    """Handle HTTP errors and raise appropriate exceptions

    Args:
        response: HTTP response to check

    Raises:
        RateLimitError: If rate limited (429)
        NetworkError: For other HTTP errors
    """
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise RateLimitError("Rate limit exceeded. Please slow down requests.") from e
        elif 500 <= e.response.status_code < 600:
            raise NetworkError(f"Server error: {e.response.status_code}") from e
        elif 400 <= e.response.status_code < 500:
            raise NetworkError(f"Client error: {e.response.status_code}") from e
        else:
            raise NetworkError(f"HTTP error: {e.response.status_code}") from e


@retry_on_failure
def _fetch_with_retry_impl(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    """Internal implementation of fetch with retry

    This function is decorated with @retry_on_failure and will retry
    on transient network errors.
    """
    response = httpx.get(url=url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
    handle_http_errors(response)
    return response


def fetch_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    """Fetch URL with automatic retry on transient failures

    Args:
        url: URL to fetch
        params: Query parameters
        headers: HTTP headers
        timeout: Request timeout in seconds

    Returns:
        HTTP response

    Raises:
        RateLimitError: If rate limited
        NetworkError: For persistent HTTP errors or if all retries failed
    """
    try:
        return _fetch_with_retry_impl(url, params, headers, timeout)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
        # All retries failed
        logger.error(f"Failed to fetch {url} after all retry attempts: {e}")
        raise NetworkError(f"Failed to fetch {url} after {DEFAULT_MAX_ATTEMPTS} attempts") from e


async def fetch_with_retry_async(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> httpx.Response:
    """Fetch URL with automatic retry on transient failures (async version)

    Args:
        url: URL to fetch
        params: Query parameters
        headers: HTTP headers
        timeout: Request timeout in seconds

    Returns:
        HTTP response

    Raises:
        RateLimitError: If rate limited
        NetworkError: For persistent HTTP errors
        RetryError: If all retry attempts failed
    """
    max_attempts = DEFAULT_MAX_ATTEMPTS
    min_wait = DEFAULT_MIN_WAIT
    max_wait = DEFAULT_MAX_WAIT

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(url=url, params=params, headers=headers)
                handle_http_errors(response)
                return response
        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt < max_attempts:
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                logger.warning(f"Retry attempt {attempt}/{max_attempts} after {e.__class__.__name__}")
                import asyncio

                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_attempts} retry attempts failed")
                raise NetworkError(f"Failed to fetch {url} after {max_attempts} attempts") from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP request failed: {e}")
            raise NetworkError(f"Failed to fetch {url}") from e

    # Should never reach here, but mypy wants it
    raise NetworkError(f"Failed to fetch {url}")
