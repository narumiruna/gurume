"""Shared map-search schemas and envelope building for CLI and MCP."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from curl_cffi.requests import exceptions as request_errors
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl

from .exceptions import ParseError
from .http_client import http_status_code
from .map_search import MAP_PAGE_SIZE
from .map_search import MAP_SEARCH_URL
from .map_search import MAP_WARNINGS
from .map_search import MapSearchRequest
from .map_search import MapSearchResult
from .server_helpers import _as_http_url
from .server_helpers import _to_restaurant_output
from .server_helpers import _upstream_access_denied_error
from .server_models import RestaurantOutput
from .server_models import ToolErrorOutput


class MapRestaurantOutput(RestaurantOutput):
    restaurant_id: str
    latitude: float
    longitude: float
    prefecture_code: str | None
    station: str | None
    closed_days: str | None
    price_range1: str | None = Field(description="Raw map budget field; meal-period meaning is unverified")
    price_range2: str | None = Field(description="Raw map budget field; meal-period meaning is unverified")


class MapFiltersOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    cuisine: Literal["焼き鳥"]
    page: int
    sort: Literal["ranking"] = "ranking"


class MapMetaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(description="Upstream rectangle total, not a prefecture ranking total")
    current_page: int
    page_size: int = MAP_PAGE_SIZE
    upstream_count: int = Field(description="Markers received before parsing or output truncation")
    skipped_count: int
    has_next_page: bool
    has_prev_page: bool
    source_url: HttpUrl
    source_params: dict[str, str]


class MapSearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "no_results", "error"]
    source: Literal["tabelog_map_xml"] = "tabelog_map_xml"
    scope: Literal["geographic_rectangle"] = "geographic_rectangle"
    items: list[MapRestaurantOutput] = Field(default_factory=list)
    returned_count: int = 0
    limit: int
    has_more: bool = False
    applied_filters: MapFiltersOutput | None = None
    meta: MapMetaOutput | None = None
    warnings: list[str] = Field(default_factory=lambda: list(MAP_WARNINGS))
    error: ToolErrorOutput | None = None


def validate_map_limit(limit: int) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAP_PAGE_SIZE:
        raise ValueError("limit must be an integer between 1 and 20; use page for additional results")


def build_map_output(request: MapSearchRequest, result: MapSearchResult, limit: int) -> MapSearchOutput:
    items = [
        MapRestaurantOutput(
            **_to_restaurant_output(item.restaurant).model_dump(),
            restaurant_id=item.restaurant_id,
            latitude=item.latitude,
            longitude=item.longitude,
            prefecture_code=item.prefecture_code,
            station=item.restaurant.station,
            closed_days=item.restaurant.closed_days,
            price_range1=item.price_range1,
            price_range2=item.price_range2,
        )
        for item in result.items[:limit]
    ]
    return MapSearchOutput(
        status="success" if items else "no_results",
        items=items,
        returned_count=len(items),
        limit=limit,
        has_more=result.has_next_page or len(result.items) > limit,
        applied_filters=MapFiltersOutput.model_validate(asdict(request)),
        meta=MapMetaOutput(
            total_count=result.total_count,
            current_page=result.page,
            upstream_count=result.upstream_count,
            skipped_count=result.skipped_count,
            has_next_page=result.has_next_page,
            has_prev_page=result.has_prev_page,
            source_url=_as_http_url(MAP_SEARCH_URL),
            source_params=result.source_params,
        ),
        warnings=result.warnings,
    )


def build_map_error(error: Exception, limit: int) -> MapSearchOutput:
    if isinstance(error, ValueError | TypeError):
        detail = ToolErrorOutput(
            error_code="invalid_parameters",
            message=f"Invalid map search parameters: {error}",
            retryable=False,
            suggested_action="Use ordered finite bounds, cuisine='焼き鳥', page>=1, and limit=1-20.",
            detail=str(error),
        )
    elif http_status_code(error) == 403:
        detail = _upstream_access_denied_error("Map search", str(error))
    else:
        upstream = isinstance(error, ParseError | request_errors.RequestException)
        detail = ToolErrorOutput(
            error_code="upstream_unavailable" if upstream else "internal_error",
            message="Map search failed because the upstream response was unavailable or invalid."
            if upstream
            else "Map search failed unexpectedly.",
            retryable=not isinstance(error, ParseError),
            suggested_action=(
                "Check permitted Tabelog access and endpoint availability; do not repeatedly retry challenges."
            ),
            detail=str(error),
        )
    return MapSearchOutput(status="error", limit=limit, error=detail)
