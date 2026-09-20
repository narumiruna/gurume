"""Offline contracts for the area catalog coverage CLI."""

import json
from pathlib import Path

import pytest

from gurume.area_mapping import parse_area_catalog_rows
from scripts import check_area_catalog_coverage as coverage


@pytest.fixture
def snapshot_row() -> dict[str, str]:
    return {
        "name": "梅田",
        "path": "osaka/A2701/A270101",
        "parent": "osaka/A2701",
        "source": "https://tabelog.com/osaka/A2701/A270101/",
        "discovered_at": "2026-05-30",
    }


@pytest.fixture
def snapshot_path(tmp_path: Path, snapshot_row: dict[str, str]) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps([snapshot_row]), encoding="utf-8")
    return path


@pytest.fixture
def catalog_row(snapshot_row: dict[str, str]) -> dict[str, object]:
    return {
        "name": snapshot_row["name"],
        "path": snapshot_row["path"],
        "parent": snapshot_row["parent"],
        "source": snapshot_row["source"],
        "level": "subarea",
        "aliases": [],
        "verified_at": snapshot_row["discovered_at"],
    }


def test_matching_coverage_cli(
    snapshot_path: Path,
    catalog_row: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    entries = parse_area_catalog_rows([catalog_row])
    monkeypatch.setattr(coverage, "get_area_catalog_entries", lambda: entries)
    assert coverage.main(["--snapshot", str(snapshot_path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == "area catalog covers 1 verified Tabelog leaf subarea paths\n"
    assert captured.err == ""


@pytest.mark.parametrize("include_extra", [False, True])
def test_missing_and_extra_paths_cli(
    snapshot_path: Path,
    catalog_row: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    include_extra: bool,
) -> None:
    extra_path = "osaka/A2701/A270102"
    catalog_row.update(path=extra_path, source=f"https://tabelog.com/{extra_path}/")
    entries = parse_area_catalog_rows([catalog_row]) if include_extra else ()
    monkeypatch.setattr(coverage, "get_area_catalog_entries", lambda: entries)
    assert coverage.main(["--snapshot", str(snapshot_path)]) == 1
    expected = "area catalog coverage check failed:\nmissing catalog paths:\n  osaka/A2701/A270101\n"
    if include_extra:
        expected += f"catalog paths not in snapshot:\n  {extra_path}\n"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == expected


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "must contain a JSON list"),
        ([None], "must contain only JSON objects"),
        ([{}], "snapshot row missing required keys"),
    ],
)
def test_malformed_snapshot_structure(snapshot_path: Path, data: object, message: str) -> None:
    snapshot_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(coverage.CoverageError, match=message):
        coverage.check_catalog_coverage(snapshot_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("path", "", "snapshot path must be a non-empty string"),
        ("parent", "osaka/A2702", "snapshot parent does not match path"),
        ("source", "https://example.com/", "snapshot source must be"),
    ],
)
def test_malformed_snapshot_relationships(
    snapshot_path: Path,
    snapshot_row: dict[str, str],
    field: str,
    value: str,
    message: str,
) -> None:
    snapshot_row[field] = value
    snapshot_path.write_text(json.dumps([snapshot_row]), encoding="utf-8")
    with pytest.raises(coverage.CoverageError, match=message):
        coverage.check_catalog_coverage(snapshot_path)


def test_duplicate_snapshot_paths(snapshot_path: Path, snapshot_row: dict[str, str]) -> None:
    snapshot_path.write_text(json.dumps([snapshot_row, snapshot_row]), encoding="utf-8")
    with pytest.raises(coverage.CoverageError, match="duplicate snapshot path: osaka/A2701/A270101"):
        coverage.check_catalog_coverage(snapshot_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("parent", "osaka/A2702", "area catalog parent does not match path"),
        ("source", "https://example.com/", "area catalog source must match path URL"),
    ],
)
def test_runtime_catalog_validation_propagates(
    snapshot_path: Path,
    catalog_row: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: str,
    message: str,
) -> None:
    catalog_row[field] = value
    monkeypatch.setattr(coverage, "get_area_catalog_entries", lambda: parse_area_catalog_rows([catalog_row]))
    with pytest.raises(ValueError, match=message):
        coverage.main(["--snapshot", str(snapshot_path)])


def test_invalid_json_propagates(snapshot_path: Path) -> None:
    snapshot_path.write_text("{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        coverage.check_catalog_coverage(snapshot_path)


def test_missing_snapshot_propagates(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        coverage.check_catalog_coverage(tmp_path / "missing.json")
