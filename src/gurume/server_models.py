"""Pydantic schemas and shared type aliases for MCP server responses."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import HttpUrl

SortOption = Literal["ranking", "review-count", "new-open", "standard"]
SuggestionDatatype = Literal[
    "AddressMaster",
    "RailroadStation",
    "Genre2",
    "Restaurant",
    "Genre2 DetailCondition",
    "Prefecture",
    "Town",
]


class RestaurantOutput(BaseModel):
    """Restaurant search result output schema."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Restaurant name")
    rating: float | None = Field(description="Tabelog rating (0.0-5.0)")
    review_count: int | None = Field(description="Number of reviews")
    area: str | None = Field(description="Location area")
    genres: list[str] = Field(description="List of cuisine genres")
    url: HttpUrl = Field(description="Tabelog restaurant page URL")
    lunch_price: str | None = Field(description="Lunch price range")
    dinner_price: str | None = Field(description="Dinner price range")


class CuisineOutput(BaseModel):
    """Cuisine type output schema."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Cuisine name in Japanese")
    code: str = Field(description="Tabelog genre code (e.g., 'RC0107')", pattern=r"^RC\d{4}$")


class SuggestionOutput(BaseModel):
    """Area or keyword suggestion output schema."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Suggestion display name")
    datatype: SuggestionDatatype = Field(
        description="Suggestion type (AddressMaster, RailroadStation, Genre2, Restaurant, etc.)"
    )
    id_in_datatype: str | int = Field(description="Unique identifier within datatype")
    lat: float | None = Field(description="Latitude (decimal degrees)")
    lng: float | None = Field(description="Longitude (decimal degrees)")


class ToolErrorOutput(BaseModel):
    """Structured MCP tool error output for agent-friendly recovery."""

    model_config = ConfigDict(extra="forbid")

    error_code: Literal[
        "invalid_parameters",
        "unsupported_cuisine",
        "upstream_unavailable",
        "internal_error",
    ] = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error summary")
    retryable: bool = Field(description="Whether retrying the same tool call may succeed")
    suggested_action: str = Field(description="Concrete next step for the caller")
    detail: str | None = Field(description="Optional raw detail for debugging or logging")


class SearchMetaOutput(BaseModel):
    """Pagination and result metadata for restaurant search."""

    model_config = ConfigDict(extra="forbid")

    total_count: int | None = Field(description="Total restaurants reported by Tabelog for this query")
    current_page: int = Field(description="Current result page returned by the tool")
    results_per_page: int | None = Field(description="Number of restaurants parsed from the fetched page")
    total_pages: int | None = Field(description="Total number of result pages reported by Tabelog")
    has_next_page: bool = Field(description="Whether Tabelog reports a next result page")
    has_prev_page: bool = Field(description="Whether Tabelog reports a previous result page")


class SearchFiltersOutput(BaseModel):
    """Normalized filters used for a search request."""

    model_config = ConfigDict(extra="forbid")

    area: str | None = Field(description="Area filter used for the search")
    keyword: str | None = Field(description="Keyword filter used for the search")
    cuisine: str | None = Field(description="Cuisine filter used for the search")
    genre_code: str | None = Field(description="Resolved Tabelog genre code for the cuisine filter")
    sort: str = Field(description="Sort option used for the search")
    page: int = Field(description="Requested result page")
    reservation_date: str | None = Field(description="Reservation date used for filtering, if any")
    reservation_time: str | None = Field(description="Reservation time used for filtering, if any")
    party_size: int | None = Field(description="Party size used for filtering, if any")


class RestaurantSearchOutput(BaseModel):
    """Structured restaurant search output for MCP clients."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "no_results", "error"] = Field(description="Search status after executing the query")
    items: list[RestaurantOutput] = Field(default_factory=list, description="Restaurants returned for the current page")
    returned_count: int = Field(default=0, description="Number of restaurants returned in this response")
    limit: int = Field(description="Maximum number of restaurants requested by the caller")
    has_more: bool = Field(
        default=False,
        description="Whether more matching restaurants likely exist beyond this response",
    )
    meta: SearchMetaOutput | None = Field(default=None, description="Tabelog pagination metadata for the current query")
    applied_filters: SearchFiltersOutput = Field(description="Normalized search filters used by the server")
    warnings: list[str] = Field(default_factory=list, description="Non-fatal usage guidance for the caller")
    error: ToolErrorOutput | None = Field(default=None, description="Structured error details when status is error")


class CuisineListOutput(BaseModel):
    """Structured cuisine list output for MCP clients."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error"] = Field(description="Cuisine list retrieval status")
    items: list[CuisineOutput] = Field(default_factory=list, description="Supported cuisine entries")
    returned_count: int = Field(default=0, description="Number of cuisine entries returned")
    error: ToolErrorOutput | None = Field(default=None, description="Structured error details when status is error")


class SuggestionListOutput(BaseModel):
    """Structured suggestion list output for MCP clients."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error"] = Field(description="Suggestion lookup status")
    query: str = Field(description="Normalized query used for the suggestion lookup")
    items: list[SuggestionOutput] = Field(default_factory=list, description="Suggestions returned by Tabelog")
    returned_count: int = Field(default=0, description="Number of suggestions returned")
    error: ToolErrorOutput | None = Field(default=None, description="Structured error details when status is error")


class ReviewOutput(BaseModel):
    """Structured restaurant review output."""

    model_config = ConfigDict(extra="forbid")

    reviewer: str = Field(description="Reviewer display name")
    content: str = Field(description="Review body text")
    rating: float | None = Field(description="Reviewer rating if available")
    visit_date: str | None = Field(description="Visit date text shown on Tabelog")
    title: str | None = Field(description="Review title if available")
    helpful_count: int | None = Field(description="Helpful vote count if available")


class MenuItemOutput(BaseModel):
    """Structured menu item output."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Menu item name")
    price: str | None = Field(description="Displayed menu item price")
    description: str | None = Field(description="Menu item description if available")
    category: str | None = Field(description="Menu section heading if available")


class CourseOutput(BaseModel):
    """Structured course output."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Course name")
    price: str | None = Field(description="Displayed course price")
    description: str | None = Field(description="Course description if available")
    items: list[str] = Field(description="Course item list if available")


class RestaurantDetailOutput(BaseModel):
    """Structured restaurant detail output for MCP clients."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "error"] = Field(description="Restaurant detail retrieval status")
    restaurant: RestaurantOutput | None = Field(
        default=None,
        description="Structured base restaurant information from the detail page",
    )
    restaurant_url: str = Field(description="Requested Tabelog restaurant URL used for detail fetches")
    address: str | None = Field(default=None, description="Street address shown on the detail page")
    station: str | None = Field(default=None, description="Nearest station text if available")
    phone: str | None = Field(default=None, description="Contact phone number if available")
    business_hours: str | None = Field(default=None, description="Business hours text if available")
    closed_days: str | None = Field(default=None, description="Closed day text if available")
    reservation_url: HttpUrl | None = Field(
        default=None,
        description="Reservation URL if one can be identified from the page",
    )
    review_count: int = Field(default=0, description="Number of review entries returned in this response")
    menu_item_count: int = Field(default=0, description="Number of menu items returned in this response")
    course_count: int = Field(default=0, description="Number of courses returned in this response")
    fetch_reviews: bool = Field(description="Whether review pages were requested")
    fetch_menu: bool = Field(description="Whether menu pages were requested")
    fetch_courses: bool = Field(description="Whether course pages were requested")
    max_review_pages: int = Field(description="Maximum review pages requested from Tabelog", ge=1)
    reviews: list[ReviewOutput] = Field(default_factory=list, description="Structured review entries")
    menu_items: list[MenuItemOutput] = Field(default_factory=list, description="Structured menu items")
    courses: list[CourseOutput] = Field(default_factory=list, description="Structured course entries")
    error: ToolErrorOutput | None = Field(default=None, description="Structured error details when status is error")
