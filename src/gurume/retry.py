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

from curl_cffi import requests
from curl_cffi.requests import exceptions as request_errors
from loguru import logger
from tenacity import RetryCallState
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_exponential

from .exceptions import NetworkError
from .exceptions import RateLimitError
from .http_client import DEFAULT_IMPERSONATE

# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 1  # seconds
DEFAULT_MAX_WAIT = 10  # seconds

RETRYABLE_REQUEST_ERRORS = (
    request_errors.ConnectionError,
    request_errors.Timeout,
)


def _retry_exception_name(retry_state: RetryCallState) -> str:
    """Return the retry exception name, if Tenacity has recorded one."""
    outcome = retry_state.outcome
    if outcome is None:
        return "unknown error"

    exception = outcome.exception()
    if exception is None:
        return "unknown error"

    return exception.__class__.__name__


def is_retryable_error(exception: BaseException) -> bool:
    """Check if an exception is retryable

    Args:
        exception: Exception to check

    Returns:
        True if the exception should trigger a retry
    """
    # Retry on network errors
    if isinstance(exception, RETRYABLE_REQUEST_ERRORS):
        return True

    # Retry on server errors (5xx)
    if isinstance(exception, request_errors.HTTPError):
        response = exception.response
        return response is not None and 500 <= response.status_code < 600

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

    def log_before_sleep(retry_state: RetryCallState) -> None:
        logger.warning(
            f"Retry attempt {retry_state.attempt_number}/{max_attempts} after {_retry_exception_name(retry_state)}"
        )

    return retry(
        retry=retry_if_exception_type(RETRYABLE_REQUEST_ERRORS),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        before_sleep=log_before_sleep,
        reraise=True,
    )


# Default retry decorator for sync requests
retry_on_failure = create_retry_decorator()


def handle_http_errors(response: requests.Response) -> None:
    """Handle HTTP errors and raise appropriate exceptions

    Args:
        response: HTTP response to check

    Raises:
        RateLimitError: If rate limited (429)
        NetworkError: For other HTTP errors
    """
    try:
        response.raise_for_status()
    except request_errors.HTTPError as e:
        status_code = getattr(e.response, "status_code", None)
        if not isinstance(status_code, int):
            raise NetworkError("HTTP error") from e
        if status_code == 429:
            raise RateLimitError("Rate limit exceeded. Please slow down requests.") from e
        if 500 <= status_code < 600:
            raise NetworkError(f"Server error: {status_code}") from e
        if 400 <= status_code < 500:
            raise NetworkError(f"Client error: {status_code}") from e
        raise NetworkError(f"HTTP error: {status_code}") from e


@retry_on_failure
def _fetch_with_retry_impl(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> requests.Response:
    """Internal implementation of fetch with retry

    This function is decorated with @retry_on_failure and will retry
    on transient network errors.
    """
    response = requests.get(
        url=url,
        params=params,
        headers=headers,
        timeout=timeout,
        allow_redirects=True,
        impersonate=DEFAULT_IMPERSONATE,
    )
    handle_http_errors(response)
    return response


def fetch_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> requests.Response:
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
    except RETRYABLE_REQUEST_ERRORS as e:
        # All retries failed
        logger.error(f"Failed to fetch {url} after all retry attempts: {e}")
        raise NetworkError(f"Failed to fetch {url} after {DEFAULT_MAX_ATTEMPTS} attempts") from e


async def fetch_with_retry_async(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    request_timeout: float = 10.0,
) -> requests.Response:
    """Fetch URL with automatic retry on transient failures (async version)

    Args:
        url: URL to fetch
        params: Query parameters
        headers: HTTP headers
        request_timeout: Request timeout in seconds

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
            async with requests.AsyncSession(
                timeout=request_timeout,
                allow_redirects=True,
                impersonate=DEFAULT_IMPERSONATE,
            ) as client:
                response = await client.get(url=url, params=params, headers=headers)
                handle_http_errors(response)
                return response
        except RETRYABLE_REQUEST_ERRORS as e:
            if attempt < max_attempts:
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                logger.warning(f"Retry attempt {attempt}/{max_attempts} after {e.__class__.__name__}")
                import asyncio

                await asyncio.sleep(wait_time)
            else:
                logger.error(f"All {max_attempts} retry attempts failed")
                raise NetworkError(f"Failed to fetch {url} after {max_attempts} attempts") from e
        except request_errors.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            raise NetworkError(f"Failed to fetch {url}") from e

    # Should never reach here, but mypy wants it
    raise NetworkError(f"Failed to fetch {url}")
