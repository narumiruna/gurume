from __future__ import annotations

import contextlib
from dataclasses import dataclass
from dataclasses import field
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .exceptions import InvalidParameterError
from .restaurant import Restaurant

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)
DETAIL_PARSE_EXCEPTIONS = (AttributeError, TypeError, ValueError)


@dataclass
class Review:
    """評論資訊"""

    reviewer: str
    content: str
    rating: float | None = None
    visit_date: str | None = None
    title: str | None = None
    helpful_count: int | None = None


@dataclass
class MenuItem:
    """菜單項目"""

    name: str
    price: str | None = None
    description: str | None = None
    category: str | None = None


@dataclass
class Course:
    """套餐資訊"""

    name: str
    price: str | None = None
    description: str | None = None
    items: list[str] = field(default_factory=list)


@dataclass
class RestaurantDetail:
    """餐廳詳細資訊"""

    restaurant: Restaurant
    reviews: list[Review] = field(default_factory=list)
    menu_items: list[MenuItem] = field(default_factory=list)
    courses: list[Course] = field(default_factory=list)


@dataclass
class RestaurantDetailRequest:
    """餐廳詳細資訊請求"""

    restaurant_url: str
    fetch_reviews: bool = True
    fetch_menu: bool = True
    fetch_courses: bool = True
    max_review_pages: int = 1

    def __post_init__(self) -> None:
        if not self.restaurant_url:
            raise InvalidParameterError("restaurant_url 不能為空")

        if not self.restaurant_url.startswith("https://tabelog.com/"):
            raise InvalidParameterError(f"restaurant_url 必須是 Tabelog URL。收到：{self.restaurant_url}")

        if self.max_review_pages < 1:
            raise InvalidParameterError(f"max_review_pages 必須 >= 1。收到：{self.max_review_pages}")

    def _get_base_url(self) -> str:
        """取得餐廳基礎 URL (移除尾部斜線和查詢參數)"""
        url = self.restaurant_url
        if "?" in url:
            url = url.split("?")[0]
        return url.rstrip("/")

    def _parse_reviews(self, html: str) -> list[Review]:
        """解析評論資訊"""
        soup = BeautifulSoup(html, "lxml")
        reviews = []

        review_items = soup.find_all("div", class_="rvw-item")

        for item in review_items:
            try:
                review = self._parse_review(item)
                if review is not None:
                    reviews.append(review)
            except DETAIL_PARSE_EXCEPTIONS:
                continue

        return reviews

    def _parse_menu_items(self, html: str) -> list[MenuItem]:
        """解析菜單項目"""
        soup = BeautifulSoup(html, "lxml")
        menu_items = []

        # 查找所有菜單分類
        menu_sections = soup.find_all("div", class_="c-offerlist-item")

        for section in menu_sections:
            category = self._get_text(section.find("h4"))
            for item_elem in section.find_all("dl"):
                with contextlib.suppress(*DETAIL_PARSE_EXCEPTIONS):
                    menu_item = self._parse_menu_item(item_elem, category)
                    if menu_item is not None:
                        menu_items.append(menu_item)

        return menu_items

    def _parse_courses(self, html: str) -> list[Course]:
        """解析套餐資訊"""
        soup = BeautifulSoup(html, "lxml")
        courses = []

        # 查找所有套餐
        course_items = soup.find_all("div", class_="c-offerlist-item")

        for item in course_items:
            with contextlib.suppress(*DETAIL_PARSE_EXCEPTIONS):
                course = self._parse_course(item)
                if course is not None:
                    courses.append(course)

        return courses

    def _parse_review(self, item: Any) -> Review | None:
        reviewer = self._get_required_text(item.find("a", class_="rvw-item__rvwr-name"))
        content = self._get_required_text(item.find("div", class_="rvw-item__rvw-comment"))
        return Review(
            reviewer=reviewer,
            content=content,
            rating=self._parse_float(item.find("span", class_="c-rating__val")),
            visit_date=self._get_text(item.find("p", class_="rvw-item__date")),
            title=self._get_text(item.find("p", class_="rvw-item__rvw-title")),
            helpful_count=self._parse_int(item.find("em", class_="rvw-item__usefulpost-count")),
        )

    def _parse_menu_item(self, item_elem: Any, category: str | None) -> MenuItem | None:
        name = self._get_required_text(item_elem.find("dt"))
        return MenuItem(
            name=name,
            price=self._get_text(item_elem.find("dd")),
            category=category,
        )

    def _parse_course(self, item: Any) -> Course | None:
        name = self._get_required_text(item.find("h4"))
        items = []
        items_elem = item.find("ul")
        if items_elem:
            items = [item_text for element in items_elem.find_all("li") if (item_text := element.get_text(strip=True))]

        return Course(
            name=name,
            price=self._get_text(item.find("p", class_="c-offerlist-item__price")),
            description=self._get_text(item.find("p", class_="c-offerlist-item__comment")),
            items=items,
        )

    def _get_text(self, element: Any) -> str | None:
        return element.get_text(strip=True) if element else None

    def _get_required_text(self, element: Any) -> str:
        text = self._get_text(element)
        if text is None:
            raise ValueError("required element missing")
        return text

    def _parse_float(self, element: Any) -> float | None:
        if not element:
            return None
        with contextlib.suppress(ValueError):
            return float(element.get_text(strip=True))
        return None

    def _parse_int(self, element: Any) -> int | None:
        if not element:
            return None
        with contextlib.suppress(ValueError):
            return int(element.get_text(strip=True))
        return None

    def fetch_sync(self) -> RestaurantDetail:
        """同步抓取餐廳詳細資訊"""
        headers = {"User-Agent": USER_AGENT}

        base_url = self._get_base_url()

        # 抓取基本資訊 (從餐廳主頁)
        # TODO: 可以從主頁解析更多基本資訊
        # 暫時使用空的 Restaurant 物件
        restaurant = Restaurant(name="", url=base_url)

        reviews = []
        menu_items = []
        courses = []

        # 抓取評論
        if self.fetch_reviews:
            for page in range(1, self.max_review_pages + 1):
                review_url = f"{base_url}/dtlrvwlst/"
                if page > 1:
                    review_url += f"?PG={page}"

                resp = httpx.get(review_url, headers=headers, timeout=30.0, follow_redirects=True)
                resp.raise_for_status()
                reviews.extend(self._parse_reviews(resp.text))

        # 抓取菜單
        if self.fetch_menu:
            menu_url = f"{base_url}/dtlmenu/"
            resp = httpx.get(menu_url, headers=headers, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            menu_items = self._parse_menu_items(resp.text)

        # 抓取套餐
        if self.fetch_courses:
            course_url = f"{base_url}/party/"
            resp = httpx.get(course_url, headers=headers, timeout=30.0, follow_redirects=True)
            resp.raise_for_status()
            courses = self._parse_courses(resp.text)

        return RestaurantDetail(
            restaurant=restaurant,
            reviews=reviews,
            menu_items=menu_items,
            courses=courses,
        )

    async def fetch(self) -> RestaurantDetail:
        """異步抓取餐廳詳細資訊"""
        headers = {"User-Agent": USER_AGENT}

        base_url = self._get_base_url()

        # 抓取基本資訊 (從餐廳主頁)
        # TODO: 可以從主頁解析更多基本資訊
        # 暫時使用空的 Restaurant 物件
        restaurant = Restaurant(name="", url=base_url)

        reviews = []
        menu_items = []
        courses = []

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # 抓取評論
            if self.fetch_reviews:
                for page in range(1, self.max_review_pages + 1):
                    review_url = f"{base_url}/dtlrvwlst/"
                    if page > 1:
                        review_url += f"?PG={page}"

                    resp = await client.get(review_url, headers=headers)
                    resp.raise_for_status()
                    reviews.extend(self._parse_reviews(resp.text))

            # 抓取菜單
            if self.fetch_menu:
                menu_url = f"{base_url}/dtlmenu/"
                resp = await client.get(menu_url, headers=headers)
                resp.raise_for_status()
                menu_items = self._parse_menu_items(resp.text)

            # 抓取套餐
            if self.fetch_courses:
                course_url = f"{base_url}/party/"
                resp = await client.get(course_url, headers=headers)
                resp.raise_for_status()
                courses = self._parse_courses(resp.text)

        return RestaurantDetail(
            restaurant=restaurant,
            reviews=reviews,
            menu_items=menu_items,
            courses=courses,
        )
