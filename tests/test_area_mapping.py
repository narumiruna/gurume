"""Tests for area mapping (area name to URL slug conversion)"""

from gurume.area_mapping import CITY_MAPPING
from gurume.area_mapping import PREFECTURE_MAPPING
from gurume.area_mapping import get_area_slug

# ============================================================================
# Test get_area_slug with full prefecture names (都/府/県 suffix)
# ============================================================================


def test_get_area_slug_tokyo_full():
    """Test Tokyo with full name"""
    assert get_area_slug("東京都") == "tokyo"


def test_get_area_slug_osaka_full():
    """Test Osaka with full name"""
    assert get_area_slug("大阪府") == "osaka"


def test_get_area_slug_kyoto_full():
    """Test Kyoto with full name"""
    assert get_area_slug("京都府") == "kyoto"


def test_get_area_slug_hokkaido_full():
    """Test Hokkaido with full name"""
    assert get_area_slug("北海道") == "hokkaido"


def test_get_area_slug_mie_full():
    """Test Mie with full name"""
    assert get_area_slug("三重県") == "mie"


def test_get_area_slug_all_47_prefectures():
    """Test all 47 prefectures with full names"""
    for prefecture, expected_slug in PREFECTURE_MAPPING.items():
        result = get_area_slug(prefecture)
        assert result == expected_slug, f"Failed for {prefecture}: expected {expected_slug}, got {result}"


# ============================================================================
# Test get_area_slug with city names (without suffix)
# ============================================================================


def test_get_area_slug_tokyo_city():
    """Test Tokyo without suffix"""
    assert get_area_slug("東京") == "tokyo"


def test_get_area_slug_osaka_city():
    """Test Osaka without suffix"""
    assert get_area_slug("大阪") == "osaka"


def test_get_area_slug_kyoto_city():
    """Test Kyoto without suffix"""
    assert get_area_slug("京都") == "kyoto"


def test_get_area_slug_fukuoka_city():
    """Test Fukuoka without suffix"""
    assert get_area_slug("福岡") == "fukuoka"


def test_get_area_slug_all_major_cities():
    """Test all major cities in CITY_MAPPING"""
    for city, expected_slug in CITY_MAPPING.items():
        result = get_area_slug(city)
        assert result == expected_slug, f"Failed for {city}: expected {expected_slug}, got {result}"


# ============================================================================
# Test get_area_slug with prefecture prefixes
# ============================================================================


def test_get_area_slug_mie_prefix():
    """Test Mie without 県 suffix"""
    assert get_area_slug("三重") == "mie"


def test_get_area_slug_aichi_prefix():
    """Test Aichi without 県 suffix"""
    assert get_area_slug("愛知") == "aichi"


def test_get_area_slug_kanagawa_prefix():
    """Test Kanagawa without 県 suffix"""
    assert get_area_slug("神奈川") == "kanagawa"


def test_get_area_slug_all_prefecture_prefixes():
    """Test all prefectures without 都/府/県 suffix"""
    # Test each prefecture by removing the suffix
    for full_name, expected_slug in PREFECTURE_MAPPING.items():
        # Remove suffix
        for suffix in ["都", "府", "県"]:
            if full_name.endswith(suffix):
                prefix = full_name[: -len(suffix)]
                result = get_area_slug(prefix)
                assert result == expected_slug, (
                    f"Failed for {prefix} (from {full_name}): expected {expected_slug}, got {result}"
                )
                break


# ============================================================================
# Test get_area_slug with 市 suffix
# ============================================================================


def test_get_area_slug_with_shi_suffix():
    """Test area names with 市 suffix"""
    # These should work by stripping the 市 suffix
    assert get_area_slug("東京市") == "tokyo"
    assert get_area_slug("大阪市") == "osaka"


# ============================================================================
# Test get_area_slug with unknown areas
# ============================================================================


def test_get_area_slug_unknown_area():
    """Test with unknown area name"""
    assert get_area_slug("存在しない地域") is None
    assert get_area_slug("Unknown City") is None


def test_get_area_slug_empty_string():
    """Test with empty string"""
    assert get_area_slug("") is None


def test_get_area_slug_invalid_input():
    """Test with various invalid inputs"""
    assert get_area_slug("123") is None
    assert get_area_slug("あいうえお") is None


# ============================================================================
# Test regional coverage
# ============================================================================


def test_get_area_slug_hokkaido_tohoku_region():
    """Test all Hokkaido/Tohoku prefectures"""
    hokkaido_tohoku = [
        ("北海道", "hokkaido"),
        ("青森県", "aomori"),
        ("岩手県", "iwate"),
        ("宮城県", "miyagi"),
        ("秋田県", "akita"),
        ("山形県", "yamagata"),
        ("福島県", "fukushima"),
    ]

    for prefecture, expected in hokkaido_tohoku:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_kanto_region():
    """Test all Kanto prefectures"""
    kanto = [
        ("茨城県", "ibaraki"),
        ("栃木県", "tochigi"),
        ("群馬県", "gunma"),
        ("埼玉県", "saitama"),
        ("千葉県", "chiba"),
        ("東京都", "tokyo"),
        ("神奈川県", "kanagawa"),
    ]

    for prefecture, expected in kanto:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_chubu_region():
    """Test all Chubu prefectures"""
    chubu = [
        ("新潟県", "niigata"),
        ("富山県", "toyama"),
        ("石川県", "ishikawa"),
        ("福井県", "fukui"),
        ("山梨県", "yamanashi"),
        ("長野県", "nagano"),
        ("岐阜県", "gifu"),
        ("静岡県", "shizuoka"),
        ("愛知県", "aichi"),
    ]

    for prefecture, expected in chubu:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_kinki_region():
    """Test all Kinki/Kansai prefectures"""
    kinki = [
        ("三重県", "mie"),
        ("滋賀県", "shiga"),
        ("京都府", "kyoto"),
        ("大阪府", "osaka"),
        ("兵庫県", "hyogo"),
        ("奈良県", "nara"),
        ("和歌山県", "wakayama"),
    ]

    for prefecture, expected in kinki:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_chugoku_region():
    """Test all Chugoku prefectures"""
    chugoku = [
        ("鳥取県", "tottori"),
        ("島根県", "shimane"),
        ("岡山県", "okayama"),
        ("広島県", "hiroshima"),
        ("山口県", "yamaguchi"),
    ]

    for prefecture, expected in chugoku:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_shikoku_region():
    """Test all Shikoku prefectures"""
    shikoku = [
        ("徳島県", "tokushima"),
        ("香川県", "kagawa"),
        ("愛媛県", "ehime"),
        ("高知県", "kochi"),
    ]

    for prefecture, expected in shikoku:
        assert get_area_slug(prefecture) == expected


def test_get_area_slug_kyushu_okinawa_region():
    """Test all Kyushu/Okinawa prefectures"""
    kyushu_okinawa = [
        ("福岡県", "fukuoka"),
        ("佐賀県", "saga"),
        ("長崎県", "nagasaki"),
        ("熊本県", "kumamoto"),
        ("大分県", "oita"),
        ("宮崎県", "miyazaki"),
        ("鹿児島県", "kagoshima"),
        ("沖縄県", "okinawa"),
    ]

    for prefecture, expected in kyushu_okinawa:
        assert get_area_slug(prefecture) == expected


# ============================================================================
# Integration Tests
# ============================================================================


def test_prefecture_mapping_count():
    """Test that we have exactly 47 prefectures"""
    assert len(PREFECTURE_MAPPING) == 47, "Japan should have 47 prefectures"


def test_city_mapping_count():
    """Test that we have the expected number of major cities"""
    assert len(CITY_MAPPING) == 5, "Should have 5 major cities"


def test_all_slugs_lowercase():
    """Test that all slugs are lowercase"""
    for slug in PREFECTURE_MAPPING.values():
        assert slug.islower(), f"Slug {slug} is not lowercase"

    for slug in CITY_MAPPING.values():
        assert slug.islower(), f"Slug {slug} is not lowercase"


def test_all_slugs_ascii():
    """Test that all slugs are ASCII (romaji)"""
    for slug in PREFECTURE_MAPPING.values():
        assert slug.isascii(), f"Slug {slug} is not ASCII"

    for slug in CITY_MAPPING.values():
        assert slug.isascii(), f"Slug {slug} is not ASCII"


def test_no_duplicate_slugs():
    """Test that all prefecture slugs are unique"""
    slugs = list(PREFECTURE_MAPPING.values())
    assert len(slugs) == len(set(slugs)), "Some prefecture slugs are duplicated"


def test_city_mapping_subset_of_prefecture():
    """Test that all cities in CITY_MAPPING are also in PREFECTURE_MAPPING slugs"""
    prefecture_slugs = set(PREFECTURE_MAPPING.values())
    city_slugs = set(CITY_MAPPING.values())

    # All city slugs should also be prefecture slugs
    assert city_slugs.issubset(prefecture_slugs), "Some city slugs are not in prefecture mapping"


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_get_area_slug_case_sensitivity():
    """Test that area names are case-sensitive"""
    # Correct case
    assert get_area_slug("東京都") == "tokyo"

    # These should not match (hypothetical - actual Japanese doesn't have case)
    # Just verify the function works with the exact strings


def test_get_area_slug_whitespace():
    """Test area names with whitespace"""
    # The function doesn't strip whitespace, so these should fail
    assert get_area_slug(" 東京都 ") is None
    assert get_area_slug("東京都 ") is None
    assert get_area_slug(" 東京都") is None


def test_get_area_slug_special_characters():
    """Test area names with special characters"""
    # Only valid Japanese prefecture names should work
    assert get_area_slug("東京都!") is None
    assert get_area_slug("東京-都") is None


def test_get_area_slug_multiple_suffixes():
    """Test that suffix removal works even with extra suffixes"""
    # "東京都府" contains "東京都" which exists in PREFECTURE_MAPPING
    # The function tries removing 府, finds "東京都" in mapping -> returns "tokyo"
    assert get_area_slug("東京都府") == "tokyo"

    # "大阪府県" contains "大阪府" which exists in PREFECTURE_MAPPING
    # The function tries removing 県, finds "大阪府" in mapping -> returns "osaka"
    assert get_area_slug("大阪府県") == "osaka"

    # Test truly invalid names that won't match
    assert get_area_slug("不存在都府県") is None


# ============================================================================
# Lookup Strategy Tests
# ============================================================================


def test_lookup_strategy_priority():
    """Test that lookup follows correct priority order"""
    # Priority: PREFECTURE_MAPPING > CITY_MAPPING > _PREFIX_TO_SLUG

    # Test that full name (PREFECTURE_MAPPING) takes priority
    assert get_area_slug("東京都") == "tokyo"

    # Test that city name (CITY_MAPPING) works
    assert get_area_slug("東京") == "tokyo"

    # Test that prefix lookup works for non-major cities
    assert get_area_slug("三重") == "mie"


def test_suffix_removal_order():
    """Test that suffix removal is tried in correct order"""
    # The function tries: 都, 府, 県, 市
    # All should resolve correctly

    assert get_area_slug("東京都") == "tokyo"  # 都
    assert get_area_slug("大阪府") == "osaka"  # 府
    assert get_area_slug("三重県") == "mie"  # 県
    assert get_area_slug("福岡市") == "fukuoka"  # 市


def test_hokkaido_special_case():
    """Test Hokkaido which doesn't have 都/府/県 suffix"""
    # Hokkaido is unique - it's already without suffix
    assert get_area_slug("北海道") == "hokkaido"
    assert get_area_slug("北海") is None  # Removing 道 should not work
