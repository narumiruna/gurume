"""Shared curl_cffi HTTP settings."""

from __future__ import annotations

import os
from typing import cast

from curl_cffi.requests import BrowserTypeLiteral

DEFAULT_IMPERSONATE = cast(BrowserTypeLiteral, os.getenv("GURUME_IMPERSONATE") or "safari")
