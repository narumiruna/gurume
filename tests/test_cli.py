"""Test CLI functionality"""

import asyncio
import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from gurume.restaurant import Restaurant
from gurume.search import SearchResponse
from gurume.search import SearchStatus


def _now() -> datetime:
    return datetime.now(UTC)


class TestCLIHelpers:
    """Test CLI helper functions"""

    def test_format_date_today(self):
        """Test formatting 'today' date"""
        from examples.cli_example import format_date

        result = format_date("today")
        expected = _now().strftime("%Y%m%d")

        assert result == expected

    def test_format_date_tomorrow(self):
        """Test formatting 'tomorrow' date"""
        from examples.cli_example import format_date

        result = format_date("tomorrow")
        expected = (_now() + timedelta(days=1)).strftime("%Y%m%d")

        assert result == expected

    def test_format_date_specific(self):
        """Test formatting specific date"""
        from examples.cli_example import format_date

        result = format_date("20250715")

        assert result == "20250715"


class TestCLISearch:
    """Test CLI search functionality"""

    @pytest.mark.asyncio
    @patch("gurume.search.SearchRequest.do")
    async def test_search_restaurants_success(self, mock_do):
        """Test successful CLI search"""
        # Mock successful response
        mock_restaurants = [
            Restaurant(
                name="テスト レストラン",
                url="https://tabelog.com/test/",
                rating=4.5,
                review_count=123,
                area="銀座",
                station="銀座駅",
                distance="50m",
                genres=["寿司", "日本料理"],
                description="新鮮なネタが自慢の寿司店です。",
            )
        ]

        from gurume.search import SearchMeta

        mock_response = SearchResponse(
            status=SearchStatus.SUCCESS,
            restaurants=mock_restaurants,
            meta=SearchMeta(
                total_count=100,
                current_page=1,
                results_per_page=20,
                total_pages=5,
                has_next_page=True,
                has_prev_page=False,
            ),
        )

        mock_do.return_value = mock_response

        # Mock args
        args = Mock()
        args.area = "銀座"
        args.keyword = "寿司"
        args.date = "today"
        args.time = "1900"
        args.party_size = 2
        args.max_pages = 1
        args.sort = "rt"
        args.price_range = None

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should not raise an exception
        await search_restaurants(args)

        # Verify SearchRequest was called
        mock_do.assert_called_once()

    @pytest.mark.asyncio
    @patch("examples.cli_example.SearchRequest.do")
    async def test_search_restaurants_no_results(self, mock_do):
        """Test CLI search with no results"""
        mock_response = SearchResponse(
            status=SearchStatus.NO_RESULTS,
            restaurants=[],
        )

        mock_do.return_value = mock_response

        # Mock args
        args = Mock()
        args.area = "存在しない場所"
        args.keyword = "存在しない料理"
        args.date = None
        args.time = None
        args.party_size = None
        args.max_pages = 1
        args.sort = None
        args.price_range = None

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should not raise an exception
        await search_restaurants(args)

        # Verify SearchRequest was called
        mock_do.assert_called_once()

    @pytest.mark.asyncio
    @patch("examples.cli_example.SearchRequest.do")
    async def test_search_restaurants_error(self, mock_do):
        """Test CLI search with error"""
        mock_response = SearchResponse(
            status=SearchStatus.ERROR,
            error_message="HTTP 404 Not Found",
        )

        mock_do.return_value = mock_response

        # Mock args
        args = Mock()
        args.area = "銀座"
        args.keyword = "寿司"
        args.date = None
        args.time = None
        args.party_size = None
        args.max_pages = 1
        args.sort = None
        args.price_range = None

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should not raise an exception
        await search_restaurants(args)

        # Verify SearchRequest was called
        mock_do.assert_called_once()

    @pytest.mark.asyncio
    @patch("gurume.search.SearchRequest.do")
    async def test_search_restaurants_with_all_params(self, mock_do):
        """Test CLI search with all parameters"""
        mock_restaurants = [
            Restaurant(
                name="高級 フレンチ レストラン",
                url="https://tabelog.com/french/",
                rating=4.8,
                review_count=456,
                area="六本木",
                station="六本木駅",
                distance="200m",
                genres=["フレンチ", "欧風料理"],
                description="本格的なフランス料理を提供する高級レストラン。",
                lunch_price="ランチ ¥8,000～¥9,999",
                dinner_price="ディナー ¥15,000～¥19,999",
                has_reservation=True,
                has_vpoint=True,
            )
        ]

        from gurume.search import SearchMeta

        mock_response = SearchResponse(
            status=SearchStatus.SUCCESS,
            restaurants=mock_restaurants,
            meta=SearchMeta(
                total_count=50,
                current_page=1,
                results_per_page=20,
                total_pages=3,
                has_next_page=True,
                has_prev_page=False,
            ),
        )

        mock_do.return_value = mock_response

        # Mock args with all parameters
        args = Mock()
        args.area = "六本木"
        args.keyword = "フレンチ"
        args.date = "20250715"
        args.time = "1930"
        args.party_size = 4
        args.max_pages = 2
        args.sort = "rt"
        args.price_range = "C009"

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should not raise an exception
        await search_restaurants(args)

        # Verify SearchRequest was called
        mock_do.assert_called_once()

    def test_invalid_price_range(self):
        """Test invalid price range handling"""
        # Mock args with invalid price range
        args = Mock()
        args.area = "銀座"
        args.keyword = "寿司"
        args.date = None
        args.time = None
        args.party_size = None
        args.max_pages = 1
        args.sort = None
        args.price_range = "INVALID"

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should handle the invalid price range gracefully
        # The function should return early with an error message
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # This should not raise an exception
        loop.run_until_complete(search_restaurants(args))

        loop.close()

    def test_invalid_sort_type(self):
        """Test invalid sort type handling"""
        # Mock args with invalid sort type
        args = Mock()
        args.area = "銀座"
        args.keyword = "寿司"
        args.date = None
        args.time = None
        args.party_size = None
        args.max_pages = 1
        args.sort = "invalid"
        args.price_range = None

        # Import and run search function
        from examples.cli_example import search_restaurants

        # This should handle the invalid sort type gracefully
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # This should not raise an exception
        loop.run_until_complete(search_restaurants(args))

        loop.close()


class TestCLIArguments:
    """Test CLI argument handling"""

    @patch("sys.argv", ["cli_example.py", "-a", "銀座", "-k", "寿司"])
    def test_basic_args(self):
        """Test basic CLI arguments"""
        import argparse

        # Create parser like in main function
        parser = argparse.ArgumentParser(description="Tabelog 餐廳搜尋工具")

        # Add arguments like in main function
        parser.add_argument("-a", "--area", help="地區或車站")
        parser.add_argument("-k", "--keyword", help="關鍵字")
        parser.add_argument("-d", "--date", help="預約日期 (YYYYMMDD, today, tomorrow)")
        parser.add_argument("-t", "--time", help="預約時間 (HHMM)")
        parser.add_argument("-p", "--party-size", type=int, help="預約人數")
        parser.add_argument("--max-pages", type=int, default=1, help="最大頁數")
        parser.add_argument("--sort", choices=["trend", "rt", "rvcn", "nod"], help="排序方式")
        parser.add_argument("--price-range", help="價格範圍")

        # Parse test arguments
        args = parser.parse_args(["-a", "銀座", "-k", "寿司"])

        assert args.area == "銀座"
        assert args.keyword == "寿司"
        assert args.date is None
        assert args.time is None
        assert args.party_size is None
        assert args.max_pages == 1
        assert args.sort is None
        assert args.price_range is None

    @patch(
        "sys.argv",
        [
            "cli_example.py",
            "-a",
            "渋谷",
            "-k",
            "焼肉",
            "-d",
            "today",
            "-t",
            "1900",
            "-p",
            "4",
            "--max-pages",
            "2",
            "--sort",
            "rt",
        ],
    )
    def test_full_args(self):
        """Test full CLI arguments"""
        import argparse

        # Create parser like in main function
        parser = argparse.ArgumentParser(description="Tabelog 餐廳搜尋工具")

        # Add arguments like in main function
        parser.add_argument("-a", "--area", help="地區或車站")
        parser.add_argument("-k", "--keyword", help="關鍵字")
        parser.add_argument("-d", "--date", help="預約日期 (YYYYMMDD, today, tomorrow)")
        parser.add_argument("-t", "--time", help="預約時間 (HHMM)")
        parser.add_argument("-p", "--party-size", type=int, help="預約人數")
        parser.add_argument("--max-pages", type=int, default=1, help="最大頁數")
        parser.add_argument("--sort", choices=["trend", "rt", "rvcn", "nod"], help="排序方式")
        parser.add_argument("--price-range", help="價格範圍")

        # Parse test arguments
        args = parser.parse_args(
            ["-a", "渋谷", "-k", "焼肉", "-d", "today", "-t", "1900", "-p", "4", "--max-pages", "2", "--sort", "rt"]
        )

        assert args.area == "渋谷"
        assert args.keyword == "焼肉"
        assert args.date == "today"
        assert args.time == "1900"
        assert args.party_size == 4
        assert args.max_pages == 2
        assert args.sort == "rt"
        assert args.price_range is None


# ============================================================================
# Test Typer search command
# ============================================================================


class TestSearchCommand:
    """Test `gurume search` command behavior."""

    def test_json_output_is_machine_parseable(self):
        from typer.testing import CliRunner

        from gurume.cli import app

        response = SearchResponse(
            status=SearchStatus.SUCCESS,
            restaurants=[Restaurant(name="すし店", url="https://tabelog.com/tokyo/A1301/A130101/1/")],
        )
        runner = CliRunner()
        with patch("gurume.search.SearchRequest.search_sync", return_value=response):
            result = runner.invoke(app, ["search", "--area", "東京", "--cuisine", "寿司", "--output", "json"])

        assert result.exit_code == 0
        assert json.loads(result.stdout) == [
            {
                "name": "すし店",
                "rating": None,
                "review_count": None,
                "area": None,
                "genres": [],
                "url": "https://tabelog.com/tokyo/A1301/A130101/1/",
                "lunch_price": None,
                "dinner_price": None,
            }
        ]
        assert "搜尋中" in result.stderr

    def test_limit_must_be_positive(self):
        from typer.testing import CliRunner

        from gurume.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["search", "--area", "東京", "--limit", "0"])

        assert result.exit_code != 0
        assert "--limit" in result.output

    def test_unmapped_area_with_cuisine_warns_about_broad_results(self):
        from typer.testing import CliRunner

        from gurume.cli import app

        response = SearchResponse(
            status=SearchStatus.SUCCESS,
            restaurants=[Restaurant(name="すし店", url="https://tabelog.com/ishikawa/A1701/A170101/1/")],
        )
        runner = CliRunner()
        with patch("gurume.search.SearchRequest.search_sync", return_value=response):
            result = runner.invoke(app, ["search", "--area", "存在しない地域", "--cuisine", "寿司", "--limit", "1"])

        assert result.exit_code == 0
        assert "無法精準映射地區" in result.output


# ============================================================================
# Test MCP transport CLI flags (issue #39)
# ============================================================================


class TestMcpCommand:
    """Test `gurume mcp` CLI flag wiring."""

    def test_help_lists_transport_flag(self):
        import re

        from typer.testing import CliRunner

        from gurume.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0
        # Strip ANSI escape sequences because Typer/Rich may color the help
        # output, splitting flag names across escape codes in CI.
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "--transport" in plain
        assert "streamable-http" in plain

    def test_default_invocation_uses_stdio(self):
        from typer.testing import CliRunner

        from gurume.cli import app

        runner = CliRunner()
        with patch("gurume.server.run") as mock_run:
            result = runner.invoke(app, ["mcp"])
            assert result.exit_code == 0
            mock_run.assert_called_once_with(transport="stdio", host="127.0.0.1", port=8000, path="/mcp")

    def test_http_invocation_passes_kwargs(self):
        from typer.testing import CliRunner

        from gurume.cli import app

        runner = CliRunner()
        with patch("gurume.server.run") as mock_run:
            result = runner.invoke(
                app,
                [
                    "mcp",
                    "--transport",
                    "streamable-http",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9001",
                    "--path",
                    "/api/mcp",
                ],
            )
            assert result.exit_code == 0
            mock_run.assert_called_once_with(
                transport="streamable-http",
                host="0.0.0.0",
                port=9001,
                path="/api/mcp",
            )
