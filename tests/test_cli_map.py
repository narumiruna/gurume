"""CLI map search envelopes and validation."""

import json
import re
from unittest.mock import patch

import pytest
from curl_cffi.requests import exceptions as request_errors
from typer.testing import CliRunner

from gurume.cli import app
from gurume.exceptions import ParseError
from gurume.map_search import MapSearchRequest

from .test_map_search import BOUNDS
from .test_map_search import XML

runner = CliRunner()
ARGS = ["map-search", "--min-lat", "34.36", "--max-lat", "35.15", "--min-lon", "135.85", "--max-lon", "137.25"]


def test_json_envelope_and_limit_preserve_upstream_metadata():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with patch.object(MapSearchRequest, "search_sync", return_value=result) as fetch:
        output = runner.invoke(app, [*ARGS, "-o", "json", "--limit", "1"])
    assert output.exit_code == 0, output.output
    data = json.loads(output.stdout)
    assert data["status"] == "success"
    assert data["scope"] == "geographic_rectangle"
    assert data["returned_count"] == 1 and data["has_more"] is True
    assert data["meta"]["total_count"] == 271 and data["meta"]["upstream_count"] == 2
    assert data["meta"]["page_size"] == 20
    assert data["applied_filters"]["sort"] == "ranking"
    assert data["items"][0]["latitude"] == pytest.approx(34.49462941849498)
    assert "Warning:" in output.stderr and "Map page" in output.stderr
    fetch.assert_called_once()


@pytest.mark.parametrize("output_format", ["json-list", "table", "simple", "json-envelope"])
def test_formats(output_format):
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with patch.object(MapSearchRequest, "search_sync", return_value=result):
        output = runner.invoke(app, [*ARGS, "-o", output_format])
    assert output.exit_code == 0, output.output
    if output_format == "json-list":
        data = json.loads(output.stdout)
        assert len(data) == 2 and data[1]["prefecture_code"] == "23"
    elif output_format == "json-envelope":
        assert json.loads(output.stdout)["returned_count"] == 2
    else:
        assert "にかわ" in output.stdout and "Warning:" in output.stdout


@pytest.mark.parametrize("output_format", ["table", "simple"])
@pytest.mark.parametrize("count,expected", [("0", "0"), ("", "N/A")])
def test_text_formats_distinguish_zero_and_missing_reviews(output_format, count, expected):
    result = MapSearchRequest(**BOUNDS)._parse(XML.replace('rvwcnt="0"', f'rvwcnt="{count}"'))
    with patch.object(MapSearchRequest, "search_sync", return_value=result):
        output = runner.invoke(app, [*ARGS, "-o", output_format])
    assert output.exit_code == 0, output.output
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output.stdout)
    if output_format == "simple":
        assert f"({expected} reviews)" in plain
    else:
        row = next(line for line in plain.splitlines() if "炭火焼鳥 かぐら" in line)
        assert row.split("│")[3].strip() == expected


def test_default_table_displays_geographic_evidence():
    result = MapSearchRequest(**BOUNDS)._parse(XML)
    with patch.object(MapSearchRequest, "search_sync", return_value=result):
        output = runner.invoke(app, ARGS)
    assert output.exit_code == 0, output.output
    plain = re.sub(r"\x1b\[[0-9;]*m", "", output.stdout)
    assert "Coordinates" in plain and "Pref. code" in plain
    assert "34.49463, 136.70591" in plain and "35.00000, 136.80000" in plain
    first = next(line for line in plain.splitlines() if "にかわ" in line)
    second = next(line for line in plain.splitlines() if "炭火焼鳥 かぐら" in line)
    assert first.split("│")[4].strip() == "24"
    assert second.split("│")[4].strip() == "23"


def test_invalid_bounds_are_structured_before_http():
    with patch.object(MapSearchRequest, "search_sync") as fetch:
        result = runner.invoke(app, [*ARGS, "--min-lat", "36", "-o", "json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["error"]["error_code"] == "invalid_parameters"
    assert data["error"]["retryable"] is False
    fetch.assert_not_called()


@pytest.mark.parametrize("extra", [["--limit", "21"], ["--page", "0"], ["--cuisine", "寿司"]])
def test_invalid_options_do_not_fetch(extra):
    with patch.object(MapSearchRequest, "search_sync") as fetch:
        result = runner.invoke(app, [*ARGS, *extra])
    assert result.exit_code != 0
    fetch.assert_not_called()


@pytest.mark.parametrize("page", [1, 2, 14])
@pytest.mark.parametrize("nextpg", ["", "next"])
def test_incomplete_page_is_upstream_error_not_no_results(page, nextpg):
    with patch("gurume.map_search.requests.get") as get:
        get.return_value.text = f'<markers><srchinfo cnt="271" nextpg="{nextpg}"/></markers>'
        result = runner.invoke(app, [*ARGS, "--page", str(page), "-o", "json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["status"] == "error" and data["error"]["error_code"] == "upstream_unavailable"
    assert data["error"]["retryable"] is False and data["has_more"] is False
    assert data["meta"] is None and data["items"] == []
    get.assert_called_once()


def test_empty_json_response():
    empty = MapSearchRequest(**BOUNDS)._parse('<markers><srchinfo cnt="0"/></markers>')
    with patch.object(MapSearchRequest, "search_sync", return_value=empty):
        result = runner.invoke(app, [*ARGS, "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["status"] == "no_results"


@pytest.mark.parametrize("error", [ParseError("challenge"), request_errors.HTTPError("403")])
def test_upstream_failure_produces_envelope(error):
    if isinstance(error, request_errors.HTTPError):
        from unittest.mock import Mock

        error.response = Mock(status_code=403)
    with patch.object(MapSearchRequest, "search_sync", side_effect=error):
        result = runner.invoke(app, [*ARGS, "-o", "json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["items"] == [] and data["meta"] is None
    assert data["error"]["error_code"] == "upstream_unavailable"
    assert data["error"]["retryable"] is False


@pytest.mark.parametrize("status,retryable", [(404, False), (410, False), (429, False), (500, True), (503, True)])
def test_http_retryability_in_json_envelope(status, retryable):
    from unittest.mock import Mock

    error = request_errors.HTTPError(str(status), response=Mock(status_code=status))
    with patch.object(MapSearchRequest, "search_sync", side_effect=error) as fetch:
        result = runner.invoke(app, [*ARGS, "-o", "json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["error"]["error_code"] == "upstream_unavailable"
    assert data["error"]["retryable"] is retryable
    fetch.assert_called_once()


@pytest.mark.parametrize("force_color", ["0", "1"])
def test_map_help_is_explicit(force_color):
    result = runner.invoke(app, ["map-search", "--help"], env={"FORCE_COLOR": force_color})
    assert result.exit_code == 0
    # Rich can insert ANSI styles between parts of a flag name in CI.
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "NOT an exact area ranking" in plain
    assert "--min-lat" in plain
