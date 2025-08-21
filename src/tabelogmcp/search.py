from __future__ import annotations

import contextlib
from datetime import datetime
from enum import Enum

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from pydantic import Field

from .restaurant import Restaurant
from .restaurant import RestaurantSearchRequest


class SearchStatus(str, Enum):
    """搜尋狀態"""

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    ERROR = "error"


class SearchMeta(BaseModel):
    """搜尋元資料"""

    total_count: int = Field(description="總結果數")
    current_page: int = Field(description="當前頁碼")
    results_per_page: int = Field(description="每頁結果數")
    total_pages: int = Field(description="總頁數")
    has_next_page: bool = Field(description="是否有下一頁")
    has_prev_page: bool = Field(description="是否有上一頁")
    search_time: datetime = Field(default_factory=datetime.now, description="搜尋時間")


class SearchResponse(BaseModel):
    """搜尋回應"""

    status: SearchStatus = Field(description="搜尋狀態")
    restaurants: list[Restaurant] = Field(default_factory=list, description="餐廳列表")
    meta: SearchMeta | None = Field(default=None, description="搜尋元資料")
    error_message: str | None = Field(default=None, description="錯誤訊息")


class SearchRequest(BaseModel):
    """通用搜尋請求 - 擴展 RestaurantSearchRequest"""

    # 繼承所有餐廳搜尋參數
    area: str | None = Field(default=None, description="地區/車站")
    keyword: str | None = Field(default=None, description="關鍵字")
    reservation_date: str | None = Field(default=None, description="預約日期 (YYYYMMDD)")
    reservation_time: str | None = Field(default=None, description="預約時間 (HHMM)")
    party_size: int | None = Field(default=None, description="預約人數")

    # 額外的搜尋配置
    max_pages: int = Field(default=1, description="最大頁數")
    include_meta: bool = Field(default=True, description="是否包含元資料")
    timeout: float = Field(default=30.0, description="請求超時時間")

    def _parse_meta(self, html: str, current_page: int) -> SearchMeta:
        """解析搜尋元資料"""
        soup = BeautifulSoup(html, "lxml")

        # 總結果數
        total_count = 0
        count_elem = soup.find("span", class_="c-page-count__num")
        if count_elem:
            with contextlib.suppress(ValueError):
                total_count = int(count_elem.get_text(strip=True))

        # 每頁結果數 (通常是20)
        results_per_page = 20
        restaurant_items = soup.find_all("div", class_="list-rst")
        if restaurant_items:
            results_per_page = len(restaurant_items)

        # 計算總頁數
        total_pages = (total_count + results_per_page - 1) // results_per_page if total_count > 0 else 1

        # 判斷是否有前後頁
        has_next_page = current_page < total_pages
        has_prev_page = current_page > 1

        return SearchMeta(
            total_count=total_count,
            current_page=current_page,
            results_per_page=results_per_page,
            total_pages=total_pages,
            has_next_page=has_next_page,
            has_prev_page=has_prev_page,
        )

    def _create_restaurant_request(self, page: int = 1) -> RestaurantSearchRequest:
        """創建餐廳搜尋請求"""
        return RestaurantSearchRequest(
            area=self.area,
            keyword=self.keyword,
            reservation_date=self.reservation_date,
            reservation_time=self.reservation_time,
            party_size=self.party_size,
            page=page,
        )

    def do_sync(self) -> SearchResponse:
        """同步執行搜尋"""
        try:
            all_restaurants = []
            meta = None

            for page in range(1, self.max_pages + 1):
                request = self._create_restaurant_request(page)

                # 使用自定義的 HTTP 請求來獲取 HTML (用於解析 meta)
                params = request._build_params()
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

                resp = httpx.get(
                    url="https://tabelog.com/rst/rstsearch",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    follow_redirects=True,
                )
                resp.raise_for_status()

                # 解析餐廳
                restaurants = request._parse_restaurants(resp.text)
                all_restaurants.extend(restaurants)

                # 解析元資料 (只在第一頁)
                if page == 1 and self.include_meta:
                    meta = self._parse_meta(resp.text, page)

                    # 如果沒有結果，提前結束
                    if meta.total_count == 0:
                        break

                    # 更新最大頁數限制
                    if self.max_pages > meta.total_pages:
                        self.max_pages = meta.total_pages

                # 如果這一頁沒有結果，停止搜尋
                if not restaurants:
                    break

            status = SearchStatus.SUCCESS if all_restaurants else SearchStatus.NO_RESULTS

            return SearchResponse(
                status=status,
                restaurants=all_restaurants,
                meta=meta,
            )

        except Exception as e:
            return SearchResponse(
                status=SearchStatus.ERROR,
                error_message=str(e),
            )

    async def do(self) -> SearchResponse:
        """異步執行搜尋"""
        try:
            all_restaurants = []
            meta = None

            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                for page in range(1, self.max_pages + 1):
                    request = self._create_restaurant_request(page)

                    params = request._build_params()
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

                    resp = await client.get(
                        url="https://tabelog.com/rst/rstsearch",
                        params=params,
                        headers=headers,
                    )
                    resp.raise_for_status()

                    # 解析餐廳
                    restaurants = request._parse_restaurants(resp.text)
                    all_restaurants.extend(restaurants)

                    # 解析元資料 (只在第一頁)
                    if page == 1 and self.include_meta:
                        meta = self._parse_meta(resp.text, page)

                        # 如果沒有結果，提前結束
                        if meta.total_count == 0:
                            break

                        # 更新最大頁數限制
                        if self.max_pages > meta.total_pages:
                            self.max_pages = meta.total_pages

                    # 如果這一頁沒有結果，停止搜尋
                    if not restaurants:
                        break

            status = SearchStatus.SUCCESS if all_restaurants else SearchStatus.NO_RESULTS

            return SearchResponse(
                status=status,
                restaurants=all_restaurants,
                meta=meta,
            )

        except Exception as e:
            return SearchResponse(
                status=SearchStatus.ERROR,
                error_message=str(e),
            )
