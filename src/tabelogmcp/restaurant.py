from __future__ import annotations

import contextlib
from enum import Enum
from functools import cache
from typing import Any

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator


class SortType(str, Enum):
    """排序方式"""

    STANDARD = "trend"  # 標準【PR店舗優先順】
    RANKING = "rt"  # ランキング
    REVIEW_COUNT = "rvcn"  # 口コミが多い順
    NEW_OPEN = "nod"  # ニューオープン


class PriceRange(str, Enum):
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


class Restaurant(BaseModel):
    """餐廳資訊"""

    name: str
    url: str
    rating: float | None = None
    review_count: int | None = None
    save_count: int | None = None
    area: str | None = None
    station: str | None = None
    distance: str | None = None
    genres: list[str] = Field(default_factory=list)
    description: str | None = None
    lunch_price: str | None = None
    dinner_price: str | None = None
    has_vpoint: bool = False
    has_reservation: bool = False
    image_urls: list[str] = Field(default_factory=list)


class RestaurantSearchRequest(BaseModel):
    """餐廳搜尋請求"""

    # 基本搜尋參數
    area: str | None = Field(default=None, description="地區/車站")
    keyword: str | None = Field(default=None, description="關鍵字")

    # 預約相關
    reservation_date: str | None = Field(default=None, description="預約日期 (YYYYMMDD)")
    reservation_time: str | None = Field(default=None, description="預約時間 (HHMM)")
    party_size: int | None = Field(default=None, description="預約人數")

    # 排序和分頁
    sort_type: SortType = Field(default=SortType.STANDARD, description="排序方式")
    page: int = Field(default=1, description="頁碼")

    # 過濾條件
    price_range: PriceRange | None = Field(default=None, description="價格範圍")
    online_booking_only: bool = Field(default=False, description="僅顯示可網路預約")
    seat_only: bool = Field(default=False, description="僅顯示座位預約")
    new_open: bool = Field(default=False, description="新開店")

    # 餐廳特色
    has_private_room: bool = Field(default=False, description="有包廂")
    has_parking: bool = Field(default=False, description="有停車場")
    smoking_allowed: bool = Field(default=False, description="允許吸菸")
    card_accepted: bool = Field(default=False, description="接受信用卡")

    @field_validator("area", "keyword")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else None

    @field_validator("reservation_date")
    @classmethod
    def validate_date(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) != 8 or not v.isdigit():
            raise ValueError("日期格式必須為 YYYYMMDD")
        return v

    @field_validator("reservation_time")
    @classmethod
    def validate_time(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) != 4 or not v.isdigit():
            raise ValueError("時間格式必須為 HHMM")
        return v

    def _build_params(self) -> dict[str, Any]:
        """構建搜尋參數"""
        params = {}

        # 基本參數
        if self.area:
            params["sa"] = self.area
        if self.keyword:
            params["sk"] = self.keyword

        # 預約參數
        if self.reservation_date:
            params["svd"] = self.reservation_date
        if self.reservation_time:
            params["svt"] = self.reservation_time
        if self.party_size:
            params["svps"] = str(self.party_size)

        # 排序
        params["SrtT"] = self.sort_type.value

        # 分頁
        params["PG"] = str(self.page)

        # 過濾條件
        if self.price_range:
            params["LstCos"] = self.price_range.value

        if self.online_booking_only:
            params["ChkOnlineBooking"] = "1"
        if self.seat_only:
            params["ChkSeatOnly"] = "1"
        if self.new_open:
            params["ChkNewOpen"] = "1"

        # 餐廳特色
        if self.has_private_room:
            params["ChkRoom"] = "1"
        if self.has_parking:
            params["ChkParking"] = "1"
        if self.smoking_allowed:
            params["LstSmoking"] = "1"
        if self.card_accepted:
            params["ChkCard"] = "1"

        return params

    def _parse_restaurants(self, html: str) -> list[Restaurant]:
        """解析餐廳資訊"""
        soup = BeautifulSoup(html, "lxml")
        restaurants = []

        # 查找餐廳列表項目 (嘗試不同的選擇器)
        restaurant_items = soup.find_all("div", class_="list-rst")
        if not restaurant_items:
            # 備用選擇器
            restaurant_items = soup.find_all("li", class_="list-rst")

        for item in restaurant_items:
            try:
                # 基本資訊
                name_elem = item.find("a", class_="list-rst__rst-name-target")
                if not name_elem:
                    # 備用選擇器
                    name_elem = item.find("a", href=True)
                    if not name_elem:
                        continue

                name = name_elem.get_text(strip=True)
                href = name_elem.get("href", "")
                url = href if href.startswith("http") else "https://tabelog.com" + href

                # 評分
                rating = None
                rating_elem = item.find("span", class_="c-rating__val")
                if rating_elem:
                    with contextlib.suppress(ValueError):
                        rating = float(rating_elem.get_text(strip=True))

                # 評論數
                review_count = None
                review_elem = item.find("em", class_="list-rst__rvw-count-num")
                if review_elem:
                    with contextlib.suppress(ValueError):
                        review_count = int(review_elem.get_text(strip=True))

                # 儲存數
                save_count = None
                save_elem = item.find("em", class_="list-rst__save-count-num")
                if save_elem:
                    with contextlib.suppress(ValueError):
                        save_count = int(save_elem.get_text(strip=True))

                # 地區和車站
                area = None
                station = None
                distance = None
                area_elem = item.find("span", class_="list-rst__area-genre")
                if area_elem:
                    area_text = area_elem.get_text(strip=True)
                    parts = area_text.split("、")
                    if len(parts) >= 2:
                        area = parts[0]
                        station_info = parts[1]
                        if "駅" in station_info:
                            station_parts = station_info.split()
                            if len(station_parts) >= 2:
                                station = station_parts[0]
                                distance = station_parts[1]

                # 料理類型
                genres = []
                genre_elem = item.find("span", class_="list-rst__genre")
                if genre_elem:
                    genre_text = genre_elem.get_text(strip=True)
                    genres = [g.strip() for g in genre_text.split("、") if g.strip()]

                # 描述
                description = None
                desc_elem = item.find("div", class_="list-rst__catch")
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # 價格
                lunch_price = None
                dinner_price = None
                price_elem = item.find("span", class_="list-rst__budget-val")
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    if "ランチ" in price_text:
                        lunch_price = price_text
                    elif "ディナー" in price_text:
                        dinner_price = price_text

                # 特色標記
                has_vpoint = bool(item.find("span", class_="c-badge-tpoint"))
                has_reservation = bool(item.find("div", class_="list-rst__booking-btn"))

                # 圖片
                image_urls = []
                img_elem = item.find("img", class_="list-rst__photo-img")
                if img_elem and img_elem.get("src"):
                    image_urls.append(img_elem.get("src"))

                restaurant = Restaurant(
                    name=name,
                    url=url,
                    rating=rating,
                    review_count=review_count,
                    save_count=save_count,
                    area=area,
                    station=station,
                    distance=distance,
                    genres=genres,
                    description=description,
                    lunch_price=lunch_price,
                    dinner_price=dinner_price,
                    has_vpoint=has_vpoint,
                    has_reservation=has_reservation,
                    image_urls=image_urls,
                )
                restaurants.append(restaurant)

            except Exception:
                # 跳過解析錯誤的項目
                continue

        return restaurants

    def do_sync(self) -> list[Restaurant]:
        """同步執行搜尋"""
        params = self._build_params()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        resp = httpx.get(
            url="https://tabelog.com/rst/rstsearch",
            params=params,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )
        resp.raise_for_status()

        return self._parse_restaurants(resp.text)

    async def do(self) -> list[Restaurant]:
        """異步執行搜尋"""
        params = self._build_params()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(
                url="https://tabelog.com/rst/rstsearch",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()

            return self._parse_restaurants(resp.text)


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
    ).do_sync()
