from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from dataclasses import field
from enum import StrEnum
from functools import cache
from typing import Any

import httpx
from bs4 import BeautifulSoup

from .area_mapping import get_area_slug
from .cache import cache_set
from .cache import cached_get
from .exceptions import InvalidParameterError
from .retry import fetch_with_retry
from .retry import fetch_with_retry_async

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/91.0.4472.124 Safari/537.36"
)
ITEM_PARSE_EXCEPTIONS = (AttributeError, TypeError, ValueError)


class SortType(StrEnum):
    """排序方式"""

    STANDARD = "trend"  # 標準【PR店舗優先順】
    RANKING = "rt"  # ランキング
    REVIEW_COUNT = "rvcn"  # 口コミが多い順
    NEW_OPEN = "nod"  # ニューオープン


class PriceRange(StrEnum):
    """價格範圍"""

    LUNCH_UNDER_1000 = "B001"  # ランチ ～￥999
    LUNCH_1000_2000 = "B002"  # ランチ ￥1,000～￥1,999
    LUNCH_2000_3000 = "B003"  # ランチ ￥2,000～￥2,999
    LUNCH_3000_4000 = "B004"  # ランチ ￥3,000～￥3,999
    LUNCH_4000_5000 = "B005"  # ランチ ￥4,000～￥4,999
    LUNCH_5000_6000 = "B006"  # ランチ ￥5,000～￥5,999
    LUNCH_6000_8000 = "B007"  # ランチ ￥6,000～￥7,999
    LUNCH_8000_10000 = "B008"  # ランチ ￥8,000～￥9,999
    LUNCH_10000_15000 = "B009"  # ランチ ￥10,000～￥14,999
    LUNCH_15000_20000 = "B010"  # ランチ ￥15,000～￥19,999
    LUNCH_20000_30000 = "B011"  # ランチ ￥20,000～￥29,999
    LUNCH_OVER_30000 = "B012"  # ランチ ￥30,000～

    DINNER_UNDER_1000 = "C001"  # ディナー ～￥999
    DINNER_1000_2000 = "C002"  # ディナー ￥1,000～￥1,999
    DINNER_2000_3000 = "C003"  # ディナー ￥2,000～￥2,999
    DINNER_3000_4000 = "C004"  # ディナー ￥3,000～￥3,999
    DINNER_4000_5000 = "C005"  # ディナー ￥4,000～￥4,999
    DINNER_5000_6000 = "C006"  # ディナー ￥5,000～￥5,999
    DINNER_6000_8000 = "C007"  # ディナー ￥6,000～￥7,999
    DINNER_8000_10000 = "C008"  # ディナー ￥8,000～￥9,999
    DINNER_10000_15000 = "C009"  # ディナー ￥10,000～￥14,999
    DINNER_15000_20000 = "C010"  # ディナー ￥15,000～￥19,999
    DINNER_20000_30000 = "C011"  # ディナー ￥20,000～￥29,999
    DINNER_OVER_30000 = "C012"  # ディナー ￥30,000～


@dataclass
class Restaurant:
    """餐廳資訊"""

    name: str
    url: str
    rating: float | None = None
    review_count: int | None = None
    save_count: int | None = None
    area: str | None = None
    station: str | None = None
    distance: str | None = None
    genres: list[str] = field(default_factory=list)
    description: str | None = None
    lunch_price: str | None = None
    dinner_price: str | None = None
    address: str | None = None
    phone: str | None = None
    business_hours: str | None = None
    closed_days: str | None = None
    reservation_url: str | None = None
    has_vpoint: bool = False
    has_reservation: bool = False
    image_urls: list[str] = field(default_factory=list)


@dataclass
class RestaurantSearchRequest:
    """餐廳搜尋請求"""

    # 基本搜尋參數
    area: str | None = None
    keyword: str | None = None
    genre_code: str | None = None  # 料理類別代碼（例如：RC0107 for すき焼き）

    # 預約相關
    reservation_date: str | None = None  # YYYYMMDD
    reservation_time: str | None = None  # HHMM
    party_size: int | None = None

    # 排序和分頁
    sort_type: SortType = SortType.STANDARD
    page: int = 1

    # 過濾條件
    price_range: PriceRange | None = None
    online_booking_only: bool = False
    seat_only: bool = False
    new_open: bool = False

    # 餐廳特色
    has_private_room: bool = False
    has_parking: bool = False
    smoking_allowed: bool = False
    card_accepted: bool = False

    def __post_init__(self) -> None:
        # 自動去除 area/keyword 前後空白
        if self.area is not None:
            self.area = self.area.strip()
        if self.keyword is not None:
            self.keyword = self.keyword.strip()

        # 驗證日期格式 YYYYMMDD
        if self.reservation_date is not None and not re.fullmatch(r"\d{8}", self.reservation_date):
            raise InvalidParameterError(
                f"reservation_date 必須是 YYYYMMDD 格式，例如：20250715。收到：{self.reservation_date}"
            )

        # 驗證時間格式 HHMM
        if self.reservation_time is not None and not re.fullmatch(r"\d{4}", self.reservation_time):
            raise InvalidParameterError(f"reservation_time 必須是 HHMM 格式，例如：1900。收到：{self.reservation_time}")

        # 驗證人數範圍
        if self.party_size is not None and not (1 <= self.party_size <= 100):
            raise InvalidParameterError(f"party_size 必須在 1 到 100 之間。收到：{self.party_size}")

        # 驗證頁數
        if self.page < 1:
            raise InvalidParameterError(f"page 必須 >= 1。收到：{self.page}")

    def _build_params(self) -> dict[str, Any]:
        """構建搜尋參數"""
        params: dict[str, str] = {
            "SrtT": self.sort_type.value,
            "PG": str(self.page),
        }
        self._apply_basic_params(params)
        self._apply_reservation_params(params)
        self._apply_filter_params(params)
        self._apply_feature_params(params)
        return params

    def _apply_basic_params(self, params: dict[str, str]) -> None:
        if self.area:
            params["sa"] = self.area
        if self.keyword:
            params["sk"] = self.keyword

    def _apply_reservation_params(self, params: dict[str, str]) -> None:
        if self.reservation_date:
            params["svd"] = self.reservation_date
        if self.reservation_time:
            params["svt"] = self.reservation_time
        if self.party_size:
            params["svps"] = str(self.party_size)

    def _apply_filter_params(self, params: dict[str, str]) -> None:
        if self.price_range:
            params["LstCos"] = self.price_range.value
        if self.online_booking_only:
            params["ChkOnlineBooking"] = "1"
        if self.seat_only:
            params["ChkSeatOnly"] = "1"
        if self.new_open:
            params["ChkNewOpen"] = "1"

    def _apply_feature_params(self, params: dict[str, str]) -> None:
        if self.has_private_room:
            params["ChkRoom"] = "1"
        if self.has_parking:
            params["ChkParking"] = "1"
        if self.smoking_allowed:
            params["LstSmoking"] = "1"
        if self.card_accepted:
            params["ChkCard"] = "1"

    def _parse_restaurants(self, html: str) -> list[Restaurant]:
        """解析餐廳資訊"""
        soup = BeautifulSoup(html, "lxml")
        restaurants = []

        # 檢查是否有地區找不到的錯誤訊息
        error_elem = soup.find("div", class_="rstlist-notfound")
        if error_elem or "該当のエリア・駅が見つかりませんでした" in html:
            # 地區無效，返回空列表而不是全國排名
            return []

        # 查找餐廳列表項目 (嘗試不同的選擇器)
        restaurant_items = soup.find_all("div", class_="list-rst")
        if not restaurant_items:
            # 備用選擇器
            restaurant_items = soup.find_all("li", class_="list-rst")

        for item in restaurant_items:
            try:
                restaurant = self._parse_restaurant_item(item)
                if restaurant is not None:
                    restaurants.append(restaurant)
            except ITEM_PARSE_EXCEPTIONS:
                # 跳過解析錯誤的項目
                continue

        return restaurants

    def _parse_restaurant_item(self, item: Any) -> Restaurant | None:
        name, url = self._parse_basic_info(item)
        if not name:
            return None

        review_count, save_count, rating = self._parse_counts(item)
        area, station, distance, genres = self._parse_area_and_genres(item)
        description = self._get_text(item.find("div", class_="list-rst__catch"))
        lunch_price, dinner_price = self._parse_prices(item)

        return Restaurant(
            name=name,
            url=url,
            rating=rating,
            review_count=review_count,
            save_count=save_count,
            area=area,
            station=station,
            distance=distance,
            genres=self._merge_genres(item, genres),
            description=description,
            lunch_price=lunch_price,
            dinner_price=dinner_price,
            has_vpoint=bool(item.find("span", class_="c-badge-tpoint")),
            has_reservation=bool(item.find("div", class_="list-rst__booking-btn")),
            image_urls=self._parse_image_urls(item),
        )

    def _parse_basic_info(self, item: Any) -> tuple[str | None, str]:
        name_elem = item.find("a", class_="list-rst__rst-name-target")
        if not name_elem:
            # Fallback: only accept href if it points to a real restaurant page.
            # Skip magazine.tabelog.com promotional items and ads.
            fallback = item.find("a", href=True)
            if fallback and "/A" in str(fallback.get("href", "")):
                name_elem = fallback
            else:
                return None, ""

        href = name_elem.get("href", "")
        url = href if href.startswith("http") else f"https://tabelog.com{href}"
        # Skip magazine/promo items that slipped through
        if "magazine.tabelog.com" in url:
            return None, ""
        return name_elem.get_text(strip=True), url

    def _parse_counts(self, item: Any) -> tuple[int | None, int | None, float | None]:
        rating = self._parse_float(item.find("span", class_="c-rating__val"))
        review_count = self._parse_int(item.find("em", class_="list-rst__rvw-count-num"))
        save_elem = item.find("span", class_="list-rst__save-count-num") or item.find(
            "em", class_="list-rst__save-count-num"
        )
        save_count = self._parse_int(save_elem, strip_commas=True)
        return review_count, save_count, rating

    def _parse_area_and_genres(self, item: Any) -> tuple[str | None, str | None, str | None, list[str]]:
        area = None
        station = None
        distance = None
        genres: list[str] = []
        area_genre_elem = item.find(class_="list-rst__area-genre")
        if not area_genre_elem:
            return area, station, distance, genres

        area_genre_text = area_genre_elem.get_text(strip=True).strip()
        if "/" in area_genre_text:
            parts = area_genre_text.split("/")
            if len(parts) >= 2:
                area = self._strip_prefecture(parts[0].strip())
                genre_part = parts[1].strip()
                if genre_part:
                    genres = [genre_part]
            return area, station, distance, genres

        if "、" in area_genre_text:
            parts = [p.strip() for p in area_genre_text.split("、") if p.strip()]
            if parts:
                area = parts[0]
            if len(parts) >= 2:
                station_part = parts[1]
                distance_match = re.search(r"(\d+\s?m)", station_part)
                if distance_match:
                    distance = distance_match.group(1).replace(" ", "")
                station_match = re.search(r"([^\d]+駅)", station_part)
                if station_match:
                    station = station_match.group(1).strip()
            return area, station, distance, genres

        return self._strip_prefecture(area_genre_text), station, distance, genres

    def _parse_prices(self, item: Any) -> tuple[str | None, str | None]:
        lunch_price = None
        dinner_price = None
        price_elem = item.find("span", class_="list-rst__budget-val")
        if not price_elem:
            return lunch_price, dinner_price

        price_text = price_elem.get_text(strip=True)
        if "ランチ" in price_text:
            lunch_price = price_text
        elif "ディナー" in price_text:
            dinner_price = price_text
        return lunch_price, dinner_price

    def _merge_genres(self, item: Any, genres: list[str]) -> list[str]:
        genre_elem = item.find(class_="list-rst__genre")
        if not genre_elem:
            return genres

        for genre in [g.strip() for g in genre_elem.get_text(strip=True).split("、") if g.strip()]:
            if genre not in genres:
                genres.append(genre)
        return genres

    def _parse_image_urls(self, item: Any) -> list[str]:
        img_elem = item.find("img", class_="list-rst__photo-img")
        if img_elem and img_elem.get("src"):
            return [img_elem.get("src")]
        return []

    def _get_text(self, element: Any) -> str | None:
        return element.get_text(strip=True) if element else None

    def _parse_float(self, element: Any) -> float | None:
        if not element:
            return None
        with contextlib.suppress(ValueError):
            return float(element.get_text(strip=True))
        return None

    def _parse_int(self, element: Any, *, strip_commas: bool = False) -> int | None:
        if not element:
            return None
        value = element.get_text(strip=True)
        if strip_commas:
            value = value.replace(",", "")
        with contextlib.suppress(ValueError):
            return int(value)
        return None

    def _strip_prefecture(self, text: str) -> str:
        return text.split("]")[-1].strip() if "]" in text else text

    def search_sync(self, use_cache: bool = True, use_retry: bool = True) -> list[Restaurant]:
        """同步執行搜尋

        Args:
            use_cache: 是否使用快取（預設：True）
            use_retry: 是否使用重試機制（預設：True）

        Returns:
            餐廳列表
        """
        params = self._build_params()
        headers = {"User-Agent": USER_AGENT}

        # 構建 URL：考慮地區和料理類別
        url = "https://tabelog.com/rst/rstsearch"
        area_slug = None

        if self.area:
            area_slug = get_area_slug(self.area)

        # 根據 area 和 genre_code 決定 URL 格式
        if area_slug and self.genre_code:
            # 有地區 + 類別：/area/rstLst/ with LstG param
            url = f"https://tabelog.com/{area_slug}/rstLst/"
            params.pop("sa", None)  # 移除 area 參數
            params["LstG"] = self.genre_code
        elif area_slug:
            # 只有地區：/area/rstLst/
            url = f"https://tabelog.com/{area_slug}/rstLst/"
            params.pop("sa", None)  # 移除 area 參數
        elif self.genre_code:
            # 只有類別：base search with LstG param
            params["LstG"] = self.genre_code

        # 檢查快取
        if use_cache:
            cached_html = cached_get(url, params)
            if cached_html is not None:
                return self._parse_restaurants(cached_html)

        # 執行請求（使用或不使用重試）
        if use_retry:
            resp = fetch_with_retry(url=url, params=params, headers=headers, timeout=30.0)
        else:
            resp = httpx.get(
                url=url,
                params=params,
                headers=headers,
                timeout=30.0,
                follow_redirects=True,
            )
            resp.raise_for_status()

        # 儲存到快取
        if use_cache:
            cache_set(url, params, resp.text, ttl=1800.0)  # 30 minutes TTL

        return self._parse_restaurants(resp.text)

    async def search(self, use_cache: bool = True, use_retry: bool = True) -> list[Restaurant]:
        """異步執行搜尋

        Args:
            use_cache: 是否使用快取（預設：True）
            use_retry: 是否使用重試機制（預設：True）

        Returns:
            餐廳列表
        """
        params = self._build_params()
        headers = {"User-Agent": USER_AGENT}

        # 構建 URL：考慮地區和料理類別
        url = "https://tabelog.com/rst/rstsearch"
        area_slug = None

        if self.area:
            area_slug = get_area_slug(self.area)

        # 根據 area 和 genre_code 決定 URL 格式
        if area_slug and self.genre_code:
            # 有地區 + 類別：/area/rstLst/ with LstG param
            url = f"https://tabelog.com/{area_slug}/rstLst/"
            params.pop("sa", None)  # 移除 area 參數
            params["LstG"] = self.genre_code
        elif area_slug:
            # 只有地區：/area/rstLst/
            url = f"https://tabelog.com/{area_slug}/rstLst/"
            params.pop("sa", None)  # 移除 area 參數
        elif self.genre_code:
            # 只有類別：base search with LstG param
            params["LstG"] = self.genre_code

        # 檢查快取
        if use_cache:
            cached_html = cached_get(url, params)
            if cached_html is not None:
                return self._parse_restaurants(cached_html)

        # 執行請求（使用或不使用重試）
        if use_retry:
            resp = await fetch_with_retry_async(url=url, params=params, headers=headers, request_timeout=30.0)
        else:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(
                    url=url,
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()

        # 儲存到快取
        if use_cache:
            cache_set(url, params, resp.text, ttl=1800.0)  # 30 minutes TTL

        return self._parse_restaurants(resp.text)

    def do_sync(self) -> list[Restaurant]:
        """同步執行搜尋（已棄用，請使用 search_sync()）"""
        return self.search_sync()

    async def do(self) -> list[Restaurant]:
        """異步執行搜尋（已棄用，請使用 search()）"""
        return await self.search()


@cache
def query_restaurants(
    area: str | None = None,
    keyword: str | None = None,
    reservation_date: str | None = None,
    reservation_time: str | None = None,
    party_size: int | None = None,
    sort_type: SortType = SortType.STANDARD,
    page: int = 1,
    price_range: PriceRange | None = None,
    online_booking_only: bool = False,
    seat_only: bool = False,
    new_open: bool = False,
    has_private_room: bool = False,
    has_parking: bool = False,
    smoking_allowed: bool = False,
    card_accepted: bool = False,
) -> list[Restaurant]:
    """快速查詢餐廳"""
    return RestaurantSearchRequest(
        area=area,
        keyword=keyword,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        party_size=party_size,
        sort_type=sort_type,
        page=page,
        price_range=price_range,
        online_booking_only=online_booking_only,
        seat_only=seat_only,
        new_open=new_open,
        has_private_room=has_private_room,
        has_parking=has_parking,
        smoking_allowed=smoking_allowed,
        card_accepted=card_accepted,
    ).search_sync()
