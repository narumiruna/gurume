"""Retry and HTTP error helpers for Tabelog requests."""

from __future__ import annotations

import asyncio
import logging
import time

from curl_cffi import requests
from curl_cffi.requests import exceptions as request_errors

from .exceptions import NetworkError
from .exceptions import RateLimitError
from .http_client import DEFAULT_IMPERSONATE

logger = logging.getLogger(__name__)

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT = 1
DEFAULT_MAX_WAIT = 10

RETRYABLE_REQUEST_ERRORS = (
    request_errors.ConnectionError,
    request_errors.Timeout,
)


def is_retryable_error(exception: BaseException) -> bool:
    """Return whether an exception should trigger a retry."""
    if isinstance(exception, RETRYABLE_REQUEST_ERRORS):
        return True

    if isinstance(exception, request_errors.HTTPError):
        response = exception.response
        return response is not None and 500 <= response.status_code < 600

    return False


def _wait_seconds(attempt: int, min_wait: float, max_wait: float) -> float:
    return min(min_wait * (2 ** (attempt - 1)), max_wait)


def handle_http_errors(response: requests.Response) -> None:
    """Raise project exceptions for HTTP error responses."""
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


def fetch_with_retry(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 10.0,
) -> requests.Response:
    """Fetch URL with retry on transient connection failures."""
    for attempt in range(1, DEFAULT_MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
                impersonate=DEFAULT_IMPERSONATE,
            )
            handle_http_errors(response)
        except RETRYABLE_REQUEST_ERRORS as e:
            if attempt == DEFAULT_MAX_ATTEMPTS:
                logger.error("Failed to fetch %s after all retry attempts: %s", url, e)
                raise NetworkError(f"Failed to fetch {url} after {DEFAULT_MAX_ATTEMPTS} attempts") from e
            logger.warning("Retry attempt %s/%s after %s", attempt, DEFAULT_MAX_ATTEMPTS, e.__class__.__name__)
            time.sleep(_wait_seconds(attempt, DEFAULT_MIN_WAIT, DEFAULT_MAX_WAIT))
        except request_errors.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            raise NetworkError(f"Failed to fetch {url}") from e
        else:
            return response

    raise NetworkError(f"Failed to fetch {url}")


async def fetch_with_retry_async(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    request_timeout: float = 10.0,
) -> requests.Response:
    """Fetch URL with retry on transient connection failures."""
    for attempt in range(1, DEFAULT_MAX_ATTEMPTS + 1):
        try:
            async with requests.AsyncSession(
                timeout=request_timeout,
                allow_redirects=True,
                impersonate=DEFAULT_IMPERSONATE,
            ) as client:
                response = await client.get(url=url, params=params, headers=headers)
                handle_http_errors(response)
        except RETRYABLE_REQUEST_ERRORS as e:
            if attempt == DEFAULT_MAX_ATTEMPTS:
                logger.error("All %s retry attempts failed", DEFAULT_MAX_ATTEMPTS)
                raise NetworkError(f"Failed to fetch {url} after {DEFAULT_MAX_ATTEMPTS} attempts") from e
            logger.warning("Retry attempt %s/%s after %s", attempt, DEFAULT_MAX_ATTEMPTS, e.__class__.__name__)
            await asyncio.sleep(_wait_seconds(attempt, DEFAULT_MIN_WAIT, DEFAULT_MAX_WAIT))
        except request_errors.RequestException as e:
            logger.error("HTTP request failed: %s", e)
            raise NetworkError(f"Failed to fetch {url}") from e
        else:
            return response

    raise NetworkError(f"Failed to fetch {url}")
