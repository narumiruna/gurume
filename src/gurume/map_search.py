"""One-page geographic yakitori search using Tabelog's undocumented map XML."""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from dataclasses import field

from curl_cffi import requests

from .exceptions import ParseError
from .http_client import DEFAULT_IMPERSONATE
from .restaurant import Restaurant

MAP_SEARCH_URL = "https://tabelog.com/xml/rstmap"
MAP_PAGE_SIZE = 20
MAP_WARNINGS = (
    "This undocumented map endpoint may change or become unavailable.",
    "Results and total_count describe a geographic rectangle, not an exact prefecture or national ranking.",
    "price_range1 and price_range2 are raw upstream fields; lunch/dinner semantics are not verified.",
)
RESTAURANT_PATH = re.compile(r"/[a-z]+/A\d+/A\d+/(\d+)/")


@dataclass
class MapRestaurant:
    restaurant: Restaurant
    restaurant_id: str
    latitude: float
    longitude: float
    prefecture_code: str | None
    price_range1: str | None
    price_range2: str | None


@dataclass
class MapSearchResult:
    items: list[MapRestaurant]
    total_count: int
    page: int
    upstream_count: int
    has_next_page: bool
    has_prev_page: bool
    source_params: dict[str, str]
    skipped_count: int = 0
    warnings: list[str] = field(default_factory=lambda: list(MAP_WARNINGS))


@dataclass
class MapSearchRequest:
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    cuisine: str = "焼き鳥"
    page: int = 1

    def __post_init__(self) -> None:
        for name, value, bound in (
            ("min_lat", self.min_lat, 90),
            ("max_lat", self.max_lat, 90),
            ("min_lon", self.min_lon, 180),
            ("max_lon", self.max_lon, 180),
        ):
            if not math.isfinite(value) or not -bound <= value <= bound:
                raise ValueError(f"{name} must be finite and between {-bound} and {bound}")
        if self.min_lat >= self.max_lat or self.min_lon >= self.max_lon:
            raise ValueError("min_lat must be less than max_lat and min_lon must be less than max_lon")
        if isinstance(self.page, bool) or not isinstance(self.page, int) or self.page < 1:
            raise ValueError("page must be an integer greater than or equal to 1")
        self.cuisine = self.cuisine.strip()
        if self.cuisine != "焼き鳥":
            raise ValueError("Map search currently supports only cuisine='焼き鳥'")

    def _build_params(self) -> dict[str, str]:
        return {
            "minLat": str(self.min_lat),
            "maxLat": str(self.max_lat),
            "minLon": str(self.min_lon),
            "maxLon": str(self.max_lon),
            "cat0": "RC",
            "cat1": "RC01",
            "cat2": "RC0106",
            "cat3": "RC010601",
            "pg": str(self.page),
            "lst": str(MAP_PAGE_SIZE),
            "SrtT": "rt",
        }

    def _parse(self, xml: str) -> MapSearchResult:
        root, info, total = _parse_document(xml)
        markers = root.findall("marker")
        if len(markers) > MAP_PAGE_SIZE or total < len(markers):
            raise ParseError("Map response has inconsistent result counts")
        items: list[MapRestaurant] = []
        seen: set[str] = set()
        for marker in markers:
            try:
                item = _parse_marker(marker)
                if item.restaurant_id in seen:
                    continue
            except (KeyError, ValueError):
                continue
            items.append(item)
            seen.add(item.restaurant_id)
        if markers and not items:
            raise ParseError("Map response contains no valid restaurant markers")
        skipped = len(markers) - len(items)
        warnings = list(MAP_WARNINGS)
        if skipped:
            warnings.append(f"Skipped {skipped} malformed or duplicate map markers; total_count is unchanged.")
        return MapSearchResult(
            items=items,
            total_count=total,
            page=self.page,
            upstream_count=len(markers),
            has_next_page=bool(info.get("nextpg", "").strip()),
            has_prev_page=bool(info.get("prevpg", "").strip()),
            source_params=self._build_params(),
            skipped_count=skipped,
            warnings=warnings,
        )

    def search_sync(self) -> MapSearchResult:
        response = requests.get(
            MAP_SEARCH_URL, params=self._build_params(), timeout=30.0, impersonate=DEFAULT_IMPERSONATE
        )
        response.raise_for_status()
        return self._parse(response.text)

    async def search(self) -> MapSearchResult:
        async with requests.AsyncSession(timeout=30.0, impersonate=DEFAULT_IMPERSONATE) as client:
            response = await client.get(MAP_SEARCH_URL, params=self._build_params())
            response.raise_for_status()
            return self._parse(response.text)


def _parse_document(xml: str) -> tuple[ET.Element, ET.Element, int]:
    # ElementTree expands internal entities; these are never needed by this API.
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ParseError("Map response must not contain XML document types or entities")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ParseError("Tabelog returned invalid map XML, possibly an access challenge") from error
    info = root.find("srchinfo")
    if root.tag != "markers" or info is None:
        raise ParseError("Tabelog returned an unexpected map response, possibly an access challenge")
    try:
        total = int(info.attrib["cnt"])
        if total < 0:
            raise ValueError("negative total")
    except (KeyError, ValueError) as error:
        raise ParseError("Map response has an invalid total count") from error
    return root, info, total


def _optional_text(marker: ET.Element, key: str) -> str | None:
    value = marker.get(key, "").strip()
    return None if value in ("", "－", "-", "—") else value


def _parse_marker(marker: ET.Element) -> MapRestaurant:
    name = marker.attrib["rstname"].strip()
    restaurant_id = marker.attrib["id"]
    path = marker.attrib["rsturl"]
    match = RESTAURANT_PATH.fullmatch(path)
    if not name or not restaurant_id.isdecimal() or match is None or match[1] != restaurant_id:
        raise ValueError("Invalid map restaurant identity or URL")
    latitude = float(marker.attrib["lat"])
    longitude = float(marker.attrib["lng"])
    if not math.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("Invalid marker latitude")
    if not math.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError("Invalid marker longitude")
    score = _optional_text(marker, "score")
    rating = float(score) if score is not None else None
    if rating is not None and (not math.isfinite(rating) or not 0 <= rating <= 5):
        raise ValueError("Invalid marker rating")
    count = _optional_text(marker, "rvwcnt")
    review_count = int(count) if count is not None else None
    if review_count is not None and review_count < 0:
        raise ValueError("Invalid marker review count")
    return MapRestaurant(
        restaurant=Restaurant(
            name=name,
            url=f"https://tabelog.com{path}",
            rating=rating or None,
            review_count=review_count,
            genres=[genre.strip() for genre in marker.get("rstcat", "").split("、") if genre.strip()],
            station=_optional_text(marker, "station_name"),
            closed_days=_optional_text(marker, "holiday"),
        ),
        restaurant_id=restaurant_id,
        latitude=latitude,
        longitude=longitude,
        prefecture_code=_optional_text(marker, "pcd"),
        price_range1=_optional_text(marker, "price_range1"),
        price_range2=_optional_text(marker, "price_range2"),
    )
