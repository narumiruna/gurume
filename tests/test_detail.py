from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from tabelog import Course
from tabelog import MenuItem
from tabelog import RestaurantDetail
from tabelog import RestaurantDetailRequest
from tabelog import Review
from tabelog.exceptions import InvalidParameterError


class TestReviewModel:
    def test_review_creation(self):
        review = Review(
            reviewer="測試評論者",
            content="很好吃的餐廳",
            rating=4.5,
            visit_date="2023/09訪問1回目",
            title="超棒的體驗",
            helpful_count=10,
        )

        assert review.reviewer == "測試評論者"
        assert review.content == "很好吃的餐廳"
        assert review.rating == 4.5
        assert review.visit_date == "2023/09訪問1回目"
        assert review.title == "超棒的體驗"
        assert review.helpful_count == 10

    def test_review_with_optional_fields(self):
        review = Review(
            reviewer="測試評論者",
            content="很好吃的餐廳",
        )

        assert review.reviewer == "測試評論者"
        assert review.content == "很好吃的餐廳"
        assert review.rating is None
        assert review.visit_date is None
        assert review.title is None
        assert review.helpful_count is None


class TestMenuItemModel:
    def test_menu_item_creation(self):
        item = MenuItem(
            name="天婦羅",
            price="2,500円",
            description="新鮮的海鮮天婦羅",
            category="一品",
        )

        assert item.name == "天婦羅"
        assert item.price == "2,500円"
        assert item.description == "新鮮的海鮮天婦羅"
        assert item.category == "一品"

    def test_menu_item_with_optional_fields(self):
        item = MenuItem(name="天婦羅")

        assert item.name == "天婦羅"
        assert item.price is None
        assert item.description is None
        assert item.category is None


class TestCourseModel:
    def test_course_creation(self):
        course = Course(
            name="豪華套餐",
            price="10,000円",
            description="最高級的食材",
            items=["前菜", "主菜", "甜點"],
        )

        assert course.name == "豪華套餐"
        assert course.price == "10,000円"
        assert course.description == "最高級的食材"
        assert len(course.items) == 3

    def test_course_with_default_items(self):
        course = Course(name="基本套餐")

        assert course.name == "基本套餐"
        assert course.items == []


class TestRestaurantDetailModel:
    def test_restaurant_detail_creation(self):
        from tabelog import Restaurant

        restaurant = Restaurant(name="測試餐廳", url="https://tabelog.com/test/")
        reviews = [Review(reviewer="評論者", content="好吃")]
        menu_items = [MenuItem(name="天婦羅")]
        courses = [Course(name="套餐")]

        detail = RestaurantDetail(
            restaurant=restaurant,
            reviews=reviews,
            menu_items=menu_items,
            courses=courses,
        )

        assert detail.restaurant.name == "測試餐廳"
        assert len(detail.reviews) == 1
        assert len(detail.menu_items) == 1
        assert len(detail.courses) == 1


class TestRestaurantDetailRequest:
    def test_valid_url(self):
        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/")
        assert request.restaurant_url == "https://tabelog.com/tokyo/A1307/A130704/13053564/"

    def test_empty_url_raises_error(self):
        with pytest.raises(InvalidParameterError, match="restaurant_url 不能為空"):
            RestaurantDetailRequest(restaurant_url="")

    def test_invalid_url_raises_error(self):
        with pytest.raises(InvalidParameterError, match="restaurant_url 必須是 Tabelog URL"):
            RestaurantDetailRequest(restaurant_url="https://example.com/restaurant/")

    def test_invalid_max_review_pages(self):
        with pytest.raises(InvalidParameterError, match="max_review_pages 必須 >= 1"):
            RestaurantDetailRequest(
                restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
                max_review_pages=0,
            )

    def test_get_base_url(self):
        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/")
        base_url = request._get_base_url()
        assert base_url == "https://tabelog.com/tokyo/A1307/A130704/13053564"

    def test_get_base_url_with_query(self):
        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/?page=2")
        base_url = request._get_base_url()
        assert base_url == "https://tabelog.com/tokyo/A1307/A130704/13053564"

    def test_parse_reviews(self):
        html = """
        <html>
            <body>
                <div class="rvw-item">
                    <a class="rvw-item__rvwr-name">測試評論者</a>
                    <div class="rvw-item__rvw-comment">很好吃的餐廳</div>
                    <span class="c-rating__val">4.5</span>
                    <p class="rvw-item__date">2023/09訪問1回目</p>
                    <p class="rvw-item__rvw-title">超棒的體驗</p>
                    <em class="rvw-item__usefulpost-count">10</em>
                </div>
            </body>
        </html>
        """

        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/")
        reviews = request._parse_reviews(html)

        assert len(reviews) == 1
        assert reviews[0].reviewer == "測試評論者"
        assert reviews[0].content == "很好吃的餐廳"
        assert reviews[0].rating == 4.5
        assert reviews[0].visit_date == "2023/09訪問1回目"
        assert reviews[0].title == "超棒的體驗"
        assert reviews[0].helpful_count == 10

    def test_parse_menu_items(self):
        html = """
        <html>
            <body>
                <div class="c-offerlist-item">
                    <h4>一品</h4>
                    <dl>
                        <dt>天婦羅</dt>
                        <dd>2,500円</dd>
                    </dl>
                </div>
            </body>
        </html>
        """

        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/")
        menu_items = request._parse_menu_items(html)

        assert len(menu_items) == 1
        assert menu_items[0].name == "天婦羅"
        assert menu_items[0].price == "2,500円"
        assert menu_items[0].category == "一品"

    def test_parse_courses(self):
        html = """
        <html>
            <body>
                <div class="c-offerlist-item">
                    <h4>豪華套餐</h4>
                    <p class="c-offerlist-item__price">10,000円</p>
                    <p class="c-offerlist-item__comment">最高級的食材</p>
                    <ul>
                        <li>前菜</li>
                        <li>主菜</li>
                        <li>甜點</li>
                    </ul>
                </div>
            </body>
        </html>
        """

        request = RestaurantDetailRequest(restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/")
        courses = request._parse_courses(html)

        assert len(courses) == 1
        assert courses[0].name == "豪華套餐"
        assert courses[0].price == "10,000円"
        assert courses[0].description == "最高級的食材"
        assert len(courses[0].items) == 3

    @patch("httpx.get")
    def test_fetch_sync(self, mock_get):
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = RestaurantDetailRequest(
            restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
            fetch_reviews=True,
            fetch_menu=True,
            fetch_courses=True,
            max_review_pages=1,
        )

        detail = request.fetch_sync()

        assert isinstance(detail, RestaurantDetail)
        assert detail.restaurant.url == "https://tabelog.com/tokyo/A1307/A130704/13053564"
        assert mock_get.call_count == 3

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_fetch_async(self, mock_client):
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        mock_client.return_value = mock_client_instance

        request = RestaurantDetailRequest(
            restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
            fetch_reviews=True,
            fetch_menu=True,
            fetch_courses=True,
            max_review_pages=1,
        )

        detail = await request.fetch()

        assert isinstance(detail, RestaurantDetail)
        assert detail.restaurant.url == "https://tabelog.com/tokyo/A1307/A130704/13053564"
        assert mock_client_instance.get.call_count == 3

    @patch("httpx.get")
    def test_fetch_sync_only_reviews(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = RestaurantDetailRequest(
            restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
            fetch_reviews=True,
            fetch_menu=False,
            fetch_courses=False,
        )

        detail = request.fetch_sync()

        assert isinstance(detail, RestaurantDetail)
        assert mock_get.call_count == 1

    @patch("httpx.get")
    def test_fetch_sync_multiple_review_pages(self, mock_get):
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        request = RestaurantDetailRequest(
            restaurant_url="https://tabelog.com/tokyo/A1307/A130704/13053564/",
            fetch_reviews=True,
            fetch_menu=False,
            fetch_courses=False,
            max_review_pages=3,
        )

        detail = request.fetch_sync()

        assert isinstance(detail, RestaurantDetail)
        assert mock_get.call_count == 3
