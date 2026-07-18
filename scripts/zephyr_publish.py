#!/usr/bin/env python3
"""Publish pytest JUnit XML results to a Zephyr Scale test cycle."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from zephyr.client import ZephyrScaleClient, ZephyrScaleError  # noqa: E402


def _git_short_sha() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=ROOT,
                text=True,
                stderr=subprocess.DEVNULL,
            )
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "local"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--junit",
        type=Path,
        default=ROOT / "reports" / "junit.xml",
        help="Path to pytest --junitxml output",
    )
    parser.add_argument(
        "--cycle-name",
        default="",
        help="Zephyr Scale test cycle name (default: includes git sha + timestamp)",
    )
    parser.add_argument(
        "--cycle-description",
        default="",
        help="Optional test cycle description",
    )
    parser.add_argument(
        "--auto-create-cases",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create missing Zephyr test cases from JUnit names (default: true)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    junit = args.junit if args.junit.is_absolute() else ROOT / args.junit
    if not junit.is_file():
        print(f"JUnit file not found: {junit}", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cycle_name = args.cycle_name or f"pytest {_git_short_sha()} @ {stamp}"
    description = args.cycle_description or (
        f"Automated pytest/Playwright run from {ROOT.name} ({_git_short_sha()})"
    )
    test_cycle = {
        "name": cycle_name,
        "description": description,
    }

    with ZephyrScaleClient() as zephyr:
        result = zephyr.upload_junit(
            junit,
            auto_create_test_cases=args.auto_create_cases,
            test_cycle=test_cycle,
        )

    print(f"Published {junit} to Zephyr Scale project {os.environ.get('ZEPHYR_PROJECT_KEY')}")
    print(f"Cycle: {cycle_name}")
    print(result)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ZephyrScaleError as exc:
        print(f"Zephyr Scale error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
