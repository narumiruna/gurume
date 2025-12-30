"""Tests for genre mapping (cuisine type to genre code conversion)"""

from gurume.genre_mapping import GENRE_CODE_MAPPING
from gurume.genre_mapping import get_all_genres
from gurume.genre_mapping import get_genre_code
from gurume.genre_mapping import get_genre_name_by_code

# ============================================================================
# Test get_genre_code (cuisine name -> code)
# ============================================================================


def test_get_genre_code_sukiyaki():
    """Test sukiyaki genre code"""
    assert get_genre_code("すき焼き") == "RC0107"


def test_get_genre_code_sushi():
    """Test sushi genre code"""
    assert get_genre_code("寿司") == "RC0201"


def test_get_genre_code_ramen():
    """Test ramen genre code"""
    assert get_genre_code("ラーメン") == "RC0501"


def test_get_genre_code_yakiniku():
    """Test yakiniku genre code"""
    assert get_genre_code("焼肉") == "RC1501"


def test_get_genre_code_izakaya():
    """Test izakaya genre code"""
    assert get_genre_code("居酒屋") == "RC1701"


def test_get_genre_code_all_japanese():
    """Test all Japanese cuisine types"""
    japanese_cuisines = {
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
    }

    for cuisine, expected_code in japanese_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_all_western():
    """Test all Western cuisine types"""
    western_cuisines = {
        "フレンチ": "RC1001",
        "イタリアン": "RC1101",
        "ステーキ": "RC1201",
        "ハンバーグ": "RC1202",
        "ハンバーガー": "RC1203",
        "洋食": "RC1301",
    }

    for cuisine, expected_code in western_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_all_chinese():
    """Test all Chinese cuisine types"""
    chinese_cuisines = {
        "中華料理": "RC1401",
        "餃子": "RC1402",
    }

    for cuisine, expected_code in chinese_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_all_yakiniku():
    """Test all yakiniku-related cuisine types"""
    yakiniku_cuisines = {
        "焼肉": "RC1501",
        "ホルモン": "RC1502",
    }

    for cuisine, expected_code in yakiniku_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_all_nabe():
    """Test all hot pot cuisine types"""
    nabe_cuisines = {
        "鍋": "RC1601",
        "もつ鍋": "RC1602",
    }

    for cuisine, expected_code in nabe_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_all_other():
    """Test all other cuisine types"""
    other_cuisines = {
        "カレー": "RC1801",
        "カフェ": "RC1901",
        "パン": "RC2001",
        "スイーツ": "RC2101",
    }

    for cuisine, expected_code in other_cuisines.items():
        assert get_genre_code(cuisine) == expected_code, f"Failed for {cuisine}"


def test_get_genre_code_unknown_cuisine():
    """Test with unknown cuisine name"""
    assert get_genre_code("存在しない料理") is None
    assert get_genre_code("unknown") is None
    assert get_genre_code("ピザ") is None


def test_get_genre_code_empty_string():
    """Test with empty string"""
    assert get_genre_code("") is None


def test_get_genre_code_case_sensitive():
    """Test that genre code lookup is case-sensitive"""
    # Should not match if case is different
    assert get_genre_code("ラーメン") == "RC0501"
    assert get_genre_code("らーめん") is None  # Wrong case


# ============================================================================
# Test get_genre_name_by_code (code -> cuisine name)
# ============================================================================


def test_get_genre_name_by_code_sukiyaki():
    """Test reverse lookup for sukiyaki"""
    assert get_genre_name_by_code("RC0107") == "すき焼き"


def test_get_genre_name_by_code_sushi():
    """Test reverse lookup for sushi"""
    assert get_genre_name_by_code("RC0201") == "寿司"


def test_get_genre_name_by_code_ramen():
    """Test reverse lookup for ramen"""
    assert get_genre_name_by_code("RC0501") == "ラーメン"


def test_get_genre_name_by_code_all_codes():
    """Test reverse lookup for all genre codes"""
    # Test that every code can be reversed
    for name, code in GENRE_CODE_MAPPING.items():
        reversed_name = get_genre_name_by_code(code)
        assert reversed_name == name, f"Failed to reverse {code} -> {name}"


def test_get_genre_name_by_code_unknown_code():
    """Test with unknown genre code"""
    assert get_genre_name_by_code("RC9999") is None
    assert get_genre_name_by_code("INVALID") is None
    assert get_genre_name_by_code("") is None


def test_get_genre_name_by_code_case_sensitive():
    """Test that code lookup is case-sensitive"""
    assert get_genre_name_by_code("RC0501") == "ラーメン"
    assert get_genre_name_by_code("rc0501") is None  # Wrong case


# ============================================================================
# Test get_all_genres
# ============================================================================


def test_get_all_genres_returns_list():
    """Test that get_all_genres returns a list"""
    genres = get_all_genres()
    assert isinstance(genres, list)
    assert len(genres) > 0


def test_get_all_genres_contains_common_cuisines():
    """Test that common cuisines are in the list"""
    genres = get_all_genres()

    # Check for common cuisines
    assert "すき焼き" in genres
    assert "寿司" in genres
    assert "ラーメン" in genres
    assert "焼肉" in genres
    assert "居酒屋" in genres
    assert "カレー" in genres


def test_get_all_genres_count():
    """Test that we have the expected number of genres"""
    genres = get_all_genres()
    # Should have 29 unique genres based on GENRE_CODE_MAPPING
    assert len(genres) == len(GENRE_CODE_MAPPING)
    assert len(genres) == 29


def test_get_all_genres_sorted():
    """Test that genres are returned in sorted order"""
    genres = get_all_genres()
    assert genres == sorted(genres)


def test_get_all_genres_no_duplicates():
    """Test that there are no duplicate genres"""
    genres = get_all_genres()
    assert len(genres) == len(set(genres))


def test_get_all_genres_all_in_mapping():
    """Test that all returned genres exist in GENRE_CODE_MAPPING"""
    genres = get_all_genres()
    for genre in genres:
        assert genre in GENRE_CODE_MAPPING, f"{genre} not in GENRE_CODE_MAPPING"


# ============================================================================
# Integration Tests
# ============================================================================


def test_roundtrip_all_genres():
    """Test that all genres can be converted to code and back"""
    for original_name in get_all_genres():
        # Name -> Code
        code = get_genre_code(original_name)
        assert code is not None, f"No code for {original_name}"

        # Code -> Name
        reversed_name = get_genre_name_by_code(code)
        assert reversed_name == original_name, f"Roundtrip failed for {original_name}"


def test_all_codes_unique():
    """Test that all genre codes are unique"""
    codes = list(GENRE_CODE_MAPPING.values())
    assert len(codes) == len(set(codes)), "Some genre codes are duplicated"


def test_genre_code_format():
    """Test that all genre codes follow the expected format"""
    for code in GENRE_CODE_MAPPING.values():
        assert code.startswith("RC"), f"Code {code} doesn't start with RC"
        assert len(code) == 6, f"Code {code} is not 6 characters"
        assert code[2:].isdigit(), f"Code {code} doesn't end with 4 digits"


def test_mapping_categories():
    """Test that we have cuisines from all major categories"""
    genres = get_all_genres()

    # Japanese
    japanese = ["すき焼き", "寿司", "ラーメン", "うどん", "そば"]
    assert all(g in genres for g in japanese), "Missing Japanese cuisines"

    # Western
    western = ["フレンチ", "イタリアン", "ステーキ"]
    assert all(g in genres for g in western), "Missing Western cuisines"

    # Chinese
    chinese = ["中華料理", "餃子"]
    assert all(g in genres for g in chinese), "Missing Chinese cuisines"

    # Yakiniku
    yakiniku = ["焼肉", "ホルモン"]
    assert all(g in genres for g in yakiniku), "Missing Yakiniku cuisines"

    # Other
    other = ["居酒屋", "カレー", "カフェ"]
    assert all(g in genres for g in other), "Missing other cuisines"


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_genre_mapping_immutability():
    """Test that GENRE_CODE_MAPPING is a dict (not meant to be modified)"""
    assert isinstance(GENRE_CODE_MAPPING, dict)
    # Verify we can read from it
    assert "すき焼き" in GENRE_CODE_MAPPING


def test_get_all_genres_returns_new_list():
    """Test that get_all_genres returns a new list each time"""
    genres1 = get_all_genres()
    genres2 = get_all_genres()

    # Should be equal but not the same object
    assert genres1 == genres2
    assert genres1 is not genres2
