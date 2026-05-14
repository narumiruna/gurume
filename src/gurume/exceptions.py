"""Custom exception classes."""

from __future__ import annotations


class TabelogError(Exception):
    """Base class for Tabelog-related errors."""


class ParseError(TabelogError):
    """HTML parsing error."""


class InvalidParameterError(TabelogError):
    """Invalid parameter error."""


class RateLimitError(TabelogError):
    """Rate limit exceeded error."""


class NetworkError(TabelogError):
    """Network connection error."""
