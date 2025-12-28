from __future__ import annotations

import contextlib
from dataclasses import dataclass
from dataclasses import field

import httpx
from bs4 import BeautifulSoup

from .exceptions import InvalidParameterError
from .restaurant import Restaurant


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

    def __post_init__(self):
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
                # 評論者名稱
                reviewer_elem = item.find("a", class_="rvw-item__rvwr-name")
                if not reviewer_elem:
                    continue
                reviewer = reviewer_elem.get_text(strip=True)

                # 評論內容
                content_elem = item.find("div", class_="rvw-item__rvw-comment")
                if not content_elem:
                    continue
                content = content_elem.get_text(strip=True)

                # 評分
                rating = None
                rating_elem = item.find("span", class_="c-rating__val")
                if rating_elem:
                    with contextlib.suppress(ValueError):
                        rating = float(rating_elem.get_text(strip=True))

                # 訪問日期
                visit_date = None
                visit_elem = item.find("p", class_="rvw-item__date")
                if visit_elem:
                    visit_date = visit_elem.get_text(strip=True)

                # 評論標題
                title = None
                title_elem = item.find("p", class_="rvw-item__rvw-title")
                if title_elem:
                    title = title_elem.get_text(strip=True)

                # 有用數
                helpful_count = None
                helpful_elem = item.find("em", class_="rvw-item__usefulpost-count")
                if helpful_elem:
                    with contextlib.suppress(ValueError):
                        helpful_count = int(helpful_elem.get_text(strip=True))

                review = Review(
                    reviewer=reviewer,
                    content=content,
                    rating=rating,
                    visit_date=visit_date,
                    title=title,
                    helpful_count=helpful_count,
                )
                reviews.append(review)

            except Exception:
                continue

        return reviews

    def _parse_menu_items(self, html: str) -> list[MenuItem]:
        """解析菜單項目"""
        soup = BeautifulSoup(html, "lxml")
        menu_items = []

        # 查找所有菜單分類
        menu_sections = soup.find_all("div", class_="c-offerlist-item")

        for section in menu_sections:
            try:
                # 分類名稱
                category_elem = section.find("h4")
                category = category_elem.get_text(strip=True) if category_elem else None

                # 查找該分類下的所有項目
                items = section.find_all("dl")

                for item_elem in items:
                    try:
                        # 料理名稱
                        name_elem = item_elem.find("dt")
                        if not name_elem:
                            continue
                        name = name_elem.get_text(strip=True)

                        # 價格
                        price = None
                        price_elem = item_elem.find("dd")
                        if price_elem:
                            price = price_elem.get_text(strip=True)

                        menu_item = MenuItem(
                            name=name,
                            price=price,
                            category=category,
                        )
                        menu_items.append(menu_item)

                    except Exception:
                        continue

            except Exception:
                continue

        return menu_items

    def _parse_courses(self, html: str) -> list[Course]:
        """解析套餐資訊"""
        soup = BeautifulSoup(html, "lxml")
        courses = []

        # 查找所有套餐
        course_items = soup.find_all("div", class_="c-offerlist-item")

        for item in course_items:
            try:
                # 套餐名稱
                name_elem = item.find("h4")
                if not name_elem:
                    continue
                name = name_elem.get_text(strip=True)

                # 價格
                price = None
                price_elem = item.find("p", class_="c-offerlist-item__price")
                if price_elem:
                    price = price_elem.get_text(strip=True)

                # 描述
                description = None
                desc_elem = item.find("p", class_="c-offerlist-item__comment")
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # 套餐內容項目
                items = []
                items_elem = item.find("ul")
                if items_elem:
                    item_elems = items_elem.find_all("li")
                    for item_elem in item_elems:
                        item_text = item_elem.get_text(strip=True)
                        if item_text:
                            items.append(item_text)

                course = Course(
                    name=name,
                    price=price,
                    description=description,
                    items=items,
                )
                courses.append(course)

            except Exception:
                continue

        return courses

    def fetch_sync(self) -> RestaurantDetail:
        """同步抓取餐廳詳細資訊"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

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
