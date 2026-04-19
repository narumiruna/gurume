"""Helper functions for MCP server validation and response building."""

from __future__ import annotations

from datetime import date
from datetime import time
from typing import Literal
from typing import cast

from pydantic import HttpUrl
from pydantic import TypeAdapter

from .detail import RestaurantDetail
from .genre_mapping import get_genre_code
from .restaurant import Restaurant
from .restaurant import SortType
from .search import SearchMeta
from .server_models import CourseOutput
from .server_models import CuisineListOutput
from .server_models import CuisineOutput
from .server_models import MenuItemOutput
from .server_models import RestaurantDetailOutput
from .server_models import RestaurantOutput
from .server_models import RestaurantSearchOutput
from .server_models import ReviewOutput
from .server_models import SearchFiltersOutput
from .server_models import SearchMetaOutput
from .server_models import SortOption
from .server_models import SuggestionDatatype
from .server_models import SuggestionListOutput
from .server_models import SuggestionOutput
from .server_models import ToolErrorOutput
from .suggest import AreaSuggestion
from .suggest import KeywordSuggestion

SORT_MAP = {
    "ranking": SortType.RANKING,
    "review-count": SortType.REVIEW_COUNT,
    "new-open": SortType.NEW_OPEN,
    "standard": SortType.STANDARD,
}

HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


def _build_tool_error(
    *,
    error_code: Literal["invalid_parameters", "unsupported_cuisine", "upstream_unavailable", "internal_error"],
    message: str,
    retryable: bool,
    suggested_action: str,
    detail: str | None = None,
) -> ToolErrorOutput:
    return ToolErrorOutput(
        error_code=error_code,
        message=message,
        retryable=retryable,
        suggested_action=suggested_action,
        detail=detail,
    )


def _validate_search_params(
    sort: SortOption,
    limit: int,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
) -> SortType:
    _validate_pagination_params(limit, page, sort)
    _validate_reservation_params(reservation_date, reservation_time, party_size)
    return SORT_MAP[sort]


def _validate_pagination_params(limit: int, page: int, sort: SortOption) -> None:
    if limit < 1 or limit > 60:
        raise ValueError("limit must be between 1 and 60")

    if page < 1:
        raise ValueError("page must be greater than or equal to 1")

    if sort not in SORT_MAP:
        raise ValueError(f"Invalid sort type: {sort}. Must be one of: {', '.join(SORT_MAP)}")


def _validate_reservation_params(
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
) -> None:
    if reservation_date is not None and (not reservation_date.isdigit() or len(reservation_date) != 8):
        raise ValueError("reservation_date must be in YYYYMMDD format (e.g., '20260427')")

    if reservation_time is not None and (not reservation_time.isdigit() or len(reservation_time) != 4):
        raise ValueError("reservation_time must be in HHMM format (e.g., '1900')")

    if reservation_date is None and reservation_time is None and party_size is None:
        return

    if reservation_date is None:
        raise ValueError("reservation_date is required when using reservation_time or party_size")

    if reservation_time is None:
        raise ValueError("reservation_time is required when using reservation_date or party_size")

    try:
        date(int(reservation_date[:4]), int(reservation_date[4:6]), int(reservation_date[6:8]))
    except ValueError as e:
        raise ValueError("reservation_date must be a valid date in YYYYMMDD format (e.g., '20260427')") from e

    try:
        time(int(reservation_time[:2]), int(reservation_time[2:4]))
    except ValueError as e:
        raise ValueError("reservation_time must be a valid 24-hour time in HHMM format (e.g., '1900')") from e


def _resolve_genre_code(cuisine: str | None) -> str | None:
    if not cuisine:
        return None

    genre_code = get_genre_code(cuisine)
    if not genre_code:
        raise ValueError(f"Unknown cuisine type: {cuisine}. Use 'tabelog_list_cuisines' to see supported cuisines.")
    return genre_code


def _to_restaurant_outputs(response: list[Restaurant], limit: int) -> list[RestaurantOutput]:
    return [
        RestaurantOutput(
            name=restaurant.name,
            rating=restaurant.rating,
            review_count=restaurant.review_count,
            area=restaurant.area,
            genres=restaurant.genres,
            url=_as_http_url(restaurant.url),
            lunch_price=restaurant.lunch_price,
            dinner_price=restaurant.dinner_price,
        )
        for restaurant in response[:limit]
    ]


def _as_http_url(url: str) -> HttpUrl:
    return HTTP_URL_ADAPTER.validate_python(url)


def _to_search_meta_output(meta: SearchMeta | None) -> SearchMetaOutput | None:
    if meta is None:
        return None

    return SearchMetaOutput(
        total_count=meta.total_count,
        current_page=meta.current_page,
        results_per_page=meta.results_per_page,
        total_pages=meta.total_pages,
        has_next_page=meta.has_next_page,
        has_prev_page=meta.has_prev_page,
    )


def _to_suggestion_outputs(suggestions: list[AreaSuggestion] | list[KeywordSuggestion]) -> list[SuggestionOutput]:
    return [
        SuggestionOutput(
            name=suggestion.name,
            datatype=cast(SuggestionDatatype, suggestion.datatype),
            id_in_datatype=suggestion.id_in_datatype,
            lat=suggestion.lat,
            lng=suggestion.lng,
        )
        for suggestion in suggestions
    ]


def _build_search_warnings(
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    reservation_date: str | None,
) -> list[str]:
    warnings: list[str] = []

    if area is not None:
        warnings.append("Use `tabelog_get_area_suggestions` first when the user provides an ambiguous area name.")

    if cuisine is None and keyword is not None:
        warnings.append(
            "If the keyword is actually a cuisine type, call `tabelog_get_keyword_suggestions` and pass the "
            "Genre2 result as `cuisine` for more precise matches."
        )

    if cuisine is not None and keyword is not None:
        warnings.append(
            "Using both `cuisine` and `keyword` narrows results. Remove `keyword` if you want broader cuisine matches."
        )

    if reservation_date is not None:
        warnings.append("Reservation filters reflect Tabelog availability data and may change over time.")

    return warnings


def _build_search_filters_output(
    *,
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    genre_code: str | None,
    sort: SortOption,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
) -> SearchFiltersOutput:
    return SearchFiltersOutput(
        area=area,
        keyword=keyword,
        cuisine=cuisine,
        genre_code=genre_code,
        sort=sort,
        page=page,
        reservation_date=reservation_date,
        reservation_time=reservation_time,
        party_size=party_size,
    )


def _build_search_output(
    *,
    items: list[RestaurantOutput],
    limit: int,
    meta: SearchMeta | None,
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    genre_code: str | None,
    sort: SortOption,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
    status: Literal["success", "no_results"],
) -> RestaurantSearchOutput:
    meta_output = _to_search_meta_output(meta)
    returned_count = len(items)

    return RestaurantSearchOutput(
        status=status,
        items=items,
        returned_count=returned_count,
        limit=limit,
        has_more=meta.has_next_page if meta is not None else False,
        meta=meta_output,
        applied_filters=_build_search_filters_output(
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            genre_code=genre_code,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
        ),
        warnings=_build_search_warnings(area, keyword, cuisine, reservation_date),
    )


def _build_search_error_output(
    *,
    limit: int,
    area: str | None,
    keyword: str | None,
    cuisine: str | None,
    sort: SortOption,
    page: int,
    reservation_date: str | None,
    reservation_time: str | None,
    party_size: int | None,
    error: ToolErrorOutput,
) -> RestaurantSearchOutput:
    return RestaurantSearchOutput(
        status="error",
        limit=limit,
        applied_filters=_build_search_filters_output(
            area=area,
            keyword=keyword,
            cuisine=cuisine,
            genre_code=get_genre_code(cuisine) if cuisine else None,
            sort=sort,
            page=page,
            reservation_date=reservation_date,
            reservation_time=reservation_time,
            party_size=party_size,
        ),
        warnings=_build_search_warnings(area, keyword, cuisine, reservation_date),
        error=error,
    )


def _validate_detail_params(
    restaurant_url: str,
    fetch_reviews: bool,
    fetch_menu: bool,
    fetch_courses: bool,
    max_review_pages: int,
) -> None:
    if not restaurant_url:
        raise ValueError("restaurant_url cannot be empty")

    if not restaurant_url.startswith("https://tabelog.com/"):
        raise ValueError("restaurant_url must be a Tabelog HTTPS URL")

    if not any((fetch_reviews, fetch_menu, fetch_courses)):
        raise ValueError("At least one of fetch_reviews, fetch_menu, or fetch_courses must be true")

    if max_review_pages < 1:
        raise ValueError("max_review_pages must be greater than or equal to 1")


def _to_detail_output(
    detail: RestaurantDetail,
    *,
    fetch_reviews: bool,
    fetch_menu: bool,
    fetch_courses: bool,
    max_review_pages: int,
) -> RestaurantDetailOutput:
    return RestaurantDetailOutput(
        status="success",
        restaurant=RestaurantOutput(
            name=detail.restaurant.name,
            rating=detail.restaurant.rating,
            review_count=detail.restaurant.review_count,
            area=detail.restaurant.area,
            genres=detail.restaurant.genres,
            url=_as_http_url(detail.restaurant.url),
            lunch_price=detail.restaurant.lunch_price,
            dinner_price=detail.restaurant.dinner_price,
        ),
        restaurant_url=detail.restaurant.url,
        address=detail.restaurant.address,
        station=detail.restaurant.station,
        phone=detail.restaurant.phone,
        business_hours=detail.restaurant.business_hours,
        closed_days=detail.restaurant.closed_days,
        reservation_url=_as_http_url(detail.restaurant.reservation_url) if detail.restaurant.reservation_url else None,
        review_count=len(detail.reviews),
        menu_item_count=len(detail.menu_items),
        course_count=len(detail.courses),
        fetch_reviews=fetch_reviews,
        fetch_menu=fetch_menu,
        fetch_courses=fetch_courses,
        max_review_pages=max_review_pages,
        reviews=[
            ReviewOutput(
                reviewer=review.reviewer,
                content=review.content,
                rating=review.rating,
                visit_date=review.visit_date,
                title=review.title,
                helpful_count=review.helpful_count,
            )
            for review in detail.reviews
        ],
        menu_items=[
            MenuItemOutput(
                name=item.name,
                price=item.price,
                description=item.description,
                category=item.category,
            )
            for item in detail.menu_items
        ],
        courses=[
            CourseOutput(
                name=course.name,
                price=course.price,
                description=course.description,
                items=course.items,
            )
            for course in detail.courses
        ],
    )


def _build_detail_error_output(
    *,
    restaurant_url: str,
    fetch_reviews: bool,
    fetch_menu: bool,
    fetch_courses: bool,
    max_review_pages: int,
    error: ToolErrorOutput,
) -> RestaurantDetailOutput:
    return RestaurantDetailOutput(
        status="error",
        restaurant_url=restaurant_url,
        fetch_reviews=fetch_reviews,
        fetch_menu=fetch_menu,
        fetch_courses=fetch_courses,
        max_review_pages=max_review_pages,
        error=error,
    )


def _build_cuisine_list_output(items: list[CuisineOutput]) -> CuisineListOutput:
    return CuisineListOutput(status="success", items=items, returned_count=len(items))


def _build_cuisine_list_error_output(error: ToolErrorOutput) -> CuisineListOutput:
    return CuisineListOutput(status="error", error=error)


def _build_suggestion_list_output(query: str, items: list[SuggestionOutput]) -> SuggestionListOutput:
    return SuggestionListOutput(status="success", query=query, items=items, returned_count=len(items))


def _build_suggestion_list_error_output(query: str, error: ToolErrorOutput) -> SuggestionListOutput:
    return SuggestionListOutput(status="error", query=query, error=error)
