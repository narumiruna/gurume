from __future__ import annotations

import os
import subprocess
import sys


def _read_default_impersonate(environment: dict[str, str]) -> str:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from gurume.http_client import DEFAULT_IMPERSONATE; print(DEFAULT_IMPERSONATE)",
        ],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return result.stdout.strip()


def test_default_impersonate_is_safari() -> None:
    environment = os.environ.copy()
    environment.pop("GURUME_IMPERSONATE", None)

    assert _read_default_impersonate(environment) == "safari"


def test_empty_impersonate_override_uses_safari() -> None:
    environment = os.environ.copy()
    environment["GURUME_IMPERSONATE"] = ""

    assert _read_default_impersonate(environment) == "safari"


def test_default_impersonate_honors_environment_override() -> None:
    environment = os.environ.copy()
    environment["GURUME_IMPERSONATE"] = "firefox"

    assert _read_default_impersonate(environment) == "firefox"
