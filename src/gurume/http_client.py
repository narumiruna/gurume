"""Shared curl_cffi HTTP settings."""

from __future__ import annotations

import os
from typing import cast

from curl_cffi.requests import BrowserTypeLiteral
from curl_cffi.requests import exceptions as request_errors

DEFAULT_IMPERSONATE = cast(BrowserTypeLiteral, os.getenv("GURUME_IMPERSONATE") or "safari")


def http_status_code(error: BaseException) -> int | None:
    """Return the HTTP status from a request error or its direct cause."""
    http_error = error if isinstance(error, request_errors.HTTPError) else error.__cause__
    if isinstance(http_error, request_errors.HTTPError) and http_error.response is not None:
        return http_error.response.status_code
    return None
