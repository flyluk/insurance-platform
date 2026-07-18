#!/usr/bin/env python3
"""Sync pytest/Playwright tests to Zephyr Scale test cases and story links."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from zephyr.client import ZephyrScaleClient, ZephyrScaleError  # noqa: E402
from zephyr.discover import (  # noqa: E402
    case_name_for,
    discover_tests,
    labels_for,
    load_mapping,
    save_mapping,
)
from zephyr.jira import JiraClient, JiraError  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned creates/updates without calling Zephyr/Jira APIs",
    )
    parser.add_argument(
        "--no-link-stories",
        action="store_true",
        help="Skip linking test cases to Jira stories",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Optional pytest paths/args to limit collection (default: all tests)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    tests = discover_tests(args.pytest_args or None)
    if not tests:
        print("No tests collected")
        return 1

    mapping = load_mapping()
    print(f"Collected {len(tests)} tests ({len(mapping)} existing mapping entries)")

    if args.dry_run:
        for test in tests:
            action = "update" if test.zephyr_key else "create"
            print(
                f"[{action}] {test.nodeid} zephyr={test.zephyr_key or '-'} "
                f"story={test.story_key or '-'} labels={labels_for(test)}"
            )
        return 0

    created = 0
    updated = 0
    linked = 0
    jira: JiraClient | None = None
    if not args.no_link_stories and any(t.story_key for t in tests):
        try:
            jira = JiraClient()
        except JiraError as exc:
            print(f"Story linking disabled: {exc}", file=sys.stderr)

    try:
        with ZephyrScaleClient() as zephyr:
            for test in tests:
                name = case_name_for(test)
                labels = labels_for(test)
                objective = test.objective or f"Automated coverage for {test.nodeid}"
                key = test.zephyr_key

                if key:
                    existing = zephyr.get_test_case(key)
                    if existing:
                        zephyr.update_test_case(
                            key, name=name, objective=objective, labels=labels
                        )
                        updated += 1
                        print(f"updated {key} <- {test.nodeid}")
                    else:
                        created_case = zephyr.create_test_case(
                            name=name, objective=objective, labels=labels
                        )
                        key = created_case.get("key")
                        if not key:
                            raise ZephyrScaleError(f"Create response missing key: {created_case}")
                        mapping[test.nodeid] = key
                        created += 1
                        print(f"recreated {key} <- {test.nodeid}")
                else:
                    created_case = zephyr.create_test_case(
                        name=name, objective=objective, labels=labels
                    )
                    key = created_case.get("key")
                    if not key:
                        raise ZephyrScaleError(f"Create response missing key: {created_case}")
                    mapping[test.nodeid] = key
                    created += 1
                    print(f"created {key} <- {test.nodeid}")

                if jira and test.story_key and key:
                    try:
                        issue_id = jira.issue_id(test.story_key)
                        zephyr.link_test_case_to_issue(key, issue_id)
                        linked += 1
                        print(f"linked {key} -> {test.story_key} ({issue_id})")
                    except ZephyrScaleError as exc:
                        msg = str(exc)
                        if "already has a COVERAGE link" in msg:
                            linked += 1
                            print(f"linked {key} -> {test.story_key} (already)")
                        else:
                            print(f"link skip {key} -> {test.story_key}: {exc}", file=sys.stderr)
                    except JiraError as exc:
                        print(f"link skip {key} -> {test.story_key}: {exc}", file=sys.stderr)
    finally:
        if jira:
            jira.close()

    path = save_mapping(mapping)
    print(f"Done. created={created} updated={updated} linked={linked} mapping={path}")
    print(
        'Tip: add @pytest.mark.zephyr("<KEY>") from mapping.json for stable keys in source.'
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ZephyrScaleError as exc:
        print(f"Zephyr Scale error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
