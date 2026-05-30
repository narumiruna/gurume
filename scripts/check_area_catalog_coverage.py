"""Check that the runtime area catalog covers the verified Tabelog leaf-subarea snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from gurume.area_mapping import get_area_catalog_entries

DEFAULT_CATALOG_PATH = Path("src/gurume/data/area_catalog.json")
DEFAULT_SNAPSHOT_PATH = Path("tests/fixtures/tabelog_leaf_subareas_snapshot.json")
REQUIRED_SNAPSHOT_KEYS = frozenset({"name", "path", "parent", "source", "discovered_at"})


class CoverageError(RuntimeError):
    """Raised when catalog coverage does not match the snapshot."""


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise CoverageError(f"{path} must contain a JSON list")

    rows: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            raise CoverageError(f"{path} must contain only JSON objects")
        rows.append(row)
    return rows


def _validate_snapshot_rows(snapshot_path: Path) -> list[dict[str, Any]]:
    rows = _load_json_list(snapshot_path)
    seen_paths: set[str] = set()
    for row in rows:
        missing = REQUIRED_SNAPSHOT_KEYS - row.keys()
        if missing:
            raise CoverageError(f"snapshot row missing required keys for {row.get('path')}: {sorted(missing)}")
        path = row["path"]
        parent = row["parent"]
        source = row["source"]
        if not isinstance(path, str) or not path:
            raise CoverageError("snapshot path must be a non-empty string")
        if path in seen_paths:
            raise CoverageError(f"duplicate snapshot path: {path}")
        seen_paths.add(path)
        if not isinstance(parent, str) or parent != path.rsplit("/", maxsplit=1)[0]:
            raise CoverageError(f"snapshot parent does not match path: {parent} -> {path}")
        expected_source = f"https://tabelog.com/{path}/"
        if source != expected_source:
            raise CoverageError(f"snapshot source must be {expected_source}: {source}")
    return rows


def _format_sample(paths: list[str]) -> str:
    sample = "\n  ".join(paths[:20])
    if len(paths) > 20:
        sample += f"\n  ... and {len(paths) - 20} more"
    return sample


def check_catalog_coverage(snapshot_path: Path = DEFAULT_SNAPSHOT_PATH) -> None:
    """Raise CoverageError if the packaged catalog does not exactly cover the snapshot path set."""
    snapshot_rows = _validate_snapshot_rows(snapshot_path)
    catalog_entries = get_area_catalog_entries()

    snapshot_paths = {row["path"] for row in snapshot_rows}
    catalog_paths = {entry.path for entry in catalog_entries}
    missing = sorted(snapshot_paths - catalog_paths)
    extra = sorted(catalog_paths - snapshot_paths)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing catalog paths:\n  {_format_sample(missing)}")
        if extra:
            details.append(f"catalog paths not in snapshot:\n  {_format_sample(extra)}")
        raise CoverageError("\n".join(details))

    for entry in catalog_entries:
        expected_source = f"https://tabelog.com/{entry.path}/"
        if entry.source != expected_source:
            raise CoverageError(f"catalog source must be {expected_source}: {entry.source}")
        if entry.parent != entry.path.rsplit("/", maxsplit=1)[0]:
            raise CoverageError(f"catalog parent does not match path: {entry.parent} -> {entry.path}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH, help="verified leaf-subarea snapshot")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        check_catalog_coverage(args.snapshot)
    except CoverageError as exc:
        print(f"area catalog coverage check failed:\n{exc}", file=sys.stderr)
        return 1

    catalog_size = len(get_area_catalog_entries())
    print(f"area catalog covers {catalog_size} verified Tabelog leaf subarea paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
