from __future__ import annotations

import contextlib
import json
import re
from collections.abc import Callable
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import UTC
from datetime import datetime
from enum import StrEnum

import httpx
from bs4 import BeautifulSoup

from .area_mapping import get_area_slug
from .restaurant import Restaurant
from .restaurant import RestaurantSearchRequest
from .restaurant import SortType
from .restaurant import build_search_url_and_params

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SEARCH_EXCEPTIONS = (httpx.HTTPError, RuntimeError, ValueError, TypeError)


def _now() -> datetime:
    return datetime.now(UTC)


def _reraise_if_fatal(error: BaseException) -> None:
    if isinstance(error, KeyboardInterrupt | SystemExit):
        raise error


class SearchStatus(StrEnum):
    """Search status."""

    SUCCESS = "success"
    NO_RESULTS = "no_results"
    ERROR = "error"


@dataclass
class SearchMeta:
    """Search metadata."""

    total_count: int | None
    current_page: int
    results_per_page: int
    total_pages: int | None
    has_next_page: bool
    has_prev_page: bool
    search_time: datetime = field(default_factory=_now)


@dataclass
class SearchResponse:
    """Search response."""

    status: SearchStatus
    restaurants: list[Restaurant] = field(default_factory=list)
    meta: SearchMeta | None = None
    error_message: str | None = None

    def filter(
        self,
        condition: Callable[[Restaurant], bool] | None = None,
        min_rating: float | None = None,
        min_review_count: int | None = None,
    ) -> SearchResponse:
        """Filter restaurants.

        Args:
            condition: Custom filter predicate.
            min_rating: Minimum rating.
            min_review_count: Minimum review count.

        Returns:
            New SearchResponse containing the filtered restaurants.
        """
        filtered = self.restaurants

        if min_rating is not None:
            filtered = [r for r in filtered if r.rating and r.rating >= min_rating]

        if min_review_count is not None:
            filtered = [r for r in filtered if r.review_count and r.review_count >= min_review_count]

        if condition is not None:
            filtered = [r for r in filtered if condition(r)]

        return SearchResponse(
            status=self.status,
            restaurants=filtered,
            meta=self.meta,
            error_message=self.error_message,
        )

    def sort_by(self, key: str, reverse: bool = False) -> SearchResponse:
        """Sort by the specified field.

        Args:
            key: Sort field: rating, review_count, save_count, or name.
            reverse: Whether to sort in reverse order. Defaults to False.

        Returns:
            New SearchResponse containing the sorted restaurants.
        """
        sorted_restaurants = sorted(
            self.restaurants,
            key=lambda r: getattr(r, key, 0) or 0,
            reverse=reverse,
        )

        return SearchResponse(
            status=self.status,
            restaurants=sorted_restaurants,
            meta=self.meta,
            error_message=self.error_message,
        )

    def top(self, n: int) -> SearchResponse:
        """Take the first N restaurants.

        Args:
            n: Number of restaurants to take.

        Returns:
            New SearchResponse containing the first N restaurants.
        """
        return SearchResponse(
            status=self.status,
            restaurants=self.restaurants[:n],
            meta=self.meta,
            error_message=self.error_message,
        )

    def to_json(self, indent: int = 2) -> str:
        """Export as a JSON string.

        Args:
            indent: Number of spaces for JSON indentation.

        Returns:
            JSON string.
        """
        data = {
            "status": self.status.value,
            "restaurants": [asdict(r) for r in self.restaurants],
            "meta": asdict(self.meta) if self.meta else None,
            "error_message": self.error_message,
        }
        return json.dumps(data, ensure_ascii=False, indent=indent, default=str)

    def to_dict(self) -> dict:
        """Convert to a dictionary.

        Returns:
            Dictionary containing all response data.
        """
        return {
            "status": self.status.value,
            "restaurants": [asdict(r) for r in self.restaurants],
            "meta": asdict(self.meta) if self.meta else None,
            "error_message": self.error_message,
        }


@dataclass
class SearchRequest:
    """Generic search request that extends RestaurantSearchRequest."""

    # Inherited restaurant search parameters.
    area: str | None = None
    keyword: str | None = None
    genre_code: str | None = None
    reservation_date: str | None = None
    reservation_time: str | None = None
    party_size: int | None = None
    sort_type: SortType = SortType.STANDARD
    page: int = 1

    # Additional search configuration.
    max_pages: int = 1
    include_meta: bool = True
    timeout: float = 30.0

    def _parse_meta(self, html: str, current_page: int) -> SearchMeta:
        """Parse search metadata."""
        soup = BeautifulSoup(html, "lxml")

        # Results per page, usually 20.
        results_per_page = 20
        restaurant_items = soup.find_all("div", class_="list-rst")
        if not restaurant_items:
            restaurant_items = soup.find_all("li", class_="list-rst")
        if restaurant_items:
            results_per_page = len(restaurant_items)

        # Total result count.
        total_count = self._parse_total_count(soup, len(restaurant_items))

        # Total page count.
        total_pages = self._parse_total_pages(soup, total_count, results_per_page, current_page)

        # Previous/next page flags.
        has_next_page = self._has_next_page(soup, total_pages, current_page)
        has_prev_page = current_page > 1

        return SearchMeta(
            total_count=total_count,
            current_page=current_page,
            results_per_page=results_per_page,
            total_pages=total_pages,
            has_next_page=has_next_page,
            has_prev_page=has_prev_page,
        )

    def _parse_total_count(self, soup: BeautifulSoup, parsed_item_count: int) -> int | None:
        count_block = soup.find(class_="c-page-count")
        count_elems = count_block.find_all("span", class_="c-page-count__num") if count_block else []
        if not count_elems:
            count_elem = soup.find("span", class_="c-page-count__num")
            count_elems = [count_elem] if count_elem else []

        total_count = None
        for count_elem in reversed(count_elems):
            total_count = self._parse_count_text(count_elem.get_text(" ", strip=True))
            if total_count is not None:
                break

        if total_count is None:
            return 0 if parsed_item_count == 0 else None

        if 0 < total_count < parsed_item_count:
            return None

        return total_count

    def _parse_total_pages(
        self,
        soup: BeautifulSoup,
        total_count: int | None,
        results_per_page: int,
        current_page: int,
    ) -> int | None:
        if total_count is not None:
            return (total_count + results_per_page - 1) // results_per_page if total_count > 0 else 1

        page_numbers = [
            page_number
            for page_elem in soup.select(".c-pagination__num")
            if (page_number := self._parse_count_text(page_elem.get_text(" ", strip=True))) is not None
        ]
        if page_numbers:
            return max(current_page, *page_numbers)

        return None if self._has_next_link(soup) else current_page

    def _has_next_page(self, soup: BeautifulSoup, total_pages: int | None, current_page: int) -> bool:
        if self._has_next_link(soup):
            return True
        return total_pages is not None and current_page < total_pages

    def _has_next_link(self, soup: BeautifulSoup) -> bool:
        return soup.select_one('a[rel="next"], a.c-pagination__arrow--next') is not None

    def _parse_count_text(self, text: str) -> int | None:
        match = re.search(r"\d[\d,]*", text)
        if match is None:
            return None

        with contextlib.suppress(ValueError):
            return int(match.group(0).replace(",", ""))
        return None

    def _create_restaurant_request(self, page: int = 1) -> RestaurantSearchRequest:
        """Create a restaurant search request."""
        return RestaurantSearchRequest(
            area=self.area,
            keyword=self.keyword,
            genre_code=self.genre_code,
            reservation_date=self.reservation_date,
            reservation_time=self.reservation_time,
            party_size=self.party_size,
            sort_type=self.sort_type,
            page=page,
        )

    def _build_headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT}

    def _build_url_and_params(self, request: RestaurantSearchRequest) -> tuple[str, dict[str, str]]:
        params = request._build_params()
        area_slug = get_area_slug(self.area) if self.area else None
        return build_search_url_and_params(params, area_slug, self.genre_code)

    def _update_meta(self, meta: SearchMeta | None, html: str, page: int) -> SearchMeta | None:
        if meta is not None or not self.include_meta:
            return meta

        meta = self._parse_meta(html, page)
        if meta.total_pages is None:
            return meta

        remaining_pages = max(meta.total_pages - self.page + 1, 0)
        if self.max_pages > remaining_pages:
            self.max_pages = remaining_pages
        return meta

    def _search_page_sync(self, request: RestaurantSearchRequest) -> tuple[str, list[Restaurant]]:
        url, params = self._build_url_and_params(request)
        try:
            resp = httpx.get(
                url=url,
                params=params,
                headers=self._build_headers(),
                timeout=self.timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except BaseException as e:
            _reraise_if_fatal(e)
            raise RuntimeError(str(e)) from e
        else:
            return resp.text, request._parse_restaurants(resp.text)

    async def _search_page_async(
        self,
        client: httpx.AsyncClient,
        request: RestaurantSearchRequest,
    ) -> tuple[str, list[Restaurant]]:
        url, params = self._build_url_and_params(request)
        try:
            resp = await client.get(url=url, params=params, headers=self._build_headers())
            resp.raise_for_status()
        except BaseException as e:
            _reraise_if_fatal(e)
            raise RuntimeError(str(e)) from e
        else:
            return resp.text, request._parse_restaurants(resp.text)

    def search_sync(self) -> SearchResponse:
        """Run the search synchronously."""
        try:
            all_restaurants: list[Restaurant] = []
            meta = None

            start_page = self.page
            end_page = self.page + self.max_pages

            for page in range(start_page, end_page):
                request = self._create_restaurant_request(page)
                html, restaurants = self._search_page_sync(request)
                all_restaurants.extend(restaurants)
                meta = self._update_meta(meta, html, page)
                if meta and meta.total_count == 0:
                    break

                # Stop when the current page has no results.
                if not restaurants:
                    break

            status = SearchStatus.SUCCESS if all_restaurants else SearchStatus.NO_RESULTS
        except SEARCH_EXCEPTIONS as e:
            return SearchResponse(
                status=SearchStatus.ERROR,
                error_message=str(e),
            )
        else:
            return SearchResponse(
                status=status,
                restaurants=all_restaurants,
                meta=meta,
            )

    async def search(self) -> SearchResponse:
        """Run the search asynchronously."""
        try:
            all_restaurants: list[Restaurant] = []
            meta = None

            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                start_page = self.page
                end_page = self.page + self.max_pages

                for page in range(start_page, end_page):
                    request = self._create_restaurant_request(page)
                    html, restaurants = await self._search_page_async(client, request)
                    all_restaurants.extend(restaurants)
                    meta = self._update_meta(meta, html, page)
                    if meta and meta.total_count == 0:
                        break

                    # Stop when the current page has no results.
                    if not restaurants:
                        break

            status = SearchStatus.SUCCESS if all_restaurants else SearchStatus.NO_RESULTS
        except SEARCH_EXCEPTIONS as e:
            return SearchResponse(
                status=SearchStatus.ERROR,
                error_message=str(e),
            )
        else:
            return SearchResponse(
                status=status,
                restaurants=all_restaurants,
                meta=meta,
            )

    def do_sync(self) -> SearchResponse:
        """Run the search synchronously. Deprecated; use search_sync()."""
        return self.search_sync()

    async def do(self) -> SearchResponse:
        """Run the search asynchronously. Deprecated; use search()."""
        return await self.search()
