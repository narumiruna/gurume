"""地區建議功能"""

from __future__ import annotations

from dataclasses import dataclass

import httpx


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

    url = "https://tabelog.com/internal_api/suggest_form_words"
    params = {"sa": query.strip()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = httpx.get(url=url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        suggestions = []
        for item in data:
            suggestion = AreaSuggestion(
                name=item.get("name", ""),
                datatype=item.get("datatype", ""),
                id_in_datatype=item.get("id_in_datatype", 0),
                lat=item.get("lat"),
                lng=item.get("lng"),
            )
            suggestions.append(suggestion)

        return suggestions
    except Exception:
        # 如果 API 失敗，返回空列表
        return []


async def get_area_suggestions_async(query: str, timeout: float = 10.0) -> list[AreaSuggestion]:
    """取得地區建議（異步版本）

    Args:
        query: 搜尋關鍵字
        timeout: 請求超時時間（秒）

    Returns:
        地區建議列表
    """
    if not query or not query.strip():
        return []

    url = "https://tabelog.com/internal_api/suggest_form_words"
    params = {"sa": query.strip()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url=url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            suggestions = []
            for item in data:
                suggestion = AreaSuggestion(
                    name=item.get("name", ""),
                    datatype=item.get("datatype", ""),
                    id_in_datatype=item.get("id_in_datatype", 0),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                )
                suggestions.append(suggestion)

            return suggestions
    except Exception:
        # 如果 API 失敗，返回空列表
        return []


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

    url = "https://tabelog.com/internal_api/suggest_form_words"
    params = {"sk": query.strip()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        resp = httpx.get(url=url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()

        suggestions = []
        for item in data:
            suggestion = KeywordSuggestion(
                name=item.get("name", ""),
                datatype=item.get("datatype", ""),
                id_in_datatype=item.get("id_in_datatype", 0),
                lat=item.get("lat"),
                lng=item.get("lng"),
            )
            suggestions.append(suggestion)

        return suggestions
    except Exception:
        # 如果 API 失敗，返回空列表
        return []


async def get_keyword_suggestions_async(query: str, timeout: float = 10.0) -> list[KeywordSuggestion]:
    """取得關鍵字建議（異步版本）

    Args:
        query: 搜尋關鍵字
        timeout: 請求超時時間（秒）

    Returns:
        關鍵字建議列表
    """
    if not query or not query.strip():
        return []

    url = "https://tabelog.com/internal_api/suggest_form_words"
    params = {"sk": query.strip()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url=url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            suggestions = []
            for item in data:
                suggestion = KeywordSuggestion(
                    name=item.get("name", ""),
                    datatype=item.get("datatype", ""),
                    id_in_datatype=item.get("id_in_datatype", 0),
                    lat=item.get("lat"),
                    lng=item.get("lng"),
                )
                suggestions.append(suggestion)

            return suggestions
    except Exception:
        # 如果 API 失敗，返回空列表
        return []
