#!/usr/bin/env python3
"""
Verification script for JavaScript rendering impact on Tabelog scraping.

This script tests the current httpx implementation against various real Tabelog pages
to determine the success rate and identify patterns of JS-rendered vs static pages.

Usage:
    uv run python scripts/verify_js_rendering.py
    uv run python scripts/verify_js_rendering.py --output results.json
"""

import json
import sys
import time
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import Progress
from rich.progress import SpinnerColumn
from rich.progress import TextColumn
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gurume import RestaurantSearchRequest
from gurume import SortType
from gurume import get_genre_code


@dataclass
class TestCase:
    """Test case for verification."""

    name: str
    area: str | None = None
    keyword: str | None = None
    cuisine: str | None = None
    expected_status: str = "unknown"  # unknown, likely_works, likely_fails


@dataclass
class TestResult:
    """Result of a test case."""

    test_name: str
    area: str | None
    keyword: str | None
    cuisine: str | None
    genre_code: str | None
    success: bool
    restaurant_count: int
    error: str | None
    duration_seconds: float
    timestamp: str


def create_test_cases() -> list[TestCase]:
    """Create comprehensive test cases covering different scenarios."""
    return [
        # Known JS-rendered case (札幌 + ハンバーグ)
        TestCase(
            name="札幌_ハンバーグ_keyword",
            area="札幌",
            keyword="ハンバーグ",
            expected_status="likely_fails",
        ),
        # Major cities with common cuisines
        TestCase(
            name="東京_すき焼き_cuisine",
            area="東京",
            cuisine="すき焼き",
            expected_status="unknown",
        ),
        TestCase(
            name="大阪_ラーメン_cuisine",
            area="大阪",
            cuisine="ラーメン",
            expected_status="unknown",
        ),
        TestCase(
            name="京都_寿司_cuisine",
            area="京都",
            cuisine="寿司",
            expected_status="unknown",
        ),
        TestCase(
            name="三重_すき焼き_cuisine",
            area="三重",
            cuisine="すき焼き",
            expected_status="unknown",
        ),
        # Cuisine only (no area)
        TestCase(
            name="すき焼き_cuisine_only",
            cuisine="すき焼き",
            expected_status="unknown",
        ),
        TestCase(
            name="ラーメン_cuisine_only",
            cuisine="ラーメン",
            expected_status="unknown",
        ),
        # Keyword searches
        TestCase(
            name="東京_寿司_keyword",
            area="東京",
            keyword="寿司",
            expected_status="unknown",
        ),
        TestCase(
            name="大阪_焼肉_keyword",
            area="大阪",
            keyword="焼肉",
            expected_status="unknown",
        ),
        # Area only
        TestCase(
            name="東京_area_only",
            area="東京",
            expected_status="unknown",
        ),
        TestCase(
            name="大阪_area_only",
            area="大阪",
            expected_status="unknown",
        ),
        # Edge cases
        TestCase(
            name="福岡_居酒屋_cuisine",
            area="福岡",
            cuisine="居酒屋",
            expected_status="unknown",
        ),
        TestCase(
            name="札幌_ラーメン_cuisine",
            area="札幌",
            cuisine="ラーメン",
            expected_status="unknown",
        ),
        TestCase(
            name="名古屋_うなぎ_cuisine",
            area="名古屋",
            cuisine="うなぎ",
            expected_status="unknown",
        ),
    ]


def run_test_case(test_case: TestCase) -> TestResult:
    """Run a single test case and return result."""
    console = Console()
    start_time = time.time()
    genre_code = None

    try:
        # Get genre code if cuisine specified
        if test_case.cuisine:
            genre_code = get_genre_code(test_case.cuisine)

        # Create search request
        request = RestaurantSearchRequest(
            area=test_case.area,
            keyword=test_case.keyword,
            genre_code=genre_code,
            sort_type=SortType.RANKING,
        )

        # Execute search
        restaurants = request.search_sync()

        # Calculate duration
        duration = time.time() - start_time

        # Check success
        success = len(restaurants) > 0

        return TestResult(
            test_name=test_case.name,
            area=test_case.area,
            keyword=test_case.keyword,
            cuisine=test_case.cuisine,
            genre_code=genre_code,
            success=success,
            restaurant_count=len(restaurants),
            error=None,
            duration_seconds=round(duration, 2),
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        duration = time.time() - start_time
        console.print(f"[red]Error in {test_case.name}: {e!s}[/red]")

        return TestResult(
            test_name=test_case.name,
            area=test_case.area,
            keyword=test_case.keyword,
            cuisine=test_case.cuisine,
            genre_code=genre_code,
            success=False,
            restaurant_count=0,
            error=str(e),
            duration_seconds=round(duration, 2),
            timestamp=datetime.now().isoformat(),
        )


def analyze_results(results: list[TestResult]) -> dict:
    """Analyze test results and generate statistics."""
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = total - successful

    success_rate = (successful / total * 100) if total > 0 else 0

    # Categorize by search type
    area_only = [r for r in results if r.area and not r.keyword and not r.cuisine]
    cuisine_only = [r for r in results if r.cuisine and not r.area and not r.keyword]
    area_cuisine = [r for r in results if r.area and r.cuisine]
    area_keyword = [r for r in results if r.area and r.keyword]

    return {
        "total_tests": total,
        "successful": successful,
        "failed": failed,
        "success_rate": round(success_rate, 2),
        "by_type": {
            "area_only": {
                "total": len(area_only),
                "successful": sum(1 for r in area_only if r.success),
            },
            "cuisine_only": {
                "total": len(cuisine_only),
                "successful": sum(1 for r in cuisine_only if r.success),
            },
            "area_cuisine": {
                "total": len(area_cuisine),
                "successful": sum(1 for r in area_cuisine if r.success),
            },
            "area_keyword": {
                "total": len(area_keyword),
                "successful": sum(1 for r in area_keyword if r.success),
            },
        },
        "average_duration": round(sum(r.duration_seconds for r in results) / total, 2),
        "total_restaurants_found": sum(r.restaurant_count for r in results),
    }


def print_report(results: list[TestResult], analysis: dict):
    """Print detailed report with Rich formatting."""
    console = Console()

    # Summary
    console.print("\n[bold cyan]═══ Verification Results Summary ═══[/bold cyan]\n")

    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Tests", str(analysis["total_tests"]))
    summary_table.add_row("Successful", f"[green]{analysis['successful']}[/green]")
    summary_table.add_row("Failed", f"[red]{analysis['failed']}[/red]")
    summary_table.add_row("Success Rate", f"[bold]{analysis['success_rate']}%[/bold]")
    summary_table.add_row("Avg Duration", f"{analysis['average_duration']}s per test")
    summary_table.add_row("Total Restaurants", str(analysis["total_restaurants_found"]))

    console.print(summary_table)

    # By type breakdown
    console.print("\n[bold cyan]═══ Results by Search Type ═══[/bold cyan]\n")

    type_table = Table()
    type_table.add_column("Search Type", style="cyan")
    type_table.add_column("Total", justify="right")
    type_table.add_column("Successful", justify="right")
    type_table.add_column("Success Rate", justify="right")

    for type_name, stats in analysis["by_type"].items():
        if stats["total"] > 0:
            rate = (stats["successful"] / stats["total"] * 100) if stats["total"] > 0 else 0
            color = "green" if rate >= 80 else "yellow" if rate >= 50 else "red"
            type_table.add_row(
                type_name.replace("_", " ").title(),
                str(stats["total"]),
                f"[{color}]{stats['successful']}[/{color}]",
                f"[{color}]{rate:.1f}%[/{color}]",
            )

    console.print(type_table)

    # Detailed results
    console.print("\n[bold cyan]═══ Detailed Test Results ═══[/bold cyan]\n")

    results_table = Table()
    results_table.add_column("Test Name", style="cyan")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Count", justify="right")
    results_table.add_column("Duration", justify="right")
    results_table.add_column("Error", style="dim")

    for result in results:
        status = "[green]✓ PASS[/green]" if result.success else "[red]✗ FAIL[/red]"
        count = str(result.restaurant_count) if result.success else "0"
        error = result.error[:50] + "..." if result.error and len(result.error) > 50 else result.error or ""

        results_table.add_row(
            result.test_name,
            status,
            count,
            f"{result.duration_seconds}s",
            error,
        )

    console.print(results_table)

    # Recommendations
    console.print("\n[bold cyan]═══ Recommendations ═══[/bold cyan]\n")

    if analysis["success_rate"] >= 95:
        console.print("[green]✓ Current httpx implementation works well (>95% success rate)[/green]")
        console.print("[green]  → No immediate action needed, document edge cases[/green]")
    elif analysis["success_rate"] >= 80:
        console.print("[yellow]⚠ Moderate success rate (80-95%)[/yellow]")
        console.print("[yellow]  → Consider hybrid approach for better reliability[/yellow]")
    elif analysis["success_rate"] >= 50:
        console.print("[red]⚠ Low success rate (50-80%)[/red]")
        console.print("[red]  → Hybrid approach recommended[/red]")
    else:
        console.print("[red]✗ CRITICAL: Very low success rate (<50%)[/red]")
        console.print("[red]  → Playwright integration REQUIRED[/red]")


def main():
    """Main verification workflow."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify JS rendering impact")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="verification_results.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    console = Console()
    console.print("[bold cyan]═══ Tabelog JS Rendering Verification ═══[/bold cyan]\n")

    # Create test cases
    test_cases = create_test_cases()
    console.print(f"Created {len(test_cases)} test cases\n")

    # Run tests with progress bar
    results: list[TestResult] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running tests...", total=len(test_cases))

        for test_case in test_cases:
            progress.update(task, description=f"Testing: {test_case.name}")
            result = run_test_case(test_case)
            results.append(result)
            progress.advance(task)

    # Analyze results
    analysis = analyze_results(results)

    # Print report
    print_report(results, analysis)

    # Save to JSON
    output_data = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(results),
            "python_version": sys.version,
        },
        "analysis": analysis,
        "results": [asdict(r) for r in results],
    }

    output_path = Path(args.output)
    output_path.write_text(json.dumps(output_data, indent=2, ensure_ascii=False))
    console.print(f"\n[green]✓ Results saved to: {output_path}[/green]")


if __name__ == "__main__":
    main()
