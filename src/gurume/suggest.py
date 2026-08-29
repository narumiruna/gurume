"""Area and keyword suggestion helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from curl_cffi import requests
from curl_cffi.requests import exceptions as request_errors

from .http_client import DEFAULT_IMPERSONATE

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
    """Area suggestion."""

    name: str
    datatype: str
    id_in_datatype: int
    lat: float | None = None
    lng: float | None = None


@dataclass
class KeywordSuggestion:
    """Keyword suggestion."""

    name: str
    datatype: str
    id_in_datatype: int | str
    lat: float | None = None
    lng: float | None = None


def _suggest_data_from_response(response: requests.Response) -> list[Any]:
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and data.get("suggest_empty"):
        raise TabelogSuggestUnavailableError(TabelogSuggestUnavailableError.HELP)
    return data if isinstance(data, list) else []


def _fetch_suggestion_data(param_name: str, query: str, timeout: float) -> list[Any]:
    query = query.strip()
    if not query:
        return []

    try:
        response = requests.get(
            url=SUGGEST_URL,
            params={param_name: query},
            timeout=timeout,
            allow_redirects=True,
            impersonate=DEFAULT_IMPERSONATE,
        )
        return _suggest_data_from_response(response)
    except TabelogSuggestUnavailableError:
        raise
    except (request_errors.RequestException, ValueError):
        return []


async def _fetch_suggestion_data_async(param_name: str, query: str, request_timeout: float) -> list[Any]:
    query = query.strip()
    if not query:
        return []

    try:
        async with requests.AsyncSession(
            timeout=request_timeout,
            allow_redirects=True,
            impersonate=DEFAULT_IMPERSONATE,
        ) as client:
            response = await client.get(url=SUGGEST_URL, params={param_name: query})
            return _suggest_data_from_response(response)
    except TabelogSuggestUnavailableError:
        raise
    except (request_errors.RequestException, ValueError):
        return []


def _parse_area_suggestions(data: list[Any]) -> list[AreaSuggestion]:
    suggestions: list[AreaSuggestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
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


def _parse_keyword_suggestions(data: list[Any]) -> list[KeywordSuggestion]:
    suggestions: list[KeywordSuggestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
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
    """Get area suggestions."""
    return _parse_area_suggestions(_fetch_suggestion_data("sa", query, timeout))


async def get_area_suggestions_async(query: str, request_timeout: float = 10.0) -> list[AreaSuggestion]:
    """Get area suggestions asynchronously."""
    data = await _fetch_suggestion_data_async("sa", query, request_timeout)
    return _parse_area_suggestions(data)


def get_keyword_suggestions(query: str, timeout: float = 10.0) -> list[KeywordSuggestion]:
    """Get keyword suggestions."""
    return _parse_keyword_suggestions(_fetch_suggestion_data("sk", query, timeout))


async def get_keyword_suggestions_async(query: str, request_timeout: float = 10.0) -> list[KeywordSuggestion]:
    """Get keyword suggestions asynchronously."""
    data = await _fetch_suggestion_data_async("sk", query, request_timeout)
    return _parse_keyword_suggestions(data)
