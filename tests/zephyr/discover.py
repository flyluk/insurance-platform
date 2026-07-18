"""Discover pytest tests and resolve Zephyr/story markers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from zephyr import MAPPING_PATH


@dataclass
class DiscoveredTest:
    nodeid: str
    name: str
    path: str
    zephyr_key: str | None = None
    story_key: str | None = None
    layers: list[str] = field(default_factory=list)
    objective: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def mapping_file(path: Path | None = None) -> Path:
    return path or (repo_root() / MAPPING_PATH)


def load_mapping(path: Path | None = None) -> dict[str, str]:
    file = mapping_file(path)
    if not file.is_file():
        return {}
    data = json.loads(file.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Mapping file must be a JSON object: {file}")
    return {str(k): str(v) for k, v in data.items()}


def save_mapping(mapping: dict[str, str], path: Path | None = None) -> Path:
    file = mapping_file(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(mapping.items()))
    file.write_text(json.dumps(ordered, indent=2) + "\n")
    return file


def _marker_arg(item: pytest.Item, name: str) -> str | None:
    marker = item.get_closest_marker(name)
    if not marker:
        return None
    if marker.args:
        return str(marker.args[0])
    if marker.kwargs.get("key"):
        return str(marker.kwargs["key"])
    return None


def _layers(item: pytest.Item) -> list[str]:
    found: list[str] = []
    for layer in ("api", "e2e", "ui"):
        if item.get_closest_marker(layer):
            found.append(layer)
    return found


def _objective(item: pytest.Item) -> str | None:
    doc = (item.obj.__doc__ or "").strip() if hasattr(item, "obj") else ""
    if not doc:
        return None
    return doc.splitlines()[0].strip()


def discover_tests(args: list[str] | None = None) -> list[DiscoveredTest]:
    """Collect pytest items without executing tests."""
    root = repo_root()
    mapping = load_mapping()
    collected: list[DiscoveredTest] = []

    class CollectorPlugin:
        def pytest_collection_finish(self, session: pytest.Session) -> None:
            for item in session.items:
                zephyr = _marker_arg(item, "zephyr") or mapping.get(item.nodeid)
                story = _marker_arg(item, "story")
                collected.append(
                    DiscoveredTest(
                        nodeid=item.nodeid,
                        name=item.name,
                        path=str(Path(item.path).relative_to(root)) if hasattr(item, "path") else item.nodeid,
                        zephyr_key=zephyr,
                        story_key=story,
                        layers=_layers(item),
                        objective=_objective(item),
                    )
                )

    pytest_args = [
        "--collect-only",
        "-q",
        "-p",
        "no:cacheprovider",
        "--no-zephyr-junit-prefix",
    ]
    if args:
        pytest_args.extend(args)
    else:
        pytest_args.append(str(root / "tests"))

    code = pytest.main(pytest_args, plugins=[CollectorPlugin()])
    if code == pytest.ExitCode.USAGE_ERROR:
        raise RuntimeError(f"pytest collection failed with exit code {code}")
    return collected


def labels_for(test: DiscoveredTest) -> list[str]:
    labels = ["automated", *test.layers]
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


def case_name_for(test: DiscoveredTest) -> str:
    if test.zephyr_key:
        return f"{test.zephyr_key} {test.name}"
    return test.name


def as_dict(test: DiscoveredTest) -> dict[str, Any]:
    return {
        "nodeid": test.nodeid,
        "name": test.name,
        "path": test.path,
        "zephyr_key": test.zephyr_key,
        "story_key": test.story_key,
        "layers": test.layers,
        "objective": test.objective,
    }
