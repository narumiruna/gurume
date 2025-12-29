"""Tests for retry module"""

from unittest.mock import Mock
from unittest.mock import patch

import httpx
import pytest

from tabelog.exceptions import NetworkError
from tabelog.exceptions import RateLimitError
from tabelog.retry import DEFAULT_MAX_ATTEMPTS
from tabelog.retry import fetch_with_retry
from tabelog.retry import handle_http_errors
from tabelog.retry import is_retryable_error


class TestRetryHelpers:
    """Test retry helper functions"""

    def test_is_retryable_error_network_errors(self):
        """Test network errors are retryable"""
        assert is_retryable_error(httpx.ConnectError("connection failed"))
        assert is_retryable_error(httpx.TimeoutException("timeout"))
        assert is_retryable_error(httpx.NetworkError("network error"))

    def test_is_retryable_error_server_errors(self):
        """Test 5xx errors are retryable"""
        mock_response = Mock()
        mock_response.status_code = 500
        error = httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        assert is_retryable_error(error)

        mock_response.status_code = 503
        error = httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        assert is_retryable_error(error)

    def test_is_retryable_error_client_errors(self):
        """Test 4xx errors are not retryable"""
        mock_response = Mock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        assert not is_retryable_error(error)

    def test_handle_http_errors_success(self):
        """Test successful response doesn't raise"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        handle_http_errors(mock_response)
        mock_response.raise_for_status.assert_called_once()

    def test_handle_http_errors_rate_limit(self):
        """Test 429 raises RateLimitError"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        )

        with pytest.raises(RateLimitError):
            handle_http_errors(mock_response)

    def test_handle_http_errors_server_error(self):
        """Test 5xx raises NetworkError"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        )

        with pytest.raises(NetworkError):
            handle_http_errors(mock_response)


class TestFetchWithRetry:
    """Test fetch_with_retry function"""

    @patch("tabelog.retry.httpx.get")
    def test_fetch_success_first_try(self, mock_get):
        """Test successful fetch on first try"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_with_retry("http://example.com")
        assert result == mock_response
        assert mock_get.call_count == 1

    @patch("tabelog.retry.httpx.get")
    def test_fetch_rate_limit_error(self, mock_get):
        """Test rate limit error raises immediately"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.raise_for_status = Mock(
            side_effect=httpx.HTTPStatusError("error", request=Mock(), response=mock_response)
        )
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError):
            fetch_with_retry("http://example.com")

    @patch("tabelog.retry.httpx.get")
    def test_fetch_success_after_retries(self, mock_get):
        """Test successful fetch after retries"""
        # First two calls fail with network error, third succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.raise_for_status = Mock()

        mock_get.side_effect = [
            httpx.ConnectError("connection failed"),
            httpx.TimeoutException("timeout"),
            mock_response_success,
        ]

        result = fetch_with_retry("http://example.com")
        assert result == mock_response_success
        assert mock_get.call_count == 3

    @patch("tabelog.retry.httpx.get")
    def test_fetch_all_retries_fail(self, mock_get):
        """Test all retries fail raises NetworkError"""
        mock_get.side_effect = [httpx.ConnectError("failed")] * (DEFAULT_MAX_ATTEMPTS + 1)

        with pytest.raises(NetworkError):
            fetch_with_retry("http://example.com")

        assert mock_get.call_count == DEFAULT_MAX_ATTEMPTS


@pytest.mark.asyncio
class TestFetchWithRetryAsync:
    """Test fetch_with_retry_async function"""

    @patch("tabelog.retry.httpx.AsyncClient")
    async def test_fetch_async_success_first_try(self, mock_async_client):
        """Test successful async fetch on first try"""
        from unittest.mock import AsyncMock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

        from tabelog.retry import fetch_with_retry_async

        result = await fetch_with_retry_async("http://example.com")
        assert result == mock_response
