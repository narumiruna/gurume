"""CLI 範例"""

import argparse
import asyncio
from datetime import datetime
from datetime import timedelta

from tabelog import PriceRange
from tabelog import SearchRequest
from tabelog import SortType


def format_date(date_str: str) -> str:
    """格式化日期字串"""
    if date_str.lower() == "today":
        return datetime.now().strftime("%Y%m%d")
    elif date_str.lower() == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")
    else:
        return date_str


async def search_restaurants(args):
    """搜尋餐廳"""
    # 處理日期
    reservation_date = None
    if args.date:
        reservation_date = format_date(args.date)

    # 處理價格範圍
    if args.price_range:
        try:
            PriceRange(args.price_range)
        except ValueError:
            print(f"無效的價格範圍: {args.price_range}")
            return

    # 處理排序
    if args.sort:
        try:
            SortType(args.sort)
        except ValueError:
            print(f"無效的排序方式: {args.sort}")
            return

    # 創建搜尋請求
    request = SearchRequest(
        area=args.area,
        keyword=args.keyword,
        reservation_date=reservation_date,
        reservation_time=args.time,
        party_size=args.party_size,
        max_pages=args.max_pages,
        include_meta=True,
    )

    print("搜尋中...")
    print(f"地區: {args.area or '全部'}")
    print(f"關鍵字: {args.keyword or '無'}")
    print(f"日期: {reservation_date or '無'}")
    print(f"時間: {args.time or '無'}")
    print(f"人數: {args.party_size or '無'}")
    print(f"最大頁數: {args.max_pages}")
    print("-" * 50)

    # 執行搜尋
    response = await request.do()

    if response.status == "error":
        print(f"搜尋錯誤: {response.error_message}")
        return

    if response.status == "no_results":
        print("沒有找到符合條件的餐廳")
        return

    # 顯示元資料
    if response.meta:
        print(f"總結果數: {response.meta.total_count}")
        print(f"顯示頁數: {response.meta.current_page}")
        print(f"總頁數: {response.meta.total_pages}")
        print("-" * 50)

    # 顯示結果
    for i, restaurant in enumerate(response.restaurants, 1):
        print(f"{i}. {restaurant.name}")
        if restaurant.rating:
            print(f"   評分: {restaurant.rating}")
        if restaurant.review_count:
            print(f"   評論數: {restaurant.review_count}")
        if restaurant.area:
            print(f"   地區: {restaurant.area}")
        if restaurant.station:
            print(f"   車站: {restaurant.station} ({restaurant.distance})")
        if restaurant.genres:
            print(f"   類型: {', '.join(restaurant.genres)}")
        if restaurant.description:
            print(f"   描述: {restaurant.description[:100]}...")
        print(f"   URL: {restaurant.url}")
        print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="Tabelog 餐廳搜尋工具")

    # 基本搜尋參數
    parser.add_argument("-a", "--area", help="地區或車站")
    parser.add_argument("-k", "--keyword", help="關鍵字")
    parser.add_argument("-d", "--date", help="預約日期 (YYYYMMDD, today, tomorrow)")
    parser.add_argument("-t", "--time", help="預約時間 (HHMM)")
    parser.add_argument("-p", "--party-size", type=int, help="預約人數")

    # 搜尋選項
    parser.add_argument("--max-pages", type=int, default=1, help="最大頁數")
    parser.add_argument(
        "--sort",
        choices=["trend", "rt", "rvcn", "nod"],
        help="排序方式: trend(標準), rt(評分), rvcn(評論數), nod(新開)",
    )
    parser.add_argument("--price-range", help="價格範圍 (例: C003 代表晚餐2000-3000)")

    # 解析參數
    args = parser.parse_args()

    # 執行搜尋
    asyncio.run(search_restaurants(args))


if __name__ == "__main__":
    main()
