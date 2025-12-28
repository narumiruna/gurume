import pytest

from tabelog.exceptions import InvalidParameterError
from tabelog.restaurant import PriceRange
from tabelog.restaurant import Restaurant
from tabelog.restaurant import RestaurantSearchRequest
from tabelog.restaurant import SortType


class TestRestaurant:
    """Test Restaurant model"""

    def test_restaurant_creation(self):
        """Test creating a Restaurant instance"""
        restaurant = Restaurant(
            name="テストレストラン",
            url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
            rating=4.5,
            review_count=123,
            area="銀座",
            genres=["寿司", "日本料理"],
        )

        assert restaurant.name == "テストレストラン"
        assert restaurant.rating == 4.5
        assert restaurant.review_count == 123
        assert restaurant.area == "銀座"
        assert restaurant.genres == ["寿司", "日本料理"]
        assert restaurant.has_vpoint is False
        assert restaurant.has_reservation is False

    def test_restaurant_minimal_creation(self):
        """Test creating a Restaurant with minimal required fields"""
        restaurant = Restaurant(
            name="テストレストラン",
            url="https://tabelog.com/tokyo/A1301/A130101/13000001/",
        )

        assert restaurant.name == "テストレストラン"
        assert restaurant.rating is None
        assert restaurant.review_count is None
        assert restaurant.genres == []
        assert restaurant.image_urls == []


class TestRestaurantSearchRequest:
    """Test RestaurantSearchRequest model"""

    def test_basic_search_request(self):
        """Test basic search request creation"""
        request = RestaurantSearchRequest(
            area="銀座",
            keyword="寿司",
            party_size=2,
        )

        assert request.area == "銀座"
        assert request.keyword == "寿司"
        assert request.party_size == 2
        assert request.sort_type == SortType.STANDARD
        assert request.page == 1

    def test_advanced_search_request(self):
        """Test advanced search request with all parameters"""
        request = RestaurantSearchRequest(
            area="渋谷",
            keyword="焼肉",
            reservation_date="20250715",
            reservation_time="1900",
            party_size=4,
            sort_type=SortType.RANKING,
            price_range=PriceRange.DINNER_4000_5000,
            online_booking_only=True,
            has_private_room=True,
            has_parking=True,
            smoking_allowed=True,
            card_accepted=True,
        )

        assert request.area == "渋谷"
        assert request.keyword == "焼肉"
        assert request.reservation_date == "20250715"
        assert request.reservation_time == "1900"
        assert request.party_size == 4
        assert request.sort_type == SortType.RANKING
        assert request.price_range == PriceRange.DINNER_4000_5000
        assert request.online_booking_only is True
        assert request.has_private_room is True

    def test_whitespace_stripping(self):
        """Test whitespace stripping in area and keyword"""
        request = RestaurantSearchRequest(
            area="  銀座  ",
            keyword="  寿司  ",
        )

        assert request.area == "銀座"
        assert request.keyword == "寿司"

    def test_none_values(self):
        """Test handling of None values"""
        request = RestaurantSearchRequest(
            area=None,
            keyword=None,
        )

        assert request.area is None
        assert request.keyword is None

    def test_date_validation(self):
        """Test reservation date validation (dataclass version)"""
        # Valid date
        request = RestaurantSearchRequest(reservation_date="20250715")
        assert request.reservation_date == "20250715"

        # Invalid date format should raise InvalidParameterError
        with pytest.raises(InvalidParameterError):
            RestaurantSearchRequest(reservation_date="2025-07-15")

        with pytest.raises(InvalidParameterError):
            RestaurantSearchRequest(reservation_date="invalid")

    def test_time_validation(self):
        """Test reservation time validation (dataclass version)"""
        # Valid time
        request = RestaurantSearchRequest(reservation_time="1900")
        assert request.reservation_time == "1900"

        # Invalid time format should raise InvalidParameterError
        with pytest.raises(InvalidParameterError):
            RestaurantSearchRequest(reservation_time="19:00")

        with pytest.raises(InvalidParameterError):
            RestaurantSearchRequest(reservation_time="invalid")

    def test_build_params(self):
        """Test building search parameters"""
        request = RestaurantSearchRequest(
            area="銀座",
            keyword="寿司",
            reservation_date="20250715",
            reservation_time="1900",
            party_size=2,
            sort_type=SortType.RANKING,
            price_range=PriceRange.DINNER_4000_5000,
            online_booking_only=True,
            has_private_room=True,
        )

        params = request._build_params()

        assert params["sa"] == "銀座"
        assert params["sk"] == "寿司"
        assert params["svd"] == "20250715"
        assert params["svt"] == "1900"
        assert int(params["svps"]) == 2
        assert params["SrtT"] == "rt"
        assert int(params["PG"]) == 1
        assert params["LstCos"] == "C005"
        assert params["ChkOnlineBooking"] == "1"
        assert params["ChkRoom"] == "1"

    def test_build_params_minimal(self):
        """Test building minimal search parameters"""
        request = RestaurantSearchRequest()
        params = request._build_params()

        assert params["SrtT"] == "trend"
        assert int(params["PG"]) == 1
        assert "sa" not in params
        assert "sk" not in params


class TestEnums:
    """Test enum values"""

    def test_sort_type_enum(self):
        """Test SortType enum"""
        assert SortType.STANDARD == "trend"
        assert SortType.RANKING == "rt"
        assert SortType.REVIEW_COUNT == "rvcn"
        assert SortType.NEW_OPEN == "nod"

    def test_price_range_enum(self):
        """Test PriceRange enum"""
        assert PriceRange.LUNCH_UNDER_1000 == "B001"
        assert PriceRange.LUNCH_1000_2000 == "B002"
        assert PriceRange.DINNER_UNDER_1000 == "C001"
        assert PriceRange.DINNER_4000_5000 == "C005"
        assert PriceRange.DINNER_OVER_30000 == "C012"
