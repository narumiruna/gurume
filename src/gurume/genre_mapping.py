"""Map cuisine names to genre codes and search path segments."""

from __future__ import annotations

# Tabelog cuisine metadata: cuisine name -> (legacy RC code, current search path segment).
# Current search pages encode cuisine filters in URL paths. Most cuisines use SEO slugs, while some still use
# category-code path segments such as RC0107 or MC0101.
_CUISINE_DEFINITIONS: dict[str, tuple[str, str]] = {
    # Japanese cuisine.
    "すき焼き": ("RC0107", "RC0107"),
    "しゃぶしゃぶ": ("RC0106", "syabusyabu"),
    "寿司": ("RC0201", "sushi"),
    "天ぷら": ("RC0301", "tempura"),
    "とんかつ": ("RC0302", "tonkatsu"),
    "焼き鳥": ("RC0401", "yakitori"),
    "ラーメン": ("RC0501", "MC0101"),
    "うどん": ("RC0601", "udon"),
    "そば": ("RC0602", "soba"),
    "うなぎ": ("RC0701", "unagi"),
    "日本料理": ("RC0801", "japanese"),
    "海鮮": ("RC0901", "seafood"),
    # Western-style cuisine.
    "フレンチ": ("RC1001", "french"),
    "イタリアン": ("RC1101", "italian"),
    "ステーキ": ("RC1201", "steak"),
    "ハンバーグ": ("RC1202", "hamburgersteak"),
    "ハンバーガー": ("RC1203", "hamburger"),
    "洋食": ("RC1301", "yoshoku"),
    # Chinese cuisine.
    "中華料理": ("RC1401", "chinese"),
    "餃子": ("RC1402", "gyouza"),
    # Yakiniku.
    "焼肉": ("RC1501", "yakiniku"),
    "ホルモン": ("RC1502", "horumon"),
    # Hot pot.
    "鍋": ("RC1601", "nabe"),
    "もつ鍋": ("RC1602", "motsu"),
    # Izakaya.
    "居酒屋": ("RC1701", "izakaya"),
    # Curry.
    "カレー": ("RC1801", "curry"),
    # Other.
    "カフェ": ("RC1901", "cafe"),
    "パン": ("RC2001", "pan"),
    "スイーツ": ("RC2101", "sweets"),
}

# Public dictionaries remain independent mutable objects for compatibility.
GENRE_CODE_MAPPING = {name: code for name, (code, _) in _CUISINE_DEFINITIONS.items()}
CUISINE_SLUG_MAPPING = {name: slug for name, (_, slug) in _CUISINE_DEFINITIONS.items()}


def get_genre_code(genre_name: str) -> str | None:
    """
    Convert a cuisine name to a Tabelog URL code.

    Args:
        genre_name: Cuisine name, for example "すき焼き" or "寿司".

    Returns:
        URL code, for example "RC0107"; otherwise None.
    """
    return GENRE_CODE_MAPPING.get(genre_name)


def get_genre_name_by_code(genre_code: str) -> str | None:
    """
    Look up a cuisine name by code.

    Args:
        genre_code: URL code, for example "RC0107".

    Returns:
        Cuisine name, or None.
    """
    for name, code in GENRE_CODE_MAPPING.items():
        if code == genre_code:
            return name
    return None


def get_cuisine_slug(genre_name: str) -> str | None:
    """Get the Tabelog path segment for area + cuisine searches."""
    return CUISINE_SLUG_MAPPING.get(genre_name)


def get_cuisine_slug_by_code(genre_code: str) -> str | None:
    """Look up the current cuisine path segment from a legacy genre code."""
    genre_name = get_genre_name_by_code(genre_code)
    if not genre_name:
        return None
    return get_cuisine_slug(genre_name)


def get_all_genres() -> list[str]:
    """
    Get all supported cuisine names.

    Returns:
        List of cuisine names.
    """
    # Remove duplicates.
    return sorted(set(GENRE_CODE_MAPPING.keys()))
