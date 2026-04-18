"""CLI 範例"""

import argparse
import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from gurume import PriceRange
from gurume import SearchRequest
from gurume import SortType


def _now() -> datetime:
    return datetime.now(UTC)


def format_date(date_str: str) -> str:
    """格式化日期字串"""
    if date_str.lower() == "today":
        return _now().strftime("%Y%m%d")
    if date_str.lower() == "tomorrow":
        return (_now() + timedelta(days=1)).strftime("%Y%m%d")
    return date_str


def _validate_enum_value(value: str | None, enum_cls: type[PriceRange] | type[SortType], label: str) -> bool:
    if value is None:
        return True

    try:
        enum_cls(value)
    except ValueError:
        print(f"無效的{label}: {value}")
        return False

    return True


async def search_restaurants(args) -> None:
    """搜尋餐廳"""
    reservation_date = format_date(args.date) if args.date else None
    if not _validate_enum_value(args.price_range, PriceRange, "價格範圍"):
        return
    if not _validate_enum_value(args.sort, SortType, "排序方式"):
        return

    request = _build_request(args, reservation_date)
    _print_search_params(args, reservation_date)
    response = await request.do()
    _handle_response(response)


def _build_request(args, reservation_date: str | None) -> SearchRequest:
    return SearchRequest(
        area=args.area,
        keyword=args.keyword,
        reservation_date=reservation_date,
        reservation_time=args.time,
        party_size=args.party_size,
        max_pages=args.max_pages,
        include_meta=True,
    )


def _print_search_params(args, reservation_date: str | None) -> None:
    print("搜尋中...")
    print(f"地區: {args.area or '全部'}")
    print(f"關鍵字: {args.keyword or '無'}")
    print(f"日期: {reservation_date or '無'}")
    print(f"時間: {args.time or '無'}")
    print(f"人數: {args.party_size or '無'}")
    print(f"最大頁數: {args.max_pages}")
    print("-" * 50)


def _handle_response(response) -> None:
    if response.status == "error":
        print(f"搜尋錯誤: {response.error_message}")
        return

    if response.status == "no_results":
        print("沒有找到符合條件的餐廳")
        return

    _print_meta(response)
    _print_restaurants(response)


def _print_meta(response) -> None:
    if not response.meta:
        return

    print(f"總結果數: {response.meta.total_count}")
    print(f"顯示頁數: {response.meta.current_page}")
    print(f"總頁數: {response.meta.total_pages}")
    print("-" * 50)


def _print_restaurants(response) -> None:
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


def main() -> None:
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
