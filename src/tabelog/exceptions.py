"""自定義例外類別"""

from __future__ import annotations


class TabelogError(Exception):
    """Tabelog 相關錯誤的基礎類別"""


class ParseError(TabelogError):
    """HTML 解析錯誤"""


class InvalidParameterError(TabelogError):
    """無效的參數錯誤"""


class RateLimitError(TabelogError):
    """超過速率限制錯誤"""


class NetworkError(TabelogError):
    """網路連線錯誤"""
