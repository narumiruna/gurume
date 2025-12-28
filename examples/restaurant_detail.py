"""
Restaurant detail page scraping example.

This example demonstrates how to scrape restaurant detail pages for comprehensive information
including reviews, menu items, and courses.
"""

from __future__ import annotations

from tabelog import RestaurantDetailRequest


def main():
    # Example restaurant URL
    restaurant_url = "https://tabelog.com/tokyo/A1307/A130704/13053564/"

    # Create a detail request
    # You can choose which tabs to fetch
    request = RestaurantDetailRequest(
        restaurant_url=restaurant_url,
        fetch_reviews=True,  # Fetch reviews
        fetch_menu=True,  # Fetch menu items
        fetch_courses=True,  # Fetch courses
        max_review_pages=2,  # Fetch first 2 pages of reviews
    )

    # Fetch detail information synchronously
    detail = request.fetch_sync()

    print(f"Restaurant URL: {detail.restaurant.url}")
    print(f"\nTotal Reviews: {len(detail.reviews)}")
    print(f"Total Menu Items: {len(detail.menu_items)}")
    print(f"Total Courses: {len(detail.courses)}")

    # Display first 3 reviews
    if detail.reviews:
        print("\n=== 評論 (Reviews) ===")
        for i, review in enumerate(detail.reviews[:3], 1):
            print(f"\n{i}. {review.reviewer}")
            if review.rating:
                print(f"   評分: {review.rating}")
            if review.visit_date:
                print(f"   訪問日期: {review.visit_date}")
            if review.title:
                print(f"   標題: {review.title}")
            print(f"   內容: {review.content[:100]}...")

    # Display first 5 menu items
    if detail.menu_items:
        print("\n=== 菜單項目 (Menu Items) ===")
        for i, item in enumerate(detail.menu_items[:5], 1):
            print(f"{i}. {item.name}")
            if item.price:
                print(f"   價格: {item.price}")
            if item.category:
                print(f"   分類: {item.category}")

    # Display first 3 courses
    if detail.courses:
        print("\n=== 套餐 (Courses) ===")
        for i, course in enumerate(detail.courses[:3], 1):
            print(f"\n{i}. {course.name}")
            if course.price:
                print(f"   價格: {course.price}")
            if course.description:
                print(f"   描述: {course.description}")
            if course.items:
                print(f"   內容: {', '.join(course.items[:5])}")


async def async_main():
    """Async example"""
    restaurant_url = "https://tabelog.com/tokyo/A1307/A130704/13053564/"

    request = RestaurantDetailRequest(
        restaurant_url=restaurant_url,
        fetch_reviews=True,
        fetch_menu=True,
        fetch_courses=True,
        max_review_pages=1,
    )

    # Fetch detail information asynchronously
    detail = await request.fetch()

    print("\n=== Async Example ===")
    print(f"Restaurant URL: {detail.restaurant.url}")
    print(f"Total Reviews: {len(detail.reviews)}")
    print(f"Total Menu Items: {len(detail.menu_items)}")
    print(f"Total Courses: {len(detail.courses)}")


def selective_fetch_example():
    """Example: Fetch only specific tabs"""
    restaurant_url = "https://tabelog.com/tokyo/A1307/A130704/13053564/"

    # Fetch only reviews
    request = RestaurantDetailRequest(
        restaurant_url=restaurant_url,
        fetch_reviews=True,
        fetch_menu=False,  # Don't fetch menu
        fetch_courses=False,  # Don't fetch courses
        max_review_pages=3,  # Fetch first 3 pages of reviews
    )

    detail = request.fetch_sync()

    print("\n=== Selective Fetch Example (Reviews Only) ===")
    print(f"Total Reviews: {len(detail.reviews)}")
    print(f"Total Menu Items: {len(detail.menu_items)}  (not fetched)")
    print(f"Total Courses: {len(detail.courses)}  (not fetched)")


if __name__ == "__main__":
    # Run synchronous example
    main()

    # Run async example
    # import asyncio
    # asyncio.run(async_main())

    # Run selective fetch example
    # selective_fetch_example()
