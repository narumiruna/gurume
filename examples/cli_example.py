"""CLI example."""

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
    """Format a date string."""
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
        print(f"Invalid {label}: {value}")
        return False

    return True


async def search_restaurants(args) -> None:
    """Search restaurants."""
    reservation_date = format_date(args.date) if args.date else None
    if not _validate_enum_value(args.price_range, PriceRange, "price range"):
        return
    if not _validate_enum_value(args.sort, SortType, "sort order"):
        return

    request = _build_request(args, reservation_date)
    _print_search_params(args, reservation_date)
    response = await request.search()
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
    print("Searching...")
    print(f"Area: {args.area or 'all'}")
    print(f"Keyword: {args.keyword or 'none'}")
    print(f"Date: {reservation_date or 'none'}")
    print(f"Time: {args.time or 'none'}")
    print(f"Party size: {args.party_size or 'none'}")
    print(f"Max pages: {args.max_pages}")
    print("-" * 50)


def _handle_response(response) -> None:
    if response.status == "error":
        print(f"Search failed: {response.error_message}")
        return

    if response.status == "no_results":
        print("No restaurants matched the search.")
        return

    _print_meta(response)
    _print_restaurants(response)


def _print_meta(response) -> None:
    if not response.meta:
        return

    print(f"Total results: {response.meta.total_count}")
    print(f"Current page: {response.meta.current_page}")
    print(f"Total pages: {response.meta.total_pages}")
    print("-" * 50)


def _print_restaurants(response) -> None:
    for i, restaurant in enumerate(response.restaurants, 1):
        print(f"{i}. {restaurant.name}")
        if restaurant.rating:
            print(f"   Rating: {restaurant.rating}")
        if restaurant.review_count:
            print(f"   Reviews: {restaurant.review_count}")
        if restaurant.area:
            print(f"   Area: {restaurant.area}")
        if restaurant.station:
            print(f"   Station: {restaurant.station} ({restaurant.distance})")
        if restaurant.genres:
            print(f"   Cuisine: {', '.join(restaurant.genres)}")
        if restaurant.description:
            print(f"   Description: {restaurant.description[:100]}...")
        print(f"   URL: {restaurant.url}")
        print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tabelog restaurant search")
    parser.add_argument("-a", "--area", help="Area or station")
    parser.add_argument("-k", "--keyword", help="Keyword")
    parser.add_argument("-d", "--date", help="Reservation date (YYYYMMDD, today, tomorrow)")
    parser.add_argument("-t", "--time", help="Reservation time (HHMM)")
    parser.add_argument("-p", "--party-size", type=int, help="Party size")
    parser.add_argument("--max-pages", type=int, default=1, help="Maximum pages")
    parser.add_argument(
        "--sort",
        choices=["trend", "rt", "rvcn", "nod"],
        help="Sort order: trend (standard), rt (ranking), rvcn (review count), nod (new openings)",
    )
    parser.add_argument("--price-range", help="Price range (e.g. C003 for a dinner budget of 2000-3000)")
    return parser


def main() -> None:
    """Run the example."""
    args = _build_parser().parse_args()
    asyncio.run(search_restaurants(args))


if __name__ == "__main__":
    main()
