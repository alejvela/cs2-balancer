"""Keep the documented current version aligned with project metadata."""

import re
import tomllib
from pathlib import Path


def test_documented_current_version_matches_project_metadata():
    root = Path(__file__).resolve().parents[2]
    with (root / "pyproject.toml").open("rb") as source:
        version = tomllib.load(source)["project"]["version"]
    readme = (root / "README.md").read_text(encoding="utf-8")
    current = re.search(r"The current release(?: candidate)? is `([^`]+)`", readme)
    assert current is not None, "README must identify the current release/candidate"
    assert current.group(1) == version
    notes = (root / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert notes.splitlines()[0].startswith(f"# cs2-balancer v{version} ")
