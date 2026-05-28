"""Map area names to Tabelog URL slugs."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import cache
from importlib import resources
from typing import Any
from typing import Literal
from typing import cast

AreaLevel = Literal["subarea"]

_AREA_CATALOG_RESOURCE = "data/area_catalog.json"
_AREA_PATH_RE = re.compile(r"^[a-z]+(?:/A\d+){1,2}$")
_REQUIRED_CATALOG_KEYS = frozenset({"name", "path", "level", "parent", "aliases", "source", "verified_at"})
_SUPPORTED_AREA_LEVELS: set[str] = {"subarea"}


@dataclass(frozen=True)
class AreaCatalogEntry:
    """Validated Tabelog area catalog row."""

    name: str
    path: str
    level: AreaLevel
    parent: str
    aliases: tuple[str, ...]
    source: str
    verified_at: str


# Prefecture mapping.
PREFECTURE_MAPPING = {
    # Hokkaido and Tohoku.
    "北海道": "hokkaido",
    "青森県": "aomori",
    "岩手県": "iwate",
    "宮城県": "miyagi",
    "秋田県": "akita",
    "山形県": "yamagata",
    "福島県": "fukushima",
    # Kanto.
    "茨城県": "ibaraki",
    "栃木県": "tochigi",
    "群馬県": "gunma",
    "埼玉県": "saitama",
    "千葉県": "chiba",
    "東京都": "tokyo",
    "神奈川県": "kanagawa",
    # Chubu.
    "新潟県": "niigata",
    "富山県": "toyama",
    "石川県": "ishikawa",
    "福井県": "fukui",
    "山梨県": "yamanashi",
    "長野県": "nagano",
    "岐阜県": "gifu",
    "静岡県": "shizuoka",
    "愛知県": "aichi",
    # Kinki.
    "三重県": "mie",
    "滋賀県": "shiga",
    "京都府": "kyoto",
    "大阪府": "osaka",
    "兵庫県": "hyogo",
    "奈良県": "nara",
    "和歌山県": "wakayama",
    # Chugoku.
    "鳥取県": "tottori",
    "島根県": "shimane",
    "岡山県": "okayama",
    "広島県": "hiroshima",
    "山口県": "yamaguchi",
    # Shikoku.
    "徳島県": "tokushima",
    "香川県": "kagawa",
    "愛媛県": "ehime",
    "高知県": "kochi",
    # Kyushu and Okinawa.
    "福岡県": "fukuoka",
    "佐賀県": "saga",
    "長崎県": "nagasaki",
    "熊本県": "kumamoto",
    "大分県": "oita",
    "宮崎県": "miyazaki",
    "鹿児島県": "kagoshima",
    "沖縄県": "okinawa",
}

# Major city mapping without prefecture suffixes.
CITY_MAPPING = {
    "東京": "tokyo",
    "大阪": "osaka",
    "京都": "kyoto",
    "北海道": "hokkaido",
    "福岡": "fukuoka",
}

# City-level Tabelog paths. Prefecture-only slugs return overly broad cross-city results for these cities.
CITY_AREA_PATH_MAPPING = {
    "札幌": "hokkaido/A0101",
    "名古屋": "aichi/A2301",
    "神戸": "hyogo/A2801",
}

# Reverse lookup from prefecture names without suffixes to slugs.
_PREFIX_TO_SLUG = {}
for full_name, slug in PREFECTURE_MAPPING.items():
    # Remove prefecture suffixes.
    for suffix in ["都", "府", "県"]:
        if full_name.endswith(suffix):
            prefix = full_name[: -len(suffix)]
            _PREFIX_TO_SLUG[prefix] = slug
            break


def _require_non_empty_string(row: dict[str, Any], key: str) -> str:
    value = row[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"area catalog {key} must be a non-empty string")
    return value


def _parse_catalog_aliases(row: dict[str, Any]) -> tuple[str, ...]:
    aliases = row["aliases"]
    if not isinstance(aliases, list):
        raise TypeError("area catalog aliases must be a list")

    parsed_aliases: list[str] = []
    seen_aliases: set[str] = set()
    for alias in aliases:
        if not isinstance(alias, str) or not alias:
            raise ValueError("area catalog aliases must contain non-empty strings")
        if alias in seen_aliases:
            raise ValueError(f"duplicate area catalog alias in row: {alias}")
        seen_aliases.add(alias)
        parsed_aliases.append(alias)
    return tuple(parsed_aliases)


def _parse_catalog_row(row: dict[str, Any]) -> AreaCatalogEntry:
    missing_keys = _REQUIRED_CATALOG_KEYS - row.keys()
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"area catalog row missing required keys: {missing}")

    unexpected_keys = row.keys() - _REQUIRED_CATALOG_KEYS
    if unexpected_keys:
        unexpected = ", ".join(sorted(unexpected_keys))
        raise ValueError(f"area catalog row has unexpected keys: {unexpected}")

    name = _require_non_empty_string(row, "name")
    path = _require_non_empty_string(row, "path")
    level = _require_non_empty_string(row, "level")
    parent = _require_non_empty_string(row, "parent")
    source = _require_non_empty_string(row, "source")
    verified_at = _require_non_empty_string(row, "verified_at")

    if not _AREA_PATH_RE.fullmatch(path):
        raise ValueError(f"area catalog path has unsupported shape: {path}")
    if not _AREA_PATH_RE.fullmatch(parent):
        raise ValueError(f"area catalog parent has unsupported shape: {parent}")
    if level not in _SUPPORTED_AREA_LEVELS:
        raise ValueError(f"area catalog level is unsupported: {level}")
    if not source.startswith("https://tabelog.com/"):
        raise ValueError(f"area catalog source must be a Tabelog URL: {source}")
    try:
        date.fromisoformat(verified_at)
    except ValueError as exc:
        raise ValueError(f"area catalog verified_at must be an ISO date: {verified_at}") from exc

    return AreaCatalogEntry(
        name=name,
        path=path,
        level=cast(AreaLevel, level),
        parent=parent,
        aliases=_parse_catalog_aliases(row),
        source=source,
        verified_at=verified_at,
    )


def parse_area_catalog_rows(data: object) -> tuple[AreaCatalogEntry, ...]:
    """Validate and parse raw area catalog data."""
    if not isinstance(data, list):
        raise TypeError("area catalog must be a list")

    parsed_entries: list[AreaCatalogEntry] = []
    for row in data:
        if not isinstance(row, dict):
            raise TypeError("area catalog rows must be objects")
        parsed_entries.append(_parse_catalog_row(cast(dict[str, Any], row)))
    entries = tuple(parsed_entries)

    seen_names: set[str] = set()
    lookup_keys: dict[str, str] = {}
    for entry in entries:
        if entry.name in seen_names:
            raise ValueError(f"duplicate area catalog name: {entry.name}")
        seen_names.add(entry.name)

        for lookup_key in (entry.name, *entry.aliases):
            if lookup_key in lookup_keys:
                raise ValueError(f"duplicate area catalog lookup key: {lookup_key}")
            lookup_keys[lookup_key] = entry.path

    return entries


@cache
def get_area_catalog_entries() -> tuple[AreaCatalogEntry, ...]:
    """Load and validate packaged Tabelog area catalog data."""
    catalog_text = resources.files("gurume").joinpath(_AREA_CATALOG_RESOURCE).read_text(encoding="utf-8")
    return parse_area_catalog_rows(json.loads(catalog_text))


@cache
def _get_area_catalog_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for entry in get_area_catalog_entries():
        index[entry.name] = entry.path
        for alias in entry.aliases:
            index[alias] = entry.path
    return index


def _lookup_catalog_area_path(area_name: str) -> str | None:
    return _get_area_catalog_index().get(area_name)


def _lookup_area_path(area_name: str) -> str | None:
    if area_name in PREFECTURE_MAPPING:
        return PREFECTURE_MAPPING[area_name]
    if area_name in CITY_MAPPING:
        return CITY_MAPPING[area_name]
    if area_name in CITY_AREA_PATH_MAPPING:
        return CITY_AREA_PATH_MAPPING[area_name]
    if area_name in _PREFIX_TO_SLUG:
        return _PREFIX_TO_SLUG[area_name]
    if catalog_path := _lookup_catalog_area_path(area_name):
        return catalog_path
    return None


def get_area_slug(area_name: str) -> str | None:
    """
    Convert an area name to a Tabelog URL slug or path.

    Args:
        area_name: Area name, for example "東京都", "東京", "大阪府", "三重", or "札幌".

    Returns:
        URL slug/path, for example "tokyo", "mie", or "hokkaido/A0101"; otherwise None.
    """
    # Check full names, city names, city-level paths, and prefecture-name prefixes first.
    area_path = _lookup_area_path(area_name)
    if area_path:
        return area_path

    # Remove prefecture/city suffixes, then try again.
    for suffix in ["都", "府", "県", "市"]:
        if area_name.endswith(suffix):
            return _lookup_area_path(area_name[: -len(suffix)])

    return None
