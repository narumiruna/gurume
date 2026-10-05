"""Command-line interface."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from .area_mapping import get_area_slug
from .genre_mapping import get_all_genres
from .genre_mapping import get_genre_code
from .restaurant import Restaurant
from .restaurant import resolve_sort_type
from .search import SearchRequest
from .search import SearchResponse
from .search import SearchStatus
from .server_helpers import _build_search_error_output
from .server_helpers import _build_search_output
from .server_helpers import _restaurant_output_data
from .server_helpers import _to_restaurant_outputs
from .server_helpers import _upstream_access_denied_error
from .server_models import RestaurantSearchOutput
from .server_models import SortOption as ServerSortOption
from .server_models import ToolErrorOutput

app = typer.Typer(
    name="gurume",
    help="Search Japanese restaurants on Tabelog with Gurume.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


class OutputFormat(StrEnum):
    """Output format."""

    TABLE = "table"
    JSON = "json"
    JSON_ENVELOPE = "json-envelope"
    JSON_LIST = "json-list"
    SIMPLE = "simple"


class SortOption(StrEnum):
    """Sort option."""

    RANKING = "ranking"
    REVIEW_COUNT = "review-count"
    NEW_OPEN = "new-open"
    STANDARD = "standard"


NATIONAL_AREAS = {"全国"}


@dataclass(frozen=True)
class ResolvedSearchFilters:
    """Normalized CLI search filters after cuisine detection."""

    keyword: str | None
    cuisine: str | None
    genre_code: str | None


def _resolve_search_filters(
    cuisine: str | None,
    keyword: str | None,
    status_console: Console = console,
) -> ResolvedSearchFilters:
    if cuisine:
        genre_code = get_genre_code(cuisine)
        if genre_code:
            status_console.print(f"[cyan]Filtering by cuisine: {cuisine} ({genre_code})[/cyan]")
            return ResolvedSearchFilters(keyword=keyword, cuisine=cuisine, genre_code=genre_code)

        status_console.print(f"[yellow]Warning: unknown cuisine '{cuisine}'; searching as a keyword instead.[/yellow]")
        return ResolvedSearchFilters(keyword=cuisine, cuisine=None, genre_code=None)

    if keyword:
        detected_genre_code = get_genre_code(keyword)
        if detected_genre_code:
            status_console.print(f"[cyan]Detected cuisine: {keyword} ({detected_genre_code})[/cyan]")
            return ResolvedSearchFilters(keyword=None, cuisine=keyword, genre_code=detected_genre_code)

    return ResolvedSearchFilters(keyword=keyword, cuisine=None, genre_code=None)


def _build_json_data(restaurants: Sequence[Restaurant]) -> list[dict[str, object]]:
    return [_restaurant_output_data(restaurant) for restaurant in restaurants]


def _server_sort_option(sort: SortOption) -> ServerSortOption:
    return sort.value


def _unmapped_area_warning(area: str | None, genre_code: str | None) -> str | None:
    if area in NATIONAL_AREAS:
        return None
    if area and genre_code and get_area_slug(area) is None:
        return "Area could not be mapped precisely; results may include restaurants from other areas."
    return None


def _append_warnings(output: RestaurantSearchOutput, warnings: Sequence[str | None]) -> RestaurantSearchOutput:
    for warning in warnings:
        if warning and warning not in output.warnings:
            output.warnings.append(warning)
    return output


def _build_search_json_envelope(
    response: SearchResponse,
    *,
    area: str | None,
    filters: ResolvedSearchFilters,
    sort: SortOption,
    limit: int,
) -> RestaurantSearchOutput:
    status: Literal["success", "no_results"] = "success"
    if response.status == SearchStatus.NO_RESULTS:
        status = "no_results"

    output = _build_search_output(
        items=_to_restaurant_outputs(response.restaurants, limit),
        limit=limit,
        meta=response.meta,
        area=area,
        keyword=filters.keyword,
        cuisine=filters.cuisine,
        genre_code=filters.genre_code,
        sort=_server_sort_option(sort),
        page=1,
        reservation_date=None,
        reservation_time=None,
        party_size=None,
        status=status,
        extra_warnings=response.warnings,
    )
    return _append_warnings(output, [_unmapped_area_warning(area, filters.genre_code)])


def _build_error_json_envelope(
    *,
    area: str | None,
    filters: ResolvedSearchFilters,
    sort: SortOption,
    limit: int,
    error: ToolErrorOutput,
) -> RestaurantSearchOutput:
    output = _build_search_error_output(
        limit=limit,
        area=area,
        keyword=filters.keyword,
        cuisine=filters.cuisine,
        sort=_server_sort_option(sort),
        page=1,
        reservation_date=None,
        reservation_time=None,
        party_size=None,
        error=error,
    )
    return _append_warnings(output, [_unmapped_area_warning(area, filters.genre_code)])


def _invalid_search_error(detail: str) -> ToolErrorOutput:
    return ToolErrorOutput(
        error_code="invalid_parameters",
        message=f"Invalid search parameters: {detail}",
        retryable=False,
        suggested_action="Provide at least one of `--area`, `--keyword`, or `--cuisine`, then retry the search.",
        detail=detail,
    )


def _upstream_search_error(detail: str | None, http_status: int | None = None) -> ToolErrorOutput:
    if http_status == 403:
        return _upstream_access_denied_error("Restaurant search", detail)
    return ToolErrorOutput(
        error_code="upstream_unavailable",
        message="Restaurant search failed because Tabelog returned an error response.",
        retryable=True,
        suggested_action="Validate the area or cuisine first, then retry the search.",
        detail=detail,
    )


def _output_error_envelope_if_requested(
    output: OutputFormat,
    *,
    area: str | None,
    filters: ResolvedSearchFilters,
    sort: SortOption,
    limit: int,
    error: ToolErrorOutput,
) -> None:
    if output in (OutputFormat.JSON, OutputFormat.JSON_ENVELOPE):
        _output_json_envelope(
            _build_error_json_envelope(area=area, filters=filters, sort=sort, limit=limit, error=error)
        )


def _output_no_results_envelope_if_requested(
    output: OutputFormat,
    response: SearchResponse,
    *,
    area: str | None,
    filters: ResolvedSearchFilters,
    sort: SortOption,
    limit: int,
) -> None:
    if output in (OutputFormat.JSON, OutputFormat.JSON_ENVELOPE):
        _output_json_envelope(_build_search_json_envelope(response, area=area, filters=filters, sort=sort, limit=limit))


def _output_search_results(
    output: OutputFormat,
    response: SearchResponse,
    restaurants: list,
    *,
    area: str | None,
    filters: ResolvedSearchFilters,
    sort: SortOption,
    limit: int,
) -> None:
    if output == OutputFormat.JSON_LIST:
        _output_json(restaurants)
    elif output in (OutputFormat.JSON, OutputFormat.JSON_ENVELOPE):
        _output_json_envelope(_build_search_json_envelope(response, area=area, filters=filters, sort=sort, limit=limit))
    elif output == OutputFormat.SIMPLE:
        _output_simple(restaurants)
    else:
        _output_table(restaurants)


@app.command()
def search(
    area: Annotated[str | None, typer.Option("--area", "-a", help="Search area (e.g. Tokyo, Osaka).")] = None,
    keyword: Annotated[str | None, typer.Option("--keyword", "-k", help="Search keyword (e.g. sushi).")] = None,
    cuisine: Annotated[str | None, typer.Option("--cuisine", "-c", help="Cuisine type (e.g. sushi).")] = None,
    sort: Annotated[SortOption, typer.Option("--sort", "-s", help="Sort order.")] = SortOption.RANKING,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Number of results to display.")] = 20,
    output: Annotated[OutputFormat, typer.Option("--output", "-o", help="Output format.")] = OutputFormat.TABLE,
) -> None:
    """Search restaurants.

    Examples:
      gurume search --area 東京 --keyword 寿司
      gurume search -a 三重 -c すき焼き --sort ranking
      gurume search --area 大阪 --cuisine ラーメン -o json
      gurume search --area 大阪 --cuisine ラーメン -o json-list
    """
    status_console = (
        err_console if output in (OutputFormat.JSON, OutputFormat.JSON_ENVELOPE, OutputFormat.JSON_LIST) else console
    )

    if not area and not keyword and not cuisine:
        status_console.print("[red]Error: provide at least one of --area, --keyword, or --cuisine.[/red]")
        _output_error_envelope_if_requested(
            output,
            area=area,
            filters=ResolvedSearchFilters(keyword=keyword, cuisine=cuisine, genre_code=None),
            sort=sort,
            limit=limit,
            error=_invalid_search_error("at least one of area, keyword, or cuisine is required"),
        )
        raise typer.Exit(1)

    filters = _resolve_search_filters(cuisine, keyword, status_console)
    if _unmapped_area_warning(area, filters.genre_code):
        status_console.print(
            f"[yellow]Warning: area '{area}' could not be mapped precisely; results may include other areas.[/yellow]"
        )
    sort_type = resolve_sort_type(sort)

    # Execute search.
    status_console.print("[green]Searching...[/green]")
    request = SearchRequest(
        area=area,
        keyword=filters.keyword,
        genre_code=filters.genre_code,
        sort_type=sort_type,
        max_pages=1,
    )

    response = request.search_sync()

    if response.status.value == "error":
        status_console.print(f"[red]Search failed: {response.error_message}[/red]")
        if response.http_status == 403:
            status_console.print(
                "[yellow]Tabelog denied access (HTTP 403); retrying the same request will not help.[/yellow]"
            )
        _output_error_envelope_if_requested(
            output,
            area=area,
            filters=filters,
            sort=sort,
            limit=limit,
            error=_upstream_search_error(response.error_message, response.http_status),
        )
        raise typer.Exit(1)

    if not response.restaurants:
        status_console.print("[yellow]No restaurants found.[/yellow]")
        _output_no_results_envelope_if_requested(
            output,
            response,
            area=area,
            filters=filters,
            sort=sort,
            limit=limit,
        )
        raise typer.Exit(0)

    # Limit result count.
    restaurants = response.restaurants[:limit]

    # Output results.
    _output_search_results(output, response, restaurants, area=area, filters=filters, sort=sort, limit=limit)

    # Show summary stats.
    status_console.print(
        f"\n[cyan]Found {len(response.restaurants)} restaurants; showing {len(restaurants)}.[/cyan]"
    )


def _output_table(restaurants: list) -> None:
    """Output restaurants as a table."""
    table = Table(title="Search results")
    table.add_column("Restaurant", style="cyan", no_wrap=False)
    table.add_column("Rating", justify="right", style="yellow")
    table.add_column("Reviews", justify="right", style="green")
    table.add_column("Area", style="blue")
    table.add_column("Cuisine", style="magenta")

    for r in restaurants:
        table.add_row(
            r.name,
            f"{r.rating:.2f}" if r.rating else "N/A",
            str(r.review_count) if r.review_count else "N/A",
            r.area or "N/A",
            ", ".join(r.genres[:2]) if r.genres else "N/A",
        )

    console.print(table)


def _output_json(restaurants: list) -> None:
    """Output restaurants as JSON."""
    _print_json(_build_json_data(restaurants))


def _output_json_envelope(output: RestaurantSearchOutput) -> None:
    """Output the structured search envelope as JSON."""
    _print_json(output.model_dump(mode="json"))


def _print_json(data: object) -> None:
    console.print(json.dumps(data, ensure_ascii=False, indent=2), markup=False, highlight=False, soft_wrap=True)


def _output_simple(restaurants: list) -> None:
    """Output restaurants in a simple text format."""
    for i, r in enumerate(restaurants, 1):
        rating_str = f"{r.rating:.2f}" if r.rating else "N/A"
        review_str = str(r.review_count) if r.review_count else "N/A"
        console.print(f"{i}. {r.name} - ⭐{rating_str} ({review_str} reviews)")
        if r.area:
            console.print(f"   Area: {r.area}")
        if r.genres:
            console.print(f"   Cuisine: {', '.join(r.genres[:3])}")
        console.print(f"   URL: {r.url}")
        console.print()


@app.command()
def list_cuisines() -> None:
    """List all supported cuisines."""
    cuisines = get_all_genres()

    table = Table(title=f"Supported cuisines ({len(cuisines)})")
    table.add_column("Cuisine", style="cyan")
    table.add_column("Code", style="yellow")

    for cuisine in cuisines:
        code = get_genre_code(cuisine)
        table.add_row(cuisine, code or "")

    console.print(table)


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    from .tui import main as tui_main

    tui_main()


class McpTransport(StrEnum):
    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"


@app.command()
def mcp(
    transport: Annotated[
        McpTransport,
        typer.Option(
            "--transport",
            "-t",
            help="MCP transport. Use 'streamable-http' for HTTP clients.",
        ),
    ] = McpTransport.STDIO,
    host: Annotated[
        str,
        typer.Option("--host", help="Bind host for HTTP transports."),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Bind port for HTTP transports."),
    ] = 8000,
    path: Annotated[
        str,
        typer.Option(
            "--path",
            help="HTTP mount path (streamable-http or sse).",
        ),
    ] = "/mcp",
) -> None:
    """Start the MCP (Model Context Protocol) server."""
    from .server import run

    run(transport=transport.value, host=host, port=port, path=path)


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
