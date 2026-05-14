"""Map cuisine names to genre codes and search path segments."""

from __future__ import annotations

# Tabelog cuisine genre codes (RC = Restaurant Category).
# Format: cuisine name -> URL code.
GENRE_CODE_MAPPING = {
    # Japanese cuisine.
    "すき焼き": "RC0107",
    "しゃぶしゃぶ": "RC0106",
    "寿司": "RC0201",
    "天ぷら": "RC0301",
    "とんかつ": "RC0302",
    "焼き鳥": "RC0401",
    "ラーメン": "RC0501",
    "うどん": "RC0601",
    "そば": "RC0602",
    "うなぎ": "RC0701",
    "日本料理": "RC0801",
    "海鮮": "RC0901",
    # Western-style cuisine.
    "フレンチ": "RC1001",
    "イタリアン": "RC1101",
    "ステーキ": "RC1201",
    "ハンバーグ": "RC1202",
    "ハンバーガー": "RC1203",
    "洋食": "RC1301",
    # Chinese cuisine.
    "中華料理": "RC1401",
    "餃子": "RC1402",
    # Yakiniku.
    "焼肉": "RC1501",
    "ホルモン": "RC1502",
    # Hot pot.
    "鍋": "RC1601",
    "もつ鍋": "RC1602",
    # Izakaya.
    "居酒屋": "RC1701",
    # Curry.
    "カレー": "RC1801",
    # Other.
    "カフェ": "RC1901",
    "パン": "RC2001",
    "スイーツ": "RC2101",
}

# Current Tabelog search pages encode cuisine filters in URL path segments instead of the legacy LstG query.
# Most cuisines use SEO slugs, but some live search pages still use category-code path segments.
CUISINE_SLUG_MAPPING = {
    "すき焼き": "RC0107",
    "しゃぶしゃぶ": "syabusyabu",
    "寿司": "sushi",
    "天ぷら": "tempura",
    "とんかつ": "tonkatsu",
    "焼き鳥": "yakitori",
    "ラーメン": "MC0101",
    "うどん": "udon",
    "そば": "soba",
    "うなぎ": "unagi",
    "日本料理": "japanese",
    "海鮮": "seafood",
    "フレンチ": "french",
    "イタリアン": "italian",
    "ステーキ": "steak",
    "ハンバーグ": "hamburgersteak",
    "ハンバーガー": "hamburger",
    "洋食": "yoshoku",
    "中華料理": "chinese",
    "餃子": "gyouza",
    "焼肉": "yakiniku",
    "ホルモン": "horumon",
    "鍋": "nabe",
    "もつ鍋": "motsu",
    "居酒屋": "izakaya",
    "カレー": "curry",
    "カフェ": "cafe",
    "パン": "pan",
    "スイーツ": "sweets",
}


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
