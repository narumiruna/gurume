#!/usr/bin/env python3
"""Sync canonical skill files into the Codex CLI runtime mirror."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "skills"
MIRROR_DIR = ROOT / ".agents" / "skills"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync skills/ to .agents/skills/.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only verify that .agents/skills/ matches skills/",
    )
    return parser.parse_args()


def iter_files(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def changed_files(source_files: set[Path], mirror_files: set[Path]) -> list[Path]:
    common_files = source_files & mirror_files
    return sorted(path for path in common_files if not filecmp.cmp(SOURCE_DIR / path, MIRROR_DIR / path, shallow=False))


def print_diff_summary() -> bool:
    if not SOURCE_DIR.is_dir():
        print(f"missing source directory: {SOURCE_DIR}", file=sys.stderr)
        return False

    source_files = iter_files(SOURCE_DIR)
    mirror_files = iter_files(MIRROR_DIR)
    missing_files = sorted(source_files - mirror_files)
    extra_files = sorted(mirror_files - source_files)
    modified_files = changed_files(source_files, mirror_files)

    if not missing_files and not extra_files and not modified_files:
        print(".agents/skills/ is in sync with skills/")
        return True

    for path in missing_files:
        print(f"missing in mirror: {path}")
    for path in extra_files:
        print(f"extra in mirror: {path}")
    for path in modified_files:
        print(f"modified in mirror: {path}")
    return False


def sync_skills() -> None:
    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"missing source directory: {SOURCE_DIR}")

    if MIRROR_DIR.exists():
        shutil.rmtree(MIRROR_DIR)
    shutil.copytree(SOURCE_DIR, MIRROR_DIR)
    print(f"synced {SOURCE_DIR.relative_to(ROOT)}/ to {MIRROR_DIR.relative_to(ROOT)}/")


def main() -> int:
    args = parse_args()
    if args.check:
        return 0 if print_diff_summary() else 1

    sync_skills()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
