"""基本搜尋範例"""

import asyncio

from tabelog import PriceRange
from tabelog import RestaurantSearchRequest
from tabelog import SearchRequest
from tabelog import SortType
from tabelog import query_restaurants


def basic_search():
    """基本搜尋示例"""
    print("=== 基本搜尋 ===")

    # 使用快速查詢函數
    restaurants = query_restaurants(
        area="銀座",
        keyword="寿司",
        party_size=2,
        sort_type=SortType.RANKING,
    )

    print(f"找到 {len(restaurants)} 家餐廳")
    for restaurant in restaurants[:3]:
        print(f"- {restaurant.name} (評分: {restaurant.rating})")
        print(f"  地址: {restaurant.area}")
        print(f"  類型: {', '.join(restaurant.genres)}")
        print(f"  URL: {restaurant.url}")
        print()


def advanced_search():
    """進階搜尋示例"""
    print("=== 進階搜尋 ===")

    # 使用 RestaurantSearchRequest 進行更詳細的搜尋
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
    )

    restaurants = request.search_sync()

    print(f"找到 {len(restaurants)} 家餐廳")
    for restaurant in restaurants[:3]:
        print(f"- {restaurant.name} (評分: {restaurant.rating})")
        print(f"  地址: {restaurant.area} {restaurant.station}")
        print(f"  類型: {', '.join(restaurant.genres)}")
        print(f"  可預約: {restaurant.has_reservation}")
        print(f"  URL: {restaurant.url}")
        print()


async def async_search():
    """異步搜尋示例"""
    print("=== 異步搜尋 ===")

    # 使用 SearchRequest 進行多頁搜尋
    request = SearchRequest(
        area="新宿",
        keyword="居酒屋",
        max_pages=2,
        include_meta=True,
    )

    response = await request.search()

    print(f"搜尋狀態: {response.status}")
    if response.meta:
        print(f"總結果數: {response.meta.total_count}")
        print(f"當前頁: {response.meta.current_page}")
        print(f"總頁數: {response.meta.total_pages}")

    print(f"找到 {len(response.restaurants)} 家餐廳")
    for restaurant in response.restaurants[:5]:
        print(f"- {restaurant.name} (評分: {restaurant.rating})")
        print(f"  評論數: {restaurant.review_count}")
        print(f"  類型: {', '.join(restaurant.genres)}")
        print()


def main():
    """主函數"""
    basic_search()
    advanced_search()

    # 運行異步搜尋
    asyncio.run(async_search())


if __name__ == "__main__":
    main()
