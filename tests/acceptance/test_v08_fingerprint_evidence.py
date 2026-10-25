"""Reviewable v0.7 evidence is fixed data, never refreshed by this test."""

import json
from pathlib import Path, PureWindowsPath

import pytest

from tests.acceptance.v08_fingerprint_probe import snapshot


def assert_snapshot(actual, expected, path=()):
    if path[:2] == ("production_config", "paths") and len(path) == 3:
        # Evidence keeps the original Windows observations. Compare only path
        # separators portably, retaining exact spelling and all path components.
        assert PureWindowsPath(actual).as_posix() == PureWindowsPath(expected).as_posix()
    elif isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_snapshot(actual[key], expected[key], (*path, key))
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            assert_snapshot(left, right, path)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=0, abs=1e-6)
    else:
        assert actual == expected


def test_production_fingerprints_match_reviewed_v08_evidence():
    evidence = json.loads(
        (Path(__file__).resolve().parents[2] / "docs/v08_fingerprint_evidence.json")
        .read_text(encoding="utf-8")
    )
    actual = json.loads(json.dumps(snapshot(), default=str))
    assert_snapshot(actual, evidence["v08"])
    # Every difference from v0.7 must have an individually recorded authorization.
    migrated = evidence["v07"]
    for row in evidence["differences"]:
        assert row["approval"] in {"SCRUM-47", "SCRUM-49"}
        keys = row["path"].strip("/").split("/")
        parent = migrated
        for key in keys[:-1]:
            parent = parent[key]
        assert parent[keys[-1]] == row["before"]
        if row["status"] == "removed":
            del parent[keys[-1]]
        else:
            parent[keys[-1]] = row["after"]
    assert migrated == evidence["v08"]
