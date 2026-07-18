"""Pytest plugin: zephyr/story markers and JUnit naming for Zephyr Scale."""

from __future__ import annotations

import re

import pytest

from zephyr.discover import load_mapping, resolve_zephyr_key

_ZEPHYR_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-T\d+$")


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("zephyr")
    group.addoption(
        "--zephyr-junit-prefix",
        action="store_true",
        default=True,
        help="Prefix JUnit/node names with Zephyr case keys when available (default: on).",
    )
    group.addoption(
        "--no-zephyr-junit-prefix",
        action="store_false",
        dest="zephyr_junit_prefix",
        help="Disable Zephyr key prefixing in JUnit/node names.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "zephyr(key): Zephyr Scale test case key (e.g. INS-T12)")
    config.addinivalue_line("markers", "story(key): Jira story key for Zephyr coverage (e.g. INS-123)")


def _marker_zephyr_key(item: pytest.Item) -> str | None:
    marker = item.get_closest_marker("zephyr")
    if not marker:
        return None
    if marker.args:
        return str(marker.args[0])
    if marker.kwargs.get("key"):
        return str(marker.kwargs["key"])
    return None


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption("zephyr_junit_prefix"):
        return
    mapping = load_mapping()
    for item in items:
        key = resolve_zephyr_key(
            nodeid=item.nodeid,
            marker_key=_marker_zephyr_key(item),
            mapping=mapping,
        )
        if not key:
            continue
        if not _ZEPHYR_KEY_RE.match(key):
            continue
        # Zephyr JUnit importer matches by test case key prefix in the name.
        if item.name.startswith(f"{key}_") or item.name.startswith(f"{key} "):
            continue
        item._nodeid = item.nodeid.replace(item.name, f"{key}_{item.name}", 1)
        item.name = f"{key}_{item.name}"
        item.user_properties.append(("zephyr_key", key))


def pytest_report_header(config: pytest.Config) -> list[str]:
    mapping = load_mapping()
    prefix = "on" if config.getoption("zephyr_junit_prefix") else "off"
    return [f"zephyr: mapping_entries={len(mapping)} junit_prefix={prefix}"]
