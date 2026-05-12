"""料理類別代碼與搜尋路徑映射"""

from __future__ import annotations

# Tabelog 料理類別代碼（RC = Restaurant Category）
# 格式：料理名稱 -> URL 代碼
GENRE_CODE_MAPPING = {
    # 和食
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
    # 洋食
    "フレンチ": "RC1001",
    "イタリアン": "RC1101",
    "ステーキ": "RC1201",
    "ハンバーグ": "RC1202",
    "ハンバーガー": "RC1203",
    "洋食": "RC1301",
    # 中華
    "中華料理": "RC1401",
    "餃子": "RC1402",
    # 焼肉
    "焼肉": "RC1501",
    "ホルモン": "RC1502",
    # 鍋
    "鍋": "RC1601",
    "もつ鍋": "RC1602",
    # 居酒屋
    "居酒屋": "RC1701",
    # カレー
    "カレー": "RC1801",
    # その他
    "カフェ": "RC1901",
    "パン": "RC2001",
    "スイーツ": "RC2101",
}

# Tabelog 搜尋頁目前會把料理過濾編碼在 URL path segment，而不是舊的 LstG query。
# 大多數料理使用 SEO slug，但部分料理在實際搜尋頁仍使用分類代碼 path segment。
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
    料理名稱轉換為 Tabelog URL 代碼

    Args:
        genre_name: 料理名稱（例如：「すき焼き」、「寿司」）

    Returns:
        URL 代碼（例如：「RC0107」）或 None（如果找不到映射）
    """
    return GENRE_CODE_MAPPING.get(genre_name)


def get_genre_name_by_code(genre_code: str) -> str | None:
    """
    從代碼反查料理名稱

    Args:
        genre_code: URL 代碼（例如：「RC0107」）

    Returns:
        料理名稱或 None
    """
    for name, code in GENRE_CODE_MAPPING.items():
        if code == genre_code:
            return name
    return None


def get_cuisine_slug(genre_name: str) -> str | None:
    """取得 area + cuisine 搜尋用的 Tabelog path segment。"""
    return CUISINE_SLUG_MAPPING.get(genre_name)


def get_cuisine_slug_by_code(genre_code: str) -> str | None:
    """從舊版 genre code 反查目前可用的 cuisine path segment。"""
    genre_name = get_genre_name_by_code(genre_code)
    if not genre_name:
        return None
    return get_cuisine_slug(genre_name)


def get_all_genres() -> list[str]:
    """
    取得所有支援的料理類別名稱

    Returns:
        料理類別名稱清單
    """
    # 去除重複項目
    return sorted(set(GENRE_CODE_MAPPING.keys()))
