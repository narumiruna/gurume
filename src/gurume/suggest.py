"""地區建議功能"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)
SUGGEST_URL = "https://tabelog.com/internal_api/suggest_form_words"
SUGGEST_PARSE_EXCEPTIONS = (AttributeError, TypeError, ValueError)


class TabelogSuggestUnavailableError(RuntimeError):
    """Raised when Tabelog's suggest API returns no data (upstream endpoint change)."""

    HELP = (
        "Tabelog's autocomplete API currently returns empty results upstream. "
        "Use 'tabelog_list_cuisines' for cuisine types, or pass area names "
        "directly to 'tabelog_search_restaurants'."
    )


@dataclass
class AreaSuggestion:
    """地區建議"""

    name: str
    datatype: str  # AddressMaster, RailroadStation
    id_in_datatype: int
    lat: float | None = None
    lng: float | None = None


@dataclass
class KeywordSuggestion:
    """關鍵字建議"""

    name: str
    datatype: str  # Genre2, Restaurant, Genre2 DetailCondition
    id_in_datatype: int | str
    lat: float | None = None
    lng: float | None = None


def _build_headers() -> dict[str, str]:
    return {"User-Agent": USER_AGENT}


def _parse_area_suggestions(data: list[dict[str, Any]]) -> list[AreaSuggestion]:
    suggestions: list[AreaSuggestion] = []
    for item in data:
        try:
            suggestions.append(
                AreaSuggestion(
                    name=item.get("name", ""),
                    datatype=item.get("datatype", ""),
                    id_in_datatype=item.get("id_in_datatype", 0),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                )
            )
        except SUGGEST_PARSE_EXCEPTIONS:
            continue
    return suggestions


def _parse_keyword_suggestions(data: list[dict[str, Any]]) -> list[KeywordSuggestion]:
    suggestions: list[KeywordSuggestion] = []
    for item in data:
        try:
            suggestions.append(
                KeywordSuggestion(
                    name=item.get("name", ""),
                    datatype=item.get("datatype", ""),
                    id_in_datatype=item.get("id_in_datatype", 0),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                )
            )
        except SUGGEST_PARSE_EXCEPTIONS:
            continue
    return suggestions


def get_area_suggestions(query: str, timeout: float = 10.0) -> list[AreaSuggestion]:
    """取得地區建議

    Args:
        query: 搜尋關鍵字
        timeout: 請求超時時間（秒）

    Returns:
        地區建議列表
    """
    if not query or not query.strip():
        return []

    params = {"sa": query.strip()}

    try:
        resp = httpx.get(
            url=SUGGEST_URL,
            params=params,
            headers=_build_headers(),
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("suggest_empty"):
            raise TabelogSuggestUnavailableError(TabelogSuggestUnavailableError.HELP)
        if not isinstance(data, list):
            return []
    except TabelogSuggestUnavailableError:
        raise
    except (httpx.HTTPError, ValueError):
        return []
    else:
        return _parse_area_suggestions(data)


async def get_area_suggestions_async(query: str, request_timeout: float = 10.0) -> list[AreaSuggestion]:
    """取得地區建議（異步版本）

    Args:
        query: 搜尋關鍵字
        request_timeout: 請求超時時間（秒）

    Returns:
        地區建議列表
    """
    if not query or not query.strip():
        return []

    params = {"sa": query.strip()}

    try:
        async with httpx.AsyncClient(timeout=request_timeout, follow_redirects=True) as client:
            resp = await client.get(url=SUGGEST_URL, params=params, headers=_build_headers())
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and data.get("suggest_empty"):
                raise TabelogSuggestUnavailableError(TabelogSuggestUnavailableError.HELP)
            if not isinstance(data, list):
                return []
    except TabelogSuggestUnavailableError:
        raise
    except (httpx.HTTPError, ValueError):
        return []
    else:
        return _parse_area_suggestions(data)


def get_keyword_suggestions(query: str, timeout: float = 10.0) -> list[KeywordSuggestion]:
    """取得關鍵字建議

    Args:
        query: 搜尋關鍵字
        timeout: 請求超時時間（秒）

    Returns:
        關鍵字建議列表
    """
    if not query or not query.strip():
        return []

    params = {"sk": query.strip()}

    try:
        resp = httpx.get(
            url=SUGGEST_URL,
            params=params,
            headers=_build_headers(),
            timeout=timeout,
            follow_redirects=True,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and data.get("suggest_empty"):
            raise TabelogSuggestUnavailableError(TabelogSuggestUnavailableError.HELP)
        if not isinstance(data, list):
            return []
    except TabelogSuggestUnavailableError:
        raise
    except (httpx.HTTPError, ValueError):
        return []
    else:
        return _parse_keyword_suggestions(data)


async def get_keyword_suggestions_async(query: str, request_timeout: float = 10.0) -> list[KeywordSuggestion]:
    """取得關鍵字建議（異步版本）

    Args:
        query: 搜尋關鍵字
        request_timeout: 請求超時時間（秒）

    Returns:
        關鍵字建議列表
    """
    if not query or not query.strip():
        return []

    params = {"sk": query.strip()}

    try:
        async with httpx.AsyncClient(timeout=request_timeout, follow_redirects=True) as client:
            resp = await client.get(url=SUGGEST_URL, params=params, headers=_build_headers())
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                return []
    except (httpx.HTTPError, ValueError):
        return []
    else:
        return _parse_keyword_suggestions(data)
