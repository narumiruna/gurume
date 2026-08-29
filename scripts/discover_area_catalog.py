"""Discover Tabelog leaf subarea paths for the area catalog.

The selectors intentionally target Tabelog's left navigation area lists instead of
suggestion API payloads. Suggestion responses expose labels and IDs, but they are
not a reliable URL-path source. Prefecture pages expose parent area paths such as
`/osaka/A2701/`; each parent page exposes leaf subarea paths such as
`/osaka/A2701/A270101/` in `#js-leftnavi-area-scroll`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Callable
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from curl_cffi import requests

from gurume.area_mapping import PREFECTURE_MAPPING
from gurume.http_client import DEFAULT_IMPERSONATE

BASE_URL = "https://tabelog.com"
DEFAULT_CACHE_DIR = Path(".cache/tabelog_area_catalog")
DEFAULT_SNAPSHOT_PATH = Path("tests/fixtures/tabelog_leaf_subareas_snapshot.json")


@dataclass(frozen=True)
class LeafSubareaRecord:
    """Discovered Tabelog leaf subarea record."""

    name: str
    path: str
    parent: str
    source: str
    discovered_at: str

    @classmethod
    def from_json(cls, row: dict[str, str]) -> LeafSubareaRecord:
        return cls(
            name=row["name"],
            path=row["path"],
            parent=row["parent"],
            source=row["source"],
            discovered_at=row["discovered_at"],
        )

    def to_json(self) -> dict[str, str]:
        return {
            "name": self.name,
            "path": self.path,
            "parent": self.parent,
            "source": self.source,
            "discovered_at": self.discovered_at,
        }


class DiscoveryError(RuntimeError):
    """Raised when live Tabelog discovery cannot produce a usable snapshot."""


class ProgressReporter:
    """Print periodic progress messages for long live crawls."""

    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = interval_seconds
        self._last_reported_at = 0.0
        self._started_at = time.monotonic()

    def force(self, message: str) -> None:
        self._last_reported_at = time.monotonic()
        print(f"[{self._elapsed()}] {message}", file=sys.stderr, flush=True)

    def maybe(self, message: str) -> None:
        if self.interval_seconds <= 0:
            return
        now = time.monotonic()
        if now - self._last_reported_at >= self.interval_seconds:
            self._last_reported_at = now
            print(f"[{self._elapsed()}] {message}", file=sys.stderr, flush=True)

    def _elapsed(self) -> str:
        elapsed = int(time.monotonic() - self._started_at)
        minutes, seconds = divmod(elapsed, 60)
        return f"{minutes:02d}:{seconds:02d}"


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


def _normalize_label(text: str) -> str:
    return " ".join(text.split()).strip()


def _path_from_href(href: str) -> str:
    parsed = urlparse(href)
    path = parsed.path if parsed.scheme else href.split("?", maxsplit=1)[0].split("#", maxsplit=1)[0]
    return path.strip("/")


def _cache_path(cache_dir: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.html"


def _fetch_html(
    session: requests.Session,
    url: str,
    *,
    cache_dir: Path,
    timeout: float,
    delay: float,
    use_cache: bool,
) -> str:
    cache_path = _cache_path(cache_dir, url)
    if use_cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code != 200:
                raise DiscoveryError(f"GET {url} returned HTTP {response.status_code}")
        except Exception as exc:  # noqa: BLE001 - CLI should retry and report the final failure.
            last_error = exc
            if attempt < 3:
                time.sleep(delay + attempt)
        else:
            html = response.text
            if use_cache:
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(html, encoding="utf-8")
            if delay > 0:
                time.sleep(delay)
            return html

    raise DiscoveryError(f"failed to fetch {url}: {last_error}") from last_error


def _path_pattern(slug: str, *, leaf: bool) -> re.Pattern[str]:
    suffix = r"A\d{4}/A\d{6}" if leaf else r"A\d{4}"
    return re.compile(rf"^{re.escape(slug)}/{suffix}$")


def _extract_named_paths(html: str, slug: str, *, leaf: bool) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    pattern = _path_pattern(slug, leaf=leaf)
    named_paths: dict[str, str] = {}

    # The full Tabelog area hierarchy is rendered in the left navigation. On prefecture pages it contains parent
    # paths; on parent pages it contains the leaf subarea paths. Sidebar recommendation links are intentionally ignored
    # because they include popular search shortcuts such as lunch/genre links for the same path.
    for anchor in soup.select("#js-leftnavi-area-scroll a[href]"):
        path = _path_from_href(str(anchor["href"]))
        if not pattern.fullmatch(path):
            continue
        name = _normalize_label(anchor.get_text(" ", strip=True))
        if not name:
            continue
        named_paths.setdefault(path, name)

    return named_paths


def _discover_prefecture(
    session: requests.Session,
    slug: str,
    *,
    discovered_at: str,
    cache_dir: Path,
    timeout: float,
    delay: float,
    use_cache: bool,
    reporter: ProgressReporter,
) -> list[LeafSubareaRecord]:
    prefecture_url = f"{BASE_URL}/{slug}/"
    prefecture_html = _fetch_html(
        session,
        prefecture_url,
        cache_dir=cache_dir,
        timeout=timeout,
        delay=delay,
        use_cache=use_cache,
    )
    parent_paths = sorted(_extract_named_paths(prefecture_html, slug, leaf=False))
    if not parent_paths:
        raise DiscoveryError(f"no parent area paths discovered from {prefecture_url}")

    reporter.force(f"{slug}: discovered {len(parent_paths)} parent area pages")
    fallback_leaf_names = _extract_named_paths(prefecture_html, slug, leaf=True)
    leaf_names: dict[str, str] = {}
    for parent_index, parent_path in enumerate(parent_paths, start=1):
        parent_url = f"{BASE_URL}/{parent_path}/"
        parent_html = _fetch_html(
            session,
            parent_url,
            cache_dir=cache_dir,
            timeout=timeout,
            delay=delay,
            use_cache=use_cache,
        )
        parent_leaf_names = _extract_named_paths(parent_html, slug, leaf=True)
        expected_prefix = f"{parent_path}/"
        leaf_names.update({path: name for path, name in parent_leaf_names.items() if path.startswith(expected_prefix)})
        reporter.maybe(
            f"{slug}: processed {parent_index}/{len(parent_paths)} parent pages, {len(leaf_names)} leaf paths so far"
        )

    if not leaf_names:
        leaf_names = fallback_leaf_names
    if not leaf_names:
        raise DiscoveryError(f"no leaf subarea paths discovered for {slug}")

    records: list[LeafSubareaRecord] = []
    for path, name in sorted(leaf_names.items()):
        parent = path.rsplit("/", maxsplit=1)[0]
        records.append(
            LeafSubareaRecord(
                name=name,
                path=path,
                parent=parent,
                source=f"{BASE_URL}/{path}/",
                discovered_at=discovered_at,
            )
        )
    return records


def _resolve_prefecture_slugs(values: Iterable[str], *, all_prefectures: bool) -> list[str]:
    if all_prefectures:
        return list(dict.fromkeys(PREFECTURE_MAPPING.values()))

    aliases = dict(PREFECTURE_MAPPING)
    aliases.update({slug: slug for slug in PREFECTURE_MAPPING.values()})
    resolved: list[str] = []
    for value in values:
        slug = aliases.get(value)
        if slug is None:
            raise DiscoveryError(f"unknown prefecture: {value}")
        resolved.append(slug)
    return list(dict.fromkeys(resolved))


def _select_batch(slugs: list[str], *, batch_size: int | None, batch_index: int | None) -> list[str]:
    if batch_size is None and batch_index is None:
        return slugs
    if batch_size is None or batch_index is None:
        raise DiscoveryError("--batch-size and --batch-index must be provided together")
    if batch_size < 1:
        raise DiscoveryError("--batch-size must be >= 1")
    if batch_index < 1:
        raise DiscoveryError("--batch-index is 1-based and must be >= 1")

    start = (batch_index - 1) * batch_size
    end = start + batch_size
    selected = slugs[start:end]
    if not selected:
        total_batches = (len(slugs) + batch_size - 1) // batch_size
        raise DiscoveryError(f"batch {batch_index} is empty; total batches: {total_batches}")
    return selected


def discover_leaf_subareas(
    slugs: Iterable[str],
    *,
    discovered_at: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    timeout: float = 30.0,
    delay: float = 0.25,
    use_cache: bool = True,
    initial_records: Iterable[LeafSubareaRecord] = (),
    on_checkpoint: Callable[[list[LeafSubareaRecord]], None] | None = None,
    reporter: ProgressReporter | None = None,
) -> list[LeafSubareaRecord]:
    """Discover leaf subareas for the given Tabelog prefecture slugs."""
    active_reporter = reporter or ProgressReporter(interval_seconds=0)
    session = requests.Session(impersonate=DEFAULT_IMPERSONATE)
    records = list(initial_records)
    seen_paths = {record.path for record in records}
    slugs_list = list(slugs)
    for slug_index, slug in enumerate(slugs_list, start=1):
        active_reporter.force(f"[{slug_index}/{len(slugs_list)}] starting {slug}")
        prefecture_records = _discover_prefecture(
            session,
            slug,
            discovered_at=discovered_at,
            cache_dir=cache_dir,
            timeout=timeout,
            delay=delay,
            use_cache=use_cache,
            reporter=active_reporter,
        )
        for record in prefecture_records:
            if record.path in seen_paths:
                raise DiscoveryError(f"duplicate discovered path: {record.path}")
            seen_paths.add(record.path)
            records.append(record)
        records.sort(key=lambda record: record.path)
        active_reporter.force(
            f"[{slug_index}/{len(slugs_list)}] finished {slug}: "
            f"{len(prefecture_records)} leaf paths, {len(records)} total"
        )
        if on_checkpoint is not None:
            on_checkpoint(records)
    return sorted(records, key=lambda record: record.path)


def _load_records(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise DiscoveryError(f"snapshot must be a list: {path}")
    records: list[dict[str, str]] = []
    for row in data:
        if not isinstance(row, dict):
            raise DiscoveryError(f"snapshot rows must be objects: {path}")
        records.append({str(key): str(value) for key, value in row.items()})
    return records


def _load_leaf_records(path: Path) -> list[LeafSubareaRecord]:
    return [LeafSubareaRecord.from_json(row) for row in _load_records(path)]


def _filter_records_by_slugs(records: list[dict[str, str]], slugs: set[str]) -> list[dict[str, str]]:
    return [record for record in records if record.get("path", "").split("/", maxsplit=1)[0] in slugs]


def _compare_with_snapshot(live_records: list[LeafSubareaRecord], snapshot_path: Path, *, slugs: set[str]) -> int:
    snapshot_records = _filter_records_by_slugs(_load_records(snapshot_path), slugs)
    live_by_path = {record.path: record.to_json() for record in live_records}
    snapshot_by_path = {record["path"]: record for record in snapshot_records}
    live_paths = set(live_by_path)
    snapshot_paths = set(snapshot_by_path)

    missing = sorted(snapshot_paths - live_paths)
    extra = sorted(live_paths - snapshot_paths)
    changed = sorted(
        path
        for path in live_paths & snapshot_paths
        if any(live_by_path[path].get(key) != snapshot_by_path[path].get(key) for key in ("name", "parent", "source"))
    )

    if not missing and not extra and not changed:
        print(f"Snapshot is fresh for {len(live_records)} leaf subarea paths: {snapshot_path}")
        return 0

    if missing:
        print("Missing from live discovery:", *missing[:20], sep="\n  ", file=sys.stderr)
    if extra:
        print("New live paths not in snapshot:", *extra[:20], sep="\n  ", file=sys.stderr)
    if changed:
        print("Changed live records:", *changed[:20], sep="\n  ", file=sys.stderr)
    print(
        f"Snapshot mismatch: missing={len(missing)} extra={len(extra)} changed={len(changed)}",
        file=sys.stderr,
    )
    return 1


def _write_records(path: Path, records: list[LeafSubareaRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.to_json() for record in sorted(records, key=lambda record: record.path)]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--all", action="store_true", help="discover all 47 Tabelog prefectures")
    scope.add_argument(
        "--prefecture",
        action="append",
        default=[],
        help="prefecture slug or Japanese name; repeat to discover multiple prefectures",
    )
    parser.add_argument("--output", type=Path, help="write discovered records to this JSON path")
    parser.add_argument("--resume", action="store_true", help="skip prefectures already present in --output")
    parser.add_argument("--batch-size", type=int, help="number of prefectures to process in this batch")
    parser.add_argument("--batch-index", type=int, help="1-based batch index to process with --batch-size")
    parser.add_argument(
        "--compare-snapshot",
        nargs="?",
        const=DEFAULT_SNAPSHOT_PATH,
        type=Path,
        help="compare live discovery with a snapshot path (default: tests fixture)",
    )
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="HTML cache directory")
    parser.add_argument("--no-cache", action="store_true", help="disable the HTML cache")
    parser.add_argument("--delay", type=float, default=0.25, help="delay after live requests in seconds")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--progress-interval",
        type=float,
        default=15.0,
        help="seconds between parent-page progress reports; prefecture start/end always prints",
    )
    parser.add_argument("--discovered-at", default=_today_iso(), help="ISO date to write into discovered_at")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        slugs = _resolve_prefecture_slugs(args.prefecture, all_prefectures=args.all)
        slugs = _select_batch(slugs, batch_size=args.batch_size, batch_index=args.batch_index)
        existing_records: list[LeafSubareaRecord] = []
        if args.resume:
            if args.output is None:
                raise DiscoveryError("--resume requires --output")
            if args.output.exists():
                existing_records = _load_leaf_records(args.output)
                completed_slugs = {record.path.split("/", maxsplit=1)[0] for record in existing_records}
                slugs = [slug for slug in slugs if slug not in completed_slugs]
                print(
                    f"Resuming from {args.output}: {len(completed_slugs)} completed prefecture(s), "
                    f"{len(slugs)} remaining in this run.",
                    file=sys.stderr,
                    flush=True,
                )

        reporter = ProgressReporter(interval_seconds=args.progress_interval)

        def checkpoint(records: list[LeafSubareaRecord]) -> None:
            if args.output is not None:
                _write_records(args.output, records)
                reporter.force(f"checkpoint wrote {len(records)} records to {args.output}")

        records = discover_leaf_subareas(
            slugs,
            discovered_at=args.discovered_at,
            cache_dir=args.cache_dir,
            timeout=args.timeout,
            delay=args.delay,
            use_cache=not args.no_cache,
            initial_records=existing_records,
            on_checkpoint=checkpoint,
            reporter=reporter,
        )
        print(f"Discovered {len(records)} leaf subarea paths across {len(slugs)} prefecture(s).")
        if args.output is not None:
            _write_records(args.output, records)
            print(f"Wrote {args.output}")
        if args.compare_snapshot is not None:
            compared_slugs = {record.path.split("/", maxsplit=1)[0] for record in records}
            return _compare_with_snapshot(records, args.compare_snapshot, slugs=compared_slugs)
    except DiscoveryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
