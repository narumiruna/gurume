"""地區名稱到 URL slug 的映射"""

from __future__ import annotations

# 都道府縣映射
PREFECTURE_MAPPING = {
    # 北海道・東北
    "北海道": "hokkaido",
    "青森県": "aomori",
    "岩手県": "iwate",
    "宮城県": "miyagi",
    "秋田県": "akita",
    "山形県": "yamagata",
    "福島県": "fukushima",
    # 関東
    "茨城県": "ibaraki",
    "栃木県": "tochigi",
    "群馬県": "gunma",
    "埼玉県": "saitama",
    "千葉県": "chiba",
    "東京都": "tokyo",
    "神奈川県": "kanagawa",
    # 中部
    "新潟県": "niigata",
    "富山県": "toyama",
    "石川県": "ishikawa",
    "福井県": "fukui",
    "山梨県": "yamanashi",
    "長野県": "nagano",
    "岐阜県": "gifu",
    "静岡県": "shizuoka",
    "愛知県": "aichi",
    # 近畿
    "三重県": "mie",
    "滋賀県": "shiga",
    "京都府": "kyoto",
    "大阪府": "osaka",
    "兵庫県": "hyogo",
    "奈良県": "nara",
    "和歌山県": "wakayama",
    # 中国
    "鳥取県": "tottori",
    "島根県": "shimane",
    "岡山県": "okayama",
    "広島県": "hiroshima",
    "山口県": "yamaguchi",
    # 四国
    "徳島県": "tokushima",
    "香川県": "kagawa",
    "愛媛県": "ehime",
    "高知県": "kochi",
    # 九州・沖縄
    "福岡県": "fukuoka",
    "佐賀県": "saga",
    "長崎県": "nagasaki",
    "熊本県": "kumamoto",
    "大分県": "oita",
    "宮崎県": "miyazaki",
    "鹿児島県": "kagoshima",
    "沖縄県": "okinawa",
}

# 主要都市映射（不含"都"、"府"、"県"的版本）
CITY_MAPPING = {
    "東京": "tokyo",
    "大阪": "osaka",
    "京都": "kyoto",
    "北海道": "hokkaido",
    "福岡": "fukuoka",
}


def get_area_slug(area_name: str) -> str | None:
    """
    將地區名稱轉換為 Tabelog URL slug

    Args:
        area_name: 地區名稱（例如："東京都"、"東京"、"大阪府"）

    Returns:
        URL slug（例如："tokyo"）或 None（如果找不到映射）
    """
    # 先檢查完整名稱
    if area_name in PREFECTURE_MAPPING:
        return PREFECTURE_MAPPING[area_name]

    # 檢查城市名稱
    if area_name in CITY_MAPPING:
        return CITY_MAPPING[area_name]

    # 移除"都"、"府"、"県"、"市"等後綴再試一次
    for suffix in ["都", "府", "県", "市"]:
        if area_name.endswith(suffix):
            base_name = area_name[: -len(suffix)]
            if base_name in PREFECTURE_MAPPING:
                return PREFECTURE_MAPPING[base_name]
            if base_name in CITY_MAPPING:
                return CITY_MAPPING[base_name]

    return None
