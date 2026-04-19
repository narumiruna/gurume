from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from urllib.parse import urljoin

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
PHONE_PATTERN = re.compile(r"0\d{1,4}-\d{1,4}-\d{3,4}|0\d{9,10}")
STATION_PATTERN = re.compile(r"([^\s、,，]+駅)")
BUDGET_PATTERN = re.compile(r"￥[^\s]+")


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

    def _parse_restaurant(self, html: str, base_url: str) -> Restaurant:
        soup = BeautifulSoup(html, "lxml")
        ld_data = self._extract_restaurant_json_ld(soup)
        info_map = self._extract_info_map(soup)

        address = self._extract_address(ld_data) or info_map.get("住所")
        traffic_text = info_map.get("交通手段")

        return Restaurant(
            name=self._extract_restaurant_name(soup, ld_data),
            url=base_url,
            rating=self._extract_rating(soup, ld_data),
            review_count=self._extract_review_count(soup, ld_data),
            area=self._extract_area(ld_data, address),
            station=self._extract_station(soup, traffic_text),
            genres=self._extract_genres(soup, ld_data, info_map),
            description=self._extract_description(soup, ld_data),
            lunch_price=self._extract_budget(soup, index=1),
            dinner_price=self._extract_budget(soup, index=0),
            address=address,
            phone=self._extract_phone(info_map),
            business_hours=info_map.get("営業時間") or info_map.get("営業時間・定休日"),
            closed_days=info_map.get("定休日"),
            reservation_url=self._extract_reservation_url(soup, base_url),
            image_urls=self._extract_image_urls(ld_data),
        )

    def _extract_restaurant_json_ld(self, soup: BeautifulSoup) -> dict[str, Any] | None:
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            raw = script.string or script.get_text(strip=True)
            if not raw:
                continue

            with contextlib.suppress(json.JSONDecodeError, TypeError):
                data = json.loads(raw)
                restaurant = self._find_restaurant_ld_node(data)
                if restaurant is not None:
                    return restaurant

        return None

    def _find_restaurant_ld_node(self, data: Any) -> dict[str, Any] | None:
        if isinstance(data, dict):
            node_type = data.get("@type")
            if node_type == "Restaurant" or (isinstance(node_type, list) and "Restaurant" in node_type):
                return data

            for key in ("@graph", "mainEntity"):
                if key in data and (node := self._find_restaurant_ld_node(data[key])) is not None:
                    return node

        if isinstance(data, list):
            for item in data:
                if (node := self._find_restaurant_ld_node(item)) is not None:
                    return node

        return None

    def _extract_info_map(self, soup: BeautifulSoup) -> dict[str, str]:
        info_map: dict[str, str] = {}
        for row in soup.find_all("tr"):
            header = row.find("th")
            value = row.find("td")
            if header is None or value is None:
                continue

            key = self._normalize_info_key(header.get_text(" ", strip=True))
            text = value.get_text(" ", strip=True)
            if key and text and key not in info_map:
                info_map[key] = text

        return info_map

    def _normalize_info_key(self, text: str) -> str:
        return re.sub(r"\s+", "", text)

    def _extract_restaurant_name(self, soup: BeautifulSoup, ld_data: dict[str, Any] | None) -> str:
        if ld_data and isinstance(ld_data.get("name"), str):
            return ld_data["name"].strip()

        selectors = [
            "h2.display-name",
            "h2.rdheader-rstname",
            "h2",
            "h1",
        ]
        for selector in selectors:
            if element := soup.select_one(selector):
                text = element.get_text(" ", strip=True)
                if text:
                    return text

        return ""

    def _extract_rating(self, soup: BeautifulSoup, ld_data: dict[str, Any] | None) -> float | None:
        aggregate = ld_data.get("aggregateRating") if ld_data else None
        if isinstance(aggregate, dict):
            rating_value = aggregate.get("ratingValue")
            if isinstance(rating_value, str | int | float):
                with contextlib.suppress(ValueError):
                    return float(rating_value)

        for selector in ("strong.rdheader-rating__score-val-dtl", "span.c-rating__val"):
            if value := self._parse_float(soup.select_one(selector)):
                return value

        return None

    def _extract_review_count(self, soup: BeautifulSoup, ld_data: dict[str, Any] | None) -> int | None:
        aggregate = ld_data.get("aggregateRating") if ld_data else None
        if isinstance(aggregate, dict):
            review_count = aggregate.get("reviewCount")
            if isinstance(review_count, str | int):
                with contextlib.suppress(ValueError):
                    return int(review_count)

        text = soup.get_text("\n", strip=True)
        match = re.search(r"口コミ\s*([0-9,]+)\s*人", text)
        if match:
            with contextlib.suppress(ValueError):
                return int(match.group(1).replace(",", ""))

        return None

    def _extract_address(self, ld_data: dict[str, Any] | None) -> str | None:
        address = ld_data.get("address") if ld_data else None
        if not isinstance(address, dict):
            return None

        parts = [
            address.get("addressRegion"),
            address.get("addressLocality"),
            address.get("streetAddress"),
        ]
        text = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
        return text or None

    def _extract_area(self, ld_data: dict[str, Any] | None, address: str | None) -> str | None:
        address_obj = ld_data.get("address") if ld_data else None
        if isinstance(address_obj, dict):
            for key in ("addressRegion", "addressLocality"):
                value = address_obj.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if address:
            return address.split()[0]

        return None

    def _extract_station(self, soup: BeautifulSoup, traffic_text: str | None) -> str | None:
        if traffic_text:
            if match := STATION_PATTERN.search(traffic_text):
                return match.group(1)
            return traffic_text

        text = soup.get_text("\n", strip=True)
        if match := re.search(r"最寄り駅[:：]\s*([^\n]+駅)", text):
            return match.group(1).strip()

        return None

    def _extract_genres(
        self,
        soup: BeautifulSoup,
        ld_data: dict[str, Any] | None,
        info_map: dict[str, str],
    ) -> list[str]:
        serves_cuisine = ld_data.get("servesCuisine") if ld_data else None
        if isinstance(serves_cuisine, list):
            return [item.strip() for item in serves_cuisine if isinstance(item, str) and item.strip()]
        if isinstance(serves_cuisine, str) and serves_cuisine.strip():
            return [item.strip() for item in re.split(r"[、,/]", serves_cuisine) if item.strip()]

        genres_text = info_map.get("ジャンル")
        if genres_text:
            return [item.strip() for item in re.split(r"[、,/]", genres_text) if item.strip()]

        text = soup.get_text("\n", strip=True)
        if match := re.search(r"ジャンル[:：]\s*([^\n]+)", text):
            return [item.strip() for item in re.split(r"[、,/]", match.group(1)) if item.strip()]

        return []

    def _extract_description(self, soup: BeautifulSoup, ld_data: dict[str, Any] | None) -> str | None:
        if ld_data and isinstance(ld_data.get("description"), str) and ld_data["description"].strip():
            return ld_data["description"].strip()

        for meta in (
            soup.find("meta", attrs={"name": "description"}),
            soup.find("meta", attrs={"property": "og:description"}),
        ):
            if meta is not None:
                content = meta.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()

        for selector in ("p.rdheader-caption__comment", "div.rdheader-caption__comment"):
            if element := soup.select_one(selector):
                text = element.get_text(" ", strip=True)
                if text:
                    return text

        return None

    def _extract_budget(self, soup: BeautifulSoup, index: int) -> str | None:
        text = soup.get_text("\n", strip=True)
        budget_start = text.find("予算")
        if budget_start == -1:
            return None

        window = text[budget_start : budget_start + 200]
        matches = BUDGET_PATTERN.findall(window)
        if len(matches) > index:
            return matches[index]

        return None

    def _extract_phone(self, info_map: dict[str, str]) -> str | None:
        for key in ("予約・お問い合わせ", "お問い合わせ", "電話番号"):
            value = info_map.get(key)
            if value and (match := PHONE_PATTERN.search(value)):
                return match.group(0)

        return None

    def _extract_reservation_url(self, soup: BeautifulSoup, base_url: str) -> str | None:
        candidates: list[tuple[int, str]] = []
        for link in soup.find_all("a", href=True):
            text = link.get_text(" ", strip=True)
            href = link.get("href")
            if not text or not isinstance(href, str) or "予約" not in text:
                continue
            if text in {"予約確認", "予約内容確認"}:
                continue

            score = 0
            if "ネット予約" in text:
                score += 3
            if "予約する" in text:
                score += 2
            if any(token in href for token in ("reserve", "booking", "yoyaku")):
                score += 2
            if href.startswith(("/", "http")):
                score += 1
            candidates.append((score, urljoin(f"{base_url}/", href)))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]

        return None

    def _extract_image_urls(self, ld_data: dict[str, Any] | None) -> list[str]:
        if not ld_data:
            return []

        image = ld_data.get("image")
        if isinstance(image, str) and image:
            return [image]
        if isinstance(image, list):
            return [item for item in image if isinstance(item, str) and item]
        return []

    def fetch_sync(self) -> RestaurantDetail:
        """同步抓取餐廳詳細資訊"""
        headers = {"User-Agent": USER_AGENT}

        base_url = self._get_base_url()

        main_resp = httpx.get(base_url, headers=headers, timeout=30.0, follow_redirects=True)
        main_resp.raise_for_status()
        restaurant = self._parse_restaurant(main_resp.text, base_url)

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

        reviews = []
        menu_items = []
        courses = []

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            main_resp = await client.get(base_url, headers=headers)
            main_resp.raise_for_status()
            restaurant = self._parse_restaurant(main_resp.text, base_url)

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
